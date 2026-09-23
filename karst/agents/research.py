"""Single main researcher: export one task, take back one analysis payload.

``save`` is the research intake: the one way an analysis payload becomes a stored
research version. ``intake`` is the same rules without storing.

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

from .. import calculations, scope as scope_module
from ..company_bundle import CompanyBundle
from ..packet import (_citations, _private_selectors, build_packet, check_packet,
                      check_research)
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
    # Incremental workers need the actual adopted assumptions and dates, not only
    # yesterday's headline. This is explicitly previous analysis, not a new read log.
    return {key: copy.deepcopy(previous_research[key]) for key in
            ("research_id", "created_at", *PAYLOAD_KEYS)}


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
    packet, records = CompanyBundle(bundle).working()
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


def intake(payload, *, bundle, clock, role_meta, previous_version_id=None, protocol=None,
           previous_research=None, update_scope=None, scope=None):
    """Validate one analysis payload and return a complete research.json.

    Raises ContractError without writing anything when the payload does not hold up.
    ``save`` is the same check followed by storing the version; use it to keep one.
    An update (``previous_research`` given) needs ``update_scope`` — see ``save``.
    """
    bundle = Path(bundle)
    packet, records = CompanyBundle(bundle).working()
    research, _, _ = _build(payload, packet, records, bundle, clock=clock, role_meta=role_meta,
                            previous_version_id=previous_version_id, protocol=protocol,
                            previous_research=previous_research, update_scope=update_scope,
                            scope=scope, base_version_id=previous_version_id)
    return research


def _build(payload, packet, records, bundle, *, clock, role_meta, previous_version_id=None,
           protocol=None, previous_research=None, update_scope=None, scope=None,
           base_version_id=None):
    """The intake rules, once: payload + this packet -> ``(research, selected, provenance)``.

    Nothing is read from disk but the evidence bytes the checks hash; nothing is written.
    Every rule about what an update may carry over from the previous version belongs
    here, next to the one place layers are built: the scope gate (``karst.scope``)
    decides which units are carried, and a carried layer keeps its ``assessed_at``.
    """
    protocol = protocol or get_research_protocol("update" if previous_research else "research")
    contract = packet["contract_version"]
    if contract not in SUPPORTED:
        raise ContractError(f"Single-researcher intake requires contract {SUPPORTED}")
    provenance, carried_ids = None, set()
    if previous_research:
        payload = scope_module.merge(previous_research, payload)
    _validate_payload(payload, contract)
    if previous_research:
        provenance, carried_ids = scope_module.gate(
            previous_research, payload, update_scope, scope, base_version_id=base_version_id)
        missing = sorted(carried_ids - set(packet["evidence_ids"]))
        if missing:
            raise ContractError(
                "Carried analysis cites evidence absent from this packet (" + ", ".join(missing)
                + "); prepare the packet with those sources or expand that layer with a reason")
    else:
        provenance = scope_module.initial()
    carried = {name for name, row in provenance["layers"].items() if row["status"] == "carried"}
    selected = check_packet(packet, records, bundle)
    read_ids = set(payload["read_evidence_ids"])
    if not read_ids <= set(packet["evidence_ids"]):
        raise ContractError("Read log references evidence outside packet")
    for name, layer in payload["layers"].items():
        if name not in carried and not set(layer["read_evidence_ids"]) <= read_ids:
            raise ContractError(f"{name} read log exceeds the research read log")
        if any(c["evidence_id"] not in layer["read_evidence_ids"] for c in _citations(layer)):
            raise ContractError(f"{name} cited evidence absent from its read log")
    for citation in _citations({k: v for k, v in payload.items() if k != "layers"}):
        if citation["evidence_id"] not in read_ids | carried_ids:
            raise ContractError("Cited evidence absent from the research read log")
    registered = {r["request_id"]: r for r in packet["supplement_requests"]}
    for request in payload["supplement_requests"]:
        if registered.get(request["request_id"]) != request:
            raise ContractError("Register outstanding supplement requests in a new packet before intake")
    models, mode = _models(role_meta)
    now = clock() if callable(clock) else clock
    research = {key: copy.deepcopy(payload[key]) for key in PAYLOAD_KEYS}
    if previous_research and previous_version_id != previous_research["research_id"]:
        raise ContractError("Previous research identity does not match update reference")
    for name, layer in research["layers"].items():
        old = (previous_research or {}).get("layers", {}).get(name)
        layer["assessed_at"] = old["assessed_at"] if name in carried and old else now
        provenance["layers"][name]["assessed_at"] = layer["assessed_at"]
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
    return research, list(selected.values()), provenance


def _with_requests(packet, records, payload, bundle):
    """This packet with the payload's new or reworded supplement requests registered.

    A researcher who could not read something asks for it; intake requires those
    requests to be registered. Same cutoff, same creation time, same previous packet:
    only the request list grows, so the rebuild is additive and the packet_id follows
    content. Returns the packet unchanged (same object) when there is nothing to add.
    Resolved requests never change; a pending one takes its owner's latest wording.
    """
    known = {request["request_id"] for request in packet["supplement_requests"]}
    incoming = [request for request in (payload.get("supplement_requests") or [])
                if isinstance(request, dict) and request.get("request_id")]
    merged = []
    for request in packet["supplement_requests"]:
        update = next((r for r in incoming if r["request_id"] == request["request_id"]), None)
        pending = update is not None and request.get("status") == "pending"
        merged.append(update if pending else request)
    fresh = [request for request in incoming if request["request_id"] not in known]
    if not fresh and merged == packet["supplement_requests"]:
        return packet
    return build_packet(
        records, packet["as_of"], packet["security"],
        created_at=packet["created_at"], knowledge_basis=packet["knowledge_basis"],
        previous_packet_id=packet["previous_packet_id"],
        dependencies=[dep for dep in packet["dependencies"] if dep["kind"] != "evidence"],
        supplement_requests=merged + fresh,
        pending_updates=packet["pending_updates"], root=bundle,
        contract_version=packet["contract_version"])


def save(store, bundle, payload, *, subject, role_meta, previous_version_id=None, clock,
         update_scope=None):
    """Research intake: take one analysis payload and append it as a research version.

    The caller hands over the payload and the version it builds on, and for an update
    its ``update_scope``: ``{scope_id}`` of a scope the system issued (``plan_update``),
    or ``{full_reason}`` for a declared full reassessment, plus optional ``reviewed``
    (layer -> evidence IDs read this time) and ``expansions`` (layer -> reason). The
    version records a layer provenance table beside it (``karst.scope``). Inside:
    the working packet is read once, the payload's supplement requests are registered on
    that copy, the payload is checked once against it, the calculator runs, and the store
    appends the version with the packet and evidence index it was checked against. The
    packet is written back only when requests were added and the version was stored.

    Rejected payloads leave nothing behind; a stale ``previous_version_id`` returns the
    store's conflict. Retry identity is the submitted analysis plus its frozen inputs,
    not the intake clock: an identical request after a lost response returns its version.
    """
    bundle = Path(bundle)
    company = CompanyBundle(bundle)
    packet, records = company.working()
    request = {
        "subject": subject, "previous": previous_version_id, "payload": payload,
        "inputs": packet.get("evidence_ids"), "as_of": packet.get("as_of"),
        "role_meta": role_meta,
        "method": get_research_protocol("update" if previous_version_id else "research")["version"]}
    if update_scope is not None:
        request["update_scope"] = update_scope
    request_key = digest(canonical(request))
    existing = store.get_research_request(request_key)
    if existing:
        return existing | {"idempotent_replay": True}
    registered = _with_requests(packet, records, payload, bundle)
    # Callers may pass one role record or the full model list; the research records the
    # list, the store keeps the researcher's own fields.
    roles = list(role_meta) if isinstance(role_meta, (list, tuple)) else [dict(role_meta)]
    researcher = next((r for r in roles if r.get("role") == "researcher"), roles[0])
    previous = store.get_research(previous_version_id) if previous_version_id else None
    if previous and previous["subject"] != subject:
        raise ContractError("Previous research belongs to a different subject")
    previous_research = previous["payload"] if previous else None
    scope_id = (update_scope or {}).get("scope_id") if isinstance(update_scope, dict) else None
    issued = store.get_update_scope(scope_id) if scope_id else None
    if issued and issued["subject"] != subject:
        raise ContractError("Update scope belongs to a different subject")
    research, selected, provenance = _build(
        payload, registered, records, bundle, clock=clock, role_meta=roles,
        previous_research=previous_research,
        previous_version_id=(previous_research or {}).get("research_id"),
        update_scope=update_scope, scope=issued, base_version_id=previous_version_id)
    try:
        receipt = calculations.calculate(research)
    except (ContractError, KeyError, TypeError) as exc:
        # An unavailable receipt is a stated gap, never a silently empty field.
        receipt = {"calculator_version": calculations.VERSION, "status": "unavailable",
                   "reason": f"{type(exc).__name__}: {exc}"}
    result = store.save_research_version(
        subject, research, expected_previous_version_id=previous_version_id,
        as_of=registered["as_of"], calc_receipt=receipt, role=researcher.get("role"),
        execution=researcher.get("execution"), provider=researcher.get("provider"),
        model=researcher.get("model") or researcher.get("model_id"),
        packet=registered, evidence=selected, request_key=request_key, provenance=provenance)
    if registered is not packet and not result.get("conflict"):
        company.save_working(registered)
    return result
