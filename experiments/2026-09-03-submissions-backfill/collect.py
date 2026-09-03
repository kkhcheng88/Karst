# -*- coding: utf-8 -*-
"""KARST-177 step 1-2: inventory the 1,051 shard files + 99 outside-universe
main files sitting in the silent-revisions / fundamentals-panel experiment
directories (KARST-174 boundary), then Move-Item them (bit-level, no decode)
into the canonical data/sec/submissions/ tree:
  - shard files (CIK##########-submissions-NNN.json) -> data/sec/submissions/pages/
  - outside-universe main files (CIK##########.json, not present in canonical) ->
    data/sec/submissions/ (top level, tagged outside_universe_v0 in manifest)

Every move is verified: sha256 before == sha256 after, else left in place and
listed in out/move_failures.csv. Nothing is deleted; Move-Item is a cut, not a
copy, so the file simply ceases to exist at the old path once verified moved.

Appends to data/sec/submissions/manifest.jsonl (append-only, per README rule 4).
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\projects\Karst")
CANON = REPO / "data" / "sec" / "submissions"
PAGES = CANON / "pages"
MANIFEST = CANON / "manifest.jsonl"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
PAGES.mkdir(parents=True, exist_ok=True)

SRC_DIRS = [
    REPO / "experiments" / "2026-09-02-silent-revisions" / "data" / "submissions",
    REPO / "experiments" / "2026-09-02-fundamentals-panel" / "data" / "submissions",
]

SHARD_RE = re.compile(r"^CIK(\d{10})-submissions-(\d{3})\.json$")
MAIN_RE = re.compile(r"^CIK(\d{10})\.json$")

FETCHED_BY = "KARST-177"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_manifest(rec: dict) -> None:
    with open(MANIFEST, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def move_verified(src: Path, dst: Path, extra: dict, move_log: list, fail_log: list) -> bool:
    if dst.exists():
        move_log.append({**extra, "src": str(src), "dst": str(dst),
                          "status": "skipped_dst_exists"})
        return False
    pre_hash = sha256_of(src)
    pre_bytes = src.stat().st_size
    try:
        shutil.move(str(src), str(dst))
    except Exception as exc:  # noqa: BLE001
        fail_log.append({**extra, "src": str(src), "dst": str(dst), "error": str(exc)})
        return False
    post_hash = sha256_of(dst)
    if post_hash != pre_hash:
        # do not silently leave a half-moved file: move it back if possible
        fail_log.append({**extra, "src": str(src), "dst": str(dst),
                          "error": f"sha256 mismatch after move: pre={pre_hash} post={post_hash}"})
        try:
            shutil.move(str(dst), str(src))
        except Exception:  # noqa: BLE001
            pass
        return False
    append_manifest({
        "cik": extra.get("cik"),
        "file": dst.name,
        "kind": extra.get("kind"),
        "page": extra.get("page"),
        "bytes": pre_bytes,
        "sha256": pre_hash,
        "fetchedAt": now_iso(),
        "fetchedBy": FETCHED_BY,
        "source": "moved",
        "movedFrom": str(src),
        "note": extra.get("note", ""),
    })
    move_log.append({**extra, "src": str(src), "dst": str(dst), "status": "moved",
                      "sha256": pre_hash, "bytes": pre_bytes})
    return True


def main() -> None:
    canon_main_ciks = {m.group(1) for p in CANON.iterdir() if p.is_file()
                        for m in [MAIN_RE.match(p.name)] if m}
    print(f"canonical main CIK files present: {len(canon_main_ciks)}", flush=True)

    move_log: list[dict] = []
    fail_log: list[dict] = []
    shard_moved = 0
    outside_moved = 0
    outside_skipped_dup = 0

    seen_shard_names: set[str] = set()

    for src_dir in SRC_DIRS:
        if not src_dir.exists():
            print(f"WARNING missing source dir {src_dir}", flush=True)
            continue
        for p in sorted(src_dir.iterdir()):
            if not p.is_file():
                continue
            m_shard = SHARD_RE.match(p.name)
            m_main = MAIN_RE.match(p.name)
            if m_shard:
                cik, page = m_shard.group(1), m_shard.group(2)
                if p.name in seen_shard_names:
                    # duplicate shard name across the two source dirs; keep first, log second
                    move_log.append({"src": str(p), "dst": "", "status": "skipped_duplicate_shard",
                                      "cik": cik, "kind": "page", "page": page})
                    continue
                seen_shard_names.add(p.name)
                dst = PAGES / p.name
                ok = move_verified(p, dst, {"cik": cik, "kind": "page", "page": page,
                                             "note": "silent-revisions 分頁檔收編(KARST-177)"},
                                    move_log, fail_log)
                if ok:
                    shard_moved += 1
            elif m_main:
                cik = m_main.group(1)
                if cik in canon_main_ciks:
                    # in-universe, different content (older 09-02 snapshot) -- leave in place,
                    # per KARST-174/D-157 "不同者保留"; not part of this ticket's scope.
                    outside_skipped_dup += 1
                    continue
                dst = CANON / p.name
                ok = move_verified(p, dst, {"cik": cik, "kind": "main", "page": None,
                                             "note": "outside_universe_v0(KARST-177 收編)"},
                                    move_log, fail_log)
                if ok:
                    canon_main_ciks.add(cik)
                    outside_moved += 1
            else:
                move_log.append({"src": str(p), "dst": "", "status": "skipped_unrecognised_name",
                                  "cik": None, "kind": None, "page": None})

    import csv
    with open(OUT / "move_log.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["cik", "kind", "page", "src", "dst", "status",
                                            "sha256", "bytes", "note"])
        w.writeheader()
        for r in move_log:
            w.writerow({k: r.get(k, "") for k in w.fieldnames})
    with open(OUT / "move_failures.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["cik", "kind", "page", "src", "dst", "error"])
        w.writeheader()
        for r in fail_log:
            w.writerow({k: r.get(k, "") for k in w.fieldnames})

    summary = {
        "shard_moved": shard_moved,
        "outside_universe_moved": outside_moved,
        "in_universe_dup_left_in_place": outside_skipped_dup,
        "move_failures": len(fail_log),
        "pages_dir_count_after": sum(1 for _ in PAGES.iterdir()),
        "canon_top_level_json_count_after": sum(1 for p in CANON.iterdir()
                                                  if p.is_file() and MAIN_RE.match(p.name)),
    }
    with open(OUT / "collect_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
