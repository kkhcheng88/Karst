"""Regime quantification — the scorecard inputs.

Turns vague "溫和 / 橫盤 / risk-on" into measurable features:
  - trend vs range : ADX(14)  (>25 trend, <20 range)
  - direction/strength: price vs SMA200, SMA200 slope(20d), distance, SMA50/200
  - IV cheap vs rich : IV rank (VIX/VXN 252d percentile)
Regime label: down / sideways / moderate_up / strong_up.
(risk-on macro overlay — yield curve, credit spread — is a later add.)
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def adx(high, low, close, period=14):
    up, down = high.diff(), -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=high.index)
    tr = pd.concat([(high - low), (high - close.shift()).abs(),
                    (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    pdi = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    mdi = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False).mean()


def iv_rank(vix, win=252):
    lo, hi = vix.rolling(win).min(), vix.rolling(win).max()
    return (vix - lo) / (hi - lo)


def classify(df, vix):
    """df: OHLC DataFrame; vix: aligned VIX/VXN Series. Returns features + regime label."""
    close = df["close"]
    sma200, sma50 = close.rolling(200).mean(), close.rolling(50).mean()
    slope = sma200.pct_change(20)
    dist = close / sma200 - 1
    ax = adx(df["high"], df["low"], close)
    ivr = iv_rank(vix)

    above = close > sma200
    reg = pd.Series(index=close.index, dtype=object)
    reg[~above] = "down"
    reg[above & (ax < 20)] = "sideways"
    reg[above & (ax >= 25) & (sma50 > sma200)] = "strong_up"
    reg[above & reg.isna()] = "moderate_up"
    return pd.DataFrame({"close": close, "adx": ax, "dist": dist, "slope200": slope,
                         "iv_rank": ivr, "regime": reg})


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from data import load

    REGS = ["strong_up", "moderate_up", "sideways", "down"]
    for under, vs in [("SPY", "^VIX"), ("QQQ", "^VXN")]:
        d = load(under)[["high", "low", "close"]]
        v = load(vs)["close"]
        df = d.join(v.rename("vix"), how="inner").dropna()
        f = classify(df, df["vix"]).dropna().iloc[-2520:]  # last ~10y
        print(f"\n### {under}  ({f.index.min().date()}->{f.index.max().date()}, {len(f)} days)")
        for r in REGS:
            m = f["regime"] == r
            if m.sum() == 0:
                continue
            lo = (m & (f["iv_rank"] < 0.25)).sum()
            hi = (m & (f["iv_rank"] > 0.75)).sum()
            print(f"  {r:12} {m.mean()*100:4.0f}% of days | low-IV {lo/max(m.sum(),1)*100:3.0f}%"
                  f"  high-IV {hi/max(m.sum(),1)*100:3.0f}%  avg-ADX {f.loc[m,'adx'].mean():4.1f}")
