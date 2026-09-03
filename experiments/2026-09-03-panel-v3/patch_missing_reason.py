# -*- coding: utf-8 -*-
"""KARST-172 修正一格:分開「整份 companyfacts 沒有帳目」與「有帳目但沒有我們要的欄」。

建面板時,凡是找不到任何期末的實體一律記 `fpi_no_facts`,但其中有一批其實**有**
us-gaap 或 ifrs-full 區塊,只是沒有一條落在我們的標籤表與主要表格類型之內。
兩者是兩件事:前者是「這家公司在證監會的結構化帳目是空的」,後者是「我們的標籤表沒有覆蓋」。
把後者記成前者,會令下一個人以為是外國申報人的問題,而不是我們自己的標籤表問題。

本腳本只改 quarterly_v3.parquet 裡 period_end 為空那批列的 facts_status 與
<欄>_missing_reason,不動任何有數的列。
"""
from __future__ import annotations

import gzip
import json
import pathlib

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
CACHE = REPO / "data" / "sec" / "companyfacts"
V3 = REPO / "data" / "panel" / "quarterly_v3.parquet"


def main() -> None:
    panel = pd.read_parquet(V3)
    blank = panel["period_end"].isna()
    reason_cols = [c for c in panel.columns if c.endswith("_missing_reason")]
    changed = {"fpi_no_facts": 0, "tag_absent": 0, "fail": 0}
    for idx in panel.index[blank]:
        cik = panel.at[idx, "entity_id"]
        p = CACHE / f"CIK{cik}.json.gz"
        if not p.exists():
            reason, status = "fail", "fail"
        else:
            with gzip.open(p, "rb") as f:
                doc = json.load(f)
            facts = doc.get("facts") or {}
            has_acc = bool((facts.get("us-gaap") or {})) or bool((facts.get("ifrs-full") or {}))
            reason = "tag_absent" if has_acc else "fpi_no_facts"
            status = "no_usable_period" if has_acc else "empty"
        panel.at[idx, "facts_status"] = status
        for c in reason_cols:
            panel.at[idx, c] = reason
        changed[reason] += 1
    panel.to_parquet(V3, index=False, compression="zstd")
    print("改了", changed)
    print(panel.groupby("entity_id")["facts_status"].first().value_counts().to_string())


if __name__ == "__main__":
    main()
