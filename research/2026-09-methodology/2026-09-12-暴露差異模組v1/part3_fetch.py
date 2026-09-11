# -*- coding: utf-8 -*-
"""KARST-218 第三部:抓衝擊後四季的 10-Q/10-K 與業績稿(8-K EX-99),落 docs/part3/(.gitignore 已擋)。

**工人抓的申報原文不入庫(D-134)**:全文只落 `docs/`,`research/2026-09-methodology/*/docs/`
已在 .gitignore。本檔不寫 `data/`、不寫其他票的目錄。

窗口 = 衝擊起日 → 衝擊起日 + 十五個月(足夠覆蓋四季 10-Q 加該年 10-K)。
每份 8-K 取其存檔目錄內最大的 .htm 附件(業績新聞稿通常就是最大那件)。
"""
from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.request

ROOT = "C:/projects/Karst"
HERE = f"{ROOT}/research/2026-09-methodology/2026-09-12-暴露差異模組v1"
DOCS = f"{HERE}/docs/part3"
UA = {"User-Agent": "Karst research kaho@example.com"}

# (事件, ticker, CIK, 衝擊起日) —— 十一家的來源見 `卡-E01/E06/E07/E08/E12/E13/E14.md`
TARGETS = [
    ("E01", "T", "0000732717", "2013-05-21"),
    ("E01", "SPG", "0001063761", "2013-05-21"),
    ("E01", "ED", "0001047862", "2013-05-21"),
    ("E06", "RMD", "0000943819", "2023-10-03"),
    ("E06", "KO", "0000021344", "2023-10-03"),
    ("E06", "MDLZ", "0001103982", "2023-10-03"),
    ("E07", "MU", "0000723125", "2025-01-24"),
    ("E08", "AAPL", "0000320193", "2025-04-02"),
    ("E12", "SWKS", "0000004127", "2019-05-17"),
    ("E13", "MSFT", "0000789019", "2022-01-03"),
    ("E14", "DUOL", "0001562088", "2023-05-01"),
]


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read())


def get_bytes(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def _rows(block):
    out = []
    it = block.get("items", [""] * len(block.get("form", [])))
    for i in range(len(block.get("form", []))):
        out.append(dict(form=block["form"][i], filingDate=block["filingDate"][i],
                        reportDate=block["reportDate"][i],
                        items=it[i] if i < len(it) else "",
                        accn=block["accessionNumber"][i], doc=block["primaryDocument"][i]))
    return out


def all_rows(cik):
    """本地 submissions 快取通常只夠近年;一律直接讀 EDGAR(含分片)。"""
    d = get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    rows = _rows(d.get("filings", {}).get("recent", {}))
    for sh in d.get("filings", {}).get("files", []):
        try:
            rows += _rows(get_json(f"https://data.sec.gov/submissions/{sh['name']}"))
        except Exception as e:  # noqa: BLE001
            print("  分片失敗", sh["name"], type(e).__name__)
        time.sleep(0.3)
    return rows


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


def save(cik, f, path, url=None):
    acc = f["accn"].replace("-", "")
    u = url or f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{f['doc']}"
    raw = get_bytes(u)
    with open(path, "w", encoding="utf-8") as g:
        g.write(strip_html(raw))
    return len(raw)


def biggest_exhibit(cik, accn_nodash):
    """8-K 的存檔目錄裡最大的 .htm/.html 附件(業績新聞稿)。"""
    u = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn_nodash}/index.json"
    try:
        d = get_json(u)
    except Exception:  # noqa: BLE001
        return None
    best, size = None, -1
    for it in d.get("directory", {}).get("item", []):
        n = it.get("name", "")
        if not re.search(r"(?i)\.(htm|html|txt)$", n):
            continue
        if re.search(r"(?i)(index|R\d+\.htm|\.xsd|\.xml)", n):
            continue
        s = int(it.get("size") or 0)
        if s > size:
            best, size = n, s
    return best


def main():
    os.makedirs(DOCS, exist_ok=True)
    index = []
    for ev, tk, cik, shock in TARGETS:
        end = str(int(shock[:4]) + 2) + "-01-31"  # 足覆蓋四季 10-Q 加該年 10-K
        rows = all_rows(cik)
        win = [x for x in rows if shock <= x["filingDate"] <= end]
        qk = [x for x in win if x["form"] in ("10-Q", "10-K", "20-F")]
        # 8-K 只要業績稿(items 含 2.02 Results of Operations),其餘 8-K 與本題無關
        ke = [x for x in win if x["form"] in ("8-K", "6-K")
              and ("2.02" in (x.get("items") or "")
                   or "earnings" in (x.get("items") or "").lower())]
        print(f"== {ev} {tk} 窗口 {shock}~{end}: 10-Q/K {len(qk)} 份, 8-K {len(ke)} 份")
        for tag, f in [("QK", x) for x in qk] + [("ER", x) for x in ke]:
            acc = f["accn"].replace("-", "")
            fn = f"{DOCS}/{ev}_{tk}_{tag}_{f['filingDate']}_{acc}.txt"
            if os.path.exists(fn):
                continue
            try:
                if tag == "ER":
                    ex = biggest_exhibit(cik, acc)
                    if not ex:
                        continue
                    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{ex}"
                    n = save(cik, f, fn, url=url)
                else:
                    n = save(cik, f, fn)
            except Exception as e:  # noqa: BLE001
                print("  FAIL", tag, f["form"], f["filingDate"], type(e).__name__, str(e)[:70])
                index.append(dict(event=ev, ticker=tk, tag=tag, form=f["form"],
                                  filingDate=f["filingDate"], reportDate=f["reportDate"],
                                  accn=f["accn"], status="抓取失敗:" + type(e).__name__))
                continue
            time.sleep(0.4)
            index.append(dict(event=ev, ticker=tk, tag=tag, form=f["form"],
                              filingDate=f["filingDate"], reportDate=f["reportDate"],
                              accn=f["accn"], file=os.path.basename(fn), bytes=n,
                              status="已落 docs/part3/"))
            print("  OK", tag, f["form"], f["filingDate"], f["reportDate"], n)
    with open(f"{HERE}/out/part3_docs_index.json", "w", encoding="utf-8") as g:
        json.dump(index, g, ensure_ascii=False, indent=1)
    print("總計", len(index), "份;失敗",
          sum(1 for x in index if not x["status"].startswith("已落")))


if __name__ == "__main__":
    main()
