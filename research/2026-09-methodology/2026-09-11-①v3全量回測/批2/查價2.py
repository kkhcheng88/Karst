# -*- coding: utf-8 -*-
"""KARST-213 批 2:日線檔結構診斷(欄位、series_role、調整痕跡)。

用法:python 查價2.py <TICKER>
"""
import glob
import sys

import pandas as pd

PRICES = "C:/projects/Karst/data/prices/daily/part_*.parquet"


def main():
    tk = sys.argv[1]
    for f in glob.glob(PRICES):
        d = pd.read_parquet(f)
        if tk not in set(d["ticker"].astype(str)):
            continue
        d = d[d["ticker"] == tk]
        print("file", f, "rows", len(d), "cols", list(d.columns))
        print("series_role:", d["series_role"].value_counts().to_dict())
        d["date"] = pd.to_datetime(d["date"])
        for role in d["series_role"].unique():
            s = d[d["series_role"] == role].sort_values("date")
            print("--", role, s["date"].min().date(), "->", s["date"].max().date())
            for dt in ["2016-11-08", "2023-03-08", "2025-01-24"]:
                m = s[s["date"] == dt]
                if len(m):
                    print("   ", dt, m[["close"] + [c for c in s.columns
                          if c not in ("close", "date", "entity_id", "ticker", "series_role")][:6]]
                          .to_dict("records"))
        break


if __name__ == "__main__":
    main()
