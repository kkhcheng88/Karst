# -*- coding: utf-8 -*-
"""診斷:依 s5 的排序取頭幾個「未快取」宇宙事件,逐個計時抓索引頁與附件,印出狀態。"""
from __future__ import annotations

import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE.parent / "A" / "edgar_cache"
UA = {"User-Agent": "Karst research kaho@example.com"}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 6


def get(url: str, timeout: int = 20):
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=timeout) as r:
            b = r.read()
        return ("HTTP %s %dB" % (r.status, len(b)), b, time.time() - t0)
    except urllib.error.HTTPError as e:
        return ("HTTPError %s" % e.code, b"", time.time() - t0)
    except Exception as e:  # noqa: BLE001
        return ("%s %s" % (type(e).__name__, e), b"", time.time() - t0)


def main() -> None:
    ev = pd.read_parquet(CACHE / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    pm = pd.read_parquet(CACHE / "price_metrics.parquet")[
        ["accessionNumber", "px_status", "listed_lt_12m", "rel_spy", "rel_sic2",
         "reaction_date"]]
    to = pd.read_parquet(CACHE / "turnover60.parquet")[
        ["accessionNumber", "turnover_mean_60d"]]
    df = ev.merge(pm, on="accessionNumber", how="left").merge(to, on="accessionNumber",
                                                              how="left")
    sic = df["sic"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(4)
    inu = ((df["px_status"].fillna("x") == "")
           & (df["turnover_mean_60d"] >= 10_000_000.0)
           & df["listed_lt_12m"].fillna(1).eq(0) & (sic != "6770") & (df["has_1_01"] == 0))
    sel = df[inu].copy()
    have = {f.split("__")[0] for f in os.listdir(DOCS) if f.endswith("__EX991.txt.gz")}
    sel["an"] = sel["accessionNumber"].str.replace("-", "", regex=False)
    sel = sel[~sel["an"].isin(have)]
    print("未快取宇宙事件 %d;試頭 %d 個" % (len(sel), N), flush=True)
    for r in sel.head(N).itertuples(index=False):
        acc = r.accessionNumber
        base = "https://www.sec.gov/Archives/edgar/data/%d/%s" % (int(r.cik),
                                                                  acc.replace("-", ""))
        st, b, dt = get(base + "/" + acc + "-index.html")
        print("  %s cik=%s 索引 %s %.2fs" % (acc, r.cik, st, dt), flush=True)
        if not b:
            time.sleep(0.4)
            continue
        page = b.decode("utf-8", "ignore")
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
            print("    無 EX-99.x", flush=True)
            time.sleep(0.4)
            continue
        st2, b2, dt2 = get(base + "/" + doc)
        print("    doc %s %s %.2fs" % (doc, st2, dt2), flush=True)
        time.sleep(0.4)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
