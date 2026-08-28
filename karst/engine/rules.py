"""規則類策略的合約型別:進出場五件規則,全部是 Karst 自己的東西。

D-013 第 3 條把訊號分成兩種合約:選股類(因子,住在 ``contracts.py``)與**進出場
類**(規則:入場、止蝕、目標、注碼、熔斷)。本檔是後者那一半的「名詞」。

D-007 第 3 條:核心回測引擎收在自家介面之後。本檔一個第三方引擎的字都不提——
哪個引擎在背後跑,由 ``vectorbt_engine.py`` 一檔獨力承擔。

五件規則(規格 5.4、6.2,D-016 第 1 條):

1. **入場突破** ``BreakoutEntry``——收市價高於前 N 日最高(不含當日)。
2. **止蝕** ``SwingLowStop``——前波段低位,一個絕對價位,不是固定百分比。
3. **目標** ``MeasuredMoveTarget``——入場價 + 前 N 日區間高度(量度移動),
   連賠率門檻:賠率低過門檻就不入場。
4. **注碼** ``RiskFractionSizing``——單筆風險 = 注碼基數 × 風險比例,
   **注碼基數預設取當下權益,不是起始本金**(規格 6.2 第 2 條結論)。
5. **月度虧損熔斷** ``MonthlyLossBreaker``——月內權益由本月起點回落達門檻,
   即停止該月餘下日子的**新入場**(不強制平倉);組合層規則,只在看得見現金
   與權益那一層表達得到(規格 6.2 第 1 條結論)。

**全部參數一律無預設值**:缺就當場拋 ``ContractViolation``,不代用戶決定
(D-008 第 3 條、D-009 第 7 條同一套規矩)。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

import numpy as np
import pandas as pd

from ..errors import ContractViolation
from .contracts import Order, TradingCosts, _normalise_prices, resolve_costs
from .funnel import (
    STAGE_SCOPE,
    STAGE_SELECTED,
    STAGE_TECHNICAL,
    SelectionTrace,
    SelectionTraceBuilder,
)

# 規則路徑的兩個逐股分數(KARST-056)。名字就是畫面上那一欄的欄名——
# 一個數字叫什麼名,由算它出來的這條路徑講清楚,不硬套「因子分數」的殼。
SCORE_BREAKOUT_MARGIN: Final[str] = "突破幅度"
SCORE_PLAN_REWARD_RISK: Final[str] = "計劃賠率"

# 注碼基數(sizing basis)的兩個選項。
# ``current_equity`` 是唯一正確的一個;``initial_cash`` 只保留給對照臂——
# 用來重現「基數走樣」那條路,證明差距歸因於基數本身(規格 6.2、KARST-013)。
EQUITY_BASES: Final[frozenset[str]] = frozenset({"current_equity", "initial_cash"})

# ----------------------------------------------------------------------
# 出場原因(exit reason)
# ----------------------------------------------------------------------
# 一筆賣出、或者一個案例,是怎樣收場的。**這裡是全倉唯一一份出場規約**:同一根
# K 線先看止蝕後看目標,跳空穿價以開市價成交,行到最後一根仍未收場就是期末未平,
# 賣出當日不可再入場。
# 策略層不准另寫一份——引擎改了規約而策略層沒跟,案例表會靜靜走樣(KARST-028 留言 2)。
EXIT_STOP: Final[str] = "stop"
EXIT_TARGET: Final[str] = "target"
EXIT_UNCLOSED: Final[str] = "unclosed"

# 出場原因的中文名。程式裡用英文碼,交出去的表兩欄都有,人眼與機讀各取所需。
EXIT_REASONS: Final[Mapping[str, str]] = MappingProxyType(
    {EXIT_STOP: "止蝕", EXIT_TARGET: "目標", EXIT_UNCLOSED: "期末未平"}
)

# 同一批原因的整數碼:引擎內圈逐根 K 線行,只放得下數字,放不下字串。
EXIT_CODE_NONE: Final[int] = 0        # 這一格根本沒有案例
EXIT_CODE_STOP: Final[int] = 1
EXIT_CODE_TARGET: Final[int] = 2
EXIT_CODE_UNCLOSED: Final[int] = 3
EXIT_CODE_REASONS: Final[Mapping[int, str]] = MappingProxyType(
    {EXIT_CODE_STOP: EXIT_STOP, EXIT_CODE_TARGET: EXIT_TARGET, EXIT_CODE_UNCLOSED: EXIT_UNCLOSED}
)

# K 線四價一致性的**相對**容差。來源的已調整價經除權除息還原之後帶浮點尾數,偶爾
# 會出現最高價比收市價低一個位(實測 3.5 萬根之中 5 根,相對誤差 1.4e-16,即 float64
# 的最後一個 bit)。容差之內壓回包絡線,越界一律拋錯——不會把一根真的壞 K 線靜靜
# 修好(KARST-028 留言 3)。
BAR_CONSISTENCY_TOLERANCE: Final[float] = 1e-9

# 算相對誤差時的分母下限,免得價格趨近 0 時除爆。
_PRICE_SCALE_FLOOR: Final[float] = 1e-12


class RuleNotSpecified(ContractViolation):
    """五件規則之中有一件沒有交代。不設預設值,缺即拋錯,不代用戶決定。"""


class RuleNotExpressible(ContractViolation):
    """這條路徑表達不到這件規則。

    訊號矩陣路徑(``from_signals``)表達不到組合層熔斷,注碼基數亦只能用起始
    本金——這正是假設 A-005 被推翻的理由(規格 6.2)。與其默默算出一個假數,
    不如當場拒收。
    """


def _positive(value: float, label: str) -> float:
    number = float(value)
    if not np.isfinite(number) or number <= 0.0:
        raise ContractViolation(f"{label}要是正數,收到 {value!r}")
    return number


def _fraction(value: float, label: str) -> float:
    number = float(value)
    if not np.isfinite(number) or not 0.0 < number < 1.0:
        raise ContractViolation(f"{label}要是 0 與 1 之間的比例,收到 {value!r}")
    return number


def _lookback(value: int, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ContractViolation(f"{label}要是整數,收到 {value!r}") from exc
    if number < 1:
        raise ContractViolation(f"{label}至少要 1 日,收到 {number}")
    return number


@dataclass(frozen=True, slots=True)
class BarPanel:
    """K 線面板(bar panel):日期 × 實體編號 → 開高低收,四張同形狀的表。

    比 ``PricePanel`` 多了高低兩張:規則類策略要逐根 K 線問「今日有沒有穿止蝕、
    有沒有觸目標」,只有收價答不到。

    ``open`` 供成交——可執行時點寫死:訊號在收市成形,**下一根 K 線的開價**成交
    (D-021 第 3 條)。``close`` 供逐日估值與突破判斷。

    欄名是實體編號(entity id),不是交易代號(D-026 第 2 條)。

    **浮點尾數在這一關收**:高低價越出開收價的包絡線,若然只差在 ``tolerance``
    之內(相對誤差),就當是已調整價的浮點尾數,壓回包絡線;越界即拋錯。這一格
    刻意放在引擎入口,不是放在某一套策略裡——每一套策略都要餵同一批 K 線,
    尾數只可以有一個壓法(KARST-028 留言 3)。
    """

    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame

    @classmethod
    def from_frames(
        cls,
        *,
        open: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
        close: pd.DataFrame,
        tolerance: float = BAR_CONSISTENCY_TOLERANCE,
    ) -> "BarPanel":
        limit = float(tolerance)
        if not np.isfinite(limit) or limit < 0.0:
            raise ContractViolation(f"四價一致性容差要是非負的有限數,收到 {tolerance!r}")

        frames = {
            "開價表": _normalise_prices(open, "開價表"),
            "高價表": _normalise_prices(high, "高價表"),
            "低價表": _normalise_prices(low, "低價表"),
            "收價表": _normalise_prices(close, "收價表"),
        }
        reference = frames["收價表"]
        for label, frame in frames.items():
            if list(frame.columns) != list(reference.columns):
                raise ContractViolation(f"{label}與收價表的實體編號欄對不上")
            if not frame.index.equals(reference.index):
                raise ContractViolation(f"{label}與收價表的交易日對不上")

        highs = frames["高價表"].to_numpy()
        lows = frames["低價表"].to_numpy()
        opens = frames["開價表"].to_numpy()
        closes = reference.to_numpy()
        if (highs < lows).any():
            raise ContractViolation("有 K 線的最高價低過最低價")

        envelope_high = np.maximum.reduce([highs, opens, closes])
        envelope_low = np.minimum.reduce([lows, opens, closes])
        scale = np.maximum(np.abs(closes), _PRICE_SCALE_FLOOR)
        worst = max(
            float(np.max((envelope_high - highs) / scale)),
            float(np.max((lows - envelope_low) / scale)),
        )
        if worst > limit:
            raise ContractViolation(
                f"有 K 線的最高/最低價越出開收價的包絡線,最大相對越界 {worst:.3e},"
                f"超過容差 {limit:.3e};這不是浮點尾數,是數據本身有問題,請先查明"
            )

        return cls(
            open=frames["開價表"],
            high=pd.DataFrame(envelope_high, index=reference.index, columns=reference.columns),
            low=pd.DataFrame(envelope_low, index=reference.index, columns=reference.columns),
            close=reference,
        )

    @property
    def dates(self) -> pd.DatetimeIndex:
        """這個面板認得的全部可交易 K 線,由早到遲。"""
        return self.close.index

    @property
    def entity_ids(self) -> tuple[int, ...]:
        return tuple(int(column) for column in self.close.columns)


@dataclass(frozen=True, slots=True)
class BreakoutEntry:
    """規則 1 入場突破:收市價高於**前 N 日**最高(不含當日)即成訊號。"""

    lookback_days: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "lookback_days", _lookback(self.lookback_days, "突破回望日數 N")
        )


@dataclass(frozen=True, slots=True)
class SwingLowStop:
    """規則 2 止蝕:前波段低位(過去 M 日最低價),一個**絕對價位**。

    ``min_stop_fraction`` / ``max_stop_fraction`` 是同一條規則的兩道閘:止蝕太貼
    注碼會爆,太遠一注輸太多——兩邊皆不做這一筆(D-016 共用風控層)。
    """

    lookback_days: int
    min_stop_fraction: float
    max_stop_fraction: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "lookback_days", _lookback(self.lookback_days, "波段低位回望日數")
        )
        low = _fraction(self.min_stop_fraction, "止蝕距離下限")
        high = _fraction(self.max_stop_fraction, "止蝕距離上限")
        if low >= high:
            raise ContractViolation(f"止蝕距離下限({low})要細過上限({high})")
        object.__setattr__(self, "min_stop_fraction", low)
        object.__setattr__(self, "max_stop_fraction", high)


@dataclass(frozen=True, slots=True)
class MeasuredMoveTarget:
    """規則 3 目標:入場價 + 前 N 日區間高度(量度移動),外加賠率門檻。

    賠率 =(目標 − 收市)/(收市 − 止蝕),低過 ``min_reward_risk`` 即不入場——
    這條策略純風險回報驅動,天花板由賠率定義(D-016 第 1 條,用戶語)。
    """

    min_reward_risk: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "min_reward_risk", _positive(self.min_reward_risk, "賠率門檻")
        )


@dataclass(frozen=True, slots=True)
class RiskFractionSizing:
    """規則 4 注碼:單筆風險 = **注碼基數 × 風險比例**,再受單一持倉市值上限封頂。

    股數 =(注碼基數 × ``risk_per_trade``)/(成交價 − 止蝕價)。

    ``equity_basis`` 就是那個基數取誰:

    - ``"current_equity"`` **當下權益**——唯一正確的一個(規格 6.2)。
    - ``"initial_cash"`` 起始本金——**已知會令回測系統性偏樂觀**,只保留給對照臂
      重現訊號矩陣路徑那條走樣的路,不要拿去跑真策略。
    """

    risk_per_trade: float
    max_position_fraction: float
    equity_basis: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "risk_per_trade", _fraction(self.risk_per_trade, "單筆風險比例")
        )
        object.__setattr__(
            self,
            "max_position_fraction",
            _fraction(self.max_position_fraction, "單一持倉市值上限"),
        )
        basis = str(self.equity_basis).strip() if self.equity_basis is not None else ""
        if basis not in EQUITY_BASES:
            raise RuleNotSpecified(
                f"注碼基數(equity basis)只收 {sorted(EQUITY_BASES)},收到 {self.equity_basis!r};"
                "正確的一個是 current_equity(當下權益),initial_cash 只供對照臂"
            )
        object.__setattr__(self, "equity_basis", basis)

    @property
    def uses_current_equity(self) -> bool:
        return self.equity_basis == "current_equity"


@dataclass(frozen=True, slots=True)
class MonthlyLossBreaker:
    """規則 5 月度虧損熔斷:月內權益由本月起點回落達門檻,停止該月的**新入場**。

    本月起點權益 = 上月最後一根 K 線收市的權益。熔斷不強制平倉,只是不再開新倉;
    落閘之後直到下個月第一根 K 線才解除。

    要關掉熔斷就傳 ``None`` 進 ``RuleStrategyParams.breaker``——**沒有預設值**,
    開或關都要明寫。
    """

    max_monthly_drawdown: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_monthly_drawdown",
            _fraction(self.max_monthly_drawdown, "月度虧損熔斷門檻"),
        )


@dataclass(frozen=True, slots=True)
class RuleStrategyParams:
    """一條規則類策略的全部參數。五件規則加三個帳目數字,**無一個有預設值**。

    ``tie_break_seed``:同一根 K 線多隻股票同時發出入場訊號、現金不夠分時,
    先來後到由抽籤決定。定死種子,同一組參數重跑一字不差(D-021 第 8 條精神)。

    ``costs`` 是交易成本合約(``contracts.TradingCosts``),與排名再平衡路徑
    **同一份定義**;留空即沿用舊的 ``fees`` 單一數字(按成交金額比例、無滑點)。
    """

    entry: BreakoutEntry
    stop: SwingLowStop
    target: MeasuredMoveTarget
    sizing: RiskFractionSizing
    breaker: MonthlyLossBreaker | None
    initial_cash: float
    fees: float
    tie_break_seed: int
    costs: TradingCosts | None = None

    def __post_init__(self) -> None:
        pieces = {
            "入場突破規則": (self.entry, BreakoutEntry),
            "止蝕規則": (self.stop, SwingLowStop),
            "目標規則": (self.target, MeasuredMoveTarget),
            "注碼規則": (self.sizing, RiskFractionSizing),
        }
        for label, (value, expected) in pieces.items():
            if value is None:
                raise RuleNotSpecified(f"缺{label};五件規則一件都不可以省")
            if not isinstance(value, expected):
                raise ContractViolation(
                    f"{label}要是 {expected.__name__},收到 {type(value).__name__}"
                )
        if self.breaker is not None and not isinstance(self.breaker, MonthlyLossBreaker):
            raise ContractViolation(
                "月度虧損熔斷要是 MonthlyLossBreaker,或者明寫 None 代表關掉,"
                f"收到 {type(self.breaker).__name__}"
            )

        object.__setattr__(self, "initial_cash", _positive(self.initial_cash, "起始本金"))
        fees = float(self.fees)
        if not np.isfinite(fees) or fees < 0.0:
            raise ContractViolation(f"手續費率不可為負,收到 {self.fees!r}")
        object.__setattr__(self, "fees", fees)
        object.__setattr__(
            self, "costs", resolve_costs(self.costs, fees, "規則類策略參數的交易成本")
        )
        try:
            object.__setattr__(self, "tie_break_seed", int(self.tie_break_seed))
        except (TypeError, ValueError) as exc:
            raise ContractViolation(f"抽籤種子要是整數,收到 {self.tie_break_seed!r}") from exc

    @property
    def breaker_on(self) -> bool:
        return self.breaker is not None

    @property
    def max_monthly_drawdown(self) -> float:
        """熔斷門檻;關掉時是 0.0,即「永不落閘」。"""
        return 0.0 if self.breaker is None else self.breaker.max_monthly_drawdown


@dataclass(frozen=True, slots=True)
class ExitPlan:
    """每一張入場訊號的收場:在哪一根 K 線、幾多錢、什麼原因。

    **全倉唯一一份出場規約的產物**。三張表同形狀(日期 × 實體編號),索引取的是
    **入場那一根**——即第 b 列第 c 欄講的是「第 c 隻股票在第 b 根 K 線入場的話,
    會怎樣收場」。沒有訊號、或者訊號到成交那一刻已經跌穿止蝕(引擎不會入場)的
    格子,``exit_code`` 是 ``EXIT_CODE_NONE``。

    - ``exit_bar`` 結算那一根的位置;沒有案例的格子是 −1。期末未平的指向最後一根。
    - ``exit_price`` 結算價:止蝕/目標按規約(跳空以開市價),期末未平按最後一根收市價。
    - ``exit_code`` 出場原因的整數碼,對照 ``EXIT_CODE_REASONS``。
    """

    exit_bar: np.ndarray
    exit_price: np.ndarray
    exit_code: np.ndarray

    def reason_at(self, bar: int, column: int) -> str | None:
        """第 ``bar`` 根、第 ``column`` 欄那個案例的出場原因;沒有案例即 ``None``。"""
        return EXIT_CODE_REASONS.get(int(self.exit_code[bar, column]))


@dataclass(frozen=True, slots=True)
class RuleSignals:
    """規則 1、2、3 算完之後、引擎吃得落的那一份。

    全部陣列已經對齊到**成交那一根 K 線**(訊號日的下一根):第 i 列就是「第 i 根
    K 線要做的事」,引擎不用再自己 shift,少一個對錯位的機會。

    - ``entries`` 這一根要不要開新倉
    - ``stop_level`` / ``target_level`` 絕對價位,不是百分比
    - ``stop_fraction`` / ``target_fraction`` 同一對價位換算成佔成交價的比例
    - ``month_id`` 每根 K 線屬於第幾個月,熔斷用來認新一個月
    - ``exits`` 每一張訊號的收場(規則 2、3 行到底),引擎與案例表共用同一份

    最後四件是**決策日那一邊**的痕跡(第 i 列就是第 i 根 K 線收市判出來的東西,
    未 shift):選股漏斗與逐股分數要的正是這一邊,因為問的是「那一日看見什麼」,
    不是「下一日做了什麼」(KARST-056)。

    - ``breakout`` 規則 1 過關沒有:收市價高過前 N 日最高
    - ``plan_ready`` 規則 2、3 加賠率門檻全部過關(即這一根收市真的出了訊號)
    - ``breakout_margin`` 收市價高出前 N 日最高幾多(比例);負數即未破頂
    - ``plan_reward_risk`` 計劃賠率 =(目標 − 收市)/(收市 − 止蝕)
    """

    entries: np.ndarray
    stop_level: np.ndarray
    target_level: np.ndarray
    stop_fraction: np.ndarray
    target_fraction: np.ndarray
    month_id: np.ndarray
    exits: ExitPlan
    breakout: np.ndarray
    plan_ready: np.ndarray
    breakout_margin: np.ndarray
    plan_reward_risk: np.ndarray

    @property
    def count(self) -> int:
        """全期入場訊號張數。"""
        return int(self.entries.sum())


def month_ids(dates: pd.DatetimeIndex) -> np.ndarray:
    """每根 K 線屬於第幾個月(年 × 12 + 月),熔斷用來認「新一個月」。"""
    index = pd.DatetimeIndex(dates)
    return (index.year * 12 + index.month).to_numpy().astype(np.int64)


def build_rule_signals(panel: BarPanel, params: RuleStrategyParams) -> RuleSignals:
    """把規則 1、2、3 算成訊號。注碼與熔斷不在這裡——那兩件要看見錢,歸引擎那層。

    交易計劃在**訊號日收市**成形(入場參考價、止蝕、目標三元素),成交在**下一根
    K 線的開價**(D-021 第 3 條)。止蝕距離的兩道閘用真正成交價做分母,換算回絕對
    價位剛好等於前波段低位本身,不會因為「引擎只收百分比」而走樣。
    """
    if not isinstance(panel, BarPanel):
        raise ContractViolation(
            f"K 線面板要是 BarPanel,收到 {type(panel).__name__};請先用 BarPanel.from_frames 核對四張表"
        )
    if not isinstance(params, RuleStrategyParams):
        raise ContractViolation(f"參數要是 RuleStrategyParams,收到 {type(params).__name__}")

    close = panel.close.to_numpy()
    fill = panel.open.to_numpy()

    n_break = params.entry.lookback_days
    prior_high = panel.high.rolling(n_break, min_periods=n_break).max().shift(1).to_numpy()
    prior_low = panel.low.rolling(n_break, min_periods=n_break).min().shift(1).to_numpy()

    swing = params.stop.lookback_days
    stop_abs = panel.low.rolling(swing, min_periods=swing).min().to_numpy()
    target_abs = close + (prior_high - prior_low)

    # 訊號日 t 的成交價 = t+1 根的開價;最後一根之後沒有 K 線可以成交
    next_open = np.full_like(fill, np.nan)
    next_open[:-1] = fill[1:]

    with np.errstate(invalid="ignore", divide="ignore"):
        breakout = close > prior_high                     # 規則 1
        plan_risk = close - stop_abs                      # 規則 2:計劃在訊號日成形
        plan_reward = target_abs - close                  # 規則 3
        reward_risk = plan_reward / plan_risk

        stop_fraction = (next_open - stop_abs) / next_open
        target_fraction = (target_abs - next_open) / next_open

        tradable = (
            np.isfinite(reward_risk)
            & np.isfinite(stop_fraction)
            & np.isfinite(target_fraction)
            & (plan_risk > 0.0)
            & (stop_fraction >= params.stop.min_stop_fraction)
            & (stop_fraction <= params.stop.max_stop_fraction)
            & (target_fraction > 0.0)
            & (reward_risk >= params.target.min_reward_risk)
        )
        signal = breakout & tradable

        # 決策日那一邊的兩個數(KARST-056):突破幅度是規則 1 那道閘的連續版
        # ——閘本身是是非題(過或不過),但「高出前 N 日最高幾多」才排得出
        # 名次,選股快照要的正是這個。計劃賠率就是規則 3 那道閘量的數。
        breakout_margin = close / prior_high - 1.0
        plan_reward_risk = np.where(plan_risk > 0.0, reward_risk, np.nan)

    rows, columns = close.shape
    entries = np.zeros((rows, columns), dtype=np.bool_)
    levels = {name: np.full((rows, columns), np.nan) for name in ("stop", "target", "sf", "tf")}
    entries[1:] = signal[:-1]
    levels["stop"][1:] = stop_abs[:-1]
    levels["target"][1:] = target_abs[:-1]
    levels["sf"][1:] = stop_fraction[:-1]
    levels["tf"][1:] = target_fraction[:-1]

    blank = lambda values: np.where(entries, values, np.nan)  # noqa: E731
    stop_level = blank(levels["stop"])
    target_level = blank(levels["target"])
    return RuleSignals(
        entries=entries,
        stop_level=stop_level,
        target_level=target_level,
        stop_fraction=blank(levels["sf"]),
        target_fraction=blank(levels["tf"]),
        month_id=month_ids(panel.dates),
        breakout=np.asarray(breakout, dtype=np.bool_),
        plan_ready=np.asarray(signal, dtype=np.bool_),
        breakout_margin=np.asarray(breakout_margin, dtype=float),
        plan_reward_risk=np.asarray(plan_reward_risk, dtype=float),
        exits=resolve_exits(panel, entries, stop_level, target_level),
    )


def rule_selection_trace(panel: BarPanel, signals: RuleSignals) -> SelectionTrace | None:
    """把規則路徑逐根 K 線的判斷,攤成選股漏斗的候選名單與逐股分數。

    三層(KARST-056、D-013):

    - **範圍**——這一日面板上有價的全部實體。K 線面板不收留空的格,所以就是
      全部;寫出來是為了讓漏斗第一層有一個由引擎交出來的數,而不是由畫面那邊
      自己數宇宙。
    - **技術關**(D-013 第二層)——規則 1 過關:收市價高過前 N 日最高。
    - **入選**——規則 2、3 加賠率門檻亦全部過關,即這一根收市真的出了訊號。
      再窄一層的「持倉」不在這裡:落唔落到注要看錢與熔斷,那是逐日持倉那條
      序列答的事,存兩份就會有兩個講法。

    分數兩個:突破幅度與計劃賠率,兩個都取**決策日那一邊**的值。留空的一格
    不入表(缺失=不參與,D-021 第 4 條)。
    """
    dates = list(panel.dates)
    entity_ids = list(panel.entity_ids)
    if not dates or not entity_ids:
        return None

    builder = SelectionTraceBuilder()
    scope = np.isfinite(panel.close.to_numpy())
    builder.stage_panel(STAGE_SCOPE, dates, entity_ids, scope)
    builder.stage_panel(STAGE_TECHNICAL, dates, entity_ids, signals.breakout & scope)
    builder.stage_panel(STAGE_SELECTED, dates, entity_ids, signals.plan_ready & scope)
    builder.score_panel(
        SCORE_BREAKOUT_MARGIN, dates, entity_ids, signals.breakout_margin
    )
    builder.score_panel(
        SCORE_PLAN_REWARD_RISK, dates, entity_ids, signals.plan_reward_risk
    )
    return builder.build()


def resolve_exits(
    panel: BarPanel,
    entries: np.ndarray,
    stop_level: np.ndarray,
    target_level: np.ndarray,
) -> ExitPlan:
    """把規則 2、3 由每一張入場訊號行到收場。**全倉唯一一份出場規約。**

    由入場那根 K 線的**下一根**起逐根行:

      · 最低價跌穿止蝕 → 出場原因「止蝕」;跳空穿價就以開市價成交。
      · 最高價觸及目標 → 出場原因「目標」;同樣處理跳空。
      · 同一根兩者皆中 → 一律當止蝕(最壞情況)。
      · 行到最後一根仍未收場 → 出場原因「期末未平」,以最後一根收市價結算。

    **賣出當日不可再入場;同一隻的新入場最早在下一個交易日開市。** 入場成交取
    開價,而離場(止蝕/目標/期末未平)是開市之後才發生的事——開市那一刻舊倉仍然
    在手,那一注根本開不成。這一句本來只活在實作裡:落單那一層見「手上有貨」就
    只看離場,同一根不再看入場訊號(``vectorbt_engine._order_rules_nb``)。
    KARST-059 手寫對照時把它寫成同一根做得到,於是同日多開一注,淨值自此分家
    ——規約沒有明寫,下一個人手算或者日後換引擎會再踩同一個坑,所以補在這裡
    (KARST-060;釘死這個行為的測試在 ``tests/test_engine_exit_reentry.py``)。

    到成交那一刻止蝕已經在成交價之上(計劃在訊號日收市成形,隔晚跳空跌穿),
    引擎本來就不會入場——這種格子不算案例,``exit_code`` 留 ``EXIT_CODE_NONE``。

    交回來的三張表同時餵兩個地方:引擎逐根 K 線照著它落賣單(所以賣出那一刻的
    出場原因是引擎自己標的),案例表照著它砌每一行。兩邊同一份數,不會走樣。
    """
    opens = panel.open.to_numpy(dtype=float)
    highs = panel.high.to_numpy(dtype=float)
    lows = panel.low.to_numpy(dtype=float)
    closes = panel.close.to_numpy(dtype=float)
    rows, columns = closes.shape

    exit_bar = np.full((rows, columns), -1, dtype=np.int64)
    exit_price = np.full((rows, columns), np.nan, dtype=np.float64)
    exit_code = np.full((rows, columns), EXIT_CODE_NONE, dtype=np.int8)

    for column in range(columns):
        for signal in np.flatnonzero(entries[:, column]):
            bar = int(signal)
            stop = float(stop_level[bar, column])
            target = float(target_level[bar, column])
            if not (float(opens[bar, column]) - stop > 0.0):
                continue                      # 引擎不會入場,不算一個案例

            after_low = lows[bar + 1 :, column]
            after_high = highs[bar + 1 :, column]
            stop_hits = np.flatnonzero(after_low <= stop)
            target_hits = np.flatnonzero(after_high >= target)
            first_stop = int(stop_hits[0]) if stop_hits.size else -1
            first_target = int(target_hits[0]) if target_hits.size else -1

            if first_stop >= 0 and (first_target < 0 or first_stop <= first_target):
                step = bar + 1 + first_stop   # 同一根兩者皆中一律當止蝕
                bar_open = float(opens[step, column])
                settle, code = step, EXIT_CODE_STOP
                price = bar_open if bar_open <= stop else stop
            elif first_target >= 0:
                step = bar + 1 + first_target
                bar_open = float(opens[step, column])
                settle, code = step, EXIT_CODE_TARGET
                price = bar_open if bar_open >= target else target
            else:
                settle, code = rows - 1, EXIT_CODE_UNCLOSED
                price = float(closes[rows - 1, column])

            exit_bar[bar, column] = settle
            exit_price[bar, column] = price
            exit_code[bar, column] = code

    return ExitPlan(exit_bar=exit_bar, exit_price=exit_price, exit_code=exit_code)


@dataclass(frozen=True, slots=True)
class RuleSimulationOutput:
    """可換件引擎跑完規則類策略之後交回來的東西,全部是 Karst 自己的型別。

    比排名再平衡那條路多兩件,兩件都是為了**查得到帳**:

    - ``sizing_basis`` 逐日注碼基數——當日開市那一刻的權益(現金 + 持倉市值)。
    - ``breaker_blocked`` 逐日熔斷狀態——該日有沒有落閘停止新入場。
    """

    equity_curve: pd.Series
    holdings: pd.DataFrame
    cash: pd.Series
    sizing_basis: pd.Series
    breaker_blocked: pd.Series
    orders: tuple[Order, ...]


@dataclass(frozen=True, slots=True)
class RuleBacktestResult:
    """一次規則類策略回測的結果。"""

    equity_curve: pd.Series
    holdings: pd.DataFrame
    cash: pd.Series
    sizing_basis: pd.Series
    breaker_blocked: pd.Series
    orders: tuple[Order, ...]
    params: RuleStrategyParams
    entry_signals: int
    engine_name: str
    # 選股痕跡(KARST-056)。留空即這次沒有交出來——舊呼叫一字不用改,
    # 落痕那一層見不到就當這條路徑交不出,照樣落痕。
    selection: SelectionTrace | None = None

    @property
    def candidates(self) -> pd.DataFrame | None:
        """候選名單:決策日 × 層 × 實體編號。落痕那一層自己會拿走這一件。"""
        return None if self.selection is None else self.selection.candidates

    @property
    def factor_scores(self) -> pd.DataFrame | None:
        """逐股分數:決策日 × 實體編號 × 分數名 → 數值與當日排名。"""
        return None if self.selection is None else self.selection.factor_scores

    @property
    def total_return(self) -> float:
        """全期總報酬。"""
        return float(self.equity_curve.iloc[-1] / self.equity_curve.iloc[0] - 1.0)

    @property
    def max_drawdown(self) -> float:
        """全期最大回撤(負數)。"""
        values = self.equity_curve.to_numpy()
        return float(np.min(values / np.maximum.accumulate(values) - 1.0))

    @property
    def worst_month_drawdown(self) -> float:
        """**月內**最深回撤(負數):每個月由上月最後一根收市重新起計。

        熔斷管的正是這一格——它不管全期最大回撤,只管單月失血(D-016 共用風控層)。
        """
        values = self.equity_curve.to_numpy()
        months = month_ids(self.equity_curve.index)
        worst = 0.0
        start = values[0]
        for position in range(len(values)):
            if position > 0 and months[position] != months[position - 1]:
                start = values[position - 1]
            worst = min(worst, values[position] / start - 1.0)
        return float(worst)

    @property
    def blocked_days(self) -> int:
        """全期被熔斷封鎖的日數。"""
        return int(self.breaker_blocked.sum())

    @property
    def exit_reason_counts(self) -> Mapping[str, int]:
        """逐個出場原因數一數賣出筆數。期末未平不在此列——它沒有賣出。"""
        counts = {EXIT_STOP: 0, EXIT_TARGET: 0}
        for order in self.orders:
            if order.side == "sell" and order.exit_reason in counts:
                counts[order.exit_reason] += 1
        return MappingProxyType(counts)

    def orders_frame(self) -> pd.DataFrame:
        """逐筆訂單攤成一張表,方便落檔與人眼核對。

        ``exit_reason`` 只有賣出那幾行才有值(買入是 ``None``)——它答的是
        「這一筆是怎樣走的」,由引擎在賣出那一刻標記,不是事後推算回來。
        """
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
                    "exit_reason": order.exit_reason,
                }
                for order in self.orders
            ],
            columns=[
                "trade_date", "entity_id", "side", "shares", "price", "fees",
                "gross_value", "exit_reason",
            ],
        )
