"""因子混合策略(factor-mix strategy)的 ETF 版(D-012、規格 5.2)。

質素、價值、動能、低波四類**因子敞口**,v1 各買一隻現成因子 ETF,按參數集
指定的權重混成一個組合,按參數集指定的換倉節奏拉回目標比重。自算因子分數
選股是日後版本,不入本檔(D-012 第 2 條)。

三條紀律寫死在這裡:

1. **ETF 與股票走同一條可投資對象路徑**(D-012 第 2 條)。ETF 只是 ``entity_kind``
   為 ``etf`` 的實體,代號照 ``store.resolve_ticker`` 按日解析成實體編號,價格照
   ``PricePanel`` 那一張表——**適配層一個為 ETF 而設的分支都沒有**。把某一格的
   ETF 換成一隻股票,本檔一個字不用改。

2. **因子名一律落在「族名·具體定義」那一級**(規格 1.8、CONTEXT.md「因子族」)。
   「質素」只是族名,不是因子;登記入庫的是「質素·MSCI USA Sector Neutral
   Quality(QUAL)」。本檔沒有一條路寫得出單以族名登記的因子。

3. **四類的權重是參數集裡的可掃描參數**(D-008 第 3 條)。本檔查不到任何權重
   數值——連預設值都沒有;掃描一組權重只需重覆呼叫 ``run_factor_mix``,不用
   改一行碼。換倉節奏同樣無預設(D-009 第 7 條)。

用法::

    from karst.strategies.factor_mix import (
        FACTOR_ETF_SLEEVES, FactorMixParams, run_factor_mix,
    )

    params = FactorMixParams(
        cadence="quarterly",                       # 無預設,一定要寫
        weights={"weight_quality": 0.25, "weight_value": 0.25,
                 "weight_momentum": 0.25, "weight_low_vol": 0.25},
    )
    result = run_factor_mix(
        store=store, panel=panel, sleeves=FACTOR_ETF_SLEEVES, params=params
    )
    result.equity_curve      # 逐日淨值
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, ClassVar, Final

import numpy as np
import pandas as pd

from ..errors import ContractViolation
from ..models import FormulaProcedure
from ..store import FAMILY_SEPARATOR, DefinitionStore, ParamSet
from ..engine.cadence import rebalance_schedule
from ..engine.contracts import (
    CADENCES,
    CadenceNotSpecified,
    Order,
    PricePanel,
)
from ..engine.funnel import (
    STAGE_SCOPE,
    STAGE_SELECTED,
    SelectionTrace,
    SelectionTraceBuilder,
)
from ..engine.protocol import PortfolioEngine
from ..executor.contract import (
    ENGINE_TARGETS,
    KIND_NUMBER,
    KIND_TEXT,
    SLOT_CADENCE,
    TEXT_FOUR_PLACES,
    TEXT_VERBATIM,
    EntityRequest,
    FactorSpec,
    FactorVersionRef,
    ParamField,
    ParamSpec,
    ResolvedEntity,
    RunRequest,
    TargetPlan,
)

# 策略類型(store.STRATEGY_TYPES 八選一):因子混合屬多因子。
FACTOR_MIX_STRATEGY_TYPE: Final[str] = "multifactor"

# 這條路的逐股分數叫什麼(KARST-056)。這套策略**沒有排名這一步**——四格敞口
# 的比例由參數集寫定,每個換倉日照抄。所以每隻 ETF 那個數字是目標比重,不是
# 一個因子分數;欄名照實寫,不硬套「因子分數」的殼扮有排名。
SCORE_TARGET_WEIGHT: Final[str] = "目標比重"

# 權重加總的容差。只用來擋浮點尾數,不是「差不多就當一」——差得遠一律拒收。
_SUM_TOLERANCE: Final[float] = 1e-9

# 換倉節奏那一格在參數規格與掃描格裡的名。**全倉一份**:掃描格那條軸
# (``karst.sweep.factor_mix.CADENCE_AXIS``)轉引本欄,兩邊飄開即同一格會寫成
# 兩個參數集。
CADENCE_PARAM: Final[str] = "cadence"


@dataclass(frozen=True, slots=True)
class FactorSleeve:
    """一格因子敞口的定義:哪一族因子、哪一個具體定義、由哪一隻可投資對象承載。

    ``family`` 只是分類(規格 1.8),真正落庫的名是 ``factor_name``——
    「族名·具體定義」。``weight_key`` 是這一格在參數集裡的參數名:權重的值
    住在參數集,不住在這裡。
    """

    family: str
    specific: str
    ticker: str
    display_name: str
    weight_key: str

    def __post_init__(self) -> None:
        for label, value in (
            ("因子族名", self.family),
            ("因子具體定義", self.specific),
            ("交易代號", self.ticker),
            ("顯示名", self.display_name),
            ("參數名", self.weight_key),
        ):
            if not str(value or "").strip():
                raise ContractViolation(f"因子敞口的{label}不可留空")
        if FAMILY_SEPARATOR in self.family:
            raise ContractViolation(
                f"因子族名不可含分隔符「{FAMILY_SEPARATOR}」:{self.family!r};"
                "族名只是分類,具體定義寫在 specific 那一格"
            )

    @property
    def factor_name(self) -> str:
        """落庫的因子名:「族名·具體定義」。族名單獨永遠不會成為一個因子名。"""
        return f"{self.family}{FAMILY_SEPARATOR}{self.specific}"


# v1 的四格因子敞口(D-012 第 1 條:質素、價值、動能、低波)。
# 這是一張**名單**,不是權重:四格各佔多少由參數集話事,本檔查不到任何權重數值。
# 換一套 ETF(例如改用標普系的 SPHQ / SPVU / SPMO / SPLV)只需另砌一個
# ``FactorSleeve`` 名單傳入,本檔一個字不用改。
FACTOR_ETF_SLEEVES: Final[tuple[FactorSleeve, ...]] = (
    FactorSleeve(
        family="質素",
        specific="MSCI USA Sector Neutral Quality(QUAL)",
        ticker="QUAL",
        display_name="iShares MSCI USA Quality Factor ETF",
        weight_key="weight_quality",
    ),
    FactorSleeve(
        family="價值",
        specific="MSCI USA Enhanced Value(VLUE)",
        ticker="VLUE",
        display_name="iShares MSCI USA Value Factor ETF",
        weight_key="weight_value",
    ),
    FactorSleeve(
        family="動能",
        specific="MSCI USA Momentum SR Variant(MTUM)",
        ticker="MTUM",
        display_name="iShares MSCI USA Momentum Factor ETF",
        weight_key="weight_momentum",
    ),
    FactorSleeve(
        family="低波",
        specific="MSCI USA Minimum Volatility(USMV)",
        ticker="USMV",
        display_name="iShares MSCI USA Min Vol Factor ETF",
        weight_key="weight_low_vol",
    ),
)


@dataclass(frozen=True, slots=True)
class FactorMixParams:
    """跑一次因子混合回測的全部參數。

    兩個欄位刻意沒有預設值:

    - ``cadence`` 換倉節奏——D-009 第 7 條明令引擎與策略皆不設預設,每次執行
      由用戶指定。
    - ``weights`` 四類的權重——D-008 第 3 條:策略內部數值一律做成可掃描參數,
      改參數不用改碼。鍵是 ``FactorSleeve.weight_key``。

    權重可以加總少於一(餘下的是現金),但**不可多於一**——v1 不做槓桿,亦
    不做淡倉,故此負權重一律拒收。
    """

    cadence: str
    weights: Mapping[str, float]
    initial_cash: float = 100_000.0
    fees: float = 0.0

    def __post_init__(self) -> None:
        if self.cadence is None or not str(self.cadence).strip():
            raise CadenceNotSpecified(
                "缺換倉節奏(rebalance cadence):"
                f"{sorted(CADENCES)} 揀一個。因子混合策略不設預設節奏(D-009 第 7 條)"
            )
        cadence = str(self.cadence).strip()
        if cadence not in CADENCES:
            raise ContractViolation(f"換倉節奏只收 {sorted(CADENCES)},收到 {self.cadence!r}")

        items = dict(self.weights or {})
        if not items:
            raise ContractViolation(
                "缺權重:四類因子敞口各佔多少要逐格寫明,本策略不設預設權重(D-008 第 3 條)"
            )

        cleaned: dict[str, float] = {}
        for key, value in items.items():
            name = str(key).strip()
            if not name:
                raise ContractViolation("權重的參數名留空")
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ContractViolation(f"權重「{name}」不是數字:{value!r}") from exc
            if not np.isfinite(number):
                raise ContractViolation(f"權重「{name}」不是有限數:{value!r}")
            if number < 0.0:
                raise ContractViolation(
                    f"權重「{name}」是負數 {number};v1 因子混合不做淡倉"
                )
            cleaned[name] = number

        total = sum(cleaned.values())
        if total <= 0.0:
            raise ContractViolation("四格權重全部是零,混不出一個組合")
        if total > 1.0 + _SUM_TOLERANCE:
            raise ContractViolation(
                f"權重加總 {total};v1 因子混合不做槓桿,加總不可多於一"
                "(少於一即餘下的持現金)"
            )

        initial_cash = float(self.initial_cash)
        if not np.isfinite(initial_cash) or initial_cash <= 0.0:
            raise ContractViolation(f"起始本金要是正數,收到 {self.initial_cash!r}")
        fees = float(self.fees)
        if not np.isfinite(fees) or fees < 0.0:
            raise ContractViolation(f"手續費率不可為負,收到 {self.fees!r}")

        object.__setattr__(self, "cadence", cadence)
        object.__setattr__(self, "weights", cleaned)
        object.__setattr__(self, "initial_cash", initial_cash)
        object.__setattr__(self, "fees", fees)

    @classmethod
    def from_param_set(
        cls,
        param_set: ParamSet,
        sleeves: Sequence[FactorSleeve],
        *,
        initial_cash: float = 100_000.0,
        fees: float = 0.0,
    ) -> "FactorMixParams":
        """由一個已登記的參數集砌出參數:節奏與四格權重全部由參數集話事。

        參數集缺其中一格即拒收——參數無預設值,缺就寫不入亦跑不動(KARST-022)。
        """
        missing = [s.weight_key for s in sleeves if s.weight_key not in param_set.values]
        if missing:
            raise ContractViolation(
                f"參數集「{param_set.name}」第 {param_set.version_no} 版缺權重:"
                f"{'、'.join(missing)};參數無預設值,要用的一律寫明"
            )
        return cls(
            cadence=param_set.rebalance_cadence,
            weights={s.weight_key: param_set.values[s.weight_key] for s in sleeves},
            initial_cash=initial_cash,
            fees=fees,
        )


@dataclass(frozen=True, slots=True)
class FactorExposure:
    """一格因子敞口解析之後的樣子:掛住哪一個實體、蓋住因子的哪一版、佔幾多。

    ``entity_id`` 由 ``store.resolve_ticker`` 按日解析而來——與股票同一個
    函式、同一張映射表(D-026 第 2 條)。
    """

    sleeve: FactorSleeve
    entity_id: int
    entity_kind: str
    factor_version_id: int
    factor_version_no: int
    weight: float

    @property
    def factor_name(self) -> str:
        return self.sleeve.factor_name


@dataclass(frozen=True, slots=True)
class FactorMixRebalance:
    """一次換倉的帳:決策日排到期,下一根 K 線按目標比重拉倉。

    ``decision_date`` 是節奏排出來的那一日;``execution_date`` 是它之後**下一根
    可交易 K 線**,成交價取該根的開價(D-021 第 3 條)。與排名策略不同,這裡
    看的不是因子值排名而是參數集寫定的權重——所以每次換倉的目標比重都一樣,
    改變的只是市價漂移之後要補回多少。
    """

    decision_date: str
    execution_date: str
    weights: tuple[tuple[int, float], ...]

    @property
    def entity_ids(self) -> tuple[int, ...]:
        return tuple(entity_id for entity_id, weight in self.weights if weight > 0.0)


@dataclass(frozen=True, slots=True)
class FactorMixResult:
    """一次因子混合回測的結果,連同追溯得回去的來歷。

    形狀與 ``karst.runs.RunStore.record_simulation`` 收的一模一樣(逐日淨值、
    逐日持倉、逐筆交易),故此落痕一句就接得通。
    """

    equity_curve: pd.Series
    holdings: pd.DataFrame
    orders: tuple[Order, ...]
    rebalances: tuple[FactorMixRebalance, ...]
    params: FactorMixParams
    exposures: tuple[FactorExposure, ...]
    engine_name: str
    # 選股痕跡(KARST-056)。留空即這次沒有交出來。
    selection: SelectionTrace | None = None

    @property
    def candidates(self) -> pd.DataFrame | None:
        """逐個換倉決策日,範圍 → 入選兩層的名單。"""
        return None if self.selection is None else self.selection.candidates

    @property
    def factor_scores(self) -> pd.DataFrame | None:
        """逐個換倉決策日、逐隻 ETF 的目標比重,連當日排名。"""
        return None if self.selection is None else self.selection.factor_scores

    @property
    def total_return(self) -> float:
        """全期累計回報。逐日淨值第一日為基準。"""
        return float(self.equity_curve.iloc[-1] / self.equity_curve.iloc[0] - 1.0)

    @property
    def factor_version_ids(self) -> tuple[int, ...]:
        """這次成績蓋住的四個因子版本(追溯深度,D-021 第 8 條)。"""
        return tuple(exposure.factor_version_id for exposure in self.exposures)

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

    def exposures_frame(self) -> pd.DataFrame:
        """四格敞口攤成一張表:族名、因子名、代號、實體編號、實體種類、權重。"""
        return pd.DataFrame(
            [
                {
                    "family": exposure.sleeve.family,
                    "factor_name": exposure.factor_name,
                    "factor_version_no": exposure.factor_version_no,
                    "ticker": exposure.sleeve.ticker,
                    "entity_id": exposure.entity_id,
                    "entity_kind": exposure.entity_kind,
                    "weight": exposure.weight,
                }
                for exposure in self.exposures
            ],
            columns=[
                "family", "factor_name", "factor_version_no", "ticker",
                "entity_id", "entity_kind", "weight",
            ],
        )


# ----------------------------------------------------------------------
# 解析:代號 → 實體編號 → 目標比重表
# ----------------------------------------------------------------------


def factor_exposures(
    sleeves: Sequence[FactorSleeve],
    params: FactorMixParams,
    *,
    entities: Mapping[str, ResolvedEntity],
    factors: Mapping[str, FactorVersionRef],
) -> tuple[FactorExposure, ...]:
    """把四格敞口砌成「實體編號 × 因子版本 × 權重」。**純函數,不開庫。**

    代號怎樣解析、有沒有撞實體,由執行台那一段解析(``karst.executor`` 的
    ``resolve_entities``)一手包辦;本函式只做因子混合真正獨有的那件事——把敞口
    名單、權重、已解析的實體與因子版本對起來。
    """
    if not sleeves:
        raise ContractViolation("因子混合最少要有一格敞口")

    exposures: list[FactorExposure] = []
    for sleeve in sleeves:
        if sleeve.weight_key not in params.weights:
            raise ContractViolation(
                f"參數缺「{sleeve.weight_key}」({sleeve.family}族)的權重;無預設值"
            )
        entity = entities[sleeve.ticker]
        version = factors[sleeve.factor_name]
        exposures.append(
            FactorExposure(
                sleeve=sleeve,
                entity_id=int(entity.entity_id),
                entity_kind=entity.entity_kind,
                factor_version_id=version.factor_version_id,
                factor_version_no=version.version_no,
                weight=float(params.weights[sleeve.weight_key]),
            )
        )
    return tuple(exposures)


def resolve_exposures(
    store: DefinitionStore,
    sleeves: Sequence[FactorSleeve],
    params: FactorMixParams,
    *,
    on_date: date | datetime | str,
) -> tuple[FactorExposure, ...]:
    """把四格敞口解析成「實體編號 × 因子版本 × 權重」(開庫的那個版本)。

    代號一律經 ``store.resolve_ticker`` **按那一日**解析(D-026 第 2 條)——
    這正是股票走的同一條路;ETF 在這裡沒有任何特殊待遇,分別只在解析出來的
    實體那一欄 ``entity_kind`` 寫住 ``etf`` 而不是 ``company``。

    解析那一段本身住在執行台(全倉一份),本函式只是把它接上因子版本。
    """
    if not sleeves:
        raise ContractViolation("因子混合最少要有一格敞口")

    from ..executor.executor import resolve_entities

    entities = resolve_entities(
        store,
        EntityRequest(exposures=tuple(sleeve.ticker for sleeve in sleeves)),
        on_date=on_date,
    )
    factors = {
        sleeve.factor_name: _factor_ref(store, sleeve.factor_name) for sleeve in sleeves
    }
    return factor_exposures(sleeves, params, entities=entities, factors=factors)


def _factor_ref(store: DefinitionStore, factor_name: str) -> FactorVersionRef:
    version = store.get_factor_version(factor_name)
    return FactorVersionRef(
        name=factor_name,
        factor_version_id=version.factor_version_id,
        version_no=version.version_no,
    )


def factor_mix_schedule(
    dates: pd.DatetimeIndex, cadence: str
) -> tuple[tuple[pd.Timestamp, pd.Timestamp], ...]:
    """排期:節奏排出來的每一次換倉,加最前那一次建倉。

    節奏本身(``karst.engine.cadence``)排的是「每個週期最後一根 K 線做決策日,
    下一根做執行日」。排名策略要等第一個因子讀數才落得到注,所以第一次換倉
    最早也在第一個週期尾;混權重策略不同——**權重在回測開始之前已經由參數集
    寫定,沒有東西要等**,故此第一根 K 線就是決策日,第二根按開價建倉。少了
    這一次,季度節奏會白白持三個月現金,交出來的淨值不是這套策略的成績。

    可執行時點照舊不變:成交永遠在決策日之後那一根 K 線的開價,不會同根成交
    (D-021 第 3 條)。
    """
    if len(dates) < 2:
        raise ContractViolation(
            f"這個價格面板只有 {len(dates)} 根 K 線;要有決策日,還要有它之後"
            "的下一根 K 線可以成交"
        )
    schedule = list(rebalance_schedule(dates, cadence))
    opening = (dates[0], dates[1])
    if not schedule or schedule[0][1] != opening[1]:
        schedule.insert(0, opening)
    return tuple(schedule)


def factor_mix_targets(
    *,
    dates: pd.DatetimeIndex,
    entity_ids: Sequence[int],
    exposures: Sequence[FactorExposure],
    cadence: str,
) -> tuple[pd.DataFrame, tuple[FactorMixRebalance, ...]]:
    """目標比重表:換倉的**執行日**那一行寫比重,其餘一律 ``NaN``。

    ``NaN`` 的意思是「這一根 K 線不下單」;寫 0 的意思是「清倉到零」——兩者
    不可混為一談(CONTEXT.md「目標比重表」)。面板上不屬任何一格敞口的實體
    (例如同一個快照裡的 SPY、QQQ)每次換倉一律寫 0,即從不持有。
    """
    columns = [int(entity) for entity in entity_ids]
    known = set(columns)
    unknown = [e.entity_id for e in exposures if e.entity_id not in known]
    if unknown:
        raise ContractViolation(
            f"敞口的實體 {unknown} 不在價格面板裡;沒有價格就落不到注,不猜、不當零"
        )

    targets = pd.DataFrame(np.nan, index=dates, columns=columns, dtype=float)
    row = {exposure.entity_id: exposure.weight for exposure in exposures}

    rebalances: list[FactorMixRebalance] = []
    for decision_day, execution_day in factor_mix_schedule(dates, cadence):
        targets.loc[execution_day, :] = 0.0  # 不屬任何一格的一律清倉
        for entity_id, weight in row.items():
            targets.loc[execution_day, entity_id] = weight
        rebalances.append(
            FactorMixRebalance(
                decision_date=pd.Timestamp(decision_day).strftime("%Y-%m-%d"),
                execution_date=pd.Timestamp(execution_day).strftime("%Y-%m-%d"),
                weights=tuple(sorted((int(k), float(v)) for k, v in row.items())),
            )
        )
    return targets, tuple(rebalances)


def factor_mix_selection_trace(
    rebalances: Sequence[FactorMixRebalance],
) -> SelectionTrace | None:
    """把每一次換倉的目標比重,攤成選股漏斗的候選名單與逐股分數(KARST-056)。

    這套策略的漏斗**只有兩層**,而那正是它的真相:範圍就是四格敞口那四隻 ETF,
    入選就是比重大於零那幾隻。中間的基本面關與技術關一層都沒有——比例由參數集
    寫定,沒有任何一道篩選閘(D-013 明言每個策略自選一至多層,多數只用一兩層)。
    畫一個空關口出來扮四層,只會令人以為它篩過而其實沒有。
    """
    if not rebalances:
        return None
    builder = SelectionTraceBuilder()
    for rebalance in rebalances:
        day = rebalance.decision_date
        weights = {int(entity): float(weight) for entity, weight in rebalance.weights}
        builder.stage(day, STAGE_SCOPE, sorted(weights))
        builder.stage(
            day,
            STAGE_SELECTED,
            sorted(entity for entity, weight in weights.items() if weight > 0.0),
        )
        builder.score(day, SCORE_TARGET_WEIGHT, weights)
    return builder.build()


# ----------------------------------------------------------------------
# 策略合約:這條策略真正獨有的那四件(KARST-090)
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FactorMixContract:
    """因子混合策略的**策略合約**(見 ``karst.executor.contract``)。

    登記、驗參數、解析實體、叫引擎、查重、落痕、算指標、判失敗運行**一件都不在
    這裡**——那些每條策略做法一模一樣的事,全部住在策略執行台。本類只交出四件:
    參數規格、要登記哪幾條因子、要解析哪些代號、以及策略本體 ``plan``。

    ``initial_cash`` 與 ``fees`` 無預設值,但它們**不是參數規格的一格**:它們是
    帳戶設定,不入參數集亦不入運行編號——把它們寫進參數集會令全部既有正式運行
    當場換編號(參數集多一格即多一版,版本號是運行編號的原料)。兩格容許明寫
    ``None``,那是「這份合約只用來登記」(見 ``for_setup``);一叫 ``plan()``
    就當場拒收,不會靜靜地用一個猜出來的本金跑出一條淨值。
    """

    sleeves: tuple[FactorSleeve, ...]
    initial_cash: float | None
    fees: float | None

    strategy_type: ClassVar[str] = FACTOR_MIX_STRATEGY_TYPE
    #: 漏斗只有兩層,而那正是它的真相(見 ``factor_mix_selection_trace``)。
    funnel_stages: ClassVar[tuple[str, ...]] = (STAGE_SCOPE, STAGE_SELECTED)
    engine_path: ClassVar[str] = ENGINE_TARGETS

    def __post_init__(self) -> None:
        sleeves = tuple(self.sleeves)
        if not sleeves:
            raise ContractViolation("因子混合最少要有一格敞口")
        object.__setattr__(self, "sleeves", sleeves)

    @classmethod
    def for_setup(cls, sleeves: Sequence[FactorSleeve]) -> "FactorMixContract":
        """只用來登記的一份合約:登記碰不到帳戶設定,所以兩格明寫留空。"""
        return cls(sleeves=tuple(sleeves), initial_cash=None, fees=None)

    @property
    def weight_keys(self) -> tuple[str, ...]:
        return tuple(sleeve.weight_key for sleeve in self.sleeves)

    def param_spec(self) -> ParamSpec:
        """四格權重 + 換倉節奏。**一格預設值都沒有,一格都掃得到**(D-008 第 3 條)。

        格數與掃描格認得的軸數相同:權重單純形格四條軸,加節奏那條選擇軸。
        """
        fields = [
            ParamField(
                name=sleeve.weight_key,
                kind=KIND_NUMBER,
                what=f"{sleeve.family}族({sleeve.ticker})佔組合的目標比重",
                label=f"{sleeve.family}族權重",
                lower=0.0,
                upper=1.0,
                lower_inclusive=True,
                upper_inclusive=True,
                text_style=TEXT_FOUR_PLACES,
            )
            for sleeve in self.sleeves
        ]
        fields.append(
            ParamField(
                name=CADENCE_PARAM,
                kind=KIND_TEXT,
                what="幾耐拉一次倉回目標比重",
                label="換倉節奏",
                choices=tuple(sorted(CADENCES)),
                text_style=TEXT_VERBATIM,
                slot=SLOT_CADENCE,
            )
        )
        return ParamSpec(fields=tuple(fields))

    def factor_specs(self, snapshot_id: str) -> tuple[FactorSpec, ...]:
        """四條因子。產生程序記成「持有這隻 ETF 一單位即取得該指數的因子敞口」,
        輸入數據版本就是這次的數據快照編號(D-021 第 6、8 條)。"""
        snapshot = str(snapshot_id or "").strip()
        if not snapshot:
            raise ContractViolation("登記因子敞口要註明數據快照編號,追溯不可留空")
        return tuple(
            FactorSpec(
                name=sleeve.factor_name,
                scale_kind="cardinal",
                procedure=FormulaProcedure(
                    formula=(
                        f"持有 {sleeve.ticker}({sleeve.display_name})一單位,"
                        f"即取得 {sleeve.specific} 的因子敞口"
                    ),
                    input_data_version=snapshot,
                ),
                description=f"{sleeve.family}族的 ETF 版因子敞口(D-012 第 2 條)",
            )
            for sleeve in self.sleeves
        )

    def needs_entities(self, params: Mapping[str, Any]) -> EntityRequest:
        """四格敞口那四隻代號,全部持得到。這條策略沒有只做訊號的線。"""
        return EntityRequest(exposures=tuple(sleeve.ticker for sleeve in self.sleeves))

    def params_from(self, values: Mapping[str, Any]) -> FactorMixParams:
        """把一組已驗取值收成 ``FactorMixParams``(加總不可多於一那條跨格規矩)。"""
        if self.initial_cash is None or self.fees is None:
            raise ContractViolation(
                "這份因子混合合約只用來登記(起始本金與手續費率留空),跑不動;"
                "要跑一次回測請明寫兩格帳戶設定"
            )
        return FactorMixParams(
            cadence=values[CADENCE_PARAM],
            weights={key: values[key] for key in self.weight_keys},
            initial_cash=self.initial_cash,
            fees=self.fees,
        )

    def plan(self, request: RunRequest) -> TargetPlan:
        """策略本體:砌一張「日期 × 實體編號 → 目標比重」的表。**純函數。**

        不開庫、不讀檔、不 import 第三方引擎——哪一件引擎在背後跑,本檔一個字
        都不提(D-007 第 3 條)。
        """
        params = self.params_from(request.params)
        exposures = factor_exposures(
            self.sleeves,
            params,
            entities=request.entities,
            factors=request.factors,
        )
        targets, rebalances = factor_mix_targets(
            dates=request.panel.dates,
            entity_ids=request.panel.entity_ids,
            exposures=exposures,
            cadence=params.cadence,
        )
        return TargetPlan(
            targets=targets,
            cadence=params.cadence,
            initial_cash=params.initial_cash,
            fees=params.fees,
            rebalances=rebalances,
            selection=factor_mix_selection_trace(rebalances),
            extras={"exposures": exposures, "params": params},
        )


# ----------------------------------------------------------------------
# 跑一次回測
# ----------------------------------------------------------------------


def run_factor_mix(
    *,
    store: DefinitionStore,
    panel: PricePanel,
    sleeves: Sequence[FactorSleeve],
    params: FactorMixParams,
    engine: PortfolioEngine | None = None,
) -> FactorMixResult:
    """四類因子敞口按參數集指定的權重混成一個組合,跑出一次完整回測。

    **本函式已經沒有引擎樣板**(KARST-090):揀哪一件引擎、目標比重路徑那句
    填空格,兩段都搬去了執行台,全倉各只此一份。留下的是一層薄殼,給尚未搬完
    的掃描跑法用;掃描本身搬入執行台之後(KARST-091)整件可以刪走。

    代號按**面板第一根 K 線那一日**解析成實體編號——ETF 與股票同一條路。
    """
    if not isinstance(panel, PricePanel):
        raise ContractViolation(
            f"價格面板要是 PricePanel,收到 {type(panel).__name__};"
            "請先用 PricePanel.from_frames 核對開價表與收價表"
        )
    from ..executor.executor import engine_for, resolve_entities, simulate_plan

    contract = FactorMixContract(
        sleeves=tuple(sleeves),
        initial_cash=params.initial_cash,
        fees=params.fees,
    )
    values = {**params.weights, CADENCE_PARAM: params.cadence}
    entities = resolve_entities(
        store,
        contract.needs_entities(values),
        on_date=panel.dates[0],
        known_entity_ids=tuple(panel.entity_ids),
    )
    factors = {
        sleeve.factor_name: _factor_ref(store, sleeve.factor_name)
        for sleeve in contract.sleeves
    }
    plan = contract.plan(
        RunRequest(
            panel=panel,
            params=values,
            entities=entities,
            factors=factors,
            snapshot_id="",
        )
    )
    engine = engine_for(contract, engine)
    engine_name = getattr(engine, "name", type(engine).__name__)
    simulation = simulate_plan(engine, panel, plan, engine_name=engine_name)

    return FactorMixResult(
        equity_curve=simulation.equity_curve,
        holdings=simulation.holdings,
        orders=tuple(simulation.orders),
        rebalances=tuple(plan.rebalances),
        params=plan.extras["params"],
        exposures=tuple(plan.extras["exposures"]),
        engine_name=engine_name,
        selection=plan.selection,
    )
