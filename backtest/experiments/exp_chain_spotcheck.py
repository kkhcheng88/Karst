"""exp_chain_spotcheck.py — real options-chain spot-check vs LEAP pricing model.

Question   : Does the core-v2 LEAP pricing model (IV_1y = m * VIX/100, m in
             {0.85 base, 1.00, 1.15}) match today's REAL 1y options chain IV?
             Does the flat-vol assumption miss equity put/call skew at deep-ITM
             deltas? Is the 0.30d/21DTE short-call bid/ask spread wider than the
             backtest's 0.5%/side cost assumption? Where does IV rank sit today?
Method     : yfinance live option_chain() snapshot (SPY + QQQ), BSM (backtest/bsm.py)
             to compute delta from each strike's own chain IV, q = trailing-12m
             dividend yield. This is a SPOT-CHECK (today, calm market) — it can
             confirm/reject the model's BASE LEVEL but cannot see historical
             crash-time term structure (no free implied-vol surface history).
Cost       : n/a (data pull + BSM, no trading).
Run        : python backtest/experiments/exp_chain_spotcheck.py
Output     : backtest/results/2026-07-09_options_chain_spotcheck.md (+ this
             script also dumps raw chain JSON to backtest/experiments/_chain_*.json
             for provenance / re-derivation).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import yfinance as yf

from bsm import call_delta

M_GRID = [0.85, 1.00, 1.15]
TARGET_DELTAS = [1.00, 0.50, 0.70, 0.80]  # 1.00 slot = "ATM" (closest to spot), rest are true deltas
RESULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def _now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def trailing_dividend_yield(ticker: yf.Ticker, spot: float) -> float:
    try:
        div = ticker.dividends
        if div is None or len(div) == 0:
            return 0.0
        div = div.tz_localize(None) if div.index.tz is not None else div
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=366)
        ttm = div[div.index >= cutoff].sum()
        return float(ttm) / spot if spot else 0.0
    except Exception:
        return 0.0


def pick_leap_expiry(expiries: list[str], lo_days=330, hi_days=420) -> str | None:
    today = pd.Timestamp.now().normalize()
    cands = []
    for e in expiries:
        d = (pd.Timestamp(e) - today).days
        if lo_days <= d <= hi_days:
            cands.append((abs(d - 365), e, d))
    if not cands:
        return None
    cands.sort()
    return cands[0][1]


def pick_short_expiry(expiries: list[str], target_days=21, tol=7) -> str | None:
    today = pd.Timestamp.now().normalize()
    cands = []
    for e in expiries:
        d = (pd.Timestamp(e) - today).days
        if d > 0:
            cands.append((abs(d - target_days), e, d))
    if not cands:
        return None
    cands.sort()
    if cands[0][0] <= tol + 100:  # always take nearest even if outside tol, but flag
        return cands[0][1]
    return None


def leap_delta_table(symbol: str, vix_symbol: str) -> dict:
    tkr = yf.Ticker(symbol)
    spot_hist = tkr.history(period="5d")
    spot = float(spot_hist["Close"].iloc[-1])
    q = trailing_dividend_yield(tkr, spot)

    expiries = tkr.options
    exp = pick_leap_expiry(list(expiries))
    if exp is None:
        return {"symbol": symbol, "error": "no expiry in 330-420d window", "expiries": list(expiries)}

    T_days = (pd.Timestamp(exp) - pd.Timestamp.now().normalize()).days
    T = T_days / 365.0
    r = 0.045  # approx short-term risk-free (T-bill), used only for BSM d1/d2

    chain = tkr.option_chain(exp)
    calls = chain.calls.copy()
    calls = calls[(calls["bid"] > 0) & (calls["ask"] > 0)]
    calls["mid_iv"] = calls["impliedVolatility"]
    calls = calls[calls["mid_iv"] > 0.01]

    # compute delta from chain IV for every strike
    calls["delta"] = calls.apply(
        lambda row: call_delta(spot, row["strike"], T, r, q, row["mid_iv"]), axis=1
    )

    rows = []
    # ATM strike = closest to spot
    atm_idx = (calls["strike"] - spot).abs().idxmin()
    picks = {"ATM": calls.loc[atm_idx]}
    for target in [0.50, 0.70, 0.80]:
        idx = (calls["delta"] - target).abs().idxmin()
        picks[f"{target:.2f}d"] = calls.loc[idx]

    vix_hist = yf.Ticker(vix_symbol).history(period="5d")
    vix_now = float(vix_hist["Close"].iloc[-1])

    for label, row in picks.items():
        real_iv = float(row["mid_iv"])
        model_ivs = {f"m={m:.2f}": m * vix_now / 100.0 for m in M_GRID}
        rows.append({
            "label": label,
            "strike": float(row["strike"]),
            "delta": float(row["delta"]),
            "bid": float(row["bid"]),
            "ask": float(row["ask"]),
            "real_iv": real_iv,
            **model_ivs,
            "diff_vs_m0.85": real_iv - model_ivs["m=0.85"],
            "diff_vs_m1.00": real_iv - model_ivs["m=1.00"],
            "diff_vs_m1.15": real_iv - model_ivs["m=1.15"],
        })

    return {
        "symbol": symbol,
        "spot": spot,
        "q_div_yield": q,
        "expiry": exp,
        "T_days": T_days,
        "vix_symbol": vix_symbol,
        "vix_now": vix_now,
        "rows": rows,
    }


def short_call_check(symbol: str = "SPY") -> dict:
    tkr = yf.Ticker(symbol)
    spot = float(tkr.history(period="5d")["Close"].iloc[-1])
    expiries = list(tkr.options)
    exp = pick_short_expiry(expiries, target_days=21, tol=10)
    if exp is None:
        return {"symbol": symbol, "error": "no near-21d expiry found"}
    T_days = (pd.Timestamp(exp) - pd.Timestamp.now().normalize()).days
    T = T_days / 365.0
    r = 0.045
    q = trailing_dividend_yield(tkr, spot)

    chain = tkr.option_chain(exp)
    calls = chain.calls.copy()
    calls = calls[(calls["bid"] > 0) & (calls["ask"] > 0) & (calls["impliedVolatility"] > 0.01)]
    calls["delta"] = calls.apply(
        lambda row: call_delta(spot, row["strike"], T, r, q, row["impliedVolatility"]), axis=1
    )
    idx = (calls["delta"] - 0.30).abs().idxmin()
    row = calls.loc[idx]
    bid, ask = float(row["bid"]), float(row["ask"])
    mid = (bid + ask) / 2
    spread = ask - bid
    spread_pct_of_mid = spread / mid if mid else float("nan")
    return {
        "symbol": symbol,
        "spot": spot,
        "expiry": exp,
        "T_days": T_days,
        "strike": float(row["strike"]),
        "delta": float(row["delta"]),
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "spread": spread,
        "spread_pct_of_mid": spread_pct_of_mid,
        "iv": float(row["impliedVolatility"]),
        "lastPrice": float(row.get("lastPrice", float("nan"))),
    }


def iv_rank(symbol: str, lookback_days=252) -> dict:
    hist = yf.Ticker(symbol).history(period="400d")["Close"].dropna()
    hist = hist.tail(lookback_days + 5)
    now = float(hist.iloc[-1])
    window = hist.tail(lookback_days)
    pct = float((window < now).sum()) / len(window) * 100
    return {
        "symbol": symbol,
        "now": now,
        "min_252d": float(window.min()),
        "max_252d": float(window.max()),
        "percentile_rank": pct,
        "n": len(window),
    }


def main():
    out = {"pulled_at": _now_utc(), "leap": {}, "short_call": {}, "iv_rank": {}}

    out["leap"]["SPY"] = leap_delta_table("SPY", "^VIX")
    out["leap"]["QQQ"] = leap_delta_table("QQQ", "^VXN")

    out["short_call"]["SPY"] = short_call_check("SPY")

    out["iv_rank"]["VIX"] = iv_rank("^VIX")
    out["iv_rank"]["VXN"] = iv_rank("^VXN")

    dump_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_chain_spotcheck_raw.json")
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)

    print(json.dumps(out, indent=2, default=str))
    print(f"\n[dumped] {dump_path}")


if __name__ == "__main__":
    main()
