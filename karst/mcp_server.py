"""MCP surface: one line per tool, all logic in ``karst.service``.

stdio by default; ``--http`` serves Streamable HTTP for a remote deployment and
refuses to start without configured authentication — GitHub OAuth plus a login
allowlist, or one fixed Bearer token; see ``karst.auth``. ``/healthz``
is the only unauthenticated route. Paths arrive as launch arguments, so no ticker
or bundle location is compiled in. Source credentials are read at startup from the
repo-root ``.env`` (gitignored; an already-set environment variable wins) — nothing
secret is ever written into a bundle. No account, position or order tool is exposed
here, and none exists to expose.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.types import Image
from mcp.types import TextContent
from starlette.responses import JSONResponse

from . import __version__, calculations, service, store as store_module
from .auth import AuthConfigError, TOKEN_VARIABLE, build_auth, token_auth as bearer_auth  # noqa: F401
from .fetch.common import load_env_file


def build(data_dir=None, *, store_path=None, bundle=None, staging=None, auth=None, knowledge_seed=None):
    root = service.data_root(data_dir)
    state = store_module.init(store_path or root / service.DB_NAME)
    if knowledge_seed:
        from .knowledge import bootstrap
        bootstrap(state, json.loads(Path(knowledge_seed).read_text(encoding="utf-8")))
    bundle = Path(bundle) if bundle else None
    staging = Path(staging) if staging else None
    server = FastMCP("karst", auth=auth)

    def one(subject):
        return service.bundle_for(data_dir, subject, bundle)

    def many(subject):
        return service.bundles_for(data_dir, subject, bundle)

    @server.custom_route("/healthz", methods=["GET"])
    async def healthz(_request):  # unauthenticated on purpose: a probe, not a data route
        return JSONResponse({"status": "ok", "version": __version__, "data_dir": str(root)})

    @server.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
    async def protected_resource_alias(_request):
        # RFC 9728 puts the metadata under the resource path (/.../oauth-protected-resource/mcp),
        # which fastmcp serves; a client probing the bare path gets pointed there instead of 404.
        from starlette.responses import RedirectResponse  # noqa: PLC0415
        return RedirectResponse("/.well-known/oauth-protected-resource/mcp", status_code=307)

    @server.tool
    def get_research_protocol(mode: str, version: str | None = None,
                              include_schema: bool = True) -> dict:
        """Versioned research / update / review / workflow method and output format."""
        return service.get_research_protocol(mode, version, include_schema=include_schema)

    @server.tool
    def get_daily_scope(universe_id: str) -> dict:
        """Read explicit daily monitoring membership, including names without research."""
        from .daily import scope
        return scope(state, universe_id)

    @server.tool
    def refresh_daily_scope(universe_id: str, since: str | None = None) -> dict:
        """Prices/news intake for every monitored member; failures persist per subject.

        Requires registered securities; returns missing registrations explicitly.
        Shared macro/chain review and investment judgment remain agent work.
        No scheduler, review completion, rating or automatic publication is implied.
        """
        from .daily import refresh_scope
        return refresh_scope(state, root, universe_id, since=since)

    @server.tool
    def get_daily_runs(run_id: str | None = None, limit: int = 10) -> dict:
        """Read an intake checkpoint, or recent run headers for recovery."""
        from .daily import get_run, recent_runs
        return {'run': get_run(root, run_id)} if run_id else {'runs': recent_runs(root, limit)}

    @server.tool
    def resume_daily_scope(run_id: str) -> dict:
        """Retry failed/unattempted members of the same run; retain successful evidence dates."""
        from .daily import get_run, refresh_scope
        previous = get_run(root, run_id)
        return refresh_scope(state, root, previous['universe_id'], resume_run_id=run_id)

    @server.tool
    def refresh_daily(subject: str, since: str | None = None) -> dict:
        """Small daily prices + dated RSS-news intake; does not re-fetch financial statements.

        Reuses registered security identity and latest research. News excerpts are
        leads to read, not verified facts. Does not save a rating or publish a page.
        """
        from .daily import refresh
        return refresh(state, root, subject, since=since)

    @server.tool
    def plan_workflow(subject: str, kind: str, intent: str, question: str,
                      universe_id: str | None = None, benchmark: str | None = None) -> dict:
        """Read-only production plan with current state and concrete next tools.

        kind=stock|fund|value_chain|market|report; intent=add|compare|analyze|update.
        For a report, subject is the affected company or industry evidence scope.
        Resolve identity first. Add means radar/comparison; analyze continues to
        an investment judgment. Does not register a task or claim research done.
        """
        from .workflow import plan
        return plan(state, root, subject=subject, kind=kind, intent=intent,
                    question=question, universe_id=universe_id, benchmark=benchmark)

    @server.tool
    def compare_registered_momentum(weights: dict[str, float], benchmark: str,
                                     cutoff: str, selected_on: str, as_of: str,
                                     currency: str, history_sessions: int = 200) -> dict:
        """Compare registered daily candles without copying raw bars into prompts.

        Keys are security IDs; positive weights sum to one. cutoff is the exact
        completed price date; as_of is a zoned evidence-availability timestamp.
        Price returns only (explicit NoAdjust), not total returns. Missing dates,
        members, currencies or basis agreement fail; short history stays null.
        Returns calculation and replayable source/input receipt; no rating.
        Default warmup is 200 completed daily sessions; record it for RSI replay.
        """
        from .workflow import compare_registered
        return compare_registered(state, root, weights=weights, benchmark=benchmark,
                                  cutoff=cutoff, selected_on=selected_on,
                                  as_of=as_of, currency=currency, history_sessions=history_sessions)

    @server.tool
    def get_research_context(subject: str, as_of: str | None = None,
                             as_of_version: str | None = None) -> dict:
        """Existing research versions, the sources and what is still open for a subject.

        Without ``as_of_version`` the sources are what the company store holds now;
        with one they are what that version was validated against. ``sources_view``
        in the result says which question was answered.
        """
        return service.get_research_context(state, one(subject), subject, as_of,
                                            as_of_version=as_of_version, data_dir=root)

    @server.tool
    def get_watchlist() -> dict:
        """Saved thesis watches with their adopted research versions; no account data."""
        return {"watches": state.list_watches()}

    @server.tool
    def save_knowledge(kind: str, object_id: str, payload: dict,
                       expected_version: str | None = None) -> dict:
        """Append a universe, economic relation, testable assumption or comparison.

        Read get_knowledge first when revising. Source references are required;
        documented relationships and analyst inference are separate. Register
        endpoints in a universe before adding relations. No ratings propagate.
        Payload field definitions are returned by get_knowledge(kind='schema').
        """
        from . import knowledge
        row = knowledge.save(state, kind, object_id, payload, expected_version=expected_version)
        return {"record": row, "affected_research": knowledge.affected_research(state, kind, object_id)
                if kind in ("relation", "assumption") else []}

    @server.tool
    def get_knowledge(kind: str, object_id: str | None = None,
                      version: str | None = None, as_of: str | None = None) -> dict:
        """Read versioned research inputs; as_of never includes later discoveries.

        kind='schema' describes write payloads. Otherwise kind is universe,
        relation, assumption or comparison. Omit object_id to list latest objects.
        Each source needs title plus url or evidence_id; uploaded documents may
        cite registered evidence without inventing a public URL.
        """
        from . import knowledge
        if kind == "schema":
            return {"source_reference": {"title": "required", "url": "public HTTPS; optional with evidence_id",
                    "evidence_id": "registered document; required if no url", "locator": "optional"},
                    "universe": {"name": "text", "summary": "text", "members":
                    [{"entity_id": "text", "name": "text", "kind": "company|security|fund|index|theme",
                      "roles": ["text"], "comparison_groups": ["text"]}], "sources": [{"url": "https://...", "title": "text"}]},
                    "relation": {"from_entity": "registered entity", "to_entity": "registered entity",
                    "relation_type": list(knowledge.RELATIONS), "mechanism": "text", "status": "active|withdrawn",
                    "valid_from": "YYYY-MM-DD|null", "valid_to": "YYYY-MM-DD|null", "basis": "documented|inference",
                    "sources": [{"url": "https://...", "title": "text", "evidence_id": "optional", "locator": "optional"}]},
                    "assumption": {"subject": "entity", "driver": "text", "statement": "text", "expected": "number or text",
                    "unit": "text", "period": "text", "next_check": "event to verify", "change_effect": "causal effect",
                    "layers": ["L2", "L3", "L4", "L6"], "status": "active|revised|rejected",
                    "sources": [{"url": "https://...", "title": "text"}]},
                    "comparison": {"subject": "entity", "as_of": "YYYY-MM-DD", "metrics": [
                    {"key": "metric name", "value": "number|null", "unit": "USD million|percent|...",
                     "period": "explicit fiscal/calendar period", "basis": "GAAP|adjusted|company definition",
                     "status": "reported|calculated|guidance|estimate|missing|not_applicable", "source_index": 0}],
                    "sources": [{"url": "https://...", "title": "text"}]}}
        if object_id is None:
            return {"records": knowledge.latest(state, kind, as_of=as_of)}
        return {"record": knowledge.get(state, kind, object_id, version=version, as_of=as_of)}

    @server.tool
    def get_value_chain(universe_id: str, focus: str | None = None,
                        depth: int = 1, as_of: str | None = None) -> dict:
        """Universe roles, comparison groups, directed relations and assumptions.

        Optional focus traverses 0–3 hops within the selected universe. Edges retain
        their direction and evidence/inference basis; connected is not comparable.
        """
        from . import knowledge
        return knowledge.value_chain(state, universe_id, focus=focus, depth=depth, as_of=as_of)

    @server.tool
    def valuation_matrix(eps_scenarios: list[dict], multiples: list[float], period: str,
                         earnings_basis: str, currency: str) -> dict:
        """EPS × P/E cross-sensitivity with a calculation receipt, not a target rating.

        eps_scenarios=[{label,eps}]; nonpositive EPS yields null, never negative P/E.
        Multiples are supplied assumptions; this tool does not invent peer data.
        """
        from . import knowledge
        return knowledge.valuation_matrix(eps_scenarios, multiples, period=period,
                                          earnings_basis=earnings_basis, currency=currency)

    @server.tool
    def set_watch(subject: str, watch: dict, based_on_version_id: str,
                  expected_version: str | None = None) -> dict:
        """Save what this thesis is waiting for, thresholds, deadline and subscriptions.

        Each subscription requires entity_id/kinds; optional source_ids, authors,
        source_types, url_prefixes narrow the report source (lists, AND across
        filters). Prefixes match an HTTPS host/path boundary. These monitor already
        ingested evidence; they do not crawl a site or create a recurring schedule.

        watch: {waiting_for, conditions, validation_deadline, subscriptions,
        dependencies}. Price conditions: {kind:'price', description, operator:
        'gte'|'lte', value, currency}; evaluated on the latest daily bar only when complete and unadjusted,
        never an automatic entry/exit. Event: {kind:'event', description}.
        subscriptions: [{entity_id, kinds:[...]}]. dependencies: [{input_kind:
        'source'|'entity'|'relation'|'assumption', input_id, input_version,
        assumption_id, assumption_version, layers:['L2',...], exposure}].
        The economic exposure is supplied by the researcher, never inferred from
        a ticker or citation. Deadline is null or a timezone-aware ISO timestamp.
        """
        return state.save_watch(subject, watch, based_on_version_id, expected_version)

    @server.tool
    def plan_update(subject: str, input_changes: list[dict] | None = None) -> dict:
        """Source changes and affected layers; no model, fetch or new research version.

        Optional relation/assumption revisions: [{kind, id, version, reason}].
        Existing source/entity subscriptions discover new uncited evidence across
        company bundles. Reuse candidates still need the researcher's judgment.
        """
        return service.plan_update(state, one(subject), subject, data_dir=root,
                                   input_changes=input_changes or ())

    @server.tool
    def record_update_check(subject: str, plan_id: str, outcome: str, reason: str,
                            input_changes: list[dict] | None = None) -> dict:
        """Record a manual check without manufacturing a new research version.

        outcome: unchanged, needs_reassessment or incomplete. The plan is checked
        again first; stale inputs are rejected. Repeating the same check is safe.
        To change advice, use save_research with the complete updated analysis.
        """
        return service.record_update_check(state, one(subject), subject, plan_id, outcome,
                                           reason, data_dir=root, input_changes=input_changes or ())

    @server.tool
    def refresh_sources(security: dict, kinds: list[str], since: str | None = None) -> dict:
        """Fetch and register the requested evidence kinds; reports added/changed/unchanged."""
        return service.refresh_sources(data_dir, security, kinds, since=since, store=state,
                                       bundle=bundle, staging=staging)

    @server.tool
    def search_evidence(query: str | None = None, kind: str | None = None,
                        date_from: str | None = None, date_to: str | None = None,
                        text: str | None = None, subject: str | None = None,
                        as_of_version: str | None = None) -> dict:
        """Search the registered evidence index (``text`` runs full text). A miss is not proof of absence.

        ``as_of_version`` searches what that research version used instead of what is
        available now; ``scope`` in the result says which was searched.
        """
        return service.search_evidence(many(subject), query, kind, date_from, date_to,
                                       text=text, store=state, as_of_version=as_of_version)

    @server.tool
    def read_evidence(evidence_id: str, offset: int = 0, limit_lines: int = 200,
                      subject: str | None = None) -> dict:
        """Read one registered artifact by line window; returns the L<start>-L<end> locator."""
        return service.read_evidence(many(subject), evidence_id, offset, limit_lines)

    @server.tool
    def ingest_source(url: str | None = None, file_path: str | None = None,
                      excerpt: str | None = None, author: str | None = None,
                      published_at: str | None = None, note: str | None = None,
                      kind: str | None = None, entity_ids: list[str] | None = None,
                      title: str | None = None, source_type: str | None = None,
                      subject: str | None = None) -> dict:
        """Register a supplied report, link or readable excerpt as evidence.

        A research report (kind=industry_report) must carry entity_ids, author,
        published_at and source_type; without them it cannot be routed later.
        """
        target = one(subject or (entity_ids or [None])[0])
        return service.ingest_source(target, url=url, file_path=file_path, excerpt=excerpt,
                                     author=author, published_at=published_at, note=note,
                                     kind=kind, entity_ids=entity_ids or (), title=title,
                                     source_type=source_type, store=state)

    @server.tool(description=calculations.TOOL["description"])
    def calculate(method: str, params: dict) -> dict:
        return calculations.run(method, params)

    @server.tool
    def render_charts(subject: str, output_dir: str | None = None,
                      as_of: str | None = None) -> dict:
        """Month / week / day / recent charts of this subject's registered prices, plus numbers.

        Returns one **artifact** per view (artifact_id, view, period, hash, bytes, the
        bar cutoff and the source evidence) and the derived JSON: exact moving
        averages and their direction, ATR, volume ratio, and support / resistance
        zones with the day each pivot formed and the later day it was confirmed.

        Server-side file paths are not returned — read a chart with ``read_chart``.
        The price arrays are transient: they are charted, measured and dropped.
        """
        output_dir = output_dir or str(
            service.company_paths(data_dir, subject)["company"] / "charts"
            if subject and bundle is None else Path(root) / "charts")
        return service.without_local_paths(
            service.render_charts(one(subject), output_dir, as_of=as_of, store=state,
                                  title=subject))

    @server.tool
    def read_chart(artifact_id: str) -> ToolResult:
        """Read one rendered chart by artifact_id: the PNG itself, as image content.

        Only artifacts this server registered can be read, and each one is checked
        against its recorded hash before it is served — so what you see is that exact
        version of that chart, not whatever is at some path now. There is no other
        file access here. Precise figures stay in ``render_charts``' derived JSON.
        """
        record = service.chart_artifact(state, artifact_id)
        meta = {key: record[key] for key in
                ("artifact_id", "view", "media_type", "sha256", "bytes",
                 "bars_as_of", "source_evidence_id")} | (record.get("meta") or {})
        meta.pop("path", None)
        image = Image(data=record["data"], format="png").to_image_content()
        return ToolResult(content=[image, TextContent(
            type="text", text=json.dumps(meta, ensure_ascii=False, default=str))])

    @server.tool
    def prepare_research(security: dict, as_of: str | None = None,
                         evidence_ids: list[str] | None = None) -> dict:
        """Freeze this run's registered evidence, security and cutoff before research.

        Refresh prepares a snapshot automatically. Use this after supplemental
        ingestion, for an explicit evidence selection, or an update cutoff.
        No model runs and no research version is saved by this operation.
        """
        subject = security.get("security_id")
        if not subject:
            raise service.ContractError("security_id is required")
        return service.prepare_research(one(subject), security, as_of=as_of,
                                        evidence_ids=evidence_ids)

    @server.tool
    def save_research(payload: dict, subject: str, role_meta: dict,
                      expected_previous_version_id: str | None = None) -> dict:
        """Validate and append a research version; a conflict is returned, never overwritten."""
        return service.save_research(state, one(subject), payload, subject=subject,
                                     expected_previous_version_id=expected_previous_version_id,
                                     role_meta=role_meta)

    @server.tool
    def publish_research(version_id: str, output_dir: str | None = None,
                         subject: str | None = None) -> dict:
        """Render the readable page for a stored version and record where it landed."""
        output_dir = output_dir or str(service.company_paths(data_dir, subject)["releases"]
                                       if subject else Path(root) / "releases")
        return service.publish_research(state, one(subject), version_id, output_dir)

    @server.tool
    def request_review(subject: str, version_id: str, dispute: str,
                       evidence_ids: list[str], reviewer: dict | None = None) -> dict:
        """Open a review job on a specific research version and dispute."""
        return service.request_review(state, subject=subject, version_id=version_id,
                                      dispute=dispute, evidence_ids=evidence_ids,
                                      reviewer=reviewer)

    @server.tool
    def claim_review(job_id: str, claimed_by: str) -> dict:
        """Take a pending review job; a second claimer is refused."""
        return service.claim_review(state, job_id, claimed_by)

    @server.tool
    def submit_review(job_id: str, result: dict) -> dict:
        """Hand back a review result; the main researcher decides what to do with it."""
        return service.submit_review(state, job_id, result)

    @server.tool
    def get_job(job_id: str) -> dict:
        """Read one job's state, result reference and recorded usage."""
        return service.get_job(state, job_id)

    return server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m karst.mcp_server", description=__doc__)
    parser.add_argument("--data-dir", default=None,
                        help=f"persistent root; default ${{KARST_DATA_DIR}} or {service.DEFAULT_DATA_DIR}")
    parser.add_argument("--store", default=None, help="SQLite state file; default <data-dir>/karst.sqlite")
    parser.add_argument("--knowledge-seed", default=None, help="Explicit versioned input manifest; create absent objects only")
    parser.add_argument("--bundle", default=None, help="compatibility: one fixed evidence bundle")
    parser.add_argument("--staging", default=None, help="compatibility: one fixed landing directory")
    parser.add_argument("--env-file", default=None, help="credentials file; default: <repo root>/.env")
    parser.add_argument("--http", action="store_true", help="serve Streamable HTTP instead of stdio")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind address")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    args = parser.parse_args(argv)
    load_env_file(args.env_file)
    auth = None
    if args.http:
        try:
            auth = build_auth(service.data_root(args.data_dir))
        except AuthConfigError as problem:
            parser.error(str(problem))
    server = build(args.data_dir, store_path=args.store, bundle=args.bundle,
                   staging=args.staging, auth=auth, knowledge_seed=args.knowledge_seed)
    if args.http:
        server.run(transport="http", host=args.host, port=args.port)
    else:
        server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
