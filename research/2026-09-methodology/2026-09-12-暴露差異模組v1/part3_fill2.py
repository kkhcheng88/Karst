# -*- coding: utf-8 -*-
"""KARST-218 第三部:補算缺季的按年,並抽 DUOL 各季三項用戶數。只印,不寫檔。"""
from __future__ import annotations

import glob
import re

import part3_fill as pf  # 重用同一套取數

REV = pf.REV


def yoy(label, cik, s1, e1, s0, e0):
    df = pf.facts(cik)
    _, a = pf.tag_of(df, REV, s1, e1)
    _, b = pf.tag_of(df, REV, s0, e0)
    if a is None or b is None:
        print(f"  {label}: 查不到")
        return
    print(f"  {label}: {round(a/1e9,2)}B 對 {round(b/1e9,2)}B = {round(a/b-1, 4)*100:+.1f}%")


print("== 缺季按年 ==")
yoy("MSFT FQ4 FY22 對 FQ4 FY21", "0000789019",
    "2021-07-01", "2022-06-30", "2020-07-01", "2021-06-30")
yoy("AAPL FQ4 FY25 對 FQ4 FY24", "0000320193",
    "2024-09-29", "2025-09-27", "2023-10-01", "2024-09-28")
yoy("KO Q4 2023 對 Q4 2022", "0000021344",
    "2023-01-01", "2023-12-31", "2022-01-01", "2022-12-31")

print("== DUOL 各季「Paid Subscribers totaled」原句 ==")
for f in sorted(glob.glob(f"{pf.HERE}/docs/part3/E14_DUOL_ER_*.txt")):
    t = re.sub(r"\s+", " ", open(f, encoding="utf-8", errors="ignore").read())
    for m in re.findall(r"Paid Subscribers totaled [^;•]{0,70}", t)[:1]:
        print("  ", f.split("/")[-1][7:17], "|", m.strip())
