"""排名再平衡路徑的門面:一句話跑完一次回測。

策略層只需要認得這一個函式與 ``contracts.py`` 那幾個型別。哪個第三方引擎在
背後跑、怎樣餵它,全部收在適配層之內(D-007 第 3 條)。
"""

from __future__ import annotations

import pandas as pd

from ..errors import ContractViolation
from ..store import DefinitionStore
from .cadence import rebalance_schedule
from .contracts import BacktestResult, PricePanel, RankingRebalanceParams
from .protocol import PortfolioEngine
from .selection import build_targets, read_factor_panel


def run_ranking_rebalance(
    *,
    store: DefinitionStore,
    panel: PricePanel,
    factor_name: str,
    cadence: str,
    top_n: int,
    direction: str,
    version_no: int | None = None,
    initial_cash: float = 100_000.0,
    fees: float = 0.0,
    engine: PortfolioEngine | None = None,
) -> BacktestResult:
    """每期按因子排名選前 ``top_n`` 隻等權再平衡,跑出一次完整回測。

    ``cadence`` 刻意**沒有預設值**:不寫即拋 ``TypeError``,寫 ``None`` 或空白
    即拋 ``CadenceNotSpecified``。引擎不代用戶決定換倉節奏(D-009 第 7 條)。

    ``top_n`` 與 ``direction`` 是可掃描參數:掃描一組參數只需重覆呼叫本函式,
    不用改一行碼(D-008 第 3 條)。

    ``engine`` 留空就用 vectorbt(D-011)。傳別的進來即整件換走引擎——本函式
    與 ``contracts.py`` 一字不用改(D-007 第 3 條)。
    """
    params = RankingRebalanceParams(
        cadence=cadence,
        top_n=top_n,
        direction=direction,
        initial_cash=initial_cash,
        fees=fees,
    )
    if not isinstance(panel, PricePanel):
        raise ContractViolation(
            f"價格面板要是 PricePanel,收到 {type(panel).__name__};"
            "請先用 PricePanel.from_frames 核對開價表與收價表"
        )

    version = store.get_factor_version(factor_name, version_no)

    schedule = rebalance_schedule(panel.dates, params.cadence)
    if not schedule:
        raise ContractViolation(
            f"這個價格面板({len(panel.dates)} 根 K 線)按「{params.cadence}」節奏排不出一次換倉:"
            "每次換倉要有決策日,還要有它之後的下一根 K 線可以成交"
        )

    factor_panel = read_factor_panel(
        store,
        factor_name,
        [decision_day for decision_day, _ in schedule],
        version_no=version_no,
        entity_ids=panel.entity_ids,
    )
    targets, rebalances = build_targets(
        dates=panel.dates,
        factor_panel=factor_panel,
        schedule=schedule,
        params=params,
        entity_ids=panel.entity_ids,
    )

    if engine is None:
        # 遲到這一刻才 import:換了引擎的人不需要裝 vectorbt(D-007 第 3 條)。
        from .vectorbt_engine import VectorbtEngine

        engine = VectorbtEngine()

    output = engine.simulate(panel, targets, params)

    return BacktestResult(
        equity_curve=output.equity_curve,
        holdings=output.holdings,
        orders=output.orders,
        rebalances=rebalances,
        params=params,
        factor_name=version.name,
        factor_version_id=version.factor_version_id,
        engine_name=getattr(engine, "name", type(engine).__name__),
    )


def target_weights(
    *,
    store: DefinitionStore,
    panel: PricePanel,
    factor_name: str,
    cadence: str,
    top_n: int,
    direction: str,
    version_no: int | None = None,
) -> tuple[pd.DataFrame, tuple]:
    """只算目標比重表與換倉帳,不跑引擎。查帳與寫測試時用。"""
    params = RankingRebalanceParams(cadence=cadence, top_n=top_n, direction=direction)
    schedule = rebalance_schedule(panel.dates, params.cadence)
    factor_panel = read_factor_panel(
        store,
        factor_name,
        [decision_day for decision_day, _ in schedule],
        version_no=version_no,
        entity_ids=panel.entity_ids,
    )
    return build_targets(
        dates=panel.dates,
        factor_panel=factor_panel,
        schedule=schedule,
        params=params,
        entity_ids=panel.entity_ids,
    )
