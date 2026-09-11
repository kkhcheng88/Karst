# -*- coding: utf-8 -*-
"""KARST-213 批 2:補抓申報主文件。

有些申報的 primaryDocument 指向 XBRL 財務報表(R 檔),沒有 MD&A。
本腳本改用申報目錄 index.json,挑最大的 .htm(排除 R 檔與 XBRL viewer)重抓。

用法:python 補文件.py <出檔名(不含.txt)> <CIK> <accession>
"""
import html
import os
import re
import sys

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
    out, cik, acc = sys.argv[1], str(int(sys.argv[2])), sys.argv[3].replace("-", "")
    idx = requests.get("https://www.sec.gov/Archives/edgar/data/%s/%s/index.json"
                       % (cik, acc), headers=UA, timeout=60).json()
    cands = [it for it in idx["directory"]["item"]
             if it["name"].lower().endswith(".htm")
             and not it["name"].lower().startswith(("r", "ex"))]
    cands.sort(key=lambda x: int(x["size"]), reverse=True)
    if not cands:
        print("NO CANDIDATE", cik, acc)
        return
    top = cands[0]
    url = ("https://www.sec.gov/Archives/edgar/data/%s/%s/%s" % (cik, acc, top["name"]))
    r = requests.get(url, headers=UA, timeout=180)
    txt = strip_html(r.text)
    path = "%s/%s.txt" % (DOCS, out)
    open(path, "w", encoding="utf-8").write(txt)
    print(out, top["name"], top["size"], "->", len(txt), "chars")


if __name__ == "__main__":
    main()
