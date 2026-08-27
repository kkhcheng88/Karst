"""Karst 策略層(strategies):把一套策略的語意寫成碼。

策略層只認得引擎適配層的介面與單一定義庫的 API,**不認得任何第三方引擎**
(D-007 第 3 條)。因此本套件下的檔案一個都不准 ``import vectorbt``。

本套件現有:

- ``factor_mix`` —— 因子混合策略(factor-mix strategy)的 ETF 版(D-012、規格 5.2):
  質素、價值、動能、低波四類因子敞口,各買一隻現成因子 ETF,按參數集指定的
  權重混成一個組合,經適配層 A 的**目標比重路徑**跑回測。

刻意不在 ``karst/__init__.py`` 掛出:``import karst`` 之後引擎連載都未載,
本套件亦然——要用才 ``from karst.strategies.factor_mix import ...``。
"""

from .factor_mix import (
    FACTOR_ETF_SLEEVES,
    FactorExposure,
    FactorMixParams,
    FactorMixRebalance,
    FactorMixResult,
    FactorSleeve,
    factor_mix_schedule,
    factor_mix_targets,
    record_factor_mix_run,
    register_factor_mix,
    resolve_exposures,
    run_factor_mix,
)

__all__ = [
    "FACTOR_ETF_SLEEVES",
    "FactorExposure",
    "FactorMixParams",
    "FactorMixRebalance",
    "FactorMixResult",
    "FactorSleeve",
    "factor_mix_schedule",
    "factor_mix_targets",
    "record_factor_mix_run",
    "register_factor_mix",
    "resolve_exposures",
    "run_factor_mix",
]
