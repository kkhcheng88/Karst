"""Versioned research inputs, not an alternative evidence or rating database.

Universe membership precedes deep research. Directed economic relationships and
testable assumptions feed the existing watch dependencies. System timestamps are
assigned on write; a newly discovered old document cannot rewrite past knowledge.
"""
from __future__ import annotations

import copy
import json
import math
import logging
from datetime import date
from urllib.parse import urlsplit

from .schema import ContractError, canonical, digest
from .updates import LAYERS, timestamp, require_text as _text

KINDS = ("universe", "relation", "assumption", "comparison")
RELATIONS = ("supplies", "customer", "competes", "finances", "exposed_to", "complements")


def fields(value, required, optional=()):
    if not isinstance(value, dict) or set(required) - set(value) or set(value) - set(required) - set(optional):
        raise ContractError(f"Expected fields {sorted(required)}, optional {sorted(optional)}")


def sources(values):
    if not isinstance(values, list) or not values:
        raise ContractError("Research inputs need source references")
    for value in values:
        fields(value, {"title"}, {"url", "evidence_id", "locator"})
        if not value.get('url') and not value.get('evidence_id'):
            raise ContractError('Source needs a public URL or a registered evidence reference')
        for key, text in value.items():
            _text(text, key)
        if 'url' in value:
            url = urlsplit(value["url"])
            if url.scheme != "https" or not url.hostname or url.username or url.password:
                raise ContractError("Source URL must be a public HTTPS reference")


def validate(kind, payload):
    from .packet import _private_selectors
    _private_selectors(payload)
    if kind == "universe":
        fields(payload, {"name", "summary", "members", "sources"})
        _text(payload["name"], "name")
        _text(payload["summary"], "summary")
        if not isinstance(payload["members"], list) or not payload["members"]:
            raise ContractError("Universe members must be nonempty")
        seen = set()
        for member in payload["members"]:
            fields(member, {"entity_id", "name", "kind", "roles", "comparison_groups"})
            for key in ("entity_id", "name"):
                _text(member[key], key)
            if member["entity_id"] in seen:
                raise ContractError("Duplicate universe member")
            seen.add(member["entity_id"])
            if member["kind"] not in ("company", "security", "fund", "index", "theme"):
                raise ContractError("Unknown member kind")
            for key in ("roles", "comparison_groups"):
                if not isinstance(member[key], list) or (key == "roles" and not member[key]):
                    raise ContractError("Member roles/groups must be lists; roles cannot be empty")
                for value in member[key]:
                    _text(value, key)
    elif kind == "relation":
        fields(payload, {"from_entity", "to_entity", "relation_type", "mechanism", "status",
                         "valid_from", "valid_to", "basis", "sources"})
        for key in ("from_entity", "to_entity", "mechanism"):
            _text(payload[key], key)
        if payload["from_entity"] == payload["to_entity"]:
            raise ContractError("Self relationships are not useful research inputs")
        if payload["relation_type"] not in RELATIONS or payload["basis"] not in ("documented", "inference"):
            raise ContractError("Unknown relation type or basis")
        if payload["status"] not in ("active", "withdrawn"):
            raise ContractError("Unknown relation status")
        for key in ("valid_from", "valid_to"):
            if payload[key] is not None:
                date.fromisoformat(payload[key])
        if payload["valid_from"] and payload["valid_to"] and payload["valid_from"] > payload["valid_to"]:
            raise ContractError("Relationship ends before it starts")
    elif kind == "assumption":
        fields(payload, {"subject", "driver", "statement", "expected", "unit", "period", "next_check",
                         "change_effect", "layers", "status", "sources"})
        for key in ("subject", "driver", "statement", "unit", "period", "next_check", "change_effect"):
            _text(payload[key], key)
        if payload["status"] not in ("active", "revised", "rejected"):
            raise ContractError("Unknown assumption status")
        value = payload["expected"]
        if not isinstance(value, str):
            number(value, "expected")
        else:
            _text(value, "expected")
        if not isinstance(payload["layers"], list) or not payload["layers"] or not set(payload["layers"]) <= set(LAYERS):
            raise ContractError("Assumption must name affected research layers")
    elif kind == "comparison":
        fields(payload, {"subject", "as_of", "metrics", "sources"})
        _text(payload["subject"], "subject")
        date.fromisoformat(payload["as_of"])
        if not isinstance(payload["metrics"], list) or not payload["metrics"]:
            raise ContractError("Comparison requires explicit metrics")
        seen = set()
        for metric in payload["metrics"]:
            fields(metric, {"key", "value", "unit", "period", "basis", "status", "source_index"})
            for key in ("key", "unit", "period", "basis"):
                _text(metric[key], key)
            if metric["key"] in seen:
                raise ContractError("Duplicate comparison metric")
            seen.add(metric["key"])
            if metric["status"] not in ("reported", "calculated", "guidance", "estimate", "missing", "not_applicable"):
                raise ContractError("Unknown metric status")
            if metric["status"] in ("missing", "not_applicable"):
                if metric["value"] is not None:
                    raise ContractError("Missing or inapplicable metrics must be null, never zero")
            else:
                number(metric["value"], "metric")
            index = metric["source_index"]
            if type(index) is not int or not 0 <= index < len(payload["sources"]):
                raise ContractError("Metric must identify its source")
    else:
        raise ContractError("Unknown knowledge kind")
    sources(payload["sources"])
    return copy.deepcopy(payload)


def _row(row):
    if row is None:
        return None
    result = dict(row)
    result["payload"] = json.loads(result["payload"])
    return result


def get(store, kind, object_id, *, version=None, as_of=None):
    if kind not in KINDS:
        raise ContractError("Unknown knowledge kind")
    sql = "SELECT * FROM knowledge_versions WHERE kind=? AND object_id=?"
    args = [kind, object_id]
    if version is not None:
        sql += " AND version=?"
        args.append(version)
    if as_of is not None:
        cutoff = timestamp(as_of).timestamp()
        sql += " AND known_epoch<=?"
        args.append(cutoff)
    return _row(store.connection.execute(sql + " ORDER BY rowid DESC LIMIT 1", args).fetchone())


def save(store, kind, object_id, payload, *, expected_version=None):
    from .store import now
    _text(object_id, "object_id")
    payload = validate(kind, payload)
    cursor = store.connection.cursor()
    cursor.execute("BEGIN IMMEDIATE")
    try:
        previous = get(store, kind, object_id)
        if previous and previous["payload"] == payload:
            cursor.execute("ROLLBACK")
            return previous
        if (previous or {}).get("version") != expected_version:
            raise ContractError("Knowledge changed; read its latest version before saving")
        if kind == "relation":
            for key in ("from_entity", "to_entity"):
                if not store.get_entity(payload[key]):
                    raise ContractError("Register relation endpoints in a universe first")
        known_at = now()
        version = "kv-" + digest(canonical({"kind": kind, "id": object_id, "payload": payload,
                                            "previous": expected_version}))
        cursor.execute("INSERT INTO knowledge_versions VALUES(?,?,?,?,?,?,?,?)",
                       (version, kind, object_id, expected_version,
                        canonical(payload).decode(), known_at, timestamp(known_at).timestamp(), 1))
        if kind == "universe":
            for member in payload["members"]:
                if store.get_entity(member["entity_id"]) is None:
                    store.upsert_entity(member["entity_id"], member["kind"], name=member["name"])
        cursor.execute("COMMIT")
    except Exception:
        if store.connection.in_transaction:
            cursor.execute("ROLLBACK")
        raise
    return get(store, kind, object_id)


def latest(store, kind, *, as_of=None):
    if kind not in KINDS:
        raise ContractError("Unknown knowledge kind")
    ids = [r[0] for r in store.connection.execute(
        "SELECT DISTINCT object_id FROM knowledge_versions WHERE kind=? ORDER BY object_id", (kind,))]
    return [row for oid in ids if (row := get(store, kind, oid, as_of=as_of))]


def bootstrap(store, manifest):
    """Seed absent objects; optional pinned revisions use the same CAS as MCP writes.

    Acquired time is this import, not a document's earlier publication date.
    An explicit expected_version permits a reviewed deployment migration. A newer
    live revision is never overwritten; conflicts are logged for operator review.
    """
    if not isinstance(manifest, list):
        raise ContractError("Knowledge seed must be a list")
    for item in manifest:
        fields(item, {"kind", "object_id", "payload"}, {"expected_version"})
        _text(item["object_id"], "object_id")
        if "expected_version" in item:
            _text(item["expected_version"], "expected_version")
        validate(item["kind"], item["payload"])
    imported = []
    for item in sorted(manifest, key=lambda i: i["kind"] != "universe"):
        current = get(store, item["kind"], item["object_id"])
        if current is None:
            # Fresh installations take the corrected payload directly.
            imported.append(save(store, item["kind"], item["object_id"], item["payload"])["version"])
        elif "expected_version" in item and current["payload"] != item["payload"]:
            if current["version"] == item["expected_version"]:
                imported.append(save(store, **item)["version"])
            else:
                logging.getLogger(__name__).warning(
                    "Knowledge migration conflict; retained live %s/%s at %s",
                    item["kind"], item["object_id"], current["version"])
    return imported


def subject_inputs(store, subject, *, as_of=None):
    result = {}
    for kind in KINDS:
        result[kind] = []
        for row in latest(store, kind, as_of=as_of):
            p = row["payload"]
            matches = (subject in {m["entity_id"] for m in p["members"]} if kind == "universe"
                       else subject in (p["from_entity"], p["to_entity"]) if kind == "relation"
                       else p["subject"] == subject)
            if matches:
                result[kind].append(row)
    return result


def value_chain(store, universe_id, *, as_of=None, focus=None, depth=1):
    from .store import now
    as_of = as_of or now()
    timestamp(as_of)
    if type(depth) is not int or not 0 <= depth <= 3:
        raise ContractError("Graph depth must be 0–3")
    universe = get(store, "universe", universe_id, as_of=as_of)
    if universe is None:
        raise ContractError("Universe not known at this cutoff")
    members = universe["payload"]["members"]
    member_ids = {m["entity_id"] for m in members}
    if focus is not None and focus not in member_ids:
        raise ContractError("Focus must be a universe member")
    eligible = []
    for row in latest(store, "relation", as_of=as_of):
        p = row["payload"]
        if (p["status"] == "active" and (not p["valid_from"] or p["valid_from"] <= as_of[:10])
                and (not p["valid_to"] or as_of[:10] <= p["valid_to"])
                and {p["from_entity"], p["to_entity"]} <= member_ids):
            eligible.append(row)
    selected = {focus} if focus else member_ids
    if focus:
        for _ in range(depth):
            selected |= {node for r in eligible for node in (r["payload"]["from_entity"], r["payload"]["to_entity"])
                         if r["payload"]["from_entity"] in selected or r["payload"]["to_entity"] in selected}
    relations = [r for r in eligible if {r["payload"]["from_entity"], r["payload"]["to_entity"]} <= selected]
    assumptions = [r for r in latest(store, "assumption", as_of=as_of)
                   if r["payload"]["subject"] in selected and r["payload"]["status"] != "rejected"]
    comparisons = [r for r in latest(store, "comparison", as_of=as_of)
                   if r["payload"]["subject"] in selected]
    return {"universe": universe, "as_of": as_of, "members": [m for m in members if m["entity_id"] in selected],
            "relations": relations, "assumptions": assumptions,
            "comparisons": comparisons,
            "interpretation": "Economic inputs for reassessment; connected companies do not inherit ratings."}


def dependency_changes(store, watch, *, as_of):
    changes = {}
    for dependency in (watch or {}).get("payload", {}).get("dependencies", []):
        kind, oid = dependency["input_kind"], dependency["input_id"]
        if kind not in ("relation", "assumption"):
            continue
        row = get(store, kind, oid, as_of=as_of)
        if row and row["version"] != dependency["input_version"]:
            changes[(kind, oid)] = {"kind": kind, "id": oid, "version": row["version"],
                                    "reason": "Adopted economic input has a newer recorded version"}
    return list(changes.values())


def affected_research(store, kind, object_id):
    if kind not in ("relation", "assumption"):
        raise ContractError("Only adopted relations and assumptions route research")
    return [{"subject": w["subject"], "based_on_version_id": w["based_on_version_id"],
             "dependencies": [d for d in w["payload"]["dependencies"]
                              if (d["input_kind"], d["input_id"]) == (kind, object_id)]}
            for w in store.list_watches() if any((d["input_kind"], d["input_id"]) == (kind, object_id)
                                                 for d in w["payload"]["dependencies"])]


def number(value, name, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or (positive and value <= 0):
        raise ContractError(f"{name} must be a finite {'positive ' if positive else ''}number")
    return value


def valuation_matrix(eps_scenarios, multiples, *, period, earnings_basis, currency):
    """Independent axes. Not probabilities, peer medians or price recommendations."""
    for key, value in (("period", period), ("earnings_basis", earnings_basis), ("currency", currency)):
        _text(value, key)
    if not isinstance(eps_scenarios, list) or not 1 <= len(eps_scenarios) <= 12:
        raise ContractError("Supply 1–12 EPS scenarios")
    if not isinstance(multiples, list) or not 1 <= len(multiples) <= 12:
        raise ContractError("Supply 1–12 multiples")
    multiples = [number(m, "multiple", positive=True) for m in multiples]
    rows = []
    for item in eps_scenarios:
        fields(item, {"label", "eps"})
        _text(item["label"], "label")
        eps = number(item["eps"], "eps")
        rows.append({**item, "prices": [number(eps * m, "price") if eps > 0 else None for m in multiples],
                     "status": "ok" if eps > 0 else "pe_not_applicable"})
    result = {"period": period, "earnings_basis": earnings_basis, "currency": currency,
              "multiples": multiples, "rows": rows}
    return {"result": result, "receipt": {"calculator_version": "valuation-matrix-v1",
            "inputs_digest": digest(canonical([eps_scenarios, multiples, period, earnings_basis, currency])),
            "outputs": result}}
