"""趨勢波段策略(trend swing strategy)(D-016、規格 5.4)。

規格 5.4 的零件:突破 N 日新高入場、前波段低位做支持阻力止蝕、三元素交易計劃
(入場/止蝕/目標)、賠率門檻、共用風控層(單筆風險、月度虧損熔斷)。純風險
回報驅動,與基本面無關,天花板由賠率定義(D-016 第 1 條,用戶語)。

本檔**不重寫任何一件規則**,只做三件事:

1. **接線** —— 把策略自己那份參數(N、波段回望、止蝕兩道閘、單一持倉市值上限、
   注碼基數取誰、本金、費用、抽籤種子)交去 ``karst.engine`` 那五件規則型別,
   三個風控數則一律經 ``karst.risk.build_rule_params`` 那條唯一通道入場。
   五件規則的執行機制住 ``karst/engine/rules.py``,三條風控規則的定義住
   ``karst/risk/layer.py``——本檔一份都不抄。

2. **登記** —— 策略、參數集、因子、風控規則與它的引用,一律經唯一入口
   ``karst.gateway.Gateway``(D-020 第 4 條),沒有第二條寫入路徑;風控層
   只交定義,本檔一列都不直接寫庫(KARST-038)。

3. **驗規則** —— 規格 5.4 第 5 條、6.5 要求「一條規則須在約 500 個歷史案例上
   驗證」。``entry_cases`` 把入場規則在整個快照(全部實體 × 全期)觸發的每一次
   都攤成一個**案例**,逐個記入場日、出場日、出場原因與報酬,交一張案例表。
   這一格與回測不同:回測受現金與熔斷所限,同一日只做得成幾筆;案例表不管錢,
   問的是「這條規則本身在歷史上出現過幾多次、贏面幾多」。

**本檔查不到任何一個參數取值**,連預設值都沒有(D-008 第 3 條)。取值屬用戶
領域,住在參數集;掃描一組取值只需多砌一個 ``TrendSwingParams`` 或多登記一個
參數集,一行碼都不用改。

用法::

    from karst.risk import RiskSettings
    from karst.strategies.trend_swing import (
        TrendSwingParams, build_bar_panel, run_trend_swing,
    )

    params = TrendSwingParams(                      # 九格全部無預設值
        breakout_lookback_days=..., swing_lookback_days=...,
        min_stop_fraction=..., max_stop_fraction=...,
        max_position_fraction=..., equity_basis="current_equity",
        initial_cash=..., fees=..., tie_break_seed=...,
    )
    risk = RiskSettings(per_trade_risk=..., monthly_loss_cap=..., reward_risk_floor=...)
    panel = build_bar_panel(store, snapshot_id, entity_ids=[...])
    result = run_trend_swing(panel=panel, params=params, risk=risk)
    result.equity_curve          # 逐日淨值
    result.orders_frame()        # 逐筆交易
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from itertools import product
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

import numpy as np
import pandas as pd

from ..data.snapshots import read_price_panel
from ..engine.protocol import RuleEngine
from ..engine.rule_runner import run_rule_strategy
from ..engine.rules import (
    BAR_CONSISTENCY_TOLERANCE,
    EQUITY_BASES,
    EXIT_REASONS,
    EXIT_STOP,
    EXIT_TARGET,
    EXIT_UNCLOSED,
    BarPanel,
    BreakoutEntry,
    RuleBacktestResult,
    RuleStrategyParams,
    SwingLowStop,
    build_rule_signals,
)
from ..errors import ContractViolation, DuplicateDefinition
from ..models import FormulaProcedure
from ..risk import (
    SWEEP_COLUMNS as RISK_SWEEP_COLUMNS,
    RiskSettings,
    RiskSweepGrid,
    build_rule_params,
    sweep_risk_settings,
)
from ..store import FAMILY_SEPARATOR, DefinitionStore, ParamSet, StrategyVersion

# 策略類型(store.STRATEGY_TYPES 八選一):純技術波段屬技術趨勢。
TREND_SWING_STRATEGY_TYPE: Final[str] = "technical"

# ----------------------------------------------------------------------
# 入場訊號登記成因子
# ----------------------------------------------------------------------
# 單一定義庫要求每套策略最少引用一個因子。趨勢波段沒有選股因子,它只有一個
# 訊號來源——入場突破。與其為它開一條「無因子策略」的旁路,不如照因子合約把這
# 個訊號登記成一個是非刻度的因子:名落在「族名·具體定義」一級(規格 1.8),
# 產生程序記得住公式與輸入數據版本,追溯得回是哪一批數據算出來的(D-021 第 6、8 條)。
# 回望日數 N 刻意**不寫入因子名**——N 是參數集裡的可掃描參數,寫入名就等於把
# 一個取值鑄死在定義裡(D-008 第 3 條)。
BREAKOUT_FACTOR_FAMILY: Final[str] = "趨勢"
BREAKOUT_FACTOR_SPECIFIC: Final[str] = "收市價突破前 N 日最高(不含當日)"
BREAKOUT_FACTOR_NAME: Final[str] = (
    f"{BREAKOUT_FACTOR_FAMILY}{FAMILY_SEPARATOR}{BREAKOUT_FACTOR_SPECIFIC}"
)
BREAKOUT_FACTOR_SCALE: Final[str] = "boolean"
BREAKOUT_FACTOR_FORMULA: Final[str] = (
    "close[t] > max(high[t-N .. t-1]);N 由參數集的 entry.breakout_lookback_days 指定"
)

# ----------------------------------------------------------------------
# 參數集裡的參數名
# ----------------------------------------------------------------------
# 三個風控數不在這裡——它們帶 ``risk.`` 字首,名由共用風控層話事
# (``karst.risk.RISK_RULES``),本檔不另起一個名。
PARAM_BREAKOUT_LOOKBACK: Final[str] = "entry.breakout_lookback_days"
PARAM_SWING_LOOKBACK: Final[str] = "stop.swing_lookback_days"
PARAM_MIN_STOP_FRACTION: Final[str] = "stop.min_stop_fraction"
PARAM_MAX_STOP_FRACTION: Final[str] = "stop.max_stop_fraction"
PARAM_MAX_POSITION_FRACTION: Final[str] = "sizing.max_position_fraction"
PARAM_EQUITY_BASIS: Final[str] = "sizing.equity_basis"
PARAM_INITIAL_CASH: Final[str] = "account.initial_cash"
PARAM_FEES: Final[str] = "account.fees"
PARAM_TIE_BREAK_SEED: Final[str] = "execution.tie_break_seed"

STRATEGY_PARAM_KEYS: Final[tuple[str, ...]] = (
    PARAM_BREAKOUT_LOOKBACK,
    PARAM_SWING_LOOKBACK,
    PARAM_MIN_STOP_FRACTION,
    PARAM_MAX_STOP_FRACTION,
    PARAM_MAX_POSITION_FRACTION,
    PARAM_EQUITY_BASIS,
    PARAM_INITIAL_CASH,
    PARAM_FEES,
    PARAM_TIE_BREAK_SEED,
)

# K 線一致性的容差(相對)住引擎那邊——尾數只可以有一個壓法,本檔只是轉引
# (``karst.engine.rules.BAR_CONSISTENCY_TOLERANCE``)。見 ``build_bar_panel``。


# ----------------------------------------------------------------------
# 參數
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrendSwingParams:
    """趨勢波段策略自己那份參數:九格,**無一格有預設值**。

    三個風控數(單筆風險上限、月度虧損熔斷、賠率門檻)不在這裡——那三格住
    ``karst.risk.RiskSettings``,經 ``build_rule_params`` 一條路入場,全平台
    只有一份定義(D-013 第 4 條)。

    取值範圍不在本檔另寫一套:``entry`` 與 ``stop`` 兩格建構那一刻就交回引擎
    的規則型別驗;其餘幾格由 ``RuleStrategyParams`` 建構時驗。本層只驗一件
    引擎驗不到的事——注碼基數的名要在 ``EQUITY_BASES`` 之內,而且要明寫。
    """

    breakout_lookback_days: int
    swing_lookback_days: int
    min_stop_fraction: float
    max_stop_fraction: float
    max_position_fraction: float
    equity_basis: str
    initial_cash: float
    fees: float
    tie_break_seed: int

    def __post_init__(self) -> None:
        entry = self.entry
        stop = self.stop
        object.__setattr__(self, "breakout_lookback_days", entry.lookback_days)
        object.__setattr__(self, "swing_lookback_days", stop.lookback_days)
        object.__setattr__(self, "min_stop_fraction", stop.min_stop_fraction)
        object.__setattr__(self, "max_stop_fraction", stop.max_stop_fraction)

        basis = str(self.equity_basis).strip() if self.equity_basis is not None else ""
        if basis not in EQUITY_BASES:
            raise ContractViolation(
                f"注碼基數(equity basis)只收 {sorted(EQUITY_BASES)},收到 {self.equity_basis!r};"
                "正確的一個是 current_equity(當下權益),initial_cash 只供對照臂"
            )
        object.__setattr__(self, "equity_basis", basis)

    @property
    def entry(self) -> BreakoutEntry:
        """規則 1 入場突破。回望日數由參數話事,本檔不設預設。"""
        return BreakoutEntry(lookback_days=self.breakout_lookback_days)

    @property
    def stop(self) -> SwingLowStop:
        """規則 2 止蝕:前波段低位,連止蝕距離的兩道閘。"""
        return SwingLowStop(
            lookback_days=self.swing_lookback_days,
            min_stop_fraction=self.min_stop_fraction,
            max_stop_fraction=self.max_stop_fraction,
        )

    def rule_params(self, risk: RiskSettings) -> RuleStrategyParams:
        """砌一份跑得動的規則參數:策略九格 + 風控三格。

        三個風控數**只有這一條路**進得了引擎(``build_rule_params``),所以庫內外
        都只有一份定義;本檔一個風控門檻都寫不出來。
        """
        return build_rule_params(
            risk=risk,
            entry=self.entry,
            stop=self.stop,
            max_position_fraction=self.max_position_fraction,
            equity_basis=self.equity_basis,
            initial_cash=self.initial_cash,
            fees=self.fees,
            tie_break_seed=self.tie_break_seed,
        )

    def to_param_values(self) -> dict[str, str]:
        """攤成參數集寫得入的「參數名→值」(策略那九格)。"""
        return {
            PARAM_BREAKOUT_LOOKBACK: str(int(self.breakout_lookback_days)),
            PARAM_SWING_LOOKBACK: str(int(self.swing_lookback_days)),
            PARAM_MIN_STOP_FRACTION: repr(float(self.min_stop_fraction)),
            PARAM_MAX_STOP_FRACTION: repr(float(self.max_stop_fraction)),
            PARAM_MAX_POSITION_FRACTION: repr(float(self.max_position_fraction)),
            PARAM_EQUITY_BASIS: str(self.equity_basis),
            PARAM_INITIAL_CASH: repr(float(self.initial_cash)),
            PARAM_FEES: repr(float(self.fees)),
            PARAM_TIE_BREAK_SEED: str(int(self.tie_break_seed)),
        }

    @classmethod
    def from_param_set(cls, param_set: ParamSet) -> "TrendSwingParams":
        """由一個已登記的參數集讀回策略那九格。缺一格即拒收,不代用戶決定。"""
        values = dict(param_set.values or {})
        missing = [key for key in STRATEGY_PARAM_KEYS if key not in values]
        if missing:
            raise ContractViolation(
                f"參數集「{param_set.name}」第 {param_set.version_no} 版缺參數:"
                f"{'、'.join(missing)};參數無預設值,要用的一律寫明"
            )
        return cls(
            breakout_lookback_days=_as_int(values[PARAM_BREAKOUT_LOOKBACK], PARAM_BREAKOUT_LOOKBACK),
            swing_lookback_days=_as_int(values[PARAM_SWING_LOOKBACK], PARAM_SWING_LOOKBACK),
            min_stop_fraction=_as_float(values[PARAM_MIN_STOP_FRACTION], PARAM_MIN_STOP_FRACTION),
            max_stop_fraction=_as_float(values[PARAM_MAX_STOP_FRACTION], PARAM_MAX_STOP_FRACTION),
            max_position_fraction=_as_float(
                values[PARAM_MAX_POSITION_FRACTION], PARAM_MAX_POSITION_FRACTION
            ),
            equity_basis=values[PARAM_EQUITY_BASIS],
            initial_cash=_as_float(values[PARAM_INITIAL_CASH], PARAM_INITIAL_CASH),
            fees=_as_float(values[PARAM_FEES], PARAM_FEES),
            tie_break_seed=_as_int(values[PARAM_TIE_BREAK_SEED], PARAM_TIE_BREAK_SEED),
        )


def param_values(params: TrendSwingParams, risk: RiskSettings) -> dict[str, str]:
    """一個參數集要寫入的全部取值:策略九格 + 風控三格(``risk.`` 字首)。

    風控那三格的名與寫法由共用風控層提供(``RiskSettings.to_param_values``),
    本檔不另抄;沒有引用的風控規則不會出現一格。
    """
    if not isinstance(params, TrendSwingParams):
        raise ContractViolation(f"策略參數要是 TrendSwingParams,收到 {type(params).__name__}")
    if not isinstance(risk, RiskSettings):
        raise ContractViolation(f"風控設定要是 RiskSettings,收到 {type(risk).__name__}")
    return {**params.to_param_values(), **risk.to_param_values()}


def read_setup(param_set: ParamSet) -> tuple[TrendSwingParams, RiskSettings]:
    """由一個參數集讀回「策略九格 + 風控三格」兩份取值。"""
    return TrendSwingParams.from_param_set(param_set), RiskSettings.from_param_values(
        param_set.values
    )


def _as_int(value: Any, key: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ContractViolation(f"參數「{key}」要是整數,收到 {value!r}") from exc


def _as_float(value: Any, key: str) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ContractViolation(f"參數「{key}」要是一個數,收到 {value!r}") from exc


# ----------------------------------------------------------------------
# 由數據快照砌 K 線面板
# ----------------------------------------------------------------------


def build_bar_panel(
    store: DefinitionStore,
    snapshot_id: str,
    *,
    entity_ids: Sequence[int] | None = None,
    start: date | datetime | str | None = None,
    end: date | datetime | str | None = None,
    root: str | Path | None = None,
    tolerance: float = BAR_CONSISTENCY_TOLERANCE,
) -> BarPanel:
    """由一個數據快照讀回開高低收四張表,砌成規則路徑吃得落的 K 線面板。

    四張表任何一格留空即整行不要(留空是停牌或未上市,不是零,D-026);規則路徑
    逐根 K 線要問「今日有沒有穿止蝕」,缺一格就答不到。

    **一致性容差**:來源的已調整價經除權除息還原之後帶浮點尾數,偶爾會出現最高價
    比收市價低一個位(實測 3.5 萬根 K 線之中 5 根,相對誤差 1.4e-16,即 float64 的
    最後一個 bit)。收這種尾數是 ``BarPanel.from_frames`` 的事——引擎入口壓一次,
    全部策略同一個壓法;越界超過 ``tolerance`` 由那一關拋 ``ContractViolation``,
    不會把一根真的壞 K 線靜靜修好。本函式只把容差傳過去。
    """
    fields = ("open", "high", "low", "close")
    frames = {
        field: read_price_panel(
            store, snapshot_id, field=field, root=root, entity_ids=entity_ids
        )
        for field in fields
    }

    index = None
    for frame in frames.values():
        usable = frame.dropna(how="any").index
        index = usable if index is None else index.intersection(usable)
    if index is None or len(index) == 0:
        raise ContractViolation(
            f"快照 {snapshot_id} 在這批實體上沒有一根開高低收四價齊全的 K 線"
        )
    if start is not None:
        index = index[index >= pd.Timestamp(start)]
    if end is not None:
        index = index[index <= pd.Timestamp(end)]
    if len(index) < 2:
        raise ContractViolation(
            f"快照 {snapshot_id} 在 {start}~{end} 這一段只剩 {len(index)} 根 K 線;"
            "規則路徑要有訊號日,還要有它之後的下一根 K 線可以成交"
        )

    frames = {field: frame.loc[index] for field, frame in frames.items()}
    return BarPanel.from_frames(**frames, tolerance=float(tolerance))


# ----------------------------------------------------------------------
# 跑一次回測
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrendSwingResult:
    """一次趨勢波段回測的結果,連同它用了哪一份取值。

    ``equity_curve`` / ``holdings`` / ``orders`` 三件的形狀與
    ``karst.runs.RunStore.record_simulation`` 收的一模一樣,故此落痕一句就接得通。
    """

    backtest: RuleBacktestResult
    params: TrendSwingParams
    risk: RiskSettings

    # ---- 落痕那三件 ----
    @property
    def equity_curve(self) -> pd.Series:
        return self.backtest.equity_curve

    @property
    def holdings(self) -> pd.DataFrame:
        return self.backtest.holdings

    @property
    def orders(self) -> tuple[Any, ...]:
        return self.backtest.orders

    @property
    def engine_name(self) -> str:
        return self.backtest.engine_name

    # ---- 規則路徑特有的兩條序列(查帳用)----
    @property
    def cash(self) -> pd.Series:
        return self.backtest.cash

    @property
    def sizing_basis(self) -> pd.Series:
        """逐日注碼基數:當日開市那一刻的權益(CONTEXT.md「注碼基數」)。"""
        return self.backtest.sizing_basis

    @property
    def breaker_blocked(self) -> pd.Series:
        """逐日熔斷狀態:該日有沒有落閘停止新入場。"""
        return self.backtest.breaker_blocked

    # ---- 成績 ----
    @property
    def rule_params(self) -> RuleStrategyParams:
        return self.backtest.params

    @property
    def entry_signals(self) -> int:
        return self.backtest.entry_signals

    @property
    def total_return(self) -> float:
        return self.backtest.total_return

    @property
    def max_drawdown(self) -> float:
        return self.backtest.max_drawdown

    @property
    def worst_month_drawdown(self) -> float:
        return self.backtest.worst_month_drawdown

    @property
    def blocked_days(self) -> int:
        return self.backtest.blocked_days

    def orders_frame(self) -> pd.DataFrame:
        return self.backtest.orders_frame()


def run_trend_swing(
    *,
    panel: BarPanel,
    params: TrendSwingParams,
    risk: RiskSettings,
    engine: RuleEngine | None = None,
) -> TrendSwingResult:
    """五件規則加共用風控層全開,跑一次完整回測。

    走的是引擎適配層的**規則路徑**(``run_rule_strategy``):組合層熔斷與「注碼
    基數取當下權益」兩件,只有在看得見現金與權益那一層才表達得到(規格 6.2)。
    哪一個第三方引擎在背後跑,本檔一個字都不提(D-007 第 3 條)。
    """
    if not isinstance(panel, BarPanel):
        raise ContractViolation(
            f"K 線面板要是 BarPanel,收到 {type(panel).__name__};"
            "請先用 build_bar_panel 或 BarPanel.from_frames 核對開高低收四張表"
        )
    if not isinstance(params, TrendSwingParams):
        raise ContractViolation(f"策略參數要是 TrendSwingParams,收到 {type(params).__name__}")
    if not isinstance(risk, RiskSettings):
        raise ContractViolation(f"風控設定要是 RiskSettings,收到 {type(risk).__name__}")

    backtest = run_rule_strategy(
        panel=panel, params=params.rule_params(risk), engine=engine
    )
    return TrendSwingResult(backtest=backtest, params=params, risk=risk)


# ----------------------------------------------------------------------
# 登記:因子、策略、參數集、風控引用,一律經唯一入口(D-020 第 4 條)
# ----------------------------------------------------------------------


def register_trend_swing(
    gateway: Any,
    *,
    strategy_name: str,
    snapshot_id: str,
    param_set_name: str,
    rebalance_cadence: str | None = None,
    values: Mapping[str, Any] | None = None,
    description: str | None = None,
) -> tuple[StrategyVersion, ParamSet]:
    """經唯一入口登記入場突破因子、這套策略與一個參數集,回傳策略版本與參數集。

    ``gateway`` 是 ``karst.gateway.Gateway``——人手與 agent 同一道門,寫入者簽章
    由它蓋(D-020 第 4 條)。本函式**不**繞過它直接寫庫。

    ``values`` 就是參數集的全部取值,用 ``param_values(params, risk)`` 砌:策略
    九格 + 風控三格。本函式一個取值都不補——缺就寫不入,亦跑不動。

    順帶做兩件登記:三條共用風控規則入庫(重覆呼叫回同一批列,單一定義),
    以及記低這套策略引用了其中哪幾條(有給取值的就是引用)。
    """
    snapshot = str(snapshot_id or "").strip()
    if not snapshot:
        raise ContractViolation("登記趨勢波段策略要註明數據快照編號,追溯不可留空")

    gateway.register_risk_rules()

    procedure = FormulaProcedure(
        formula=BREAKOUT_FACTOR_FORMULA, input_data_version=snapshot
    )
    try:
        gateway.register_factor(
            BREAKOUT_FACTOR_NAME,
            scale_kind=BREAKOUT_FACTOR_SCALE,
            procedure=procedure,
            description="趨勢波段策略的入場訊號(規格 5.4);N 是參數集裡的可掃描參數",
        )
    except DuplicateDefinition:
        head = gateway.store.get_factor_version(BREAKOUT_FACTOR_NAME)
        if getattr(head.procedure, "input_data_version", None) != snapshot:
            gateway.new_factor_version(
                BREAKOUT_FACTOR_NAME,
                scale_kind=head.scale_kind,
                procedure=procedure,
                description=f"趨勢波段策略的入場訊號,改用快照 {snapshot}",
            )

    factor_version = gateway.store.get_factor_version(BREAKOUT_FACTOR_NAME)
    factor_refs = [f"{BREAKOUT_FACTOR_NAME}@{factor_version.version_no}"]
    try:
        version, _ = gateway.register_strategy(
            strategy_name,
            strategy_type=TREND_SWING_STRATEGY_TYPE,
            factor_refs=factor_refs,
            description=description,
        )
    except DuplicateDefinition:
        head = gateway.store.get_strategy_version(strategy_name)
        current = sorted(f"{f.name}@{f.version_no}" for f in head.factors)
        if current == sorted(factor_refs):
            version = head
        else:
            version, _ = gateway.new_strategy_version(
                strategy_name, factor_refs=factor_refs, description=description
            )

    # 同名同節奏同取值即沿用舊版——這條規矩住在唯一入口,本層不另抄一份(KARST-046)。
    param_set, _ = gateway.register_param_set(
        version.name,
        param_set_name=param_set_name,
        rebalance_cadence=rebalance_cadence,
        values=values,
        strategy_version_no=version.version_no,
    )
    gateway.attach_risk_rules(
        version.name,
        RiskSettings.from_param_values(param_set.values).referenced_keys,
        strategy_version_no=version.version_no,
    )
    return version, param_set


def record_trend_swing_run(
    runs: Any,
    result: TrendSwingResult,
    *,
    strategy_name: str,
    param_set_name: str,
    snapshot_id: str,
    engine_version: str,
    period_start: date | datetime | str | None = None,
    period_end: date | datetime | str | None = None,
    strategy_version_no: int | None = None,
    param_set_version_no: int | None = None,
    factor_version_ids: Sequence[int] | None = None,
) -> Any:
    """把一次趨勢波段回測交去 ``karst.runs`` 登記,回傳運行留痕。

    ``factor_version_ids`` 留空即由庫裡讀回這個策略版本引用住的因子版本——
    運行編號要蓋齊「策略版本 × 參數集 × 期間 × 數據快照 × 引擎版本」,
    追溯深度連因子那一層都要有(D-021 第 8、9 條)。
    """
    if factor_version_ids is None:
        version = runs.store.get_strategy_version(strategy_name, strategy_version_no)
        factor_version_ids = tuple(factor.factor_version_id for factor in version.factors)
    return runs.record_simulation(
        result,
        strategy_name=strategy_name,
        param_set_name=param_set_name,
        snapshot_id=snapshot_id,
        engine_version=engine_version,
        engine_name=result.engine_name,
        period_start=period_start,
        period_end=period_end,
        strategy_version_no=strategy_version_no,
        param_set_version_no=param_set_version_no,
        factor_version_ids=factor_version_ids,
    )


# ----------------------------------------------------------------------
# 案例:入場規則在歷史上觸發過幾多次、每次收場如何(規格 5.4 第 5 條、6.5)
# ----------------------------------------------------------------------

# 出場原因(exit reason)與它的中文名住引擎那邊(``karst.engine.rules``):
# 出場規約全倉只此一份,本檔只是轉引,不另寫一套。案例表按這個次序數。
CASE_EXIT_REASONS: Final[tuple[str, ...]] = (EXIT_STOP, EXIT_TARGET, EXIT_UNCLOSED)

CASE_COLUMNS: Final[tuple[str, ...]] = (
    "entity_id",
    "signal_date",
    "entry_date",
    "entry_price",
    "stop_price",
    "target_price",
    "reward_risk",
    "exit_date",
    "exit_price",
    "exit_reason",
    "exit_reason_name",
    "holding_days",
    "return_pct",
    "r_multiple",
)


@dataclass(frozen=True, slots=True)
class EntryCase:
    """入場規則觸發的一個**案例**:一次訊號,由入場行到收場。

    案例不是交易。回測那一邊受現金、單一持倉市值上限與熔斷所限,同一日發出十個
    訊號可能只做得成兩筆;案例這一邊不管錢,問的是「這條規則本身在歷史上出現過
    幾多次、每次收場如何」——規格 5.4 第 5 條那條「約 500 個歷史案例」量的正是它。

    ``reward_risk`` 是這一次的**計劃賠率**,以真正成交價為基準:
    (目標 − 成交價)/(成交價 − 止蝕)。它與規則 3 那道閘量的不是同一刻——閘在
    訊號日收市判,計劃在下一根開價成交;中間跳空升得多,成交價這一邊的賠率就會
    低過門檻。兩個數不同不是錯,是跳空本身的代價。

    ``r_multiple`` 是**已實現賠率**:賺蝕除以當初計劃要冒的風險(成交價 − 止蝕價)。
    止蝕收場約等於 −1,觸目標收場約等於計劃賠率。
    """

    entity_id: int
    signal_date: str
    entry_date: str
    entry_price: float
    stop_price: float
    target_price: float
    reward_risk: float
    exit_date: str
    exit_price: float
    exit_reason: str
    holding_days: int
    return_pct: float
    r_multiple: float

    @property
    def exit_reason_name(self) -> str:
        return EXIT_REASONS[self.exit_reason]

    @property
    def is_win(self) -> bool:
        return self.return_pct > 0.0

    @property
    def is_closed(self) -> bool:
        """有沒有真的按規則收場(止蝕或觸目標)。期末未平的不算。"""
        return self.exit_reason != EXIT_UNCLOSED


def entry_cases(panel: BarPanel, params: RuleStrategyParams) -> tuple[EntryCase, ...]:
    """把入場規則在整個面板(全部實體 × 全期)觸發的每一次攤成一個案例。

    訊號由 ``build_rule_signals`` 算——與回測用的是**同一個函式**,所以案例表數
    的正是回測那條路認得的訊號,不是另一套自己寫的規則。

    收場的日子、價位與**出場原因**同樣不在本檔判:一律取引擎交回來那份
    ``signals.exits``(``karst.engine.rules.resolve_exits``),與回測落賣單時查的是
    **同一份表**。所以同一個入場,回測做得成的話,案例的收場日子與價位一定對得上;
    不同的只是回測會因為沒錢或熔斷而做不成——案例照樣記。
    """
    if not isinstance(panel, BarPanel):
        raise ContractViolation(f"K 線面板要是 BarPanel,收到 {type(panel).__name__}")
    if not isinstance(params, RuleStrategyParams):
        raise ContractViolation(f"規則參數要是 RuleStrategyParams,收到 {type(params).__name__}")

    signals = build_rule_signals(panel, params)
    exits = signals.exits
    dates = [pd.Timestamp(day).strftime("%Y-%m-%d") for day in panel.dates]
    entity_ids = panel.entity_ids
    opens = panel.open.to_numpy(dtype=float)
    closes = panel.close.to_numpy(dtype=float)
    rows, columns = closes.shape

    cases: list[EntryCase] = []
    for column in range(columns):
        for signal in np.flatnonzero(signals.entries[:, column]):
            bar = int(signal)
            reason = exits.reason_at(bar, column)
            if reason is None:
                # 訊號日成形的計劃,到成交那一根已經跌穿止蝕:引擎照樣不會入場
                continue

            entry_price = float(opens[bar, column])
            stop = float(signals.stop_level[bar, column])
            target = float(signals.target_level[bar, column])
            risk_per_share = entry_price - stop
            exit_bar = int(exits.exit_bar[bar, column])
            exit_price = float(exits.exit_price[bar, column])

            cases.append(
                EntryCase(
                    entity_id=int(entity_ids[column]),
                    signal_date=dates[bar - 1],
                    entry_date=dates[bar],
                    entry_price=entry_price,
                    stop_price=stop,
                    target_price=target,
                    reward_risk=float((target - entry_price) / risk_per_share),
                    exit_date=dates[exit_bar],
                    exit_price=float(exit_price),
                    exit_reason=reason,
                    holding_days=int(exit_bar - bar),
                    return_pct=float(exit_price / entry_price - 1.0),
                    r_multiple=float((exit_price - entry_price) / risk_per_share),
                )
            )

    cases.sort(key=lambda case: (case.entry_date, case.entity_id))
    return tuple(cases)


def cases_frame(cases: Sequence[EntryCase]) -> pd.DataFrame:
    """案例表:一案一列,欄位見 ``CASE_COLUMNS``。落 parquet 或 csv 皆可。"""
    return pd.DataFrame(
        [
            {
                "entity_id": case.entity_id,
                "signal_date": case.signal_date,
                "entry_date": case.entry_date,
                "entry_price": case.entry_price,
                "stop_price": case.stop_price,
                "target_price": case.target_price,
                "reward_risk": case.reward_risk,
                "exit_date": case.exit_date,
                "exit_price": case.exit_price,
                "exit_reason": case.exit_reason,
                "exit_reason_name": case.exit_reason_name,
                "holding_days": case.holding_days,
                "return_pct": case.return_pct,
                "r_multiple": case.r_multiple,
            }
            for case in cases
        ],
        columns=list(CASE_COLUMNS),
    )


@dataclass(frozen=True, slots=True)
class CaseStats:
    """一批案例的驗證結果:數量、勝率、平均賠率,加逐個出場原因的分佈。

    ``win_rate`` 算的是**全部**案例(期末未平的按最後一根收市價結算),
    ``closed_win_rate`` 只算真的按規則收場那一批。兩個一併交出來,免得
    「未平倉的算不算贏」變成一個要靠猜的問題。

    案例一個都沒有時,四個比率是 ``None`` 而不是 0——沒有樣本就沒有勝率,
    填 0 會被讀成「全部輸清」(與 ``karst.metrics`` 同制)。
    """

    cases: int
    closed: int
    wins: int
    win_rate: float | None
    closed_win_rate: float | None
    average_return: float | None
    average_r_multiple: float | None
    average_reward_risk: float | None
    average_holding_days: float | None
    by_reason: Mapping[str, int]

    def as_row(self) -> dict[str, Any]:
        return {
            "cases": self.cases,
            "closed": self.closed,
            "wins": self.wins,
            "win_rate": self.win_rate,
            "closed_win_rate": self.closed_win_rate,
            "average_return": self.average_return,
            "average_r_multiple": self.average_r_multiple,
            "average_reward_risk": self.average_reward_risk,
            "average_holding_days": self.average_holding_days,
            **{f"reason_{key}": self.by_reason.get(key, 0) for key in CASE_EXIT_REASONS},
        }


def case_stats(cases: Sequence[EntryCase]) -> CaseStats:
    """數一批案例:幾多個、贏幾多、平均賠率幾多。"""
    items = list(cases)
    by_reason = {key: 0 for key in CASE_EXIT_REASONS}
    for case in items:
        by_reason[case.exit_reason] += 1

    if not items:
        return CaseStats(
            cases=0, closed=0, wins=0, win_rate=None, closed_win_rate=None,
            average_return=None, average_r_multiple=None, average_reward_risk=None,
            average_holding_days=None, by_reason=MappingProxyType(by_reason),
        )

    closed = [case for case in items if case.is_closed]
    wins = [case for case in items if case.is_win]
    closed_wins = [case for case in closed if case.is_win]
    return CaseStats(
        cases=len(items),
        closed=len(closed),
        wins=len(wins),
        win_rate=len(wins) / len(items),
        closed_win_rate=(len(closed_wins) / len(closed)) if closed else None,
        average_return=float(np.mean([case.return_pct for case in items])),
        average_r_multiple=float(np.mean([case.r_multiple for case in items])),
        average_reward_risk=float(np.mean([case.reward_risk for case in items])),
        average_holding_days=float(np.mean([case.holding_days for case in items])),
        by_reason=MappingProxyType(by_reason),
    )


# ----------------------------------------------------------------------
# 掃描:策略九格 × 風控三格,全部可掃
# ----------------------------------------------------------------------

SWEEP_COLUMNS: Final[tuple[str, ...]] = (*STRATEGY_PARAM_KEYS, *RISK_SWEEP_COLUMNS)


def params_grid(
    *,
    breakout_lookback_days: Sequence[int],
    swing_lookback_days: Sequence[int],
    min_stop_fraction: Sequence[float],
    max_stop_fraction: Sequence[float],
    max_position_fraction: Sequence[float],
    equity_basis: Sequence[str],
    initial_cash: Sequence[float],
    fees: Sequence[float],
    tie_break_seed: Sequence[int],
) -> tuple[TrendSwingParams, ...]:
    """策略那九格的取值格,砌成一串參數。九串都要明寫,一串都沒有預設值。

    只掃其中一格就把其餘八串各寫一個值——**沒有一格是掃不到的**(D-008 第 3 條)。
    """
    axes = {
        "breakout_lookback_days": list(breakout_lookback_days),
        "swing_lookback_days": list(swing_lookback_days),
        "min_stop_fraction": list(min_stop_fraction),
        "max_stop_fraction": list(max_stop_fraction),
        "max_position_fraction": list(max_position_fraction),
        "equity_basis": list(equity_basis),
        "initial_cash": list(initial_cash),
        "fees": list(fees),
        "tie_break_seed": list(tie_break_seed),
    }
    empty = [name for name, values in axes.items() if not values]
    if empty:
        raise ContractViolation(
            f"這幾格的掃描取值一個都沒有:{'、'.join(empty)};掃描不設預設值,要掃哪幾個一律寫明"
        )
    return tuple(
        TrendSwingParams(**dict(zip(axes, combination, strict=True)))
        for combination in product(*axes.values())
    )


@dataclass(frozen=True, slots=True)
class TrendSwingSweepCell:
    """掃描表的一格:一組取值(策略九格 + 風控三格),加它跑出來的成績。"""

    params: TrendSwingParams
    risk: RiskSettings
    entry_signals: int
    orders: int
    total_return: float
    max_drawdown: float
    worst_month_drawdown: float
    blocked_days: int

    def as_row(self) -> dict[str, Any]:
        row: dict[str, Any] = dict(self.params.to_param_values())
        for key in (PARAM_BREAKOUT_LOOKBACK, PARAM_SWING_LOOKBACK, PARAM_TIE_BREAK_SEED):
            row[key] = int(row[key])
        for key in (
            PARAM_MIN_STOP_FRACTION,
            PARAM_MAX_STOP_FRACTION,
            PARAM_MAX_POSITION_FRACTION,
            PARAM_INITIAL_CASH,
            PARAM_FEES,
        ):
            row[key] = float(row[key])
        row.update(
            {
                "per_trade_risk": self.risk.per_trade_risk,
                "monthly_loss_cap": self.risk.monthly_loss_cap,
                "reward_risk_floor": self.risk.reward_risk_floor,
                "entry_signals": self.entry_signals,
                "orders": self.orders,
                "total_return": self.total_return,
                "max_drawdown": self.max_drawdown,
                "worst_month_drawdown": self.worst_month_drawdown,
                "blocked_days": self.blocked_days,
            }
        )
        return row


@dataclass(frozen=True, slots=True)
class TrendSwingSweepResult:
    """一次趨勢波段參數掃描的全部結果。

    哪一格算好、是不是孤峰,由用戶看這張表定奪——本層一個「最優」都不替他揀
    (D-016 第 3 條參數穩健平原)。
    """

    cells: tuple[TrendSwingSweepCell, ...]
    engine_name: str

    def __len__(self) -> int:
        return len(self.cells)

    def frame(self) -> pd.DataFrame:
        """攤成一張表,次序與掃描次序一致。

        ``monthly_loss_cap`` 那一格空白(NaN)即這一組**不引用熔斷**,不是門檻為零。
        """
        return pd.DataFrame(
            [cell.as_row() for cell in self.cells], columns=list(SWEEP_COLUMNS)
        )


def sweep_trend_swing(
    *,
    panel: BarPanel,
    grid: Sequence[TrendSwingParams],
    risk_grid: RiskSweepGrid,
    engine: RuleEngine | None = None,
) -> TrendSwingSweepResult:
    """策略九格 × 風控三格逐格跑一次回測,交回整張表。

    風控那三格照走共用風控層的正本掃描器(``karst.risk.sweep_risk_settings``),
    本檔不另寫一次;策略那九格由 ``grid`` 逐份參數換入,其餘一字不動——所以格與
    格之間的差異只可能來自取值本身。
    """
    if not isinstance(panel, BarPanel):
        raise ContractViolation(f"K 線面板要是 BarPanel,收到 {type(panel).__name__}")
    if not isinstance(risk_grid, RiskSweepGrid):
        raise ContractViolation(f"風控取值格要是 RiskSweepGrid,收到 {type(risk_grid).__name__}")
    grid = tuple(grid)
    if not grid:
        raise ContractViolation("策略參數的掃描取值一份都沒有;掃描不設預設值,要掃哪幾組一律寫明")

    seed_settings = risk_grid.settings()[0]
    cells: list[TrendSwingSweepCell] = []
    engine_name = ""
    for params in grid:
        if not isinstance(params, TrendSwingParams):
            raise ContractViolation(
                f"掃描取值格的每一份都要是 TrendSwingParams,收到 {type(params).__name__}"
            )
        swept = sweep_risk_settings(
            panel=panel,
            params=params.rule_params(seed_settings),
            grid=risk_grid,
            engine=engine,
        )
        engine_name = swept.engine_name
        cells.extend(
            TrendSwingSweepCell(
                params=params,
                risk=cell.settings,
                entry_signals=cell.entry_signals,
                orders=cell.orders,
                total_return=cell.total_return,
                max_drawdown=cell.max_drawdown,
                worst_month_drawdown=cell.worst_month_drawdown,
                blocked_days=cell.blocked_days,
            )
            for cell in swept.cells
        )
    return TrendSwingSweepResult(cells=tuple(cells), engine_name=engine_name)
