"""Longbridge public market data through the ``longport`` SDK QuoteContext.

Lands ``<out>/longbridge/<tool>.json`` + ``.meta.json`` in the same envelope shape as
``broker.land`` ({tool, symbol, fetched_at, params, response}), so the registry treats a
re-fetch with unchanged content as the same source version.

Quote data only. Account, position and order methods are never called, and the same
private-key guard as the manual landing path runs on every params/response pair.
Credentials are LONGPORT_APP_KEY / LONGPORT_APP_SECRET / LONGPORT_ACCESS_TOKEN, read from
the repo-root ``.env`` (gitignored, never committed) unless already set in the environment.
When any is missing every output is a metadata-only ``status: error`` with
``status_reason: credentials missing`` — never an invented body.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

from .broker import refuse_private
from .common import clean_value, load_env_file, utc_now, write_json, write_meta
from .port import LandedRecord, options_for, response_status, scan

SOURCE = "longbridge"
# The kinds this adapter covers for refresh_sources. ``static_info`` also lands a
# profile, but the profile kind is served by defeatbeta; routing stays single-valued.
KINDS = ("prices", "quote")
# tool -> evidence kind, declared here rather than inferred at registration.
TOOL_KINDS = {"quote": "prices", "static_info": "profile", "calc_indexes": "prices",
              "history_candlesticks_by_date": "prices"}
ENV_KEYS = ("LONGPORT_APP_KEY", "LONGPORT_APP_SECRET", "LONGPORT_ACCESS_TOKEN")
MISSING_CREDENTIALS = "credentials missing"
SNAPSHOT_BASIS = ("現時快照 (snapshot at fetch time); the SDK return carries no publication "
                  "time for this version")
DEFAULT_INDEXES = ("LastDone", "Volume", "Turnover", "TotalMarketValue", "TurnoverRate")
US_EXCHANGES = {"NASDAQ", "NYSE", "NYSEARCA", "NYSEAMERICAN", "AMEX", "BATS", "CBOE",
                "XNAS", "XNYS", "XASE", "ARCX", "BATS", "US"}
HK_EXCHANGES = {"HKEX", "SEHK", "XHKG", "HK"}


def symbol_for(security):
    """The vendor symbol for a security record.

    An explicit ``symbols.longbridge`` mapping wins. Otherwise the symbol is derived from
    the exchange: US venues -> ``<ticker>.US``, Hong Kong -> ``<code>.HK``. A ticker that
    already carries a market suffix is passed through. Anything else is refused rather
    than guessed: a wrong symbol comes back from the vendor as "invalid symbol" with no
    hint about which record produced it.
    """
    explicit = (security.get("symbols") or {}).get("longbridge")
    if explicit:
        return str(explicit)
    ticker = str(security.get("ticker") or "").strip().upper()
    if not ticker:
        raise ValueError("security has no ticker; cannot derive a Longbridge symbol")
    if "." in ticker:
        return ticker
    exchange = str(security.get("exchange") or "").strip().upper()
    if exchange in US_EXCHANGES or exchange.startswith(("NYSE", "NASDAQ")):
        return f"{ticker}.US"
    if exchange in HK_EXCHANGES:
        return f"{ticker.zfill(5) if ticker.isdigit() else ticker}.HK"
    raise ValueError(f"cannot derive a Longbridge symbol for exchange {exchange!r}; "
                     "set security.symbols.longbridge explicitly")


def credentials(environ=None, env_file=None):
    """Present credentials, or None when any of the three is absent/blank.

    The repo-root ``.env`` is consulted first (an already-set variable wins), so the
    secrets stay in one gitignored file instead of the machine's environment.
    """
    if environ is None:
        load_env_file(env_file)
        environ = os.environ
    values = {key: (environ.get(key) or "").strip() for key in ENV_KEYS}
    return values if all(values.values()) else None


def _plain(value, depth=0):
    """SDK object -> JSON-safe dict/scalar. Unknown objects fall back to their text form.

    Enum members expose every sibling member as a class attribute, so a naive
    ``dir()`` walk recurses forever; enums become their name and nesting is capped.
    """
    if isinstance(value, dt.datetime) and value.tzinfo is None:
        # The SDK hands back naive datetimes in the *host's* local time (12:00 on a
        # HK machine, 04:00 on a UTC server for the same US day bar). Attach that zone
        # so the landed ISO string names one instant wherever it was fetched; a bar
        # without a zone cannot be placed against a cutoff and is refused downstream.
        value = value.astimezone()
    # Containers are walked here, not by clean_value, so nested datetimes get the same treatment.
    if isinstance(value, (list, tuple)):
        return [_plain(item, depth + 1) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain(item, depth + 1) for key, item in value.items()}
    cleaned = clean_value(value)
    if isinstance(cleaned, (str, int, float, bool)) or cleaned is None:
        return cleaned
    fields = {}
    for name in dir(value):
        if name.startswith("_"):
            continue
        item = getattr(value, name, None)
        if callable(item) or isinstance(item, type) or item is value:
            continue
        fields[name] = item
    # pyo3 enums carry no .name/.value; their only public attributes are sibling
    # members of the same type. Render such a member by its text form.
    if fields and all(type(item) is type(value) for item in fields.values()):
        return str(value).rsplit(".", 1)[-1]
    if depth >= 6:
        return str(value)
    return {name: _plain(item, depth + 1) for name, item in fields.items()} if fields else str(value)


class SdkClient:
    """Adapter over ``longport.openapi.QuoteContext``; enum names arrive as plain strings."""

    def __init__(self, context=None, credentials_map=None):
        if context is None:
            from longport.openapi import Config, QuoteContext  # noqa: PLC0415
            values = credentials_map or credentials()
            config = Config.from_apikey(*(values[key] for key in ENV_KEYS),
                                        enable_print_quote_packages=False)
            context = QuoteContext(config)
        self.context = context

    @staticmethod
    def _enum(name, value):
        from longport import openapi  # noqa: PLC0415
        holder = getattr(openapi, name)
        member = getattr(holder, str(value), None)
        if member is None:
            raise ValueError(f"unknown {name}: {value!r}")
        return member

    def quote(self, symbols):
        return self.context.quote(list(symbols))

    def static_info(self, symbols):
        return self.context.static_info(list(symbols))

    def calc_indexes(self, symbols, indexes):
        return self.context.calc_indexes(
            list(symbols), [self._enum("CalcIndex", name) for name in indexes])

    def history_candlesticks_by_date(self, symbol, period, adjust, start, end, sessions=None):
        parse = lambda value: dt.date.fromisoformat(value) if value else None  # noqa: E731
        extra = {} if sessions is None else {
            "trade_sessions": self._enum("TradeSessions", sessions)}
        return self.context.history_candlesticks_by_date(
            symbol, self._enum("Period", period), self._enum("AdjustType", adjust),
            parse(start), parse(end), **extra)


def client_factory():
    """Default factory: a live SDK client, or None when credentials are absent."""
    return SdkClient() if credentials() else None


def land(out_dir, tool, symbol, params, response, *, fetched_at=None, period=None,
         known_gaps=(), status=None, status_reason=None):
    """Write the envelope + meta. ``response=None`` lands the metadata-only failure only."""
    refuse_private(tool, params, response)
    fetched_at = fetched_at or utc_now()
    out = Path(out_dir) / SOURCE
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", tool)
    gaps = list(known_gaps)
    if response is None:
        status, path = status or "error", out / f"{name}.meta.json"
    else:
        inferred, error, reason = response_status(response)
        status = status or inferred
        if inferred != "ok":
            gaps.append(reason)
        status_reason = status_reason or (reason if status == inferred else None)
        path = out / f"{name}.json"
        write_json(path, {"tool": tool, "symbol": symbol, "fetched_at": fetched_at,
                          "params": params, "response": response})
    if status != "ok" and not status_reason:
        status_reason = f"adapter reported {status}; see known gaps and the preserved envelope"
    meta_path = write_meta(path, source=SOURCE, tool=tool, params=params, fetched_at=fetched_at,
                           published_at=None, published_at_basis=SNAPSHOT_BASIS, period=period,
                           truncated={"is_truncated": False}, known_gaps=gaps, status=status,
                           source_url=None, symbol=symbol, status_reason=status_reason)
    return {"tool": tool, "path": None if response is None else str(path),
            "meta": str(meta_path), "status": status, "status_reason": status_reason}


def _call(out_dir, client, tool, symbol, params, produce, *, period=None):
    if client is None:
        return land(out_dir, tool, symbol, params, None, status="error",
                    status_reason=MISSING_CREDENTIALS,
                    known_gaps=[f"no call attempted: set {', '.join(ENV_KEYS)}"])
    try:
        response = _plain(produce(client))
    except Exception as exc:  # noqa: BLE001 - the adapter records failures, never invents a body
        return land(out_dir, tool, symbol, params, None, status="error",
                    status_reason=f"{type(exc).__name__}: {exc}",
                    known_gaps=["SDK call failed; no response body was received"])
    return land(out_dir, tool, symbol, params, response, period=period)


def quote(out_dir, symbols, *, client=None):
    symbols = list(symbols)
    return _call(out_dir, client, "quote", symbols[0] if len(symbols) == 1 else symbols,
                 {"symbols": symbols}, lambda c: c.quote(symbols))


def static_info(out_dir, symbols, *, client=None):
    symbols = list(symbols)
    return _call(out_dir, client, "static_info", symbols[0] if len(symbols) == 1 else symbols,
                 {"symbols": symbols}, lambda c: c.static_info(symbols))


def calc_indexes(out_dir, symbols, *, indexes=DEFAULT_INDEXES, client=None):
    symbols, indexes = list(symbols), list(indexes)
    return _call(out_dir, client, "calc_indexes", symbols[0] if len(symbols) == 1 else symbols,
                 {"symbols": symbols, "indexes": indexes},
                 lambda c: c.calc_indexes(symbols, indexes))


def history_candlesticks(out_dir, symbol, start, end, *, period="Day", adjust="NoAdjust",
                         sessions=None, client=None):
    """``start``/``end`` are ISO dates (or None); ``period``/``adjust`` are SDK enum names.

    ``sessions`` is the SDK ``TradeSessions`` name (Intraday / All). The landed params
    always declare the bar length, the adjustment and the trading sessions, because a
    series whose basis is not stated cannot be compared with, or extended by, another
    one (KARST-250). Left unset, the SDK's own default applies and the params say
    ``unknown`` rather than naming a session we did not ask for.
    """
    params = {"symbol": symbol, "period": period, "adjust_type": adjust,
              "trade_session": sessions or "unknown", "start": start, "end": end}
    return _call(out_dir, client, "history_candlesticks_by_date", symbol, params,
                 lambda c: c.history_candlesticks_by_date(symbol, period, adjust, start, end,
                                                          sessions),
                 period={"start": start, "end": end})


def fetch_company(symbol, out_dir, *, start=None, end=None, period="Day", adjust="NoAdjust",
                  sessions=None, indexes=DEFAULT_INDEXES, client=None, factory=client_factory):
    """Land the four public quote tools for one symbol; returns {tool: status}."""
    if client is None:
        client = factory()
    results = [quote(out_dir, [symbol], client=client),
               static_info(out_dir, [symbol], client=client),
               calc_indexes(out_dir, [symbol], indexes=indexes, client=client),
               history_candlesticks(out_dir, symbol, start, end, period=period,
                                    adjust=adjust, sessions=sessions, client=client)]
    return {result["tool"]: result["status"] for result in results}


def kind_for(meta) -> str:
    tool = str(meta.get("tool") or "")
    if tool not in TOOL_KINDS:
        raise ValueError(f"no declared kind for longbridge tool {tool!r}")
    return TOOL_KINDS[tool]


def fetch(security, out_dir, *, since=None, client=None) -> list[LandedRecord]:
    """Land this security's public quote tools. The vendor symbol is derived here.

    ``client`` is an SDK client or a zero-argument factory returning one (a test
    passes ``lambda: None`` to exercise the credentials-missing path); without it
    the default factory builds one, or lands ``error / credentials missing``.
    """
    options = options_for(client, "client")
    given = options.get("client")
    options["client"] = given() if callable(given) else (client_factory() if given is None else given)
    # The client is already resolved here, so an injected "no client" stays no client.
    options.setdefault("start", since)
    fetch_company(symbol_for(security), out_dir, factory=lambda: None, **options)
    return scan(Path(out_dir) / SOURCE, kind_for)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Land Longbridge public quote data for one symbol under <out>/longbridge/.")
    parser.add_argument("--symbol", required=True, help="e.g. AAPL.US")
    parser.add_argument("--out", required=True)
    parser.add_argument("--start", default=None, help="ISO date for candlesticks")
    parser.add_argument("--end", default=None, help="ISO date for candlesticks")
    parser.add_argument("--period", default="Day", help="SDK Period name: Day/Week/Month/...")
    parser.add_argument("--adjust", default="NoAdjust", help="SDK AdjustType name")
    parser.add_argument("--indexes", default=",".join(DEFAULT_INDEXES), help="SDK CalcIndex names")
    parser.add_argument("--env-file", default=None, help="default: <repo root>/.env")
    args = parser.parse_args(argv)
    load_env_file(args.env_file)
    statuses = fetch_company(args.symbol, args.out, start=args.start, end=args.end,
                             period=args.period, adjust=args.adjust,
                             indexes=[i for i in args.indexes.split(",") if i])
    json.dump(statuses, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0 if "error" not in statuses.values() else 1


if __name__ == "__main__":
    sys.exit(main())
