"""Standard day / week / month charts a model can read, plus the numbers behind them.

The arrays are this run's transient input (``karst.bars``): they are charted and
measured, and then they are gone. What is kept is three PNGs and one small JSON of
derived numbers — the same numbers the picture was drawn from, so a researcher who
reads a level off a chart can quote the figure instead of the pixel. No price array
is written to either file, and no company identity is compiled in: what is charted
arrives as bars, where it lands arrives as a path.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no GUI, no display, no event loop — this runs on a server
import matplotlib.pyplot as plt  # noqa: E402  (backend must be chosen before pyplot)

from .calculations import confirmed_pivots, sma
from .fetch.common import write_json
from .schema import ContractError

VERSION = "0.1.0"
VIEWS = (("D", "daily"), ("W", "weekly"), ("M", "monthly"))
SMA_WINDOW = 200
PIVOT_WIDTH = {"D": 2, "W": 1, "M": 1}
NOTE = ("圖只作參考，數字以衍生 JSON（derived.json）為準。圖不保存價格陣列；"
        "本次陣列只存在於記憶體，發布只保存衍生數字與圖檔。")
# Drawn on the figure itself. ASCII on purpose: the bundled matplotlib fonts have no
# CJK glyphs, and a caption of empty boxes is worse than an English one.
CAPTION = "reference only - read the figures from derived.json, not off the chart"


def _period(bar, rule):
    day = dt.date.fromisoformat(bar["at"][:10])
    if rule == "W":
        return (day - dt.timedelta(days=day.weekday())).isoformat()
    return day.replace(day=1).isoformat()


def resample(bars, rule):
    """Daily bars -> weekly (Monday-anchored) or monthly bars; the last one may be open.

    A period is complete only when every bar in it is complete AND a later period
    has started: an unfinished week must not feed a moving average.
    """
    if rule == "D":
        return list(bars)
    grouped = {}
    for bar in bars:
        grouped.setdefault(_period(bar, rule), []).append(bar)
    keys = sorted(grouped)
    out = []
    for index, key in enumerate(keys):
        group = grouped[key]
        out.append({"at": key, "open": group[0]["open"], "close": group[-1]["close"],
                    "high": max(b["high"] for b in group), "low": min(b["low"] for b in group),
                    "volume": sum(b.get("volume") or 0.0 for b in group),
                    "complete": index < len(keys) - 1 and all(b["complete"] for b in group)})
    return out


def key_levels(bars, width):
    """The nearest confirmed turning points above and below the last close."""
    last = bars[-1]["close"] if bars else None
    pivots = confirmed_pivots(bars, width=width)
    above = [p for p in pivots if last is not None and p["price"] > last]
    below = [p for p in pivots if last is not None and p["price"] <= last]
    return {"last_close": last, "pivots": len(pivots),
            "resistance": min(above, key=lambda p: p["price"]) if above else None,
            "support": max(below, key=lambda p: p["price"]) if below else None,
            "recent": pivots[-4:]}


def _draw(view, bars, derived, path, caption):
    figure, (price, volume) = plt.subplots(
        2, 1, figsize=(10, 6), sharex=True, height_ratios=[3, 1], constrained_layout=True)
    labels = [bar["at"][:10] for bar in bars]
    closes = [bar["close"] for bar in bars]
    price.plot(range(len(bars)), closes, linewidth=1.2, color="#1f3a5f", label="close")
    line = derived["sma200"]
    if line is not None:
        price.axhline(line, linewidth=1.0, color="#b4642a", linestyle="--", label=f"SMA{SMA_WINDOW}")
    for name, colour in (("support", "#2e7d32"), ("resistance", "#b03030")):
        level = derived["levels"][name]
        if level:
            price.axhline(level["price"], linewidth=0.8, color=colour, alpha=0.7)
            price.annotate(f'{name} {level["price"]:g} ({level["at"][:10]})',
                           xy=(0, level["price"]), xytext=(4, 2), textcoords="offset points",
                           fontsize=8, color=colour)
    price.set_title(f'{view} · {len(bars)} bars · data as of {derived["data_as_of"]}', fontsize=10)
    price.legend(loc="upper left", fontsize=8)
    price.grid(alpha=0.25)
    volume.bar(range(len(bars)), [bar.get("volume") or 0.0 for bar in bars], color="#8899aa")
    volume.grid(alpha=0.25)
    volume.set_ylabel("volume", fontsize=8)
    ticks = range(0, len(bars), max(1, len(bars) // 8))
    volume.set_xticks(list(ticks))
    volume.set_xticklabels([labels[i] for i in ticks], fontsize=7, rotation=45, ha="right")
    figure.text(0.01, 0.005, caption, fontsize=7, color="#555555")
    figure.savefig(path, dpi=110)
    plt.close(figure)
    return path


def render(bars, out_dir, *, as_of=None, note=NOTE):
    """Write ``<out_dir>/{daily,weekly,monthly}.png`` + ``derived.json``; return both.

    ``bars`` is the transient daily array (``karst.bars.from_evidence``). The
    returned mapping is what the JSON holds: nothing but derived numbers.
    """
    bars = list(bars or [])
    if not bars:
        raise ContractError("No bars to chart; publish the page without a chart instead")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data_as_of = as_of or bars[-1]["at"]
    views, files = {}, {}
    for rule, name in VIEWS:
        series = resample(bars, rule)
        derived = {"bars_count": len(series),
                   "complete_bars": sum(1 for bar in series if bar["complete"]),
                   "first_bar": series[0]["at"][:10], "last_bar": series[-1]["at"][:10],
                   "sma200": sma(series, SMA_WINDOW) if rule == "D" else None,
                   "levels": key_levels(series, PIVOT_WIDTH[rule]),
                   "data_as_of": data_as_of}
        _draw(name, series, derived, out / f"{name}.png", CAPTION)
        files[rule] = out / f"{name}.png"
        views[rule] = derived
    # The JSON names the files beside it, never an absolute path on this machine:
    # it travels into a task directory, where the host's layout is nobody's business.
    payload = {"charts_version": VERSION, "data_as_of": data_as_of, "note": note,
               "sma_window": SMA_WINDOW, "views": views,
               "files": {rule: path.name for rule, path in files.items()}}
    write_json(out / "derived.json", payload)
    return {"derived": payload, "files": {rule: str(path) for rule, path in files.items()},
            "path": str(out)}
