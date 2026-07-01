"""Reward-vs-skill curve: how much ranking SKILL do you need to cash in the dispersion?

The user's (correct) point: because weekly sector dispersion is enormous, you don't need to
pick THE best -- hitting the 2nd/3rd best is still a huge reward. So the real question isn't
"can we be perfect" but "can we rank sectors even slightly better than random". Two views:

 (A) Payoff by EXACT rank k=1..9 (perfect foresight of the k-th best each week) -- shows the
     reward gradient (is 2nd/3rd still huge?).
 (B) Reward vs SKILL: degrade the perfect ranking with noise to a target IC (Spearman corr with
     next-week returns), pick top-3 by the noisy prediction, measure net CAGR. Sweep IC from 0
     (random=EW) to 1 (oracle). Then mark our MEASURED real IC (~0.01 from exp_weekly_trigger).

This answers honestly: the reward IS hugely convex in skill (user is right); the problem is that
every quant feature we tested ranks sectors with ~0 IC. Even modest IC (0.1) would be transformative
-> justifies hunting for a real ranking signal (incl. qualitative / Phase 3), which is the point.

9 core SPDR, total-return, weekly, 1999-2026, 5bp/unit turnover.
Run: python backtest/exp_skill_curve.py
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exp_portfolio_oracle import SECTORS, weekly_returns
from metrics import ann_sharpe, cagr, max_drawdown

COST_BPS = 5.0
NTOP = 3


def _zscore(x):
    return (x - x.mean(axis=1, keepdims=True)) / (x.std(axis=1, keepdims=True) + 1e-9)


def topk_from_scores(scores, sec):
    n, k = sec.shape
    W = np.zeros((n, k))
    r = np.zeros(n)
    for t in range(n):
        picks = np.argsort(-scores[t])[:NTOP]
        for i in picks:
            W[t, int(i)] = 1.0 / NTOP
            r[t] += sec[t, int(i)] / NTOP
    turn = np.abs(np.diff(W, axis=0, prepend=np.zeros((1, k)))).sum(axis=1)
    return r, r - turn * COST_BPS / 1e4


def run():
    rets, d0, d1 = weekly_returns()
    sec = rets[SECTORS].to_numpy()
    spy = rets["SPY"].to_numpy()
    n, k = sec.shape
    print(f"\n=== reward vs ranking SKILL -- {len(SECTORS)} sectors, {d0}->{d1}, {n} weeks ===")
    print(f"SPY {cagr(np.cumprod(1+spy),52)*100:.1f}%/yr, EW {cagr(np.cumprod(1+sec.mean(1)),52)*100:.1f}%/yr\n")

    # (A) payoff by exact rank
    print("(A) perfect foresight of the EXACT k-th best sector each week (hold 1 week):")
    srt = np.sort(sec, axis=1)[:, ::-1]     # each row sorted high->low
    for kk in range(k):
        cg = cagr(np.cumprod(1 + srt[:, kk]), 52)
        print(f"    rank {kk+1} ({'best' if kk==0 else 'worst' if kk==k-1 else ' '}): {cg*100:8.1f}%/yr")

    # (B) reward vs skill: noisy prediction with target IC
    ztrue = _zscore(sec)                    # higher = higher realized next return (this week)
    rng = np.random.default_rng(0)
    print("\n(B) reward vs SKILL -- top-3 by a prediction with target IC (avg of 40 noise draws):")
    print(f"    {'target IC':>10}{'realized IC':>12}{'CAGR gross':>12}{'CAGR net':>10}")
    for rho in [0.0, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 1.00]:
        gross_l, net_l, ic_l = [], [], []
        draws = 1 if rho == 1.0 else 40
        for _ in range(draws):
            noise = rng.standard_normal((n, k))
            pred = rho * ztrue + np.sqrt(max(1 - rho * rho, 0)) * noise
            # realized IC (avg per-week Spearman ~ Pearson on z)
            ic = np.mean([np.corrcoef(pred[t], sec[t])[0, 1] for t in range(0, n, 5)])
            g, nt = topk_from_scores(pred, sec)
            gross_l.append(cagr(np.cumprod(1 + g), 52))
            net_l.append(cagr(np.cumprod(1 + nt), 52))
            ic_l.append(ic)
        print(f"    {rho:>10.2f}{np.mean(ic_l):>12.3f}{np.mean(gross_l)*100:>11.1f}%{np.mean(net_l)*100:>9.1f}%")

    print("\n  Our MEASURED real IC (momentum/reversal/rsi/vol, exp_weekly_trigger) ~ 0.01 -> lands at")
    print("  the top row (~EW, no edge). The curve is steeply convex: IC 0.1 would already ~double")
    print("  SPY, IC 0.3+ is transformative. So the reward for ranking skill IS huge (user is right);")
    print("  the unsolved problem is that no quant feature we tested ranks sectors better than ~random.")
    print("  That is exactly where a qualitative edge (news/catalyst/fundamentals -> Phase 3) could pay,")
    print("  IF it delivers even IC ~0.1 -- a falsifiable, forward-trackable bet.")


if __name__ == "__main__":
    run()
