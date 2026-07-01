"""Top-20 single-week gaps of the best NON-TECH sector vs SPY -- event-driven or noise?

The frequency-collapse (weekly 151% -> monthly 66%) shows a LOT of the oracle edge lives at the
weekly frequency, which slow regime persistence can't explain. So test the tail directly: the 20
weeks where the single best sector most out-gapped SPY, EXCLUDING weeks tech (XLK) won (tech's
dominance is the obvious story). Are those weeks recognizable EVENTS (oil shock, bank crisis,
Fed pivot, COVID) -- a catalyst layer a qualitative/news approach could see -- or scattered noise?

9 core SPDR + SPY, 1999-2026.
Run: python backtest/exp_gap_forensics.py
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exp_portfolio_oracle import SECTORS, weekly_returns


def run():
    rets, d0, d1 = weekly_returns()
    A = rets[SECTORS].to_numpy()
    spy = rets["SPY"].to_numpy()
    idx = rets.index
    n, k = A.shape

    win = A.argmax(1)
    win_ret = A[np.arange(n), win]
    gap = win_ret - spy

    # exclude weeks tech won
    xlk = SECTORS.index("XLK")
    mask = win != xlk
    cand = [(idx[t].date(), SECTORS[win[t]], win_ret[t], spy[t], gap[t]) for t in range(n) if mask[t]]
    cand.sort(key=lambda r: -r[4])
    top = cand[:20]

    print(f"\n=== top-20 weekly gaps: best NON-tech sector vs SPY -- {d0}->{d1} ===")
    print(f"{'#':>3}  {'week':12}{'sector':8}{'sec%':>8}{'SPY%':>8}{'gap%':>8}")
    for i, (dt, s, wr, sr, g) in enumerate(top, 1):
        print(f"{i:>3}  {str(dt):12}{s:8}{wr*100:>7.1f}{sr*100:>7.1f}{g*100:>7.1f}")

    # clustering
    from collections import Counter
    yrs = Counter(dt.year for dt, *_ in top)
    secs = Counter(s for _, s, *_ in top)
    print("\n  by year:  " + ", ".join(f"{y}x{c}" for y, c in sorted(yrs.items())))
    print("  by sector:" + ", ".join(f"{s}x{c}" for s, c in secs.most_common()))
    print("\n  Read: if these cluster on known crisis/shock weeks (2008 GFC, 2020 COVID, 2022 energy),")
    print("  the high-frequency tail is EVENT-driven (recognizable via news/catalysts -> a Phase-3")
    print("  information source), not pure noise. If scattered with no catalyst, it's noise.")


if __name__ == "__main__":
    run()
