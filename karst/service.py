"""Shared operations for the CLI, the MCP server and the scheduler.

Nothing here calls a model. Research method text comes from ``karst.agents.protocol``
(owned elsewhere); this module only delegates to it. No ticker, CIK or date is
hard-coded: identity always arrives as a parameter.
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

from . import bars as bars_module, charts, publish as publish_module
from .fetch import broker, defeatbeta, edgar, longbridge, prices, news, port
from .fetch.common import utc_now, write_json, write_meta
from .company_bundle import CompanyBundle
from .agents import research as research_intake
from .packet import build_packet, read_json
from .schema import ContractError, canonical, digest
from .identity import security_record

# The source port: one entry per adapter module, each exposing KINDS and
# fetch(security, out_dir, *, since, client). Adding a source is adding a module
# and one row here — no if/elif anywhere downstream.
ADAPTERS = {"edgar": edgar, "defeatbeta": defeatbeta, "longbridge": longbridge,
            "prices": prices, "broker": broker, "news_rss": news}
# kind -> adapter name, composed from what each adapter says it covers. Kinds are
# evidence kinds (packet vocabulary), not tool names; two adapters must not claim one.
KIND_ADAPTERS = {}
for _name, _module in ADAPTERS.items():
    for _kind in _module.KINDS:
        if KIND_ADAPTERS.setdefault(_kind, _name) != _name:
            raise ContractError(f"Two adapters claim kind {_kind!r}: "
                                f"{KIND_ADAPTERS[_kind]} and {_name}")
DEFAULT_DATA_DIR = "./karst-data"
DB_NAME = "karst.sqlite"
# Ingested reports need a stated origin: who wrote it decides how much it can carry.
SOURCE_TYPES = ("broker_report", "independent_research", "news", "user_note", "other")
TAGGED_KINDS = ("industry_report",)


# --- data directory ---------------------------------------------------------

def data_root(data_dir=None):
    """``KARST_DATA_DIR`` (or the argument) is the one persistent root; default is local."""
    return Path(data_dir or os.environ.get("KARST_DATA_DIR") or DEFAULT_DATA_DIR)


def safe_name(identifier):
    """Filesystem-safe directory name for an entity id. ``XNAS:DEMO`` -> ``XNAS_DEMO``."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(identifier)).strip("._-")
    if not cleaned:
        raise ContractError(f"Cannot derive a directory name from {identifier!r}")
    return cleaned


def company_paths(data_dir, security_id):
    """One evidence store per company; every research of it registers into the same bundle."""
    root = data_root(data_dir)
    company = root / "companies" / safe_name(security_id)
    return {"root": root, "database": root / DB_NAME, "company": company,
            "bundle": company / "bundle", "releases": company / "releases",
            "tmp": root / "tmp"}


def ensure_company(store, data_dir, security):
    """Create the company's directories and register its entity rows. Returns the paths."""
    security_id = security.get("security_id") or security.get("issuer_id")
    if not security_id:
        raise ContractError("Security must carry security_id and/or issuer_id")
    paths = company_paths(data_dir, security_id)
    for key in ("bundle", "releases", "tmp"):
        paths[key].mkdir(parents=True, exist_ok=True)
    # The bundle holds the identity; the entity rows below only index it.
    security = CompanyBundle(paths["bundle"]).claim(security)
    if store is not None:
        if security.get("security_id"):
            store.upsert_entity(security["security_id"], "security", name=security.get("name"),
                                exchange=security.get("exchange"),
                                currency=security.get("currency"),
                                symbols=security.get("symbols") or {})
        if security.get("issuer_id"):
            store.upsert_entity(security["issuer_id"], "company", name=security.get("name"))
    return paths


def company_bundles(data_dir, subject=None):
    """One bundle when a subject is named, otherwise every registered company's bundle."""
    if subject:
        return [company_paths(data_dir, subject)["bundle"]]
    companies = data_root(data_dir) / "companies"
    return sorted(path / "bundle" for path in companies.glob("*") if (path / "bundle").is_dir())


def bundle_for(data_dir, subject, fixed=None):
    """The one bundle to write to: a fixed launch bundle, else the subject's company store.

    Which store a caller means is a service question, not an MCP question; the
    server passes its ``--bundle`` through as ``fixed`` and asks here.
    """
    if fixed is not None:
        return Path(fixed)
    if not subject:
        raise ContractError("Supply a subject (security id) or launch with a fixed bundle")
    return company_paths(data_dir, subject)["bundle"]


def bundles_for(data_dir, subject=None, fixed=None):
    """The bundles to read across: the fixed one, else this subject's, else every company's."""
    return [Path(fixed)] if fixed is not None else company_bundles(data_dir, subject)


# --- research method (delegated) --------------------------------------------

def get_research_protocol(mode, version=None, *, include_schema=True):
    """Delegate to ``karst.agents.protocol``; this module never authors research rules."""
    try:
        from .agents.protocol import get_research_protocol as protocol  # noqa: PLC0415
    except ImportError as exc:
        raise ContractError(
            "karst.agents.protocol is not available; the research method has one versioned "
            f"owner and the service does not substitute its own rules ({exc})") from exc
    result = protocol(mode, version)
    return result if include_schema else {k: v for k, v in result.items() if k != 'output_schema'}


# --- evidence ---------------------------------------------------------------

def _summary(record):
    params = record.get('params') or {}
    document = {key: params.get(key) for key in ('author', 'title', 'source_type')}
    return {"evidence_id": record["evidence_id"], "source_id": record["source_id"],
            "source_version": record.get('source_version'),
            **({'document': document} if any(document.values()) else {}),
            "source": record["source"], "kind": record["kind"], "status": record["status"],
            "published_at": record["published_at"], "fetched_at": record["fetched_at"],
            "period": record["period"], "truncated": record["truncated"],
            "source_url": record["source_url"], "title": document.get("title") or record["tool"],
            # A failed or empty fetch must say why through the same interface the
            # researcher reads; otherwise "no data" and "fetch broke" look identical.
            "status_reason": record.get("status_reason"),
            "known_gaps": list(record.get("known_gaps") or [])}


def _records(bundle):
    """``bundle`` may be one root or several (search across every company store)."""
    roots = [bundle] if isinstance(bundle, (str, Path)) else list(bundle)
    return [record for root in roots for record in CompanyBundle(root).records()]


def _frozen_version(store, version_id):
    """One research version with the inputs it was validated against, or a clear refusal."""
    if store is None:
        raise ContractError("Reading a version's own sources needs the store that holds it")
    version = store.get_research(version_id)
    if version is None:
        raise ContractError(f"Unknown research version: {version_id}")
    if version["packet"] is None or version["evidence"] is None:
        raise ContractError(
            f"Research version {version_id} was saved before versions carried their inputs; "
            "what it actually read cannot be reconstructed, so it is not guessed from the "
            "current company sources")
    return version


def _source_view(bundle, store, as_of_version):
    """The two questions, kept apart: what is available now, what that version used.

    Returns ``(records, packet_or_None, view_name)``. Nothing merges them: answering
    "what did version X read" with today's registry would quietly destroy versioning.
    """
    if as_of_version is None:
        return _records(bundle), None, "current"
    version = _frozen_version(store, as_of_version)
    return version["evidence"], version["packet"], "as_of_research"


VIEW_NOTES = {
    "current": "Current sources: what the company evidence store holds now.",
    "as_of_research": "As-of-research sources: exactly what this version was validated "
                      "against; later registrations are deliberately not included.",
}


def search_evidence(bundle, query=None, kind=None, date_from=None, date_to=None, *,
                    text=None, store=None, limit=20, as_of_version=None):
    """Index search only. A miss means nothing was registered here, not that nothing exists.

    ``text`` runs the SQLite FTS5 index (built when sources are registered) and
    keeps the field filters; the other arguments alone never touch full text.
    ``as_of_version`` switches the question from "what is available now" to "what did
    that research version use"; ``scope`` in the result always says which was answered.
    """
    matches = None
    if text is not None:
        if store is None:
            raise ContractError("Full-text search needs the store that holds the FTS index")
        matches = {hit["evidence_id"]: hit for hit in store.search_text(text, limit=limit)}
    records, _, view = _source_view(bundle, store, as_of_version)
    hits = []
    for record in records:
        if matches is not None and record["evidence_id"] not in matches:
            continue
        if kind and record["kind"] != kind:
            continue
        when = record["published_at"] or record["period"]["end"] or record["fetched_at"]
        if date_from and (when or "") < date_from:
            continue
        if date_to and (when or "")[:10] > date_to:
            continue
        if query:
            haystack = " ".join(str(record[field]) for field in
                                ("source", "kind", "tool", "source_url", "source_id"))
            if query.lower() not in haystack.lower():
                continue
        summary = _summary(record)
        if matches is not None:
            hit = matches[record["evidence_id"]]
            summary.update(snippet=hit["snippet"], line=hit["line"])
        hits.append(summary)
    note = VIEW_NOTES[view] + " Registered evidence only; absence here is not absence in the world."
    if matches is not None:
        note += " Full text covers text artifacts that were indexed at registration time."
    return {"scope": view, "as_of_version": as_of_version, "count": len(hits),
            "results": sorted(hits, key=lambda row: row["evidence_id"]), "note": note}


def read_evidence(bundle, evidence_id, offset=0, limit_lines=200):
    """Line-paged read of one registered artifact; line numbers are 1-based and inclusive."""
    roots = [bundle] if isinstance(bundle, (str, Path)) else list(bundle)
    record = root = None
    for candidate in roots:
        record = next((r for r in CompanyBundle(candidate).records()
                       if r["evidence_id"] == evidence_id), None)
        if record is not None:
            root = candidate
            break
    if record is None:
        raise ContractError(f"Unregistered evidence: {evidence_id}")
    data = CompanyBundle(root).artifact(record)
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return {"evidence_id": evidence_id, "binary": True, "bytes": len(data),
                "media_type": record["media_type"],
                "note": "Artifact is not UTF-8 text; read it from the bundle path directly."}
    if offset < 0 or limit_lines <= 0:
        raise ContractError("offset must be >= 0 and limit_lines > 0")
    window = lines[offset:offset + limit_lines]
    start = offset + 1 if window else None
    end = offset + len(window) if window else None
    return {"evidence_id": evidence_id, "media_type": record["media_type"],
            "total_lines": len(lines), "first_line": start, "last_line": end,
            "locator": f"L{start}-L{end}" if window else None,
            "has_more": offset + len(window) < len(lines),
            "text": "\n".join(window)}


def _check_tags(kind, entity_ids, author, published_at, source_type):
    """A report nobody can route is a report nobody will find again: tag it at the door."""
    if kind not in TAGGED_KINDS:
        return
    missing = [name for name, value in (("entity_ids", list(entity_ids)), ("author", author),
                                        ("published_at", published_at),
                                        ("source_type", source_type)) if not value]
    if missing:
        raise ContractError(
            f"kind={kind} needs {', '.join(missing)}; supply the company/industry nodes "
            f"(e.g. 'NASDAQ:XXX', 'cik:0000000001', 'industry:<slug>'), the author, the "
            f"publication date and one of {SOURCE_TYPES}")
    if source_type not in SOURCE_TYPES:
        raise ContractError(f"source_type must be one of {SOURCE_TYPES}: {source_type!r}")


def ingest_source(bundle, *, url=None, file_path=None, excerpt=None, author=None,
                  published_at=None, note=None, kind=None, entity_ids=(), title=None,
                  source_type=None, store=None):
    """Register a user-supplied document or the part of a page that was actually readable."""
    if not (url or file_path or excerpt):
        raise ContractError("Supply at least one of url, file_path or excerpt")
    kind = kind or ("industry_report" if author else "other_public")
    _check_tags(kind, entity_ids, author, published_at, source_type)
    truncated = file_path is None
    gaps = ["Excerpt only: the full document was not captured."] if truncated else []
    if url and file_path is None:
        gaps.append("URL recorded without a fetched body; the page was not archived here.")
    if author:
        gaps.append("Author statements and forecasts are the author's, not this system's judgement.")
    with tempfile.TemporaryDirectory() as staging:
        landing = Path(staging) / "ingested"
        if file_path is not None:
            source = Path(file_path)
            landing = landing.with_suffix(source.suffix or ".bin")
            landing.parent.mkdir(parents=True, exist_ok=True)
            landing.write_bytes(source.read_bytes())
        else:
            landing = landing.with_suffix(".json")
            write_json(landing, {"url": url, "author": author, "title": title,
                                 "excerpt": excerpt, "note": note})
        precision = {"published_at_precision":
                     "date" if len(str(published_at)) == 10 else "datetime"} if published_at else {}
        write_meta(landing, source="user_document", tool="ingest_source",
                   params={"url": url, "author": author, "title": title,
                           "source_type": source_type},
                   fetched_at=utc_now(), published_at=published_at,
                   published_at_basis=("Supplied by the person who ingested it; not independently "
                                       "verified" if published_at else
                                       "No publication time was supplied"),
                   **precision, period=None,
                   truncated={"is_truncated": truncated}, known_gaps=gaps, status="ok",
                   source_url=url, kind=kind, note=note)
        record = CompanyBundle(bundle).register(landing, entity_ids=list(entity_ids) or None)
    if store is not None:
        _index(store, bundle, [record], entity_kinds=True)
    summary = _summary(record)
    summary["source_type"] = source_type
    summary["entity_ids"] = record["entity_ids"]
    return summary


def _index(store, bundle, records, entity_kinds=False):
    """Mirror registered evidence into the query index (and the FTS text index)."""
    store.index_sources(records, root=bundle)
    if not entity_kinds:
        return
    for record in records:
        for entity_id in record["entity_ids"]:
            if store.get_entity(entity_id) is None:
                kind = ("industry" if str(entity_id).startswith("industry:")
                        else "company" if str(entity_id).startswith("cik:") else "security")
                store.upsert_entity(entity_id, kind)


# --- refresh ----------------------------------------------------------------

def _entity_ids(security):
    ids = {security[key] for key in ("issuer_id", "security_id") if security.get(key)}
    if not ids:
        raise ContractError("Security must carry issuer_id and/or security_id")
    return sorted(ids)


def _run_adapters(staging, security, adapters, since, clients):
    """Land raw returns through the source port, with each adapter's coverage report.

    Returns ``(landed, coverage)``: the adapters' own LandedRecords (kind declared
    by the adapter) and ``{adapter: report}`` from ``port.cover``, where a broken
    source is a failed report, not a hidden one. ``clients[<adapter>]`` is that
    adapter's injected client, if any.
    """
    landed, coverage = [], {}
    for name in sorted(adapters):
        records, coverage[name] = port.cover(name, lambda: ADAPTERS[name].fetch(
            security, staging, since=since, client=clients.get(name)))
        landed += records
    return landed, coverage


def refresh_sources(data_dir, security, kinds, since=None, clients=None, store=None,
                    bundle=None, staging=None):
    """Fetch the requested kinds into the company's own evidence store and report what changed.

    Added / changed / unchanged is decided by the registry's content fingerprint,
    never by ``fetched_at``: re-fetching the same bytes is an observation, not news.
    Every research of one company registers into the same bundle; the raw landing
    goes to ``<data>/tmp/<run>/`` and is scratch.
    """
    security = security_record(security)
    clients = clients or {}
    unknown = sorted(set(kinds) - set(KIND_ADAPTERS))
    if unknown:
        raise ContractError(f"No adapter registered for kinds: {unknown}")
    if bundle is None or staging is None:
        paths = ensure_company(store, data_dir, security)
        bundle = bundle or paths["bundle"]
        staging = staging or paths["tmp"] / "-".join(
            ["refresh", utc_now().replace(":", ""),
             safe_name(security.get("security_id") or security.get("issuer_id")),
             uuid4().hex[:8]])  # one landing per run: stale files must not be re-registered
    Path(staging).mkdir(parents=True, exist_ok=True)
    company = CompanyBundle(bundle)
    current = company.records()
    known_ids = {record["evidence_id"] for record in current}
    known_sources = {record["source_id"] for record in current}
    from .updates import latest_sources
    from .evidence_changes import equivalent
    known_records = latest_sources(current, utc_now())
    adapters = {KIND_ADAPTERS[kind] for kind in kinds}
    landed, coverage = _run_adapters(staging, security, adapters, since, clients)

    result = {"added": [], "changed": [], "unchanged": [], "failed": [], "uncovered": [],
              "coverage": coverage, "records": [], "bundle": str(bundle),
              "staging": str(staging)}
    entity_ids = _entity_ids(security)
    registered = []
    # Only what the adapters reported: the registry registers their records, it
    # does not go looking through the directory for files nobody claimed.
    for record in company.register_many(landed, entity_ids=entity_ids):
        registered.append(record)
        result["records"].append(_summary(record))
        evidence_id = record["evidence_id"]
        if record["status"] == "error":
            bucket = "failed"
        elif record["status"] == "empty":
            bucket = "uncovered"
        elif evidence_id in known_ids or equivalent(known_records.get(record['source_id']), record, bundle):
            bucket = "unchanged"
        elif record["source_id"] in known_sources:
            bucket = "changed"
        else:
            bucket = "added"
        result[bucket].append(evidence_id)
        known_ids.add(evidence_id)
        known_sources.add(record["source_id"])
    for bucket in ("added", "changed", "unchanged", "failed", "uncovered"):
        result[bucket] = sorted(set(result[bucket]))
    if store is not None and registered:
        _index(store, bundle, registered)
    # Refresh is the mutation that advances the working evidence snapshot. Saved
    # versions retain their own inputs; this never rewrites a research version.
    if registered:
        try:
            result["research_input"] = prepare_research(bundle, security)
        except ContractError as exc:
            result["packet_error"] = str(exc)
    if store is not None:
        for adapter, report in sorted(coverage.items()):
            store.record_refresh(security["security_id"], adapter, {
                **report, "checked_at": utc_now(),
                "kinds": sorted(k for k in kinds if KIND_ADAPTERS[k] == adapter),
                "packet_error": result.get("packet_error")})
        result["update_plan"] = plan_update(store, bundle, security["security_id"], data_dir=data_root(data_dir))
    return result


def prepare_research(bundle, security, *, as_of=None, evidence_ids=None):
    """Freeze registered inputs for a research run, without invoking a model.

    An explicit selection is supported, but unknown IDs and late observations fail
    instead of silently disappearing. Diagnostics and missing requirements survive.
    Older research versions remain immutable in the store.
    """
    from .agents.research import CONTRACT
    from .schema import schemas

    security = security_record(security)
    bundle = Path(bundle)
    company = CompanyBundle(bundle)
    records = company.records(contract_version=CONTRACT)
    if evidence_ids is not None:
        ids = list(evidence_ids)
        index = {r["evidence_id"]: r for r in records}
        if len(ids) != len(set(ids)) or not set(ids) <= set(index):
            raise ContractError("Evidence selection contains duplicates or unknown IDs")
        records = [index[eid] for eid in ids]
    if not records:
        raise ContractError("No registered sources; refresh or ingest evidence first")
    fields = schemas(CONTRACT)["evidence"]["$defs"]["security"]["properties"]
    identity = {key: security[key] for key in fields if key in security}
    company.claim(security)  # refuses a different security
    previous = company.packet()
    now = utc_now()
    # Keep pending requests; resolved ones belong to the immutable prior snapshot.
    requests = [r for r in (previous or {}).get("supplement_requests", [])
                if r["status"] == "pending"]
    packet = build_packet(
        records, as_of or now, identity, created_at=now, root=bundle,
        contract_version=CONTRACT,
        previous_packet_id=(previous or {}).get("packet_id"),
        dependencies=[d for d in (previous or {}).get("dependencies", [])
                      if d["kind"] != "evidence"],
        supplement_requests=requests)
    # Validated completely before the working snapshot is replaced (atomically);
    # the stored research transaction independently checks the snapshot.
    company.save_working(packet, records)
    return {"packet_id": packet["packet_id"], "as_of": packet["as_of"],
            "security": identity, "evidence_ids": packet["evidence_ids"],
            "diagnostic_ids": packet["diagnostic_ids"],
            "requirements": packet["requirements"]}


# --- research state ---------------------------------------------------------

def _headline(payload):
    if not isinstance(payload, dict):
        return {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {key: (payload.get(key) or summary.get(key)) for key in
            ("rating", "execution_state", "headline", "key_assumption", "strongest_counter")
            if payload.get(key) is not None or summary.get(key) is not None}


def plan_update(store, bundle, subject, *, data_dir=None, as_of=None, input_changes=()):
    """Compare registered evidence with the latest immutable research, without fetching.

    External sources enter only through explicit subscriptions/dependencies. The
    full registered source set is checked, so a new transcript need not have been
    cited by the old report to be noticed.

    ``scope`` is the update scope the system issues and records for the next update of
    the latest research (None without one): the layers that update may rewrite, what
    triggered each, and carried layers that expired. ``save_research`` names it by
    ``scope_id``; it is not part of the plan's identity.
    """
    from . import triage
    plan = triage.plan(store, bundle, subject, data_dir=data_dir, as_of=as_of,
                       input_changes=input_changes)
    plan["scope"] = triage.issue_scope(store, bundle, subject, plan)
    return plan


def record_update_check(store, bundle, subject, plan_id, outcome, reason, *, data_dir=None, input_changes=()):
    from . import triage
    return triage.record_check(store, bundle, subject, plan_id, outcome, reason,
                               data_dir=data_dir, input_changes=input_changes)


def get_research_context(store, bundle, subject, as_of=None, as_of_version=None, *, data_dir=None):
    """Directory, not content: existing versions, the sources, what is still open.

    Two questions that must not be merged into "always read the latest":

    * no ``as_of_version`` — **current sources**: what the company evidence store
      holds now, and what is open against its current packet;
    * with one — **as-of-research sources**: exactly what that version was validated
      against, from its own frozen packet and evidence index.

    ``sources_view`` names the answer either way. Each version row carries its
    predecessor and its own publication id, so the chain reads in both directions.
    """
    versions = []
    for row in store.list_research(subject):
        if as_of and (row["as_of"] or "") > as_of:
            continue
        versions.append({"version_id": row["version_id"], "as_of": row["as_of"],
                         "status": row["status"], "created_at": row["created_at"],
                         "previous_version_id": row["previous_version_id"],
                         "publication_path": row["publication_path"],
                         "publication_id": (publication_id_at(row["publication_path"])
                                            if row["publication_path"] else None),
                         "role": row["role"], "execution": row["execution"],
                         "provider": row["provider"], "model": row["model"],
                         "layers": _layer_dates(row["payload"], row.get("provenance")),
                         **_headline(row["payload"])})
    if as_of_version is None:
        company = CompanyBundle(bundle)
        records, packet, view = company.records(), company.packet(), "current"
        security = company.security() or {}
    else:
        frozen = _frozen_version(store, as_of_version)
        if frozen["subject"] != subject:
            raise ContractError("Research version belongs to a different subject")
        records, packet, view = frozen["evidence"], frozen["packet"], "as_of_research"
        security = security_record(packet.get("security") or {})
    sources = [_summary(record) for record in records]
    pending = [request for request in (packet or {}).get("supplement_requests", [])
               if request["status"] == "pending"]
    reviews = [{"job_id": job["job_id"], "status": job["status"], "input_ref": job["input_ref"],
                "result_ref": job["result_ref"], "provider": job["provider"],
                "model": job["model"]}
               for job in store.list_jobs(kind="review")
               if (job["input_ref"] or {}).get("subject") == subject]
    from .updates import research_changes
    from .knowledge import subject_inputs
    previous = store.get_research(frozen["previous_version_id"]) if as_of_version and frozen["previous_version_id"] else None
    return {"subject": subject, "as_of": as_of, "as_of_version": as_of_version,
            "knowledge": subject_inputs(store, subject, as_of=frozen["created_at"] if as_of_version else as_of),
            "sources_view": view, "packet_id": (packet or {}).get("packet_id"),
            "security": security,
            "versions": versions,
            "latest_version_id": next((v["version_id"] for v in versions
                                       if v["status"] == "latest"), None),
            "sources": sources, "pending_supplements": pending, "reviews": reviews,
            "latest_review": _review_summary(reviews),
            "research": frozen["payload"] if as_of_version is not None else None,
            "calculation_receipt": frozen["calc_receipt"] if as_of_version is not None else None,
            "layer_provenance": frozen.get("provenance") if as_of_version is not None else None,
            "changes_since_previous": research_changes(previous["payload"] if previous else None, frozen["payload"]) if as_of_version else None,
            "watch": store.get_watch(subject) if as_of_version is None else None,
            "update_plan": plan_update(store, bundle, subject, data_dir=data_dir) if as_of_version is None and as_of is None else None,
            "last_update_check": store.latest_update_check(subject) if as_of_version is None else None,
            "note": VIEW_NOTES[view] + " Source text is not inlined; read it with read_evidence."}


def _layer_dates(payload, provenance):
    """Each layer's assessed date and whether this version carried it (None: not recorded,
    a version saved before layer provenance existed)."""
    rows = (provenance or {}).get("layers") or {}
    layers = (payload or {}).get("layers") if isinstance(payload, dict) else None
    if not isinstance(layers, dict):
        return None
    return {name: {"assessed_at": layer.get("assessed_at") if isinstance(layer, dict) else None,
                   "status": (rows.get(name) or {}).get("status")}
            for name, layer in layers.items()}


def _review_summary(reviews):
    """The newest finished review, in one line: verdict, hardest challenge, target layer.

    The reviewer never returns a second rating, so a summary is a challenge to dispose
    of, not a vote. Unfinished jobs stay out: a pending review is not an opinion.
    """
    rank = {"blocking": 0, "material": 1, "minor": 2}
    done = next((row for row in reviews
                 if row["status"] == "done" and isinstance(row["result_ref"], dict)), None)
    if done is None:
        return None
    result = done["result_ref"]
    verdict = result.get("verdict_on_dispute") or {}
    challenges = sorted(result.get("challenges") or [],
                        key=lambda item: rank.get(item.get("severity"), 9))
    strongest = challenges[0] if challenges else None
    return {"job_id": done["job_id"], "research_id": result.get("research_id"),
            "verdict": verdict.get("verdict"), "reasoning": verdict.get("reasoning"),
            "strongest_challenge": None if strongest is None else
            {key: strongest.get(key) for key in ("target_layer", "claim", "severity")},
            "challenges": len(challenges),
            "new_evidence_requests": len(result.get("new_evidence_requests") or [])}


def render_charts(bundle, out_dir, *, as_of=None, bars=None, records=None, store=None, title=None):
    """Month / week / day / recent charts + derived numbers for registered prices.

    The arrays are built from the registered candlestick evidence, charted, measured
    and dropped: only the PNGs and ``derived.json`` land in ``out_dir``. Charting
    something that was never registered is not offered — a chart the researcher can
    cite has to come from evidence they can read.

    Each PNG comes back as an **artifact**: a content-addressed id, its hash, the
    cutoff it was drawn to and the evidence it came from. Given a ``store`` the
    artifacts are registered there, which is what lets a remote client ask for the
    image itself (``read_chart``) instead of a path it cannot open.
    """
    company = CompanyBundle(bundle)
    records = company.records() if records is None else records
    if as_of is None:
        as_of = (company.packet() or {}).get("as_of") or utc_now()
    source = None
    # Which exchange's clock decides whether the last bar has closed: the store's own
    # security, never a guess from the subject string.
    security = company.security() or {}
    if bars is not None:
        series = bars_module.views(bars)
    else:
        found = bars_module.series_for(bundle, security, as_of, records=records)
        series, source = found.views, found.source
    if not series or not series.get("D"):
        raise ContractError("No registered daily candlesticks to chart for this subject as of "
                            f"{as_of}; refresh the prices kind first. A snapshot fetched after "
                            "that cutoff is not read back into it (KARST-250): re-render at a "
                            "cutoff the evidence existed at.")
    if not bars_module.enough(series["D"], "chart"):
        raise ContractError('Insufficient history for an analytical chart: fewer than two daily bars. '
                            'Refresh full prices without since; do not infer trend or support from one candle.')
    # A company store that has never carried a packet still knows what it is: the
    # caller's subject names the chart rather than a bare "price".
    title = " ".join(str(security[key]) for key in ("exchange", "ticker") if security.get(key)) or title
    result = charts.render(series["D"], out_dir, as_of=as_of, source=source, title=title or None)
    if store is not None:
        for artifact in result["artifacts"]:
            store.register_chart(artifact)
    return {"data_as_of": result["derived"]["data_as_of"], "files": result["files"],
            "artifacts": result["artifacts"], "derived": result["derived"], "note": charts.NOTE}


def without_local_paths(result):
    """The same chart result, minus this host's file layout: a remote caller reads a
    chart by artifact id, and a path it cannot open only invites a pretend read."""
    return {key: value for key, value in result.items() if key != "files"} | {
        "artifacts": [{k: v for k, v in artifact.items() if k != "path"}
                      for artifact in result["artifacts"]]}


def chart_artifact(store, artifact_id):
    """One registered chart, verified against its recorded hash before it is served."""
    record = store.get_chart(artifact_id)
    if record is None:
        raise ContractError(f"Unknown chart artifact: {artifact_id}. Render the charts "
                            "first; only registered artifacts can be read.")
    path = Path(record["path"])
    if not path.is_file():
        raise ContractError(f"Chart artifact {artifact_id} is registered but its file is gone")
    data = path.read_bytes()
    if digest(data) != record["sha256"]:
        raise ContractError(f"Chart artifact {artifact_id} no longer matches its registered "
                            "hash; re-render before reading it")
    return record | {"data": data}


# --- save / publish ---------------------------------------------------------

def save_research(store, bundle, payload, *, subject, expected_previous_version_id=None,
                  role_meta, update_scope=None):
    """Research intake (``agents.research.save``): check once, then append a version.

    The stored version freezes the packet and the evidence index it was validated
    against, so publishing it later never picks up evidence that arrived since. An
    update names its ``update_scope`` (``plan_update``'s ``scope.scope_id``, or a
    declared ``full_reason``); see ``karst.scope``.
    """
    return research_intake.save(store, bundle, payload, subject=subject, role_meta=role_meta,
                                previous_version_id=expected_previous_version_id,
                                clock=utc_now, update_scope=update_scope)


def _check_technical_basis(research, rebuilt, gaps, as_of):
    """Refuse to publish a chart materially thinner than the one the version measured.

    The version recorded how many daily bars its technical reading stood on. Rebuilding
    that series from the version's own evidence can come up short — the series was never
    registered, or the only snapshot that holds it was fetched after this cutoff and the
    replay guard (KARST-250) will not read it back. Either way the page still renders:
    fewer pivots, no 200-day average, and nothing on it saying so. A publication that
    quietly loses figures somebody already read is worse than one that fails.
    """
    recorded = (((research.get("technical") or {}).get("derived") or {})
                .get("bars_count") or {}).get("D") or 0
    daily = (rebuilt or {}).get("D") or []
    if bars_module.enough(daily, "publication", recorded=recorded):
        return
    found = len(daily)
    cause = ("; ".join(gaps) if gaps else
             f"no prices evidence in this version holds a daily series as of {as_of}")
    raise ContractError(
        f"This version's technical reading stands on {recorded} daily bars; rebuilding "
        f"them from its own evidence yields {found}. Publishing would silently drop the "
        f"pivots and averages behind the chart. Cause: {cause}. Pass bars= from a "
        "registered series, or re-render at a cutoff the evidence existed at.")


def _publication_bars(bundle, packet, records, research, bars, bars_provider):
    """This run's price arrays: from registered candlesticks, else from a live provider.

    Either way they are transient — charted and measured, never registered and never
    written back into research.json (0.3). A provider that fails leaves the page with
    its derived numbers; it does not fail the publication. ``records`` are the version's
    own evidence index, so republishing an old version does not chart newer prices.
    """
    if (research.get("technical") or {}).get("views"):
        # An older saved research already carries its arrays; a second set would be
        # two sources of truth for the same chart.
        return None
    if bars is not None:  # the caller vouched for these; nothing was rebuilt to compare
        return bars_module.views(bars)
    as_of = packet["as_of"]
    found = bars_module.series_for(bundle, packet.get("security"), as_of, records=records)
    rebuilt = found.views
    if not rebuilt and callable(bars_provider):
        rebuilt = bars_module.views(bars_provider(packet["security"], as_of))
    _check_technical_basis(research, rebuilt, found.gaps, as_of)
    return rebuilt


def publication_id_at(page_path):
    """A release's own id, read from the manifest beside a recorded page path."""
    directory = Path(page_path).parent
    manifest = directory / "publication.json"
    if manifest.is_file():
        return read_json(manifest).get("publication_id")
    return directory.name if directory.name.startswith("pub-") else None


def previous_publication_id(store, version):
    """The release this one follows: the nearest earlier version of the same subject
    that was actually published. Unpublished versions in between are skipped, an
    unbroken chain matters more than counting versions."""
    rows = {row["version_id"]: row for row in store.list_research(version["subject"], limit=1000)}
    current, seen = version["previous_version_id"], set()
    while current and current not in seen:
        seen.add(current)
        row = rows.get(current)
        if row is None:
            return None
        if row["publication_path"]:
            return publication_id_at(row["publication_path"])
        current = row["previous_version_id"]
    return None


def publish_research(store, bundle, version_id, output_dir, bars=None, bars_provider=None):
    """Write the release directory first, then record where it is.

    The release is built from **this version's own** packet and evidence index, not
    from whatever the company store holds today: republishing an old version after
    the company gained new sources yields the same publication, byte for byte. Only
    the source bytes come from the company store — they are content-addressed, so the
    same fingerprint is the same file, and publication re-hashes every one it copies.

    ``bars`` (or whatever ``bars_provider`` returns) are this run's price arrays: they
    reach the chart and the measurements, not the saved research.
    """
    version = store.get_research(version_id)
    if version is None:
        raise ContractError(f"Unknown research version: {version_id}")
    bundle = Path(bundle)
    stored = version["payload"]
    packet, records = version["packet"], version["evidence"]
    snapshot = (packet, records, stored)
    inputs_from = "version_snapshot"
    if packet is None or records is None:
        # Saved before versions carried their inputs: fall back to the bundle as it
        # stands, and say so rather than pretending the version was pinned.
        inputs_from, snapshot = "bundle", None
        company = CompanyBundle(bundle)
        packet, records = company.working()
        if company.research() != stored:
            company.save_research(stored)
    from .page.company import render_company_index  # noqa: PLC0415 - it reads this module

    release = publish_module.publish(
        bundle, output_dir, snapshot=snapshot,
        previous_publication_id=previous_publication_id(store, version),
        bars=_publication_bars(bundle, packet, records, stored, bars, bars_provider))
    page = (Path(release) / "index.html").resolve()
    store.set_publication_path(version_id, page)
    index = Path(output_dir) / "index.html"
    index.write_text(render_company_index(store, bundle, packet["security"], Path(output_dir)),
                     encoding="utf-8")
    return {"version_id": version_id, "publication_dir": str(Path(release).resolve()),
            "index_html": str(page), "company_index": str(index.resolve()),
            "publication_id": Path(release).name, "inputs_from": inputs_from}


# --- review jobs ------------------------------------------------------------

REVIEW_ADAPTERS = {"anthropic": "anthropic_adapter", "openai": "openai_adapter"}


def _review_adapter(provider):
    from importlib import import_module  # noqa: PLC0415

    if provider not in REVIEW_ADAPTERS:
        raise ContractError("API review needs a provider with an adapter: "
                            + ", ".join(sorted(REVIEW_ADAPTERS)))
    return import_module(f".agents.adapters.{REVIEW_ADAPTERS[provider]}", __package__)


def _stage_review_task(store, bundle, version_id, dispute, evidence_ids, task_dir):
    from .agents.review import build_review_task  # noqa: PLC0415

    version = store.get_research(version_id)
    if version is None:
        raise ContractError(f"Unknown research version: {version_id}")
    protocol = get_research_protocol("review")
    build_review_task(version["payload"], dispute, list(evidence_ids), protocol,
                      bundle=bundle, destination=task_dir)
    return protocol


def request_review(store, *, subject, version_id, dispute, evidence_ids, reviewer=None,
                   bundle=None, task_dir=None, transport=None, budget=None):
    """Open a review job; with ``execution='api'`` also run it and write the result back.

    The same (version_id, dispute) is not paid for twice: an existing job that has not
    failed is returned as it stands. A request that was sent but whose outcome is
    unknown lands as ``needs_check`` — it is reconciled by hand, never auto-resent.
    """
    reviewer = reviewer or {"execution": "interactive"}
    execution = reviewer.get("execution", "interactive")
    if execution not in ("interactive", "api"):
        raise ContractError("reviewer execution must be interactive or api")
    fingerprint = digest(canonical({"version_id": version_id, "dispute": dispute}))
    for existing in store.list_jobs(kind="review"):
        reference = existing["input_ref"] or {}
        if reference.get("dispute_digest") == fingerprint and existing["status"] != "failed":
            return existing
    job = store.create_job("review", role="reviewer", execution=execution,
                           provider=reviewer.get("provider"), model=reviewer.get("model"),
                           input_ref={"subject": subject, "version_id": version_id,
                                      "dispute": dispute, "evidence_ids": list(evidence_ids),
                                      "dispute_digest": fingerprint, "task_dir": str(task_dir)
                                      if task_dir else None})
    if execution != "api":
        return job
    return _run_review(store, job, reviewer, bundle=bundle, task_dir=task_dir,
                       dispute=dispute, version_id=version_id, evidence_ids=evidence_ids,
                       transport=transport, budget=budget)


def _run_review(store, job, reviewer, *, bundle, task_dir, dispute, version_id,
                evidence_ids, transport, budget):
    from .agents.adapters import ResultUnknown  # noqa: PLC0415

    job_id = job["job_id"]
    store.transition(job_id, "claimed", claimed_by=reviewer.get("provider") or "api")
    store.transition(job_id, "running")
    try:
        adapter = _review_adapter(reviewer.get("provider"))
        if task_dir is None:
            raise ContractError("API review needs a task_dir to stage the task in")
        if not Path(task_dir).exists():
            _stage_review_task(store, bundle, version_id, dispute, evidence_ids, task_dir)
        run = adapter.run(task_dir, reviewer.get("model"), budget, transport=transport)
    except ResultUnknown as exc:
        return store.transition(job_id, "needs_check", error=str(exc))
    except Exception as exc:  # noqa: BLE001 - a failed review is a job outcome, not a crash
        return store.transition(job_id, "failed", error=f"{type(exc).__name__}: {exc}")
    try:
        submit_review(store, job_id, run["result"])
    except ContractError as exc:
        return store.transition(job_id, "failed", usage=run["usage"],
                                error=f"review result rejected: {exc}")
    return store.transition(job_id, usage=run["usage"])


def claim_review(store, job_id, claimed_by):
    """Take a pending job, then start it. A second claimer is refused by the store."""
    store.transition(job_id, "claimed", claimed_by=claimed_by)
    return store.transition(job_id, "running")


def submit_review(store, job_id, result):
    """Accept the reviewer's result, validated against ``karst.agents.review``.

    The same entry point serves the interactive client and the API path; a result that
    does not hold up raises here rather than being stored as if it did.
    """
    if not isinstance(result, dict):
        raise ContractError("Review result must be a JSON object")
    try:
        from .agents.review import validate_review  # noqa: PLC0415
    except ImportError:
        pass
    else:
        result = validate_review(result)
    return store.transition(job_id, "done", result_ref=result)


def get_job(store, job_id):
    job = store.get_job(job_id)
    if job is None:
        raise ContractError(f"Unknown job: {job_id}")
    return job
