# -*- coding: utf-8 -*-
"""逐宗找兩條可連線核對的出處:先試指定 URL,再用 EDGAR full-text search 找成員公司的申報。"""
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
 ("C2_BOE_a", "https://www.bankofengland.co.uk/news/2016/june/mark-carney-statement-following-the-eu-referendum-result"),
 ("C2_BOE_b", "https://www.bankofengland.co.uk/news/2016/june"),
 ("C2_GOVUK", "https://www.gov.uk/government/news/eu-referendum-result"),
 ("C4_CELSIUS", "https://celsius.network/a-message-from-celsius"),
 ("C12_BIS_a", "https://www.bis.doc.gov/index.php/documents/about-bis/newsroom/press-releases/3158-2022-10-07-bis-press-release-chips-and-scientific-act"),
 ("C12_WH", "https://www.whitehouse.gov/briefing-room/statements-releases/2022/10/07/fact-sheet-the-biden-administration-imposes-sweeping-new-export-controls-on-the-peoples-republic-of-china/"),
 ("C11_UAW_a", "https://uaw.org/stand-up-strike/"),
 ("C11_UAW_b", "https://uaw.org/uaw-announces-stand-up-strike-strategy-at-the-big-three/"),
 ("C17_TREAS", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value=2023"),
 ("C21_AMZN", "https://press.aboutamazon.com/2018/1/amazon-berkshire-hathaway-and-jpmorgan-chase-to-partner-on-u-s-employee-health-care"),
 ("C21_JPM", "https://www.jpmorganchase.com/newsroom/press-releases/2018/amazon-berkshire-hathaway-jpmorgan-chase-partner"),
 ("C22_MFA", "https://www.congress.gov/bill/116th-congress/senate-bill/1129"),
]

FTS = [
 ("E21 Brexit banks", '"EU referendum"', "2016-06-01", "2016-07-31"),
 ("E23 Celsius", '"Celsius"', "2022-06-01", "2022-07-15"),
 ("E25 UAW", '"stand-up strike"', "2023-09-01", "2023-10-31"),
 ("E26 10-year yield", '"10-year Treasury yield"', "2023-09-15", "2023-10-31"),
 ("E27 health venture", '"health care"', "2018-01-25", "2018-02-05"),
]


def head(u):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
            body = r.read(8000).decode("utf-8", "ignore")
            t = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
            title = re.sub(r"\s+", " ", t.group(1)).strip()[:70] if t else ""
            return f"{r.status} :: {title}"
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__} {str(e)[:50]}"


def fts(q, d1, d2):
    url = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(q)
           + "&dateRange=custom&startdt=" + d1 + "&enddt=" + d2
           + "&forms=8-K")
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        hits = d.get("hits", {}).get("hits", [])[:6]
        out = []
        for h in hits:
            s = h.get("_source", {})
            out.append((s.get("display_names", [""])[0][:40], s.get("file_date"),
                        h.get("_id", "")[:60]))
        return out
    except Exception as e:  # noqa: BLE001
        return [("ERR", type(e).__name__, str(e)[:60])]


def main() -> None:
    for k, u in URLS:
        print(k, "|", head(u), flush=True)
    print("--- EDGAR FTS (8-K) ---")
    for label, q, d1, d2 in FTS:
        print("###", label, flush=True)
        for row in fts(q, d1, d2):
            print("   ", row, flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
