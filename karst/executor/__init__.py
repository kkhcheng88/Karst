"""策略合約與策略執行台(架構審視候選一,D-043)。

一條新策略只寫一份**策略合約**(``contract.py``);登記、驗參數、解析實體、叫引擎、
查重、落痕、算指標、判失敗運行全部住在**策略執行台**(``executor.py``)。

用法::

    from karst.executor import Executor, SAMPLE
    from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES, FactorMixContract

    contract = FactorMixContract(FACTOR_ETF_SLEEVES)
    executor = Executor(gateway, runs, snapshot_root=root)
    setup = executor.register(
        contract,
        strategy_name="因子混合(ETF 版)",
        snapshot_id=snapshot_id,
        param_set_name="示例-四等分季度",
        values={"weight_quality": "0.25", ..., "cadence": "quarterly"},
        alignment=SAMPLE,            # 未經與用戶對齊,不是現役設定(D-038)
    )
    outcome = executor.run(
        contract, setup=setup, panel=panel, period=period,
        engine_version="0.1.0", risk_free_rate=0.04,
    )
"""

from .contract import (
    ENGINE_PATHS,
    ENGINE_RULES,
    ENGINE_TARGETS,
    KIND_INTEGER,
    KIND_NUMBER,
    KIND_TEXT,
    PARAM_KINDS,
    PARAM_SLOTS,
    RISK_MAX_POSITION,
    RISK_MONTHLY_CAP,
    RISK_PER_TRADE,
    SLOT_CADENCE,
    SLOT_VALUE,
    SLUG_PERCENT,
    SLUG_STYLES,
    SLUG_VERBATIM,
    TEXT_AUTO,
    TEXT_EIGHT_PLACES,
    TEXT_FOUR_PLACES,
    TEXT_STYLES,
    TEXT_VERBATIM,
    DuplicateExposureEntity,
    EngineNameMismatch,
    EntityNotInPanel,
    EntityRequest,
    FactorSpec,
    FactorVersionRef,
    MissingParameter,
    MissingRequiredInput,
    ParameterOutOfRange,
    ParamField,
    ParamSpec,
    PlanShapeViolation,
    ResolvedEntity,
    RulePlan,
    RunRequest,
    StrategyContract,
    TargetPlan,
    UnknownParameter,
    UnresolvedTicker,
    display_text,
    field_slug,
    point_slug,
    risk_fields,
    value_slug,
    value_text,
)

# ``executor.py`` 遲到用的那一刻才 import。理由不是省時間,是**避免圈**:
# ``karst.engine.rules`` 要用本套件的值域檢查(五套純量驗證收成一份正本),
# 而 ``executor.py`` 自己又要用 ``karst.engine``;``contract.py`` 只 import
# ``karst.errors``,所以它永遠圈不起來,重的那一半留到有人真的叫 ``Executor``
# 才載(PEP 562)。
_LAZY: dict[str, str] = {
    "ALIGNED": "executor",
    "ALIGNMENTS": "executor",
    "SAMPLE": "executor",
    "Executor": "executor",
    "Rejudgement": "executor",
    "RunOutcome": "executor",
    "Setup": "executor",
    "Simulation": "executor",
    "as_period": "executor",
    "engine_for": "executor",
    "register_setup": "executor",
    "resolve_entities": "executor",
    "simulate_plan": "executor",
}


def __getattr__(name: str):
    module_name = _LAZY.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    value = getattr(import_module(f".{module_name}", __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY))


__all__ = [
    "ALIGNED",
    "ALIGNMENTS",
    "ENGINE_PATHS",
    "ENGINE_RULES",
    "ENGINE_TARGETS",
    "KIND_INTEGER",
    "KIND_NUMBER",
    "KIND_TEXT",
    "PARAM_KINDS",
    "PARAM_SLOTS",
    "RISK_MAX_POSITION",
    "RISK_MONTHLY_CAP",
    "RISK_PER_TRADE",
    "SAMPLE",
    "SLOT_CADENCE",
    "SLOT_VALUE",
    "SLUG_PERCENT",
    "SLUG_STYLES",
    "SLUG_VERBATIM",
    "TEXT_AUTO",
    "TEXT_EIGHT_PLACES",
    "TEXT_FOUR_PLACES",
    "TEXT_STYLES",
    "TEXT_VERBATIM",
    "DuplicateExposureEntity",
    "EngineNameMismatch",
    "EntityNotInPanel",
    "EntityRequest",
    "Executor",
    "FactorSpec",
    "FactorVersionRef",
    "MissingParameter",
    "MissingRequiredInput",
    "ParamField",
    "ParamSpec",
    "ParameterOutOfRange",
    "PlanShapeViolation",
    "Rejudgement",
    "ResolvedEntity",
    "RulePlan",
    "RunOutcome",
    "RunRequest",
    "Setup",
    "Simulation",
    "StrategyContract",
    "TargetPlan",
    "UnknownParameter",
    "UnresolvedTicker",
    "as_period",
    "display_text",
    "engine_for",
    "field_slug",
    "point_slug",
    "register_setup",
    "resolve_entities",
    "risk_fields",
    "simulate_plan",
    "value_slug",
    "value_text",
]
