"""Karst scorecard — daily 0-100 suitability per tool (decision support, NOT autopilot).

Transparent, weighted from this session's validated findings. The human reads the
scores + drivers and allocates within the invariants (sizing, ETF-only, etc.).

  LEAP : uncapped leveraged long. HARD GATE price>200SMA (else 0; ruin avoidance / INV-6).
         Wants strong uptrend + LOW IV (cheap) + RSI-2 dip.
  PMCC : leveraged long + short-call income. Gate price>200SMA. Wants uptrend + ELEVATED IV
         (rich calls to sell). [Note: uptrend+high-IV is empirically rare -> PMCC rarely peaks.]
  CSP  : capped income / short vol, recoverable on index. Wants calm/sideways + LOW IV + dip;
         downtrend penalized (assignment risk, recoverable but path-risky).
  CASH : downtrend / fragility (below 200SMA + falling + high IV).

Weights are v1 (judgment grounded in backtests) — tunable. Scores can co-exist (tools are
NOT mutually exclusive); the score = "how favorable is this tool right now".
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
    adx_trend = clamp01((f["adx"] - 15) / 20)          # ADX 15->0, 35->1
    adx_range = 1 - adx_trend
    iv_low = clamp01((0.5 - f["ivr"]) / 0.5)           # IV rank 0->1, 0.5->0
    iv_high = clamp01((f["ivr"] - 0.5) / 0.5)
    dip = clamp01((10 - f["rsi2"]) / 10)               # RSI-2 < 10 oversold bonus
    above = f["above"]
    falling = (f["slope"] < 0).astype(float)

    leap = above * (40 * adx_trend + 25 * iv_low + 20 * dip + 15 * f["ma50_200"])
    pmcc = above * (30 * iv_high + 25 * adx_trend + 20 * dip + 25 * f["ma50_200"])
    csp = 35 * adx_range + 30 * iv_low + 20 * dip + 15 * above
    csp = csp * np.where((above < 0.5) & (falling > 0.5), 0.5, 1.0)
    cash = 50 * (1 - above) + 30 * iv_high + 20 * falling * (1 - above)

    return pd.DataFrame({"LEAP": leap, "PMCC": pmcc, "CSP": csp, "CASH": cash}).clip(0, 100)


def driver_str(row):
    abv = "above" if row["above"] > 0.5 else "below"
    return (f"{abv} 200SMA ({row['dist']*100:+.1f}%) | ADX {row['adx']:.0f} | "
            f"IV-rank {row['ivr']*100:.0f}% | RSI2 {row['rsi2']:.0f} | "
            f"50>200 {'Y' if row['ma50_200'] > 0.5 else 'N'}")


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
                     "drivers": driver_str(last_f)})

    if as_json:
        print(json.dumps(recs, indent=2))
    else:
        print("=== KARST SCORECARD (latest) — 0-100 suitability, decision support ===")
        for r in recs:
            ranked = sorted(r["scores"].items(), key=lambda kv: -kv[1])
            print(f"\n### {r['underlying']}  {r['date']}")
            print("  " + "  ".join(f"{k} {int(x):3d}" for k, x in ranked))
            print(f"  drivers: {r['drivers']}")
