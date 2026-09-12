# -*- coding: utf-8 -*-
"""Read-only: headline of each Q+1/Q+2 earnings release."""
import csv, gzip, re
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
CACHE = ROOT / "A" / "edgar_cache"
rows = list(csv.DictReader(open(ROOT / "試跑" / "結果對照.csv", encoding="utf-8")))
for r in rows:
    for m in re.finditer(r"(Q\+\d) (有下修|無|查不到)\(([\d-]+);", r["guide_detail"]):
        qk, acc = m.group(1), m.group(3)
        p = CACHE / (acc.replace("-", "") + "__EX991.txt.gz")
        if not p.exists():
            print("==", r["event_id"], qk, "NO CACHE"); continue
        t = re.sub(r"\s+", " ", gzip.open(p, "rt", encoding="utf-8").read()).strip()
        print("==", r["event_id"], r["ticker"], qk, "|", t[:330])
