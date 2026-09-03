# -*- coding: utf-8 -*-
"""KARST-172:對帳差異按「v3 那格的期間長度」分類,看差異是否集中在財年末(唯讀)。"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
HERE = pathlib.Path(__file__).resolve().parent
V2 = REPO / "experiments" / "2026-09-02-panel-scale-fix" / "out" / "panel_monthly_v2.parquet"
PAIRS = {"revenue": "revenue", "net_income": "net_income", "cfo": "operating_cash_flow"}


def main() -> None:
    rep = json.loads((HERE / "out" / "coverage_report.json").read_text(encoding="utf-8"))
    sample = rep["reconcile"]["sample_entities"]
    p = pd.read_parquet(REPO / "data" / "panel" / "quarterly_v3.parquet")
    v3 = p[p["entity_id"].isin(sample) & p["period_end"].notna()]
    v2 = pd.read_parquet(V2)
    v2["entity_id"] = v2["cik"].astype(str).str.zfill(10)
    for v2f, v3f in PAIRS.items():
        endcol = f"{v2f}_end"
        sub = v2[v2["entity_id"].isin(sample) & v2[v2f].notna() & v2[endcol].notna()]
        sub = sub.drop_duplicates(subset=["entity_id", endcol]).copy()
        sub[endcol] = pd.to_datetime(sub[endcol])
        right = v3[["entity_id", "period_end", v3f, f"{v3f}_period"]].rename(
            columns={v3f: "v3_val", f"{v3f}_period": "v3_span"})
        left = sub[["entity_id", endcol, v2f]].rename(columns={v2f: "v2_val"})
        m = left.merge(right, left_on=["entity_id", endcol],
                       right_on=["entity_id", "period_end"], how="inner")
        m = m[m["v3_val"].notna()]
        rel = ((m["v2_val"] - m["v3_val"]).abs()
               / m[["v2_val", "v3_val"]].abs().max(axis=1).clip(lower=1.0))
        d = m[rel >= 1e-6]
        print(f"{v2f}:比對 {len(m)},不同 {len(d)}")
        print("  不同的按 v3 期間長度:", d["v3_span"].value_counts().to_dict())
        print("  全部的按 v3 期間長度:", m["v3_span"].value_counts().to_dict())
        if len(d):
            fy_end = d[endcol].dt.month.value_counts().head(3).to_dict()
            print("  不同的按月份(頭三):", {int(k): int(v) for k, v in fy_end.items()})


if __name__ == "__main__":
    main()
