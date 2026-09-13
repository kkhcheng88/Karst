# -*- coding: utf-8 -*-
"""KARST-236 第 5 步:核對改動後 84 包的 sha256。

以 `cache/packets_sha_before_fix235.json`(KARST-235 修正前快照)為底:
  * 九包(八包實改 + E006 只備份未改)列出 before/after;
  * 其餘 75 包必須逐包 sha 不變 —— **一包變了就當失敗**。

只讀封包;輸出 `audit_out_fixed/packets_sha_after_fix235.json` 與
`audit_out_fixed/sha_compare.csv`。不列公司名或代號。
用法:`PYTHONUTF8=1 python audit_sha_after_fix235.py`
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "audit_out_fixed"
OUT_DIR.mkdir(exist_ok=True)
PKT = HERE / "packets"
BEFORE = HERE / "cache" / "packets_sha_before_fix235.json"
NINE = ["E017", "E021", "E022", "E024", "E025", "E047", "E057", "E073", "E006"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    before = json.load(open(BEFORE, encoding="utf-8"))
    after = {p.stem: sha(p) for p in sorted(PKT.glob("*.json"))}
    json.dump(after, open(OUT_DIR / "packets_sha_after_fix235.json", "w",
                          encoding="utf-8"), ensure_ascii=False, indent=1)
    rows, changed, untouched_changed, missing = [], [], [], []
    for eid in sorted(set(before) | set(after)):
        b, a = before.get(eid), after.get(eid)
        if b is None or a is None:
            missing.append(eid)
            continue
        same = b == a
        rows.append({"event_id": eid, "group": "nine" if eid in NINE else "rest",
                     "sha_before": b, "sha_after": a, "same": int(same)})
        if not same:
            (changed if eid in NINE else untouched_changed).append(eid)
    with open(OUT_DIR / "sha_compare.csv", "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    nine = [r for r in rows if r["group"] == "nine"]
    rest = [r for r in rows if r["group"] == "rest"]
    summ = {"n_before": len(before), "n_after": len(after),
            "n_nine": len(nine), "n_rest": len(rest),
            "nine_changed": sorted(changed),
            "nine_unchanged": sorted(r["event_id"] for r in nine
                                     if r["same"]),
            "rest_changed": sorted(untouched_changed),
            "rest_all_unchanged": int(not untouched_changed),
            "missing": missing}
    json.dump(summ, open(OUT_DIR / "sha_compare_summary.json", "w",
                         encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
