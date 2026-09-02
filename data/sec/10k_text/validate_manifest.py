"""年報全文快取 manifest 唯讀校驗(KARST-163,D-134 單一原料庫治理)。

只讀不寫:本腳本不會改動 manifest.jsonl,也不會改動任何 .txt.gz。
它逐行檢查五件事:

  1. 必填欄位齊全       ticker cik accession form filingDate reportDate
                        url chars sha256 fetchedAt fetchedBy
  2. 檔案存在           <TICKER>_<accession>.txt.gz
  3. sha256 對得上      對「解壓後的 UTF-8 純文本位元組」取 sha256
                        (不是對 .gz 檔本身;兩支抓取腳本都是這樣寫的)
  4. accession 沒有重複
  5. 目錄裡沒有 manifest 未登記的孤兒 .txt.gz

用法:
    set PYTHONUTF8=1
    python validate_manifest.py            # 全部行(要解壓 9,900+ 個檔,約數分鐘)
    python validate_manifest.py --fast     # 只查欄位/檔案存在/重複,略過 sha256
    python validate_manifest.py --sample 300   # 隨機抽 300 行核 sha256

輸出:主控台摘要 + 同目錄 validate_report.json(對不上的行的清單)。
發現對不上的行只列出,不會修——修法要在票上 raise 由人裁。
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.jsonl"
REPORT = HERE / "validate_report.json"

REQUIRED = ["ticker", "cik", "accession", "form", "filingDate", "reportDate",
            "url", "chars", "sha256", "fetchedAt", "fetchedBy"]
OPTIONAL = ["primaryDoc"]


def sha_of(path: Path) -> tuple[str, int]:
    """回傳 (解壓後純文本的 sha256, 字元數)。"""
    blob = gzip.decompress(path.read_bytes())
    return hashlib.sha256(blob).hexdigest(), len(blob.decode("utf-8", "replace"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="略過 sha256 核對")
    ap.add_argument("--sample", type=int, default=0, help="只抽 N 行核 sha256")
    args = ap.parse_args()

    if not MANIFEST.exists():
        print(f"manifest not found: {MANIFEST}")
        return 2

    rows: list[dict] = []
    bad_json: list[dict] = []
    with MANIFEST.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            s = line.strip()
            if not s:
                continue
            try:
                rows.append({"_line": i, **json.loads(s)})
            except Exception as exc:  # noqa: BLE001
                bad_json.append({"line": i, "why": str(exc)[:120]})

    missing_fields: list[dict] = []
    unknown_fields: list[dict] = []
    missing_file: list[dict] = []
    dup_accession: list[dict] = []
    sha_mismatch: list[dict] = []
    chars_mismatch: list[dict] = []

    allowed = set(REQUIRED) | set(OPTIONAL) | {"_line"}
    for r in rows:
        miss = [k for k in REQUIRED if k not in r or r[k] in (None, "")]
        if miss:
            missing_fields.append({"line": r["_line"],
                                   "accession": r.get("accession"),
                                   "missing": miss})
        extra = sorted(set(r) - allowed)
        if extra:
            unknown_fields.append({"line": r["_line"],
                                   "accession": r.get("accession"),
                                   "extra": extra})

    seen: dict[str, int] = {}
    for r in rows:
        acc = r.get("accession")
        if acc is None:
            continue
        if acc in seen:
            dup_accession.append({"accession": acc,
                                  "first_line": seen[acc],
                                  "dup_line": r["_line"],
                                  "ticker": r.get("ticker")})
        else:
            seen[acc] = r["_line"]

    # 檔案存在 + 檔名對得上 ticker+accession
    for r in rows:
        t, acc = r.get("ticker"), r.get("accession")
        if not t or not acc:
            continue
        p = HERE / f"{t}_{acc}.txt.gz"
        if not p.exists():
            missing_file.append({"line": r["_line"], "ticker": t,
                                 "accession": acc, "expected": p.name})

    # sha256
    todo = [r for r in rows if (HERE / f"{r.get('ticker')}_{r.get('accession')}.txt.gz").exists()]
    if args.fast:
        todo = []
    elif args.sample and args.sample < len(todo):
        random.seed(163)
        todo = random.sample(todo, args.sample)

    for n, r in enumerate(todo, 1):
        p = HERE / f"{r['ticker']}_{r['accession']}.txt.gz"
        try:
            got, nchars = sha_of(p)
        except Exception as exc:  # noqa: BLE001
            sha_mismatch.append({"line": r["_line"], "ticker": r["ticker"],
                                 "accession": r["accession"],
                                 "why": f"unreadable: {exc}"[:120]})
            continue
        if got != r.get("sha256"):
            sha_mismatch.append({"line": r["_line"], "ticker": r["ticker"],
                                 "accession": r["accession"],
                                 "manifest": r.get("sha256"), "file": got})
        if isinstance(r.get("chars"), int) and nchars != r["chars"]:
            chars_mismatch.append({"line": r["_line"], "ticker": r["ticker"],
                                   "accession": r["accession"],
                                   "manifest": r["chars"], "file": nchars})
        if n % 1000 == 0:
            print(f"  sha256 {n}/{len(todo)}", flush=True)

    # 孤兒檔
    on_disk = {p.name for p in HERE.glob("*.txt.gz")}
    registered = {f"{r.get('ticker')}_{r.get('accession')}.txt.gz" for r in rows}
    orphans = sorted(on_disk - registered)

    fetched_by = Counter(r.get("fetchedBy") for r in rows)

    summary = {
        "manifest": str(MANIFEST),
        "rows": len(rows),
        "files_on_disk": len(on_disk),
        "mode": "fast" if args.fast else (f"sample={len(todo)}" if args.sample else "full"),
        "sha256_checked": len(todo),
        "fetchedBy": dict(fetched_by),
        "bad_json": len(bad_json),
        "missing_fields": len(missing_fields),
        "unknown_fields": len(unknown_fields),
        "missing_file": len(missing_file),
        "duplicate_accession": len(dup_accession),
        "sha256_mismatch": len(sha_mismatch),
        "chars_mismatch": len(chars_mismatch),
        "orphan_files": len(orphans),
    }
    report = {
        "summary": summary,
        "bad_json": bad_json,
        "missing_fields": missing_fields[:200],
        "unknown_fields": unknown_fields[:200],
        "missing_file": missing_file[:200],
        "duplicate_accession": dup_accession[:200],
        "sha256_mismatch": sha_mismatch[:200],
        "chars_mismatch": chars_mismatch[:200],
        "orphan_files": orphans[:200],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    for k, v in summary.items():
        print(f"{k:22} {v}")
    print(f"\nreport -> {REPORT}")
    problems = (len(bad_json) + len(missing_fields) + len(missing_file)
                + len(dup_accession) + len(sha_mismatch) + len(orphans))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
