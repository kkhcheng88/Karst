"""Shared operations for the CLI, the MCP server and the scheduler.

Nothing here calls a model. Research method text comes from ``karst.agents.protocol``
(owned elsewhere); this module only delegates to it. No ticker, CIK or date is
hard-coded: identity always arrives as a parameter.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from . import calculations, publish as publish_module
from .fetch import defeatbeta, edgar, longbridge
from .fetch.common import utc_now, write_json, write_meta
from .fetch.registry import EvidenceRegistry
from .packet import check_packet, check_research, confined, read_json
from .schema import ContractError, canonical

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
            "source_url": record["source_url"], "title": record["tool"]}


def search_evidence(bundle, query=None, kind=None, date_from=None, date_to=None):
    """Index search only. A miss means nothing was registered here, not that nothing exists."""
    hits = []
    for record in _registry(bundle).records():
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
        hits.append(_summary(record))
    return {"count": len(hits), "results": sorted(hits, key=lambda row: row["evidence_id"]),
            "note": "Registered evidence only; absence here is not absence in the world."}


def read_evidence(bundle, evidence_id, offset=0, limit_lines=200):
    """Line-paged read of one registered artifact; line numbers are 1-based and inclusive."""
    record = next((r for r in _registry(bundle).records()
                   if r["evidence_id"] == evidence_id), None)
    if record is None:
        raise ContractError(f"Unregistered evidence: {evidence_id}")
    data = confined(Path(bundle), record["artifact"]["path"]).read_bytes()
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


def ingest_source(bundle, *, url=None, file_path=None, excerpt=None, author=None,
                  published_at=None, note=None, kind=None, entity_ids=(), title=None):
    """Register a user-supplied document or the part of a page that was actually readable."""
    if not (url or file_path or excerpt):
        raise ContractError("Supply at least one of url, file_path or excerpt")
    kind = kind or ("industry_report" if author else "other_public")
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
                   params={"url": url, "author": author, "title": title},
                   fetched_at=utc_now(), published_at=published_at,
                   published_at_basis=("Supplied by the person who ingested it; not independently "
                                       "verified" if published_at else
                                       "No publication time was supplied"),
                   **precision, period=None,
                   truncated={"is_truncated": truncated}, known_gaps=gaps, status="ok",
                   source_url=url, kind=kind, note=note)
        record = _registry(bundle).register(landing, entity_ids=list(entity_ids) or None)
    return _summary(record)


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
                symbol = (security.get("symbols") or {}).get("longbridge") or security["ticker"]
                longbridge.fetch_company(symbol, staging, start=since,
                                         client=clients.get("longbridge"),
                                         factory=clients.get("longbridge_factory",
                                                             longbridge.client_factory))
        except Exception as exc:  # noqa: BLE001 - one broken source must not hide the others
            failures[name] = f"{type(exc).__name__}: {exc}"
    return failures


def refresh_sources(staging, bundle, security, kinds, since=None, clients=None):
    """Fetch the requested kinds, register them, and report what actually changed.

    Added / changed / unchanged is decided by the registry's content fingerprint,
    never by ``fetched_at``: re-fetching the same bytes is an observation, not news.
    """
    from .pipeline import pair_staging  # noqa: PLC0415 - avoid an import cycle at module load

    clients = clients or {}
    unknown = sorted(set(kinds) - set(KIND_ADAPTERS))
    if unknown:
        raise ContractError(f"No adapter registered for kinds: {unknown}")
    registry = _registry(bundle)
    known_ids = {record["evidence_id"] for record in registry.records()}
    known_sources = {record["source_id"] for record in registry.records()}
    adapters = {KIND_ADAPTERS[kind] for kind in kinds}
    adapter_errors = _run_adapters(staging, security, adapters, since, clients)

    result = {"added": [], "changed": [], "unchanged": [], "failed": [], "uncovered": [],
              "adapter_errors": adapter_errors, "records": []}
    entity_ids = _entity_ids(security)
    for meta_path, raws in pair_staging(staging):
        for raw in raws or [None]:
            record = registry.register(raw, meta_path, entity_ids=entity_ids)
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
            "note": "Source text is not inlined; read it with read_evidence."}


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


def save_research(store, bundle, payload, *, subject, expected_previous_version_id=None,
                  role_meta, intake=None):
    """Validate first, store second: a rejected payload leaves no half version behind."""
    bundle = Path(bundle)
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
        model=role_meta.get("model"))
    return saved


def publish_research(store, bundle, version_id, output_dir):
    """Write the release directory first, then record where it is."""
    version = store.get_research(version_id)
    if version is None:
        raise ContractError(f"Unknown research version: {version_id}")
    bundle = Path(bundle)
    stored = version["payload"]
    on_disk = read_json(bundle / "research.json") if (bundle / "research.json").exists() else None
    if on_disk != stored:
        (bundle / "research.json").write_bytes(canonical(stored))
    release = publish_module.publish(bundle, output_dir)
    page = (Path(release) / "index.html").resolve()
    store.set_publication_path(version_id, page)
    return {"version_id": version_id, "publication_dir": str(Path(release).resolve()),
            "index_html": str(page)}


# --- review jobs ------------------------------------------------------------

def request_review(store, *, subject, version_id, dispute, evidence_ids,
                   reviewer=None):
    """Create a pending review job. The API call itself belongs to W2."""
    reviewer = reviewer or {"execution": "interactive"}
    execution = reviewer.get("execution", "interactive")
    if execution not in ("interactive", "api"):
        raise ContractError("reviewer execution must be interactive or api")
    job = store.create_job("review", role="reviewer", execution=execution,
                           provider=reviewer.get("provider"), model=reviewer.get("model"),
                           input_ref={"subject": subject, "version_id": version_id,
                                      "dispute": dispute, "evidence_ids": list(evidence_ids)})
    return job


def claim_review(store, job_id, claimed_by):
    job = store.claim_job(job_id, claimed_by)
    if job is None:
        current = store.get_job(job_id)
        raise ContractError(
            f"Job {job_id} is not pending (status: {current['status'] if current else 'unknown'})")
    return store.update_job(job_id, status="running")


def submit_review(store, job_id, result):
    """Accept the reviewer's result.

    TODO(W2): validate ``result`` against the shape ``karst.agents.review`` defines
    once that module lands; until then any JSON object is stored verbatim.
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
