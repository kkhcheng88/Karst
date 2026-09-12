# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2):判同日帶 Item 1.01 的 8-K 正文是否含併購字眼。

執行口徑 v1.2 第 5 項 (c) 字面:正文含 merger / acquisition / agreement and plan of
merger / acquire 者剔;僅 Item 1.01 而無字眼者**不剔**(並記舊閘誤剔數)。

輸入 `A/edgar_cache/{accnodash}__8K.txt.gz` 與 `cache/merger_fetch_list.json`;
輸出 `cache/merger_text.parquet`:accessionNumber, has_merger_words, matched, chars, status
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE.parent / "A" / "edgar_cache"

WORDS = {
    "merger": re.compile(r"(?i)\bmerger"),
    "acquisition": re.compile(r"(?i)\bacquisition"),
    "agreement and plan of merger": re.compile(r"(?i)agreement and plan of merger"),
    "acquire": re.compile(r"(?i)\bacquire"),
}


def main() -> None:
    need = json.loads((CACHE / "merger_fetch_list.json").read_text(encoding="utf-8"))
    rows = []
    for acc in need:
        p = DOCS / ("%s__8K.txt.gz" % acc.replace("-", ""))
        if not p.exists():
            rows.append(dict(accessionNumber=acc, has_merger_words=None,
                             matched="", chars=0, status="未抓到正文"))
            continue
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                t = f.read()
        except OSError:
            rows.append(dict(accessionNumber=acc, has_merger_words=None,
                             matched="", chars=0, status="讀取失敗"))
            continue
        hit = [k for k, rx in WORDS.items() if rx.search(t)]
        rows.append(dict(accessionNumber=acc, has_merger_words=bool(hit),
                         matched="|".join(hit), chars=len(t),
                         status="ok_words" if hit else "ok_no_words"))
    df = pd.DataFrame(rows)
    df.to_parquet(CACHE / "merger_text.parquet", index=False)
    print("判過 %d 宗 1.01 的 8-K 正文;含併購字眼 %d;不含 %d;未抓到 %d"
          % (len(df), int(df["has_merger_words"].fillna(False).sum()),
             int((df["has_merger_words"] == False).sum()),              # noqa: E712
             int(df["has_merger_words"].isna().sum())))
    print("命中的字:", df["matched"].value_counts().head(8).to_dict())
    print("→", CACHE / "merger_text.parquet")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
