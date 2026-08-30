"""把交易成本注入引擎參數之後,才交給真正的引擎跑。

策略那幾個參數型別(``strategies.factor_mix.FactorMixParams`` 一類)暫時只有舊的
``fees`` 一個數字,載不起「每股手續費」與「滑點」;而**策略計劃**(``TargetPlan``)
同樣不帶成本——成本入的是引擎參數,不是策略的決定。引擎本身是**可換件**
(D-007 第 3 條),所以成本由這一件薄薄的替換件補上去:它不改任何成績的算法,
只在參數交到引擎之前把成本那一格填好。

日後適配層補一個帶成本的組合參數型別(乙份設計叫它 ``TargetWeightsInput``),
這一件就可以整件刪走,呼叫方一個字不用改。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..errors import ContractViolation
from .contracts import TradingCosts

__all__ = ["CostedEngine"]


class CostedEngine:
    """包住一件引擎,在參數交出去之前補上交易成本。

    ``name`` 照抄被包住那件引擎——**引擎名是運行編號的一部分**,包一層不可以令它
    變成另一個名(否則同一件引擎會算出兩個編號,同一格帶成本與不帶成本以外還多
    出一種分岔)。
    """

    def __init__(self, costs: TradingCosts, engine: Any | None = None) -> None:
        if not isinstance(costs, TradingCosts):
            raise ContractViolation(
                f"交易成本要是 TradingCosts,收到 {type(costs).__name__}"
            )
        if engine is None:
            # 遲到這一刻才 import:換了引擎的人不需要裝 vectorbt(D-007 第 3 條)。
            from .vectorbt_engine import VectorbtEngine

            engine = VectorbtEngine()
        self._costs = costs
        self._engine = engine
        self.name = getattr(engine, "name", type(engine).__name__)

    @property
    def costs(self) -> TradingCosts:
        return self._costs

    def simulate(self, panel: Any, targets: Any, params: Any) -> Any:
        return self._engine.simulate(panel, targets, replace(params, costs=self._costs))
