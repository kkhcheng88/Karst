# -*- coding: utf-8 -*-
"""KARST-173:先看清楚幾份原料的欄位(唯讀)。"""
from __future__ import annotations

import pathlib

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")


def show(name: str, df: pd.DataFrame, n: int = 3) -> None:
    print("===", name, df.shape)
    print(list(df.columns))
    print(df.head(n).to_string())


def main() -> None:
    show("entities", pd.read_parquet(REPO / "data" / "universe" / "entities.parquet"))
    show("ticker_periods", pd.read_parquet(REPO / "data" / "universe" / "ticker_periods.parquet"))
    show("smallcap_v1", pd.read_csv(REPO / "data" / "universe" / "universe_smallcap_v1.csv"))
    show("prices manifest", pd.read_csv(REPO / "data" / "prices" / "daily" / "manifest.csv"))
    show("tenbagger names",
         pd.read_csv(REPO / "experiments" / "2026-09-02-tenbagger-scan" / "out" /
                     "tenbagger_names.csv"))
    show("t0_cells",
         pd.read_parquet(REPO / "experiments" / "2026-09-02-tenbagger-scan" / "out" /
                         "t0_cells.parquet"))


if __name__ == "__main__":
    main()
