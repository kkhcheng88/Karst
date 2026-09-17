"""Single main researcher: export one task, take back one analysis payload.

No six fragments, no sealed counter-first pass — that path stays in assemble.py for
existing 0.2 bundles. The model returns analysis only; every ID, clock, version and
model record is written here by the program under contract 0.4.0 (0.3 bundles still
come in at their own version).
"""
from __future__ import annotations

import copy
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from ..packet import (_citations, _private_selectors, check_packet, check_research,
                      read_json)
from ..schema import ContractError, canonical, digest, embed_evidence_defs, schemas, validate
from .protocol import get_research_protocol
from .staging import stage_task

CONTRACT = "0.4.0"
# 0.3 bundles are still taken in as they are: an old saved research must stay
# readable and republishable, and it is its own packet's version that decides.
SUPPORTED = ("0.3.0", "0.4.0")
# Analysis the researcher owns. Everything else in the research contract is engineering
# metadata the program fills in; the payload schema does not even offer those fields.
PAYLOAD_KEYS = ("headline", "layers", "modules", "phases", "market", "valuation",
                "technical", "plan", "coverage", "rating", "execution_state",
                "target_date", "open_questions")
ENGINEERING_KEYS = ("contract_version", "research_id", "packet_id", "previous_research_id",
                    "created_at", "mode", "strategy_version", "mandate_version",
                    "method_version", "models")
MODE_BY_EXECUTION = {"interactive": "interactive_research", "api": "api_research"}
# Staged charts are a reading aid, never a measurement: the numbers are in the JSON.
CHARTS_NOTE = ("charts/ 內的月／週／日／近期放大圖只作參考，數字一律以 charts/derived.json 為準"
               "（各均線值與方向、ATR、量比、支撐阻力區的形成與確認時點、資料截止日）。"
               "視覺判讀前用 read_chart(artifact_id) 實際開啟該圖（artifact_id 見 "
               "charts.artifacts）；只看檔名或 derived 數字不算看過圖，圖像不可用就按 L5 "
               "記「視覺未完成」及影響。圖與 JSON 都不含價格陣列。")


class Verified(dict):
    """A research object that already passed check_packet / check_research.

    It is an ordinary dict everywhere it matters (canonical JSON, the schema, the
    store), and carries one extra attribute: what exactly was verified. The saver
    re-runs the checks unless that fingerprint still matches the bundle, so the
    rule lives in one place and an injected intake — which cannot set it — is
    always verified the long way.
    """

    verified = None


def fingerprint(research, packet, records):
    """What a verification covered: this research, this packet, these exact bytes."""
    evidence = sorted((record["evidence_id"], record["artifact"]["sha256"])
                      for record in records)
    return {"research_digest": digest(canonical(research)),
            "packet_id": packet["packet_id"],
            "evidence_digest": digest(canonical(evidence)),
            "contract_version": packet["contract_version"]}


@lru_cache(maxsize=None)
def analysis_schema(contract=CONTRACT):
    if contract not in SUPPORTED:
        raise ContractError(f"Single-researcher intake requires contract {SUPPORTED}")
    contracts = schemas(contract)
    source = copy.deepcopy(contracts["research"])
    defs = source["$defs"]
    layer = defs["layer"]
    layer["properties"].pop("assessed_at")
    layer["required"] = [key for key in layer["required"] if key != "assessed_at"]
    properties = {key: copy.deepcopy(source["properties"][key]) for key in PAYLOAD_KEYS}
    # Price arrays are this run's transient input; the payload carries derived numbers only.
    properties["technical"]["properties"].pop("views")
    properties["read_evidence_ids"] = copy.deepcopy(layer["properties"]["read_evidence_ids"])
    properties["supplement_requests"] = copy.deepcopy(
        contracts["packet"]["properties"]["supplement_requests"])
    result = {"$schema": source["$schema"], "title": f"Karst research payload {contract}",
              "type": "object", "additionalProperties": False, "properties": properties,
              "required": sorted(properties), "allOf": copy.deepcopy(source["allOf"]),
              "$defs": defs}
    return embed_evidence_defs(result, contracts)


ANALYSIS_SCHEMA = analysis_schema()


def _validate_payload(payload, contract=CONTRACT):
    present = [key for key in ENGINEERING_KEYS if isinstance(payload, dict) and key in payload]
    if present:
        raise ContractError("Model payload must not carry engineering fields: " + ", ".join(present))
    canonical(payload)
    errors = sorted(Draft202012Validator(analysis_schema(contract), format_checker=FormatChecker()).iter_errors(payload),
                    key=lambda error: str(list(error.absolute_path)))
    if errors:
        path = "/".join(map(str, errors[0].absolute_path)) or "<root>"
        raise ContractError(f"payload/{path}: {errors[0].message}")
    _private_selectors(payload)
    return payload


def _previous_summary(previous_research):
    if previous_research is None:
        return None
    return {key: copy.deepcopy(previous_research[key]) for key in
            ("research_id", "created_at", "target_date", "rating", "execution_state",
             "headline", "open_questions")}


def export_task(bundle, subject, destination, protocol, previous_research=None,
                *, allowed_evidence_ids=None, charts=None):
    """Stage a NEW task directory: input.json, prompt.md, output.schema.json and sources.

    The worker gets this directory only — never the bundle, the repo or this
    conversation. Isolation is still the runner's job; this only limits what is staged.

    ``charts`` is one ``service.render_charts`` result: the PNGs and their derived
    numbers are copied into ``charts/`` so the researcher can read the day / week /
    month picture and then quote the figure rather than the pixel.
    """
    bundle = Path(bundle)
    packet, records = read_json(bundle / "packet.json"), read_json(bundle / "evidence.json")
    selected = check_packet(packet, records, bundle)
    allowed = list(allowed_evidence_ids if allowed_evidence_ids is not None else packet["evidence_ids"])
    if len(set(allowed)) != len(allowed) or not set(allowed) <= set(packet["evidence_ids"]):
        raise ContractError("Allowed read list must contain unique usable evidence IDs")
    if protocol.get("mode") not in ("research", "update"):
        raise ContractError("export_task needs a research or update protocol")
    _private_selectors(subject)
    exported = [copy.deepcopy(selected[eid]) for eid in allowed]
    context = {
        "subject": copy.deepcopy(subject), "bundle_path": ".",
        "packet_id": packet["packet_id"], "security": packet["security"],
        "as_of": packet["as_of"], "requirements": packet["requirements"],
        "pending_updates": packet["pending_updates"],
        "supplement_requests": packet["supplement_requests"],
        "diagnostics": [{key: selected[eid][key] for key in
                         ("evidence_id", "source", "kind", "status", "status_reason",
                          "known_gaps", "fetched_at")} for eid in packet["diagnostic_ids"]],
        "allowed_evidence_ids": allowed, "evidence": exported,
        # The mandate, discipline sections and scenario questions live inside the
        # protocol text; prompt.md is that same text, not a second copy of the rules.
        "method": {"version": protocol["version"], "mode": protocol["mode"],
                   "steps": protocol["steps"], "text": protocol["text"]},
        "previous_research": _previous_summary(previous_research),
    }
    extra, prompt_text = {}, protocol["text"]
    if charts:
        extra = {f"charts/{Path(path).name}": Path(path)
                 for path in charts["files"].values()}
        extra["charts/derived.json"] = canonical(charts["derived"])
        # Each artifact keeps its id, hash and cutoff, and points at its staged copy:
        # that is what read_chart resolves, and what the run records as actually seen.
        artifacts = [copy.deepcopy(artifact) | {"path": f'charts/{Path(artifact["path"]).name}'}
                     for artifact in charts.get("artifacts") or []]
        context["charts"] = {"path": "charts/", "note": CHARTS_NOTE,
                             "files": {view: f"charts/{Path(path).name}"
                                       for view, path in charts["files"].items()},
                             "artifacts": artifacts,
                             "derived": copy.deepcopy(charts["derived"])}
        prompt_text += "\n\n## 圖\n\n" + CHARTS_NOTE
    stage_task(bundle, exported, destination=destination, input_context=context,
               prompt_text=prompt_text, output_schema=protocol["output_schema"],
               extra_files=extra)
    return context


def _models(role_meta):
    models = copy.deepcopy(list(role_meta))
    researchers = [m for m in models if m.get("role") == "researcher"]
    if len(researchers) != 1:
        raise ContractError("Record exactly one researcher in role_meta")
    execution = researchers[0].get("execution")
    if execution not in MODE_BY_EXECUTION:
        raise ContractError("Researcher execution must be interactive or api")
    return models, MODE_BY_EXECUTION[execution]


def intake(payload, *, bundle, clock, role_meta, previous_version_id=None, protocol=None):
    """Validate one analysis payload and return a complete research.json.

    Raises ContractError without writing anything when the payload does not hold up.
    The result carries a ``verified`` fingerprint of what these checks covered, so
    the caller does not have to hash the same evidence a second time.
    """
    protocol = protocol or get_research_protocol("research")
    bundle = Path(bundle)
    packet, records = read_json(bundle / "packet.json"), read_json(bundle / "evidence.json")
    contract = packet["contract_version"]
    if contract not in SUPPORTED:
        raise ContractError(f"Single-researcher intake requires contract {SUPPORTED}")
    _validate_payload(payload, contract)
    selected = check_packet(packet, records, bundle)
    read_ids = set(payload["read_evidence_ids"])
    if not read_ids <= set(packet["evidence_ids"]):
        raise ContractError("Read log references evidence outside packet")
    for name, layer in payload["layers"].items():
        if not set(layer["read_evidence_ids"]) <= read_ids:
            raise ContractError(f"{name} read log exceeds the research read log")
        if any(c["evidence_id"] not in layer["read_evidence_ids"] for c in _citations(layer)):
            raise ContractError(f"{name} cited evidence absent from its read log")
    for citation in _citations({k: v for k, v in payload.items() if k != "layers"}):
        if citation["evidence_id"] not in read_ids:
            raise ContractError("Cited evidence absent from the research read log")
    registered = {r["request_id"]: r for r in packet["supplement_requests"]}
    for request in payload["supplement_requests"]:
        if registered.get(request["request_id"]) != request:
            raise ContractError("Register outstanding supplement requests in a new packet before intake")
    models, mode = _models(role_meta)
    now = clock() if callable(clock) else clock
    research = {key: copy.deepcopy(payload[key]) for key in PAYLOAD_KEYS}
    for layer in research["layers"].values():
        layer["assessed_at"] = now
    research.update({
        "contract_version": contract, "packet_id": packet["packet_id"],
        "previous_research_id": previous_version_id, "created_at": now, "mode": mode,
        "strategy_version": protocol["version"]["strategy"],
        "mandate_version": protocol["version"]["mandate"],
        "method_version": protocol["version"]["declared"] + "+" + protocol["version"]["digest"][:12],
        "models": models, "research_id": "res-pending",
    })
    research["research_id"] = "res-" + digest(canonical(research))
    validate("research", research)
    check_research(packet, research, selected, bundle)
    result = Verified(research)
    result.verified = fingerprint(research, packet, list(selected.values()))
    return result
