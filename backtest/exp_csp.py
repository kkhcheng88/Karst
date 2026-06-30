"""Experiment: CSP on QQQ/SPY — validate VRP + test entry timing. (last 10 years)

20-delta put, 30 DTE (~21 trading days), 50% PT, no SL, single-leg (no wheel),
capital $50k/underlying, cost 1.5%/side of premium. Three entry timings:
  - unconditional / low IV rank (<=25% trailing 252d) / RSI-2 dip (RSI(2)<10)
Plus a PURE-HOLDING ($50k in the ETF) benchmark with total trades (=1) and total profit.
Window: last 10 years (indicators use full-history lookback so they're valid at the
start of the window). Note: this window EXCLUDES 2000/2008 — a milder max-DD regime.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import metrics  # noqa: E402
from data import load  # noqa: E402
from engine import buy_hold  # noqa: E402
from options_engine import simulate_csp  # noqa: E402
from signals import rsi  # noqa: E402

PAIRS = [("QQQ", "^VXN", 0.006), ("SPY", "^VIX", 0.013)]
TARGET_DELTA, DTE, PT, CAP, YEARS = 0.20, 21, 0.50, 50000.0, 10
WIN = 252 * YEARS


def iv_rank(v, win=252):
    s = pd.Series(v)
    lo, hi = s.rolling(win).min(), s.rolling(win).max()
    return ((s - lo) / (hi - lo)).values


def navmetrics(nav, ret, mkt):
    a, b, ta = metrics.jensen_alpha(ret, mkt)
    return metrics.cagr(nav), a, ta, metrics.ann_sharpe(ret), \
        metrics.max_drawdown(nav), metrics.avg_drawdown(nav)


def main():
    print(f"CSP {int(TARGET_DELTA*100)}D put, {DTE}td, {int(PT*100)}% PT, no SL, "
          f"${CAP:,.0f}/underlying, cost 1.5%/side — LAST {YEARS} YEARS")
    for under, volsym, q in PAIRS:
        c, vv = load(under)["close"], load(volsym)["close"]
        df = pd.concat({"close": c, "vol": vv}, axis=1).dropna()
        ivr, r2 = iv_rank(df["vol"].values), rsi(df["close"], 2).values
        sub = df.iloc[-WIN:]
        S, Vol = sub["close"].values, sub["vol"].values
        bh_ret, bh_nav0 = buy_hold(S)
        bh_nav = CAP * S / S[0]
        gates = {"unconditional": None, "low-IV-rank<=25%": ivr[-WIN:] <= 0.25,
                 "RSI2<10 dip": r2[-WIN:] < 10}

        print(f"\n### {under}  ({sub.index.min().date()}->{sub.index.max().date()})")
        print("  entry-gate         | Trades  TotalP/L   Win%   PF | CAGR  Alpha   aT  Shrp | MaxDD  AvgDD")
        for name, g in gates.items():
            nav, tr = simulate_csp(S, Vol, gate=g, target_delta=TARGET_DELTA,
                                   dte_init=DTE, pt=PT, q=q, capital=CAP)
            ret = np.concatenate([[0.0], nav[1:] / nav[:-1] - 1])
            cg, a, ta, sh, mdd, add = navmetrics(nav, ret, bh_ret)
            win = float((tr > 0).mean()) if len(tr) else float("nan")
            pf = (tr[tr > 0].sum() / abs(tr[tr < 0].sum())) if (len(tr) and tr[tr < 0].sum() != 0) else float("inf")
            print(f"  {name:18} | {len(tr):6d} {tr.sum():9,.0f} {win*100:5.0f}% {pf:5.2f} | "
                  f"{cg*100:5.2f}% {a*100:5.2f}% {ta:5.1f} {sh:5.2f} | {mdd*100:5.1f}% {add*100:5.1f}%")
        # pure holding benchmark
        cg, _, _, sh, mdd, add = navmetrics(bh_nav, bh_ret, bh_ret)
        print(f"  {'PURE HOLDING':18} | {1:6d} {bh_nav[-1]-CAP:9,.0f} {'  - ':>5} {'  - ':>5} | "
              f"{cg*100:5.2f}% {'   - ':>5} {'  - ':>5} {sh:5.2f} | {mdd*100:5.1f}% {add*100:5.1f}%")


if __name__ == "__main__":
    main()
