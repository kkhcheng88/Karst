"""Confirmed market structure: swings, breaks, prior highs and liquidity sweeps.

The chart module already finds confirmed pivots and clusters them into support and
resistance bands. That answers *where* levels are. It does not answer what the
sequence of levels is doing, nor what happened when price arrived at one — which is
where the reading breaks down. Each capability here exists to close one such gap:

* **Labelled swings (HH / HL / LH / LL) and a trend state** — the pivot list is a
  price-sorted set, so nothing in it says whether the sequence is rising or falling;
  without that a fall into a zone cannot be told from a pullback inside an uptrend
  (**waiting**).
* **BOS** — a zone says a level exists, never that it was taken out on a closing
  basis, so the moment a range actually gives way has no timestamp (**trigger**).
* **CHoCH** — nothing in the existing analysis dates the bar on which the trend
  stopped being the trend, which is exactly when a trend-following thesis dies
  (**invalidation**).
* **Prior high / low and their retest** — a cluster forgets that one of its pivots
  was broken, so a level already taken out and one never tested look identical; the
  difference is entry-on-breakout versus entry-on-pullback (**waiting**).
* **Equal highs / lows** — two pivots within a fraction of an ATR read today as "a
  slightly wide zone" rather than as a level price has twice refused to leave behind
  (**missed read**).
* **Liquidity sweep** — a bar poking a wick through a zone and a bar closing through
  it currently count as the same touch, which is the difference between a failed
  breakout and a breakout (**missed read**, and the **invalidation** of the break).

The swing definition is the repository's existing confirmed pivot
(:func:`karst.calculations.confirmed_pivots`): a symmetric left/right window of
``width`` bars, strict inequality, confirmed on the close of the right-hand bar.
**This is not LuxAlgo's ``leg(size)`` rule**, which detects the leg on the current
bar and draws the marker back at ``time[size]``; results near a turn will differ and
no claim of point-for-point agreement with that script is made here.

Nothing is decided from a bar the caller has not declared complete: pivots come only
from complete bars, breaks and sweeps read on an incomplete bar are emitted as
``provisional`` and change no state. A confirmed event is never rewritten — its
status only ever moves forward (confirmed -> touched -> invalidated), which is what
makes a prefix replay of the same series reproduce the same history.
"""
from __future__ import annotations

from .calculations import confirmed_pivots
from .schema import canonical, digest

DEFINITION = "karst.structure/1"
ATR_PERIOD = 14
PIVOT_WIDTH = 2
ATR_MULTIPLE = 0.25    # two swings within a quarter ATR of each other are "equal"
# A break given back on the next bar or the one after is the cross-bar version of the
# same-bar sweep. Beyond that, a close back under the level is a pullback to it, which
# is a different reading and is carried by prior_high / retested_at instead.
RECLAIM_WINDOW = 2
EVENTS_KEPT = 12       # the recent tail a reader is shown; the run keeps all of them
STATUSES = ("provisional", "confirmed", "touched", "invalidated")
KINDS = ("swing", "bos", "choch", "sweep", "equal_levels")
SIDES = {"up": "high", "down": "low"}


def atr_series(bars, period=ATR_PERIOD):
    """Wilder's ATR after each bar: the first ``period`` true ranges averaged, then
    ``((period-1)*prev + tr)/period``. ``None`` until the window has filled, and an
    incomplete bar carries the previous value rather than moving it.

    One value per input bar, so a tolerance quoted at bar *t* uses only bars up to
    *t* — a single figure taken from the end of the run would be hindsight.
    """
    out, ranges, value, previous = [], [], None, None
    for bar in bars:
        if bar["complete"]:
            if previous is not None:
                true_range = max(bar["high"] - bar["low"],
                                 abs(bar["high"] - previous["close"]),
                                 abs(bar["low"] - previous["close"]))
                if value is None:
                    ranges.append(true_range)
                    if len(ranges) == period:
                        value = sum(ranges) / period
                else:
                    value = (value * (period - 1) + true_range) / period
            previous = bar
        out.append(value)
    return out


# --- events ----------------------------------------------------------------

def _event(kind, direction, *, timeframe, anchor_time, confirmed_at, level,
           status="confirmed", invalidation=None, refs=(), zone=None, **extra):
    """One structure event. ``anchor_time`` is when the price extreme or level formed,
    ``confirmed_at`` the close of the bar that made it knowable — never the same bar
    for a swing, and never a later bar for a break."""
    event = {"event_id": None, "kind": kind, "direction": direction, "timeframe": timeframe,
             "anchor_time": anchor_time, "confirmed_at": confirmed_at, "level": level,
             "zone": zone, "status": status, "status_at": confirmed_at,
             "invalidation": invalidation, "definition": DEFINITION, "refs": list(refs),
             **extra}
    event["event_id"] = "st-" + digest(canonical(
        [kind, direction, timeframe, anchor_time, confirmed_at, level]))[:12]
    return event


def _advance(event, status, at):
    """Status only ever moves forward. A later bar may report that a level was retested
    or taken out; it may not un-confirm what was already true."""
    if STATUSES.index(status) > STATUSES.index(event["status"]):
        event["status"], event["status_at"] = status, at


def _label(side, previous, price):
    """HH/LH above, HL/LL below — against the previous swing of the same side, broken
    or not. ``None`` for the first one: there is nothing yet to be higher than."""
    if previous is None:
        return None
    if side == "up":
        return "HH" if price > previous["price"] else "LH"
    return "HL" if price > previous["price"] else "LL"


def _zone_for(zones, price, now):
    """The support/resistance band this level sits in, if one was already confirmed.

    A reference only: the band's edges are as the caller's zone list stands now, so
    they are a reading aid. The event's own level, times and direction are its
    identity; this is not.
    """
    for zone in zones or ():
        if zone["lower"] <= price <= zone["upper"] and zone["last_confirmed_at"] <= now:
            return {"pivots": zone["pivots"], "lower": zone["lower"], "upper": zone["upper"]}
    return None


def _beyond(side, price, level):
    return price > level if side == "up" else price < level


def _other(side):
    return "down" if side == "up" else "up"


def _side_word(side):
    return "above" if side == "up" else "below"


def _view(record):
    if record is None:
        return None
    return {"price": record["price"], "formed_at": record["formed_at"],
            "confirmed_at": record["confirmed_at"], "label": record["event"].get("label"),
            "status": record["event"]["status"], "event_id": record["event"]["event_id"]}


def events(bars, *, width=PIVOT_WIDTH, atr_multiple=ATR_MULTIPLE,
           reclaim_window=RECLAIM_WINDOW, timeframe="D", zones=None):
    """Swings, breaks, sweeps and equal levels for one timeframe's bars.

    Returns ``{"swings": [...], "events": [...], "state": {...}}``: the labelled swing
    sequence, everything that happened *to* those levels (bos / choch / sweep /
    equal_levels), and where structure stands after the last bar. ``zones`` is the
    optional support/resistance list from :func:`karst.charts.key_levels`, used only
    to say which band an event relates to.

    Bars are walked once, oldest first. Each bar is read against the levels that were
    already knowable before it (breaks and sweeps) and only then contributes the
    pivots it confirms — which is why a level can never be broken by the same bar
    that confirmed it, and why feeding a prefix of the series reproduces this history
    exactly rather than a reconstruction of it.
    """
    bars = list(bars or [])
    parameters = {"definition": DEFINITION, "pivot_width": width,
                  "pivot_rule": "symmetric confirmed pivot, strict, right-bar close "
                                "(karst.calculations.confirmed_pivots); not LuxAlgo leg(size)",
                  "break_rule": "close of a complete bar beyond the most recent confirmed "
                                "swing level", "atr_multiple": atr_multiple,
                  "atr_period": ATR_PERIOD, "reclaim_window": reclaim_window}
    atr_values = atr_series(bars)
    arriving = {}
    for pivot in confirmed_pivots(bars, width=width):
        arriving.setdefault(pivot["confirmed_at"], []).append(pivot)

    swings, other = [], []
    armed = {"up": None, "down": None}    # the level currently available to be broken
    latest = {"up": None, "down": None}   # the most recent confirmed swing, broken or not
    prior = {"up": None, "down": None}    # the most recently broken level, and its retest
    watching = []                         # breaks still inside their reclaim window
    trend, trend_since = "undetermined", None

    for index, bar in enumerate(bars):
        now, closed, atr_now = bar["at"], bar["complete"], atr_values[index]

        # A break that is given back inside its window was liquidity taken, not structure.
        if closed:
            for watch in list(watching):
                if _beyond(_other(watch["side"]), bar["close"], watch["price"]):
                    _advance(watch["event"], "invalidated", now)
                    other.append(_event(
                        "sweep", watch["side"], timeframe=timeframe,
                        anchor_time=watch["event"]["anchor_time"], confirmed_at=now,
                        level=watch["price"], basis="cross_bar_reclaim",
                        invalidation=f"a complete bar closes {_side_word(watch['side'])} "
                                     f"{watch['price']:g} again",
                        refs=[watch["event"]["event_id"]],
                        zone_ref=watch["event"].get("zone_ref")))
                    watching.remove(watch)
                else:
                    watch["bars_left"] -= 1
                    if watch["bars_left"] <= 0:
                        watching.remove(watch)
            for side in ("up", "down"):
                level = prior[side]
                if level and level["retested_at"] is None \
                        and bar["low"] <= level["price"] <= bar["high"]:
                    level["retested_at"] = now

        # --- what this bar does to levels that were knowable before it ---
        broke = None
        for side in ("up", "down"):
            live = armed[side]
            if live is None or broke:
                # Two opposite breaks on one bar would be a contradiction, not a
                # reading: the first one taken wins and the other waits for a bar.
                continue
            price = live["price"]
            if _beyond(side, bar["close"], price):
                kind = "choch" if trend == _other(side) else "bos"
                event = _event(kind, side, timeframe=timeframe, anchor_time=live["formed_at"],
                               confirmed_at=now, level=price,
                               status="confirmed" if closed else "provisional",
                               invalidation=f"a complete bar closes back "
                                            f"{_side_word(_other(side))} {price:g} within "
                                            f"{reclaim_window} bars",
                               refs=[live["event"]["event_id"]], trend_before=trend,
                               trend_after=side, broke_label=live["event"].get("label"),
                               zone_ref=_zone_for(zones, price, now))
                other.append(event)
                if not closed:
                    continue
                broke, trend, trend_since = side, side, now
                _advance(live["event"], "invalidated", now)
                for dependent in live["dependents"]:
                    _advance(dependent, "invalidated", now)
                prior[side] = {"price": price, "formed_at": live["formed_at"],
                               "broken_at": now, "retested_at": None,
                               "event_id": live["event"]["event_id"]}
                armed[side] = None
                if reclaim_window > 0:
                    watching.append({"event": event, "side": side, "price": price,
                                     "bars_left": reclaim_window})
            else:
                extreme = bar["high"] if side == "up" else bar["low"]
                through = _beyond(side, extreme, price)
                if not through and extreme != price:
                    continue  # price never reached the level: nothing happened to it
                if through:  # a wick through it, and a close back on the original side
                    event = _event("sweep", side, timeframe=timeframe,
                                   anchor_time=live["formed_at"], confirmed_at=now, level=price,
                                   status="confirmed" if closed else "provisional",
                                   basis="same_bar",
                                   invalidation=f"a complete bar closes {_side_word(side)} "
                                                f"{price:g}",
                                   refs=[live["event"]["event_id"]], reached=extreme,
                                   zone_ref=_zone_for(zones, price, now))
                    other.append(event)
                    if closed:
                        live["dependents"].append(event)
                if closed:
                    _advance(live["event"], "touched", now)

        # --- and only now, the pivots this bar confirms ---
        for pivot in arriving.get(now, ()) if closed else ():
            side = "up" if pivot["kind"] == "high" else "down"
            previous, price = latest[side], pivot["price"]
            event = _event("swing", side, timeframe=timeframe, anchor_time=pivot["at"],
                           confirmed_at=now, level=price, label=_label(side, previous, price),
                           invalidation=f"a complete bar closes {_side_word(side)} {price:g}",
                           refs=[previous["event"]["event_id"]] if previous else [],
                           zone_ref=_zone_for(zones, price, now))
            swings.append(event)
            record = {"price": price, "formed_at": pivot["at"], "confirmed_at": now,
                      "event": event, "dependents": []}
            tolerance = None if atr_now is None else atr_multiple * atr_now
            if previous and tolerance is not None and abs(price - previous["price"]) <= tolerance:
                equal = _event("equal_levels", side, timeframe=timeframe,
                               anchor_time=previous["formed_at"], confirmed_at=now,
                               level=(price + previous["price"]) / 2,
                               zone={"lower": min(price, previous["price"]),
                                     "upper": max(price, previous["price"])},
                               invalidation=f"a complete bar closes {_side_word(side)} "
                                            f"{max(price, previous['price']):g}",
                               refs=[previous["event"]["event_id"], event["event_id"]],
                               tolerance=tolerance,
                               zone_ref=_zone_for(zones, price, now))
                other.append(equal)
                record["dependents"].append(equal)
            latest[side] = record
            armed[side] = record

    last = bars[-1] if bars else None
    state = {"timeframe": timeframe, "definition": DEFINITION, "parameters": parameters,
             "trend": trend, "trend_since": trend_since,
             "swing_high": _view(armed["up"]), "swing_low": _view(armed["down"]),
             "prior_high": prior["up"], "prior_low": prior["down"],
             "atr": atr_values[-1] if atr_values else None,
             "last_bar": last["at"] if last else None,
             "last_bar_complete": bool(last and last["complete"]),
             "swings_count": len(swings), "events_count": len(other)}
    return {"swings": swings, "events": other, "state": state}


def recent(result, limit=EVENTS_KEPT):
    """The tail of the whole event history, oldest first — what is still decision
    relevant. The full history stays with the caller; this is what gets shown."""
    merged = sorted(result["swings"] + result["events"],
                    key=lambda event: (event["confirmed_at"], event["kind"], event["event_id"]))
    return merged[-limit:] if limit else merged
