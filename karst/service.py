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

from . import calculations, publish as publish_module
from .fetch import defeatbeta, edgar, longbridge
from .fetch.common import utc_now, write_json, write_meta
from .fetch.registry import EvidenceRegistry
from .packet import check_packet, check_research, confined, read_json
from .schema import ContractError, canonical, digest

# kind -> adapter key. Kinds are evidence kinds (packet vocabulary), not tool names.
KIND_ADAPTERS = {
    "filing": "edgar", "filing_index": "edgar",
    "transcript": "defeatbeta", "financials": "defeatbeta", "calendar": "defeatbeta",
    "profile": "defeatbeta",
    "prices": "longbridge", "quote": "longbridge",
}
CALCULATION_METHODS = {
    "fcff_dcf": ("fair value per share", ("cashflows", "discount_rate", "terminal_growth",
                                          "cash", "nonoperating_assets", "debt",
                                          "other_claims", "diluted_shares")),
    "risk_reward": ("per-share and percentage risk/reward", ("plan",)),
    "sma": ("simple moving average of complete bars", ("bars",)),
    "confirmed_pivots": ("confirmed local turning points", ("bars",)),
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


# --- research method (delegated) --------------------------------------------

def get_research_protocol(mode, version=None):
    """Delegate to ``karst.agents.protocol``; this module never authors research rules."""
    try:
        from .agents.protocol import get_research_protocol as protocol  # noqa: PLC0415
    except ImportError as exc:
        raise ContractError(
            "karst.agents.protocol is not available; the research method has one versioned "
            f"owner and the service does not substitute its own rules ({exc})") from exc
    return protocol(mode, version)


# --- evidence ---------------------------------------------------------------

def _registry(bundle):
    return EvidenceRegistry(bundle)


def _summary(record):
    return {"evidence_id": record["evidence_id"], "source_id": record["source_id"],
            "source": record["source"], "kind": record["kind"], "status": record["status"],
            "published_at": record["published_at"], "fetched_at": record["fetched_at"],
            "period": record["period"], "truncated": record["truncated"],
            "source_url": record["source_url"], "title": record["tool"],
            # A failed or empty fetch must say why through the same interface the
            # researcher reads; otherwise "no data" and "fetch broke" look identical.
            "status_reason": record.get("status_reason"),
            "known_gaps": list(record.get("known_gaps") or [])}


def _records(bundle):
    """``bundle`` may be one root or several (search across every company store)."""
    roots = [bundle] if isinstance(bundle, (str, Path)) else list(bundle)
    return [record for root in roots for record in _registry(root).records()]


def search_evidence(bundle, query=None, kind=None, date_from=None, date_to=None, *,
                    text=None, store=None, limit=20):
    """Index search only. A miss means nothing was registered here, not that nothing exists.

    ``text`` runs the SQLite FTS5 index (built when sources are registered) and
    keeps the field filters; the other arguments alone never touch full text.
    """
    matches = None
    if text is not None:
        if store is None:
            raise ContractError("Full-text search needs the store that holds the FTS index")
        matches = {hit["evidence_id"]: hit for hit in store.search_text(text, limit=limit)}
    hits = []
    for record in _records(bundle):
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
    note = "Registered evidence only; absence here is not absence in the world."
    if matches is not None:
        note += " Full text covers text artifacts that were indexed at registration time."
    return {"count": len(hits), "results": sorted(hits, key=lambda row: row["evidence_id"]),
            "note": note}


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

def _cik(security):
    value = security.get("cik") or str(security.get("issuer_id", "")).split(":")[-1]
    if not str(value).isdigit():
        raise ContractError("Security must carry a CIK (cik or issuer_id 'cik:<digits>')")
    return str(value).zfill(10)


def _entity_ids(security):
    ids = {security[key] for key in ("issuer_id", "security_id") if security.get(key)}
    if not ids:
        raise ContractError("Security must carry issuer_id and/or security_id")
    return sorted(ids)


def _run_adapters(staging, security, adapters, since, clients):
    """Land raw returns for the requested adapters; each failure stays a per-source diagnostic."""
    failures = {}
    for name in sorted(adapters):
        try:
            if name == "edgar":
                edgar.fetch_filings(_cik(security), staging, ticker=security.get("ticker"),
                                    http_get=clients.get("edgar_http_get"))
            elif name == "defeatbeta":
                defeatbeta.fetch_company(security["ticker"], staging,
                                         ticker_factory=clients.get("defeatbeta_ticker_factory"))
            elif name == "longbridge":
                longbridge.fetch_company(longbridge.symbol_for(security), staging, start=since,
                                         client=clients.get("longbridge"),
                                         factory=clients.get("longbridge_factory",
                                                             longbridge.client_factory))
        except Exception as exc:  # noqa: BLE001 - one broken source must not hide the others
            failures[name] = f"{type(exc).__name__}: {exc}"
    return failures


def refresh_sources(data_dir, security, kinds, since=None, clients=None, store=None,
                    bundle=None, staging=None):
    """Fetch the requested kinds into the company's own evidence store and report what changed.

    Added / changed / unchanged is decided by the registry's content fingerprint,
    never by ``fetched_at``: re-fetching the same bytes is an observation, not news.
    Every research of one company registers into the same bundle; the raw landing
    goes to ``<data>/tmp/<run>/`` and is scratch.
    """
    from .pipeline import pair_staging  # noqa: PLC0415 - avoid an import cycle at module load

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
    adapters = {KIND_ADAPTERS[kind] for kind in kinds}
    adapter_errors = _run_adapters(staging, security, adapters, since, clients)

    result = {"added": [], "changed": [], "unchanged": [], "failed": [], "uncovered": [],
              "adapter_errors": adapter_errors, "records": [], "bundle": str(bundle),
              "staging": str(staging)}
    entity_ids = _entity_ids(security)
    registered = []
    for meta_path, raws in pair_staging(staging):
        for raw in raws or [None]:
            record = registry.register(raw, meta_path, entity_ids=entity_ids)
            registered.append(record)
            result["records"].append(_summary(record))
            evidence_id = record["evidence_id"]
            if record["status"] == "error":
                bucket = "failed"
            elif record["status"] == "empty":
                bucket = "uncovered"
            elif evidence_id in known_ids:
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
    return result


# --- research state ---------------------------------------------------------

def _headline(payload):
    if not isinstance(payload, dict):
        return {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {key: (payload.get(key) or summary.get(key)) for key in
            ("rating", "execution_state", "headline", "key_assumption", "strongest_counter")
            if payload.get(key) is not None or summary.get(key) is not None}


def get_research_context(store, bundle, subject, as_of=None):
    """Directory, not content: existing versions, the source index, what is still open."""
    versions = []
    for row in store.list_research(subject):
        if as_of and (row["as_of"] or "") > as_of:
            continue
        versions.append({"version_id": row["version_id"], "as_of": row["as_of"],
                         "status": row["status"], "created_at": row["created_at"],
                         "publication_path": row["publication_path"],
                         "role": row["role"], "execution": row["execution"],
                         "provider": row["provider"], "model": row["model"],
                         **_headline(row["payload"])})
    records = _registry(bundle).records()
    evidence_path = Path(bundle) / "evidence.json"
    if not records and evidence_path.exists():  # a replayed bundle carries no manifest
        records = read_json(evidence_path)
    sources = [_summary(record) for record in records]
    packet_path = Path(bundle) / "packet.json"
    pending = []
    if packet_path.exists():
        packet = read_json(packet_path)
        pending = [request for request in packet["supplement_requests"]
                   if request["status"] == "pending"]
    reviews = [{"job_id": job["job_id"], "status": job["status"], "input_ref": job["input_ref"],
                "result_ref": job["result_ref"], "provider": job["provider"],
                "model": job["model"]}
               for job in store.list_jobs(kind="review")
               if (job["input_ref"] or {}).get("subject") == subject]
    return {"subject": subject, "as_of": as_of, "versions": versions,
            "latest_version_id": next((v["version_id"] for v in versions
                                       if v["status"] == "latest"), None),
            "sources": sources, "pending_supplements": pending, "reviews": reviews,
            "latest_review": _review_summary(reviews),
            "note": "Source text is not inlined; read it with read_evidence."}


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
    """Arithmetic only. Whether the inputs describe the right economics is the caller's problem."""
    if method not in CALCULATION_METHODS:
        raise ContractError(f"Unknown calculation method {method!r}; available: "
                            + ", ".join(sorted(CALCULATION_METHODS)))
    description, required = CALCULATION_METHODS[method]
    if method == "risk_reward":
        result = calculations.risk_reward(params["plan"], params.get("distributions", 0))
        unit = "per share and ratio"
    elif method == "fcff_dcf":
        missing = [key for key in required if key not in params]
        if missing:
            raise ContractError(f"fcff_dcf needs: {missing}")
        result = calculations.fcff_dcf(params)
        unit = "absolute currency units; fair_value_per_share per share"
    elif method == "sma":
        result = {"sma": calculations.sma(params["bars"], params.get("window", 200)),
                  "window": params.get("window", 200)}
        unit = "price"
    else:
        result = {"pivots": calculations.confirmed_pivots(params["bars"], params.get("width", 2))}
        unit = "price with confirmation timestamps"
    return {"method": method, "description": description, "result": result, "unit": unit,
            "inputs": params, "calculator_version": calculations.VERSION}


# --- save / publish ---------------------------------------------------------

def _intake(payload, *, bundle, role_meta):
    """Default intake: contract validation only. ``karst.agents.research`` owns the real one."""
    from .agents.research import intake as research_intake  # noqa: PLC0415
    return research_intake(payload, bundle=bundle, clock=utc_now, role_meta=role_meta)


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


def save_research(store, bundle, payload, *, subject, expected_previous_version_id=None,
                  role_meta, intake=None):
    """Validate first, store second: a rejected payload leaves no half version behind."""
    bundle = Path(bundle)
    if (bundle / "packet.json").exists():
        _register_requests(bundle, payload)
    # Callers may pass one role record or the full model list; intake wants the list,
    # the store keeps the researcher's own fields.
    roles = list(role_meta) if isinstance(role_meta, (list, tuple)) else [dict(role_meta)]
    researcher = next((r for r in roles if r.get("role") == "researcher"), roles[0])
    if intake is None:
        try:
            research = _intake(payload, bundle=bundle, role_meta=roles)
        except ImportError:
            research = payload
    else:
        research = intake(payload, bundle=bundle, clock=utc_now, role_meta=roles)
    role_meta = researcher
    packet = read_json(bundle / "packet.json")
    records = read_json(bundle / "evidence.json")
    selected = check_packet(packet, records, bundle)
    check_research(packet, research, selected, bundle)
    try:
        receipt = calculations.calculate(research)
    except (ContractError, KeyError, TypeError) as exc:
        # An unavailable receipt is a stated gap, never a silently empty field.
        receipt = {"calculator_version": calculations.VERSION, "status": "unavailable",
                   "reason": f"{type(exc).__name__}: {exc}"}
    saved = store.save_research_version(
        subject, research, expected_previous_version_id=expected_previous_version_id,
        as_of=packet["as_of"], calc_receipt=receipt, role=role_meta.get("role"),
        execution=role_meta.get("execution"), provider=role_meta.get("provider"),
        model=role_meta.get("model") or role_meta.get("model_id"))
    return saved


def _publication_bars(bundle, packet, research, bars, bars_provider):
    """This run's price arrays: from registered candlesticks, else from a live provider.

    Either way they are transient — charted and measured, never registered and never
    written back into research.json (0.3). A provider that fails leaves the page with
    its derived numbers; it does not fail the publication.
    """
    from . import bars as bars_module  # noqa: PLC0415 - avoid an import cycle at load

    if (research.get("technical") or {}).get("views"):
        # An older saved research already carries its arrays; a second set would be
        # two sources of truth for the same chart.
        return None
    if bars is not None:
        return bars_module.views(bars)
    from_evidence = bars_module.from_evidence(bundle, read_json(bundle / "evidence.json"),
                                              packet["as_of"])
    if from_evidence:
        return from_evidence
    if callable(bars_provider):
        return bars_module.views(bars_provider(packet["security"], packet["as_of"]))
    return None


def publish_research(store, bundle, version_id, output_dir, bars=None, bars_provider=None):
    """Write the release directory first, then record where it is.

    ``bars`` (or whatever ``bars_provider`` returns) are this run's price arrays: they
    reach the chart and the measurements, not the saved research.
    """
    version = store.get_research(version_id)
    if version is None:
        raise ContractError(f"Unknown research version: {version_id}")
    bundle = Path(bundle)
    stored = version["payload"]
    on_disk = read_json(bundle / "research.json") if (bundle / "research.json").exists() else None
    if on_disk != stored:
        (bundle / "research.json").write_bytes(canonical(stored))
    from .page.company import render_company_index  # noqa: PLC0415 - it reads this module

    packet = read_json(bundle / "packet.json")
    release = publish_module.publish(
        bundle, output_dir, bars=_publication_bars(bundle, packet, stored, bars, bars_provider))
    page = (Path(release) / "index.html").resolve()
    store.set_publication_path(version_id, page)
    index = Path(output_dir) / "index.html"
    index.write_text(render_company_index(store, bundle, packet["security"], Path(output_dir)),
                     encoding="utf-8")
    return {"version_id": version_id, "publication_dir": str(Path(release).resolve()),
            "index_html": str(page), "company_index": str(index.resolve())}


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
    store.claim_job(job_id, reviewer.get("provider") or "api")
    store.update_job(job_id, status="running")
    try:
        adapter = _review_adapter(reviewer.get("provider"))
        if task_dir is None:
            raise ContractError("API review needs a task_dir to stage the task in")
        if not Path(task_dir).exists():
            _stage_review_task(store, bundle, version_id, dispute, evidence_ids, task_dir)
        run = adapter.run(task_dir, reviewer.get("model"), budget, transport=transport)
    except ResultUnknown as exc:
        return store.update_job(job_id, status="needs_check", error=str(exc))
    except Exception as exc:  # noqa: BLE001 - a failed review is a job outcome, not a crash
        return store.update_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
    try:
        submit_review(store, job_id, run["result"])
    except ContractError as exc:
        return store.update_job(job_id, status="failed", usage=run["usage"],
                                error=f"review result rejected: {exc}")
    return store.update_job(job_id, usage=run["usage"])


def claim_review(store, job_id, claimed_by):
    job = store.claim_job(job_id, claimed_by)
    if job is None:
        current = store.get_job(job_id)
        raise ContractError(
            f"Job {job_id} is not pending (status: {current['status'] if current else 'unknown'})")
    return store.update_job(job_id, status="running")


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
    return store.update_job(job_id, status="done", result_ref=result)


def get_job(store, job_id):
    job = store.get_job(job_id)
    if job is None:
        raise ContractError(f"Unknown job: {job_id}")
    return job
