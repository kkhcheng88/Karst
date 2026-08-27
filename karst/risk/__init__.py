"""共用風控層(shared risk layer):三條規則,全平台一份定義。

D-013 第 4 條、規格 1.6:單筆風險上限、月度虧損熔斷、風險回報比(賠率)門檻抽成
平台層面所有策略共用的一層;每個策略**可用可不用、參數自設**,定義只有一個正本。

    from karst.risk import RiskSettings, build_rule_params, register_risk_layer

    register_risk_layer(store)                      # 三條規則登記入庫,只此一份

    risk = RiskSettings(                            # 這套策略的取值,無預設值
        per_trade_risk=0.02,                        # 單筆風險上限
        monthly_loss_cap=0.06,                      # 月度虧損熔斷
        reward_risk_floor=1.5,                      # 賠率門檻
    )
    params = build_rule_params(                     # 餵入引擎那五件既有規則型別
        risk=risk,
        entry=BreakoutEntry(lookback_days=40),
        stop=SwingLowStop(lookback_days=10, min_stop_fraction=0.01, max_stop_fraction=0.25),
        max_position_fraction=0.25,
        equity_basis="current_equity",
        initial_cash=1_000_000.0,
        fees=0.0,
        tie_break_seed=20260828,
    )
    result = run_rule_strategy(panel=panel, params=params)

不引用的策略照樣跑:目標比重路徑(``run_ranking_rebalance``)本來就不經本層,
不會因為沒有風控參數而報錯。三條規則的取值全部可掃描,見 ``sweep_risk_settings``。
"""

from .layer import (
    RISK_PARAM_PREFIX,
    RISK_RULES,
    RULES_BY_PARAM_KEY,
    RiskRule,
    RiskRuleNotReferenced,
    RiskSettings,
    build_rule_params,
    get_risk_rule,
    read_risk_settings,
)
from .registry import (
    referenced_rule_keys,
    reference_risk_rules,
    register_risk_layer,
    risk_settings_of,
)
from .sweep import (
    SWEEP_COLUMNS,
    RiskSweepCell,
    RiskSweepGrid,
    RiskSweepResult,
    sweep_grid,
    sweep_risk_settings,
)

__all__ = [
    "RISK_PARAM_PREFIX",
    "RISK_RULES",
    "RULES_BY_PARAM_KEY",
    "SWEEP_COLUMNS",
    "RiskRule",
    "RiskRuleNotReferenced",
    "RiskSettings",
    "RiskSweepCell",
    "RiskSweepGrid",
    "RiskSweepResult",
    "build_rule_params",
    "get_risk_rule",
    "read_risk_settings",
    "reference_risk_rules",
    "referenced_rule_keys",
    "register_risk_layer",
    "risk_settings_of",
    "sweep_grid",
    "sweep_risk_settings",
]
