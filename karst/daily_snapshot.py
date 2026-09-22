"""Daily snapshot (日更快照): the mechanical layer of an incremental build.

Each day, for each monitored security, the machine brings the numbers up to date and
decides *who has to look*; it never judges. The snapshot holds the new bars, the
technical readings (the same ``charts.measure`` numbers a chart is drawn from), the
distance from the close to every price in the research plan, where the close sits
against the fair-value range, reward/risk at the close and the entry / invalidation /
target trigger states. It is saved beside the research version it reads and never
changes that version, records no update check and publishes nothing.

What changed decides which layers go to the agent queue (``karst.updates`` routing):

* a price event — a trigger state changed, the close crossed the 200-day SMA or a key
  level, a new BOS/CHoCH, a gap of several ATRs, reward/risk crossing its threshold —
  queues L5/L6 (``updates.PRICE_EVENT_LAYERS``);
* new news candidates queue the news layers (``updates.KIND_LAYERS['news']``);
* incomplete source coverage queues nothing but holds the news window where it is.

A radar member without formal research gets the technical part only: there is no plan
to update and nothing to reassess. No ticker, date or security lives here.
"""
from __future__ import annotations

from . import charts, updates
from .calculations import calculate_valuation, risk_reward
from .schema import ContractError

VERSION = "daily-snapshot/1"

# Event thresholds (事件門檻): defaults, each with its reason — the one place to tune.
GAP_ATR_MULTIPLE = 2.0   # an open two daily ATRs away from the prior close is outside a
                         # normal day's range: the market repriced overnight
RR_THRESHOLD = 2.0       # reward/risk at the close crossing 2:1, the usual floor for a
                         # long plan to be worth its planned loss
STRUCTURE_KINDS = ("bos", "choch")  # breaks of structure; swings and sweeps are context
QUEUE_REASONS_KEPT = 20  # an unreviewed queue keeps its latest reasons, not a year of them

TRIGGERS = {  # plan field -> (name, state when the close is on the plan's side, otherwise)
    "entry_price": ("entry", "at_or_below", "above"),
    "exit_price": ("invalidation", "breached", "holding"),
    "target_price": ("target", "reached", "below"),
}


def merge_bars(stored, fresh):
    """Stored history plus a newer snapshot's bars: the newer one owns every day it covers.

    This is ``bars._select``'s rule — older snapshots only extend history before the
    newest one starts — applied to a series already built, so the result equals a
    rebuild from all evidence.
    """
    if not fresh:
        return list(stored)
    first = fresh[0]["at"][:10]
    return [bar for bar in stored if bar["at"][:10] < first] + list(fresh)


def _last_complete(bars):
    return next((bar for bar in reversed(bars) if bar["complete"]), None)


def _plan_view(plan, close, factor, distributions):
    """Distances, triggers and reward/risk at the close, in the plan's quote basis."""
    price = close / factor
    levels, triggers = {}, {}
    for field in ("entry_price", "exit_price", "target_price", "stress_price"):
        level = plan.get(field)
        if level is None:
            continue
        levels[field] = {"price": level, "distance": level - price,
                         "distance_pct": level / price - 1}
        if field in TRIGGERS:
            name, on_side, off_side = TRIGGERS[field]
            hit = price >= level if field == "target_price" else price <= level
            triggers[name] = on_side if hit else off_side
    exit_price = plan.get("exit_price")
    if exit_price is not None and exit_price >= price:
        reward = {"available": False, "reason": "close at or below the planned exit"}
    else:
        try:
            reward = risk_reward({"round_trip_cost_per_share": 0, "stress_price": None,
                                  **plan, "entry_price": price}, distributions)
        except (ContractError, KeyError, TypeError, ZeroDivisionError) as exc:
            reward = {"available": False, "reason": f"plan cannot be priced at the close: {exc}"}
    return {"close_quote_basis": price, "levels": levels, "triggers": triggers,
            "risk_reward_at_close": reward}


def _valuation_view(valuation, close, factor):
    fair, gaps = {}, []
    for row in valuation.get("scenarios") or []:
        try:
            fair[row["name"]] = calculate_valuation(row["calculation"])["outputs"]["fair_value_per_share"]
        except Exception as exc:  # noqa: BLE001 - an old contract's calculation is a gap, not a crash
            gaps.append(f"{row.get('name')}: {exc}")
    if not fair:
        return {"fair_value": None, "gaps": gaps or ["no calculated scenario"]}
    price = close / factor
    ordered = sorted(fair.values())
    position = ("below_range" if price < ordered[0] else
                "above_range" if price > ordered[-1] else "inside_range")
    base = fair.get("base")
    return {"fair_value": fair, "position": position,
            "to_base_pct": None if not base else base / price - 1, "gaps": gaps}


def _zone(zone):
    return None if not zone else {"lower": zone["lower"], "upper": zone["upper"],
                                  "touches": zone.get("touches")}


def _state(state):
    return None if not state else {key: value for key, value in state.items()
                                   if key not in ("definition", "parameters")}


def _side(close, level):
    return None if level is None else ("above" if close > level else "at_or_below")


def _events(previous, current, measured, fresh, has_research):
    """Price events against the previous snapshot of the same research version."""
    events = []
    if previous is None:
        return events
    prior = previous.get("technical") or {}
    now = current["technical"]
    if has_research:
        before = (previous.get("plan") or {}).get("triggers") or {}
        for name, state in ((current.get("plan") or {}).get("triggers") or {}).items():
            if before.get(name) not in (None, state):
                events.append({"kind": "trigger_changed", "trigger": name,
                               "before": before[name], "after": state})
        old_rr = ((previous.get("plan") or {}).get("risk_reward_at_close") or {}).get("ratio")
        new_rr = ((current.get("plan") or {}).get("risk_reward_at_close") or {}).get("ratio")
        if None not in (old_rr, new_rr) and (old_rr >= RR_THRESHOLD) != (new_rr >= RR_THRESHOLD):
            events.append({"kind": "rr_cross", "before": old_rr, "after": new_rr,
                           "threshold": RR_THRESHOLD})
    if prior.get("sma200_side") and now.get("sma200_side") and prior["sma200_side"] != now["sma200_side"]:
        events.append({"kind": "sma200_cross", "before": prior["sma200_side"],
                       "after": now["sma200_side"], "sma200": now["sma200"]})
    close = now["close"]
    resistance, support = prior.get("resistance"), prior.get("support")
    if close is not None and resistance and close > resistance["upper"]:
        events.append({"kind": "level_cross", "level": "resistance", "zone": resistance})
    if close is not None and support and close < support["lower"]:
        events.append({"kind": "level_cross", "level": "support", "zone": support})
    since = prior.get("last_complete_at") or ""
    for rule, view in (measured.get("views") or {}).items():
        for event in (view.get("structure") or {}).get("events") or []:
            if event["kind"] in STRUCTURE_KINDS and event["confirmed_at"] > since \
                    and event.get("status", "confirmed") == "confirmed":
                events.append({"kind": "structure", "timeframe": rule, "structure": event["kind"],
                               "direction": event["direction"], "level": event["level"],
                               "confirmed_at": event["confirmed_at"]})
    atr = now.get("atr")
    for before_bar, bar in zip(fresh, fresh[1:]):
        if bar["complete"] and bar["at"] > since and atr:
            gap = bar["open"] - before_bar["close"]
            if abs(gap) >= GAP_ATR_MULTIPLE * atr:
                events.append({"kind": "gap", "at": bar["at"], "gap": gap, "atr": atr,
                               "multiple": abs(gap) / atr, "threshold": GAP_ATR_MULTIPLE})
    return events


def build(*, subject, checked_at, bars, new_bars, research, previous, news_candidates,
          coverage_complete, reviewed_at=None):
    """One day's snapshot. ``research`` is the latest research row (or None for radar).

    ``previous`` is the last snapshot; its queue carries forward until an update check
    (``reviewed_at``) is recorded after it was queued. ``new_bars`` are the bars this
    refresh added, plus the one before them so a gap can be measured.
    """
    measured = charts.measure(bars)
    last = _last_complete(bars)
    daily = measured["daily"]
    sma200 = daily["moving_averages"]["sma200"]["value"]
    views = measured["views"]
    close = last["close"] if last else None
    technical = {
        "close": close, "last_complete_at": last["at"] if last else None,
        "last_bar": daily["last_bar"], "last_bar_complete": daily["last_bar_complete"],
        "bars_count": daily["bars_count"], "moving_averages": daily["moving_averages"],
        "sma200": sma200, "sma200_side": _side(close, sma200) if close is not None else None,
        "atr": daily["atr"], "volume": daily["volume"],
        "resistance": _zone(views["D"]["levels"]["resistance"]),
        "support": _zone(views["D"]["levels"]["support"]),
        "structure": {rule: _state(view.get("structure", {}).get("state")) for rule, view in views.items()},
        "charts_version": measured["charts_version"]}
    payload = (research or {}).get("payload") or {}
    has_research = bool(payload)
    plan = valuation = None
    if has_research and close is not None:
        factor = (payload.get("technical") or {}).get("quote_to_bar_factor") or 1.0
        distributions = (payload.get("valuation") or {}).get("expected_distributions") or 0
        if payload.get("plan"):
            plan = _plan_view(payload["plan"], close, factor, distributions)
        if payload.get("valuation"):
            valuation = _valuation_view(payload["valuation"], close, factor)
    snapshot = {"snapshot_version": VERSION, "subject": subject, "date": checked_at[:10],
                "checked_at": checked_at,
                "base_version_id": (research or {}).get("version_id"),
                "target_date": payload.get("target_date"),
                "new_bars": new_bars, "technical": technical, "plan": plan, "valuation": valuation}
    same_version = previous and previous.get("base_version_id") == snapshot["base_version_id"]
    if has_research and plan and not same_version:
        # No earlier snapshot of this version: its triggers start from the price the
        # research was written at, so a move since then is still an event today.
        market = payload.get("market") or {}
        factor = (payload.get("technical") or {}).get("quote_to_bar_factor") or 1.0
        if market.get("price"):
            start = _plan_view(payload["plan"], market["price"] * factor, factor,
                               (payload.get("valuation") or {}).get("expected_distributions") or 0)
            previous_view = {"plan": start, "technical": (previous or {}).get("technical") or {}}
        else:
            previous_view = previous
    else:
        previous_view = previous
    events = _events(previous_view, snapshot, measured, new_bars, has_research)
    reasons = [{"kind": "price_event", "events": events}] if events and has_research else []
    layers = set(updates.PRICE_EVENT_LAYERS) if reasons else set()
    if news_candidates and has_research:
        reasons.append({"kind": "news", "evidence_ids": [c["evidence_id"] for c in news_candidates]})
        layers.update(updates.KIND_LAYERS["news"])
    queued = (previous or {}).get("queue") or {}
    if queued.get("layers") and not (reviewed_at and reviewed_at > queued["since"]) \
            and queued.get("base_version_id") == snapshot["base_version_id"]:
        layers.update(queued["layers"])
        reasons = queued["reasons"] + reasons
        since = queued["since"]
    else:
        since = checked_at
    snapshot["events"] = events
    snapshot["queue"] = ({"layers": sorted(layers), "since": since,
                          "base_version_id": snapshot["base_version_id"],
                          "reasons": reasons[-QUEUE_REASONS_KEPT:]} if layers else None)
    snapshot["news"] = {"candidates": len(news_candidates), "coverage_complete": coverage_complete,
                        "pending_review": bool(snapshot["queue"] and "L2" in snapshot["queue"]["layers"])}
    return snapshot
