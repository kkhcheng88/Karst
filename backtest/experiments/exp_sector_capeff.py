"""Sector-ETF CAPITAL-EFFICIENCY loop (Core Loop-2) — NOT a rotation/prediction test.

Quant cross-sectional sector ROTATION is already dead (0/28 factors past Bonferroni; see
`exp_rotation_challenge.py` / `exp_skill_curve.py` / `2026-07-06_core_strategy.md` §5). This
script does NOT try to predict which sector wins. It tests four pre-registered, narrower
DEPLOYMENT-MECHANISM hypotheses: given money is going somewhere at a given moment anyway
(a dip-buy, a panic hedge, a defensive tilt, a buffer asset), is a SECTOR EXPRESSION of that
deployment better than the SAME deployment in SPY? Every hypothesis therefore carries an
explicit CONTROL LEG on the identical entry/exit dates, buying SPY instead — the number that
matters is the INCREMENT (strategy − control), not the absolute return (validation-mirror-
and-increment discipline; see memory `validation-mirror-and-increment`).

H1 — Cross-sectional dip rotation (bull regime only): while SPY>200SMA, buy any sector with
     RSI-2<10 (equal-weight, cap 3 concurrent, 1/3 notional each; ties broken by MOST oversold
     first). Exit on RSI-2>{70,80} OR {5,10}-trading-day timeout (2x2 grid, whichever first).
     Control: identical entry/exit dates, buy SPY instead (same notional, same cost).
H2 — Panic-window sector deployment: quadrant (2) = SPY>200SMA & VIX>28 -> buy the 2 sectors
     with the WORST trailing 63d return (contrarian, equal-weight 50/50); exit when VIX<18.
     Quadrant (3) = SPY<=200SMA & VIX>28 variant reported separately (expected to lose — a bear
     panic dip-buy). Control: same dates, buy SPY (full notional). Episodes are rare -> reported
     per-episode, not just aggregated.
H3 — Defensive tilt at the PORTFOLIO level: 75/25 SPY/cash shell. On bear-hysteresis (close <
     0.98*200SMA for 5 CONSECUTIVE days), move the 25pp cash (Variant A) — or the 25pp cash
     PLUS an extra 25pp pulled from the SPY base (Variant B, total 50pp) — into an equal-weight
     defensive basket (XLP/XLV/XLU). Revert to cash/base the instant SPY reclaims 200SMA (no
     hysteresis on the way back up, matching the T2 rule in core_strategy.md). Two controls:
     Control-DoNothing (75/25 forever, no transitions) and Control-SPY (same transition dates/
     sizing, but the freed capital buys MORE SPY instead of the defensive basket — isolates
     whether the SECTOR CHOICE adds anything beyond simply being more/less equity-exposed).
     This is a structural index-timing variant (T2 drag risk) — negative results are reported
     as negative, not massaged (repo rule: never manufacture alpha that isn't there).
H4 — Defensive LEG asset: cash vs bonds vs 50/50. Core shell 75% SPY / 10% LEAP-premium PROXY
     (simplified per spec to a 1.7x daily-reset SPY exposure sleeve — NOT a real option, no
     theta/skew/crash-vega; documented, not hidden) / 15% buffer. Buffer variants: 100% cash
     (^IRX), 100% IEF (7-10y Treasury total return), 50/50, rebalanced monthly back to target
     weights. Reports full period + specific stress windows (2008 GFC, 2020 COVID, 2022 stock-
     bond selloff) since the prior (exp_portfolio_rotation.py, 2026-07-06) found bonds beat
     cash as a rotation sleeve's defensive leg — this tests whether that holds at the core-
     shell buffer level too.

DATA: `backtest/data.py` `load(sym, adjusted=True)` (yfinance total-return, dividends matter a
lot for high-yield sectors) for the 11 SPDR sectors + SPY + IEF; `^VIX` / `^IRX` loaded raw (no
dividends, adjusted has no effect). Universe is POINT-IN-TIME: XLRE (inception 2015-10-08) and
XLC (inception 2018-06-19) simply have no price data before their inception in the loaded
frame (no ffill-before-inception) and are silently excluded from cross-sectional selection
until then — this is what "只入 2018+ 窗" means mechanically, no separate window hack needed.
Cost: 5bps/side (ETF) applied at every entry/exit/rebalance. Execution: T close signal -> T+1
close trade (position starts earning from T+2 onward — the conservative, literal reading of
"T 收市訊號 -> T+1 收市成交", not the common shift(1)-into-day-T convention used elsewhere in
this repo for continuously-held sleeves). Windows: FULL (2000-01-01+, sector-200SMA-warmup-
safe) / 2016-2020 / 2021+ for H1-H3; H4 is IEF-inception-constrained (2002-08-01+).

Stats: increment = paired same-day/same-episode t-test (scipy ttest_1samp on the excess
series, which IS the paired diff) — no Bonferroni here (orchestrator does that across the
whole research program), but every section reports its own trial count for that purpose.

    python backtest/experiments/exp_sector_capeff.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load  # noqa: E402
from metrics import ann_sharpe, cagr, jensen_alpha, max_drawdown  # noqa: E402

TD = 252
COST = 0.0005  # 5bps/side, ETF trades (repo standard)

SECTORS_LONG = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB"]
SECTORS_SHORT = ["XLRE", "XLC"]
ALL_SECTORS = SECTORS_LONG + SECTORS_SHORT
DEFENSIVE = ["XLP", "XLV", "XLU"]

WINDOWS = [
    ("FULL 2000-2026", "2000-01-01", "2026-12-31"),
    ("2016-2020", "2016-01-01", "2020-12-31"),
    ("2021+", "2021-01-01", "2026-12-31"),
]
WINDOWS_H4 = [
    ("FULL 2002-2026 (IEF-constrained)", "2002-08-01", "2026-12-31"),
    ("2016-2020", "2016-01-01", "2020-12-31"),
    ("2021+", "2021-01-01", "2026-12-31"),
]
CRISIS_WINDOWS = [
    ("2008 GFC", "2008-01-01", "2008-12-31"),
    ("2020 COVID", "2020-01-01", "2020-12-31"),
    ("2022 stock-bond selloff", "2022-01-01", "2022-12-31"),
]


# ============================================================================
# 1. Data
# ============================================================================

def load_all():
    """Master calendar = SPY's trading days (NYSE). Sector/SPY/IEF closes are total-return
    (adjusted=True); NOT forward/back-filled across inception gaps (point-in-time universe).
    VIX/IRX are ffilled onto the calendar (small cross-venue calendar mismatches only)."""
    closes = {}
    for sym in ALL_SECTORS + ["SPY", "IEF"]:
        closes[sym] = load(sym, adjusted=True)["close"]
    vix = load("^VIX")["close"]
    irx = load("^IRX")["close"]
    idx = closes["SPY"].index
    df = pd.DataFrame({k: v.reindex(idx) for k, v in closes.items()}, index=idx)
    vix_s = vix.reindex(idx).ffill(limit=3)
    irx_s = irx.reindex(idx).ffill(limit=3)
    avail = {s: df[s].notna() for s in ALL_SECTORS}
    return df, vix_s, irx_s, avail


# ============================================================================
# 2. Signal primitives
# ============================================================================

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


def net_ret(entry_px: float, exit_px: float, cost: float = COST) -> float:
    return (exit_px * (1 - cost)) / (entry_px * (1 + cost)) - 1.0


def window_mask(idx: pd.DatetimeIndex, ws: str, we: str) -> np.ndarray:
    return np.asarray((idx >= ws) & (idx <= we))


def rebase(nav_slice: np.ndarray) -> np.ndarray:
    nav_slice = np.asarray(nav_slice, float)
    valid = ~np.isnan(nav_slice)
    if not valid.any():
        return nav_slice
    first = nav_slice[valid][0]
    return nav_slice / first if first != 0 else nav_slice


def ann_from_daily(returns_when_invested: np.ndarray, td: int = TD):
    """(deployed_CAGR, conditional_Sharpe) -- exp_capital_efficiency.py's 'return on deployed
    capital' convention: geometric compounding over invested days only, annualized by the
    ACTUAL number of invested days (not calendar days)."""
    r = np.asarray(returns_when_invested, float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n < 5:
        return float("nan"), float("nan")
    compound = np.prod(1.0 + r)
    dep_cagr = compound ** (td / n) - 1.0 if compound > 0 else float("nan")
    sd = r.std(ddof=1)
    dep_sharpe = (r.mean() / sd) * np.sqrt(td) if sd > 0 else float("nan")
    return dep_cagr, dep_sharpe


def ttest(excess: np.ndarray):
    x = np.asarray(excess, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 2 or x.std(ddof=1) == 0:
        return float("nan"), float("nan"), n
    t, p = stats.ttest_1samp(x, 0.0)
    return float(t), float(p), n


# ============================================================================
# 3. H1 -- cross-sectional dip rotation (bull-gated)
# ============================================================================

def simulate_h1(df, avail, spy_close, sma200_spy, rsi_map, exit_rsi, timeout_td, capacity=3):
    idx = df.index
    n = len(idx)
    spy_v = spy_close.values
    bull = (spy_close > sma200_spy).values
    sec_arr = {s: df[s].values for s in ALL_SECTORS}
    avail_arr = {s: avail[s].values for s in ALL_SECTORS}
    rsi_arr = {s: rsi_map[s].values for s in ALL_SECTORS}

    start_i = int(np.argmax(sma200_spy.notna().values))
    held: dict[str, dict] = {}
    trades = []

    for i in range(start_i, n - 1):
        if np.isnan(spy_v[i]) or np.isnan(spy_v[i + 1]):
            continue
        # exits (signal at close i, execute i+1)
        to_exit = []
        for s, info in held.items():
            r2 = rsi_arr[s][i]
            days_held = i - info["entry_exec_i"]
            if (not np.isnan(r2) and r2 > exit_rsi) or (days_held >= timeout_td):
                to_exit.append(s)
        for s in to_exit:
            info = held.pop(s)
            entry_i, exit_i = info["entry_exec_i"], i + 1
            ep, xp = sec_arr[s][entry_i], sec_arr[s][exit_i]
            if np.isnan(ep) or np.isnan(xp):
                continue
            strat_r = net_ret(ep, xp)
            ctrl_r = net_ret(spy_v[entry_i], spy_v[exit_i])
            trades.append(dict(sector=s, entry_date=idx[entry_i], exit_date=idx[exit_i],
                                days_held=exit_i - entry_i, strat_ret=strat_r, ctrl_ret=ctrl_r,
                                excess=strat_r - ctrl_r))
        # entries
        if bull[i] and len(held) < capacity:
            free = capacity - len(held)
            cands = []
            for s in ALL_SECTORS:
                if s in held or not avail_arr[s][i]:
                    continue
                r2 = rsi_arr[s][i]
                if not np.isnan(r2) and r2 < 10:
                    cands.append((r2, s))
            cands.sort()  # most-oversold first
            for r2, s in cands[:free]:
                if np.isnan(sec_arr[s][i + 1]):
                    continue
                held[s] = dict(entry_exec_i=i + 1)
        # cross-foot: capacity/notional conservation -- never more than `capacity` concurrent
        # 1/3-weight slots (i.e. never >100% notional deployed across sector picks)
        assert len(held) <= capacity, "H1 cross-foot: capacity exceeded"
    return trades


def deployed_daily(df, trades, weight, use_spy=False):
    idx = df.index
    n = len(idx)
    contrib = np.zeros(n)
    wsum = np.zeros(n)
    date_pos = {d: p for p, d in enumerate(idx)}
    for tr in trades:
        entry_i = date_pos[tr["entry_date"]]
        exit_i = date_pos[tr["exit_date"]]
        px = df["SPY"].values if use_spy else df[tr["sector"]].values
        for d in range(entry_i, exit_i):
            r = px[d + 1] / px[d] - 1.0
            if d == entry_i:
                r = (1 + r) * (1 - COST) - 1.0
            if d + 1 == exit_i:
                r = (1 + r) * (1 - COST) - 1.0
            contrib[d + 1] += weight * r
            wsum[d + 1] += weight
    out = np.full(n, np.nan)
    m = wsum > 0
    out[m] = contrib[m] / wsum[m]
    return out


def run_h1(df, avail, vix, irx):
    spy_close = df["SPY"]
    sma200_spy = sma(spy_close, 200)
    rsi_map = {s: rsi2(df[s]) for s in ALL_SECTORS}
    idx = df.index
    grid = [(70, 5), (70, 10), (80, 5), (80, 10)]
    lines = []
    lines.append("=== H1: cross-sectional sector dip rotation (bull-gated, cap 3, 1/3 notional) ===")
    trial_n = 0
    for exit_rsi, timeout in grid:
        trades = simulate_h1(df, avail, spy_close, sma200_spy, rsi_map, exit_rsi, timeout)
        strat_daily = deployed_daily(df, trades, 1 / 3, use_spy=False)
        ctrl_daily = deployed_daily(df, trades, 1 / 3, use_spy=True)
        lines.append(f"\n-- grid cell: exit RSI-2>{exit_rsi} OR {timeout}td timeout "
                      f"(n_trades total={len(trades)}) --")
        for wname, ws, we in WINDOWS:
            wtrades = [t for t in trades if ws <= str(t["entry_date"].date()) <= we]
            if len(wtrades) < 3:
                lines.append(f"  [{wname:16}] n<3 trades, skip")
                continue
            excess = np.array([t["excess"] for t in wtrades])
            winrate = float((excess > 0).mean())
            t_stat, p_val, n_used = ttest(excess)
            mask = window_mask(idx, ws, we)
            dep_cagr, dep_sharpe = ann_from_daily(strat_daily[mask])
            ctrl_cagr, ctrl_sharpe = ann_from_daily(ctrl_daily[mask])
            trial_n += 1
            lines.append(
                f"  [{wname:16}] n={len(wtrades):4d}  mean_excess/trade={excess.mean()*100:+.3f}%  "
                f"t={t_stat:+.2f} (p={p_val:.3f})  win%={winrate*100:5.1f}%  "
                f"avg_days_held={np.mean([t['days_held'] for t in wtrades]):.1f}  |  "
                f"deployed-CAGR strat={dep_cagr*100:+7.2f}% ctrl(SPY)={ctrl_cagr*100:+7.2f}%  "
                f"cond.Sharpe strat={dep_sharpe:5.2f} ctrl={ctrl_sharpe:5.2f}")
    lines.append(f"\nH1 trial count (grid cells x windows, for orchestrator Bonferroni bookkeeping): "
                  f"{len(grid)} cells x up to {len(WINDOWS)} windows = up to {len(grid)*len(WINDOWS)} "
                  f"tests ({trial_n} actually had n>=3)")
    return "\n".join(lines)


# ============================================================================
# 4. H2 -- panic-window sector deployment (episode-level)
# ============================================================================

def simulate_h2(df, avail, spy_close, sma200_spy, vix, bull_required=True):
    idx = df.index
    n = len(idx)
    bull = (spy_close > sma200_spy).values
    vix_v = vix.values
    spy_v = spy_close.values
    start_i = max(int(np.argmax(sma200_spy.notna().values)), 63)

    in_pos = False
    entry_secs = entry_exec_i = entry_vix = None
    episodes = []
    for i in range(start_i, n - 1):
        if np.isnan(spy_v[i]):
            continue
        if not in_pos:
            cond = (bull[i] == bull_required) and (not np.isnan(vix_v[i])) and (vix_v[i] > 28)
            if cond:
                scores = []
                for s in ALL_SECTORS:
                    if not (avail[s].values[i] and avail[s].values[i - 63]):
                        continue
                    px = df[s].values
                    p0, p1 = px[i - 63], px[i]
                    if np.isnan(p0) or np.isnan(p1) or p0 == 0:
                        continue
                    scores.append((p1 / p0 - 1.0, s))
                if len(scores) < 2:
                    continue
                scores.sort()
                entry_secs = [s for _, s in scores[:2]]
                entry_exec_i = i + 1
                entry_vix = vix_v[i]
                in_pos = True
        else:
            if not np.isnan(vix_v[i]) and vix_v[i] < 18:
                exit_exec_i = i + 1
                ok = True
                strat_r = 0.0
                for s in entry_secs:
                    px = df[s].values
                    ep, xp = px[entry_exec_i], px[exit_exec_i]
                    if np.isnan(ep) or np.isnan(xp):
                        ok = False
                        break
                    strat_r += 0.5 * net_ret(ep, xp)
                if ok:
                    ctrl_r = net_ret(spy_v[entry_exec_i], spy_v[exit_exec_i])
                    episodes.append(dict(
                        entry_date=idx[entry_exec_i], exit_date=idx[exit_exec_i], sectors=entry_secs,
                        entry_vix=entry_vix, exit_vix=vix_v[i], days_held=exit_exec_i - entry_exec_i,
                        strat_ret=strat_r, ctrl_ret=ctrl_r, excess=strat_r - ctrl_r))
                in_pos = False
                entry_secs = None
    return episodes


def fmt_episodes(episodes, label):
    lines = [f"\n-- {label}: per-episode table (n={len(episodes)}) --"]
    if not episodes:
        lines.append("  (no episodes in sample)")
        return "\n".join(lines)
    lines.append(f"  {'entry':11}{'exit':11}{'sectors':16}{'entryVIX':>9}{'exitVIX':>8}"
                  f"{'days':>6}{'strat%':>9}{'ctrl%':>9}{'excess%':>9}")
    for e in episodes:
        secs = "+".join(e["sectors"])
        lines.append(f"  {str(e['entry_date'].date()):11}{str(e['exit_date'].date()):11}{secs:16}"
                      f"{e['entry_vix']:9.1f}{e['exit_vix']:8.1f}{e['days_held']:6d}"
                      f"{e['strat_ret']*100:9.2f}{e['ctrl_ret']*100:9.2f}{e['excess']*100:9.2f}")
    excess = np.array([e["excess"] for e in episodes])
    winrate = float((excess > 0).mean())
    t_stat, p_val, n_used = ttest(excess)
    lines.append(f"  AGGREGATE: mean_excess={excess.mean()*100:+.2f}%  t={t_stat:+.2f} (p={p_val:.3f}, "
                 f"n={n_used}{'  [SMALL-N, indicative only]' if n_used < 15 else ''})  "
                 f"win%={winrate*100:.1f}%")
    return "\n".join(lines)


def run_h2(df, avail, vix, irx):
    spy_close = df["SPY"]
    sma200_spy = sma(spy_close, 200)
    lines = ["\n=== H2: panic-window sector deployment (worst-63d-return pair, exit VIX<18) ==="]
    ep_q2 = simulate_h2(df, avail, spy_close, sma200_spy, vix, bull_required=True)
    lines.append(fmt_episodes(ep_q2, "Quadrant (2) bull+panic (SPY>200SMA & VIX>28) -- the brief's primary case"))
    ep_q3 = simulate_h2(df, avail, spy_close, sma200_spy, vix, bull_required=False)
    lines.append(fmt_episodes(ep_q3, "Quadrant (3) bear+panic variant (SPY<=200SMA & VIX>28) -- expected negative"))
    lines.append(f"\nH2 trial count: 2 quadrant variants tested.")
    return "\n".join(lines)


# ============================================================================
# 5. H3 -- portfolio-level defensive tilt
# ============================================================================

def simulate_h3(df, irx_daily, spy_close, sma200_spy, extra_from_base=0.0, use_spy_instead=False,
                base_w=0.75, enabled=True):
    idx = df.index
    n = len(idx)
    close_spy = spy_close.values
    sma200_v = sma200_spy.values
    ret_spy = np.zeros(n)
    ret_spy[1:] = close_spy[1:] / close_spy[:-1] - 1.0
    ret_def = {}
    for s in DEFENSIVE:
        c = df[s].values
        r = np.zeros(n)
        valid = ~np.isnan(c)
        m = valid[1:] & valid[:-1]
        r[1:][m] = c[1:][m] / c[:-1][m] - 1.0
        # pre-inception days are NaN in c; def_val is 0.0 there anyway (position never opens before
        # a sector exists), but 0.0 * NaN = NaN in IEEE754, so zero the pre-inception returns
        # explicitly rather than let NaN silently poison def_val for the rest of the simulation.
        ret_def[s] = r

    below98 = pd.Series(close_spy < 0.98 * sma200_v, index=idx)
    bear_trigger = (below98.rolling(5, min_periods=5).sum() == 5).values
    bull_trigger = (close_spy > sma200_v)

    cash_w0 = 1.0 - base_w
    base_val, cash_val = base_w, cash_w0
    def_val = {s: 0.0 for s in DEFENSIVE}
    spy_extra_val = 0.0
    state = 0  # 0 normal, 1 defensive-deployed
    pending = None
    nav = np.full(n, np.nan)
    nav[0] = base_val + cash_val
    def_first_valid = max(int(np.argmax(~np.isnan(df[s].values))) for s in DEFENSIVE)
    start_i = max(int(np.argmax(sma200_spy.notna().values)), def_first_valid)

    for i in range(1, n):
        base_val *= (1 + ret_spy[i])
        cash_val *= (1 + irx_daily[i])
        for s in DEFENSIVE:
            def_val[s] *= (1 + ret_def[s][i])
        spy_extra_val *= (1 + ret_spy[i])

        if pending == "ENTER":
            total_now = base_val + cash_val + sum(def_val.values()) + spy_extra_val
            deploy = cash_val
            if extra_from_base > 0:
                pull = min(extra_from_base * total_now, base_val)
                base_val -= pull
                deploy += pull
            deploy_after_cost = deploy * (1 - COST)
            if use_spy_instead:
                spy_extra_val += deploy_after_cost
            else:
                for s in DEFENSIVE:
                    def_val[s] += deploy_after_cost / 3.0
            cash_val = 0.0
            state = 1
        elif pending == "EXIT":
            proceeds = sum(def_val.values()) + spy_extra_val
            proceeds_after_cost = proceeds * (1 - COST)
            def_val = {s: 0.0 for s in DEFENSIVE}
            spy_extra_val = 0.0
            if extra_from_base > 0:
                total_deployed_frac = cash_w0 + extra_from_base
                base_back = proceeds_after_cost * (extra_from_base / total_deployed_frac)
                cash_val = proceeds_after_cost - base_back
                base_val += base_back
            else:
                cash_val = proceeds_after_cost
            state = 0
        pending = None

        nav[i] = base_val + cash_val + sum(def_val.values()) + spy_extra_val
        assert cash_val >= -1e-9 and base_val >= -1e-9, "H3 cross-foot: negative leg value"

        if enabled and i >= start_i:
            if state == 0 and bear_trigger[i]:
                pending = "ENTER"
            elif state == 1 and bull_trigger[i]:
                pending = "EXIT"
    ret = np.zeros(n)
    ret[1:] = nav[1:] / nav[:-1] - 1.0
    return nav, ret


def report_h3_config(label, nav, ret, base_ret, idx, lines):
    for wname, ws, we in WINDOWS:
        mask = window_mask(idx, ws, we)
        if mask.sum() < 30:
            continue
        nav_w = rebase(nav[mask])
        ret_w = ret[mask]
        a, b, t = jensen_alpha(ret_w, base_ret[mask])
        lines.append(f"  [{wname:16}] {label:34} CAGR {cagr(nav_w)*100:+7.2f}%  "
                      f"Sharpe {ann_sharpe(ret_w):5.2f}  MaxDD {max_drawdown(nav_w)*100:7.1f}%  "
                      f"vs-donothing Alpha {a*100:+6.2f}% (t{t:+4.1f}) Beta {b:4.2f}")


def run_h3(df, avail, vix, irx):
    spy_close = df["SPY"]
    sma200_spy = sma(spy_close, 200)
    irx_daily = (irx / 100.0 / TD).ffill().fillna(0.0).values
    idx = df.index
    lines = ["\n=== H3: portfolio-level defensive tilt (75/25 SPY/cash shell) ==="]

    nav_none, ret_none = simulate_h3(df, irx_daily, spy_close, sma200_spy, enabled=False)
    nav_a, ret_a = simulate_h3(df, irx_daily, spy_close, sma200_spy, extra_from_base=0.0, use_spy_instead=False)
    nav_a_spy, ret_a_spy = simulate_h3(df, irx_daily, spy_close, sma200_spy, extra_from_base=0.0, use_spy_instead=True)
    nav_b, ret_b = simulate_h3(df, irx_daily, spy_close, sma200_spy, extra_from_base=0.25, use_spy_instead=False)
    nav_b_spy, ret_b_spy = simulate_h3(df, irx_daily, spy_close, sma200_spy, extra_from_base=0.25, use_spy_instead=True)

    lines.append("\n-- Control-DoNothing (75/25 SPY/cash, no transitions ever) vs itself as base --")
    for wname, ws, we in WINDOWS:
        mask = window_mask(idx, ws, we)
        if mask.sum() < 30:
            continue
        nav_w = rebase(nav_none[mask])
        lines.append(f"  [{wname:16}] {'Control-DoNothing (75/25)':34} CAGR {cagr(nav_w)*100:+7.2f}%  "
                      f"Sharpe {ann_sharpe(ret_none[mask]):5.2f}  MaxDD {max_drawdown(nav_w)*100:7.1f}%")

    lines.append("\n-- Variant A: 25pp cash -> defensive basket (XLP/XLV/XLU) on bear-hysteresis --")
    report_h3_config("Variant A (defensive, 25pp)", nav_a, ret_a, ret_none, idx, lines)
    lines.append("\n-- Control A-SPY: same 25pp/dates, buy MORE SPY instead of defensive basket --")
    report_h3_config("Control A-SPY (25pp into SPY)", nav_a_spy, ret_a_spy, ret_none, idx, lines)
    lines.append("\n-- increment: Variant A minus Control A-SPY (does the SECTOR CHOICE matter, beyond just more/less SPY?) --")
    for wname, ws, we in WINDOWS:
        mask = window_mask(idx, ws, we)
        if mask.sum() < 30:
            continue
        diff = ret_a[mask] - ret_a_spy[mask]
        t_stat, p_val, n_used = ttest(diff)
        lines.append(f"  [{wname:16}] mean daily diff={np.nanmean(diff)*TD*100:+.2f}%/yr(ann. arith.)  "
                      f"t={t_stat:+.2f} (p={p_val:.3f}, n={n_used})")

    lines.append("\n-- Variant B: 25pp cash + 25pp PULLED FROM BASE (50pp total) -> defensive basket --")
    report_h3_config("Variant B (defensive, 50pp)", nav_b, ret_b, ret_none, idx, lines)
    lines.append("\n-- Control B-SPY: same 50pp/dates, buy MORE SPY instead --")
    report_h3_config("Control B-SPY (50pp into SPY)", nav_b_spy, ret_b_spy, ret_none, idx, lines)
    lines.append("\n-- increment: Variant B minus Control B-SPY --")
    for wname, ws, we in WINDOWS:
        mask = window_mask(idx, ws, we)
        if mask.sum() < 30:
            continue
        diff = ret_b[mask] - ret_b_spy[mask]
        t_stat, p_val, n_used = ttest(diff)
        lines.append(f"  [{wname:16}] mean daily diff={np.nanmean(diff)*TD*100:+.2f}%/yr(ann. arith.)  "
                      f"t={t_stat:+.2f} (p={p_val:.3f}, n={n_used})")

    lines.append("\nH3 trial count: 2 variants (A/B) x 2 comparisons (vs DoNothing, vs SPY-control) "
                 "x 3 windows = up to 12 tests.")
    return "\n".join(lines)


# ============================================================================
# 6. H4 -- defensive leg: cash vs bonds vs 50/50
# ============================================================================

def simulate_h4(df, irx_daily, buffer_mode, base_w=0.75, leap_w=0.10, buf_w=0.15, leap_mult=1.7):
    idx = df.index
    n = len(idx)
    spy_v = df["SPY"].values
    ief_v = df["IEF"].values
    ret_spy = np.zeros(n)
    ret_spy[1:] = spy_v[1:] / spy_v[:-1] - 1.0
    ret_ief = np.full(n, 0.0)
    valid_ief = ~np.isnan(ief_v)
    ret_ief[1:][valid_ief[1:] & valid_ief[:-1]] = (
        ief_v[1:][valid_ief[1:] & valid_ief[:-1]] / ief_v[:-1][valid_ief[1:] & valid_ief[:-1]] - 1.0)

    if buffer_mode == "cash":
        cash_frac, ief_frac = buf_w, 0.0
    elif buffer_mode == "ief":
        cash_frac, ief_frac = 0.0, buf_w
    else:
        cash_frac, ief_frac = buf_w / 2, buf_w / 2

    base_val, leap_val = base_w, leap_w
    cash_val, ief_val = cash_frac, ief_frac
    nav = np.full(n, np.nan)
    nav[0] = base_val + leap_val + cash_val + ief_val
    months = idx.to_period("M")

    for i in range(1, n):
        base_val *= (1 + ret_spy[i])
        leap_val *= (1 + leap_mult * ret_spy[i])
        cash_val *= (1 + irx_daily[i])
        ief_val *= (1 + ret_ief[i])

        if months[i] != months[i - 1]:
            total = base_val + leap_val + cash_val + ief_val
            target_base, target_leap = base_w * total, leap_w * total
            target_cash, target_ief = cash_frac * total, ief_frac * total
            turnover = (abs(base_val - target_base) + abs(leap_val - target_leap)
                        + abs(cash_val - target_cash) + abs(ief_val - target_ief))
            total_after = total - turnover * COST
            base_val, leap_val = base_w * total_after, leap_w * total_after
            cash_val, ief_val = cash_frac * total_after, ief_frac * total_after

        nav[i] = base_val + leap_val + cash_val + ief_val
        assert nav[i] > 0, "H4 cross-foot: NAV went non-positive"

    ret = np.zeros(n)
    ret[1:] = nav[1:] / nav[:-1] - 1.0
    return nav, ret


def run_h4(df, avail, vix, irx):
    idx = df.index
    irx_daily = (irx / 100.0 / TD).ffill().fillna(0.0).values
    lines = ["\n=== H4: defensive leg -- cash vs IEF(bonds) vs 50/50 "
             "(core shell 75% SPY / 10% LEAP-proxy(1.7x SPY, SIMPLIFIED) / 15% buffer) ==="]

    navs = {}
    for mode in ["cash", "ief", "5050"]:
        navs[mode] = simulate_h4(df, irx_daily, mode)

    spy_v = df["SPY"].values
    spy_ret = np.zeros(len(idx))
    spy_ret[1:] = spy_v[1:] / spy_v[:-1] - 1.0
    spy_ret[0] = -COST
    spy_nav = np.cumprod(1 + spy_ret)

    lines.append("\n-- Full-period + sub-window CAGR/Sharpe/MaxDD by buffer variant --")
    for wname, ws, we in WINDOWS_H4:
        mask = window_mask(idx, ws, we)
        if mask.sum() < 30:
            continue
        lines.append(f"\n  [{wname}]")
        nav_w = rebase(spy_nav[mask])
        lines.append(f"    {'SPY 100% B&H (ref)':28} CAGR {cagr(nav_w)*100:+7.2f}%  "
                      f"Sharpe {ann_sharpe(spy_ret[mask]):5.2f}  MaxDD {max_drawdown(nav_w)*100:7.1f}%")
        for mode, label in [("cash", "buffer=cash(IRX)"), ("ief", "buffer=IEF(bonds)"), ("5050", "buffer=50/50")]:
            nav_m, ret_m = navs[mode]
            nav_mw = rebase(nav_m[mask])
            lines.append(f"    {'shell 75/10/'+label:28} CAGR {cagr(nav_mw)*100:+7.2f}%  "
                          f"Sharpe {ann_sharpe(ret_m[mask]):5.2f}  MaxDD {max_drawdown(nav_mw)*100:7.1f}%")

    lines.append("\n-- Stress windows (2008 GFC / 2020 COVID / 2022 stock-bond selloff), within-window MaxDD --")
    for wname, ws, we in CRISIS_WINDOWS:
        mask = window_mask(idx, ws, we)
        if mask.sum() < 30:
            continue
        lines.append(f"\n  [{wname}]")
        nav_w = rebase(spy_nav[mask])
        lines.append(f"    {'SPY 100% B&H (ref)':28} CAGR {cagr(nav_w)*100:+7.2f}%  MaxDD {max_drawdown(nav_w)*100:7.1f}%")
        for mode, label in [("cash", "buffer=cash(IRX)"), ("ief", "buffer=IEF(bonds)"), ("5050", "buffer=50/50")]:
            nav_m, ret_m = navs[mode]
            nav_mw = rebase(nav_m[mask])
            lines.append(f"    {'shell 75/10/'+label:28} CAGR {cagr(nav_mw)*100:+7.2f}%  MaxDD {max_drawdown(nav_mw)*100:7.1f}%")

    lines.append("\n-- Increment: buffer variant minus cash-buffer, paired daily return t-test --")
    ret_cash = navs["cash"][1]
    for wname, ws, we in WINDOWS_H4:
        mask = window_mask(idx, ws, we)
        if mask.sum() < 30:
            continue
        for mode, label in [("ief", "IEF - cash"), ("5050", "50/50 - cash")]:
            diff = navs[mode][1][mask] - ret_cash[mask]
            t_stat, p_val, n_used = ttest(diff)
            lines.append(f"  [{wname:28}] {label:14} ann.diff={np.nanmean(diff)*TD*100:+.2f}pp/yr  "
                          f"t={t_stat:+.2f} (p={p_val:.3f}, n={n_used})")

    lines.append("\nH4 trial count: 3 buffer variants, 2 increments (IEF-cash, 5050-cash) x "
                 f"{len(WINDOWS_H4)} windows = up to {2*len(WINDOWS_H4)} increment tests "
                 f"+ {3*len(CRISIS_WINDOWS)} stress-window cells.")
    return "\n".join(lines)


# ============================================================================
# 7. Main
# ============================================================================

def main():
    print("Loading data (11 SPDR sectors + SPY + IEF, total-return; ^VIX; ^IRX)...")
    df, vix, irx, avail = load_all()
    print(f"Master calendar: {df.index.min().date()} -> {df.index.max().date()}, {len(df)} rows")
    for s in ALL_SECTORS:
        fv = df[s].first_valid_index()
        print(f"  {s:6} first valid {fv.date() if fv is not None else 'N/A'}  "
              f"n_valid={int(avail[s].sum())}")
    print(f"  IEF first valid {df['IEF'].first_valid_index().date()}")
    print(f"  VIX  {vix.first_valid_index().date()} -> {vix.last_valid_index().date()}")
    print(f"  IRX  {irx.first_valid_index().date()} -> {irx.last_valid_index().date()}")

    print(run_h1(df, avail, vix, irx))
    print(run_h2(df, avail, vix, irx))
    print(run_h3(df, avail, vix, irx))
    print(run_h4(df, avail, vix, irx))

    print("\n" + "=" * 100)
    print("DONE. Module: backtest/experiments/exp_sector_capeff.py")
    print("Total trial count across H1-H4 (for orchestrator Bonferroni bookkeeping): "
          "H1<=12 + H2=2 + H3<=12 + H4<=(6+9) -> see per-section counts above.")
    print("=" * 100)


if __name__ == "__main__":
    main()
