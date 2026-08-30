"""Karst 策略層(strategies):把一套策略的語意寫成碼。

策略層只認得引擎適配層的介面與單一定義庫的 API,**不認得任何第三方引擎**
(D-007 第 3 條)。因此本套件下的檔案一個都不准 ``import vectorbt``。

本套件現有:

- ``factor_mix`` —— 因子混合策略(factor-mix strategy)的 ETF 版(D-012、規格 5.2):
  質素、價值、動能、低波四類因子敞口,各買一隻現成因子 ETF,按參數集指定的
  權重混成一個組合,經適配層 A 的**目標比重路徑**跑回測。
- ``trend_swing`` —— 趨勢波段策略(trend swing strategy)(D-016、規格 5.4):
  突破 N 日新高入場、前波段低位止蝕、量度移動目標、賠率門檻,加共用風控層,
  經適配層的**規則路徑**跑回測;另交一張入場規則的歷史案例表。

刻意不在 ``karst/__init__.py`` 掛出:``import karst`` 之後引擎連載都未載,
本套件亦然——要用才 ``from karst.strategies.factor_mix import ...``。
"""

from .factor_mix import (
    CADENCE_PARAM,
    FACTOR_ETF_SLEEVES,
    FactorExposure,
    FactorMixContract,
    FactorMixParams,
    FactorMixRebalance,
    FactorMixResult,
    FactorSleeve,
    factor_exposures,
    factor_mix_schedule,
    factor_mix_targets,
    resolve_exposures,
    run_factor_mix,
)
from .trend_swing import (
    BREAKOUT_FACTOR_NAME,
    CaseStats,
    EntryCase,
    TrendSwingParams,
    TrendSwingResult,
    TrendSwingSweepResult,
    build_bar_panel,
    case_stats,
    cases_frame,
    entry_cases,
    param_values,
    params_grid,
    read_setup,
    record_trend_swing_run,
    register_trend_swing,
    run_trend_swing,
    sweep_trend_swing,
)

__all__ = [
    "BREAKOUT_FACTOR_NAME",
    "CaseStats",
    "EntryCase",
    "TrendSwingParams",
    "TrendSwingResult",
    "TrendSwingSweepResult",
    "build_bar_panel",
    "case_stats",
    "cases_frame",
    "entry_cases",
    "param_values",
    "params_grid",
    "read_setup",
    "record_trend_swing_run",
    "register_trend_swing",
    "run_trend_swing",
    "sweep_trend_swing",
    "CADENCE_PARAM",
    "FACTOR_ETF_SLEEVES",
    "FactorExposure",
    "FactorMixContract",
    "FactorMixParams",
    "FactorMixRebalance",
    "FactorMixResult",
    "FactorSleeve",
    "factor_exposures",
    "factor_mix_schedule",
    "factor_mix_targets",
    "resolve_exposures",
    "run_factor_mix",
]
