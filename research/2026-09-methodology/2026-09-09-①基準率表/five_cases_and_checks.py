# -*- coding: utf-8 -*-
"""KARST-187:五家走通對照 + 口徑抽驗 + 倖存者口徑量度。

一、五家(LULU/TDC/ON/ENPH/ARM)2026 年的觸發日落在哪一格,那一格的歷史勝率與賠率
二、抽三個事件用原始 parquet 手算一次超額回報,核對 events.csv
三、倖存者口徑:事件表裡有幾多家已停止申報(捕捉得到的壞結局),幾多家仍在申報
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FIVE = ["LULU", "TDC", "ON", "ENPH", "ARM"]
HORIZONS = ["1m", "3m", "6m", "12m"]
ENTRY_LABEL = {"A": "觸發日即買", "B": "跌勢衰竭", "C": "買方回來"}


def main() -> None:
    ev = pd.read_csv(OUT / "events.csv", encoding="utf-8-sig", parse_dates=["trigger_date"],
                     dtype={"entity_id": "string"})
    ev["entity_id"] = ev["entity_id"].str.zfill(10)   # CSV 會吃掉 CIK 的前置零
    pan = pd.read_parquet(ROOT / "data/panel/quarterly_v3.parquet",
                          columns=["entity_id", "period_end", "total_debt_missing_reason"])
    ev["panel_period_end"] = pd.to_datetime(ev["panel_period_end"])
    ev = ev.merge(pan, left_on=["entity_id", "panel_period_end"],
                  right_on=["entity_id", "period_end"], how="left").drop(columns=["period_end"])
    ev["缺債務標籤"] = (~ev["has_total_debt"]) & (ev["total_debt_missing_reason"] == "tag_absent")
    tab = pd.read_csv(OUT / "base_rate_tables.csv", encoding="utf-8-sig")
    report: dict[str, object] = {}

    # ---------------------------------------------------------- 一、五家對照
    f = ev[ev["primary_ticker"].isin(FIVE) & (ev["trigger_date"] >= "2026-01-01")].copy()
    base_all = tab[(tab["表"] == "軸一 行業殺 vs 個別殺") &
                   (tab["年份段"] == "全期 2010-2026")]
    ma_all = tab[(tab["表"] == "軸二 200 日線位置") & (tab["年份段"] == "全期 2010-2026")]

    rows = []
    for r in f.itertuples(index=False):
        if r.gate_debt_n2:
            ver = "A(淨現金 N2)"
        elif getattr(r, "缺債務標籤"):
            ver = "A2(N2,缺債務標籤當零負債)"
        elif r.gate_debt_ratio:
            ver = "B(總債務/四季經營現金流<=3)"
        else:
            ver = None
        for key, label in ENTRY_LABEL.items():
            for h in HORIZONS:
                rec = {
                    "代號": r.primary_ticker, "公司": r.name, "觸發日": r.trigger_date.date(),
                    "相對SPY60日": round(r.rel60, 4),
                    "過負債閘A(N2)": bool(r.gate_debt_n2),
                    "總債務欄缺標籤": bool(getattr(r, "缺債務標籤")),
                    "過負債閘B(債務比)": bool(r.gate_debt_ratio),
                    "過現金流閘": bool(r.gate_cf), "過市值閘": bool(r.gate_mcap),
                    "行業殺格": r.industry_kill, "200日線格": r.pos_sma200, "250日線格": r.pos_sma250,
                    "進場格": label, "期": h,
                    "本次進場日": getattr(r, f"entry_{key}_date"),
                    "本次等待交易日": getattr(r, f"entry_{key}_lag"),
                    "本次結果狀態": getattr(r, f"{key}_{h}_status"),
                }
                if ver is None:
                    rec["對照基準率版本"] = "兩個負債閘都不過——沒有對得上的歷史格"
                else:
                    b = base_all[(base_all["版本"] == ver) & (base_all["進場格"] == label) &
                                 (base_all["期"] == h) & (base_all["industry_kill"] == r.industry_kill)]
                    m = ma_all[(ma_all["版本"] == ver) & (ma_all["進場格"] == label) &
                               (ma_all["期"] == h) & (ma_all["pos_sma200"] == r.pos_sma200)]
                    rec["對照基準率版本"] = ver
                    if len(b):
                        rec["軸一格 樣本N"] = int(b["樣本N"].iloc[0])
                        rec["軸一格 勝率"] = b["勝率"].iloc[0]
                        rec["軸一格 賠率"] = b["賠率"].iloc[0]
                        rec["軸一格 中位超額"] = b["中位超額"].iloc[0]
                    if len(m):
                        rec["軸二格 樣本N"] = int(m["樣本N"].iloc[0])
                        rec["軸二格 勝率"] = m["勝率"].iloc[0]
                        rec["軸二格 賠率"] = m["賠率"].iloc[0]
                        rec["軸二格 中位超額"] = m["中位超額"].iloc[0]
                rows.append(rec)
    five = pd.DataFrame(rows)
    five.to_csv(OUT / "five_cases_map.csv", index=False, encoding="utf-8-sig")
    print("五家對照落檔:", len(five), "列")

    # ---------------------------------------------------------- 二、口徑抽驗
    spy = pd.read_csv(ROOT / "data/prices/spy_daily.csv", parse_dates=["date"])
    spy = spy.set_index("date")["adj_close"]
    checks = []
    sample = ev[ev["gate_debt_n2"] & ev["gate_cf"] & ev["gate_mcap"] &
                (ev["A_12m_status"] == "已成熟")].sample(3, random_state=7)
    for r in sample.itertuples(index=False):
        part = int(r.entity_id[-2:]) % 16
        px = pd.read_parquet(ROOT / f"data/prices/daily/part_{part:02d}.parquet",
                             columns=["entity_id", "date", "adj_close", "series_role"])
        px = px[(px.entity_id == r.entity_id) & (px.series_role == "primary")].copy()
        px["date"] = pd.to_datetime(px["date"])
        px = px[px["date"].isin(spy.index)].sort_values("date").reset_index(drop=True)
        entry = pd.Timestamp(r.entry_A_date)
        i = int(px.index[px["date"] == entry][0])
        spy_pos = int(spy.index.get_loc(entry))
        tgt = spy.index[spy_pos + 252]
        j = int(px.index[px["date"] <= tgt][-1])
        stock = px["adj_close"].iloc[j] / px["adj_close"].iloc[i] - 1
        mkt = spy.loc[px["date"].iloc[j]] / spy.loc[entry] - 1
        手算 = (1 + stock) / (1 + mkt) - 1
        checks.append({"代號": r.primary_ticker, "觸發日": str(r.trigger_date.date()),
                       "進場日": str(entry.date()), "手算12月超額": round(float(手算), 6),
                       "腳本12月超額": round(float(r.A_12m_excess), 6),
                       "差": round(float(手算 - r.A_12m_excess), 9)})
    report["口徑抽驗"] = checks
    for c in checks:
        print("抽驗", c)
        assert abs(c["差"]) < 1e-6, "抽驗不符,超額回報算錯"

    # ---------------------------------------------------------- 三、倖存者口徑
    ent = pd.read_parquet(ROOT / "data/universe/entities.parquet",
                          columns=["entity_id", "filing_status", "last_filing_date"])
    q = ev[ev["gate_debt_n2"] & ev["gate_cf"] & ev["gate_mcap"] &
           (~ev["split_basis_suspect"]) & (ev["dollar_vol_60d"] >= 3e6)]
    q = q.merge(ent, on="entity_id", how="left")
    report["合格事件A"] = int(len(q))
    report["合格事件A_不重複公司數"] = int(q["entity_id"].nunique())
    report["其中已停止申報(ceased)的公司數"] = int(
        q[q["filing_status"] == "ceased"]["entity_id"].nunique())
    report["其中仍在申報(active)的公司數"] = int(
        q[q["filing_status"] == "active"]["entity_id"].nunique())

    # 倖存者敏感度:假設 x% 的事件屬於「當年觸發後除牌、回報 -100%」的公司,
    # 把它們補回去之後 12 個月勝率會變成多少
    m = q[q["A_12m_status"] == "已成熟"]
    w = float((m["A_12m_excess"] > 0).mean())
    sens = {}
    for x in (0.03, 0.05, 0.10):
        n = len(m)
        add = int(round(n * x / (1 - x)))
        sens[f"若另有 {int(x*100)}% 事件是已除牌(全部當輸)"] = round(w * n / (n + add), 4)
    report["12個月勝率_觸發日即買_現值"] = round(w, 4)
    report["倖存者敏感度"] = sens

    with open(OUT / "checks_and_survivorship.json", "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
