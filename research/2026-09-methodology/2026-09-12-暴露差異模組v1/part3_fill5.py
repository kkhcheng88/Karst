# -*- coding: utf-8 -*-
"""KARST-218 第三部:最後三格財年第四季(MDLZ 2023/2022、DUOL 2022)。只印,不寫檔。"""
from __future__ import annotations

import part3_fill as pf

REV = pf.REV

for label, cik, fy_s, q3_e, fy_e in [
    ("MDLZ Q4 2023(2023-12-31)", "0001103982", "2023-01-01", "2023-09-30", "2023-12-31"),
    ("MDLZ Q4 2022(2022-12-31)", "0001103982", "2022-01-01", "2022-09-30", "2022-12-31"),
    ("DUOL Q4 2022(2022-12-31)", "0001562088", "2022-01-01", "2022-09-30", "2022-12-31"),
]:
    df = pf.facts(cik)
    _, full = pf.tag_of(df, REV, fy_s, fy_e)
    _, nine = pf.tag_of(df, REV, fy_s, q3_e)
    if full is None or nine is None:
        print(f"  {label}: 查不到")
        continue
    print(f"  {label}: 全年 {round(full/1e9,4)}B − 前三季 {round(nine/1e9,4)}B"
          f" = 第四季 {round((full-nine)/1e9,4)}B")
