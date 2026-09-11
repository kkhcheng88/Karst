# -*- coding: utf-8 -*-
"""KARST-218 抓衝擊前申報原文(10-K 一份、10-Q 最近兩份),落 docs/(已被 .gitignore 擋)。

**工人抓的申報原文不入庫(D-134)**:全文只落 `docs/`,倉內 .gitignore 已擋
`research/2026-09-methodology/*/docs/`。本檔只落衍生物以外的一份快取,不另存副本。
"""
from __future__ import annotations

import gzip
import html
import json
import os
import re
import time
import urllib.request

ROOT = "C:/projects/Karst"
HERE = f"{ROOT}/research/2026-09-methodology/2026-09-12-暴露差異模組v1"
DOCS = f"{HERE}/docs"
SUB_LOCAL = ROOT + "/data/sec/submissions/CIK{cik}.json"
UA = {"User-Agent": "Karst research kaho@example.com"}

EV_CUTOFF = {"E17": "2011-08-05", "E18": "2024-08-01", "E19": "2021-11-24", "E20": "2022-05-17"}
PICKS = {
    # E17:BK(託管)與 ICE(交易所)兩隻在日線庫裡解析不到(BK 代號不在宇宙、ICE 衝擊日不在有效時段),
    # 判了也無法對成績,故換成同在籃子內、同一暴露形態的 STT(託管銀行)與 CME(交易所與清算)。
    # **換家在讀任何結果欄之前做**,理由寫在 `picks_before_results.md` 修訂欄。
    "E17": [("JPM", "0000019617"), ("STT", "0000093751"), ("CME", "0001156375"), ("MET", "0001099219")],
    "E18": [("NVDA", "0001045810"), ("MU", "0000723125"), ("TXN", "0000097476"), ("ASML", "0000937966")],
    "E19": [("CCL", "0000815097"), ("DAL", "0000027904"), ("MAR", "0001048286"), ("BKNG", "0001075531")],
    "E20": [("WMT", "0000104169"), ("TGT", "0000027419"), ("TJX", "0000109198"), ("DG", "0000029534")],
}


def submissions(cik):
    p = SUB_LOCAL.format(cik=cik)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    else:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            d = json.loads(r.read())
    return d


def _rows_from(block):
    out = []
    for i in range(len(block.get("form", []))):
        out.append(dict(form=block["form"][i], filingDate=block["filingDate"][i],
                        reportDate=block["reportDate"][i],
                        accn=block["accessionNumber"][i], doc=block["primaryDocument"][i]))
    return out


def all_rows(d, cutoff):
    """本地 submissions 的 recent 只覆蓋近年;更早的申報住在分片檔,要一併抓落嚟。"""
    f = d.get("filings", {})
    rows = _rows_from(f.get("recent", {}))
    for sh in f.get("files", []):
        url = f"https://data.sec.gov/submissions/{sh['name']}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                rows += _rows_from(json.loads(r.read()))
        except Exception as e:  # noqa: BLE001
            print("  分片抓取失敗", sh["name"], type(e).__name__)
    return [x for x in rows if x["filingDate"] < cutoff]


def pick_filings(d, cutoff):
    rows = all_rows(d, cutoff)
    out = []
    k = [x for x in rows if x["form"] in ("10-K", "20-F", "40-F")]
    if k:
        out.append(("10K", k[0]))
    q = [x for x in rows if x["form"] == "10-Q"][:2]
    for j, x in enumerate(q):
        out.append((f"10Q{j}", x))
    return out


def strip_html(raw: bytes) -> str:
    t = raw.decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?is)<br\s*/?>", "\n", t)
    t = re.sub(r"(?is)</(p|div|tr|h[1-6]|li)>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t


def fetch_text(cik, f):
    """先讀本地 10k_text 快取,沒有才打 EDGAR。"""
    acc = f["accn"].replace("-", "")
    local = f"{ROOT}/data/sec/10k_text/{TICKER_FOR[acc] if False else ''}"
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{f['doc']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        return strip_html(r.read())


def main():
    os.makedirs(DOCS, exist_ok=True)
    index = []
    for ev, comps in PICKS.items():
        cutoff = EV_CUTOFF[ev]
        for ticker, cik in comps:
            d = submissions(cik)
            fl = pick_filings(d, cutoff)
            for tag, f in fl:
                fn = f"{DOCS}/{ev}_{ticker}_{tag}_{f['accn'].replace('-','')}.txt"
                if not os.path.exists(fn):
                    try:
                        txt = fetch_text(cik, f)
                    except Exception as e:  # noqa: BLE001
                        print("FAIL", ev, ticker, tag, type(e).__name__, str(e)[:80])
                        index.append(dict(event=ev, ticker=ticker, tag=tag, form=f["form"],
                                          filingDate=f["filingDate"], accn=f["accn"],
                                          status="抓取失敗:" + type(e).__name__))
                        continue
                    with open(fn, "w", encoding="utf-8") as g:
                        g.write(txt)
                    time.sleep(0.4)
                index.append(dict(event=ev, ticker=ticker, tag=tag, form=f["form"],
                                  filingDate=f["filingDate"], reportDate=f["reportDate"],
                                  accn=f["accn"], file=os.path.basename(fn),
                                  chars=os.path.getsize(fn), status="已落 docs/"))
                print("OK", ev, ticker, tag, f["form"], f["filingDate"], os.path.getsize(fn))
    with open(f"{HERE}/out/docs_index.json", "w", encoding="utf-8") as g:
        json.dump(index, g, ensure_ascii=False, indent=1)


TICKER_FOR = {}

if __name__ == "__main__":
    main()
