# -*- coding: utf-8 -*-
"""Read-only inspection: packet financial series keys, row csv headers."""
import csv, json
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
EVENTS = ["E001", "E009", "E017", "E025", "E033", "E041", "E049", "E057", "E065", "E073"]

for eid in EVENTS:
    p = json.load(open(ROOT / "A2" / "packets" / (eid + ".json"), encoding="utf-8"))
    fs = p["4_財務數列"]
    idn = p["1_事件識別"]
    print(eid, p["ticker"], idn["fiscal_quarter"], "| series keys:", list(fs.keys()))
    if eid == "E001":
        print(json.dumps({k: v for k, v in fs.items() if k != "quarters"}, ensure_ascii=False))

print()
with open(ROOT / "試跑" / "ds" / "rows" / "E001.csv", encoding="utf-8") as f:
    r = list(csv.reader(f))
print("ds header n=", len(r[0]))
for i, c in enumerate(r[0]):
    print(i, c)
