# -*- coding: utf-8 -*-
"""KARST-213 批 2:為挑選的公司取衝擊前文件(本地快取缺就打到 EDGAR)。

挑家(只用衝擊前資訊,按暴露形態不同;E06/E07 沿用 KARST-210 同一批代號以便 215 對比):
  E05 地區銀行:WAL / MCB / ZION / SCHW
  E06 減肥藥:  MDLZ / KO / RMD / DXCM
  E07 DeepSeek: NVDA / MU / VRT / ANET
  E10 特朗普:  FSLR / RUN / THC / CNC
  E11 劍橋分析:META / SNAP(籃子只有兩家,全做)

只落檔到 批2/docs/,不寫 data/sec/(那是共用快取,本票不動)。
每份文件截到衝擊起日之前最後一份 10-K;另外抓衝擊前最後兩份 10-Q 供步四核最近一季。
"""
import html
import json
import os
import re
import time

import requests

ROOT = "C:/projects/Karst"
B2 = ROOT + "/research/2026-09-methodology/2026-09-11-①v3全量回測/批2"
DOCS = B2 + "/docs"
UA = {"User-Agent": "Karst Research (kaho@example.com)"}
SEL = {"E05": ["WAL", "MCB", "ZION", "SCHW"],
       "E06": ["MDLZ", "KO", "RMD", "DXCM"],
       "E07": ["NVDA", "MU", "VRT", "ANET"],
       "E10": ["FSLR", "RUN", "THC", "CNC"],
       "E11": ["META", "SNAP"]}


def all_filings(cik):
    """全部申報(連 EDGAR 分頁檔)。"""
    url = "https://data.sec.gov/submissions/CIK%s.json" % cik
    d = requests.get(url, headers=UA, timeout=60).json()
    fin = d.get("filings", {})
    rows = []
    for blk in [fin.get("recent", {})] + [
            requests.get("https://data.sec.gov/submissions/" + f["name"],
                         headers=UA, timeout=60).json() for f in fin.get("files", [])]:
        n = len(blk.get("form", []))
        for i in range(n):
            rows.append({"form": blk["form"][i], "filingDate": blk["filingDate"][i],
                         "reportDate": blk.get("reportDate", [""] * n)[i],
                         "accessionNumber": blk["accessionNumber"][i],
                         "primaryDocument": blk["primaryDocument"][i]})
    return rows


def strip_html(raw):
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?is)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?is)</(p|div|tr|table|h[1-6])>", "\n", raw)
    raw = re.sub(r"(?is)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = raw.replace("\u00a0", " ")
    raw = re.sub(r"[ \t\x0b\f\r]+", " ", raw)
    raw = re.sub(r"\n\s*\n+", "\n", raw)
    return raw.strip()


def fetch(cik, acc, doc, ticker, tag):
    path = "%s/%s_%s_%s.txt" % (DOCS, ticker, tag, acc.replace("-", ""))
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return path, "cached"
    url = ("https://www.sec.gov/Archives/edgar/data/%d/%s/%s"
           % (int(cik), acc.replace("-", ""), doc))
    r = requests.get(url, headers=UA, timeout=120)
    if r.status_code != 200:
        return None, "HTTP %d" % r.status_code
    txt = strip_html(r.text)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    time.sleep(0.3)
    return path, "fetched %d chars" % len(txt)


def main():
    os.makedirs(DOCS, exist_ok=True)
    for eid, tickers in SEL.items():
        pack = json.load(open("%s/packets/%s.json" % (B2, eid), encoding="utf-8"))
        cutoff = pack["shock_start"]
        by_t = {c["ticker"]: c for c in pack["companies"]}
        for t in tickers:
            c = by_t[t]
            cik = c["entity_id"]
            # 先看本地 submissions 快取有沒有合用的 10-K / 10-Q
            rows = []
            sub = ROOT + "/data/sec/submissions/CIK%s.json" % cik
            if os.path.exists(sub):
                r = json.load(open(sub, encoding="utf-8"))["filings"]["recent"]
                rows = [{"form": r["form"][i], "filingDate": r["filingDate"][i],
                         "accessionNumber": r["accessionNumber"][i],
                         "primaryDocument": r["primaryDocument"][i]}
                        for i in range(len(r["form"]))]
            k10 = [x for x in rows if x["form"] == "10-K" and x["filingDate"] < cutoff]
            qs = [x for x in rows if x["form"] == "10-Q" and x["filingDate"] < cutoff]
            if not k10 or len(qs) < 1:
                rows = all_filings(cik)
                k10 = [x for x in rows if x["form"] == "10-K" and x["filingDate"] < cutoff]
                qs = [x for x in rows if x["form"] == "10-Q" and x["filingDate"] < cutoff]
            k10.sort(key=lambda x: x["filingDate"], reverse=True)
            qs.sort(key=lambda x: x["filingDate"], reverse=True)
            out = {"event": eid, "ticker": t, "cik": cik, "cutoff": cutoff, "docs": []}
            if k10:
                p, st = fetch(cik, k10[0]["accessionNumber"], k10[0]["primaryDocument"],
                              t, "10K_%s" % k10[0]["filingDate"])
                out["docs"].append({"form": "10-K", "filingDate": k10[0]["filingDate"],
                                    "accession": k10[0]["accessionNumber"],
                                    "path": p, "status": st})
                out["last_10k"] = k10[0]["filingDate"]
            else:
                out["docs"].append({"form": "10-K", "status": "NONE before cutoff"})
            for q in qs[:2]:
                p, st = fetch(cik, q["accessionNumber"], q["primaryDocument"], t,
                              "10Q_%s" % q["filingDate"])
                out["docs"].append({"form": "10-Q", "filingDate": q["filingDate"],
                                    "accession": q["accessionNumber"],
                                    "path": p, "status": st})
            print(eid, t, "|".join("%s %s %s" % (d["form"], d.get("filingDate"),
                                                 d["status"]) for d in out["docs"]))
            with open("%s/%s_%s_docs.json" % (DOCS, eid, t), "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
