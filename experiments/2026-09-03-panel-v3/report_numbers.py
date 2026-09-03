# -*- coding: utf-8 -*-
"""KARST-172:報告要用的餘下數字(貨幣分佈、外國申報人對本土、對帳差異的樣子)。唯讀。"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
HERE = pathlib.Path(__file__).resolve().parent


def main() -> None:
    p = pd.read_parquet(REPO / "data" / "panel" / "quarterly_v3.parquet")
    real = p[p["period_end"].notna()]
    latest = real.sort_values("period_end").groupby("entity_id").tail(1)
    print("=== 貨幣(以列計)===")
    print(real["currency"].value_counts().head(10).to_string())
    print("非 USD 的實體數:",
          int(latest.loc[latest["currency"].ne("USD") & latest["currency"].ne(""),
                         "entity_id"].nunique()))
    rep = json.loads((HERE / "out" / "coverage_report.json").read_text(encoding="utf-8"))
    print("=== 外國申報人 vs 本土(最新一列)===")
    for k in ("foreign_filer", "domestic_filer"):
        c = rep["coverage"][k]
        print(k, "實體", c["entities"], "四核心齊", c["core_four"],
              {f: c["fields"][f] for f in
               ("cash_and_equivalents", "total_debt", "liabilities", "revenue",
                "shares_outstanding")})
    print("=== 重述比例(有值的格之中,日後被改過的)===")
    print(json.dumps(rep["coverage"]["restated_share"], ensure_ascii=False))
    print("=== 對帳差異樣本 ===")
    for r in rep["reconcile"]["by_field"]:
        if r["different"]:
            print(r["field_v2"], "最大三個:", r["worst"])
    print("=== 期間長度分佈 ===")
    for f in ("revenue", "operating_cash_flow", "net_income"):
        print(f, real[f"{f}_period"].value_counts().to_dict())
    print("=== 日期範圍 ===")
    print("period_end", str(real["period_end"].min().date()), "至",
          str(real["period_end"].max().date()))
    print("filed_date", str(real["filed_date"].min().date()), "至",
          str(real["filed_date"].max().date()))
    lag = (real["filed_date"] - real["period_end"]).dt.days
    print("申報滯後日數 中位", float(lag.median()), "九十分位", float(lag.quantile(0.9)))
    print("每個實體的期數 中位", float(real.groupby("entity_id").size().median()))


if __name__ == "__main__":
    main()
