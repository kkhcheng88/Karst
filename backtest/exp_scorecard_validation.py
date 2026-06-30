"""Validate the scorecard: do scores reach both ends, and do they PREDICT?

For each tool, bucket every day by that tool's score, then measure the realized
FORWARD outcome of the underlying over the next 21 trading days:
  - fwd return (mean, % positive)
  - fwd drawdown (mean worst close-to-trough within the window)
Uses only OHLCV forward returns (reliable) — no provisional option magnitudes.

Answers: (1) score distribution/range, (2) is high score -> better outcome (monotonic?),
(3) where does the outcome turn favorable = the entry boundary.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import scorecard  # noqa: E402
from data import load  # noqa: E402

N = next((int(a) for a in sys.argv[1:] if a.isdigit()), 21)
BINS = [(0, 25), (25, 50), (50, 75), (75, 101)]
TOOLS = ["LEAP", "PMCC", "CSP", "CASH"]


def fwd(close, n=N):
    m = len(close)
    ret = np.full(m, np.nan)
    dd = np.full(m, np.nan)
    for i in range(m - n):
        w = close[i + 1:i + n + 1]
        ret[i] = close[i + n] / close[i] - 1
        dd[i] = w.min() / close[i] - 1
    return ret, dd


def main():
    print(f"Scorecard validation — forward {N}-day underlying outcome by score bucket\n"
          "(LEAP/PMCC want high fwd-ret; CSP wants small fwd-dd; CASH should flag BAD fwd)")
    for under, vs in [("SPY", "^VIX"), ("QQQ", "^VXN")]:
        d = load(under)[["high", "low", "close"]]
        v = load(vs)["close"]
        df = d.join(v.rename("vix"), how="inner").dropna()
        f = scorecard.features(df, df["vix"]).dropna()
        sc = scorecard.scores(f)
        close = f["close"].values
        fret, fdd = fwd(close)

        print(f"\n========== {under} ({f.index.min().date()}->{f.index.max().date()}) ==========")
        for tool in TOOLS:
            s = sc[tool].values
            pr = np.nanpercentile(s, [50, 90, 99])
            print(f"\n{tool}  score p50={pr[0]:.0f} p90={pr[1]:.0f} p99={pr[2]:.0f} max={np.nanmax(s):.0f}")
            print(f"  bucket | days  fwd21-ret  %pos  fwd21-dd")
            for lo, hi in BINS:
                m = (s >= lo) & (s < hi) & ~np.isnan(fret)
                if m.sum() == 0:
                    print(f"  {lo:>2}-{hi-1:<2} | (none)")
                    continue
                print(f"  {lo:>2}-{hi-1:<2} | {m.sum():5d}  {np.nanmean(fret[m])*100:+6.2f}%  "
                      f"{(fret[m]>0).mean()*100:3.0f}%  {np.nanmean(fdd[m])*100:6.2f}%")


if __name__ == "__main__":
    main()
