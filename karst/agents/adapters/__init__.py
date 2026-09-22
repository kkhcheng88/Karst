"""API execution of a staged task: shared turn loop, local task tools, usage record.

The provider modules own the wire format (``request`` / ``parse`` / ``append``); this
module owns the loop, the budget, the local tools and the schema check. A
``transport`` is always injectable, so a test never touches a network, and the tools
are executed here, against the task directory only — the model gets no other file
access, no bundle and no repo.

A chart read here is a real image on the wire (an Anthropic tool_result image block,
an OpenAI ``input_image``), not a filename the model then claims to have looked at;
which image, which version and which period went out is recorded in the run.

Credentials are named by environment variable in the provider modules and are never
written into a task, a result or a usage record.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from ... import calculations
from ...fetch.common import utc_now
from ...packet import confined, read_json
from ...schema import ContractError, digest

BUDGET_KEYS = ("max_output_tokens", "max_cost_usd", "max_turns", "max_input_tokens")
DEFAULT_BUDGET = {"max_output_tokens": 16000, "max_cost_usd": None,
                  "max_turns": 12, "max_input_tokens": 400_000}
# Unknown usage stays None; a missing number is never rounded to zero. cost_usd is
# left null until a priced model table exists: an invented estimate is worse than none.
USAGE_KEYS = ("request_id", "started_at", "finished_at",
              "input_tokens", "cached_input_tokens", "output_tokens", "cost_usd")

TOOLS = (
    {"name": "list_evidence",
     "description": "列出本任務目錄內的全部來源:evidence_id、來源、種類、公開與取得時間、狀態、行數。",
     "schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "read_evidence",
     "description": "按 evidence_id 逐行讀一份已登記的原文,回 L<起>-L<迄> 定位供引用。",
     "schema": {"type": "object", "additionalProperties": False,
                "properties": {"evidence_id": {"type": "string"},
                               "offset": {"type": "integer", "minimum": 0},
                               "limit": {"type": "integer", "minimum": 1}},
                "required": ["evidence_id"]}},
    {"name": "read_chart",
     "description": "按 artifact_id 開啟本任務已登記的圖(PNG),回真正圖像內容供視覺判讀;"
                    "清單在 input.json 的 charts.artifacts,精確數字在 charts/derived.json。",
     "schema": {"type": "object", "additionalProperties": False,
                "properties": {"artifact_id": {"type": "string"}},
                "required": ["artifact_id"]}},
    {"name": calculations.TOOL["name"], "description": calculations.TOOL["description"],
     "schema": calculations.TOOL["schema"]},
)
# A tool that cannot do anything for this task is not offered: a task with no charts
# staged would otherwise advertise a reading the worker can never actually make.
CHART_TOOL = "read_chart"


def tools_for(task):
    """The tools this particular task can honestly offer."""
    charts = (task["input"].get("charts") or {}).get("artifacts")
    return [tool for tool in TOOLS if tool["name"] != CHART_TOOL or charts]


class ResultUnknown(ContractError):
    """A request was sent but its outcome is unknown.

    The caller records the job as needs_check and reconciles it by hand; it never
    re-sends, because a second paid call may duplicate one that actually ran.
    """


def check_budget(budget):
    if not isinstance(budget, dict) or set(budget) != set(BUDGET_KEYS):
        raise ContractError("Budget must set exactly: " + ", ".join(BUDGET_KEYS))
    for key in BUDGET_KEYS:
        value = budget[key]
        if value is not None and not (isinstance(value, (int, float)) and value > 0):
            raise ContractError(f"Budget {key} must be a positive number or null")
    if budget["max_turns"] is None:
        raise ContractError("Budget max_turns must be a positive number")
    return dict(budget)


def usage_record(raw=None):
    raw = raw or {}
    unknown = set(raw) - set(USAGE_KEYS)
    if unknown:
        raise ContractError("Unknown usage fields: " + ", ".join(sorted(unknown)))
    return {key: raw.get(key) for key in USAGE_KEYS}


def load_task(task_dir):
    """Read the staged task: the prompt, its input and the schema its result must match."""
    task = Path(task_dir)
    prompt = task / ("prompt.md" if (task / "prompt.md").exists() else "review.md")
    if not prompt.exists():
        raise ContractError(f"Task directory has no prompt.md or review.md: {task}")
    return {"dir": task, "prompt": prompt.read_text(encoding="utf-8"),
            "input": read_json(task / "input.json"),
            "output_schema": read_json(task / "output.schema.json")}


class TaskEvidence:
    """The tools, executed locally over ONE task directory. No bundle, no network."""

    def __init__(self, task_dir):
        self.root = Path(task_dir)
        staged = load_task(task_dir)["input"]
        self.records = staged["evidence"]
        self.charts = (staged.get("charts") or {}).get("artifacts") or []

    def _lines(self, record):
        data = confined(self.root, record["artifact"]["path"]).read_bytes()
        try:
            return data.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            return None

    def listing(self):
        rows = []
        for record in self.records:
            lines = self._lines(record)
            rows.append({key: record[key] for key in
                         ("evidence_id", "source", "kind", "status", "published_at",
                          "fetched_at", "truncated", "source_url")}
                        | {"total_lines": None if lines is None else len(lines),
                           "media_type": record["media_type"]})
        return rows

    def read(self, evidence_id, offset=0, limit=200):
        record = next((r for r in self.records if r["evidence_id"] == evidence_id), None)
        if record is None:
            raise ContractError(f"Evidence is not staged with this task: {evidence_id}")
        if not isinstance(offset, int) or offset < 0 or not isinstance(limit, int) or limit <= 0:
            raise ContractError("offset must be >= 0 and limit > 0")
        lines = self._lines(record)
        if lines is None:
            return {"evidence_id": evidence_id, "binary": True,
                    "media_type": record["media_type"],
                    "note": "Artifact is not UTF-8 text; it cannot be read by line."}
        window = lines[offset:offset + limit]
        start = offset + 1 if window else None
        end = offset + len(window) if window else None
        return {"evidence_id": evidence_id, "total_lines": len(lines),
                "locator": f"L{start}-L{end}" if window else None,
                "has_more": offset + len(window) < len(lines),
                "text": "\n".join(window)}

    def chart(self, artifact_id):
        """One staged chart as real image bytes, checked against its registered hash.

        The image travels in ``image``; the caller lifts it out and puts it on the
        wire in the provider's own image format. What stays in the text is identity:
        which artifact, which period, which cutoff, which source series.
        """
        artifact = next((c for c in self.charts if c["artifact_id"] == artifact_id), None)
        if artifact is None:
            raise ContractError(
                f"Chart is not staged with this task: {artifact_id}. Staged charts: "
                + ", ".join(f'{c["view"]}={c["artifact_id"]}' for c in self.charts))
        data = confined(self.root, artifact["path"]).read_bytes()
        if len(data) != artifact["bytes"] or digest(data) != artifact["sha256"]:
            raise ContractError(f"Staged chart {artifact_id} does not match its registered hash")
        identity = {key: artifact.get(key) for key in
                    ("artifact_id", "view", "label", "period", "bars_as_of", "drawn_from",
                     "drawn_to", "sha256", "bytes", "source_evidence_id")}
        return identity | {"note": "圖已送出;精確數字讀 charts/derived.json。",
                           "image": {"media_type": artifact.get("media_type", "image/png"),
                                     "data": base64.b64encode(data).decode("ascii"),
                                     "identity": identity}}

    def call(self, name, arguments):
        arguments = arguments or {}
        if name == "list_evidence":
            return self.listing()
        if name == "read_evidence":
            return self.read(arguments.get("evidence_id"), arguments.get("offset", 0),
                             arguments.get("limit", 200))
        if name == "read_chart":
            return self.chart(arguments.get("artifact_id"))
        if name == "calculate":
            return calculations.run_tool(arguments)
        raise ContractError(f"Unknown tool: {name}")


def opening(task):
    """The one user message: the task input plus what the tools do and what to return."""
    tools = [tool["name"] for tool in tools_for(task)]
    charts = ("read_chart(artifact_id) 開圖,回真正圖像;input.json 的 charts.artifacts 列出"
              "各週期的 artifact_id,視覺判讀前必須實際開啟,精確數字仍讀 charts/derived.json。"
              if CHART_TOOL in tools else
              "本任務沒有圖像,視覺判讀請寫明未完成,不要從數字倒推圖形。")
    return "\n\n".join([
        "# 任務輸入(input.json)",
        json.dumps(task["input"], ensure_ascii=False, indent=1),
        "# 可用工具",
        "list_evidence() 列出本任務的來源;read_evidence(evidence_id, offset, limit) 按行讀原文;"
        "calculate(method, params) 做確定性計算。" + charts
        + "只有這幾個工具,只讀本任務目錄內已登記的來源;沒有其他檔案、網絡或帳戶入口。"
        "引用時用 read_evidence 回的 L<起>-L<迄> 定位。",
        "# 輸出",
        "讀完所需原文後,最後一則訊息只輸出一個 JSON 物件,符合以下 schema,不要加說明文字:",
        json.dumps(task["output_schema"], ensure_ascii=False),
    ])


def parse_result(text, schema):
    """The final text must be one JSON object that the task's own schema accepts."""
    body = (text or "").strip()
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end <= start:
        raise ContractError("Model returned no JSON object as its result")
    try:
        result = json.loads(body[start:end + 1])
    except ValueError as exc:
        raise ContractError(f"Model result is not valid JSON: {exc}") from exc
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(result),
                    key=lambda error: str(list(error.absolute_path)))
    if errors:
        path = "/".join(map(str, errors[0].absolute_path)) or "<root>"
        raise ContractError(f"result/{path}: {errors[0].message}")
    return result


def _tool_results(evidence, calls):
    """Run the calls locally. An ``image`` in a result is lifted out of the text and
    handed to the provider module, which puts it on the wire as image content."""
    results = []
    for call in calls:
        try:
            content = evidence.call(call["name"], call["input"])
            failed = False
        except (ContractError, KeyError, TypeError, ValueError, OSError) as exc:
            content, failed = {"error": f"{type(exc).__name__}: {exc}"}, True
        image = content.pop("image", None) if isinstance(content, dict) else None
        results.append({"id": call["id"], "name": call["name"], "is_error": failed,
                        "content": json.dumps(content, ensure_ascii=False, default=str),
                        "image": image})
    return results


def run_task(wire, task_dir, model, budget=None, *, transport):
    """Drive one staged task to a validated result.

    Returns {provider, model_id, execution, budget, usage, images_sent, result}.
    ``images_sent`` is the record of which chart, in which version and for which
    period actually went to the model — a PNG in a directory proves nothing. Raises
    ``ResultUnknown`` when a request was sent and its outcome is unknown, and a plain
    ``ContractError`` when nothing was sent or the returned result does not hold up.
    """
    task = load_task(task_dir)
    budget = check_budget({**DEFAULT_BUDGET, **dict(budget or {})})
    if transport is None:
        raise ContractError(f"{wire.PROVIDER} adapter is not wired: supply a transport")
    evidence = TaskEvidence(task_dir)
    started = utc_now()
    messages = [{"role": "user", "content": opening(task)}]
    totals = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    images, request_id, turn = [], None, None
    for index in range(int(budget["max_turns"])):
        request = wire.request(task, messages, model, budget)
        try:
            response = transport(request)
        except Exception as exc:  # noqa: BLE001 - sent, outcome unknown: never auto-resend
            raise ResultUnknown(
                f"{wire.PROVIDER} request was sent and its outcome is unknown "
                f"({type(exc).__name__}: {exc}); reconcile this job by hand") from exc
        turn = wire.parse(response)
        request_id = turn.get("request_id") or request_id
        for key in totals:
            totals[key] += turn["usage"].get(key) or 0
        if totals["input_tokens"] > budget["max_input_tokens"]:
            raise ContractError(
                f"Input token budget exhausted ({totals['input_tokens']} > "
                f"{budget['max_input_tokens']}); no result was produced")
        if not turn["calls"]:
            break
        results = _tool_results(evidence, turn["calls"])
        images += [dict(result["image"]["identity"], turn=index + 1, sent_at=utc_now())
                   for result in results if result.get("image")]
        messages = wire.append(messages, turn, results)
    else:
        raise ContractError(f"Turn limit reached ({budget['max_turns']}) before a result "
                            "was returned; raise max_turns or narrow the task")
    # The task keeps its own record of what was actually put in front of the model.
    # An empty list means the run saw no image, which is different from never running.
    try:
        (Path(task_dir) / "images_sent.json").write_text(
            json.dumps({"provider": wire.PROVIDER, "model_id": model, "images": images},
                       ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:  # a paid run is not failed by a record that could not be written
        pass
    return {"provider": wire.PROVIDER, "model_id": model, "execution": "api",
            "budget": budget, "images_sent": images,
            "usage": usage_record({**totals, "request_id": request_id, "started_at": started,
                                   "finished_at": utc_now(), "cost_usd": None}),
            "result": parse_result(turn["text"], task["output_schema"])}
