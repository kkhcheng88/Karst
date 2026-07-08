"""User-challenge A/B: does an RSI-2 TIMED top-up (instead of a calendar-cadence
top-up) beat the locked Loop-4 winner, and does gating LEAP entries on a dip
(GATED+DIP) inside the top-up program help? Two pre-registered new cells, run
against the ALREADY-SELECTED winner from `exp_core_topup.py`
(C-monthly/b15/Delta0.50/SPY+QQQ) — not a new grid search.

Background (settled, not re-tested here — see backtest/results/2026-07-06_core_topup.md)
--------
Loop-4 pre-registered a 4(top-up rule) x 2(b) x 3(delta) = 24-cell grid and found
C-monthly (a floor top-up fired on the first trading day of each calendar month:
pull cash up to b%NAV from core ONLY when short) dominates the annual-only
control and the quarterly/on-roll alternatives at every (b,delta) cell. Winner:
C-monthly/b15/Delta0.50/SPY+QQQ — FULL(2001+) base CAGR +22.3%/Sharpe 0.98/MaxDD
-54.5%/alpha +12.4pp(t+5.4); damp=0.4 CAGR +16.1%/Sharpe 0.72/MaxDD -55.6%/alpha
+6.5pp(t+3.1); cash-starved% (SPY-leg/QQQ-leg) 10%/7%.

User's challenge: "why not RSI-time the top-up instead of using the calendar?"
This script answers with 2 pre-registered NEW cells, holding everything else
(b=15%, Delta=0.50, mix=SPY+QQQ 50/50, roll@63td, pure 200SMA gate unless stated
otherwise) fixed to the winning cell's own settings.

Question
--------
(1) Rule E (RSI-funded top-up): does tying the SAME floor top-up mechanic to an
    EVENT (SPY RSI-2(Wilder) < 10, signal at close T -> executed T+1) instead of
    a calendar date change the cash-starvation fix or the alpha, and does it
    leave some years with ZERO top-up because RSI-2 never dipped under 10 (the
    "2017-type year" pathology hypothesized by the user)?
(2) Rule F (monthly top-up + dip-gated entry): does layering a DIP entry
    condition (enter iff close>200SMA AND the leg's own RSI-2<10 sometime in the
    last 5 trading days = GATED+DIP, trend-exit unchanged) on top of Rule C's
    monthly top-up help or hurt, and is the portfolio-level result consistent
    with the already-settled ENGINE-level finding that plain GATED beats
    GATED+DIP/GATED+DIP+HYST (`exp_leap_real_sweep.py` /
    `2026-07-06_leap_real_sweep.md`, "pure GATED > DIP/HYST")?
Rule C itself is NOT re-run for the headline numbers (cited verbatim from
`2026-07-06_core_topup.md`); this script DOES also recompute Rule C internally,
purely as a byte-for-byte regression / sanity cross-check that the imported
engine still reproduces the cited numbers (see "Regression check" section).

Method (mirror / increment / horizon)
------
Mirror     : identical 3-bucket program (SPY+QQQ LEAP sleeve + cash + SPY core,
             never trend-sold) the user would actually run; same real
             ^VIX/^VXN/^IRX data; same benchmark (SPY B&H total return, HK 30%
             dividend withholding netted).
Increment  : ONLY the top-up TRIGGER (axis: calendar vs RSI-2 event) and, for
             Rule F only, the LEAP entry GATE (pure 200SMA vs GATED+DIP) are new.
             The floor-top-up MECHANIC (`simulate_portfolio_topup`), the LEAP
             unit engine (`simulate_unit_path`, incl. the pre-built GATED+DIP
             state machine), the IV-damping method (`damp_iv`), and every
             window/metrics helper are IMPORTED verbatim from
             `exp_core_topup.py` / `exp_core_assembly_real.py` /
             `exp_leap_real_sweep.py` — not reimplemented.
Horizon    : continuous multi-year program; LEAP rolled at 63 trading days
             remaining (engine default, unchanged); b=15% premium budget,
             Delta=0.50, cash target 15% NAV, LEAP mix FIXED to 50/50 SPY+QQQ —
             all pinned to the Loop-4 winning cell's own settings.

Pre-registered rules (both new; C is a citation, not a new trial)
------
  Rule E (RSI-funded top-up): gate = pure 200SMA GATED (same as the winner).
    Top-up trigger = SPY RSI-2(Wilder) < 10 at close T -> executed T+1 (same
    signal-to-execution convention as every gate in this repo). On a trigger
    day, pull cash up to b%NAV from core ONLY if short (identical floor-top-up
    mechanic as Rule C, just a different trigger mask). No calendar fallback —
    if RSI-2 never dips under 10 in a given year, that year gets ZERO top-ups,
    exactly like Rule B/C/D never fall back to an annual rebalance if their own
    trigger doesn't fire (this repo's established convention, not a new
    asymmetry introduced here).
  Rule F (monthly top-up + dip-gated entry): top-up trigger = calendar month
    start (IDENTICAL to Rule C). LEAP entry gate = GATED+DIP: enter iff
    close>200SMA AND RSI-2(Wilder)<10 occurred at least once in the trailing 5
    trading days; exit iff close<200SMA (trend exit UNCHANGED from plain
    GATED — GATED+DIP's state machine already encodes exactly this and is
    IMPORTED verbatim from `exp_leap_real_sweep.build_gates`, not reimplemented).
  Windows: FULL (2001+, native start of the SPY+QQQ common window) PRIMARY,
    + H2 2011-2026 / 2016-2020 / 2021+ (identical set to `exp_core_topup.py`).

Disclosure requirement (same asymmetry-avoidance rule as Loop-4)
------
BOTH new cells report BOTH a base-IV (m=0.85) row and an IV-damped (damp=0.4)
row on the PRIMARY (FULL 2001+) window. Damping method identical to Loop-4:
sigma_damped = sigma_bar + damp*(sigma_raw - sigma_bar), sigma_bar = full-sample
mean of that leg's OWN raw IV_1y proxy — `damp_iv()` imported verbatim.

Statistical context (why no fresh Bonferroni/DSR table here)
------
This is a targeted 2-cell challenge test compared directly against the
ALREADY-SELECTED Loop-4 winner (same b/delta/mix), not a new multi-cell search
competing for "best" — so a fresh multiple-testing correction is not the
governing lens for these 2 cells (consistent with how Loop-4 itself did not
re-run Bonferroni/DSR every time a single alternative was checked against the
control). The cumulative registry context (42 trials as of Loop-4) is noted for
the record but not recomputed.

Cross-foot (hard asserts, every bar of every accounting run, IMPORTED verbatim
from `exp_core_topup.simulate_portfolio_topup`): NAV = core + cash + sum(option
market value); cash >= 0; NAV > 0; NAV_t = NAV_{t-1} + interest + core P&L +
option P&L - costs (the floor top-up is a zero-sum internal transfer and does
not appear in this identity).

Run:  PYTHONUTF8=1 python backtest/experiments/exp_topup_timing_ab.py
Writes: backtest/results/2026-07-07_topup_timing_ab.md
"""
from __future__ import annotations

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
    build_underlying, build_gates, simulate_unit_path, TD,
)
from exp_core_assembly_real import (               # noqa: E402
    damp_iv, to_wslices, window_metrics, bench_metrics,
    cost_drag, two_sided_p_from_t, _p, _a, _ruin, CAPITAL,
)
from exp_core_topup import (                       # noqa: E402
    simulate_portfolio_topup, cell_label, month_start_mask,
    CASH_W, IV_MULT, COST_BASE, DAMP, MAXDD_CAP,
)

B = 0.15
DELTA = 0.50
RSI_THRESH = 10.0

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-07_topup_timing_ab.md")

# Winner cell (C-monthly/b15/Delta0.50/SPY+QQQ), CITED verbatim from
# backtest/results/2026-07-06_core_topup.md — NOT re-derived, just quoted for
# the side-by-side comparison tables below (a fresh regression-check re-run of
# the identical cell is done separately, see "Regression check" section).
CITED_C = {
    "full": {
        "base": {"CAGR": 0.223, "Sharpe": 0.98, "MaxDD": -0.545, "Alpha": 0.124, "t": 5.4,
                 "WorstMonth": -0.398, "TE": 0.116, "DnMed": 1.20, "DnP90": 2.16, "DnMax": 3.01,
                 "CostDrag": 0.7},
        "damp": {"CAGR": 0.161, "Sharpe": 0.72, "MaxDD": -0.556, "Alpha": 0.065, "t": 3.1,
                 "WorstMonth": -0.416, "TE": 0.112, "DnMed": 1.18, "DnP90": 1.72, "DnMax": 2.17,
                 "CostDrag": 0.6},
    },
    "sub": {
        "H2 2011-2026": {"CAGR": 0.328, "Alpha": 0.143, "t": 4.6},
        "2016-2020":    {"CAGR": 0.416, "Alpha": 0.204, "t": 3.3},
        "2021+":        {"CAGR": 0.299, "Alpha": 0.101, "t": 2.0},
    },
    "starved": [0.10, 0.07],   # SPY-leg / QQQ-leg
}

# Engine-level (single-unit, PORTFOLIO frame, Delta=0.50) GATED vs GATED+DIP,
# CITED verbatim from backtest/results/2026-07-06_leap_real_sweep.md — the
# already-settled finding Rule F is checked against for consistency.
CITED_ENGINE_GATE = {
    "SPY": {"GATED": {"Alpha": 0.106, "t": 5.9}, "GATED+DIP": {"Alpha": 0.100, "t": 5.7}},
    "QQQ": {"GATED": {"Alpha": 0.120, "t": 5.0}, "GATED+DIP": {"Alpha": 0.092, "t": 4.2}},
}

ASSERT_COUNT_START = None


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
    print(f"common (mix) window: {common_idx[0].date()} -> {common_idx[-1].date()}, "
          f"{len(common_idx)} days", flush=True)

    for under, df in [("SPY", spy_df), ("QQQ", qqq_df)]:
        d = data[under]
        d["close"] = df["close"].values
        d["iv_raw"] = df["vol"].values / 100.0 * IV_MULT
        d["r_arr"] = df["irx"].values / 100.0
        d["q_arr"] = df["q"].values
        d["r_cash"] = d["r_arr"] / TD
        gates = build_gates(df)
        d["gate_GATED"] = gates["GATED"]
        d["gate_DIP"] = gates["GATED+DIP"]
        d["r_net"] = df["r_net"].values
        d["rsi2"] = df["rsi2"]     # pd.Series, native index, Wilder RSI-2

    # Sanity anchor
    a_mask = spy_df.index >= "1996-01-01"
    a_lo = int(np.where(a_mask)[0][0])
    anchor = bench_metrics(spy_df["r_net"].values, a_lo, len(spy_df))
    print(f"SANITY SPY B&H TR (HK net) 1996->end: CAGR {anchor['CAGR']*100:.2f}% "
          f"Sharpe {anchor['Sharpe']:.2f} MaxDD {anchor['MaxDD']*100:.1f}%", flush=True)

    # ------------------------------------------------------------------
    # Unit paths: base (m=0.85) + damp (0.4), x2 underlyings x2 gate variants
    # (GATED used by Rule E & the Rule-C regression check; GATED+DIP by Rule F)
    # ------------------------------------------------------------------
    base_paths, damped_paths = {}, {}
    for under in ("SPY", "QQQ"):
        d = data[under]
        iv_damped_native = damp_iv(d["iv_raw"], DAMP)
        for gname, garr in [("GATED", d["gate_GATED"]), ("GATED+DIP", d["gate_DIP"])]:
            base_paths[(under, gname)] = simulate_unit_path(
                d["close"], d["iv_raw"], d["r_arr"], d["q_arr"], garr, DELTA)
            damped_paths[(under, gname)] = simulate_unit_path(
                d["close"], iv_damped_native, d["r_arr"], d["q_arr"], garr, DELTA)
    print(f"8 unit paths (base+damp x 2 underlyings x 2 gate variants) done "
          f"({time.time()-t0:.0f}s)", flush=True)

    native_index = {"SPY": spy_df.index, "QQQ": qqq_df.index}

    def unit_slice(under, gname, paths_dict, index_target):
        udf = pd.DataFrame(paths_dict[(under, gname)], index=native_index[under])
        sl = udf.reindex(index_target)
        return {k: sl[k].values for k in udf.columns}

    spy_close_c = pd.Series(data["SPY"]["close"], index=spy_df.index).reindex(common_idx).values
    qqq_close_c = pd.Series(data["QQQ"]["close"], index=qqq_df.index).reindex(common_idx).values
    core_ret_c = pd.Series(data["SPY"]["r_net"], index=spy_df.index).reindex(common_idx).values
    r_cash_c = pd.Series(data["SPY"]["r_cash"], index=spy_df.index).reindex(common_idx).values
    bench_c = core_ret_c   # Jensen-alpha benchmark = SPY net-TR (same as core sleeve's own return)

    gate_c = {}
    for under, gname in [("SPY", "GATED"), ("QQQ", "GATED"), ("SPY", "GATED+DIP"), ("QQQ", "GATED+DIP")]:
        key = f"{under}_{gname}"
        native = spy_df.index if under == "SPY" else qqq_df.index
        garr = data[under]["gate_GATED"] if gname == "GATED" else data[under]["gate_DIP"]
        gate_c[key] = pd.Series(garr, index=native).reindex(common_idx).values.astype(bool)

    def legs_for(gname, paths_dict):
        u_spy = unit_slice("SPY", gname, paths_dict, common_idx)
        u_qqq = unit_slice("QQQ", gname, paths_dict, common_idx)
        return [{"b": B / 2.0, "unit": u_spy, "close": spy_close_c},
                {"b": B / 2.0, "unit": u_qqq, "close": qqq_close_c}]

    # ------------------------------------------------------------------
    # Triggers
    # ------------------------------------------------------------------
    ms_mask = month_start_mask(common_idx)                       # Rule C & F (calendar)

    spy_rsi2_native = data["SPY"]["rsi2"]
    raw_rsi_signal_native = (spy_rsi2_native < RSI_THRESH)
    exec_rsi_native = raw_rsi_signal_native.shift(1).fillna(False).astype(bool)   # T close -> T+1 exec
    trig_E = exec_rsi_native.reindex(common_idx).fillna(False).values.astype(bool)
    raw_rsi_signal_c = raw_rsi_signal_native.reindex(common_idx).fillna(False).values.astype(bool)

    wslices_all = to_wslices("QQQ", common_idx)
    wslices = {name: (lo, hi) for name, lo, hi in wslices_all
              if name.startswith("FULL") or name.startswith("H2")
              or name.startswith("2016") or name.startswith("2021")}
    full_name = [n for n in wslices if n.startswith("FULL")][0]
    lo0, hi0 = wslices[full_name]
    print(f"windows reported: {list(wslices.keys())}", flush=True)

    # ------------------------------------------------------------------
    # Run one rule (E, F, or the Rule-C regression check)
    # ------------------------------------------------------------------
    def run_rule(rule_id, gname, trig, starved_gate_key):
        legs_base = legs_for(gname, base_paths)
        legs_damp = legs_for(gname, damped_paths)

        res_base = simulate_portfolio_topup(legs_base, core_ret_c, r_cash_c, COST_BASE, CASH_W,
                                            rule_id, B, trig)
        res_base0 = simulate_portfolio_topup(legs_base, core_ret_c, r_cash_c, 0.0, CASH_W,
                                             rule_id, B, trig)
        res_damp = simulate_portfolio_topup(legs_damp, core_ret_c, r_cash_c, COST_BASE, CASH_W,
                                            rule_id, B, trig)
        res_damp0 = simulate_portfolio_topup(legs_damp, core_ret_c, r_cash_c, 0.0, CASH_W,
                                             rule_id, B, trig)

        wmetrics_base, wmetrics_damp = {}, {}
        for wname, (lo, hi) in wslices.items():
            mb = window_metrics(res_base, bench_c, common_idx, lo, hi)
            mb["CostDrag"] = cost_drag(res_base, res_base0, lo, hi)
            wmetrics_base[wname] = mb
            md = window_metrics(res_damp, bench_c, common_idx, lo, hi)
            md["CostDrag"] = cost_drag(res_damp, res_damp0, lo, hi)
            wmetrics_damp[wname] = md

        starved = []
        for L, key in enumerate([f"SPY_{starved_gate_key}", f"QQQ_{starved_gate_key}"]):
            g = gate_c[key]
            conts = res_base["conts"][L]
            elig = g[lo0:hi0]
            unfunded = elig & (conts[lo0:hi0] <= 0)
            frac = float(unfunded.sum()) / float(elig.sum()) if elig.sum() > 0 else float("nan")
            starved.append(frac)

        return {"base": wmetrics_base, "damp": wmetrics_damp, "starved": starved, "res_base": res_base}

    R = {}
    R["E-rsi2topup"] = run_rule("E-rsi2topup", "GATED", trig_E, "GATED")
    R["F-monthlydip"] = run_rule("F-monthlydip", "GATED+DIP", ms_mask, "GATED+DIP")
    # Regression check ONLY: recompute the winner cell (C-monthly/GATED/b15/D0.50)
    # with the identical imported engine — NOT used as the reported Rule-C numbers.
    R["C-regen"] = run_rule("C-monthly", "GATED", ms_mask, "GATED")
    print(f"3 rules simulated ({time.time()-t0:.0f}s)", flush=True)

    # ------------------------------------------------------------------
    # Rule E: "no RSI<10 day all year" diagnostic (starved-year check)
    # ------------------------------------------------------------------
    years = common_idx[lo0:hi0].year
    df_yr = pd.DataFrame({"year": years, "raw_sig": raw_rsi_signal_c[lo0:hi0],
                          "exec_sig": trig_E[lo0:hi0]})
    yr_counts = df_yr.groupby("year").agg(raw_days=("raw_sig", "sum"),
                                          exec_days=("exec_sig", "sum"),
                                          ndays=("year", "size"))
    starved_years = yr_counts[yr_counts["raw_days"] == 0]
    print(f"Rule E starved years (raw RSI<10 day count == 0): "
          f"{list(starved_years.index)}", flush=True)

    # ------------------------------------------------------------------
    # Regression check vs cited Rule-C numbers
    # ------------------------------------------------------------------
    c_regen_full_base = R["C-regen"]["base"][full_name]
    c_regen_full_damp = R["C-regen"]["damp"][full_name]
    cited_base = CITED_C["full"]["base"]
    cited_damp = CITED_C["full"]["damp"]
    regress_rows = []
    for label, regen, cited in [("base CAGR", c_regen_full_base["CAGR"], cited_base["CAGR"]),
                                ("base Sharpe", c_regen_full_base["Sharpe"], cited_base["Sharpe"]),
                                ("base MaxDD", c_regen_full_base["MaxDD"], cited_base["MaxDD"]),
                                ("base alpha", c_regen_full_base["Alpha"], cited_base["Alpha"]),
                                ("base t", c_regen_full_base["t"], cited_base["t"]),
                                ("damp CAGR", c_regen_full_damp["CAGR"], cited_damp["CAGR"]),
                                ("damp alpha", c_regen_full_damp["Alpha"], cited_damp["Alpha"]),
                                ("damp t", c_regen_full_damp["t"], cited_damp["t"])]:
        regress_rows.append((label, regen, cited, regen - cited))

    # ------------------------------------------------------------------
    # Write results markdown
    # ------------------------------------------------------------------
    L = []
    add = L.append
    add("# Result — Top-up TIMING A/B: RSI-2-funded top-up (E) and monthly top-up "
        "+ dip-gated entry (F) vs the locked Loop-4 winner (C-monthly/b15/Delta0.50/SPY+QQQ)")
    add("")
    add("**Date:** 2026-07-07  **Script:** `backtest/experiments/exp_topup_timing_ab.py`  "
        "**Status:** active")
    add("")
    add("## Question")
    add("")
    add("User challenge to the Loop-4 winner: \"why not RSI-time the top-up?\" Two "
        "pre-registered new cells, everything else pinned to the winning cell's own "
        "settings (b=15% NAV, Delta=0.50, mix=SPY+QQQ 50/50, roll@63td): **Rule E** "
        "replaces the calendar top-up trigger with SPY RSI-2(Wilder)<10 (signal T -> "
        "exec T+1), same pure-200SMA GATED entry gate as the winner. **Rule F** keeps "
        "the winner's monthly calendar top-up but requires each leg's OWN entry to ALSO "
        "clear a dip condition (GATED+DIP: close>200SMA AND RSI-2<10 within the last 5 "
        "trading days; trend-exit unchanged). Rule C's own numbers are CITED from "
        "`2026-07-06_core_topup.md` (not re-derived as the reported figures); a "
        "regression-check re-run of the identical Rule-C cell is included separately to "
        "confirm the imported engine still reproduces those numbers.")
    add("")
    add("## Method")
    add("")
    add("- LEAP unit engine (`simulate_unit_path`), the GATED+DIP state machine, and the "
        "floor-top-up mechanic (`simulate_portfolio_topup`) are IMPORTED verbatim from "
        "`exp_leap_real_sweep.py` / `exp_core_topup.py` — only the TRIGGER mask (and, for "
        "Rule F, which pre-built gate array feeds the unit path) is new.")
    add("- IV_1y = vol-index/100 x 0.85 (base), real ^VIX (SPY leg) / ^VXN (QQQ leg); "
        "damp=0.4 IV via `damp_iv()` (verbatim). Costs: 0.5%/side of option premium, "
        "core-equity transfers zero-cost. Sharpe = raw daily returns. CAPITAL = $500,000.")
    add("- Core sleeve compounds at the SAME SPY net-TR series used as the Jensen-alpha "
        "benchmark, so alpha isolates the LEAP-sleeve + cash-buffer + top-up-TIMING "
        "machinery, not stock selection.")
    add("- Windows: FULL (native start of the SPY+QQQ common window, 2001+) PRIMARY, + "
        "H2 2011-2026 / 2016-2020 / 2021+ (identical set to `exp_core_topup.py`).")
    add("- Statistical context: this is a targeted 2-cell challenge test against the "
        "ALREADY-SELECTED winner (same b/delta/mix), not a fresh multi-cell search — a "
        "new Bonferroni/DSR table is not the governing lens here (see docstring).")
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

    # -- Table 1: FULL window, base + damp, E/F (computed) vs C (cited) -----
    add("## Table 1 — FULL (2001+) window, base (m0.85) AND damp=0.4, b15/Delta0.50/SPY+QQQ "
        "(E and F computed here; C-monthly is CITED from `2026-07-06_core_topup.md`, not rerun)")
    add("")
    add("| Rule | Gate | IV | CAGR | Sharpe | MaxDD | alpha vs SPY net-TR (t) | Worst mo | "
        "TE | Dn% med/p90/max | CostDrag pp/yr |")
    add("|---|---|---|---|---|---|---|---|---|---|---|")
    for rule_label, key, gname in [("C-monthly (CITED, winner)", None, "GATED"),
                                   ("E-rsi2topup", "E-rsi2topup", "GATED"),
                                   ("F-monthlydip", "F-monthlydip", "GATED+DIP")]:
        for ivlabel, mkey in [("base m0.85", "base"), ("damp 0.4", "damp")]:
            if key is None:
                m = CITED_C["full"][mkey]
                add(f"| {rule_label} | {gname} | {ivlabel} | {_p(m['CAGR'])} | "
                    f"{m['Sharpe']:.2f} | {_p(m['MaxDD'])} | {m['Alpha']*100:+.1f}pp "
                    f"(t{m['t']:+.1f}) | {_p(m['WorstMonth'])} | {_p(m['TE'])} | "
                    f"{m['DnMed']*100:.0f}%/{m['DnP90']*100:.0f}%/{m['DnMax']*100:.0f}% | "
                    f"{m['CostDrag']:+.1f} |")
            else:
                m = R[key][mkey][full_name]
                add(f"| {rule_label} | {gname} | {ivlabel} | {_p(m['CAGR'])}{_ruin(m)} | "
                    f"{m['Sharpe']:.2f} | {_p(m['MaxDD'])} | {_a(m)} | {_p(m['WorstMonth'])} | "
                    f"{_p(m['TE'])} | {m['DnMed']*100:.0f}%/{m['DnP90']*100:.0f}%/"
                    f"{m['DnMax']*100:.0f}% | {m['CostDrag']:+.1f} |")
    add("")
    add(f"MaxDD tolerance ceiling (Loop-4 convention): >= {MAXDD_CAP*100:.0f}%.")
    add("")

    # -- Table 2: sub-windows, base only -------------------------------------
    add("## Table 2 — sub-windows (H2 2011-2026 / 2016-2020 / 2021+), base IV only "
        "(CAGR / alpha(t))")
    add("")
    sub_names = [n for n in wslices if not n.startswith("FULL")]
    add("| Rule | " + " | ".join(f"{w} CAGR | alpha(t)" for w in sub_names) + " |")
    add("|---|" + "---|" * (2 * len(sub_names)))
    row = ["C-monthly (CITED, winner)"]
    for w in sub_names:
        m = CITED_C["sub"][w]
        row += [_p(m["CAGR"]), f"{m['Alpha']*100:+.1f}pp (t{m['t']:+.1f})"]
    add("| " + " | ".join(row) + " |")
    for rule_label, key in [("E-rsi2topup", "E-rsi2topup"), ("F-monthlydip", "F-monthlydip")]:
        row = [rule_label]
        for w in sub_names:
            m = R[key]["base"][w]
            row += [_p(m["CAGR"]), _a(m)]
        add("| " + " | ".join(row) + " |")
    add("")

    # -- Table 3: cash-starved% ------------------------------------------------
    add("## Table 3 — cash-starved% (base IV, FULL window; SPY-leg/QQQ-leg): \"of days the "
        "leg's OWN entry gate says eligible, fraction the sim carried 0 contracts because "
        "cash could not fund the fresh premium\"")
    add("")
    add("| Rule | Gate | SPY-leg starved% | QQQ-leg starved% |")
    add("|---|---|---|---|")
    s = CITED_C["starved"]
    add(f"| C-monthly (CITED, winner) | GATED | {s[0]*100:.0f}% | {s[1]*100:.0f}% |")
    for rule_label, key, gname in [("E-rsi2topup", "E-rsi2topup", "GATED"),
                                   ("F-monthlydip", "F-monthlydip", "GATED+DIP")]:
        s = R[key]["starved"]
        add(f"| {rule_label} | {gname} | {s[0]*100:.0f}% | {s[1]*100:.0f}% |")
    add("")

    # -- Table 4: Rule E starved-year diagnostic -----------------------------
    add("## Table 4 — Rule E \"no RSI<10 day all year\" diagnostic (FULL window, raw SPY "
        "RSI-2(Wilder)<10 signal days per calendar year, BEFORE the T+1 execution shift)")
    add("")
    add(f"Total calendar years in FULL window: {len(yr_counts)}. Years with ZERO raw "
        f"RSI-2<10 day (sleeve gets NO top-up all year under Rule E): "
        f"**{len(starved_years)}** -> {', '.join(str(y) for y in starved_years.index) or '(none)'}.")
    add("")
    add("| Year | Trading days | Raw RSI<10 days | Executed top-up days |")
    add("|---|---|---|---|")
    for y, row in yr_counts.iterrows():
        flag = " **(starved year)**" if row["raw_days"] == 0 else ""
        add(f"| {y} | {int(row['ndays'])} | {int(row['raw_days'])}{flag} | "
            f"{int(row['exec_days'])} |")
    add("")

    # -- Engine-level GATED+DIP consistency check for Rule F -----------------
    add("## Rule F vs the engine-level GATED+DIP finding (consistency check)")
    add("")
    add("Already-settled engine-level (single-unit, PORTFOLIO frame, Delta=0.50) finding "
        "from `exp_leap_real_sweep.py` / `2026-07-06_leap_real_sweep.md` "
        "(\"pure GATED > DIP/HYST\", CITED):")
    add("")
    add("| Underlying | Gate | alpha vs SPY net-TR (t) |")
    add("|---|---|---|")
    for u in ("SPY", "QQQ"):
        for g in ("GATED", "GATED+DIP"):
            m = CITED_ENGINE_GATE[u][g]
            add(f"| {u} | {g} | {m['Alpha']*100:+.1f}pp (t{m['t']:+.1f}) |")
    add("")
    f_full_base = R["F-monthlydip"]["base"][full_name]
    c_full_base = CITED_C["full"]["base"]
    f_full_damp = R["F-monthlydip"]["damp"][full_name]
    c_full_damp = CITED_C["full"]["damp"]
    consistent = (f_full_base["Alpha"] < c_full_base["Alpha"]) and (f_full_damp["Alpha"] < c_full_damp["Alpha"])
    add(f"Portfolio-level, this script (FULL window, b15/Delta0.50/SPY+QQQ, monthly top-up "
        f"both sides): **F (GATED+DIP entry) base alpha {f_full_base['Alpha']*100:+.1f}pp "
        f"(t{f_full_base['t']:+.1f}) vs C (pure GATED, CITED) base alpha "
        f"{c_full_base['Alpha']*100:+.1f}pp (t{c_full_base['t']:+.1f})**; damp=0.4: F "
        f"{f_full_damp['Alpha']*100:+.1f}pp (t{f_full_damp['t']:+.1f}) vs C "
        f"{c_full_damp['Alpha']*100:+.1f}pp (t{c_full_damp['t']:+.1f}). "
        f"{'CONSISTENT' if consistent else 'INCONSISTENT'} with the engine-level finding "
        f"that dip-gating entries does not help (F underperforms C at both IV settings)."
        if consistent else
        f"Portfolio-level, this script (FULL window): F base alpha "
        f"{f_full_base['Alpha']*100:+.1f}pp (t{f_full_base['t']:+.1f}) vs C base alpha "
        f"{c_full_base['Alpha']*100:+.1f}pp (t{c_full_base['t']:+.1f}); damp=0.4 F "
        f"{f_full_damp['Alpha']*100:+.1f}pp (t{f_full_damp['t']:+.1f}) vs C "
        f"{c_full_damp['Alpha']*100:+.1f}pp (t{c_full_damp['t']:+.1f}). "
        f"**INCONSISTENT with the engine-level finding on at least one IV setting** — "
        f"flagged, not smoothed over.")
    add("")

    # -- Regression check -----------------------------------------------------
    add("## Regression check — Rule C recomputed here vs CITED (`2026-07-06_core_topup.md`)")
    add("")
    add("Recomputed with the IDENTICAL imported engine (GATED gate, monthly trigger, "
        "b15/Delta0.50/SPY+QQQ) purely to confirm the import chain still reproduces the "
        "cited winner numbers before trusting E/F's comparisons against it. Small residual "
        "diffs are expected: this run's `load()` call pulls data through 2026-07-07 (one "
        "extra trading day vs the cited file's 2026-07-06 snapshot).")
    add("")
    add("| Metric | Recomputed here | Cited (2026-07-06) | Diff |")
    add("|---|---|---|---|")
    for label, regen, cited, diff in regress_rows:
        add(f"| {label} | {regen:.4f} | {cited:.4f} | {diff:+.4f} |")
    add("")

    # -- Cross-foot -------------------------------------------------------------
    add("## Cross-foot verification")
    add("")
    add("- All 3 rules' accounting runs (base+base0+damp+damp0 x {E, F, C-regen} = 12 runs) "
        "passed every bar-level assert IMPORTED from `exp_core_topup.simulate_portfolio_topup`: "
        "NAV = core + cash + sum(option market value); cash >= 0; NAV > 0; NAV_t = "
        "NAV_(t-1) + cash interest + core P&L + option P&L - costs (the floor top-up is a "
        "zero-sum internal transfer and does not appear in this identity; rel. tol 1e-6). "
        "Any violation raises and aborts the run — none did.")
    add("")

    add("## Conclusions")
    add("")
    add("(placeholder — filled by hand after reviewing Tables 1-4 and the consistency check above)")
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
    print(f"\nWrote {RESULTS}  ({time.time()-t0:.0f}s total)", flush=True)


if __name__ == "__main__":
    main()
