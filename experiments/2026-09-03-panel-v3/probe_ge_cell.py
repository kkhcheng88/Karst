# -*- coding: utf-8 -*-
"""KARST-172 事後核對:GE 2015-12-31 那一格,面板 v2 與 v3 各自放了什麼跨度(唯讀)。"""
from __future__ import annotations

import pathlib

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
V2 = REPO / "experiments" / "2026-09-02-panel-scale-fix" / "out" / "panel_monthly_v2.parquet"


def main() -> None:
    v2 = pd.read_parquet(V2)
    v2["entity_id"] = v2["cik"].astype(str).str.zfill(10)
    s = v2[(v2["entity_id"] == "0000040545")
           & (pd.to_datetime(v2["revenue_end"]) == pd.Timestamp("2015-12-31"))]
    cols = ["ticker", "month_end", "revenue", "revenue_period", "revenue_tag", "revenue_filed"]
    print(s[cols].drop_duplicates(subset=["revenue", "revenue_period"]).to_string(index=False))
    print("--- v2 逐格 revenue_period 分佈 ---")
    print(v2["revenue_period"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
