# -*- coding: utf-8 -*-
"""KARST-231 附件:檢查本票新增/改動的檔有沒有公司名或代號外洩(唯讀)。

逐字稿本文(A3/transcripts/E*.json|B*.json 的 segments)必然含公司名,那是交付資料本身,
不在本檢查範圍;本檢查針對控制檔:coverage.csv、_fetch_log.jsonl、覆蓋核查 .md、
inject_transcripts.py 及本目錄的腳本。
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
A3 = os.path.dirname(HERE)

tickers = set()
names = set()
for fn in os.listdir(os.path.join(A3, "packets")):
    if not fn.endswith(".json"):
        continue
    with open(os.path.join(A3, "packets", fn), encoding="utf-8") as fh:
        p = json.load(fh)
    if p.get("ticker"):
        tickers.add(p["ticker"].upper())
    if p.get("name"):
        names.add(p["name"].upper())

targets = [os.path.join(HERE, "coverage.csv"),
           os.path.join(HERE, "_fetch_log.jsonl"),
           os.path.join(HERE, "news_coverage.json"),
           os.path.join(HERE, "summarize.py"),
           os.path.join(HERE, "fetch_transcripts.py"),
           os.path.join(HERE, "news_coverage.py"),
           os.path.join(HERE, "diag_qna.py"),
           os.path.join(HERE, "inject_preview.py"),
           os.path.join(HERE, "leak_check.py"),
           os.path.join(A3, "inject_transcripts.py")]
targets += glob.glob(os.path.join(HERE, "*.md"))
targets = [t for t in targets if os.path.exists(t)]

print("tickers checked:", len(tickers), "| names checked:", len(names))
bad = 0
for t in targets:
    txt = open(t, encoding="utf-8").read()
    up = txt.upper()
    hits = sorted(x for x in tickers if re.search(r"\b" + re.escape(x) + r"\b", up))
    hitsn = sorted(x for x in names if x in up)
    print(("  OK   " if not (hits or hitsn) else "  HIT  "),
          os.path.relpath(t, A3), "ticker:", hits[:5], "name:", hitsn[:3])
    bad += bool(hits or hitsn)
print("files with leak:", bad)
