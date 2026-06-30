"""Karst scorecard v3 — daily 0-100 suitability per tool (decision support, NOT autopilot).

v3 = the user's clean rule-based model (simpler + better than v2's blended/percentile version):
  LEAP = >200SMA  AND  RSI-2 dip            (pure gate x dip = the validated entry setup)
  PMCC = >200SMA  AND  high IV rank          (uptrend + rich calls to sell; rare/honest)
  CSP  = IV-rank U-SHAPE (low OR very-high)   (56/57); low end = calm income (safe default),
         high end = capitulation contrarian (RISKY, same regime as CASH)
  CASH = <200SMA  AND  high IV rank           (defend/reduce; note downturns bounce)

Raw scores span 0-100 by construction (no percentile — that broke on sparse signals in v2).
Tools are NOT mutually exclusive. Scorecard = regime/RISK suitability; the entry trigger is the
RSI-2 dip itself (shown in drivers). Human reads scores + drivers and allocates within invariants.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from regime import adx, iv_rank
from signals import rsi, sma


def clamp01(x):
    return np.clip(x, 0.0, 1.0)


def features(df, vix):
    close = df["close"]
    sma200, sma50 = sma(close, 200), sma(close, 50)
    return pd.DataFrame({
        "close": close,
        "above": (close > sma200).astype(float),
        "dist": close / sma200 - 1,
        "slope": sma200.pct_change(20),
        "adx": adx(df["high"], df["low"], close),
        "ma50_200": (sma50 > sma200).astype(float),
        "ivr": iv_rank(vix),
        "rsi2": rsi(close, 2),
    })


def scores(f):
    above = f["above"]
    dip = clamp01((10 - f["rsi2"]) / 10)            # RSI-2 < 10 (deeper = higher)
    iv_low = clamp01((0.30 - f["ivr"]) / 0.30)      # IV rank < 30%
    iv_high = clamp01((f["ivr"] - 0.70) / 0.30)     # IV rank > 70%

    leap = 100 * above * dip
    pmcc = 100 * above * iv_high
    csp = 100 * np.maximum(iv_low, iv_high)         # U-shape (both ends)
    cash = 100 * (1 - above) * (0.5 + 0.5 * iv_high)
    return pd.DataFrame({"LEAP": leap, "PMCC": pmcc, "CSP": csp, "CASH": cash}).clip(0, 100)


def csp_mode(row):
    if row["ivr"] < 0.30:
        return "low-IV income"
    if row["ivr"] > 0.70:
        return "high-IV CAPITULATION (risky, vs CASH)"
    return "mid-IV (avoid)"


def driver_str(row):
    abv = "above" if row["above"] > 0.5 else "below"
    return (f"{abv} 200SMA ({row['dist']*100:+.1f}%) | IV-rank {row['ivr']*100:.0f}% | "
            f"RSI2 {row['rsi2']:.0f} {'(DIP)' if row['rsi2'] < 10 else ''} | "
            f"ADX {row['adx']:.0f}")


if __name__ == "__main__":
    import json
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from data import load

    as_json = "--json" in sys.argv
    recs = []
    for under, vs in [("SPY", "^VIX"), ("QQQ", "^VXN"), ("SPMO", "^VIX")]:
        d = load(under)[["high", "low", "close"]]
        v = load(vs)["close"]
        df = d.join(v.rename("vix"), how="inner").dropna()
        f = features(df, df["vix"]).dropna()
        last_f, last_s = f.iloc[-1], scores(f).iloc[-1]
        recs.append({"underlying": under, "date": str(df.index[-1].date()),
                     "scores": {k: round(float(x)) for k, x in last_s.items()},
                     "drivers": driver_str(last_f), "csp_mode": csp_mode(last_f)})

    if as_json:
        print(json.dumps(recs, indent=2))
    else:
        print("=== KARST SCORECARD v3 (latest) — 0-100 suitability, decision support ===")
        for r in recs:
            ranked = sorted(r["scores"].items(), key=lambda kv: -kv[1])
            print(f"\n### {r['underlying']}  {r['date']}")
            print("  " + "  ".join(f"{k} {int(x):3d}" for k, x in ranked))
            print(f"  drivers: {r['drivers']}")
            print(f"  CSP mode: {r['csp_mode']}")
