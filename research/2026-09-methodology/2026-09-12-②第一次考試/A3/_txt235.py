# -*- coding: utf-8 -*-
"""KARST-235 診斷六:印某包的訊號季/去年同季格、包內自報越界布林、稿內首 400 字。只讀。"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
for eid in sys.argv[1:]:
    p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
    fin = p["4_財務數列"]
    t1 = str(p["1_事件識別"]["T1_分析截止"])[:10]
    text = (p["2_觸發資料"] or {}).get("ex991_full_text") or ""
    print("=" * 72)
    print(eid, "T1", t1, "sig", fin["signal_q_end"],
          "n_rows_first_filed_after_T1", fin.get("n_rows_first_filed_after_T1"),
          "hist_public_by_T1", fin.get("hist_quarters_public_by_T1"))
    for q in fin["quarters"]:
        print("   %s rev=%-16s 首報晚於T1=%s" % (
            q["period_end"], q.get("revenue"),
            q.get("revenue_xbrl_first_filed_after_T1")))
    if text:
        snips = [s for s in re.split(r"(?<=[.;])\s+|\n", text)
                 if re.search(r"(?i)(prior|last year|year-ago)", s)
                 and re.search(r"(?i)(revenue|net sales|total sales)", s)][:4]
        for s in snips:
            print("   TEXT>", s.strip()[:300])
