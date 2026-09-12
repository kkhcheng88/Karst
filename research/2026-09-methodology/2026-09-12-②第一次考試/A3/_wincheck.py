# -*- coding: utf-8 -*-
"""量度:本地 submissions 的 filings.recent 窗口有多長,以及「無年報」同業是否只是窗口截斷。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
ROOT = Path(r"C:\projects\Karst")
SUB = ROOT / "data" / "sec" / "submissions"


def rows(cik):
    p = SUB / ("CIK%s.json" % cik)
    if not p.exists():
        return None, None
    d = json.loads(p.read_text(encoding="utf-8"))
    f = d.get("filings", {})
    r = f.get("recent", {})
    older = f.get("files", [])
    return r, older


def main():
    picks = json.loads((CACHE / "picks_final.json").read_text(encoding="utf-8"))
    plan = json.loads((CACHE / "enrich_plan.json").read_text(encoding="utf-8"))
    meta = pd.read_parquet(CACHE / "population_improvement.parquet").set_index("accessionNumber")
    reacl = []
    n_noann = 0
    n_noann_nofile = 0
    n_noann_hasolder = 0
    n_local_missing = 0
    for f in picks["final"]:
        slot = f["slot"]
        m = meta.loc[f["acc"]]
        r, older = rows(m["cik"])
        if r is None:
            n_local_missing += 1
            continue
        ds = [x for x in r.get("filingDate", []) if x]
        if ds:
            reacl.append((min(ds), m["reaction_date"], slot))
        for pr in plan["peers"][slot]["peers"]:
            if pr["has_annual"]:
                continue
            n_noann += 1
            r2, o2 = rows(pr["entity_id"])
            if r2 is None:
                n_noann_nofile += 1
                continue
            d2 = [x for x in r2.get("filingDate", []) if x]
            lo = min(d2) if d2 else ""
            if o2:
                n_noann_hasolder += 1
            print("NOANN", slot, pr["entity_id"], pr["sic4"], "T1", m["reaction_date"],
                  "recent_lo", lo, "older_chunks", len(o2))
    df = pd.DataFrame(reacl, columns=["recent_lo", "T1", "slot"])
    cut = (df["recent_lo"] > df["T1"]).sum()
    print("母體事件 issuer 本地 submissions 存在 %d;不存在 %d" % (len(df), n_local_missing))
    print("issuer 自己 recent 起點已晚於 T1 的宗數:", int(cut))
    print("無年報同業 %d;其中本地無 submissions %d;有更舊分片 %d"
          % (n_noann, n_noann_nofile, n_noann_hasolder))
    print("recent_lo 分位:", df["recent_lo"].min(), df["recent_lo"].quantile(.5),
          df["recent_lo"].max())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
