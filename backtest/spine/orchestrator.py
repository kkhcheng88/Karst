"""Stage glue — run the daily top-down scan and render it.

Build the market context ONCE, then route each universe ticker through its tier and
emit a Card. Per-ticker failures are isolated (an error card) so one bad symbol never
crashes the run.

Run:  python backtest/scan.py            (human)   /   --json   /   --universe <path>
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from . import card as card_mod
from . import context, expression, providers
from . import universe as universe_mod
from .dataio import load


def run_daily(path: str | None = None):
    _sectors, entries = universe_mod.load_universe(path or universe_mod.DEFAULT_PATH)
    mc = context.build_market_context()
    cards = []
    for e in entries:
        try:
            th = providers.thesis_quality(e.ticker)
            if expression.route(e) == "options":
                d = load(e.ticker)[["high", "low", "close"]]
                v = load(e.iv_proxy, min_rows=50)["close"]
                df = d.join(v.rename("vix"), how="inner").dropna()
                score, expr = expression.express_options(e, df)
                temp, warm = "N/A", 1
            else:
                df = load(e.ticker)
                temp, warm = providers.SECTOR_STUB_TEMP, providers.SECTOR_STUB_WARM
                score, expr = expression.express_long(e, df, mc, th, warm)
            cards.append(card_mod.build_card(e, mc, score, expr, th, temp, warm))
        except Exception as ex:  # isolate per-ticker failures
            cards.append(card_mod.error_card(e, mc, ex))
    return mc, cards


def _print_human(mc, cards):
    print("=== KARST SCAN -- Phase 0 (market gate + two-tier router) ===")
    print(f"as of {mc.asof}")
    print(f"\nMARKET: {mc.gate_label.upper()}  (gate={mc.gate})")
    print(f"  {mc.drivers}")
    for c in mc.caveats:
        print(f"  ! {c}")

    opts = [c for c in cards if c.tier == "options"]
    longs = [c for c in cards if c.tier == "long"]

    print("\n--- tier-1 OPTIONS (SPY/QQQ/SPMO) ---")
    for c in opts:
        if c.expression.get("type") == "ERROR":
            print(f"### {c.ticker:5}  ERROR: {c.expression['error']}")
            continue
        ranked = sorted(c.score.items(), key=lambda kv: -kv[1])
        print(f"### {c.ticker:5}  {c.asof}")
        print("  " + "  ".join(f"{k} {int(v):3d}" for k, v in ranked)
              + f"   (rec: {c.expression['recommended']})")
        print(f"  {c.expression['drivers']}  | CSP: {c.expression['csp_mode']}")

    print("\n--- tier-2 LONG (sector temp = STUB in Phase 0; NO timing -- that's Phase 4) ---")
    for c in longs:
        if c.expression.get("type") == "ERROR":
            print(f"### {c.ticker:5}  ERROR: {c.expression['error']}")
            continue
        blk = c.expression.get("blocked_by") or []
        tail = f"  blocked: {', '.join(blk)}" if blk else ""
        print(f"### {c.ticker:5}  {c.asof}  sector={c.sector} temp={c.sector_temp}")
        print(f"  score {c.score:>5.0f}  {c.expression['action']}  | {c.expression['drivers']}{tail}")
        print(f"  thesis: {c.thesis.get('verdict')} ({c.thesis.get('source')})")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Karst top-down scan (Phase 0)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--universe", default=None, help="path to universe.yaml")
    args = ap.parse_args(argv)

    mc, cards = run_daily(args.universe)
    if args.json:
        out = {"market": asdict(mc), "cards": [card_mod.to_dict(c) for c in cards]}
        print(json.dumps(out, indent=2, default=str))
    else:
        _print_human(mc, cards)


if __name__ == "__main__":
    main()
