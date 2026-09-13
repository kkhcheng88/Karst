# -*- coding: utf-8 -*-
"""KARST-235 診斷四:印出被標越界的格(舊容忍度版),只讀。"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
s = json.load(open(HERE / "audit_out" / "revenue_integrity_summary.json",
                   encoding="utf-8"))
for r in s["rows"]:
    cells = [c for c in (r["revenue_leakcells"] or "").split(";") if c]
    if cells:
        print(r["event_id"], "|", "; ".join(cells))
