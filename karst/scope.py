"""Update scope (更新範圍): which parts of a research an update may rewrite, and the proof.

The routing plan (``karst.updates.plan``) and the daily snapshot queue say what changed;
:func:`issue` turns that into a **scope** the system records and hands to the researcher.
At intake :func:`gate` holds the update to it:

* units outside the scope are **carried** from the previous version verbatim — the
  researcher may leave them out of the payload;
* changing a carried unit needs an **expansion** with a reason (any old error may still
  be corrected; the reason is recorded);
* every unit inside the scope is either **changed** or **reviewed** — kept, with the
  evidence IDs read this time; a silent copy is refused;
* the result is a provenance row per unit: status, triggers, previous version.

Carried layers expire (:data:`MAX_CARRY_DAYS`, :data:`VERIFICATION_LAYERS`); an expired
layer is put back into the next scope. No ticker, date or security lives here, no I/O.
"""
from __future__ import annotations

import copy
from datetime import timedelta

from .packet import _citations, instant
from .schema import ContractError, canonical, digest
from .updates import LAYERS

VERSION = "update-scope/1"

# --- field ownership (欄位歸屬) --------------------------------------------------
# A unit is a layer, plus L4_price: the part of L4 that only moves with the share price.
# Every analysis key belongs to exactly one unit, so "what changed" is always a unit.
#
# L4 split, decided here: a pure price move changes what the *current price* requires,
# not what the business is worth. So L4_price owns the quote (``market``) and the two
# valuation fields stated against it — ``implied_requirements`` (現價隱含要求) and
# ``implied`` (the input solved for a target price). The rest of the valuation (scenarios,
# fair value, target prices, method, assumptions, attribution) and the L4 layer text are
# L4 proper: rewriting them on a price move needs an expansion with a reason.
L4_PRICE = "L4_price"
UNITS = ("L1", "L2", "L3", "L4", L4_PRICE, "L5", "L6")
L4_PRICE_VALUATION_KEYS = ("implied_requirements", "implied")
OWNERS = {
    "modules": "L2",            # which scenario modules are active is thesis framing
    "market": L4_PRICE,
    "valuation": "L4",          # minus L4_PRICE_VALUATION_KEYS
    "technical": "L5",
    "plan": "L6", "rating": "L6", "execution_state": "L6", "headline": "L6",
    "open_questions": "L6", "coverage": "L6", "target_date": "L6",
    "phases": "L6",             # the phase panel is a common output of all layers
}
# Triggers that are only a price move — a new prices source, a watch price condition,
# a daily-snapshot price event — route L4 as L4_price (see ``issue``).

# --- carried-layer expiry (沿用期限) ---------------------------------------------
# A carried layer older than this many days is put back into the next scope.
MAX_CARRY_DAYS = {
    "L1": 45,   # macro: about one central-bank meeting cycle
    "L2": 90,   # industry and value chain: one quarter of industry news
    "L3": 100,  # fundamentals: one reporting quarter plus the ~10-day filing lag
    "L4": 100,  # valuation follows the fundamentals it is built on
    "L5": 30,   # technicals: a month of price action changes the picture
    "L6": 30,   # the plan follows L5
}
# A verification date recorded in the research (``plan.next_review_at``) or its watch
# (``validation_deadline``) that has passed since a layer was assessed expires these
# layers: the next results/verification event is what they were waiting for.
VERIFICATION_LAYERS = ("L3", "L4", "L6")


def _days(later, earlier):
    return (instant(later) - instant(earlier)) / timedelta(days=1)


def expired(research, watch, as_of):
    """Triggers for layers of ``research`` that may no longer be carried at ``as_of``."""
    found = []
    events = [("plan.next_review_at", (research.get("plan") or {}).get("next_review_at")),
              ("watch.validation_deadline", ((watch or {}).get("payload") or {}).get("validation_deadline"))]
    for name, layer in sorted((research.get("layers") or {}).items()):
        assessed = layer.get("assessed_at")
        if not assessed or name not in MAX_CARRY_DAYS:
            continue
        age = _days(as_of, assessed)
        if age > MAX_CARRY_DAYS[name]:
            found.append({"kind": "expired", "rule": "max_age", "layers": [name],
                          "assessed_at": assessed, "age_days": round(age, 1),
                          "max_age_days": MAX_CARRY_DAYS[name]})
            continue
        if name in VERIFICATION_LAYERS:
            for event, at in events:
                if at and instant(assessed) < instant(at) <= instant(as_of):
                    found.append({"kind": "expired", "rule": "verification_passed",
                                  "layers": [name], "assessed_at": assessed,
                                  "event": event, "event_at": at})
                    break
    return found


def _price_units(layers):
    return sorted({L4_PRICE if layer == "L4" else layer for layer in layers})


def issue(plan, baseline, *, snapshot=None, snapshot_unread=False, watch=None, as_of):
    """The scope of the next update of ``baseline`` (a stored research row), or None.

    Pure: the plan says which sources and dates changed, an unread daily snapshot queue
    adds its price events and news, and carried layers that expired are added back.
    """
    if not baseline or plan.get("base_version_id") != baseline["version_id"]:
        return None
    triggers = []
    for change in plan["source_changes"]:
        price = change["kind"] == "prices"
        triggers.append({"kind": "source", "source_id": change["source_id"],
                         "evidence_id": change["evidence_id"], "source_kind": change["kind"],
                         "change": change["change"],
                         "layers": _price_units(change["layers"]) if price else list(change["layers"])})
    for reason in plan["reasons"]:
        if reason.get("layers"):
            detail = {k: v for k, v in reason.items() if k not in ("layers", "market", "sources")}
            layers = reason["layers"]
            triggers.append(detail | {"layers": _price_units(layers)
                                      if reason["kind"] == "price_condition" else list(layers)})
    queue = (snapshot or {}).get("queue")
    if queue and snapshot_unread:
        kinds = [reason["kind"] for reason in queue["reasons"]]
        layers = set(queue["layers"])
        if "price_event" in kinds and "L4" not in layers:
            layers.add(L4_PRICE)
        triggers.append({"kind": "daily_snapshot", "date": snapshot["date"],
                         "checked_at": snapshot["checked_at"], "since": queue["since"],
                         "reasons": sorted(set(kinds)),
                         "events": sorted({e["kind"] for r in queue["reasons"]
                                           for e in r.get("events", [])}),
                         "news_evidence_ids": sorted({eid for r in queue["reasons"]
                                                      for eid in r.get("evidence_ids", [])}),
                         "layers": sorted(layers)})
    routed = {layer for trigger in triggers for layer in trigger["layers"]}
    for trigger in expired(baseline["payload"], watch, as_of):
        if trigger["layers"][0] not in routed:
            triggers.append(trigger)
    units = {unit for trigger in triggers for unit in trigger["layers"]}
    if "L4" in units:
        units.add(L4_PRICE)
    scope = {"scope_version": VERSION, "subject": plan["subject"],
             "base_version_id": baseline["version_id"], "plan_id": plan["plan_id"],
             "layers": [unit for unit in UNITS if unit in units], "triggers": triggers}
    return {"scope_id": "scope-" + digest(canonical(scope)), **scope, "issued_at": as_of}


# --- intake gate ----------------------------------------------------------------

def view(research, unit):
    """The fields of ``research`` owned by ``unit`` (a layer's assessed_at excluded)."""
    result = {}
    layer = (research.get("layers") or {}).get(unit)
    if layer is not None:
        result["layer"] = {k: v for k, v in layer.items() if k != "assessed_at"}
    for key, owner in OWNERS.items():
        if owner == unit and key in research:
            value = research[key]
            if key == "valuation" and isinstance(value, dict):
                value = {k: v for k, v in value.items() if k not in L4_PRICE_VALUATION_KEYS}
            result[key] = value
    if unit == L4_PRICE and isinstance(research.get("valuation"), dict):
        result["valuation"] = {k: research["valuation"].get(k) for k in L4_PRICE_VALUATION_KEYS}
    return result


def _evidence(unit_view):
    ids = set((unit_view.get("layer") or {}).get("read_evidence_ids") or [])
    return ids | {c["evidence_id"] for c in _citations(unit_view)}


def _declaration(declaration, read_ids):
    if not isinstance(declaration, dict):
        raise ContractError("An update needs update_scope: {scope_id} from plan_update, or "
                            "{full_reason} for a declared full reassessment")
    extra = set(declaration) - {"scope_id", "full_reason", "reviewed", "expansions"}
    if extra:
        raise ContractError("update_scope has unknown keys: " + ", ".join(sorted(extra)))
    if ("scope_id" in declaration) == ("full_reason" in declaration):
        raise ContractError("update_scope needs exactly one of scope_id or full_reason")
    if "full_reason" in declaration and not str(declaration["full_reason"] or "").strip():
        raise ContractError("full_reason must be nonempty text")
    reviewed = declaration.get("reviewed") or {}
    expansions = declaration.get("expansions") or {}
    if not isinstance(reviewed, dict) or not isinstance(expansions, dict):
        raise ContractError("update_scope.reviewed and .expansions map a layer to a value")
    for unit, ids in reviewed.items():
        if unit not in UNITS:
            raise ContractError(f"Unknown layer in update_scope.reviewed: {unit}")
        if (not isinstance(ids, list) or not ids or len(set(ids)) != len(ids)
                or not all(isinstance(i, str) for i in ids)):
            raise ContractError(f"update_scope.reviewed.{unit} must list the evidence IDs read this time")
        if not set(ids) <= read_ids:
            raise ContractError(f"update_scope.reviewed.{unit} names evidence absent from this read log")
    for unit, reason in expansions.items():
        if unit not in UNITS:
            raise ContractError(f"Unknown layer in update_scope.expansions: {unit}")
        if not isinstance(reason, str) or not reason.strip():
            raise ContractError(f"update_scope.expansions.{unit} needs a reason")
    return reviewed, expansions


def merge(previous, payload):
    """``payload`` with the keys and layers it left out taken from ``previous``.

    An update need not resend what it does not touch; whatever it omits is the previous
    version's, verbatim (a layer's ``assessed_at`` is restored by the intake).
    """
    if not isinstance(payload, dict):
        raise ContractError("Payload must be an object")
    merged = copy.deepcopy(payload)
    for key in OWNERS:
        if key not in merged and key in previous:
            merged[key] = copy.deepcopy(previous[key])
    layers = merged.setdefault("layers", {})
    if isinstance(layers, dict):
        for name in LAYERS:
            if name not in layers and name in previous["layers"]:
                layers[name] = {k: copy.deepcopy(v) for k, v in previous["layers"][name].items()
                                if k != "assessed_at"}
    return merged


def gate(previous, merged, declaration, scope, *, base_version_id):
    """Hold a merged, schema-valid update payload to its scope.

    ``previous`` is the previous research, ``scope`` the issued scope (None with
    ``full_reason``). Returns ``(provenance, carried evidence IDs)``: a row per unit
    with its status. With ``full_reason`` every unit may change under that one reason
    and unchanged units are carried.
    """
    read_ids = set(merged.get("read_evidence_ids") or [])
    reviewed, expansions = _declaration(declaration, read_ids)
    full = "full_reason" in declaration
    if not full:
        if scope is None or scope["scope_id"] != declaration["scope_id"]:
            raise ContractError("Unknown update scope; call plan_update and use its scope.scope_id")
        if scope["base_version_id"] != base_version_id:
            raise ContractError("This scope was issued for another research version; call plan_update again")
    allowed = set() if full else set(scope["layers"])
    triggers = {} if full else {unit: [t for t in scope["triggers"]
                                       if unit in t["layers"] or (unit == L4_PRICE and "L4" in t["layers"])]
                                for unit in UNITS}
    rows, carried_ids = {}, set()
    for unit in UNITS:
        before, after = view(previous, unit), view(merged, unit)
        changed = before != after
        covered = reviewed.get(unit) or (reviewed.get("L4") if unit == L4_PRICE else None)
        row = {"triggers": triggers.get(unit, []), "previous_version_id": base_version_id}
        if unit in allowed:
            if changed:
                row["status"] = "changed"
            elif covered:
                row |= {"status": "reviewed", "evidence_ids": list(covered)}
            else:
                raise ContractError(
                    f"{unit} is in this update's scope but neither changed nor reviewed: "
                    f"list the evidence read this time in update_scope.reviewed.{unit}")
        elif changed or covered:
            reason = declaration["full_reason"] if full else expansions.get(unit)
            if not reason:
                raise ContractError(
                    f"{unit} is outside this update's scope ({', '.join(scope['layers']) or 'none'}); "
                    f"declare update_scope.expansions.{unit} with a reason to change it")
            row |= {"status": "expanded", "reason": reason}
            if covered and not changed:
                row["evidence_ids"] = list(covered)
        else:
            row["status"] = "carried"
            carried_ids |= _evidence(before)
        rows[unit] = row
    provenance = {"scope_version": VERSION, "mode": "full" if full else "scoped",
                  "scope_id": None if full else scope["scope_id"],
                  "base_version_id": base_version_id, "layers": rows}
    return provenance, carried_ids


def initial():
    """Provenance of a first research: every unit assessed from scratch."""
    return {"scope_version": VERSION, "mode": "initial", "scope_id": None,
            "base_version_id": None,
            "layers": {unit: {"status": "initial", "triggers": [], "previous_version_id": None}
                       for unit in UNITS}}
