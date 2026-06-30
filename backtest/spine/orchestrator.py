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
from . import context, expression, providers, sector
from . import universe as universe_mod
from .dataio import load


def run_daily(path: str | None = None):
    sectors_cfg, entries = universe_mod.load_universe(path or universe_mod.DEFAULT_PATH)
    entries = universe_mod.expand_with_sectors(sectors_cfg, entries)
    mc = context.build_market_context()
    sec_ctx = sector.build_all(sectors_cfg)
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
                df = load(e.ticker, min_rows=30)  # young names/ETFs (e.g. DRAM 61d) still load
                sc = sec_ctx.get(e.sector)
                score, expr = expression.express_long(e, df, mc, th, sc)
                temp = sc.temperature if sc else providers.SECTOR_STUB_TEMP
                warm = sc.warm if sc else providers.SECTOR_STUB_WARM
            cards.append(card_mod.build_card(e, mc, score, expr, th, temp, warm))
        except Exception as ex:  # isolate per-ticker failures
            cards.append(card_mod.error_card(e, mc, ex))
    return mc, sec_ctx, cards


def _print_human(mc, sec_ctx, cards):
    print("=== KARST SCAN -- Phase 1 (market gate + sector temp + two-tier router) ===")
    print(f"as of {mc.asof}")
    print(f"\nMARKET: {mc.gate_label.upper()}  (gate={mc.gate})")
    print(f"  {mc.drivers}")
    for c in mc.caveats:
        print(f"  ! {c}")

    if sec_ctx:
        print("\n--- SECTORS (Stage 1: temperature from ETF holdings) ---")
        for key, sc in sec_ctx.items():
            print(f"### {key} (parent {sc.parent})  {sc.temperature}  warm={sc.warm}")
            print(f"  {sc.drivers}")
            for t, info in sorted(sc.member_rank.items(), key=lambda kv: kv[1]["rank"])[:6]:
                flag = "US" if info["is_us"] else "intl"
                lag = " LAGGARD" if info["is_laggard"] else ""
                rvp = info["rs_vs_parent"]
                print(f"    {info['rank']}. {t:11} {flag:4} w{info['weight'] * 100:4.1f}%  "
                      f"RSvs{sc.parent} {rvp if rvp is not None else 'n/a':<5}  ROC20 {info['roc20'] * 100:+5.0f}%{lag}")
            for cav in sc.caveats:
                print(f"  ! {cav}")

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

    print("\n--- tier-2 LONG (sector temp LIVE; NO entry timing -- that's Phase 4) ---")
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

    mc, sec_ctx, cards = run_daily(args.universe)
    if args.json:
        out = {"market": asdict(mc),
               "sectors": {k: asdict(v) for k, v in sec_ctx.items()},
               "cards": [card_mod.to_dict(c) for c in cards]}
        print(json.dumps(out, indent=2, default=str))
    else:
        _print_human(mc, sec_ctx, cards)


if __name__ == "__main__":
    main()
