# -*- coding: utf-8 -*-
"""Read-only: dump raw companyfacts revenue rows around a date for CLX / SM."""
import gzip, json, sys
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
sys.path.insert(0, str(ROOT / "A2"))
import finlib  # noqa
from datetime import date

for cik, lo, hi in [("0000021076", "2023-03-01", "2023-10-15"),
                    ("0000893538", "2016-09-01", "2017-04-15")]:
    facts = finlib.load_facts(cik)
    print("=== CIK", cik, facts["entityName"] if facts else None)
    for t in finlib.REV_TAGS:
        rows = finlib.unit_rows(facts, t)
        for r in rows:
            st, en = r.get("start"), r.get("end")
            if st and en and lo <= en <= hi:
                d = (date.fromisoformat(en) - date.fromisoformat(st)).days
                print("  %-58s %s %s %5dd %14.0f filed=%s" % (t[:58], st, en, d, r["val"], r["filed"]))
