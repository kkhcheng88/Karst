"""Experiment: WHEN to sell the short call (the only new leg vs LEAP).

Short OTM call (0.30 delta, 30 DTE ~21td, 50% PT). Compare timing gates:
  - unconditional (always)
  - overbought RSI-2 > 70 / > 90  (sell when underlying is high — the user's hypothesis)
  - high IV rank (>50%)  (richer premium)
Short call profits if underlying stays below strike; the risk is a rip-up. Question: does
selling on overbought / high-IV improve per-trade quality (PF, avg) vs selling blindly?
(cf. Backtest Everything covered calls: 30 DTE, 0.3 delta, 50% PT.)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from data import load  # noqa: E402
from options_engine import simulate_short_call  # noqa: E402
from regime import iv_rank  # noqa: E402
from signals import rsi  # noqa: E402

PAIRS = [("SPY", "^VIX", 0.013), ("QQQ", "^VXN", 0.006)]
CAP = 50000.0


def stats(trades):
    a = np.array([p for _, p in trades]) if trades else np.array([])
    if len(a) == 0:
        return 0, 0.0, float("nan"), float("nan"), float("nan")
    neg = a[a < 0].sum()
    pf = a[a > 0].sum() / abs(neg) if neg != 0 else float("inf")
    return len(a), a.sum(), (a > 0).mean(), pf, a.mean()


def main():
    print("Short-call overlay (0.30D, 21td, 50% PT) — when to sell?  cost 1.5%/side")
    for under, vs, q in PAIRS:
        c, vv = load(under)["close"], load(vs)["close"]
        df = pd.concat({"close": c, "vol": vv}, axis=1).dropna()
        S, Vol = df["close"].values, df["vol"].values
        r2 = rsi(df["close"], 2).values
        ivr = iv_rank(df["vol"]).values
        gates = {
            "unconditional": None,
            "overbought RSI2>70": r2 > 70,
            "overbought RSI2>90": r2 > 90,
            "high IV rank>50%": ivr > 0.50,
        }
        print(f"\n### {under}  ({df.index.min().date()}->{df.index.max().date()})")
        print("  gate                 | Trades  TotalP/L   Win%    PF   Avg/trade")
        for name, g in gates.items():
            _, tr = simulate_short_call(S, Vol, gate=g, q=q, capital=CAP)
            n, tot, win, pf, avg = stats(tr)
            print(f"  {name:20} | {n:6d} {tot:9,.0f} {win*100:5.0f}% {pf:5.2f} {avg:9,.0f}")


if __name__ == "__main__":
    main()
