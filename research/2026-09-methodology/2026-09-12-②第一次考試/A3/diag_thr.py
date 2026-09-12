# -*- coding: utf-8 -*-
"""看 thresholds_window.parquet 的欄位,供 s10 寫 thresholds.md 用。"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
w = pd.read_parquet(HERE / "cache" / "thresholds_window.parquet")
print(list(w.columns))
print(len(w))
print(w.head(3).to_string()[:700])
print(w.dtypes.to_dict())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
