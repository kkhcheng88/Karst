"""Experiment: LEAP call DELTA sweep (0.30 vs 0.50 vs 0.70 vs 0.80) — never done before.

Question: all prior LEAP backtests used a single fixed 0.80-delta deep-ITM strike.
User constraint rules out short-DTE OTM, but doesn't fix the delta of a 1y LEAP.
Lower delta = more leverage per premium $ (fewer shares-equivalent dollars buy more
convexity) but also more theta bleed (OTM/ATM extrinsic decays faster than deep-ITM
intrinsic-heavy premium) and more vega/gamma risk. Does 0.5Δ or 0.3Δ beat 0.8Δ
risk-adjusted, UNDER the already-proven 200SMA/RSI-2 gates, at REALISTIC costs?

Method (mirror + increment): mirrors exp_leap_timing.py's gate structure (always /
200SMA-gated) and ADDS (a) delta sweep, (b) a third GATED+DIP entry rule (200SMA +
RSI-2<10 dip trigger), (c) realistic costs (0.5%/side base, 1.0%/side sensitivity)
replacing the flagged-too-low 7bps, (d) an RV-based IV term-structure proxy replacing
raw VIX (unavailable in this sandbox — no QQQ/^VIX locally, network blocked), (e) TWO
sizing frames (SLEEVE = 100% compounds in the option; PORTFOLIO = 10% NAV premium
budget / 90% cash, rebalanced at each roll), (f) next-bar execution throughout (no
same-bar look-ahead — exp_leap_timing.py used same-bar gate, a known limitation fixed
here), (g) two-halves (1996-2010 / 2011-2026) + 2016-20/2021+ sub-rows per repo
standard, (h) Jensen alpha vs a SPY total-return B&H proxy for the PORTFOLIO frame.

IV proxy (LIMITATION, not a free lunch — real VIX unavailable in sandbox):
  RV21_ann = 21-day realized vol of daily log returns, annualized (sqrt(252)).
  IV_1y    = max(0.12, 1.25 * RV21_ann) * 0.85          [term-structure haircut]
  Sensitivity variants: multiplier 1.0x and 1.5x instead of 1.25x (the "* 0.85" term
  haircut is held fixed across sensitivity — only the RV->IV multiplier is stressed).
This systematically UNDERSTATES vol-of-vol and skew (no smile, no VIX spikes decoupled
from realized vol e.g. 2018-02 vol event, Aug-2024 unwind) — flagged throughout.

No BSM/scipy import: options_engine.py's bsm.py needs scipy (unavailable in this
sandbox), so the Black-Scholes math is reimplemented standalone below using
math.erf for norm.cdf (verified against textbook values in dev; see prototype).

Costs: 0.5%/side of option premium (base), 1.0%/side (sensitivity) — replaces the
flagged 7bps from exp_leap_timing.py. Charged on both the roll-exit premium and the
new-entry premium (a full roll therefore pays ~2x the per-side rate).

Grid (the WHOLE experiment — no fishing, report every cell):
  delta   in {0.30, 0.50, 0.70, 0.80}
  gate    in {ALWAYS, GATED (200SMA), GATED+DIP (200SMA + RSI-2<10 last 5d)}
  frame   in {SLEEVE (full compounding), PORTFOLIO (10% NAV budget / 90% cash)}
  IV mult in {1.0x, 1.25x (base), 1.5x}   (RV->IV multiplier sensitivity)
  cost    in {0.5%/side (base), 1.0%/side (sensitivity)}
  window  in {FULL 1996-2026, H1 1996-2010, H2 2011-2026, 2016-20, 2021+}

    python backtest/experiments/exp_leap_delta_sweep.py
"""
from __future__ import annotations

import math
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TD = 252
DATA_PKL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        ".insider_data", "sp500_px.pkl")

# ----------------------------------------------------------------------------
# Standalone Black-Scholes (no scipy — math.erf-based norm.cdf, sandbox-safe).
# Mirrors backtest/bsm.py's formulas exactly (continuous dividend yield q,
# time in trading-days/252). Verified vs textbook norm.cdf(0)=0.5,
# norm.cdf(1.96)=0.9750, norm.cdf(-1.645)=0.0500 during development.
# ----------------------------------------------------------------------------

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / 1.4142135623730951))


def _d1d2(S, K, T, r, q, sig):
    vt = sig * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sig * sig) * T) / vt
    return d1, d1 - vt


def call_price(S, K, T, r, q, sig):
    if T <= 0 or sig <= 0:
        return max(S - K, 0.0)
    d1, d2 = _d1d2(S, K, T, r, q, sig)
    return S * math.exp(-q * T) * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)


def call_delta(S, K, T, r, q, sig):
    if T <= 0 or sig <= 0:
        return 1.0 if S > K else 0.0
    d1, _ = _d1d2(S, K, T, r, q, sig)
    return math.exp(-q * T) * norm_cdf(d1)


def call_theta_annual(S, K, T, r, q, sig):
    """Annualized theta as a FRACTION of option premium (bleed rate), central diff
    on T (in years) to avoid re-deriving the analytic theta formula by hand."""
    dT = 1.0 / TD
    T_hi = max(T - dT, 1e-6)
    p0 = call_price(S, K, T, r, q, sig)
    p1 = call_price(S, K, T_hi, r, q, sig)
    if p0 <= 1e-8:
        return 0.0
    daily_bleed = (p0 - p1)          # value lost over 1 trading day, holding S,sig fixed
    return float(daily_bleed / p0 * TD)   # annualized fraction-of-premium bleed rate


def strike_for_call_delta(S, T, r, q, sig, target):
    lo, hi = 0.2 * S, 1.5 * S
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if call_delta(S, mid, T, r, q, sig) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ----------------------------------------------------------------------------
# Data + signals (mirrors backtest/signals.py rsi()/sma() exactly, reimplemented
# standalone to avoid any accidental import of network-touching data.py module).
# ----------------------------------------------------------------------------

def load_spy_close() -> pd.Series:
    with open(DATA_PKL, "rb") as f:
        d = pickle.load(f)
    s = d["SPY"].astype("float64").sort_index()
    s.index = pd.to_datetime(s.index)
    s.index.name = "date"
    return s


def rsi2(close: pd.Series) -> pd.Series:
    period = 2
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period, min_periods=period).mean()


def rv_iv_proxy(close: pd.Series, mult: float = 1.25, floor: float = 0.12,
                term_haircut: float = 0.85) -> pd.Series:
    """IV_1y = max(floor, mult * RV21_annualized) * term_haircut.

    LIMITATION (documented, not silent): this is a realized-vol proxy for implied
    vol, NOT real VIX (unavailable in this sandbox — no ^VIX locally, network
    blocked for Yahoo/FRED/stooq). It structurally misses vol-of-vol, skew, and any
    VIX-realized decoupling (e.g. 2018-02 vol event, Aug-2024 carry unwind) where
    real IV spikes ABOVE what trailing realized vol would suggest. Sensitivity
    variants (mult=1.0, 1.5) are run to bound how much the ranking depends on this
    proxy's calibration.
    """
    logret = np.log(close / close.shift(1))
    rv21 = logret.rolling(21, min_periods=21).std() * math.sqrt(TD)
    iv = np.maximum(floor, mult * rv21) * term_haircut
    return iv


# ----------------------------------------------------------------------------
# Gate construction — next-bar execution throughout (signal computed on bar i,
# ACTED ON at bar i+1 via .shift(1); fixes exp_leap_timing.py's same-bar gate).
# ----------------------------------------------------------------------------

def build_gates(close: pd.Series) -> dict:
    sma200 = sma(close, 200)
    r2 = rsi2(close)
    above = (close > sma200)
    dip_recent = (r2 < 10).rolling(5, min_periods=1).max().astype(bool)  # dip within last 5d

    always = pd.Series(True, index=close.index)
    gated = above.copy()
    # GATED+DIP: enter only when above AND a dip triggered in the last 5 days;
    # exit when below. Modeled as a stateful hold (not a bar-by-bar AND) so that
    # a triggered position isn't force-exited the instant the 5-day dip window
    # rolls off — it holds until the SMA200 exit condition fires.
    gd = np.zeros(len(close), dtype=bool)
    holding = False
    above_v, trig_v = above.values, dip_recent.values
    for i in range(len(close)):
        if not holding and above_v[i] and trig_v[i]:
            holding = True
        elif holding and not above_v[i]:
            holding = False
        gd[i] = holding
    gated_dip = pd.Series(gd, index=close.index)

    # next-bar execution: shift ALL gates by 1 (decision on bar i acted at i+1)
    return {
        "ALWAYS": always.shift(1).astype(bool).fillna(False),
        "GATED": gated.shift(1).astype("boolean").fillna(False).astype(bool),
        "GATED+DIP": gated_dip.shift(1).astype("boolean").fillna(False).astype(bool),
    }


# ----------------------------------------------------------------------------
# LEAP simulator — SLEEVE frame (100% of sleeve compounds in the option, mirrors
# options_engine.simulate_leap structure) + per-day option value / theta / delta
# telemetry needed to derive the PORTFOLIO frame and the leverage/theta metrics.
# ----------------------------------------------------------------------------

def simulate_leap_sleeve(close, iv, gate, target_delta, dte_init=TD, roll_dte=63,
                         r=0.03, q=0.013, cost_pct=0.005, capital=10000.0):
    """Continuously-held long call LEAP, SLEEVE frame (100% compounds in the
    option). Returns dict of arrays: nav, opt_value (per-contract, unit notional),
    delta, theta_ann (bleed rate), in_pos (bool), rolled (bool, True on roll days),
    entered (bool, True on any fresh entry incl. post-gate-exit re-entry).
    """
    close = np.asarray(close, float)
    iv = np.asarray(iv, float)
    gate = np.asarray(gate, bool)
    n = len(close)
    nav = np.full(n, np.nan)
    opt_val = np.full(n, np.nan)          # per-100-notional option value (for telemetry)
    delta_arr = np.full(n, np.nan)
    theta_arr = np.full(n, np.nan)
    in_pos_arr = np.zeros(n, dtype=bool)
    rolled_arr = np.zeros(n, dtype=bool)
    entered_arr = np.zeros(n, dtype=bool)

    cash = capital
    contracts = 0.0
    K = None
    dte = 0
    in_pos = False
    n_rolls = 0
    cost_paid_total = 0.0

    for i in range(n):
        if in_pos and i > 0:
            dte -= 1
        S = close[i]
        sig = max(iv[i], 1e-4) if not math.isnan(iv[i]) else 1e-4
        cash *= (1 + r / TD)
        allowed = bool(gate[i])

        # exit (gated out, or roll due)
        if in_pos and ((not allowed) or dte <= roll_dte):
            T_rem = max(dte / TD, 1e-6)
            opt = call_price(S, K, T_rem, r, q, sig)
            proceeds = contracts * opt * 100 * (1 - cost_pct)
            cost_paid_total += contracts * opt * 100 * cost_pct
            cash += proceeds
            was_roll = (dte <= roll_dte) and allowed
            if was_roll:
                n_rolls += 1
                rolled_arr[i] = True
            contracts, in_pos = 0.0, False

        # enter / re-enter
        if (not in_pos) and allowed and cash > 0:
            T = dte_init / TD
            if math.isnan(iv[i]):
                sig = 0.15  # cold-start fallback before RV21 warms up
            K = strike_for_call_delta(S, T, r, q, sig, target_delta)
            price = call_price(S, K, T, r, q, sig)
            if price > 0:
                cost_paid_total += (cash / (1 + cost_pct)) * cost_pct
                contracts = cash / (price * 100 * (1 + cost_pct))
                cash = 0.0
                dte = dte_init
                in_pos = True
                entered_arr[i] = True

        if in_pos:
            T_rem = max(dte / TD, 1e-6)
            opt = call_price(S, K, T_rem, r, q, sig)
            nav[i] = cash + contracts * opt * 100
            opt_val[i] = opt
            delta_arr[i] = call_delta(S, K, T_rem, r, q, sig)
            theta_arr[i] = call_theta_annual(S, K, T_rem, r, q, sig)
            in_pos_arr[i] = True
        else:
            nav[i] = cash

    return {
        "nav": nav, "opt_value": opt_val, "delta": delta_arr, "theta_ann": theta_arr,
        "in_pos": in_pos_arr, "rolled": rolled_arr, "entered": entered_arr,
        "n_rolls": n_rolls, "cost_paid_total": cost_paid_total,
    }


def portfolio_frame_from_sleeve(close, sleeve, budget_frac=0.10, r=0.03,
                                cost_pct=0.005, capital=10000.0):
    """PORTFOLIO frame: budget_frac of NAV as premium, rebalanced to budget_frac
    AT EACH ROLL/ENTRY (not daily — daily rebalance would be unrealistic/costly
    and isn't what "core strategy" sizing means: you top up the options sleeve
    when you roll, and let it float between rolls). Remainder in cash @ r.

    Mechanically: runs its OWN contracts-count path (independent dollar sizing
    from the SLEEVE frame — budget_frac of ITS OWN NAV) but reuses the SLEEVE's
    per-unit option value / roll-timing path (same strikes/delta/theta — only
    the $ sizing differs).

    TWO liquidation events must be caught, not one:
      (a) gate-driven exit: sleeve's in_pos flips True->False with a genuine
          gap of False days before any re-entry — caught by watching in_pos.
      (b) ROLL: the sleeve closes the OLD contract and opens a NEW one on the
          SAME index (in_pos stays True continuously; entered[i]=True marks
          the roll day). A first cut of this function detected liquidations
          ONLY via the in_pos True->False transition and therefore SILENTLY
          DROPPED the outstanding contracts' value on every roll (re-budgeting
          off `cash` alone, which hadn't yet been credited with the old
          contract's proceeds) — a bug caught in dev via a hand-inspected roll
          date (1997-09-04) showing a fake -25% one-day PORTFOLIO nav drop
          with SLEEVE nav roughly flat that same day. Both (a) and (b) must
          liquidate the OUTSTANDING contracts at the LAST known option value
          (yesterday's mark; today's opt_value may already reflect a brand
          NEW strike) before any re-budgeting.
    """
    close = np.asarray(close, float)
    opt_value = sleeve["opt_value"]
    in_pos = sleeve["in_pos"]
    entered = sleeve["entered"]
    n = len(close)
    nav = np.full(n, np.nan)
    cash = capital
    contracts = 0.0
    prev_ov = 0.0             # last known per-unit option value while held
    was_in_pos = False

    for i in range(n):
        cash *= (1 + r / TD)
        now_in_pos = bool(in_pos[i])
        is_roll_day = now_in_pos and was_in_pos and bool(entered[i]) and contracts > 0.0

        # liquidate OUTSTANDING contracts whenever (a) a gate-driven exit
        # happened (in_pos True->False) or (b) a roll is happening today (old
        # contract closed + new one opened same-index) — in BOTH cases the
        # existing `contracts` were priced at `prev_ov` (yesterday's mark),
        # never at today's opt_value[i] (which is NaN post-gate-exit, or
        # already the NEW strike's price on a roll day).
        if (was_in_pos and not now_in_pos) or is_roll_day:
            cash += contracts * prev_ov * 100 * (1 - cost_pct)
            contracts = 0.0

        if now_in_pos:
            ov = opt_value[i]
            if entered[i] or contracts == 0.0:
                # fresh entry/roll: re-budget to budget_frac of current NAV
                # (now correctly includes the just-liquidated old contract's
                # proceeds), paying entry cost on the new premium (mirrors
                # sleeve's (1+cost) entry convention).
                port_nav_pre = cash
                target_premium = budget_frac * port_nav_pre
                contracts = target_premium / (ov * 100 * (1 + cost_pct)) if ov > 0 else 0.0
                cash = port_nav_pre - target_premium
            nav[i] = cash + contracts * ov * 100
            prev_ov = ov
        else:
            nav[i] = cash

        was_in_pos = now_in_pos

    return nav


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------

def cagr(nav, ann=TD):
    nav = np.asarray(nav, float)
    m = ~np.isnan(nav)
    nav = nav[m]
    if len(nav) < 2 or nav[0] <= 0:
        return float("nan")
    years = (len(nav) - 1) / ann
    if years <= 0:
        return float("nan")
    return (nav[-1] / nav[0]) ** (1 / years) - 1


def ann_sharpe(ret, ann=TD):
    r = ret[~np.isnan(ret)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return float("nan")
    return math.sqrt(ann) * r.mean() / r.std(ddof=1)


def max_drawdown(nav):
    nav = np.asarray(nav, float)
    m = ~np.isnan(nav)
    nav = nav[m]
    if len(nav) < 2:
        return float("nan")
    peak = np.maximum.accumulate(nav)
    return float((nav / peak - 1.0).min())


def nav_to_ret(nav):
    nav = np.asarray(nav, float)
    ret = np.full(len(nav), np.nan)
    valid = ~np.isnan(nav)
    idx = np.where(valid)[0]
    for k in range(1, len(idx)):
        i0, i1 = idx[k - 1], idx[k]
        if i1 == i0 + 1 and nav[i0] > 0:
            ret[i1] = nav[i1] / nav[i0] - 1
    return ret


def jensen_alpha(strat_ret, mkt_ret, ann=TD):
    y = np.asarray(strat_ret, float)
    x = np.asarray(mkt_ret, float)
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    n = len(x)
    if n < 30:
        return (float("nan"), float("nan"), float("nan"))
    X = np.column_stack([np.ones(n), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    s2 = float(resid @ resid) / (n - 2)
    xtx_inv = np.linalg.inv(X.T @ X)
    se_a = math.sqrt(max(s2 * xtx_inv[0, 0], 0))
    t_a = coef[0] / se_a if se_a > 0 else float("nan")
    return (float(coef[0] * ann), float(coef[1]), float(t_a))


def spy_bh_total_return(close: pd.Series, div_yield_net=0.0105):
    """SPY B&H total-return proxy: price return + net dividend drip (1.05%/yr net
    of 30% HK withholding on the gross ~1.5%/yr SPY yield, per user spec), applied
    as a smooth daily drip since a real dividend calendar is unavailable in this
    price-only pickle (no distributions data)."""
    ret = close.pct_change().fillna(0.0).values
    ret = ret + div_yield_net / TD
    nav = np.cumprod(1.0 + ret) * 10000.0
    nav[0] = 10000.0
    return nav, ret


# ----------------------------------------------------------------------------
# Per-cell metric bundle
# ----------------------------------------------------------------------------

def cell_metrics(nav, close_slice, sleeve_bundle_slice, gate_slice, bh_ret_slice,
                 frame, cost_pct):
    ret = nav_to_ret(nav)
    c = cagr(nav)
    sh = ann_sharpe(ret)
    dd = max_drawdown(nav)
    out = {"CAGR": c, "Sharpe": sh, "MaxDD": dd, "N": int((~np.isnan(nav)).sum())}

    if frame == "PORTFOLIO":
        a, b, t = jensen_alpha(ret, bh_ret_slice)
        out["Alpha"] = a
        out["Beta"] = b
        out["tstat"] = t

    delta_arr = sleeve_bundle_slice["delta"]
    theta_arr = sleeve_bundle_slice["theta_ann"]
    opt_val = sleeve_bundle_slice["opt_value"]
    in_pos = sleeve_bundle_slice["in_pos"]
    S = np.asarray(close_slice, float)

    if in_pos.sum() > 0:
        with np.errstate(invalid="ignore", divide="ignore"):
            eff_lev = (delta_arr * S) / opt_val  # contract multiplier (x100) cancels num/denom
        eff_lev = eff_lev[in_pos & np.isfinite(eff_lev)]
        out["EffLev"] = float(np.mean(eff_lev)) if len(eff_lev) else float("nan")
        th = theta_arr[in_pos & np.isfinite(theta_arr)]
        out["ThetaBleed"] = float(np.mean(th)) if len(th) else float("nan")
    else:
        out["EffLev"] = float("nan")
        out["ThetaBleed"] = float("nan")

    out["NRolls"] = int(sleeve_bundle_slice["rolled"].sum())
    out["Exposure"] = float(np.mean(gate_slice))
    return out


def cost_drag_pct_per_yr(nav_with_cost, nav_zero_cost):
    c_with = cagr(nav_with_cost)
    c_without = cagr(nav_zero_cost)
    if math.isnan(c_with) or math.isnan(c_without):
        return float("nan")
    return (c_without - c_with) * 100  # percentage points/yr


# ----------------------------------------------------------------------------
# Windows (repo standard: two-halves + 2016-20/2021+ sub-rows)
# ----------------------------------------------------------------------------

WINDOWS = [
    ("FULL 1996-2026", "1996-01-01", "2026-12-31"),
    ("H1 1996-2010", "1996-01-01", "2010-12-31"),
    ("H2 2011-2026", "2011-01-01", "2026-12-31"),
    ("2016-2020", "2016-01-01", "2020-12-31"),
    ("2021+", "2021-01-01", "2026-12-31"),
]

DELTAS = [0.30, 0.50, 0.70, 0.80]
GATES = ["ALWAYS", "GATED", "GATED+DIP"]


def run_variant(close, iv_mult, cost_pct, label):
    """Run the full delta x gate grid (both frames) for one (iv_mult, cost_pct)
    setting. Returns nested dict: [delta][gate][frame][window] -> metrics dict.

    Also runs a ZERO-COST shadow simulation per (delta, gate) to compute total
    cost drag %/yr = zero-cost CAGR - actual CAGR, per window (SLEEVE frame —
    the drag is a property of the option roll mechanics, same rolls/timing in
    both frames since PORTFOLIO reuses the SLEEVE's roll schedule).
    """
    iv = rv_iv_proxy(close, mult=iv_mult)
    gates = build_gates(close)
    bh_nav, bh_ret = spy_bh_total_return(close)

    results = {}
    for delta in DELTAS:
        results[delta] = {}
        for gname in GATES:
            gate = gates[gname].values
            sleeve = simulate_leap_sleeve(close.values, iv.values, gate,
                                          target_delta=delta, cost_pct=cost_pct)
            sleeve_zero_cost = simulate_leap_sleeve(close.values, iv.values, gate,
                                                    target_delta=delta, cost_pct=0.0)
            port_nav = portfolio_frame_from_sleeve(close.values, sleeve, cost_pct=cost_pct)

            results[delta][gname] = {}
            for wname, wstart, wend in WINDOWS:
                mask = (close.index >= wstart) & (close.index <= wend)
                idx = np.where(np.asarray(mask))[0]
                if len(idx) < 30:
                    continue
                lo, hi = idx[0], idx[-1] + 1
                slice_bundle = {k: (v[lo:hi] if isinstance(v, np.ndarray) else v)
                                for k, v in sleeve.items()}

                sleeve_nav = sleeve["nav"][lo:hi]
                sleeve_nav = sleeve_nav / sleeve_nav[~np.isnan(sleeve_nav)][0] * 10000.0 \
                    if (~np.isnan(sleeve_nav)).any() else sleeve_nav
                m_sleeve = cell_metrics(sleeve_nav, close.values[lo:hi], slice_bundle,
                                        gate[lo:hi], bh_ret[lo:hi], "SLEEVE", cost_pct)

                zc_nav = sleeve_zero_cost["nav"][lo:hi]
                zc_nav = zc_nav / zc_nav[~np.isnan(zc_nav)][0] * 10000.0 \
                    if (~np.isnan(zc_nav)).any() else zc_nav
                drag = cost_drag_pct_per_yr(sleeve_nav, zc_nav)
                m_sleeve["CostDrag"] = drag

                port_nav_w = port_nav[lo:hi]
                port_nav_w = port_nav_w / port_nav_w[~np.isnan(port_nav_w)][0] * 10000.0 \
                    if (~np.isnan(port_nav_w)).any() else port_nav_w
                m_port = cell_metrics(port_nav_w, close.values[lo:hi], slice_bundle,
                                      gate[lo:hi], bh_ret[lo:hi], "PORTFOLIO", cost_pct)
                m_port["CostDrag"] = drag  # same roll schedule/cost-rate drives both frames

                results[delta][gname][wname] = {"SLEEVE": m_sleeve, "PORTFOLIO": m_port}

    return results, gates, bh_nav, bh_ret


def fmt_row(m):
    a = m.get("Alpha")
    astr = f"{a*100:+6.2f}%(t{m['tstat']:+4.1f})" if a is not None and not math.isnan(a) else "      --      "
    drag = m.get("CostDrag", float("nan"))
    dragstr = f"{drag:5.1f}pp/yr" if not math.isnan(drag) else "   -- "
    return (f"CAGR {m['CAGR']*100:+7.2f}%  Sharpe {m['Sharpe']:5.2f}  "
            f"MaxDD {m['MaxDD']*100:7.1f}%  Alpha {astr}  "
            f"EffLev {m['EffLev']:4.2f}x  Theta {m['ThetaBleed']*100:6.1f}%/yr  "
            f"Rolls {m['NRolls']:4d}  Expo {m['Exposure']*100:5.1f}%  CostDrag {dragstr}")


def main():
    close = load_spy_close()
    print(f"SPY loaded: {close.index.min().date()} -> {close.index.max().date()}, "
          f"{len(close)} days")

    bh_nav, bh_ret = spy_bh_total_return(close)
    print(f"SPY B&H total-return proxy: CAGR {cagr(bh_nav)*100:.2f}%  "
          f"Sharpe {ann_sharpe(bh_ret):.2f}  MaxDD {max_drawdown(bh_nav)*100:.1f}%")

    variants = [
        ("BASE (IVx1.25, cost 0.5%/side)", 1.25, 0.005),
        ("SENS: IVx1.00", 1.00, 0.005),
        ("SENS: IVx1.50", 1.50, 0.005),
        ("SENS: cost 1.0%/side", 1.25, 0.010),
    ]

    all_results = {}
    for label, iv_mult, cost_pct in variants:
        print(f"\n{'='*100}\nVARIANT: {label}\n{'='*100}")
        results, gates, _, _ = run_variant(close, iv_mult, cost_pct, label)
        all_results[label] = results

        for delta in DELTAS:
            print(f"\n--- delta={delta:.2f} ---")
            for gname in GATES:
                for wname, _, _ in WINDOWS:
                    if wname not in results[delta][gname]:
                        continue
                    cell = results[delta][gname][wname]
                    print(f"  [{gname:10}][{wname:14}][SLEEVE   ] {fmt_row(cell['SLEEVE'])}")
                    print(f"  [{gname:10}][{wname:14}][PORTFOLIO] {fmt_row(cell['PORTFOLIO'])}")

    # Cache full nested results for the results-writer step (avoid re-running).
    cache_path = "/tmp/leap_sweep_cache/all_results.pkl"
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "wb") as f:
        pickle.dump({"all_results": all_results, "bh_cagr": cagr(bh_nav),
                    "bh_sharpe": ann_sharpe(bh_ret), "bh_maxdd": max_drawdown(bh_nav)}, f)
    print(f"\nCached nested results -> {cache_path}")


if __name__ == "__main__":
    main()
