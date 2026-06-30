"""Black-Scholes (with continuous dividend yield q) — price, greeks, strike solver.

For index options we use VIX/VXN as the IV input (no options chain needed).
Time is measured in TRADING days / 252 to stay consistent with the price data
(a ~1yr LEAP ≈ 252 trading days; roll at ~63 ≈ 90 calendar days).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


def _d1d2(S, K, T, r, q, sig):
    vt = sig * np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sig * sig) * T) / vt
    return d1, d1 - vt


def call_price(S, K, T, r, q, sig):
    if T <= 0 or sig <= 0:
        return max(S - K, 0.0)
    d1, d2 = _d1d2(S, K, T, r, q, sig)
    return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def put_price(S, K, T, r, q, sig):
    if T <= 0 or sig <= 0:
        return max(K - S, 0.0)
    d1, d2 = _d1d2(S, K, T, r, q, sig)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)


def call_delta(S, K, T, r, q, sig):
    if T <= 0 or sig <= 0:
        return 1.0 if S > K else 0.0
    d1, _ = _d1d2(S, K, T, r, q, sig)
    return float(np.exp(-q * T) * norm.cdf(d1))


def put_delta(S, K, T, r, q, sig):
    if T <= 0 or sig <= 0:
        return -1.0 if S < K else 0.0
    d1, _ = _d1d2(S, K, T, r, q, sig)
    return float(-np.exp(-q * T) * norm.cdf(-d1))


def strike_for_call_delta(S, T, r, q, sig, target):
    """K such that call delta == target. Delta decreases as K rises -> bisection."""
    lo, hi = 0.2 * S, 1.5 * S
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if call_delta(S, mid, T, r, q, sig) > target:
            lo = mid          # too deep ITM (delta too high) -> raise K
        else:
            hi = mid
    return 0.5 * (lo + hi)


def strike_for_put_delta(S, T, r, q, sig, target_abs):
    """K such that |put delta| == target_abs (e.g. 0.20 for a 20-delta put)."""
    lo, hi = 0.2 * S, 1.5 * S
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if -put_delta(S, mid, T, r, q, sig) > target_abs:
            hi = mid          # too ITM (|delta| too high) -> lower K
        else:
            lo = mid
    return 0.5 * (lo + hi)
