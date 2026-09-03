# -*- coding: utf-8 -*-
"""KARST-172:缺失原因分佈與面板欄位清單(唯讀)。"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
HERE = pathlib.Path(__file__).resolve().parent


def main() -> None:
    rep = json.loads((HERE / "out" / "coverage_report.json").read_text(encoding="utf-8"))
    print("=== missing_reason(全部列)===")
    print(json.dumps(rep["coverage"].get("missing_reason"), ensure_ascii=False, indent=1))
    p = pd.read_parquet(REPO / "data" / "panel" / "quarterly_v3.parquet")
    print("=== 欄位 ===")
    print(len(p.columns), list(p.columns))
    print("=== 檔案大小 ===")
    f = REPO / "data" / "panel" / "quarterly_v3.parquet"
    print(f.stat().st_size)


if __name__ == "__main__":
    main()
