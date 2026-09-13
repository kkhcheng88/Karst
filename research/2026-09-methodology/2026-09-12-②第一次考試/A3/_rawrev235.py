# -*- coding: utf-8 -*-
"""KARST-235 診斷二:印出某 CIK 的收入原始事實(start/end/val/filed),只讀。"""
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8")
import finlib as F  # noqa: E402

cik = sys.argv[1].zfill(10)
lo, hi = sys.argv[2], sys.argv[3]
facts = F.load_facts(cik)
for tag in F.REV_TAGS:
    rows = F.unit_rows(facts, tag)
    keep = []
    for r in rows:
        en = r.get("end", "")
        if not (lo <= en <= hi):
            continue
        st = r.get("start")
        if not st:
            continue
        d = (date.fromisoformat(en) - date.fromisoformat(st)).days
        if not (60 <= d <= 400):
            continue
        keep.append((en, st, r.get("val"), r.get("filed"), d,
                     r.get("frame", "")))
    if not keep:
        continue
    print("### tag", tag, "rows", len(keep))
    for en, st, v, f, d, fr in sorted(keep):
        print("   end=%s start=%s val=%-16s filed=%s dur=%d %s" % (en, st, v, f, d, fr))
