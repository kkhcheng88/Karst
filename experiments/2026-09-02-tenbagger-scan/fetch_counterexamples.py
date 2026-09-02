# -*- coding: utf-8 -*-
"""KARST-160 第四步之一:抓反例(迷因股)的價格與知情時點帳目。
這批公司不在 728 家宇宙內,是本票新增的原料,不是既有原料的副本(D-134 相容)。
帳目規則照 fundamentals-panel/RULES.md 第一、二、六節:filed <= 月底、首版優先、
季度跨度 80–100 日、TTM 取最近四季。
"""
import json
import os
import pathlib
import time
import urllib.request

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "out"
CACHE = DATA / "secfacts"
for d in (DATA, OUT, CACHE):
    d.mkdir(parents=True, exist_ok=True)

UA = "Karst Research research@vl-lawyers.com"
# 票面點名七個;NKLA 與 RIDE 已除牌,免費行情源無歷史價(這件事本身是誠實聲明的證據),
# 故補上五個仍然掛牌、同屬「故事先行 + 靠增發續命 + 由高位跌逾九成」的同類。
COUNTEREXAMPLES = ["BYND", "AMC", "SPCE", "CLOV", "GME",
                   "WKHS", "HYLN", "LCID", "PTON", "CHPT"]
DELISTED_NO_PRICE = ["NKLA", "RIDE"]

TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueNet", "SalesRevenueGoodsNet", "Revenue",
                "RevenueFromContractsWithCustomers"],
    "diluted_shares": ["WeightedAverageNumberOfDilutedSharesOutstanding",
                       "WeightedAverageNumberOfDilutedSharesOutstandingBasicAndDiluted",
                       "WeightedAverageNumberOfSharesOutstandingBasic",
                       "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
                       "AdjustedWeightedAverageShares", "WeightedAverageShares"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "assets": ["Assets"],
}
FLOW = {"revenue", "diluted_shares", "cfo"}


def cik_map():
    p = pathlib.Path(r"C:\projects\Karst\data\sec\company_tickers.json")
    j = json.loads(p.read_text())
    if isinstance(j, dict) and j and isinstance(next(iter(j.values())), str):
        return {k.upper(): str(v).zfill(10) for k, v in j.items()}
    rows = j.values() if isinstance(j, dict) else j
    return {r["ticker"].upper(): str(r["cik_str"]).zfill(10) for r in rows}


def companyfacts(cik):
    f = CACHE / f"CIK{cik}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8")
    f.write_text(body, encoding="utf-8")
    time.sleep(0.4)
    return json.loads(body)


def collect(facts):
    """→ DataFrame(field, start, end, filed, val, dur)"""
    rows = []
    for field, tags in TAGS.items():
        for tax in ("us-gaap", "ifrs-full"):
            blk = facts.get("facts", {}).get(tax, {})
            for pri, tag in enumerate(tags):
                if tag not in blk:
                    continue
                for unit, items in blk[tag]["units"].items():
                    if field == "diluted_shares" and unit != "shares":
                        continue
                    if field != "diluted_shares" and unit != "USD":
                        continue
                    for it in items:
                        if "filed" not in it or "end" not in it:
                            continue
                        if it.get("form", "").endswith("/A"):
                            continue
                        s = it.get("start")
                        dur = None
                        if s:
                            dur = (pd.Timestamp(it["end"]) - pd.Timestamp(s)).days
                        rows.append(dict(field=field, tag=tag, pri=pri, start=s,
                                         end=it["end"], filed=it["filed"],
                                         val=it["val"], dur=dur))
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for c in ("start", "end", "filed"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def build_panel(df, months):
    """逐月底取 filed<=m 的值。存量取 end 最近;流量 TTM 取最近四季(80–100 日跨度)。"""
    out = []
    for m in months:
        vis = df[df.filed <= m]
        rec = {"month_end": m}
        for field in TAGS:
            v = vis[vis.field == field]
            if v.empty:
                rec[field] = np.nan
                rec[field + "_ttm"] = np.nan
                continue
            if field in FLOW:
                q = v[(v.dur >= 80) & (v.dur <= 100)]
                a = v[(v.dur >= 330) & (v.dur <= 400)]
                if q.empty and a.empty:
                    rec[field] = np.nan
                    rec[field + "_ttm"] = np.nan
                    rec[field + "_ttm_basis"] = "insufficient"
                    continue
                ttm, basis = np.nan, "insufficient"
                if not q.empty:
                    q = q.sort_values(["end", "pri", "filed"]).drop_duplicates("end", keep="first")
                    q = q.sort_values("end")
                    rec[field] = float(q.iloc[-1]["val"])
                    last4 = q.tail(4)
                    span = (last4.iloc[-1]["end"] - last4.iloc[0]["start"]).days if len(last4) == 4 else None
                    if span and 350 <= span <= 380:
                        ttm, basis = float(last4["val"].sum()), "four_quarters"
                else:
                    rec[field] = np.nan
                if basis == "insufficient" and not a.empty:
                    # 面板 RULES 第六節 annual_only:只有全年數,直接當滾動和,並標明基礎
                    a = a.sort_values(["end", "pri", "filed"]).drop_duplicates("end", keep="first")
                    ttm, basis = float(a.sort_values("end").iloc[-1]["val"]), "annual_only"
                    if not np.isfinite(rec.get(field, np.nan)):
                        rec[field] = np.nan
                rec[field + "_ttm"] = ttm
                rec[field + "_ttm_basis"] = basis
            else:
                s = v.sort_values(["end", "pri", "filed"]).drop_duplicates("end", keep="first")
                rec[field] = float(s.sort_values("end").iloc[-1]["val"])
                rec[field + "_ttm"] = np.nan
        out.append(rec)
    return pd.DataFrame(out)


def main():
    import yfinance as yf
    cm = cik_map()
    px = yf.download(COUNTEREXAMPLES, start="2004-01-01", end="2026-09-02",
                     auto_adjust=True, progress=False)["Close"]
    px = px.dropna(how="all")
    px.to_parquet(DATA / "counterexample_close.parquet")
    print("價格", px.shape, px.index.min(), px.index.max())

    # 拆股表:反例多有反向拆股,價格已還原而申報股數未還原,算市值前必須對齊
    sp = []
    for t in COUNTEREXAMPLES:
        try:
            ss = yf.Ticker(t).splits
            for d, r in ss.items():
                sp.append({"symbol": t, "report_date": pd.Timestamp(d).tz_localize(None),
                           "ratio": float(r)})
        except Exception as e:
            print("splits 失敗", t, e)
    pd.DataFrame(sp).to_parquet(DATA / "counterexample_splits.parquet", index=False)
    print("拆股筆數", len(sp))

    idx = px.index
    s = pd.Series(idx, index=idx)
    months = pd.DatetimeIndex(sorted(s.groupby([idx.year, idx.month]).max().values))

    panels, notes = [], {}
    for t in COUNTEREXAMPLES:
        cik = cm.get(t)
        if not cik:
            notes[t] = "無 CIK"
            continue
        try:
            facts = companyfacts(cik)
        except Exception as e:
            notes[t] = f"companyfacts 失敗:{e}"
            continue
        df = collect(facts)
        if df.empty:
            notes[t] = "無可用 XBRL 標籤"
            continue
        first = px[t].first_valid_index()
        mm = months[(months >= first) & (months <= idx.max())]
        p = build_panel(df, mm)
        p["ticker"] = t
        p["cik"] = cik
        panels.append(p)
        notes[t] = f"CIK {cik},{len(p)} 個月,首個有價月 {first.date()}"
        print(t, notes[t])

    pan = pd.concat(panels, ignore_index=True)
    pan.to_parquet(DATA / "counterexample_panel.parquet", index=False)
    notes["__delisted_no_price__"] = DELISTED_NO_PRICE
    json.dump(notes, open(OUT / "counterexample_notes.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("面板", pan.shape)


if __name__ == "__main__":
    main()
