# -*- coding: utf-8 -*-
"""KARST-172:面板建法的小樣本試跑(不寫 data/panel)。"""
import pandas as pd

from build_panel_v3 import build_one

CIKS = ["0000001750", "0000001800", "0000002098", "0000320193", "0000789019"]


def main() -> None:
    frames = [pd.DataFrame(build_one((c, "ok"))) for c in CIKS]
    p = pd.concat(frames, ignore_index=True)
    print(p.shape)
    cols = ["entity_id", "period_end", "filed_date", "cash_and_equivalents",
            "short_term_investments", "lt_debt", "st_debt", "total_debt",
            "liabilities", "revenue", "revenue_period", "operating_cash_flow",
            "net_income", "shares_outstanding", "n_fields"]
    print(p[cols].tail(12).to_string())
    for f in ["cash_and_equivalents", "short_term_investments", "lt_debt", "st_debt",
              "total_debt", "liabilities", "revenue", "operating_cash_flow",
              "net_income", "shares_outstanding", "assets", "equity"]:
        print(f, "覆蓋", round(p[f].notna().mean() * 100, 1), "%")


if __name__ == "__main__":
    main()
