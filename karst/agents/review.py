"""Provider-neutral targeted review: one task out, one result back.

The reviewer challenges a named research version and dispute. It never returns a
second rating and never rewrites the main research; the main researcher disposes of
the challenges. Which model plays which role is configuration, not method.
"""
from __future__ import annotations

import copy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from ..packet import _private_selectors, check_packet, read_json
from ..schema import ContractError, canonical, embed_evidence_defs, schemas, validate
from .research import CONTRACT
from .staging import stage_task

LAYERS = ("L1", "L2", "L3", "L4", "L5", "L6")
SEVERITIES = ("blocking", "material", "minor")
VERDICTS = ("supports_research", "challenges_research", "inconclusive")


def _result_schema():
    contracts = schemas(CONTRACT)
    citation = {"type": "array", "minItems": 0, "items": {
        "$ref": contracts["evidence"]["$id"] + "#/$defs/citation"}}
    result = {
        "$schema": contracts["research"]["$schema"],
        "title": "Karst review result 0.3.0",
        "type": "object", "additionalProperties": False,
        "properties": {
            "research_id": copy.deepcopy(contracts["research"]["properties"]["research_id"]),
            "challenges": {"type": "array", "minItems": 0, "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "target_layer": {"enum": list(LAYERS)},
                    "claim": {"type": "string", "minLength": 1},
                    "citations": copy.deepcopy(citation),
                    "severity": {"enum": list(SEVERITIES)},
                },
                "required": ["target_layer", "claim", "citations", "severity"]}},
            "verdict_on_dispute": {
                "type": "object", "additionalProperties": False,
                "properties": {"verdict": {"enum": list(VERDICTS)},
                               "reasoning": {"type": "string", "minLength": 1},
                               "citations": copy.deepcopy(citation)},
                "required": ["verdict", "reasoning", "citations"]},
            # Same shape as a packet supplement request: the local fetcher handles it.
            "new_evidence_requests": copy.deepcopy(
                contracts["packet"]["properties"]["supplement_requests"]),
            "reviewer": {
                "type": "object", "additionalProperties": False,
                "properties": {"role": {"const": "reviewer"},
                               "execution": {"enum": ["interactive", "api"]},
                               "provider": {"type": "string", "minLength": 1},
                               "model_id": {"type": "string", "minLength": 1},
                               "prompt_version": {"type": "string", "minLength": 1}},
                "required": ["role", "execution", "provider", "model_id", "prompt_version"]},
        },
        "$defs": {},
    }
    result["required"] = sorted(result["properties"])
    return embed_evidence_defs(result, contracts)


REVIEW_RESULT_SCHEMA = _result_schema()


def validate_review(result):
    canonical(result)
    errors = sorted(Draft202012Validator(REVIEW_RESULT_SCHEMA, format_checker=FormatChecker()).iter_errors(result),
                    key=lambda error: str(list(error.absolute_path)))
    if errors:
        path = "/".join(map(str, errors[0].absolute_path)) or "<root>"
        raise ContractError(f"review/{path}: {errors[0].message}")
    _private_selectors(result)
    ids = [request["request_id"] for request in result["new_evidence_requests"]]
    if len(ids) != len(set(ids)):
        raise ContractError("Duplicate evidence request_id")
    for request in result["new_evidence_requests"]:
        if request["status"] != "pending" or request["evidence_ids"] or request["resolution"] is not None:
            raise ContractError("Reviewer requests must be pending, without evidence or resolution")
    return result


def build_review_task(research_json, dispute, evidence_ids, protocol, *, bundle, destination):
    """Stage the review task: the exact research version, the dispute, named sources."""
    if protocol.get("mode") != "review":
        raise ContractError("build_review_task needs a review protocol")
    if not isinstance(dispute, str) or not dispute.strip():
        raise ContractError("A review task needs a specific dispute")
    validate("research", research_json)
    bundle = Path(bundle)
    packet, records = read_json(bundle / "packet.json"), read_json(bundle / "evidence.json")
    selected = check_packet(packet, records, bundle)
    if research_json["packet_id"] != packet["packet_id"]:
        raise ContractError("Review must name the packet version the research used")
    wanted = list(evidence_ids)
    if len(set(wanted)) != len(wanted) or not set(wanted) <= set(packet["evidence_ids"]):
        raise ContractError("Review evidence list must contain unique usable evidence IDs")
    exported = [copy.deepcopy(selected[eid]) for eid in wanted]
    context = {"bundle_path": ".", "dispute": dispute,
               "research_id": research_json["research_id"],
               "packet_id": packet["packet_id"], "security": packet["security"],
               "as_of": packet["as_of"], "research": copy.deepcopy(research_json),
               "allowed_evidence_ids": wanted, "evidence": exported,
               "method": {"version": protocol["version"], "mode": protocol["mode"],
                          "steps": protocol["steps"], "text": protocol["text"]}}
    stage_task(bundle, exported, destination=destination, input_context=context,
               prompt_text=protocol["text"], output_schema=protocol["output_schema"],
               prompt_name="review.md")
    return context
