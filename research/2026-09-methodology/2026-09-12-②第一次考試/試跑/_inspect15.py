# -*- coding: utf-8 -*-
"""Read-only: compact guidance-direction contexts for all 20 Q+1/Q+2 releases."""
import csv, gzip, re
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
CACHE = ROOT / "A" / "edgar_cache"
NOUN = re.compile(r"(?i)\b(guidance|outlook)\b")
DIRW = re.compile(r"(?i)(rais|lower|reduc|cut|withdraw|below|above|reaffirm|reiterat|revis|"
                  r"narrow|increas|decreas|update|confirm|maintain|anticipat|expect)")

rows = list(csv.DictReader(open(ROOT / "試跑" / "結果對照.csv", encoding="utf-8")))
for r in rows:
    for m in re.finditer(r"(Q\+\d) (有下修|無|查不到)\(([\d-]+);(\w+)\)", r["guide_detail"]):
        qk, acc = m.group(1), m.group(3)
        p = CACHE / (acc.replace("-", "") + "__EX991.txt.gz")
        if not p.exists():
            print("==", r["event_id"], qk, acc, "NO CACHE")
            continue
        txt = gzip.open(p, "rt", encoding="utf-8").read()
        print("==", r["event_id"], r["ticker"], qk, acc)
        seen = set()
        for n in NOUN.finditer(txt):
            seg = txt[max(0, n.start() - 160): n.end() + 160]
            if not DIRW.search(seg):
                continue
            s = re.sub(r"\s+", " ", seg).strip()
            key = s[:60]
            if key in seen:
                continue
            seen.add(key)
            print("    ..", s[:250])
