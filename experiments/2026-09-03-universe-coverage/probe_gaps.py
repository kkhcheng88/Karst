# -*- coding: utf-8 -*-
"""KARST-173:看清楚哪些十倍股算不出、為什麼(唯讀,不改判準)。"""
from __future__ import annotations

import pandas as pd

import common as C


def main() -> None:
    d = pd.read_csv(C.OUT / "tenbagger_t0_v3.csv")
    d["t0"] = pd.to_datetime(d["t0"])
    print("=== 接不回實體的 9 家 ===")
    print(d.loc[d["mcap_missing_reason"] == "entity_unmatched",
                ["ticker", "t0", "match_note", "宇宙分段"]].to_string(index=False))
    print("\n=== 有面板但無股數(16 家)===")
    m = d[(d["has_panel_at_t0"] == True) & (d["mcap"].isna())]
    print(m[["ticker", "t0", "mcap_missing_reason", "panel_filed_date"]].to_string(index=False))
    print("\n=== 接得回實體但 t0 之前無面板(45 家)按年 ===")
    n = d[(d["entity_id"].notna()) & (d["has_panel_at_t0"] != True)]
    print(n["t0"].dt.year.value_counts().sort_index().to_string())
    print(n.loc[n["t0"].dt.year.isin([2011, 2014, 2016, 2017, 2020, 2021]),
                ["ticker", "t0", "entity_id"]].to_string(index=False))
    print("\n=== 有市值那 68 家的市值分佈(百萬美元)===")
    k = d[d["mcap"].notna()].sort_values("mcap")
    print((k[["ticker", "t0", "mcap", "currency", "in_index", "n1", "n2"]]
           .assign(mcap=lambda x: (x["mcap"] / 1e6).round(1)).to_string(index=False)))
    print("\n=== 新舊倍數對照(交叉核對)===")
    c = d[d["multiple_new"].notna()]
    rel = (c["multiple_new"] - c["multiple_old"]).abs() / c["multiple_old"]
    print("家數", len(c), "相對差中位", round(float(rel.median()), 4),
          "差 >10% 的家數", int((rel > 0.10).sum()),
          "新算仍 >=10 倍的家數", int((c["multiple_new"] >= 10).sum()))
    print(c.loc[rel > 0.10, ["ticker", "t0", "multiple_old", "multiple_new"]]
          .head(15).to_string(index=False))


if __name__ == "__main__":
    main()
