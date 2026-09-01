# -*- coding: utf-8 -*-
"""KARST-146 step 8: audit the finished panel against its own rules.

The one thing this panel exists to guarantee is that no cell was knowable
later than its month end. That claim is worth nothing unless it is checked on
every cell, so this checks every cell.

Run:  PYTHONUTF8=1 python validate_panel.py
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"

FIELDS = ["revenue", "gross_profit", "net_income", "diluted_shares", "cfo",
          "capex", "assets", "liabilities", "equity", "cash", "lt_debt"]


def main() -> None:
    panel = pd.read_parquet(OUT / "panel_monthly.parquet")
    res: dict = {"panel_rows": int(len(panel)),
                 "tickers": int(panel.ticker.nunique()),
                 "month_end_min": str(panel.month_end.min().date()),
                 "month_end_max": str(panel.month_end.max().date())}

    # 1. no cell may carry a filing date later than its month end
    violations = {}
    for f in FIELDS:
        col = f"{f}_filed"
        if col not in panel.columns:
            continue
        sub = panel[panel[col].notna()]
        bad = (pd.to_datetime(sub[col]) > sub.month_end).sum()
        violations[f] = int(bad)
    res["look_ahead_violations"] = violations
    res["look_ahead_total"] = int(sum(violations.values()))

    # 2. the period end must never be after the filing date either
    end_after_filed = {}
    for f in FIELDS:
        ce, cf = f"{f}_end", f"{f}_filed"
        if ce not in panel.columns:
            continue
        sub = panel[panel[ce].notna() & panel[cf].notna()]
        end_after_filed[f] = int((pd.to_datetime(sub[ce])
                                  > pd.to_datetime(sub[cf])).sum())
    res["period_end_after_filing"] = end_after_filed

    # 3. how stale is the data in practice
    stale = {}
    for f in FIELDS:
        c = f"{f}_age_days"
        if c in panel.columns:
            s = panel[c].dropna()
            stale[f] = dict(median=int(s.median()), p90=int(s.quantile(0.9)),
                            max=int(s.max()))
    res["age_days"] = stale

    # 4. restatement rate: how often the first version was later revised
    restated = {}
    for f in FIELDS:
        c = f"{f}_was_restated"
        if c in panel.columns:
            restated[f] = round(float(panel[c].fillna(False).mean()), 4)
    res["share_of_cells_later_restated"] = restated

    # 5. panel span per company
    span = panel.groupby("ticker").month_end.agg(["min", "max", "count"])
    res["months_per_ticker"] = dict(
        median=int(span["count"].median()), min=int(span["count"].min()),
        max=int(span["count"].max()))
    res["tickers_with_full_history"] = int((span["count"] >= 200).sum())

    # 6. index membership
    res["rows_while_in_index"] = int(panel.in_index.sum())
    res["tickers_ever_in_index_in_panel"] = int(
        panel.loc[panel.in_index, "ticker"].nunique())

    (OUT / "validation.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
