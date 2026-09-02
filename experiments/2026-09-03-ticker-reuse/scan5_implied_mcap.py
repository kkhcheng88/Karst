"""KARST-165 決定性篩查:接錯公司的代號,市值會小得不合理。

道理:名單裡的代號都是大型指數成分股,成分期內市值不可能只有幾千萬美元。
如果面板的股數(來自解析到的 CIK 的 XBRL)乘以價格,在成分期內得出一個微型市值,
那個 CIK 幾乎肯定不是成分期那家公司,而是代號後來的使用者。
"""
import json
import pathlib

import numpy as np
import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
OUT = REPO / "experiments" / "2026-09-03-ticker-reuse" / "out"
OUT.mkdir(parents=True, exist_ok=True)

uni = pd.read_csv(REPO / "experiments/2026-09-02-fundamentals-panel/out/universe_cik.csv",
                  dtype=str)
panel = pd.read_parquet(
    REPO / "experiments/2026-09-02-fundamentals-panel/out/panel_monthly.parquet",
    columns=["ticker", "cik", "month_end", "diluted_shares", "revenue_ttm"])
panel["month_end"] = pd.to_datetime(panel["month_end"])
mon = pd.read_parquet(
    REPO / "experiments/2026-09-01-stock-oracle-curve/data/stock_monthly.parquet",
    columns=["symbol", "month_end", "close"])
mon["month_end"] = pd.to_datetime(mon["month_end"])
mon = mon.rename(columns={"symbol": "ticker"})

p = panel.merge(mon, on=["ticker", "month_end"], how="left")
p["mcap"] = p["diluted_shares"] * p["close"]

info = uni.set_index("ticker")
rows = []
for t, g in p.groupby("ticker"):
    if t not in info.index:
        continue
    r = info.loc[t]
    if isinstance(r, pd.DataFrame):
        r = r.iloc[0]
    g = g.dropna(subset=["mcap"])
    if g.empty:
        continue
    left = r["left_on"]
    gi = g[g["month_end"] <= pd.Timestamp(left)] if isinstance(left, str) and left else g
    if gi.empty:
        gi = g
    rows.append({
        "ticker": t,
        "delisted": r["delisted_or_removed"],
        "index_joined": r["joined_on"], "index_left": left,
        "cik": r["cik"], "cik_source": r["cik_source"],
        "cells": int(len(g)),
        "median_mcap_usd_m": round(float(np.nanmedian(gi["mcap"])) / 1e6, 2),
        "median_shares_m": round(float(np.nanmedian(gi["diluted_shares"])) / 1e6, 3),
        "median_rev_ttm_usd_m": (round(float(np.nanmedian(gi["revenue_ttm"])) / 1e6, 2)
                                 if gi["revenue_ttm"].notna().any() else None),
        "cik_note": (r["cik_note"] or "")[:120],
    })
m = pd.DataFrame(rows).sort_values("median_mcap_usd_m")
m.to_csv(OUT / "implied_mcap_screen.csv", index=False, encoding="utf-8")
pd.set_option("display.width", 250, "display.max_colwidth", 60)
print("有市值算得出的代號:", len(m))
print("\n=== 成分期內市值中位數低於 3 億美元(接錯公司的嫌疑)===")
sus = m[m.median_mcap_usd_m < 300]
print(sus.to_string(index=False))
print("\n=== 3 億至 10 億 ===")
print(m[(m.median_mcap_usd_m >= 300) & (m.median_mcap_usd_m < 1000)].to_string(index=False))
