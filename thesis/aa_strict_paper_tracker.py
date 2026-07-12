"""thesis/aa_strict_paper_tracker.py -- daily PAPER (no real capital) NAV tracker for the
Karst-AA-strict structure, run in PARALLEL with core v2's existing live signals for a period
before any real-money migration decision (user's explicit call, 2026-07-13: "AA-strict and
core v2 need a parallel run for a while until we know the winner" -- this is that tracker).

Structure being paper-tracked (docs/2026-07-12_all_active_design_response.md Sec2, validated
by BT-2 backtest, results/2026-07-12_bt2_aa_vs_core.md):
  B (ballast) = XLP/XLU/XLV equal-weight trio
  L (LEAP engine) = SPY+QQQ 0.50-delta 1y LEAP, delta target from the regime band, filling
                    whatever delta the B+T sleeves don't already provide
  T (thesis)   = fixed 25% NAV, QQQ as a market-beta PROXY for now (PRELIMINARY judge status --
                 per docs/2026-07-12_all_active_design_response.md Sec8 step 1, T sleeve stays
                 mostly proxy until the judge reaches PASS, then gradually swaps to real themes)

Regime -> band (3-state, matches BT-2's exact model, not the fuller 4-state VIX table in the
design doc's Sec2.2 -- using what was actually BACKTESTED keeps this comparable to the real
BT-2 numbers, not an untested variant):
  0 legs (SPY+QQQ) below 200SMA -> band 1.15 (bull+calm)
  1 leg  below 200SMA           -> band 0.925
  2 legs below 200SMA           -> band 0.0 (fully gated)

LEAP delta target solved in closed form (SIMPLIFICATION vs BT-2's real option-chain math --
this is a daily paper tracker, not a live option pricer):
  leap_delta = [band - T*beta_T - beta_B*(1-T)] / (1 - k*beta_B),  k = 9.55%/115% from the
  real LEAP rent spot-check (results/2026-07-12_leap_rent_delta_ledger.md) -- i.e. a FIXED
  linear premium-per-unit-delta ratio, not a fresh option-chain pull each day. Good enough for
  STRUCTURAL/directional comparison (does this shape of portfolio behave as expected), not for
  penny-accurate $ P&L. LEAP P&L itself is modeled as leap_delta x SPY daily return (delta-
  notional approximation; theta decay is NOT modeled day to day -- flagged explicitly below,
  same "operative = damped, base is upper bound" honesty convention as the rest of Karst's LEAP
  work).

Core v2 comparison column = SPY buy-and-hold NAV (the ~70% base that dominates core v2's own
return). This is NOT core v2's full NAV (that already has its own live tracking via
playbook_readout.py / playbook_log.txt) -- it's a directional reference so the two structures'
SHAPE (drawdown depth, recovery speed) can be eyeballed side by side without re-implementing
core v2's own LEAP overlay math a second time here.

State: thesis/.raw/aa_strict_paper_state.json (gitignored, carries yesterday's NAV forward).
Output: appends one row/day to thesis/.raw/aa_strict_paper_log.jsonl (gitignored, regenerable
by replaying from the start date) AND prints a human-readable line for playbook_log.txt.

Run: python thesis/aa_strict_paper_tracker.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
from backtest.data import load

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(ROOT, ".raw", "aa_strict_paper_state.json")
LOG_PATH = os.path.join(ROOT, ".raw", "aa_strict_paper_log.jsonl")

BALLAST = ["XLP", "XLU", "XLV"]
T_WEIGHT = 0.25             # fixed T-sleeve target (design Sec2.1, PRELIMINARY judge -> proxy)
BAND_OPEN = 1.15            # 0 legs off (bull+calm)
BAND_1OFF = 0.925           # 1 leg off
BAND_2OFF = 0.0             # both legs off
PREMIUM_PER_DELTA = 9.55 / 115.0   # from the real LEAP rent spot-check, 2026-07-12 (SPY+QQQ
                                    # blended 0.50-delta, target 115% delta needs 9.55% NAV)
BETA_WIN, BETA_MINP = 252, 60      # same window BT-2 uses


def _leg_gate(close):
    sma = close.rolling(200).mean()
    return bool(close.iloc[-1] > sma.iloc[-1])


def _rolling_beta(asset_ret, mkt_ret, window=BETA_WIN, min_periods=BETA_MINP):
    cov = asset_ret.rolling(window, min_periods=min_periods).cov(mkt_ret)
    var = mkt_ret.rolling(window, min_periods=min_periods).var()
    return float((cov / var).iloc[-1])


def _load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def run():
    spy = load("SPY")["close"]
    qqq = load("QQQ")["close"]
    ballast_px = {s: load(s)["close"] for s in BALLAST}

    common_idx = spy.index
    for s in [qqq] + list(ballast_px.values()):
        common_idx = common_idx.intersection(s.index)
    spy_c, qqq_c = spy.reindex(common_idx), qqq.reindex(common_idx)
    ballast_c = {s: p.reindex(common_idx) for s, p in ballast_px.items()}

    ballast_ret = pd.concat([p.pct_change() for p in ballast_c.values()], axis=1).mean(axis=1)
    spy_ret = spy_c.pct_change()
    qqq_ret = qqq_c.pct_change()

    beta_B = _rolling_beta(ballast_ret, spy_ret)
    beta_T = _rolling_beta(qqq_ret, spy_ret)
    if not np.isfinite(beta_B) or not np.isfinite(beta_T):
        print("[aa_strict_paper] insufficient history for rolling beta yet -- skipping today")
        return

    spy_off = not _leg_gate(spy_c)
    qqq_off = not _leg_gate(qqq_c)
    n_off = int(spy_off) + int(qqq_off)
    band = {0: BAND_OPEN, 1: BAND_1OFF, 2: BAND_2OFF}[n_off]

    # closed-form solve for leap_delta given B = 1 - T - leap_delta*PREMIUM_PER_DELTA
    # (see module docstring for the derivation)
    denom = 1.0 - PREMIUM_PER_DELTA * beta_B
    leap_delta = max(0.0, (band - T_WEIGHT * beta_T - beta_B * (1.0 - T_WEIGHT)) / denom) \
        if denom > 0 else 0.0
    premium_pct = leap_delta * PREMIUM_PER_DELTA
    b_weight = max(0.0, 1.0 - T_WEIGHT - premium_pct)

    today_str = spy_c.index[-1].date().isoformat()
    state = _load_state()
    if state is None or state.get("last_date") != common_idx[-2].date().isoformat():
        # first run, or state is stale/missing yesterday -- (re)initialize at par, no return
        # applied today (nothing to compound against yet)
        aa_nav, spy_nav = 100.0, 100.0
        note = "initialized at par (no prior-day state to compound from)"
    else:
        r_today_aa = (b_weight * float(ballast_ret.iloc[-1])
                      + T_WEIGHT * float(qqq_ret.iloc[-1])
                      + leap_delta * float(spy_ret.iloc[-1]))
        aa_nav = state["aa_nav"] * (1.0 + r_today_aa)
        spy_nav = state["spy_nav"] * (1.0 + float(spy_ret.iloc[-1]))
        note = f"day return {r_today_aa*100:+.2f}% (AA) vs {float(spy_ret.iloc[-1])*100:+.2f}% (SPY B&H)"

    new_state = {"last_date": today_str, "aa_nav": aa_nav, "spy_nav": spy_nav}
    _save_state(new_state)

    row = {
        "date": today_str, "n_legs_off": n_off, "band": band,
        "beta_ballast": round(beta_B, 3), "beta_T_proxy": round(beta_T, 3),
        "b_weight": round(b_weight, 4), "t_weight": T_WEIGHT,
        "leap_target_delta": round(leap_delta, 4), "leap_premium_pct_nav": round(premium_pct, 4),
        "aa_paper_nav": round(aa_nav, 4), "spy_bh_nav": round(spy_nav, 4),
    }
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"==== {datetime.now():%Y-%m-%d %H:%M} ====")
    print("=== AA-strict PAPER tracker (no real capital -- parallel run vs core v2) ===")
    print(f"regime: {n_off} leg(s) off 200SMA -> band={band:.3f}  "
          f"(beta_B={beta_B:.2f} beta_T={beta_T:.2f})")
    print(f"sleeve weights: B(ballast)={b_weight*100:.1f}%  T(QQQ proxy)={T_WEIGHT*100:.0f}%  "
          f"LEAP premium={premium_pct*100:.2f}% NAV @ target delta {leap_delta*100:.1f}%")
    print(f"AA paper NAV: {aa_nav:.2f}  |  SPY B&H reference NAV: {spy_nav:.2f}  ({note})")
    print("(LEAP leg modeled as delta-notional only -- theta decay NOT simulated day-to-day; "
          "directional/structural comparison only, not penny-accurate P&L)")


if __name__ == "__main__":
    run()
