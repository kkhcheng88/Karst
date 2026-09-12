# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2)第二步之一:由 EX-99.1 全文解析**稿頭日期**(dateline)。

執行口徑 v1.2 第 2 項。稿頭日期 = 業績稿開頭新聞稿資料日期(通常寫成
「CITY, State, March 27, 2025 --」)。做法:
  - 只讀 `A/edgar_cache/` 內已有的 `*__EX991.txt.gz`(已抓到者),不聯網。
  - 在正文**首 2,500 字元**找第一個「Month DD, YYYY」形式且日期合理的候選;
    找不到則放寬到首 8,000 字元。
  - 合理性:年份 2005–2026、日期不遲於申報日、與申報日相距 ≤ 45 日
    (遠處的日期多為財務期間引用,不是稿頭)。
輸出 `cache/dateline.parquet`:`accessionNumber, dateline, dateline_span, chars, parsed`。
"""
from __future__ import annotations

import datetime as dt
import gzip
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE.parent / "A" / "edgar_cache"

MONTHS = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
          "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
          "december": 12,
          "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
          "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
MON_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
DATE_RE = re.compile(r"\b(" + MON_RE + r")\.?\s+(\d{1,2}),?\s+(\d{4})\b", re.I)
NEAR = 2500
FAR = 8000
MAX_LAG_DAYS = 45


def parse_dateline(txt: str, filing_date: str) -> tuple[str, str]:
    """回傳 (日期 ISO, 命中位置類別);找不到回 ("", "")。"""
    fd = dt.date.fromisoformat(filing_date)
    for span, name in ((NEAR, "首2500字"), (FAR, "首8000字")):
        head = txt[:span]
        for m in DATE_RE.finditer(head):
            try:
                d = dt.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
            except (ValueError, KeyError):
                continue
            if not (2005 <= d.year <= 2026):
                continue
            lag = (fd - d).days
            if lag < 0 or lag > MAX_LAG_DAYS:
                continue
            return d.isoformat(), name
    return "", ""


def main() -> None:
    ev = pd.read_parquet(CACHE / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    rows = []
    for r in ev.itertuples(index=False):
        an = r.accessionNumber.replace("-", "")
        p = DOCS / ("%s__EX991.txt.gz" % an)
        if not p.exists():
            rows.append(dict(accessionNumber=r.accessionNumber, dateline="",
                             dateline_span="", chars=0, has_text=0))
            continue
        try:
            txt = gzip.open(p, "rt", encoding="utf-8").read()
        except OSError:
            rows.append(dict(accessionNumber=r.accessionNumber, dateline="",
                             dateline_span="", chars=0, has_text=0))
            continue
        d, span = parse_dateline(txt, r.filingDate)
        rows.append(dict(accessionNumber=r.accessionNumber, dateline=d,
                         dateline_span=span, chars=len(txt), has_text=1))
    df = pd.DataFrame(rows)
    df.to_parquet(CACHE / "dateline.parquet", index=False)
    ht = df[df["has_text"] == 1]
    print("事件總數:%d;有全文:%d;解析到稿頭日期:%d(%.1f%% of 有全文)"
          % (len(df), len(ht), int((ht["dateline"] != "").sum()),
             100.0 * (ht["dateline"] != "").sum() / max(len(ht), 1)))
    print("命中位置分佈:", ht["dateline_span"].value_counts().to_dict())
    print("→", CACHE / "dateline.parquet")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
