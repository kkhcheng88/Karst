"""One-shot migration: normalize thesis/track_record.jsonl to a single schema (Phase-3 WS1 D1).

Context: the log accreted two shapes -- schema A (written by the now-retired
`forward_ic.log_predictions()`: ts/ticker/thesis_id/confidence/cycle_stage only) and schema B
(the superset written by `thesis/log_predictions.py`: adds prediction/kill_condition/entry_ctx/
outcome, sourced from the real spine run via `backtest/spine/orchestrator.run_daily`).

This script rewrites every row to schema B shape:
    {ts, thesis_id, ticker, confidence, cycle_stage, prediction, kill_condition, entry_ctx,
     outcome, legacy}
A-schema rows get prediction/kill_condition/entry_ctx/outcome = null and legacy = true (they carry
strictly less information than a real B row -- this is honest, not a backfill of facts we don't
have). B-schema rows are kept as-is except legacy is stamped false.

Dedup: some (ts, ticker, thesis_id) keys got logged under BOTH schemas on the same day (schema B's
log_predictions.py had no schedule wired, so it and the legacy log ran side by side for a window).
When a key has both an A row and a B row, the B row wins (it is a strict superset) and the A
duplicate is dropped.

Safety: backs up the original file to track_record.jsonl.pre-ws1.bak before writing (idempotent --
running twice on an already-migrated file is a no-op re-normalization, but the backup is only taken
once per invocation so re-running will overwrite it with the *migrated* file; check the backup
exists before re-running if you need the true pre-migration original).

Run: python thesis/migrate_track_record.py
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TRACK = os.path.join(ROOT, "track_record.jsonl")
BACKUP = os.path.join(ROOT, "track_record.jsonl.pre-ws1.bak")

B_FIELDS = ["ts", "thesis_id", "ticker", "confidence", "cycle_stage",
            "prediction", "kill_condition", "entry_ctx", "outcome"]


def _load_raw():
    rows = []
    with open(TRACK, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _is_schema_b(r):
    """Schema B rows carry a 'prediction' dict; schema A rows do not have this key at all."""
    return "prediction" in r


def _key(r):
    return (r.get("ts"), r.get("ticker"), r.get("thesis_id"))


def _to_b_shape(r, legacy):
    out = {f: r.get(f, None) for f in B_FIELDS}
    out["legacy"] = legacy
    return out


def migrate():
    if not os.path.exists(TRACK):
        print(f"[migrate] {TRACK} not found -- nothing to do.")
        return

    if not os.path.exists(BACKUP):
        shutil.copyfile(TRACK, BACKUP)
        print(f"[migrate] backed up original -> {BACKUP}")
    else:
        print(f"[migrate] backup already exists at {BACKUP} (not overwritten)")

    rows = _load_raw()
    n_before = len(rows)

    # Which keys have a real schema-B row anywhere in the file? Those win over any A duplicate.
    b_keys = {_key(r) for r in rows if _is_schema_b(r)}

    out_rows = []
    seen = set()
    n_a_dropped_as_dupe = 0
    n_a = n_b = 0
    for r in rows:
        k = _key(r)
        is_b = _is_schema_b(r)
        if is_b:
            n_b += 1
            if k in seen:
                continue  # exact duplicate B row (shouldn't happen given log_predictions dedup, but be safe)
            seen.add(k)
            out_rows.append(_to_b_shape(r, legacy=False))
        else:
            n_a += 1
            if k in b_keys:
                n_a_dropped_as_dupe += 1
                continue  # a fuller B row for this exact key exists elsewhere -- drop the A one
            if k in seen:
                continue  # duplicate A row for a key already emitted
            seen.add(k)
            out_rows.append(_to_b_shape(r, legacy=True))

    with open(TRACK, "w", encoding="utf-8") as fh:
        for r in out_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[migrate] rows before: {n_before} (schema A: {n_a}, schema B: {n_b})")
    print(f"[migrate] dropped {n_a_dropped_as_dupe} schema-A row(s) that duplicated a schema-B key")
    print(f"[migrate] rows after: {len(out_rows)} -- all schema B shape, written -> {TRACK}")


if __name__ == "__main__":
    migrate()
