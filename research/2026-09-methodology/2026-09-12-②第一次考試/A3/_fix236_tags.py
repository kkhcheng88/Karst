# -*- coding: utf-8 -*-
"""KARST-236 診斷:訊號季各收入 tag 的原始事實(只讀)。"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import finlib_fixed as FF  # noqa: E402

CASES = [("E073", "2024-09-30"), ("E057", "2022-06-30"), ("E047", "2020-09-30"),
         ("E021", "2017-03-31"), ("E022", "2016-12-31"), ("E024", "2017-09-30"),
         ("E017", "2016-12-31"), ("E025", "2018-03-31")]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for eid, period in CASES:
        p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
        cik = str(p["1_事件識別"]["cik"]).zfill(10)
        t1 = str(p["1_事件識別"]["T1_分析截止"])[:10]
        facts = FF.load_facts(cik)
        print("##### %s cik=%s T1=%s period=%s" % (eid, cik, t1, period))
        for t in FF.REV_TAGS:
            hit = []
            for r in FF.unit_rows(facts, t):
                st, en, v = r.get("start"), r.get("end"), r.get("val")
                if v is None or st is None:
                    continue
                try:
                    d = (date.fromisoformat(en) - date.fromisoformat(st)).days
                except ValueError:
                    continue
                if 80 <= d <= 100 and (en == period or st <= period <= en):
                    hit.append((r.get("filed"), en, float(v)))
            if hit:
                print("  %-58s %s" % (t, sorted(hit)[:4]))


if __name__ == "__main__":
    main()
