"""Minimal long/flat backtester. Transparent, look-ahead-safe.

Look-ahead safety (per distillation §20.11): the position held on bar i is decided
from signals available at bar i-1. Entries/exits therefore act on the NEXT bar.
"""
from __future__ import annotations

import numpy as np


def backtest(close, entry, exit, cost_bps: float = 1.0):
    """Long/flat. entry/exit are boolean arrays aligned to `close`.

    Returns (position, strat_returns, equity), all length len(close).
    cost_bps charged on each change in position (round-trip ≈ 2× one-way).
    """
    close = np.asarray(close, dtype="float64")
    entry = np.asarray(entry, dtype=bool)
    exit = np.asarray(exit, dtype=bool)
    n = len(close)
    pos = np.zeros(n, dtype="float64")
    in_mkt = False
    for i in range(1, n):
        if not in_mkt and entry[i - 1]:
            in_mkt = True
        elif in_mkt and exit[i - 1]:
            in_mkt = False
        pos[i] = 1.0 if in_mkt else 0.0

    ret = np.zeros(n, dtype="float64")
    ret[1:] = close[1:] / close[:-1] - 1.0
    strat = pos * ret
    turn = np.abs(np.diff(np.concatenate([[0.0], pos])))
    strat = strat - turn * (cost_bps / 1e4)
    equity = np.cumprod(1.0 + strat)
    return pos, strat, equity


def buy_hold(close):
    close = np.asarray(close, dtype="float64")
    ret = np.zeros(len(close), dtype="float64")
    ret[1:] = close[1:] / close[:-1] - 1.0
    return ret, np.cumprod(1.0 + ret)
