"""File inputs and additive evidence requests, shared by replay and future adapters."""
from __future__ import annotations

import copy
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .schema import ContractError, canonical, decode, digest, validate


def build_packet(evidence_records, as_of, security, *, created_at=None,
                 knowledge_basis="system_observed", previous_packet_id=None,
                 required_kinds=("filing", "transcript", "financials", "prices"),
                 dependencies=(), supplement_requests=(), pending_updates=(), root=None,
                 contract_version="0.2.0"):
    """Build from an explicitly selected set, never silently filter late evidence.

    Caller selects current applicable versions (including shared industry evidence),
    resolves security IDs and registers supplements before rebuilding the packet.
    root, when supplied, additionally verifies all source bytes before returning.
    """
    records = copy.deepcopy(list(evidence_records))
    for record in records:
        validate("evidence", record)
        if record["contract_version"] != contract_version:
            raise ContractError(f"build_packet requires contract {contract_version} evidence")
        _private_selectors(record["params"])
    if len({r["evidence_id"] for r in records}) != len(records):
        raise ContractError("Duplicate evidence_id")
    usable = sorted((r for r in records if r["status"] == "ok"), key=lambda r: r["evidence_id"])
    diagnostics = sorted(r["evidence_id"] for r in records if r["status"] != "ok")
    kinds = sorted(set(required_kinds) | {"transcript"} | {r["kind"] for r in records})
    requirements = []
    for kind in kinds:
        matching = [r for r in usable if r["kind"] == kind]
        status = "missing" if not matching else (
            "partial" if any(r["truncated"] for r in matching) else "available")
        reason = {"missing": "No usable source supplied; inspect diagnostics or request a supplement.",
                  "partial": "At least one supplied source is truncated; full coverage is not established.",
                  "available": "Supplied source is not truncated; recency and required sections still need review."}[status]
        requirements.append({"kind": kind, "status": status,
                             "evidence_ids": [r["evidence_id"] for r in matching], "reason": reason})
    extra = copy.deepcopy(list(dependencies))
    if any(dep.get("kind") == "evidence" for dep in extra):
        raise ContractError("Evidence dependencies are generated from exact selected versions")
    packet = {"contract_version": contract_version, "packet_id": "packet-pending",
              "previous_packet_id": previous_packet_id, "security": copy.deepcopy(security),
              "as_of": as_of, "created_at": created_at or datetime.now(timezone.utc).isoformat(),
              "knowledge_basis": knowledge_basis,
              "evidence_ids": [r["evidence_id"] for r in usable], "diagnostic_ids": diagnostics,
              "dependencies": [{"kind": "evidence", "id": r["evidence_id"], "version": r["source_version"]}
                               for r in usable] + extra,
              "requirements": requirements, "supplement_requests": copy.deepcopy(list(supplement_requests)),
              "pending_updates": list(pending_updates)}
    packet["packet_id"] = "packet-" + digest(canonical(packet))
    validate("packet", packet)
    if instant(packet["created_at"]) < instant(as_of):
        raise ContractError("Packet cannot be created before its data cutoff")
    for record in records:
        check_observation_time(packet, record)
        start, end = record["period"]["start"], record["period"]["end"]
        if start and end and start > end:
            raise ContractError("Normalized period start exceeds end")
    usable_ids = set(packet["evidence_ids"])
    request_ids = [r["request_id"] for r in packet["supplement_requests"]]
    if len(set(request_ids)) != len(request_ids):
        raise ContractError("Duplicate supplement request_id")
    for request in packet["supplement_requests"]:
        if not set(request["evidence_ids"]) <= usable_ids:
            raise ContractError("Supplement references unselected evidence")
        if request["status"] == "fulfilled" and (not request["evidence_ids"] or not request["resolution"]):
            raise ContractError("Fulfilled supplement needs registered evidence and resolution")
        if request["status"] != "fulfilled" and request["evidence_ids"]:
            raise ContractError("Only fulfilled supplements can attach evidence")
        if request["status"] != "pending" and not request["resolution"]:
            raise ContractError("Resolved supplement needs a resolution")
    if root is not None:
        check_packet(packet, records, root)
    return packet


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def time_bounds(record, field):
    """Availability interval, not an invented timestamp. A date's upper bound is exclusive."""
    value = record[field]
    precision = record.get(field + "_precision", "datetime" if value else "unknown")
    if precision == "unknown":
        return None, None
    if precision == "datetime":
        moment = instant(value)
        return moment, moment
    day = date.fromisoformat(value)
    try:
        tomorrow = day + timedelta(days=1)
    except OverflowError as exc:
        raise ContractError("Date has no representable availability upper bound") from exc
    zone_name = record.get(field + "_timezone")
    if zone_name is None:
        # Unknown source zone: cover all offsets in [-14h, +14h]. Never assume UTC.
        return (datetime.combine(day, time.min, timezone.utc) - timedelta(hours=14),
                datetime.combine(tomorrow, time.min, timezone.utc) + timedelta(hours=14))
    try:
        zone = ZoneInfo(zone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ContractError(f"Unknown IANA timezone: {zone_name}") from exc
    return (datetime.combine(day, time.min, zone).astimezone(timezone.utc),
            datetime.combine(tomorrow, time.min, zone).astimezone(timezone.utc))


def check_observation_time(packet, record):
    cutoff, created, fetched = map(instant, (packet["as_of"], packet["created_at"], record["fetched_at"]))
    for field in ("published_at", "data_as_of"):
        lower, _ = time_bounds(record, field)
        if lower is not None and lower > cutoff:
            raise ContractError(f"Evidence {record['evidence_id']}/{field} is after cutoff")
    if fetched > created:
        raise ContractError("Evidence was fetched after packet creation")
    diagnostic = record.get("status", "ok") != "ok"
    if packet["knowledge_basis"] == "system_observed" or diagnostic:
        if fetched > cutoff:
            raise ContractError("Evidence or diagnostic was not observed by system cutoff")
        return
    lower, upper = time_bounds(record, "published_at")
    if lower is None:
        raise ContractError("Public-as-of replay needs known publication time")
    if upper > cutoff and fetched > cutoff:
        raise ContractError("Publication date is ambiguous at the replay cutoff; actual observation or a later cutoff is required")


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
        if record["contract_version"] != packet["contract_version"]:
            raise ContractError("Packet and evidence must use the same contract version")
        if record["evidence_id"] in index:
            raise ContractError("Duplicate evidence_id")
        _private_selectors(record["params"])
        index[record["evidence_id"]] = record
    selected = {}
    usable = set(packet["evidence_ids"])
    diagnostics = set(packet.get("diagnostic_ids", []))
    if usable & diagnostics:
        raise ContractError("Evidence and diagnostic IDs must be disjoint")
    for eid in packet["evidence_ids"] + packet.get("diagnostic_ids", []):
        if eid not in index:
            raise ContractError(f"Unregistered evidence: {eid}")
        record = index[eid]
        status = record.get("status", "ok")
        if (eid in usable) != (status == "ok"):
            raise ContractError("Only ok records are evidence; empty/error records belong in diagnostic_ids")
        check_observation_time(packet, record)
        start, end = record["period"]["start"], record["period"]["end"]
        if start is not None and end is not None and start > end:
            raise ContractError("Normalized period start exceeds end")
        artifact = record["artifact"]
        data = confined(root, artifact["path"]).read_bytes()
        if len(data) != artifact["bytes"] or digest(data) != artifact["sha256"]:
            raise ContractError(f"Evidence content hash/size mismatch: {eid}")
        selected[eid] = record
    for requirement in packet["requirements"]:
        if not set(requirement["evidence_ids"]) <= usable:
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
        if not set(request["evidence_ids"]) <= usable:
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
            if dep["id"] not in usable or selected[dep["id"]]["source_version"] != dep["version"]:
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
    if research["contract_version"] != packet["contract_version"]:
        raise ContractError("Packet and research must use the same contract version")
    usable = set(packet["evidence_ids"])
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
        if not set(section["read_evidence_ids"]) <= usable:
            raise ContractError("Read log references evidence outside packet")
        if instant(section["assessed_at"]) > instant(research["created_at"]):
            raise ContractError("Layer assessed after research creation")
    transcript_ids = {eid for r in packet["requirements"] if r["kind"] == "transcript"
                      for eid in r["evidence_ids"]}
    if not transcript_ids <= set(research["layers"]["L3"]["read_evidence_ids"]):
        raise ContractError("Fundamentals must record reading supplied transcripts")
    for citation in _citations(research):
        if citation["evidence_id"] not in usable:
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
    # 0.4: a sensitivity or a reverse solve is an operation ON one scenario. Naming a
    # scenario that carries no calculation would leave a number with nothing behind it.
    attached = [row["scenario"] for row in research["valuation"].get("sensitivities") or []]
    implied = research["valuation"].get("implied")
    if implied:
        attached.append(implied["scenario"])
    if not set(attached) <= set(names):
        raise ContractError("A sensitivity or reverse solve names a scenario without a calculation")
    # 0.3 may omit the price arrays entirely; the derived numbers stay in `derived`.
    for bars in (research["technical"].get("views") or {}).values():
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
    derived = research["technical"].get("derived")
    if derived and instant(derived["data_as_of"]) > instant(packet["as_of"]):
        raise ContractError("Technical data cutoff is after the packet cutoff")
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

