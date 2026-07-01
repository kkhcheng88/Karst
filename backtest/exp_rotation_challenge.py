"""Challenge: is the 7% -> 155% -> 327% gap a MISSED FACTOR, or a high-frequency mirage?

Two tests:
 (1) ORACLE top-3 CAGR vs HOLDING frequency (rebalance/hold every F weeks, perfect foresight
     of the next F-week block). If the ceiling COLLAPSES as F grows, the big number is mostly
     the value of perfect WEEKLY switching -- a noise/compounding artifact, not a persistent
     systematic factor you could ever design toward.
 (2) BEST-EFFORT causal: dual momentum (relative top-3 + absolute filter -> BOND fallback when
     a sector's own momentum is weak), monthly. This is the best-documented tactical-allocation
     recipe (Antonacci). If even this doesn't beat SPY/EW net of cost, the "missed factor" isn't
     a capturable quant signal at the sector level.

9 core SPDR + IEF (7-10y Treasuries) as the defensive asset. Total-return, weekly, 1999-2026,
5bp/unit turnover, look-ahead-safe for the causal test.

Run: python backtest/exp_rotation_challenge.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import load
from metrics import ann_sharpe, cagr, max_drawdown

SECTORS = ["XLK", "XLY", "XLF", "XLV", "XLI", "XLP", "XLU", "XLB", "XLE"]
COST_BPS = 5.0
NTOP = 3


def load_weekly(syms):
    cols = {}
    for s in syms:
        cols[s] = load(s, adjusted=True)["close"].resample("W-FRI").last()
    return pd.DataFrame(cols).dropna()


def block_returns(R, F):
    """R: (n x k) weekly simple returns. Return (m x k) F-week block simple returns."""
    n, k = R.shape
    G = np.log1p(R)
    blocks = []
    for s in range(0, n - F + 1, F):
        blocks.append(np.expm1(G[s:s + F].sum(axis=0)))
    return np.array(blocks)


def cagr_from_block(port_block, F):
    eq = np.cumprod(1 + port_block)
    years = len(port_block) * F / 52.0
    return eq[-1] ** (1 / years) - 1 if years > 0 else np.nan


def run():
    df = load_weekly(SECTORS + ["SPY", "IEF"])
    R = df.pct_change().dropna()
    sec = R[SECTORS].to_numpy()
    spy = R["SPY"].to_numpy()
    ief = R["IEF"].to_numpy()
    n, k = sec.shape
    d0, d1 = str(df.index[1].date()), str(df.index[-1].date())
    print(f"\n=== rotation challenge -- {d0}->{d1}, {n} weeks (IEF starts {str(df.index[0].date())}) ===\n")

    # ---- (1) oracle top-3 vs holding frequency ----
    print("(1) ORACLE top-3 CAGR vs HOLDING period (perfect foresight of each block):")
    spy_cagr = cagr(np.cumprod(1 + spy), 52)
    print(f"    SPY buy-hold = {spy_cagr*100:.1f}%/yr   (reference)")
    for F, label in [(1, "weekly"), (4, "monthly"), (13, "quarterly"), (52, "yearly")]:
        B = block_returns(sec, F)                       # (m x k) block returns
        top3 = np.sort(B, axis=1)[:, -NTOP:].mean(axis=1)   # perfect top-3 each block
        cg = cagr_from_block(top3, F)
        print(f"    hold {label:9} (F={F:2}): oracle top-3 = {cg*100:8.1f}%/yr")
    print("    -> if this collapses toward SPY as the holding period grows, the huge weekly")
    print("       number is a high-frequency perfect-switching artifact, NOT a missed factor.\n")

    # ---- (2) best-effort causal: dual momentum + bond fallback, monthly ----
    P = np.cumprod(1 + sec, axis=0)
    Pief = np.cumprod(1 + ief)
    K, FREQ = 26, 4
    mom = np.full((n, k), np.nan)
    mom[K + 1:] = P[K:-1] / P[:-K - 1] - 1.0
    mom_ief = np.full(n, np.nan)
    mom_ief[K + 1:] = Pief[K:-1] / Pief[:-K - 1] - 1.0

    W_sec = np.zeros((n, k))
    w_ief = np.zeros(n)
    last_sec, last_ief, start = None, 0.0, K + 1
    for t in range(start, n):
        if (t - start) % FREQ == 0 or last_sec is None:
            m = mom[t]
            order = np.argsort(-np.nan_to_num(m, nan=-9))[:NTOP]
            ws = np.zeros(k)
            wi = 0.0
            for i in order:
                i = int(i)
                if m[i] > max(mom_ief[t], 0.0):          # absolute filter: beat bonds AND >0
                    ws[i] = 1.0 / NTOP
                else:
                    wi += 1.0 / NTOP                     # else that slot -> bonds (dual momentum)
            last_sec, last_ief = ws, wi
        W_sec[t], w_ief[t] = last_sec, last_ief

    r = (W_sec * sec).sum(axis=1) + w_ief * ief
    W_full = np.column_stack([W_sec, w_ief])
    turn = np.abs(np.diff(W_full, axis=0, prepend=np.zeros((1, k + 1)))).sum(axis=1)
    rnet = r - turn * COST_BPS / 1e4

    Wew = np.full((n, k), 1.0 / k)
    rew = (Wew * sec).sum(axis=1)

    def line(name, x):
        eq = np.cumprod(1 + np.asarray(x))
        return f"    {name:28}{cagr(eq,52)*100:6.1f}%  Sharpe {ann_sharpe(x,52):5.2f}  MaxDD {max_drawdown(eq)*100:6.1f}%"

    print("(2) BEST-EFFORT causal (dual momentum 26w + IEF bond fallback, monthly, net of cost):")
    print(line("SPY buy-hold", spy))
    print(line("EW 9 sectors", rew))
    print(line("DualMom + bond fallback", rnet))
    print(f"    avg bond weight {w_ief.mean()*100:.0f}%, turnover/yr {turn.mean()*52:.1f}")
    print("    -> if even the best-documented TAA recipe doesn't beat SPY/EW, the missed 'factor'")
    print("       is not a capturable sector-level quant signal.")


if __name__ == "__main__":
    run()
