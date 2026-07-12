"""exp_leap_rent.py -- LEAP "beta warehouse rent" + delta-notional ledger, real chain snapshot.

Question   : Core v2's all-weather design wants index beta delivered via SPY/QQQ LEAP calls
             (no spot holding), freeing the capital NOT spent on premium for thesis/defensive
             sleeves. Two numbers are needed from TODAY's real option chain:
               (1) "rent" -- the annualized time-value drag of holding a LEAP instead of the
                   underlying, as % of spot notional, at Delta~0.80 (stock-replacement) and
                   Delta~0.50 (flagship convexity, core v2's actual choice).
               (2) delta-notional leverage per $ of premium at each delta choice, and the
                   resulting AA-table premium requirement to hit a target overall portfolio
                   delta (100/115/130%) given a ballast+thesis sleeve base.
Method     : yfinance live option_chain() snapshot, SPY (vs ^VIX) and QQQ (vs ^VXN). Delta
             computed per-strike from the chain's OWN impliedVolatility via BSM (backtest/bsm.py),
             matching backtest/experiments/exp_chain_spotcheck.py's methodology (the script that
             produced backtest/results/2026-07-09_options_chain_spotcheck.md) so IV/skew results
             are directly cross-referenceable, not just eyeballed.
             Expiry: nearest standard monthly in the 365-456 day window (12-15mo), closest to a
             410d (~13.5mo) midpoint target.
             Rent annualization: linear pro-rata (time_value/spot) * (365.25/T_days) -- a
             straight-line average annualized rate, NOT a theta-decay curve (time value does not
             decay linearly -- see caveats in the output doc).
Cost       : n/a (data pull + BSM, no trading).
Run        : python backtest/experiments/exp_leap_rent.py
Output     : backtest/results/2026-07-12_leap_rent_delta_ledger.md (+ this script also dumps raw
             JSON to backtest/experiments/_leap_rent_raw.json for provenance/re-derivation).
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

RESULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
TARGET_DELTAS = [0.80, 0.50]


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


def pick_expiry(expiries: list[str], lo_days=365, hi_days=456, target_days=410):
    today = pd.Timestamp.now().normalize()
    cands = []
    for e in expiries:
        d = (pd.Timestamp(e) - today).days
        if lo_days <= d <= hi_days:
            cands.append((abs(d - target_days), e, d))
    if not cands:
        return None, None
    cands.sort()
    return cands[0][1], cands[0][2]


def risk_free_rate() -> float:
    try:
        h = yf.Ticker("^IRX").history(period="5d")["Close"]
        return float(h.iloc[-1]) / 100.0
    except Exception:
        return 0.045


def leg_table(symbol: str, vix_symbol: str, r: float) -> dict:
    tkr = yf.Ticker(symbol)
    spot = float(tkr.history(period="5d")["Close"].iloc[-1])
    q = trailing_dividend_yield(tkr, spot)

    expiries = list(tkr.options)
    exp, T_days = pick_expiry(expiries)
    if exp is None:
        return {"symbol": symbol, "error": "no expiry in 365-456d window", "expiries": expiries}
    T = T_days / 365.0

    chain = tkr.option_chain(exp)
    calls = chain.calls.copy()
    calls = calls[(calls["bid"] > 0) & (calls["ask"] > 0) & (calls["impliedVolatility"] > 0.01)].copy()
    calls["delta"] = calls.apply(
        lambda row: call_delta(spot, row["strike"], T, r, q, row["impliedVolatility"]), axis=1
    )

    vix_now = float(yf.Ticker(vix_symbol).history(period="5d")["Close"].iloc[-1])

    rows = {}
    for target in TARGET_DELTAS:
        idx = (calls["delta"] - target).abs().idxmin()
        row = calls.loc[idx]
        bid, ask = float(row["bid"]), float(row["ask"])
        mid = (bid + ask) / 2
        intrinsic = max(spot - float(row["strike"]), 0.0)
        time_value = mid - intrinsic
        rent_raw = time_value / spot
        rent_ann = rent_raw * (365.25 / T_days)
        delta_notional = float(row["delta"]) * spot
        rent_per_delta_raw = time_value / delta_notional if delta_notional else float("nan")
        rent_per_delta_ann = rent_per_delta_raw * (365.25 / T_days)
        leverage = delta_notional / mid if mid else float("nan")
        oi = row.get("openInterest", float("nan"))
        rows[f"{target:.2f}d"] = {
            "target_delta": target,
            "strike": float(row["strike"]),
            "actual_delta": float(row["delta"]),
            "bid": bid, "ask": ask, "mid": mid,
            "spread_pct_of_mid": (ask - bid) / mid if mid else float("nan"),
            "intrinsic": intrinsic, "time_value": time_value,
            "iv": float(row["impliedVolatility"]),
            "open_interest": float(oi) if pd.notna(oi) else None,
            "rent_raw": rent_raw, "rent_annualized": rent_ann,
            "rent_per_delta_raw": rent_per_delta_raw, "rent_per_delta_annualized": rent_per_delta_ann,
            "leverage_delta_per_premium": leverage,
        }
    return {
        "symbol": symbol, "spot": spot, "q_div_yield": q, "r": r,
        "expiry": exp, "T_days": T_days,
        "vix_symbol": vix_symbol, "vix_now": vix_now,
        "rows": rows,
    }


def aa_table(rows_by_sym: dict, ballast_w=0.45, ballast_beta=0.55, thesis_w=0.25, thesis_beta=1.20,
             targets=(1.00, 1.15, 1.30)) -> dict:
    base_delta = ballast_w * ballast_beta + thesis_w * thesis_beta
    out = {
        "base_delta": base_delta,
        "ballast_w": ballast_w, "ballast_beta": ballast_beta,
        "thesis_w": thesis_w, "thesis_beta": thesis_beta,
        "targets": {},
    }
    for tgt in targets:
        needed = tgt - base_delta
        per_leg_needed = needed / 2.0  # SPY/QQQ split 50/50
        leg_detail = {}
        for dsel in TARGET_DELTAS:
            key = f"{dsel:.2f}d"
            prem_pcts = {}
            for sym in ["SPY", "QQQ"]:
                lev = rows_by_sym[sym]["rows"][key]["leverage_delta_per_premium"]
                prem_pcts[sym] = per_leg_needed / lev if lev else float("nan")
            leg_detail[key] = {
                "premium_pct_nav_per_leg": prem_pcts,
                "premium_pct_nav_total": sum(prem_pcts.values()),
            }
        out["targets"][f"{tgt:.2f}"] = {
            "target_delta": tgt, "needed_from_leap": needed, "per_leg_needed": per_leg_needed,
            "by_delta_choice": leg_detail,
        }
    return out


def main():
    r = risk_free_rate()
    out = {"pulled_at": _now_utc(), "r": r, "legs": {}}
    out["legs"]["SPY"] = leg_table("SPY", "^VIX", r)
    out["legs"]["QQQ"] = leg_table("QQQ", "^VXN", r)
    out["aa"] = aa_table(out["legs"])
    out["aa_bear"] = {
        "note": "LEAP delta collapses to 0 (deep OTM / worthless / rolled off before renewal) "
                "-- floor = ballast+thesis sleeves only, LEAP contributes nothing.",
        "floor_delta": out["aa"]["base_delta"],
    }

    dump_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_leap_rent_raw.json")
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))
    print(f"\n[dumped] {dump_path}")


if __name__ == "__main__":
    main()
