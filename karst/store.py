"""SQLite state: entities, source index, research versions, jobs.

One file, one writer at a time (WAL). Nothing here calls a model, the network
or a broker. The path is always a parameter; no ticker or date is hard-coded.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .schema import ContractError, canonical, digest

JOB_KINDS = ("review", "research", "refresh")
JOB_STATUSES = ("pending", "claimed", "running", "done", "failed", "interrupted", "needs_check")
RESEARCH_STATUSES = ("latest", "superseded")

SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT,
    exchange TEXT,
    currency TEXT,
    symbols TEXT NOT NULL DEFAULT '{}',
    extra TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source TEXT,
    kind TEXT,
    published_at TEXT,
    fetched_at TEXT,
    period_start TEXT,
    period_end TEXT,
    status TEXT,
    artifact_path TEXT,
    entity_ids TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS sources_by_source_id ON sources(source_id);
CREATE INDEX IF NOT EXISTS sources_by_kind ON sources(kind);
CREATE TABLE IF NOT EXISTS research_versions (
    version_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    previous_version_id TEXT,
    as_of TEXT,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    calc_receipt TEXT,
    publication_path TEXT,
    role TEXT,
    execution TEXT,
    provider TEXT,
    model TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS research_by_subject ON research_versions(subject, status);
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    role TEXT,
    execution TEXT,
    provider TEXT,
    model TEXT,
    input_ref TEXT,
    result_ref TEXT,
    claimed_by TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error TEXT,
    usage TEXT
);
CREATE INDEX IF NOT EXISTS jobs_by_status ON jobs(kind, status);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _dump(value):
    return None if value is None else canonical(value).decode("utf-8").rstrip("\n")


def _load(text):
    return None if text is None else json.loads(text)


def _row(row, json_fields=()):
    if row is None:
        return None
    result = dict(row)
    for field in json_fields:
        result[field] = _load(result.get(field))
    return result


class Store:
    """Thin SQLite wrapper. Every method opens its own short transaction."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path), isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(SCHEMA)

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # --- entities -----------------------------------------------------------

    def upsert_entity(self, entity_id, kind, *, name=None, exchange=None,
                      currency=None, symbols=None, extra=None):
        """Company / security / industry / market node. ``symbols`` maps provider -> code."""
        self.connection.execute(
            "INSERT INTO entities(entity_id, kind, name, exchange, currency, symbols, extra, updated_at)"
            " VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(entity_id) DO UPDATE SET"
            " kind=excluded.kind, name=excluded.name, exchange=excluded.exchange,"
            " currency=excluded.currency, symbols=excluded.symbols, extra=excluded.extra,"
            " updated_at=excluded.updated_at",
            (entity_id, kind, name, exchange, currency,
             _dump(symbols or {}), _dump(extra or {}), now()))
        return self.get_entity(entity_id)

    def get_entity(self, entity_id):
        row = self.connection.execute(
            "SELECT * FROM entities WHERE entity_id=?", (entity_id,)).fetchone()
        return _row(row, ("symbols", "extra"))

    def list_entities(self, kind=None):
        sql = "SELECT * FROM entities" + (" WHERE kind=?" if kind else "") + " ORDER BY entity_id"
        rows = self.connection.execute(sql, (kind,) if kind else ()).fetchall()
        return [_row(row, ("symbols", "extra")) for row in rows]

    # --- sources ------------------------------------------------------------

    def index_sources(self, records):
        """Sync the query index from registry manifest records (identity stays the manifest's)."""
        rows = []
        for record in records:
            period = record.get("period") or {}
            rows.append((record["evidence_id"], record["source_id"], record.get("source"),
                         record.get("kind"), record.get("published_at"), record.get("fetched_at"),
                         period.get("start"), period.get("end"), record.get("status"),
                         (record.get("artifact") or {}).get("path"),
                         _dump(record.get("entity_ids") or [])))
        self.connection.executemany(
            "INSERT INTO sources(evidence_id, source_id, source, kind, published_at, fetched_at,"
            " period_start, period_end, status, artifact_path, entity_ids)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(evidence_id) DO NOTHING", rows)
        return len(rows)

    def list_sources(self, *, kind=None, status=None, entity_id=None):
        sql, params = "SELECT * FROM sources WHERE 1=1", []
        if kind:
            sql += " AND kind=?"
            params.append(kind)
        if status:
            sql += " AND status=?"
            params.append(status)
        rows = self.connection.execute(sql + " ORDER BY fetched_at, evidence_id", params).fetchall()
        result = [_row(row, ("entity_ids",)) for row in rows]
        if entity_id:
            result = [row for row in result if entity_id in (row["entity_ids"] or [])]
        return result

    # --- research versions --------------------------------------------------

    @staticmethod
    def version_id(subject, payload):
        return "rv-" + digest(canonical({"subject": subject, "payload": payload}))

    def save_research_version(self, subject, payload, *, expected_previous_version_id=None,
                              as_of=None, calc_receipt=None, publication_path=None,
                              role=None, execution=None, provider=None, model=None):
        """Append a version. Returns ``{'conflict': ...}`` instead of overwriting a newer one.

        ``expected_previous_version_id`` must name the version that is currently
        latest for this subject (None when the subject has none yet).
        """
        version_id = self.version_id(subject, payload)
        cursor = self.connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        try:
            current = cursor.execute(
                "SELECT version_id FROM research_versions WHERE subject=? AND status='latest'",
                (subject,)).fetchone()
            current_id = current["version_id"] if current else None
            if current_id != expected_previous_version_id:
                cursor.execute("ROLLBACK")
                return {"conflict": True, "current_version_id": current_id,
                        "expected_previous_version_id": expected_previous_version_id,
                        "reason": "A newer version exists for this subject; re-read it before saving."}
            if cursor.execute("SELECT 1 FROM research_versions WHERE version_id=?",
                              (version_id,)).fetchone():
                cursor.execute("ROLLBACK")
                return {"conflict": True, "current_version_id": current_id,
                        "reason": "This exact payload is already stored under " + version_id}
            cursor.execute("UPDATE research_versions SET status='superseded'"
                           " WHERE subject=? AND status='latest'", (subject,))
            cursor.execute(
                "INSERT INTO research_versions(version_id, subject, previous_version_id, as_of,"
                " status, payload, calc_receipt, publication_path, role, execution, provider,"
                " model, created_at) VALUES(?,?,?,?,'latest',?,?,?,?,?,?,?,?)",
                (version_id, subject, current_id, as_of, _dump(payload), _dump(calc_receipt),
                 publication_path, role, execution, provider, model, now()))
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        return self.get_research(version_id)

    def get_research(self, version_id):
        row = self.connection.execute(
            "SELECT * FROM research_versions WHERE version_id=?", (version_id,)).fetchone()
        return _row(row, ("payload", "calc_receipt"))

    def latest_research(self, subject):
        row = self.connection.execute(
            "SELECT * FROM research_versions WHERE subject=? AND status='latest'",
            (subject,)).fetchone()
        return _row(row, ("payload", "calc_receipt"))

    def list_research(self, subject=None, *, limit=50):
        sql = "SELECT * FROM research_versions"
        params = []
        if subject:
            sql += " WHERE subject=?"
            params.append(subject)
        rows = self.connection.execute(
            sql + " ORDER BY created_at DESC, version_id LIMIT ?", params + [limit]).fetchall()
        return [_row(row, ("payload", "calc_receipt")) for row in rows]

    def set_publication_path(self, version_id, path):
        self.connection.execute("UPDATE research_versions SET publication_path=? WHERE version_id=?",
                                (str(path), version_id))
        return self.get_research(version_id)

    # --- jobs ---------------------------------------------------------------

    def create_job(self, kind, *, input_ref=None, role=None, execution=None,
                   provider=None, model=None):
        if kind not in JOB_KINDS:
            raise ContractError(f"job kind must be one of {JOB_KINDS}: {kind!r}")
        created = now()
        job_id = "job-" + digest(canonical(
            {"kind": kind, "input_ref": input_ref, "created_at": created}))[:24]
        self.connection.execute(
            "INSERT INTO jobs(job_id, kind, status, role, execution, provider, model,"
            " input_ref, created_at) VALUES(?,?,'pending',?,?,?,?,?,?)",
            (job_id, kind, role, execution, provider, model, _dump(input_ref), created))
        return self.get_job(job_id)

    def claim_job(self, job_id, claimed_by):
        """Atomic: only a pending job can be claimed; a second claimer gets None."""
        cursor = self.connection.execute(
            "UPDATE jobs SET status='claimed', claimed_by=?, started_at=?"
            " WHERE job_id=? AND status='pending'", (claimed_by, now(), job_id))
        return self.get_job(job_id) if cursor.rowcount else None

    def update_job(self, job_id, *, status=None, result_ref=None, error=None, usage=None,
                   finished_at=None):
        if status is not None and status not in JOB_STATUSES:
            raise ContractError(f"job status must be one of {JOB_STATUSES}: {status!r}")
        sets, params = [], []
        for column, value in (("status", status), ("error", error)):
            if value is not None:
                sets.append(f"{column}=?")
                params.append(value)
        for column, value in (("result_ref", result_ref), ("usage", usage)):
            if value is not None:
                sets.append(f"{column}=?")
                params.append(_dump(value))
        if status in ("done", "failed") or finished_at is not None:
            sets.append("finished_at=?")
            params.append(finished_at or now())
        if not sets:
            return self.get_job(job_id)
        self.connection.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE job_id=?",
                                params + [job_id])
        return self.get_job(job_id)

    def get_job(self, job_id):
        row = self.connection.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return _row(row, ("input_ref", "result_ref", "usage"))

    def list_jobs(self, *, kind=None, status=None, limit=50):
        sql, params = "SELECT * FROM jobs WHERE 1=1", []
        if kind:
            sql += " AND kind=?"
            params.append(kind)
        if status:
            sql += " AND status=?"
            params.append(status)
        rows = self.connection.execute(
            sql + " ORDER BY created_at DESC, job_id LIMIT ?", params + [limit]).fetchall()
        return [_row(row, ("input_ref", "result_ref", "usage")) for row in rows]


def init(path) -> Store:
    """Open (creating if needed) the SQLite state file at ``path``."""
    return Store(path)
