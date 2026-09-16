"""OpenAI API execution — interface only; credentials and client live in the runner."""
from __future__ import annotations

from . import run as _run

PROVIDER = "openai"


def run(task_dir, model, budget, *, transport=None):
    """Same interface and same result shape as the Anthropic adapter; see that module."""
    return _run(PROVIDER, task_dir, model, budget, transport=transport)
