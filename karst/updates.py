"""Manual incremental research: evidence differences and explicit economic routing.

This is a triage plan, never an investment conclusion or an assertion of reading.
The registry owns evidence identity; the researcher owns relevance and exposure.
No network, model calls, scheduling or automatic trading happen here.
"""
from __future__ import annotations

import copy
import math
from urllib.parse import urlsplit

from .packet import _private_selectors, instant
from .schema import ContractError, canonical, digest

VERSION = "incremental-v1"
LAYERS = tuple(f"L{i}" for i in range(1, 7))
DOWNSTREAM = {
    "L1": LAYERS, "L2": ("L2", "L3", "L4", "L6"),
    "L3": ("L3", "L4", "L6"), "L4": ("L4", "L6"),
    "L5": ("L5", "L6"), "L6": ("L6",),
}
KIND_LAYERS = {
    "prices": ("L4", "L5", "L6"),
    "filing": ("L2", "L3", "L4", "L5", "L6"),
    "financials": ("L3", "L4", "L6"), "transcript": ("L2", "L3", "L4", "L6"),
    "industry_report": ("L2", "L3", "L4", "L6"),
    "consensus": ("L4", "L6"), "ratings": ("L4", "L6"),
    "valuation": ("L4", "L6"), "calendar": ("L3", "L6"),
    "filing_index": ("L3", "L6"), "profile": ("L2", "L3", "L6"),
    "ownership": ("L3", "L5", "L6"), "short_interest": ("L5", "L6"),
}


def identifier(value):
    return digest(canonical(value))


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} must be nonempty text")


def timestamp(value):
    try:
        at = instant(value)
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError()
        return at
    except (ValueError, TypeError, AttributeError) as exc:
        raise ContractError("Use an ISO timestamp with an explicit timezone") from exc


def validate_watch(item):
    """An agent-written thesis watch; subscriptions discover previously uncited sources.

    Dependencies pin a source/entity/relation input and the assumption it supports.
    Exposure is prose because a supplier and its customer need different judgments.
    """
    required = {"waiting_for", "conditions", "validation_deadline", "subscriptions", "dependencies"}
    if not isinstance(item, dict) or set(item) != required:
        raise ContractError(f"watch must contain exactly {sorted(required)}")
    _private_selectors(item)
    _text(item["waiting_for"], "waiting_for")
    if item["validation_deadline"] is not None:
        timestamp(item["validation_deadline"])
    for name in ("conditions", "subscriptions", "dependencies"):
        if not isinstance(item[name], list):
            raise ContractError(f"{name} must be a list")
    for condition in item["conditions"]:
        if not isinstance(condition, dict) or condition.get("kind") not in ("price", "event"):
            raise ContractError("condition kind must be price or event")
        _text(condition.get("description"), "condition.description")
        if condition["kind"] == "price":
            if set(condition) != {"kind", "description", "operator", "value", "currency"}:
                raise ContractError("price condition needs operator, value, currency and description")
            value = condition["value"]
            if (condition["operator"] not in ("gte", "lte") or isinstance(value, bool)
                    or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0):
                raise ContractError("Invalid price threshold")
            _text(condition["currency"], "condition.currency")
        elif set(condition) != {"kind", "description"}:
            raise ContractError("Event conditions are questions for the researcher, not automatic event claims")
    for sub in item["subscriptions"]:
        optional = {"source_ids", "authors", "source_types", "url_prefixes"}
        if (not isinstance(sub, dict) or not {"entity_id", "kinds"} <= set(sub)
                or set(sub) - {"entity_id", "kinds"} - optional):
            raise ContractError("subscription requires entity_id/kinds and optional source_ids/authors/source_types/url_prefixes")
        _text(sub["entity_id"], "subscription.entity_id")
        if not isinstance(sub["kinds"], list) or not sub["kinds"]:
            raise ContractError("subscription.kinds must be nonempty")
        for kind in sub["kinds"]:
            _text(kind, "subscription.kind")
        for key in optional & set(sub):
            if not isinstance(sub[key], list) or not sub[key]:
                raise ContractError(f'subscription.{key} must be a nonempty list')
            for value in sub[key]:
                _text(value, f'subscription.{key}')
                if key == 'url_prefixes':
                    parsed = urlsplit(value)
                    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                            or parsed.password or parsed.query or parsed.fragment):
                        raise ContractError('Report URL prefixes require public HTTPS host/path without query or credentials')
    for dep in item["dependencies"]:
        keys = {"input_kind", "input_id", "input_version", "assumption_id",
                "assumption_version", "layers", "exposure"}
        if not isinstance(dep, dict) or set(dep) != keys:
            raise ContractError(f"dependency requires {sorted(keys)}")
        if dep["input_kind"] not in ("source", "entity", "relation", "assumption"):
            raise ContractError("Unknown dependency kind")
        for key in keys - {"layers"}:
            _text(dep[key], key)
        if not isinstance(dep["layers"], list) or not dep["layers"] or not set(dep["layers"]) <= set(LAYERS):
            raise ContractError("dependency layers must name L1–L6")
    return copy.deepcopy(item)


def latest_sources(records, as_of, observations=()):
    """Latest acquired version per logical source, including failed/empty observations.

    Historical snapshots remain available to the chart builder; triage compares
    current source versions, not every superseded snapshot with every new one.
    """
    cutoff = timestamp(as_of)
    observed = {}
    for row in observations:
        at = timestamp(row["fetched_at"])
        if at <= cutoff:
            observed[row["evidence_id"]] = max(at, observed.get(row["evidence_id"], at))
    index = {r["evidence_id"]: r for r in records}
    def rank(record):
        # Frozen input lists may be sorted by ID rather than journal order. Follow
        # the immutable supersession chain for multiple revisions in one second.
        seen, prior = set(), record.get("supersedes")
        while prior in index and prior not in seen:
            seen.add(prior)
            prior = index[prior].get("supersedes")
        return (max(timestamp(record["fetched_at"]), observed.get(record["evidence_id"], timestamp(record["fetched_at"]))), len(seen), record["evidence_id"])
    result = {}
    for record in records:
        acquired = timestamp(record["fetched_at"])
        if acquired > cutoff:
            continue
        key = record["source_id"]
        old = result.get(key)
        if old is None or rank(record) > rank(old):
            result[key] = record
    return result


def _matches(record, dependency):
    return ((dependency["input_kind"] == "source" and dependency["input_id"] == record["source_id"])
            or (dependency["input_kind"] == "entity" and dependency["input_id"] in record.get("entity_ids", [])))


def subscribed(record, watch):
    return any(subscription_matches(record, s) for s in watch.get("subscriptions", [])) or any(
                   _matches(record, dep) for dep in watch.get("dependencies", []))


def subscription_matches(record, subscription):
    """AND between filters, OR within each list. Filters select, never fetch a URL."""
    if (subscription['entity_id'] not in record.get('entity_ids', [])
            or record['kind'] not in subscription['kinds']):
        return False
    params = record.get('params') or {}
    for key, actual in (('source_ids', record.get('source_id')),
                        ('authors', params.get('author')), ('source_types', params.get('source_type'))):
        if key in subscription:
            normalized = str(actual or '').strip().casefold() if key == 'authors' else actual
            allowed = [x.strip().casefold() for x in subscription[key]] if key == 'authors' else subscription[key]
            if normalized not in allowed:
                return False
    if 'url_prefixes' in subscription:
        try:
            target = urlsplit(record.get('source_url') or params.get('url') or '')
            def contains(prefix):
                base = urlsplit(prefix)
                root = base.path.rstrip('/')
                return (target.scheme == base.scheme and target.hostname == base.hostname
                        and (target.port or 443) == (base.port or 443) and not target.username and not target.password
                        and (target.path == root or target.path.startswith(root + '/')))
            if not any(contains(prefix) for prefix in subscription['url_prefixes']):
                return False
        except ValueError:
            return False
    return True


def validate_input_changes(events):
    if not isinstance(events, (list, tuple)):
        raise ContractError("input_changes must be a list")
    for event in events:
        if not isinstance(event, dict) or set(event) != {"kind", "id", "version", "reason"}:
            raise ContractError("input change requires kind, id, version and reason")
        if event["kind"] not in ("relation", "assumption"):
            raise ContractError("Explicit input changes are relation or assumption revisions")
        for key in event:
            _text(event[key], key)
    return events


def plan(subject, baseline, records, *, as_of, watch=None, refresh_status=(),
         market=None, method_versions=None, input_changes=(), observations=()):
    """A reproducible plan; only checked_at is excluded from its content identity.

    input_changes handles explicit relation/assumption revisions. It does not infer
    economic propagation from a citation. No source is silently judged immaterial.
    """
    timestamp(as_of)
    watch_row = watch or {}
    watch = watch_row.get("payload", {})
    old_records = (baseline or {}).get("evidence")
    old = latest_sources(old_records or [], (baseline or {}).get("as_of") or as_of, observations)
    current = latest_sources(records, as_of, observations)
    changed, diagnostics, affected, reasons = [], [], set(), []
    for sid, record in sorted(current.items()):
        before = old.get(sid)
        same = before and before["source_version"] == record["source_version"]
        if record["status"] != "ok":
            diagnostics.append({"source_id": sid, "evidence_id": record["evidence_id"],
                                "status": record["status"], "reason": record.get("status_reason")})
            continue
        if same:
            continue
        deps = [d for d in watch.get("dependencies", []) if _matches(record, d)]
        # A specifically reviewed source version need not cause a new research
        # edition if its impact was judged immaterial. Broader entity subscriptions
        # do not undo that explicit adoption. Conflicting adopted versions still alert.
        source_deps = [d for d in deps if d['input_kind'] == 'source']
        if (source_deps and watch_row.get('based_on_version_id') == (baseline or {}).get('version_id')
                and all(d["input_version"] == record["source_version"] for d in source_deps)):
            continue
        layers = set(KIND_LAYERS.get(record["kind"], LAYERS))
        for dep in deps:
            for layer in dep["layers"]:
                layers.update(DOWNSTREAM[layer])
        affected.update(layers)
        changed.append({"source_id": sid, "evidence_id": record["evidence_id"],
                        "source_version": record['source_version'],
                        "previous_evidence_id": (before or {}).get("evidence_id"),
                        "kind": record["kind"], "change": "changed" if before else "discovered",
                        "layers": sorted(layers), "dependencies": deps,
                        "published_at": record.get("published_at"), "period": record.get("period")})
    for event in validate_input_changes(input_changes):
        mapped = False
        for dep in watch.get("dependencies", []):
            if (dep["input_kind"], dep["input_id"]) == (event["kind"], event["id"]):
                mapped = True
            if (dep["input_kind"], dep["input_id"]) == (event["kind"], event["id"]) and dep["input_version"] != event["version"]:
                affected.update(l for layer in dep["layers"] for l in DOWNSTREAM[layer])
                reasons.append({"kind": "dependency_changed", "event": event, "dependency": dep})
        if not mapped:
            reasons.append({"kind": "unmapped_input_change", "event": event})
            affected.update(("L2", "L6"))
    missing = sorted(set(old) - set(current))
    if missing:
        reasons.append({"kind": "missing_sources", "source_ids": missing})
        affected.update(LAYERS)
    if baseline and old_records is None:
        reasons.append({"kind": "missing_baseline_inputs"})
        affected.update(LAYERS)
    if baseline is None:
        reasons.append({"kind": "initial_research"})
        affected.update(LAYERS)
    research = (baseline or {}).get("payload", {})
    if method_versions and research and research.get("method_version") not in method_versions:
        reasons.append({"kind": "method_changed", "previous": research.get("method_version")})
        affected.update(LAYERS)
    if watch_row and watch_row.get("based_on_version_id") != (baseline or {}).get("version_id"):
        reasons.append({"kind": "watch_needs_revalidation"})
        affected.add("L6")
    deadline = watch.get("validation_deadline")
    if deadline and timestamp(deadline) <= timestamp(as_of):
        reasons.append({"kind": "validation_due", "deadline": deadline, "waiting_for": watch["waiting_for"]})
        affected.update(("L3", "L4", "L6"))
    target = research.get("target_date")
    if target and target <= as_of[:10]:
        reasons.append({"kind": "target_due", "target_date": target})
        affected.update(("L4", "L6"))
    review_at = research.get("plan", {}).get("next_review_at")
    if review_at and timestamp(review_at) <= timestamp(as_of):
        reasons.append({"kind": "plan_review_due", "next_review_at": review_at})
        affected.add("L6")
    conditions = []
    for condition in watch.get("conditions", []):
        status = "requires_reading" if condition["kind"] == "event" else "unknown"
        if (condition["kind"] == "price" and market and market.get("complete") is True
                and market.get("currency") == condition["currency"]
                and market.get("adjustment", "").lower() in ("raw", "noadjust", "none", "unadjusted")):
            hit = (market["price"] >= condition["value"] if condition["operator"] == "gte"
                   else market["price"] <= condition["value"])
            status = "threshold_met" if hit else "threshold_not_met"
            if hit:
                affected.update(("L4", "L5", "L6"))
                reasons.append({"kind": "price_condition", "condition": condition, "market": market})
        conditions.append({"condition": condition, "status": status, "market": market})
    problems = [s for s in refresh_status if s["status"] != "ok"]
    if problems:
        reasons.append({"kind": "refresh_incomplete", "sources": problems})
    needs = bool(affected)
    status = "needs_reassessment" if needs else "incomplete" if problems or diagnostics else "no_change"
    result = {"routing_version": VERSION, "subject": subject,
              "base_version_id": (baseline or {}).get("version_id"),
              "watch_version": watch_row.get("version"), "status": status,
              "source_changes": changed, "diagnostics": diagnostics, "reasons": reasons,
              "affected_layers": sorted(affected),
              "reuse_candidates": [l for l in LAYERS if l not in affected] if baseline else [],
              "price_only": bool(changed) and all(c["kind"] == "prices" for c in changed) and not reasons,
              "conditions": conditions, "refresh_status": list(refresh_status),
              "preserve": {"target_date": target, "valuation_date": research.get("valuation", {}).get("valuation_date"),
                           "assessed_at": {k: v.get("assessed_at") for k, v in research.get("layers", {}).items()}},
              "note": "Routing is triage, not a conclusion. Inspect relevance and dependencies; reuse candidates need agent judgment. A price threshold is not an executed trade."}
    identity = copy.deepcopy(result)
    # Observation clocks are useful freshness data, not a new investment event.
    for status in identity["refresh_status"]:
        status.pop("checked_at", None)
    for reason in identity["reasons"]:
        if reason["kind"] == "refresh_incomplete":
            for status in reason["sources"]:
                status.pop("checked_at", None)
    result["plan_id"] = "upd-" + identifier(identity)
    result["checked_at"] = as_of
    return result


def research_changes(previous, current):
    """Exact decision differences plus the researcher's reason, without invented rationale."""
    keys = ("rating", "execution_state", "target_date", "market", "valuation", "technical", "plan", "open_questions", "coverage")
    changes = [{"field": key, "before": (previous or {}).get(key), "after": current.get(key)}
               for key in keys if (previous or {}).get(key) != current.get(key)]
    return {"initial": previous is None, "changes": changes,
            "reason": current.get("headline", {}).get("change_since_last"),
            "layers": {key: {"mode": "reused" if previous and value == previous.get("layers", {}).get(key) else "reassessed",
                              "assessed_at": value.get("assessed_at")}
                       for key, value in current.get("layers", {}).items()},
            "note": "Reassessed means changed submitted analysis; it is not independent review or proof of new reading."}
