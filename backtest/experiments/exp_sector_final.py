"""按 ASSUMPTIONS.md(2026-07-17 版)

Sector rotation FINAL SETTLEMENT test -- three independent, pre-registered questions run
once, to either close the sector-rotation book or open a narrow forward path. This is NOT
a re-test of anything already SETTLED: `backtest/SETTLED.md` #24/#25 already closed "does
mechanical/price-momentum sector rotation capture alpha" (no, across 11+ variants) and
`2026-07-17_xle_xlk_rotation.md` already closed "can the ONE genuine residual pair be
traded" (direction right, p>0.10 everywhere, CapEff-ratio trap demonstrated). Do not repeat
those tests here -- this script only touches NEW ground: (A) an arithmetic decomposition of
why the oracle looks so good, (B) three drivers that are NOT the sector's own price
(closing off the "just rediscovered price momentum" critique), (C) one dimensionality-
reduced binary axis (tech vs "everything else", the one axis the residual matrix flagged as
real) instead of an 11-way rotation.

Cites, per ASSUMPTIONS.md (2026-07-17 version):
  A1 - always invested; benchmark = 100% spot, never cash. Every Part B/C leg here is
       ALWAYS 100% in one of two assets (never cash) -- honours A1's spirit even though A1
       itself is written for the core LEAP/spot decision, not sector rotation.
  A3 - capital efficiency (PnL / exposure) + absolute PnL reported side by side; alpha only
       at the whole-portfolio layer. NOTE: because every Part B/C leg is ALWAYS 100%
       invested (binary switch, no cash state), CapEff = CAGR / 1.0 = CAGR EXACTLY here --
       there is no "thin-denominator inflates the ratio" trap (the ASSUMPTIONS A3 warning,
       and the trap `2026-07-17_xle_xlk_rotation.md` #4 fell into) because the denominator
       is always 1.0 by construction. Disclosed ONCE here, not re-derived per table.
  A4 - 2016+ primary window, split front/back half (H1 2016-2020 / H2 2021+); long-sample
       sensitivity reported ALONGSIDE, never substituted in for the primary windows.
  A6 - weekly/monthly cadence only. No day trading, no 0DTE.
  A7 - ETF-only vehicles.

Report numbers ONLY -- no verdicts. Verdict slots are explicitly left as "pending review"
(待覆核點) per instruction; SETTLED.md is NOT touched by this script or its output file.

Part A (arithmetic demonstration, NOT a hypothesis test): decompose the 11-GICS-sector
monthly perfect-foresight oracle into (1) its CAGR vs SPY, (2) the monthly best-vs-median
dispersion that IS the oracle's entire source, (3) a capture-rate grid (0/5/10/20/100%)
showing what fraction of that dispersion a real signal would need to capture to matter,
plus a reverse-engineered implied capture rate for the best already-tested signal
(XLE-XLK 63d momentum switch, exact `exp_xle_xlk_rotation.py` rule) -- re-evaluated here
ONLY for its win-rate statistic, not re-litigating its already-settled p-value (p>0.10
stands, see SETTLED #24 and the source file). This script's own generic 2-leg engine is
cross-validated against that settled XLE-XLK CapEff number before being trusted for the
new Part B/C pairs (see `sanity_check_xle_xlk` in main()).

Part B (hypothesis test, mechanism-first): three PRE-REGISTERED external-driver pairs
(oil trend -> XLE, rate trend -> XLF, rate trend -> XLU inverse) -- the driver is NEVER the
sector's own price, closing off the critique that killed the pure price-momentum rotation
variants in SETTLED #24. Dual control required per pair (missing either voids the pair):
  (a) 1000-draw Monte Carlo, SAME number of monthly switches + SAME (100%) exposure as the
      real signal within that window, random initial state and random switch timing;
  (b) static 50/50 buy-and-hold of the pair (daily-blended, zero cost -- same convention as
      `exp_xle_xlk_rotation.py`'s strategy 5).
Bonferroni-disclosed: 3 pairs x 2 windows (H1/H2) = 6 primary tests, alpha_adj =
0.05/6 = 0.00833; 2001+ is a sensitivity row, NOT part of the corrected family.

Part C (hypothesis test, dimensionality-reduced rotation): QQQ-vs-RSP binary monthly
decision using a composite signal: 63d relative momentum AND the slope of the QQQ/RSP
ratio's 200d SMA (the latter EXPLICITLY a PRICE proxy for "relative earnings-revision",
NOT real analyst-estimate data -- disclosed, not hidden) -- both legs must agree in
direction to flip; otherwise the PRIOR month's holding is maintained (sticky rule). Same
dual control as Part B. Family: 1 axis x 2 windows = 2 tests, alpha_adj = 0.05/2 = 0.025;
combined report-wide family (Part B + C) = 8 tests, alpha_adj = 0.05/8 = 0.00625
(disclosed for both framings, not cherry-picked).

Costs: 10bp/side (0.001), per user instruction for Part B, extended to Part C by
convention (same as this repo's other rotation tests). Windowing convention: each window's
NAV is rebased to 1.0 at the window's first reporting day; per convention that first day's
own return is dropped (treated as 0) to keep the slicing logic simple and identical between
the real strategy and every MC draw -- immaterial over a multi-year window, and applied
IDENTICALLY to both real and MC paths (not a biasing asymmetry).

    PYTHONUTF8=1 python backtest/experiments/exp_sector_final.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load  # noqa: E402
from metrics import cagr, max_drawdown  # noqa: E402

TD = 252
COST = 0.001            # 10bp/side (Part B instruction, extended to Part C by convention)
SEED = 20260718
N_SIMS = 1000
END_CAP = "2026-12-31"  # open-ended forward cap, matches exp_xle_xlk_rotation.py convention

GICS11 = ["XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]

WINDOWS_BC = [
    ("H1 2016-2020", "2016-01-01", "2020-12-31"),
    ("H2 2021+", "2021-01-01", END_CAP),
]
SENS_B = ("SENS 2001+", "2001-01-01", END_CAP)
SENS_C = ("SENS 2004+", "2004-01-01", END_CAP)      # RSP inception 2003-05 + warm-up buffer

CAPTURE_RATES_HEADLINE = [0.0, 0.05, 0.10, 0.20, 1.0]


# ============================================================================
# Shared helpers
# ============================================================================

def month_end_flags(idx: pd.DatetimeIndex) -> np.ndarray:
    months = idx.to_period("M")
    return np.asarray((months.values[:-1] != months.values[1:]).tolist() + [True])


def window_mask(idx, ws, we):
    return np.asarray((idx >= ws) & (idx <= we))


def rebase(nav_slice):
    nav_slice = np.asarray(nav_slice, float)
    valid = ~np.isnan(nav_slice)
    if not valid.any():
        return nav_slice
    first = nav_slice[valid][0]
    return nav_slice / first if first != 0 else nav_slice


# ============================================================================
# Part A -- oracle decomposition (arithmetic demonstration, NOT a hypothesis test)
# ============================================================================

def load_gics_monthly():
    """Month-end close for all 11 GICS sectors + SPY, FULL available history (resample
    first, filter to a window LATER) so the first return inside any reporting window is
    a real month-over-month return, not an artifact of slicing prices before differencing.
    Dynamic universe: XLC is NaN before its 2018-06-19 inception -- NOT a look-ahead trick,
    just realistic (you could not have owned XLC before it existed); nanmedian/nanmax below
    naturally skip it until then."""
    cols = {}
    for s in GICS11 + ["SPY"]:
        cols[s] = load(s, adjusted=True)["close"]
    idx = cols["SPY"].index
    df = pd.DataFrame({k: v.reindex(idx) for k, v in cols.items()}, index=idx)
    me = df.resample("ME").last()
    return me


def oracle_decompose(me: pd.DataFrame, start="2016-01-01"):
    """Step 1+2: monthly perfect-foresight oracle vs SPY/EW, and the monthly
    best-vs-median dispersion that IS the oracle's entire source."""
    sec = me[GICS11]
    ret_full = sec.pct_change()
    spy_ret_full = me["SPY"].pct_change()
    ret = ret_full[ret_full.index >= start]
    spy_ret = spy_ret_full[spy_ret_full.index >= start]

    best = ret.max(axis=1, skipna=True)
    median = ret.median(axis=1, skipna=True)
    best_sector = ret.idxmax(axis=1, skipna=True)
    gap = best - median

    oracle_nav_gross = (1 + best).cumprod()
    spy_nav = (1 + spy_ret).cumprod()
    ew_ret = ret.mean(axis=1, skipna=True)
    ew_nav = (1 + ew_ret).cumprod()

    # oracle NET-of-cost bonus number: 10bp/side charged whenever the picked sector changes
    # month to month (near-total-turnover strategy by construction -- re-picking the single
    # best sector every month almost never repeats the same winner twice running)
    prev_sector = best_sector.shift(1)
    switched = (best_sector != prev_sector).astype(float)
    cost_drag = switched * (2 * COST)
    oracle_ret_net = best - cost_drag
    oracle_nav_net = (1 + oracle_ret_net).cumprod()

    return dict(ret=ret, spy_ret=spy_ret, best=best, median=median, gap=gap,
                best_sector=best_sector, oracle_nav_gross=oracle_nav_gross,
                oracle_nav_net=oracle_nav_net, spy_nav=spy_nav, ew_nav=ew_nav,
                switched_frac=float(switched.iloc[1:].mean()))


def capture_grid(best: pd.Series, median: pd.Series, capture_rates):
    """Step 3: synthetic monthly return = median + capture*(best-median); compound -> CAGR
    per capture rate. capture=0 -> always exactly the median sector (theoretical zero-skill
    reference, NOT itself achievable without foresight either); capture=1 -> oracle."""
    out = {}
    for c in capture_rates:
        r = median + c * (best - median)
        nav = (1 + r).cumprod()
        out[c] = cagr(nav.to_numpy(), periods_per_year=12)
    return out


def xle_xlk_winrate(start="2016-01-01"):
    """Re-derive (NOT re-litigate) the settled 63d-momentum-switch win rate for XLE-XLK --
    EXACT same rule as `exp_xle_xlk_rotation.py`'s weights_switch(mom_gap_63). Used only to
    get a precise number for Part A's capture-rate bridge; the significance question for
    this pair is already settled (p>0.10) and is not re-tested here."""
    xle = load("XLE", adjusted=True)["close"]
    xlk = load("XLK", adjusted=True)["close"]
    idx = xle.index.intersection(xlk.index)
    xle, xlk = xle.reindex(idx), xlk.reindex(idx)
    mom_gap_63 = xle.pct_change(63) - xlk.pct_change(63)
    me_flags = month_end_flags(idx)
    me_pos = np.where(me_flags)[0]

    hits, total = 0, 0
    for j in range(len(me_pos) - 1):
        i = me_pos[j]
        d = idx[i]
        if d < pd.Timestamp(start):
            continue
        g = mom_gap_63.iloc[i]
        if np.isnan(g):
            continue
        i_next = me_pos[j + 1]
        realized_xle = xle.iloc[i_next] / xle.iloc[i] - 1.0
        realized_xlk = xlk.iloc[i_next] / xlk.iloc[i] - 1.0
        picked_xle = g > 0
        actual_winner_xle = realized_xle > realized_xlk
        hits += int(picked_xle == actual_winner_xle)
        total += 1
    return (hits / total if total else np.nan), total, hits


# ============================================================================
# Generic 2-leg binary engine (shared by Part B and Part C)
# ============================================================================

def weights_binary(signal: pd.Series, me_flags: np.ndarray, invert: bool = False) -> np.ndarray:
    """w = fraction in the 'A' leg (1.0/0.0 binary); decided at each month-end using data
    through that day (causal), held through the following month (month-end-signal / hold-
    next-month convention, matches exp_xle_xlk_rotation.py). invert=True flips polarity
    (used for the XLU 'falling yields' pair, which shares TNX's driver series with XLF but
    reads it in reverse)."""
    n = len(signal)
    sig = signal.to_numpy()
    w = np.full(n, np.nan)
    cur = 0.5  # neutral until first valid signal
    for i in range(n):
        if me_flags[i] and not np.isnan(sig[i]):
            positive = sig[i] > 0
            if invert:
                positive = not positive
            cur = 1.0 if positive else 0.0
        w[i] = cur
    return w


def simulate_binary(ret_a: np.ndarray, ret_b: np.ndarray, w_a: np.ndarray, cost: float):
    """w_a: fraction in leg A on each day (0/1 mostly, 0.5 only pre-warm-up). Index 0 of
    the arrays is treated as the window's rebasing anchor (nav[0]=1.0, its own return
    dropped by convention -- see module docstring); returns (nav, daily_ret, cost_drag)."""
    n = len(w_a)
    nav = np.empty(n)
    cost_drag = np.zeros(n)
    nav[0] = 1.0
    prev = w_a[0]
    for i in range(1, n):
        day_ret = prev * ret_a[i] + (1 - prev) * ret_b[i]
        step = nav[i - 1] * (1 + day_ret)
        turn = abs(w_a[i] - prev) * 2.0   # sell 1 unit + buy 1 unit when fully flipping
        if turn > 1e-9:
            step *= (1 - turn * cost)
            cost_drag[i] = turn * cost
        nav[i] = step
        prev = w_a[i]
    dret = np.full(n, np.nan)
    dret[1:] = nav[1:] / nav[:-1] - 1.0
    return nav, dret, cost_drag


def mc_matched_switches(ret_a: np.ndarray, ret_b: np.ndarray, real_w_a: np.ndarray,
                         me_pos: np.ndarray, cost: float, n_sims: int, rng: np.random.Generator):
    """Random control: n_sims monthly binary paths with EXACTLY the same number of
    month-to-month switches as the real signal within this window, random initial state,
    random switch timing. "Matched exposure" is automatic (both real and random are
    ALWAYS 100% in one leg, never cash). Vectorized across sims after a cheap per-sim
    monthly-sequence generation loop."""
    real_month_state = real_w_a[me_pos]
    n_months = len(me_pos)
    switches = int(np.sum(np.abs(np.diff(real_month_state)) > 1e-9)) if n_months > 1 else 0

    rand_month = np.empty((n_sims, n_months))
    for s in range(n_sims):
        init = rng.integers(0, 2)
        if n_months <= 1 or switches <= 0:
            rand_month[s, :] = init
            continue
        n_slots = n_months - 1
        k = min(switches, n_slots)
        slots = rng.choice(n_slots, size=k, replace=False)
        slot_mask = np.zeros(n_slots, dtype=bool)
        slot_mask[slots] = True
        state = init
        seq = np.empty(n_months)
        seq[0] = state
        for i in range(1, n_months):
            if slot_mask[i - 1]:
                state = 1 - state
            seq[i] = state
        rand_month[s] = seq

    n = len(ret_a)
    daily = np.empty((n_sims, n))
    daily[:, 0:me_pos[0] + 1] = rand_month[:, 0:1]
    for j in range(n_months):
        start_i = me_pos[j]
        end_i = me_pos[j + 1] if j + 1 < n_months else n
        daily[:, start_i:end_i] = rand_month[:, j:j + 1]

    day_ret = daily * ret_a[None, :] + (1 - daily) * ret_b[None, :]
    turn = np.zeros_like(daily)
    turn[:, 1:] = np.abs(np.diff(daily, axis=1)) * 2.0
    net_ret = day_ret - turn * cost
    net_ret[:, 0] = 0.0    # window anchor day: return dropped by convention (see docstring)
    nav = np.cumprod(1 + net_ret, axis=1)
    return nav, switches


def metrics_row(nav_1d: np.ndarray):
    c = cagr(nav_1d, periods_per_year=TD)
    mdd = max_drawdown(nav_1d)
    pnl = 10_000.0 * (nav_1d[-1] - 1.0)
    return c, mdd, pnl


def metrics_matrix(nav_2d: np.ndarray):
    """Vectorized CAGR/MaxDD/PnL across the sims axis (rows=sims)."""
    n_sims, n = nav_2d.shape
    years = (n - 1) / TD
    total_ret = nav_2d[:, -1] / nav_2d[:, 0]
    c = total_ret ** (1 / years) - 1 if years > 0 else total_ret - 1
    peak = np.maximum.accumulate(nav_2d, axis=1)
    dd = (nav_2d / peak - 1.0).min(axis=1)
    pnl = 10_000.0 * (nav_2d[:, -1] - 1.0)
    return c, dd, pnl


def monthly_compound(daily_ret: np.ndarray, me_pos: np.ndarray) -> np.ndarray:
    out = np.full(len(me_pos), np.nan)
    prev = 0
    for t, mp in enumerate(me_pos):
        seg = daily_ret[prev + 1:mp + 1] if t > 0 else daily_ret[1:mp + 1]
        seg = seg[~np.isnan(seg)]
        out[t] = np.prod(1 + seg) - 1 if len(seg) else np.nan
        prev = mp
    return out


def monthly_winrate(ret_a_monthly: np.ndarray, ret_b_monthly: np.ndarray, w_a_at_me: np.ndarray):
    """Fraction of decision months where the CHOSEN leg's realized return over the
    FOLLOWING month beat the leg not chosen (directional hit rate)."""
    hits, total = 0, 0
    for t in range(len(w_a_at_me) - 1):
        a, b = ret_a_monthly[t + 1], ret_b_monthly[t + 1]
        if np.isnan(a) or np.isnan(b) or np.isnan(w_a_at_me[t]):
            continue
        chose_a = w_a_at_me[t] > 0.5
        a_won = a > b
        hits += int(chose_a == a_won)
        total += 1
    return (hits / total if total else np.nan), total


def window_slice(idx_full, ret_a_full, ret_b_full, w_a_full, ws, we):
    mask = window_mask(idx_full, ws, we)
    if mask.sum() < 30:
        return None
    idxs = np.where(mask)[0]
    i0, i1 = int(idxs[0]), int(idxs[-1])
    ret_a = ret_a_full[i0:i1 + 1]
    ret_b = ret_b_full[i0:i1 + 1]
    w_a = w_a_full[i0:i1 + 1]
    sub_idx = idx_full[i0:i1 + 1]
    return ret_a, ret_b, w_a, sub_idx


def run_pair_window(ret_a_full, ret_b_full, w_a_full, idx_full, ws, we, rng):
    sl = window_slice(idx_full, ret_a_full, ret_b_full, w_a_full, ws, we)
    if sl is None:
        return None
    ret_a, ret_b, w_a, sub_idx = sl
    me_flags = month_end_flags(sub_idx)
    me_pos = np.where(me_flags)[0]
    me_pos = me_pos[me_pos > 0]   # drop a month-end that lands exactly on index 0 (anchor day)
    if len(me_pos) < 4:
        return None

    real_nav, real_dret, _ = simulate_binary(ret_a, ret_b, w_a, COST)
    real_c, real_mdd, real_pnl = metrics_row(real_nav)

    mc_nav, switches = mc_matched_switches(ret_a, ret_b, w_a, me_pos, COST, N_SIMS, rng)
    mc_c, mc_mdd, mc_pnl = metrics_matrix(mc_nav)

    ret_a_m = monthly_compound(ret_a, me_pos)
    ret_b_m = monthly_compound(ret_b, me_pos)
    w_a_at_me = w_a[me_pos]
    wr, wr_n = monthly_winrate(ret_a_m, ret_b_m, w_a_at_me)

    p_val = (1 + np.sum(mc_c >= real_c)) / (N_SIMS + 1)

    # 50/50 static benchmark (daily-blended, zero cost -- same convention as
    # exp_xle_xlk_rotation.py strategy 5)
    blend = 0.5 * ret_a + 0.5 * ret_b
    nav5050 = np.empty(len(blend))
    nav5050[0] = 1.0
    nav5050[1:] = np.cumprod(1 + blend[1:])
    c5050, mdd5050, pnl5050 = metrics_row(nav5050)

    return dict(
        real_cagr=real_c, real_mdd=real_mdd, real_pnl=real_pnl,
        mc_mean=float(np.mean(mc_c)), mc_p05=float(np.percentile(mc_c, 5)),
        mc_p50=float(np.percentile(mc_c, 50)), mc_p95=float(np.percentile(mc_c, 95)),
        mc_mdd_p50=float(np.percentile(mc_mdd, 50)), switches=switches,
        n_months=len(me_pos), p_val=p_val, winrate=wr, winrate_n=wr_n,
        bench5050_cagr=c5050, bench5050_mdd=mdd5050, bench5050_pnl=pnl5050,
        n_days=len(ret_a) - 1,
    )


# ============================================================================
# Part B -- three pre-registered external-driver pairs
# ============================================================================

def load_driver_frame():
    """WTI (CL=F) + 10y yield (^TNX) + XLE/XLF/XLU + SPY, common daily calendar
    (intersection -- futures/bond calendars differ from equities, intersection is the
    SAFEST causal-alignment choice)."""
    wti = load("CL=F", adjusted=False)["close"]
    tnx = load("^TNX", adjusted=False)["close"]
    xle = load("XLE", adjusted=True)["close"]
    xlf = load("XLF", adjusted=True)["close"]
    xlu = load("XLU", adjusted=True)["close"]
    spy = load("SPY", adjusted=True)["close"]
    idx = spy.index
    for s in (wti, tnx, xle, xlf, xlu):
        idx = idx.intersection(s.index)
    df = pd.DataFrame({
        "WTI": wti.reindex(idx), "TNX": tnx.reindex(idx), "XLE": xle.reindex(idx),
        "XLF": xlf.reindex(idx), "XLU": xlu.reindex(idx), "SPY": spy.reindex(idx),
    }, index=idx).dropna()
    return df


def build_driver_signals(df: pd.DataFrame):
    wti_sma26w = df["WTI"].rolling(130).mean()      # 26 weeks ~= 130 trading days
    oil_trend = df["WTI"] - wti_sma26w               # >0 -> price above 26w MA -> trend UP
    tnx_chg_13w = df["TNX"].diff(65)                 # 13 weeks ~= 65 trading days, LEVEL change
    return oil_trend, tnx_chg_13w


def run_part_b(rng):
    df = load_driver_frame()
    idx = df.index
    print(f"Part B master calendar: {idx.min().date()} -> {idx.max().date()}, {len(df)} rows")
    oil_trend, tnx_chg = build_driver_signals(df)
    me_flags = month_end_flags(idx)

    ret_xle = df["XLE"].pct_change().to_numpy()
    ret_xlf = df["XLF"].pct_change().to_numpy()
    ret_xlu = df["XLU"].pct_change().to_numpy()
    ret_spy = df["SPY"].pct_change().to_numpy()

    w_oil_xle = weights_binary(oil_trend, me_flags, invert=False)
    w_rate_xlf = weights_binary(tnx_chg, me_flags, invert=False)      # rising -> XLF
    w_rate_xlu = weights_binary(tnx_chg, me_flags, invert=True)       # falling -> XLU

    pairs = {
        "B1 Oil-trend -> XLE": (ret_xle, ret_spy, w_oil_xle),
        "B2 Rate-trend -> XLF": (ret_xlf, ret_spy, w_rate_xlf),
        "B3 Rate-trend(inv) -> XLU": (ret_xlu, ret_spy, w_rate_xlu),
    }

    windows = WINDOWS_BC + [SENS_B]
    results = {}
    for pname, (ret_a, ret_b, w_a) in pairs.items():
        for wname, ws, we in windows:
            r = run_pair_window(ret_a, ret_b, w_a, idx, ws, we, rng)
            results[(pname, wname)] = r

    return results, pairs.keys(), windows


# ============================================================================
# Part C -- tech-axis binary decision (QQQ vs RSP)
# ============================================================================

def load_qqq_rsp_frame():
    qqq = load("QQQ", adjusted=True)["close"]
    rsp = load("RSP", adjusted=True)["close"]
    idx = qqq.index.intersection(rsp.index)
    df = pd.DataFrame({"QQQ": qqq.reindex(idx), "RSP": rsp.reindex(idx)}, index=idx).dropna()
    return df


def build_composite_signal(df: pd.DataFrame):
    mom_gap_63 = df["QQQ"].pct_change(63) - df["RSP"].pct_change(63)
    ratio = df["QQQ"] / df["RSP"]
    sma200 = ratio.rolling(200).mean()
    slope = sma200.diff(21)     # ~1-month slope of the 200d SMA of the relative ratio
    return mom_gap_63, slope


def weights_composite(mom_gap: pd.Series, slope: pd.Series, me_flags: np.ndarray) -> np.ndarray:
    """Composite signal: 63d relative momentum AND the slope of the QQQ/RSP ratio's 200d
    SMA (a PRICE proxy for relative earnings-revision, NOT real estimates data -- disclosed).
    Both must agree in direction to flip; otherwise the prior month's holding is MAINTAINED
    (sticky rule, per brief)."""
    n = len(mom_gap)
    mg = mom_gap.to_numpy()
    sl = slope.to_numpy()
    w = np.full(n, np.nan)
    cur = 0.5   # neutral until warm-up complete
    for i in range(n):
        if me_flags[i] and not np.isnan(mg[i]) and not np.isnan(sl[i]):
            mom_dir = 1 if mg[i] > 0 else (-1 if mg[i] < 0 else 0)
            slope_dir = 1 if sl[i] > 0 else (-1 if sl[i] < 0 else 0)
            if mom_dir != 0 and mom_dir == slope_dir:
                cur = 1.0 if mom_dir > 0 else 0.0
            # else: disagreement or a flat reading -> MAINTAIN cur unchanged
        w[i] = cur
    return w


def run_part_c(rng):
    df = load_qqq_rsp_frame()
    idx = df.index
    print(f"Part C master calendar: {idx.min().date()} -> {idx.max().date()}, {len(df)} rows")
    mom_gap, slope = build_composite_signal(df)
    me_flags = month_end_flags(idx)

    ret_qqq = df["QQQ"].pct_change().to_numpy()
    ret_rsp = df["RSP"].pct_change().to_numpy()
    w_qqq = weights_composite(mom_gap, slope, me_flags)

    windows = WINDOWS_BC + [SENS_C]
    results = {}
    for wname, ws, we in windows:
        r = run_pair_window(ret_qqq, ret_rsp, w_qqq, idx, ws, we, rng)
        results[("C Tech-axis QQQ/RSP", wname)] = r
    return results, ["C Tech-axis QQQ/RSP"], windows


# ============================================================================
# Sanity check -- cross-validate the generic engine against the SETTLED XLE-XLK number
# ============================================================================

def sanity_check_xle_xlk(rng):
    """`2026-07-17_xle_xlk_rotation.md` reports 63d-momentum-switch CapEff = +22.80%/yr
    for the 2016+ PRIMARY window (2016-01-01 -> 2026-12-31, NOT the H1/H2 split used
    elsewhere in this script). Reproduce that number with THIS script's generic engine as
    an end-to-end correctness check before trusting it for the new Part B/C pairs."""
    xle = load("XLE", adjusted=True)["close"]
    xlk = load("XLK", adjusted=True)["close"]
    spy = load("SPY", adjusted=True)["close"]
    idx = spy.index.intersection(xle.index).intersection(xlk.index)
    xle, xlk, spy = xle.reindex(idx), xlk.reindex(idx), spy.reindex(idx)
    mom_gap_63 = xle.pct_change(63) - xlk.pct_change(63)
    me_flags = month_end_flags(idx)
    w_xle = weights_binary(mom_gap_63, me_flags, invert=False)
    ret_xle = xle.pct_change().to_numpy()
    ret_xlk = xlk.pct_change().to_numpy()

    r = run_pair_window(ret_xle, ret_xlk, w_xle, idx, "2016-01-01", END_CAP, rng)
    print(f"\n[SANITY CHECK] Generic engine reproduces XLE-XLK 63d switch, 2016+ primary window:")
    print(f"  this-script CapEff(=CAGR, exposure=100%) = {r['real_cagr']*100:+.2f}%/yr   "
          f"(settled report: +22.80%/yr, exp_xle_xlk_rotation.py)")
    print(f"  this-script MaxDD = {r['real_mdd']*100:.1f}%   (settled report: -31.2%)")
    return r


# ============================================================================
# Reporting
# ============================================================================

def fmt_pair_window(label, r):
    if r is None:
        return f"  {label:40} n<30, skip"
    sig = "*" if r["p_val"] < 0.05 else " "
    return (f"  {label:40} real={r['real_cagr']*100:+7.2f}%/yr  MC[mean={r['mc_mean']*100:+6.2f} "
            f"p05={r['mc_p05']*100:+6.2f} p50={r['mc_p50']*100:+6.2f} p95={r['mc_p95']*100:+6.2f}]  "
            f"p={r['p_val']:.3f}{sig}  switches={r['switches']:3d}/{r['n_months']:3d}mo  "
            f"WR={r['winrate']*100:5.1f}%(n={r['winrate_n']})  MaxDD={r['real_mdd']*100:7.1f}%  "
            f"PnL$10k->${10000+r['real_pnl']:9,.0f}  "
            f"[vs 5050: CAGR={r['bench5050_cagr']*100:+7.2f}% MaxDD={r['bench5050_mdd']*100:7.1f}% "
            f"PnL->${10000+r['bench5050_pnl']:9,.0f}]")


def main():
    rng = np.random.default_rng(SEED)
    print("=" * 118)
    print("SECTOR ROTATION FINAL SETTLEMENT -- Part A (oracle decomposition) / B (3 external ")
    print("drivers) / C (tech-axis binary) -- report numbers only, no verdicts")
    print("=" * 118)

    # ---------------- Part A ----------------
    print("\n" + "=" * 118)
    print("PART A -- 11-GICS-sector monthly perfect-foresight oracle: decomposition")
    print("=" * 118)
    me = load_gics_monthly()
    dec = oracle_decompose(me, start="2016-01-01")
    n_months = len(dec["best"])
    print(f"Universe: {len(GICS11)} GICS SPDR sectors (XLC dynamic-join 2018-06-19), "
          f"2016-01-01 -> {me.index.max().date()}, {n_months} monthly decisions")

    oracle_cagr_gross = cagr(dec["oracle_nav_gross"].to_numpy(), periods_per_year=12)
    oracle_cagr_net = cagr(dec["oracle_nav_net"].to_numpy(), periods_per_year=12)
    spy_cagr = cagr(dec["spy_nav"].to_numpy(), periods_per_year=12)
    ew_cagr = cagr(dec["ew_nav"].to_numpy(), periods_per_year=12)
    oracle_mdd = max_drawdown(dec["oracle_nav_gross"].to_numpy())
    spy_mdd = max_drawdown(dec["spy_nav"].to_numpy())

    print(f"\n-- Step 1: oracle CAGR vs SPY --")
    print(f"  SPY B&H                          CAGR={spy_cagr*100:+7.2f}%/yr   MaxDD={spy_mdd*100:7.1f}%")
    print(f"  EW 11 sectors (monthly rebal)     CAGR={ew_cagr*100:+7.2f}%/yr")
    print(f"  ORACLE (perfect monthly pick)     CAGR={oracle_cagr_gross*100:+7.2f}%/yr (gross)  "
          f"MaxDD={oracle_mdd*100:7.1f}%")
    print(f"  ORACLE net of cost (10bp/side, {dec['switched_frac']*100:.0f}% of months switch)"
          f"  CAGR={oracle_cagr_net*100:+7.2f}%/yr")
    print(f"  Gap oracle(net) - SPY = {(oracle_cagr_net-spy_cagr)*100:+.1f}pp/yr")

    gap = dec["gap"].dropna()
    print(f"\n-- Step 2: monthly (best - median) sector-return gap distribution, n={len(gap)} --")
    print(f"  p25={np.percentile(gap,25)*100:+6.2f}%   median={np.percentile(gap,50)*100:+6.2f}%   "
          f"p75={np.percentile(gap,75)*100:+6.2f}%   mean={gap.mean()*100:+6.2f}%")
    print(f"  Oracle = compounding the FULL (100% of) this gap every single month, on top of "
          f"the median sector's return.")

    print(f"\n-- Step 3: capture-rate grid (synthetic monthly return = median + capture*gap) --")
    grid = capture_grid(dec["best"], dec["median"], CAPTURE_RATES_HEADLINE)
    for c in CAPTURE_RATES_HEADLINE:
        print(f"  capture={c*100:5.1f}%   CAGR={grid[c]*100:+7.2f}%/yr")

    p_xlexlk, n_xlexlk, hits_xlexlk = xle_xlk_winrate(start="2016-01-01")
    implied_capture = 2 * p_xlexlk - 1
    grid_implied = capture_grid(dec["best"], dec["median"], [max(implied_capture, 0.0)])
    print(f"\n-- Reverse-engineer: XLE-XLK 63d-momentum-switch monthly win rate (2016+, "
          f"same rule as settled exp_xle_xlk_rotation.py) --")
    print(f"  win rate = {p_xlexlk*100:.1f}% ({hits_xlexlk}/{n_xlexlk} months)   "
          f"[user's cited approx range: ~52-55%]")
    print(f"  implied capture rate = 2p-1 = {implied_capture*100:+.1f}%   "
          f"(derivation: excess-over-5050 = (p-0.5)*gap; oracle excess-over-5050 = 0.5*gap; "
          f"ratio = 2p-1. ASSUMES win probability independent of gap size.)")
    print(f"  -> mapped onto the 11-sector capture-grid formula (illustrative bridge ONLY, "
          f"NOT a claim the 2-asset edge transfers to an 11-sector universe): "
          f"CAGR@{max(implied_capture,0.0)*100:.1f}% capture = {grid_implied[max(implied_capture,0.0)]*100:+.2f}%/yr")

    # ---------------- sanity check ----------------
    print("\n" + "=" * 118)
    print("SANITY CHECK -- generic engine vs SETTLED XLE-XLK number")
    print("=" * 118)
    sanity_check_xle_xlk(rng)

    # ---------------- Part B ----------------
    print("\n" + "=" * 118)
    print("PART B -- three pre-registered external-driver pairs (mechanism, not price)")
    print("=" * 118)
    res_b, pair_names_b, windows_b = run_part_b(rng)
    for pname in pair_names_b:
        print(f"\n-- {pname} --")
        for wname, ws, we in windows_b:
            print(fmt_pair_window(f"{wname} ({ws}->{we[:4]})", res_b.get((pname, wname))))

    # Bonferroni family for Part B: 3 pairs x 2 windows (H1/H2) = 6 (SENS excluded)
    print(f"\nBonferroni (Part B family, 3 pairs x 2 windows = 6 tests): alpha_adj = 0.05/6 = "
          f"{0.05/6:.5f}")
    for pname in pair_names_b:
        for wname, ws, we in WINDOWS_BC:
            r = res_b.get((pname, wname))
            if r is None:
                continue
            surv = "SURVIVES" if r["p_val"] < 0.05 / 6 else "does not survive"
            print(f"  {pname:30} {wname:14} p={r['p_val']:.4f}  {surv}")

    # ---------------- Part C ----------------
    print("\n" + "=" * 118)
    print("PART C -- tech-axis binary decision (QQQ vs RSP, composite signal)")
    print("=" * 118)
    res_c, pair_names_c, windows_c = run_part_c(rng)
    for pname in pair_names_c:
        print(f"\n-- {pname} --")
        for wname, ws, we in windows_c:
            print(fmt_pair_window(f"{wname} ({ws}->{we[:4]})", res_c.get((pname, wname))))

    print(f"\nBonferroni (Part C family, 1 axis x 2 windows = 2 tests): alpha_adj = 0.05/2 = "
          f"{0.05/2:.5f}")
    for wname, ws, we in WINDOWS_BC:
        r = res_c.get(("C Tech-axis QQQ/RSP", wname))
        if r is None:
            continue
        surv = "SURVIVES" if r["p_val"] < 0.05 / 2 else "does not survive"
        print(f"  {wname:14} p={r['p_val']:.4f}  {surv}")

    # combined whole-report family
    print(f"\nBonferroni (combined report-wide family, Part B + C = 8 tests): alpha_adj = "
          f"0.05/8 = {0.05/8:.5f}")
    all_survive = True
    for pname in pair_names_b:
        for wname, ws, we in WINDOWS_BC:
            r = res_b.get((pname, wname))
            if r is not None and r["p_val"] >= 0.05 / 8:
                all_survive = False
    for wname, ws, we in WINDOWS_BC:
        r = res_c.get(("C Tech-axis QQQ/RSP", wname))
        if r is not None and r["p_val"] >= 0.05 / 8:
            all_survive = False
    print(f"  ALL 8 primary tests survive combined Bonferroni: {all_survive}")

    print("\n" + "=" * 118)
    print("DONE. Module: backtest/experiments/exp_sector_final.py")
    print("Report numbers only -- no verdicts rendered here; see results .md '待覆核點' section.")
    print("=" * 118)


if __name__ == "__main__":
    main()
