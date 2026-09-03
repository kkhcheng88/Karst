# -*- coding: utf-8 -*-
"""KARST-172:逐欄 missing_reason 分佈(唯讀)。"""
from __future__ import annotations

import pathlib

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
FIELDS = ["cash_and_equivalents", "short_term_investments", "lt_debt", "st_debt",
          "total_debt", "liabilities", "assets", "equity", "revenue",
          "operating_cash_flow", "net_income", "shares_outstanding"]


def main() -> None:
    p = pd.read_parquet(REPO / "data" / "panel" / "quarterly_v3.parquet")
    rows = []
    for f in FIELDS:
        vc = p[f"{f}_missing_reason"].fillna("").value_counts()
        rows.append({"欄": f, **{k: int(v) for k, v in vc.items()}})
    out = pd.DataFrame(rows).fillna(0).astype({c: int for c in
                                               set().union(*[set(r) for r in rows]) - {"欄"}})
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
