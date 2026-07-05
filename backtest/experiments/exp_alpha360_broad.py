"""Alpha360-style ML on a BROAD stock universe -- the fair-breadth test (per the user).

The 11-sector cross-section is too narrow for ML. Here the universe = ~110 US stocks (top-10
holdings of all 11 SPDR sectors), so each week's cross-section is ~100 names -- real breadth for
the model to learn cross-sectional ranking, and far less overfit-prone than 9 sectors. Same
Alpha360-style raw normalized OHLCV features, GBDT, STRICT walk-forward OOS. Explore openly; let
the out-of-sample IC decide.

Features: last L=26 weeks of [close,open,high,low,volume,vwap] normalized -> 156 per (stock,week).
Target: next-week return. OOS: expanding train, 52w blocks. Metric: OOS cross-sectional forward IC
(across the ~100 stocks each week) + a top-10 long portfolio net of cost vs SPY / universe-EW.

Run: python backtest/experiments/exp_alpha360_broad.py
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf

from data import load
from metrics import ann_sharpe, cagr, max_drawdown

SECTOR_ETFS = ["XLK", "XLC", "XLY", "XLI", "XLF", "XLB", "XLE", "XLV", "XLP", "XLU", "XLRE"]
L, MIN_TRAIN, BLOCK = 26, 300, 52
COST_BPS, NTOP = 5.0, 10


def universe():
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


def weekly(s, cal):
    d = load(s, adjusted=True, min_rows=200)
    w = pd.DataFrame({
        "o": d["open"].resample("W-FRI").first(), "h": d["high"].resample("W-FRI").max(),
        "l": d["low"].resample("W-FRI").min(), "c": d["close"].resample("W-FRI").last(),
        "v": d["volume"].resample("W-FRI").sum()})
    return w.reindex(cal)


def run():
    syms = universe()
    cal = load("SPY", adjusted=True)["close"].resample("W-FRI").last().index
    print(f"\n=== Alpha360-style GBDT, BROAD universe -- {len(syms)} US stocks, weekly ===")
    frames, kept = {}, []
    for s in syms:
        try:
            frames[s] = weekly(s, cal)
            kept.append(s)
        except Exception:
            continue
    T = len(cal)
    S = len(kept)
    C = np.column_stack([frames[s]["c"] for s in kept])
    O = np.column_stack([frames[s]["o"] for s in kept])
    H = np.column_stack([frames[s]["h"] for s in kept])
    Lo = np.column_stack([frames[s]["l"] for s in kept])
    V = np.column_stack([frames[s]["v"] for s in kept])
    VW = (H + Lo + C) / 3.0
    ret = np.full((T, S), np.nan)
    ret[:-1] = C[1:] / C[:-1] - 1.0

    Xs, ys, ts, ss = [], [], [], []
    for t in range(L, T - 1):
        for j in range(S):
            c0 = C[t, j]
            vw = V[t - L + 1:t + 1, j]
            v0 = np.nanmean(vw)
            if not (c0 > 0) or not (v0 > 0) or np.isnan(ret[t, j]):
                continue
            w = slice(t - L + 1, t + 1)
            feat = np.concatenate([C[w, j] / c0, O[w, j] / c0, H[w, j] / c0,
                                   Lo[w, j] / c0, V[w, j] / v0, VW[w, j] / c0])
            if np.isnan(feat).any():
                continue
            Xs.append(feat); ys.append(ret[t, j]); ts.append(t); ss.append(j)
    X, y, ts, ss = np.array(Xs), np.array(ys), np.array(ts, int), np.array(ss, int)
    print(f"{S} stocks kept, {len(y)} samples, {X.shape[1]} features, {cal[0].date()}->{cal[-1].date()}\n")

    pred = np.full((T, S), np.nan)
    for start in range(MIN_TRAIN, T - 1, BLOCK):
        tr = ts < start
        te = (ts >= start) & (ts < start + BLOCK)
        if tr.sum() < 2000 or te.sum() == 0:
            continue
        m = HistGradientBoostingRegressor(max_depth=4, max_iter=300, learning_rate=0.05,
                                          l2_regularization=1.0, min_samples_leaf=100)
        m.fit(X[tr], y[tr])
        p = m.predict(X[te])
        ii = np.where(te)[0]
        pred[ts[ii], ss[ii]] = p

    ics, port_r, port_W, ew_r = [], [], [], []
    for t in range(MIN_TRAIN, T - 1):
        pv, rv = pred[t], ret[t]
        m = ~(np.isnan(pv) | np.isnan(rv))
        if m.sum() >= 20:
            rho = spearmanr(pv[m], rv[m]).correlation
            if rho == rho:
                ics.append(rho)
            order = np.argsort(-np.where(np.isnan(pv), -9, pv))[:NTOP]
            w = np.zeros(S)
            for i in order:
                w[i] = 1.0 / NTOP
            port_W.append(w)
            port_r.append(np.nanmean([rv[i] for i in order]))
            ew_r.append(np.nanmean(rv[m]))
    ics = np.array(ics)
    t_ic = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics)))
    print(f"OOS forward IC (cross-section ~{S} stocks): mean {ics.mean():.3f}  t {t_ic:.1f}  "
          f"(n={len(ics)} wks)   [bar >=0.05]")

    W = np.array(port_W)
    r = np.array(port_r)
    turn = np.abs(np.diff(W, axis=0, prepend=np.zeros((1, S)))).sum(1)
    rnet = r - turn * COST_BPS / 1e4
    spy = load("SPY", adjusted=True)["close"].resample("W-FRI").last().pct_change().dropna().to_numpy()

    def cg(x):
        x = np.asarray(x); x = x[~np.isnan(x)]
        return cagr(np.cumprod(1 + x), 52)
    print(f"\nOOS top-{NTOP}-by-model portfolio (net): CAGR {cg(rnet)*100:.1f}%  Sharpe {ann_sharpe(rnet,52):.2f}  "
          f"MaxDD {max_drawdown(np.cumprod(1+rnet[~np.isnan(rnet)]))*100:.1f}%")
    print(f"  vs SPY {cg(spy)*100:.1f}% (same window ~), universe-EW {cg(ew_r)*100:.1f}%")
    print("  Open read: if OOS IC clears ~0.05 with t>2 on this broad cross-section, ML on raw")
    print("  price/volume DOES rank -- a real hint worth pursuing. If ~0, the door holds even with breadth.")


if __name__ == "__main__":
    run()
