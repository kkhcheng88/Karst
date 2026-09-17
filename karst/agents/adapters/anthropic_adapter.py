"""Anthropic Messages API execution of a staged task.

Wire format only: the turn loop, the two local tools, the budget and the schema
check live in ``adapters/__init__.py``. The API key is referenced by the name
``ANTHROPIC_API_KEY`` (repo-root ``.env`` or the environment) and never written
into a task, a result or a usage record.
"""
from __future__ import annotations

import os
import sys

from ...fetch.common import load_env_file
from ...schema import ContractError
from . import run_task, tools_for

PROVIDER = "anthropic"
API_KEY_ENV = "ANTHROPIC_API_KEY"


def api_tools(task):
    return [{"name": tool["name"], "description": tool["description"],
             "input_schema": tool["schema"]} for tool in tools_for(task)]


def request(task, messages, model, budget):
    return {"model": model, "max_tokens": int(budget["max_output_tokens"]),
            "system": task["prompt"], "tools": api_tools(task), "messages": messages}


def parse(response):
    content = response.get("content") or []
    usage = response.get("usage") or {}
    return {
        "raw": content,
        "calls": [{"id": block["id"], "name": block["name"], "input": block.get("input") or {}}
                  for block in content if block.get("type") == "tool_use"],
        "text": "\n".join(block.get("text") or "" for block in content
                          if block.get("type") == "text"),
        "request_id": response.get("id"),
        "usage": {"input_tokens": usage.get("input_tokens"),
                  "cached_input_tokens": usage.get("cache_read_input_tokens"),
                  "output_tokens": usage.get("output_tokens")},
    }


def _content(result):
    """A tool result's content. An image goes back as a real image block inside the
    tool_result — the model sees the picture, not a path it could only pretend to read."""
    if not result.get("image"):
        return result["content"]
    return [{"type": "text", "text": result["content"]},
            {"type": "image", "source": {"type": "base64",
                                         "media_type": result["image"]["media_type"],
                                         "data": result["image"]["data"]}}]


def append(messages, turn, results):
    return messages + [
        {"role": "assistant", "content": turn["raw"]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": result["id"],
                                      "content": _content(result),
                                      "is_error": result["is_error"]} for result in results]},
    ]


def sdk_transport(environ=None, client=None):
    """Default transport: one Messages call per turn, returned as a plain dict."""
    environ = os.environ if environ is None else environ
    if client is None:
        if environ is os.environ:
            load_env_file()
        key = (environ.get(API_KEY_ENV) or "").strip()
        if not key:
            raise ContractError(f"{PROVIDER} adapter needs {API_KEY_ENV} "
                                "(repo-root .env or the environment); no call was made")
        import anthropic  # noqa: PLC0415 - imported only when a real call is wanted

        client = anthropic.Anthropic(api_key=key)

    def send(payload):
        return client.messages.create(**payload).to_dict()

    return send


def run(task_dir, model, budget=None, *, transport=None, environ=None, client=None):
    """Run a staged task through the Messages API (or an injected transport)."""
    return run_task(sys.modules[__name__], task_dir, model, budget,
                    transport=transport or sdk_transport(environ, client))
