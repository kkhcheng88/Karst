"""Karst 引擎適配層(engine adapter):兩條路徑。

策略層與資料層**完全不需要認識背後那個第三方引擎**(D-007 第 3 條、規格 6.3):

- **排名再平衡路徑**(``run_ranking_rebalance``)——每期按因子排名選前 N 隻等權。
- **規則類路徑**(``run_rule_strategy``)——進出場五件規則一次過表達:入場突破、
  止蝕、目標、注碼(基數取**當下權益**)、組合層月度虧損熔斷(規格 6.2)。

進出兩頭全部是 Karst 自己的型別:

    價格面板 PricePanel ─┐
    因子(單一定義庫按知情時間讀出)─┼─► run_ranking_rebalance ─► BacktestResult
    參數 RankingRebalanceParams ─┘                              (逐日淨值 / 逐日持倉 / 逐筆訂單)

換倉節奏沒有預設值,不指定即報錯(D-009 第 7 條)。可執行時點寫死:知情時點
之後的下一根可交易 K 線的開價(D-021 第 3 條)。

規則類路徑的用法見 ``rule_runner.py``;它的注碼基數與熔斷寫在看得見現金與權益
那一層,訊號矩陣路徑表達不到(規格 6.2 推翻 A-005)。

排名再平衡路徑用法:

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
from .protocol import PortfolioEngine, RuleEngine
from .rule_runner import run_rule_strategy, run_rule_strategy_on_signal_matrix
from .rules import (
    BAR_CONSISTENCY_TOLERANCE,
    EQUITY_BASES,
    EXIT_CODE_NONE,
    EXIT_CODE_REASONS,
    EXIT_CODE_STOP,
    EXIT_CODE_TARGET,
    EXIT_CODE_UNCLOSED,
    EXIT_REASONS,
    EXIT_STOP,
    EXIT_TARGET,
    EXIT_UNCLOSED,
    BarPanel,
    BreakoutEntry,
    ExitPlan,
    MeasuredMoveTarget,
    MonthlyLossBreaker,
    RiskFractionSizing,
    RuleBacktestResult,
    RuleNotExpressible,
    RuleNotSpecified,
    RuleSignals,
    RuleSimulationOutput,
    RuleStrategyParams,
    SwingLowStop,
    build_rule_signals,
    month_ids,
    resolve_exits,
)
from .runner import run_ranking_rebalance, target_weights
from .selection import build_targets, read_factor_panel

__all__ = [
    "BAR_CONSISTENCY_TOLERANCE",
    "CADENCES",
    "EQUITY_BASES",
    "EXIT_CODE_NONE",
    "EXIT_CODE_REASONS",
    "EXIT_CODE_STOP",
    "EXIT_CODE_TARGET",
    "EXIT_CODE_UNCLOSED",
    "EXIT_REASONS",
    "EXIT_STOP",
    "EXIT_TARGET",
    "EXIT_UNCLOSED",
    "ORDER_SIDES",
    "RANK_DIRECTIONS",
    "BacktestResult",
    "BarPanel",
    "BreakoutEntry",
    "CadenceNotSpecified",
    "ExitPlan",
    "MeasuredMoveTarget",
    "MonthlyLossBreaker",
    "Order",
    "PortfolioEngine",
    "PricePanel",
    "RankingRebalanceParams",
    "Rebalance",
    "RiskFractionSizing",
    "RuleBacktestResult",
    "RuleEngine",
    "RuleNotExpressible",
    "RuleNotSpecified",
    "RuleSignals",
    "RuleSimulationOutput",
    "RuleStrategyParams",
    "SimulationOutput",
    "SwingLowStop",
    "build_rule_signals",
    "build_targets",
    "decision_dates",
    "month_ids",
    "read_factor_panel",
    "rebalance_schedule",
    "resolve_exits",
    "run_ranking_rebalance",
    "run_rule_strategy",
    "run_rule_strategy_on_signal_matrix",
    "target_weights",
]
