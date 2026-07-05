"""Experiment: does a deep-ITM LEAP need timing?

Hypothesis: the 200SMA right-side gate that HURT the RSI-2 share strategy should
HELP a leveraged LEAP, because it keeps leverage OFF in downtrends (where leverage
is ~terminal). Compares: LEAP always-in vs LEAP gated by price>SMA200 vs B&H shares.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import metrics  # noqa: E402
from data import load  # noqa: E402
from options_engine import simulate_leap  # noqa: E402

PAIRS = [("SPY", "^VIX", 0.013), ("QQQ", "^VXN", 0.006)]
CAPITAL = 10000.0


def navmetrics(nav):
    nav = np.asarray(nav, float)
    ret = np.zeros(len(nav))
    ret[1:] = nav[1:] / nav[:-1] - 1
    return {"CAGR": metrics.cagr(nav), "Sharpe": metrics.ann_sharpe(ret),
            "MaxDD": metrics.max_drawdown(nav), "Final": nav[-1] / nav[0]}


def fmt(name, m):
    return (f"  {name:16} CAGR {m['CAGR']*100:6.2f}%  Sharpe {m['Sharpe']:5.2f}  "
            f"MaxDD {m['MaxDD']*100:7.1f}%  x{m['Final']:.1f}")


def main():
    for under, volsym, q in PAIRS:
        c = load(under)["close"]
        v = load(volsym)["close"]
        df = pd.concat({"close": c, "vol": v}, axis=1).dropna()
        sma = df["close"].rolling(200).mean()
        df = df.loc[sma.first_valid_index():]
        gate = (df["close"] > sma.loc[df.index]).values

        navs = {
            "LEAP always": simulate_leap(df["close"].values, df["vol"].values,
                                         gate=None, q=q, capital=CAPITAL),
            "LEAP 200SMA-gated": simulate_leap(df["close"].values, df["vol"].values,
                                               gate=gate, q=q, capital=CAPITAL),
        }
        bh = (CAPITAL * df["close"] / df["close"].iloc[0]).values

        print(f"\n### {under} (vol={volsym}, q={q:.1%})  "
              f"{df.index.min().date()}->{df.index.max().date()}")
        for name, nav in navs.items():
            print(fmt(name, navmetrics(nav)))
        print(fmt("buy & hold shares", navmetrics(bh)))


if __name__ == "__main__":
    main()
