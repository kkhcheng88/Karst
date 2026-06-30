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


def simulate_csp(close, vol, gate=None, target_delta=0.20, dte_init=21, pt=0.50,
                 r=0.03, q=0.013, cost_pct=0.015, capital=50000.0):
    """Cash-secured short put, non-overlapping, single-leg (no wheel).

    Sell a ~target_delta put, dte_init trading days; close at `pt` profit (buy back
    when value <= pt*premium) or at expiry (settle intrinsic). Capital-normalized
    (contracts = capital/(K*100), i.e. fully cash-secured). NAV excludes collateral
    T-bill interest (it would earn ~r separately) to isolate the option edge.
    Returns (nav array, trades array of per-trade $ P&L).
    """
    close = np.asarray(close, float)
    vol = np.asarray(vol, float)
    n = len(close)
    nav = np.full(n, np.nan)
    trades = []
    realized = 0.0
    in_pos = False
    K = prem = 0.0
    dte = 0
    contracts = 0.0
    cp = cost_pct

    for i in range(n):
        if in_pos and i > 0:
            dte -= 1
        S = close[i]
        sig = max(vol[i] / 100.0, 1e-4)
        allowed = True if gate is None else bool(gate[i])

        if in_pos:
            V = max(K - S, 0.0) if dte <= 0 else bsm.put_price(S, K, max(dte / 252, 1e-9), r, q, sig)
            if dte <= 0 or V <= pt * prem:
                pnl = contracts * (prem - V) * 100 - contracts * 100 * (prem + V) * cp
                realized += pnl
                trades.append(pnl)
                in_pos = False
                contracts = 0.0

        if (not in_pos) and allowed and S > 0:
            T = dte_init / 252
            K = bsm.strike_for_put_delta(S, T, r, q, sig, target_delta)
            prem = bsm.put_price(S, K, T, r, q, sig)
            if prem > 0 and K > 0:
                contracts = capital / (K * 100)
                dte = dte_init
                in_pos = True

        if in_pos:
            V = bsm.put_price(S, K, max(dte / 252, 1e-9), r, q, sig)
            unreal = contracts * (prem - V) * 100
        else:
            unreal = 0.0
        nav[i] = capital + realized + unreal

    return nav, np.array(trades)


def simulate_pmcc(close, vol, gate=None, long_delta=0.80, long_dte=TD, long_roll=63,
                  short_delta=0.30, short_dte=21, short_pt=0.50,
                  r=0.03, q=0.013, cost_bps=7.0, capital=10000.0):
    """PMCC: deep-ITM long LEAP (long_delta, roll at long_roll) + 1:1 short OTM call
    (short_delta, short_dte, 50% PT). `gate` controls the long leg (whole position).
    Short strike > long strike (covered). Returns NAV array.
    """
    close = np.asarray(close, float)
    vol = np.asarray(vol, float)
    n = len(close)
    nav = np.full(n, np.nan)
    cost = cost_bps / 1e4
    cash = capital
    lin = sin = False
    lK = sK = sprem = 0.0
    ldte = sdte = 0
    lc = sc = 0.0

    for i in range(n):
        if lin and i > 0:
            ldte -= 1
        if sin and i > 0:
            sdte -= 1
        S = close[i]
        sig = max(vol[i] / 100.0, 1e-4)
        cash *= (1 + r / TD)
        allowed = True if gate is None else bool(gate[i])

        # long-leg exit (gated out or roll) -> also close the short
        if lin and ((not allowed) or ldte <= long_roll):
            lv = bsm.call_price(S, lK, max(ldte / TD, 1e-6), r, q, sig)
            cash += lc * lv * 100 * (1 - cost)
            if sin:
                sv = bsm.call_price(S, sK, max(sdte / TD, 1e-6), r, q, sig)
                cash -= sc * sv * 100 * (1 + cost)
                sin, sc = False, 0.0
            lin, lc = False, 0.0

        # long entry
        if (not lin) and allowed and cash > 0:
            T = long_dte / TD
            lK = bsm.strike_for_call_delta(S, T, r, q, sig, long_delta)
            lp = bsm.call_price(S, lK, T, r, q, sig)
            if lp > 0:
                lc = cash / (lp * 100 * (1 + cost))
                cash = 0.0
                ldte = long_dte
                lin = True

        # short leg (only while long is on)
        if lin and allowed:
            if sin:
                sv = bsm.call_price(S, sK, max(sdte / TD, 1e-6), r, q, sig)
                if sdte <= 0 or sv <= short_pt * sprem:
                    cash -= sc * sv * 100 * (1 + cost)
                    sin, sc = False, 0.0
            if not sin:
                T = short_dte / TD
                sK = bsm.strike_for_call_delta(S, T, r, q, sig, short_delta)
                sp = bsm.call_price(S, sK, T, r, q, sig)
                if sp > 0:
                    sc = lc
                    cash += sc * sp * 100 * (1 - cost)
                    sprem, sdte, sin = sp, short_dte, True

        v = cash
        if lin:
            v += lc * bsm.call_price(S, lK, max(ldte / TD, 1e-6), r, q, sig) * 100
        if sin:
            v -= sc * bsm.call_price(S, sK, max(sdte / TD, 1e-6), r, q, sig) * 100
        nav[i] = v

    return nav
