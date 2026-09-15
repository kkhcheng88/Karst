"""Broker landing: write an MCP return (futu / longbridge) the agent already holds to ``<out>/<source>/<tool>.json`` + meta.

This module calls no MCP. It refuses anything that looks like account, position, P&L or order data
(研究不讀私人帳戶, D-181): offending keys at the top level of ``params``/``response`` (and one level under
``data``/``result``), or an account/trade-class tool name, raise ``PrivateDataError``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .common import utc_now, write_json, write_meta

PRIVATE_KEYS = frozenset({
    "acc_id", "account", "account_id", "accounts", "position", "positions", "pl_ratio", "pl_val", "cost_price",
    "cost_price_valid", "market_val", "unrealized_pl", "realized_pl", "cash", "total_cash", "funds", "power",
    "max_power_short", "order_id", "orders", "order_status", "trd_env", "trd_side", "trd_market", "can_sell_qty",
    "net_assets", "available_cash", "buying_power", "executions", "fills", "holdings",
})
PRIVATE_KEY_PREFIXES = ("acc_", "account", "position", "pl_ratio", "cost_price", "trd_env", "order_id", "unrealized", "realized")
PRIVATE_TOOL_PATTERN = re.compile(
    r"(?i)(^|_)(account|accounts|trading|trade|sim_trade|crypto_account|positions|stock_positions|fund_positions|"
    r"submit_order|cancel_order|replace_order|order_detail|orders|executions|deposits|withdrawals|bank_cards|"
    r"ipo_subscriptions|ipo_profit_loss|estimate_max_purchase_quantity|user_security|dca|grid|watchlist|sharelist|alert|"
    r"statement_list|statement_export)(_|$)"
)
PUBLIC_TOOL_ALLOW = re.compile(
    r"(?i)(^|_)(order_book|depth|trading_days|trading_session|trade_stats|short_trades|short_positions|insider_trade|insider_trade_list)(_|$)"
)


class PrivateDataError(ValueError):
    """Raised when a landing would carry account/position/order data."""


def _is_private_key(key: str) -> bool:
    key = str(key).lower()
    return key in PRIVATE_KEYS or key.startswith(PRIVATE_KEY_PREFIXES)


def private_keys_in(payload) -> list[str]:
    """Private-looking keys at the top level of a dict (and one level under data/result); lists are scanned per item."""
    found = []
    items = payload if isinstance(payload, list) else [payload]
    for item in items:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if _is_private_key(key):
                found.append(str(key))
            if key in ("data", "result", "response"):
                found += [f"{key}.{k}" for k in private_keys_in(value)]
    return found


def refuse_private(tool: str, params, response) -> None:
    if PRIVATE_TOOL_PATTERN.search(tool or "") and not PUBLIC_TOOL_ALLOW.search(tool or ""):
        raise PrivateDataError(f"tool {tool!r} is an account/trade-class tool; broker landing accepts public market methods only")
    hits = private_keys_in(params) + private_keys_in(response)
    if hits:
        raise PrivateDataError(f"private keys refused for {tool!r}: {sorted(set(hits))}")


def response_status(response) -> tuple[str, dict | None]:
    """ok / empty / error by the shape of the return: error envelopes (error_code, error, ret_code != 0), then emptiness."""
    if isinstance(response, dict):
        if response.get("error_code") not in (None, 0, "0") or response.get("error"):
            return "error", response.get("error") if isinstance(response.get("error"), dict) else response
        if "ret_code" in response and response.get("ret_code") not in (0, "0", None):
            return "error", response
        body = response.get("data", response.get("result", response))
        if body in (None, [], {}, ""):
            return "empty", None
        return "ok", None
    if response in (None, [], "", ()):
        return "empty", None
    return "ok", None


def land(out_dir, source: str, tool: str, symbol, params, response, *, fetched_at: str | None = None,
         known_gaps=()) -> dict:
    """Write ``<out_dir>/<source>/<tool>.json`` (outer {tool, symbol, fetched_at, params, response}) and its meta."""
    if source not in ("futu", "longbridge"):
        raise ValueError(f"source must be futu or longbridge, got {source!r}")
    refuse_private(tool, params, response)
    fetched_at = fetched_at or utc_now()
    out = Path(out_dir) / source
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", tool.rsplit("__", 1)[-1])
    path = out / f"{name}.json"
    write_json(path, {"tool": tool, "symbol": symbol, "fetched_at": fetched_at, "params": params, "response": response})
    status, error = response_status(response)
    gaps = list(known_gaps) + ["response transcribed from MCP tool output by the agent; time fields inside the response not parsed"]
    if status == "error":
        gaps.append(f"tool returned an error envelope: {json.dumps(error, ensure_ascii=False, default=str)[:500]}; "
                    "fetch failed is not 'no data' (資料來源 §零)")
    if status == "empty":
        gaps.append("empty return: distinguish 'nothing to report' from 'not covered' before treating as absence")
    meta_path = write_meta(path, source=source, tool=tool, params=params, fetched_at=fetched_at, published_at=None,
                           published_at_basis="現時快照 (snapshot at fetch time); the source gives no publication time for this return",
                           period=None, truncated={"is_truncated": False}, known_gaps=gaps, status=status, source_url=None,
                           symbol=symbol, error=error)
    return {"path": str(path), "meta": str(meta_path), "status": status}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Land one MCP return under <out>/<source>/<tool>.json (no MCP call is made).")
    parser.add_argument("--out", required=True)
    parser.add_argument("--source", required=True, choices=("futu", "longbridge"))
    parser.add_argument("--tool", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--params", default="{}", help="JSON object")
    parser.add_argument("--response-file", required=True, help="JSON file holding the raw tool return")
    parser.add_argument("--fetched-at", default=None, help="UTC Z; default now")
    args = parser.parse_args(argv)
    with open(args.response_file, encoding="utf-8") as handle:
        response = json.load(handle)
    try:
        result = land(args.out, args.source, args.tool, args.symbol, json.loads(args.params), response, fetched_at=args.fetched_at)
    except PrivateDataError as exc:
        sys.stderr.write(f"refused: {exc}\n")
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0 if result["status"] != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
