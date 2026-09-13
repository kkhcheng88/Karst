# -*- coding: utf-8 -*-
"""KARST-236 診斷:某包訊號季的修正值由哪一條事實來(只讀)。"""
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
    eid = sys.argv[1] if len(sys.argv) > 1 else "E073"
    p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
    cik = str(p["1_事件識別"]["cik"]).zfill(10)
    sig = p["4_財務數列"]["signal_q_end"]
    facts = FF.load_facts(cik)
    print("eid=%s cik=%s sig=%s" % (eid, cik, sig))
    full = FF.quarterly_full(facts, FF.REV_TAGS, derive_fy=True)
    print("rev_full[sig] =", full.get(sig))
    print("nearby ends:", sorted(k for k in full if abs(
        (date.fromisoformat(k) - date.fromisoformat(sig)).days) <= 200))
    print("--- all raw facts ending at sig (any duration) ---")
    for t in FF.REV_TAGS:
        for r in FF.unit_rows(facts, t):
            if r.get("end") == sig and r.get("val") is not None:
                st = r.get("start") or ""
                d = ((date.fromisoformat(sig) - date.fromisoformat(r["end"])).days
                     if not st else
                     (date.fromisoformat(sig) - date.fromisoformat(st)).days)
                print("  %-58s start=%s days=%s val=%s filed=%s" % (
                    t, st, d, r["val"], r.get("filed")))
    print("--- year_end derived candidates ---")
    for t in FF.REV_TAGS:
        y = FF._year_end_quarters(facts, [t])
        if sig in y:
            print("  %s %s" % (t, y[sig]))


if __name__ == "__main__":
    main()
