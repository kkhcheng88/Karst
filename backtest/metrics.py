"""Performance metrics — transparent, no framework.

All Sharpe figures are annualized (×sqrt(252)). Deflated/Probabilistic Sharpe
follow Bailey & López de Prado (2014) to penalize multiple testing — because we
WILL test several variants and the spec demands we don't fool ourselves.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import kurtosis, norm, skew

TRADING_DAYS = 252


def _clean(returns) -> np.ndarray:
    r = np.asarray(returns, dtype="float64")
    return r[~np.isnan(r)]


def cagr(equity, periods_per_year: int = TRADING_DAYS) -> float:
    eq = np.asarray(equity, dtype="float64")
    if len(eq) < 2 or eq[0] <= 0:
        return np.nan
    years = (len(eq) - 1) / periods_per_year
    return eq[-1] / eq[0] ** 1 - 1 if years <= 0 else (eq[-1] / eq[0]) ** (1 / years) - 1


def ann_sharpe(returns, periods_per_year: int = TRADING_DAYS) -> float:
    r = _clean(returns)
    if len(r) < 2 or r.std(ddof=1) == 0:
        return np.nan
    return np.sqrt(periods_per_year) * r.mean() / r.std(ddof=1)


def max_drawdown(equity) -> float:
    eq = np.asarray(equity, dtype="float64")
    if len(eq) < 2:
        return np.nan
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def probabilistic_sharpe_ratio(returns, sr_star_annual=0.0,
                               periods_per_year: int = TRADING_DAYS) -> float:
    """P(true SR > sr_star). Accounts for skew/kurtosis of returns."""
    r = _clean(returns)
    n = len(r)
    if n < 10 or r.std(ddof=1) == 0:
        return np.nan
    sr = r.mean() / r.std(ddof=1)                 # per-period
    sr_b = sr_star_annual / np.sqrt(periods_per_year)
    g3, g4 = skew(r), kurtosis(r, fisher=False)
    denom = np.sqrt(max(1 - g3 * sr + ((g4 - 1) / 4) * sr ** 2, 1e-12))
    z = (sr - sr_b) * np.sqrt(n - 1) / denom
    return float(norm.cdf(z))


def deflated_sharpe_ratio(returns, all_trial_sharpes_annual,
                          periods_per_year: int = TRADING_DAYS) -> float:
    """DSR: PSR against the expected-max Sharpe under N independent trials.

    all_trial_sharpes_annual: annualized Sharpes of EVERY variant tested (the
    multiple-testing universe). DSR > 0.95 ≈ survives multiple testing.
    """
    r = _clean(returns)
    n = len(r)
    if n < 10 or r.std(ddof=1) == 0:
        return np.nan
    trials = np.asarray(all_trial_sharpes_annual, dtype="float64")
    trials = trials[~np.isnan(trials)] / np.sqrt(periods_per_year)
    big_n = len(trials)
    if big_n < 2:
        return probabilistic_sharpe_ratio(returns, 0.0, periods_per_year)
    var_tr = np.var(trials, ddof=1)
    emc = 0.5772156649015329  # Euler–Mascheroni
    z1 = norm.ppf(1 - 1.0 / big_n)
    z2 = norm.ppf(1 - 1.0 / (big_n * np.e))
    sr_star = np.sqrt(var_tr) * ((1 - emc) * z1 + emc * z2)  # per-period
    return probabilistic_sharpe_ratio(returns, sr_star * np.sqrt(periods_per_year),
                                      periods_per_year)


def summary(strat_returns, equity, position=None) -> dict:
    out = {
        "CAGR": cagr(equity),
        "Sharpe": ann_sharpe(strat_returns),
        "MaxDD": max_drawdown(equity),
        "TotalRet": float(equity[-1] / equity[0] - 1) if len(equity) > 1 else np.nan,
    }
    if position is not None:
        pos = np.asarray(position, dtype="float64")
        out["Exposure"] = float(pos.mean())
        out["Trades"] = int(np.sum(np.diff(pos) > 0))
    return out
