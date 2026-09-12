# -*- coding: utf-8 -*-
"""scratch inspector (not a deliverable)"""
import gzip
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
DOCS = HERE.parent / "A" / "edgar_cache"

what = sys.argv[1] if len(sys.argv) > 1 else "pkt"
eid = sys.argv[2] if len(sys.argv) > 2 else "E001"

if what == "pkt":
    d = json.loads((HERE / "packets" / ("%s.json" % eid)).read_text(encoding="utf-8"))
    print("3_截止前文件:", json.dumps(d["3_截止前文件"], ensure_ascii=False, indent=1)[:1500])
    print("5_同業:", json.dumps(d["5_同業與行業"]["peer_annual_reports_2_largest"],
                                ensure_ascii=False, indent=1)[:900])
elif what == "pop":
    pop = pd.read_parquet(HERE / "cache" / "population_improvement.parquet")
    picks = json.loads((HERE / "cache" / "picks.json").read_text(encoding="utf-8"))
    info = {p["event_id"]: p for p in picks["main"] + picks["backup"]}
    for e in (sys.argv[2:] or ["B033"]):
        p = info[e]
        r = pop[pop["accessionNumber"] == p["acc"]]
        print("==", e, p["year"], p["bucket"], p["acc"], "rows=%d" % len(r))
        if len(r):
            x = r.iloc[0]
            for c in ["cik", "ticker", "name", "sic", "sic2", "reaction_date", "signal_q_end",
                      "fiscal_quarter", "improvement_type", "entry_pool", "accel_text_hit",
                      "guide_rev_raise", "hist_quarters_public_by_t1", "release_timing"]:
                print("   ", c, "=", x[c])
        an = p["acc"].replace("-", "")
        print("   EX991 cached:", (DOCS / ("%s__EX991.txt.gz" % an)).exists())
elif what == "cache":
    import collections
    c = collections.Counter()
    for p in DOCS.iterdir():
        if p.name.endswith(".txt.gz"):
            c[p.name.split("__")[-1].replace(".txt.gz", "")] += 1
    print(sorted(c.items(), key=lambda x: -x[1])[:30])
