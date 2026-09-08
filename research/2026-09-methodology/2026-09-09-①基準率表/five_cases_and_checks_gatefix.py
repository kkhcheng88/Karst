# -*- coding: utf-8 -*-
"""KARST-191:負債閘資料不足重算——五家(LULU/TDC/ON/ENPH/ARM)落格對照,gatefix 版本。

讀 out/events_gatefix.csv + out/base_rate_tables_gatefix.csv,重做原
five_cases_and_checks.py 第一節(五家對照),換上 gatefix 之後的負債閘判定與
「資料不足」分類(取代原本的「缺債務標籤」)。口徑抽驗與倖存者口徑兩節不受
負債閘影響,不重覆做(仍以原 out/checks_and_survivorship.json 為準)。

輸出:out/five_cases_map_gatefix.csv
"""
from __future__ import annotations

import pandas as pd

from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FIVE = ["LULU", "TDC", "ON", "ENPH", "ARM"]
HORIZONS = ["1m", "3m", "6m", "12m"]
ENTRY_LABEL = {"A": "觸發日即買", "B": "跌勢衰竭", "C": "買方回來"}


def main() -> None:
    ev = pd.read_csv(OUT / "events_gatefix.csv", encoding="utf-8-sig",
                     parse_dates=["trigger_date"], dtype={"entity_id": "string"})
    ev["entity_id"] = ev["entity_id"].str.zfill(10)
    tab = pd.read_csv(OUT / "base_rate_tables_gatefix.csv", encoding="utf-8-sig")

    f = ev[ev["primary_ticker"].isin(FIVE) & (ev["trigger_date"] >= "2026-01-01")].copy()
    base_all = tab[(tab["表"] == "軸一 行業殺 vs 個別殺") & (tab["年份段"] == "全期 2010-2026")]
    ma_all = tab[(tab["表"] == "軸二 200 日線位置") & (tab["年份段"] == "全期 2010-2026")]

    rows = []
    for r in f.itertuples(index=False):
        if r.gate_debt_n2_gatefix:
            ver = "A(淨現金 N2, gatefix)"
        elif r.資料不足_債務閘:
            ver = "A2(N2, gatefix, 資料不足當過閘)"
        elif r.gate_debt_ratio_gatefix:
            ver = "B(總債務/四季經營現金流<=3, gatefix)"
        else:
            ver = None
        for key, label in ENTRY_LABEL.items():
            for h in HORIZONS:
                rec = {
                    "代號": r.primary_ticker, "公司": r.name, "觸發日": r.trigger_date.date(),
                    "相對SPY60日": round(r.rel60, 4),
                    "面板total_debt空白": not bool(r.has_total_debt),
                    "總債務來源_gatefix": r.total_debt_source_gatefix,
                    "總債務值_gatefix": r.total_debt_gatefix,
                    "過負債閘A(N2)_gatefix": bool(r.gate_debt_n2_gatefix),
                    "資料不足_債務閘": bool(r.資料不足_債務閘),
                    "過負債閘B(債務比)_gatefix": bool(r.gate_debt_ratio_gatefix),
                    "過現金流閘": bool(r.gate_cf), "過市值閘": bool(r.gate_mcap),
                    "行業殺格": r.industry_kill, "200日線格": r.pos_sma200, "250日線格": r.pos_sma250,
                    "進場格": label, "期": h,
                    "本次進場日": getattr(r, f"entry_{key}_date"),
                    "本次等待交易日": getattr(r, f"entry_{key}_lag"),
                    "本次結果狀態": getattr(r, f"{key}_{h}_status"),
                }
                if ver is None:
                    rec["對照基準率版本_gatefix"] = "三個負債閘版本都不過——沒有對得上的歷史格"
                else:
                    b = base_all[(base_all["版本"] == ver) & (base_all["進場格"] == label) &
                                (base_all["期"] == h) & (base_all["industry_kill"] == r.industry_kill)]
                    m = ma_all[(ma_all["版本"] == ver) & (ma_all["進場格"] == label) &
                               (ma_all["期"] == h) & (ma_all["pos_sma200"] == r.pos_sma200)]
                    rec["對照基準率版本_gatefix"] = ver
                    if len(b):
                        rec["軸一格 樣本N_gatefix"] = int(b["樣本N"].iloc[0])
                        rec["軸一格 勝率_gatefix"] = b["勝率"].iloc[0]
                        rec["軸一格 賠率_gatefix"] = b["賠率"].iloc[0]
                        rec["軸一格 中位超額_gatefix"] = b["中位超額"].iloc[0]
                    if len(m):
                        rec["軸二格 樣本N_gatefix"] = int(m["樣本N"].iloc[0])
                        rec["軸二格 勝率_gatefix"] = m["勝率"].iloc[0]
                        rec["軸二格 賠率_gatefix"] = m["賠率"].iloc[0]
                        rec["軸二格 中位超額_gatefix"] = m["中位超額"].iloc[0]
                rows.append(rec)
    five = pd.DataFrame(rows)
    five.to_csv(OUT / "five_cases_map_gatefix.csv", index=False, encoding="utf-8-sig")
    print("五家對照(gatefix)落檔:", len(five), "列")

    # 只印五家各自的負債閘判定(對照用的第一眼摘要)
    summ = (f[["primary_ticker", "trigger_date", "has_total_debt", "total_debt_gatefix",
              "total_debt_source_gatefix", "gate_debt_n2_gatefix", "gate_debt_ratio_gatefix",
              "資料不足_債務閘"]]
            .drop_duplicates())
    print(summ.to_string(index=False))


if __name__ == "__main__":
    main()
