"""共用風控層(shared risk layer)的定義正本:三條規則,全平台只有這一份。

D-013 第 4 條:單筆風險上限、月度虧損熔斷、風險回報比(賠率)門檻是**平台層面
所有策略共用**的風控規則;策略可用可不用、參數自設,定義單一正本。本檔就是那份
正本——三條規則叫什麼、管什麼、參數叫什麼名、取值容許在什麼範圍,只寫在這裡。

三條規則:

1. **單筆風險上限** ``per_trade_risk``——一筆交易最多押注碼基數的幾多。
   注碼基數是當日開市的當下權益(CONTEXT.md「注碼基數」),不是起始本金。
2. **月度虧損熔斷** ``monthly_loss_cap``——月內權益由月初起計跌穿門檻,即停止
   該月新入場,已有持倉照原規則管理(CONTEXT.md「月度虧損熔斷」)。
3. **賠率門檻** ``reward_risk_floor``——(目標 − 入場)/(入場 − 止蝕)低過這個
   倍數就不入場。

**本層只管定義,不管取值。** 取值屬用戶領域,一律做成可掃描的參數住在該策略自己
的參數集(param set)裡(D-008);本層不裁定亦不優化任何一個數,更加沒有預設值——
缺就當場拋錯,不代用戶決定(D-008 第 3 條)。

**與引擎那五件規則型別的關係**:``karst.engine.rules`` 那五件是**執行機制**——
引擎逐根 K 線怎樣落單。本層是**規則定義**——這條風控規則是什麼。兩者不重覆:
風控取值只有一條路進得了引擎,就是 ``build_rule_params`` / ``RiskSettings.apply``;
策略碼不會自己再寫一次這三個數。引擎型別建構時照樣自檢,那是防線,不是第二份定義。

不屬本層的:單一持倉市值上限、注碼基數取誰、入場突破、止蝕波段——本票明文只抽
三類,不新增規則種類。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Final

import numpy as np

from ..engine.rules import (
    BreakoutEntry,
    MeasuredMoveTarget,
    MonthlyLossBreaker,
    RiskFractionSizing,
    RuleStrategyParams,
    SwingLowStop,
)
from ..errors import ContractViolation

# 參數集內風控參數的字首:一望即知這個數來自共用風控層,不是策略自己的參數。
RISK_PARAM_PREFIX: Final[str] = "risk."


class RiskRuleNotReferenced(ContractViolation):
    """規則路徑要用到某條風控規則,但這套策略沒有引用它(沒有給取值)。

    不引用是可以的——但那就要走目標比重路徑(適配層 A),那條路本來就無風控。
    走規則路徑而不給值,不會有預設值頂上,只會當場拋錯。
    """


@dataclass(frozen=True, slots=True)
class RiskRule:
    """一條共用風控規則的定義。三條規則各一個實例,住在 ``RISK_RULES``。

    - ``key`` 程式裡的名,同時是 ``RiskSettings`` 的欄名。
    - ``param_key`` 這條規則的取值在參數集內叫什麼(帶 ``risk.`` 字首)。
    - ``lower`` / ``upper`` 取值容許範圍,兩邊都不含;``upper`` 為 ``None`` 即無上限。
    """

    key: str
    name: str
    english: str
    param_key: str
    unit: str
    lower: float
    upper: float | None
    what: str

    def check(self, value: Any) -> float:
        """驗一個取值。過得到就回一個 float,過不到即拋 ``ContractViolation``。"""
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ContractViolation(
                f"{self.name}({self.param_key})要是一個數,收到 {value!r}"
            ) from exc
        if not np.isfinite(number):
            raise ContractViolation(f"{self.name}({self.param_key})要是有限數,收到 {value!r}")
        if number <= self.lower or (self.upper is not None and number >= self.upper):
            ceiling = "無上限" if self.upper is None else f"細過 {self.upper}"
            raise ContractViolation(
                f"{self.name}({self.param_key})要{self.unit}、大過 {self.lower}、{ceiling},"
                f"收到 {value!r}"
            )
        return number


_RULES: Final[tuple[RiskRule, ...]] = (
    RiskRule(
        key="per_trade_risk",
        name="單筆風險上限",
        english="per-trade risk cap",
        param_key=f"{RISK_PARAM_PREFIX}per_trade_risk",
        unit="是比例",
        lower=0.0,
        upper=1.0,
        what="一筆交易最多押注碼基數的幾多;注碼基數是當日開市的當下權益,不是起始本金",
    ),
    RiskRule(
        key="monthly_loss_cap",
        name="月度虧損熔斷",
        english="monthly loss breaker",
        param_key=f"{RISK_PARAM_PREFIX}monthly_loss_cap",
        unit="是比例",
        lower=0.0,
        upper=1.0,
        what="月內權益由月初起計跌穿這個幅度,即停止該月新入場,已有持倉照原規則管理",
    ),
    RiskRule(
        key="reward_risk_floor",
        name="賠率門檻",
        english="reward-risk floor",
        param_key=f"{RISK_PARAM_PREFIX}reward_risk_floor",
        unit="是倍數",
        lower=0.0,
        upper=None,
        what="(目標 − 入場)/(入場 − 止蝕)低過這個倍數就不入場",
    ),
)

# 三條規則的正本索引。全平台引用這一份,不另抄一份(D-002 第 4 條單一定義)。
RISK_RULES: Final[Mapping[str, RiskRule]] = MappingProxyType({rule.key: rule for rule in _RULES})

# 參數集裡的參數名 → 規則,由參數集讀回取值時用。
RULES_BY_PARAM_KEY: Final[Mapping[str, RiskRule]] = MappingProxyType(
    {rule.param_key: rule for rule in _RULES}
)


def get_risk_rule(key: str) -> RiskRule:
    """按程式名取一條風控規則的定義。查不到即拋錯,不猜。"""
    try:
        return RISK_RULES[str(key).strip()]
    except KeyError as exc:
        raise ContractViolation(
            f"共用風控層只有 {sorted(RISK_RULES)} 三條規則,收到 {key!r};本層不新增規則種類"
        ) from exc


@dataclass(frozen=True, slots=True)
class RiskSettings:
    """一套策略對三條共用風控規則各自所設的取值。

    三格皆**無預設值**:要用就明寫一個數,不用就明寫 ``None``。寫 ``None`` 即
    「這套策略不引用這條規則」——不是關掉之後仍然算數,是根本沒有這一格。

    定義只有一份(``RISK_RULES``),取值一策略一份:改一套策略的取值,不會動到
    另一套(D-013 第 4 條)。
    """

    per_trade_risk: float | None
    monthly_loss_cap: float | None
    reward_risk_floor: float | None

    def __post_init__(self) -> None:
        for rule in _RULES:
            value = getattr(self, rule.key)
            if value is None:
                continue
            object.__setattr__(self, rule.key, rule.check(value))

    @property
    def referenced(self) -> tuple[RiskRule, ...]:
        """這套策略實際引用了哪幾條規則(有給取值的那幾條)。"""
        return tuple(rule for rule in _RULES if getattr(self, rule.key) is not None)

    @property
    def referenced_keys(self) -> tuple[str, ...]:
        return tuple(rule.key for rule in self.referenced)

    def value_of(self, key: str) -> float | None:
        """取某條規則的值;沒有引用即 ``None``。"""
        return getattr(self, get_risk_rule(key).key)

    def to_param_values(self) -> dict[str, str]:
        """攤成參數集寫得入的「參數名→值」。沒有引用的規則不會出現一格。"""
        return {
            rule.param_key: repr(float(getattr(self, rule.key)))
            for rule in self.referenced
        }

    @classmethod
    def from_param_values(cls, values: Mapping[str, Any]) -> "RiskSettings":
        """由一個參數集的「參數名→值」讀回風控取值。

        參數集裡的其他參數一概不理;缺哪一格就是沒有引用那一條規則。
        """
        items = dict(values or {})
        return cls(
            **{
                rule.key: (items[rule.param_key] if rule.param_key in items else None)
                for rule in _RULES
            }
        )

    def require(self, *keys: str) -> None:
        """點名幾條規則:有一條沒有引用即拋 ``RiskRuleNotReferenced``。"""
        missing = [get_risk_rule(key) for key in keys if getattr(self, get_risk_rule(key).key) is None]
        if missing:
            raise RiskRuleNotReferenced(
                "這套策略沒有引用:"
                + "、".join(f"{rule.name}({rule.param_key})" for rule in missing)
                + ";規則路徑一定要這幾條,不設預設值。不用風控層的策略請走目標比重路徑"
            )

    def apply(self, params: RuleStrategyParams) -> RuleStrategyParams:
        """把本設定的三個取值換入一份既有的規則參數,回傳新的一份(原本那份不變)。

        掃描時就是靠這一格:同一份參數,只換三個風控數,其餘一字不動。
        """
        if not isinstance(params, RuleStrategyParams):
            raise ContractViolation(
                f"要是 RuleStrategyParams,收到 {type(params).__name__}"
            )
        self.require("per_trade_risk", "reward_risk_floor")
        return replace(
            params,
            target=replace(params.target, min_reward_risk=self.reward_risk_floor),
            sizing=replace(params.sizing, risk_per_trade=self.per_trade_risk),
            breaker=(
                None
                if self.monthly_loss_cap is None
                else MonthlyLossBreaker(max_monthly_drawdown=self.monthly_loss_cap)
            ),
        )


def build_rule_params(
    *,
    risk: RiskSettings,
    entry: BreakoutEntry,
    stop: SwingLowStop,
    max_position_fraction: float,
    equity_basis: str,
    initial_cash: float,
    fees: float,
    tie_break_seed: int,
) -> RuleStrategyParams:
    """把風控層的取值餵入引擎那五件既有規則型別,砌出一份可以直接跑的參數。

    這是三個風控數進入引擎的**唯一一條路**:策略碼不會自己再寫一次單筆風險、
    熔斷門檻或賠率門檻,所以庫內外都只有一份定義(D-002 第 4 條)。

    其餘幾格(入場突破、止蝕波段、單一持倉市值上限、注碼基數取誰、本金、費用、
    抽籤種子)是策略自己那一份,本層不管。

    月度熔斷沒有引用即傳 ``None`` 落引擎——明寫關掉,不是靜靜當它是 0。
    """
    if not isinstance(risk, RiskSettings):
        raise ContractViolation(f"風控設定要是 RiskSettings,收到 {type(risk).__name__}")
    risk.require("per_trade_risk", "reward_risk_floor")

    return RuleStrategyParams(
        entry=entry,
        stop=stop,
        target=MeasuredMoveTarget(min_reward_risk=risk.reward_risk_floor),
        sizing=RiskFractionSizing(
            risk_per_trade=risk.per_trade_risk,
            max_position_fraction=max_position_fraction,
            equity_basis=equity_basis,
        ),
        breaker=(
            None
            if risk.monthly_loss_cap is None
            else MonthlyLossBreaker(max_monthly_drawdown=risk.monthly_loss_cap)
        ),
        initial_cash=initial_cash,
        fees=fees,
        tie_break_seed=tie_break_seed,
    )


def read_risk_settings(params: RuleStrategyParams) -> RiskSettings:
    """由一份規則參數讀回它現時帶住的三個風控取值(查帳與掃描落檔時用)。"""
    if not isinstance(params, RuleStrategyParams):
        raise ContractViolation(f"要是 RuleStrategyParams,收到 {type(params).__name__}")
    return RiskSettings(
        per_trade_risk=params.sizing.risk_per_trade,
        monthly_loss_cap=(None if params.breaker is None else params.breaker.max_monthly_drawdown),
        reward_risk_floor=params.target.min_reward_risk,
    )
