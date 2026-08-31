"""KARST-121 樣本驗證:標普官方那個免費試算表,舊版與新版的歷史數字對不對得上。

這是本票最關鍵的一條事實。倍數情緒儀要回測,分母必須是「當時知道的數」;
如果數據商每次更新都把歷史一齊改寫,那麼今日下載的歷史就不是當時的歷史,回測即前視。

驗法很直接:攞同一個檔案的兩個舊版本(2020-07-25 與 2026-05-27,相隔近六年),
把兩邊都有的「行業 × 季度 每股盈利」逐格對。一格都不差 = 這家從不改寫歷史。

兩個版本由 Wayback Machine 取得,放在 data/(大檔,不入 git)。
原始網址:https://www.spglobal.com/spdji/en/documents/additional-material/sp-500-eps-est.xlsx
(該網址今日已回 403;檔案本身自 2026-01-30 起停止更新——編者 Howard Silverblatt 退休。)

讀這張表有三個坑,全部踩過才行得通:
  1. 季度欄標題住在第 6 行,不是第一行——認錯即讀出一張空表;
  2. 同一批行業名出現兩次(營運盈利一組、公認會計準則盈利一組),
     淨用行業名做鑰匙會兩組溝埋一齊,對出來的數字沒有意義;
  3. 表內另有市盈率欄,它含價格,兩版之間本來就應該不同——
     那不是改寫歷史,所以只對「年份 + 季」那批純每股盈利欄。

跑法(Windows PowerShell):
    $env:PYTHONUTF8 = "1"; python verify_sp_vintage_no_restatement.py

輸出:sp_vintage_diff_result.json(小檔,入 git)
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
OLD_FILE = DATA_DIR / "eps-20200725.xlsx"
NEW_FILE = DATA_DIR / "eps-20260527.xlsx"
SHEET = "SECTOR EPS"

# 季度欄標題所在行(0 起數)
HEADER_ROW = 5

# 只收「2008 Q1」這種純季度每股盈利欄;市盈率欄含價格,不在對數範圍
QUARTER_COL = re.compile(r"^\d{4}\s+Q\d$")

# 兩版數字視為相同的容差。每股盈利以美元計、通常兩位小數,
# 用 0.005 即「四捨五入到分位仍然一樣」,足以分辨真改寫與浮點雜訊。
TOLERANCE = 0.005


def load_sector_eps(path: Path) -> pd.DataFrame:
    """把 SECTOR EPS 分頁讀成 (區段, 行業, 季度) -> 每股盈利 的長表。

    區段 = 「營運盈利」定「公認會計準則盈利」那條分界線。表內同一批行業名
    在兩個區段各出現一次,所以鑰匙一定要連區段一齊,否則兩組數會溝埋。
    """
    raw = pd.read_excel(path, sheet_name=SHEET, header=None)

    col_labels: dict[int, str] = {}
    for col_idx in range(1, raw.shape[1]):
        label = raw.iat[HEADER_ROW, col_idx]
        if isinstance(label, str) and QUARTER_COL.match(label.strip()):
            col_labels[col_idx] = label.strip()

    records = []
    section = "(未標明)"
    for row_idx in range(HEADER_ROW + 1, len(raw)):
        row_label = raw.iat[row_idx, 0]
        if not isinstance(row_label, str) or not row_label.strip():
            continue
        row_label = row_label.strip()

        values = {
            col_idx: raw.iat[row_idx, col_idx]
            for col_idx in col_labels
            if isinstance(raw.iat[row_idx, col_idx], (int, float))
            and not isinstance(raw.iat[row_idx, col_idx], bool)
            and not (
                isinstance(raw.iat[row_idx, col_idx], float)
                and math.isnan(raw.iat[row_idx, col_idx])
            )
        }

        # 整行無數字 = 這是一條區段標題(例如「As Reported Earnings Per Share…」)
        if not values:
            if row_label.upper() != "INDEX NAME":
                section = row_label
            continue

        for col_idx, value in values.items():
            records.append(
                {
                    "section": section,
                    "index_name": row_label,
                    "quarter": col_labels[col_idx],
                    "value": float(value),
                }
            )
    return pd.DataFrame(records)


def main() -> None:
    old = load_sector_eps(OLD_FILE)
    new = load_sector_eps(NEW_FILE)

    key = ["section", "index_name", "quarter"]
    # 鑰匙必須唯一,否則 merge 會做笛卡兒積、把格數發大——先自證
    assert not old.duplicated(key).any(), "舊版鑰匙撞重複"
    assert not new.duplicated(key).any(), "新版鑰匙撞重複"

    merged = old.merge(new, on=key, suffixes=("_old", "_new"))
    merged["diff"] = (merged["value_old"] - merged["value_new"]).abs()
    changed = merged[merged["diff"] > TOLERANCE]

    worst = None
    if not merged.empty:
        top = merged.loc[merged["diff"].idxmax()]
        worst = {
            "section": top["section"],
            "index_name": top["index_name"],
            "quarter": top["quarter"],
            "old": round(float(top["value_old"]), 4),
            "new": round(float(top["value_new"]), 4),
            "diff": round(float(top["diff"]), 6),
        }

    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "old_vintage": OLD_FILE.name,
        "new_vintage": NEW_FILE.name,
        "sheet": SHEET,
        "compared": "只對『年份 + 季』的每股盈利欄;市盈率欄含價格,不在範圍",
        "tolerance": TOLERANCE,
        "sections": sorted(merged["section"].unique().tolist()),
        "cells_in_old": int(len(old)),
        "cells_in_new": int(len(new)),
        "overlapping_cells": int(len(merged)),
        "cells_changed": int(len(changed)),
        "changed_pct": round(100.0 * len(changed) / len(merged), 4) if len(merged) else None,
        "largest_gap": worst,
        "changed_samples": changed.head(10).to_dict("records"),
        "verdict": (
            "兩版重疊格全部一致 = 標普不改寫已公佈的歷史,存檔版本可當 point-in-time 用"
            if len(changed) == 0
            else "有格改動了,不可當 point-in-time,要逐格查改了什麼"
        ),
    }

    out_path = Path(__file__).parent / "sp_vintage_diff_result.json"
    out_path.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"舊版 {OLD_FILE.name}:{result['cells_in_old']} 格")
    print(f"新版 {NEW_FILE.name}:{result['cells_in_new']} 格")
    print(f"區段:{'、'.join(result['sections'])}")
    print(f"兩邊都有的:{result['overlapping_cells']} 格")
    print(f"對不上的:{result['cells_changed']} 格({result['changed_pct']}%)")
    if worst:
        print(
            f"最大差距:{worst['index_name']} / {worst['quarter']} "
            f"{worst['old']} -> {worst['new']}(差 {worst['diff']})"
        )
    print(result["verdict"])
    print(f"落檔:{out_path}")


if __name__ == "__main__":
    main()
