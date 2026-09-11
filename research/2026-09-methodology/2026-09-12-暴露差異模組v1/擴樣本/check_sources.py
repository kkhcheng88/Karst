# -*- coding: utf-8 -*-
"""KARST-220 出處連線核對:逐條 URL 打一次,只報狀態碼與標題前 80 字。"""
from __future__ import annotations

import re
import sys
import urllib.request

UA = {"User-Agent": "Karst research kaho@example.com"}

URLS = {
 "C1_PBoC20150811": "http://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2933762/index.html",
 "C1_FED_2015": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20150917a.htm",
 "C2_BOE_20160624": "https://www.bankofengland.co.uk/news/2016/june/statement-from-the-governor-following-the-eu-referendum-result",
 "C2_ECB_20160624": "https://www.ecb.europa.eu/press/pr/date/2016/html/pr160624.en.html",
 "C2_ELECTORAL": "https://www.electoralcommission.org.uk/who-we-are-and-what-we-do/elections-and-referendums/past-elections-and-referendums/eu-referendum/results-and-turnout-eu-referendum",
 "C3_CAC_20210702": "http://www.cac.gov.cn/2021-07/02/c_1626811521011934.htm",
 "C3_GOV_20210724": "http://www.gov.cn/zhengce/2021-07/24/content_5627132.htm",
 "C4_FOMC_20220615": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20220615a.htm",
 "C4_SEC_202206": "https://www.sec.gov/news/press-release/2022-100",
 "C4_FRED_VIX": "https://fred.stlouisfed.org/series/VIXCLS",
 "C11_UAW_20230914": "https://uaw.org/uaw-stand-up-strike-begins/",
 "C11_FORD_8K": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000037996&type=8-K&dateb=&owner=include&count=40",
 "C12_BIS_20221007": "https://www.bis.doc.gov/index.php/documents/about-bis/newsroom/press-releases/3158-2022-10-07-bis-press-release-chips-and-scientific-act",
 "C12_FR_20221013": "https://www.federalregister.gov/documents/2022/10/13/2022-22273/implementation-of-additional-export-controls-certain-advanced-computing-and-semiconductor",
 "C17_FRED_DGS10": "https://fred.stlouisfed.org/series/DGS10",
 "C17_POWELL_20231019": "https://www.federalreserve.gov/newsevents/speech/powell20231019a.htm",
 "C17_FOMC_20230920": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20230920a.htm",
}


def main() -> None:
    for k, u in URLS.items():
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read(4000).decode("utf-8", "ignore")
                t = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
                title = re.sub(r"\s+", " ", t.group(1)).strip()[:80] if t else ""
                print(f"{r.status} {k} :: {title}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"ERR {k} {type(e).__name__} {str(e)[:60]}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
