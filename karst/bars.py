"""Transient price arrays for one publication: charted and measured, never saved.

A candlestick series that was landed as evidence can be read back into the bar shape
the renderer and the calculator use. Nothing here fetches, registers or stores
anything: the arrays live for the length of one ``publish`` call (0.3 keeps derived
numbers in research.json, not the series). No ticker or provider name is hard-coded —
any registered ``prices`` source whose rows carry OHLC and a timestamp is read.

Three rules decide which prices are read and which bars may be trusted (KARST-250):

* **Which snapshot.** The series is chosen by security identity, comparable basis and
  acquisition time — never by length. A longer *older* snapshot cannot outvote a newer
  one; it may only extend the history *before* the newer one starts.
* **Availability.** A snapshot fetched after the cutoff is not read back at all: today's
  prices truncated to last week are not what last week could see.
* **Completion.** A bar is confirmed only when its exchange session has closed *and* we
  held the data after that close. Unknown acquisition time, unknown zone or an unknown
  session close are never promoted to "confirmed".
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

from .packet import confined, instant, read_json
from .schema import ContractError
from .identity import entity_ids

OHLC = ("open", "high", "low", "close")
TIME_KEYS = ("timestamp", "at", "time", "datetime")
SYMBOL_KEYS = ("symbol", "symbols", "code", "code_list", "ticker")
# What makes two candlestick series comparable at all: same adjustment, same bar
# length, same trading sessions. Params that only widen coverage (start / end) are
# deliberately absent — a longer window is the same series, not a different one.
BASIS_KEYS = {"adjust": ("adjust_type", "adjust", "price_basis"),
              "period": ("period", "interval", "granularity"),
              "session": ("trade_session", "trade_sessions", "session")}
UNKNOWN = "unknown"
_EPOCH = dt.datetime.min.replace(tzinfo=dt.timezone.utc)


class Session:
    """An exchange's closing instant, so a bar can be asked whether it has closed yet.

    The default is US equities: 16:00 America/New_York, which is 20:00Z in summer and
    21:00Z in winter — the zone does that arithmetic, no offset is hard-coded.
    ``half_days`` maps an ISO date to that day's early close (the day after Thanksgiving,
    Christmas Eve...); ``holidays`` are dates the exchange does not trade, on which a bar
    has no closing instant and is therefore never confirmed. Both default to empty: this
    is a configurable calendar, not a table of dates baked into the code.

    A weekend is not special-cased. A provider that hands back a dated bar is taken at
    its word about the date; only what time that date closes is ours to decide.
    """

    def __init__(self, zone="America/New_York", close=dt.time(16, 0), *, half_days=None,
                 holidays=()):
        self.zone = ZoneInfo(zone) if isinstance(zone, str) else zone
        self.close = close
        self.half_days = {str(day): time for day, time in (half_days or {}).items()}
        self.holidays = frozenset(str(day) for day in holidays)

    # Exchange code -> (zone, regular close). Anything not listed falls back to US hours,
    # which the chart caption should make visible rather than hide.
    EXCHANGES = {"NYSE": ("America/New_York", dt.time(16, 0)),
                 "NASDAQ": ("America/New_York", dt.time(16, 0)),
                 "AMEX": ("America/New_York", dt.time(16, 0)),
                 "US": ("America/New_York", dt.time(16, 0)),
                 "HKEX": ("Asia/Hong_Kong", dt.time(16, 0)),
                 "SEHK": ("Asia/Hong_Kong", dt.time(16, 0)),
                 "HK": ("Asia/Hong_Kong", dt.time(16, 0))}

    @classmethod
    def for_exchange(cls, exchange, **kwargs):
        """The regular session of a listed exchange code (``NYSE``, ``HKEX``...); unknown
        or missing codes get the US default so behaviour is unchanged for old callers."""
        zone, close = cls.EXCHANGES.get(str(exchange or "").upper(), cls.EXCHANGES["US"])
        return cls(zone, close, **kwargs)

    def close_instant(self, day):
        """The moment that day's session ends, or None when this calendar has none."""
        if day in self.holidays:
            return None
        try:
            calendar_day = dt.date.fromisoformat(day)
        except (ValueError, TypeError):
            return None
        return dt.datetime.combine(calendar_day, self.half_days.get(day, self.close), self.zone)


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _moment(value):
    """An offset-aware instant, or None: a time without a zone names no moment."""
    if not isinstance(value, str):
        return None
    try:
        parsed = instant(value)
    except (ValueError, AttributeError):
        return None
    return parsed if parsed.tzinfo is not None else None


def _bar(row, cutoff, *, fetched_at=None, session=None):
    """One row -> one bar, or None when it is not a complete OHLC candle in range.

    ``fetched_at`` is when the snapshot this row came from was acquired, ``session`` the
    exchange calendar that says when the row's day closed. The bar is marked ``complete``
    only when that close is behind **both** of them: a snapshot taken mid-session does not
    become confirmed by being read the next day, and a bar cannot be closed at a cutoff
    that falls before its own close.
    """
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
    closes_at = (session or Session()).close_instant(when[:10])
    complete = (closes_at is not None and fetched_at is not None
                and closes_at <= min(fetched_at, cutoff))
    return {"at": when, **prices, "volume": _number(row.get("volume")) or 0.0,
            "complete": complete}


def _identity(record):
    """Which security this series is about: entity IDs plus the vendor symbol asked for."""
    params = record.get("params") or {}
    symbol = next((params[key] for key in SYMBOL_KEYS if params.get(key)), None)
    if isinstance(symbol, (list, tuple)):
        symbol = ",".join(str(item) for item in symbol)
    return entity_ids(record.get("entity_ids") or ()), str(symbol or UNKNOWN).upper()


def _basis(record):
    """Adjustment / bar length / trading sessions, as the record declares them."""
    params = record.get("params") or {}
    basis = {}
    for name, keys in BASIS_KEYS.items():
        value = next((params[key] for key in keys if params.get(key) not in (None, "")), None)
        if isinstance(value, (list, tuple)):
            value = ",".join(sorted(str(item) for item in value))
        basis[name] = UNKNOWN if value is None else str(value)
    return basis


def _display(basis):
    """The basis as a chart caption states it: unknown is said out loud, not omitted."""
    return " ".join(f"{name}={basis[name]}" for name in ("adjust", "period", "session"))


def _comparable(basis):
    """The basis reduced to what equality is judged on: case is a vendor's spelling."""
    return tuple(sorted((name, value.lower()) for name, value in basis.items()))


def _rank(candidate):
    """Newest first. Length only breaks a tie; an unknown acquisition time never wins."""
    return (candidate["fetched"] is not None, candidate["fetched"] or _EPOCH,
            len(candidate["bars"]), str(candidate["record"].get("evidence_id") or ""))


def _segment(candidate, bars):
    """One traceable stretch of the charted series: which version supplied which days."""
    record = candidate["record"]
    return {"evidence_id": record.get("evidence_id"), "source": record.get("source"),
            "fetched_at": record.get("fetched_at"),
            "sha256": (record.get("artifact") or {}).get("sha256"),
            "first_bar": bars[0]["at"][:10], "last_bar": bars[-1]["at"][:10],
            "bars": len(bars)}


def _read_bars(bundle, record, cutoff, session):
    """Every readable candle in one registered artifact, one per day, oldest first."""
    try:
        payload = read_json(confined(bundle, record["artifact"]["path"]))
    except (ContractError, ValueError, OSError, KeyError, TypeError):
        return []
    rows = payload.get("response") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    fetched = _moment(record.get("fetched_at"))
    bars = {}
    for row in rows:
        bar = _bar(row, cutoff, fetched_at=fetched, session=session)
        if bar is not None:
            bars[bar["at"][:10]] = bar
    return [bars[day] for day in sorted(bars)]


def _after_cutoff(record, cutoff, as_of):
    """Why this snapshot may not be read back at ``as_of``, or None when it may be."""
    fetched = _moment(record.get("fetched_at"))
    if fetched is None or fetched <= cutoff:
        return None
    return (f"{record.get('evidence_id')} was fetched at {record.get('fetched_at')}, "
            f"after the cutoff {as_of}: a snapshot that did not exist yet is not "
            "truncated into one that did")


def refused_prices(records, as_of):
    """Every registered prices snapshot the replay guard keeps out of ``as_of``'s series.

    :func:`series_from_evidence` reports these in its ``gaps`` — but only when it found a
    series at all. A caller that got nothing back needs the same list to say why.
    """
    cutoff = instant(as_of)
    reasons = []
    for record in records:
        if record.get("kind") != "prices" or record.get("status", "ok") != "ok":
            continue
        reason = _after_cutoff(record, cutoff, as_of)
        if reason:
            reasons.append(reason)
    return reasons


def series_from_evidence(bundle, records, as_of, *, session=None):
    """The candlestick series that was current at ``as_of`` **and the records it came from**.

    Returns ``{"bars": {"D": [...]}, "source": {...}}`` or None. The source is what a
    chart is stamped with: a picture nobody can trace back to registered versions of one
    series is a picture nobody can check. It carries ``segments`` — one entry per version
    that supplied days — and ``gaps``, which name every series that was refused and why.

    Candidates are grouped by security identity and comparable basis (adjustment, bar
    length, sessions). The newest snapshot in the winning group is the series; older
    snapshots of the same basis may only add days *before* it starts, and an incompatible
    basis is never merged — a mixed adjusted / unadjusted line is a fabricated one.
    """
    bundle, cutoff = Path(bundle), instant(as_of)
    session = session or Session()
    groups, gaps = {}, []
    for record in records:
        if record.get("kind") != "prices" or record.get("status", "ok") != "ok":
            continue
        refused = _after_cutoff(record, cutoff, as_of)
        if refused:
            gaps.append(refused)
            continue
        fetched = _moment(record.get("fetched_at"))
        bars = _read_bars(bundle, record, cutoff, session)
        if not bars:  # quotes and calc results register as prices too; neither is a series
            continue
        basis = _basis(record)
        groups.setdefault((_identity(record), _comparable(basis)),
                          []).append({"record": record, "bars": bars, "fetched": fetched,
                                      "basis": basis})
    if not groups:
        return None
    winner = max(groups, key=lambda key: _rank(max(groups[key], key=_rank)))
    for key, group in groups.items():
        if key != winner:
            newest = max(group, key=_rank)
            gaps.append(f"{newest['record'].get('evidence_id')} covers "
                        f"{key[0][1]} with different basis ({_display(newest['basis'])}) or identity {key[0][0]} and was "
                        "not merged into the charted series")
    group = groups[winner]
    chosen = max(group, key=_rank)
    taken = {bar["at"][:10]: bar for bar in chosen["bars"]}
    segments, earliest = [_segment(chosen, chosen["bars"])], min(taken)
    for older in sorted((c for c in group if c is not chosen), key=_rank, reverse=True):
        # Only earlier history: every day the chosen snapshot covers comes from the
        # chosen snapshot, whatever an older one says that day's close was.
        extension = [bar for bar in older["bars"] if bar["at"][:10] < earliest]
        if not extension:
            continue
        taken |= {bar["at"][:10]: bar for bar in extension}
        segments.append(_segment(older, extension))
        earliest = min(taken)
    record = chosen["record"]
    return {"bars": {"D": [taken[day] for day in sorted(taken)]},
            "source": {key: record.get(key) for key in
                       ("evidence_id", "source", "kind", "fetched_at", "source_url")}
            | {"sha256": (record.get("artifact") or {}).get("sha256"),
               "price_basis": _display(chosen["basis"]), "segments": segments, "gaps": gaps}}


def from_evidence(bundle, records, as_of, *, session=None):
    """Daily bars from the registered candlesticks current at ``as_of``, or None.

    ``records`` are evidence records (the bundle's evidence.json). Rows that are not
    complete OHLC candles, and rows after ``as_of``, are dropped rather than repaired.
    """
    found = series_from_evidence(bundle, records, as_of, session=session)
    return None if found is None else found["bars"]


def views(bars):
    """Accept a bare daily list or an already-keyed {'D': [...]} mapping; keep it uniform."""
    if bars is None:
        return None
    return {"D": list(bars)} if isinstance(bars, list) else dict(bars)
