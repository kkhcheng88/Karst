"""Deterministic calculations. No forecast, scenario probability, or rating is invented.

One dispatcher, one receipt shape. ``calculate_valuation`` picks the method named in
the input and returns ``{calculator_version, method, inputs_digest, outputs}``; the
main model, an alternative view, a sensitivity and a reverse solve all run through
that same function, so a number on the page can always be traced to the exact inputs
that produced it. No ticker, date or company identity is written here.

Scale is declared by the input (``absolute`` / ``thousands`` / ``millions``) and applies
to money *and* share counts alike, so per-share values are scale-invariant while the
reported money totals are always absolute currency units. Inputs without a declared
scale (contract 0.2 / 0.3) are absolute, exactly as before.
"""
from __future__ import annotations

import copy
from datetime import date

from .schema import ContractError, canonical, digest

VERSION = "0.3.0"
# One multiplier per declared scale; `absolute` stays an int so x * 1 is bit-identical.
SCALES = {"absolute": 1, "thousands": 1000, "millions": 1000000}
DAYS_PER_YEAR = 365
# Reverse-solve grid: enough points to see a second root, cheap enough to run per cell.
SOLVE_SAMPLES = 64
SOLVE_STEPS = 80


def _scale(inputs):
    scale = inputs.get("scale", "absolute")
    if scale not in SCALES:
        raise ContractError(f"Unknown money scale: {scale}")
    return SCALES[scale]


def _money(outputs, keys, unit):
    """Money fields are reported in absolute currency; ratios and per-share are not scaled."""
    return {key: (value * unit if key in keys else value) for key, value in outputs.items()}


def _finite(result, method):
    try:
        canonical(result)
    except ValueError as exc:
        raise ContractError(
            f"{method} produces non-finite values; inspect scale and assumptions") from exc
    return result


def _day(value, field):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{field} must be a YYYY-MM-DD date") from exc


def _years(start, end):
    return (end - start).days / DAYS_PER_YEAR


def _equity_from_bridge(enterprise, bridge):
    """Enterprise value to equity, once, for every enterprise-level method.

    ``convertibles_dilution`` may be null only when the gap is named: an unpriced
    convertible or warrant is a stated hole in the bridge, never a silent zero.
    """
    if bridge["convertibles_dilution"] is None and not bridge["unsupported_claims"]:
        raise ContractError("A null convertibles_dilution must be named in unsupported_claims")
    claims = (bridge["debt"] + bridge["minority_interest"] + bridge["redeemable_claims"]
              + (bridge["convertibles_dilution"] or 0))
    return enterprise + bridge["cash"] + bridge["nonoperating_assets"] - claims


def fcff_dcf(inputs):
    """Annual end-of-year FCFF (contract 0.2 / 0.3 meaning, unchanged).

    Cashflows are enterprise free cash flow at each full year end from the valuation
    date, in the declared scale; shares are diluted shares in that same scale.
    """
    unit = _scale(inputs)
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
    return _finite(_money(result, ("pv_explicit_fcff", "pv_terminal", "enterprise_value",
                                   "equity_value"), unit), "fcff_dcf")


def _dated_enterprise(model):
    """Dated multi-stage FCFF: explicit dated flows plus a separately normalized terminal.

    Every flow carries its own date, so a stub is simply the first, shorter period.
    ``mid_period`` discounts each flow at the midpoint between the previous boundary
    and its own date; the terminal lump is always discounted at its own date.
    """
    start = _day(model["valuation_date"], "valuation_date")
    rate, terminal = model["discount_rate"], model["terminal"]
    growth = terminal["growth"]
    if rate <= growth:
        raise ContractError("DCF discount rate must exceed terminal growth")
    if terminal["normalized_fcff"] <= 0:
        raise ContractError("Perpetuity requires positive normalized terminal FCFF")
    if model["timing"] not in ("end_of_period", "mid_period"):
        raise ContractError("timing must be end_of_period or mid_period")
    previous, pv_flows, stub_years, rows = start, 0.0, 0.0, []
    for index, flow in enumerate(model["flows"]):
        moment = _day(flow["date"], "flow date")
        if moment <= start:
            raise ContractError("A cashflow dated on or before the valuation date is past, "
                                "not forecast; drop it or restate the valuation date")
        if moment <= previous:
            raise ContractError("Cashflow dates must strictly increase")
        if flow.get("is_stub") and index:
            raise ContractError("Only the first period can be a stub")
        span_end = _years(start, moment)
        span_start = _years(start, previous)
        years = span_end if model["timing"] == "end_of_period" else (span_start + span_end) / 2
        present = flow["amount"] / (1 + rate) ** years
        pv_flows += present
        rows.append({"date": flow["date"], "years": years, "present_value": present})
        if flow.get("is_stub"):
            stub_years = span_end
        previous = moment
    terminal_date = _day(terminal["date"], "terminal date")
    if terminal_date < previous:
        raise ContractError("The terminal date cannot precede the last explicit cashflow")
    years_to_terminal = _years(start, terminal_date)
    value = terminal["normalized_fcff"] * (1 + growth) / (rate - growth)
    pv_terminal = value / (1 + rate) ** years_to_terminal
    expansion = terminal["final_expansion_fcff"]
    return {
        "pv_explicit_fcff": pv_flows,
        "pv_terminal": pv_terminal,
        "terminal_value_at_terminal_date": value,
        "enterprise_value": pv_flows + pv_terminal,
        "stub_years": stub_years,
        "years_to_terminal": years_to_terminal,
        # What the terminal assumption does to the last expansion-year cash flow: the
        # step is stated, not buried inside the perpetuity.
        "normalization_step": (terminal["normalized_fcff"] / expansion) if expansion > 0 else None,
        "discounted_flows": rows,
    }


def fcff_dcf_dated(inputs):
    unit = _scale(inputs)
    if "equity" in inputs:
        raise ContractError("fcff_dcf_dated is an enterprise method; use bridge, not equity")
    core = _dated_enterprise(inputs["model"])
    bridge = inputs["bridge"]
    equity = _equity_from_bridge(core["enterprise_value"], bridge)
    enterprise = core["enterprise_value"]
    result = {**core,
              "equity_value": equity,
              "fair_value_per_share": equity / bridge["diluted_shares"],
              "terminal_share_of_enterprise_value":
                  core["pv_terminal"] / enterprise if enterprise else None}
    result["discounted_flows"] = [{**row, "present_value": row["present_value"] * unit}
                                  for row in core["discounted_flows"]]
    return _finite(_money(result, ("pv_explicit_fcff", "pv_terminal", "enterprise_value",
                                   "equity_value", "terminal_value_at_terminal_date"), unit),
                   "fcff_dcf_dated")


def _multiple_enterprise(model):
    if model.get("multiple_basis") != "enterprise_value":
        raise ContractError("An EV/EBIT or EV/EBITDA multiple must declare "
                            "multiple_basis=enterprise_value")
    if model["metric"] not in ("ebit", "ebitda"):
        raise ContractError("ev_multiple metric must be ebit or ebitda")
    return {"metric": model["metric"], "metric_value": model["metric_value"],
            "multiple": model["multiple"],
            "enterprise_value": model["metric_value"] * model["multiple"]}


def ev_multiple(inputs):
    """Enterprise multiple with the full equity bridge. Never an equity multiple."""
    unit = _scale(inputs)
    if "equity" in inputs:
        raise ContractError("ev_multiple is an enterprise method; use bridge, not equity")
    core = _multiple_enterprise(inputs["model"])
    bridge = inputs["bridge"]
    equity = _equity_from_bridge(core["enterprise_value"], bridge)
    result = {**core, "equity_value": equity,
              "fair_value_per_share": equity / bridge["diluted_shares"]}
    return _finite(_money(result, ("metric_value", "enterprise_value", "equity_value"), unit),
                   "ev_multiple")


def forward_pe(inputs):
    """Forward P/E: an equity multiple on per-share earnings. No enterprise bridge.

    Cash and debt are already inside the earnings stream and the share count; adding a
    bridge on top of an equity multiple double counts them, so it is refused.
    """
    unit = _scale(inputs)
    if "bridge" in inputs:
        raise ContractError("forward_pe is an equity multiple; an enterprise bridge would "
                            "double count cash and debt")
    model = inputs["model"]
    if model.get("multiple_basis") != "equity":
        raise ContractError("A forward P/E must declare multiple_basis=equity")
    start = _day(model["valuation_date"], "valuation_date")
    horizon = _day(model["applies_at"], "applies_at")
    years = _years(start, horizon)
    if years < 0:
        raise ContractError("A forward multiple cannot apply before the valuation date")
    at_horizon = model["eps"] * model["multiple"]
    rate = model["discount_rate"]
    per_share = at_horizon if rate is None else at_horizon / (1 + rate) ** years
    shares = inputs["equity"]["diluted_shares"]
    result = {"eps": model["eps"], "multiple": model["multiple"],
              "value_per_share_at_horizon": at_horizon, "years_to_horizon": years,
              "discounted": rate is not None,
              "fair_value_per_share": per_share,
              "equity_value": per_share * shares}
    return _finite(_money(result, ("equity_value",), unit), "forward_pe")


def sotp(inputs):
    """Sum of the parts: each part contributes enterprise value, one bridge at the end."""
    unit = _scale(inputs)
    if "equity" in inputs:
        raise ContractError("sotp is an enterprise method; use bridge, not equity")
    parts, total = [], 0.0
    for part in inputs["parts"]:
        kind = part["kind"]
        if kind == "fcff_dcf_dated":
            core = _dated_enterprise(part["model"])
        elif kind == "ev_multiple":
            core = _multiple_enterprise(part["model"])
        else:
            raise ContractError(f"Unknown sum-of-the-parts kind: {kind}")
        stake = part["stake"]
        contribution = core["enterprise_value"] * stake
        total += contribution
        parts.append({"name": part["name"], "kind": kind, "stake": stake,
                      "enterprise_value": core["enterprise_value"] * unit,
                      "attributable_enterprise_value": contribution * unit})
    bridge = inputs["bridge"]
    equity = _equity_from_bridge(total, bridge)
    result = {"parts": parts, "enterprise_value": total, "equity_value": equity,
              "fair_value_per_share": equity / bridge["diluted_shares"]}
    return _finite(_money(result, ("enterprise_value", "equity_value"), unit), "sotp")


# The method catalog: the one place a calculation method is named. Each row says what
# it answers, the params it needs and the unit of its result; the valuation family also
# carries its function. METHODS, the MCP ``calculate`` tool and the API adapter tool are
# all read from here, so adding a method is adding one row (plus its branch in ``run``
# when it is not a valuation). For the valuation family `params` IS the calculation
# object of contract 0.4 (its `method` key may be omitted).
_ENTERPRISE_UNIT = "absolute currency units; fair_value_per_share per share"
CATALOG = {
    "fcff_dcf": {"answers": "annual end-of-year FCFF DCF, fair value per share (0.2/0.3 meaning)",
                 "needs": ("cashflows", "discount_rate", "terminal_growth", "cash",
                           "nonoperating_assets", "debt", "other_claims", "diluted_shares"),
                 "unit": _ENTERPRISE_UNIT, "valuation": fcff_dcf},
    "fcff_dcf_dated": {"answers": "dated multi-stage FCFF DCF: stub, mid/end period discounting "
                                  "and a terminal normalized apart from the last expansion year",
                       "needs": ("model", "bridge"), "unit": _ENTERPRISE_UNIT,
                       "valuation": fcff_dcf_dated},
    "forward_pe": {"answers": "forward P/E on per-share earnings; an equity multiple, so no "
                              "enterprise bridge",
                   "needs": ("model", "equity"),
                   "unit": "per share; equity_value in absolute currency units",
                   "valuation": forward_pe},
    "ev_multiple": {"answers": "EV/EBIT or EV/EBITDA with the full equity bridge",
                    "needs": ("model", "bridge"), "unit": _ENTERPRISE_UNIT,
                    "valuation": ev_multiple},
    "sotp": {"answers": "sum of the parts: enterprise value per part, one consolidated bridge",
             "needs": ("parts", "bridge"), "unit": _ENTERPRISE_UNIT, "valuation": sotp},
    "sensitivity": {"answers": "re-run one calculation with named inputs changed, both sides "
                               "in one receipt",
                    "needs": ("calculation", "changes"), "unit": "per share"},
    "solve_implied": {"answers": "what one input must be for this model to produce a target "
                                 "price; reports no solution and multiple solutions",
                      "needs": ("calculation", "target_price", "solve_for", "bounds"),
                      "unit": "the unit of the solved input"},
    "risk_reward": {"answers": "per-share and percentage risk/reward", "needs": ("plan",),
                    "unit": "per share and ratio"},
    "sma": {"answers": "simple moving average of complete bars", "needs": ("bars",),
            "unit": "price"},
    "confirmed_pivots": {"answers": "confirmed local turning points", "needs": ("bars",),
                         "unit": "price with confirmation timestamps"},
}
METHODS = {name: row["valuation"] for name, row in CATALOG.items() if "valuation" in row}


def calculate_valuation(calculation):
    """Dispatch on the declared method and return one receipt.

    ``inputs_digest`` fingerprints the exact calculation object, so a sensitivity or a
    reverse solve can be checked against the scenario it claims to belong to.
    """
    if not isinstance(calculation, dict):
        raise ContractError("A calculation must be an object with a method")
    method = calculation.get("method")
    if method not in METHODS:
        raise ContractError(f"Unknown valuation method {method!r}; available: "
                            + ", ".join(sorted(METHODS)))
    return {"calculator_version": VERSION, "method": method,
            "inputs_digest": digest(canonical(calculation)),
            "outputs": METHODS[method](calculation)}


def _set_path(target, path, value):
    """Set one existing numeric input by dotted path (``model.flows.2.amount``).

    Only existing positions are writable: a typo is an error, never a new field that
    silently changes nothing.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"A calculation input must be varied to a number: {path}")
    parts = str(path).split(".")
    for step in parts[:-1]:
        target = _step(target, step, path)
    last = parts[-1]
    if isinstance(target, list):
        key = _index(last, len(target), path)
    elif isinstance(target, dict) and last in target:
        key = last
    else:
        raise ContractError(f"Unknown calculation input path: {path}")
    current = target[key]
    if isinstance(current, bool) or not isinstance(current, (int, float)):
        # Replacing a whole model, bridge or label with a number would produce a
        # number with no model behind it. Only the leaf assumptions are variable.
        raise ContractError(f"Calculation input path {path} is not a number; only a "
                            "numeric assumption can be varied")
    target[key] = value


def _index(step, length, path):
    if not step.isdigit() or not 0 <= int(step) < length:
        raise ContractError(f"Unknown calculation input path: {path}")
    return int(step)


def _step(target, step, path):
    if isinstance(target, list):
        return target[_index(step, len(target), path)]
    if isinstance(target, dict) and step in target:
        return target[step]
    raise ContractError(f"Unknown calculation input path: {path}")


def apply_changes(calculation, changes):
    result = copy.deepcopy(calculation)
    for change in changes:
        _set_path(result, change["input_path"], change["value"])
    return result


def sensitivity(calculation, changes):
    """Vary named inputs of one calculation and report both sides through one calculator.

    ``inputs_digest`` is the unchanged calculation's: that is what ties the result to
    the scenario it was claimed for.
    """
    if not changes:
        raise ContractError("A sensitivity must change at least one input")
    base = calculate_valuation(calculation)
    after = calculate_valuation(apply_changes(calculation, changes))
    before_value = base["outputs"]["fair_value_per_share"]
    after_value = after["outputs"]["fair_value_per_share"]
    return {"calculator_version": VERSION, "method": base["method"],
            "inputs_digest": base["inputs_digest"],
            "outputs": {"changes": copy.deepcopy(list(changes)),
                        "base_fair_value_per_share": before_value,
                        "fair_value_per_share": after_value,
                        "delta_per_share": after_value - before_value,
                        "changed_inputs_digest": after["inputs_digest"],
                        "changed_outputs": after["outputs"]}}


def _residual(calculation, solve_for, value, target_price):
    trial = apply_changes(calculation, [{"input_path": solve_for, "value": value}])
    return calculate_valuation(trial)["outputs"]["fair_value_per_share"] - target_price


def solve_implied(calculation, target_price, solve_for, bounds):
    """What one input must be for this model to produce ``target_price``.

    The bounded range is sampled first, so a second root or an undefined region is
    reported rather than hidden behind whichever answer bisection happens to find.
    """
    lower, upper = bounds["lower"], bounds["upper"]
    if not lower < upper:
        raise ContractError("Reverse solve bounds must satisfy lower < upper")
    samples, undefined = [], 0
    for step in range(SOLVE_SAMPLES + 1):
        point = lower + (upper - lower) * step / SOLVE_SAMPLES
        try:
            samples.append((point, _residual(calculation, solve_for, point, target_price)))
        except ContractError:
            # An input the model cannot evaluate here (r <= g, a negative terminal):
            # that is a hole in the range, not an answer.
            samples.append((point, None))
            undefined += 1
    exact = [point for point, value in samples if value == 0]
    brackets = [(a, b) for (a, fa), (b, fb) in zip(samples, samples[1:])
                if fa is not None and fb is not None and fa * fb < 0]
    roots = [(point, point) for point in exact] + brackets
    outcome, value = "solved", None
    if not roots:
        outcome = "undefined" if undefined == len(samples) else "no_solution"
    elif len(roots) > 1:
        outcome = "multiple_solutions"
    else:
        value = _bisect(calculation, solve_for, target_price, *roots[0])
    return {"calculator_version": VERSION, "method": calculation.get("method"),
            "inputs_digest": digest(canonical(calculation)),
            "outputs": {"outcome": outcome, "value": value, "solve_for": solve_for,
                        "target_price": target_price,
                        "bounds": {"lower": lower, "upper": upper},
                        "brackets": [list(pair) for pair in roots],
                        "undefined_samples": undefined}}


def _bisect(calculation, solve_for, target_price, low, high):
    if low == high:
        return low
    f_low = _residual(calculation, solve_for, low, target_price)
    for _ in range(SOLVE_STEPS):
        middle = (low + high) / 2
        f_middle = _residual(calculation, solve_for, middle, target_price)
        if f_middle == 0:
            return middle
        if (f_low < 0) != (f_middle < 0):
            high = middle
        else:
            low, f_low = middle, f_middle
    return (low + high) / 2


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


def _reported(stored, recomputed):
    """Does the receipt the researcher recorded match what the calculator gets now?

    None means nothing was recorded. False means the stored numbers do not belong to
    this scenario — a stale or hand-written receipt, which the page must not repeat.
    """
    if not stored:
        return None
    if stored.get("inputs_digest") != recomputed["inputs_digest"]:
        return False
    claimed = (stored.get("outputs") or {}).get("fair_value_per_share")
    actual = recomputed["outputs"].get("fair_value_per_share")
    if claimed is None or actual is None:
        return claimed == actual
    return abs(claimed - actual) <= 1e-6 * max(1.0, abs(actual))


def _valuation_extras(valuation, scenarios):
    """Alternative view, sensitivities and reverse solve — same calculator, same receipts."""
    extras = {"alternative_view": None, "sensitivities": [], "implied": None}
    alternative = (valuation.get("alternative_view") or {}).get("calculation")
    if alternative:
        extras["alternative_view"] = calculate_valuation(alternative)
    for row in valuation.get("sensitivities") or []:
        calculation = scenarios.get(row["scenario"])
        if calculation is None:
            raise ContractError("A sensitivity names a scenario that has no calculation")
        receipt = sensitivity(calculation, row["changes"])
        extras["sensitivities"].append(
            {"scenario": row["scenario"], "label": row["label"], "receipt": receipt,
             "reported_matches": _reported(row.get("receipt"), receipt)})
    implied = valuation.get("implied")
    if implied:
        calculation = scenarios.get(implied["scenario"])
        if calculation is None:
            raise ContractError("A reverse solve names a scenario that has no calculation")
        receipt = solve_implied(calculation, implied["target_price"],
                                implied["solve_for"], implied["bounds"])
        extras["implied"] = {"scenario": implied["scenario"], "receipt": receipt,
                             "reported_outcome": implied.get("outcome"),
                             "reported_matches": receipt["outputs"]["outcome"] ==
                             implied.get("outcome")}
    return extras


def calculate(research, bars=None):
    """bars, when given, are this run's transient price arrays: they are charted and
    measured but never saved back into research.json (0.3). Without arrays the
    already-derived numbers in research.technical.derived are reported as they stand."""
    valuation = research["valuation"]
    scenarios = {row["name"]: row["calculation"] for row in valuation["scenarios"]}
    receipts = {name: calculate_valuation(calculation)
                for name, calculation in scenarios.items()}
    values = {name: receipt["outputs"] for name, receipt in receipts.items()}
    base = values.get("base", {}).get("fair_value_per_share")
    quote = research["market"]["price"]
    technical = research["technical"]
    factor = technical["quote_to_bar_factor"]
    views = bars if bars is not None else technical.get("views") or {}
    daily = views.get("D", [])
    ma = sma(daily) if daily else (technical.get("derived") or {}).get("sma200")
    return {
        "calculator_version": VERSION, "valuation": values,
        "valuation_receipts": receipts,
        **_valuation_extras(valuation, scenarios),
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


def run(method, params):
    """One catalog method by name. Arithmetic only: whether the inputs describe the right
    economics is the caller's problem.

    The valuation family, its sensitivities and its reverse solve all return the same
    ``receipt`` the saved research carries, so a number quoted by a model can be matched
    against the scenario it claims to come from.
    """
    if method not in CATALOG:
        raise ContractError(f"Unknown calculation method {method!r}; available: "
                            + ", ".join(sorted(CATALOG)))
    row = CATALOG[method]
    if not isinstance(params, dict):
        raise ContractError(f"{method} params must be an object")
    missing = [key for key in row["needs"] if key not in params]
    if missing:
        raise ContractError(f"{method} needs: {missing}")
    receipt = None
    if method in METHODS:
        receipt = calculate_valuation({**params, "method": method})
    elif method == "sensitivity":
        receipt = sensitivity(params["calculation"], params["changes"])
    elif method == "solve_implied":
        receipt = solve_implied(params["calculation"], params["target_price"],
                                params["solve_for"], params["bounds"])
    elif method == "risk_reward":
        result = risk_reward(params["plan"], params.get("distributions", 0))
    elif method == "sma":
        result = {"sma": sma(params["bars"], params.get("window", 200)),
                  "window": params.get("window", 200)}
    else:
        result = {"pivots": confirmed_pivots(params["bars"], params.get("width", 2))}
    if receipt is not None:
        result = receipt["outputs"]
    answer = {"method": method, "description": row["answers"], "result": result,
              "unit": row["unit"], "inputs": params, "calculator_version": VERSION}
    return answer if receipt is None else {**answer, "receipt": receipt}


# The one tool every client mounts — the MCP server and both API adapters — with its
# description and method enum read from CATALOG: a single dict in, a single dict out.
TOOL = {
    "name": "calculate",
    "description": "用同一個計算器算數:估值方法分派、敏感度、反推、R&R、SMA 與轉折。"
                   "回傳 receipt(calculator_version、method、inputs_digest、outputs),"
                   "引用數字時引 receipt,不要自己心算。可用 method:"
                   + "、".join(f"{name}（{row['answers']}）" for name, row in sorted(CATALOG.items()))
                   + "。params:估值方法的 params 就是契約 0.4 的 calculation 物件（method 可省);"
                   "sensitivity 要 {calculation, changes:[{input_path, value}]};solve_implied 要 "
                   "{calculation, target_price, solve_for, bounds:{lower, upper}}。金額與股數同用 "
                   "params.scale（absolute／thousands／millions)宣告的尺度。",
    "schema": {"type": "object", "additionalProperties": False,
               "properties": {"method": {"type": "string", "enum": sorted(CATALOG)},
                              "params": {"type": "object"}},
               "required": ["method", "params"]},
}


def run_tool(arguments):
    """``{"method": ..., "params": {...}}`` -> the ``run`` result. For tool wiring."""
    if not isinstance(arguments, dict):
        raise ContractError("calculate arguments must be an object")
    unknown = set(arguments) - {"method", "params"}
    if unknown:
        raise ContractError("Unknown calculate arguments: " + ", ".join(sorted(unknown)))
    return run(arguments.get("method"), arguments.get("params"))
