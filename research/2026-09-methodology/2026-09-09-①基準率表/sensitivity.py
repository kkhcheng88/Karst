# -*- coding: utf-8 -*-
"""KARST-187 敏感度:2020 年單一事件對基準率的支配程度。

建表年份(2010–2021)的「行業殺」那一格,樣本有一半以上來自 2020 年 3 月同一次崩盤。
本腳本逐格重算「剔走 2020 年觸發」之後的結果,看結論還在不在。
輸出:out/sensitivity_2020.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
HORIZONS = ["1m", "3m", "6m", "12m"]
ENTRY = {"A": "觸發日即買", "B": "跌勢衰竭", "C": "買方回來"}


def stat(s: pd.DataFrame, col: str) -> dict:
    ex = s[col].dropna().to_numpy(dtype=float)
    if len(ex) < 30:
        return {"樣本N": len(ex), "勝率": np.nan, "平均超額": np.nan, "中位超額": np.nan,
                "賠率": np.nan, "可信度": "低(樣本不足,只報樣本數)"}
    w, l = ex[ex > 0], ex[ex <= 0]
    return {"樣本N": len(ex), "勝率": float(np.mean(ex > 0)),
            "平均超額": float(np.mean(ex)), "中位超額": float(np.median(ex)),
            "賠率": float(np.median(w) / abs(np.median(l))) if len(w) and len(l) else np.nan,
            "可信度": "高" if len(ex) >= 100 else "中"}


def main() -> None:
    ev = pd.read_csv(OUT / "events.csv", encoding="utf-8-sig",
                     parse_dates=["trigger_date", "panel_period_end"],
                     dtype={"entity_id": "string"})
    ev["entity_id"] = ev["entity_id"].str.zfill(10)
    pan = pd.read_parquet(ROOT / "data/panel/quarterly_v3.parquet",
                          columns=["entity_id", "period_end", "total_debt_missing_reason"])
    ev = ev.merge(pan, left_on=["entity_id", "panel_period_end"],
                  right_on=["entity_id", "period_end"], how="left")
    ev["缺債務標籤"] = (~ev["has_total_debt"]) & (ev["total_debt_missing_reason"] == "tag_absent")
    ev["資料可信"] = (~ev["split_basis_suspect"]) & (ev["dollar_vol_60d"] >= 3e6)

    versions = {
        "A(淨現金 N2)": ev["gate_debt_n2"],
        "A2(N2,缺債務標籤當零負債)": ev["gate_debt_n2"] | ev["缺債務標籤"],
        "B(總債務/四季經營現金流<=3)": ev["gate_debt_ratio"],
    }
    rows = []
    for vname, vmask in versions.items():
        q = ev[vmask & ev["gate_cf"] & ev["gate_mcap"] & ev["資料可信"]]
        cuts = {
            "全期 2010-2026": q,
            "全期 剔走 2020 年觸發": q[q["trigger_year"] != 2020],
            "建表年份 2010-2021": q[q["trigger_year"] <= 2021],
            "建表年份 剔走 2020": q[(q["trigger_year"] <= 2021) & (q["trigger_year"] != 2020)],
            "驗證年份 2022-2026": q[q["trigger_year"] >= 2022],
        }
        for cname, sub in cuts.items():
            for kill in ["行業殺", "個別殺", "全部"]:
                s0 = sub if kill == "全部" else sub[sub["industry_kill"] == kill]
                for key, elabel in ENTRY.items():
                    for h in HORIZONS:
                        col = f"{key}_{h}_excess"
                        rec = {"版本": vname, "年份切法": cname, "軸一格": kill,
                               "進場格": elabel, "期": h,
                               "2020年觸發佔比": float((s0["trigger_year"] == 2020).mean()) if len(s0) else np.nan}
                        rec.update(stat(s0, col))
                        rows.append(rec)
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "sensitivity_2020.csv", index=False, encoding="utf-8-sig")

    view = res[(res["版本"].str.startswith("A2")) & (res["進場格"] == "觸發日即買") &
               (res["期"] == "12m")]
    pd.set_option("display.width", 220)
    print(view[["年份切法", "軸一格", "樣本N", "勝率", "賠率", "平均超額", "中位超額",
                "2020年觸發佔比", "可信度"]].to_string(index=False))


if __name__ == "__main__":
    main()
