"""引擎介面的「動詞」那一半:一個可換件的組合模擬器要做到什麼。

D-007 第 3 條:核心回測引擎必須隔離在自家介面之後,**引擎是可換件**,日後
換走不用重寫語意層。凡實作得到本協定的東西都插得進來——策略層與資料層不會
察覺換了誰,因為進出兩頭都只有 Karst 自己的型別。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

from .contracts import PricePanel, RankingRebalanceParams, SimulationOutput


@runtime_checkable
class PortfolioEngine(Protocol):
    """組合模擬器:收目標比重表,回逐日淨值、逐日持倉、逐筆訂單。"""

    name: str

    def simulate(
        self,
        panel: PricePanel,
        targets: pd.DataFrame,
        params: RankingRebalanceParams,
    ) -> SimulationOutput:
        """跑一次模擬。

        ``targets`` 是「日期 × 實體編號 → 目標比重」;``NaN`` 代表那一根 K 線
        不下單,0 代表清倉到零。成交價一律取執行日那根 K 線的**開價**
        (D-021 第 3 條,實作方不得自行改成收價)。
        """
        ...
