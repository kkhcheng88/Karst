"""換倉節奏(rebalance cadence)換算成日子。

D-009 第 7 條:引擎必須節奏無關,**不設任何預設值**,每次執行由用戶指定
(用戶 2026-08-25 反問「Why we need a default?」)。本檔因此只有「把指定的節奏
換算成日子」的邏輯——全檔查不到任何預設節奏值。

一次換倉分**兩個**日子,不是一個(D-021 第 3 條可執行時點):

- **決策日**(decision date):看因子的那一日。知情時間閘定在該日收工,
  即「截至該日收工為止知道的一切」。
- **執行日**(execution date):決策日之後**下一根可交易 K 線**,成交價取該根的開價。

綁 K 線不綁時鐘:所謂「下一根」是價格面板裡的下一行,不是日曆的下一日。
"""

from __future__ import annotations

from typing import Final

import pandas as pd

from ..errors import ContractViolation
from .contracts import CADENCES

# 節奏 → pandas 期間代號。這是換算表,不是預設值。
_PERIOD_ALIAS: Final[dict[str, str]] = {"weekly": "W", "monthly": "M", "quarterly": "Q"}


def decision_dates(dates: pd.DatetimeIndex, cadence: str) -> pd.DatetimeIndex:
    """按節奏挑出決策日:每個週期的**最後一根**可交易 K 線。

    日度節奏即每一根 K 線都是決策日。
    """
    if cadence not in CADENCES:
        raise ContractViolation(f"換倉節奏只收 {sorted(CADENCES)},收到 {cadence!r}")
    if cadence == "daily":
        return dates
    periods = dates.to_period(_PERIOD_ALIAS[cadence])
    is_period_end = ~periods.duplicated(keep="last")
    return dates[is_period_end]


def rebalance_schedule(
    dates: pd.DatetimeIndex, cadence: str
) -> tuple[tuple[pd.Timestamp, pd.Timestamp], ...]:
    """排期:每個決策日配它之後下一根可交易 K 線做執行日。

    最後一個決策日若已經沒有下一根 K 線,那一次換倉**不做**——因子看得見,
    但成交不到,回測不可以當它成交過。
    """
    positions = {timestamp: position for position, timestamp in enumerate(dates)}
    schedule: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for decision_day in decision_dates(dates, cadence):
        position = positions[decision_day]
        if position + 1 < len(dates):
            schedule.append((decision_day, dates[position + 1]))
    return tuple(schedule)
