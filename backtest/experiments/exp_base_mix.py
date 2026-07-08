"""Experiment: does the core v2 BASE HOLDING have to be SPY? A/B vs QQQ / SPMO /
50-50 SPY+QQQ, with the LEAP sleeve spec and the benchmark both held FIXED.

Background (settled, not re-tested here — see docs/2026-07-06_core_strategy_v2.md)
--------
Core v2 = base holding (70% target, never trend-sold) + LEAP sleeve (SPY+QQQ
50/50, pure 200SMA gate, b=15% NAV premium, MONTHLY top-up, delta=0.50 —
`exp_core_topup.py`'s winner cell "C-monthly/b15/Δ0.50/mix") + cash (^IRX,
15% target). The user has never tested WHY the base holding is SPY rather than
QQQ or SPMO — this script answers that with real data, holding everything else
(sleeve spec, cash rule, top-up cadence) fixed, so the ONLY thing varying is the
70%-target base-holding symbol.

Question
--------
Is swapping the base holding from SPY to QQQ / SPMO / a 50-50 SPY+QQQ blend a
real Jensen-alpha improvement, or just a higher-beta bet dressed up as one?
The benchmark is NOT allowed to move (always SPY B&H net-TR) — that is the
whole point: the question IS "beta bet vs alpha," and moving the yardstick
would erase the answer.

Method (mirror / increment / horizon)
------
Mirror     : the SAME 3-bucket program the user would actually run (base
             holding + LEAP sleeve(s) + cash), same real ^VIX/^VXN/^IRX data,
             SAME benchmark (SPY B&H total return, HK 30% dividend withholding
             netted) — never re-pointed at the candidate base holding.
Increment  : ONLY the base-holding symbol (axis below) is new. The LEAP unit
             engine (`simulate_unit_path`) is IMPORTED verbatim from
             `exp_leap_real_sweep.py`; the top-up portfolio simulator
             (`simulate_portfolio_topup`, C-monthly floor rule) is IMPORTED
             verbatim from `exp_core_topup.py` (this repo's settled winner
             mechanics) — not reimplemented. LEAP sleeve mix (SPY+QQQ 50/50),
             b (15%), delta (0.50), cash target (15%) are ALL held fixed at the
             core v2 winner-cell spec.
Horizon    : continuous multi-year program, monthly top-up cadence (rule
             C-monthly, unchanged), LEAP rolled at 63 trading days remaining.

Pre-registered grid (run all, report all)
------
  base-holding candidate: {SPY (status quo), QQQ, SPMO, 50/50 SPY+QQQ
                          (daily-rebalanced average of each leg's own r_net —
                          the standard convention for a continuously-rebalanced
                          blend, cross-term error is negligible at daily
                          frequency)}.
  IV assumption          : {base m=0.85, damp=0.4} — SAME two rows as
                          `exp_core_topup.py`'s disclosure convention; affects
                          ONLY the (fixed) LEAP sleeve's option pricing/marks,
                          never the base-holding return series or the gate
                          (price-driven, IV-independent).
  window A (PRIMARY, all 4 cells) : 2015-10-12+ (SPMO inception, loaded via
                          `data.load(symbol, adjusted=True)`) — the only window
                          every one of the 4 base-holding candidates can share.
  window B (long-history, 3 cells, SPMO excluded — no data pre-2015-10) :
                          2001+ (native start of the SPY+QQQ LEAP-sleeve common
                          window, ^VXN availability — identical convention to
                          `exp_core_topup.py`'s "common_idx").
  = 4 cells x 2 IV (window A) + 3 cells x 2 IV (window B) = 14 portfolio runs.

Per-cell metrics (the point is the beta/alpha split, so both are reported
separately, never conflated)
------
CAGR / annualized Sharpe (raw daily returns) / MaxDD / Jensen alpha (annualized,
t-stat) AND beta vs SPY B&H net-TR (kept as SEPARATE columns, never merged into
one "excess return" figure) / tracking error (annualized) / worst rolling
21-trading-day (~month) return / excess CAGR (RAW arithmetic CAGR difference vs
SPY B&H net-TR over the SAME window — a distinct, non-beta-adjusted number from
Jensen alpha, reported alongside it per spec).

Reading discipline (pre-registered BEFORE running the grid — see docstring
`judge()` below for the exact rule)
------
For every non-SPY cell, compare its beta and alpha-t to the SPY cell in the
SAME window x IV row:
  - beta clearly higher (+0.05 or more) AND alpha-t does NOT meaningfully rise
    (< +0.3 t AND < +0.5pp alpha) over the SPY cell -> flagged "BETA BET" —
    the improvement is a higher risk-appetite wager on the same market factor,
    NOT a new source of skill.
  - alpha-t AND alpha level both rise meaningfully over the SPY cell -> flagged
    "ALPHA GAIN" — reported straight, not explained away.
  - neither condition clearly met -> "INCONCLUSIVE / SIMILAR".
This flag is computed mechanically (not picked after eyeballing the numbers)
and printed in the main table; the hand-written Conclusions section applies it.

SPMO caveats (pre-registered, must be stated regardless of result)
------
- Only 9.7 years of history (2015-10-12 to date) = effectively ONE market
  regime (a momentum bull market with one short 2022 drawdown, one 2020 V-shape
  and one 2025 chop) — a 30-year-class conclusion CANNOT be drawn from window A
  alone, no matter how good the numbers look.
- SPMO's OWN options market is thin/short-history — irrelevant to the BASE
  HOLDING question here (SPMO never enters the LEAP sleeve in this script), but
  relevant to any FUTURE fantasy about running the sleeve itself on SPMO.
- Expense ratio 0.13% (SPMO) vs 0.09% (SPY) — already netted into each fund's
  own adjusted-close total return (no separate adjustment applied here), noted
  for completeness only.

2000-02 regime note (window B)
------
QQQ x ^VXN data starts 2001-01-23 (^VXN availability, same bound as
`exp_core_topup.py`) — i.e. AFTER QQQ's March-2000 peak. Window B's QQQ B&H
MaxDD therefore captures only the POST-peak continuation of the dot-com crash
(2001-2002), not the full peak-to-trough figure (which is deeper, ~-83%,
per widely cited history) — printed and disclosed in Caveats, not silently
extrapolated to "QQQ's crash risk = what Window B shows."

Cross-foot (hard asserts, every bar of every accounting run, inherited
byte-for-byte from `exp_core_topup.simulate_portfolio_topup`): NAV = base-
holding value + cash + sum(option market value); cash >= 0; NAV > 0;
NAV_t = NAV_{t-1} + interest + base-holding P&L + option P&L - costs (the
monthly top-up is a zero-sum internal transfer and does not appear in this
identity).

Run:  PYTHONUTF8=1 python backtest/experiments/exp_base_mix.py
Writes: backtest/results/2026-07-07_base_mix.md
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metrics                                     # noqa: E402
from data import load                              # noqa: E402
from exp_leap_real_sweep import (                   # noqa: E402
    build_underlying, build_gates, simulate_unit_path, TD,
)
from exp_core_assembly_real import (                # noqa: E402
    damp_iv, window_metrics, bench_metrics, _p, _a, _ruin, CAPITAL,
)
from exp_core_topup import (                        # noqa: E402
    simulate_portfolio_topup, month_start_mask, ASSERT_COUNT,
)

DELTA = 0.50
B_TOTAL = 0.15
CASH_W = 0.15
IV_MULT = 0.85
COST_BASE = 0.005
DAMP = 0.4

BASE_VARIANTS_A = ["SPY", "QQQ", "SPMO", "SPY+QQQ 50/50"]
BASE_VARIANTS_B = ["SPY", "QQQ", "SPY+QQQ 50/50"]

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-07_base_mix.md")


# ---------------------------------------------------------------------------
# Data — base-holding-only return series (no vol/gate needed, unlike the sleeve)
# ---------------------------------------------------------------------------

def build_core_only(symbol: str):
    """HK-net total-return series for a candidate BASE HOLDING (no options
    engine needed — same r_net convention as `exp_leap_real_sweep.build_underlying`,
    just without requiring a vol-index join / 200SMA / RSI-2 warm-up)."""
    raw = load(symbol)
    adj = load(symbol, adjusted=True)
    prov = [(symbol, raw.attrs.get("source", "?"), len(raw),
             str(raw.index.min().date()), str(raw.index.max().date())),
            (f"{symbol}(adj)", adj.attrs.get("source", "?"), len(adj),
             str(adj.index.min().date()), str(adj.index.max().date()))]
    close = raw["close"]
    r_adj = adj["close"].pct_change()
    r_raw = close.pct_change()
    dy = (r_adj - r_raw).clip(lower=0.0)
    dy = dy.where(dy > 1e-4, 0.0)          # 1bp threshold: kill adjustment rounding noise
    r_net = r_adj - 0.30 * dy               # HK 30% withholding on dividends
    df = pd.DataFrame({"r_net": r_net}).dropna()
    return df, prov


# ---------------------------------------------------------------------------
# Reading-discipline flag (pre-registered, mechanical — see docstring)
# ---------------------------------------------------------------------------

def judge(m, m_spy):
    if not (np.isfinite(m.get("Beta", np.nan)) and np.isfinite(m_spy.get("Beta", np.nan))):
        return "n/a"
    beta_hi = (m["Beta"] - m_spy["Beta"]) >= 0.05
    t_ok = np.isfinite(m.get("t", np.nan)) and np.isfinite(m_spy.get("t", np.nan))
    alpha_gain = (t_ok and (m["t"] - m_spy["t"]) >= 0.3
                  and (m["Alpha"] - m_spy["Alpha"]) >= 0.005)
    if alpha_gain:
        return "ALPHA GAIN"
    if beta_hi:
        return "BETA BET"
    return "similar/inconclusive"


def cell_label(variant: str, ivlabel: str) -> str:
    return f"{variant} / {ivlabel}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    irx_df = load("^IRX")
    irx = irx_df["close"]
    prov_all = [("^IRX", irx_df.attrs.get("source", "?"), len(irx_df),
                 str(irx_df.index.min().date()), str(irx_df.index.max().date()))]

    # -- LEAP sleeve underlyings (SPY x ^VIX, QQQ x ^VXN) — FIXED spec, never varies --
    sleeve = {}
    for under, volsym in [("SPY", "^VIX"), ("QQQ", "^VXN")]:
        df, prov, _ = build_underlying(under, volsym, irx)
        sleeve[under] = {"df": df}
        prov_all += prov
        print(f"{under} sleeve joined: {df.index[0].date()} -> {df.index[-1].date()}, "
              f"{len(df)} days", flush=True)

    for under, d in sleeve.items():
        df = d["df"]
        d["close"] = df["close"].values
        d["iv_raw"] = df["vol"].values / 100.0 * IV_MULT
        d["r_arr"] = df["irx"].values / 100.0
        d["q_arr"] = df["q"].values
        d["r_cash"] = d["r_arr"] / TD
        d["gate"] = build_gates(df)["GATED"]

    # -- Base-holding candidates: own r_net series, no options engine needed --
    core = {}
    for sym in ["SPY", "QQQ", "SPMO"]:
        cdf, prov = build_core_only(sym)
        core[sym] = cdf
        prov_all += prov
        print(f"{sym} core-only series: {cdf.index[0].date()} -> {cdf.index[-1].date()}, "
              f"{len(cdf)} days", flush=True)

    sleeve_common = sleeve["SPY"]["df"].index.intersection(sleeve["QQQ"]["df"].index)
    idx_B = (sleeve_common.intersection(core["SPY"].index)
             .intersection(core["QQQ"].index))
    idx_A = idx_B.intersection(core["SPMO"].index)
    print(f"Window B (long-history, no SPMO): {idx_B[0].date()} -> {idx_B[-1].date()}, "
          f"{len(idx_B)} days", flush=True)
    print(f"Window A (SPMO-comparable, PRIMARY): {idx_A[0].date()} -> {idx_A[-1].date()}, "
          f"{len(idx_A)} days", flush=True)

    # Sanity anchor
    a_mask = sleeve["SPY"]["df"].index >= "1996-01-01"
    a_lo = int(np.where(a_mask)[0][0])
    anchor_bench = core["SPY"]["r_net"].reindex(sleeve["SPY"]["df"].index).values
    anchor = bench_metrics(anchor_bench, a_lo, len(sleeve["SPY"]["df"]))
    print(f"SANITY SPY B&H TR (HK net) 1996->end: CAGR {anchor['CAGR']*100:.2f}% "
          f"Sharpe {anchor['Sharpe']:.2f} MaxDD {anchor['MaxDD']*100:.1f}%", flush=True)

    # 2000-02 regime note diagnostic: QQQ B&H MaxDD within Window B (partial crash capture)
    qqq_bh_full = core["QQQ"]["r_net"].reindex(idx_B).values
    qqq_bh_metrics = bench_metrics(qqq_bh_full, 0, len(idx_B))
    print(f"QQQ B&H (Window B, 2001+ only, post-peak) MaxDD: "
          f"{qqq_bh_metrics['MaxDD']*100:.1f}% (full 2000-peak MaxDD is deeper, ~-83%, "
          f"not captured here — see Caveats)", flush=True)

    # -- LEAP sleeve unit paths: delta=0.50 ONLY, base (m0.85) + damp (0.4), FIXED --
    native_index = {u: sleeve[u]["df"].index for u in ("SPY", "QQQ")}
    base_paths, damped_paths = {}, {}
    for under in ("SPY", "QQQ"):
        d = sleeve[under]
        iv_damped = damp_iv(d["iv_raw"], DAMP)
        base_paths[under] = simulate_unit_path(
            d["close"], d["iv_raw"], d["r_arr"], d["q_arr"], d["gate"], DELTA)
        damped_paths[under] = simulate_unit_path(
            d["close"], iv_damped, d["r_arr"], d["q_arr"], d["gate"], DELTA)
    print(f"LEAP sleeve unit paths (SPY+QQQ, delta=0.50, base+damp) done "
          f"({time.time()-t0:.0f}s)", flush=True)

    def unit_slice(under, paths_dict, index_target):
        udf = pd.DataFrame(paths_dict[under], index=native_index[under])
        sl = udf.reindex(index_target)
        return {k: sl[k].values for k in udf.columns}

    spy_close_native = pd.Series(sleeve["SPY"]["close"], index=native_index["SPY"])
    qqq_close_native = pd.Series(sleeve["QQQ"]["close"], index=native_index["QQQ"])
    spy_rcash_native = pd.Series(sleeve["SPY"]["r_cash"], index=native_index["SPY"])
    spy_bench_native = core["SPY"]["r_net"]     # FIXED benchmark, never re-pointed

    def legs_for(index_target, paths_dict):
        u_spy = unit_slice("SPY", paths_dict, index_target)
        u_qqq = unit_slice("QQQ", paths_dict, index_target)
        return [{"b": B_TOTAL / 2.0, "unit": u_spy,
                  "close": spy_close_native.reindex(index_target).values},
                {"b": B_TOTAL / 2.0, "unit": u_qqq,
                  "close": qqq_close_native.reindex(index_target).values}]

    def r_cash_for(index_target):
        return spy_rcash_native.reindex(index_target).values

    def bench_for(index_target):
        return spy_bench_native.reindex(index_target).values

    def core_ret_for(variant, index_target):
        if variant == "SPY+QQQ 50/50":
            s = (0.5 * core["SPY"]["r_net"].reindex(index_target)
                 + 0.5 * core["QQQ"]["r_net"].reindex(index_target))
            return s.values
        return core[variant]["r_net"].reindex(index_target).values

    WINDOWS = [("Window A (2015-10-12+, SPMO-comparable, PRIMARY)", idx_A, BASE_VARIANTS_A),
               ("Window B (2001+, long-history, no SPMO)", idx_B, BASE_VARIANTS_B)]

    R = {}          # (wname, variant, ivlabel) -> metrics dict
    BENCH_FULL = {}  # wname -> SPY B&H bench_metrics over that window

    for wname, widx, variants in WINDOWS:
        legs_base = legs_for(widx, base_paths)
        legs_damp = legs_for(widx, damped_paths)
        r_cash_w = r_cash_for(widx)
        bench_w = bench_for(widx)
        month_mask = month_start_mask(widx)
        bench_full = bench_metrics(bench_w, 0, len(widx))
        BENCH_FULL[wname] = bench_full

        for variant in variants:
            core_ret_w = core_ret_for(variant, widx)
            for ivlabel, legs in [("base m0.85", legs_base), ("damp 0.4", legs_damp)]:
                res = simulate_portfolio_topup(legs, core_ret_w, r_cash_w, COST_BASE,
                                                CASH_W, "C-monthly", B_TOTAL, month_mask)
                m = window_metrics(res, bench_w, widx, 0, len(widx))
                m["ExcessCAGR"] = m["CAGR"] - bench_full["CAGR"]
                R[(wname, variant, ivlabel)] = m
                print(f"{wname} | {cell_label(variant, ivlabel)} done "
                      f"({time.time()-t0:.0f}s)", flush=True)

    # ------------------------------------------------------------------
    # Write results markdown
    # ------------------------------------------------------------------
    L = []
    add = L.append
    add("# Result — Core v2 base holding: SPY vs QQQ vs SPMO vs 50/50 SPY+QQQ "
        "(fixed LEAP sleeve + fixed benchmark, real data)")
    add("")
    add("**Date:** 2026-07-07  **Script:** `backtest/experiments/exp_base_mix.py`  "
        "**Status:** active")
    add("")
    add("## Question")
    add("")
    add("Core v2 (`docs/2026-07-06_core_strategy_v2.md`) never tested WHY the base "
        "holding is SPY rather than QQQ or SPMO. This script A/Bs the base holding "
        "{SPY, QQQ, SPMO, 50/50 SPY+QQQ} while holding the LEAP sleeve (SPY+QQQ 50/50, "
        "pure 200SMA gate, b=15% NAV, C-monthly top-up, Δ=0.50 — the settled winner "
        "cell from `exp_core_topup.py`) and cash (15% NAV, ^IRX) FIXED. Benchmark is "
        "ALSO fixed at SPY B&H total return (HK 30% dividend withholding netted) — it "
        "is never re-pointed at the candidate base holding, because the question IS "
        "\"beta bet vs alpha,\" and moving the yardstick would erase the answer.")
    add("")
    add("## Method")
    add("")
    add("- LEAP unit engine (`simulate_unit_path`) IMPORTED verbatim from "
        "`exp_leap_real_sweep.py`; portfolio top-up simulator "
        "(`simulate_portfolio_topup`, rule=C-monthly) IMPORTED verbatim from "
        "`exp_core_topup.py` — not reimplemented. Only the base-holding return series "
        "(axis below) is new plumbing in this script.")
    add("- Base-holding candidates use their OWN adjusted-close total return, HK 30% "
        "dividend withholding netted (same `r_net` formula as "
        "`exp_leap_real_sweep.build_underlying`, computed standalone here since the "
        "base holding needs no options engine / 200SMA / RSI-2 warm-up). 50/50 SPY+QQQ "
        "= daily-rebalanced average of each leg's own r_net (standard continuously-"
        "rebalanced-blend convention; cross-term error negligible at daily frequency).")
    add("- Windows: **Window A (PRIMARY)** = 2015-10-12+ (SPMO inception via "
        "`data.load(symbol, adjusted=True)`), all 4 base-holding cells share it. "
        "**Window B** = 2001+ (native start of the SPY+QQQ LEAP-sleeve common window, "
        "^VXN availability — identical convention to `exp_core_topup.py`), 3 cells "
        "(SPMO excluded — no data pre-2015-10).")
    add("- Every cell reports BOTH a base-IV (m=0.85) row and an IV-damped (damp=0.4) "
        "row — same disclosure convention as `exp_core_topup.py` — affecting ONLY the "
        "(fixed) LEAP sleeve's option pricing, never the base-holding return series or "
        "the price-driven 200SMA gate.")
    add("- **Reading discipline (pre-registered, mechanical — not picked after seeing "
        "numbers)**: for every non-SPY cell, compare beta and alpha-t to the SPY cell "
        "in the SAME window x IV row. Beta higher by >=0.05 AND alpha-t does NOT rise "
        "by >=0.3 (and alpha level by >=0.5pp) -> **BETA BET** (a higher risk-appetite "
        "wager on the same market factor, not a new source of skill). Both rise "
        "meaningfully -> **ALPHA GAIN** (reported straight). Neither -> "
        "**similar/inconclusive**.")
    add("- Costs: 0.5%/side of option premium (LEAP legs only); base-holding trades "
        "(monthly top-up, annual/roll transfers) zero-cost (ETF shares). Sharpe = raw "
        "daily returns. CAPITAL = $500,000.")
    add("")
    add("## Data provenance (`backtest/data.py` `load()`)")
    add("")
    add("| Series | Source | Rows | From | To |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in prov_all:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")
    add(f"- Window A (PRIMARY, SPMO-comparable): {idx_A[0].date()} -> {idx_A[-1].date()} "
        f"({len(idx_A)} days).")
    add(f"- Window B (long-history, no SPMO): {idx_B[0].date()} -> {idx_B[-1].date()} "
        f"({len(idx_B)} days).")
    add(f"- Sanity anchor — SPY B&H TR (HK net) 1996-01->{sleeve['SPY']['df'].index[-1].date()}: "
        f"CAGR **{anchor['CAGR']*100:.2f}%**, Sharpe {anchor['Sharpe']:.2f}, MaxDD "
        f"{anchor['MaxDD']*100:.1f}% (pre-registered acceptance band 9-11%).")
    add(f"- QQQ B&H, Window B (2001+ only, POST-peak): MaxDD **{qqq_bh_metrics['MaxDD']*100:.1f}%** "
        "— this window starts AFTER QQQ's March-2000 peak (^VXN availability bound), so it "
        "captures only the continuation of the dot-com crash (2001-2002), NOT the full "
        "peak-to-trough figure (widely cited at roughly -83%). Do not read Window B's QQQ "
        "MaxDD as \"QQQ's worst case.\"")
    add("")

    # -- Main table: window A (PRIMARY) --------------------------------------
    add("## Table 1 — Window A (2015-10-12+, SPMO-comparable, PRIMARY): all 4 base-"
        "holding candidates, base+damp IV")
    add("")
    add(f"SPY B&H benchmark this window: CAGR {_p(BENCH_FULL[WINDOWS[0][0]]['CAGR'], 2)}, "
        f"Sharpe {BENCH_FULL[WINDOWS[0][0]]['Sharpe']:.2f}, "
        f"MaxDD {_p(BENCH_FULL[WINDOWS[0][0]]['MaxDD'])}.")
    add("")
    add("| Base holding | IV | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | β | TE | "
        "Worst mo | Excess CAGR (raw) | Judge |")
    add("|---|---|---|---|---|---|---|---|---|---|---|")
    wnameA = WINDOWS[0][0]
    for variant in BASE_VARIANTS_A:
        for ivlabel in ["base m0.85", "damp 0.4"]:
            m = R[(wnameA, variant, ivlabel)]
            m_spy = R[(wnameA, "SPY", ivlabel)]
            jg = "(status quo)" if variant == "SPY" else judge(m, m_spy)
            add(f"| {variant} | {ivlabel} | {_p(m['CAGR'])}{_ruin(m)} | {m['Sharpe']:.2f} | "
                f"{_p(m['MaxDD'])} | {_a(m)} | {m['Beta']:.2f} | {_p(m['TE'])} | "
                f"{_p(m['WorstMonth'])} | {_p(m['ExcessCAGR'])} | {jg} |")
    add("")

    # -- Main table: window B --------------------------------------------------
    add("## Table 2 — Window B (2001+, long-history, no SPMO): 3 base-holding "
        "candidates, base+damp IV")
    add("")
    wnameB = WINDOWS[1][0]
    add(f"SPY B&H benchmark this window: CAGR {_p(BENCH_FULL[wnameB]['CAGR'], 2)}, "
        f"Sharpe {BENCH_FULL[wnameB]['Sharpe']:.2f}, MaxDD {_p(BENCH_FULL[wnameB]['MaxDD'])}. "
        f"QQQ B&H this window: CAGR {_p(qqq_bh_metrics['CAGR'], 2)}, Sharpe "
        f"{qqq_bh_metrics['Sharpe']:.2f}, MaxDD {_p(qqq_bh_metrics['MaxDD'])} "
        "(post-peak only — see note above).")
    add("")
    add("| Base holding | IV | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | β | TE | "
        "Worst mo | Excess CAGR (raw) | Judge |")
    add("|---|---|---|---|---|---|---|---|---|---|---|")
    for variant in BASE_VARIANTS_B:
        for ivlabel in ["base m0.85", "damp 0.4"]:
            m = R[(wnameB, variant, ivlabel)]
            m_spy = R[(wnameB, "SPY", ivlabel)]
            jg = "(status quo)" if variant == "SPY" else judge(m, m_spy)
            add(f"| {variant} | {ivlabel} | {_p(m['CAGR'])}{_ruin(m)} | {m['Sharpe']:.2f} | "
                f"{_p(m['MaxDD'])} | {_a(m)} | {m['Beta']:.2f} | {_p(m['TE'])} | "
                f"{_p(m['WorstMonth'])} | {_p(m['ExcessCAGR'])} | {jg} |")
    add("")
    add("**Sanity check**: the `SPY` row of Table 2 (base m0.85 / damp 0.4) is the SAME "
        "spec as `exp_core_topup.py`'s winner cell (C-monthly/b15/Δ0.50/mix) on "
        "effectively the same 2001+ window — its numbers should closely reproduce "
        "`backtest/results/2026-07-06_core_topup.md`'s published winner-cell figures "
        "(α base +12.4pp t+5.4, damp +6.5pp t+3.1, CAGR 22.3%/16.1%, MaxDD "
        "-54.5%/-55.6%) as an independent re-implementation check.")
    add("")

    # -- Cross-foot -------------------------------------------------------------
    add("## Cross-foot verification")
    add("")
    add(f"- {ASSERT_COUNT['runs']} accounting runs, {ASSERT_COUNT['n']:,} bar-level "
        "assertions, ALL passed (inherited byte-for-byte from "
        "`exp_core_topup.simulate_portfolio_topup`): NAV = base-holding value + cash + "
        "sum(option market value); cash >= 0; NAV > 0; NAV_t = NAV_(t-1) + interest + "
        "base-holding P&L + option P&L - costs (the monthly top-up is a zero-sum "
        "internal transfer, rel. tol 1e-6). Any violation raises and aborts the run.")
    add("")

    add("## Conclusions")
    add("")
    add("(placeholder — filled by hand after reviewing Tables 1-2)")
    add("")
    add("## Caveats")
    add("")
    add("- **SPMO (Window A only)**: 9.7 years of history (2015-10-12 to date) = "
        "effectively ONE market regime (a momentum bull market with one short 2022 "
        "drawdown, one 2020 V-shape, one 2025 chop) — a 30-year-class conclusion cannot "
        "be drawn from Window A alone, however the numbers look. SPMO's own options "
        "market is thin/short-history (irrelevant here — SPMO never enters the LEAP "
        "sleeve — but relevant to any future idea of running the sleeve itself on "
        "SPMO). Expense ratio 0.13% (SPMO) vs 0.09% (SPY) is already netted into each "
        "fund's own adjusted-close total return; no separate adjustment applied.")
    add("- **QQQ / Window B dot-com coverage**: ^VXN availability starts 2001-01-23, "
        "AFTER QQQ's March-2000 peak, so Window B's QQQ B&H MaxDD "
        f"({_p(qqq_bh_metrics['MaxDD'])}) captures only the POST-peak continuation of "
        "the dot-com crash, not the full peak-to-trough figure (widely cited near "
        "-83%). Do not read this as QQQ's full crash-risk envelope.")
    add("- 50/50 SPY+QQQ base holding uses a daily-average-of-returns approximation for "
        "a continuously-rebalanced blend (not a literal daily-rebalance simulation with "
        "its own transaction costs) — immaterial at this frequency but noted for "
        "completeness.")
    add("- Single historical path, no bootstrap; multiple-testing correction not run "
        "here (only 4/3-cell grids, and the SPY cells are sanity anchors, not new "
        "trials competing with the already Bonferroni-corrected `exp_core_topup.py` "
        "winner).")
    add("(additional caveats to be added by hand after number review)")
    add("")
    add("## Implication")
    add("")
    add("(placeholder — filled by hand after reviewing Tables 1-2)")
    add("")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS}  ({time.time()-t0:.0f}s total, "
          f"{ASSERT_COUNT['n']:,} asserts / {ASSERT_COUNT['runs']} runs)", flush=True)


if __name__ == "__main__":
    main()
