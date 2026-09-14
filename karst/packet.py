"""File inputs and additive evidence requests, shared by replay and future adapters."""
from __future__ import annotations

import copy
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from .schema import ContractError, decode, digest, validate


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def confined(root, relative):
    path = PurePosixPath(relative)
    if (path.is_absolute() or "\\" in relative or ":" in relative
            or any(part in ("", ".", "..") for part in relative.split("/"))):
        raise ContractError(f"Artifact must be a clean relative path: {relative}")
    root = Path(root).resolve()
    target = root.joinpath(*path.parts).resolve()
    if not target.is_relative_to(root):
        raise ContractError("Artifact escaped bundle root (including symlinks)")
    return target


def read_json(path):
    return decode(Path(path).read_bytes())


def _private_selectors(value):
    forbidden = {"accountid", "accountnumber", "accountno", "portfolioid",
                 "costbasis", "buyingpower", "privatepositions", "orderid", "pnl",
                 "apikey", "accesstoken", "authorization", "password", "secret"}
    if isinstance(value, dict):
        for key, child in value.items():
            if re.sub(r"[^a-z0-9]", "", key.lower()) in forbidden:
                raise ContractError(f"Private account selector is not allowed: {key}")
            _private_selectors(child)
    elif isinstance(value, list):
        for child in value:
            _private_selectors(child)


def check_packet(packet, records, root):
    validate("packet", packet)
    if instant(packet["created_at"]) < instant(packet["as_of"]):
        raise ContractError("Packet cannot be created before its data cutoff")
    index = {}
    for record in records:
        validate("evidence", record)
        if record["evidence_id"] in index:
            raise ContractError("Duplicate evidence_id")
        _private_selectors(record["params"])
        index[record["evidence_id"]] = record
    selected = {}
    for eid in packet["evidence_ids"]:
        if eid not in index:
            raise ContractError(f"Unregistered evidence: {eid}")
        record = index[eid]
        for field in ("published_at", "data_as_of"):
            if record[field] and instant(record[field]) > instant(packet["as_of"]):
                raise ContractError(f"Evidence {eid}/{field} is after cutoff")
        if instant(record["fetched_at"]) > instant(packet["created_at"]):
            raise ContractError("Evidence was fetched after packet creation")
        if packet["knowledge_basis"] == "system_observed":
            if instant(record["fetched_at"]) > instant(packet["as_of"]):
                raise ContractError("Evidence was not observed by system cutoff")
        elif record["published_at"] is None:
            raise ContractError("Public-as-of replay needs known publication time")
        artifact = record["artifact"]
        data = confined(root, artifact["path"]).read_bytes()
        if len(data) != artifact["bytes"] or digest(data) != artifact["sha256"]:
            raise ContractError(f"Evidence content hash/size mismatch: {eid}")
        selected[eid] = record
    for requirement in packet["requirements"]:
        if not set(requirement["evidence_ids"]) <= selected.keys():
            raise ContractError("Requirement references evidence outside packet")
        if requirement["status"] in ("available", "partial") and not requirement["evidence_ids"]:
            raise ContractError("Available requirement needs registered evidence")
        if requirement["status"] == "available" and any(
                selected[eid]["truncated"] for eid in requirement["evidence_ids"]):
            raise ContractError("Truncated source cannot satisfy a full requirement")
        if any(selected[eid]["kind"] != requirement["kind"] for eid in requirement["evidence_ids"]):
            raise ContractError("Requirement kind differs from referenced source")
        if requirement["status"] in ("missing", "not_applicable") and requirement["evidence_ids"]:
            raise ContractError("Missing/not applicable requirement cannot claim available sources")
    if not any(r["kind"] == "transcript" for r in packet["requirements"]):
        raise ContractError("Packet must explicitly report transcript availability")
    for request in packet["supplement_requests"]:
        if not set(request["evidence_ids"]) <= selected.keys():
            raise ContractError("Supplement references evidence outside packet")
        if request["status"] == "fulfilled" and not request["evidence_ids"]:
            raise ContractError("Fulfilled supplement must register evidence")
        if request["status"] != "pending" and not request["resolution"]:
            raise ContractError("Resolved supplement needs a resolution")
        if request["status"] != "fulfilled" and request["evidence_ids"]:
            raise ContractError("Only fulfilled supplements can attach evidence")
    request_ids = [item["request_id"] for item in packet["supplement_requests"]]
    if len(request_ids) != len(set(request_ids)):
        raise ContractError("Duplicate supplement request_id")
    for dep in packet["dependencies"]:
        if dep["kind"] == "evidence":
            if dep["id"] not in selected or selected[dep["id"]]["source_version"] != dep["version"]:
                raise ContractError("Evidence dependency version mismatch")
    return selected


def add_request(packet, request):
    """Never mutate an input packet; a pending request does not claim new evidence."""
    if request.get("status") != "pending" or request.get("evidence_ids") or request.get("resolution") is not None:
        raise ContractError("New supplement must be pending without evidence or resolution")
    new = copy.deepcopy(packet)
    new["previous_packet_id"] = packet["packet_id"]
    new["packet_id"] = "packet-" + uuid4().hex
    new["supplement_requests"].append(request)
    validate("packet", new)
    return new


def resolve_request(packet, request_id, evidence_ids, *, resolution,
                    created_at, as_of=None, unavailable=False):
    """Local adapter registers records first, then resolves a request in a new packet."""
    new = copy.deepcopy(packet)
    matches = [item for item in new["supplement_requests"] if item["request_id"] == request_id]
    if len(matches) != 1 or matches[0]["status"] != "pending":
        raise ContractError("Exactly one pending request is required")
    if unavailable and evidence_ids:
        raise ContractError("Unavailable result cannot attach evidence")
    if not unavailable and not evidence_ids:
        raise ContractError("A fulfilled request requires evidence")
    if instant(created_at) < instant(packet["created_at"]):
        raise ContractError("Supplement creation cannot move backwards")
    new["previous_packet_id"] = packet["packet_id"]
    new["packet_id"] = "packet-" + uuid4().hex
    new["created_at"] = created_at
    if as_of is not None:
        if instant(as_of) < instant(packet["as_of"]):
            raise ContractError("Supplement cutoff cannot move backwards")
        new["as_of"] = as_of
    new["evidence_ids"] = list(dict.fromkeys(new["evidence_ids"] + evidence_ids))
    matches[0].update(status="unavailable" if unavailable else "fulfilled",
                      evidence_ids=list(evidence_ids), resolution=resolution)
    validate("packet", new)
    return new


def _citations(value):
    if isinstance(value, dict):
        if "citations" in value:
            yield from value["citations"]
        for key, child in value.items():
            if key != "citations":
                yield from _citations(child)
    elif isinstance(value, list):
        for child in value:
            yield from _citations(child)


def check_research(packet, research, selected, root):
    validate("research", research)
    if research["packet_id"] != packet["packet_id"]:
        raise ContractError("Research must use the exact packet version")
    if instant(research["created_at"]) < instant(packet["created_at"]):
        raise ContractError("Research precedes its packet")
    if research["target_date"] < packet["as_of"][:10]:
        raise ContractError("Target date precedes cutoff")
    if research["valuation"]["valuation_date"] > packet["as_of"][:10]:
        raise ContractError("Intrinsic valuation date is after cutoff")
    if instant(research["market"]["at"]) > instant(packet["as_of"]):
        raise ContractError("Market quote is after cutoff")
    currency = packet["security"]["currency"]
    if research["market"]["currency"] != currency:
        raise ContractError("Quote currency differs from security")
    if research["mode"] != "synthetic_demo" and any(
            record["provenance"] == "synthetic" for record in selected.values()):
        raise ContractError("Synthetic evidence requires synthetic_demo mode")
    if research["coverage"] == "complete":
        if packet["pending_updates"] or any(r["status"] == "pending" for r in packet["supplement_requests"]):
            raise ContractError("Complete coverage cannot hide pending evidence")
        if any(r["status"] in ("partial", "missing") for r in packet["requirements"]):
            raise ContractError("Complete coverage contradicts missing requirements")
    for section in research["layers"].values():
        if not set(section["read_evidence_ids"]) <= selected.keys():
            raise ContractError("Read log references evidence outside packet")
        if instant(section["assessed_at"]) > instant(research["created_at"]):
            raise ContractError("Layer assessed after research creation")
    transcript_ids = {eid for r in packet["requirements"] if r["kind"] == "transcript"
                      for eid in r["evidence_ids"]}
    if not transcript_ids <= set(research["layers"]["L3"]["read_evidence_ids"]):
        raise ContractError("Fundamentals must record reading supplied transcripts")
    for citation in _citations(research):
        if citation["evidence_id"] not in selected:
            raise ContractError("Citation references evidence outside packet")
        locator = citation["locator"]
        match = re.fullmatch(r"L(\d+)(?:-L(\d+))?", locator)
        if match:
            data = confined(root, selected[citation["evidence_id"]]["artifact"]["path"]).read_bytes()
            try:
                length = len(data.decode("utf-8").splitlines())
            except UnicodeDecodeError as exc:
                raise ContractError("Line locator needs a UTF-8 text artifact") from exc
            start, end = int(match[1]), int(match[2] or match[1])
            if not 1 <= start <= end <= length:
                raise ContractError("Citation line range is outside source")
    names = [row["name"] for row in research["valuation"]["scenarios"]]
    if names and set(names) != {"bear", "base", "bull"}:
        raise ContractError("DCF scenarios must contain bear, base and bull exactly once")
    target_names = [row["name"] for row in research["valuation"]["target_prices"]]
    if len(target_names) != len(set(target_names)):
        raise ContractError("Duplicate target scenario")
    for row in research["valuation"]["scenarios"]:
        if row["calculation"]["currency"] != currency:
            raise ContractError("Valuation currency differs from security")
    for bars in research["technical"]["views"].values():
        previous = None
        for bar in bars:
            at = instant(bar["at"])
            if at > instant(packet["as_of"]):
                raise ContractError("Price bar is after cutoff")
            if previous is not None and at <= previous:
                raise ContractError("Bars must have unique increasing timestamps")
            if not bar["low"] <= min(bar["open"], bar["close"]) <= max(bar["open"], bar["close"]) <= bar["high"]:
                raise ContractError("OHLC range is inconsistent")
            previous = at
    for level in research["technical"]["key_levels"]:
        if level["lower"] > level["upper"] or instant(level["confirmed_at"]) > instant(packet["as_of"]):
            raise ContractError("Key level is inverted or not yet confirmed")
    for phase in research["phases"]:
        if phase["status"] == "confirmed" and phase["confirmed_at"] is None:
            raise ContractError("Confirmed phase needs a confirmation timestamp")
        if phase["confirmed_at"] and instant(phase["confirmed_at"]) > instant(packet["as_of"]):
            raise ContractError("Phase confirmation is after cutoff")
    if research["technical"]["price_basis"] == "raw" and research["technical"]["quote_to_bar_factor"] != 1:
        raise ContractError("Raw bars require quote_to_bar_factor=1")
    return research


def load_bundle(root):
    root = Path(root)
    packet = read_json(root / "packet.json")
    records = read_json(root / "evidence.json")
    if not isinstance(records, list):
        raise ContractError("evidence.json must contain a list of evidence records")
    selected = check_packet(packet, records, root)
    research = read_json(root / "research.json")
    check_research(packet, research, selected, root)
    return packet, list(selected.values()), research
