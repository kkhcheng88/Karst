"""MCP surface: one line per tool, all logic in ``karst.service``.

stdio by default. ``--http`` is reserved for W2 (remote deployment) and refuses for now.
Paths arrive as launch arguments, so no ticker or bundle location is compiled in.
Source credentials are read at startup from the repo-root ``.env`` (gitignored; an
already-set environment variable wins) — nothing secret is ever written into a bundle.
No account, position or order tool is exposed here, and none exists to expose.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from fastmcp import FastMCP

from . import service, store as store_module
from .fetch.common import load_env_file


def build(store_path, bundle, staging):
    state = store_module.init(store_path)
    bundle, staging = Path(bundle), Path(staging)
    server = FastMCP("karst")

    @server.tool
    def get_research_protocol(mode: str, version: str | None = None) -> dict:
        """Versioned research / update / review method: rules, steps and output format."""
        return service.get_research_protocol(mode, version)

    @server.tool
    def get_research_context(subject: str, as_of: str | None = None) -> dict:
        """Existing research versions, the source index and what is still open for a subject."""
        return service.get_research_context(state, bundle, subject, as_of)

    @server.tool
    def refresh_sources(security: dict, kinds: list[str], since: str | None = None) -> dict:
        """Fetch and register the requested evidence kinds; reports added/changed/unchanged."""
        return service.refresh_sources(staging, bundle, security, kinds, since=since)

    @server.tool
    def search_evidence(query: str | None = None, kind: str | None = None,
                        date_from: str | None = None, date_to: str | None = None) -> dict:
        """Search the registered evidence index. A miss is not proof of absence."""
        return service.search_evidence(bundle, query, kind, date_from, date_to)

    @server.tool
    def read_evidence(evidence_id: str, offset: int = 0, limit_lines: int = 200) -> dict:
        """Read one registered artifact by line window; returns the L<start>-L<end> locator."""
        return service.read_evidence(bundle, evidence_id, offset, limit_lines)

    @server.tool
    def ingest_source(url: str | None = None, file_path: str | None = None,
                      excerpt: str | None = None, author: str | None = None,
                      published_at: str | None = None, note: str | None = None) -> dict:
        """Register a supplied report, link or readable excerpt as evidence."""
        return service.ingest_source(bundle, url=url, file_path=file_path, excerpt=excerpt,
                                     author=author, published_at=published_at, note=note)

    @server.tool
    def calculate(method: str, params: dict) -> dict:
        """Deterministic calculation with an input receipt and the calculator version."""
        return service.calculate(method, params)

    @server.tool
    def save_research(payload: dict, subject: str, role_meta: dict,
                      expected_previous_version_id: str | None = None) -> dict:
        """Validate and append a research version; a conflict is returned, never overwritten."""
        return service.save_research(state, bundle, payload, subject=subject,
                                     expected_previous_version_id=expected_previous_version_id,
                                     role_meta=role_meta)

    @server.tool
    def publish_research(version_id: str, output_dir: str) -> dict:
        """Render the readable page for a stored version and record where it landed."""
        return service.publish_research(state, bundle, version_id, output_dir)

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
    parser.add_argument("--store", required=True, help="SQLite state file")
    parser.add_argument("--bundle", required=True, help="evidence bundle root")
    parser.add_argument("--staging", required=True, help="adapter landing directory")
    parser.add_argument("--env-file", default=None, help="credentials file; default: <repo root>/.env")
    parser.add_argument("--http", action="store_true", help="reserved for W2; not wired yet")
    args = parser.parse_args(argv)
    load_env_file(args.env_file)
    if args.http:
        parser.error("--http (remote Streamable HTTP) is a W2 deliverable and is not wired yet")
    build(args.store, args.bundle, args.staging).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
