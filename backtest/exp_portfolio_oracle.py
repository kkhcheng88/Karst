"""Portfolio-composition CEILING — how much can WEEKLY sector rotation earn, at best?

Corrects the single-asset framing error: the question isn't "does a signal beat B&H this
asset", it's "given a FINITE pool, where should it go this week" (composition). Before
building a causal rotation signal, bound the OPPORTUNITY with an ORACLE (perfect foresight):
each week allocate by NEXT week's realized returns. Gap(oracle - SPY) = the max edge weekly
sector rotation could ever add. If small, stop; if large, ask how much a real signal captures.

Look-ahead is INTENTIONAL here (it's the ceiling). Net-of-cost matters: weekly full rotation
has big turnover, so even perfect foresight bleeds to cost -- shown gross AND net.

Universe: 9 core SPDR sectors with long history (XLC/XLRE excluded -- too young), total-return,
weekly (W-FRI), common window (~1999-2026: dotcom/GFC/2018/2020/2022).

Run: python backtest/exp_portfolio_oracle.py
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
COST_BPS = 5.0   # per unit turnover, one-way (sector ETFs are liquid; conservative for weekly)


def weekly_returns():
    cols = {}
    for s in SECTORS + ["SPY"]:
        c = load(s, adjusted=True)["close"].resample("W-FRI").last()
        cols[s] = c
    df = pd.DataFrame(cols).dropna()
    return df.pct_change().dropna(), str(df.index[0].date()), str(df.index[-1].date())


def stats(r, W=None):
    r = np.asarray(r, float)
    eq = np.cumprod(1 + r)
    out = {"CAGR": cagr(eq, 52), "Sharpe": ann_sharpe(r, 52), "MaxDD": max_drawdown(eq)}
    if W is not None:
        turn = np.abs(np.diff(W, axis=0, prepend=np.zeros((1, W.shape[1])))).sum(axis=1)
        rn = r - turn * COST_BPS / 1e4
        out["CAGR_net"] = cagr(np.cumprod(1 + rn), 52)
        out["Sharpe_net"] = ann_sharpe(rn, 52)
        out["turn/yr"] = float(turn.mean() * 52)
    return out


def onehot(idx, k):
    W = np.zeros((len(idx), k))
    W[np.arange(len(idx)), idx] = 1.0
    return W


def topk_weights(sec, k_top, cash_if_neg=False):
    n, k = sec.shape
    W = np.zeros((n, k))
    r = np.zeros(n)
    order = np.argsort(-sec, axis=1)[:, :k_top]
    for t in range(n):
        picks = [int(i) for i in order[t]]
        if cash_if_neg:
            picks = [i for i in picks if sec[t, i] > 0]
        w = 1.0 / k_top                          # cash-if-neg leaves the rest in cash (0)
        for i in picks:
            W[t, i] = w
            r[t] += sec[t, i] * w
    return r, W


def run():
    rets, d0, d1 = weekly_returns()
    sec = rets[SECTORS].to_numpy()
    spy = rets["SPY"].to_numpy()
    n, k = sec.shape
    print(f"\n=== WEEKLY sector-rotation CEILING (oracle) -- {len(SECTORS)} sectors, {d0}->{d1}, {n} weeks ===")
    print(f"cost {COST_BPS}bp/unit turnover, ann=52\n")

    # baselines
    Wspy = np.zeros((n, k))                       # SPY held separately; turnover ~0
    Wew = np.full((n, k), 1.0 / k)
    rew = (sec * Wew).sum(1)

    # oracles
    idx1 = sec.argmax(1)
    r1, W1 = sec[np.arange(n), idx1], onehot(idx1, k)
    r3, W3 = topk_weights(sec, 3)
    r3c, W3c = topk_weights(sec, 3, cash_if_neg=True)
    worst = sec.min(1)

    rows = [
        ("SPY (do nothing)", stats(spy)),
        ("EW 9 sectors", stats(rew, Wew)),
        ("ORACLE top-1", stats(r1, W1)),
        ("ORACLE top-3", stats(r3, W3)),
        ("ORACLE top-3 +cash", stats(r3c, W3c)),
        ("WORST top-1 (floor)", stats(worst, onehot(sec.argmin(1), k))),
    ]
    hdr = f"{'strategy':22}{'CAGR':>7}{'Sharpe':>7}{'MaxDD':>8} | {'CAGRnet':>8}{'Shnet':>7}{'turn/yr':>8}"
    print(hdr)
    print("-" * len(hdr))
    spy_cagr = rows[0][1]["CAGR"]
    for name, s in rows:
        net = f"{s.get('CAGR_net', float('nan'))*100:7.1f}%{s.get('Sharpe_net', float('nan')):7.2f}{s.get('turn/yr', float('nan')):8.1f}" if "CAGR_net" in s else f"{'':>23}"
        print(f"{name:22}{s['CAGR']*100:6.1f}%{s['Sharpe']:7.2f}{s['MaxDD']*100:7.1f}% | {net}")

    print(f"\n  ceiling gap vs SPY (net): "
          f"top-1 {(rows[2][1].get('CAGR_net',np.nan)-spy_cagr)*100:+.1f}pp/yr, "
          f"top-3 {(rows[3][1].get('CAGR_net',np.nan)-spy_cagr)*100:+.1f}pp, "
          f"top-3+cash {(rows[4][1].get('CAGR_net',np.nan)-spy_cagr)*100:+.1f}pp")
    print("  Read: that net gap is the MOST weekly sector rotation could add. A real (causal) signal")
    print("  captures only a fraction. If the net ceiling is modest, rotation isn't where the edge is.")


if __name__ == "__main__":
    run()
