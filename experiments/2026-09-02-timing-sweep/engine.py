"""KARST-145 timing-layer sweep engine.

Signals, candidate pools, event-driven daily backtest, benchmarks.
All parameters are frozen in CRITERIA.md before any result is looked at.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_YEAR = 252
LOOKBACK_HIGH = 126        # 6 months of trading days for drawdown-from-high
RSI_WINDOW = 2
VOL_WINDOW_MONTHS = 12     # trailing window for the "calmest" stock proxy


# --------------------------------------------------------------------------
# indicators
# --------------------------------------------------------------------------

def wilder_rsi(close: pd.DataFrame, window: int = RSI_WINDOW) -> pd.DataFrame:
    """Wilder-smoothed RSI on a (dates x tickers) close frame."""
    delta = close.diff()
    up = delta.clip(lower=0.0)
    dn = (-delta).clip(lower=0.0)
    roll_up = up.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    roll_dn = dn.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = roll_up / roll_dn.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    # zero average loss -> RSI 100 ; zero average gain -> RSI 0
    rsi = rsi.where(roll_dn != 0.0, 100.0)
    rsi = rsi.where(~((roll_up == 0.0) & (roll_dn == 0.0)), 50.0)
    return rsi


def weekly_rsi_daily(close: pd.DataFrame, window: int = RSI_WINDOW) -> pd.DataFrame:
    """RSI(2) computed on weekly (Friday) closes, forward-filled onto daily grid.

    A week's RSI is only knowable at that week's close, so the value is stamped
    on the week-ending date and forward-filled from there -- no look-ahead.
    """
    wk = close.resample("W-FRI").last()
    rsi_w = wilder_rsi(wk, window)
    return rsi_w.reindex(close.index, method="ffill")


def build_signals(close: pd.DataFrame) -> dict:
    """All entry/exit state matrices, aligned to `close`."""
    rsi_d = wilder_rsi(close)
    rsi_w = weekly_rsi_daily(close)
    ma20 = close.rolling(20, min_periods=20).mean()
    ma50 = close.rolling(50, min_periods=50).mean()
    above = ma20 > ma50
    golden = above & ~above.shift(1, fill_value=False)
    high6 = close.rolling(LOOKBACK_HIGH, min_periods=LOOKBACK_HIGH).max()
    dd = close / high6 - 1.0

    entries = {
        "rsi2d_lt10": rsi_d < 10.0,
        "rsi2w_lt10": rsi_w < 10.0,
        "dd_5": dd <= -0.05,
        "dd_10": dd <= -0.10,
        "dd_15": dd <= -0.15,
        "golden_cross": golden,
    }
    exits_state = {
        "rsi2d_gt90": rsi_d > 90.0,
        "death_cross": ma20 < ma50,
    }
    return {
        "entries": {k: v.fillna(False).to_numpy() for k, v in entries.items()},
        "exits_state": {k: v.fillna(False).to_numpy() for k, v in exits_state.items()},
    }


# --------------------------------------------------------------------------
# stock-selection proxies (NOT swept -- fixed by the ticket)
# --------------------------------------------------------------------------

MIN_MEMBERS = 8            # KARST-143 rule: a sector with fewer eligible names sits out
VOL_WINDOW_PRIMARY = 36    # KARST-143 vol_score(): trailing 36 monthly returns
VOL_WINDOW_FALLBACK = 24


def pool_forward_yield(fwd: pd.DataFrame) -> pd.DataFrame:
    """Proxy (a): highest forward earnings yield within each sector bucket.

    Score = earn_fwd1 / mcap, exactly the `ey_fwd1` of KARST-143 run.py.
    Higher is better. Membership filtered by joined_on/left_on.
    """
    d = fwd[fwd["month_end"].between(fwd["joined_on"], fwd["left_on"], inclusive="left")]
    d = d[(d["mcap"] > 0) & d["earn_fwd1"].notna()].copy()
    d["score"] = d["earn_fwd1"] / d["mcap"]
    d["rank_asc"] = False
    return d[["symbol", "month_end", "etf", "score", "rank_asc"]]


def pool_low_vol(monthly: pd.DataFrame) -> pd.DataFrame:
    """Proxy (b): lowest trailing monthly volatility within each sector bucket.

    KARST-143 vol_score(): stdev (ddof=1) of the trailing 36 monthly total
    returns ending at the ranking month, all 36 present; else the trailing 24,
    all present; else the name sits out. Lower is better.
    """
    d = monthly[["symbol", "month_end", "etf", "ret"]].copy().sort_values(["symbol", "month_end"])
    g = d.groupby("symbol", observed=True)["ret"]
    s36 = g.transform(lambda s: s.rolling(VOL_WINDOW_PRIMARY, min_periods=VOL_WINDOW_PRIMARY).std())
    s24 = g.transform(lambda s: s.rolling(VOL_WINDOW_FALLBACK, min_periods=VOL_WINDOW_FALLBACK).std())
    d["score"] = s36.fillna(s24)
    d = d[d["score"].notna()].copy()
    d["rank_asc"] = True
    return d[["symbol", "month_end", "etf", "score", "rank_asc"]]


def top_n_pool(scored: pd.DataFrame, n: int) -> dict:
    """month_end -> ordered list of symbols (top n per sector, best first).

    Sectors with fewer than MIN_MEMBERS eligible names that month sit out
    entirely (KARST-143 rule). Cross-sector ordering interleaves by within-sector
    rank so that filling K slots does not exhaust one sector first.
    """
    asc = bool(scored["rank_asc"].iloc[0])
    d = scored.copy()
    cnt = d.groupby(["month_end", "etf"], observed=True)["symbol"].transform("size")
    d = d[cnt >= MIN_MEMBERS]
    d = d.sort_values(["month_end", "etf", "score"], ascending=[True, True, asc])
    d = d.groupby(["month_end", "etf"], observed=True).head(n)
    d["within"] = d.groupby(["month_end", "etf"], observed=True).cumcount()
    d = d.sort_values(["month_end", "within", "score"], ascending=[True, True, asc])
    return {m: list(g["symbol"]) for m, g in d.groupby("month_end", observed=True)}


# --------------------------------------------------------------------------
# backtest
# --------------------------------------------------------------------------

def run_cell(
    close_arr: np.ndarray,
    ret_arr: np.ndarray,
    valid_arr: np.ndarray,
    col_of: dict,
    dates: pd.DatetimeIndex,
    pool_by_month: dict,
    pool_month_index: np.ndarray,
    entry_sig: np.ndarray,
    exit_key: str,
    exit_state: np.ndarray | None,
    max_hold: int,
    trail_stop: float,
    drop_out: bool,
    k_slots: int,
    spy_col: int,
    start_i: int,
):
    """One sweep cell. Signals read on day t, executed at day t+1 close.

    Returns dict of daily series and trade stats.
    """
    n_days = len(dates)
    port_ret = np.zeros(n_days)
    pick_ret = np.zeros(n_days)      # self-picked sleeve only, equal weight
    turnover = np.zeros(n_days)      # one-sided fraction of portfolio traded
    slots_filled = np.zeros(n_days)

    held: dict[int, dict] = {}       # col -> {entry_i, peak}
    n_entries = 0
    hold_days_total = 0

    month_keys = sorted(pool_by_month)
    cur_pool: set[int] = set()
    cur_order: list[int] = []

    for i in range(start_i, n_days):
        mi = pool_month_index[i]
        if mi >= 0:
            syms = pool_by_month[month_keys[mi]]
            cur_order = [col_of[s] for s in syms if s in col_of]
            cur_pool = set(cur_order)

        # ---- returns of the book carried into day i (positions set at i-1 close)
        w_pick = 1.0 / k_slots
        held_cols = list(held)
        r_day = 0.0
        for c in held_cols:
            r_day += w_pick * ret_arr[i, c]
        n_h = len(held_cols)
        cash_w = 1.0 - n_h * w_pick
        r_day += cash_w * ret_arr[i, spy_col]
        port_ret[i] = r_day
        pick_ret[i] = (sum(ret_arr[i, c] for c in held_cols) / n_h) if n_h else 0.0
        slots_filled[i] = n_h

        # peaks update on today's close
        for c in held_cols:
            px = close_arr[i, c]
            if px > held[c]["peak"]:
                held[c]["peak"] = px

        # ---- decide at close of day i, trade at close of day i+1
        if i + 1 >= n_days:
            continue

        to_exit = []
        for c in held_cols:
            st = held[c]
            if not valid_arr[i, c] or not valid_arr[i + 1, c]:
                to_exit.append(c)
                continue
            if exit_state is not None and exit_state[i, c]:
                to_exit.append(c)
                continue
            if max_hold and (i - st["entry_i"]) >= max_hold:
                to_exit.append(c)
                continue
            if trail_stop and close_arr[i, c] <= st["peak"] * (1.0 - trail_stop):
                to_exit.append(c)
                continue
            if drop_out and c not in cur_pool:
                to_exit.append(c)
                continue

        traded = 0.0
        for c in to_exit:
            hold_days_total += i - held[c]["entry_i"]
            del held[c]
            traded += w_pick

        free = k_slots - len(held)
        if free > 0:
            for c in cur_order:
                if free == 0:
                    break
                if c in held:
                    continue
                if not valid_arr[i, c] or not valid_arr[i + 1, c]:
                    continue
                if not entry_sig[i, c]:
                    continue
                held[c] = {"entry_i": i + 1, "peak": close_arr[i + 1, c]}
                traded += w_pick
                n_entries += 1
                free -= 1

        turnover[i + 1] = traded

    for c in held:
        hold_days_total += (n_days - 1) - held[c]["entry_i"]

    return {
        "port_ret": port_ret,
        "pick_ret": pick_ret,
        "turnover": turnover,
        "slots_filled": slots_filled,
        "n_entries": n_entries,
        "avg_hold_days": (hold_days_total / n_entries) if n_entries else 0.0,
    }


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------

def cagr(daily_ret: np.ndarray, n_years: float) -> float:
    growth = float(np.prod(1.0 + daily_ret))
    if growth <= 0:
        return -1.0
    return growth ** (1.0 / n_years) - 1.0


def max_drawdown(daily_ret: np.ndarray) -> float:
    nav = np.cumprod(1.0 + daily_ret)
    peak = np.maximum.accumulate(nav)
    return float((nav / peak - 1.0).min())


def apply_cost(daily_ret: np.ndarray, turnover: np.ndarray, bps: float) -> np.ndarray:
    return daily_ret - turnover * (bps / 10000.0) * 2.0
