"""規則類策略路徑的門面:一句話跑完一次回測。

策略層只需要認得這一個函式與 ``rules.py`` 那幾個型別。哪個第三方引擎在背後跑、
怎樣餵它,全部收在適配層之內(D-007 第 3 條)。

    from karst.engine import (
        BarPanel, BreakoutEntry, SwingLowStop, MeasuredMoveTarget,
        RiskFractionSizing, MonthlyLossBreaker, RuleStrategyParams,
        run_rule_strategy,
    )

    params = RuleStrategyParams(
        entry=BreakoutEntry(lookback_days=20),
        stop=SwingLowStop(lookback_days=10, min_stop_fraction=0.01, max_stop_fraction=0.25),
        target=MeasuredMoveTarget(min_reward_risk=1.5),
        sizing=RiskFractionSizing(
            risk_per_trade=0.02,
            max_position_fraction=0.20,
            equity_basis="current_equity",     # 當下權益,不是起始本金
        ),
        breaker=MonthlyLossBreaker(max_monthly_drawdown=0.06),   # 寫 None 即關掉
        initial_cash=1_000_000.0,
        fees=0.0,
        tie_break_seed=20260828,
    )
    result = run_rule_strategy(panel=panel, params=params)

一個參數都沒有預設值:少寫一個即拋 ``TypeError``,寫 ``None`` 即拋
``ContractViolation``。引擎不代用戶決定風控門檻(D-008 第 3 條、D-009 第 7 條)。
"""

from __future__ import annotations

from ..errors import ContractViolation
from .protocol import RuleEngine
from .rules import BarPanel, RuleBacktestResult, RuleStrategyParams, build_rule_signals


def run_rule_strategy(
    *,
    panel: BarPanel,
    params: RuleStrategyParams,
    engine: RuleEngine | None = None,
) -> RuleBacktestResult:
    """五件規則一次過跑一次完整回測。

    ``engine`` 留空就用 vectorbt 的 ``from_order_func`` 路徑(規格 6.2)。傳別的
    進來即整件換走引擎——本函式與 ``rules.py`` 一字不用改(D-007 第 3 條)。
    """
    if not isinstance(panel, BarPanel):
        raise ContractViolation(
            f"K 線面板要是 BarPanel,收到 {type(panel).__name__};"
            "請先用 BarPanel.from_frames 核對開高低收四張表"
        )
    if not isinstance(params, RuleStrategyParams):
        raise ContractViolation(
            f"參數要是 RuleStrategyParams,收到 {type(params).__name__};五件規則一件都不可以省"
        )

    signals = build_rule_signals(panel, params)

    if engine is None:
        # 遲到這一刻才 import:換了引擎的人不需要裝 vectorbt(D-007 第 3 條)。
        from .vectorbt_engine import VectorbtRuleEngine

        engine = VectorbtRuleEngine()

    output = engine.simulate_rules(panel, signals, params)

    return RuleBacktestResult(
        equity_curve=output.equity_curve,
        holdings=output.holdings,
        cash=output.cash,
        sizing_basis=output.sizing_basis,
        breaker_blocked=output.breaker_blocked,
        orders=output.orders,
        params=params,
        entry_signals=signals.count,
        engine_name=getattr(engine, "name", type(engine).__name__),
    )


def run_rule_strategy_on_signal_matrix(
    *,
    panel: BarPanel,
    params: RuleStrategyParams,
) -> RuleBacktestResult:
    """**對照臂**:同一套規則改行訊號矩陣路徑(``from_signals``)。

    存在的唯一理由是查數:把注碼基數改回起始本金、熔斷關掉之後,兩條路應該算出
    同一個數。對得上,就證明「當下權益 vs 起始本金」那段差距是**基數本身**造成,
    不是實作誤差(規格 6.2、KARST-013)。

    熔斷開著、或者基數用當下權益,這條路根本表達不到,會當場拋
    ``RuleNotExpressible``——不會默默算個假數出來。
    """
    from .vectorbt_engine import VectorbtSignalMatrixEngine

    return run_rule_strategy(panel=panel, params=params, engine=VectorbtSignalMatrixEngine())
