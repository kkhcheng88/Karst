# -*- coding: utf-8 -*-
"""KARST-236 診斷:某包訊號季收入在稿內的最接近命中(只讀)。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s22_fix235_rebuild as R  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for eid in sys.argv[1:]:
        p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
        fin = p["4_財務數列"]
        sig = fin["signal_q_end"]
        row = next(q for q in fin["quarters"] if q["period_end"] == sig)
        v = row.get("revenue_ex991")
        text = (p["2_觸發資料"] or {}).get("ex991_full_text") or ""
        print("== %s sig=%s revenue=%s ex991=%s src=%s len=%s"
              % (eid, sig, row.get("revenue"), v, row.get("revenue_source"),
                 len(text)))
        hits = []
        for m in R.NUM_RX.finditer(text):
            raw = R._num(m.group(1))
            if raw in (None, 0) or v in (None, 0):
                continue
            u = (m.group(2) or "").lower()
            cands = ([raw * R.MULT[u]] if u in R.MULT else []) + \
                    [raw * s for s in (1.0, 1e3, 1e6, 1e9)]
            for c in cands:
                if c and abs(abs(c) / abs(v) - 1.0) <= 0.02:
                    snip = re.sub(r"\s+", " ", text[max(0, m.start() - 100):
                                                    m.end() + 30])
                    hits.append((abs(abs(c) / abs(v) - 1.0), m.group(1), u, snip))
        hits.sort()
        for d, tok, u, snip in hits[:4]:
            print("   rel=%.4f tok=%-14s unit=%-8s | %s" % (d, tok, u or "-", snip))
        if not hits:
            print("   (2% 內無任何候選)")


if __name__ == "__main__":
    main()
