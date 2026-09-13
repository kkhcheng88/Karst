# -*- coding: utf-8 -*-
"""KARST-236 診斷:印出「只在裸數(表格)中命中」那些格在稿內的實際上下文(只讀)。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s22_fix235_rebuild as R  # noqa: E402

TARGETS = [("E017", "gross_profit"), ("E022", "operating_income"),
           ("E025", "operating_income"), ("E047", "operating_income")]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for eid, name in TARGETS:
        p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
        fin = p["4_財務數列"]
        sig = fin["signal_q_end"]
        row = next(q for q in fin["quarters"] if q["period_end"] == sig)
        v = row.get(name)
        text = (p["2_觸發資料"] or {}).get("ex991_full_text") or ""
        print("== %s %s sig=%s value=%s" % (eid, name, sig, v))
        for m in R.NUM_RX.finditer(text):
            raw = R._num(m.group(1))
            if raw in (None, 0) or v in (None, 0):
                continue
            unit = (m.group(2) or "").lower()
            cands = ([raw * R.MULT[unit]] if unit in R.MULT else []) + \
                    [raw * s for s in (1.0, 1e3, 1e6, 1e9)]
            if not any(c and abs(abs(c) / abs(v) - 1.0) <= 0.005 for c in cands):
                continue
            snip = re.sub(r"\s+", " ", text[max(0, m.start() - 120):
                                            m.end() + 30])
            print("   pos=%-7s raw=%-14s unit=%-9s | %s"
                  % (m.start(), m.group(1), unit or "-", snip))
        kw = R.KW[name]
        print("   keyword-nearby = %s" % bool(
            kw.search(text[max(0, text.find(str(int(v // 1000))) - 200):])))


if __name__ == "__main__":
    main()
