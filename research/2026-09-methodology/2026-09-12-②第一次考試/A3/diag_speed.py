# -*- coding: utf-8 -*-
"""診斷:索引頁 + EX-99.1 文件兩段抓取的實際耗時與大小(5 宗事件)。只讀不寫檔。"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
DOCS = HERE.parent / "A" / "edgar_cache"
UA = {"User-Agent": "Karst research kaho@example.com"}


def get(url: str, timeout: int = 60) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                timeout=timeout) as r:
        return r.read()


def main() -> None:
    ev = pd.read_parquet(HERE / "cache" / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    have = {f.split("__")[0] for f in __import__("os").listdir(DOCS)
            if f.endswith("__EX991.txt.gz")}
    ev["an"] = ev["accessionNumber"].str.replace("-", "", regex=False)
    cand = ev[(ev["filingDate"] >= "2022-01-01") & (~ev["an"].isin(have))].head(6)
    t_all = time.time()
    for r in cand.itertuples(index=False):
        acc, an, cik = r.accessionNumber, r.an, int(r.cik)
        base = "https://www.sec.gov/Archives/edgar/data/%d/%s" % (cik, an)
        t0 = time.time()
        try:
            page = get(base + "/" + acc + "-index.html").decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            print("  索引失敗", type(e).__name__, flush=True)
            time.sleep(0.34)
            continue
        t_idx = time.time() - t0
        doc = ""
        for tr in re.findall(r"(?is)<tr.*?</tr>", page):
            href = re.search(r'href="([^"]+)"', tr)
            if not href:
                continue
            tds = re.findall(r"(?is)<td[^>]*>\s*([^<]*?)\s*</td>", tr)
            if any(re.match(r"(?i)^EX-?9", t) for t in tds):
                doc = href.group(1).rsplit("/", 1)[-1]
                break
        if not doc:
            print("  無 EX-99.x 連結", flush=True)
            time.sleep(0.34)
            continue
        t1 = time.time()
        try:
            raw = get(base + "/" + doc, timeout=90)
        except Exception as e:  # noqa: BLE001
            print("  文件失敗", type(e).__name__, flush=True)
            time.sleep(0.34)
            continue
        t_doc = time.time() - t1
        print("  idx %.2fs %dKB | doc %.2fs %dKB | 合計 %.2fs"
              % (t_idx, len(page) // 1024, t_doc, len(raw) // 1024, t_idx + t_doc),
              flush=True)
        time.sleep(0.34)
    print("6 宗合計 %.1fs" % (time.time() - t_all))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
