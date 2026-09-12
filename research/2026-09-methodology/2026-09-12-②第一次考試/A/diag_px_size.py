# -*- coding: utf-8 -*-
"""診斷:價格面板的列數、切檔方式(entity 分檔 or 日期分檔)與單檔記憶體。"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
PRICES = ROOT / "data" / "prices" / "daily"


def main() -> None:
    parts = sorted(PRICES.glob("part_*.parquet"))
    print("檔數", len(parts))
    tot = 0
    for p in parts:
        d = pd.read_parquet(p, columns=["entity_id", "date", "series_role"])
        n = len(d)
        tot += n
        print("%s rows=%d entities=%d daterange=%s..%s roles=%s" % (
            p.name, n, d["entity_id"].nunique(), d["date"].min(), d["date"].max(),
            d["series_role"].value_counts().to_dict()))
        del d
    print("總列數", tot)
    d = pd.read_parquet(parts[0], columns=["entity_id", "date", "adj_close", "close",
                                           "volume", "series_role"])
    print("單檔深拷貝記憶體 MB", round(d.memory_usage(deep=True).sum() / 1e6, 1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
