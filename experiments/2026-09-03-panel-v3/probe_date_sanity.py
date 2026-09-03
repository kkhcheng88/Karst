# -*- coding: utf-8 -*-
"""KARST-172:期末日超出常理的列有幾多(唯讀,只數不改)。"""
from __future__ import annotations

import pathlib

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")


def main() -> None:
    p = pd.read_parquet(REPO / "data" / "panel" / "quarterly_v3.parquet")
    real = p[p["period_end"].notna()]
    today = pd.Timestamp("2026-09-03")
    future = real[real["period_end"] > today]
    old = real[real["period_end"] < pd.Timestamp("1990-01-01")]
    print("期末在今日之後的列:", len(future), "實體", future["entity_id"].nunique())
    print(future[["entity_id", "period_end", "filed_date"]].head(10).to_string(index=False))
    print("期末早於 1990 的列:", len(old), "實體", old["entity_id"].nunique())
    print(old[["entity_id", "period_end", "filed_date"]].head(10).to_string(index=False))
    neg = real[(real["filed_date"] - real["period_end"]).dt.days < 0]
    print("申報日早於期末的列:", len(neg), "實體", neg["entity_id"].nunique())


if __name__ == "__main__":
    main()
