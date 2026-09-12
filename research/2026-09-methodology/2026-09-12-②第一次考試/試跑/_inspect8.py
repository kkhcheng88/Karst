# -*- coding: utf-8 -*-
"""Read-only: check the revenue series used for M1/M2."""
import json, sys
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
sys.path.insert(0, str(ROOT / "A2"))
import finlib  # noqa

for eid in ["E065", "E073", "E009", "E001"]:
    pk = json.load(open(ROOT / "A2" / "packets" / (eid + ".json"), encoding="utf-8"))
    cik = pk["cik"]
    sq = pk["4_財務數列"]["signal_q_end"]
    b = finlib.bundle(cik)
    rev = b["rev_q"]
    keys = sorted(rev)
    print("===", eid, pk["ticker"], "signal_q_end", sq, "n_q", len(keys))
    lo = [k for k in keys if k >= "2014-01-01"]
    start = keys.index(sq) if sq in keys else None
    idx = keys.index(sq) if sq in keys else 0
    for k in keys[max(0, idx - 5): idx + 7]:
        print("   ", k, "%.1fM" % (rev[k] / 1e6))
    print("    yoy:", [(e, None if finlib.yoy(rev, e) is None else round(finlib.yoy(rev, e), 4))
                       for e in keys[idx:idx + 6]])
