"""KARST-174 附帶查證:正本的 filings.files 分頁缺口有多大,silent-revisions 補到幾多。

只讀。輸出 out/shard_gap.json。
"""
import json
import os
import re

ROOT = r"C:\projects\Karst"
CANON = os.path.join(ROOT, "data", "sec", "submissions")
SHARDS = os.path.join(ROOT, "experiments", "2026-09-02-silent-revisions", "data", "submissions")
OUT = os.path.join(ROOT, "experiments", "2026-09-03-submissions-dedup", "out")


def main():
    have = set(n for n in os.listdir(SHARDS) if "-submissions-" in n)

    total = truncated = 0
    declared = covered = 0
    ciks_truncated, ciks_fully_covered = set(), set()
    for name in os.listdir(CANON):
        if not name.upper().startswith("CIK") or not name.endswith(".json"):
            continue
        total += 1
        with open(os.path.join(CANON, name), encoding="utf-8") as f:
            doc = json.load(f)
        files = (doc.get("filings") or {}).get("files") or []
        if not files:
            continue
        truncated += 1
        cik = re.sub(r"\D", "", name)
        ciks_truncated.add(cik)
        names = [x["name"] for x in files]
        declared += len(names)
        got = [n for n in names if n in have]
        covered += len(got)
        if len(got) == len(names):
            ciks_fully_covered.add(cik)

    res = {
        "canon_files": total,
        "canon_truncated_files": truncated,
        "canon_truncated_pct": round(100.0 * truncated / total, 1),
        "declared_shards": declared,
        "shards_present_in_silent_revisions": covered,
        "shard_coverage_pct": round(100.0 * covered / declared, 1) if declared else 0,
        "ciks_truncated": len(ciks_truncated),
        "ciks_fully_covered_by_shards": len(ciks_fully_covered),
        "shard_files_on_disk": len(have),
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "shard_gap.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
