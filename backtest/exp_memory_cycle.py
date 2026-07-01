"""Thin event-study base rate: buying an EXTENDED memory name -> what happens next?

Grounds the memory-supercycle thesis's "LATE cycle -> don't chase" call with a historical base
rate, from PRICE alone (no FNSPID needed -- the thin version, DESIGN §9 step 3). Memory is deeply
cyclical; buying it far above its 200SMA (as now: MU +165%) has historically been late-cycle.

For long-history memory names (MU 1984+, STX, WDC), bucket every day by distance-above-200SMA and
measure the forward 126d return conditional on the bucket, pooled. If the far-extended bucket has
poor/negative forward returns vs the unconditional, "don't chase extended memory" is the base rate.

Run: python backtest/exp_memory_cycle.py
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import load
from signals import sma

NAMES = ["MU", "STX", "WDC"]      # long-history memory / storage
FWD = 126
BUCKETS = [(-1, 0.0), (0.0, 0.5), (0.5, 1.0), (1.0, 99)]   # dist-above-200SMA bands


def run():
    pooled = {b: [] for b in range(len(BUCKETS))}
    allf = []
    print(f"\n=== memory extension base rate -- fwd-{FWD}d return by dist-above-200SMA ===")
    for s in NAMES:
        try:
            c = load(s, adjusted=True)["close"]
        except Exception as e:
            print(f"{s} SKIP {str(e)[:40]}")
            continue
        s200 = sma(c, 200)
        dist = (c / s200 - 1).to_numpy()
        fwd = (c.shift(-FWD) / c - 1).to_numpy()
        cur = float(dist[-1])
        for i in range(len(c)):
            d, f = dist[i], fwd[i]
            if d != d or f != f:
                continue
            allf.append(f)
            for bi, (lo, hi) in enumerate(BUCKETS):
                if lo <= d < hi:
                    pooled[bi].append(f)
                    break
        print(f"  {s}: current dist above 200SMA = {cur*100:+.0f}%")

    allf = np.array(allf)
    print(f"\n  unconditional fwd-{FWD}d: mean {allf.mean()*100:+.1f}%  median {np.median(allf)*100:+.1f}%  n={len(allf)}")
    print(f"  {'dist band':16}{'mean fwd%':>10}{'median%':>9}{'% positive':>11}{'n':>8}")
    for bi, (lo, hi) in enumerate(BUCKETS):
        arr = np.array(pooled[bi])
        if len(arr) < 30:
            continue
        label = f"{lo*100:+.0f}%..{'+inf' if hi>90 else f'{hi*100:+.0f}%'}"
        print(f"  {label:16}{arr.mean()*100:>9.1f}{np.median(arr)*100:>9.1f}{(arr>0).mean()*100:>10.0f}%{len(arr):>8}")
    print("\n  Read: if the far-extended band (+100%..) has clearly WORSE fwd return / lower %positive")
    print("  than the unconditional, 'buying extended memory = late-cycle, don't chase' is the base")
    print("  rate -> supports the thesis's LATE cycle_stage + tempered confidence. (Small-n, price-only,")
    print("  survivorship: these names survived; a cleaner version needs FNSPID + regime-conditioning.)")


if __name__ == "__main__":
    run()
