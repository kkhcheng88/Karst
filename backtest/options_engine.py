"""Option-position simulators built on BSM + a VIX/VXN IV path.

Captures theta (time decay) and vega (IV moves) — the risks an underlying-only
backtest misses. Fractional/continuous contracts (capital-normalized NAV) so the
equity curve is directly comparable to buy-and-hold shares regardless of price level.

Assumptions (documented, not free): constant r, constant dividend yield q, and
VIX/VXN (30-day ATM IV) used as the vol for longer-dated options — the latter
OVERSTATES vega sensitivity somewhat (30-day IV is more jumpy than 9-month IV),
so LEAP drawdowns here are, if anything, conservative-pessimistic on the vol side.
"""
from __future__ import annotations

import numpy as np

import bsm

TD = 252


def simulate_leap(close, vol, gate=None, target_delta=0.80,
                  dte_init=TD, roll_dte=63, r=0.03, q=0.013,
                  cost_bps=7.0, capital=10000.0):
    """Continuously-held deep-ITM long call LEAP program.

    close, vol: arrays (vol = VIX/VXN in % points, e.g. 17.6). gate: bool array
    (True = allowed to hold leverage) or None = always-in. Rolls at roll_dte.
    Returns NAV array (len = len(close)).
    """
    close = np.asarray(close, float)
    vol = np.asarray(vol, float)
    n = len(close)
    nav = np.full(n, np.nan)
    cost = cost_bps / 1e4

    cash = capital
    contracts = 0.0
    K = None
    dte = 0
    in_pos = False

    for i in range(n):
        if in_pos and i > 0:
            dte -= 1
        S = close[i]
        sig = max(vol[i] / 100.0, 1e-4)
        cash *= (1 + r / TD)

        allowed = True if gate is None else bool(gate[i])

        # exit (gated out, or due to roll)
        if in_pos and ((not allowed) or dte <= roll_dte):
            opt = bsm.call_price(S, K, max(dte / TD, 1e-6), r, q, sig)
            cash += contracts * opt * 100 * (1 - cost)
            contracts, in_pos = 0.0, False

        # enter / re-enter
        if (not in_pos) and allowed and cash > 0:
            T = dte_init / TD
            K = bsm.strike_for_call_delta(S, T, r, q, sig, target_delta)
            price = bsm.call_price(S, K, T, r, q, sig)
            if price > 0:
                contracts = cash / (price * 100 * (1 + cost))
                cash = 0.0
                dte = dte_init
                in_pos = True

        if in_pos:
            opt = bsm.call_price(S, K, max(dte / TD, 1e-6), r, q, sig)
            nav[i] = cash + contracts * opt * 100
        else:
            nav[i] = cash

    return nav
