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
from .funnel import SelectionTrace

# 換倉節奏(rebalance cadence)的全部選項。
# 這是一張選單,**不是**預設值:D-009 第 7 條明令引擎必須節奏無關、不設任何
# 預設節奏,每次執行由用戶指定(用戶原話「Why we need a default?」)。
CADENCES: Final[frozenset[str]] = frozenset({"daily", "weekly", "monthly", "quarterly"})

# 排名方向:取因子值最高的一批,還是最低的一批。可掃描參數(D-008 第 3 條)。
RANK_DIRECTIONS: Final[frozenset[str]] = frozenset({"high", "low"})

ORDER_SIDES: Final[frozenset[str]] = frozenset({"buy", "sell"})

# 手續費型別(fee model)。兩個取值的意思完全不同,所以型別要寫明,不可以只交一個數:
#
# - ``per_share``          每買賣一股收固定金額(美股經紀慣例,例如每股 US$0.005)
# - ``fraction_of_value``  按成交金額收比例(例如 0.001 即 10 個基點)
#
# 這是一張選單,**不是**預設值:成本用哪個型別、收多少,一律由參數集講明(D-008 第 3 條)。
FEE_MODELS: Final[frozenset[str]] = frozenset({"per_share", "fraction_of_value"})


class CadenceNotSpecified(ContractViolation):
    """沒有指定換倉節奏。D-009 第 7 條:不設預設值,缺即拋錯,不代用戶決定。"""


@dataclass(frozen=True, slots=True)
class TradingCosts:
    """交易成本(trading costs):手續費與滑點,兩條引擎路徑共用**同一份**定義。

    三個欄位一個都沒有預設值——要計成本就三件事都要講清楚,引擎不代用戶揀一個
    「行內慣例」的數(D-008 第 3 條、D-009 第 7 條的同一個道理)。明示不計成本
    要寫 ``TradingCosts.zero()``,寫出來的那一刻就是一個決定,不是一個預設。

    定義(兩條路徑逐字相同):

    - **滑點**(slippage)按成交價比例收:買入成交價 = 計劃價 × (1 + s),
      賣出成交價 = 計劃價 × (1 − s)。計劃價是可執行時點那根 K 線的開價
      (排名再平衡路徑),或者規則路徑算出來的止蝕/目標價位。
    - **手續費**(fee)按 ``fee_model`` 收:
      ``per_share`` 每股收 ``fee_rate`` 元,一筆收 ``fee_rate × 股數``;
      ``fraction_of_value`` 按成交金額收 ``fee_rate``,一筆收
      ``fee_rate × 股數 × 成交價``(成交價已含滑點)。

    ``fee_rate`` 為 0 時兩個型別算出來一模一樣;``zero()`` 揀 ``fraction_of_value``
    純粹因為要填一格,不代表偏好哪一個。
    """

    fee_model: str
    fee_rate: float
    slippage_fraction: float

    def __post_init__(self) -> None:
        fee_model = str(self.fee_model).strip() if self.fee_model is not None else ""
        if fee_model not in FEE_MODELS:
            raise ContractViolation(
                f"手續費型別只收 {sorted(FEE_MODELS)}"
                "(per_share=每股收固定金額,fraction_of_value=按成交金額收比例),"
                f"收到 {self.fee_model!r};光有一個數字講不清是每股還是按金額"
            )
        try:
            fee_rate = float(self.fee_rate)
        except (TypeError, ValueError) as exc:
            raise ContractViolation(f"手續費要是數字,收到 {self.fee_rate!r}") from exc
        if not np.isfinite(fee_rate) or fee_rate < 0.0:
            raise ContractViolation(f"手續費不可為負,收到 {self.fee_rate!r}")
        try:
            slippage = float(self.slippage_fraction)
        except (TypeError, ValueError) as exc:
            raise ContractViolation(f"滑點要是數字,收到 {self.slippage_fraction!r}") from exc
        if not np.isfinite(slippage) or slippage < 0.0:
            raise ContractViolation(f"滑點不可為負,收到 {self.slippage_fraction!r}")
        if slippage >= 1.0:
            raise ContractViolation(
                f"滑點是佔成交價的比例(0.0005 即 5 個基點),收到 {self.slippage_fraction!r};"
                "1.0 即賣出價變成 0,那不是滑點是報廢"
            )
        if fee_model == "fraction_of_value" and fee_rate >= 1.0:
            raise ContractViolation(
                f"按金額比例的手續費是比例(0.001 即 10 個基點),收到 {self.fee_rate!r}"
            )

        object.__setattr__(self, "fee_model", fee_model)
        object.__setattr__(self, "fee_rate", fee_rate)
        object.__setattr__(self, "slippage_fraction", slippage)

    @classmethod
    def zero(cls) -> "TradingCosts":
        """明示「這次不計成本」。用來重現成本入引擎之前的舊運行。"""
        return cls(fee_model="fraction_of_value", fee_rate=0.0, slippage_fraction=0.0)

    @property
    def is_zero(self) -> bool:
        return self.fee_rate == 0.0 and self.slippage_fraction == 0.0

    @property
    def fee_per_share(self) -> float:
        """每股手續費;不是每股型別即 0。"""
        return self.fee_rate if self.fee_model == "per_share" else 0.0

    @property
    def fee_fraction_of_value(self) -> float:
        """按成交金額計的手續費率;不是這個型別即 0。"""
        return self.fee_rate if self.fee_model == "fraction_of_value" else 0.0

    def as_params(self) -> dict[str, float | str]:
        """攤成參數集入面的三格。成本入了參數集,運行編號自然跟著變。"""
        return {
            "fee_model": self.fee_model,
            "fee_rate": self.fee_rate,
            "slippage_fraction": self.slippage_fraction,
        }

    @property
    def label(self) -> str:
        """一行人話,供參數集命名與報告用。"""
        if self.is_zero:
            return "無成本"
        if self.fee_model == "per_share":
            fee = f"每股{self.fee_rate:g}"
        else:
            fee = f"金額{self.fee_rate * 10_000:g}bp"
        return f"{fee}+滑點{self.slippage_fraction * 10_000:g}bp"


def resolve_costs(costs: "TradingCosts | None", fees: float, label: str) -> "TradingCosts":
    """把舊的 ``fees`` 單一數字與新的成本合約收成一個定義。

    ``costs`` 留空即沿用 ``fees``(按成交金額比例、無滑點)——成本入引擎之前
    全倉就是這樣算,所以舊呼叫逐位不變。兩邊同時講就當場拒收:成本只可以有
    一個講法,不可以兩個。
    """
    if costs is None:
        return TradingCosts(
            fee_model="fraction_of_value", fee_rate=fees, slippage_fraction=0.0
        )
    if not isinstance(costs, TradingCosts):
        raise ContractViolation(
            f"{label}要是 TradingCosts,收到 {type(costs).__name__}"
        )
    if fees:
        raise ContractViolation(
            f"{label}同時收到 fees={fees!r} 與成本合約 {costs.label};"
            "成本只可以有一個講法——交了 TradingCosts 就不要再交 fees"
        )
    return costs


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

    ``costs`` 是交易成本合約(手續費型別 + 費率 + 滑點),同樣是可掃描參數。
    留空即沿用舊的 ``fees`` 單一數字(按成交金額比例、無滑點);兩邊同時講即拒收。
    """

    cadence: str
    top_n: int
    direction: str
    initial_cash: float = 100_000.0
    fees: float = 0.0
    costs: "TradingCosts | None" = None

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
        costs = resolve_costs(self.costs, fees, "排名再平衡參數的交易成本")

        object.__setattr__(self, "costs", costs)
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
    # 選股痕跡(KARST-056):逐個決策日的候選名單各層與逐股因子分數。
    # 留空即這次沒有交出來——落痕那一層見不到就當交不出,照樣落痕。
    selection: "SelectionTrace | None" = None

    @property
    def candidates(self) -> "pd.DataFrame | None":
        """候選名單:決策日 × 層 × 實體編號。落痕那一層自己會拿走這一件。"""
        return None if self.selection is None else self.selection.candidates

    @property
    def factor_scores(self) -> "pd.DataFrame | None":
        """逐股因子分數:決策日 × 實體編號 × 分數名 → 數值與當日排名。"""
        return None if self.selection is None else self.selection.factor_scores

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
