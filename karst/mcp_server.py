"""MCP surface: one line per tool, all logic in ``karst.service``.

stdio by default; ``--http`` serves Streamable HTTP for a remote deployment and
requires a Bearer token in ``KARST_MCP_TOKEN`` (no token, no HTTP mode). ``/healthz``
is the only unauthenticated route. Paths arrive as launch arguments, so no ticker
or bundle location is compiled in. Source credentials are read at startup from the
repo-root ``.env`` (gitignored; an already-set environment variable wins) — nothing
secret is ever written into a bundle. No account, position or order tool is exposed
here, and none exists to expose.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.responses import JSONResponse

from . import __version__, service, store as store_module
from .fetch.common import load_env_file

TOKEN_VARIABLE = "KARST_MCP_TOKEN"  # name only; the value never appears in the repo


def build(data_dir=None, *, store_path=None, bundle=None, staging=None, auth=None):
    root = service.data_root(data_dir)
    state = store_module.init(store_path or root / service.DB_NAME)
    bundle = Path(bundle) if bundle else None
    staging = Path(staging) if staging else None
    server = FastMCP("karst", auth=auth)

    def one(subject):
        """The evidence bundle for a subject: the fixed --bundle, else the company store."""
        if bundle is not None:
            return bundle
        if not subject:
            raise service.ContractError("Supply a subject (security id) or launch with --bundle")
        return service.company_paths(data_dir, subject)["bundle"]

    def many(subject):
        return [bundle] if bundle is not None else service.company_bundles(data_dir, subject)

    @server.custom_route("/healthz", methods=["GET"])
    async def healthz(_request):  # unauthenticated on purpose: a probe, not a data route
        return JSONResponse({"status": "ok", "version": __version__, "data_dir": str(root)})

    @server.tool
    def get_research_protocol(mode: str, version: str | None = None) -> dict:
        """Versioned research / update / review method: rules, steps and output format."""
        return service.get_research_protocol(mode, version)

    @server.tool
    def get_research_context(subject: str, as_of: str | None = None) -> dict:
        """Existing research versions, the source index and what is still open for a subject."""
        return service.get_research_context(state, one(subject), subject, as_of)

    @server.tool
    def refresh_sources(security: dict, kinds: list[str], since: str | None = None) -> dict:
        """Fetch and register the requested evidence kinds; reports added/changed/unchanged."""
        return service.refresh_sources(data_dir, security, kinds, since=since, store=state,
                                       bundle=bundle, staging=staging)

    @server.tool
    def search_evidence(query: str | None = None, kind: str | None = None,
                        date_from: str | None = None, date_to: str | None = None,
                        text: str | None = None, subject: str | None = None) -> dict:
        """Search the registered evidence index (``text`` runs full text). A miss is not proof of absence."""
        return service.search_evidence(many(subject), query, kind, date_from, date_to,
                                       text=text, store=state)

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


def bearer_auth(token):
    """One static Bearer token. Rotation is a deployment action, not a code change."""
    return StaticTokenVerifier({token: {"client_id": "karst-client", "scopes": []}})


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
        token = os.environ.get(TOKEN_VARIABLE)
        if not token:
            parser.error(f"--http needs a Bearer token in {TOKEN_VARIABLE}; refusing to serve "
                         "research writes on an unauthenticated port")
        auth = bearer_auth(token)
    server = build(args.data_dir, store_path=args.store, bundle=args.bundle,
                   staging=args.staging, auth=auth)
    if args.http:
        server.run(transport="http", host=args.host, port=args.port)
    else:
        server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
