"""Can MAGS (Mag7 end) + SOXX (semis end) together represent QQQ? -- 2026-07-17

User question: if the tech axis has two ends (blue-chip megacap vs semis),
do MAGS+SOXX jointly span QQQ well enough to treat them as its representation?
Test: OLS of QQQ daily returns on MAGS/SOXX (and variants), R^2 + residual vol
+ tracking error of the fitted combo. MAGS limits the sample to 2023-04+.

Run: PYTHONUTF8=1 python backtest/experiments/exp_qqq_two_factor.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load

TICKERS = ["QQQ", "MAGS", "SOXX", "SMH", "IGV", "XLK"]


def main():
    rets = {}
    for t in TICKERS:
        px = load(t, adjusted=True, min_rows=50)["close"]
        rets[t] = np.log(px).diff()
    df = pd.DataFrame(rets).dropna()
    print(f"common sample: {df.index[0].date()} -> {df.index[-1].date()}  n={len(df)}")

    y = df["QQQ"]

    def ols_r2(cols):
        X = np.column_stack([np.ones(len(df))] + [df[c].values for c in cols])
        beta, *_ = np.linalg.lstsq(X, y.values, rcond=None)
        fit = X @ beta
        resid = y.values - fit
        r2 = 1 - resid.var() / y.values.var()
        te = resid.std() * np.sqrt(252)  # annualized tracking error
        return beta, r2, te

    specs = [
        ["MAGS"],
        ["SOXX"],
        ["SMH"],
        ["XLK"],
        ["MAGS", "SOXX"],
        ["MAGS", "SMH"],
        ["MAGS", "SOXX", "IGV"],
        ["MAGS", "SMH", "IGV"],
    ]
    print(f"\n{'spec':22} {'R2':>7} {'ann.TE':>7}  betas")
    rows = []
    for cols in specs:
        beta, r2, te = ols_r2(cols)
        bstr = ", ".join(f"{c}={b:+.3f}" for c, b in zip(cols, beta[1:]))
        print(f"{'+'.join(cols):22} {r2:7.4f} {te:6.2%}  {bstr}")
        rows.append((cols, beta, r2, te))

    # simple constrained combo: weights sum to 1, no intercept (investable mix)
    X = df[["MAGS", "SOXX"]].values
    # grid search w in [0,1]
    ws = np.linspace(0, 1, 101)
    best = min(ws, key=lambda w: np.var(y.values - (w * X[:, 0] + (1 - w) * X[:, 1])))
    resid = y.values - (best * X[:, 0] + (1 - best) * X[:, 1])
    r2c = 1 - resid.var() / y.values.var()
    te_c = resid.std() * np.sqrt(252)
    print(f"\ninvestable mix (w*MAGS + (1-w)*SOXX, sum=1): w_MAGS={best:.2f}  R2={r2c:.4f}  ann.TE={te_c:.2%}")

    # cumulative divergence of investable mix vs QQQ over sample
    mix = best * df["MAGS"] + (1 - best) * df["SOXX"]
    cum_gap = (mix - y).cumsum()
    print(f"cumulative log-return gap (mix - QQQ) over sample: {cum_gap.iloc[-1]:+.2%}")

    # SMH vs SOXX head-to-head (long history, independent of MAGS sample)
    smh = np.log(load("SMH", adjusted=True, min_rows=50)["close"]).diff()
    soxx = np.log(load("SOXX", adjusted=True, min_rows=50)["close"]).diff()
    qqq = np.log(load("QQQ", adjusted=True, min_rows=50)["close"]).diff()
    d2 = pd.DataFrame({"SMH": smh, "SOXX": soxx, "QQQ": qqq}).dropna()
    d2 = d2[d2.index >= "2016-01-01"]
    print(f"\nSMH vs SOXX (2016+, n={len(d2)}):")
    print(f"  corr(SMH,SOXX) = {d2['SMH'].corr(d2['SOXX']):.4f}")
    for t in ["SMH", "SOXX"]:
        cagr = np.expm1(d2[t].mean() * 252)
        vol = d2[t].std() * np.sqrt(252)
        cum = d2[t].cumsum()
        dd = (cum - cum.cummax()).min()  # log-scale max drawdown
        print(f"  {t}: CAGR {cagr:+.2%}  vol {vol:.2%}  maxDD(log) {dd:+.2%}")


if __name__ == "__main__":
    main()
