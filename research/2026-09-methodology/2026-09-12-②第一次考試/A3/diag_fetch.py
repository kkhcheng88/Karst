# -*- coding: utf-8 -*-
"""診斷:對一個 accession 試三種 SEC 抓取路徑,印出 HTTP 狀態與大小。只讀不寫檔。"""
from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
UA = {"User-Agent": "Karst research kaho@example.com"}


def try_url(url: str) -> str:
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            b = r.read()
        return "HTTP %s %d bytes %.1fs" % (r.status, len(b), time.time() - t0)
    except urllib.error.HTTPError as e:
        return "HTTPError %s %.1fs" % (e.code, time.time() - t0)
    except Exception as e:  # noqa: BLE001
        return "%s: %s %.1fs" % (type(e).__name__, e, time.time() - t0)


def main() -> None:
    ev = pd.read_parquet(HERE / "cache" / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    r = ev[ev["filingDate"] >= "2024-01-01"].iloc[0]
    acc = r["accessionNumber"]
    an = acc.replace("-", "")
    cik = int(r["cik"])
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s" % (cik, an)
    print("accession", acc, "cik", cik)
    for label, url in (("全文本(帶橫線)", base + "/" + acc + ".txt"),
                       ("全文本(無橫線)", base + "/" + an + ".txt"),
                       ("索引頁", base + "/" + acc + "-index.html"),
                       ("index.json", base + "/index.json")):
        print(" ", label, "→", try_url(url), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
