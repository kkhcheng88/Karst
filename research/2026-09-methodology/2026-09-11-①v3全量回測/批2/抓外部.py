# -*- coding: utf-8 -*-
"""KARST-213 批 2:抓事件以外的外部公司衝擊前文件(例如 GLP-1 藥廠),
用來為步〇 的必要條件取得衝擊前出處。只落 批2/docs/,不寫 data/sec/。

用法:python 抓外部.py <標籤> <CIK> <cutoff YYYY-MM-DD> [表單=10-Q]
"""
import html
import json
import os
import re
import sys
import time

import requests

B2 = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①v3全量回測/批2"
DOCS = B2 + "/docs"
UA = {"User-Agent": "Karst Research (kaho@example.com)"}


def strip_html(raw):
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?is)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?is)</(p|div|tr|table|h[1-6])>", "\n", raw)
    raw = re.sub(r"(?is)<[^>]+>", " ", raw)
    raw = html.unescape(raw).replace("\u00a0", " ")
    raw = re.sub(r"[ \t\x0b\f\r]+", " ", raw)
    return re.sub(r"\n\s*\n+", "\n", raw).strip()


def main():
    tag, cik, cutoff = sys.argv[1], sys.argv[2], sys.argv[3]
    forms = sys.argv[4].split(",") if len(sys.argv) > 4 else ["10-Q", "10-K", "20-F"]
    cik10 = str(int(cik)).zfill(10)
    d = requests.get("https://data.sec.gov/submissions/CIK%s.json" % cik10,
                     headers=UA, timeout=60).json()
    fin = d.get("filings", {})
    blks = [fin.get("recent", {})]
    for f in fin.get("files", []):
        blks.append(requests.get("https://data.sec.gov/submissions/" + f["name"],
                                 headers=UA, timeout=60).json())
    rows = []
    for blk in blks:
        n = len(blk.get("form", []))
        for i in range(n):
            rows.append({"form": blk["form"][i], "filingDate": blk["filingDate"][i],
                         "accessionNumber": blk["accessionNumber"][i],
                         "primaryDocument": blk["primaryDocument"][i]})
    os.makedirs(DOCS, exist_ok=True)
    for form in forms:
        hits = [x for x in rows if x["form"] == form and x["filingDate"] < cutoff]
        hits.sort(key=lambda x: x["filingDate"], reverse=True)
        if not hits:
            print(tag, form, "NONE before", cutoff)
            continue
        x = hits[0]
        path = "%s/%s_%s_%s.txt" % (DOCS, tag, form.replace("/", ""),
                                    x["accessionNumber"].replace("-", ""))
        if not (os.path.exists(path) and os.path.getsize(path) > 2000):
            url = ("https://www.sec.gov/Archives/edgar/data/%s/%s/%s"
                   % (cik10.lstrip("0"), x["accessionNumber"].replace("-", ""),
                      x["primaryDocument"]))
            r = requests.get(url, headers=UA, timeout=120)
            if r.status_code != 200:
                print(tag, form, x["filingDate"], "HTTP", r.status_code)
                continue
            open(path, "w", encoding="utf-8").write(strip_html(r.text))
            time.sleep(0.3)
        print(tag, form, x["filingDate"], x["accessionNumber"], path, os.path.getsize(path))


if __name__ == "__main__":
    main()
