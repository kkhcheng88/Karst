# -*- coding: utf-8 -*-
"""Read-only: print the four post-T1 quarters with base values and provenance."""
import json, sys
from datetime import date
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
sys.path.insert(0, str(ROOT / "A2"))
sys.path.insert(0, str(ROOT / "試跑"))
import finlib  # noqa
from score_pilot import add_months, nearest, rev_series  # noqa

EVENTS = ["E001", "E009", "E017", "E025", "E033", "E041", "E049", "E057", "E065", "E073"]

for eid in EVENTS:
    pk = json.load(open(ROOT / "A2" / "packets" / (eid + ".json"), encoding="utf-8"))
    cik, sq = pk["cik"], pk["4_財務數列"]["signal_q_end"]
    facts = finlib.load_facts(cik)
    q3 = finlib.quarterly(facts, finlib.REV_TAGS)
    rev = rev_series(cik)
    sqd = date.fromisoformat(sq)
    print("===", eid, pk["ticker"], "sq_end", sq, "g0=%.4f" % pk["4_財務數列"]["g0_signal_q_yoy"])
    for k in (1, 2, 3, 4):
        tgt = add_months(sqd, 3 * k)
        key = nearest(rev, tgt)
        if key is None:
            print("   Q+%d target %s -> 缺" % (k, tgt))
            continue
        base = nearest(rev, add_months(date.fromisoformat(key), -12), tol=30)
        y = None if base is None else rev[key] / rev[base] - 1
        print("   Q+%d target %s -> %s %10.1fM src=%s | base %s %10.1fM yoy=%s" % (
            k, tgt, key, rev[key] / 1e6, "3M" if key in q3 else "累計相減",
            base, rev[base] / 1e6 if base else float("nan"),
            "—" if y is None else "%+.3f" % y))
