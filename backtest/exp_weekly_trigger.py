"""What FACTOR triggers the profitable weekly sector switch? (answering the challenge properly)

Correction: "the oracle collapses with holding period" proves the opportunity is HIGH-FREQUENCY,
NOT that it is unpredictable. I only tested momentum. The natural high-frequency factor -- SHORT-
TERM REVERSAL (weekly mean-reversion: last week's loser bounces) -- was untested, and momentum
buys the opposite (last week's winner). So test what actually predicts next-week sector returns.

Method: Information Coefficient (IC) = cross-sectional Spearman rank-corr between a feature known
at week t and the 9 sectors' return in week t+1, averaged over all weeks (+ t-stat). Positive IC
= the feature ranks sectors in the right order for next week (a capturable trigger). Features:
  REV-1w   : -last week return         (reversal: buy the loser)
  REV-4w   : -last 4-week return
  MOM-26w  : trailing 26-week return   (momentum, for contrast)
  RSI2-os  : 100 - weekly RSI-2        (oversold)
  LOW-VOL  : -trailing 13-week vol
Then a causal REVERSAL rotation (buy bottom-3 by last-week return, weekly) net of cost.

Run: python backtest/exp_weekly_trigger.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exp_portfolio_oracle import SECTORS, weekly_returns
from metrics import ann_sharpe, cagr, max_drawdown
from signals import rsi

COST_BPS = 5.0
NTOP = 3


def ic(feat, fwd):
    """mean cross-sectional Spearman IC of feat[t] vs fwd[t] (=return[t+1]); + t-stat, n."""
    vals = []
    for t in range(len(feat)):
        f, r = feat[t], fwd[t]
        if np.isnan(f).any() or np.isnan(r).any():
            continue
        rho = spearmanr(f, r).correlation
        if rho == rho:
            vals.append(rho)
    v = np.array(vals)
    return v.mean(), v.mean() / (v.std(ddof=1) / np.sqrt(len(v))), len(v)


def run():
    rets, d0, d1 = weekly_returns()
    sec = rets[SECTORS].to_numpy()
    spy = rets["SPY"].to_numpy()
    n, k = sec.shape
    P = np.cumprod(1 + sec, axis=0)
    fwd = np.roll(sec, -1, axis=0)          # fwd[t] = return[t+1]
    fwd[-1] = np.nan

    mom26 = np.full((n, k), np.nan)
    mom26[26:] = P[26:] / P[:-26] - 1.0
    rev4 = np.full((n, k), np.nan)
    rev4[4:] = -(P[4:] / P[:-4] - 1.0)
    vol13 = pd.DataFrame(sec).rolling(13).std().to_numpy()
    rsi2 = np.column_stack([rsi(pd.Series(P[:, j]), 2).to_numpy() for j in range(k)])

    features = {
        "REV-1w  (buy loser)": -sec,
        "REV-4w": rev4,
        "MOM-26w (buy winner)": mom26,
        "RSI2-oversold": 100 - rsi2,
        "LOW-VOL": -vol13,
    }
    print(f"\n=== weekly sector trigger: IC vs next-week return -- {d0}->{d1}, {n} weeks ===")
    print(f"{'feature':22}{'mean IC':>9}{'t-stat':>8}{'n':>7}   (|t|>2 ~ real; +IC = capturable order)")
    print("-" * 60)
    for name, f in features.items():
        m, t, nn = ic(f, fwd)
        print(f"{name:22}{m:>9.3f}{t:>8.1f}{nn:>7}")

    # causal reversal rotation: buy bottom-3 by last-week return, weekly
    W = np.zeros((n, k))
    for t in range(1, n):
        losers = np.argsort(sec[t - 1])[:NTOP]     # smallest last-week returns
        for i in losers:
            W[t, int(i)] = 1.0 / NTOP
    r = (W * sec).sum(axis=1)
    turn = np.abs(np.diff(W, axis=0, prepend=np.zeros((1, k)))).sum(axis=1)
    rnet = r - turn * COST_BPS / 1e4
    Wew = np.full((n, k), 1.0 / k)
    rew = (Wew * sec).sum(axis=1)

    def line(name, x):
        eq = np.cumprod(1 + np.asarray(x))
        return f"    {name:26}{cagr(eq,52)*100:6.1f}%  Sharpe {ann_sharpe(x,52):5.2f}  MaxDD {max_drawdown(eq)*100:6.1f}%"

    print("\ncausal REVERSAL rotation (buy bottom-3 by last-week return, weekly, net of cost):")
    print(line("SPY", spy))
    print(line("EW 9 sectors", rew))
    print(line("REVERSAL top-3 (gross)", r))
    print(line("REVERSAL top-3 (net)", rnet))
    print(f"    turnover/yr {turn.mean()*52:.1f}")
    print("\n  Read: if a feature has a real +IC AND the causal reversal beats SPY/EW net of cost,")
    print("  then there WAS a capturable trigger (I was wrong to call it a pure mirage). If the IC")
    print("  is ~0 / the net strategy still loses, the weekly switches are genuinely unpredictable.")


if __name__ == "__main__":
    run()
