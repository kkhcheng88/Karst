"""LOOP 4 (final loop, real-data core-strategy search) — FIX the cash-starvation
mechanism `exp_core_assembly_real.py` (this repo's "Loop-3") discovered, and close
the model-risk disclosure gap (every cell now reports base AND IV-damped alpha).

Background (settled, not re-tested here — see backtest/results/2026-07-06_core_assembly_real.md)
--------
Loop-3 assembled SPY core (never trend-sold) + a 200SMA-GATED deep-ITM LEAP sleeve
(PORTFOLIO premium-budget frame, real ^VIX/^VXN engine from `exp_leap_real_sweep.py`)
+ a cash buffer (^IRX), ANNUAL rebalance + roll-time profit sweep back to core.
Finding: the annual-only cash top-up starves the sleeve — 40-60% of the days each
leg's OWN 200SMA gate says "eligible to hold", the sim actually carried ZERO
contracts because the shared cash pool could not fund the fresh b*NAV premium
target between annual rebalances. Direct proof the rebalance/cash machinery IS the
alpha engine (not cosmetic): cash=0% or annual-rebalance-OFF collapses alpha to
~0 (headline b20/D0.50/SPY+QQQ: +7.8pp(t+4.1) -> +0.3pp(t+0.9)). Also: the
Delta=0.50 mix cells' headline alpha (best under BASE IV) shrinks hard under an
IV-damping model-risk sensitivity (+7.8pp(t+4.1) -> +2.8pp(t+1.7), b15/b10
similar) — but Loop-3 never ran that damping sensitivity on Delta=0.70/0.80 (lower
vega, expected to be more damp-resistant), so the asymmetry (only Delta=0.50 gets
the honest stress test) is an open disclosure gap this loop closes.

Question
--------
(1) Does a HIGHER-FREQUENCY / EVENT-TIED cash top-up rule fix the cash-starvation
    mechanism (mechanical liquidity fix, NOT a new market-timing signal) better
    than Loop-3's annual-only rebalance? (2) Does the Delta=0.50 dominance survive
    once EVERY cell (not just the Delta=0.50 top-3) is stress-tested under
    IV-damping? Pre-registered 4(rule) x 2(b) x 3(delta) = 24-cell grid, mix FIXED
    to SPY+QQQ 50/50 (Loop-3 proved mix beats SPY-only at every (b,delta) pair on
    the identical window — not re-tested here). b capped at {10%,15%} (20% already
    known to breach the user's MaxDD tolerance band, per Loop-3's own caveats).

Method (mirror / increment / horizon)
------
Mirror     : same 3-bucket program the user would actually run (core + LEAP
             sleeve(s) + cash), same real ^VIX/^VXN/^IRX data, same benchmark
             (SPY B&H total return, HK 30% dividend withholding netted).
Increment  : ONLY the fund-replenishment rule (axis 1 below) and the disclosure
             scope (damp=0.4 now run on ALL 24 cells, not just a top-3) are new.
             The LEAP unit engine (`simulate_unit_path`, option marks/gate/roll)
             is IMPORTED verbatim from `exp_leap_real_sweep.py`; the core-equity
             benchmark/return series, the IV-damping method (`damp_iv`), the
             annual-rebalance mechanics (rule A, reproduced byte-for-byte as the
             control arm) and several report-formatting helpers are IMPORTED from
             `exp_core_assembly_real.py` (this repo's "Loop-3") — not reimplemented.
Horizon    : continuous multi-year program; LEAP rolled at 63 trading days
             remaining (engine default, unchanged); rebalance/top-up cadence is
             the ONLY thing varying across the rule axis.

Pre-registered grid (run all, report all — nothing else)
------
  axis 1 (fund-replenishment RULE — mechanical liquidity fix, NOT a signal):
    A-annual    : Loop-3 status quo (CONTROL). SYMMETRIC core:cash rebalance to
                  target weights at the first trading day of each calendar year,
                  fired AFTER that bar's leg processing (byte-identical order to
                  exp_core_assembly_real.py's annual_rebalance=True path).
    B-quarterly : ASYMMETRIC FLOOR top-up at the first trading day of each
                  calendar quarter: if cash < b*NAV, pull the shortfall from core
                  into cash; if cash already >= b*NAV, do NOTHING (no forced sale
                  of cash back into core — floor, not a rebalance). Fired BEFORE
                  that bar's leg processing so the top-up can fund THAT bar's buys.
    C-monthly   : same floor top-up, first trading day of each calendar month.
    D-onroll    : same floor top-up, fired on any bar where EITHER leg's own
                  63td-remaining ROLL fires (`unit["rolled"]`, i.e. the periodic
                  re-entry retry point when a leg's cash was insufficient at a
                  prior buy — the natural cadence this rule targets).
    NOTE (disclosed limitation): D ties the top-up to the ROLL event specifically
    (dte<=63 while gate remains open), NOT to a fresh gate re-entry after a
    trend-down exit — a fresh re-entry after being fully gated out is a `buy`
    event but not a `rolled` event, so D may still leave some post-re-entry days
    unfunded until the position's own first roll ~189td later. Reported honestly,
    not smoothed over (see Caveats).
  axis 2 (b, premium budget)  : {10%, 15%} of NAV (20% excluded: known to already
                                breach the user's MaxDD tolerance band).
  axis 3 (Delta)              : {0.50, 0.70, 0.80} (1y call, GATED, roll @ 63td;
                                0.30D cap and DIP/HYST gate variants already
                                settled elsewhere, not re-tested here).
  axis 4 (LEAP underlying mix): FIXED to 50/50 SPY+QQQ (Loop-3 pre-registered
                                finding: mix beats SPY-only at every (b,delta)
                                pair on the identical 2001+ window).
  = 4 x 2 x 3 = 24 cells. Windows: FULL (2001+, native start of the SPY+QQQ mix
  common window) as PRIMARY, + H2 2011-2026 / 2016-2020 / 2021+ (H1 2001-2010
  dropped from the printed tables — it is a strict subset of FULL here and was
  the source of a labeling-lookup artifact in Loop-3's own sub-window table for
  mix cells; not a new finding, just not re-litigated).

Disclosure requirement (fixing Loop-3's asymmetry — the actual point of this loop)
------
EVERY one of the 24 cells reports BOTH a base-IV (m=0.85) row and an IV-damped
(damp=0.4) row on the PRIMARY (FULL 2001+) window — no cell is allowed to report
base only. Damping: sigma_damped = sigma_bar + damp*(sigma_raw - sigma_bar),
sigma_bar = full-sample mean of that leg's OWN raw IV_1y proxy over its own full
native availability window — `damp_iv()` imported verbatim from
`exp_core_assembly_real.py` (same method Loop-3's own adversarial review already
checked; not reinvented here). Damping repriced marks/strikes only; it does not
touch the 200SMA gate (price-driven, unaffected), so roll timing (and hence the
D-onroll trigger) is PROVABLY IV-independent — verified by construction, not
re-derived per iv-variant.

Winner-selection rule (pre-registered BEFORE running the grid, not picked after
seeing numbers)
------
1. Rank all 24 cells by DAMP=0.4 Jensen-alpha t-stat on the FULL(2001+) window,
   descending.
2. Filter to cells whose DAMP=0.4 MaxDD >= -56% (the user's MaxDD tolerance
   ceiling — interpreting "-56%" as a FLOOR on returns / CEILING on drawdown
   magnitude: MaxDD must not be WORSE than -56%, consistent with Loop-3's own use
   of ~-55.6% (SPY's own historical MaxDD) as the practical tolerance edge, and
   with why b=20% was excluded from this grid).
3. Among survivors, take the highest-ranked (by damp t-stat) cell that ALSO
   places in the top 6 (25% of 24) by BASE-IV alpha t-stat — i.e. reject a pick
   that only looks good under one IV assumption ("base and damp rankings must
   roughly agree").
4. If the winner's Delta != 0.50, state plainly that the more-aggressive/lower-
   vega delta needs real options-chain validation before being trusted over the
   0.50-delta result (pre-registered contingency, not a post-hoc excuse).

Statistical discipline
------
Registry = THIS loop's 24 cells + Loop-3's 18 cells = 42 cumulative trials
(hardcoded Loop-3 Sharpes below, sourced from its results file's main table,
native FULL window, base IV/cost — NOT re-run here, just cited). Bonferroni
(normal-approx p x42) and DSR (`backtest.metrics.deflated_sharpe_ratio`, fed the
winner's REAL daily-return series + the 42-cell annualized-Sharpe universe) are
reported for the winning cell.

Cross-foot (hard asserts, every bar of every accounting run): NAV = core + cash +
sum(option market value); cash >= 0; NAV > 0; NAV_t = NAV_{t-1} + interest + core
P&L + option P&L - costs (both the annual rebalance AND the new floor top-up are
zero-sum internal transfers between core_val/cash, so neither appears in this
identity — matches exp_core_assembly_real.py's convention exactly).

Run:  PYTHONUTF8=1 python backtest/experiments/exp_core_topup.py
Writes: backtest/results/2026-07-06_core_topup.md
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metrics                                    # noqa: E402
from data import load                             # noqa: E402
from exp_leap_real_sweep import (                  # noqa: E402
    build_underlying, build_gates, simulate_unit_path, make_windows, TD,
)
from exp_core_assembly_real import (               # noqa: E402
    damp_iv, year_start_mask, to_wslices, window_metrics, bench_metrics,
    cost_drag, two_sided_p_from_t, _p, _a, _ruin, CAPITAL,
)

DELTAS = [0.50, 0.70, 0.80]
BUDGETS = [0.10, 0.15]
RULES = ["A-annual", "B-quarterly", "C-monthly", "D-onroll"]
CASH_W = 0.15
IV_MULT = 0.85
COST_BASE = 0.005
DAMP = 0.4
MAXDD_CAP = -0.56          # user tolerance ceiling (see docstring point 2)
RANK_CONSISTENCY_TOP = 6   # top-25%-of-24 for the "base/damp ranking agrees" check

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-06_core_topup.md")

# 18 Loop-3 trial Sharpes (native FULL window, base IV m=0.85, base cost 0.5%/side),
# hardcoded from backtest/results/2026-07-06_core_assembly_real.md's main table
# (retrieved 2026-07-06) -- NOT re-run here, just cited for the x42 registry.
# Order: b in {10,15,20}% x delta in {0.50,0.70,0.80} x mix in {SPY-only,SPY+QQQ}.
LOOP3_SHARPES_18 = [0.81, 0.73, 0.73, 0.65, 0.70, 0.62,
                    0.81, 0.79, 0.73, 0.69, 0.69, 0.65,
                    0.80, 0.82, 0.72, 0.71, 0.69, 0.66]

ASSERT_COUNT = {"n": 0, "runs": 0}


# ---------------------------------------------------------------------------
# Trigger masks (axis 1)
# ---------------------------------------------------------------------------

def quarter_start_mask(index: pd.DatetimeIndex) -> np.ndarray:
    n = len(index)
    m = np.zeros(n, dtype=bool)
    q = index.quarter.values
    if n > 1:
        m[1:] = q[1:] != q[:-1]
    return m


def month_start_mask(index: pd.DatetimeIndex) -> np.ndarray:
    n = len(index)
    m = np.zeros(n, dtype=bool)
    mo = index.month.values
    if n > 1:
        m[1:] = mo[1:] != mo[:-1]
    return m


# ---------------------------------------------------------------------------
# Portfolio assembly engine (op-for-op port of exp_core_assembly_real.simulate_
# portfolio, +topup-rule axis +optional whole-contract rounding). Same return
# dict shape (nav/core/cash/opt/conts/dnotional) so window_metrics/cost_drag/
# bench_metrics from exp_core_assembly_real.py are reused UNCHANGED downstream.
# ---------------------------------------------------------------------------

def simulate_portfolio_topup(legs, core_ret, r_cash, cost, w_cash, rule, b_total,
                             trigger_mask, round_contracts=False, capital=CAPITAL):
    n = len(core_ret)
    w_core = 1.0 - w_cash - b_total
    if w_core <= 0:
        raise AssertionError(f"non-positive core weight: w_core={w_core!r}")

    core_val = w_core * capital
    cash = capital - core_val
    n_legs = len(legs)
    opt_val = [0.0] * n_legs
    c = [0.0] * n_legs
    prev_mark = [np.nan] * n_legs

    nav = np.empty(n)
    core_arr = np.empty(n)
    cash_arr = np.empty(n)
    opt_arr = [np.empty(n) for _ in legs]
    conts_arr = [np.empty(n) for _ in legs]
    dnotional = np.empty(n)
    topup_arr = np.zeros(n)     # $ pulled core->cash this bar (B/C/D telemetry)

    prev_nav = capital

    for i in range(n):
        interest = cash * r_cash[i]
        cash += interest
        core_pnl = core_val * core_ret[i]
        core_val += core_pnl

        total_costs = 0.0
        total_opt_pnl = 0.0

        # ---- B/C/D floor top-up: BEFORE leg processing (funds THIS bar's buys) --
        if rule != "A-annual" and trigger_mask[i]:
            navnow = core_val + cash + sum(opt_val)
            target = b_total * navnow
            if cash < target:
                amt = min(target - cash, max(core_val, 0.0))
                core_val -= amt
                cash += amt
                topup_arr[i] = amt

        for L, leg in enumerate(legs):
            u = leg["unit"]
            mark, mark_pre = u["mark"], u["mark_pre"]
            sell, sell_mark = u["sell"], u["sell_mark"]
            buy, buy_mark = u["buy"], u["buy_mark"]

            pnl = c[L] * (mark_pre[i] - prev_mark[L]) * 100.0 if c[L] > 0.0 else 0.0
            opt_val[L] += pnl
            total_opt_pnl += pnl

            leg_costs = 0.0
            did_sell = bool(sell[i])
            cash_before_leg = cash
            if did_sell:
                gross = c[L] * sell_mark[i] * 100.0
                proceeds = gross * (1.0 - cost)
                leg_costs += gross * cost
                cash += proceeds
                opt_val[L] = 0.0
                c[L] = 0.0

            if bool(buy[i]):
                other_opt = sum(opt_val) - opt_val[L]
                nav_now = core_val + cash + other_opt
                target_premium = leg["b"] * nav_now
                spend_cont = min(target_premium, max(cash, 0.0))
                bm = buy_mark[i]
                prem_cont = spend_cont / (1.0 + cost)
                c_cont = prem_cont / (bm * 100.0) if bm > 1e-12 else 0.0
                if round_contracts:
                    c_r = round(c_cont)
                    prem_r = c_r * bm * 100.0
                    spend_r = prem_r * (1.0 + cost)
                    if spend_r > cash + 1e-9:      # can't afford round-UP -> floor
                        c_r = math.floor(c_cont)
                        prem_r = c_r * bm * 100.0
                        spend_r = prem_r * (1.0 + cost)
                    c[L] = c_r
                    prem = prem_r
                    spend = spend_r
                else:
                    c[L] = c_cont
                    prem = prem_cont
                    spend = spend_cont
                cash -= spend
                leg_costs += spend - prem
                opt_val[L] = prem

            if did_sell:
                net_change = cash - cash_before_leg
                sweep = max(net_change, 0.0)
                if sweep > 0.0:
                    cash -= sweep
                    core_val += sweep

            total_costs += leg_costs
            prev_mark[L] = mark[i] if c[L] > 0.0 else np.nan
            conts_arr[L][i] = c[L]
            opt_arr[L][i] = opt_val[L]

        # ---- A-annual: SYMMETRIC rebalance AFTER leg processing (Loop-3 status quo)
        if rule == "A-annual" and trigger_mask[i]:
            nonopt = core_val + cash
            ratio = w_core / (w_core + w_cash) if (w_core + w_cash) > 0 else 1.0
            new_core = nonopt * ratio
            cash = nonopt - new_core
            core_val = new_core

        total_opt_val = sum(opt_val)
        v = core_val + cash + total_opt_val
        expected = prev_nav + interest + core_pnl + total_opt_pnl - total_costs
        if abs(v - expected) > 1e-6 * max(1.0, abs(expected)):
            raise AssertionError(f"cross-foot fail bar {i}: nav={v!r} expected={expected!r}")
        if cash < -1e-6:
            raise AssertionError(f"negative cash bar {i}: {cash!r}")
        if v <= 0:
            raise AssertionError(f"non-positive NAV bar {i}: {v!r}")
        ASSERT_COUNT["n"] += 3

        dn = 0.0
        for L, leg in enumerate(legs):
            u = leg["unit"]
            if c[L] > 0.0:
                dn += c[L] * u["delta"][i] * leg["close"][i] * 100.0
        dnotional[i] = dn / v if v > 0 else np.nan

        nav[i] = v
        core_arr[i] = core_val
        cash_arr[i] = cash
        prev_nav = v

    ASSERT_COUNT["runs"] += 1
    return {"nav": nav, "core": core_arr, "cash": cash_arr, "opt": opt_arr,
            "conts": conts_arr, "dnotional": dnotional, "topup": topup_arr}


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def cell_label(rule: str, b: float, delta: float) -> str:
    return f"{rule}/b{int(b*100)}/Δ{delta:.2f}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    irx_df = load("^IRX")
    irx = irx_df["close"]
    prov_all = [("^IRX", irx_df.attrs.get("source", "?"), len(irx_df),
                 str(irx_df.index.min().date()), str(irx_df.index.max().date()))]

    data = {}
    for under, volsym in [("SPY", "^VIX"), ("QQQ", "^VXN")]:
        df, prov, r_net_full = build_underlying(under, volsym, irx)
        data[under] = {"df": df}
        prov_all += prov
        print(f"{under} joined: {df.index[0].date()} -> {df.index[-1].date()}, "
              f"{len(df)} days", flush=True)

    spy_df = data["SPY"]["df"]
    qqq_df = data["QQQ"]["df"]
    common_idx = spy_df.index.intersection(qqq_df.index)
    print(f"common (mix, FIXED this loop) window: {common_idx[0].date()} -> "
          f"{common_idx[-1].date()}, {len(common_idx)} days", flush=True)

    for under, df in [("SPY", spy_df), ("QQQ", qqq_df)]:
        d = data[under]
        d["close"] = df["close"].values
        d["iv_raw"] = df["vol"].values / 100.0 * IV_MULT
        d["r_arr"] = df["irx"].values / 100.0
        d["q_arr"] = df["q"].values
        d["r_cash"] = d["r_arr"] / TD
        d["gate"] = build_gates(df)["GATED"]
        d["r_net"] = df["r_net"].values

    # Sanity anchor
    a_mask = spy_df.index >= "1996-01-01"
    a_lo = int(np.where(a_mask)[0][0])
    anchor = bench_metrics(spy_df["r_net"].values, a_lo, len(spy_df))
    print(f"SANITY SPY B&H TR (HK net) 1996->end: CAGR {anchor['CAGR']*100:.2f}% "
          f"Sharpe {anchor['Sharpe']:.2f} MaxDD {anchor['MaxDD']*100:.1f}%", flush=True)

    # ------------------------------------------------------------------
    # Unit paths: base (m=0.85) + damped (damp=0.4), 2 underlyings x 3 deltas = 12
    # ------------------------------------------------------------------
    base_paths, damped_paths = {}, {}
    for under in ("SPY", "QQQ"):
        d = data[under]
        iv_damped_native = damp_iv(d["iv_raw"], DAMP)   # sigma_bar over OWN full window
        for delta in DELTAS:
            base_paths[(under, delta)] = simulate_unit_path(
                d["close"], d["iv_raw"], d["r_arr"], d["q_arr"], d["gate"], delta)
            damped_paths[(under, delta)] = simulate_unit_path(
                d["close"], iv_damped_native, d["r_arr"], d["q_arr"], d["gate"], delta)
    print(f"12 unit paths (base+damp x 2 underlyings x 3 deltas) done "
          f"({time.time()-t0:.0f}s)", flush=True)

    native_index = {"SPY": spy_df.index, "QQQ": qqq_df.index}

    def unit_slice(under, delta, paths_dict, index_target):
        udf = pd.DataFrame(paths_dict[(under, delta)], index=native_index[under])
        sl = udf.reindex(index_target)
        return {k: sl[k].values for k in udf.columns}

    spy_close_c = pd.Series(data["SPY"]["close"], index=spy_df.index).reindex(common_idx).values
    qqq_close_c = pd.Series(data["QQQ"]["close"], index=qqq_df.index).reindex(common_idx).values
    core_ret_c = pd.Series(data["SPY"]["r_net"], index=spy_df.index).reindex(common_idx).values
    r_cash_c = pd.Series(data["SPY"]["r_cash"], index=spy_df.index).reindex(common_idx).values
    bench_c = core_ret_c   # Jensen-alpha benchmark = SPY net-TR (same as core sleeve's own return)
    gate_spy_c = pd.Series(data["SPY"]["gate"], index=spy_df.index).reindex(common_idx).values.astype(bool)
    gate_qqq_c = pd.Series(data["QQQ"]["gate"], index=qqq_df.index).reindex(common_idx).values.astype(bool)

    def legs_for(b, delta, paths_dict):
        u_spy = unit_slice("SPY", delta, paths_dict, common_idx)
        u_qqq = unit_slice("QQQ", delta, paths_dict, common_idx)
        return [{"b": b / 2.0, "unit": u_spy, "close": spy_close_c},
                {"b": b / 2.0, "unit": u_qqq, "close": qqq_close_c}]

    ys_mask = year_start_mask(common_idx)
    qs_mask = quarter_start_mask(common_idx)
    ms_mask = month_start_mask(common_idx)

    wslices_all = to_wslices("QQQ", common_idx)
    wslices = {name: (lo, hi) for name, lo, hi in wslices_all
              if name.startswith("FULL") or name.startswith("H2")
              or name.startswith("2016") or name.startswith("2021")}
    full_name = [n for n in wslices if n.startswith("FULL")][0]
    lo0, hi0 = wslices[full_name]
    print(f"windows reported: {list(wslices.keys())} (H1 2001-2010 dropped from "
          f"printed tables per pre-registration — see docstring)", flush=True)

    # ------------------------------------------------------------------
    # 24-cell grid: rule x b x delta, mix FIXED SPY+QQQ
    # ------------------------------------------------------------------
    CELLS = [(rule, b, delta) for rule in RULES for b in BUDGETS for delta in DELTAS]
    R = {}   # (rule,b,delta) -> dict of everything

    for delta in DELTAS:
        # roll timing is IV-independent (dte countdown + price/200SMA gate only), so the
        # on-roll trigger is computed ONCE per delta from the base unit paths and reused
        # for both the base-IV and damp-IV portfolio runs below (verified by construction).
        u_spy_r = unit_slice("SPY", delta, base_paths, common_idx)["rolled"].astype(bool)
        u_qqq_r = unit_slice("QQQ", delta, base_paths, common_idx)["rolled"].astype(bool)
        onroll_mask = u_spy_r | u_qqq_r
        trigger_of = {"A-annual": ys_mask, "B-quarterly": qs_mask,
                     "C-monthly": ms_mask, "D-onroll": onroll_mask}
        for b in BUDGETS:
            legs_b_base = legs_for(b, delta, base_paths)
            legs_b_damp = legs_for(b, delta, damped_paths)
            for rule in RULES:
                trig = trigger_of[rule]
                key = (rule, b, delta)

                res_base = simulate_portfolio_topup(legs_b_base, core_ret_c, r_cash_c,
                                                    COST_BASE, CASH_W, rule, b, trig)
                res_base0 = simulate_portfolio_topup(legs_b_base, core_ret_c, r_cash_c,
                                                     0.0, CASH_W, rule, b, trig)
                res_damp = simulate_portfolio_topup(legs_b_damp, core_ret_c, r_cash_c,
                                                    COST_BASE, CASH_W, rule, b, trig)
                res_damp0 = simulate_portfolio_topup(legs_b_damp, core_ret_c, r_cash_c,
                                                     0.0, CASH_W, rule, b, trig)

                wmetrics_base, wmetrics_damp = {}, {}
                for wname, (lo, hi) in wslices.items():
                    mb = window_metrics(res_base, bench_c, common_idx, lo, hi)
                    mb["CostDrag"] = cost_drag(res_base, res_base0, lo, hi)
                    wmetrics_base[wname] = mb
                    md = window_metrics(res_damp, bench_c, common_idx, lo, hi)
                    md["CostDrag"] = cost_drag(res_damp, res_damp0, lo, hi)
                    wmetrics_damp[wname] = md

                starved = []
                for L, g in enumerate([gate_spy_c, gate_qqq_c]):
                    conts = res_base["conts"][L]
                    elig = g[lo0:hi0]
                    unfunded = elig & (conts[lo0:hi0] <= 0)
                    frac = float(unfunded.sum()) / float(elig.sum()) if elig.sum() > 0 else float("nan")
                    starved.append(frac)

                R[key] = {"base": wmetrics_base, "damp": wmetrics_damp,
                         "starved": starved, "res_base": res_base}
                print(f"cell {cell_label(*key)} done ({time.time()-t0:.0f}s)", flush=True)

    # ------------------------------------------------------------------
    # Cash-starved% under rule A at the SAME (b,delta) -- "rescue" comparator
    # ------------------------------------------------------------------
    rescue = {}
    for b in BUDGETS:
        for delta in DELTAS:
            a_starved = R[("A-annual", b, delta)]["starved"]
            for rule in RULES:
                rescue[(rule, b, delta)] = a_starved

    # ------------------------------------------------------------------
    # Winner selection (pre-registered algorithm, see docstring)
    # ------------------------------------------------------------------
    def t_base(key):
        return R[key]["base"][full_name]["t"]

    def t_damp(key):
        return R[key]["damp"][full_name]["t"]

    rank_base = sorted(CELLS, key=lambda k: -(t_base(k) if np.isfinite(t_base(k)) else -9e9))
    rank_damp = sorted(CELLS, key=lambda k: -(t_damp(k) if np.isfinite(t_damp(k)) else -9e9))
    base_rank_pos = {k: i for i, k in enumerate(rank_base)}

    winner = None
    for k in rank_damp:
        maxdd_ok = R[k]["damp"][full_name]["MaxDD"] >= MAXDD_CAP
        consistent = base_rank_pos[k] < RANK_CONSISTENCY_TOP
        if maxdd_ok and consistent:
            winner = k
            break
    if winner is None:
        winner = rank_damp[0]
        winner_fallback = True
    else:
        winner_fallback = False
    print(f"WINNER: {cell_label(*winner)} (fallback={winner_fallback})", flush=True)

    # ------------------------------------------------------------------
    # Rounding (granularity) check on the winner cell
    # ------------------------------------------------------------------
    w_rule, w_b, w_delta = winner
    legs_w = legs_for(w_b, w_delta, base_paths)
    onroll_mask_w = legs_w[0]["unit"]["rolled"].astype(bool) | legs_w[1]["unit"]["rolled"].astype(bool)
    trig_w = {"A-annual": ys_mask, "B-quarterly": qs_mask,
             "C-monthly": ms_mask, "D-onroll": onroll_mask_w}[w_rule]
    res_w_cont = R[winner]["res_base"]
    res_w_round = simulate_portfolio_topup(legs_w, core_ret_c, r_cash_c, COST_BASE, CASH_W,
                                           w_rule, w_b, trig_w, round_contracts=True)
    m_w_cont = window_metrics(res_w_cont, bench_c, common_idx, lo0, hi0)
    m_w_round = window_metrics(res_w_round, bench_c, common_idx, lo0, hi0)
    rounding_drag_cagr = (m_w_cont["CAGR"] - m_w_round["CAGR"]) * 100.0
    rounding_drag_alpha = (m_w_cont["Alpha"] - m_w_round["Alpha"]) * 100.0

    RECENT_N = 252
    hconts = res_w_cont["conts"]
    hopt = res_w_cont["opt"]
    prem_dollars = w_b / 2.0 * CAPITAL
    granularity_lines = []
    for i, leg_name in enumerate(["SPY leg", "QQQ leg"]):
        conts = hconts[i][-RECENT_N:]
        opt_v_all = hopt[i][-RECENT_N:]
        held = conts[conts > 0]
        opt_v = opt_v_all[conts > 0]
        if len(held) > 0:
            prem_per_contract = float(np.median(opt_v / held))
            granularity_lines.append(
                f"- {leg_name}: premium budget ~${prem_dollars:,.0f}; median per-contract "
                f"premium (last {RECENT_N}td) ~${prem_per_contract:,.0f} -> "
                f"~{prem_dollars/prem_per_contract:.1f} contracts (continuous).")
        else:
            granularity_lines.append(f"- {leg_name}: gated out for the entire last "
                                     f"{RECENT_N}td — no recent per-contract premium observed.")

    # ------------------------------------------------------------------
    # Registry: Bonferroni x42, DSR
    # ------------------------------------------------------------------
    new_24_sharpes = [R[k]["base"][full_name]["Sharpe"] for k in CELLS]
    trial_sharpes_42 = np.array(LOOP3_SHARPES_18 + new_24_sharpes, dtype="float64")

    hl_base_m = R[winner]["base"][full_name]
    hl_damp_m = R[winner]["damp"][full_name]
    p_base = two_sided_p_from_t(hl_base_m["t"])
    p_base_bonf = min(1.0, p_base * 42) if np.isfinite(p_base) else np.nan
    p_damp = two_sided_p_from_t(hl_damp_m["t"])
    p_damp_bonf = min(1.0, p_damp * 42) if np.isfinite(p_damp) else np.nan
    hl_ret = hl_base_m["ret"]
    hl_dsr = metrics.deflated_sharpe_ratio(hl_ret, trial_sharpes_42)
    hl_psr = metrics.probabilistic_sharpe_ratio(hl_ret, 0.0)

    # ------------------------------------------------------------------
    # Write results markdown
    # ------------------------------------------------------------------
    L = []
    add = L.append
    add("# Result — Core portfolio, Loop 4 (final): cash top-up rules to fix "
        "Loop-3's cash-starvation + full base/damp disclosure, 24-cell grid (real data)")
    add("")
    add("**Date:** 2026-07-06  **Script:** `backtest/experiments/exp_core_topup.py`  "
        "**Status:** active")
    add("")
    add("## Question")
    add("")
    add("Loop-3 (`exp_core_assembly_real.py`) found the annual-only cash rebalance "
        "leaves the LEAP sleeve cash-starved 40-60% of trend-eligible days, and only "
        "stress-tested IV-damping on its Delta=0.50 top-3 (not Delta=0.70/0.80). This "
        "loop fixes both: (1) tests 3 higher-frequency/event-tied cash top-up rules "
        "against the annual-rebalance control, (2) runs base-IV AND damp=0.4 IV on "
        "EVERY cell. Grid: 4 top-up rules x {10%,15%} premium budget x "
        "{0.50,0.70,0.80} delta, LEAP mix FIXED to 50/50 SPY+QQQ (Loop-3's settled "
        "winner). Benchmark = SPY B&H total return, HK 30% dividend withholding netted.")
    add("")
    add("## Method")
    add("")
    add("- LEAP unit engine (`simulate_unit_path`) IMPORTED verbatim from "
        "`exp_leap_real_sweep.py`. Gate = pure 200SMA GATED. 1y call (252td), roll @ "
        "63td remaining. IV_1y = vol-index/100 x 0.85 (base), real ^VIX (SPY leg) / "
        "^VXN (QQQ leg); damp=0.4 IV via `damp_iv()` IMPORTED verbatim from "
        "`exp_core_assembly_real.py` (same adversarially-reviewed method, not redone).")
    add("- NEW in this script: the fund-replenishment RULE axis. Rule A (annual, "
        "SYMMETRIC core:cash rebalance) reproduces `exp_core_assembly_real.py`'s "
        "mechanics byte-for-byte as the control. Rules B/C/D are an ASYMMETRIC FLOOR "
        "top-up (pull cash up to b%NAV from core ONLY when short; never sell cash back "
        "down when already sufficient) fired quarterly / monthly / on-roll "
        "respectively — a liquidity-mechanics fix, not a market-timing signal.")
    add("- Core sleeve compounds at the SAME SPY net-TR series used as the Jensen-alpha "
        "benchmark, so alpha isolates the LEAP-sleeve + cash-buffer + replenishment-rule "
        "MACHINERY, not stock selection.")
    add("- Costs: 0.5%/side of option premium (base), charged on entry/exit/both legs of "
        "a roll; core-equity trades (rebalance/top-up/sweep) zero-cost (ETF shares). "
        "Sharpe = raw daily returns. CAPITAL = $500,000.")
    add("- Windows: FULL (native start of the SPY+QQQ common window, 2001+) as PRIMARY, "
        "+ H2 2011-2026 / 2016-2020 / 2021+. H1 2001-2010 is dropped from the printed "
        "tables (pre-registered; see script docstring).")
    add("")
    add("## Data provenance (`backtest/data.py` `load()`)")
    add("")
    add("| Series | Source | Rows | From | To |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in prov_all:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")
    add(f"- Common (mix) simulation window: {common_idx[0].date()} -> "
        f"{common_idx[-1].date()} ({len(common_idx)} days).")
    add(f"- Sanity anchor — SPY B&H TR (HK net) 1996-01->{spy_df.index[-1].date()}: CAGR "
        f"**{anchor['CAGR']*100:.2f}%**, Sharpe {anchor['Sharpe']:.2f}, MaxDD "
        f"{anchor['MaxDD']*100:.1f}% (pre-registered acceptance band 9-11%).")
    add("")

    # -- Table 1: main grid, FULL window, base + damp -----------------------
    add("## Table 1 — 24-cell grid, FULL (2001+) window, base (m0.85) AND damp=0.4 "
        "(every cell reports both — no base-only rows)")
    add("")
    add("| Rule | b | Δ | IV | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | Worst mo | "
        "TE | Dn% med/p90/max | CostDrag pp/yr |")
    add("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for key in CELLS:
        rule, b, delta = key
        for ivlabel, wm in [("base m0.85", R[key]["base"]), ("damp 0.4", R[key]["damp"])]:
            m = wm[full_name]
            add(f"| {rule} | {int(b*100)}% | {delta:.2f} | {ivlabel} | {_p(m['CAGR'])}{_ruin(m)} "
                f"| {m['Sharpe']:.2f} | {_p(m['MaxDD'])} | {_a(m)} | {_p(m['WorstMonth'])} | "
                f"{_p(m['TE'])} | {m['DnMed']*100:.0f}%/{m['DnP90']*100:.0f}%/{m['DnMax']*100:.0f}% "
                f"| {m['CostDrag']:+.1f} |")
    add("")

    # -- Table 2: sub-windows, base only -------------------------------------
    add("## Table 2 — sub-windows (H2 2011-2026 / 2016-2020 / 2021+), base IV only "
        "(CAGR / a(t))")
    add("")
    sub_names = [n for n in wslices if not n.startswith("FULL")]
    add("| Rule | b | Δ | " + " | ".join(f"{w} CAGR | α(t)" for w in sub_names) + " |")
    add("|---|---|---|" + "---|" * (2 * len(sub_names)))
    for key in CELLS:
        rule, b, delta = key
        row = [rule, f"{int(b*100)}%", f"{delta:.2f}"]
        for w in sub_names:
            m = R[key]["base"][w]
            row += [_p(m["CAGR"]), _a(m)]
        add("| " + " | ".join(row) + " |")
    add("")

    # -- Table 3: cash-starved% ------------------------------------------------
    add("## Table 3 — cash-starved% (base IV, FULL window; SPY-leg/QQQ-leg): "
        "\"of days the leg's own 200SMA gate says eligible, fraction the sim carried "
        "0 contracts because cash could not fund the fresh premium\"")
    add("")
    add("| Rule | b | Δ | SPY-leg starved% | QQQ-leg starved% | (rule-A same b/Δ, for comparison) |")
    add("|---|---|---|---|---|---|")
    for key in CELLS:
        rule, b, delta = key
        s = R[key]["starved"]
        a_s = rescue[key]
        add(f"| {rule} | {int(b*100)}% | {delta:.2f} | {s[0]*100:.0f}% | {s[1]*100:.0f}% | "
            f"{a_s[0]*100:.0f}%/{a_s[1]*100:.0f}% |")
    add("")

    # -- Winner selection -----------------------------------------------------
    add("## Winner selection (pre-registered algorithm — see script docstring)")
    add("")
    add(f"Ranking by DAMP=0.4 α-t-stat (FULL window), top 8: " +
        ", ".join(f"{cell_label(*k)} (t={t_damp(k):+.2f})" for k in rank_damp[:8]))
    add("")
    add(f"Ranking by BASE α-t-stat (FULL window), top 8: " +
        ", ".join(f"{cell_label(*k)} (t={t_base(k):+.2f})" for k in rank_base[:8]))
    add("")
    add(f"MaxDD cap filter: damp MaxDD >= {MAXDD_CAP*100:.0f}%. Rank-consistency filter: "
        f"must place in the top {RANK_CONSISTENCY_TOP} (of 24) by BASE α-t as well.")
    add("")
    add(f"**WINNER: {cell_label(*winner)}**"
        + (" (fallback: no cell passed both filters — reporting the top damp-ranked "
           "cell regardless; see Caveats)" if winner_fallback else ""))
    add("")
    add("| | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) |")
    add("|---|---|---|---|---|")
    add(f"| base m0.85 | {_p(hl_base_m['CAGR'])}{_ruin(hl_base_m)} | {hl_base_m['Sharpe']:.2f} "
        f"| {_p(hl_base_m['MaxDD'])} | {_a(hl_base_m)} |")
    add(f"| damp 0.4 | {_p(hl_damp_m['CAGR'])}{_ruin(hl_damp_m)} | {hl_damp_m['Sharpe']:.2f} "
        f"| {_p(hl_damp_m['MaxDD'])} | {_a(hl_damp_m)} |")
    add("")
    if w_delta != 0.50:
        add(f"**Δ={w_delta:.2f} != 0.50 won under damp=0.4 — per pre-registration, "
            f"this more-aggressive/lower-vega delta needs real options-chain validation "
            f"before being trusted over the Δ=0.50 result** (Δ=0.50's own damp "
            f"figures are in Table 1 for direct comparison).")
    else:
        add("Δ=0.50 still wins under damp=0.4 (consistent with Loop-3's un-stressed "
            "ranking) — the pre-registered aggressive-delta contingency does not apply.")
    add("")

    # -- Rounding / granularity check -----------------------------------------
    add(f"## Granularity check ($500k program, winner cell {cell_label(*winner)})")
    add("")
    add("Per-contract premium uses the LAST 252 trading days only (recent price/IV level, "
        "not a full-history median dominated by cheaper legacy prices).")
    add("")
    for ln in granularity_lines:
        add(ln)
    add("")
    add("| | CAGR | α vs SPY net-TR (t) |")
    add("|---|---|---|")
    add(f"| continuous/fractional contracts | {_p(m_w_cont['CAGR'])} | {_a(m_w_cont)} |")
    add(f"| whole-contract rounding | {_p(m_w_round['CAGR'])} | {_a(m_w_round)} |")
    add(f"| **rounding drag** | **{rounding_drag_cagr:+.2f}pp CAGR** | "
        f"**{rounding_drag_alpha:+.2f}pp alpha** |")
    add("")

    # -- Cross-foot -------------------------------------------------------------
    add("## Cross-foot verification")
    add("")
    add(f"- {ASSERT_COUNT['runs']} accounting runs, {ASSERT_COUNT['n']:,} bar-level "
        "assertions, ALL passed: NAV = core + cash + sum(option market value); cash >= 0; "
        "NAV > 0; NAV_t = NAV_(t-1) + cash interest + core P&L + option P&L - costs "
        "(both the annual rebalance and the new floor top-up are zero-sum internal "
        "transfers and do not appear in this identity; rel. tol 1e-6). Any violation "
        "raises and aborts the run.")
    add("")

    # -- Registry ----------------------------------------------------------------
    add("## Trial registry, Bonferroni x42, DSR")
    add("")
    add("- **This loop's registered trial universe: 24 grid cells** (4 top-up rules x "
        "2 premium budgets x 3 deltas, mix fixed), all reported (Table 1). Cumulative "
        "with Loop-3's 18 pre-registered cells (`2026-07-06_core_assembly_real.md`, "
        "hardcoded not re-run) = **42 trials** for this correction.")
    add(f"- Winner **{cell_label(*winner)}**, FULL(2001+) window: base α-t = "
        f"{hl_base_m['t']:+.2f} (two-sided p={p_base:.4g}, **Bonferroni x42 p={p_base_bonf:.4g}**); "
        f"damp=0.4 α-t = {hl_damp_m['t']:+.2f} (two-sided p={p_damp:.4g}, "
        f"**Bonferroni x42 p={p_damp_bonf:.4g}**).")
    add(f"- **Deflated Sharpe Ratio (DSR)** of the winner (real daily-return series at base "
        f"IV/cost, vs the 42-cell annualized-Sharpe trial universe): **{hl_dsr:.3f}** "
        f"(PSR against 0 = {hl_psr:.3f}). DSR > 0.95 ~ survives multiple testing.")
    add(f"- Trial-universe annualized Sharpes (42 cells): min {np.nanmin(trial_sharpes_42):.2f}, "
        f"median {np.nanmedian(trial_sharpes_42):.2f}, max {np.nanmax(trial_sharpes_42):.2f}.")
    add("")

    add("## Conclusions")
    add("")
    add("(placeholder — filled by hand after reviewing Tables 1-3 and the winner block above)")
    add("")
    add("## Caveats")
    add("")
    add("(placeholder — filled by hand)")
    add("")
    add("## Implication")
    add("")
    add("(placeholder — filled by hand)")
    add("")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS}  ({time.time()-t0:.0f}s total, "
          f"{ASSERT_COUNT['n']:,} asserts / {ASSERT_COUNT['runs']} runs)", flush=True)


if __name__ == "__main__":
    main()
