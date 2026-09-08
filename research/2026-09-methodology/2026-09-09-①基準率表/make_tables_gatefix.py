# -*- coding: utf-8 -*-
"""KARST-191:負債閘資料不足重算——基準率表層。

讀 out/events_gatefix.csv,用 debt_gatefix 之後的三個負債閘版本重建三條分格軸的
基準率表,統計方法(簇 bootstrap、樣本<30 不報勝率、未成熟樣本標記)完全沿用
make_tables.py 的 cell()/boot_ci()/build()——直接匯入該模組的函式,不重寫、
不複製一份出來自己改,避免兩份統計邏輯日後兜不攏。

版本定義(與原版對齊,只是負債閘的判定源頭換成 companyfacts 後備):
  A(gatefix)  只收「有值可判、而且現金 >= 總債務」的事件;資料不足的事件排除
              (與原 A 版同一個保守方向,但排除的集合已由 14,482 縮到 8,063)
  A2(gatefix) A(gatefix) + 資料不足的事件一律當過閘(與原 A2 版同一個樂觀方向,
              但「假設過閘」的集合同樣已經縮小)
  B(gatefix)  總債務(gatefix)/ 四季經營現金流 <= 3;資料不足的事件排除

輸出:out/base_rate_tables_gatefix.csv、out/table_info_gatefix.json、
out/entry_lag_gatefix.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_tables as MT  # noqa: E402  # 沿用 cell()/boot_ci()/build(),不重寫統計邏輯

OUT = HERE / "out"


def load_long_gatefix() -> tuple[pd.DataFrame, dict]:
    ev = pd.read_csv(OUT / "events_gatefix.csv", encoding="utf-8-sig",
                     parse_dates=["trigger_date", "panel_period_end"],
                     dtype={"entity_id": "string"})
    ev["entity_id"] = ev["entity_id"].str.zfill(10)
    info: dict = {"事件表列數": int(len(ev))}

    ev["過閘A"] = ev["gate_debt_n2_gatefix"] & ev["gate_cf"] & ev["gate_mcap"]
    ev["過閘A2"] = (ev["gate_debt_n2_gatefix"] | ev["資料不足_債務閘"]) & ev["gate_cf"] & ev["gate_mcap"]
    ev["過閘B"] = ev["gate_debt_ratio_gatefix"] & ev["gate_cf"] & ev["gate_mcap"]
    ev["資料可信"] = (~ev["split_basis_suspect"]) & (ev["dollar_vol_60d"] >= MT.LIQ_MIN)

    info["過閘A(N2,gatefix)"] = int(ev["過閘A"].sum())
    info["過閘A2(gatefix,資料不足當過閘)"] = int(ev["過閘A2"].sum())
    info["過閘B(債務比,gatefix)"] = int(ev["過閘B"].sum())
    info["資料不足_債務閘事件數"] = int(ev["資料不足_債務閘"].sum())
    info["過閘A_剔拆股基準可疑"] = int((ev["過閘A"] & ev["split_basis_suspect"]).sum())
    info["過閘A_剔流動性不足"] = int((ev["過閘A"] & (~ev["split_basis_suspect"]) &
                                     (ev["dollar_vol_60d"] < MT.LIQ_MIN)).sum())
    info["合格事件A(gatefix)"] = int((ev["過閘A"] & ev["資料可信"]).sum())
    info["合格事件A2(gatefix)"] = int((ev["過閘A2"] & ev["資料可信"]).sum())
    info["合格事件B(gatefix)"] = int((ev["過閘B"] & ev["資料可信"]).sum())

    recs = []
    for key in MT.ENTRIES:
        base = ev.copy()
        base["進場格"] = MT.ENTRIES[key]
        base["進場日"] = base[f"entry_{key}_date"]
        base["等待交易日"] = base[f"entry_{key}_lag"]
        for h in MT.HORIZONS:
            r = base.copy()
            r["期"] = h
            r["超額"] = base[f"{key}_{h}_excess"]
            r["期內最大跌幅"] = base[f"{key}_{h}_mdd"]
            r["觸及負33"] = base[f"{key}_{h}_touch33"]
            r["狀態"] = base[f"{key}_{h}_status"]
            recs.append(r)
    long = pd.concat(recs, ignore_index=True)
    return long, info


def main() -> None:
    long, info = load_long_gatefix()
    tables = []

    for ver, flag in (("A(淨現金 N2, gatefix)", "過閘A"),
                      ("A2(N2, gatefix, 資料不足當過閘)", "過閘A2"),
                      ("B(總債務/四季經營現金流<=3, gatefix)", "過閘B")):
        q = long[long[flag] & long["資料可信"]].copy()
        q["版本"] = ver
        for period_label, sub in (("全期 2010-2026", q),
                                  ("建表年份 2010-2021", q[q["trigger_year"] <= 2021]),
                                  ("驗證年份 2022-2026", q[q["trigger_year"] >= 2022])):
            sub = sub.copy()
            sub["年份段"] = period_label
            tables.append(MT.build(sub, ["版本", "年份段", "進場格", "期"], "總表(三格進場)"))
            tables.append(MT.build(sub, ["版本", "年份段", "進場格", "期", "industry_kill"],
                                   "軸一 行業殺 vs 個別殺"))
            tables.append(MT.build(sub, ["版本", "年份段", "進場格", "期", "pos_sma200"],
                                   "軸二 200 日線位置"))
            tables.append(MT.build(sub, ["版本", "年份段", "進場格", "期", "pos_sma250"],
                                   "軸二 250 日線位置(緩衝對照)"))

    res = pd.concat(tables, ignore_index=True)
    res.to_csv(OUT / "base_rate_tables_gatefix.csv", index=False, encoding="utf-8-sig")

    q = long[long["過閘A"] & long["資料可信"] & (long["期"] == "12m")]
    lag = (q.groupby("進場格")["等待交易日"]
             .agg(["count", "median", lambda s: float(np.nanpercentile(s.dropna(), 90))]))
    lag.columns = ["有進場點事件數", "等待交易日中位", "等待交易日p90"]
    lag.to_csv(OUT / "entry_lag_gatefix.csv", encoding="utf-8-sig")

    with open(OUT / "table_info_gatefix.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print(lag.to_string())

    main_tbl = res[(res["表"] == "總表(三格進場)") & (res["版本"].str.startswith("A"))]
    cols = ["年份段", "進場格", "期", "樣本N", "勝率", "勝率下限", "勝率上限", "賠率",
            "中位超額", "觸及負33比例", "未成熟"]
    print(main_tbl[cols].to_string(index=False))


if __name__ == "__main__":
    main()
