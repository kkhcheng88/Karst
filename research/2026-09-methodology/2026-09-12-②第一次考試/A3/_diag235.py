# -*- coding: utf-8 -*-
"""KARST-235 診斷:印出被標越界的包的 revenue 逐格 vs 重算值 vs T1 後四季值(只讀)。"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8")
import finlib as F  # noqa: E402
import audit_revenue_integrity as A  # noqa: E402

which = sys.argv[1:] or ["E006", "E022", "E024", "E026", "E029", "E030", "E033",
                         "E049", "E059", "E078", "E079", "E050", "E032"]
for eid in which:
    p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
    cik = str(p["1_事件識別"]["cik"]).zfill(10)
    t1 = str(p["1_事件識別"]["T1_分析截止"])[:10]
    facts = F.load_facts(cik)
    rec = A.rec_series(facts) if facts else {}
    rev = rec.get("revenue", {})
    ends = sorted(rev)
    post = [e for e in ends if e > t1][:4]
    print("=" * 70)
    print(eid, "T1", t1, "sig", p["4_財務數列"]["signal_q_end"],
          "q_cik", p["1_事件識別"]["cik"], "file", "CIK%s.json.gz" % cik,
          "exists", (F.CF / ("CIK%s.json.gz" % cik)).exists())
    print("  packet rows:")
    for q in p["4_財務數列"]["quarters"]:
        e = q["period_end"]
        print("    %s rev=%-16s rec=%-16s gp=%-14s oi=%-14s ocf=%-14s src=%s" % (
            e, q.get("revenue"), rev.get(e), q.get("gross_profit"),
            q.get("operating_income"), q.get("ocf"),
            q.get("revenue_source", "")[:12]))
    print("  post-T1 quarters:", [(e, rev.get(e)) for e in post])
    print("  all rec ends:", [(e, rev[e]) for e in ends][-14:])
