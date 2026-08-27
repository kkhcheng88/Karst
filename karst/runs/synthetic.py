"""合成序列:引擎接上之前,用來走通留痕全程的假結果。

**這不是回測。**引擎票(KARST-023)接上之後,運行來源改為引擎交回來的真結果
——``RunStore.record_simulation`` 收的形狀就是引擎那個形狀,換源不用改留痕層。
在此之前,本檔產生一份形狀正確、內容假的結果,讓「落痕 → 讀回 → 開檢視視窗」
這條路今日就走得通、驗收得到。

同一個 ``seed`` 永遠產生同一條序列——留痕的驗收條件之一是「同一輸入得同一運行
編號」,序列本身若然每次不同就驗不到。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import numpy as np
import pandas as pd

from ..errors import ContractViolation
from ..models import as_date

# 假股價。合成序列不接行情,持倉股數要有個換算單位,寫死一個。
SYNTHETIC_PRICE = 100.0


@dataclass(frozen=True, slots=True)
class SyntheticSimulation:
    """一份假的運行結果,形狀與引擎適配層交回來的一模一樣。

    三件齊:逐日淨值、逐日持倉、逐筆交易。``RunStore.record_simulation``
    照收——它只看這三個欄位的名,不看是誰產生的。
    """

    equity_curve: pd.Series
    holdings: pd.DataFrame
    orders: pd.DataFrame
    engine_name: str = "synthetic"


def synthetic_simulation(
    *,
    start: date | datetime | str,
    end: date | datetime | str,
    entity_ids: tuple[int, ...],
    seed: int = 0,
    initial_cash: float = 100_000.0,
    drift: float = 0.0004,
    volatility: float = 0.01,
) -> SyntheticSimulation:
    """產生一份確定的假結果:平日排日曆,淨值隨機遊走,持倉等權不變。"""
    first = as_date(start, "start")
    last = as_date(end, "end")
    if last < first:
        raise ContractViolation(f"合成期間的結束日 {last} 早於開始日 {first}")
    ids = tuple(int(e) for e in entity_ids)
    if not ids:
        raise ContractViolation("合成序列要最少一個實體編號")

    days = pd.bdate_range(first, last)
    if len(days) < 2:
        raise ContractViolation(f"合成期間 {first}~{last} 不夠兩個交易日")

    rng = np.random.default_rng(int(seed))
    returns = rng.normal(float(drift), float(volatility), len(days))
    returns[0] = 0.0
    equity = pd.Series(
        float(initial_cash) * np.cumprod(1.0 + returns), index=days, name="equity"
    )

    shares_each = float(initial_cash) / len(ids) / SYNTHETIC_PRICE
    holdings = pd.DataFrame(
        [
            {"date": str(day.date()), "entity_id": entity_id, "shares": shares_each}
            for day in days
            for entity_id in ids
        ],
        columns=["date", "entity_id", "shares"],
    )
    orders = pd.DataFrame(
        [
            {
                "trade_date": str(days[0].date()),
                "entity_id": entity_id,
                "side": "buy",
                "shares": shares_each,
                "price": SYNTHETIC_PRICE,
                "fees": 0.0,
            }
            for entity_id in ids
        ]
        + [
            {
                "trade_date": str(days[-1].date()),
                "entity_id": entity_id,
                "side": "sell",
                "shares": shares_each,
                "price": SYNTHETIC_PRICE,
                "fees": 0.0,
            }
            for entity_id in ids
        ],
        columns=["trade_date", "entity_id", "side", "shares", "price", "fees"],
    )
    return SyntheticSimulation(equity_curve=equity, holdings=holdings, orders=orders)
