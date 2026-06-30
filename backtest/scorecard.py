"""Karst scorecard v2 — daily 0-100 suitability per tool (decision support, NOT autopilot).

v2 changes (from the v1 validation, see results/2026-06-30_scorecard_validation.md):
- Scores predict RISK/REGIME, not return. LEAP/PMCC are reframed around the validated
  entry edge (RSI-2 dip) + the regime GATE (>200SMA) + cheap IV — strength/extension is
  demoted (it mean-reverts, so it was a backwards return signal in v1).
- Scores are reported as PER-TOOL EXPANDING PERCENTILE (no look-ahead): "more favorable
  for this tool than X% of past days" — so the scale truly spans 0-100 and boundaries mean
  something.
- CSP / CASH kept (v1 validated: CSP score -> lower forward drawdown; CASH flags fragility).

Tools are NOT mutually exclusive. Human reads scores + drivers and allocates within invariants.
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


def raw_scores(f):
    """Raw weighted scores (0-100). v2: LEAP/PMCC = gate + RSI-2 dip + IV, not strength."""
    adx_trend = clamp01((f["adx"] - 15) / 20)
    adx_range = 1 - adx_trend
    iv_low = clamp01((0.5 - f["ivr"]) / 0.5)
    iv_high = clamp01((f["ivr"] - 0.5) / 0.5)
    dip = clamp01((10 - f["rsi2"]) / 10)        # RSI-2 < 10 oversold = the validated entry edge
    above = f["above"]
    falling = (f["slope"] < 0).astype(float)

    # LEAP/PMCC: hard gate (>200SMA), then dip-entry + cheapness; strength only as confirmation.
    leap = above * (40 * dip + 30 * iv_low + 30 * f["ma50_200"])
    pmcc = above * (40 * iv_high + 30 * f["ma50_200"] + 30 * dip)
    # CSP: calm (low ADX) + low IV + dip; downtrend penalized. (v1 validated.)
    csp = 35 * adx_range + 30 * iv_low + 20 * dip + 15 * above
    csp = csp * np.where((above < 0.5) & (falling > 0.5), 0.5, 1.0)
    # CASH: fragility flag.
    cash = 50 * (1 - above) + 30 * iv_high + 20 * falling * (1 - above)
    return pd.DataFrame({"LEAP": leap, "PMCC": pmcc, "CSP": csp, "CASH": cash}).clip(0, 100)


def pct_rank(s):
    """Expanding percentile (0-100), no look-ahead: rank of value[i] within values[:i]."""
    a = np.asarray(s, dtype="float64")
    out = np.full(len(a), 50.0)
    for i in range(1, len(a)):
        past = a[:i]
        out[i] = np.count_nonzero(past <= a[i]) / i * 100.0
    return pd.Series(out, index=s.index)


def scores(f):
    """Per-tool expanding-percentile scores (what the human reads)."""
    raw = raw_scores(f)
    return pd.DataFrame({c: pct_rank(raw[c]) for c in raw.columns})


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
        print("=== KARST SCORECARD v2 (latest) — per-tool percentile (0-100), decision support ===")
        for r in recs:
            ranked = sorted(r["scores"].items(), key=lambda kv: -kv[1])
            print(f"\n### {r['underlying']}  {r['date']}")
            print("  " + "  ".join(f"{k} {int(x):3d}" for k, x in ranked))
            print(f"  drivers: {r['drivers']}")
