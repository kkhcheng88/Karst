"""Composite RISK-ON score (0-100) with magnitude, trend, and factor breakdown.

The engine's market gate is BINARY (gate=1/0 + a label like risk_on). The user wants
MAGNITUDE ("risk-on can have a degree") and TREND ("more or less risk-on than last
week?"). Every gate factor is derived from a PRICE SERIES (SPY, VIX, VIX3M, IWM, SPMO),
so the composite can be recomputed at every past date -> the trend (Δ vs 1d/1w/1m) and a
sparkline come for free, with no historical logging needed.

score = Σ wᵢ · subᵢ,  each subᵢ ∈ [0,100], higher = more risk-on. The breakdown is
returned so the dashboard can EXPLAIN the number (the drivers line becomes the factors).
This is a presentation-layer composite (transparent, monotonic), NOT a validated alpha
signal — it re-expresses the same gate factors as a continuous, decomposable read.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# factor -> weight (sums to 1.0). Trend dominates (most robust), momentum/term lighter.
_WEIGHTS = {"trend": 0.30, "vol": 0.20, "breadth": 0.20, "momentum": 0.15, "term": 0.15}


def _clip(s):
    return s.clip(0, 100)


def _load_closes():
    import data
    def g(sym, min_rows=250):
        return data.load(sym, min_rows=min_rows)["close"]
    spy = g("SPY")
    out = {"SPY": spy}
    for sym, mr in [("^VIX", 50), ("^VIX3M", 50), ("IWM", 250), ("SPMO", 120)]:
        try:
            out[sym] = g(sym, mr).reindex(spy.index).ffill()
        except Exception:
            out[sym] = None
    return out


def _subscores(cl: dict) -> pd.DataFrame:
    """Per-date factor sub-scores (0-100). Vectorized over the whole history."""
    spy = cl["SPY"]
    idx = spy.index
    d = pd.DataFrame(index=idx)

    # 1) TREND — SPY vs its 200SMA (dist). +ve = uptrend. ±10% spans the 0-100 band.
    dist = spy / spy.rolling(200).mean() - 1
    d["trend"] = _clip(50 + dist * 500)

    # 2) VOL — inverse VIX 252d percentile rank (low VIX rank = calm = risk-on)
    vix = cl.get("^VIX")
    if vix is not None:
        rank = vix.rolling(252).apply(lambda w: (w.iloc[-1] > w).mean(), raw=False)
        d["vol"] = _clip((1 - rank) * 100)
    else:
        d["vol"] = 50.0

    # 3) BREADTH — IWM (small-cap) vs its 200SMA dist (participation)
    iwm = cl.get("IWM")
    if iwm is not None:
        idist = iwm / iwm.rolling(200).mean() - 1
        d["breadth"] = _clip(50 + idist * 500)
    else:
        d["breadth"] = 50.0

    # 4) MOMENTUM — RS(SPMO/SPY) 63d (momentum factor in/out of favor)
    spmo = cl.get("SPMO")
    if spmo is not None:
        rs = (spmo / spmo.shift(63)) / (spy / spy.shift(63))
        d["momentum"] = _clip(50 + (rs - 1) * 250)
    else:
        d["momentum"] = 50.0

    # 5) TERM — VIX / VIX3M (<1 contango = calm; >1 backwardation = near-term stress)
    v, v3 = cl.get("^VIX"), cl.get("^VIX3M")
    if v is not None and v3 is not None:
        term = v / v3
        d["term"] = _clip(50 + (1.0 - term) / 0.30 * 50)
    else:
        d["term"] = 50.0
    return d


def _human(cl: dict) -> dict:
    """Current raw factor values, for the 'value' label under each bar."""
    spy = cl["SPY"]
    dist = float(spy.iloc[-1] / spy.rolling(200).mean().iloc[-1] - 1)
    out = {"trend": f"SPY {dist*100:+.1f}% vs 200SMA"}
    vix = cl.get("^VIX")
    if vix is not None:
        rk = float((vix.iloc[-1] > vix.iloc[-252:]).mean())
        out["vol"] = f"VIX {float(vix.iloc[-1]):.1f} · rank {rk*100:.0f}%"
    iwm = cl.get("IWM")
    if iwm is not None:
        idist = float(iwm.iloc[-1] / iwm.rolling(200).mean().iloc[-1] - 1)
        out["breadth"] = f"IWM {idist*100:+.1f}% vs 200SMA"
    spmo = cl.get("SPMO")
    if spmo is not None:
        rs = float((spmo.iloc[-1] / spmo.iloc[-64]) / (spy.iloc[-1] / spy.iloc[-64]))
        out["momentum"] = f"SPMO-RS {rs:.2f}"
    v, v3 = cl.get("^VIX"), cl.get("^VIX3M")
    if v is not None and v3 is not None:
        out["term"] = f"VIX/VIX3M {float(v.iloc[-1]/v3.iloc[-1]):.2f}"
    return out


def _label(score: float) -> str:
    if score >= 65:
        return "進攻"
    if score >= 45:
        return "中性"
    return "防禦"


def compute() -> dict:
    """Return the composite risk-on read: score, deltas, sparkline, factor breakdown."""
    cl = _load_closes()
    sub = _subscores(cl)
    comp = sum(sub[k] * w for k, w in _WEIGHTS.items()).dropna()
    if comp.empty:
        return {"score": None}
    cur = float(comp.iloc[-1])

    def delta(n):
        return round(cur - float(comp.iloc[-1 - n]), 1) if len(comp) > n else None

    human = _human(cl)
    factors = []
    for k, w in _WEIGHTS.items():
        val = float(sub[k].iloc[-1])
        factors.append({"name": k, "subscore": round(val, 1), "weight": w,
                        "contribution": round(val * w, 1), "value": human.get(k, "")})
    spark = [round(float(x), 1) for x in comp.iloc[-90:].tolist()]   # ~4.5 months
    return {
        "score": round(cur, 1),
        "label": _label(cur),
        "delta_1d": delta(1), "delta_1w": delta(5), "delta_1m": delta(21),
        "factors": factors,
        "sparkline": spark,
        "weights": _WEIGHTS,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(compute(), indent=2, default=str))
