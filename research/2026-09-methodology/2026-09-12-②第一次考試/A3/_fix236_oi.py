# -*- coding: utf-8 -*-
"""KARST-236 診斷:某包某 tag 在訊號期末的所有原始事實(只讀)。"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import finlib_fixed as FF  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    eid, tag = sys.argv[1], sys.argv[2]
    p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
    cik = str(p["1_事件識別"]["cik"]).zfill(10)
    sig = p["4_財務數列"]["signal_q_end"]
    facts = FF.load_facts(cik)
    print("eid=%s tag=%s sig=%s" % (eid, tag, sig))
    print("--- 直接單季事實(全部期長,含 sig 前後 400 日)---")
    for r in FF.unit_rows(facts, tag):
        st, en, v = r.get("start"), r.get("end"), r.get("val")
        if st is None or v is None:
            continue
        try:
            d = (date.fromisoformat(en) - date.fromisoformat(st)).days
        except ValueError:
            continue
        if abs((date.fromisoformat(en) - date.fromisoformat(sig)).days) > 400:
            continue
        print("  %s→%s d=%-4s val=%-16s filed=%s" % (st, en, d, v, r.get("filed")))
    print("--- 年報期末推算 ---")
    print(" ", FF._year_end_quarters(facts, [tag]).get(sig))


if __name__ == "__main__":
    main()
