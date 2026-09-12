# -*- coding: utf-8 -*-
"""Read-only: SM Energy raw revenue rows 2016-2018 (check Q2 2017 = 120.7M)."""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
sys.path.insert(0, str(ROOT / "A2"))
import finlib  # noqa

facts = finlib.load_facts("0000893538")
for t in finlib.REV_TAGS:
    for r in finlib.unit_rows(facts, t):
        st, en = r.get("start"), r.get("end")
        if st and en and "2016-09-01" <= en <= "2018-01-05":
            d = (date.fromisoformat(en) - date.fromisoformat(st)).days
            print("%-56s %s %s %4dd %14.0f filed=%s" % (t[:56], st, en, d, r["val"], r["filed"]))
