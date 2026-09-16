"""Deterministic calculations. No forecast, scenario probability, or rating is invented."""
from __future__ import annotations

from .schema import ContractError, canonical

VERSION = "0.2.0"


def fcff_dcf(inputs):
    """Annual end-of-year FCFF, absolute currency units and absolute diluted shares."""
    flows = inputs["cashflows"]
    rate, growth = inputs["discount_rate"], inputs["terminal_growth"]
    if rate <= growth:
        raise ContractError("DCF discount rate must exceed terminal growth")
    if flows[-1] <= 0:
        raise ContractError("Perpetuity requires positive normalized terminal FCFF")
    pv_flows = sum(flow / (1 + rate) ** year for year, flow in enumerate(flows, 1))
    terminal = flows[-1] * (1 + growth) / (rate - growth)
    pv_terminal = terminal / (1 + rate) ** len(flows)
    enterprise = pv_flows + pv_terminal
    equity = (enterprise + inputs["cash"] + inputs["nonoperating_assets"]
              - inputs["debt"] - inputs["other_claims"])
    result = {
        "pv_explicit_fcff": pv_flows,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise,
        "equity_value": equity,
        "fair_value_per_share": equity / inputs["diluted_shares"],
        "terminal_share_of_enterprise_value": pv_terminal / enterprise if enterprise else None,
    }
    try:
        canonical(result)
    except ValueError as exc:
        raise ContractError("DCF produces non-finite values; inspect scale and assumptions") from exc
    return result


def risk_reward(plan, distributions=0):
    entry, stop, target = (plan[key] for key in
                           ("entry_price", "exit_price", "target_price"))
    if None in (entry, stop, target):
        return {"available": False, "reason": "入場、退出或目標價格未定。"}
    if not stop < entry:
        raise ContractError("Long-only planned exit must be below entry")
    cost = plan["round_trip_cost_per_share"]
    risk = entry - stop + cost
    reward = target - entry + distributions - cost
    stress = plan["stress_price"]
    return {
        "available": True, "reference_price": entry, "planned_loss_per_share": risk,
        "reward_per_share": reward, "ratio": reward / risk,
        "reward_return": reward / entry, "planned_loss_return": risk / entry,
        "stress_loss_per_share": max(0, entry - stress + cost) if stress is not None else None,
    }


def sma(bars, window=200):
    closes = [bar["close"] for bar in bars if bar["complete"]]
    return sum(closes[-window:]) / window if len(closes) >= window else None


def confirmed_pivots(bars, width=2):
    """Strict unequal pivots. The confirmation timestamp is the right-hand bar close."""
    bars = [bar for bar in bars if bar["complete"]]
    result = []
    for index in range(width, len(bars) - width):
        bar = bars[index]
        neighbours = bars[index-width:index] + bars[index+1:index+width+1]
        for kind, key, compare in (("high", "high", max), ("low", "low", min)):
            threshold = compare(other[key] for other in neighbours)
            valid = bar[key] > threshold if kind == "high" else bar[key] < threshold
            if valid:
                result.append({"kind": kind, "price": bar[key], "at": bar["at"],
                               "confirmed_at": bars[index + width]["at"]})
    return result


def calculate(research, bars=None):
    """bars, when given, are this run's transient price arrays: they are charted and
    measured but never saved back into research.json (0.3). Without arrays the
    already-derived numbers in research.technical.derived are reported as they stand."""
    valuation = research["valuation"]
    values = {row["name"]: fcff_dcf(row["calculation"])
              for row in valuation["scenarios"]}
    base = values.get("base", {}).get("fair_value_per_share")
    quote = research["market"]["price"]
    technical = research["technical"]
    factor = technical["quote_to_bar_factor"]
    views = bars if bars is not None else technical.get("views") or {}
    daily = views.get("D", [])
    ma = sma(daily) if daily else (technical.get("derived") or {}).get("sma200")
    return {
        "calculator_version": VERSION, "valuation": values,
        "price_to_value_gap": 1 - quote / base if base is not None and base > 0 else None,
        "ma200": ma, "ma200_quote_basis": ma / factor if ma else None,
        "confirmed_pivots": confirmed_pivots(daily),
        "risk_reward": risk_reward(research["plan"], valuation["expected_distributions"]),
        "current_price_risk_reward": risk_reward(
            {**research["plan"], "entry_price": quote}, valuation["expected_distributions"]
        ) if research["plan"]["exit_price"] is None or
             research["plan"]["exit_price"] < quote else
             {"available": False, "reason": "現價已觸及／低於計劃退出位，需重評計劃。"},
    }
