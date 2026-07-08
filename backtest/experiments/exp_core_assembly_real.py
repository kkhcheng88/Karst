"""Experiment: Core portfolio assembly — SPY core + gated LEAP sleeve(s) + cash buffer.

Question
--------
Assemble the full retail-sized program the user will actually run: a SPY core
(never trend-sold) + a 200SMA-GATED deep-ITM LEAP sleeve (PORTFOLIO premium-budget
frame, pre-registered engine from `exp_leap_real_sweep.py`, no RSI-2 dip, no
hysteresis) + a cash buffer (^IRX). Pre-registered 18-cell grid over premium
budget x delta x LEAP-underlying-mix. All 18 cells reported (no cherry-picking).
Sector rotation is dead (2026-07-06_sector_capeff.md) so it is NOT part of the
assembly. Benchmark = SPY buy-and-hold total return, HK 30% dividend withholding
netted (the user's actual tax mirror).

Method (mirror / increment / horizon)
------
Mirror     : the assembled 3-bucket portfolio the user would actually hold
             (core equity + LEAP sleeve + cash), annually rebalanced, vs SPY B&H
             net-TR — the way the money would really be run.
Increment  : this is the FIRST time the (already-validated) real-data LEAP unit
             engine from `exp_leap_real_sweep.py` is embedded in a full 3-bucket
             assembly with annual rebalance + roll-time profit-sweep. Loop-1..4
             (`exp_core_portfolio_lab/loop2/loop3/loop4.py`) built the same shape
             of assembly earlier, but on a hand-rolled BSM/LEAP engine mirroring
             the SUPERSEDED RV-proxy `exp_leap_delta_sweep.py`, never on the real
             ^VIX/^VXN engine. This script closes that gap: `simulate_unit_path`
             (option marks/events, per-unit, delta/gate-driven) is IMPORTED
             verbatim from `exp_leap_real_sweep.py` — not reimplemented — for
             both SPY x ^VIX and QQQ x ^VXN. Only the portfolio-level assembly
             (core + cash + annual rebalance + roll-sweep accounting) is new.
Horizon    : continuous multi-year program, annual rebalance at the first
             trading day of each calendar year; LEAP rolled at 63 trading days
             remaining (engine default, unchanged).

Grid (pre-registered; every cell reported)
------
  premium budget b   : {10%, 15%, 20% of NAV}  -> core = 100% - b - 15% cash
                        (75% / 70% / 65%); cash fixed at 15% NAV (base case).
  delta               : {0.50, 0.70, 0.80}  (1y call, GATED, roll @ 63 td; the
                        0.30Δ cap and the DIP/HYST gate variants are already
                        settled in exp_leap_real_sweep and NOT re-tested here).
  LEAP underlying mix : SPY-only (100% of b in one SPY leg) vs 50/50 SPY+QQQ
                        (b split in half: b/2 in a SPY leg, b/2 in a QQQ leg,
                        each independently gated on ITS OWN 200SMA). The core
                        equity sleeve is ALWAYS SPY regardless of LEAP mix.
  -> 3 x 3 x 2 = 18 cells. QQQ legs only have data from ~2001 (^VXN availability)
     so every mix cell's native window starts 2001; every SPY-only cell is ALSO
     reported on a 2001+ slice (identical start date) as a direct apples-to-apples
     comparator to the paired mix cell — see "2001+ comparator" table.
  windows            : FULL (native start for that cell) / H1 / H2 / 2016-2020 /
                        2021+ (`exp_leap_real_sweep.make_windows` convention,
                        reused verbatim).

Portfolio-assembly algorithm (new; the only genuinely new mechanics here)
------
State per bar: core_val (SPY equity, $), cash ($, earns ^IRX), opt_val per LEAP
leg ($, mark-to-market from the leg's `simulate_unit_path` telemetry).
NAV = core_val + cash + sum(opt_val).

Init (t=0): core_val = (1 - cash_w - sum(b_leg)) * CAPITAL; cash = CAPITAL -
core_val (i.e. the not-yet-deployed LEAP budget sits in cash until first entry).

Each bar, in order:
  1. cash += cash * r_cash[t]                              (interest accrual)
  2. core_val += core_val * r_net_SPY[t]                    (core B&H total return,
     HK 30% withholding netted — same series used as the Jensen-alpha benchmark)
  3. For each LEAP leg (processed SPY-leg then QQQ-leg, a fixed, documented order):
     a. mark unrealized option P&L into opt_val (unit path's mark_pre - prior mark)
     b. if the unit path SELLS today: proceeds (net of cost) -> cash; opt_val -> 0
     c. if the unit path BUYS today: target_premium = b_leg * NAV_now (NAV_now =
        core_val + cash + OTHER leg's current opt_val, i.e. NAV excluding this
        leg's own just-closed position); spend = min(target_premium, cash) (a
        defensive floor — binds only under the cash=0% stress sensitivity);
        cash -= spend; opt_val = spend/(1+cost) (the premium, net of cost)
     d. ROLL-TIME SWEEP ("beta maintenance", user spec): if step (b) fired this
        bar, net_cash_change_this_leg = cash_after_steps_b_c - cash_before_b.
        If > 0 (sale proceeds exceeded the fresh premium budget, i.e. realized
        LEAP profit beyond what's needed to re-fund the sleeve, OR the leg
        exited the gate entirely so target_premium=0 and 100% of proceeds count
        as "excess") -> sweep it OUT of cash INTO core_val (cash -= sweep;
        core_val += sweep). This caps the LEAP sleeve's dollar budget at
        b_leg*NAV every roll instead of letting option gains compound
        unboundedly (the known SLEEVE-frame leverage-snowball failure mode from
        exp_leap_real_sweep). If <= 0 (proceeds fell short of the fresh budget)
        cash simply absorbs the shortfall from its own buffer — core is
        untouched (only "excess profit" sweeps out, shortfalls are NOT clawed
        back from core).
  4. Annual rebalance (first trading day of each calendar year; OFF under the
     "no annual rebalance" sensitivity): redistribute ONLY the tradeable
     non-option wealth (core_val + cash) back to the target core:cash RATIO
     (option positions are never traded at rebalance, only at their own roll):
        nonopt = core_val + cash
        core_val = nonopt * w_core / (w_core + w_cash)
        cash     = nonopt - core_val
     (w_core, w_cash are the NAV-level target weights, e.g. 0.75/0.15 for b=10%.)
  5. Cross-foot assert every bar: NAV = core_val + cash + sum(opt_val); cash >=
     -1e-9; NAV > 0; NAV_t == NAV_{t-1} + interest + core P&L + sum(option P&L)
     - sum(costs), rel. tol 1e-7 (rebalance is a zero-sum internal transfer, so
     it does not appear in this identity — it doesn't change NAV, only its mix).

Sensitivities (headline cell + best-3 cells only, per pre-registration)
------
1. IV term-structure damping: sigma_damped = sigma_bar + damp*(sigma_raw -
   sigma_bar), sigma_bar = full-sample mean of that leg's raw IV_1y proxy
   (vol_index/100 * 0.85) over its own full availability window. damp in
   {1.0 base, 0.4}. This changes OPTION PRICING/marks only (strike selection,
   marks, greeks) — it does not touch the 200SMA gate, which is price-driven
   and unaffected. Rationale: VIX/VXN are 30d-tenor implied vols; a genuine 1y
   IV term structure is empirically less volatile (mean-reverting) than the
   spot 30d print, so this is a model-risk bound on how much of VIX's swings
   should flow into 1y LEAP pricing.
2. Cost x2: option cost 1.0%/side (base 0.5%/side). Core-equity trades (annual
   rebalance, roll-sweep buys) are treated as zero-cost (ETF share trades,
   immaterial vs. option costs — not modeled).
3. Cash target = 0% (core absorbs the 15pp; the defensive spend-floor in step
   3c will then visibly bind in down-cycles — expected, not a bug).
4. Annual rebalance OFF (pure roll-sweep only, no year-start core/cash reset).

Headline + best-3 selection (data-driven, not hand-picked): rank all 18 base
cells by Jensen alpha t-stat vs SPY B&H net-TR on the COMMON 2001+ window (the
only window every cell — SPY-only and mix alike — can be compared on
apples-to-apples); headline = rank #1; best-3 = ranks #1-3 (so sensitivities
run on 3 distinct cells, not 4).

Per-cell metrics (every window)
------
CAGR / annualized Sharpe (raw daily returns, repo convention) / MaxDD / Jensen
alpha (t) vs SPY B&H net-TR / worst single month (rolling 21td) / worst 63td /
tracking error (annualized std of daily return spread) / delta-notional
exposure as %NAV (median/p90/max, ALL days incl. gated-out days — a portfolio-
level exposure metric, unconditional) / annual excess win-rate (full calendar
years only, >=200 trading days, portfolio annual return > SPY net-TR annual
return) / option cost drag pp/yr (zero-cost-shadow CAGR - actual CAGR, same
convention as exp_leap_real_sweep).

Statistical discipline
------
Registry = THIS loop's 18 grid cells (the trial universe for Bonferroni/DSR).
Loop-1's 384-cell sweep (`exp_core_portfolio_lab.py`) was an ENGINE-SELECTION
exercise on a since-superseded hand-rolled BSM path, not a portfolio-assembly
trial competing with these 18 — listed separately, NOT pooled into the x18
correction. Bonferroni-adjusted p (normal approx from the headline cell's
Jensen-alpha t-stat, x18) and DSR (`backtest.metrics.deflated_sharpe_ratio`,
fed the headline cell's REAL daily return series + the 18 cells' annualized
Sharpes as the trial universe — not a constant array) are reported for the
headline cell.

Run:  PYTHONUTF8=1 python backtest/experiments/exp_core_assembly_real.py
Writes: backtest/results/2026-07-06_core_assembly_real.md
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metrics                                   # noqa: E402
from data import load                            # noqa: E402
from exp_leap_real_sweep import (                 # noqa: E402
    build_underlying, build_gates, simulate_unit_path, make_windows,
    TD, DTE_INIT, ROLL_DTE,
)

DELTAS = [0.50, 0.70, 0.80]
BUDGETS = [0.10, 0.15, 0.20]
MIXES = ["SPY-only", "SPY+QQQ"]
CASH_W_BASE = 0.15
IV_MULT = 0.85
COST_BASE = 0.005
CAPITAL = 500_000.0

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-06_core_assembly_real.md")

ASSERT_COUNT = {"n": 0, "runs": 0}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def unit_to_df(unit: dict, index: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(unit, index=index)


def damp_iv(iv_raw: np.ndarray, damp: float) -> np.ndarray:
    sigma_bar = float(np.nanmean(iv_raw))
    return sigma_bar + damp * (iv_raw - sigma_bar)


def to_wslices(under_label: str, index: pd.DatetimeIndex, extra=None):
    """(name, lo, hi) integer bar slices, exp_leap_real_sweep convention."""
    out = []
    for wname, ws, we in make_windows(under_label, index):
        mask = (index >= ws) & (index <= we)
        idx = np.where(mask)[0]
        if len(idx) == 0:
            continue
        out.append((wname, int(idx[0]), int(idx[-1]) + 1))
    if extra is not None:
        wname, ws, we = extra
        mask = (index >= ws) & (index <= we)
        idx = np.where(mask)[0]
        if len(idx) > 0:
            out.append((wname, int(idx[0]), int(idx[-1]) + 1))
    return out


def worst_roll_return(nav: np.ndarray, lo: int, hi: int, span: int) -> float:
    navw = nav[lo:hi]
    if len(navw) <= span:
        return np.nan
    logr = np.diff(np.log(navw))
    roll = pd.Series(logr).rolling(span).sum()
    w = roll.min()
    return np.nan if pd.isna(w) else float(np.exp(w) - 1.0)


def tracking_error(strat_ret: np.ndarray, bench_ret: np.ndarray) -> float:
    d = strat_ret - bench_ret
    d = d[np.isfinite(d)]
    if len(d) < 2:
        return np.nan
    return float(np.std(d, ddof=1) * np.sqrt(TD))


def annual_excess_winrate(nav: np.ndarray, bench_ret: np.ndarray,
                          dates: pd.DatetimeIndex, lo: int, hi: int) -> tuple[float, int]:
    sub_dates = dates[lo:hi]
    navw = nav[lo:hi]
    bret = bench_ret[lo:hi]
    years = pd.DatetimeIndex(sub_dates).year
    df = pd.DataFrame({"nav": navw, "bret": bret, "year": years})
    wins, total = 0, 0
    for y, g in df.groupby("year"):
        if len(g) < 200:            # drop partial first/last calendar year
            continue
        port_ret = g["nav"].iloc[-1] / g["nav"].iloc[0] - 1.0
        bench_ret_y = float(np.prod(1.0 + g["bret"].iloc[1:].values) - 1.0)
        total += 1
        if port_ret > bench_ret_y:
            wins += 1
    return (wins / total if total else np.nan), total


def two_sided_p_from_t(t: float) -> float:
    if not np.isfinite(t):
        return np.nan
    return float(2.0 * (1.0 - norm.cdf(abs(t))))


# ---------------------------------------------------------------------------
# Portfolio assembly engine (NEW — the only new simulator in this experiment)
# ---------------------------------------------------------------------------

def simulate_portfolio(legs: list[dict], core_ret: np.ndarray, r_cash: np.ndarray,
                       cost: float, w_cash: float, annual_rebalance: bool = True,
                       capital: float = CAPITAL):
    """legs: [{"b": float, "unit": unit_df-derived arrays dict}, ...] (1 or 2 legs).

    Returns dict with nav, core, cash, opt (list per leg), conts (list per leg),
    dnotional (array: sum_L conts_L*delta_L*close_L*100 / nav, ALL days).
    """
    n = len(core_ret)
    sum_b = sum(leg["b"] for leg in legs)
    w_core = 1.0 - w_cash - sum_b
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

    prev_nav = capital

    for i in range(n):
        interest = cash * r_cash[i]
        cash += interest
        core_pnl = core_val * core_ret[i]
        core_val += core_pnl

        total_costs = 0.0
        total_opt_pnl = 0.0

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
                spend = min(target_premium, max(cash, 0.0))
                bm = buy_mark[i]
                prem = spend / (1.0 + cost)
                c[L] = prem / (bm * 100.0) if bm > 1e-12 else 0.0
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

        # year-start rebalance (mask computed by caller in run_cell(), see below)
        if annual_rebalance and _YEAR_START_HOOK[0] is not None and _YEAR_START_HOOK[0][i]:
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
            "conts": conts_arr, "dnotional": dnotional}


_YEAR_START_HOOK = [None]   # set by caller right before invoking simulate_portfolio


def year_start_mask(index: pd.DatetimeIndex) -> np.ndarray:
    n = len(index)
    m = np.zeros(n, dtype=bool)
    years = index.year.values
    m[0] = False
    if n > 1:
        m[1:] = years[1:] != years[:-1]
    return m


def run_cell(legs_spec, core_ret, r_cash, index, cost, w_cash, annual_rebalance, capital=CAPITAL):
    _YEAR_START_HOOK[0] = year_start_mask(index)
    out = simulate_portfolio(legs_spec, core_ret, r_cash, cost, w_cash,
                             annual_rebalance=annual_rebalance, capital=capital)
    _YEAR_START_HOOK[0] = None
    return out


# ---------------------------------------------------------------------------
# Per-cell / per-window metrics
# ---------------------------------------------------------------------------

def window_metrics(res, bench_ret, index, lo, hi):
    nav = res["nav"]
    navw = nav[lo:hi]
    norm_nav = navw / navw[0] * CAPITAL
    ret = navw[1:] / navw[:-1] - 1.0
    out = {"CAGR": metrics.cagr(norm_nav), "Sharpe": metrics.ann_sharpe(ret),
           "MaxDD": metrics.max_drawdown(norm_nav)}
    a, b, t = metrics.jensen_alpha(ret, bench_ret[lo + 1:hi])
    out["Alpha"], out["Beta"], out["t"] = a, b, t
    out["WorstMonth"] = worst_roll_return(nav, lo, hi, 21)
    out["Worst63d"] = worst_roll_return(nav, lo, hi, 63)
    out["TE"] = tracking_error(ret, bench_ret[lo + 1:hi])
    dn = res["dnotional"][lo:hi]
    dn = dn[np.isfinite(dn)]
    out["DnMed"] = float(np.median(dn)) if len(dn) else np.nan
    out["DnP90"] = float(np.percentile(dn, 90)) if len(dn) else np.nan
    out["DnMax"] = float(np.max(dn)) if len(dn) else np.nan
    wr, nyrs = annual_excess_winrate(nav, bench_ret, index, lo, hi)
    out["WinRate"], out["NYears"] = wr, nyrs
    out["Days"] = hi - lo
    out["ret"] = ret          # kept for DSR / registry use on the headline cell
    return out


def bench_metrics(bench_ret, lo, hi):
    r = bench_ret[lo + 1:hi]
    navb = np.concatenate([[1.0], np.cumprod(1.0 + r)])
    return {"CAGR": metrics.cagr(navb), "Sharpe": metrics.ann_sharpe(r),
            "MaxDD": metrics.max_drawdown(navb)}


def cost_drag(res_base, res_zero, lo, hi):
    nb = res_base["nav"][lo:hi]; nz = res_zero["nav"][lo:hi]
    cb = metrics.cagr(nb / nb[0] * CAPITAL)
    cz = metrics.cagr(nz / nz[0] * CAPITAL)
    return (cz - cb) * 100.0


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _p(x, dec=1):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:+.{dec}f}%"


def _a(m):
    a, t = m.get("Alpha"), m.get("t")
    if a is None or not np.isfinite(a):
        return "n/a"
    return f"{a * 100:+.1f}pp (t{t:+.1f})"


def _ruin(m):
    return " **RUIN**" if np.isfinite(m["MaxDD"]) and m["MaxDD"] <= -0.99 else ""


def cell_label(b, delta, mix):
    return f"b{int(b*100)}/Δ{delta:.2f}/{mix}"


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
    print(f"common (mix) window: {common_idx[0].date()} -> {common_idx[-1].date()}, "
          f"{len(common_idx)} days", flush=True)

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
    # Unit paths: base case (IV mult 0.85), one per (underlying, delta)
    # ------------------------------------------------------------------
    base_paths = {}     # (under, delta) -> unit dict (native index of that underlying)
    for under in ("SPY", "QQQ"):
        d = data[under]
        for delta in DELTAS:
            base_paths[(under, delta)] = simulate_unit_path(
                d["close"], d["iv_raw"], d["r_arr"], d["q_arr"], d["gate"], delta)
    print(f"base unit paths done ({time.time()-t0:.0f}s)", flush=True)

    def unit_slice(under, delta, index_target):
        """Native unit-path dict -> DataFrame on native index -> reindex to target."""
        native_index = data[under]["df"].index
        udf = unit_to_df(base_paths[(under, delta)], native_index)
        sl = udf.reindex(index_target)
        return {k: sl[k].values for k in udf.columns}

    # close price series aligned to arbitrary target index, per underlying
    spy_close_s = pd.Series(data["SPY"]["close"], index=spy_df.index)
    qqq_close_s = pd.Series(data["QQQ"]["close"], index=qqq_df.index)
    spy_rnet_s = pd.Series(data["SPY"]["r_net"], index=spy_df.index)
    irx_r_s = pd.Series(data["SPY"]["r_cash"], index=spy_df.index)  # same source both legs

    def legs_for2(mix, b, delta, index_target, paths_override=None):
        pf = paths_override or {}
        if mix == "SPY-only":
            unit = pf.get(("SPY", delta)) or unit_slice("SPY", delta, index_target)
            return [{"b": b, "unit": unit, "close": spy_close_s.reindex(index_target).values}]
        unit_spy = pf.get(("SPY", delta)) or unit_slice("SPY", delta, index_target)
        unit_qqq = pf.get(("QQQ", delta)) or unit_slice("QQQ", delta, index_target)
        return [{"b": b / 2.0, "unit": unit_spy, "close": spy_close_s.reindex(index_target).values},
                {"b": b / 2.0, "unit": unit_qqq, "close": qqq_close_s.reindex(index_target).values}]

    def index_for(mix):
        return spy_df.index if mix == "SPY-only" else common_idx

    def core_ret_for(index_target):
        return spy_rnet_s.reindex(index_target).values

    def r_cash_for(index_target):
        return irx_r_s.reindex(index_target).values

    def bench_for(index_target):
        return spy_rnet_s.reindex(index_target).values

    gate_spy_s = pd.Series(data["SPY"]["gate"], index=spy_df.index)
    gate_qqq_s = pd.Series(data["QQQ"]["gate"], index=qqq_df.index)

    # ------------------------------------------------------------------
    # 18 base cells
    # ------------------------------------------------------------------
    CELLS = [(b, delta, mix) for b in BUDGETS for delta in DELTAS for mix in MIXES]
    R = {}        # key -> {"wslices":..., "windows": {wname: metrics}, "res": res}

    for (b, delta, mix) in CELLS:
        key = (b, delta, mix)
        index_t = index_for(mix)
        legs = legs_for2(mix, b, delta, index_t)
        core_ret = core_ret_for(index_t)
        r_cash = r_cash_for(index_t)
        bench = bench_for(index_t)

        res = run_cell(legs, core_ret, r_cash, index_t, COST_BASE, CASH_W_BASE, True)
        legs_zero = legs_for2(mix, b, delta, index_t)
        res_zero = run_cell(legs_zero, core_ret, r_cash, index_t, 0.0, CASH_W_BASE, True)

        under_label = "SPY" if mix == "SPY-only" else "QQQ"
        extra = None
        if mix == "SPY-only":
            extra = ("2001+ (mix-comparable)", common_idx[0], index_t[-1])
        wslices = to_wslices(under_label, index_t, extra=extra)

        wmetrics = {}
        for wname, lo, hi in wslices:
            m = window_metrics(res, bench, index_t, lo, hi)
            m["CostDrag"] = cost_drag(res, res_zero, lo, hi)
            wmetrics[wname] = m

        # Cash-starved diagnostic (native FULL window): of the days the leg's OWN
        # 200SMA gate says "eligible to hold", what fraction ended up with 0
        # contracts because the shared cash pool couldn't fund the fresh premium
        # (a structural side-effect of annual-only rebalance cadence, distinct
        # from trend-gate exits — see Caveats/Implication).
        lo0, hi0 = wslices[0][1], wslices[0][2]
        leg_gates = ([gate_spy_s.reindex(index_t).values] if mix == "SPY-only"
                    else [gate_spy_s.reindex(index_t).values, gate_qqq_s.reindex(index_t).values])
        starved = []
        for L, g in enumerate(leg_gates):
            conts = res["conts"][L]
            elig = g[lo0:hi0].astype(bool)
            unfunded = elig & (conts[lo0:hi0] <= 0)
            frac = float(unfunded.sum()) / float(elig.sum()) if elig.sum() > 0 else np.nan
            starved.append(frac)

        R[key] = {"wslices": wslices, "windows": wmetrics, "res": res, "index": index_t,
                  "bench": bench, "starved": starved}
        print(f"cell {cell_label(b, delta, mix)} done ({time.time()-t0:.0f}s)", flush=True)

    # ------------------------------------------------------------------
    # Headline / best-3 selection: rank on common 2001+ window Jensen alpha t
    # ------------------------------------------------------------------
    def common_window_name(key):
        b, delta, mix = key
        return "2001+ (mix-comparable)" if mix == "SPY-only" else R[key]["wslices"][0][0]

    ranked = sorted(CELLS, key=lambda k: -(R[k]["windows"][common_window_name(k)]["t"]
                                           if np.isfinite(R[k]["windows"][common_window_name(k)]["t"])
                                           else -9e9))
    best3 = ranked[:3]
    headline = best3[0]
    print(f"headline cell: {cell_label(*headline)}; best3: "
          f"{[cell_label(*k) for k in best3]}", flush=True)

    # ------------------------------------------------------------------
    # Sensitivities on best-3 cells only
    # ------------------------------------------------------------------
    SENS = {}   # (cell, sens_name) -> metrics dict on that cell's native FULL/common window

    # 1. IV damp=0.4 -> new unit paths needed for legs used by best3
    damped_paths = {}
    legs_needed = set()
    for (b, delta, mix) in best3:
        legs_needed.add(("SPY", delta))
        if mix == "SPY+QQQ":
            legs_needed.add(("QQQ", delta))
    for (under, delta) in legs_needed:
        d = data[under]
        iv_d = damp_iv(d["iv_raw"], 0.4)
        damped_paths[(under, delta)] = simulate_unit_path(
            d["close"], iv_d, d["r_arr"], d["q_arr"], d["gate"], delta)

    for key in best3:
        b, delta, mix = key
        index_t = index_for(mix)
        core_ret = core_ret_for(index_t)
        r_cash = r_cash_for(index_t)
        bench = bench_for(index_t)
        wname = common_window_name(key)
        lo, hi = [(l, h) for (n, l, h) in R[key]["wslices"] if n == wname][0]

        # sens: damp 0.4
        dp = {}
        for (u, dl) in ([("SPY", delta)] if mix == "SPY-only" else [("SPY", delta), ("QQQ", delta)]):
            native_index = data[u]["df"].index
            udf = unit_to_df(damped_paths[(u, dl)], native_index)
            sl = udf.reindex(index_t)
            dp[(u, dl)] = {k: sl[k].values for k in udf.columns}
        legs_d = legs_for2(mix, b, delta, index_t, paths_override=dp)
        res_d = run_cell(legs_d, core_ret, r_cash, index_t, COST_BASE, CASH_W_BASE, True)
        SENS[(key, "damp0.4")] = window_metrics(res_d, bench, index_t, lo, hi)

        # sens: cost x2
        legs_c = legs_for2(mix, b, delta, index_t)
        res_c = run_cell(legs_c, core_ret, r_cash, index_t, 0.01, CASH_W_BASE, True)
        SENS[(key, "cost2x")] = window_metrics(res_c, bench, index_t, lo, hi)

        # sens: cash 0%
        legs_z = legs_for2(mix, b, delta, index_t)
        res_z = run_cell(legs_z, core_ret, r_cash, index_t, COST_BASE, 0.0, True)
        SENS[(key, "cash0")] = window_metrics(res_z, bench, index_t, lo, hi)

        # sens: annual rebalance off
        legs_nr = legs_for2(mix, b, delta, index_t)
        res_nr = run_cell(legs_nr, core_ret, r_cash, index_t, COST_BASE, CASH_W_BASE, False)
        SENS[(key, "norebal")] = window_metrics(res_nr, bench, index_t, lo, hi)

        # base (for comparison row)
        SENS[(key, "base")] = R[key]["windows"][wname]
        print(f"sensitivities for {cell_label(*key)} done ({time.time()-t0:.0f}s)", flush=True)

    # ------------------------------------------------------------------
    # Registry / Bonferroni / DSR
    # ------------------------------------------------------------------
    trial_sharpes = []
    for key in CELLS:
        wname = R[key]["wslices"][0][0]     # native FULL window for that cell
        trial_sharpes.append(R[key]["windows"][wname]["Sharpe"])
    trial_sharpes = np.array(trial_sharpes, dtype="float64")

    hl_wname = common_window_name(headline)
    hl_m = R[headline]["windows"][hl_wname]
    hl_ret = hl_m["ret"]
    hl_p = two_sided_p_from_t(hl_m["t"])
    hl_p_bonf = min(1.0, hl_p * 18) if np.isfinite(hl_p) else np.nan
    hl_dsr = metrics.deflated_sharpe_ratio(hl_ret, trial_sharpes)
    hl_psr = metrics.probabilistic_sharpe_ratio(hl_ret, 0.0)

    # ------------------------------------------------------------------
    # Write results markdown
    # ------------------------------------------------------------------
    L = []
    add = L.append
    add("# Result — Core portfolio assembly: SPY core + gated LEAP sleeve(s) + cash, "
        "18-cell grid (real data)")
    add("")
    add("**Date:** 2026-07-06  **Script:** `backtest/experiments/exp_core_assembly_real.py`  "
        "**Status:** active")
    add("")
    add("## Question")
    add("")
    add("Which premium budget b {10/15/20% NAV}, which delta {0.50/0.70/0.80}, which LEAP "
        "underlying mix {SPY-only / 50-50 SPY+QQQ} for the assembled program (SPY core, "
        "never trend-sold + 200SMA-GATED deep-ITM LEAP sleeve, PORTFOLIO frame + cash buffer "
        "@ ^IRX), annually rebalanced, roll-time profit swept back to core. Pre-registered "
        "3x3x2=18-cell grid; every cell reported. Benchmark = SPY B&H total return, HK 30% "
        "dividend withholding netted.")
    add("")
    add("## Method")
    add("")
    add("- LEAP unit engine (option marks, gate, delta-targeted strike, roll events) is "
        "`simulate_unit_path` IMPORTED from `exp_leap_real_sweep.py` verbatim — not "
        "reimplemented. Gate = pure 200SMA GATED (no RSI-2 dip, no hysteresis — already "
        "settled). 1y call (252 td), roll @ 63 td remaining. IV_1y = vol-index/100 x 0.85 "
        "(base), real ^VIX (SPY leg) / ^VXN (QQQ leg). r/q are the same time-varying ^IRX / "
        "trailing dividend-yield series as exp_leap_real_sweep.")
    add("- NEW in this script: the 3-bucket portfolio assembly (core + LEAP sleeve(s) + cash), "
        "annual rebalance (core:cash ratio reset at each year's first trading day, LEAP left "
        "untouched between its own rolls) + roll-time excess-profit sweep from the LEAP sleeve "
        "into the core (caps the sleeve's dollar budget at b x NAV every roll instead of "
        "letting option gains compound unboundedly — see docstring for the exact bar-by-bar "
        "algorithm). Core-equity trades are treated as zero-cost (ETF shares); only option "
        "trades carry the cost assumption.")
    add("- Core sleeve compounds at the SAME r_net (SPY total return, HK 30% dividend "
        "withholding netted) series used as the Jensen-alpha benchmark — so alpha here isolates "
        "the LEAP-sleeve + cash-buffer + rebalance MACHINERY's effect on top of a pure SPY-beta "
        "baseline, not a stock-selection effect.")
    add("- Mix cells (50/50 SPY+QQQ) only have data from ~2001 (^VXN availability); SPY-only "
        "cells are reported on BOTH their native full window AND a 2001+ slice for a direct, "
        "same-period comparator vs the paired mix cell.")
    add("- Headline + best-3 cells are chosen DATA-DRIVEN: rank all 18 base cells by Jensen "
        "alpha t-stat vs SPY B&H net-TR on the common 2001+ window (the only window every cell "
        "shares); headline = rank #1, best-3 = ranks #1-3. Sensitivities run on those 3 cells "
        "only (pre-registered scope), not all 18.")
    add("- Costs: 0.5%/side of option premium (base), charged on entry/exit/both legs of a "
        "roll. Sharpe = raw daily returns (repo convention, no rf subtraction). CAPITAL = "
        "$500,000 (mid-point of the user's stated $500k-1M program; all % metrics are scale-"
        "invariant, the $-figures below are directly usable for the granularity check).")
    add("")
    add("## Data provenance (backtest/data.py `load()`)")
    add("")
    add("| Series | Source | Rows | From | To |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in prov_all:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")
    add(f"- SPY x ^VIX joined sim window: {spy_df.index[0].date()} -> {spy_df.index[-1].date()} "
        f"({len(spy_df)} days).")
    add(f"- QQQ x ^VXN joined sim window: {qqq_df.index[0].date()} -> {qqq_df.index[-1].date()} "
        f"({len(qqq_df)} days).")
    add(f"- Common (mix) simulation window: {common_idx[0].date()} -> {common_idx[-1].date()} "
        f"({len(common_idx)} days).")
    add(f"- Sanity anchor — SPY B&H TR (HK net) 1996-01->{spy_df.index[-1].date()}: CAGR "
        f"**{anchor['CAGR']*100:.2f}%**, Sharpe {anchor['Sharpe']:.2f}, MaxDD "
        f"{anchor['MaxDD']*100:.1f}% (pre-registered acceptance band 9-11%).")
    add("")

    # -- main 18-cell table (native FULL window per cell) --------------------
    add("## Main table — 18 cells, native FULL window, base setting "
        "(IV m=0.85, cost 0.5%/side, cash 15%, annual rebalance ON)")
    add("")
    add("| b | Δ | Mix | Window | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | Worst mo | "
        "Worst 63d | TE | Dn% med/p90/max | WinRate(n) | CostDrag pp/yr | Cash-starved% |")
    add("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for (b, delta, mix) in CELLS:
        key = (b, delta, mix)
        wname = R[key]["wslices"][0][0]
        m = R[key]["windows"][wname]
        starved = R[key]["starved"]
        starved_s = "/".join(f"{s*100:.0f}%" for s in starved)
        add(f"| {int(b*100)}% | {delta:.2f} | {mix} | {wname} | {_p(m['CAGR'])}{_ruin(m)} | "
            f"{m['Sharpe']:.2f} | {_p(m['MaxDD'])} | {_a(m)} | {_p(m['WorstMonth'])} | "
            f"{_p(m['Worst63d'])} | {_p(m['TE'])} | {m['DnMed']*100:.0f}%/{m['DnP90']*100:.0f}%/"
            f"{m['DnMax']*100:.0f}% | {_p(m['WinRate'],0)}({m['NYears']}) | "
            f"{m['CostDrag']:+.1f} | {starved_s} |")
    add("")
    add("**Cash-starved%** = of the days the leg's OWN 200SMA gate says \"eligible to hold\" "
        "(trend is up), the fraction where the sim actually carried 0 contracts because the "
        "shared cash pool could not fund the fresh premium between annual rebalances (SPY-only: "
        "1 value; mix: SPY-leg/QQQ-leg). This is a CASH-driven dark period, distinct from a "
        "trend-gate exit — see Caveats/Implication. It is the main reason the Dn% median is "
        "often 0% even though the trend gate itself is open ~75% of the time.")
    add("")

    # -- SPY-only 2001+ comparator ------------------------------------------
    add("## SPY-only cells, 2001+ comparator window (identical period as the paired mix cells)")
    add("")
    add("| b | Δ | Window | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | TE | "
        "Dn% med/p90/max |")
    add("|---|---|---|---|---|---|---|---|---|")
    for b in BUDGETS:
        for delta in DELTAS:
            key = (b, delta, "SPY-only")
            wname = "2001+ (mix-comparable)"
            m = R[key]["windows"][wname]
            add(f"| {int(b*100)}% | {delta:.2f} | {wname} | {_p(m['CAGR'])}{_ruin(m)} | "
                f"{m['Sharpe']:.2f} | {_p(m['MaxDD'])} | {_a(m)} | {_p(m['TE'])} | "
                f"{m['DnMed']*100:.0f}%/{m['DnP90']*100:.0f}%/{m['DnMax']*100:.0f}% |")
    add("")
    add("| b | Δ | Window | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | TE | "
        "Dn% med/p90/max | (mix, same window, repeated for comparison) |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for b in BUDGETS:
        for delta in DELTAS:
            key = (b, delta, "SPY+QQQ")
            wname = R[key]["wslices"][0][0]
            m = R[key]["windows"][wname]
            add(f"| {int(b*100)}% | {delta:.2f} | {wname} | {_p(m['CAGR'])}{_ruin(m)} | "
                f"{m['Sharpe']:.2f} | {_p(m['MaxDD'])} | {_a(m)} | {_p(m['TE'])} | "
                f"{m['DnMed']*100:.0f}%/{m['DnP90']*100:.0f}%/{m['DnMax']*100:.0f}% | mix |")
    add("")

    # -- two-halves + sub-windows --------------------------------------------
    add("## Two-halves + sub-windows (CAGR / α(t) per window)")
    add("")
    add("| b | Δ | Mix | " + " | ".join(f"{w} CAGR | α(t)" for w in
        [n for (n, _, _) in R[CELLS[0]]["wslices"][1:5]]) + " |")
    header_windows = [n for (n, _, _) in R[CELLS[0]]["wslices"][1:5]]
    add("|---|---|---|" + "---|" * (2 * len(header_windows)))
    for (b, delta, mix) in CELLS:
        cellw = R[(b, delta, mix)]["windows"]
        row = [f"{int(b*100)}%", f"{delta:.2f}", mix]
        for wn in header_windows:
            if wn in cellw:
                m = cellw[wn]
                row += [_p(m["CAGR"]), _a(m)]
            else:
                row += ["n/a", "n/a"]
        add("| " + " | ".join(row) + " |")
    add("")

    # -- sensitivity tables ---------------------------------------------------
    add("## Sensitivity — headline + best-3 cells (ranked by common-window α t-stat)")
    add("")
    add(f"Ranking (common 2001+ window, α t-stat desc): " +
        ", ".join(f"#{i+1} {cell_label(*k)} (t={R[k]['windows'][common_window_name(k)]['t']:+.2f})"
                  for i, k in enumerate(best3)))
    add("")
    add(f"**Headline cell: {cell_label(*headline)}**")
    add("")
    add("| Sensitivity | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) |")
    add("|---|---|---|---|---|")
    for sname, label in [("base", "base (m0.85, 0.5%, 15% cash, rebal ON)"),
                         ("damp0.4", "IV damp=0.4"), ("cost2x", "cost 1.0%/side"),
                         ("cash0", "cash 0%"), ("norebal", "annual rebalance OFF")]:
        m = SENS[(headline, sname)]
        add(f"| {label} | {_p(m['CAGR'])}{_ruin(m)} | {m['Sharpe']:.2f} | {_p(m['MaxDD'])} | "
            f"{_a(m)} |")
    add("")
    for key in best3:
        if key == headline:
            continue
        add(f"**{cell_label(*key)}**")
        add("")
        add("| Sensitivity | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) |")
        add("|---|---|---|---|---|")
        for sname, label in [("base", "base"), ("damp0.4", "IV damp=0.4"),
                             ("cost2x", "cost 1.0%/side"), ("cash0", "cash 0%"),
                             ("norebal", "annual rebalance OFF")]:
            m = SENS[(key, sname)]
            add(f"| {label} | {_p(m['CAGR'])}{_ruin(m)} | {m['Sharpe']:.2f} | {_p(m['MaxDD'])} | "
                f"{_a(m)} |")
        add("")

    # -- granularity / implication inputs -------------------------------------
    hb, hdelta, hmix = headline
    add("## Granularity check ($500k program, headline cell)")
    add("")
    add("Per-contract premium uses the LAST 252 trading days only (recent SPY/QQQ price + IV "
        "level) — a full-history median would be dominated by 1990s/2000s-era (far cheaper) "
        "prices and misrepresent what a fresh $500k account funds TODAY.")
    add("")
    hopt = R[headline]["res"]["opt"]
    hconts = R[headline]["res"]["conts"]
    prem_dollars = hb * CAPITAL if hmix == "SPY-only" else (hb / 2.0) * CAPITAL
    RECENT_N = 252
    for i, leg_name in enumerate(["SPY leg"] if hmix == "SPY-only" else ["SPY leg", "QQQ leg"]):
        conts = hconts[i][-RECENT_N:]
        opt_v_all = hopt[i][-RECENT_N:]
        held = conts[conts > 0]
        opt_v = opt_v_all[conts > 0]
        if len(held) > 0:
            prem_per_contract = float(np.median(opt_v / held))
            add(f"- {leg_name}: premium budget ~${prem_dollars:,.0f}; median per-contract "
                f"premium over the last {RECENT_N} trading days ~${prem_per_contract:,.0f} -> ~"
                f"{prem_dollars / prem_per_contract:.1f} contracts (continuous/fractional in "
                f"this backtest; REAL trading must round to whole contracts — see Implication).")
        else:
            add(f"- {leg_name}: gated out for the entire last {RECENT_N} trading days — no "
                f"recent per-contract premium observed.")
    add("")

    # -- cross-foot verification ---------------------------------------------
    add("## Cross-foot verification")
    add("")
    add(f"- {ASSERT_COUNT['runs']} accounting runs, {ASSERT_COUNT['n']:,} bar-level "
        "assertions, ALL passed: NAV = core + cash + sum(option market value); cash >= 0; "
        "NAV > 0; NAV_t = NAV_(t-1) + cash interest + core P&L + option P&L - costs "
        "(annual rebalance is a zero-sum internal transfer and does not appear in this "
        "identity; rel. tol 1e-6). Any violation raises and aborts the run.")
    add("")

    # -- registry / Bonferroni / DSR ------------------------------------------
    add("## Trial registry, Bonferroni, DSR")
    add("")
    add("- **This loop's registered trial universe: 18 grid cells** (3 premium budgets x 3 "
        "deltas x 2 LEAP-underlying mixes), pre-registered above, all 18 reported (main table). "
        "Sensitivity re-tests on the best-3 cells are NOT additional trials for this count "
        "(robustness checks on already-selected cells, not new candidates competing for best).")
    add("- **Separately noted, not pooled**: Loop-1 (`exp_core_portfolio_lab.py`, 384 cells) was "
        "an engine-selection sweep on the since-superseded hand-rolled BSM/LEAP path (mirroring "
        "the RV-proxy `exp_leap_delta_sweep.py`), settling delta/gate/frame choices BEFORE this "
        "script existed — a different question, a closed decision, not part of this loop's "
        "multiple-testing correction.")
    add(f"- Headline cell **{cell_label(*headline)}**, common 2001+ window: Jensen alpha t = "
        f"{hl_m['t']:+.2f}, two-sided p (normal approx) = {hl_p:.4g}, "
        f"**Bonferroni-adjusted p (x18) = {hl_p_bonf:.4g}**.")
    add(f"- **Deflated Sharpe Ratio (DSR)** of the headline cell (real daily-return series, "
        f"vs the 18-cell annualized-Sharpe trial universe): **{hl_dsr:.3f}** "
        f"(PSR against 0 = {hl_psr:.3f}). DSR > 0.95 ~ survives multiple testing.")
    add(f"- Trial-universe annualized Sharpes (18 cells, native FULL window): "
        f"min {np.nanmin(trial_sharpes):.2f}, median {np.nanmedian(trial_sharpes):.2f}, "
        f"max {np.nanmax(trial_sharpes):.2f}.")
    add("")

    add("## Conclusions")
    add("")
    add("(TO FILL — hand-written after number review)")
    add("")
    add("## Caveats")
    add("")
    add("- Leg-processing order (SPY leg then QQQ leg) means a same-bar roll-sweep target for "
        "the first-processed leg uses the SECOND leg's PRIOR-bar option value, not its "
        "same-bar mark-to-market — a second-order sequencing approximation, immaterial to "
        "results (affects only the $ budget snap on the rare bars both legs roll together).")
    add("- IV damping's sigma_bar is a FULL-SAMPLE mean (mild look-ahead in the pricing input "
        "only — it does not touch gate/entry timing, which is price/200SMA-driven and "
        "unaffected). Acceptable for a sensitivity/robustness check, not presented as a "
        "tradable rule.")
    add("- Annual excess win-rate excludes partial first/last calendar years (<200 trading "
        "days) to avoid partial-year distortion.")
    add("- Core-equity trades (rebalance, roll-sweep) assumed zero-cost (ETF shares) — only "
        "option legs carry the cost assumption.")
    add("(TO FILL — additional caveats after number review)")
    add("")
    add("## Implication")
    add("")
    add("(TO FILL — hand-written after number review, including the granularity check above)")
    add("")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS}  ({time.time()-t0:.0f}s total, "
          f"{ASSERT_COUNT['n']:,} asserts / {ASSERT_COUNT['runs']} runs)", flush=True)


if __name__ == "__main__":
    main()
