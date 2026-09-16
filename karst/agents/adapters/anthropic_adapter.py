"""Anthropic API execution — interface only; credentials and client live in the runner."""
from __future__ import annotations

from . import run as _run

PROVIDER = "anthropic"


def run(task_dir, model, budget, *, transport=None):
    """transport(request) -> {'result': <parsed JSON>, 'usage': {...}}.

    The runner's transport owns the SDK call, the API key and retry/dedup policy;
    a job that was sent but whose result is unknown must be reconciled there, not
    re-sent from here.
    """
    return _run(PROVIDER, task_dir, model, budget, transport=transport)
