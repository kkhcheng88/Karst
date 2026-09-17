"""SQLite state: entities, the evidence text index, research versions, jobs.

One file, one writer at a time (WAL). Nothing here calls a model, the network
or a broker. The path is always a parameter; no ticker or date is hard-coded.

What is NOT here: a copy of the evidence manifest. The registry in each company
bundle owns evidence identity; SQLite only holds what the files cannot — the
full-text index, the research versions and the job board.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .schema import ContractError, canonical, digest

JOB_KINDS = ("review", "research", "refresh")
# Destination -> the states it may be reached from. The legal moves live here once;
# every caller asks this table instead of writing `status=` itself. done, failed and
# needs_check are terminal: a finished job is reconciled by hand, never moved on.
JOB_TRANSITIONS = {
    "claimed": ("pending",),
    "running": ("pending", "claimed"),
    "done": ("claimed", "running"),
    "failed": ("pending", "claimed", "running"),
    "needs_check": ("claimed", "running"),
}
JOB_TERMINAL = ("done", "failed", "needs_check")
JOB_STATUSES = ("pending", *JOB_TRANSITIONS)  # derived: a state nobody can reach is not a state
JOB_FIELDS = {"claimed_by": False, "error": False, "finished_at": False,
              "result_ref": True, "usage": True}  # True = stored as canonical JSON
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
CREATE TABLE IF NOT EXISTS research_versions (
    version_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    previous_version_id TEXT,
    as_of TEXT,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    packet TEXT,
    evidence TEXT,
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
CREATE TABLE IF NOT EXISTS chart_artifacts (
    artifact_id TEXT PRIMARY KEY,
    view TEXT NOT NULL,
    path TEXT NOT NULL,
    media_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    bars_as_of TEXT,
    source_evidence_id TEXT,
    meta TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
"""
# Why charts get their own (small) table rather than a column on research_versions or a
# job row: they are rendered *before* any research version exists, and the only thing
# ``read_chart`` must do is turn an id into one registered file and refuse everything
# else. Six columns and a primary key do that; hanging them off a row that does not
# exist yet would not.

# Full text lives in its own FTS5 table, rebuildable from the manifests at any time:
# rebuilding the text index never touches evidence identity.
FTS_SCHEMA = "CREATE VIRTUAL TABLE IF NOT EXISTS evidence_text USING fts5(evidence_id UNINDEXED, text)"
TEXT_SUFFIXES = (".txt", ".json", ".jsonl", ".csv", ".md", ".htm", ".html", ".xml")
TEXT_MAX_BYTES = 2_000_000  # per artifact; raise per deployment if transcripts get bigger


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


def _artifact_text(root, record, max_bytes=TEXT_MAX_BYTES):
    """UTF-8 body of a text artifact, or None (binary, oversized, missing, undecodable)."""
    relative = (record.get("artifact") or {}).get("path")
    if not relative:
        return None
    path = Path(root) / relative
    media = record.get("media_type") or ""
    texty = path.suffix.lower() in TEXT_SUFFIXES or media.startswith("text/") or "json" in media
    if not texty or not path.is_file() or path.stat().st_size > max_bytes:
        return None
    try:
        return path.read_bytes().decode("utf-8")
    except (UnicodeDecodeError, OSError):
        return None


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
        self._migrate()
        try:
            self.connection.execute(FTS_SCHEMA)
        except sqlite3.OperationalError as exc:  # SQLite built without FTS5
            self.fts5 = False
            self.fts5_reason = str(exc)
        else:
            self.fts5 = True
            self.fts5_reason = None

    def _migrate(self):
        """Additive only: a database written before a column existed keeps its rows.

        A version saved by an older build has no packet/evidence snapshot; it reads
        back as None and the caller falls back to the bundle instead of failing.
        An older database may also still carry the dropped ``sources`` table — a
        duplicate of the manifests that nothing reads. It is left where it is:
        rebuildable data is not worth a destructive migration.
        """
        existing = {row["name"] for row in
                    self.connection.execute("PRAGMA table_info(research_versions)")}
        for column in ("packet", "evidence"):
            if column not in existing:
                self.connection.execute(f"ALTER TABLE research_versions ADD COLUMN {column} TEXT")

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

    # --- sources ------------------------------------------------------------

    def index_sources(self, records, root=None, max_bytes=TEXT_MAX_BYTES):
        """Index registered evidence for full-text search; identity stays the manifest's.

        There is no second copy of the manifest in SQLite: the registry answers what
        exists, this only builds the text index it cannot hold. With ``root`` (the
        bundle the artifact paths are relative to) every UTF-8 text artifact is
        indexed; binary, oversized and undecodable artifacts are simply not indexed,
        never half-indexed.
        """
        if root is None:
            return 0
        return sum(self.index_text(record["evidence_id"],
                                   _artifact_text(root, record, max_bytes))
                   for record in records)

    def index_text(self, evidence_id, text):
        """Index one artifact's text; ``None`` text and a missing FTS5 build are both no-ops."""
        if not text or not self.fts5:
            return False
        if self.connection.execute("SELECT 1 FROM evidence_text WHERE evidence_id=?",
                                   (evidence_id,)).fetchone():
            return False
        self.connection.execute("INSERT INTO evidence_text(evidence_id, text) VALUES(?,?)",
                                (evidence_id, text))
        return True

    def search_text(self, query, *, limit=20):
        """FTS5 match -> evidence_id, snippet and the line the snippet starts on (1-based)."""
        if not self.fts5:
            raise ContractError(
                "Full-text search needs SQLite compiled with FTS5; this build has none "
                f"({self.fts5_reason}). Not falling back to a substring scan silently.")
        try:
            rows = self.connection.execute(
                "SELECT evidence_id, snippet(evidence_text, 1, '', '', '…', 16) AS snippet, text"
                " FROM evidence_text WHERE evidence_text MATCH ? ORDER BY rank LIMIT ?",
                (query, limit)).fetchall()
        except sqlite3.OperationalError as exc:
            raise ContractError(f"Invalid full-text query {query!r}: {exc}") from exc
        hits = []
        for row in rows:
            snippet = row["snippet"]
            probe = snippet.strip("…").strip()[:40]
            position = row["text"].find(probe) if probe else -1
            hits.append({"evidence_id": row["evidence_id"], "snippet": snippet,
                         "line": None if position < 0 else row["text"].count("\n", 0, position) + 1})
        return hits

    # --- research versions --------------------------------------------------

    @staticmethod
    def version_id(subject, payload):
        return "rv-" + digest(canonical({"subject": subject, "payload": payload}))

    def save_research_version(self, subject, payload, *, expected_previous_version_id=None,
                              as_of=None, calc_receipt=None, publication_path=None,
                              role=None, execution=None, provider=None, model=None,
                              packet=None, evidence=None):
        """Append a version. Returns ``{'conflict': ...}`` instead of overwriting a newer one.

        ``expected_previous_version_id`` must name the version that is currently
        latest for this subject (None when the subject has none yet).

        ``packet`` and ``evidence`` freeze what this version was validated against.
        The company's evidence store keeps growing; a version that carries its own
        packet and evidence records can still be republished byte-identically after
        it does. Evidence *bytes* stay in the company store (content-addressed, so
        the same fingerprint is the same file); only the index is frozen here.
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
                " status, payload, packet, evidence, calc_receipt, publication_path, role,"
                " execution, provider, model, created_at)"
                " VALUES(?,?,?,?,'latest',?,?,?,?,?,?,?,?,?,?)",
                (version_id, subject, current_id, as_of, _dump(payload), _dump(packet),
                 _dump(evidence), _dump(calc_receipt), publication_path, role, execution,
                 provider, model, now()))
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        return self.get_research(version_id)

    def get_research(self, version_id):
        """One version with its frozen packet and evidence index (None on pre-snapshot rows)."""
        row = self.connection.execute(
            "SELECT * FROM research_versions WHERE version_id=?", (version_id,)).fetchone()
        return _row(row, ("payload", "packet", "evidence", "calc_receipt"))

    def latest_research(self, subject):
        row = self.connection.execute(
            "SELECT * FROM research_versions WHERE subject=? AND status='latest'",
            (subject,)).fetchone()
        return _row(row, ("payload", "packet", "evidence", "calc_receipt"))

    def list_research(self, subject=None, *, limit=50):
        """Directory rows: the frozen snapshots are left out, one version can be megabytes."""
        sql = ("SELECT version_id, subject, previous_version_id, as_of, status, payload,"
               " calc_receipt, publication_path, role, execution, provider, model, created_at"
               " FROM research_versions")
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

    # --- chart artifacts ----------------------------------------------------

    CHART_COLUMNS = ("artifact_id", "view", "path", "media_type", "sha256", "bytes",
                     "bars_as_of", "source_evidence_id")

    def register_chart(self, artifact):
        """Register one rendered chart so it can be read back by id. Re-rendering the
        same picture yields the same content-addressed id and simply refreshes the row."""
        missing = [key for key in ("artifact_id", "view", "path", "media_type",
                                   "sha256", "bytes") if not artifact.get(key)]
        if missing:
            raise ContractError(f"Chart artifact is missing: {missing}")
        meta = {key: value for key, value in artifact.items() if key not in self.CHART_COLUMNS}
        self.connection.execute(
            "INSERT OR REPLACE INTO chart_artifacts(artifact_id, view, path, media_type,"
            " sha256, bytes, bars_as_of, source_evidence_id, meta, created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (artifact["artifact_id"], artifact["view"], str(artifact["path"]),
             artifact["media_type"], artifact["sha256"], artifact["bytes"],
             artifact.get("bars_as_of"), artifact.get("source_evidence_id"),
             _dump(meta), now()))
        return self.get_chart(artifact["artifact_id"])

    def get_chart(self, artifact_id):
        row = self.connection.execute(
            "SELECT * FROM chart_artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
        return _row(row, ("meta",))

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

    def transition(self, job_id, to=None, **fields):
        """Move one job to ``to`` (``None`` only records fields), atomically and legally.

        The move is a single conditional UPDATE, so two claimers cannot both win.
        An illegal move raises instead of silently rewriting a finished job: the
        caller is told the job's actual state. ``fields`` are ``JOB_FIELDS``.
        """
        unknown = sorted(set(fields) - set(JOB_FIELDS))
        if unknown:
            raise ContractError(f"Unknown job fields: {unknown}; allowed: {sorted(JOB_FIELDS)}")
        sets = [f"{column}=?" for column in fields]
        params = [_dump(value) if JOB_FIELDS[column] else value
                  for column, value in fields.items()]
        sources = ()
        if to is not None:
            if to not in JOB_TRANSITIONS:
                raise ContractError(f"No job transition to {to!r}; targets: "
                                    f"{sorted(JOB_TRANSITIONS)}")
            sources = JOB_TRANSITIONS[to]
            sets.append("status=?")
            params.append(to)
            if to == "claimed":
                sets.append("started_at=?")
                params.append(now())
            if to in JOB_TERMINAL and "finished_at" not in fields:
                sets.append("finished_at=?")
                params.append(now())
        if not sets:
            return self.get_job(job_id)
        where = "job_id=?"
        if sources:
            where += " AND status IN (%s)" % ",".join("?" * len(sources))
        cursor = self.connection.execute(
            f"UPDATE jobs SET {', '.join(sets)} WHERE {where}", params + [job_id, *sources])
        if not cursor.rowcount:
            current = self.get_job(job_id)
            if current is None:
                raise ContractError(f"Unknown job: {job_id}")
            raise ContractError(
                f"Job {job_id} is {current['status']}; a move to {to!r} is only legal from "
                f"{list(sources)}")
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


def backup(data_dir, out, db_name="karst.sqlite"):
    """Zip a consistent snapshot: the SQLite file (online backup API) plus every company file.

    ``tmp/`` is scratch for in-flight fetches and is deliberately left out.
    """
    data_dir, out = Path(data_dir), Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    database = data_dir / db_name
    with tempfile.TemporaryDirectory() as scratch:
        snapshot = Path(scratch) / db_name
        if database.is_file():
            source = sqlite3.connect(str(database))
            target = sqlite3.connect(str(snapshot))
            try:
                with target:
                    source.backup(target)
            finally:
                source.close()
                target.close()
        written = 0
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            if snapshot.is_file():
                archive.write(snapshot, db_name)
                written += 1
            for path in sorted((data_dir / "companies").rglob("*")):
                if path.is_file():
                    archive.write(path, str(path.relative_to(data_dir).as_posix()))
                    written += 1
    return {"archive": str(out.resolve()), "files": written,
            "note": "tmp/ is scratch and is not backed up."}


def main(argv=None) -> int:
    import argparse  # noqa: PLC0415 - CLI only

    parser = argparse.ArgumentParser(prog="python -m karst.store")
    sub = parser.add_subparsers(dest="command", required=True)
    snapshot = sub.add_parser("backup", help="zip the SQLite state and the evidence files")
    snapshot.add_argument("--data-dir", required=True)
    snapshot.add_argument("--out", required=True)
    snapshot.add_argument("--db-name", default="karst.sqlite")
    args = parser.parse_args(argv)
    result = backup(args.data_dir, args.out, args.db_name)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
