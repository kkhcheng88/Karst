# -*- coding: utf-8 -*-
"""診斷:適用性 F 的「連續 8 季」為何在 2022 年後大量失敗。

比較兩種標籤集下的連續季數:
  3 標籤(v1.2 明文)= Revenues / RevenueFromContractWithCustomerExcludingAssessedTax /
                      SalesRevenueNet
  6 標籤(A/ s3 用過)= 上面三個 + RevenueFromContractWithCustomerIncludingAssessedTax /
                      SalesRevenueGoodsNet / RegulatedAndUnregulatedOperatingRevenue
用法:python diag_tags.py [CIK 數上限]
"""
from __future__ import annotations

import gzip
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
CF = ROOT / "data" / "sec" / "companyfacts"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

TAGS3 = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
         "SalesRevenueNet"]
TAGS6 = TAGS3 + ["RevenueFromContractWithCustomerIncludingAssessedTax",
                 "SalesRevenueGoodsNet", "RegulatedAndUnregulatedOperatingRevenue"]


def series_of(facts: dict, tags: list[str]) -> dict[str, float]:
    gaap = facts.get("facts", {}).get("us-gaap", {})
    by_end: dict[str, tuple[float, str]] = {}
    for tag in tags:
        node = gaap.get(tag)
        if not node:
            continue
        for unit, rows in node.get("units", {}).items():
            if unit != "USD":
                continue
            for r in rows:
                st, en, v = r.get("start"), r.get("end"), r.get("val")
                if st is None or en is None or v is None:
                    continue
                try:
                    d = (date.fromisoformat(en) - date.fromisoformat(st)).days
                except ValueError:
                    continue
                if not (80 <= d <= 100):
                    continue
                prev = by_end.get(en)
                if prev is None or r.get("filed", "") < prev[1]:
                    by_end[en] = (float(v), r.get("filed", ""), tag)
    return by_end


def n_consec(ends: list[str], q: str) -> int:
    if q not in ends:
        return 0
    i = ends.index(q)
    n, j = 1, i
    while j - 1 >= 0:
        gap = (date.fromisoformat(ends[j]) - date.fromisoformat(ends[j - 1])).days
        if 60 <= gap <= 130:
            n += 1
            j -= 1
        else:
            break
    return n


def one(cik: str) -> dict:
    p = CF / ("CIK%s.json.gz" % cik)
    if not p.exists():
        return {"cik": cik}
    with gzip.open(p, "rt", encoding="utf-8") as f:
        facts = json.load(f)
    s3 = series_of(facts, TAGS3)
    s6 = series_of(facts, TAGS6)
    gaap = facts.get("facts", {}).get("us-gaap", {})
    tags_with_q = []
    for tag, node in gaap.items():
        for unit, rows in node.get("units", {}).items():
            if unit != "USD":
                continue
            for r in rows:
                st, en = r.get("start"), r.get("end")
                if st is None or en is None:
                    continue
                try:
                    d = (date.fromisoformat(en) - date.fromisoformat(st)).days
                except ValueError:
                    continue
                if 80 <= d <= 100:
                    tags_with_q.append(tag)
                    break
    return {"cik": cik, "s3": s3, "s6": s6,
            "extra": [t for t in tags_with_q if t not in TAGS3]}


def main() -> None:
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    d = pd.read_parquet(CACHE / "population_improvement.parquet")
    e = pd.read_parquet(CACHE / "events_raw.parquet")
    e = e.drop_duplicates(subset=["accessionNumber"])[
        ["accessionNumber", "filingDate"]]
    d = d.merge(e, on="accessionNumber", how="left")
    c = d[(d["in_universe"] == 1) & (d["in_pool_window"])
          & (d["rel_spy"] >= d["thr_p90"]) & (d["rel_sic2"] > 0)].copy()
    c["year"] = c["year"].astype(int)
    bad = c[(c["year"] >= 2022) & (c["n_consec_q"].fillna(0) < 8)]
    print("2022+ 候選未過連續 8 季:%d / %d" % (len(bad), (c["year"] >= 2022).sum()))
    ciks = sorted(bad["cik"].unique())[:cap]
    print("取樣公司數:%d" % len(ciks))

    import multiprocessing as mp
    got = []
    with mp.Pool(processes=8) as pool:
        for r in pool.imap_unordered(one, ciks, chunksize=8):
            got.append(r)

    n_both = n_only6 = n_only3 = n_none = 0
    extra_ct: Counter = Counter()
    n6_ok = 0
    for r in got:
        s3, s6 = r.get("s3") or {}, r.get("s6") or {}
        if not s3 and not s6:
            n_none += 1
            continue
        # 用該公司最新期末做 q(診斷用,不必與事件對齊)
        q3 = max(s3) if s3 else ""
        q6 = max(s6) if s6 else ""
        c3 = n_consec(sorted(s3), q3) if q3 else 0
        c6 = n_consec(sorted(s6), q6) if q6 else 0
        if c3 >= 8 and c6 >= 8:
            n_both += 1
        elif c6 >= 8:
            n_only6 += 1
        elif c3 >= 8:
            n_only3 += 1
        n6_ok += int(c6 >= 8)
        for t in r["extra"]:
            extra_ct[t] += 1
    print("公司層:兩者皆≥8 %d;只有 6 標籤≥8 %d;只有 3 標籤≥8 %d;皆不足 %d;無資料 %d"
          % (n_both, n_only6, n_only3, len(got) - n_both - n_only6 - n_only3 - n_none,
             n_none))
    print("6 標籤下公司最新季連續≥8:%d / %d" % (n6_ok, len(got)))
    print("3 標籤以外有單季值的標籤:", extra_ct.most_common(8))

    # 印 6 家看缺口形態
    shown = 0
    for r in got:
        s3, s6 = r.get("s3") or {}, r.get("s6") or {}
        if s3 and len(s3) >= 5 and n_consec(sorted(s3), max(s3)) < 8 and shown < 8:
            ends = sorted(s3)
            gaps = [(date.fromisoformat(ends[i]) - date.fromisoformat(ends[i - 1])).days
                    for i in range(1, len(ends))]
            print("  CIK%s 3 標籤 %d 季(連續 %d);最近 8 個期末 %s;缺口 %s"
                  % (r["cik"], len(ends), n_consec(ends, max(ends)),
                     ends[-8:], gaps[-7:]))
            shown += 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
