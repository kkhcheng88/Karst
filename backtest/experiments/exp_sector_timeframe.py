"""2b follow-up — does sector-level RSI-2 have MORE edge on DAILY or WEEKLY bars?

Connors RSI-2 was designed/validated on DAILY bars. At the sector level (diversified, less
noisy), a WEEKLY oversold = a genuine multi-week pullback (vs daily wiggle), which may align
better with a trend-hold. Cost: ~1/5 the bars -> less statistical power, higher overfit risk.
So we MEASURE it, same gates as 2b (beats B&H, deflated Sharpe over all trials).

Daily : RSI2<10 & close>200SMA ; HOLD exit <200SMA / BOUNCE exit RSI2>70   (ann=252)
Weekly: RSI2<10 & close>40wSMA ; HOLD exit <40wSMA / BOUNCE exit RSI2>70    (ann=52)
(40-week SMA ~ 200 trading days, so the trend gate is comparable across timeframes.)

Run: python backtest/experiments/exp_sector_timeframe.py
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load
from engine import backtest, buy_hold
from metrics import ann_sharpe, cagr, deflated_sharpe_ratio, max_drawdown
from signals import rsi, sma

SPDR = [("XLK", "Tech"), ("XLC", "Comm"), ("XLY", "Discr"), ("XLI", "Indus"), ("XLF", "Fin"),
        ("XLB", "Materl"), ("XLE", "Energy"), ("XLV", "Health"), ("XLP", "Staples"),
        ("XLU", "Util"), ("XLRE", "RealEst")]
COST_BPS = 2.0


def variants(close, trend_win):
    """Return {name: (entry, exit)} for a given close series + trend SMA window."""
    r2 = rsi(close, 2)
    st = sma(close, trend_win)
    up = (close > st).to_numpy()
    dip = (r2 < 10).to_numpy()
    ob = (r2 > 70).to_numpy()
    return {"HOLD": (dip & up, ~up), "BOUNCE": (dip & up, ob)}


def run_tf(close, trend_win, ppy):
    out = {}
    arr = close.to_numpy()
    for k, (en, ex) in variants(close, trend_win).items():
        pos, strat, equity = backtest(arr, en, ex, cost_bps=COST_BPS)
        out[k] = {"Sharpe": ann_sharpe(strat, ppy), "CAGR": cagr(equity, ppy),
                  "MaxDD": max_drawdown(equity), "Trades": int(np.sum(np.diff(pos) > 0)),
                  "strat": strat}
    bh_ret, bh_eq = buy_hold(arr)
    out["BH"] = {"Sharpe": ann_sharpe(bh_ret, ppy), "CAGR": cagr(bh_eq, ppy), "MaxDD": max_drawdown(bh_eq)}
    return out


def run():
    rows = []
    trials = []
    for etf, name in SPDR:
        try:
            d = load(etf, adjusted=True, min_rows=300)["close"]
        except Exception as e:
            print(f"{etf:5} SKIP {str(e)[:40]}")
            continue
        wk = d.resample("W-FRI").last().dropna()
        daily = run_tf(d, 200, 252)
        weekly = run_tf(wk, 40, 52)
        for tf in (daily, weekly):
            for k in ("HOLD", "BOUNCE"):
                trials.append(tf[k]["Sharpe"])
        rows.append({"etf": etf, "name": name, "d": daily, "w": weekly})

    print(f"\n=== sector RSI-2: DAILY vs WEEKLY (total-return, {COST_BPS}bp) ===")
    print(f"trial universe = {len(trials)} Sharpes\n")
    h = (f"{'sec':10}| {'D.HOLD':>7}{'D.BNCE':>7}{'D.BH':>6}{'>BH':>4} | "
         f"{'W.HOLD':>7}{'W.BNCE':>7}{'W.BH':>6}{'>BH':>4} | {'better':>7}")
    print(h)
    print("-" * len(h))
    d_wins = w_wins = 0
    for r in rows:
        d, w = r["d"], r["w"]
        d_best = max(d["HOLD"]["Sharpe"], d["BOUNCE"]["Sharpe"])
        w_best = max(w["HOLD"]["Sharpe"], w["BOUNCE"]["Sharpe"])
        d_bh = "Y" if d_best > d["BH"]["Sharpe"] else "n"
        w_bh = "Y" if w_best > w["BH"]["Sharpe"] else "n"
        better = "WEEKLY" if w_best > d_best else "daily"
        if better == "WEEKLY":
            w_wins += 1
        else:
            d_wins += 1
        print(f"{r['name']:10}| {d['HOLD']['Sharpe']:7.2f}{d['BOUNCE']['Sharpe']:7.2f}"
              f"{d['BH']['Sharpe']:6.2f}{d_bh:>4} | {w['HOLD']['Sharpe']:7.2f}{w['BOUNCE']['Sharpe']:7.2f}"
              f"{w['BH']['Sharpe']:6.2f}{w_bh:>4} | {better:>7}")

    # best (timeframe x variant) per sector + DSR
    print("\nbest variant per sector (Sharpe), with deflated-SR vs the full trial spread:")
    for r in rows:
        cands = [("D.HOLD", r["d"]["HOLD"]), ("D.BOUNCE", r["d"]["BOUNCE"]),
                 ("W.HOLD", r["w"]["HOLD"]), ("W.BOUNCE", r["w"]["BOUNCE"])]
        bn, bv = max(cands, key=lambda c: c[1]["Sharpe"] if c[1]["Sharpe"] == c[1]["Sharpe"] else -9)
        ppy = 52 if bn.startswith("W") else 252
        dsr = deflated_sharpe_ratio(bv["strat"], trials, ppy)
        bh = r["w"]["BH"] if bn.startswith("W") else r["d"]["BH"]
        print(f"  {r['name']:10} {bn:9} Sharpe {bv['Sharpe']:5.2f}  CAGR {bv['CAGR']*100:6.1f}% "
              f"MaxDD {bv['MaxDD']*100:6.1f}% Tr {bv['Trades']:4d}  DSR {dsr:.2f}   (B&H CAGR {bh['CAGR']*100:5.1f}%)")

    print(f"\nbetter timeframe (by best Sharpe): WEEKLY {w_wins}/{len(rows)}, daily {d_wins}/{len(rows)}")


if __name__ == "__main__":
    run()
