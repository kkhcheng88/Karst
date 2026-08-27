"""引擎適配層的合約型別:全部是 Karst 自己的東西。

D-007 第 3 條:核心回測引擎必須隔離在自家介面之後,引擎是可換件。本檔是那道
介面的「名詞」那一半——策略層與資料層只認得這裡的型別;哪一個第三方引擎在
背後跑,本檔一個字都不提。日後換引擎,本檔不用改。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from ..errors import ContractViolation

# 換倉節奏(rebalance cadence)的全部選項。
# 這是一張選單,**不是**預設值:D-009 第 7 條明令引擎必須節奏無關、不設任何
# 預設節奏,每次執行由用戶指定(用戶原話「Why we need a default?」)。
CADENCES: Final[frozenset[str]] = frozenset({"daily", "weekly", "monthly", "quarterly"})

# 排名方向:取因子值最高的一批,還是最低的一批。可掃描參數(D-008 第 3 條)。
RANK_DIRECTIONS: Final[frozenset[str]] = frozenset({"high", "low"})

ORDER_SIDES: Final[frozenset[str]] = frozenset({"buy", "sell"})


class CadenceNotSpecified(ContractViolation):
    """沒有指定換倉節奏。D-009 第 7 條:不設預設值,缺即拋錯,不代用戶決定。"""


def _normalise_prices(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    """把一張價格表核對兼規範化。對不上即當場拒收——不猜、不補值。"""
    if not isinstance(frame, pd.DataFrame):
        raise ContractViolation(f"{label}要一張 pandas 表,收到 {type(frame).__name__}")
    if frame.empty:
        raise ContractViolation(f"{label}是空的")
    try:
        columns = [int(column) for column in frame.columns]
    except (TypeError, ValueError) as exc:
        raise ContractViolation(
            f"{label}的欄名要是實體編號(整數),不是交易代號——代號會被回收再發給別人(D-026 第 2 條)"
        ) from exc
    if len(set(columns)) != len(columns):
        raise ContractViolation(f"{label}有重複的實體編號欄")
    try:
        index = pd.DatetimeIndex(frame.index)
    except (TypeError, ValueError) as exc:
        raise ContractViolation(f"{label}的列索引要是交易日") from exc
    if index.has_duplicates:
        raise ContractViolation(f"{label}有重複的交易日")

    out = pd.DataFrame(frame.to_numpy(dtype=float), index=index, columns=columns).sort_index()
    values = out.to_numpy()
    if not np.isfinite(values).all():
        raise ContractViolation(
            f"{label}有非有限數(NaN 或 ±inf);那一日沒有價格就不要那一根 K 線,不要填 0"
        )
    if (values <= 0.0).any():
        raise ContractViolation(f"{label}有非正價格")
    return out


@dataclass(frozen=True, slots=True)
class PricePanel:
    """價格面板(price panel):日期 × 實體編號 → 價格,兩張同形狀的表。

    ``open`` 供成交——可執行時點寫死於因子合約、策略不得繞過:「知情時點之後的
    下一根可交易 K 線的開價」(D-021 第 3 條)。``close`` 供逐日估值。

    欄名是實體編號(entity id),不是交易代號(D-026 第 2 條)。
    """

    open: pd.DataFrame
    close: pd.DataFrame

    @classmethod
    def from_frames(cls, open: pd.DataFrame, close: pd.DataFrame) -> "PricePanel":
        opens = _normalise_prices(open, "開價表")
        closes = _normalise_prices(close, "收價表")
        if list(opens.columns) != list(closes.columns):
            raise ContractViolation("開價表與收價表的實體編號欄對不上")
        if not opens.index.equals(closes.index):
            raise ContractViolation("開價表與收價表的交易日對不上")
        return cls(open=opens, close=closes)

    @property
    def dates(self) -> pd.DatetimeIndex:
        """這個面板認得的全部可交易 K 線,由早到遲。"""
        return self.close.index

    @property
    def entity_ids(self) -> tuple[int, ...]:
        return tuple(int(column) for column in self.close.columns)


@dataclass(frozen=True, slots=True)
class RankingRebalanceParams:
    """「每期按因子排名選前 N 隻等權再平衡」的全部參數。

    頭三個欄位刻意沒有預設值:

    - ``cadence`` 換倉節奏——D-009 第 7 條明令不設預設,每次執行由用戶指定。
    - ``top_n`` 選幾隻、``direction`` 排名方向——D-008 第 3 條:策略內部數值
      一律做成可掃描參數,改參數不用改碼。
    """

    cadence: str
    top_n: int
    direction: str
    initial_cash: float = 100_000.0
    fees: float = 0.0

    def __post_init__(self) -> None:
        if self.cadence is None or not str(self.cadence).strip():
            raise CadenceNotSpecified(
                "缺換倉節奏(rebalance cadence):"
                f"{sorted(CADENCES)} 揀一個。引擎不設預設節奏(D-009 第 7 條)"
            )
        cadence = str(self.cadence).strip()
        if cadence not in CADENCES:
            raise ContractViolation(f"換倉節奏只收 {sorted(CADENCES)},收到 {self.cadence!r}")

        direction = str(self.direction).strip() if self.direction is not None else ""
        if direction not in RANK_DIRECTIONS:
            raise ContractViolation(
                f"排名方向只收 {sorted(RANK_DIRECTIONS)}(high=取因子值最高的一批),收到 {self.direction!r}"
            )

        try:
            top_n = int(self.top_n)
        except (TypeError, ValueError) as exc:
            raise ContractViolation(f"選股數 N 要是整數,收到 {self.top_n!r}") from exc
        if top_n < 1:
            raise ContractViolation(f"選股數 N 至少要 1,收到 {top_n}")

        initial_cash = float(self.initial_cash)
        if not np.isfinite(initial_cash) or initial_cash <= 0.0:
            raise ContractViolation(f"起始本金要是正數,收到 {self.initial_cash!r}")
        fees = float(self.fees)
        if not np.isfinite(fees) or fees < 0.0:
            raise ContractViolation(f"手續費率不可為負,收到 {self.fees!r}")

        object.__setattr__(self, "cadence", cadence)
        object.__setattr__(self, "direction", direction)
        object.__setattr__(self, "top_n", top_n)
        object.__setattr__(self, "initial_cash", initial_cash)
        object.__setattr__(self, "fees", fees)


@dataclass(frozen=True, slots=True)
class Order:
    """一筆成交。價格一定是執行日那根 K 線的開價(D-021 可執行時點)。

    ``exit_reason`` 是**出場原因**(exit reason):這一筆賣出是止蝕還是觸目標,
    由引擎在賣出那一刻標記(取值見 ``rules.EXIT_REASONS``)。買入一律 ``None``;
    出場原因與規則路徑綁在一起,排名再平衡那條路沒有止蝕目標可言,同樣 ``None``。
    """

    trade_date: str
    entity_id: int
    side: str
    shares: float
    price: float
    fees: float
    exit_reason: str | None = None

    @property
    def gross_value(self) -> float:
        return self.shares * self.price


@dataclass(frozen=True, slots=True)
class Rebalance:
    """一次換倉的帳:決策日看見了什麼因子值,下一根 K 線揀了誰。

    ``decision_date`` 是知情時間閘所在的交易日——「截至該日收工為止知道的一切」;
    ``execution_date`` 是它之後下一根可交易 K 線,成交價取該根的開價(D-021 第 3 條)。
    """

    decision_date: str
    execution_date: str
    selected: tuple[int, ...]
    weight: float


@dataclass(frozen=True, slots=True)
class SimulationOutput:
    """可換件引擎交回來的三件東西,全部是 Karst 自己的型別。

    引擎介面的「動詞」那一半(見 ``protocol.py``)只准回這個;第三方引擎的
    型別一律止步於適配層之內(D-007 第 3 條)。
    """

    equity_curve: pd.Series
    holdings: pd.DataFrame
    orders: tuple[Order, ...]


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """一次回測的結果,連同追溯得回去的來歷。

    ``factor_version_id`` 是追溯深度(lineage depth)三件之一(D-021 第 8 條):
    知道這次成績是由因子的哪一版跑出來的,舊運行永不自動更新。
    """

    equity_curve: pd.Series
    holdings: pd.DataFrame
    orders: tuple[Order, ...]
    rebalances: tuple[Rebalance, ...]
    params: RankingRebalanceParams
    factor_name: str
    factor_version_id: int
    engine_name: str

    @property
    def total_return(self) -> float:
        """全期總報酬。逐日淨值第一日為基準。"""
        return float(self.equity_curve.iloc[-1] / self.equity_curve.iloc[0] - 1.0)

    def orders_frame(self) -> pd.DataFrame:
        """逐筆訂單攤成一張表,方便落檔與人眼核對。"""
        return pd.DataFrame(
            [
                {
                    "trade_date": order.trade_date,
                    "entity_id": order.entity_id,
                    "side": order.side,
                    "shares": order.shares,
                    "price": order.price,
                    "fees": order.fees,
                    "gross_value": order.gross_value,
                }
                for order in self.orders
            ],
            columns=["trade_date", "entity_id", "side", "shares", "price", "fees", "gross_value"],
        )
