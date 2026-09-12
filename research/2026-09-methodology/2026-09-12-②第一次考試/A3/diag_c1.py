# -*- coding: utf-8 -*-
"""診斷 C1:為何 25 宗有財年收入指引的事件定位不到財年。只印欄位與日期,不印公司名。"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

import finlib as F
import s8_controls as S

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def main() -> None:
    picks = json.loads((CACHE / "picks.json").read_text(encoding="utf-8"))
    pop = pd.read_parquet(CACHE / "population_improvement.parquet").set_index("accessionNumber")
    recs: dict[str, list[dict]] = {}
    for line in (CACHE / "guidance_parsed.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        recs.setdefault(r["accessionNumber"], []).append(r)
    n = 0
    for kind in ("main", "backup"):
        for p in picks[kind]:
            rs = [r for r in recs.get(p["acc"], [])
                  if r.get("metric") == "revenue" and r.get("period") == "FY"
                  and r.get("new_mid") is not None]
            if not rs:
                continue
            m = pop.loc[p["acc"]]
            b = F.bundle(m["cik"])
            q_end = m["signal_q_end"]
            ann = sorted({e for _s, e, _v in b["rev_annual"]})
            ends = sorted(e for e in b["rev_q"] if e and e <= q_end)
            fye = [e for e in ann if e >= q_end]
            py = [e for e in ann if e < q_end]
            py_end = py[-1] if py else None
            py_qs = sorted(e for e in b["rev_q"] if py_end and e <= py_end)[-4:]
            ytds = [(s, e, v) for s, e, v in b["rev_cum"] if e == q_end]
            ytd = max(ytds, key=lambda x: S._days(x[0], x[1]))[2] if ytds else None
            c1 = S.c1_for(rs, b, q_end)
            n += 1
            print("%s %s sig=%s ann=%s py_end=%s py_qs=%s(n=%d) ytd=%s mid=%s → %s %s" % (
                p["event_id"], "M" if kind == "main" else "B", q_end, ann[-4:], py_end,
                py_qs, len(py_qs), None if ytd is None else round(ytd),
                rs[0]["new_mid"], c1["C1_implied_yoy"], c1["C1_note"][:40]))
    print("有財年收入指引的事件:", n)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
