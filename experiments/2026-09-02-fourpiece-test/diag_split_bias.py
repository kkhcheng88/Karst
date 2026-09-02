# -*- coding: utf-8 -*-
"""KARST-148 diagnostic: how much free money does the split trap hand out?

Market cap = shares x price. The panel's share count is as-filed; the price is
split-adjusted. Multiply them raw and any company that split AFTER the filing
gets a market cap that is too small by the split ratio -- so its earnings yield
looks too high, and it gets bought. Companies split after their price has run,
so this is a look-ahead bias that pays.

This script re-runs the value arm and the composite arm with the correction
switched off, purely to size the trap. It is a diagnostic, not a result arm.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

import engine
import run_test as rt

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"


def main() -> None:
    daily = pd.read_parquet(rt.DAILY)
    daily.index = pd.to_datetime(daily.index)
    sig = pd.read_parquet(rt.DATA / "signals.parquet")
    sig["month_end"] = pd.to_datetime(sig["month_end"])

    splits = pd.read_parquet(rt.DATA / "splits.parquet")
    panel = pd.read_parquet(rt.PANEL if hasattr(rt, "PANEL") else
                            HERE.parent / "2026-09-02-fundamentals-panel" / "out" /
                            "panel_monthly.parquet",
                            columns=["ticker", "month_end", "diluted_shares",
                                     "diluted_shares_filed"])
    panel["month_end"] = pd.to_datetime(panel["month_end"])
    sig = sig.merge(panel, on=["ticker", "month_end"], how="left")
    # uncorrected market cap: as-filed shares x split-adjusted price
    sig["mcap_raw"] = sig["diluted_shares"] * sig["px"]
    sig["ey_raw"] = np.where(sig["mcap_raw"] > 0,
                             sig["mcap"] * sig["ey"] / sig["mcap_raw"], np.nan)

    cols = list(daily.columns)
    col_of = {c: i for i, c in enumerate(cols)}
    ret_all = daily.pct_change().to_numpy()
    dates = daily.index
    reb = sorted(pd.Timestamp(x) for x in sig["month_end"].unique())
    exec_day = {}
    for m in reb:
        pos = dates.searchsorted(m, side="right") - 1
        if pos + 1 < len(dates):
            exec_day[m] = pos + 1
    first_exec = min(exec_day.values())
    end_i = int(dates.searchsorted(rt.WIN_END, side="right"))
    ret = ret_all[:end_i]
    win = np.zeros(end_i, dtype=bool)
    win[first_exec:] = True
    by_month = {m: g for m, g in sig.groupby("month_end")}

    def build(kind: str, ey_col: str) -> dict:
        out = {}
        for m in reb:
            if m not in exec_day:
                continue
            q = by_month[m].copy()
            q["ey"] = q[ey_col]
            q = q[q["ey"].notna()]
            allowed = rt.sectors_in_play(q)
            if kind == "value":
                names = rt.top_per_sector(q, "ey", rt.TOP_N, False, allowed)
            else:
                d = rt.discipline(q, rt.DROP_PCT)
                d = rt.composite_scores(d, False)
                names = rt.top_per_sector(d, "score", rt.TOP_N, False, allowed)
            i = exec_day[m]
            idx = [col_of[t] for t in names if t in col_of and np.isfinite(daily.iloc[i][t])]
            if idx:
                out[i] = idx
        return out

    res = {}
    yrs = int(win.sum()) / engine.TRADING_DAYS_YEAR
    for kind in ("value", "composite"):
        for label, ey_col in (("修正後", "ey"), ("未修正(踩陷阱)", "ey_raw")):
            g, t = engine.run_one(ret, build(kind, ey_col))
            net = engine.apply_cost(g, t, rt.MAIN_BPS)[win]
            res[f"{kind}/{label}"] = {
                "cagr_15": round(float(engine.cagr(net, yrs)), 5),
                "mdd_15": round(engine.max_drawdown(net), 4),
                "turnover_yr": round(float(t[win].sum() / yrs), 3),
            }
    res["說明"] = ("「未修正」是把申報當時的股數直接乘已調整拆股的價格。"
                  "兩者之差就是拆股陷阱送出來的假優勢。")
    (OUT / "diag_split_bias.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
