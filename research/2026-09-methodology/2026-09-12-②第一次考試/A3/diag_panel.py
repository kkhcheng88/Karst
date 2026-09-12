# -*- coding: utf-8 -*-
"""Diagnostic: availability of 3-month revenue periods by quarter-end month and year.

Question: why does the "8 consecutive quarters" applicability gate fail for 2022+?
Hypothesis: the fiscal-year-end quarter never carries a 3-month duration.
"""
from __future__ import annotations

import gzip
import json
import multiprocessing as mp
import sys
from datetime import date
from pathlib import Path

import pandas as pd

CF = Path(r"C:\projects\Karst\data\sec\companyfacts")
HERE = Path(__file__).resolve().parent
TAGS3 = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
         "SalesRevenueNet"]


def one(c: str):
    p = CF / ("CIK%s.json.gz" % c)
    if not p.exists():
        return None
    with gzip.open(p, "rt", encoding="utf-8") as f:
        g = json.load(f)["facts"].get("us-gaap", {})
    ends = set()
    for t in TAGS3:
        n = g.get(t)
        if not n:
            continue
        for u, rs in n.get("units", {}).items():
            if u != "USD":
                continue
            for r in rs:
                s, e = r.get("start"), r.get("end")
                if not s or not e:
                    continue
                try:
                    d = (date.fromisoformat(e) - date.fromisoformat(s)).days
                except ValueError:
                    continue
                if 80 <= d <= 100:
                    ends.add(e)
    return c, sorted(ends)


def main() -> None:
    n_cik = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    ev = pd.read_parquet(HERE / "cache" / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"])
    ciks = sorted(ev["cik"].unique())[:n_cik]
    res = []
    with mp.Pool(8) as pool:
        for r in pool.imap_unordered(one, ciks):
            if r:
                res.append(r)
    print("companies %d" % len(res))
    for y in range(2015, 2026):
        mon = {3: 0, 6: 0, 9: 0, 12: 0}
        for _c, ends in res:
            for m in mon:
                if any(e[:4] == str(y) and int(e[5:7]) == m for e in ends):
                    mon[m] += 1
        print(y, mon)
    # how many ends in total per year
    for y in range(2015, 2026):
        tot = sum(len([e for e in ends if e[:4] == str(y)]) for _c, ends in res)
        print("total ends %d: %d" % (y, tot))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
