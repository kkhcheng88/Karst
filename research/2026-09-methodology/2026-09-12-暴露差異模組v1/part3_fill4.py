# -*- coding: utf-8 -*-
"""KARST-218 第三部:補齊「衝擊後四季」窗內其餘財年第四季。只印,不寫檔。"""
from __future__ import annotations

import part3_fill as pf

REV = pf.REV

for label, cik, fy_s, q3_e, fy_e in [
    ("ED Q4 2013(2013-12-31)", "0001047862", "2013-01-01", "2013-09-30", "2013-12-31"),
    ("RMD FQ4 FY2024(2024-06-30)", "0000943819", "2023-07-01", "2024-03-31", "2024-06-30"),
    ("RMD FQ4 FY2023(2023-06-30)", "0000943819", "2022-07-01", "2023-03-31", "2023-06-30"),
    ("MDLZ Q4 2024(2024-12-31)", "0001103982", "2024-01-01", "2024-09-30", "2024-12-31"),
    ("DUOL Q4 2023(2023-12-31)", "0001562088", "2023-01-01", "2023-09-30", "2023-12-31"),
    ("ED Q4 2012(2012-12-31)", "0001047862", "2012-01-01", "2012-09-30", "2012-12-31"),
]:
    df = pf.facts(cik)
    _, full = pf.tag_of(df, REV, fy_s, fy_e)
    _, nine = pf.tag_of(df, REV, fy_s, q3_e)
    if full is None or nine is None:
        print(f"  {label}: 查不到")
        continue
    print(f"  {label}: 全年 {round(full/1e9,3)}B − 前三季 {round(nine/1e9,3)}B"
          f" = 第四季 {round((full-nine)/1e9,3)}B")
