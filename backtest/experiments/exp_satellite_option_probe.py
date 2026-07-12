"""exp_satellite_option_probe.py — satellite-theme option-expression feasibility probe.

Question   : Karst's two-tier design gives the options toolkit only to SPY/QQQ/SPMO; every
             Phase-3 satellite name is long-only stock. But core v2's own biggest structural
             finding is that LEVERAGE (a LEAP call, not the underlying) is what turns timing
             skill into real outperformance -- premium=max-loss is a natural kill discipline,
             and convexity payoff naturally "eats" the magnitude axis Phase-3 theses are
             explicitly betting on (2-3x / 5-10x-binary magnitude_tier tags in themes.yaml).
             This probe asks: for a sample of satellite names, is a long-dated call CURRENTLY
             tradeable (does a LEAP expiry exist, are spread/OI/IV sane), and how does a
             stock-vs-option expression of the same dollar target compare under a real
             current quote?
             *** This is a MARKET-STRUCTURE FEASIBILITY CHECK on TODAY's live chain, NOT a
             backtest.*** yfinance exposes only the current option chain snapshot -- there is
             no free historical options-chain data source to backtest an option overlay
             against (same limitation exp_chain_spotcheck.py already documented for SPY/QQQ).
Method     : yfinance live option_chain() per name (identical method to
             backtest/playbook_readout.py's LEAP-quote block and
             backtest/experiments/exp_chain_spotcheck.py), BSM (backtest/bsm.py) delta from
             the chain's own impliedVolatility per strike, pick the expiry closest to 365d
             within [330,420]d (fallback: longest available expiry >250d, flagged as
             "no true LEAP"), pick the strike closest to 0.50 delta (the flagship LEAP
             delta used elsewhere in this repo). Then a worked demonstration: MU
             (memory-supercycle thesis, $3,000 target satellite allocation) Plan A = all
             stock vs Plan B = $1,000 premium into the 0.50d LEAP call + $2,000 cash, P&L
             under MU +100% / MU -40% AT EXPIRY (intrinsic value only -- no invented IV
             path or theta decay schedule; real current spot + real current quote).
Cost       : n/a (data pull + BSM, no trading).
Run        : python backtest/experiments/exp_satellite_option_probe.py
Output     : backtest/results/2026-07-12_satellite_option_expression_probe.md (this script
             prints + dumps raw JSON to
             backtest/experiments/_satellite_option_probe_raw.json for provenance / re-run).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yfinance as yf

from bsm import call_delta

TARGET_DELTA = 0.50
RESULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

# ticker -> (theme, ttm_pe percentile note pulled from thesis/themes.yaml, for context only)
THEME_MAP = {
    "MU":   "memory-supercycle (late, cushioned by LTA; confidence 0.38)",
    "FSLR": "us-solar-manufacturing (22nd pctile PE, cheapest of discovery-radar batch; confidence 0.30)",
    "ASML": "euv-lithography-monopoly (98th pctile PE, most priced-in; confidence 0.22)",
    "AVGO": "tpu-custom-silicon (75-87th pctile chain; confidence 0.25)",
    "ETN":  "ai-power-grid / grid-hardware node (99th pctile PE; confidence 0.33 theme-level)",
    "TSM":  "tpu-custom-silicon (eroded-incumbent framing per note; confidence 0.25)",
    "WST":  "glp1-biologics-packaging (71st pctile PE; confidence 0.27)",
    "LPX":  "building-products / specialty-siding (95th pctile whole-co PE; confidence 0.20)",
    "USAC": "gas-compression-equipment (2nd pctile PE, most undiscovered; confidence 0.33)",
    "ATI":  "aerospace-specialty-alloys (98th pctile PE; confidence 0.24)",
    "GEV":  "ai-power-grid / grid-hardware node (magnitude_tier 2-3x; confidence 0.33 theme-level)",
    "COHR": "photonics-optical (most crowded cluster, 58% bull; confidence 0.30)",
}

TICKERS = list(THEME_MAP.keys())


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


def risk_free_rate() -> float:
    try:
        irx = yf.Ticker("^IRX").history(period="5d")["Close"].iloc[-1]
        return float(irx) / 100.0
    except Exception:
        return 0.045  # T-bill proxy fallback, matches exp_chain_spotcheck.py


def pick_leap_expiry(expiries: list[str]) -> tuple[str | None, bool]:
    """Returns (expiry, is_true_leap). True LEAP = 330-420d window closest to 365d.
    Fallback = longest available expiry if it's >250d (flagged not-true-LEAP)."""
    today = pd.Timestamp.now().normalize()
    dte = [(e, (pd.Timestamp(e) - today).days) for e in expiries]
    true_leap = [(e, d) for e, d in dte if 330 <= d <= 420]
    if true_leap:
        true_leap.sort(key=lambda x: abs(x[1] - 365))
        return true_leap[0][0], True
    long_dated = [(e, d) for e, d in dte if d > 250]
    if long_dated:
        long_dated.sort(key=lambda x: -x[1])
        return long_dated[0][0], False
    return None, False


def probe_ticker(symbol: str, r: float) -> dict:
    out = {"symbol": symbol, "theme": THEME_MAP.get(symbol, "?")}
    try:
        tkr = yf.Ticker(symbol)
        hist = tkr.history(period="5d")["Close"].dropna()
        if len(hist) == 0:
            out["error"] = "no price history"
            return out
        spot = float(hist.iloc[-1])
        out["spot"] = spot
        q = trailing_dividend_yield(tkr, spot)
        out["div_yield"] = q

        expiries = list(tkr.options)
        out["n_expiries"] = len(expiries)
        if not expiries:
            out["error"] = "no options chain listed"
            return out

        exp, is_true_leap = pick_leap_expiry(expiries)
        if exp is None:
            longest = max(((pd.Timestamp(e) - pd.Timestamp.now().normalize()).days for e in expiries), default=0)
            out["error"] = f"no expiry >250d (longest listed = {longest}d)"
            return out

        dte = (pd.Timestamp(exp) - pd.Timestamp.now().normalize()).days
        out["expiry"] = exp
        out["dte"] = int(dte)
        out["is_true_leap"] = is_true_leap
        T = dte / 365.0

        chain = tkr.option_chain(exp)
        calls = chain.calls.copy()
        calls = calls[(calls["bid"] >= 0) & (calls["ask"] > 0) & (calls["impliedVolatility"] > 0.01)]
        if len(calls) == 0:
            out["error"] = "call chain empty/unquoted at picked expiry"
            return out

        calls["delta"] = calls.apply(
            lambda row: call_delta(spot, row["strike"], T, r, q, row["impliedVolatility"]), axis=1
        )
        idx = (calls["delta"] - TARGET_DELTA).abs().idxmin()
        row = calls.loc[idx]

        bid, ask = float(row["bid"]), float(row["ask"])
        mid = (bid + ask) / 2 if bid > 0 else float(row.get("lastPrice", ask))
        spread = ask - bid
        spread_pct = spread / mid if mid else float("nan")
        delta = float(row["delta"])
        oi = float(row.get("openInterest", 0) or 0)
        vol = float(row.get("volume", 0) or 0)
        iv = float(row["impliedVolatility"])

        # leverage_multiple = delta-notional bought per $1 of premium, vs $1 of stock (=1x)
        leverage_multiple = (delta * spot / mid) if mid else float("nan")

        out.update({
            "strike": float(row["strike"]),
            "delta": delta,
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spread": spread,
            "spread_pct": spread_pct,
            "open_interest": oi,
            "volume": vol,
            "iv": iv,
            "leverage_multiple": leverage_multiple,
        })

        # liquidity classification
        if spread_pct < 0.10 and oi >= 50:
            verdict = "viable"
        elif spread_pct < 0.25 and oi >= 10:
            verdict = "marginal"
        else:
            verdict = "not viable"
        if not is_true_leap:
            verdict += " (no true 12m+ LEAP -- longest available used)"
        out["verdict"] = verdict
        return out
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        return out


def _scenario_table(S, K, budget, contracts, premium_spent, cash, plan_a_shares):
    scenarios = {}
    for label, mult in [("MU +100%", 2.0), ("MU -40%", 0.6)]:
        s_new = S * mult
        a_value = plan_a_shares * s_new
        a_pnl = a_value - budget
        opt_intrinsic = contracts * max(s_new - K, 0.0) * 100
        b_value = opt_intrinsic + cash
        b_pnl = b_value - budget
        scenarios[label] = {
            "S_new": s_new,
            "plan_a_value": a_value,
            "plan_a_pnl": a_pnl,
            "plan_b_option_intrinsic": opt_intrinsic,
            "plan_b_cash": cash,
            "plan_b_value": b_value,
            "plan_b_pnl": b_pnl,
        }
    return scenarios


def mu_demo(mu_row: dict) -> dict:
    """Plan A (all-stock) vs Plan B (premium into 0.50d LEAP call + cash), MU +100% / MU -40%
    scenarios, at-expiry intrinsic value only.

    MU's own re-rating (spot ~$979, per memory-supercycle late-cycle thesis) makes the literal
    task-scoped sizing ($1,000 premium / $3,000 total) arithmetically infeasible: the picked
    0.50d contract costs $20,575, and even the CHEAPEST strike on the whole chain (deep OTM,
    delta~0.27) costs ~$9,108/contract -- no strike fits a $3,000 budget. We therefore report
    BOTH:
      (a) "as_specified" -- literal $1,000/$2,000/$3,000 sizing using FRACTIONAL contracts, to
          answer the two-scenario P&L question exactly as asked. Explicitly labeled
          non-executable (real brokers do not sell fractional option contracts).
      (b) "min_tradeable" -- the smallest REAL, executable trade (1 whole contract), with cash
          scaled to preserve the requested 1:2 premium:cash ratio, and Plan A sized to the same
          total budget for a fair comparison.
    """
    S = mu_row["spot"]
    K = mu_row["strike"]
    mid = mu_row["mid"]
    delta = mu_row["delta"]
    premium_per_contract = mid * 100

    # (a) as-specified: literal $1,000 premium / $2,000 cash / $3,000 total, fractional contracts
    budget_spec = 3000.0
    option_budget_spec = 1000.0
    contracts_spec = option_budget_spec / premium_per_contract  # fractional, illustrative only
    premium_spent_spec = contracts_spec * premium_per_contract
    cash_spec = budget_spec - premium_spent_spec
    plan_a_shares_spec = budget_spec / S
    as_specified = {
        "note": "ILLUSTRATIVE ONLY -- fractional contracts (%.4f) are not tradeable; shown to "
                "answer the literal $1,000-premium/$3,000-total sizing as asked." % contracts_spec,
        "contracts": contracts_spec,
        "premium_spent": premium_spent_spec,
        "cash_held": cash_spec,
        "plan_a_shares": plan_a_shares_spec,
        "plan_a_max_loss": -budget_spec,
        "plan_b_max_loss": -premium_spent_spec,
        "scenarios": _scenario_table(S, K, budget_spec, contracts_spec, premium_spent_spec,
                                      cash_spec, plan_a_shares_spec),
    }

    # (b) min-tradeable: 1 whole contract, cash = 2x premium (preserves the 1:2 ratio), Plan A
    # gets the same total budget so the comparison stays apples-to-apples.
    contracts_min = 1
    premium_spent_min = contracts_min * premium_per_contract
    cash_min = 2.0 * premium_spent_min
    budget_min = premium_spent_min + cash_min
    plan_a_shares_min = budget_min / S
    min_tradeable = {
        "note": "smallest REAL executable trade: 1 whole contract; cash sized 2x premium to "
                "preserve the requested 1:2 ratio; total budget therefore scales to $%.0f "
                "(~%.1fx the task's nominal $3,000 satellite slice)." % (
                    budget_min, budget_min / 3000.0),
        "budget_total": budget_min,
        "contracts": contracts_min,
        "premium_spent": premium_spent_min,
        "cash_held": cash_min,
        "plan_a_shares": plan_a_shares_min,
        "plan_a_max_loss": -budget_min,
        "plan_b_max_loss": -premium_spent_min,
        "scenarios": _scenario_table(S, K, budget_min, contracts_min, premium_spent_min,
                                      cash_min, plan_a_shares_min),
    }

    return {
        "spot": S,
        "strike": K,
        "mid_premium_per_contract": premium_per_contract,
        "delta": delta,
        "leverage_multiple": mu_row.get("leverage_multiple"),
        "affordability_finding": "no strike on MU's LEAP-length chain fits a $3,000 (or even "
                                  "$1,000) total budget -- cheapest available strike (deep OTM, "
                                  "~0.27d) still costs ~$9,108/contract; the 0.50d flagship "
                                  "strike costs $20,575/contract.",
        "as_specified": as_specified,
        "min_tradeable": min_tradeable,
    }


def mu_cheapest_strike(mu_row: dict, r: float) -> dict:
    """Reproducible evidence for the affordability finding: scans MU's own picked-expiry call
    chain (same expiry probe_ticker already selected) for the single cheapest premium/contract
    available at ANY strike, and separately checks whether any strike fits <=$3,000/contract."""
    try:
        symbol = mu_row["symbol"]
        exp = mu_row["expiry"]
        spot = mu_row["spot"]
        q = mu_row["div_yield"]
        T = mu_row["dte"] / 365.0
        tkr = yf.Ticker(symbol)
        calls = tkr.option_chain(exp).calls.copy()
        calls = calls[(calls["bid"] >= 0) & (calls["ask"] > 0) & (calls["impliedVolatility"] > 0.01)]
        calls["delta"] = calls.apply(
            lambda row: call_delta(spot, row["strike"], T, r, q, row["impliedVolatility"]), axis=1
        )
        calls["mid"] = calls.apply(lambda row: (row["bid"] + row["ask"]) / 2, axis=1)
        calls["premium_per_contract"] = calls["mid"] * 100
        cheapest = calls.loc[calls["premium_per_contract"].idxmin()]
        under_3000 = calls[calls["premium_per_contract"] <= 3000.0]
        return {
            "expiry": exp,
            "n_strikes_scanned": int(len(calls)),
            "cheapest_strike": float(cheapest["strike"]),
            "cheapest_delta": float(cheapest["delta"]),
            "cheapest_bid": float(cheapest["bid"]),
            "cheapest_ask": float(cheapest["ask"]),
            "cheapest_mid": float(cheapest["mid"]),
            "cheapest_premium_per_contract": float(cheapest["premium_per_contract"]),
            "n_strikes_under_3000_premium": int(len(under_3000)),
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main():
    r = risk_free_rate()
    out = {"pulled_at": _now_utc(), "risk_free_rate": r, "target_delta": TARGET_DELTA, "tickers": {}}

    for sym in TICKERS:
        print(f"probing {sym} ...", file=sys.stderr)
        out["tickers"][sym] = probe_ticker(sym, r)

    mu = out["tickers"].get("MU", {})
    if "strike" in mu:
        print("scanning MU chain for cheapest strike ...", file=sys.stderr)
        out["mu_cheapest_strike"] = mu_cheapest_strike(mu, r)
        out["mu_demo"] = mu_demo(mu)
    else:
        out["mu_demo"] = {"error": "MU chain probe failed, cannot build demo"}

    dump_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_satellite_option_probe_raw.json")
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)

    print(json.dumps(out, indent=2, default=str))
    print(f"\n[dumped] {dump_path}")


if __name__ == "__main__":
    main()
