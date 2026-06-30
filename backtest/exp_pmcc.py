"""Experiment: PMCC vs standalone LEAP vs pure holding (the untested tool).

Does adding a 1:1 short OTM call (PMCC) to a 200SMA-gated deep-ITM LEAP help or hurt?
All 200SMA-gated. Last 10 years. Reports total profit ($), Sharpe, alpha, MaxDD.
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
from options_engine import simulate_leap, simulate_pmcc  # noqa: E402

PAIRS = [("SPY", "^VIX", 0.013), ("QQQ", "^VXN", 0.006)]
CAP, YEARS = 10000.0, 10
WIN = 252 * YEARS


def row(name, nav, mkt):
    ret = np.concatenate([[0.0], nav[1:] / nav[:-1] - 1])
    a, b, ta = metrics.jensen_alpha(ret, mkt)
    return (f"  {name:20} {nav[-1]-CAP:11,.0f} {metrics.cagr(nav)*100:6.2f}% "
            f"{a*100:6.2f}% {ta:5.1f} {metrics.ann_sharpe(ret):5.2f} "
            f"{metrics.max_drawdown(nav)*100:6.1f}% {metrics.avg_drawdown(nav)*100:5.1f}%")


def main():
    print(f"200SMA-gated LEAP vs PMCC vs pure holding, ${CAP:,.0f}, last {YEARS}y")
    for under, volsym, q in PAIRS:
        c, vv = load(under)["close"], load(volsym)["close"]
        df = pd.concat({"close": c, "vol": vv}, axis=1).dropna()
        sma = df["close"].rolling(200).mean()
        df = df.loc[sma.first_valid_index():]
        gate = (df["close"] > sma.loc[df.index]).values
        sub = df.iloc[-WIN:]
        S, Vol, g = sub["close"].values, sub["vol"].values, gate[-WIN:]
        mkt = buy_hold(S)[0]

        nav_leap = simulate_leap(S, Vol, gate=g, q=q, capital=CAP)
        nav_pmcc = simulate_pmcc(S, Vol, gate=g, q=q, capital=CAP)
        bh = CAP * S / S[0]

        print(f"\n### {under}  ({sub.index.min().date()}->{sub.index.max().date()})")
        print("  strategy              TotalP/L    CAGR   Alpha   aT  Shrp  MaxDD  AvgDD")
        print(row("LEAP (gated)", nav_leap, mkt))
        print(row("PMCC (gated)", nav_pmcc, mkt))
        print(row("pure holding", bh, mkt))


if __name__ == "__main__":
    main()
