# -*- coding: utf-8 -*-
"""診斷:8 個補位事件的年／桶,與被補者的年／桶是否相符(鎖定檔要求同年同桶優先)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def main() -> None:
    picks = json.loads((CACHE / "picks.json").read_text(encoding="utf-8"))
    pop = pd.read_parquet(CACHE / "population_improvement.parquet").set_index("accessionNumber")
    main_ids = {p["event_id"]: p for p in picks["main"]}
    bk_ids = {p["event_id"]: p for p in picks["backup"]}
    bad = [("E009", "B002"), ("E013", "B003"), ("E060", "B004"), ("E061", "B005"),
           ("E071", "B006"), ("E076", "B007"), ("E077", "B008")]
    for me, be in bad:
        a, b = main_ids[me], bk_ids[be]
        ma, ba = pop.loc[a["acc"]], pop.loc[b["acc"]]
        print("%s(%s,%s) ← %s(%s,%s) 同年 %s 同桶 %s;被補者 signal_q_end=%s reason_xbrl=%s"
              % (me, a["year"], a["bucket"], be, b["year"], b["bucket"],
                 a["year"] == b["year"], a["bucket"] == b["bucket"],
                 ma["signal_q_end"], ma["improvement_type"]))
    print()
    for p in picks["backup"][:10]:
        m = pop.loc[p["acc"]]
        print("%s %s %s ticker=%s signal_q_end=%s imp=%s" % (
            p["event_id"], p["year"], p["bucket"], m["ticker"], m["signal_q_end"],
            m["improvement_type"]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
