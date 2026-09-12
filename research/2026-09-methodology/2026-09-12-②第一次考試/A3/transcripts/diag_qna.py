# -*- coding: utf-8 -*-
"""KARST-231 附件:檢查已存逐字稿的 Q&A 判法,原地更新 has_qna。

原本 has_qna 用「有 Analysts/Operator 講者標籤」判,結果 114/114 全中,無分辨力。
本腳本改為兩個獨立欄位:
  has_qna_section —— 文本內有明確的問答段標記(Question-and-Answer / Q&A)
  n_analyst_segs  —— 講者標為 Analysts 的段數(有 = 逐字稿含分析員提問部分)
has_qna 保留為「兩者取或」,但同時寫出上面兩欄,讀者自行取用。
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MK = re.compile(
    r"question[\s\-–]*and[\s\-–]*answer|question[\s\-–]*&\s*answer|\bq\s*&\s*a\b",
    re.IGNORECASE,
)

fs = sorted(glob.glob(os.path.join(HERE, "E*.json")) + glob.glob(os.path.join(HERE, "B*.json")))
stats = {"marker": 0, "analyst": 0, "both": 0, "neither": 0, "n": 0}
refined = {}
for f in fs:
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    segs = d["segments"]
    body = " ".join(s["content"] for s in segs)
    marker = bool(MK.search(body))
    n_an = sum(1 for s in segs if s["speaker"].strip().lower() in ("analysts", "analyst"))
    d["has_qna_section"] = marker
    d["n_analyst_segs"] = n_an
    d["has_qna"] = marker or n_an > 0
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False)
    stats["n"] += 1
    stats["marker"] += marker
    stats["analyst"] += n_an > 0
    stats["both"] += marker and n_an > 0
    stats["neither"] += (not marker) and n_an == 0
    refined[d["event_id"]] = (marker, n_an)

print(stats)

# --- 把細分欄位寫入 coverage.csv
import csv

cp = os.path.join(HERE, "coverage.csv")
with open(cp, encoding="utf-8", newline="") as fh:
    rows = list(csv.DictReader(fh))
FIELDS = list(rows[0].keys())
for c in ("has_qna_section", "n_analyst_segs"):
    if c not in FIELDS:
        FIELDS.append(c)
for r in rows:
    m, n = refined.get(r["event_id"], ("", ""))
    r["has_qna_section"] = m
    r["n_analyst_segs"] = n
    if r["event_id"] in refined:
        r["has_qna"] = bool(m) or n > 0
with open(cp, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
print("coverage.csv patched:", len(rows))
