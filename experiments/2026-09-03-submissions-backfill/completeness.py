# -*- coding: utf-8 -*-
"""KARST-177 step 4: completeness check. For every one of the 8,012 v0-universe
main files, check whether all shards declared in filings.files[] are now
present in data/sec/submissions/pages/. complete = all present; partial =
some missing; n/a = filings.files was empty to begin with (never truncated).

Writes data/sec/submissions/completeness.csv (per-CIK grain; kept separate
from manifest.csv, which KARST-174 deliberately made directory-level rather
than per-file -- adding a per-CIK completeness column there would collide
with that design choice, see manifest.csv note and this ticket's comment).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(r"C:\projects\Karst")
CANON = REPO / "data" / "sec" / "submissions"
PAGES = CANON / "pages"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

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

present_pages = {p.name for p in PAGES.iterdir() if p.is_file()}

rows = []
n_complete = n_partial = n_na = 0
for cik in sorted(universe_ciks):
    main_path = CANON / f"CIK{cik}.json"
    with open(main_path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    files = doc.get("filings", {}).get("files", []) or []
    declared = [blk.get("name") for blk in files if blk.get("name")]
    missing = [n for n in declared if n not in present_pages]
    if not declared:
        status = "n/a"
        n_na += 1
    elif not missing:
        status = "complete"
        n_complete += 1
    else:
        status = "partial"
        n_partial += 1
    rows.append({
        "cik": cik,
        "declared_shards": len(declared),
        "present_shards": len(declared) - len(missing),
        "missing_shards": len(missing),
        "missing_names": "|".join(missing),
        "completeness": status,
    })

with open(CANON / "completeness.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["cik", "declared_shards", "present_shards",
                                        "missing_shards", "missing_names", "completeness"])
    w.writeheader()
    for r in rows:
        w.writerow(r)

truncated = n_complete + n_partial
summary = {
    "universe_ciks": len(universe_ciks),
    "truncated_ciks": truncated,
    "complete": n_complete,
    "partial": n_partial,
    "na_never_truncated": n_na,
    "complete_ratio_of_truncated": round(n_complete / truncated, 4) if truncated else None,
    "complete_ratio_of_universe": round(n_complete / len(universe_ciks), 4) if universe_ciks else None,
}
with open(OUT / "completeness_summary.json", "w", encoding="utf-8") as fh:
    json.dump(summary, fh, ensure_ascii=False, indent=2)
print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
