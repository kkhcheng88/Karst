# -*- coding: utf-8 -*-
"""KARST-192 第(一)步:口徑對帳表。

對每個版本 x 年份段 x 進場格 x 持有期 x 分格,在**同一個樣本**內同時出:
  平均超額、中位超額、勝率、贏家平均/輸家平均(平均盈虧比)、贏家中位/輸家中位(中位盈虧比)
並驗算  平均 = p x 贏家平均 - (1-p) x |輸家平均|  是否成立(誤差 < 0.1 個百分點)。

樣本定義完全沿用 make_tables.load_long()/make_tables_gatefix.load_long_gatefix(),
不重寫一份;「已成熟」的定義、資料可信閘、版本旗標全部照抄上游,務求與
base_rate_tables.csv / base_rate_tables_gatefix.csv 逐格對得上。

輸出:out/recon_caliber_recon.csv、out/recon_top_winners_recon.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_tables as MT            # noqa: E402
import make_tables_gatefix as MTG   # noqa: E402

OUT = HERE / "out"

VERSIONS_BASE = (("A(淨現金 N2)", "過閘A"),
                 ("A2(N2,缺債務標籤當零負債)", "過閘A2"),
                 ("B(總債務/四季經營現金流<=3)", "過閘B"))
VERSIONS_GF = (("A(淨現金 N2, gatefix)", "過閘A"),
               ("A2(N2, gatefix, 資料不足當過閘)", "過閘A2"),
               ("B(總債務/四季經營現金流<=3, gatefix)", "過閘B"))

PERIODS = (("全期 2010-2026", None),
           ("建表年份 2010-2021", "le2021"),
           ("驗證年份 2022-2026", "ge2022"))


def cell_recon(sub: pd.DataFrame) -> dict:
    """同一樣本內把六個統計量一次過算齊,再做驗算。"""
    mature = sub[sub["狀態"] == "已成熟"]
    n = len(mature)
    row = {"樣本N": n, "未成熟": int((sub["狀態"] == "未成熟").sum()),
           "無進場點": int((sub["狀態"] == "無進場點").sum()),
           "簇數": int(mature["cluster"].nunique()) if n else 0,
           "可信度": "高" if n >= 100 else ("中" if n >= MT.MIN_CELL else "低(樣本不足)")}
    if n == 0:
        return row
    ex = mature["超額"].to_numpy(dtype=float)
    w = ex[ex > 0]
    l = ex[ex <= 0]
    p = float(len(w)) / n
    row["勝率"] = p
    row["平均超額"] = float(np.mean(ex))
    row["中位超額"] = float(np.median(ex))
    row["贏家數"] = int(len(w))
    row["輸家數"] = int(len(l))
    row["贏家平均"] = float(np.mean(w)) if len(w) else np.nan
    row["輸家平均"] = float(np.mean(l)) if len(l) else np.nan
    row["贏家中位"] = float(np.median(w)) if len(w) else np.nan
    row["輸家中位"] = float(np.median(l)) if len(l) else np.nan
    row["平均盈虧比(贏家平均/|輸家平均|)"] = (
        float(np.mean(w) / abs(np.mean(l))) if len(w) and len(l) and np.mean(l) != 0 else np.nan)
    row["中位盈虧比(贏家中位/|輸家中位|)=原表賠率欄"] = (
        float(np.median(w) / abs(np.median(l))) if len(w) and len(l) and np.median(l) != 0 else np.nan)
    # 驗算:平均 = p x 贏家平均 - (1-p) x |輸家平均|
    if len(w) and len(l):
        recomputed = p * np.mean(w) - (1 - p) * abs(np.mean(l))
    elif len(w):
        recomputed = p * np.mean(w)
    else:
        recomputed = -(1 - p) * abs(np.mean(l))
    row["驗算平均(p x 贏家平均 - (1-p) x |輸家平均|)"] = float(recomputed)
    row["驗算差(個百分點)"] = float(abs(recomputed - np.mean(ex)) * 100.0)
    # 集中度
    ex_sorted = np.sort(ex)
    row["最大單筆超額"] = float(ex_sorted[-1])
    row["剔走前三大贏家後平均"] = float(np.mean(ex_sorted[:-3])) if n > 3 else np.nan
    k1 = max(1, int(np.ceil(n * 0.01)))
    k5 = max(1, int(np.ceil(n * 0.05)))
    tot = float(np.sum(ex))
    row["前1%事件數"] = k1
    row["前1%佔總超額比例"] = float(np.sum(ex_sorted[-k1:]) / tot) if tot != 0 else np.nan
    row["前5%事件數"] = k5
    row["前5%佔總超額比例"] = float(np.sum(ex_sorted[-k5:]) / tot) if tot != 0 else np.nan
    row["剔走前1%後平均"] = float(np.mean(ex_sorted[:-k1]))
    row["剔走前5%後平均"] = float(np.mean(ex_sorted[:-k5]))
    return row


def grid(long: pd.DataFrame, versions, tag: str) -> pd.DataFrame:
    rows = []
    for ver, flag in versions:
        q = long[long[flag] & long["資料可信"]].copy()
        for plabel, pf in PERIODS:
            if pf == "le2021":
                sub0 = q[q["trigger_year"] <= 2021]
            elif pf == "ge2022":
                sub0 = q[q["trigger_year"] >= 2022]
            else:
                sub0 = q
            for entry in MT.ENTRIES.values():
                for h in MT.HORIZONS:
                    s = sub0[(sub0["進場格"] == entry) & (sub0["期"] == h)]
                    # 總表
                    base = {"事件表": tag, "版本": ver, "年份段": plabel,
                            "進場格": entry, "期": h}
                    rows.append({**base, "表": "總表(三格進場)", "格": "全部",
                                 **cell_recon(s)})
                    for col, label in (("industry_kill", "軸一 行業殺 vs 個別殺"),
                                       ("pos_sma200", "軸二 200 日線位置"),
                                       ("pos_sma250", "軸二 250 日線位置(緩衝對照)")):
                        for gval, gsub in s.groupby(col, dropna=False, observed=True):
                            rows.append({**base, "表": label, "格": str(gval),
                                         **cell_recon(gsub)})
    return pd.DataFrame(rows)


def top_winners(long: pd.DataFrame, versions, tag: str, k: int = 20) -> pd.DataFrame:
    """每個版本前 k 大單筆超額(12 個月、觸發日即買、已成熟)。"""
    keep = ["entity_id", "primary_ticker", "name", "trigger_date", "trigger_year",
            "entry_A_date", "超額", "mcap", "shares", "cash", "total_debt",
            "has_total_debt", "ttm_ocf", "ttm_method", "split_basis_suspect",
            "dollar_vol_60d", "rel60", "px_vs_sma200", "industry_kill",
            "sic2", "sic_description", "is_foreign_filer", "panel_period_end",
            "panel_filed", "currency"]
    out = []
    for ver, flag in versions:
        q = long[long[flag] & long["資料可信"]
                 & (long["進場格"] == MT.ENTRIES["A"]) & (long["期"] == "12m")
                 & (long["狀態"] == "已成熟")].copy()
        q = q.sort_values("超額", ascending=False).head(k)
        q = q[[c for c in keep if c in q.columns]].copy()
        q.insert(0, "版本", ver)
        q.insert(0, "事件表", tag)
        q.insert(2, "名次", range(1, len(q) + 1))
        out.append(q)
    return pd.concat(out, ignore_index=True)


def main() -> None:
    long_b, info_b = MT.load_long()
    long_g, info_g = MTG.load_long_gatefix()

    grids = pd.concat([grid(long_b, VERSIONS_BASE, "events.csv(正本)"),
                       grid(long_g, VERSIONS_GF, "events_gatefix.csv")],
                      ignore_index=True)
    grids.to_csv(OUT / "recon_caliber_recon.csv", index=False, encoding="utf-8-sig")

    tw = pd.concat([top_winners(long_b, VERSIONS_BASE, "events.csv(正本)"),
                    top_winners(long_g, VERSIONS_GF, "events_gatefix.csv")],
                   ignore_index=True)
    tw.to_csv(OUT / "recon_top_winners_recon.csv", index=False, encoding="utf-8-sig")

    # 驗算式總結
    ok = grids.dropna(subset=["驗算差(個百分點)"])
    summary = {
        "對帳格數": int(len(grids)),
        "有驗算的格數": int(len(ok)),
        "驗算差最大(個百分點)": float(ok["驗算差(個百分點)"].max()),
        "驗算差中位(個百分點)": float(ok["驗算差(個百分點)"].median()),
        "驗算差>=0.1個百分點的格數": int((ok["驗算差(個百分點)"] >= 0.1).sum()),
        "前二十大贏家表列數": int(len(tw)),
    }
    with open(OUT / "recon_caliber_summary_recon.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # 主線快覽:總表 12 個月 觸發日即買
    m = grids[(grids["表"] == "總表(三格進場)") & (grids["期"] == "12m")
              & (grids["進場格"] == "觸發日即買")]
    cols = ["事件表", "版本", "年份段", "樣本N", "勝率", "平均超額", "中位超額",
            "贏家平均", "輸家平均", "平均盈虧比(贏家平均/|輸家平均|)",
            "贏家中位", "輸家中位", "中位盈虧比(贏家中位/|輸家中位|)=原表賠率欄",
            "驗算差(個百分點)"]
    with pd.option_context("display.width", 250, "display.max_columns", 50):
        print(m[cols].to_string(index=False))


if __name__ == "__main__":
    main()
