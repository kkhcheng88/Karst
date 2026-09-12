# -*- coding: utf-8 -*-
"""檢查 v1.2 排除旗標的取值分佈與定義一致性(population 級)。"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
df = pd.read_parquet(HERE / "cache" / "population_improvement.parquet")
print("總列:", len(df))
print("signal_rev_in_text 值分佈:",
      df["signal_rev_in_text"].value_counts(dropna=False).to_dict())
for c in ("excl_no_text", "excl_intraday", "excl_earlier_release", "excl_hist_not_public",
          "excl_applicability", "excl_financial_sic"):
    print(c, df[c].value_counts(dropna=False).to_dict())
nu = df[(df["in_universe"] == 1) & (df["in_pool_window"]) & (df["pass_thr"] == True)]  # noqa: E712
print("候選(過門檻且同業正):", len(nu))
print("候選中 excl_no_text=1:", int(nu["excl_no_text"].sum()))
print("非候選中 excl_no_text=1:", int(df.loc[df.index.difference(nu.index), "excl_no_text"].sum()))
print("入口池:", int(df["entry_pool"].sum()))
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
