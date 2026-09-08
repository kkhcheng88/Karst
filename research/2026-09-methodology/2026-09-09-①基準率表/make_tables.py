# -*- coding: utf-8 -*-
"""KARST-187 基準率表:由 out/events.csv 產出三條分格軸的結果分佈。

控制(依 D-169 影響欄所列的評論修正):
  * 勝率的置信區間用「簇 bootstrap」——同一觸發月同一行業的事件視為一簇,重抽簇不重抽事件
  * 未成熟樣本(12 個月結果未到期)逐格標明,不計入勝率
  * 2022 年以後的觸發日分開報,不與 2009–2021 混合
  * 每格樣本 < 30 只報樣本數,不報勝率

資料品質過濾(不是策略條件,是修資料):
  * 剔「拆股基準可疑」——封面頁股數是當時基準、價格庫已調整到今日基準,
    觸發日之後發生拆股/反向拆股就會令市值放大或縮小
  * 加一條流動性閘(近 60 日中位成交金額 >= 300 萬美元),與 KARST-184 現役候選池同一條;
    它同時擋住外國申報人 ADR 比例造成的虛高市值
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
PANEL = ROOT / "data" / "panel" / "quarterly_v3.parquet"

HORIZONS = ["1m", "3m", "6m", "12m"]
H_LABEL = {"1m": "1 個月", "3m": "3 個月", "6m": "6 個月", "12m": "12 個月"}
ENTRIES = {"A": "觸發日即買", "B": "跌勢衰竭", "C": "買方回來"}
MIN_CELL = 30
N_BOOT = 2000
LIQ_MIN = 3e6
RNG = np.random.default_rng(20260909)


def load_long() -> tuple[pd.DataFrame, dict]:
    ev = pd.read_csv(OUT / "events.csv", encoding="utf-8-sig",
                     parse_dates=["trigger_date", "panel_period_end"],
                     dtype={"entity_id": "string"})
    ev["entity_id"] = ev["entity_id"].str.zfill(10)   # CSV 會吃掉 CIK 的前置零
    info = {"事件表列數": int(len(ev))}

    # 缺總債務標籤 vs 真的零負債,原料上分不開(面板盤點誠實聲明第 4 條)。
    # 所以負債閘出三個版本,A 與 A2 是同一件事的兩個極端,真值在中間。
    pan = pd.read_parquet(PANEL, columns=["entity_id", "period_end", "total_debt_missing_reason"])
    ev = ev.merge(pan, left_on=["entity_id", "panel_period_end"],
                  right_on=["entity_id", "period_end"], how="left").drop(columns=["period_end"])
    ev["缺債務標籤"] = (~ev["has_total_debt"]) & (ev["total_debt_missing_reason"] == "tag_absent")

    ev["過閘A"] = ev["gate_debt_n2"] & ev["gate_cf"] & ev["gate_mcap"]
    ev["過閘A2"] = (ev["gate_debt_n2"] | ev["缺債務標籤"]) & ev["gate_cf"] & ev["gate_mcap"]
    ev["過閘B"] = ev["gate_debt_ratio"] & ev["gate_cf"] & ev["gate_mcap"]
    ev["資料可信"] = (~ev["split_basis_suspect"]) & (ev["dollar_vol_60d"] >= LIQ_MIN)

    info["過閘A(N2)"] = int(ev["過閘A"].sum())
    info["過閘A2(缺債務標籤當零負債)"] = int(ev["過閘A2"].sum())
    info["過閘B(債務比)"] = int(ev["過閘B"].sum())
    info["缺總債務標籤的事件數"] = int(ev["缺債務標籤"].sum())
    info["過閘A_剔拆股基準可疑"] = int((ev["過閘A"] & ev["split_basis_suspect"]).sum())
    info["過閘A_剔流動性不足"] = int((ev["過閘A"] & (~ev["split_basis_suspect"]) &
                                     (ev["dollar_vol_60d"] < LIQ_MIN)).sum())
    info["合格事件A"] = int((ev["過閘A"] & ev["資料可信"]).sum())
    info["合格事件A2"] = int((ev["過閘A2"] & ev["資料可信"]).sum())
    info["合格事件B"] = int((ev["過閘B"] & ev["資料可信"]).sum())

    recs = []
    for key in ENTRIES:
        base = ev.copy()
        base["進場格"] = ENTRIES[key]
        base["進場日"] = base[f"entry_{key}_date"]
        base["等待交易日"] = base[f"entry_{key}_lag"]
        for h in HORIZONS:
            r = base.copy()
            r["期"] = h
            r["超額"] = base[f"{key}_{h}_excess"]
            r["期內最大跌幅"] = base[f"{key}_{h}_mdd"]
            r["觸及負33"] = base[f"{key}_{h}_touch33"]
            r["狀態"] = base[f"{key}_{h}_status"]
            recs.append(r)
    long = pd.concat(recs, ignore_index=True)
    return long, info


def boot_ci(win: np.ndarray, clusters: np.ndarray, extra: np.ndarray | None = None):
    """簇 bootstrap:重抽簇(同一觸發月同一行業算一簇),不重抽單一事件。

    同一批重抽同時給勝率與平均超額的區間——兩個數的非獨立性來源一樣。
    """
    uniq, inv = np.unique(clusters, return_inverse=True)
    buckets = [np.nonzero(inv == i)[0] for i in range(len(uniq))]
    n = len(uniq)
    if n < 3:
        return (np.nan, np.nan, np.nan, np.nan)
    out = np.empty(N_BOOT)
    out2 = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = RNG.integers(0, n, n)
        idx = np.concatenate([buckets[i] for i in pick])
        out[b] = win[idx].mean()
        if extra is not None:
            out2[b] = extra[idx].mean()
    lo, hi = float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))
    if extra is None:
        return lo, hi, np.nan, np.nan
    return lo, hi, float(np.percentile(out2, 2.5)), float(np.percentile(out2, 97.5))


def cell(df: pd.DataFrame) -> dict:
    mature = df[df["狀態"] == "已成熟"]
    n_imm = int((df["狀態"] == "未成熟").sum())
    n_none = int((df["狀態"] == "無進場點").sum())
    n_short = int((df["狀態"].isin(["資料不足", "資料提早結束"])).sum())
    n = len(mature)
    row = {
        "樣本N": n, "未成熟": n_imm, "無進場點": n_none, "資料不足": n_short,
        "可信度": "高" if n >= 100 else ("中" if n >= MIN_CELL else "低(樣本不足,只報樣本數)"),
    }
    if n == 0:
        return row
    ex = mature["超額"].to_numpy(dtype=float)
    row["中位超額"] = float(np.median(ex))
    row["p25超額"] = float(np.percentile(ex, 25))
    row["p75超額"] = float(np.percentile(ex, 75))
    row["平均超額"] = float(np.mean(ex))
    mdd = mature["期內最大跌幅"].to_numpy(dtype=float)
    row["中位期內最大跌幅"] = float(np.median(mdd))
    row["觸及負33比例"] = float(np.mean(mature["觸及負33"].astype(float)))
    row["最大單筆超額"] = float(np.max(ex))
    row["剔走前三大贏家後的平均超額"] = float(np.mean(np.sort(ex)[:-3])) if n > 3 else np.nan
    row["2020年觸發佔比"] = float((mature["trigger_year"] == 2020).mean())
    if n < MIN_CELL:
        # 票面規矩:每格樣本 < 30 只報樣本數,不報勝率
        for k in ("勝率", "勝率下限", "勝率上限", "賠率", "中位超額", "p25超額",
                  "p75超額", "平均超額", "中位期內最大跌幅", "觸及負33比例",
                  "最大單筆超額", "剔走前三大贏家後的平均超額"):
            row[k] = np.nan
        return row
    win = (ex > 0).astype(float)
    row["勝率"] = float(win.mean())
    lo, hi, mlo, mhi = boot_ci(win, mature["cluster"].to_numpy(), ex)
    row["勝率下限"], row["勝率上限"] = lo, hi
    row["平均超額下限"], row["平均超額上限"] = mlo, mhi
    w = ex[ex > 0]
    l = ex[ex <= 0]
    row["賠率"] = float(np.median(w) / abs(np.median(l))) if len(w) and len(l) else np.nan
    row["簇數"] = int(mature["cluster"].nunique())
    return row


def build(df: pd.DataFrame, by: list[str], label: str) -> pd.DataFrame:
    rows = []
    for keys, sub in df.groupby(by, dropna=False, observed=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        rec = dict(zip(by, keys))
        rec["表"] = label
        rec.update(cell(sub))
        rows.append(rec)
    out = pd.DataFrame(rows)
    if "期" in out.columns:
        out["期"] = pd.Categorical(out["期"], categories=HORIZONS, ordered=True)
        out = out.sort_values(by)
    return out


def main() -> None:
    long, info = load_long()
    tables = []

    for ver, flag in (("A(淨現金 N2)", "過閘A"),
                      ("A2(N2,缺債務標籤當零負債)", "過閘A2"),
                      ("B(總債務/四季經營現金流<=3)", "過閘B")):
        q = long[long[flag] & long["資料可信"]].copy()
        q["版本"] = ver
        for period_label, sub in (("全期 2010-2026", q),
                                  ("建表年份 2010-2021", q[q["trigger_year"] <= 2021]),
                                  ("驗證年份 2022-2026", q[q["trigger_year"] >= 2022])):
            sub = sub.copy()
            sub["年份段"] = period_label
            tables.append(build(sub, ["版本", "年份段", "進場格", "期"], "總表(三格進場)"))
            tables.append(build(sub, ["版本", "年份段", "進場格", "期", "industry_kill"],
                                "軸一 行業殺 vs 個別殺"))
            tables.append(build(sub, ["版本", "年份段", "進場格", "期", "pos_sma200"],
                                "軸二 200 日線位置"))
            tables.append(build(sub, ["版本", "年份段", "進場格", "期", "pos_sma250"],
                                "軸二 250 日線位置(緩衝對照)"))

    res = pd.concat(tables, ignore_index=True)
    res.to_csv(OUT / "base_rate_tables.csv", index=False, encoding="utf-8-sig")

    # 進場等待日數
    q = long[long["過閘A"] & long["資料可信"] & (long["期"] == "12m")]
    lag = (q.groupby("進場格")["等待交易日"]
             .agg(["count", "median", lambda s: float(np.nanpercentile(s.dropna(), 90))]))
    lag.columns = ["有進場點事件數", "等待交易日中位", "等待交易日p90"]
    lag.to_csv(OUT / "entry_lag.csv", encoding="utf-8-sig")

    with open(OUT / "table_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print(lag.to_string())

    # 主表快覽
    main_tbl = res[(res["表"] == "總表(三格進場)") & (res["版本"].str.startswith("A"))]
    cols = ["年份段", "進場格", "期", "樣本N", "勝率", "勝率下限", "勝率上限", "賠率",
            "中位超額", "觸及負33比例", "未成熟"]
    print(main_tbl[cols].to_string(index=False))


if __name__ == "__main__":
    main()
