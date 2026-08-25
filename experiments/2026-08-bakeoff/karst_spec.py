"""KARST-009 對決:兩個引擎共用的考題規格。

這個模組刻意只放「兩邊都必須一模一樣」的東西:資料路徑、宇宙大小、日期範圍、
參數網格、換倉日的定義。選股邏輯本身不放這裡——那正是本次要比較的東西,
必須各自用各自引擎的慣用寫法表達。
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

# ---- 考題規格(兩邊共用,不准各自改)----
SEED = 20260825
N_SYMBOLS = 500
START = "2016-01-04"
END = "2025-12-31"

INIT_CASH = 1_000_000.0

# 基準參數組(單次回測用)
BASE_N = 10
BASE_INTERVAL = 1  # 每 1 個月換倉
BASE_SMOOTH = 1  # 因子平滑窗(日)

# 參數掃描網格:40 × 5 × 5 = 1000 組
GRID_TOP_N = list(range(1, 41))
GRID_INTERVAL = [1, 2, 3, 4, 6]
GRID_SMOOTH = [1, 3, 5, 10, 21]

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
RESULT_DIR = os.path.join(HERE, "results")
PANEL_PATH = os.path.join(DATA_DIR, "panel.parquet")

SYMBOLS = [f"S{i:03d}" for i in range(N_SYMBOLS)]


def param_grid() -> list[dict]:
    """1000 組參數,次序固定,兩邊必須跑同一批。"""
    out = []
    for smooth in GRID_SMOOTH:
        for interval in GRID_INTERVAL:
            for top_n in GRID_TOP_N:
                out.append({"top_n": top_n, "interval": interval, "smooth": smooth})
    return out


def trading_days() -> pd.DatetimeIndex:
    return pd.bdate_range(START, END)


def load_panel() -> pd.DataFrame:
    """讀回長格式面板:一行 = (日期, 股票),欄位含 OHLCV 與 factor。

    這就是「自家資料層」的模擬形態:(日期, 股票) -> 因子值 的一張表。
    """
    return pd.read_parquet(PANEL_PATH)


def rebalance_dates(dates: pd.DatetimeIndex, interval: int) -> pd.DatetimeIndex:
    """每 interval 個月的第一個交易日 = 換倉日(訊號日)。"""
    s = pd.Series(np.arange(len(dates)), index=dates)
    first_of_month = np.sort(np.asarray(s.groupby([dates.year, dates.month]).min()))
    picked = first_of_month[::interval]
    return dates[picked]


def smooth_factor(wide_factor: pd.DataFrame, window: int) -> pd.DataFrame:
    """因子平滑:寬表 (日期 x 股票) 的滾動平均。兩邊語意必須一致。"""
    if window <= 1:
        return wide_factor
    return wide_factor.rolling(window, min_periods=1).mean()
