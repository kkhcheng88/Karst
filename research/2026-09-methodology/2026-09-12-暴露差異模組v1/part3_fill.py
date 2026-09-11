# -*- coding: utf-8 -*-
"""KARST-218 第三部:補幾格 XBRL 缺季(財年第四季通常只有年度事實)。

缺季的單季值 = 同財年累計(全年)− 同財年累計(前三季)。只印,不寫檔。
"""
from __future__ import annotations

import glob
import gzip
import json
import re
from datetime import date

ROOT = "C:/projects/Karst"
HERE = f"{ROOT}/research/2026-09-methodology/2026-09-12-暴露差異模組v1"
REV = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"]


def facts(cik):
    with gzip.open(f"{ROOT}/data/sec/companyfacts/CIK{cik}.json.gz", "rt", encoding="utf-8") as f:
        return json.load(f)


def ytd(df, tag, start, end):
    node = df.get("facts", {}).get("us-gaap", {}).get(tag)
    if not node:
        return None
    best = None
    for unit, rows in node.get("units", {}).items():
        if unit != "USD":
            continue
        for r in rows:
            if r.get("start") == start and r.get("end") == end:
                if best is None or r.get("filed", "") > best.get("filed", ""):
                    best = r
    return best["val"] if best else None


def tag_of(df, cands, start, end):
    for t in cands:
        v = ytd(df, t, start, end)
        if v is not None:
            return t, v
    return None, None


def show(label, cik, cands, fy_start, y9_end, fy_end):
    df = facts(cik)
    t, full = tag_of(df, cands, fy_start, fy_end)
    _, nine = tag_of(df, cands, fy_start, y9_end)
    if full is None or nine is None:
        print(f"  {label}: 查不到(start={fy_start} end={fy_end})")
        return
    print(f"  {label}: {t}  全年 {round(full/1e9,2)}B − 前三季 {round(nine/1e9,2)}B"
          f" = 第四季 {round((full-nine)/1e9,2)}B")


print("== 補季 ==")
show("MSFT FQ4 FY2022(2022-06-30)", "0000789019", REV,
     "2021-07-01", "2022-03-31", "2022-06-30")
show("AAPL FQ4 FY2025(2025-09-27)", "0000320193", REV,
     "2024-09-29", "2025-06-28", "2025-09-27")
show("KO Q4 2023(2023-12-31)", "0000021344", REV,
     "2023-01-01", "2023-09-29", "2023-12-31")

print("== 業績稿原文核句 ==")
for pat, stems in [
    (r"[^.]{0,70}Paid Subscribers[^.]{0,80}\.",
     ["E14_DUOL_ER_2023-08-08", "E14_DUOL_ER_2023-11-08", "E14_DUOL_ER_2024-02-28",
      "E14_DUOL_ER_2024-05-08"]),
]:
    for stem in stems:
        for f in glob.glob(f"{HERE}/docs/part3/{stem}*.txt"):
            t2 = re.sub(r"\s+", " ", open(f, encoding="utf-8", errors="ignore").read())
            hits = [h.strip() for h in re.findall(pat, t2)]
            print(" ", f.split("/")[-1][:22], "|", (hits[0][:160] if hits else "—"))
