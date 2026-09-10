# -*- coding: utf-8 -*-
"""KARST-209 步驟四(補漏):對照不到收費語的那幾家,放闊網睇原文。

`extract_fee_model.py` 用准許清單掃「per-user / usage-based」一類語式,掃不到的
不代表公司沒有講,只代表它用別的講法(例:「we charge a fee for each return processed」)。
本檔對指定代號放闊網:在收入確認附註窗口內找**同時有收費字與顧客字**的句子,
順序印出前幾句,由人讀。**不自動分桶,不猜**——掃不到就在 `收費模式.md` 標查不到。

用法:PYTHONUTF8=1 python probe_fee.py INTU ANET ...
"""
import glob
import gzip
import json
import re
import sys

CACHE = "C:/projects/Karst/data/sec/10k_text"
OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①SaaS籃子重定義"
NOTE_HEAD = re.compile(r"revenue (?:recognition|from contracts with customers)", re.I)
MONEY = re.compile(r"pric\w+|fee|fees|charg\w+|subscription\w*|licen[cs]\w*|royalt\w+|"
                   r"per[\s\-](?:user|seat|return|customer|unit|device|employee)", re.I)
PARTY = re.compile(r"\bcustomers?\b|\busers?\b|\bclients?\b|\bsubscribers?\b", re.I)


def plain(path):
    with gzip.open(path, "rb") as f:
        h = f.read().decode("utf-8", errors="replace")
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&#8217;", "'"), ("&#39;", "'"),
                 ("&#8220;", '"'), ("&#8221;", '"'), ("&#160;", " "),
                 ("&#8226;", " "), ("&#8211;", "-")):
        h = h.replace(a, b)
    return re.sub(r"\s+", " ", re.sub(r"-\s+", "-", h))


def sentences(txt, win_only=True):
    m = list(NOTE_HEAD.finditer(txt))
    if win_only and m:
        st = m[-1 if len(m) > 4 else 0].start()
        txt = txt[st:st + 60000]
    out, seen = [], set()
    for s in re.split(r"(?<=\.)\s+", txt):
        s = s.strip()
        if not (70 < len(s) < 420) or not MONEY.search(s) or not PARTY.search(s):
            continue
        k = s[:60]
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
        if len(out) >= 4:
            break
    return out


def main():
    import csv as _csv
    man = [json.loads(l) for l in
           open(f"{CACHE}/manifest.jsonl", encoding="utf-8") if l.strip()]
    latest = {}
    for m in man:
        t = m["ticker"]
        if t not in latest or m["filingDate"] > latest[t]["filingDate"]:
            latest[t] = m
    tickers = sys.argv[1:]
    if not tickers:                      # 無參數 = 全籃,寫檔不印(免炸 stdout)
        tickers = [r["ticker"] for r in
                   _csv.DictReader(open(f"{OUT}/constituents.csv", encoding="utf-8-sig"))]
    rows, n_none = [], 0
    for t in tickers:
        m = latest.get(t)
        p = glob.glob(f"{CACHE}/{t}_{m['accession'].replace('-','')}.txt.gz") if m else []
        if not p:
            n_none += 1
            continue
        ss = sentences(plain(p[0])) or sentences(plain(p[0]), win_only=False)
        if not ss:
            n_none += 1
        for i, s in enumerate(ss[:4]):
            rows.append({"代號": t, "序": i, "句": s[:400]})
    if not sys.argv[1:]:
        with open(f"{OUT}/fee_probe.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=["代號", "序", "句"])
            w.writeheader()
            w.writerows(rows)
        print(f"闊網掃描寫入 fee_probe.csv:{len(tickers)} 家、{len(rows)} 句、空白 {n_none} 家")
        return
    for t in tickers:
        print(f"\n=== {t} ===")
        for r in rows:
            if r["代號"] == t:
                print(f"  [{r['序']}] " + r["句"][:240])


if __name__ == "__main__":
    main()
