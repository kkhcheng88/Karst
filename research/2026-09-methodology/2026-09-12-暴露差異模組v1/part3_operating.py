# -*- coding: utf-8 -*-
"""KARST-218 第三部:由 `data/sec/companyfacts` 取十一家衝擊前後八季的財務骨幹。

**只讀 `data/sec/`,不寫任何既有目錄**;輸出落本票 `out/`。

口徑:
  - 單季損益 = 事實表裡時長 80–100 日、期末落在該季的 facts(優先次序見 REV_TAGS)。
  - 單季經營現金流 = 同年累計值相減(現金流量表只報累計);第一季直接取 80–100 日的值。
  - 期間按申報的實際期末日排,不按日曆季(公司財年各異)。
  - 「衝擊前四季」= 期末日早於衝擊起日的最後四季;「衝擊後四季」= 期末日晚於衝擊起日的首四季。
"""
from __future__ import annotations

import gzip
import json
from datetime import date

import pandas as pd

ROOT = "C:/projects/Karst"
HERE = f"{ROOT}/research/2026-09-methodology/2026-09-12-暴露差異模組v1"

TARGETS = [
    ("E01", "T", "0000732717", "2013-05-21"),
    ("E01", "SPG", "0001063761", "2013-05-21"),
    ("E01", "ED", "0001047862", "2013-05-21"),
    ("E06", "RMD", "0000943819", "2023-10-03"),
    ("E06", "KO", "0000021344", "2023-10-03"),
    ("E06", "MDLZ", "0001103982", "2023-10-03"),
    ("E07", "MU", "0000723125", "2025-01-24"),
    ("E08", "AAPL", "0000320193", "2025-04-02"),
    ("E12", "SWKS", "0000004127", "2019-05-17"),
    ("E13", "MSFT", "0000789019", "2022-01-03"),
    ("E14", "DUOL", "0001562088", "2023-05-01"),
]

REV_TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "RegulatedAndUnregulatedOperatingRevenue"]
GP_TAGS = ["GrossProfit"]
OI_TAGS = ["OperatingIncomeLoss"]
NI_TAGS = ["NetIncomeLoss", "ProfitLoss"]
OCF_TAGS = ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]
DA_TAGS = ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet"]


def load(cik):
    with gzip.open(f"{ROOT}/data/sec/companyfacts/CIK{cik}.json.gz", "rt", encoding="utf-8") as f:
        return json.load(f)


def facts(df, tag):
    node = df.get("facts", {}).get("us-gaap", {}).get(tag)
    if not node:
        return []
    out = []
    for unit, rows in node.get("units", {}).items():
        if unit != "USD":
            continue
        out += rows
    return out


def daily(rows, end, lo=80, hi=100):
    """時長 80–100 日、期末等於 end 的事實;同一期末取最後申報的那份。"""
    cand = []
    for r in rows:
        if r.get("end") != end:
            continue
        st = r.get("start")
        if not st:
            continue
        d = (date.fromisoformat(r["end"]) - date.fromisoformat(st)).days
        if lo <= d <= hi:
            cand.append(r)
    if not cand:
        return None
    cand.sort(key=lambda r: (r.get("filed", ""), r.get("accn", "")))
    return cand[-1].get("val")


def ytd(rows, end):
    """最近一年內、期末等於 end 的累計值(期長最貼近財年第一日起)。"""
    cand = []
    for r in rows:
        if r.get("end") != end or not r.get("start"):
            continue
        d = (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days
        if 80 <= d <= 400:
            cand.append((d, r))
    if not cand:
        return None
    cand.sort(key=lambda x: (x[0], x[1].get("filed", "")))
    return cand[-1][1].get("val")


def first_of(df, tag_list, end, fn):
    """按科目優先次序取第一個有值的(公司各年用不同 tag)。"""
    for t in tag_list:
        v = fn(facts(df, t), end)
        if v is not None:
            return t, v
    return None, None


def quarter_row(df, end):
    out = {}
    for name, lst in (("revenue", REV_TAGS), ("gross_profit", GP_TAGS),
                      ("operating_income", OI_TAGS), ("net_income", NI_TAGS)):
        tag, v = first_of(df, lst, end, daily)
        out[name] = v
        out[name + "_tag"] = tag
    return out


def periods(df):
    """所有出現過單季損益的期末日,由申報日排。"""
    ends = {}
    for t in REV_TAGS:
        for r in facts(df, t):
            if r.get("end") and r.get("start"):
                d = (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days
                if 80 <= d <= 100:
                    ends[r["end"]] = max(ends.get(r["end"], ""), r.get("filed", ""))
    return sorted(ends)


def main():
    rows = []
    for ev, tk, cik, shock in TARGETS:
        df = load(cik)
        ps = periods(df)
        pre = [p for p in ps if p < shock][-4:]
        post = [p for p in ps if p > shock][:4]
        ocf_rows = {t: facts(df, t) for t in OCF_TAGS}
        ocftag, _ = first_of(OCF_TAGS, None, lambda r, e: next(
            (x for x in r if x), None)) if False else (None, None)
        # 單季經營現金流:同年累計相減
        ytd_by_end = {}
        for t in OCF_TAGS:
            for r in facts(df, t):
                if not r.get("start") or not r.get("end"):
                    continue
                d = (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days
                if 80 <= d <= 400:
                    k = (r["start"], r["end"])
                    if k not in ytd_by_end or r.get("filed", "") > ytd_by_end[k][1].get("filed", ""):
                        ytd_by_end[k] = (t, r)
        for side, ends in (("衝擊前", pre), ("衝擊後", post)):
            for p in ends:
                r = quarter_row(df, p)
                # 同一財年、上一個期末的累計
                cand = [(k, v) for k, v in ytd_by_end.items()
                        if k[1] == p and k[0] <= p]
                cand.sort(key=lambda x: x[0][0])
                ocf = None
                if cand:
                    st, rr = cand[-1]
                    base = [(k, v) for k, v in ytd_by_end.items()
                            if k[1] < p and k[0] == st]
                    base.sort(key=lambda x: x[0][1])
                    if base:
                        ocf = rr[1].get("val") - base[-1][1][1].get("val")
                    else:
                        ocf = rr[1].get("val")
                rows.append(dict(event_id=ev, ticker=tk, 期間=side, 期末=p,
                                 期間長度日="", 收入=r["revenue"], 收入科目=r["revenue_tag"],
                                 毛利=r["gross_profit"], 營業利潤=r["operating_income"],
                                 淨利=r["net_income"], 單季經營現金流=ocf))
    d = pd.DataFrame(rows)
    d.to_csv(f"{HERE}/out/part3_財務骨幹.csv", index=False, encoding="utf-8-sig")
    print(d.to_string(index=False, max_colwidth=18))


if __name__ == "__main__":
    main()
