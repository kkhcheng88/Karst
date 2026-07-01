"""Reverse-engineer the weekly oracle: WHICH sectors, WHEN, and WHAT was happening.

Instead of forward-testing signals (exhausted), dissect the perfect-foresight weekly oracle:
 (1) how often each sector is the weekly winner (pick distribution),
 (2) each sector's contribution to the oracle's cumulative alpha vs SPY,
 (3) BY YEAR: oracle top-3 vs SPY excess -- is the edge spread out or concentrated in a few
     periods? and which sector dominated each year,
so we can go check WHAT HAPPENED in the high-excess periods. If the oracle alpha is concentrated
in a few recognizable regime/event windows (energy 2022, defensives 2008, ...), a qualitative /
macro-aware approach (Phase 3) could capture chunks of it even though WEEKLY ranking IC ~ 0.

9 core SPDR (long history 1999-2026: dotcom/GFC/COVID/2022). XLC/XLRE excluded (start 2018/2015).
Run: python backtest/exp_oracle_forensics.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exp_portfolio_oracle import SECTORS, weekly_returns

NTOP = 3


def run():
    rets, d0, d1 = weekly_returns()
    sec = rets[SECTORS]
    spy = rets["SPY"]
    n, k = sec.shape
    A = sec.to_numpy()
    print(f"\n=== ORACLE FORENSICS (top-{NTOP} weekly) -- 9 sectors, {d0}->{d1}, {n} weeks ===")

    # weekly oracle top-3: which sectors, what return
    order = np.argsort(-A, axis=1)
    top_idx = order[:, :NTOP]
    top1_idx = order[:, 0]
    oracle_r = np.array([A[t, top_idx[t]].mean() for t in range(n)])
    contrib = np.zeros(k)                       # sum of each sector's contribution to oracle return
    for t in range(n):
        for j in top_idx[t]:
            contrib[j] += A[t, j] / NTOP

    # (1) pick frequency
    picks1 = np.bincount(top1_idx, minlength=k)
    picks3 = np.bincount(top_idx.reshape(-1), minlength=k)
    print("\n(1) pick frequency + alpha attribution:")
    print(f"    {'sector':8}{'top1 %':>8}{'top3 %':>8}{'contrib/yr':>11}")
    rowsF = sorted(range(k), key=lambda j: -contrib[j])
    for j in rowsF:
        print(f"    {SECTORS[j]:8}{picks1[j]/n*100:7.1f}%{picks3[j]/n*100:7.1f}%{contrib[j]/(n/52)*100:10.1f}%")

    # (3) by year
    idx = rets.index
    yr = idx.year
    print("\n(3) BY YEAR -- oracle top-3 vs SPY (annual return), excess, dominant sector:")
    print(f"    {'year':6}{'oracle3':>9}{'SPY':>8}{'excess':>9}   top sector (that year)")
    years = sorted(set(yr))
    ann = []
    for y in years:
        m = yr == y
        o = np.prod(1 + oracle_r[m]) - 1
        s = np.prod(1 + spy[m].to_numpy()) - 1
        dom = SECTORS[np.bincount(top1_idx[m], minlength=k).argmax()]
        ann.append((y, o, s, o - s, dom))
    for y, o, s, e, dom in ann:
        bar = "#" * min(int(e * 20), 40) if e > 0 else ""
        print(f"    {y:6}{o*100:8.0f}%{s*100:7.0f}%{e*100:8.0f}%   {dom:7} {bar}")

    # concentration: how much of total excess is in the top-5 years
    exc = np.array([e for _, _, _, e, _ in ann])
    tot = exc.sum()
    top5 = np.sort(exc)[::-1][:5].sum()
    print(f"\n  total oracle-vs-SPY excess (sum of annual): {tot*100:.0f}%; top-5 years = {top5/tot*100:.0f}% of it")
    print("  -> if the excess is concentrated in a few years, check what regime/events drove them")
    print("     (dominant sector per year is the clue). Weekly IC~0, but regime positioning may be")
    print("     recognizable -> a job for macro/qualitative (Phase 3), not weekly quant ranking.")


if __name__ == "__main__":
    run()
