# -*- coding: utf-8 -*-
"""KARST-235 診斷七:印某包稿內含指定字串的句子(每句一行,最多 n 句)。只讀。"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
eid, pat = sys.argv[1], sys.argv[2]
nmax = int(sys.argv[3]) if len(sys.argv) > 3 else 12
p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
text = (p["2_觸發資料"] or {}).get("ex991_full_text") or ""
rx = re.compile(pat, re.I)
hits = 0
for sent in re.split(r"(?<=[.;])\s+|\n", text):
    if rx.search(sent) and sent.strip():
        print(">", " ".join(sent.split())[:280])
        hits += 1
        if hits >= nmax:
            break
print("[hits shown]", hits, "of len", len(text))
