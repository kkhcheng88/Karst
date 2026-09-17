"""Transient price arrays for one publication: charted and measured, never saved.

A candlestick series that was landed as evidence can be read back into the bar shape
the renderer and the calculator use. Nothing here fetches, registers or stores
anything: the arrays live for the length of one ``publish`` call (0.3 keeps derived
numbers in research.json, not the series). No ticker or provider name is hard-coded —
any registered ``prices`` source whose rows carry OHLC and a timestamp is read.
"""
from __future__ import annotations

from pathlib import Path

from .packet import confined, instant, read_json
from .schema import ContractError

OHLC = ("open", "high", "low", "close")
TIME_KEYS = ("timestamp", "at", "time", "datetime")


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bar(row, cutoff):
    """One row -> one bar, or None when it is not a complete OHLC candle in range."""
    if not isinstance(row, dict):
        return None
    when = next((row[key] for key in TIME_KEYS if isinstance(row.get(key), str)), None)
    prices = {key: _number(row.get(key)) for key in OHLC}
    if when is None or any(value is None or value <= 0 for value in prices.values()):
        return None
    try:
        at = instant(when)
    except ValueError:
        return None
    if at.tzinfo is None:  # a bar without a zone cannot be placed against the cutoff
        return None
    if at > cutoff:
        return None
    if not prices["low"] <= min(prices["open"], prices["close"]) \
            <= max(prices["open"], prices["close"]) <= prices["high"]:
        return None
    return {"at": when, **prices, "volume": _number(row.get("volume")) or 0.0,
            # A bar whose day is still the cutoff day may still be trading; only
            # closed bars feed the moving average.
            "complete": when[:10] < cutoff.isoformat()[:10]}


def series_from_evidence(bundle, records, as_of):
    """The longest registered candlestick series **and the record it came from**.

    Returns ``{"bars": {"D": [...]}, "source": {...}}`` or None. The source is what a
    chart is stamped with: a picture nobody can trace back to one registered version
    of one series is a picture nobody can check.
    """
    bundle, cutoff = Path(bundle), instant(as_of)
    best, origin = [], None
    for record in records:
        if record.get("kind") != "prices" or record.get("status", "ok") != "ok":
            continue
        try:
            payload = read_json(confined(bundle, record["artifact"]["path"]))
        except (ContractError, ValueError, OSError):
            continue
        rows = payload.get("response") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            continue
        bars = [bar for bar in (_bar(row, cutoff) for row in rows) if bar is not None]
        if len(bars) > len(best):
            best, origin = bars, record
    if not best:
        return None
    unique = {bar["at"]: bar for bar in best}
    return {"bars": {"D": [unique[at] for at in sorted(unique)]},
            "source": {key: origin.get(key) for key in
                       ("evidence_id", "source", "kind", "fetched_at", "source_url")}
            | {"sha256": (origin.get("artifact") or {}).get("sha256")}}


def from_evidence(bundle, records, as_of):
    """Daily bars from the longest registered candlestick series, or None if there is none.

    ``records`` are evidence records (the bundle's evidence.json). Rows that are not
    complete OHLC candles, and rows after ``as_of``, are dropped rather than repaired.
    """
    found = series_from_evidence(bundle, records, as_of)
    return None if found is None else found["bars"]


def views(bars):
    """Accept a bare daily list or an already-keyed {'D': [...]} mapping; keep it uniform."""
    if bars is None:
        return None
    return {"D": list(bars)} if isinstance(bars, list) else dict(bars)
