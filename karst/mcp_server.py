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
from pathlib import Path

from fastmcp import FastMCP
from starlette.responses import JSONResponse

from . import __version__, service, store as store_module
from .auth import AuthConfigError, TOKEN_VARIABLE, build_auth, token_auth as bearer_auth  # noqa: F401
from .fetch.common import load_env_file


def build(data_dir=None, *, store_path=None, bundle=None, staging=None, auth=None):
    root = service.data_root(data_dir)
    state = store_module.init(store_path or root / service.DB_NAME)
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
    def get_research_protocol(mode: str, version: str | None = None) -> dict:
        """Versioned research / update / review method: rules, steps and output format."""
        return service.get_research_protocol(mode, version)

    @server.tool
    def get_research_context(subject: str, as_of: str | None = None,
                             as_of_version: str | None = None) -> dict:
        """Existing research versions, the sources and what is still open for a subject.

        Without ``as_of_version`` the sources are what the company store holds now;
        with one they are what that version was validated against. ``sources_view``
        in the result says which question was answered.
        """
        return service.get_research_context(state, one(subject), subject, as_of,
                                            as_of_version=as_of_version)

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

    @server.tool
    def calculate(method: str, params: dict) -> dict:
        """Deterministic calculation with an input receipt and the calculator version."""
        return service.calculate(method, params)

    @server.tool
    def render_charts(subject: str, output_dir: str | None = None,
                      as_of: str | None = None) -> dict:
        """Day / week / month charts of this subject's registered prices, plus their numbers.

        Returns the file paths and the derived JSON (SMA200, bar counts, key levels,
        data cutoff). The price arrays are transient: they are charted and dropped.
        """
        output_dir = output_dir or str(
            service.company_paths(data_dir, subject)["company"] / "charts"
            if subject and bundle is None else Path(root) / "charts")
        return service.render_charts(one(subject), output_dir, as_of=as_of)

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
                   staging=args.staging, auth=auth)
    if args.http:
        server.run(transport="http", host=args.host, port=args.port)
    else:
        server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
