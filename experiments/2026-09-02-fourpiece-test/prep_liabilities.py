"""KARST-148 preparation step (a): back-fill total liabilities as assets - equity.

D-125 decision 3. Writes a NEW file; the KARST-146 panel original is never touched.
CRITERIA sec.11.1.
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

PANEL = REPO / "experiments" / "2026-09-02-fundamentals-panel" / "out" / "panel_monthly.parquet"


def main() -> None:
    cols = ["ticker", "month_end", "in_index", "assets", "assets_end", "assets_filed",
            "equity", "equity_end", "equity_filed", "liabilities", "liabilities_end",
            "liabilities_filed"]
    p = pd.read_parquet(PANEL, columns=cols)

    reported = p["liabilities"].notna()
    # only derive when both legs come from the same balance-sheet date -- mixing an
    # assets figure from one quarter with an equity figure from another is not the
    # accounting identity, it is noise.
    same_date = p["assets_end"].eq(p["equity_end"]) & p["assets_end"].notna()
    derivable = (~reported) & same_date & p["assets"].notna() & p["equity"].notna()

    p["liabilities_filled"] = p["liabilities"]
    p.loc[derivable, "liabilities_filled"] = p.loc[derivable, "assets"] - p.loc[derivable, "equity"]
    p["liabilities_source"] = "missing"
    p.loc[reported, "liabilities_source"] = "reported"
    p.loc[derivable, "liabilities_source"] = "derived"

    # sanity: on rows where BOTH exist, how close is the identity?
    both = reported & same_date & p["assets"].notna() & p["equity"].notna()
    chk = p.loc[both].copy()
    chk["identity"] = chk["assets"] - chk["equity"]
    rel = ((chk["identity"] - chk["liabilities"]).abs()
           / chk["liabilities"].abs().replace(0, pd.NA)).dropna()

    out = p[["ticker", "month_end", "liabilities_filled", "liabilities_source"]]
    out.to_parquet(OUT / "panel_liab_backfill.parquet", index=False)

    meta = {
        "rows": int(len(p)),
        "reported": int(reported.sum()),
        "derived": int(derivable.sum()),
        "still_missing": int((p["liabilities_source"] == "missing").sum()),
        "coverage_before": round(float(reported.mean()), 4),
        "coverage_after": round(float((p["liabilities_source"] != "missing").mean()), 4),
        "identity_check_rows": int(len(rel)),
        "identity_rel_err_median": round(float(rel.median()), 6) if len(rel) else None,
        "identity_rel_err_p90": round(float(rel.quantile(0.90)), 6) if len(rel) else None,
        "identity_rel_err_within_1pct": round(float((rel <= 0.01).mean()), 4) if len(rel) else None,
        "note": ("差額源於少數股東權益:面板 equity 欄的回退次序把 StockholdersEquity "
                 "(不含少數股東)排在含少數股東那個之前,所以倒算值在有少數股東的公司會偏高。"
                 "四件套本身沒有用到總負債,本欄只作記錄。"),
    }
    (OUT / "prep_liabilities.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
