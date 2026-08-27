"""Karst 引擎適配層(engine adapter):排名再平衡路徑。

「每期按因子排名選前 N 隻等權再平衡」這一類策略由此跑得出回測,而策略層與
資料層**完全不需要認識背後那個第三方引擎**(D-007 第 3 條、規格 6.3)。

進出兩頭全部是 Karst 自己的型別:

    價格面板 PricePanel ─┐
    因子(單一定義庫按知情時間讀出)─┼─► run_ranking_rebalance ─► BacktestResult
    參數 RankingRebalanceParams ─┘                              (逐日淨值 / 逐日持倉 / 逐筆訂單)

換倉節奏沒有預設值,不指定即報錯(D-009 第 7 條)。可執行時點寫死:知情時點
之後的下一根可交易 K 線的開價(D-021 第 3 條)。

帶組合層風控的規則類策略走另一條路(``from_order_func``,規格 6.2),不在本層。

用法:

    from karst import DefinitionStore
    from karst.engine import PricePanel, run_ranking_rebalance

    panel = PricePanel.from_frames(open=opens, close=closes)
    result = run_ranking_rebalance(
        store=store,
        panel=panel,
        factor_name="動量·12-1 月",
        cadence="monthly",   # 無預設,一定要寫
        top_n=10,
        direction="high",
    )
    result.equity_curve      # 逐日淨值
    result.holdings          # 逐日持倉
    result.orders_frame()    # 逐筆訂單
"""

from .cadence import decision_dates, rebalance_schedule
from .contracts import (
    CADENCES,
    ORDER_SIDES,
    RANK_DIRECTIONS,
    BacktestResult,
    CadenceNotSpecified,
    Order,
    PricePanel,
    RankingRebalanceParams,
    Rebalance,
    SimulationOutput,
)
from .protocol import PortfolioEngine
from .runner import run_ranking_rebalance, target_weights
from .selection import build_targets, read_factor_panel

__all__ = [
    "CADENCES",
    "ORDER_SIDES",
    "RANK_DIRECTIONS",
    "BacktestResult",
    "CadenceNotSpecified",
    "Order",
    "PortfolioEngine",
    "PricePanel",
    "RankingRebalanceParams",
    "Rebalance",
    "SimulationOutput",
    "build_targets",
    "decision_dates",
    "read_factor_panel",
    "rebalance_schedule",
    "run_ranking_rebalance",
    "target_weights",
]
