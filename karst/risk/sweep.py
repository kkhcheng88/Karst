"""三條風控規則的參數掃描:一次交出多組取值的成績。

D-008 第 3 條:平台對策略內部數值的責任形態是**做成可掃描的參數,支援用戶自己
實驗**——不裁定、不優化任何一個取值。本檔就是那一格:給一份規則參數同一個
取值格,逐格跑一次回測,交回一張可以直接看的表。

評估準則不在本檔。哪一格算好、是不是孤峰,按 D-016「參數穩健平原」由用戶自己看
那張表定奪;本層一個「最優」都不替他揀。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import product

import pandas as pd

from ..engine.protocol import RuleEngine
from ..engine.rule_runner import run_rule_strategy
from ..engine.rules import BarPanel, RuleStrategyParams
from ..errors import ContractViolation
from .layer import RISK_RULES, RiskSettings

# 掃描結果那張表的欄:三條規則的取值 + 六格成績。
SWEEP_COLUMNS: tuple[str, ...] = (
    "per_trade_risk",
    "monthly_loss_cap",
    "reward_risk_floor",
    "entry_signals",
    "orders",
    "total_return",
    "max_drawdown",
    "worst_month_drawdown",
    "blocked_days",
)


def _values(
    raw: Iterable[float | None], key: str, *, allow_none: bool
) -> tuple[float | None, ...]:
    rule = RISK_RULES[key]
    items = list(raw)
    if not items:
        raise ContractViolation(
            f"{rule.name}({rule.param_key})的掃描取值一個都沒有;掃描不設預設值,要掃哪幾個一律寫明"
        )
    cleaned: list[float | None] = []
    for item in items:
        if item is None:
            if not allow_none:
                raise ContractViolation(
                    f"{rule.name}({rule.param_key})不可以掃 None:規則路徑一定要這一條。"
                    "不用風控層的策略請走目標比重路徑"
                )
            cleaned.append(None)
            continue
        cleaned.append(rule.check(item))
    if len(set(cleaned)) != len(cleaned):
        raise ContractViolation(f"{rule.name}({rule.param_key})的掃描取值有重複")
    return tuple(cleaned)


@dataclass(frozen=True, slots=True)
class RiskSweepGrid:
    """一次掃描要走的取值格:三條規則各給一串取值,逐格砌成組合。

    ``monthly_loss_cap`` 可以放 ``None``——那一格就是「這次不引用熔斷」,
    掃描表之內直接比得到「開熔斷 vs 不開」。另外兩條規則路徑一定要,不收 ``None``。

    **無預設值**:三串取值一串都不可以省。
    """

    per_trade_risk: tuple[float, ...]
    monthly_loss_cap: tuple[float | None, ...]
    reward_risk_floor: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "per_trade_risk", _values(self.per_trade_risk, "per_trade_risk", allow_none=False)
        )
        object.__setattr__(
            self,
            "monthly_loss_cap",
            _values(self.monthly_loss_cap, "monthly_loss_cap", allow_none=True),
        )
        object.__setattr__(
            self,
            "reward_risk_floor",
            _values(self.reward_risk_floor, "reward_risk_floor", allow_none=False),
        )

    def settings(self) -> tuple[RiskSettings, ...]:
        """攤成逐格的風控設定,次序固定(單筆風險 × 熔斷 × 賠率),重跑一字不差。"""
        return tuple(
            RiskSettings(
                per_trade_risk=risk,
                monthly_loss_cap=cap,
                reward_risk_floor=floor,
            )
            for risk, cap, floor in product(
                self.per_trade_risk, self.monthly_loss_cap, self.reward_risk_floor
            )
        )

    @property
    def combinations(self) -> int:
        """這個取值格一共有幾多組。"""
        return len(self.per_trade_risk) * len(self.monthly_loss_cap) * len(self.reward_risk_floor)


@dataclass(frozen=True, slots=True)
class RiskSweepCell:
    """掃描表的一格:一組風控取值,加它跑出來的成績。"""

    settings: RiskSettings
    entry_signals: int
    orders: int
    total_return: float
    max_drawdown: float
    worst_month_drawdown: float
    blocked_days: int

    def as_row(self) -> dict[str, float | int | None]:
        return {
            "per_trade_risk": self.settings.per_trade_risk,
            "monthly_loss_cap": self.settings.monthly_loss_cap,
            "reward_risk_floor": self.settings.reward_risk_floor,
            "entry_signals": self.entry_signals,
            "orders": self.orders,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "worst_month_drawdown": self.worst_month_drawdown,
            "blocked_days": self.blocked_days,
        }


@dataclass(frozen=True, slots=True)
class RiskSweepResult:
    """一次風控參數掃描的全部結果。"""

    cells: tuple[RiskSweepCell, ...]
    grid: RiskSweepGrid
    engine_name: str

    def __len__(self) -> int:
        return len(self.cells)

    def frame(self) -> pd.DataFrame:
        """攤成一張表,方便落檔與人眼核對。次序與掃描次序一致。

        ``monthly_loss_cap`` 那一格空白(NaN)即這一組**不引用熔斷**,不是門檻為零。
        """
        return pd.DataFrame([cell.as_row() for cell in self.cells], columns=list(SWEEP_COLUMNS))

    def cell_for(self, settings: RiskSettings) -> RiskSweepCell:
        for cell in self.cells:
            if cell.settings == settings:
                return cell
        raise ContractViolation(f"這次掃描沒有跑過 {settings}")


def sweep_risk_settings(
    *,
    panel: BarPanel,
    params: RuleStrategyParams,
    grid: RiskSweepGrid,
    engine: RuleEngine | None = None,
) -> RiskSweepResult:
    """逐格換三條風控規則的取值,各跑一次回測,交回整張表。

    ``params`` 是那份「其餘一字不動」的規則參數(用 ``build_rule_params`` 砌);
    每一格只換三個風控數,其他參數、數據、種子全部相同——所以格與格之間的差異
    只可能來自風控取值本身。
    """
    if not isinstance(panel, BarPanel):
        raise ContractViolation(f"K 線面板要是 BarPanel,收到 {type(panel).__name__}")
    if not isinstance(params, RuleStrategyParams):
        raise ContractViolation(f"規則參數要是 RuleStrategyParams,收到 {type(params).__name__}")
    if not isinstance(grid, RiskSweepGrid):
        raise ContractViolation(f"掃描取值格要是 RiskSweepGrid,收到 {type(grid).__name__}")

    cells: list[RiskSweepCell] = []
    engine_name = ""
    for settings in grid.settings():
        result = run_rule_strategy(panel=panel, params=settings.apply(params), engine=engine)
        engine_name = result.engine_name
        cells.append(
            RiskSweepCell(
                settings=settings,
                entry_signals=result.entry_signals,
                orders=len(result.orders),
                total_return=result.total_return,
                max_drawdown=result.max_drawdown,
                worst_month_drawdown=result.worst_month_drawdown,
                blocked_days=result.blocked_days,
            )
        )
    return RiskSweepResult(cells=tuple(cells), grid=grid, engine_name=engine_name)


def sweep_grid(
    *,
    per_trade_risk: Sequence[float],
    monthly_loss_cap: Sequence[float | None],
    reward_risk_floor: Sequence[float],
) -> RiskSweepGrid:
    """砌一個掃描取值格。三串取值都要明寫,一串都沒有預設值。"""
    return RiskSweepGrid(
        per_trade_risk=tuple(per_trade_risk),
        monthly_loss_cap=tuple(monthly_loss_cap),
        reward_risk_floor=tuple(reward_risk_floor),
    )
