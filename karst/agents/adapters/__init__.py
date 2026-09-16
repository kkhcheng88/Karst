"""API execution of a staged task: interface, budget and usage shape only.

Nothing here calls a network or a model. `run` builds the request from a task
directory and hands it to a `transport` callable supplied by the local runner
(the real SDK client, or a fake in tests). Without a transport it refuses rather
than pretending an adapter is wired.
"""
from __future__ import annotations

from pathlib import Path

from ...packet import read_json
from ...schema import ContractError

BUDGET_KEYS = ("max_output_tokens", "max_cost_usd", "max_turns")
# Unknown usage stays None; a missing number is never rounded to zero.
USAGE_KEYS = ("request_id", "started_at", "finished_at",
              "input_tokens", "output_tokens", "cost_usd")


def check_budget(budget):
    if not isinstance(budget, dict) or set(budget) != set(BUDGET_KEYS):
        raise ContractError("Budget must set exactly: " + ", ".join(BUDGET_KEYS))
    for key in BUDGET_KEYS:
        value = budget[key]
        if value is not None and not (isinstance(value, (int, float)) and value > 0):
            raise ContractError(f"Budget {key} must be a positive number or null")
    return dict(budget)


def usage_record(raw=None):
    raw = raw or {}
    unknown = set(raw) - set(USAGE_KEYS)
    if unknown:
        raise ContractError("Unknown usage fields: " + ", ".join(sorted(unknown)))
    return {key: raw.get(key) for key in USAGE_KEYS}


def run(provider, task_dir, model, budget, *, transport=None):
    """Return {provider, model_id, execution, budget, usage, result}; result is unvalidated.

    The caller validates the result with the task's own schema (research intake or
    validate_review). This layer only carries the request, the budget and the usage.
    """
    task = Path(task_dir)
    request = {"provider": provider, "model_id": model,
               "prompt": (task / "prompt.md").read_text(encoding="utf-8")
               if (task / "prompt.md").exists() else (task / "review.md").read_text(encoding="utf-8"),
               "input": read_json(task / "input.json"),
               "output_schema": read_json(task / "output.schema.json"),
               "budget": check_budget(budget)}
    if transport is None:
        raise ContractError(
            f"{provider} adapter is not wired: supply a transport; a staged task is not an API call")
    response = transport(request)
    if not isinstance(response, dict) or "result" not in response:
        raise ContractError("Transport must return {'result': ..., 'usage': {...}}")
    return {"provider": provider, "model_id": model, "execution": "api",
            "budget": request["budget"], "usage": usage_record(response.get("usage")),
            "result": response["result"]}
