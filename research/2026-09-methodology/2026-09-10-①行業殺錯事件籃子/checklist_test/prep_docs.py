# -*- coding: utf-8 -*-
"""KARST-204:把一宗事件籃子每家的「衝擊前最後一份 10-K」落成純文字,供判斷隊 Grep。

三條取件路徑,按次序:
  1. data/sec/10k_text/<TICKER>_<accession>.txt.gz 本地快取;
  2. 本地 submissions 快取解析得到 accession → 打 EDGAR 取正文;
  3. 本地 submissions 的 recent 一千筆已經比衝擊日新(舊事件常見)→
     打 EDGAR 取分頁 submissions(CIK##########-submissions-00N.json)再取正文。

輸出:checklist_test/docs/<EVENT>/<TICKER>__<form>_<filingDate>_<accession>.txt
另出 docs/<EVENT>/_index.md 記每家拿到什麼、拿不到什麼(拿不到要逐家寫明原因)。

用法:PYTHONUTF8=1 python prep_docs.py E03 E12 E13
"""
import gzip
import html
import io
import json
import os
import re
import sys
import time
import urllib.request

ROOT = "C:/projects/Karst"
BASE = f"{ROOT}/research/2026-09-methodology/2026-09-10-①行業殺錯事件籃子"
PK = f"{BASE}/checklist_test/packets"
DOCS = f"{BASE}/checklist_test/docs"
UA = "Karst Research karsoncheng@casy.hk"
LAST = [0.0]


def get(url, timeout=60):
    wait = 0.25 - (time.time() - LAST[0])
    if wait > 0:
        time.sleep(wait)
    LAST[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
    return data


def to_text(raw):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    raw = re.sub(r"(?is)<(script|style|ix:header).*?</\1>", " ", raw)
    raw = re.sub(r"(?is)<br\s*/?>|</(p|div|tr|td|th|li|h\d)>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = raw.replace("\xa0", " ")
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n\s*\n\s*\n+", "\n\n", raw)
    return raw.strip()


def paged_prefilings(cik, cutoff):
    """本地 recent 不夠舊時,改用 KARST-177 已快取的歷史分頁
    (data/sec/submissions/pages/);分頁本地缺才打 EDGAR。"""
    main = f"{ROOT}/data/sec/submissions/CIK{cik}.json"
    try:
        if os.path.exists(main):
            with open(main, encoding="utf-8") as f:
                d = json.load(f)
        else:
            d = json.loads(get(f"https://data.sec.gov/submissions/CIK{cik}.json"))
    except Exception as e:
        return None, f"submissions 取不到:{e}"
    out = []
    r = d.get("filings", {}).get("recent", {})
    pages = [r]
    for meta in d.get("filings", {}).get("files", []):
        if meta.get("filingFrom", "9999") <= cutoff:
            lp = f"{ROOT}/data/sec/submissions/pages/{meta['name']}"
            try:
                if os.path.exists(lp):
                    with open(lp, encoding="utf-8") as f:
                        pages.append(json.load(f))
                else:
                    pages.append(json.loads(get(
                        f"https://data.sec.gov/submissions/{meta['name']}")))
            except Exception:
                pass
    for p in pages:
        forms = p.get("form", [])
        for i in range(len(forms)):
            if forms[i] in ("10-K", "20-F", "40-F") and p["filingDate"][i] < cutoff:
                out.append({"form": forms[i], "filingDate": p["filingDate"][i],
                            "reportDate": p["reportDate"][i],
                            "accession": p["accessionNumber"][i],
                            "primaryDocument": p["primaryDocument"][i]})
    if not out:
        return None, "EDGAR 分頁之中亦無衝擊日之前的 10-K"
    out.sort(key=lambda x: x["filingDate"], reverse=True)
    b = out[0]
    acc = b["accession"].replace("-", "")
    b["url"] = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/"
                f"{b['primaryDocument']}")
    return b, ""


def run(eid):
    with open(f"{PK}/{eid}.json", encoding="utf-8") as f:
        pack = json.load(f)
    cutoff = pack["shock_start"]
    outdir = f"{DOCS}/{eid}"
    os.makedirs(outdir, exist_ok=True)
    lines = [f"# {eid} {pack['name']} — 衝擊前 10-K 取件索引",
             f"\n硬界線:申報日 < {cutoff}。取不到的逐家寫明原因。\n"]
    for c in pack["companies"]:
        tk, cik = c["ticker"], c["entity_id"]
        pf = c.get("prefilings") or {}
        blk = pf.get("10-K")
        why = ""
        if not blk:
            blk, why = paged_prefilings(cik, cutoff)
        if not blk:
            lines.append(f"- **{tk}** {c['name']} — 取不到:{why}")
            continue
        acc = blk["accession"]
        name = f"{tk}__{blk.get('form','10-K')}_{blk['filingDate']}_{acc.replace('-', '')}.txt"
        path = f"{outdir}/{name}"
        if os.path.exists(path) and os.path.getsize(path) > 5000:
            lines.append(f"- **{tk}** {c['name']} — 10-K 申報日 {blk['filingDate']} "
                         f"期末 {blk['reportDate']} accession {acc} → `docs/{eid}/{name}`")
            continue
        text = None
        lp = c.get("local_10k_gz")
        src = ""
        if lp and os.path.exists(lp):
            with gzip.open(lp, "rt", encoding="utf-8", errors="ignore") as f:
                text = to_text(f.read())
            src = "本地快取"
        if not text or len(text) < 5000:
            try:
                text = to_text(get(blk["url"]))
                src = "EDGAR"
            except Exception as e:
                lines.append(f"- **{tk}** {c['name']} — 取不到:EDGAR 正文 {e} "
                             f"({blk['url']})")
                continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {tk} {blk.get('form','10-K')} 申報日 {blk['filingDate']} 期末 {blk['reportDate']}\n"
                    f"# accession {acc}\n# {blk['url']}\n# 取件來源:{src}\n\n")
            f.write(text)
        lines.append(f"- **{tk}** {c['name']} — 10-K 申報日 {blk['filingDate']} "
                     f"期末 {blk['reportDate']} accession {acc}({src},"
                     f"{len(text) // 1000}k 字)→ `docs/{eid}/{name}`")
        print(tk, src, len(text))
    with open(f"{outdir}/_index.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    for e in sys.argv[1:]:
        run(e)
