"""Train-broad, trade-narrow: learn the ranking on 110 stocks, apply it to the 11 tradeable sectors.

The 9/11-sector cross-section is too thin for ML to LEARN on (direct sector ML gave OOS IC ~0).
But the broad 110-stock ML found a real (small) OOS signal. The user's actual tradeable universe
is the 11 XL_ sector ETFs (+ SPY/QQQ), and 1st-3rd best is enough. So: TRAIN the GBDT where there
is breadth (110 stocks), then SCORE & RANK the 11 sector ETFs with the learned function, and
measure OOS forward IC + a top-3 sector portfolio. Same Alpha360-style features, strict walk-forward.

Run: python backtest/exp_ml_broad2sectors.py
"""
from __future__ import annotations

import contextlib
import io
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf

from data import load
from metrics import ann_sharpe, cagr, max_drawdown

SECTOR_ETFS = ["XLK", "XLC", "XLY", "XLI", "XLF", "XLB", "XLE", "XLV", "XLP", "XLU", "XLRE"]
L, MIN_TRAIN, BLOCK = 26, 300, 52
COST_BPS, NTOP = 5.0, 3


def stock_universe():
    u = set()
    for etf in SECTOR_ETFS:
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                th = yf.Ticker(etf).funds_data.top_holdings
            for sym in th.index:
                s = str(sym)
                if "." not in s:
                    u.add(s)
        except Exception:
            continue
    return sorted(u)


def panel(syms, cal):
    keep, C, O, H, Lo, V = [], [], [], [], [], []
    for s in syms:
        try:
            d = load(s, adjusted=True, min_rows=200)
        except Exception:
            continue
        c = d["close"].resample("W-FRI").last().reindex(cal)
        C.append(c); O.append(d["open"].resample("W-FRI").first().reindex(cal))
        H.append(d["high"].resample("W-FRI").max().reindex(cal))
        Lo.append(d["low"].resample("W-FRI").min().reindex(cal))
        V.append(d["volume"].resample("W-FRI").sum().reindex(cal))
        keep.append(s)
    A = lambda xs: np.column_stack(xs)
    return keep, A(C), A(O), A(H), A(Lo), A(V)


def samples(C, O, H, Lo, V):
    VW = (H + Lo + C) / 3.0
    T, S = C.shape
    ret = np.full((T, S), np.nan)
    ret[:-1] = C[1:] / C[:-1] - 1.0
    Xs, ys, ts, ss = [], [], [], []
    for t in range(L, T - 1):
        for j in range(S):
            c0 = C[t, j]
            v0 = np.nanmean(V[t - L + 1:t + 1, j])
            if not (c0 > 0) or not (v0 > 0) or np.isnan(ret[t, j]):
                continue
            w = slice(t - L + 1, t + 1)
            feat = np.concatenate([C[w, j] / c0, O[w, j] / c0, H[w, j] / c0,
                                   Lo[w, j] / c0, V[w, j] / v0, VW[w, j] / c0])
            if np.isnan(feat).any():
                continue
            Xs.append(feat); ys.append(ret[t, j]); ts.append(t); ss.append(j)
    return np.array(Xs), np.array(ys), np.array(ts, int), np.array(ss, int), ret


def run():
    cal = load("SPY", adjusted=True)["close"].resample("W-FRI").last().index
    T = len(cal)
    print("\n=== train-broad (110 stocks) -> trade-narrow (11 XL_ sectors), OOS walk-forward ===")
    stk = stock_universe()
    _, Cs, Os, Hs, Ls, Vs = panel(stk, cal)
    Xtr, ytr, tstr, _, _ = samples(Cs, Os, Hs, Ls, Vs)
    _, Cx, Ox, Hx, Lx, Vx = panel(SECTOR_ETFS, cal)
    Xse, yse, tse, sse, rsec = samples(Cx, Ox, Hx, Lx, Vx)
    Ssec = Cx.shape[1]
    print(f"train: {len(ytr)} stock samples; eval: {Ssec} sectors, {len(yse)} samples, {cal[0].date()}->{cal[-1].date()}\n")

    pred = np.full((T, Ssec), np.nan)
    for start in range(MIN_TRAIN, T - 1, BLOCK):
        tr = tstr < start
        te = (tse >= start) & (tse < start + BLOCK)
        if tr.sum() < 2000 or te.sum() == 0:
            continue
        m = HistGradientBoostingRegressor(max_depth=4, max_iter=300, learning_rate=0.05,
                                          l2_regularization=1.0, min_samples_leaf=100)
        m.fit(Xtr[tr], ytr[tr])
        p = m.predict(Xse[te])
        ii = np.where(te)[0]
        pred[tse[ii], sse[ii]] = p

    ics, pr, PW, ewr = [], [], [], []
    for t in range(MIN_TRAIN, T - 1):
        pv, rv = pred[t], rsec[t]
        m = ~(np.isnan(pv) | np.isnan(rv))
        if m.sum() >= 6:
            rho = spearmanr(pv[m], rv[m]).correlation
            if rho == rho:
                ics.append(rho)
            order = np.argsort(-np.where(np.isnan(pv), -9, pv))[:NTOP]
            w = np.zeros(Ssec)
            for i in order:
                w[i] = 1.0 / NTOP
            PW.append(w); pr.append(np.nanmean([rv[i] for i in order])); ewr.append(np.nanmean(rv[m]))
    ics = np.array(ics)
    t_ic = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics)))
    print(f"OOS forward IC on the 11 sectors: mean {ics.mean():.3f}  t {t_ic:.1f}  (n={len(ics)} wks)   [bar >=0.05]")

    W, r = np.array(PW), np.array(pr)
    turn = np.abs(np.diff(W, axis=0, prepend=np.zeros((1, Ssec)))).sum(1)
    rnet = r - turn * COST_BPS / 1e4
    spy = load("SPY", adjusted=True)["close"].resample("W-FRI").last().pct_change().dropna().to_numpy()

    def cg(x):
        x = np.asarray(x); x = x[~np.isnan(x)]
        return cagr(np.cumprod(1 + x), 52)
    print(f"\nOOS top-{NTOP} sector portfolio (net): CAGR {cg(rnet)*100:.1f}%  Sharpe {ann_sharpe(rnet,52):.2f}  "
          f"MaxDD {max_drawdown(np.cumprod(1+rnet[~np.isnan(rnet)]))*100:.1f}%")
    print(f"  vs SPY {cg(spy)*100:.1f}%, sector-EW {cg(ewr)*100:.1f}%")
    print("\n  Open read: does the signal LEARNED on 110 stocks transfer to RANK the 11 tradeable")
    print("  sectors (OOS IC>0, top-3 beats SPY/EW net)? If yes, you trade the ETFs but borrow breadth.")


if __name__ == "__main__":
    run()
