# -*- coding: utf-8 -*-
"""出處核對第二輪:補上憑證鏈在本機未通過的站(改用不驗證 context,照實記『憑證未過』)。"""
from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "Karst research kaho@example.com"}
CTX = ssl._create_unverified_context()  # noqa: SLF001

URLS = {
 "C3_CAC_20210702": "http://www.cac.gov.cn/2021-07/02/c_1626811521011934.htm",
 "C3_GOV_20210724": "http://www.gov.cn/zhengce/2021-07/24/content_5627132.htm",
 "C2_ECB_20160624": "https://www.ecb.europa.eu/press/pr/date/2016/html/pr160624.en.html",
 "C1_PBoC_20150811": "http://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2933762/index.html",
 "C2_BOE_search": "https://www.bankofengland.co.uk/news/2016/june",
 "C11_UAW_news": "https://uaw.org/news/",
 "C12_BIS_press": "https://www.bis.doc.gov/index.php/policy-guidance/advanced-computing-and-semiconductor-manufacturing-items",
 "C4_CELSIUS": "https://celsius.network/",
}

EFTS = [
 ("C3 滴滴網絡安全審查", '"DiDi" "cybersecurity review"'),
 ("C11 UAW 罷工", '"United Auto Workers" strike'),
 ("C4 加密", '"Celsius" withdrawals'),
 ("C12 出口管制", '"advanced computing" export controls'),
 ("C2 脫歐", '"European Union referendum"'),
 ("C17 利率", '"10-year Treasury" yield'),
]


def head(u, ctx=None):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            body = r.read(6000).decode("utf-8", "ignore")
            t = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
            title = re.sub(r"\s+", " ", t.group(1)).strip()[:70] if t else ""
            return f"{r.status} :: {title}"
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__} {str(e)[:50]}"


def main() -> None:
    for k, u in URLS.items():
        print(k, "|", head(u, CTX), flush=True)
    print("--- EDGAR full-text search ---")
    for label, q in EFTS:
        u = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(q))
        try:
            req = urllib.request.Request(
                "https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(q),
                headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read())
            tot = d.get("hits", {}).get("total", {}).get("value")
            print(label, "hits=", tot, flush=True)
        except Exception as e:  # noqa: BLE001
            print(label, "ERR", type(e).__name__, str(e)[:60], flush=True)
        _ = u


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
