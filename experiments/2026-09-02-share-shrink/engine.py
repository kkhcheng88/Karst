# -*- coding: utf-8 -*-
"""KARST-148 backtest engine.

Frozen in CRITERIA.md sections 4-6:
  * signal read at the rebalance month-end close, executed at the NEXT trading
    day's close -- never same-day;
  * no timing switch of any kind (D-122);
  * weights drift with prices between quarterly rebalances;
  * a held name whose price series breaks is force-exited at that day's close and
    its weight spread equally over the survivors, cost charged;
  * cost is `bps` per side on the one-sided weight change, applied afterwards so
    one run serves every cost level.
"""
from __future__ import annotations

import numpy as np

TRADING_DAYS_YEAR = 252


def cagr(daily: np.ndarray, n_years: float) -> float:
    growth = float(np.prod(1.0 + daily))
    if growth <= 0:
        return -1.0
    return growth ** (1.0 / n_years) - 1.0


def max_drawdown(daily: np.ndarray) -> float:
    nav = np.cumprod(1.0 + daily)
    peak = np.maximum.accumulate(nav)
    return float((nav / peak - 1.0).min())


def apply_cost(daily: np.ndarray, turnover: np.ndarray, bps: float) -> np.ndarray:
    """`bps` per side on the one-sided weight change already carried in `turnover`."""
    return daily - turnover * (bps / 10000.0)


def run_paths(ret: np.ndarray, exec_idx: dict[int, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Vectorised over paths.

    ret       : (n_days, n_cols) daily returns, NaN where the name has no price
    exec_idx  : day index -> (n_paths, n_picks) integer column ids to hold from
                that day's close; -1 pads a short row.

    Returns (gross, turnover), each (n_paths, n_days).
    """
    n_days, n_cols = ret.shape
    any_day = next(iter(exec_idx.values()))
    n_paths = any_day.shape[0]
    W = np.zeros((n_paths, n_cols))
    gross = np.zeros((n_paths, n_days))
    turn = np.zeros((n_paths, n_days))

    for i in range(n_days):
        row = ret[i]
        ok = np.isfinite(row)
        rr = np.where(ok, row, 0.0)
        r_day = W @ rr
        gross[:, i] = r_day
        denom = 1.0 + r_day
        W = W * (1.0 + rr) / denom[:, None]

        bad = ~ok
        if bad.any():
            held_bad = W[:, bad]
            lost = held_bad.sum(axis=1)
            if (lost > 0).any():
                tot = W.sum(axis=1)
                W[:, bad] = 0.0
                rest = tot - lost
                scale = np.where(rest > 1e-12, tot / np.maximum(rest, 1e-12), 1.0)
                W *= scale[:, None]
                turn[:, i] += 2.0 * lost

        picks = exec_idx.get(i)
        if picks is not None:
            T = np.zeros_like(W)
            valid = picks >= 0
            n_pick = valid.sum(axis=1)
            has = n_pick > 0
            if has.any():
                rows = np.repeat(np.arange(n_paths), picks.shape[1])
                cols = picks.ravel()
                w = np.repeat(np.where(has, 1.0 / np.maximum(n_pick, 1), 0.0),
                              picks.shape[1])
                m = cols >= 0
                np.add.at(T, (rows[m], cols[m]), w[m])
            turn[:, i] += np.abs(T - W).sum(axis=1)
            W = T

    return gross, turn


def run_one(ret: np.ndarray, exec_picks: dict[int, list[int]]) -> tuple[np.ndarray, np.ndarray]:
    """Single-path convenience wrapper."""
    width = max((len(v) for v in exec_picks.values()), default=1)
    idx = {}
    for i, cols in exec_picks.items():
        a = np.full((1, width), -1, dtype=np.int64)
        a[0, :len(cols)] = cols
        idx[i] = a
    g, t = run_paths(ret, idx)
    return g[0], t[0]
