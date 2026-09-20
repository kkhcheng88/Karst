"""Small, reproducible screening calculations; no ratings or peer selection.

Financial amounts must share a currency and scale (e.g. USD millions). Quarter
inputs are actual group results, not ARR or forecasts. Caller retains source,
period and accounting basis beside the output in a knowledge comparison snapshot.
"""
from __future__ import annotations

import math
from datetime import date


def _number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def fundamental_ratios(*, market_cap, revenue, previous_quarter_revenue,
                       adjusted_ebitda, operating_income, debt, finance_leases,
                       cash, noncontrolling_interest=0):
    """Screening ratios. Annualizing a quarter is explicitly NOT a forecast.

    EV proxy includes drawn debt carrying values, finance leases and NCI, deducts
    unrestricted cash only. It excludes operating leases and investment SOTP;
    therefore the caller must date the balance sheet and label it a proxy.
    """
    values = dict(locals())
    for key, value in values.items():
        _number(value, key, positive=key in ("market_cap", "revenue", "previous_quarter_revenue"))
        if key in ("debt", "finance_leases", "cash", "noncontrolling_interest") and value < 0:
            raise ValueError(f"{key} cannot be negative")
    net_debt = debt + finance_leases - cash
    ev = market_cap + net_debt + noncontrolling_interest
    result = {
        "revenue_qoq_pct": (revenue / previous_quarter_revenue - 1) * 100,
        "adjusted_ebitda_margin_pct": adjusted_ebitda / revenue * 100,
        "operating_margin_pct": operating_income / revenue * 100,
        "annualized_quarter_revenue": revenue * 4,
        "ps_annualized_quarter": market_cap / (revenue * 4),
        "net_debt": net_debt,
        "enterprise_value_proxy": ev,
        "ev_annualized_quarter_sales_proxy": ev / (revenue * 4),
    }
    for key, value in result.items():
        _number(value, key)
    return result


def price_returns(bars, *, cutoff, windows=(21, 63)):
    """Same completed daily price basis; returns are price-only, not total return.

    Missing exact cutoff and unsorted/duplicate sessions fail. A partial bar or
    future bar cannot enter the comparison. Short history produces null, not zero.
    """
    end = date.fromisoformat(cutoff)
    selected = []
    previous = None
    for bar in bars:
        day = date.fromisoformat(bar["date"])
        if previous is not None and day <= previous:
            raise ValueError("Daily sessions must be strictly increasing")
        previous = day
        close = _number(bar["close"], "close", positive=True)
        if day <= end and bar.get("complete") is True:
            selected.append((day, close))
    if not selected or selected[-1][0] != end:
        raise ValueError("No completed bar at the requested cutoff")
    result = {}
    for window in windows:
        if type(window) is not int or window < 1:
            raise ValueError("Return window must be a positive number of sessions")
        result[str(window)] = (None if len(selected) <= window else {
            "from": selected[-window-1][0].isoformat(), "to": cutoff,
            "value_pct": (selected[-1][1] / selected[-window-1][1] - 1) * 100})
    return result
