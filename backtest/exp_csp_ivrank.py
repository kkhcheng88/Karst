"""Experiment: naked CSP split by IV-rank bucket (the user's tool, vs 56/57 spreads).

20-delta cash-secured put, 30 DTE (~21 td), HOLD TO EXPIRY (matches 56/57), single-leg,
full history (for sample in rare buckets). Buckets trades by IV rank at entry.
Does naked CSP show the same U-shape (low IV best) as the bull-put-spread test?
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from data import load  # noqa: E402
from options_engine import simulate_csp  # noqa: E402
from regime import iv_rank  # noqa: E402

PAIRS = [("QQQ", "^VXN", 0.006), ("SPY", "^VIX", 0.013)]
TD, CAP = 21, 50000.0
BUCKETS = [("low 0-25", 0.0, 0.25), ("mid 25-50", 0.25, 0.5),
           ("high 50-75", 0.5, 0.75), ("vhigh 75-100", 0.75, 1.01)]


def main():
    print(f"CSP 20D put, {TD}td, HOLD-TO-EXPIRY, single-leg, full history, by IV rank "
          f"(cf. 56/57 bull-put-spread)")
    for under, volsym, q in PAIRS:
        c, vv = load(under)["close"], load(volsym)["close"]
        df = pd.concat({"close": c, "vol": vv}, axis=1).dropna()
        ivr = iv_rank(df["vol"]).values
        nav, trades = simulate_csp(df["close"].values, df["vol"].values, gate=None,
                                   target_delta=0.20, dte_init=TD, pt=None, q=q, capital=CAP)
        print(f"\n### {under}  ({df.index.min().date()}->{df.index.max().date()})  "
              f"trades {len(trades)}")
        print("  IV-rank bucket | Trades  TotalP/L   Win%    PF   Avg/trade")
        for label, lo, hi in BUCKETS:
            arr = np.array([p for (ei, p) in trades
                            if not np.isnan(ivr[ei]) and lo <= ivr[ei] < hi])
            if len(arr) == 0:
                print(f"  {label:14} | (none)")
                continue
            neg = arr[arr < 0].sum()
            pf = arr[arr > 0].sum() / abs(neg) if neg != 0 else float("inf")
            print(f"  {label:14} | {len(arr):6d} {arr.sum():9,.0f} {(arr>0).mean()*100:5.0f}% "
                  f"{pf:5.2f} {arr.mean():9,.0f}")


if __name__ == "__main__":
    main()
