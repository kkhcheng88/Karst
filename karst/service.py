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

from . import bars as bars_module, calculations, charts, publish as publish_module
from .fetch import broker, defeatbeta, edgar, longbridge, prices, news
from .fetch.common import utc_now, write_json, write_meta
from .fetch.registry import EvidenceRegistry
from .packet import build_packet, check_packet, check_research, confined, read_json
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
# method -> (what it answers, the params it needs). For the valuation family `params`
# IS the calculation object of contract 0.4 (its `method` key may be omitted); the
# receipt it returns is the same one a saved scenario carries.
CALCULATION_METHODS = {
    "fcff_dcf": ("annual end-of-year FCFF DCF, fair value per share (0.2/0.3 meaning)",
                 ("cashflows", "discount_rate", "terminal_growth", "cash",
                  "nonoperating_assets", "debt", "other_claims", "diluted_shares")),
    "fcff_dcf_dated": ("dated multi-stage FCFF DCF: stub, mid/end period discounting and a "
                       "terminal normalized apart from the last expansion year",
                       ("model", "bridge")),
    "forward_pe": ("forward P/E on per-share earnings; an equity multiple, so no "
                   "enterprise bridge", ("model", "equity")),
    "ev_multiple": ("EV/EBIT or EV/EBITDA with the full equity bridge",
                    ("model", "bridge")),
    "sotp": ("sum of the parts: enterprise value per part, one consolidated bridge",
             ("parts", "bridge")),
    "sensitivity": ("re-run one calculation with named inputs changed, both sides in "
                    "one receipt", ("calculation", "changes")),
    "solve_implied": ("what one input must be for this model to produce a target price; "
                      "reports no solution and multiple solutions",
                      ("calculation", "target_price", "solve_for", "bounds")),
    "risk_reward": ("per-share and percentage risk/reward", ("plan",)),
    "sma": ("simple moving average of complete bars", ("bars",)),
    "confirmed_pivots": ("confirmed local turning points", ("bars",)),
}
CALCULATION_UNITS = {
    "fcff_dcf": "absolute currency units; fair_value_per_share per share",
    "fcff_dcf_dated": "absolute currency units; fair_value_per_share per share",
    "forward_pe": "per share; equity_value in absolute currency units",
    "ev_multiple": "absolute currency units; fair_value_per_share per share",
    "sotp": "absolute currency units; fair_value_per_share per share",
    "sensitivity": "per share",
    "solve_implied": "the unit of the solved input",
    "risk_reward": "per share and ratio",
    "sma": "price",
    "confirmed_pivots": "price with confirmation timestamps",
}
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

def _registry(bundle):
    return EvidenceRegistry(bundle)


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
    return [record for root in roots for record in _registry(root).records()]


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
        record = next((r for r in _registry(candidate).records()
                       if r["evidence_id"] == evidence_id), None)
        if record is not None:
            root = candidate
            break
    if record is None:
        raise ContractError(f"Unregistered evidence: {evidence_id}")
    data = confined(Path(root), record["artifact"]["path"]).read_bytes()
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
        record = _registry(bundle).register(landing, entity_ids=list(entity_ids) or None)
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
    """Land raw returns through the source port; each failure stays a per-source diagnostic.

    Returns ``(landed, failures)``: the adapters' own LandedRecords (kind declared
    by the adapter) and one message per adapter that raised. ``clients[<adapter>]``
    is that adapter's injected client, if any.
    """
    landed, failures = [], {}
    for name in sorted(adapters):
        try:
            landed += ADAPTERS[name].fetch(security, staging, since=since,
                                           client=clients.get(name))
        except Exception as exc:  # noqa: BLE001 - one broken source must not hide the others
            failures[name] = f"{type(exc).__name__}: {exc}"
    return landed, failures


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
    registry = _registry(bundle)
    known_ids = {record["evidence_id"] for record in registry.records()}
    known_sources = {record["source_id"] for record in registry.records()}
    from .updates import latest_sources
    from .evidence_changes import equivalent
    known_records = latest_sources(registry.records(), utc_now())
    adapters = {KIND_ADAPTERS[kind] for kind in kinds}
    landed, adapter_errors = _run_adapters(staging, security, adapters, since, clients)

    result = {"added": [], "changed": [], "unchanged": [], "failed": [], "uncovered": [],
              "adapter_errors": adapter_errors, "records": [], "bundle": str(bundle),
              "staging": str(staging)}
    coverage_path = Path(staging) / news.SOURCE / 'coverage.json'
    if 'news_rss' in adapters and coverage_path.exists():
        result['news_coverage'] = read_json(coverage_path)
    entity_ids = _entity_ids(security)
    registered = []
    # Only what the adapters reported: the registry registers their records, it
    # does not go looking through the directory for files nobody claimed.
    for item in landed:
        record = registry.register(item, entity_ids=entity_ids)
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
        for adapter in sorted(adapters):
            statuses = [r["status"] for r in registered
                        if KIND_ADAPTERS.get(r["kind"]) == adapter]
            status = ("error" if adapter in adapter_errors or "error" in statuses else
                      "empty" if not statuses or "empty" in statuses else "ok")
            coverage = result.get('news_coverage') if adapter == 'news_rss' else None
            if coverage:
                status = 'ok' if coverage['status'] == 'ok' else 'error'
            store.record_refresh(security["security_id"], adapter, {
                "adapter": adapter, "status": status, "checked_at": utc_now(),
                "kinds": sorted(k for k in kinds if KIND_ADAPTERS[k] == adapter),
                "error": adapter_errors.get(adapter),
                "packet_error": result.get("packet_error"),
                **({'coverage': coverage} if coverage else {})})
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
    records = _registry(bundle).records(contract_version=CONTRACT)
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
    previous_path = bundle / "packet.json"
    previous = read_json(previous_path) if previous_path.exists() else None
    if previous and previous["security"]["security_id"] != identity.get("security_id"):
        raise ContractError("Research security differs from this bundle")
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
    # Validate completely before updating the working files. Each replacement is
    # atomic; the stored research transaction independently checks the snapshot.
    for name, value in (("evidence.json", records), ("packet.json", packet)):
        temporary = bundle / (name + "." + uuid4().hex + ".tmp")
        temporary.write_bytes(canonical(value))
        temporary.replace(bundle / name)
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
    """
    from . import updates
    from .store import now as state_now
    as_of = as_of or state_now()
    if updates.timestamp(as_of) > updates.timestamp(state_now()):
        raise ContractError("Update cutoff cannot be in the future")
    baseline = store.latest_research(subject)
    if baseline and updates.timestamp(baseline["created_at"]) > updates.timestamp(as_of):
        raise ContractError("Latest research did not exist at the requested cutoff; use frozen-version context")
    records = _records(bundle)
    if not records and (Path(bundle) / "evidence.json").exists():
        records = read_json(Path(bundle) / "evidence.json")
    def observations_at(root):
        import json
        path = Path(root) / "evidence" / "observations.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
    observations = observations_at(bundle)
    watch = store.get_watch(subject)
    if data_dir is not None and watch:
        seen = {r["evidence_id"] for r in records}
        for other in company_bundles(data_dir):
            if Path(other).resolve() == Path(bundle).resolve():
                continue
            observations.extend(observations_at(other))
            for record in _records(other):
                if record["evidence_id"] not in seen and updates.subscribed(record, watch["payload"]):
                    records.append(record)
                    seen.add(record["evidence_id"])
    market = None
    if watch and any(c["kind"] == "price" for c in watch["payload"]["conditions"]):
        packet_path = Path(bundle) / "packet.json"
        security = read_json(packet_path).get("security", {}) if packet_path.exists() else {}
        # A supplier's bars never become this company's threshold price: only this
        # bundle's own records, and only those registered to this security.
        found = bars_module.series_for(bundle, security or {"security_id": subject}, as_of,
                                       records=_records(bundle))
        if found.daily:
            bar = found.daily[-1]
            market = {"price": bar["close"], "at": bar["at"], "complete": bar["complete"],
                      "currency": security.get("currency"), "basis": found.source["price_basis"],
                      "adjustment": found.basis["adjust"],
                      "evidence_id": found.source["evidence_id"]}
    methods = []
    for mode in ("research", "update"):
        version = get_research_protocol(mode)["version"]
        methods.append(version["declared"] + "+" + version["digest"][:12])
    from .knowledge import dependency_changes
    from .evidence_changes import equivalent
    explicit = {(e["kind"], e["id"]): e for e in updates.validate_input_changes(input_changes)}
    # Stored revisions are authoritative; callers cannot hide one with a stale event.
    explicit.update({(e["kind"], e["id"]): e for e in dependency_changes(store, watch, as_of=as_of)})
    return updates.plan(subject, baseline, records, as_of=as_of, watch=watch,
                        refresh_status=store.refresh_status(subject), market=market,
                        method_versions=methods, input_changes=list(explicit.values()), observations=observations,
                        equivalent=lambda before, after: equivalent(before, after, bundle))


def record_update_check(store, bundle, subject, plan_id, outcome, reason, *, data_dir=None, input_changes=()):
    current = plan_update(store, bundle, subject, data_dir=data_dir, input_changes=input_changes)
    if current["plan_id"] != plan_id:
        raise ContractError("Inputs or conditions changed; read the new update plan before recording the check")
    return store.record_update_check(current, outcome, reason)


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
                         **_headline(row["payload"])})
    if as_of_version is None:
        records = _registry(bundle).records()
        evidence_path = Path(bundle) / "evidence.json"
        if not records and evidence_path.exists():  # a replayed bundle carries no manifest
            records = read_json(evidence_path)
        packet_path = Path(bundle) / "packet.json"
        packet = read_json(packet_path) if packet_path.exists() else None
        view = "current"
    else:
        frozen = _frozen_version(store, as_of_version)
        if frozen["subject"] != subject:
            raise ContractError("Research version belongs to a different subject")
        records, packet, view = frozen["evidence"], frozen["packet"], "as_of_research"
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
            "security": security_record((packet or {}).get("security") or {}),
            "versions": versions,
            "latest_version_id": next((v["version_id"] for v in versions
                                       if v["status"] == "latest"), None),
            "sources": sources, "pending_supplements": pending, "reviews": reviews,
            "latest_review": _review_summary(reviews),
            "research": frozen["payload"] if as_of_version is not None else None,
            "calculation_receipt": frozen["calc_receipt"] if as_of_version is not None else None,
            "changes_since_previous": research_changes(previous["payload"] if previous else None, frozen["payload"]) if as_of_version else None,
            "watch": store.get_watch(subject) if as_of_version is None else None,
            "update_plan": plan_update(store, bundle, subject, data_dir=data_dir) if as_of_version is None and as_of is None else None,
            "last_update_check": store.latest_update_check(subject) if as_of_version is None else None,
            "note": VIEW_NOTES[view] + " Source text is not inlined; read it with read_evidence."}


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


# --- calculation ------------------------------------------------------------

def calculate(method, params):
    """Arithmetic only. Whether the inputs describe the right economics is the caller's problem.

    The valuation family, its sensitivities and its reverse solve all return the same
    ``receipt`` the saved research carries, so a number quoted by a model can be matched
    against the scenario it claims to come from.
    """
    if method not in CALCULATION_METHODS:
        raise ContractError(f"Unknown calculation method {method!r}; available: "
                            + ", ".join(sorted(CALCULATION_METHODS)))
    description, required = CALCULATION_METHODS[method]
    if not isinstance(params, dict):
        raise ContractError(f"{method} params must be an object")
    missing = [key for key in required if key not in params]
    if missing:
        raise ContractError(f"{method} needs: {missing}")
    receipt = None
    if method in calculations.METHODS:
        receipt = calculations.calculate_valuation({**params, "method": method})
    elif method == "sensitivity":
        receipt = calculations.sensitivity(params["calculation"], params["changes"])
    elif method == "solve_implied":
        receipt = calculations.solve_implied(params["calculation"], params["target_price"],
                                             params["solve_for"], params["bounds"])
    elif method == "risk_reward":
        result = calculations.risk_reward(params["plan"], params.get("distributions", 0))
    elif method == "sma":
        result = {"sma": calculations.sma(params["bars"], params.get("window", 200)),
                  "window": params.get("window", 200)}
    else:
        result = {"pivots": calculations.confirmed_pivots(params["bars"], params.get("width", 2))}
    if receipt is not None:
        result = receipt["outputs"]
    answer = {"method": method, "description": description, "result": result,
              "unit": CALCULATION_UNITS[method], "inputs": params,
              "calculator_version": calculations.VERSION}
    return answer if receipt is None else {**answer, "receipt": receipt}


# The one tool facade an API adapter mounts: a single dict in, a single dict out.
# It reuses `calculate` above — there is no second copy of any formula.
CALCULATE_TOOL = {
    "name": "calculate",
    "description": "用同一個計算器算數:估值方法分派、敏感度、反推、R&R、SMA 與轉折。"
                   "回傳 receipt(calculator_version、method、inputs_digest、outputs),"
                   "引用數字時引 receipt,不要自己心算。可用 method:"
                   + "、".join(f"{name}（{text}）" for name, (text, _) in
                               sorted(CALCULATION_METHODS.items())),
    "schema": {"type": "object", "additionalProperties": False,
               "properties": {"method": {"enum": sorted(CALCULATION_METHODS)},
                              "params": {"type": "object"}},
               "required": ["method", "params"]},
}


def calculate_tool(arguments):
    """``{"method": ..., "params": {...}}`` -> the calculate result. For tool wiring."""
    if not isinstance(arguments, dict):
        raise ContractError("calculate arguments must be an object")
    unknown = set(arguments) - {"method", "params"}
    if unknown:
        raise ContractError("Unknown calculate arguments: " + ", ".join(sorted(unknown)))
    return calculate(arguments.get("method"), arguments.get("params"))


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
    bundle = Path(bundle)
    if records is None:
        records = _registry(bundle).records()
        evidence_path = bundle / "evidence.json"
        if not records and evidence_path.exists():
            records = read_json(evidence_path)
    packet_path = bundle / "packet.json"
    packet = read_json(packet_path) if packet_path.exists() else {}
    if as_of is None:
        as_of = packet.get("as_of") or utc_now()
    source = None
    security = packet.get("security") or {}
    # Which exchange's clock decides whether the last bar has closed: the packet's
    # security, else the "EXCHANGE:TICKER" subject a company store was asked about.
    exchange = security.get("exchange") or (str(title).split(":", 1)[0] if title and ":" in str(title) else None)
    if bars is not None:
        series = bars_module.views(bars)
    else:
        found = bars_module.series_for(bundle, security | {"exchange": exchange}, as_of,
                                       records=records)
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

def _intake(payload, *, bundle, role_meta, previous_research=None):
    """Default intake: contract validation only. ``karst.agents.research`` owns the real one."""
    from .agents.research import intake as research_intake  # noqa: PLC0415
    return research_intake(payload, bundle=bundle, clock=utc_now, role_meta=role_meta,
                           previous_research=previous_research,
                           previous_version_id=(previous_research or {}).get("research_id"))


def _register_requests(bundle, payload):
    """Put the payload's new supplement requests into the packet before intake.

    A researcher who could not read something asks for it; intake requires those
    requests to be registered, so the packet is rebuilt here instead of by hand in
    every runner. Same cutoff, same creation time, same previous packet: only the
    request list grows, so the rebuild is additive and the packet_id follows content.
    """
    from .packet import build_packet  # noqa: PLC0415 - avoid an import cycle at load

    packet = read_json(bundle / "packet.json")
    known = {request["request_id"]: request for request in packet["supplement_requests"]}
    incoming = [request for request in (payload.get("supplement_requests") or [])
                if isinstance(request, dict) and request.get("request_id")]
    # A researcher may reword a request it raised earlier; while it is still pending the
    # owner's latest wording replaces the registered one. Resolved requests never change.
    changed = False
    merged = []
    for request in packet["supplement_requests"]:
        update = next((r for r in incoming if r["request_id"] == request["request_id"]), None)
        if update is not None and update != request and request.get("status") == "pending":
            merged.append(update)
            changed = True
        else:
            merged.append(request)
    fresh = [request for request in incoming if request["request_id"] not in known]
    if not fresh and not changed:
        return packet
    rebuilt = build_packet(
        read_json(bundle / "evidence.json"), packet["as_of"], packet["security"],
        created_at=packet["created_at"], knowledge_basis=packet["knowledge_basis"],
        previous_packet_id=packet["previous_packet_id"],
        dependencies=[dep for dep in packet["dependencies"] if dep["kind"] != "evidence"],
        supplement_requests=merged + fresh,
        pending_updates=packet["pending_updates"], root=bundle,
        contract_version=packet["contract_version"])
    (bundle / "packet.json").write_bytes(canonical(rebuilt))
    return rebuilt


def _selected(packet, records):
    """The exact records this packet selected, in packet order. No bytes are read."""
    index = {record["evidence_id"]: record for record in records}
    chosen = []
    for evidence_id in list(packet["evidence_ids"]) + list(packet.get("diagnostic_ids", [])):
        if evidence_id not in index:
            raise ContractError(f"Unregistered evidence: {evidence_id}")
        chosen.append(index[evidence_id])
    return chosen


def _verify(bundle, packet, records, research):
    """Run the contract checks, unless this exact research already passed them.

    Reuse is fingerprint-gated: the same research bytes, the same packet and the same
    evidence versions that ``intake`` verified a moment ago. A reworded packet, a
    re-registered source, an edited conclusion or an injected intake (which cannot
    produce a credential) all fall through to the full check. The byte-level guarantee
    is not weakened: publication re-hashes every file it copies, every time.
    """
    credential = getattr(research, "verified", None)
    selected = _selected(packet, records)
    if credential is not None:
        from .agents.research import fingerprint  # noqa: PLC0415 - only when one exists

        if credential == fingerprint(research, packet, selected):
            return selected
    chosen = check_packet(packet, records, bundle)
    check_research(packet, research, chosen, bundle)
    return list(chosen.values())


def save_research(store, bundle, payload, *, subject, expected_previous_version_id=None,
                  role_meta, intake=None):
    """Validate first, store second: a rejected payload leaves no half version behind.

    The stored version freezes the packet and the evidence index it was validated
    against. The company's evidence store keeps growing after it; publishing this
    version later must not silently pick up whatever arrived in the meantime.
    """
    bundle = Path(bundle)
    # Retry identity uses the submitted analysis and frozen inputs, not the new
    # intake clock. An identical request after a lost response returns its version.
    snapshot = read_json(bundle / "packet.json") if (bundle / "packet.json").exists() else {}
    request_key = digest(canonical({"subject": subject, "previous": expected_previous_version_id,
                                   "payload": payload, "inputs": snapshot.get("evidence_ids"),
                                   "as_of": snapshot.get("as_of"), "role_meta": role_meta,
                                   "method": get_research_protocol("update" if expected_previous_version_id else "research")["version"]}))
    existing = store.get_research_request(request_key)
    if existing:
        return existing | {"idempotent_replay": True}
    if (bundle / "packet.json").exists():
        _register_requests(bundle, payload)
    # Callers may pass one role record or the full model list; intake wants the list,
    # the store keeps the researcher's own fields.
    roles = list(role_meta) if isinstance(role_meta, (list, tuple)) else [dict(role_meta)]
    researcher = next((r for r in roles if r.get("role") == "researcher"), roles[0])
    previous = (store.get_research(expected_previous_version_id)
                if expected_previous_version_id else None)
    if previous and previous["subject"] != subject:
        raise ContractError("Previous research belongs to a different subject")
    if intake is None:
        try:
            research = _intake(payload, bundle=bundle, role_meta=roles,
                               previous_research=previous["payload"] if previous else None)
        except ImportError:
            research = payload
    else:
        research = intake(payload, bundle=bundle, clock=utc_now, role_meta=roles)
    role_meta = researcher
    packet = read_json(bundle / "packet.json")
    records = read_json(bundle / "evidence.json")
    selected = _verify(bundle, packet, records, research)
    try:
        receipt = calculations.calculate(research)
    except (ContractError, KeyError, TypeError) as exc:
        # An unavailable receipt is a stated gap, never a silently empty field.
        receipt = {"calculator_version": calculations.VERSION, "status": "unavailable",
                   "reason": f"{type(exc).__name__}: {exc}"}
    return store.save_research_version(
        subject, research, expected_previous_version_id=expected_previous_version_id,
        as_of=packet["as_of"], calc_receipt=receipt, role=role_meta.get("role"),
        execution=role_meta.get("execution"), provider=role_meta.get("provider"),
        model=role_meta.get("model") or role_meta.get("model_id"),
        packet=packet, evidence=selected, request_key=request_key)


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
        packet = read_json(bundle / "packet.json")
        records = read_json(bundle / "evidence.json")
        on_disk = (read_json(bundle / "research.json")
                   if (bundle / "research.json").exists() else None)
        if on_disk != stored:
            (bundle / "research.json").write_bytes(canonical(stored))
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
