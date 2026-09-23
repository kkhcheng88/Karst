"""Incremental triage (增量分流): watch -> plan -> check, and the news window.

``karst.updates.plan`` stays a pure function of its inputs. This module owns the
two impure edges around it and the one rule that ties them to the daily run:

* :func:`inputs` collects what a plan reads — the subject's own evidence, sources
  from other company stores that the watch subscribes to or depends on, the latest
  complete own-security price for price conditions, refresh status, method versions
  and stored relation/assumption revisions;
* :func:`record_check` re-plans and records the researcher's outcome;
* the news window: :func:`news_since` is where a daily refresh starts reading news,
  :func:`check_outcome` refuses an ``unchanged`` check the window may not advance
  past, and :func:`unread_queue` / :func:`news_pending` keep unread news queued.

The rule, in one sentence: the news window advances only past a recorded
``unchanged`` check, which requires complete source coverage and a plan that
still matches what was read (nothing unread); incomplete coverage never advances it.
No network, model call, rating or publication happens here.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import bars, updates
from .company_bundle import CompanyBundle
from .packet import instant
from .schema import ContractError

OUTCOMES = ("unchanged", "needs_reassessment", "incomplete")
# Overlap catches publication during the prior read/check and modest provider
# indexing delay; stable article identity deduplicates what is read twice.
NEWS_OVERLAP = timedelta(days=1)
# A radar member with no research and no check starts this far back.
FIRST_LOOKBACK = timedelta(days=3)


def _records(root):
    return CompanyBundle(root).records()


# --- watch -> plan -> check ----------------------------------------------------

def inputs(store, bundle, subject, *, data_dir=None, as_of=None, input_changes=()):
    """The keyword arguments of :func:`karst.updates.plan` for ``subject``, without fetching.

    External sources enter only through explicit subscriptions/dependencies. The
    full registered source set is checked, so a new transcript need not have been
    cited by the old report to be noticed.
    """
    from . import service
    from .evidence_changes import equivalent
    from .knowledge import dependency_changes
    from .store import now as state_now
    as_of = as_of or state_now()
    if updates.timestamp(as_of) > updates.timestamp(state_now()):
        raise ContractError("Update cutoff cannot be in the future")
    baseline = store.latest_research(subject)
    if baseline and updates.timestamp(baseline["created_at"]) > updates.timestamp(as_of):
        raise ContractError("Latest research did not exist at the requested cutoff; use frozen-version context")
    own = _records(bundle)
    records = list(own)
    observations = CompanyBundle(bundle).observations()
    watch = store.get_watch(subject)
    if data_dir is not None and watch:
        seen = {r["evidence_id"] for r in records}
        for other in service.company_bundles(data_dir):
            if Path(other).resolve() == Path(bundle).resolve():
                continue
            observations.extend(CompanyBundle(other).observations())
            for record in _records(other):
                if record["evidence_id"] not in seen and updates.subscribed(record, watch["payload"]):
                    records.append(record)
                    seen.add(record["evidence_id"])
    market = None
    if watch and any(c["kind"] == "price" for c in watch["payload"]["conditions"]):
        security = CompanyBundle(bundle).security() or {}
        # A supplier's bars never become this company's threshold price: only this
        # bundle's own records, and only those registered to this security.
        found = bars.series_for(bundle, security or {"security_id": subject}, as_of, records=own)
        if found.daily:
            bar = found.daily[-1]
            market = {"price": bar["close"], "at": bar["at"], "complete": bar["complete"],
                      "currency": security.get("currency"), "basis": found.source["price_basis"],
                      "adjustment": found.basis["adjust"],
                      "evidence_id": found.source["evidence_id"]}
    methods = []
    for mode in ("research", "update"):
        version = service.get_research_protocol(mode)["version"]
        methods.append(version["declared"] + "+" + version["digest"][:12])
    explicit = {(e["kind"], e["id"]): e for e in updates.validate_input_changes(input_changes)}
    # Stored revisions are authoritative; callers cannot hide one with a stale event.
    explicit.update({(e["kind"], e["id"]): e for e in dependency_changes(store, watch, as_of=as_of)})
    return {"subject": subject, "baseline": baseline, "records": records, "as_of": as_of,
            "watch": watch, "refresh_status": store.refresh_status(subject), "market": market,
            "method_versions": methods, "input_changes": list(explicit.values()),
            "observations": observations,
            "equivalent": lambda before, after: equivalent(before, after, bundle)}


def plan(store, bundle, subject, *, data_dir=None, as_of=None, input_changes=()):
    """Compare registered evidence with the latest immutable research."""
    return updates.plan(**inputs(store, bundle, subject, data_dir=data_dir, as_of=as_of,
                                 input_changes=input_changes))


def record_check(store, bundle, subject, plan_id, outcome, reason, *, data_dir=None, input_changes=()):
    """Record the researcher's outcome against the plan they read, never a stale one."""
    current = plan(store, bundle, subject, data_dir=data_dir, input_changes=input_changes)
    if current["plan_id"] != plan_id:
        raise ContractError("Inputs or conditions changed; read the new update plan before recording the check")
    return store.record_update_check(current, outcome, reason)


# --- the news window -------------------------------------------------------------

def check_outcome(plan, outcome, reason):
    """Refuse a check the news window may not advance past; the store calls this."""
    if outcome not in OUTCOMES:
        raise ContractError("Invalid update check outcome")
    updates.require_text(reason, "reason")
    if outcome == "unchanged" and (not plan["base_version_id"] or any(
            r["kind"] == "missing_baseline_inputs" for r in plan["reasons"])):
        raise ContractError("A prior research snapshot is required for an unchanged check")
    # Incomplete retrieval must stay disclosed even if the material that did
    # arrive did not change the analyst's view.
    if outcome == "unchanged" and (plan["diagnostics"] or any(
            s["status"] != "ok" for s in plan["refresh_status"])):
        raise ContractError("Incomplete sources cannot be recorded as an unchanged check")


def news_since(baseline, last_check, now=None):
    """Where a daily refresh starts reading news for one subject.

    Only an ``unchanged`` check moves the start (less the overlap); an incomplete or
    needs-reassessment check never advances it past unread news.
    """
    if last_check and last_check["payload"]["outcome"] == "unchanged":
        return (instant(last_check["created_at"]) - NEWS_OVERLAP).isoformat()
    if baseline:
        return baseline["as_of"]
    return ((now or datetime.now(timezone.utc)) - FIRST_LOOKBACK).isoformat()


def unread_queue(queued, reviewed_at, base_version_id):
    """A reassessment queue carries forward until a check is recorded after it began,
    and only while it belongs to the same research version."""
    return bool(queued.get("layers")) and not (reviewed_at and reviewed_at > queued["since"]) \
        and queued.get("base_version_id") == base_version_id


def news_pending(queue):
    """Whether queued layers still include unread news (news routes through L2)."""
    return bool(queue and "L2" in queue["layers"])
