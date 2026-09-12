# -*- coding: utf-8 -*-
"""票 A″ 第 10 步後檢查:84 個取證包的季數、遮罩、越界列數、欄位齊全。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
log = pd.read_csv(HERE / "cache" / "packets_log.csv")
print("包數:", len(log), "| n_quarters 分佈:",
      log["n_quarters"].value_counts().to_dict())
print("遮罩不合:", int((~log["ok"]).sum()))
print("替補:", int((log["replaces"].fillna("") != "").sum()))
n_leak = []
keys_bad = []
for p in sorted((HERE / "packets").glob("*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    f4 = d["4_財務數列"]
    n_leak.append(f4["n_rows_first_filed_after_T1"])
    for k in ("1_事件識別", "2_觸發資料", "3_截止前文件", "4_財務數列", "5_同業與行業",
              "6_價格狀態", "7_共識", "masking_check"):
        if k not in d:
            keys_bad.append((p.name, k))
print("每包越界列(最早申報晚於 T1 的列)分佈:", pd.Series(n_leak).value_counts().to_dict())
print("缺欄位:", keys_bad[:5])
print("packets/ 檔數:", len(list((HERE / "packets").glob("*.json"))))
