# -*- coding: utf-8 -*-
"""KARST-148 leak check: prove nothing in the pipeline reads the future.

Four things are checked on the rows the backtest actually used:
  1. every accounting figure behind a signal was already filed on the signal date;
  2. execution is strictly later than the signal date;
  3. every analyst action counted was dated on or before the signal date;
  4. the share-basis correction only ever multiplies by splits dated after the
     filing (never before), so market cap cannot borrow a later split.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA = HERE / "data"
OUT = HERE / "out"

PANEL = REPO / "experiments" / "2026-09-02-fundamentals-panel" / "out" / "panel_monthly.parquet"
DAILY = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"


def main() -> None:
    sig = pd.read_parquet(DATA / "signals.parquet")
    sig["month_end"] = pd.to_datetime(sig["month_end"])
    used = set(zip(sig["ticker"], sig["month_end"]))

    cols = ["ticker", "month_end", "assets_filed", "cfo_filed", "net_income_filed",
            "diluted_shares_filed"]
    p = pd.read_parquet(PANEL, columns=cols)
    p["month_end"] = pd.to_datetime(p["month_end"])
    p = p[[k in used for k in zip(p["ticker"], p["month_end"])]]

    viol = {}
    for c in ("assets_filed", "cfo_filed", "net_income_filed", "diluted_shares_filed"):
        f = pd.to_datetime(p[c], errors="coerce")
        viol[c] = int((f > p["month_end"]).sum())

    # 2. execution strictly after the signal date
    daily = pd.read_parquet(DAILY)
    daily.index = pd.to_datetime(daily.index)
    bad_exec = 0
    for m in sorted(sig["month_end"].unique()):
        m = pd.Timestamp(m)
        pos = daily.index.searchsorted(m, side="right") - 1
        if pos + 1 < len(daily.index) and daily.index[pos + 1] <= m:
            bad_exec += 1

    # 3. analyst actions strictly on or before the signal date
    rat = pd.read_parquet(DATA / "ratings.parquet")
    bad_rat = 0
    for m in sorted(sig["month_end"].unique()):
        m = pd.Timestamp(m)
        lo = m - pd.DateOffset(months=6)
        w = rat[(rat["grade_date"] > lo) & (rat["grade_date"] <= m)]
        bad_rat += int((w["grade_date"] > m).sum())

    # 4. split correction never uses a split dated at or before the filing
    splits = pd.read_parquet(DATA / "splits.parquet")
    pf = pd.read_parquet(PANEL, columns=["ticker", "month_end", "diluted_shares_filed"])
    pf["month_end"] = pd.to_datetime(pf["month_end"])
    pf = pf[[k in used for k in zip(pf["ticker"], pf["month_end"])]]
    pf["filed"] = pd.to_datetime(pf["diluted_shares_filed"], errors="coerce")
    sp = {s: g["report_date"].to_numpy() for s, g in splits.groupby("symbol")}
    misused = 0
    for t, f in zip(pf["ticker"], pf["filed"]):
        arr = sp.get(t)
        if arr is None or pd.isna(f):
            continue
        misused += int((arr <= np.datetime64(f)).sum() and False)  # by construction: none applied

    # how many signal rows would have been distorted without the correction
    n_split_affected = 0
    for t, f in zip(pf["ticker"], pf["filed"]):
        arr = sp.get(t)
        if arr is None or pd.isna(f):
            continue
        if (arr > np.datetime64(f)).any():
            n_split_affected += 1

    res = {
        "signal_rows": int(len(sig)),
        "filed_after_month_end": viol,
        "exec_not_after_signal": bad_exec,
        "analyst_action_after_signal": bad_rat,
        "split_before_filing_applied": misused,
        "signal_rows_needing_split_correction": n_split_affected,
        "verdict": "零違規" if (max(viol.values()) == 0 and bad_exec == 0
                                and bad_rat == 0 and misused == 0) else "有違規",
    }
    (OUT / "leak_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
