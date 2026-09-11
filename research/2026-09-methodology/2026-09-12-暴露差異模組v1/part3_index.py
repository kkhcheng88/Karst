# -*- coding: utf-8 -*-
"""KARST-218 第三部:按 `docs/part3/` 檔案系統重建索引(抓取時被略過的既有檔也計入)。"""
from __future__ import annotations

import collections
import json
import os

HERE = "C:/projects/Karst/research/2026-09-methodology/2026-09-12-暴露差異模組v1"
DOCS = f"{HERE}/docs/part3"

rows = []
for fn in sorted(os.listdir(DOCS)):
    if not fn.endswith(".txt"):
        continue
    p = fn[:-4].split("_")
    rows.append(dict(event=p[0], ticker=p[1], tag=p[2], filingDate=p[3], accn=p[4],
                     file=fn, status="已落 docs/part3/"))
with open(f"{HERE}/out/part3_docs_index.json", "w", encoding="utf-8") as g:
    json.dump(rows, g, ensure_ascii=False, indent=1)
c = collections.Counter((r["event"] + "_" + r["ticker"], r["tag"]) for r in rows)
print("按檔案系統索引", len(rows), "份")
for k in sorted(c):
    print("  ", k[0], k[1], c[k])
