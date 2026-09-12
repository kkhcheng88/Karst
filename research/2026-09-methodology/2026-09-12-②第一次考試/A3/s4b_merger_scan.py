# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2)第四步之二:掃 submissions,取窗口內全部帶 Item 1.01 或 2.01 的 8-K。

執行口徑 v1.2 第 5 項 (c):併購閘要用「同日 8-K 含 Item 2.01」與「同日 8-K 含 Item 1.01
且正文含併購字眼」,故需要**同日其他 8-K** 的項目與申報編號(母體只收 Item 2.02 的 8-K)。

輸入 `data/sec/submissions/CIK*.json`;輸出 `cache/merger_scan.parquet`:
  cik, filingDate, accessionNumber, primaryDocument, items, has_1_01, has_2_01
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
SUB = ROOT / "data" / "sec" / "submissions"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
WIN_START, WIN_END = "2013-06-01", "2025-12-31"


def main() -> None:
    rows = []
    n_files = 0
    for fp in sorted(SUB.glob("CIK*.json")):
        n_files += 1
        try:
            with open(fp, encoding="utf-8") as f:
                d = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
        r = d.get("filings", {}).get("recent", {})
        forms = r.get("form", [])
        dates = r.get("filingDate", [])
        items_l = r.get("items", [])
        accs = r.get("accessionNumber", [])
        prim = r.get("primaryDocument", [])
        cik = d.get("cik", "")
        for i in range(len(forms)):
            if forms[i] not in ("8-K", "8-K/A"):
                continue
            fd = dates[i] if i < len(dates) else ""
            if not (WIN_START <= fd <= WIN_END):
                continue
            it = items_l[i] if i < len(items_l) else ""
            parts = {x.strip() for x in it.split(",") if x.strip()}
            h1 = int("1.01" in parts)
            h2 = int("2.01" in parts)
            if not (h1 or h2):
                continue
            rows.append((cik, fd, accs[i] if i < len(accs) else "",
                         prim[i] if i < len(prim) else "", it, h1, h2))
        if n_files % 3000 == 0:
            print("  ...掃過 %d 檔,累積 %d 列" % (n_files, len(rows)), flush=True)

    df = pd.DataFrame(rows, columns=["cik", "filingDate", "accessionNumber",
                                     "primaryDocument", "items", "has_1_01", "has_2_01"])
    df = df.drop_duplicates(subset=["accessionNumber"])
    df.to_parquet(CACHE / "merger_scan.parquet", index=False)
    print("掃過 %d 個 submissions 快取檔" % n_files)
    print("帶 1.01 或 2.01 的 8-K:%d 宗(1.01 %d;2.01 %d)"
          % (len(df), int(df["has_1_01"].sum()), int(df["has_2_01"].sum())))
    print("逐年:", df["filingDate"].str[:4].value_counts().sort_index().to_dict())
    print("→", CACHE / "merger_scan.parquet")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
