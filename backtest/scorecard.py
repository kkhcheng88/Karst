"""Karst scorecard v3.1 — daily 0-100 suitability per tool (decision support, NOT autopilot).

Clean rule-based model. PMCC dropped (its long leg == LEAP); the only NEW leg vs LEAP is the
SHORT CALL overlay, and its validated timing is RSI-2 OVERBOUGHT (mirror of the LEAP dip):

  LEAP       = >200SMA  AND  RSI-2 DIP            (buy the oversold dip in an uptrend)
  SHORT_CALL = >200SMA  AND  RSI-2 OVERBOUGHT     (sell a call vs your long on a peak;
               validated: SPY short-call PF 1.53->2.26 at RSI2>90. NOTE: momentum names like
               QQQ can keep ripping when extremely overbought — don't oversize.)
  CSP        = IV-rank U-SHAPE                    (low=calm income SAFE; high=capitulation RISKY)
  CASH       = <200SMA  AND  high IV rank         (defend/reduce)

Raw scores span 0-100 by construction. Scorecard = regime/RISK suitability; entry/overlay timing
is the RSI-2 extreme itself (shown in drivers). Human reads scores + drivers, allocates within
invariants. LEAP & SHORT_CALL are two legs of one position you can hold together.
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
    dip = clamp01((10 - f["rsi2"]) / 10)            # RSI-2 < 10 oversold
    overbought = clamp01((f["rsi2"] - 70) / 30)     # RSI-2 > 70 overbought
    iv_low = clamp01((0.30 - f["ivr"]) / 0.30)
    iv_high = clamp01((f["ivr"] - 0.70) / 0.30)

    leap = 100 * above * dip
    short_call = 100 * above * overbought           # overlay on a held long, sell on a peak
    csp = 100 * np.maximum(iv_low, iv_high)         # U-shape (both ends)
    cash = 100 * (1 - above) * (0.5 + 0.5 * iv_high)
    return pd.DataFrame({"LEAP": leap, "SHORT_CALL": short_call,
                         "CSP": csp, "CASH": cash}).clip(0, 100)


def csp_mode(row):
    if row["ivr"] < 0.30:
        return "low-IV income"
    if row["ivr"] > 0.70:
        return "high-IV CAPITULATION (risky, vs CASH)"
    return "mid-IV (avoid)"


def driver_str(row):
    abv = "above" if row["above"] > 0.5 else "below"
    r2 = row["rsi2"]
    tag = "(DIP)" if r2 < 10 else "(OB)" if r2 > 70 else ""
    return (f"{abv} 200SMA ({row['dist']*100:+.1f}%) | IV-rank {row['ivr']*100:.0f}% | "
            f"RSI2 {r2:.0f} {tag} | ADX {row['adx']:.0f}")


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
        print("=== KARST SCORECARD v3.1 (latest) — 0-100 suitability, decision support ===")
        for r in recs:
            ranked = sorted(r["scores"].items(), key=lambda kv: -kv[1])
            print(f"\n### {r['underlying']}  {r['date']}")
            print("  " + "  ".join(f"{k} {int(x):3d}" for k, x in ranked))
            print(f"  drivers: {r['drivers']}  | CSP: {r['csp_mode']}")
