# -*- coding: utf-8 -*-
"""出處核對第三輪:逐宗定兩條可連線核對的出處(EDGAR 8-K/6-K + 官方文件)。"""
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
 ("E21_ECB", "https://www.ecb.europa.eu/press/pr/date/2016/html/pr160624.en.html"),
 ("E21_BOE_pdf", "https://www.bankofengland.co.uk/-/media/boe/files/news/2016/june/statement-from-the-governor-following-the-eu-referendum-result.pdf"),
 ("E24_govinfo", "https://www.govinfo.gov/content/pkg/FR-2022-10-13/html/2022-22273.htm"),
 ("E24_BIS", "https://www.bis.doc.gov/index.php/documents/about-bis/newsroom/press-releases/3158-bis-press-release-chips-and-scientific-act"),
 ("E25_UAW", "https://uaw.org/2023/09/14/uaw-stand-up-strike-begins/"),
 ("E26_TREAS", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value=2023"),
]

FTS = [
 ("E21 6-K referendum", '"referendum"', "2016-06-23", "2016-07-31", "6-K"),
 ("E23 crypto 8-K", '"Celsius" OR "digital asset"', "2022-06-10", "2022-07-15", "8-K"),
 ("E25 strike 8-K", '"strike"', "2023-09-13", "2023-10-31", "8-K"),
 ("E26 REIT 8-K", '"10-year Treasury"', "2023-09-18", "2023-11-15", "8-K"),
]


def head(u):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            body = r.read(10000).decode("utf-8", "ignore")
            t = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
            title = re.sub(r"\s+", " ", t.group(1)).strip()[:70] if t else ""
            return f"{r.status} :: {title}"
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
