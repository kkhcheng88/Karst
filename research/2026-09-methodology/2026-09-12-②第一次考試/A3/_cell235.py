# -*- coding: utf-8 -*-
"""KARST-235 診斷五:解釋某一包某一格——列出該期末所有相關事實(哪個 tag、哪日申報)。只讀。

用法:python _cell235.py E039 revenue 2017-12-31
"""
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8")
import finlib as F  # noqa: E402

TAGS = {"revenue": F.REV_TAGS, "gross_profit": F.GP_TAGS,
        "operating_income": F.OI_TAGS, "ocf": F.OCF_TAGS}
eid, field, end = sys.argv[1], sys.argv[2], sys.argv[3]
p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
cik = str(p["1_事件識別"]["cik"]).zfill(10)
t1 = str(p["1_事件識別"]["T1_分析截止"])[:10]
pv = next(q.get(field) for q in p["4_財務數列"]["quarters"]
          if q["period_end"] == end)
print("%s %s %s pkt=%s T1=%s" % (eid, field, end, pv, t1))
facts = F.load_facts(cik)
for t in TAGS[field]:
    for r in F.unit_rows(facts, t):
        if r.get("end") != end:
            continue
        st = r.get("start")
        d = None
        if st:
            try:
                d = (date.fromisoformat(end) - date.fromisoformat(st)).days
            except ValueError:
                d = None
        flag = ""
        if pv is not None and r.get("val") is not None:
            if abs(float(r["val"]) - pv) <= max(1.0, abs(pv) * 1e-4):
                flag = "  <<< 等於包內值"
        print("  %-58s start=%-11s dur=%-5s val=%-16s filed=%s%s" % (
            t, st, d, r.get("val"), r.get("filed"), flag))
