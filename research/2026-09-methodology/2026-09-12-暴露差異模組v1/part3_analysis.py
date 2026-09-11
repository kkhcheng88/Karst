# -*- coding: utf-8 -*-
"""KARST-218 第三部:把十一家衝擊前後的季度骨幹做按年對比,供逐家人工核讀。

**只讀 `data/sec/companyfacts`,不寫任何既有目錄。** 輸出 `out/part3_按年對比.csv`。
口徑:同一家、期末相差 350–380 日的兩季視為同年同季;缺季(財年第四季通常只有年度事實)
不補值,原樣留空——缺季的單季數字由 `docs/part3/` 的業績稿人工補讀。
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

TAGS = {
    "收入": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
           "RevenueFromContractWithCustomerIncludingAssessedTax",
           "RegulatedAndUnregulatedOperatingRevenue"],
    "營業利潤": ["OperatingIncomeLoss"],
    "淨利": ["NetIncomeLoss", "ProfitLoss"],
    "毛利": ["GrossProfit"],
}


def facts(df, tag):
    node = df.get("facts", {}).get("us-gaap", {}).get(tag)
    if not node:
        return []
    out = []
    for unit, rows in node.get("units", {}).items():
        if unit == "USD":
            out += rows
    return out


def series(df, tag_list):
    """{期末: 單季值},同期末同日取最後申報。"""
    best = {}
    for t in tag_list:
        for r in facts(df, t):
            if not r.get("start") or not r.get("end"):
                continue
            dur = (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days
            if not (80 <= dur <= 100):
                continue
            k = r["end"]
            if k not in best or r.get("filed", "") > best[k][1].get("filed", ""):
                best[k] = (r.get("val"), r)
    return {k: v[0] for k, v in best.items()}


def yoy(ser, end):
    """同期去年的值(期末相差 350–380 日)。"""
    e = date.fromisoformat(end)
    for k, v in ser.items():
        d = (e - date.fromisoformat(k)).days
        if 350 <= d <= 380:
            return v
    return None


def main():
    rows = []
    for ev, tk, cik, shock in TARGETS:
        with gzip.open(f"{ROOT}/data/sec/companyfacts/CIK{cik}.json.gz", "rt", encoding="utf-8") as f:
            df = json.load(f)
        sers = {name: series(df, tl) for name, tl in TAGS.items()}
        ends = sorted(sers["收入"])
        for e in ends:
            r = dict(event_id=ev, ticker=tk, 期末=e,
                     期間=("衝擊後" if e > shock else "衝擊前"))
            for name in TAGS:
                v, p = sers[name].get(e), yoy(sers[name], e)
                r[name] = v
                r[name + "_去年同期"] = p
                r[name + "_按年"] = (round(v / p - 1, 4) if v is not None and p not in (None, 0)
                                    else None)
            if r["收入"]:
                r["營業利潤率"] = (round(r["營業利潤"] / r["收入"], 4)
                                  if r["營業利潤"] is not None else None)
                r["淨利率"] = (round(r["淨利"] / r["收入"], 4)
                              if r["淨利"] is not None else None)
            rows.append(r)
    d = pd.DataFrame(rows)
    keep = ["event_id", "ticker", "期間", "期末", "收入", "收入_按年", "毛利_按年",
            "營業利潤", "營業利潤_按年", "營業利潤率", "淨利", "淨利_按年", "淨利率"]
    d[keep].to_csv(f"{HERE}/out/part3_按年對比.csv", index=False, encoding="utf-8-sig")
    print(d[keep].to_string(index=False, max_colwidth=14))


if __name__ == "__main__":
    main()
