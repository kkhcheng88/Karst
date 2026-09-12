# -*- coding: utf-8 -*-
"""KARST-222 票 A 第四步補:同日 8-K Item 1.01(重大收購/處置)名單。

執行口徑 v1 第一節的排除條件之一「同日 8-K 有 Item 1.01(合併)」= **同一家公司同一日**
有任何 8-K/8-K/A 帶 Item 1.01,而該日的 2.02 事件要剔。s1 只看了 2.02 那些申報,
所以同日另一份 8-K 帶 1.01 的情況它抓不到;本檔補這個掃描。

只讀 `data/sec/submissions/`;輸出 `A/cache/merger_days.parquet`(cik, filingDate)。
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

WIN_START, WIN_END = "2015-01-01", "2025-06-30"


def main() -> None:
    rows: list[tuple[str, str]] = []
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
        cik = d.get("cik", "")
        for i in range(len(forms)):
            if forms[i] not in ("8-K", "8-K/A"):
                continue
            fd = dates[i] if i < len(dates) else ""
            if not (WIN_START <= fd <= WIN_END):
                continue
            it = items_l[i] if i < len(items_l) else ""
            if it and "1.01" in [x.strip() for x in it.split(",")]:
                rows.append((cik, fd))

    df = pd.DataFrame(rows, columns=["cik", "filingDate"]).drop_duplicates()
    df.to_parquet(CACHE / "merger_days.parquet", index=False)
    print("掃過 %d 個 submissions 快取檔" % n_files)
    print("公司—日 帶 Item 1.01 的 8-K 名單:%d 對(涉及 %d 家)"
          % (len(df), df["cik"].nunique()))
    print("逐年:", df["filingDate"].str[:4].value_counts().sort_index().to_dict())
    print("→", CACHE / "merger_days.parquet")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
