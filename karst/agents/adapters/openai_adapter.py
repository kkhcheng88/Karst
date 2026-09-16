"""OpenAI Responses API execution of a staged task — same shape as the Anthropic adapter.

Wire format only: the turn loop, the two local tools, the budget and the schema check
live in ``adapters/__init__.py``. The API key is referenced by the name
``OPENAI_API_KEY`` (repo-root ``.env`` or the environment) and never written into a
task, a result or a usage record.
"""
from __future__ import annotations

import json
import os
import sys

from ...fetch.common import load_env_file
from ...schema import ContractError
from . import TOOLS, run_task

PROVIDER = "openai"
API_KEY_ENV = "OPENAI_API_KEY"
ENDPOINT = "https://api.openai.com/v1/responses"
API_TOOLS = [{"type": "function", "name": tool["name"], "description": tool["description"],
              "parameters": tool["schema"]} for tool in TOOLS]


def request(task, messages, model, budget):
    return {"model": model, "max_output_tokens": int(budget["max_output_tokens"]),
            "instructions": task["prompt"], "tools": API_TOOLS, "input": messages}


def parse(response):
    output = response.get("output") or []
    usage = response.get("usage") or {}
    calls, text = [], []
    for item in output:
        if item.get("type") == "function_call":
            arguments = item.get("arguments")
            try:
                parsed = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
            except ValueError:
                parsed = {}
            calls.append({"id": item.get("call_id") or item.get("id"),
                          "name": item.get("name"), "input": parsed})
        elif item.get("type") == "message":
            text += [part.get("text") or "" for part in (item.get("content") or [])
                     if part.get("type") == "output_text"]
    return {"raw": output, "calls": calls, "text": "\n".join(text),
            "request_id": response.get("id"),
            "usage": {"input_tokens": usage.get("input_tokens"),
                      "cached_input_tokens": (usage.get("input_tokens_details") or {}).get("cached_tokens"),
                      "output_tokens": usage.get("output_tokens")}}


def append(messages, turn, results):
    return messages + list(turn["raw"]) + [
        {"type": "function_call_output", "call_id": result["id"], "output": result["content"]}
        for result in results]


def http_transport(environ=None, post=None):
    """Default transport: one Responses call per turn over httpx."""
    environ = os.environ if environ is None else environ
    if post is None:
        if environ is os.environ:
            load_env_file()
        key = (environ.get(API_KEY_ENV) or "").strip()
        if not key:
            raise ContractError(f"{PROVIDER} adapter needs {API_KEY_ENV} "
                                "(repo-root .env or the environment); no call was made")
        import httpx  # noqa: PLC0415 - imported only when a real call is wanted

        def post(payload):  # noqa: F811 - the injected hook and the default share one name
            response = httpx.post(ENDPOINT, json=payload, timeout=600.0,
                                  headers={"Authorization": f"Bearer {key}",
                                           "Content-Type": "application/json"})
            response.raise_for_status()
            return response.json()

    return post


def run(task_dir, model, budget=None, *, transport=None, environ=None, post=None):
    """Run a staged task through the Responses API (or an injected transport)."""
    return run_task(sys.modules[__name__], task_dir, model, budget,
                    transport=transport or http_transport(environ, post))
