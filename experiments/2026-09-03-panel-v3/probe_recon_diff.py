# -*- coding: utf-8 -*-
"""KARST-172:對帳差異最大那幾格,面板 v3 到底放了什麼(唯讀)。"""
from __future__ import annotations

import pathlib

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
CASES = [("0000040545", "2015-12-31", "revenue"),
         ("0000202058", "2011-07-01", "revenue"),
         ("0000040545", "2011-12-31", "revenue"),
         ("0001045810", "2010-01-31", "net_income"),
         ("0001442145", "2018-06-30", "operating_cash_flow"),
         ("0000055785", "2012-12-31", "lt_debt")]


def main() -> None:
    p = pd.read_parquet(REPO / "data" / "panel" / "quarterly_v3.parquet")
    for cik, pe, f in CASES:
        r = p[(p["entity_id"] == cik) & (p["period_end"] == pd.Timestamp(pe))]
        if r.empty:
            print(cik, pe, f, "沒有這一列")
            continue
        r = r.iloc[0]
        cols = [f, f"{f}_tag", f"{f}_scope", f"{f}_unit", f"{f}_filed"]
        if f"{f}_period" in p.columns:
            cols.append(f"{f}_period")
        if f"{f}_restated" in p.columns:
            cols.append(f"{f}_restated")
        print(cik, pe, {c: r[c] for c in cols})
    print("--- 同一實體同一期是否有多條可選(以 GE 2015 為例)---")
    ge = p[(p["entity_id"] == "0000040545")].sort_values("period_end")
    print(ge[["period_end", "revenue", "revenue_period", "revenue_tag"]].tail(60).to_string(index=False))


if __name__ == "__main__":
    main()
