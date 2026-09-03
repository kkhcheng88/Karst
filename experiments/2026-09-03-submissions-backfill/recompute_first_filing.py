# -*- coding: utf-8 -*-
"""KARST-177 step 6: recompute the "first filing year" distribution three ways
for the 8,012 CIKs in the v0 universe (KARST-167's original population for
research/2026-09-03-小型股宇宙v0盤點.md section 2.4), and compare:

  A) naive       -- min(filings.recent.filingDate) only (what A-046 assumed
                     KARST-167 had done: read only the truncated recent block)
  B) metadata     -- naive plus min(filings.files[].filingFrom) (what
                     build_universe.py actually does today -- filingFrom is a
                     boundary EDGAR declares in the *truncated* main file
                     itself, no shard fetch required)
  C) shard-verified -- metadata plus, for every declared shard now present in
                     data/sec/submissions/pages/ (after this ticket's
                     collect+fetch), the actual min(filingDate) read out of
                     the shard's own content -- the ground truth.

If B and C match, it proves build_universe.py's existing first_filing_date
(and therefore the report's published table) was already correct, and
A-046's practical impact on this specific table was nil -- the bug A-046
documents (shard *content* absent from the cache) is real, but this one
downstream number was insulated from it by the filingFrom field.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(r"C:\projects\Karst")
CANON = REPO / "data" / "sec" / "submissions"
PAGES = CANON / "pages"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

manifest_path = CANON / "manifest.jsonl"
raw_ciks: set[str] = set()
with open(manifest_path, "r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("fetchedBy") == "KARST-167 universe-167" and rec.get("file", "").startswith("CIK") \
                and rec.get("file", "").endswith(".json") and "-submissions-" not in rec.get("file", ""):
            raw_ciks.add(rec["cik"])

# Section 2.4 of the report is over the 5,257 FINAL entities (post gates
# I1-E4 in build_universe.py), not the raw 8,012 fetched CIKs. Load that
# population so the recomputed distribution is comparable to the published
# table cell-for-cell.
entities_df = pd.read_parquet(REPO / "data" / "universe" / "entities.parquet")
report_ciks = set(entities_df["entity_id"].astype(str))
universe_ciks = raw_ciks  # keep full population for the supplementary raw-8012 table

rows = []
mismatches = []  # cases where shard-verified differs from metadata (filingFrom inaccurate)
for cik in sorted(universe_ciks):
    main_path = CANON / f"CIK{cik}.json"
    with open(main_path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    recent = doc.get("filings", {}).get("recent", {}) or {}
    dates = [d for d in (recent.get("filingDate") or []) if d]
    naive_min = min(dates) if dates else None

    files = doc.get("filings", {}).get("files", []) or []
    meta_candidates = list(dates)
    for blk in files:
        if blk.get("filingFrom"):
            meta_candidates.append(blk["filingFrom"])
    metadata_min = min(meta_candidates) if meta_candidates else None

    verified_candidates = list(meta_candidates)
    all_present = True
    for blk in files:
        name = blk.get("name")
        if not name:
            continue
        shard_path = PAGES / name
        if not shard_path.exists():
            all_present = False
            continue
        try:
            with open(shard_path, "r", encoding="utf-8") as fh:
                sdoc = json.load(fh)
            sdates = [d for d in (sdoc.get("filingDate") or []) if d]
            if sdates:
                verified_candidates.append(min(sdates))
        except Exception:  # noqa: BLE001
            all_present = False
    verified_min = min(verified_candidates) if verified_candidates else None

    if verified_min != metadata_min:
        mismatches.append({"cik": cik, "metadata_min": metadata_min,
                            "verified_min": verified_min, "shards_all_present": all_present})

    rows.append({
        "cik": cik,
        "naive_first_filing_date": naive_min,
        "metadata_first_filing_date": metadata_min,
        "verified_first_filing_date": verified_min,
        "shards_declared": len(files),
        "shards_all_present": all_present,
    })

df = pd.DataFrame(rows)
df["naive_year"] = df["naive_first_filing_date"].str.slice(0, 4)
df["metadata_year"] = df["metadata_first_filing_date"].str.slice(0, 4)
df["verified_year"] = df["verified_first_filing_date"].str.slice(0, 4)


def bucket(year_series: pd.Series) -> pd.Series:
    y = pd.to_numeric(year_series, errors="coerce")
    bins = [0, 1995, 2000, 2005, 2010, 2015, 2020, 2023, 9999]
    labels = ["1995 或之前", "1996-2000", "2001-2005", "2006-2010",
              "2011-2015", "2016-2020", "2021-2023", "2024-2026"]
    return pd.cut(y, bins=bins, labels=labels, right=True)


for col, label in [("naive_year", "naive"), ("metadata_year", "metadata"),
                    ("verified_year", "verified")]:
    df[f"bucket_{label}"] = bucket(df[col])

compare = pd.DataFrame({
    "naive": df["bucket_naive"].value_counts().reindex(
        ["1995 或之前", "1996-2000", "2001-2005", "2006-2010", "2011-2015",
         "2016-2020", "2021-2023", "2024-2026"]),
    "metadata_(published_table)": df["bucket_metadata"].value_counts().reindex(
        ["1995 或之前", "1996-2000", "2001-2005", "2006-2010", "2011-2015",
         "2016-2020", "2021-2023", "2024-2026"]),
    "shard_verified": df["bucket_verified"].value_counts().reindex(
        ["1995 或之前", "1996-2000", "2001-2005", "2006-2010", "2011-2015",
         "2016-2020", "2021-2023", "2024-2026"]),
})
compare.to_csv(OUT / "first_filing_year_compare_raw8012.csv")
df.to_csv(OUT / "first_filing_year_per_cik.csv", index=False)

# Report-scope table: the 5,257 entities actually published in section 2.4.
df_report = df[df["cik"].isin(report_ciks)].copy()
compare_report = pd.DataFrame({
    "naive": df_report["bucket_naive"].value_counts().reindex(
        ["1995 或之前", "1996-2000", "2001-2005", "2006-2010", "2011-2015",
         "2016-2020", "2021-2023", "2024-2026"]),
    "metadata_(published_table)": df_report["bucket_metadata"].value_counts().reindex(
        ["1995 或之前", "1996-2000", "2001-2005", "2006-2010", "2011-2015",
         "2016-2020", "2021-2023", "2024-2026"]),
    "shard_verified": df_report["bucket_verified"].value_counts().reindex(
        ["1995 或之前", "1996-2000", "2001-2005", "2006-2010", "2011-2015",
         "2016-2020", "2021-2023", "2024-2026"]),
})
compare_report.to_csv(OUT / "first_filing_year_compare_report5257.csv")
print("\n--- report-scope (5,257 entities) ---")
print(compare_report.to_string(), flush=True)

n_all_present = int(df.loc[df["shards_declared"] > 0, "shards_all_present"].sum())
n_truncated = int((df["shards_declared"] > 0).sum())
summary = {
    "universe_ciks_raw": len(universe_ciks),
    "report_entities": len(report_ciks),
    "truncated_ciks": n_truncated,
    "truncated_ciks_all_shards_present": n_all_present,
    "truncated_ciks_still_missing_some_shard": n_truncated - n_all_present,
    "metadata_vs_shard_verified_mismatches": len(mismatches),
    "naive_vs_metadata_differs_n_ciks": int((df["naive_first_filing_date"]
                                              != df["metadata_first_filing_date"]).sum()),
    "metadata_vs_verified_differs_n_ciks": int((df["metadata_first_filing_date"]
                                                 != df["verified_first_filing_date"]).sum()),
    "report_scope_metadata_equals_published_table": compare_report["metadata_(published_table)"].tolist(),
}
with open(OUT / "recompute_summary.json", "w", encoding="utf-8") as fh:
    json.dump(summary, fh, ensure_ascii=False, indent=2)
with open(OUT / "mismatches.json", "w", encoding="utf-8") as fh:
    json.dump(mismatches, fh, ensure_ascii=False, indent=2)

print(compare.to_string(), flush=True)
print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
