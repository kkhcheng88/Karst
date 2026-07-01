"""Alpha360-style ML test -- the final boss of the price/volume search (nonlinear, OOS).

Alpha360 is NOT 360 clever factors -- it's the raw normalized last-N OHLCV(+vwap) fed to an ML
model to learn nonlinear patterns. So the meaningful test is: train a GBDT on that raw price/volume
and measure its OUT-OF-SAMPLE cross-sectional forward IC. If even this can't clear IC ~0.05 with
strict walk-forward, the price/volume door is closed for LINEAR and NONLINEAR alike.

Features: last L=26 weeks of [close, open, high, low, volume, vwap], price fields normalized by
close[t], volume by its window mean -> 156 features per (sector, week). Target: next-week return.
Model: HistGradientBoostingRegressor (regularized). Walk-forward: expanding train, 52-week OOS
blocks, retrain each block. IC measured on OOS predictions only.

Caveat baked in: the 9-sector cross-section is TINY for ML -> high overfit risk; walk-forward OOS
is mandatory and the honest prior is it won't clear 0.05 robustly.

Run: python backtest/exp_alpha360_ml.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import load
from metrics import ann_sharpe, cagr, max_drawdown

SECTORS = ["XLK", "XLY", "XLF", "XLV", "XLI", "XLP", "XLU", "XLB", "XLE"]
L, MIN_TRAIN, BLOCK = 26, 400, 52
COST_BPS, NTOP = 5.0, 3


def weekly(s):
    d = load(s, adjusted=True)
    return pd.DataFrame({
        "o": d["open"].resample("W-FRI").first(), "h": d["high"].resample("W-FRI").max(),
        "l": d["low"].resample("W-FRI").min(), "c": d["close"].resample("W-FRI").last(),
        "v": d["volume"].resample("W-FRI").sum()})


def run():
    data = {s: weekly(s) for s in SECTORS}
    idx = None
    for s in SECTORS:
        idx = data[s].index if idx is None else idx.intersection(data[s].index)
    C = np.column_stack([data[s]["c"].reindex(idx) for s in SECTORS])
    O = np.column_stack([data[s]["o"].reindex(idx) for s in SECTORS])
    H = np.column_stack([data[s]["h"].reindex(idx) for s in SECTORS])
    Lo = np.column_stack([data[s]["l"].reindex(idx) for s in SECTORS])
    V = np.column_stack([data[s]["v"].reindex(idx) for s in SECTORS])
    VW = (H + Lo + C) / 3.0
    T, S = C.shape
    ret = np.full((T, S), np.nan)
    ret[:-1] = C[1:] / C[:-1] - 1.0            # next-week return at row t = C[t+1]/C[t]-1

    # build samples
    Xs, ys, ts, ss = [], [], [], []
    for t in range(L, T - 1):
        for j in range(S):
            c0, v0 = C[t, j], V[t - L + 1:t + 1, j].mean()
            if c0 <= 0 or v0 <= 0 or np.isnan(ret[t, j]):
                continue
            w = slice(t - L + 1, t + 1)
            feat = np.concatenate([
                C[w, j] / c0, O[w, j] / c0, H[w, j] / c0, Lo[w, j] / c0,
                V[w, j] / v0, VW[w, j] / c0])
            if np.isnan(feat).any():
                continue
            Xs.append(feat); ys.append(ret[t, j]); ts.append(t); ss.append(j)
    X, y, ts, ss = np.array(Xs), np.array(ys), np.array(ts), np.array(ss)
    print(f"\n=== Alpha360-style GBDT (OOS walk-forward) -- {S} sectors, {idx[0].date()}->{idx[-1].date()} ===")
    print(f"{len(y)} samples, {X.shape[1]} features (L={L}w x 6), 52w OOS blocks\n")

    pred = np.full(T * S, np.nan)             # indexed by t*S+j
    for start in range(MIN_TRAIN, T - 1, BLOCK):
        tr = ts < start
        te = (ts >= start) & (ts < start + BLOCK)
        if tr.sum() < 500 or te.sum() == 0:
            continue
        m = HistGradientBoostingRegressor(max_depth=3, max_iter=200, learning_rate=0.05,
                                          l2_regularization=1.0, min_samples_leaf=50)
        m.fit(X[tr], y[tr])
        p = m.predict(X[te])
        for idx_te, pv in zip(np.where(te)[0], p):
            pred[ts[idx_te] * S + ss[idx_te]] = pv

    # OOS cross-sectional IC + portfolio
    ics, port_r, port_W = [], [], []
    weeks = sorted(set(ts[(ts >= MIN_TRAIN)]))
    for t in weeks:
        pv = np.array([pred[t * S + j] for j in range(S)])
        rv = ret[t]
        m = ~(np.isnan(pv) | np.isnan(rv))
        if m.sum() >= 5:
            rho = spearmanr(pv[m], rv[m]).correlation
            if rho == rho:
                ics.append(rho)
            w = np.zeros(S)
            picks = np.argsort(-np.where(np.isnan(pv), -9, pv))[:NTOP]
            for i in picks:
                w[i] = 1.0 / NTOP
            port_W.append(w)
            port_r.append(sum(rv[i] / NTOP for i in picks if not np.isnan(rv[i])))
    ics = np.array(ics)
    t_ic = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics)))
    print(f"OOS forward IC: mean {ics.mean():.3f}  t {t_ic:.1f}  (n={len(ics)} weeks)   [bar: >=0.05]")

    W = np.array(port_W)
    r = np.array(port_r)
    turn = np.abs(np.diff(W, axis=0, prepend=np.zeros((1, S)))).sum(1)
    rnet = r - turn * COST_BPS / 1e4
    spy = load("SPY", adjusted=True)["close"].resample("W-FRI").last().reindex(idx).pct_change().dropna().to_numpy()
    ew = np.nanmean(ret[:-1], axis=1)
    def cg(x): return cagr(np.cumprod(1 + np.asarray(x)[~np.isnan(np.asarray(x))]), 52)
    print(f"\nOOS top-3-by-model portfolio (net): CAGR {cg(rnet)*100:.1f}%  Sharpe {ann_sharpe(rnet,52):.2f}  "
          f"MaxDD {max_drawdown(np.cumprod(1+rnet))*100:.1f}%")
    print(f"  benchmarks (full): SPY {cg(spy)*100:.1f}%, EW {cg(ew)*100:.1f}%")
    print("\n  Read: if OOS IC is ~0 (t<2) and the portfolio doesn't beat SPY net, then nonlinear ML on")
    print("  raw price/volume ALSO fails -> the price/volume door is closed, linear AND nonlinear.")


if __name__ == "__main__":
    run()
