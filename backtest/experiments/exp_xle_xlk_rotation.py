"""XLE-XLK rotation capture test -- can the ONE genuine residual seesaw pair be traded?

Context: `exp_gics_residual_matrix.py` (2026-07-16) found XLE-XLK is the only pair (besides
the XLK-weight axis itself) whose full-period residual correlation (-0.376) clears its
OWN pair-specific mechanical baseline (p05 -0.171) by a real margin (+0.205), i.e. the
"seesaw exists" claim is established. This script does NOT re-test existence -- it asks
the separate, harder question: does a monthly-rebalanced, honestly-costed trading rule
actually CAPTURE that seesaw as tradable PnL, or does it just exist as a correlation fact
that decays/whipsaws away once you try to harvest it?

Karst's PRIMARY metric is CAPITAL EFFICIENCY (PnL / average deployed exposure), not CAGR
or Jensen alpha (repo instruction) -- a strategy that gets 70% of buy-and-hold's PnL on
50% of buy-and-hold's exposure is a WIN because the freed capital can be redeployed
elsewhere. All comparison tables report capital efficiency FIRST, CAGR/MaxDD after.

Universe: XLE, XLK. Both SPDR sectors inception 1998-12-16 -> full 1999+ sample is
available (robustness check) alongside the primary 2016+ window (repo standard start,
matches the residual-matrix study's window).

5 pre-registered variants (multiple-comparison count = 5, reported explicitly per repo
"backtest-testing-standard" / statistical honesty rule):
  1. Relative-momentum SWITCH  (63d and 126d lookback sub-variants): winner-take-all
     (100/0) by trailing total-return gap XLE-XLK.
  2. Relative-momentum TILT    (63d and 126d): 70/30 winner/loser (softer version of #1).
  3. Residual z-score REVERSAL: rolling-252d-beta residual vs SPY, cumulative 63d, spread
     z-scored on its own trailing 252d distribution; |z|>1.5 -> bet on reversion (buy the
     laggard 100%), else neutral 50/50 (no signal read as "no edge", not "no position" --
     this variant is always fully invested, unlike #4).
  4. CONDITIONAL EXPOSURE (capital-efficiency headline variant): only take variant #1's
     63d winner-take-all position when the signal is "clear" (|63d momentum gap| > a
     PRE-REGISTERED 5pp threshold, with 3pp/8pp reported as a sensitivity check, NOT
     re-optimized against the outcome); otherwise sit in CASH (0% return, conservative --
     no T-bill credit given, biases AGAINST this variant).
  5. Benchmarks: SPY 100% B&H; 50/50 XLE+XLK monthly-rebalanced B&H (both cost-honest).

Costs: 10bp per side (0.001), applied to every entry/exit/rebalance notional (per-user
instruction -- NOT the repo-default 5bp used in `exp_sector_capeff.py`). Execution: month-
end close signal -> hold the resulting weights unrebalanced through the following month
(single decision per month; standard month-end-signal / next-month-hold convention).

Metrics (capital efficiency FIRST): PnL / average deployed exposure (CAGR / mean fraction
invested, "return on capital deployed"), conditional Sharpe (invested days only), CAGR,
MaxDD, monthly turnover, cumulative cost drag, 2016-2020 vs 2021+ sub-period stability.

    PYTHONUTF8=1 python backtest/experiments/exp_xle_xlk_rotation.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load  # noqa: E402
from metrics import ann_sharpe, cagr, max_drawdown  # noqa: E402

TD = 252
COST = 0.001  # 10bp/side per user instruction (not repo-default 5bp)

WINDOWS = [
    ("2016+ (primary)", "2016-01-01", "2026-12-31"),
    ("1999+ (long-sample robustness)", "1999-01-01", "2026-12-31"),
    ("2016-2020", "2016-01-01", "2020-12-31"),
    ("2021+", "2021-01-01", "2026-12-31"),
]


# ============================================================================
# 1. Data
# ============================================================================

def load_all():
    xle = load("XLE", adjusted=True)["close"]
    xlk = load("XLK", adjusted=True)["close"]
    spy = load("SPY", adjusted=True)["close"]
    idx = spy.index
    df = pd.DataFrame({
        "XLE": xle.reindex(idx),
        "XLK": xlk.reindex(idx),
        "SPY": spy.reindex(idx),
    }, index=idx).dropna()
    return df


def month_end_flags(idx: pd.DatetimeIndex) -> np.ndarray:
    months = idx.to_period("M")
    return np.asarray((months.values[:-1] != months.values[1:]).tolist() + [True])


# ============================================================================
# 2. Signal construction
# ============================================================================

def build_signals(df: pd.DataFrame):
    ret = df.pct_change()
    ret_xle, ret_xlk, ret_spy = ret["XLE"], ret["XLK"], ret["SPY"]

    # trailing total-return momentum gap (XLE - XLK), two lookbacks
    tr_xle_63 = df["XLE"].pct_change(63)
    tr_xlk_63 = df["XLK"].pct_change(63)
    mom_gap_63 = tr_xle_63 - tr_xlk_63
    tr_xle_126 = df["XLE"].pct_change(126)
    tr_xlk_126 = df["XLK"].pct_change(126)
    mom_gap_126 = tr_xle_126 - tr_xlk_126

    # rolling-252d beta residual vs SPY (same method as exp_gics_residual_matrix.py)
    roll_cov_xle = ret_xle.rolling(252).cov(ret_spy)
    roll_var_spy = ret_spy.rolling(252).var()
    beta_xle = roll_cov_xle / roll_var_spy
    resid_xle = ret_xle - beta_xle * ret_spy

    roll_cov_xlk = ret_xlk.rolling(252).cov(ret_spy)
    beta_xlk = roll_cov_xlk / roll_var_spy
    resid_xlk = ret_xlk - beta_xlk * ret_spy

    cum_resid_xle_63 = resid_xle.rolling(63).sum()
    cum_resid_xlk_63 = resid_xlk.rolling(63).sum()
    resid_spread = cum_resid_xle_63 - cum_resid_xlk_63
    z_spread = (resid_spread - resid_spread.rolling(252).mean()) / resid_spread.rolling(252).std()

    return dict(mom_gap_63=mom_gap_63, mom_gap_126=mom_gap_126, z_spread=z_spread)


# ============================================================================
# 3. Weight schedules (one weight decision per month-end, held through next month)
# ============================================================================

def weights_switch(mom_gap: pd.Series, me_flags: np.ndarray) -> pd.DataFrame:
    """Strategy 1: winner-take-all (100/0) by momentum gap sign."""
    w_xle = np.full(len(mom_gap), np.nan)
    w_xlk = np.full(len(mom_gap), np.nan)
    gap = mom_gap.values
    cur_xle, cur_xlk = 0.5, 0.5  # neutral until first valid signal
    for i in range(len(gap)):
        if me_flags[i] and not np.isnan(gap[i]):
            cur_xle, cur_xlk = (1.0, 0.0) if gap[i] > 0 else (0.0, 1.0)
        w_xle[i], w_xlk[i] = cur_xle, cur_xlk
    return pd.DataFrame({"XLE": w_xle, "XLK": w_xlk}, index=mom_gap.index)


def weights_tilt(mom_gap: pd.Series, me_flags: np.ndarray, winner=0.70) -> pd.DataFrame:
    """Strategy 2: 70/30 tilt toward momentum winner."""
    w_xle = np.full(len(mom_gap), np.nan)
    w_xlk = np.full(len(mom_gap), np.nan)
    gap = mom_gap.values
    cur_xle, cur_xlk = 0.5, 0.5
    loser = 1 - winner
    for i in range(len(gap)):
        if me_flags[i] and not np.isnan(gap[i]):
            cur_xle, cur_xlk = (winner, loser) if gap[i] > 0 else (loser, winner)
        w_xle[i], w_xlk[i] = cur_xle, cur_xlk
    return pd.DataFrame({"XLE": w_xle, "XLK": w_xlk}, index=mom_gap.index)


def weights_zreversal(z: pd.Series, me_flags: np.ndarray, thresh=1.5) -> pd.DataFrame:
    """Strategy 3: |z|>thresh -> buy the residual LAGGARD 100% (reversion bet);
    else neutral 50/50 (always fully invested)."""
    w_xle = np.full(len(z), np.nan)
    w_xlk = np.full(len(z), np.nan)
    zv = z.values
    cur_xle, cur_xlk = 0.5, 0.5
    for i in range(len(zv)):
        if me_flags[i] and not np.isnan(zv[i]):
            if zv[i] > thresh:
                cur_xle, cur_xlk = 0.0, 1.0   # XLE overperformed residually -> buy XLK
            elif zv[i] < -thresh:
                cur_xle, cur_xlk = 1.0, 0.0   # XLK overperformed residually -> buy XLE
            else:
                cur_xle, cur_xlk = 0.5, 0.5
        w_xle[i], w_xlk[i] = cur_xle, cur_xlk
    return pd.DataFrame({"XLE": w_xle, "XLK": w_xlk}, index=z.index)


def weights_conditional(mom_gap: pd.Series, me_flags: np.ndarray, gap_thresh=0.05) -> pd.DataFrame:
    """Strategy 4: winner-take-all ONLY when |mom_gap| > gap_thresh, else CASH (0/0)."""
    w_xle = np.full(len(mom_gap), np.nan)
    w_xlk = np.full(len(mom_gap), np.nan)
    gap = mom_gap.values
    cur_xle, cur_xlk = 0.0, 0.0  # start in cash until first clear signal
    for i in range(len(gap)):
        if me_flags[i] and not np.isnan(gap[i]):
            if abs(gap[i]) > gap_thresh:
                cur_xle, cur_xlk = (1.0, 0.0) if gap[i] > 0 else (0.0, 1.0)
            else:
                cur_xle, cur_xlk = 0.0, 0.0
        w_xle[i], w_xlk[i] = cur_xle, cur_xlk
    return pd.DataFrame({"XLE": w_xle, "XLK": w_xlk}, index=mom_gap.index)


def weights_5050_rebal(idx: pd.DatetimeIndex, me_flags: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({"XLE": np.full(len(idx), 0.5), "XLK": np.full(len(idx), 0.5)}, index=idx)


# ============================================================================
# 4. Simulation: weights -> daily NAV, with 10bp/side rebalance cost
# ============================================================================

def simulate(df: pd.DataFrame, weights: pd.DataFrame, first_valid_i: int):
    idx = df.index
    n = len(idx)
    ret_xle = df["XLE"].pct_change().values
    ret_xlk = df["XLK"].pct_change().values
    w_xle = weights["XLE"].values
    w_xlk = weights["XLK"].values

    nav = np.full(n, np.nan)
    exposure = np.full(n, np.nan)
    turnover_cost = np.zeros(n)
    nav[first_valid_i] = 1.0
    exposure[first_valid_i] = w_xle[first_valid_i] + w_xlk[first_valid_i]
    prev_w_xle, prev_w_xlk = w_xle[first_valid_i], w_xlk[first_valid_i]

    for i in range(first_valid_i + 1, n):
        day_ret = prev_w_xle * ret_xle[i] + prev_w_xlk * ret_xlk[i]
        step_nav = nav[i - 1] * (1 + day_ret)
        # rebalance cost charged when the PRIOR day's decided weight changes vs the day before
        turn = abs(w_xle[i] - prev_w_xle) + abs(w_xlk[i] - prev_w_xlk)
        if turn > 1e-9:
            step_nav *= (1 - turn * COST)
            turnover_cost[i] = turn * COST
        nav[i] = step_nav
        exposure[i] = w_xle[i] + w_xlk[i]
        prev_w_xle, prev_w_xlk = w_xle[i], w_xlk[i]

    daily_ret = np.full(n, np.nan)
    daily_ret[first_valid_i + 1:] = nav[first_valid_i + 1:] / nav[first_valid_i:-1] - 1.0
    return nav, daily_ret, exposure, turnover_cost


def simulate_spy(df: pd.DataFrame, first_valid_i: int):
    idx = df.index
    n = len(idx)
    spy = df["SPY"].values
    nav = np.full(n, np.nan)
    nav[first_valid_i] = 1.0 * (1 - COST)
    for i in range(first_valid_i + 1, n):
        nav[i] = nav[i - 1] * (spy[i] / spy[i - 1])
    daily_ret = np.full(n, np.nan)
    daily_ret[first_valid_i + 1:] = nav[first_valid_i + 1:] / nav[first_valid_i:-1] - 1.0
    return nav, daily_ret


# ============================================================================
# 5. Metrics
# ============================================================================

def window_mask(idx, ws, we):
    return np.asarray((idx >= ws) & (idx <= we))


def rebase(nav_slice):
    nav_slice = np.asarray(nav_slice, float)
    valid = ~np.isnan(nav_slice)
    if not valid.any():
        return nav_slice
    first = nav_slice[valid][0]
    return nav_slice / first if first != 0 else nav_slice


def cond_sharpe(daily_ret, exposure):
    mask = (exposure > 1e-9) & ~np.isnan(daily_ret)
    r = daily_ret[mask]
    if len(r) < 10 or r.std(ddof=1) == 0:
        return np.nan
    return np.sqrt(TD) * r.mean() / r.std(ddof=1)


def capital_efficiency(nav_slice, exposure_slice):
    """CAGR / mean deployed exposure -- 'return on capital deployed'. Undefined (NaN) if
    avg exposure ~0 (never invested)."""
    c = cagr(rebase(nav_slice))
    avg_exp = np.nanmean(exposure_slice)
    if avg_exp is None or np.isnan(avg_exp) or avg_exp < 1e-6:
        return np.nan, avg_exp
    return c / avg_exp, avg_exp


def monthly_turnover(weights: pd.DataFrame, me_flags: np.ndarray, mask: np.ndarray):
    w = weights[["XLE", "XLK"]].values
    idxs = np.where(me_flags & mask)[0]
    if len(idxs) < 2:
        return np.nan
    turns = []
    for a, b in zip(idxs[:-1], idxs[1:]):
        turns.append(abs(w[b, 0] - w[a, 0]) + abs(w[b, 1] - w[a, 1]))
    return float(np.mean(turns))


def report_row(label, nav, daily_ret, exposure, idx, ws, we, cost_series=None):
    mask = window_mask(idx, ws, we) & ~np.isnan(nav)  # exclude pre-warm-up NaN NAV rows
    if mask.sum() < 30:
        return f"  [{ws[:4]}+] {label:34}  n<30, skip"
    nav_w = rebase(nav[mask])
    ceff, avg_exp = capital_efficiency(nav[mask], exposure[mask])
    csh = cond_sharpe(daily_ret[mask], exposure[mask])
    mdd = max_drawdown(nav_w)
    c = cagr(nav_w)
    if cost_series is not None:
        cost_drag_s = f"{float(np.nansum(cost_series[mask]))*100:5.2f}pp-cum"
    else:
        cost_drag_s = " n/a (one-off entry cost only)"
    return (f"  {label:34} avgExp={avg_exp*100:5.1f}%  CapEff(PnL/Exp)={ceff*100:+7.2f}%/yr  "
            f"CondSharpe={csh:5.2f}  CAGR={c*100:+7.2f}%  MaxDD={mdd*100:7.1f}%  "
            f"CostDrag={cost_drag_s}")


# ============================================================================
# 6. Main
# ============================================================================

def main():
    print("Loading XLE / XLK / SPY (total-return, yfinance)...")
    df = load_all()
    idx = df.index
    print(f"Master calendar (post-dropna, all 3 series overlap): "
          f"{idx.min().date()} -> {idx.max().date()}, {len(df)} rows")
    me_flags = month_end_flags(idx)
    sig = build_signals(df)

    first_valid_i = int(np.argmax(~sig["mom_gap_126"].isna().values & ~sig["z_spread"].isna().values))
    print(f"First fully-warmed-up signal date (126d mom + 252d beta + 63d cum-resid + 252d z): "
          f"{idx[first_valid_i].date()}")

    strategies = {}

    strategies["1a. Switch 100/0 (63d mom)"] = weights_switch(sig["mom_gap_63"], me_flags)
    strategies["1b. Switch 100/0 (126d mom)"] = weights_switch(sig["mom_gap_126"], me_flags)
    strategies["2a. Tilt 70/30 (63d mom)"] = weights_tilt(sig["mom_gap_63"], me_flags)
    strategies["2b. Tilt 70/30 (126d mom)"] = weights_tilt(sig["mom_gap_126"], me_flags)
    strategies["3. Resid z-reversal (|z|>1.5)"] = weights_zreversal(sig["z_spread"], me_flags)
    strategies["4. Conditional (63d gap>5pp else cash)"] = weights_conditional(sig["mom_gap_63"], me_flags, 0.05)
    strategies["4s. Conditional sens. gap>3pp"] = weights_conditional(sig["mom_gap_63"], me_flags, 0.03)
    strategies["4s. Conditional sens. gap>8pp"] = weights_conditional(sig["mom_gap_63"], me_flags, 0.08)
    strategies["5. 50/50 XLE+XLK monthly-rebal"] = weights_5050_rebal(idx, me_flags)

    sim_results = {}
    for name, w in strategies.items():
        nav, dret, exp_, cost_ = simulate(df, w, first_valid_i)
        sim_results[name] = (nav, dret, exp_, cost_)

    spy_nav, spy_dret = simulate_spy(df, first_valid_i)
    spy_exp = np.where(np.isnan(spy_nav), np.nan, 1.0)

    lines = []
    lines.append("=" * 110)
    lines.append("XLE-XLK ROTATION CAPTURE TEST -- capital efficiency FIRST, CAGR/MaxDD after")
    lines.append("5 pre-registered variant FAMILIES (9 configs incl. sub-variants + 3 sensitivity "
                  "reruns of #4) x up to 4 windows -- multiple-comparison count disclosed here.")
    lines.append("=" * 110)

    for wname, ws, we in WINDOWS:
        lines.append(f"\n--- Window: {wname} ({ws} -> {we}) ---")
        lines.append(report_row("SPY 100% B&H (benchmark)", spy_nav, spy_dret, spy_exp, idx, ws, we))
        for name, (nav, dret, exp_, cost_) in sim_results.items():
            lines.append(report_row(name, nav, dret, exp_, idx, ws, we, cost_series=cost_))
        # monthly turnover for the 4 primary (non-sensitivity) strategies in this window
        mask = window_mask(idx, ws, we)
        lines.append("  -- monthly turnover (mean |Δweight| per rebalance) --")
        for name, w in strategies.items():
            if "sens." in name:
                continue
            t = monthly_turnover(w, me_flags, mask)
            lines.append(f"    {name:34} turnover={t*100:5.1f}pp/rebalance" if not np.isnan(t)
                          else f"    {name:34} turnover=n/a")

    lines.append("\n" + "=" * 110)
    lines.append("INCREMENT SIGNIFICANCE (paired daily-return t-test, strategy minus benchmark) "
                 "-- descriptive tables above are NOT hypothesis tests by themselves")
    lines.append("=" * 110)
    bench_series = {"vs SPY": spy_dret, "vs 50/50 XLE+XLK": sim_results["5. 50/50 XLE+XLK monthly-rebal"][1]}
    headline = ["1a. Switch 100/0 (63d mom)", "1b. Switch 100/0 (126d mom)",
                "2a. Tilt 70/30 (63d mom)", "3. Resid z-reversal (|z|>1.5)",
                "4. Conditional (63d gap>5pp else cash)"]
    for wname, ws, we in WINDOWS:
        lines.append(f"\n--- {wname} ---")
        mask = window_mask(idx, ws, we)
        for name in headline:
            dret = sim_results[name][1]
            for bname, bser in bench_series.items():
                m = mask & ~np.isnan(dret) & ~np.isnan(bser)
                if m.sum() < 30:
                    continue
                diff = dret[m] - bser[m]
                if diff.std(ddof=1) == 0:
                    continue
                t_stat, p_val = stats.ttest_1samp(diff, 0.0)
                ann_diff = diff.mean() * TD * 100
                sig = "*" if p_val < 0.05 else " "
                lines.append(f"  {name:34} {bname:18} ann.diff={ann_diff:+6.2f}pp/yr  "
                              f"t={t_stat:+5.2f} p={p_val:.3f}{sig} n={int(m.sum())}")

    lines.append(f"\nMultiple-comparison disclosure: 5 strategy FAMILIES pre-registered in the brief "
                 f"(switch / tilt / z-reversal / conditional / benchmarks); 9 total configs simulated "
                 f"(2 lookbacks x 2 for switch+tilt, 1 z-reversal, 1 conditional headline + 2 sensitivity "
                 f"reruns, 1 50/50 benchmark) x {len(WINDOWS)} windows = up to {9*len(WINDOWS)} reported cells. "
                 f"No post-hoc threshold tuning: the 5pp conditional-exposure gate and 1.5 z-threshold were "
                 f"fixed BEFORE running, sensitivity reruns (3pp/8pp) are reported alongside, not substituted in.")

    print("\n".join(lines))
    print("\n" + "=" * 110)
    print("DONE. Module: backtest/experiments/exp_xle_xlk_rotation.py")
    print("=" * 110)


if __name__ == "__main__":
    main()
