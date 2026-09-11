# -*- coding: utf-8 -*-
"""KARST-218 第三部:補「去年同季」那一格的三個財年第四季(全年 − 前三季)。只印,不寫檔。"""
from __future__ import annotations

import part3_fill as pf

REV = pf.REV

for label, cik, fy_s, q3_e, fy_e in [
    ("MSFT FQ4 FY2021(2021-06-30)", "0000789019", "2020-07-01", "2021-03-31", "2021-06-30"),
    ("AAPL FQ4 FY2024(2024-09-28)", "0000320193", "2023-10-01", "2024-06-29", "2024-09-28"),
    ("KO Q4 2022(2022-12-31)", "0000021344", "2022-01-01", "2022-09-30", "2022-12-31"),
]:
    df = pf.facts(cik)
    _, full = pf.tag_of(df, REV, fy_s, fy_e)
    _, nine = pf.tag_of(df, REV, fy_s, q3_e)
    if full is None or nine is None:
        print(f"  {label}: 查不到")
        continue
    print(f"  {label}: 全年 {round(full/1e9,2)}B − 前三季 {round(nine/1e9,2)}B"
          f" = 第四季 {round((full-nine)/1e9,2)}B")
