# -*- coding: utf-8 -*-
"""KARST-235 診斷三:某 CIK 某 end 日的所有收入類事實(全部 tag/單位),只讀。"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8")
import finlib as F  # noqa: E402

cik = sys.argv[1].zfill(10)
ends = set(sys.argv[2:])
facts = F.load_facts(cik)
for tag, node in facts.get("facts", {}).get("us-gaap", {}).items():
    if not any(k in tag for k in ("Revenue", "Sales", "GrossProfit",
                                  "OperatingIncome")):
        continue
    for unit, rows in node.get("units", {}).items():
        for r in rows:
            if r.get("end") in ends:
                print("%-58s %-4s end=%s start=%s val=%-16s filed=%s dur=%s %s" % (
                    tag, unit, r.get("end"), r.get("start"), r.get("val"),
                    r.get("filed"),
                    (len(r.get("start", "")) and r.get("start")),
                    r.get("frame", "")))
