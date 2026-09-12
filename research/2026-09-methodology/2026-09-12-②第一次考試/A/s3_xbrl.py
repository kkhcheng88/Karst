# -*- coding: utf-8 -*-
"""KARST-222 票 A 第三步:由 companyfacts 取訊號季按年收入增速 g0 與上一季按年增速。

只讀 `data/sec/companyfacts/`;輸出 `A/cache/xbrl_metrics.parquet`。

口徑:
  - 單季收入 = 時長 80–100 日、期末落在該季的事實;同一 (start,end) 多份取**首報**
    (filed 最早那份);同一期末多個 tag 按 REV_TAGS 次序取先者(公司換 tag 用)。
  - 訊號季 = 期末 ≤ filingDate 且距 filingDate ≤ 120 日的最後一季;不合標資料不足。
  - g0 = 訊號季收入 / 去年同季收入 − 1;去年同季 = 期末相距 340–390 日中最近的一季。
  - 上一季增速 = 訊號季前一季的同法按年增速;加速 = g0 − 上一季增速(百分點)。
"""
from __future__ import annotations

import gzip
import json
import multiprocessing as mp
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
CF = ROOT / "data" / "sec" / "companyfacts"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

REV_TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
            "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax",
            "SalesRevenueGoodsNet", "RegulatedAndUnregulatedOperatingRevenue"]

def quarter_rev(cik: str) -> tuple[dict[str, float], str]:
    """回傳 (期末日 → 首報單季收入, 狀態)。逐家載入、抽完即棄(不整批留在記憶體)。"""
    p = CF / ("CIK%s.json.gz" % cik)
    if not p.exists():
        return {}, "無 companyfacts 快取"
    try:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            facts = json.load(f)
    except (OSError, json.JSONDecodeError, EOFError):
        return {}, "companyfacts 讀取失敗"

    gaap = facts.get("facts", {}).get("us-gaap", {})
    if not gaap:
        return {}, "無 us-gaap 科目(可能 IFRS 申報)"
    by_end: dict[str, tuple[float, str]] = {}
    for tag in REV_TAGS:
        node = gaap.get(tag)
        if not node:
            continue
        for unit, rows in node.get("units", {}).items():
            if unit != "USD":
                continue
            for r in rows:
                st, en = r.get("start"), r.get("end")
                v = r.get("val")
                if st is None or en is None or v is None:
                    continue
                try:
                    d = (date.fromisoformat(en) - date.fromisoformat(st)).days
                except ValueError:
                    continue
                if not (80 <= d <= 100):
                    continue
                prev = by_end.get(en)
                if prev is None:
                    by_end[en] = (float(v), r.get("filed", ""))
                elif r.get("filed", "") < prev[1]:
                    # 同一期末多份(重述)→ 取 filed 最早那份(首報值)
                    by_end[en] = (float(v), r.get("filed", ""))
    if not by_end:
        return {}, "無單季收入事實(可能只報累計)"
    return {k: v[0] for k, v in by_end.items()}, ""


def yoy(series: dict[str, float], end: str) -> float | None:
    e = date.fromisoformat(end)
    cands = []
    for k in series:
        d = (e - date.fromisoformat(k)).days
        if 340 <= d <= 390:
            cands.append((abs(d - 365), k))
    if not cands:
        return None
    cands.sort()
    base = series[cands[0][1]]
    if base == 0:
        return None
    return series[end] / base - 1.0


def _one(cik: str):
    return cik, quarter_rev(cik)


def main() -> None:
    ev = pd.read_parquet(CACHE / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    ciks = sorted(ev["cik"].unique())
    print("要取 XBRL 的公司數:%d" % len(ciks), flush=True)

    series_by_cik: dict[str, dict[str, float]] = {}
    status_by_cik: dict[str, str] = {}
    n_done = 0
    with mp.Pool(processes=8) as pool:
        for cik, (s, st) in pool.imap_unordered(_one, ciks, chunksize=20):
            series_by_cik[cik] = s
            status_by_cik[cik] = st
            n_done += 1
            if n_done % 500 == 0:
                print("  ...%d/%d" % (n_done, len(ciks)), flush=True)

    rows = []
    for r in ev.itertuples(index=False):
        s = series_by_cik.get(r.cik, {})
        st = status_by_cik.get(r.cik, "")
        fd = r.filingDate
        fdd = date.fromisoformat(fd)
        rec = dict(accessionNumber=r.accessionNumber, cik=r.cik,
                   signal_q_end="", signal_q_days_before_filing=None,
                   fiscal_quarter="", rev_g0=None, rev_prev_q_yoy=None,
                   accel_pp=None, accel_hit=None, xbrl_status=st or "無收入數列")
        if s:
            ends = sorted(s)
            cands = [e for e in ends if date.fromisoformat(e) <= fdd
                     and (fdd - date.fromisoformat(e)).days <= 120]
            if not cands:
                rec["xbrl_status"] = "filingDate 前 120 日內無單季收入期末"
            else:
                q = cands[-1]
                rec["signal_q_end"] = q
                rec["signal_q_days_before_filing"] = (fdd - date.fromisoformat(q)).days
                qm = date.fromisoformat(q).month
                rec["fiscal_quarter"] = "%dQ%d" % (
                    date.fromisoformat(q).year, (qm - 1) // 3 + 1)
                g0 = yoy(s, q)
                rec["rev_g0"] = g0
                idx = ends.index(q)
                if idx >= 1:
                    pq = ends[idx - 1]
                    pg = yoy(s, pq)
                    rec["rev_prev_q_yoy"] = pg
                    if g0 is not None and pg is not None:
                        rec["accel_pp"] = (g0 - pg) * 100.0
                        rec["accel_hit"] = int(rec["accel_pp"] >= 2.0)
                if g0 is None:
                    rec["xbrl_status"] = "算不出 g0(缺去年同季)"
                else:
                    rec["xbrl_status"] = ""
        rows.append(rec)

    out = pd.DataFrame(rows)
    out.to_parquet(CACHE / "xbrl_metrics.parquet", index=False)
    print("有 g0:%d / %d" % (out["rev_g0"].notna().sum(), len(out)))
    print("有上一季增速:%d;加速命中(≥2pp):%d" % (
        out["rev_prev_q_yoy"].notna().sum(), (out["accel_hit"] == 1).sum()))
    print("狀態分佈:", out["xbrl_status"].value_counts().to_dict())
    print("→", CACHE / "xbrl_metrics.parquet")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
