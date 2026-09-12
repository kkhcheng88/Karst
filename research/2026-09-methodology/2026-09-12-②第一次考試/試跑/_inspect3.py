# -*- coding: utf-8 -*-
"""Read-only: check population coverage + edgar_cache naming for post-T1 events."""
import csv, gzip, json
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
CACHE = ROOT / "A" / "edgar_cache"
EVENTS = ["E001", "E009", "E017", "E025", "E033", "E041", "E049", "E057", "E065", "E073"]

rows = list(csv.DictReader(open(ROOT / "A2" / "population.csv", encoding="utf-8-sig")))
print("population rows:", len(rows))
by_cik = {}
for r in rows:
    by_cik.setdefault(r["cik"], []).append(r)

meta = {}
for eid in EVENTS:
    p = json.load(open(ROOT / "A2" / "packets" / (eid + ".json"), encoding="utf-8"))
    meta[eid] = p

for eid in EVENTS:
    p = meta[eid]
    cik = p["cik"]
    t1 = p["1_事件識別"]["signal_date_反應日"]
    evs = sorted([r for r in by_cik.get(cik, []) if r["reaction_date"] > t1],
                 key=lambda r: r["reaction_date"])
    print("---", eid, p["ticker"], "T1", t1, "| future events:", len(evs))
    for r in evs[:3]:
        acc = r["accessionNumber"]
        f = CACHE / (acc.replace("-", "") + "__EX991.txt.gz")
        print("    ", r["reaction_date"], r["fiscal_quarter"], acc, "has_text=", r["has_text"],
              "cache=", f.exists())
