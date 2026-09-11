# -*- coding: utf-8 -*-
"""出處核對第四輪:鎖定 E21/E23/E24/E25/E26 的第二條(成員公司申報)並連線核。"""
from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "Karst research kaho@example.com"}
CTX = ssl._create_unverified_context()  # noqa: SLF001

URLS = [
 ("E21_AVIVA_6K", "https://www.sec.gov/Archives/edgar/data/1140022/000119163816002226/av201606246k.htm"),
 ("E21_LLOYDS_6K", "https://www.sec.gov/Archives/edgar/data/1163002/000165495416000992/a4588f.htm"),
 ("E23_GDLC_8K", "https://www.sec.gov/Archives/edgar/data/1729997/000095017022012299/gdlc-20220629.htm"),
 ("E24_FR", "https://www.govinfo.gov/content/pkg/FR-2022-10-13/html/2022-22273.htm"),
 ("E25_DANA_8K", "https://www.sec.gov/Archives/edgar/data/26780/000119312523264461/d528555dex991.htm"),
 ("E25_UAW", "https://uaw.org/news/"),
 ("E27_HCA_8K", "https://www.sec.gov/Archives/edgar/data/860730/000119312518024575/d521507dex991.htm"),
 ("E27_AETNA_8K", "https://www.sec.gov/Archives/edgar/data/1122304/000112230418000011/exhibit99_1.htm"),
]

FTS = [
 ("E24 export 8-K", '"export controls"', "2022-10-01", "2022-11-30", "8-K"),
 ("E26 REIT 10月 8-K", '"REIT" AND "interest rates"', "2023-10-01", "2023-11-15", "8-K"),
 ("E22 China ADR 8-K", '"regulatory"', "2021-07-02", "2021-08-15", "6-K"),
]


def head(u):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            body = r.read(200000).decode("utf-8", "ignore")
            t = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
            title = re.sub(r"\s+", " ", t.group(1)).strip()[:60] if t else ""
            txt = re.sub(r"(?s)<[^>]+>", " ", body)
            txt = re.sub(r"\s+", " ", txt)
            return f"{r.status} :: {title} :: {txt[:160]}"
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__} {str(e)[:50]}"


def fts(q, d1, d2, forms):
    url = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(q)
           + "&dateRange=custom&startdt=" + d1 + "&enddt=" + d2 + "&forms=" + forms)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        out = []
        for h in d.get("hits", {}).get("hits", [])[:8]:
            s = h.get("_source", {})
            out.append((s.get("display_names", [""])[0][:44], s.get("file_date"),
                        h.get("_id", "")[:58]))
        return out
    except Exception as e:  # noqa: BLE001
        return [("ERR", type(e).__name__, str(e)[:60])]


def main() -> None:
    for k, u in URLS:
        print(k, "|", head(u), flush=True)
    print("--- EDGAR FTS ---")
    for label, q, d1, d2, forms in FTS:
        print("###", label, flush=True)
        for row in fts(q, d1, d2, forms):
            print("   ", row, flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
