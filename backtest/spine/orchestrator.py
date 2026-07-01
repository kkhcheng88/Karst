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
from . import context, expression, providers, rotation, sector, timing
from . import universe as universe_mod
from .dataio import load


def run_daily(path: str | None = None):
    sectors_cfg, entries = universe_mod.load_universe(path or universe_mod.DEFAULT_PATH)
    entries = universe_mod.expand_with_sectors(sectors_cfg, entries)
    mc = context.build_market_context()
    rot = rotation.build_rotation()
    sec_ctx = sector.build_all(sectors_cfg)
    cards = []
    for e in entries:
        try:
            th = providers.thesis_quality(e.ticker)
            if expression.route(e) == "options":
                d = load(e.ticker)[["high", "low", "close"]]
                v = load(e.iv_proxy, min_rows=50)["close"]
                df = d.join(v.rename("vix"), how="inner").dropna()
                tm = timing.entry_timing(df["close"])
                score, expr = expression.express_options(e, df)
                temp, warm = "N/A", 1
            else:
                df = load(e.ticker, min_rows=30)  # young names/ETFs (e.g. DRAM 61d) still load
                tm = timing.entry_timing(df["close"])
                sc = sec_ctx.get(e.sector)
                score, expr = expression.express_long(e, df, mc, th, sc, tm)
                temp = sc.temperature if sc else providers.SECTOR_STUB_TEMP
                warm = sc.warm if sc else providers.SECTOR_STUB_WARM
            cards.append(card_mod.build_card(e, mc, score, expr, th, temp, warm, tm))
        except Exception as ex:  # isolate per-ticker failures
            cards.append(card_mod.error_card(e, mc, ex))
    return mc, rot, sec_ctx, cards


def _print_human(mc, rot, sec_ctx, cards):
    print("=== KARST SCAN -- MVP1 + sector rotation (2a) ===")
    print(f"as of {mc.asof}")
    print(f"\nMARKET: {mc.gate_label.upper()}  (gate={mc.gate})")
    print(f"  {mc.drivers}")
    for c in mc.caveats:
        print(f"  ! {c}")

    if rot:
        print("\n--- SECTOR ROTATION (11 SPDR vs SPY -- the DEFENSE/regime lens) ---")
        print(f"  {rot.drivers}")
        for r in rot.rows:
            beat = "+" if r["rs63"] > 1 else " "
            print(f"    {beat} {r['etf']:5}{r['name']:9} RS63 {r['rs63']:.2f}  RS21 {r['rs21']}  "
                  f"{'>200' if r['above200'] else '<200':5} {r['temp']:5} [{r['group']}]")
        for cav in rot.caveats:
            print(f"  ! {cav}")

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

    print("\n--- tier-2 LONG (action = structural eligibility x RSI-2 timing) ---")
    for c in longs:
        if c.expression.get("type") == "ERROR":
            print(f"### {c.ticker:5}  ERROR: {c.expression['error']}")
            continue
        blk = c.expression.get("blocked_by") or []
        tail = f"  blocked: {', '.join(blk)}" if blk else ""
        et = c.entry_timing or {}
        tcol = f"RSI2 {et.get('rsi2')} {et.get('label')}"
        th = c.thesis
        print(f"### {c.ticker:5}  {c.asof}  {c.sector} temp={c.sector_temp}")
        print(f"  {c.expression['action']:8} score {c.score:>3.0f}  | {tcol:18} | {c.expression['drivers']}{tail}")
        conf = th.get("confidence")
        print(f"  thesis: {th.get('verdict')} | conf {conf if conf is None else round(conf, 2)}"
              f" | cycle {th.get('cycle_stage')} | {th.get('source')}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Karst top-down scan (Phase 0)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--universe", default=None, help="path to universe.yaml")
    args = ap.parse_args(argv)

    mc, rot, sec_ctx, cards = run_daily(args.universe)
    if args.json:
        out = {"market": asdict(mc),
               "rotation": asdict(rot) if rot else None,
               "sectors": {k: asdict(v) for k, v in sec_ctx.items()},
               "cards": [card_mod.to_dict(c) for c in cards]}
        print(json.dumps(out, indent=2, default=str))
    else:
        _print_human(mc, rot, sec_ctx, cards)


if __name__ == "__main__":
    main()
