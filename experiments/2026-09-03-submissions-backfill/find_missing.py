# -*- coding: utf-8 -*-
"""KARST-177 step 3a: scan the 8,012 in-universe main files' filings.files[]
declarations and diff against what now sits in data/sec/submissions/pages/
(after collect.py's move) to get the exact list of shards still to fetch.

Scope: only the 8,012 v0-universe main files (the ones KARST-167 fetched),
not the 99 outside_universe_v0 files moved in by this ticket -- those are
outside the v0 universe this whole exercise is about (D-157), and were never
claimed to need shard backfill in the ticket text.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(r"C:\projects\Karst")
CANON = REPO / "data" / "sec" / "submissions"
PAGES = CANON / "pages"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

MAIN_RE = re.compile(r"^CIK(\d{10})\.json$")

# universe scope = the CIKs KARST-167 originally fetched into the canonical
# cache (i.e. NOT the 99 outside_universe_v0 ones this ticket just moved in).
# We recover that set from manifest.jsonl entries whose fetchedBy is KARST-167.
manifest_path = CANON / "manifest.jsonl"
universe_ciks: set[str] = set()
with open(manifest_path, "r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("fetchedBy") == "KARST-167 universe-167" and rec.get("file", "").startswith("CIK") \
                and rec.get("file", "").endswith(".json") and "-submissions-" not in rec.get("file", ""):
            universe_ciks.add(rec["cik"])

print(f"v0-universe main CIKs (from manifest, fetchedBy KARST-167): {len(universe_ciks)}", flush=True)

present_pages = {p.name for p in PAGES.iterdir() if p.is_file()}
print(f"pages present now: {len(present_pages)}", flush=True)

declared: dict[str, dict] = {}  # shard_name -> {cik, filingFrom, filingTo, filingCount}
truncated_ciks = 0
for cik in sorted(universe_ciks):
    main_path = CANON / f"CIK{cik}.json"
    if not main_path.exists():
        print(f"WARNING main file missing for in-universe cik {cik}", flush=True)
        continue
    with open(main_path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    files = doc.get("filings", {}).get("files", []) or []
    if files:
        truncated_ciks += 1
    for blk in files:
        name = blk.get("name")
        if not name:
            continue
        declared[name] = {
            "cik": cik,
            "filingFrom": blk.get("filingFrom"),
            "filingTo": blk.get("filingTo"),
            "filingCount": blk.get("filingCount"),
        }

missing = {name: meta for name, meta in declared.items() if name not in present_pages}
already_present = {name: meta for name, meta in declared.items() if name in present_pages}

print(f"truncated in-universe CIKs (filings.files non-empty): {truncated_ciks}", flush=True)
print(f"declared shards total: {len(declared)}", flush=True)
print(f"already present (post-move): {len(already_present)}", flush=True)
print(f"missing (to fetch): {len(missing)}", flush=True)

import csv
with open(OUT / "missing_shards.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["name", "cik", "filingFrom", "filingTo", "filingCount"])
    for name, meta in sorted(missing.items()):
        w.writerow([name, meta["cik"], meta["filingFrom"], meta["filingTo"], meta["filingCount"]])

summary = {
    "v0_universe_main_ciks": len(universe_ciks),
    "truncated_in_universe_ciks": truncated_ciks,
    "declared_shards_total": len(declared),
    "already_present_after_move": len(already_present),
    "missing_to_fetch": len(missing),
}
with open(OUT / "find_missing_summary.json", "w", encoding="utf-8") as fh:
    json.dump(summary, fh, ensure_ascii=False, indent=2)
print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
