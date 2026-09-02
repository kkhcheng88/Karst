# -*- coding: utf-8 -*-
"""KARST-160:報告要引用的幾張小表,一次過印出來。"""
import os

import pandas as pd

OUT = r"C:\projects\Karst\experiments\2026-09-02-tenbagger-scan\out"

a = pd.read_csv(os.path.join(OUT, "base_rate_arms.csv"), encoding="utf-8-sig")
for arm in ["A_best_month_in_year", "B_january_only"]:
    for h in ["3y", "5y"]:
        d = a[(a.arm == arm) & (a.horizon == h)]
        print(arm, h,
              "| 十倍 中位", round(d["share_ge_10x"].median(), 4),
              "平均", round(d["share_ge_10x"].mean(), 4),
              "| 五倍 中位", round(d["share_ge_5x"].median(), 4),
              "平均", round(d["share_ge_5x"].mean(), 4),
              "| 三倍 中位", round(d["share_ge_3x"].median(), 4))
print()
d = a[(a.arm == "B_january_only")]
print(d.pivot(index="start_year", columns="horizon",
              values="share_ge_10x").to_string())
