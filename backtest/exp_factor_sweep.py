"""Broad factor-IC sweep (the "just map all factors" idea, done with discipline).

The user's instinct: don't hand-invent factors -- map a whole factor zoo (Qlib Alpha158-style),
vectorize, find what predicts. Right instinct; but the 11-sector cross-section is NARROW, so with
many factors several will look significant BY CHANCE -> apply MULTIPLE-TESTING correction. And
Qlib's factors are all price/volume, the same source we measured at IC~0 -- so this is really a
proper closing of the price/volume door, not a new information source.

~30 factors across the Alpha158 families (momentum, reversal, MA-ratio, volatility, RSI, range
position, volume, higher moments, 52w-high distance), computed vectorized on weekly OHLCV of the
9 core SPDR sectors. For each: mean cross-sectional forward IC (Spearman) + t-stat. Bonferroni
flag. Also a composite (mean-z) and the 1st PC, to show combining ~0-IC factors stays ~0.

Run: python backtest/exp_factor_sweep.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import load
from signals import rsi

SECTORS = ["XLK", "XLY", "XLF", "XLV", "XLI", "XLP", "XLU", "XLB", "XLE"]


def weekly_ohlcv():
    C, H, L, V = {}, {}, {}, {}
    for s in SECTORS:
        d = load(s, adjusted=True)
        C[s] = d["close"].resample("W-FRI").last()
        H[s] = d["high"].resample("W-FRI").max()
        L[s] = d["low"].resample("W-FRI").min()
        V[s] = d["volume"].resample("W-FRI").sum()
    C = pd.DataFrame(C).dropna()
    idx, cols = C.index, C.columns
    H = pd.DataFrame(H).reindex(idx)[cols]
    L = pd.DataFrame(L).reindex(idx)[cols]
    V = pd.DataFrame(V).reindex(idx)[cols]
    return C, H, L, V


def build_factors(C, H, L, V):
    r = C.pct_change()
    f = {}
    for k in (1, 2, 4, 8, 13, 26, 52):
        f[f"mom{k}"] = C / C.shift(k) - 1
    for k in (1, 2, 4):
        f[f"rev{k}"] = -(C / C.shift(k) - 1)
    for k in (5, 10, 20, 40):
        f[f"maR{k}"] = C / C.rolling(k).mean() - 1
    for k in (4, 13, 26):
        f[f"vol{k}"] = r.rolling(k).std()
    for k in (4, 13):
        f[f"volR{k}"] = V / V.rolling(k).mean()
    for k in (2, 4, 14):
        f[f"rsi{k}"] = C.apply(lambda s: rsi(s, k))
    for k in (13, 52):
        rng = (H.rolling(k).max() - L.rolling(k).min())
        f[f"pos{k}"] = (C - L.rolling(k).min()) / rng.replace(0, np.nan)
    f["hi52"] = C / C.rolling(52).max() - 1
    f["skew13"] = r.rolling(13).skew()
    f["kurt13"] = r.rolling(13).kurt()
    f["vov13"] = r.rolling(13).std().pct_change().rolling(4).mean()
    return f


def ic_series(fac, fwd):
    vals = []
    for t in fac.index:
        a, b = fac.loc[t].to_numpy(float), fwd.loc[t].to_numpy(float)
        m = ~(np.isnan(a) | np.isnan(b))
        if m.sum() >= 5:
            rho = spearmanr(a[m], b[m]).correlation
            if rho == rho:
                vals.append(rho)
    v = np.array(vals)
    if len(v) < 30:
        return np.nan, np.nan, len(v)
    return v.mean(), v.mean() / (v.std(ddof=1) / np.sqrt(len(v))), len(v)


def run():
    C, H, L, V = weekly_ohlcv()
    fwd = C.pct_change().shift(-1)          # next-week return per sector
    factors = build_factors(C, H, L, V)
    F = len(factors)
    t_bonf = norm.ppf(1 - 0.025 / F)        # two-sided Bonferroni over F tests
    print(f"\n=== factor-IC sweep -- {F} factors, {len(C)} weeks {C.index[0].date()}->{C.index[-1].date()} ===")
    print(f"9 sectors; Bonferroni |t|>{t_bonf:.2f} to survive {F} tests; ~{F*0.05:.0f} pass at 5% BY CHANCE\n")
    print(f"{'factor':10}{'mean IC':>9}{'t':>7}   {'factor':10}{'mean IC':>9}{'t':>7}")
    rows = []
    for name, fac in factors.items():
        m, t, nn = ic_series(fac, fwd)
        rows.append((name, m, t))
    rows.sort(key=lambda x: -abs(x[2]) if x[2] == x[2] else 0)
    for i in range(0, len(rows), 2):
        a = rows[i]
        b = rows[i + 1] if i + 1 < len(rows) else ("", np.nan, np.nan)
        flag = " *" if (a[2] == a[2] and abs(a[2]) > t_bonf) else "  "
        print(f"{a[0]:10}{a[1]:>9.3f}{a[2]:>7.1f}{flag} {b[0]:10}"
              + (f"{b[1]:>9.3f}{b[2]:>7.1f}" if b[0] else ""))

    surv = [r for r in rows if r[2] == r[2] and abs(r[2]) > t_bonf]
    best = max((r for r in rows if r[2] == r[2]), key=lambda r: abs(r[2]))
    print(f"\n  survive Bonferroni: {len(surv)}/{F}  |  strongest: {best[0]} IC {best[1]:.3f} (t {best[2]:.1f})")

    # composite (mean of z-scored factors) + 1st PC -- do combos manufacture IC?
    def z(df):
        return df.sub(df.mean(1), axis=0).div(df.std(1) + 1e-9, axis=0)
    Z = [z(f).to_numpy() for f in factors.values()]
    comp = pd.DataFrame(np.nanmean(Z, axis=0), index=C.index, columns=C.columns)
    mC, tC, _ = ic_series(comp, fwd)
    # 1st PC of the factor panel (flatten week x sector x factor -> per (t,sector) vector)
    stack = np.stack([np.nan_to_num(zi) for zi in Z], axis=-1)   # (T, S, F)
    X = stack.reshape(-1, F)
    X = X[~np.isnan(X).any(1)]
    U, Sv, Vt = np.linalg.svd(X - X.mean(0), full_matrices=False)
    pc1 = (stack @ Vt[0])                                        # (T,S) projection on PC1
    pc1df = pd.DataFrame(pc1, index=C.index, columns=C.columns)
    mP, tP, _ = ic_series(pc1df, fwd)
    print(f"  composite mean-z IC {mC:.3f} (t {tC:.1f}) | 1st-PC (SVD) IC {mP:.3f} (t {tP:.1f})")
    print("  -> combining / SVD-ing ~0-IC factors stays ~0 (variance != prediction). If nothing")
    print("     survives, the missing ingredient is a NEW information source (Phase 3), not more price/volume.")


if __name__ == "__main__":
    run()
