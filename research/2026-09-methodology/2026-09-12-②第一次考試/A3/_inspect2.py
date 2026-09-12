# -*- coding: utf-8 -*-
"""scratch: list a company's filings before a cutoff (not a deliverable)"""
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\projects\Karst")
SUB = ROOT / "data" / "sec" / "submissions"

cik = sys.argv[1]
cut = sys.argv[2] if len(sys.argv) > 2 else "2099-01-01"
p = SUB / ("CIK%s.json" % cik)
d = json.loads(p.read_text(encoding="utf-8"))
r = d["filings"]["recent"]
n = len(r["form"])
print("total recent rows:", n)
rows = []
for i in range(n):
    rows.append((r["filingDate"][i], r["form"][i], r["accessionNumber"][i],
                 r["reportDate"][i], (r.get("items", [""] * n)[i] or "")))
rows.sort(reverse=True)
print("oldest:", rows[-1][0], "newest:", rows[0][0])
for x in rows:
    if x[0] <= cut and x[1] in ("10-Q", "10-K", "20-F", "6-K", "8-K"):
        print("  ", x[0], x[1], x[2], x[3], x[4][:60])
