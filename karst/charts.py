"""Standard month / week / day / recent charts a model can actually read.

Four pictures out of one daily array: the monthly and weekly background, the whole
daily history, and the last few months zoomed in far enough that a candle body and
its wick are distinguishable. Every chart is OHLC candles with volume under them and
the moving averages drawn as *curves* — computed over the full history first and
only then cut to the window, so a 60-bar zoom still shows the 200-day line's real
slope, and a weekly chart that maps the daily average says "200-day SMA" in its
legend rather than silently becoming a 200-week one.

What survives the run is the PNGs and one small JSON of derived numbers — the same
numbers the picture was drawn from, so a researcher who reads a level off a chart
quotes the figure instead of the pixel. Both are named after their own content, so
tomorrow's render lands beside today's rather than over it: a chart that was read
once has to stay readable. No price array is written to either file,
and no company identity is compiled in: what is charted arrives as bars, whose
identity arrives as a title, and where it lands arrives as a path.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no GUI, no display, no event loop — this runs on a server
import matplotlib.pyplot as plt  # noqa: E402  (backend must be chosen before pyplot)
from matplotlib.ticker import ScalarFormatter  # noqa: E402

from .calculations import confirmed_pivots  # noqa: E402
from .fetch.common import write_json  # noqa: E402
from .schema import ContractError, canonical, digest  # noqa: E402
from .structure import (ATR_MULTIPLE, ATR_PERIOD, EVENTS_KEPT, RECLAIM_WINDOW,  # noqa: E402
                        atr_series)
from .structure import events as structure_events  # noqa: E402
from .structure import recent as structure_recent  # noqa: E402

VERSION = "0.2.0"
SMA_WINDOWS = (200, 50)
EMA_SPAN = 20
VOLUME_BASE = 20      # bars the last volume is compared against
DIRECTION_BARS = 20   # trading days the 200-day average's direction is read over
RECENT_BARS = 90      # the zoom: enough context to place a setup, few enough to see wicks
LOG_SCALE_RATIO = 4.0  # high/low ratio inside a window beyond which a log axis reads better
FLAT_BAND = 0.001     # |change| under 0.1% over DIRECTION_BARS is called flat, not a trend
ZONE_ATR_SHARE = 0.25  # a support/resistance band is a quarter-ATR wide before it is a line
ZONE_FLOOR = 0.004    # ...and never narrower than 0.4% of the last close
ZONES_KEPT = 8        # zones nearest the last close that reach derived.json

# view key -> (resample rule, file stem, bars drawn (None = all), what the view is for,
#              pivot half-width, overlays drawn on it)
VIEWS = (
    ("M", "M", "monthly", None, "long-term position", 1, ("sma200",)),
    ("W", "W", "weekly", None, "primary trend and structure", 1, ("sma200",)),
    ("D", "D", "daily", None, "the whole daily history", 2, ("sma200", "sma50")),
    ("DR", "D", "daily_recent", RECENT_BARS, f"the last {RECENT_BARS} daily bars, close enough "
     "to read candle bodies and wicks", 2, ("sma200", "sma50", "ema20")),
)
OVERLAYS = {"sma200": ("200-day SMA", "#b4642a", 1.6),
            "sma50": ("50-day SMA", "#4c6fbf", 1.2),
            "ema20": ("20-day EMA", "#7a4fa3", 1.0)}
STRUCTURE_RULES = ("D", "W")  # where structure is read: the two timeframes a plan is made on
STRUCTURE_COLOUR = "#0f8b8d"  # deliberately not the zone colours: this is not a band
STRUCTURE_LABEL = "structure: BOS/CHoCH, swing + prior high/low, sweep"
STRUCTURE_SWEEPS_DRAWN = 3
UP, DOWN = "#1a7f5a", "#b03030"
NOTE = ("圖只作參考，數字以衍生 JSON（derived.json）為準。圖不保存價格陣列；"
        "本次陣列只存在於記憶體，發布只保存衍生數字與圖檔。")
# Drawn on the figure itself. ASCII on purpose: the bundled matplotlib fonts have no
# CJK glyphs, and a caption of empty boxes is worse than an English one.
CAPTION = "reference only - read the figures from derived.json, not off the chart"


def _ascii(value):
    """Figure text the bundled fonts can actually draw; anything else becomes '?'."""
    return "".join(character if character.isascii() and character.isprintable() else "?"
                   for character in str(value))


def _period(bar, rule):
    day = dt.date.fromisoformat(bar["at"][:10])
    if rule == "W":
        return (day - dt.timedelta(days=day.weekday())).isoformat()
    return day.replace(day=1).isoformat()


def resample(bars, rule):
    """Daily bars -> weekly (Monday-anchored) or monthly bars; the last one may be open.

    Every bar carries ``end``: the timestamp of the last daily bar inside it, which is
    where a daily moving average is read when it is mapped onto this period.

    A period is complete only when every bar in it is complete AND a later period
    has started: an unfinished week must not feed a moving average.
    """
    if rule == "D":
        return [{**bar, "end": bar["at"]} for bar in bars]
    grouped = {}
    for bar in bars:
        grouped.setdefault(_period(bar, rule), []).append(bar)
    keys = sorted(grouped)
    out = []
    for index, key in enumerate(keys):
        group = grouped[key]
        out.append({"at": key, "end": group[-1]["at"],
                    "open": group[0]["open"], "close": group[-1]["close"],
                    "high": max(b["high"] for b in group), "low": min(b["low"] for b in group),
                    "volume": sum(b.get("volume") or 0.0 for b in group),
                    "complete": index < len(keys) - 1 and all(b["complete"] for b in group)})
    return out


# --- series ----------------------------------------------------------------

def sma_series(bars, window):
    """Simple moving average of the *complete* closes, one value per bar.

    None until the window has filled. An unfinished bar does not move the line: it
    carries the last confirmed value, which is what an average of closed bars is.
    """
    values, closes = [], []
    for bar in bars:
        if bar["complete"]:
            closes.append(bar["close"])
        values.append(sum(closes[-window:]) / window if len(closes) >= window else None)
    return values


def ema_series(bars, span):
    """Exponential moving average, smoothing 2/(span+1), over complete closes only."""
    weight = 2.0 / (span + 1)
    values, current, seen = [], None, 0
    for bar in bars:
        if bar["complete"]:
            seen += 1
            current = bar["close"] if current is None else bar["close"] * weight + current * (1 - weight)
        values.append(current if seen >= span else None)
    return values


def atr(bars, period=ATR_PERIOD):
    """Wilder's ATR over complete bars, as it stands after the last one.

    The running series lives in :mod:`karst.structure`, which needs the value *at*
    each bar rather than only at the end; one definition, read at two points.
    """
    values = atr_series(bars, period)
    return values[-1] if values else None


def map_daily(daily, series, bars):
    """A daily series read at each period's last trading day (its ``end``).

    This is how a 200-**day** average lands on a weekly or monthly chart without
    turning into a 200-week one; nothing is recomputed on the coarser bars.
    """
    by_day = {bar["at"][:10]: value for bar, value in zip(daily, series)}
    out, last = [], None
    for bar in bars:
        last = by_day.get(bar["end"][:10], last)
        out.append(last)
    return out


def direction(series, bars=DIRECTION_BARS):
    """Where a moving average has been going over the last ``bars`` bars of it."""
    known = [value for value in series if value is not None]
    if len(known) <= bars:
        return None
    now, before = known[-1], known[-1 - bars]
    change = now - before
    share = change / before if before else None
    label = "flat" if share is not None and abs(share) < FLAT_BAND else \
        ("rising" if change > 0 else "falling")
    return {"bars": bars, "value_now": now, "value_before": before, "change": change,
            "change_pct": share, "label": label}


# --- levels ----------------------------------------------------------------

def pivot_zones(bars, width, tolerance):
    """Confirmed pivots clustered into price bands, each keeping the bars that made it.

    A level is a zone, not a line: neighbouring pivots within ``tolerance`` join one
    band. Every anchor keeps the day the pivot **formed** and the later day it was
    **confirmed** apart, because only the second one was knowable at the time.
    """
    zones = []
    for pivot in sorted(confirmed_pivots(bars, width=width), key=lambda p: p["price"]):
        anchor = {"price": pivot["price"], "formed_at": pivot["at"],
                  "confirmed_at": pivot["confirmed_at"]}
        # Joined against the band's own floor, not its running top: chaining pivot to
        # pivot would let one "zone" creep across half the chart.
        zone = next((z for z in zones if z["pivots"] == pivot["kind"]
                     and pivot["price"] <= z["lower"] + 2 * tolerance), None)
        if zone is None:
            zones.append({"pivots": pivot["kind"], "lower": pivot["price"],
                          "upper": pivot["price"], "anchors": [anchor]})
        else:
            zone["upper"] = max(zone["upper"], pivot["price"])
            zone["anchors"].append(anchor)
    for zone in zones:
        zone["touches"] = len(zone["anchors"])
        zone["anchors"] = sorted(zone["anchors"], key=lambda a: a["formed_at"])[-6:]
        zone["last_confirmed_at"] = max(anchor["confirmed_at"] for anchor in zone["anchors"])
    return zones


def key_levels(bars, width, tolerance):
    """The zones around the last close: what is above, what is below, what contains it.

    Which side of price a zone sits on decides whether it acts as resistance or
    support today; what made it (``pivots``: highs or lows) is kept separately,
    because a band of old highs under the price is exactly the interesting case.
    """
    last = bars[-1]["close"] if bars else None
    zones = pivot_zones(bars, width, tolerance)
    above = [z for z in zones if last is not None and z["lower"] > last]
    below = [z for z in zones if last is not None and z["upper"] < last]
    inside = [z for z in zones if last is not None and z["lower"] <= last <= z["upper"]]
    nearest = sorted(zones, key=lambda z: min(abs(z["lower"] - last), abs(z["upper"] - last))
                     if last is not None else 0)[:ZONES_KEPT]
    return {"last_close": last, "tolerance": tolerance,
            "tolerance_method": (f"max({ZONE_ATR_SHARE} x ATR{ATR_PERIOD}, "
                                 f"{ZONE_FLOOR} x last close)"),
            "zones_found": len(zones), "zones": nearest,
            "resistance": min(above, key=lambda z: z["lower"]) if above else None,
            "support": max(below, key=lambda z: z["upper"]) if below else None,
            "containing": inside or None}


def structure(bars, rule="D", *, width=None, **kwargs):
    """Structure events for one resampled view: ``structure(daily, "W")`` reads the
    weekly sequence off the same daily array the charts are drawn from, using that
    view's pivot window. Everything else is :func:`karst.structure.events`."""
    return structure_events(resample(bars, rule), timeframe=rule,
                            width=width or {entry[1]: entry[5] for entry in VIEWS}[rule],
                            **kwargs)


# --- drawing ---------------------------------------------------------------

def _nan(series):
    return [float("nan") if value is None else float(value) for value in series]


def _plain(values):
    return [None if value != value else float(value) for value in values]  # noqa: PLR0124


def _candles(axis, bars):
    for index, bar in enumerate(bars):
        colour = UP if bar["close"] >= bar["open"] else DOWN
        axis.vlines(index, bar["low"], bar["high"], color=colour, linewidth=0.9)
        bottom = min(bar["open"], bar["close"])
        # A doji has no body; give it a hairline so the bar is still visible.
        height = abs(bar["close"] - bar["open"]) or max((bar["high"] - bar["low"]) * 0.02, 1e-9)
        axis.bar(index, height, bottom=bottom, width=0.6, color=colour, edgecolor=colour,
                 linewidth=0.4, hatch=None if bar["complete"] else "///",
                 alpha=1.0 if bar["complete"] else 0.55, zorder=3)
        if not bar["complete"]:
            axis.axvline(index, color="#777777", linewidth=0.8, linestyle=":", zorder=1)
            axis.annotate("unconfirmed bar", xy=(index, bar["high"]), xytext=(-6, 6),
                          textcoords="offset points", fontsize=7, color="#555555", ha="right")


def _zones(axis, zones, positions, last_close, span, right):
    """Zones that reach the drawn price range. One outside it would only stretch the
    axis until the candles are a flat ribbon — the full list is in derived.json."""
    low, high = span
    visible = [zone for zone in zones if low <= zone["upper"] and zone["lower"] <= high]
    for order, zone in enumerate(visible):
        role = ("resistance" if last_close is None or zone["lower"] > last_close else
                "support" if zone["upper"] < last_close else "at price")
        colour = DOWN if role == "resistance" else UP if role == "support" else "#555555"
        axis.axhspan(zone["lower"], zone["upper"], color=colour, alpha=0.12, zorder=0)
        side = order % 2  # alternate sides so neighbouring bands do not write over each other
        axis.annotate(
            f'{role} {zone["lower"]:g}-{zone["upper"]:g} '
            f'({zone["touches"]} {zone["pivots"]}s, confirmed {zone["last_confirmed_at"][:10]})',
            xy=(right if side else 0, zone["upper"]),
            xytext=(-4 if side else 4, 3 + (order // 2) * 10),  # and stagger upwards
            textcoords="offset points", fontsize=7, color=colour,
            ha="right" if side else "left")
        for anchor in zone["anchors"]:
            formed = positions.get(anchor["formed_at"][:10])
            confirmed = positions.get(anchor["confirmed_at"][:10])
            if formed is not None:
                axis.plot([formed], [anchor["price"]], marker="o", markersize=3.5,
                          color=colour, zorder=4)
            if confirmed is not None:
                axis.plot([confirmed], [anchor["price"]], marker="|", markersize=7,
                          color=colour, zorder=4)
    if last_close is not None:
        axis.axhline(last_close, color="#333333", linewidth=0.6, linestyle="--", alpha=0.6)


def _structure(axis, result, positions, right):
    """Only the structure a decision turns on now: the latest break, the levels in
    play, and the last few sweeps. The whole event history is in derived.json — drawn
    on the picture it would be a wall of lines nobody reads."""
    drawn, state = [], result["state"]
    for event in [e for e in result["events"] if e["kind"] in ("bos", "choch")][-1:]:
        start = positions.get(event["anchor_time"][:10], 0)
        end = positions.get(event["confirmed_at"][:10], right)
        axis.plot([start, end], [event["level"]] * 2, color=STRUCTURE_COLOUR, linewidth=1.5,
                  solid_capstyle="butt", zorder=5)
        axis.annotate(f'{event["kind"].upper()} {event["direction"]} {event["level"]:g} '
                      f'({event["confirmed_at"][:10]}, {event["status"]})',
                      # under the line: the zone captions sit above theirs
                      xy=(end, event["level"]), xytext=(4, -12), textcoords="offset points",
                      fontsize=7, color=STRUCTURE_COLOUR)
        drawn.append(event["event_id"])
    for name, level in (("swing high", state["swing_high"]), ("swing low", state["swing_low"]),
                        ("prior high", state["prior_high"]), ("prior low", state["prior_low"])):
        if not level:
            continue
        axis.axhline(level["price"], color=STRUCTURE_COLOUR, linewidth=0.9, linestyle="-.",
                     alpha=0.85, zorder=4)
        # On the right: the legend and the zone captions live on the left of the frame.
        axis.annotate(f'{name} {level["price"]:g}', xy=(right, level["price"]),
                      xytext=(-4, -10 - len(drawn) * 2), textcoords="offset points",
                      fontsize=7, color=STRUCTURE_COLOUR, ha="right")
        drawn.append(name)
    for event in [e for e in result["events"]
                  if e["kind"] == "sweep"][-STRUCTURE_SWEEPS_DRAWN:]:
        at = positions.get(event["confirmed_at"][:10])
        if at is not None:
            axis.plot([at], [event["level"]], color=STRUCTURE_COLOUR, zorder=6, markersize=6,
                      marker="v" if event["direction"] == "up" else "^")
            drawn.append(event["event_id"])
    if drawn:  # one proxy artist, so the legend says this is structure, not a price band
        axis.plot([], [], color=STRUCTURE_COLOUR, linewidth=1.5, label=STRUCTURE_LABEL)
    return drawn


def _draw(path, *, bars, overlays, zones, last_close, title, subtitle, caption, scale,
          structure=None):
    """Draw one view and return the series that were actually plotted.

    The returned overlays are read back off the axes, not off the caller's arrays: a
    test that compares them to an independently computed average is checking the
    picture, not the intention.
    """
    figure, (price, volume) = plt.subplots(
        2, 1, figsize=(11, 6.5), sharex=True, height_ratios=[3, 1], constrained_layout=True)
    _candles(price, bars)
    lines = {}
    for name, series in overlays.items():
        label, colour, width = OVERLAYS[name]
        drawn, = price.plot(range(len(bars)), _nan(series), linewidth=width, color=colour,
                            label=label, zorder=2)
        lines[name] = _plain(drawn.get_ydata())
    # The drawn price range: the candles and the averages over them, nothing else.
    seen = [bar["low"] for bar in bars] + [bar["high"] for bar in bars] \
        + [value for series in lines.values() for value in series if value is not None]
    low, high = min(seen), max(seen)
    margin = (high - low) * 0.06 or max(high * 0.01, 1e-9)
    span = (low - margin, high + margin)
    positions = {bar["at"][:10]: index for index, bar in enumerate(bars)}
    _zones(price, zones, positions, last_close, span, len(bars) - 1)
    marked = _structure(price, structure, positions, len(bars) - 1) if structure else []
    price.set_title(_ascii(title) + "\n" + _ascii(subtitle), fontsize=9)
    price.set_ylabel("price")
    if scale == "log":
        price.set_yscale("log")
        price.yaxis.set_major_formatter(ScalarFormatter())
        price.yaxis.set_minor_formatter(ScalarFormatter())
        span = (max(span[0], low * 0.9), span[1])  # a log axis has no room below zero
    price.set_ylim(*span)
    price.legend(loc="upper left", fontsize=8)
    legend = list(price.get_legend_handles_labels()[1])
    price.grid(alpha=0.25)
    volumes = [bar.get("volume") or 0.0 for bar in bars]
    volume.bar(range(len(bars)), volumes, width=0.6,
               color=[UP if bar["close"] >= bar["open"] else DOWN for bar in bars], alpha=0.55)
    average = sma_series([{"close": value, "complete": True} for value in volumes], VOLUME_BASE)
    volume.plot(range(len(bars)), _nan(average), linewidth=1.0, color="#555555",
                label=f"{VOLUME_BASE}-bar average volume")
    volume.legend(loc="upper left", fontsize=7)
    volume.set_ylabel("volume", fontsize=8)
    volume.grid(alpha=0.25)
    labels = [bar["at"][:10] for bar in bars]
    ticks = range(0, len(bars), max(1, len(bars) // 9))
    volume.set_xticks(list(ticks))
    volume.set_xticklabels([labels[i] for i in ticks], fontsize=7, rotation=45, ha="right")
    figure.text(0.01, 0.002, _ascii(caption), fontsize=7, color="#555555")
    figure.savefig(path, dpi=120)
    plt.close(figure)
    return {"overlays": lines, "volume_average": average, "structure_drawn": marked,
            "legend": legend}


# --- assembly --------------------------------------------------------------

def _scale(bars, scale):
    if scale in ("log", "linear"):
        return scale
    low = min(bar["low"] for bar in bars)
    high = max(bar["high"] for bar in bars)
    return "log" if low > 0 and high / low > LOG_SCALE_RATIO else "linear"


def _volume(bars):
    volumes = [bar.get("volume") or 0.0 for bar in bars]
    base = volumes[-1 - VOLUME_BASE:-1]
    average = sum(base) / len(base) if base else None
    return {"last": volumes[-1], "bars_compared": len(base), "average": average,
            "ratio": volumes[-1] / average if average else None,
            "method": f"last bar volume / mean of the previous {len(base)} bars "
                      f"(target {VOLUME_BASE})"}


def _averages(daily, series):
    """The daily moving averages as numbers: value, distance, and where they are going."""
    close = daily[-1]["close"]
    out = {}
    for name, values in series.items():
        value = next((v for v in reversed(values) if v is not None), None)
        out[name] = {
            "basis": OVERLAYS[name][0] + " on complete daily closes",
            "value": value,
            # The average's own last point is the last CLOSED bar: an open bar
            # carries the previous value forward, it does not date it.
            "at": next((bar["at"] for bar, v in zip(reversed(daily), reversed(values))
                        if v is not None and bar["complete"]), None),
            "distance_from_close": None if value is None else close - value,
            "distance_pct": None if not value else close / value - 1,
            "direction": direction(values),
        }
    return out


def _view(rule, bars, window, overlays, width, purpose, label):
    """Everything measured for one view: the same numbers its picture is drawn from."""
    period_atr = atr(bars)
    last = bars[-1]["close"]
    tolerance = max(ZONE_ATR_SHARE * (period_atr or 0.0), ZONE_FLOOR * last)
    levels = key_levels(bars, width, tolerance)
    drawn = window if window else bars
    return {
        "rule": rule, "label": label, "purpose": purpose,
        "bars_count": len(bars), "complete_bars": sum(1 for bar in bars if bar["complete"]),
        "first_bar": bars[0]["at"][:10], "last_bar": bars[-1]["at"][:10],
        "last_bar_complete": bars[-1]["complete"], "last_close": last,
        "drawn_bars": len(drawn), "drawn_from": drawn[0]["at"][:10],
        "pivot_width": width,
        "atr": None if period_atr is None else {
            "value": period_atr, "period": ATR_PERIOD, "bars": rule,
            "method": "Wilder: mean of the first 14 true ranges, then ((13*prev)+tr)/14"},
        "volume": _volume(bars),
        "overlays": list(overlays),
        "levels": levels,
    }


def render(bars, out_dir, *, as_of=None, note=NOTE, source=None, title=None, scale="auto",
           events_kept=EVENTS_KEPT):
    """Write four PNGs + ``derived.json`` into ``out_dir``; return both, plus artifacts.

    ``bars`` is the transient daily array (``karst.bars.from_evidence``). ``source``
    is the evidence record the array came from — it is stamped on every artifact, so
    a chart can be traced back to the exact registered series and version that drew
    it. ``title`` is the subject line drawn on the figure (identity is a parameter,
    never a constant here).

    The returned ``plotted`` series are what matplotlib actually holds; like the
    bars they stay in memory. Nothing but derived numbers reaches the JSON.
    """
    bars = list(bars or [])
    if not bars:
        raise ContractError("No bars to chart; publish the page without a chart instead")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data_as_of = as_of or bars[-1]["at"]
    daily = resample(bars, "D")
    daily_series = {f"sma{window}": sma_series(daily, window) for window in SMA_WINDOWS}
    daily_series["ema20"] = ema_series(daily, EMA_SPAN)
    parameters = {"sma_windows": list(SMA_WINDOWS), "ema_span": EMA_SPAN,
                  "atr_period": ATR_PERIOD, "volume_base": VOLUME_BASE,
                  "direction_bars": DIRECTION_BARS, "recent_bars": RECENT_BARS,
                  "scale": scale, "log_scale_ratio": LOG_SCALE_RATIO,
                  "zone_tolerance": {"atr_share": ZONE_ATR_SHARE, "floor_pct": ZONE_FLOOR},
                  "moving_average_basis": "daily complete closes, mapped onto weekly / "
                                          "monthly bars at each period's last trading day",
                  "structure": {"rules": list(STRUCTURE_RULES), "atr_multiple": ATR_MULTIPLE,
                                "reclaim_window": RECLAIM_WINDOW, "events_kept": events_kept}}
    params_digest = digest(canonical(parameters))
    views, files, artifacts, plotted = {}, {}, [], {}
    for key, rule, name, limit, purpose, width, overlays in VIEWS:
        series = daily if rule == "D" else resample(bars, rule)
        mapped = {name_: (daily_series[name_] if rule == "D"
                          else map_daily(daily, daily_series[name_], series))
                  for name_ in overlays}
        window = series[-limit:] if limit else series
        cut = {name_: values[-limit:] if limit else values for name_, values in mapped.items()}
        measured = _view(rule, series, window, overlays, width, purpose, name)
        measured["scale"] = _scale(window, scale)
        # Structure is read where a plan is made — the daily and weekly bars. The
        # monthly view stays background: a break on it is a decision nobody takes
        # inside this horizon.
        found = (structure_events(series, width=width, timeframe=rule,
                                  zones=measured["levels"]["zones"])
                 if rule in STRUCTURE_RULES else None)
        if found is not None:
            measured["structure"] = {"state": found["state"],
                                     "events": structure_recent(found, events_kept)}
        path = out / f"{name}.png"
        subtitle = (f"{measured['drawn_bars']} {rule} bars from {measured['drawn_from']} to "
                    f"{measured['last_bar']} | {measured['scale']} price scale | "
                    f"{'last bar unconfirmed' if not measured['last_bar_complete'] else 'all bars closed'}")
        # The basis is stated even when it is not known: a chart that quietly omits
        # whether its prices are adjusted invites the reader to assume one.
        caption = (f"{CAPTION} | data as of {data_as_of}"
                   + (f" | source {source['evidence_id']}" if source else "")
                   + f" | price basis {(source or {}).get('price_basis') or 'unstated - check the source record'}")
        drawn = _draw(path, bars=window, overlays=cut, zones=measured["levels"]["zones"][:4],
                      last_close=measured["last_close"],
                      title=f"{title or 'price'} | {name} | {purpose}",
                      subtitle=subtitle, caption=caption, scale=measured["scale"],
                      structure=found)
        data = path.read_bytes()
        # The file is named after its own content, so tomorrow's render of the same
        # view lands beside this one instead of over it: an artifact promised to be
        # readable later cannot share a path with the next version of itself.
        path = path.replace(out / f"{name}-{digest(data)[:12]}.png")
        measured["overlay_endpoints"] = {
            name_: {"first_drawn": values[0], "last_drawn": values[-1]}
            for name_, values in drawn["overlays"].items()}
        artifact = {"artifact_id": "cha-" + digest(data), "view": key, "label": name,
                    "file": path.name, "path": str(path), "media_type": "image/png",
                    "sha256": digest(data), "bytes": len(data),
                    "bars_as_of": data_as_of, "period": rule,
                    "drawn_from": measured["drawn_from"], "drawn_to": measured["last_bar"],
                    "source_evidence_id": (source or {}).get("evidence_id"),
                    "source_sha256": (source or {}).get("sha256"),
                    "charts_version": VERSION, "params_digest": params_digest}
        measured["artifact_id"] = artifact["artifact_id"]
        measured["file"] = path.name
        views[key], files[key], plotted[key] = measured, path, drawn
        artifacts.append(artifact)
    # The JSON names the files beside it, never an absolute path on this machine:
    # it travels into a task directory, where the host's layout is nobody's business.
    payload = {"charts_version": VERSION, "data_as_of": data_as_of, "note": note,
               "parameters": parameters, "params_digest": params_digest,
               "source": source,
               "daily": {"bars_count": len(daily), "last_close": daily[-1]["close"],
                         "last_bar": daily[-1]["at"], "last_bar_complete": daily[-1]["complete"],
                         "moving_averages": _averages(daily, daily_series),
                         "atr": atr(daily), "volume": _volume(daily)},
               "views": views,
               "files": {key: path.name for key, path in files.items()},
               "artifacts": [{k: v for k, v in artifact.items() if k != "path"}
                             for artifact in artifacts]}
    # derived.json is the latest render; the hashed copy beside it is this render,
    # kept for the same reason its PNGs are: the numbers behind a chart someone read.
    write_json(out / "derived.json", payload)
    write_json(out / f"derived-{digest(canonical(payload))[:12]}.json", payload)
    return {"derived": payload, "artifacts": artifacts, "plotted": plotted,
            "files": {key: str(path) for key, path in files.items()}, "path": str(out)}
