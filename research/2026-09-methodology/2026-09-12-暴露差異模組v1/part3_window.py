# -*- coding: utf-8 -*-
"""KARST-218 第三部:把「衝擊後四季」這一格釘死——逐家列出衝擊日之後最近四季的期末、收入、按年。

前版表內若干收入按年引錯了窗(多列了一季、漏了財年第四季),且首版本腳本的「去年同季」取錯方向
(取了期末在海後 365 日的那一季)。本版:
  - 窗 = [衝擊日, 衝擊日+400 日],取其中最早四季;
  - 去年同季 = 期末早於本季、相差 350–380 日的那一季;
  - 財年第四季在 XBRL 無單季事實,由 part3_fill.py 的「全年 − 前三季」補(`FILL`)。
輸出 `out/part3_衝擊後四季.csv`。
"""
from __future__ import annotations

import csv
from datetime import date, timedelta

import part3_fill as pf

HERE = pf.HERE
REV = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
       "RevenueFromContractWithCustomerIncludingAssessedTax",
       "RegulatedAndUnregulatedOperatingRevenue"]

CASES = [
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

FILL = {  # (CIK, 期末) -> 單季收入;來源「全年 − 前三季」(part3_fill.py/fill3/fill4),並核過業績稿
    ("0000789019", "2022-06-30"): 51.87e9,
    ("0000789019", "2021-06-30"): 46.15e9,
    ("0000320193", "2025-09-27"): 102.47e9,
    ("0000320193", "2024-09-28"): 94.93e9,
    ("0000021344", "2023-12-31"): 10.85e9,
    ("0000021344", "2022-12-31"): 10.12e9,
    ("0001047862", "2013-12-31"): 2.867e9,
    ("0001047862", "2012-12-31"): 2.901e9,
    ("0000943819", "2024-06-30"): 1.223e9,
    ("0000943819", "2023-06-30"): 1.122e9,
    ("0001103982", "2024-12-31"): 9.604e9,
    ("0001103982", "2023-12-31"): 9.314e9,
    ("0001103982", "2022-12-31"): 8.695e9,
    ("0001562088", "2023-12-31"): 0.151e9,
    ("0001562088", "2022-12-31"): 0.1038e9,
}


def daily(df, tag):
    """(期末 -> 值) 只收時長 80–100 日的單季事實,同日取後申報者。"""
    node = df.get("facts", {}).get("us-gaap", {}).get(tag) or {}
    seen = {}
    for unit, rows in node.get("units", {}).items():
        if unit != "USD":
            continue
        for r in rows:
            s, e = r.get("start"), r.get("end")
            if not s or not e:
                continue
            if not 80 <= (date.fromisoformat(e) - date.fromisoformat(s)).days <= 100:
                continue
            if e not in seen or r.get("filed", "") > seen[e][1]:
                seen[e] = (r["val"], r.get("filed", ""))
    return {e: v for e, (v, _) in seen.items()}


def series(cik):
    """合併所有收入標籤;同一期末以先出現者為準(標籤優先次序照 REV)。"""
    df = pf.facts(cik)
    merged = {}
    for t in REV:
        for e, v in daily(df, t).items():
            merged.setdefault(e, v)
    for (c, e), v in FILL.items():
        if c == cik:
            merged[e] = v
    return merged


rows = []
print("== 衝擊後四季(重取;去年同季 = 期末早 350–380 日)==")
for ev, tk, cik, shock in CASES:
    s = date.fromisoformat(shock)
    end_win = s + timedelta(days=400)
    ser = series(cik)
    qs = [(e, v) for e, v in sorted(ser.items())
          if s <= date.fromisoformat(e) <= end_win][:4]
    # 去年同季也允許落在單季事實以外(FILL 已補),故直接查 ser 的期末
    line = []
    for e, v in qs:
        ed = date.fromisoformat(e)
        cand = [x for x in ser if 350 <= (ed - date.fromisoformat(x)).days <= 380]
        if cand:
            pv = ser[sorted(cand)[-1]]
            yoy = v / pv - 1
        else:
            pv, yoy = None, None
        line.append(f"{e} {v/1e9:.2f}B({'—' if yoy is None else f'{yoy*100:+.1f}%'})")
        rows.append(dict(event=ev, ticker=tk, 期末=e, 收入億=round(v / 1e8, 1),
                         去年同季_收入億=("" if pv is None else round(pv / 1e8, 1)),
                         收入_按年=("" if yoy is None else round(yoy, 4))))
    print(f"  {ev} {tk:5s} 起 {shock} | " + "  ".join(line))

with open(f"{HERE}/out/part3_衝擊後四季.csv", "w", encoding="utf-8", newline="") as g:
    w = csv.DictWriter(g, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("→ out/part3_衝擊後四季.csv", len(rows), "格")
