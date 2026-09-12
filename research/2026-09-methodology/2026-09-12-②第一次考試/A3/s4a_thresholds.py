# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2)第四步之一:逐事件滾動窗口門檻(執行口徑 v1.2 第 1 項)。

規則(一字不改照修訂頁):
  門檻 = 反應日**之前**過去 252 個交易日內「宇宙內合資格事件」的相對 SPY 反應第 90 百分位;
  窗內事件 < 300 宗 → 改用過去 504 個交易日;仍不足 → 標 `thr_insufficient`(不入池,記數)。

**反例自查**:窗口嚴格取反應日之前(p-252 .. p-1),不含反應日當日或之後,
故任何入池事件的窗口都不可能含反應日當日或之後的事件(驗收條件第 1 條)。

輸入:`cache/population_base.parquet`(由 s4_assemble.py 產生,含 in_universe)。
輸出:`cache/thresholds_window.parquet`(逐事件一行)與 `cache/thresholds.json`(描述統計)。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
SPY_CSV = ROOT / "data" / "prices" / "spy_daily.csv"

WIN_MAIN = 252
WIN_WIDE = 504
MIN_N = 300


def main() -> None:
    spy = pd.read_csv(SPY_CSV, parse_dates=["date"]).sort_values("date")
    spy_dates = spy["date"].values.astype("datetime64[D]")
    n_spy = len(spy_dates)

    df = pd.read_parquet(CACHE / "population_base.parquet")
    u = df[(df["in_universe"] == 1) & df["reaction_date"].notna()
           & (df["reaction_date"].astype(str) != "")].copy()
    u = u[u["rel_spy"].notna()]
    u["rd"] = pd.to_datetime(u["reaction_date"]).values.astype("datetime64[D]")
    print("宇宙內且有 rel_spy:%d" % len(u), flush=True)

    # 逐交易日的宇宙內事件 rel_spy(同一日多宗 = 同一窗內多個觀測)
    order = np.argsort(u["rd"].values, kind="stable")
    rd = u["rd"].values[order]
    rv = u["rel_spy"].values[order].astype("float64")
    rp = np.searchsorted(spy_dates, rd, side="left")   # 事件日 → SPY 索引

    rows = []
    for k in range(len(rd)):
        p = int(rp[k])
        if p >= n_spy or spy_dates[p] != rd[k]:
            p = int(np.searchsorted(spy_dates, rd[k], side="right"))
        lo = max(0, p - WIN_MAIN)
        # 窗口 = SPY 索引 [lo, p-1] → 嚴格早於反應日
        a = int(np.searchsorted(rd, spy_dates[lo], side="left"))
        b = int(np.searchsorted(rd, rd[k], side="left"))    # 嚴格早於 rd[k]
        win = rv[a:b]
        used = WIN_MAIN
        if len(win) < MIN_N:
            lo2 = max(0, p - WIN_WIDE)
            a2 = int(np.searchsorted(rd, spy_dates[lo2], side="left"))
            win2 = rv[a2:b]
            if len(win2) > len(win):
                win, used = win2, WIN_WIDE
        n = len(win)
        if n < MIN_N:
            rows.append(dict(accessionNumber=u["accessionNumber"].iat[order[k]],
                             thr_win_days=used, thr_n=n, thr_p90=None, thr_p95=None,
                             thr_p80=None, thr_insufficient=1))
            continue
        rows.append(dict(accessionNumber=u["accessionNumber"].iat[order[k]],
                         thr_win_days=used, thr_n=n,
                         thr_p90=float(np.percentile(win, 90)),
                         thr_p95=float(np.percentile(win, 95)),
                         thr_p80=float(np.percentile(win, 80)),
                         thr_insufficient=0))

    out = pd.DataFrame(rows)
    out.to_parquet(CACHE / "thresholds_window.parquet", index=False)

    by_year = {}
    o = out.copy()
    # 年份由 accessionNumber 對回 population
    ymap = dict(zip(df["accessionNumber"], df["year"]))
    o["year"] = o["accessionNumber"].map(ymap)
    for y, g in o.groupby("year"):
        if pd.isna(y):
            continue
        by_year[str(int(y))] = {
            "n_events": int(len(g)),
            "p90_median": round(float(np.nanmedian(g["thr_p90"])), 5),
            "p90_min": round(float(np.nanmin(g["thr_p90"])), 5),
            "p90_max": round(float(np.nanmax(g["thr_p90"])), 5),
            "win_n_median": int(np.median(g["thr_n"])),
            "used_504": int((g["thr_win_days"] == WIN_WIDE).sum()),
            "insufficient": int(g["thr_insufficient"].sum()),
        }
    summary = {
        "win_main": WIN_MAIN, "win_wide": WIN_WIDE, "min_n": MIN_N,
        "n_events_universe": int(len(out)),
        "n_insufficient": int(out["thr_insufficient"].sum()),
        "n_used_504": int((out["thr_win_days"] == WIN_WIDE).sum()),
        "win_n_median": int(np.median(out["thr_n"])),
        "by_year": by_year,
    }
    (CACHE / "thresholds.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("宇宙內事件 %d;資料不足 %d;用 504 日 %d;窗內中位數 %d"
          % (len(out), summary["n_insufficient"], summary["n_used_504"],
             summary["win_n_median"]))
    print("→", CACHE / "thresholds_window.parquet")


if __name__ == "__main__":
    main()
