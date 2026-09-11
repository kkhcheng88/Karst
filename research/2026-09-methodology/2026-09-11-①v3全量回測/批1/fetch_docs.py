# -*- coding: utf-8 -*-
"""KARST-212 批 1:把本批選定公司「衝擊起日之前」最後一份 10-K 與最後一份 10-Q 全文抓落本機。

本地 data/sec/10k_text 只覆蓋近年,多數公司 2013–2021 的申報不在其中;
submissions 快取只有 recent 1000 筆,舊申報要抓 filings.files 分片。
所以本腳本:抓分片 → 找 cutoff 之前最後 10-K/10-Q → 抓 primary document → 去 HTML 存文字。
硬界線:只抓申報日 < 衝擊起日的文件;界線之後一份都不抓。
"""
import io
import json
import os
import sys
import time
import urllib.request

from bs4 import BeautifulSoup

ROOT = "C:/projects/Karst"
BASE = f"{ROOT}/research/2026-09-methodology/2026-09-11-①v3全量回測/批1"
SUB = ROOT + "/data/sec/submissions/CIK{cik}.json"
SHARD = BASE + "/edgar_cache/submissions/{name}"
DOCS = BASE + "/docs"
UA = {"User-Agent": "Karst research (contact: kaho@example.com)"}

PICKS = [
    ("E01", "T", "0000732717", "2013-05-21"),
    ("E01", "SPG", "0001063761", "2013-05-21"),
    ("E01", "NLY", "0001043219", "2013-05-21"),
    ("E01", "ED", "0001047862", "2013-05-21"),
    ("E02", "BIIB", "0000875045", "2015-09-18"),
    ("E02", "REGN", "0000872589", "2015-09-18"),
    ("E02", "GILD", "0000882095", "2015-09-18"),
    ("E02", "JNJ", "0000200406", "2015-09-18"),
    ("E03", "UNFI", "0001020859", "2017-06-15"),
    ("E03", "KR", "0000056873", "2017-06-15"),
    ("E03", "SFM", "0001575515", "2017-06-15"),
    ("E03", "GIS", "0000040704", "2017-06-15"),
    ("E04", "ZM", "0001585521", "2021-02-12"),
    ("E04", "PTON", "0001639825", "2021-02-12"),
    ("E04", "TDOC", "0001477449", "2021-02-12"),
    ("E04", "FSLY", "0001517413", "2021-02-12"),
    ("E09", "OXY", "0000797468", "2014-11-26"),
    ("E09", "RIG", "0001451505", "2014-11-26"),
    ("E09", "HAL", "0000045012", "2014-11-26"),
    ("E09", "CVX", "0000093410", "2014-11-26"),
]


def get(url, kind="json"):
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            return json.loads(raw) if kind == "json" else raw
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 + attempt * 2)


def all_filings(cik):
    """recent + 所有分片,合成一份 (form, filingDate, reportDate, accession, primaryDocument)。"""
    d = json.load(open(SUB.format(cik=cik), encoding="utf-8"))
    out = []
    rec = d["filings"]["recent"]
    for i in range(len(rec["form"])):
        out.append((rec["form"][i], rec["filingDate"][i], rec["reportDate"][i],
                    rec["accessionNumber"][i], rec["primaryDocument"][i]))
    os.makedirs(BASE + "/edgar_cache/submissions", exist_ok=True)
    for f in d["filings"].get("files", []):
        p = SHARD.format(name=f["name"])
        if not os.path.exists(p):
            j = get(f"https://data.sec.gov/submissions/{f['name']}")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(j, fh)
            time.sleep(0.3)
        j = json.load(open(p, encoding="utf-8"))
        for i in range(len(j["form"])):
            out.append((j["form"][i], j["filingDate"][i], j["reportDate"][i],
                        j["accessionNumber"][i], j["primaryDocument"][i]))
    return out


def doc_url(cik, acc, primary):
    return (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{acc.replace('-', '')}/{primary}")


def to_text(raw):
    soup = BeautifulSoup(raw.decode("utf-8", "ignore"), "lxml")
    for t in soup(["script", "style"]):
        t.decompose()
    txt = soup.get_text("\n")
    lines = [ln.strip() for ln in txt.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def fetch_one(eid, tk, cik, cutoff, form, rec, wanted):
    filed, period, acc, primary = rec
    out = f"{DOCS}/{tk}_{form}_{filed}.txt"
    if os.path.exists(out) and os.path.getsize(out) > 5000:
        return "cached"
    url = doc_url(cik, acc, primary)
    raw = get(url, kind="raw")
    if len(raw) < 20000:  # primary 可能是目錄頁,改抓 index.json 內最大的 htm
        idx = get(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                  f"{acc.replace('-', '')}/index.json")
        cands = [x for x in idx["directory"]["item"]
                 if x["name"].lower().endswith((".htm", ".html"))]
        cands.sort(key=lambda x: -int(x["size"]))
        if cands:
            raw = get(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                      f"{acc.replace('-', '')}/{cands[0]['name']}", kind="raw")
    txt = to_text(raw)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# {tk} {form} filed {filed} period {period} accession {acc}\n")
        f.write(f"# source {url}\n\n")
        f.write(txt)
    return f"{len(txt)} chars"


def main():
    os.makedirs(DOCS, exist_ok=True)
    for eid, tk, cik, cutoff in PICKS:
        try:
            rows = all_filings(cik)
        except Exception as e:
            print(f"{eid} {tk} 分片抓取失敗: {e}")
            continue
        for form in ("10-K", "10-Q"):
            sel = [r for r in rows if r[0] == form and r[1] < cutoff]
            sel.sort(key=lambda x: x[1], reverse=True)
            if not sel:
                print(f"{eid} {tk} {form} cutoff 前查無")
                continue
            rec = (sel[0][1], sel[0][2], sel[0][3], sel[0][4])
            try:
                st = fetch_one(eid, tk, cik, cutoff, form, rec, None)
            except Exception as e:
                st = f"失敗 {e}"
            print(f"{eid} {tk} {form} filed {rec[0]} period {rec[1]} -> {st}")
            time.sleep(0.3)


if __name__ == "__main__":
    main()
