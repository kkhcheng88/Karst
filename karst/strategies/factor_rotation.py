"""因子輪動策略(factor rotation)的 ETF 版(KARST-036;D-008、D-012、D-021)。

因子混合策略(``karst.strategies.factor_mix``)每次換倉都拉回**同一組**寫死在參數集
裡的權重。本檔做的是另一件事:每到換倉的決策日,由一個**驅動器**(driver)看住四
隻因子 ETF 到當日收工為止的價格,算出這一期該怎樣分,再由下一根 K 線的開價執行。
權重不再是常數,而是一條隨訊號走的路。

三條紀律寫死在這裡:

1. **驅動器是可換件**。全部驅動器同一個接口:收一個 ``DriverView``(四隻 ETF 截至
   決策日的收價歷史,必要時加大市那一條),回四格權重。換驅動器**不改引擎、不改
   因子混合策略的目標比重路徑**——本檔照樣只砌一張「日期 × 實體編號 → 目標比重」
   的表交給 ``PortfolioEngine.simulate``,連換倉排期都是直接叫因子混合那一個
   (``factor_mix_schedule``)。自己寫一個驅動器插進來,本檔一個字不用改。

2. **訊號只可以用決策日收工前的數據**(D-021 第 3 條)。``DriverView.history`` 由
   ``closes.loc[:decision_date]`` 切出來,最後一行**就是**決策日——驅動器根本拿不到
   之後的價格,不是靠自律。成交照舊在決策日之後那一根 K 線的開價。

3. **參數無預設值**(D-008 第 3 條)。回望期 L、均線日數 M、換倉節奏、熱身期權重,
   全部要寫明。本檔查不到任何一個「常用取值」。

外部數據:**價格驅動器一個都不用**,宏觀驅動器**只用免費序列**(KARST-040)。
頭四個驅動器的訊號全部由六隻 ETF 自身的收價算出來;之後五個宏觀驅動器另收一張
宏觀面板(VIX、美債息率、信用利差代理、聯邦基金期貨),逐條列於 ``EXTERNAL_DATA``
——來源、免費與否、知情時間怎樣處置,三件事在那裡寫明。宏觀序列**不是可投資
對象**,不入實體表、不入價格面板(處置見 ``karst.data.macro``),所以它們影響的
永遠只是「四格怎樣分」,不會變成第五格持倉。

接口是**向後相容**地擴出來的:``DriverView.macro``、``rotation_targets(macro=…)``
兩處都是有預設值的新參數,留空即與 KARST-036 那四個驅動器一模一樣;不看宏觀的
驅動器連 ``macro`` 這個字都不用提。宏觀面板由執行台當一格 ``extras`` 交進來
(鍵 ``MACRO_INPUT``)。

用法(KARST-091 起走策略合約,策略自己不開庫、不碰引擎)::

    from karst.executor import Executor, RunRequest
    from karst.strategies.factor_rotation import FactorRotationContract
    from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES

    contract = FactorRotationContract(
        driver_key="factor_momentum",
        sleeves=FACTOR_ETF_SLEEVES,
        warmup_bars=252,
        warmup_weights={s.weight_key: 0.25 for s in FACTOR_ETF_SLEEVES},
        market_ticker="SPY",
        initial_cash=100_000.0,
        fees=0.0,
    )
    # 策略只交一張目標比重表出來;落痕、落格、判讀全部是執行台的事。
    plan = contract.plan(RunRequest(...))
    result.equity_curve      # 逐日淨值
    result.weights_frame()   # 逐次換倉那四格權重走過的路
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable, ClassVar, Final, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from ..errors import ContractViolation
from ..executor.contract import (
    ENGINE_TARGETS,
    KIND_INTEGER,
    KIND_NUMBER,
    KIND_TEXT,
    SLOT_CADENCE,
    TEXT_AUTO,
    TEXT_FOUR_PLACES,
    TEXT_VERBATIM,
    SLUG_VERBATIM,
    EntityRequest,
    FactorSpec,
    ParamField,
    ParamSpec,
    RunRequest,
    TargetPlan,
    check_count,
    check_ratio,
    cost_fields,
)
from ..store import DefinitionStore
from ..engine.contracts import (
    CADENCES,
    CadenceNotSpecified,
    Order,
    PricePanel,
    TradingCosts,
    resolve_costs,
)
from .factor_mix import (
    CADENCE_PARAM,
    FACTOR_ETF_SLEEVES,
    FACTOR_MIX_STRATEGY_TYPE,
    FactorMixContract,
    FactorSleeve,
    factor_mix_schedule,
)

# 策略類型(store.STRATEGY_TYPES 八選一):輪動仍然是多因子,與因子混合同類。
FACTOR_ROTATION_STRATEGY_TYPE: Final[str] = FACTOR_MIX_STRATEGY_TYPE

# 這條策略在參數集裡那幾個鍵。**它們同時是運行編號的原料**:改一個字,全部輪動
# 運行當場換編號,所以正本只此一份。
DRIVER_KEY: Final[str] = "driver"
"""驅動器的名。**它不是掃描格的一條軸**——一次掃描只掃一個驅動器(不同驅動器的
參數名根本不同,排不進同一個笛卡兒積),所以它寫在參數集的值裡做身份,不入名。"""

WARMUP_BARS_KEY: Final[str] = "warmup_bars"
WARMUP_PREFIX: Final[str] = "warmup_"
MACRO_SNAPSHOT_KEY: Final[str] = "macro_snapshot"
MACRO_SERIES_KEY: Final[str] = "macro_series"
MACRO_SERIES_SEPARATOR: Final[str] = "、"

# 權重加總的容差。只用來擋浮點尾數,不是「差不多就當一」。
_SUM_TOLERANCE: Final[float] = 1e-9

# 大市那一條線用的代號。**它只做訊號,一股不持**——它不是四格敞口之一。
DEFAULT_MARKET_TICKER: Final[str] = "SPY"

# 四格敞口在參數集裡的參數名。開關型驅動器要指名「押哪一格」,用得着這四個。
MOMENTUM_KEY: Final[str] = "weight_momentum"
LOW_VOL_KEY: Final[str] = "weight_low_vol"
QUALITY_KEY: Final[str] = "weight_quality"
VALUE_KEY: Final[str] = "weight_value"

# **外部數據清單**(驗收條件四)。KARST-036 那四個價格驅動器一個外部來源都不用,
# 故此清單本來是空的;KARST-040 加宏觀驅動器時照這裡的規矩逐條列明「來源、免費
# 與否、知情時間怎樣處置」才實作。日後再加序列,一樣先在這裡寫一行。
#
# 全部經 ``karst.data.macro`` 的來源適配器入宏觀快照,對齊價格快照那條主日曆,
# 知情時間一律**當日收市後可得**(D-021 第 3 條)——與價格同一級,成交照舊在決策
# 日之後那一根 K 線的開價。**一個付費來源、一把 API 鑰匙都沒有用。**
EXTERNAL_DATA: Final[tuple[Mapping[str, str], ...]] = (
    {
        "序列": "VIX、VIX_3M",
        "來源": "yfinance ^VIX / ^VIX3M",
        "免費": "是(無鑰匙)",
        "知情時間": "當日收市後可得",
        "用途": "恐慌水平與期限結構開關",
    },
    {
        "序列": "HY_ETF、IG_ETF",
        "來源": "yfinance HYG / LQD",
        "免費": "是(無鑰匙)",
        "知情時間": "當日收市後可得",
        "用途": "信用利差的免費替代(FRED 高收益 OAS 要 API 鑰匙,故不用)",
    },
    {
        "序列": "UST_3M、UST_5Y、UST_10Y、UST_30Y",
        "來源": "yfinance ^IRX / ^FVX / ^TNX / ^TYX",
        "免費": "是(無鑰匙)",
        "知情時間": "當日收市後可得",
        "用途": "美債息率與曲線斜度(2 年期以 ^IRX 替代,FRED DGS2 要鑰匙)",
    },
    {
        "序列": "FF_FUTURE",
        "來源": "yfinance ZQ=F",
        "免費": "是(無鑰匙)",
        "知情時間": "當日收市後可得",
        "用途": "聯邦基金利率預期的免費替代(**FedWatch 本身不免費**,FRED DFF 要鑰匙)",
    },
)

# 每次換倉那一格權重是誰決定的。報告與審計靠這一欄分得出「驅動器真的講過話」
# 與「熱身期照鋪」兩件事。
SOURCE_DRIVER: Final[str] = "驅動器"
SOURCE_WARMUP: Final[str] = "熱身期"
SOURCE_INSUFFICIENT: Final[str] = "數據不足"


class InsufficientHistory(ContractViolation):
    """驅動器要的回望期比手上的歷史還長。

    不是 bug,是事實:回望 12 個月的驅動器在第一年根本算不出訊號。拋這個錯,
    由排期那一層接住並改用**熱身期權重**,而且會逐次記低——不會靜靜地當作
    驅動器真的作過決定。
    """


# ----------------------------------------------------------------------
# 決策日視角:驅動器唯一看得見的東西
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DriverView:
    """一個決策日,驅動器看得見的全部東西。**看不見的就是看不見。**

    ``history`` 的最後一行就是決策日那一日的收價(D-021 第 3 條):它由
    ``closes.loc[:decision_date]`` 切出來,所以「偷看下一日」在這裡連表達都表達
    不出。欄名是**參數名**(``weight_quality`` 一類),不是實體編號亦不是代號——
    驅動器談的是「四格因子敞口」,不需要知道背後掛住哪一個實體。

    ``market`` 是大市那一條收價線(預設 SPY),同樣切到決策日為止;用不着它的
    驅動器(例如逆波幅)不會碰它。

    ``macro`` 是宏觀面板(KARST-040):日期為列、**序列代號**為欄,同樣只切到決策
    日為止。它與 ``history`` 對齊同一條主日曆,所以「決策日」在兩張表裡指同一日。
    宏觀讀數的知情時間是當日收市後可得(D-021 第 3 條),與收價同一級,故最後一行
    用得着。**留空的格就是留空**——那一日沒有讀數,不是零;讀到留空即拋
    ``InsufficientHistory``,由排期那一層退回熱身期權重並記成「數據不足」。
    """

    decision_date: pd.Timestamp
    history: pd.DataFrame
    keys: tuple[str, ...]
    market: pd.Series | None = None
    market_ticker: str | None = None
    macro: pd.DataFrame | None = None

    def __post_init__(self) -> None:
        if self.history.empty:
            raise ContractViolation("決策日視角的價格歷史是空的")
        last = pd.Timestamp(self.history.index[-1])
        if last != pd.Timestamp(self.decision_date):
            raise ContractViolation(
                f"決策日是 {pd.Timestamp(self.decision_date).date()},但價格歷史去到 "
                f"{last.date()};訊號只可以用決策日收工前的數據(D-021 第 3 條)"
            )

    # ---- 給驅動器用的幾條算式。全部只讀 history / market,拿不到之後的日子 ----

    def _cutoff(self, months: int) -> pd.Timestamp:
        return pd.Timestamp(self.decision_date) - pd.DateOffset(months=int(months))

    def _base_row(self, index: pd.Index, months: int) -> int:
        """回望 ``months`` 個月那一日在索引上的位置。**不夠數就拋錯,不縮短回望期。**"""
        position = int(index.searchsorted(self._cutoff(months), side="right")) - 1
        if position < 0:
            raise InsufficientHistory(
                f"回望 {months} 個月要有 "
                f"{self._cutoff(months).date()} 或之前的價格,但歷史由 "
                f"{pd.Timestamp(index[0]).date()} 起才有"
            )
        return position

    def returns_over(self, months: int) -> dict[str, float]:
        """四格各自過去 ``months`` 個月的報酬(決策日收價 ÷ 回望日收價 − 1)。"""
        position = self._base_row(self.history.index, months)
        base = self.history.iloc[position]
        last = self.history.iloc[-1]
        return {key: float(last[key] / base[key] - 1.0) for key in self.keys}

    def market_return_over(self, months: int) -> float:
        """大市過去 ``months`` 個月的報酬。沒有大市那條線就當場拒收,不當零。"""
        series = self.require_market()
        position = self._base_row(series.index, months)
        return float(series.iloc[-1] / series.iloc[position] - 1.0)

    def daily_returns(self, days: int) -> pd.DataFrame:
        """四格最近 ``days`` 根 K 線的每日對數報酬。不夠數即拋錯。"""
        window = int(days)
        if window < 2:
            raise ContractViolation(f"波幅回望期最少要 2 日,收到 {days!r}")
        if len(self.history) < window + 1:
            raise InsufficientHistory(
                f"逆波幅要 {window + 1} 根 K 線才算得出 {window} 日波幅,"
                f"手上只有 {len(self.history)} 根"
            )
        recent = self.history.iloc[-(window + 1) :]
        return pd.DataFrame(np.log(recent.to_numpy(dtype=float)), columns=list(recent.columns)).diff().iloc[1:]

    def market_moving_average(self, days: int) -> float:
        """大市最近 ``days`` 根 K 線的收價均線。"""
        window = int(days)
        if window < 2:
            raise ContractViolation(f"均線日數最少要 2,收到 {days!r}")
        series = self.require_market()
        if len(series) < window:
            raise InsufficientHistory(
                f"{window} 日均線要 {window} 根 K 線,手上只有 {len(series)} 根"
            )
        return float(series.iloc[-window:].mean())

    def market_last(self) -> float:
        return float(self.require_market().iloc[-1])

    def require_market(self) -> pd.Series:
        if self.market is None:
            raise ContractViolation(
                "這個驅動器要看大市那一條線,但今次沒有給大市代號;"
                f"跑的時候寫明 market_ticker(例如 {DEFAULT_MARKET_TICKER!r})"
            )
        return self.market

    # ---- 宏觀序列(KARST-040)。同樣只讀得到決策日或之前的日子 ----

    def require_macro(self, code: str) -> pd.Series:
        """取一條宏觀序列(切到決策日為止)。沒有那條序列就當場拒收,不當零。"""
        name = str(code).strip().upper()
        if self.macro is None:
            raise ContractViolation(
                f"這個驅動器要看宏觀序列「{name}」,但今次沒有給宏觀面板;"
                "跑的時候寫明 macro=(見 karst.data.macro.read_macro_panel)"
            )
        if name not in self.macro.columns:
            raise ContractViolation(
                f"宏觀面板裡沒有序列「{name}」;有的是:"
                f"{'、'.join(str(c) for c in self.macro.columns) or '(一條都沒有)'}"
            )
        return self.macro[name]

    def macro_last(self, code: str) -> float:
        """一條宏觀序列在決策日的讀數。那一格留空即當回望期不夠,不當零。"""
        series = self.require_macro(code)
        if series.empty:
            raise InsufficientHistory(f"宏觀序列 {code} 在決策日之前一個讀數都沒有")
        value = float(series.iloc[-1])
        if not np.isfinite(value):
            raise InsufficientHistory(
                f"宏觀序列 {code} 在 {pd.Timestamp(self.decision_date).date()} 留空"
                "(那一日沒有讀數);留空不當零,這一期不由驅動器話事"
            )
        return value

    def _macro_pair(self, code: str, days: int) -> tuple[float, float]:
        """一條宏觀序列的「``days`` 根 K 線之前」與「決策日」兩個讀數。

        用**位置**回望(不是日曆月份):宏觀序列已對齊主日曆,第 ``days`` 根之前就
        是第 ``days`` 個交易日之前。兩端任何一端留空即拋 ``InsufficientHistory``
        ——半個訊號不是訊號。
        """
        window = int(days)
        if window < 1:
            raise ContractViolation(f"宏觀回望期最少 1 日,收到 {days!r}")
        series = self.require_macro(code)
        if len(series) < window + 1:
            raise InsufficientHistory(
                f"宏觀序列 {code} 回望 {window} 日要 {window + 1} 個讀數,"
                f"手上只有 {len(series)} 個"
            )
        base = float(series.iloc[-(window + 1)])
        last = float(series.iloc[-1])
        if not (np.isfinite(base) and np.isfinite(last)):
            raise InsufficientHistory(
                f"宏觀序列 {code} 回望 {window} 日的兩端有留空"
                f"(起 {base}、訖 {last});留空不當零,這一期不由驅動器話事"
            )
        return base, last

    def macro_change(self, code: str, days: int) -> float:
        """一條宏觀序列過去 ``days`` 個交易日的**絕對變化**(決策日讀數減回望日讀數)。

        息率、斜度一類以百分點計的序列要用這一條:2.1% 升到 2.3% 是升了 0.2 個
        百分點,不是升了 9.5%。
        """
        base, last = self._macro_pair(code, days)
        return last - base

    def macro_return(self, code: str, days: int) -> float:
        """一條宏觀序列過去 ``days`` 個交易日的**相對變化**(比率減一)。

        價格型序列(ETF 收價一類)要用這一條。回望日的讀數是零即拋錯,不當無限大。
        """
        base, last = self._macro_pair(code, days)
        if base == 0.0:
            raise InsufficientHistory(f"宏觀序列 {code} 回望日的讀數是零,算不出相對變化")
        return last / base - 1.0

    def macro_ratio_last(self, numerator: str, denominator: str) -> float:
        """兩條宏觀序列在決策日的比率(例如 VIX ÷ VIX_3M 即期限結構)。"""
        top = self.macro_last(numerator)
        bottom = self.macro_last(denominator)
        if bottom == 0.0:
            raise InsufficientHistory(f"宏觀序列 {denominator} 在決策日是零,算不出比率")
        return top / bottom

    def macro_ratio_change(self, numerator: str, denominator: str, days: int) -> float:
        """兩條序列的比率過去 ``days`` 個交易日的**相對變化**。

        信用利差代理(HY_ETF ÷ IG_ETF)用的正是這一條:比率跌 = 高收益跑輸 =
        利差擴闊。兩條序列的兩端共四個讀數,任何一個留空即當數據不足。
        """
        top_base, top_last = self._macro_pair(numerator, days)
        bottom_base, bottom_last = self._macro_pair(denominator, days)
        if bottom_base == 0.0 or bottom_last == 0.0:
            raise InsufficientHistory(
                f"宏觀序列 {denominator} 在回望窗兩端有零,算不出比率變化"
            )
        base = top_base / bottom_base
        last = top_last / bottom_last
        if base == 0.0:
            raise InsufficientHistory(f"{numerator}÷{denominator} 在回望日是零,算不出變化")
        return last / base - 1.0


# ----------------------------------------------------------------------
# 驅動器:同一個接口,四個實作
# ----------------------------------------------------------------------


@runtime_checkable
class RotationDriver(Protocol):
    """驅動器(rotation driver):收一個決策日視角,回四格權重。

    這就是整份可換件合約。實作得到它的東西就插得進來——本檔、引擎、掃描層
    一個字都不用改。回出來的權重:每格非負、加總不可多於一(少於一即餘下持
    現金;全零即這一期全部持現金)。
    """

    key: str
    name: str
    needs_market: bool
    needs_macro: tuple[str, ...]
    """要看的宏觀序列代號(KARST-040)。空的即這個驅動器只看價格。

    跑的時候由 ``_prepare_macro`` 逐條核對:宏觀面板裡缺任何一條即**當場
    拒收**,不會靜靜地跑出一條「訊號從來沒有講過話」的淨值線。
    """

    def weights(self, view: DriverView) -> Mapping[str, float]: ...

    def describe(self) -> str: ...


def normalise_weights(raw: Mapping[str, Any], keys: Sequence[str]) -> dict[str, float]:
    """核對驅動器交回來的一組權重。**這是驅動器與引擎之間的驗關口。**

    四格要齊、不可有負數、加總不可多於一。加總可以是零——那是「這一期全部持
    現金」,一個講得通的決定,不當它出錯。
    """
    names = tuple(keys)
    table = dict(raw or {})
    missing = [key for key in names if key not in table]
    if missing:
        raise ContractViolation(
            f"驅動器沒有交代這幾格的權重:{'、'.join(missing)};四格要齊,不猜、不當零"
        )
    extra = [key for key in table if key not in names]
    if extra:
        raise ContractViolation(f"驅動器交回來的權重有不認得的格:{'、'.join(map(str, extra))}")

    cleaned: dict[str, float] = {}
    for key in names:
        try:
            value = float(table[key])
        except (TypeError, ValueError) as exc:
            raise ContractViolation(f"權重「{key}」不是數字:{table[key]!r}") from exc
        if not np.isfinite(value):
            raise ContractViolation(f"權重「{key}」不是有限數:{table[key]!r}")
        if value < 0.0:
            raise ContractViolation(f"權重「{key}」是負數 {value};v1 因子輪動不做淡倉")
        cleaned[key] = value

    total = sum(cleaned.values())
    if total > 1.0 + _SUM_TOLERANCE:
        raise ContractViolation(
            f"驅動器交回來的權重加總 {total};v1 不做槓桿,加總不可多於一"
            "(少於一即餘下持現金)"
        )
    return cleaned


def _even(keys: Sequence[str], chosen: Sequence[str]) -> dict[str, float]:
    """揀中的那幾格均分一注,其餘零。"""
    picked = list(chosen)
    if not picked:
        return {key: 0.0 for key in keys}
    share = 1.0 / len(picked)
    return {key: (share if key in picked else 0.0) for key in keys}


def _ranked(values: Mapping[str, float]) -> list[str]:
    """由高到低排名。**打和時取參數名排最前那一格**——同一份數據重跑要指向同一格。"""
    return sorted(values, key=lambda key: (-float(values[key]), key))


def _tilt_towards(
    keys: Sequence[str], targets: Sequence[str], tilt: float
) -> dict[str, float]:
    """把 ``tilt`` 那一注平均押在 ``targets`` 幾格,其餘平均分給剩下那幾格。

    開關型驅動器(趨勢開關與五個宏觀驅動器)共用這一條。``tilt=1.0`` 即整注押在
    那幾格、其餘清零;``tilt=0.5`` 即一半押那幾格、一半平均分給其餘。要押的格不在
    四格敞口裡就當場拒收——**不靜靜地把注落在別處**。
    """
    names = tuple(keys)
    picked = [key for key in dict.fromkeys(targets)]
    missing = [key for key in picked if key not in names]
    if missing:
        raise ContractViolation(
            f"這個驅動器要押「{'、'.join(missing)}」那幾格,但四格敞口裡沒有它們:"
            f"{'、'.join(names)}"
        )
    if not picked:  # pragma: no cover - 每個驅動器都指名道姓押哪幾格
        raise ContractViolation("開關型驅動器要指名押哪一格,不可以一格都不押")
    share = float(tilt) / len(picked)
    rest = [key for key in names if key not in picked]
    spare = (1.0 - float(tilt)) / len(rest) if rest else 0.0
    return {key: (share if key in picked else spare) for key in names}


# 純量驗證的正本住在參數規格(``karst.executor.contract``,KARST-090):
# 押注比重是「大於 0、上限 1 含」,回望期是「整數、下限 1 含」——兩種值域本檔
# 不再自己算一次。
def _check_tilt(value: Any) -> float:
    return check_ratio(value, "押注比重")


def _check_lookback_days(value: Any, label: str = "回望期") -> int:
    return check_count(value, label)


# 「避險」那一邊押哪幾格:低波與質素。五個宏觀驅動器之中有四個用這一組——
# 這是**結構性選擇不是可掃描參數**(與趨勢開關同一個道理):恐慌高、利差擴闊、
# 預期加息時押防守型因子,正是這幾個驅動器的定義本身。要押別的組合,砌另一個
# 驅動器,不要把它調成參數。
RISK_OFF_KEYS: Final[tuple[str, ...]] = (LOW_VOL_KEY, QUALITY_KEY)
# 「進攻」那一邊:動能。
RISK_ON_KEYS: Final[tuple[str, ...]] = (MOMENTUM_KEY,)


@dataclass(frozen=True, slots=True)
class FactorMomentumDriver:
    """(a)**因子動量排名**:過去 L 個月報酬排名,全押第一或者按名次遞減。

    ``mode``:``winner`` 即整注押排第一那格;``rank`` 即按名次遞減分注——四格就是
    4 : 3 : 2 : 1(佔 40% / 30% / 20% / 10%)。兩種都是「跟住贏家走」,分別只在
    集中程度,所以同一個軸上掃。
    """

    lookback_months: int
    mode: str
    key: str = field(default="factor_momentum", init=False)
    name: str = field(default="因子動量排名", init=False)
    needs_market: bool = field(default=False, init=False)
    needs_macro: tuple[str, ...] = field(default=(), init=False)

    MODES: ClassVar[tuple[str, ...]] = ("winner", "rank")

    def __post_init__(self) -> None:
        months = int(self.lookback_months)
        if months < 1:
            raise ContractViolation(f"回望期最少一個月,收到 {self.lookback_months!r}")
        mode = str(self.mode).strip()
        if mode not in self.MODES:
            raise ContractViolation(f"排名用法只收 {list(self.MODES)},收到 {self.mode!r}")
        object.__setattr__(self, "lookback_months", months)
        object.__setattr__(self, "mode", mode)

    def weights(self, view: DriverView) -> Mapping[str, float]:
        order = _ranked(view.returns_over(self.lookback_months))
        if self.mode == "winner":
            return _even(view.keys, order[:1])
        count = len(order)
        total = count * (count + 1) / 2.0
        return {key: (count - place) / total for place, key in enumerate(order)}

    def describe(self) -> str:
        how = "整注押排第一那格" if self.mode == "winner" else "按名次遞減分注(4:3:2:1)"
        return f"{self.name}:比過去 {self.lookback_months} 個月的報酬,{how}"


@dataclass(frozen=True, slots=True)
class RelativeStrengthDriver:
    """(b)**相對強弱對大市**:跑贏大市的因子均分,全輸就按參數處置。

    ``fallback``:``cash`` 即四格全零(這一期全部持現金);``equal`` 即四格等權。
    兩者是同一個問題的兩個答案——「無人跑贏就唔好玩」對「無人跑贏就照均分」,
    所以做成參數,不代用戶決定。
    """

    lookback_months: int
    fallback: str
    key: str = field(default="relative_strength", init=False)
    name: str = field(default="相對強弱對大市", init=False)
    needs_market: bool = field(default=True, init=False)
    needs_macro: tuple[str, ...] = field(default=(), init=False)

    FALLBACKS: ClassVar[tuple[str, ...]] = ("cash", "equal")

    def __post_init__(self) -> None:
        months = int(self.lookback_months)
        if months < 1:
            raise ContractViolation(f"回望期最少一個月,收到 {self.lookback_months!r}")
        fallback = str(self.fallback).strip()
        if fallback not in self.FALLBACKS:
            raise ContractViolation(
                f"全輸時的處置只收 {list(self.FALLBACKS)},收到 {self.fallback!r}"
            )
        object.__setattr__(self, "lookback_months", months)
        object.__setattr__(self, "fallback", fallback)

    def weights(self, view: DriverView) -> Mapping[str, float]:
        returns = view.returns_over(self.lookback_months)
        market = view.market_return_over(self.lookback_months)
        winners = [key for key in view.keys if returns[key] > market]
        if winners:
            return _even(view.keys, winners)
        if self.fallback == "cash":
            return {key: 0.0 for key in view.keys}
        return _even(view.keys, list(view.keys))

    def describe(self) -> str:
        tail = "四格全部持現金" if self.fallback == "cash" else "四格等權"
        return (
            f"{self.name}:比過去 {self.lookback_months} 個月的報酬,"
            f"跑贏大市的因子均分;全部跑輸就{tail}"
        )


@dataclass(frozen=True, slots=True)
class InverseVolatilityDriver:
    """(c)**逆波幅**:過去 L 日波幅的倒數加權,波幅越細分得越多。

    ``power`` 是集中程度:1 即倒數、2 即倒數平方(把注更集中在最穩那一格)。
    四格波幅全部是零(例如四條價格線一動不動的合成數據)就退回等權——那不是
    「零風險」,是「這段數據分不出高下」。
    """

    lookback_days: int
    power: float
    key: str = field(default="inverse_volatility", init=False)
    name: str = field(default="逆波幅", init=False)
    needs_market: bool = field(default=False, init=False)
    needs_macro: tuple[str, ...] = field(default=(), init=False)

    def __post_init__(self) -> None:
        days = int(self.lookback_days)
        if days < 2:
            raise ContractViolation(f"波幅回望期最少 2 日,收到 {self.lookback_days!r}")
        power = float(self.power)
        if not np.isfinite(power) or power <= 0.0:
            raise ContractViolation(f"集中程度要是正數,收到 {self.power!r}")
        object.__setattr__(self, "lookback_days", days)
        object.__setattr__(self, "power", power)

    def weights(self, view: DriverView) -> Mapping[str, float]:
        moves = view.daily_returns(self.lookback_days)
        deviation = {key: float(moves[key].std(ddof=1)) for key in view.keys}
        scores = {
            key: (0.0 if value <= 0.0 else float(value ** (-self.power)))
            for key, value in deviation.items()
        }
        total = sum(scores.values())
        if total <= 0.0:
            return _even(view.keys, list(view.keys))
        return {key: value / total for key, value in scores.items()}

    def describe(self) -> str:
        return (
            f"{self.name}:按過去 {self.lookback_days} 日的每日波幅,"
            f"以波幅的 {self.power:g} 次方倒數分注(越穩分得越多)"
        )


@dataclass(frozen=True, slots=True)
class TrendSwitchDriver:
    """(d)**大市趨勢開關**:大市高於 M 日均線押動能,低於則押低波。

    ``tilt`` 是押幾重:1.0 即整注押那一格,0.5 即一半押那一格、另一半平均分給
    其餘三格。押邊兩格(``risk_on_key`` / ``risk_off_key``)是**結構性選擇**不是
    可掃描參數——「升市押動能、跌市押低波」正是這個驅動器的定義;要押別的組合,
    砌另一個驅動器,不要調這兩格。
    """

    ma_days: int
    tilt: float
    risk_on_key: str = MOMENTUM_KEY
    risk_off_key: str = LOW_VOL_KEY
    key: str = field(default="trend_switch", init=False)
    name: str = field(default="大市趨勢開關", init=False)
    needs_market: bool = field(default=True, init=False)
    needs_macro: tuple[str, ...] = field(default=(), init=False)

    def __post_init__(self) -> None:
        days = int(self.ma_days)
        if days < 2:
            raise ContractViolation(f"均線日數最少 2,收到 {self.ma_days!r}")
        tilt = float(self.tilt)
        if not (0.0 < tilt <= 1.0):
            raise ContractViolation(f"押注比重要在 0 與 1 之間,收到 {self.tilt!r}")
        object.__setattr__(self, "ma_days", days)
        object.__setattr__(self, "tilt", tilt)

    def weights(self, view: DriverView) -> Mapping[str, float]:
        risk_on = view.market_last() > view.market_moving_average(self.ma_days)
        target = self.risk_on_key if risk_on else self.risk_off_key
        if target not in view.keys:
            raise ContractViolation(
                f"這個驅動器要押「{target}」那一格,但四格敞口裡沒有它:"
                f"{'、'.join(view.keys)}"
            )
        rest = [key for key in view.keys if key != target]
        spare = (1.0 - self.tilt) / len(rest) if rest else 0.0
        return {key: (self.tilt if key == target else spare) for key in view.keys}

    def describe(self) -> str:
        return (
            f"{self.name}:大市收價高於 {self.ma_days} 日均線就押 {self.risk_on_key}、"
            f"低於就押 {self.risk_off_key},押注比重 {self.tilt:.0%},"
            "其餘平均分給另外三格"
        )


# ----------------------------------------------------------------------
# 宏觀驅動器(KARST-040):訊號來自價格以外
# ----------------------------------------------------------------------
#
# 五個宏觀驅動器共通的三件事:
#
#   · **門檻與回望期一律是掃描參數,無預設值**(D-008 第 3 條)。本檔查不到任何
#     一個「常用取值」——VIX 高於 20 算不算恐慌、利差回望 20 日還是 60 日,
#     一律由掃描寫明,由平原判讀答。
#   · **押哪幾格是結構性選擇**(見 ``RISK_OFF_KEYS``),不是可掃描參數。
#   · 讀不到宏觀讀數(留空、回望期不夠)即拋 ``InsufficientHistory``,由排期那一層
#     退回熱身期權重並記成「數據不足」——**不當零、不猜、不靜靜地當訊號講過話**。


@dataclass(frozen=True, slots=True)
class VixLevelDriver:
    """(e)**VIX 水平開關**:VIX 高於門檻即高恐慌,押低波與質素;否則押動能。

    ``threshold`` 的單位是 VIX 點數(年化波動率),``tilt`` 是押幾重。恐慌高低與
    因子表現的關係是這個驅動器的假設本身:市場怕的時候低波與質素跑贏、不怕的時候
    動能跑贏。它是不是真的,由掃描與分段超額答,不由本檔斷言。
    """

    threshold: float
    tilt: float
    key: str = field(default="vix_level", init=False)
    name: str = field(default="VIX 水平開關", init=False)
    needs_market: bool = field(default=False, init=False)
    needs_macro: tuple[str, ...] = field(default=("VIX",), init=False)

    def __post_init__(self) -> None:
        threshold = float(self.threshold)
        if not np.isfinite(threshold) or threshold <= 0.0:
            raise ContractViolation(f"VIX 門檻要是正數,收到 {self.threshold!r}")
        object.__setattr__(self, "threshold", threshold)
        object.__setattr__(self, "tilt", _check_tilt(self.tilt))

    def weights(self, view: DriverView) -> Mapping[str, float]:
        fearful = view.macro_last("VIX") > self.threshold
        targets = RISK_OFF_KEYS if fearful else RISK_ON_KEYS
        return _tilt_towards(view.keys, targets, self.tilt)

    def describe(self) -> str:
        return (
            f"{self.name}:VIX 收市高於 {self.threshold:g} 就押低波與質素、"
            f"低於就押動能,押注比重 {self.tilt:.0%},其餘平均分給另外幾格"
        )


@dataclass(frozen=True, slots=True)
class VixTermDriver:
    """(f)**VIX 期限結構開關**:VIX ÷ VIX_3M 高於門檻即倒掛,押低波與質素。

    期限結構講的是「即市恐慌對遠期恐慌」:比率大於 1 即近月高於遠月(倒掛),
    通常出現在急跌之中;小於 1 是常態。它與水平開關是兩件事——VIX 可以在高水平
    但不倒掛(持續緊張),亦可以在低水平突然倒掛(急插開始),所以分開兩個驅動器
    各自掃,不合併成一個「門檻」軸(兩者的門檻連單位都不同,排不進同一條軸)。
    """

    threshold: float
    tilt: float
    key: str = field(default="vix_term", init=False)
    name: str = field(default="VIX 期限結構開關", init=False)
    needs_market: bool = field(default=False, init=False)
    needs_macro: tuple[str, ...] = field(default=("VIX", "VIX_3M"), init=False)

    def __post_init__(self) -> None:
        threshold = float(self.threshold)
        if not np.isfinite(threshold) or threshold <= 0.0:
            raise ContractViolation(f"期限結構門檻要是正數,收到 {self.threshold!r}")
        object.__setattr__(self, "threshold", threshold)
        object.__setattr__(self, "tilt", _check_tilt(self.tilt))

    def weights(self, view: DriverView) -> Mapping[str, float]:
        inverted = view.macro_ratio_last("VIX", "VIX_3M") > self.threshold
        targets = RISK_OFF_KEYS if inverted else RISK_ON_KEYS
        return _tilt_towards(view.keys, targets, self.tilt)

    def describe(self) -> str:
        return (
            f"{self.name}:VIX ÷ VIX_3M 高於 {self.threshold:g}(近月高於遠月)"
            f"就押低波與質素、低於就押動能,押注比重 {self.tilt:.0%}"
        )


@dataclass(frozen=True, slots=True)
class CreditTrendDriver:
    """(g)**信用利差變化方向**:利差擴闊押低波與質素,收窄押動能。

    利差本身用免費替代:``HY_ETF ÷ IG_ETF`` 的價格比率(FRED 的高收益 OAS 要 API
    鑰匙,見 ``EXTERNAL_DATA``)。比率**跌**即高收益跑輸投資級,亦即利差擴闊;
    比率升即利差收窄。所以判的是比率過去 ``lookback_days`` 個交易日的相對變化的
    **方向**,不是它的水平——水平那一半含存續期與流動性差異,讀不準。
    """

    lookback_days: int
    tilt: float
    key: str = field(default="credit_trend", init=False)
    name: str = field(default="信用利差變化方向", init=False)
    needs_market: bool = field(default=False, init=False)
    needs_macro: tuple[str, ...] = field(default=("HY_ETF", "IG_ETF"), init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "lookback_days", _check_lookback_days(self.lookback_days, "信用利差回望期")
        )
        object.__setattr__(self, "tilt", _check_tilt(self.tilt))

    def weights(self, view: DriverView) -> Mapping[str, float]:
        change = view.macro_ratio_change("HY_ETF", "IG_ETF", self.lookback_days)
        widening = change < 0.0
        targets = RISK_OFF_KEYS if widening else RISK_ON_KEYS
        return _tilt_towards(view.keys, targets, self.tilt)

    def describe(self) -> str:
        return (
            f"{self.name}:HY_ETF÷IG_ETF 比率過去 {self.lookback_days} 個交易日下跌"
            f"(利差擴闊)就押低波與質素、上升就押動能,押注比重 {self.tilt:.0%}"
        )


@dataclass(frozen=True, slots=True)
class CurveTrendDriver:
    """(h)**曲線斜度變化方向**:陡峭化押價值,平坦化押低波。

    斜度 = ``UST_10Y − UST_3M``(長端減短端,單位是百分點)。2 年期要 FRED 鑰匙,
    故短端用 13 週國庫券替代(用戶 2026-08-28 裁定),代價明記於
    ``karst.data.macro`` 的序列名冊:斜度的**絕對水平**因此與市場慣講的「10 年減
    2 年」不同,所以本驅動器只讀**變化方向**,不讀水平、不設「倒掛與否」的門檻。

    陡峭化(斜度升)通常伴隨增長與通脹預期回升,價值股受惠;平坦化押低波。
    """

    lookback_days: int
    tilt: float
    key: str = field(default="curve_trend", init=False)
    name: str = field(default="曲線斜度變化方向", init=False)
    needs_market: bool = field(default=False, init=False)
    needs_macro: tuple[str, ...] = field(default=("UST_10Y", "UST_3M"), init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "lookback_days", _check_lookback_days(self.lookback_days, "曲線斜度回望期")
        )
        object.__setattr__(self, "tilt", _check_tilt(self.tilt))

    def weights(self, view: DriverView) -> Mapping[str, float]:
        # 斜度的變化 = 長端變化 − 短端變化(兩者同一個回望窗,單位皆百分點)
        steepening = (
            view.macro_change("UST_10Y", self.lookback_days)
            - view.macro_change("UST_3M", self.lookback_days)
        ) > 0.0
        targets = (VALUE_KEY,) if steepening else (LOW_VOL_KEY,)
        return _tilt_towards(view.keys, targets, self.tilt)

    def describe(self) -> str:
        return (
            f"{self.name}:UST_10Y 減 UST_3M 的斜度過去 {self.lookback_days} 個交易日"
            f"上升(陡峭化)就押價值、下降就押低波,押注比重 {self.tilt:.0%}"
        )


@dataclass(frozen=True, slots=True)
class RateTrendDriver:
    """(i)**10 年息率趨勢**:息率升押價值,息率跌押低波。

    與曲線斜度那個分開,因為兩者可以各講各話:長短端同步上移時斜度不變而息率
    大升。用戶裁定的第一層第(3)項寫的正是「美債息率**與**曲線斜度」兩件,
    所以兩件各自一個驅動器,各自掃自己的回望期。
    """

    lookback_days: int
    tilt: float
    key: str = field(default="rate_trend", init=False)
    name: str = field(default="10 年息率趨勢", init=False)
    needs_market: bool = field(default=False, init=False)
    needs_macro: tuple[str, ...] = field(default=("UST_10Y",), init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "lookback_days", _check_lookback_days(self.lookback_days, "息率回望期")
        )
        object.__setattr__(self, "tilt", _check_tilt(self.tilt))

    def weights(self, view: DriverView) -> Mapping[str, float]:
        rising = view.macro_change("UST_10Y", self.lookback_days) > 0.0
        targets = (VALUE_KEY,) if rising else (LOW_VOL_KEY,)
        return _tilt_towards(view.keys, targets, self.tilt)

    def describe(self) -> str:
        return (
            f"{self.name}:UST_10Y 過去 {self.lookback_days} 個交易日上升就押價值、"
            f"下跌就押低波,押注比重 {self.tilt:.0%}"
        )


@dataclass(frozen=True, slots=True)
class FedExpectationDriver:
    """(j)**聯邦基金利率預期方向**:預期加息押低波與質素,預期減息押動能。

    **FedWatch 本身不免費**,FRED 的有效聯邦基金利率 DFF 亦要 API 鑰匙,故用免費
    替代:聯邦基金期貨(``ZQ=F``)。隱含利率 = 100 − 報價,所以**報價升 = 隱含
    利率跌 = 預期減息**;本驅動器判的是**隱含利率**的變化方向,即報價變化取負號。

    近月連續合約在轉倉時會跳一格,所以同樣只讀方向不讀水平(見序列名冊的註記)。
    """

    lookback_days: int
    tilt: float
    key: str = field(default="fed_expectation", init=False)
    name: str = field(default="聯邦基金利率預期方向", init=False)
    needs_market: bool = field(default=False, init=False)
    needs_macro: tuple[str, ...] = field(default=("FF_FUTURE",), init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "lookback_days", _check_lookback_days(self.lookback_days, "利率預期回望期")
        )
        object.__setattr__(self, "tilt", _check_tilt(self.tilt))

    def weights(self, view: DriverView) -> Mapping[str, float]:
        # 隱含利率 = 100 − 報價,故隱含利率的變化 = 報價變化的相反數
        implied_change = -view.macro_change("FF_FUTURE", self.lookback_days)
        tightening = implied_change > 0.0
        targets = RISK_OFF_KEYS if tightening else RISK_ON_KEYS
        return _tilt_towards(view.keys, targets, self.tilt)

    def describe(self) -> str:
        return (
            f"{self.name}:聯邦基金期貨隱含利率(100 − 報價)過去 "
            f"{self.lookback_days} 個交易日上升(預期加息)就押低波與質素、"
            f"下跌(預期減息)就押動能,押注比重 {self.tilt:.0%}"
        )


# 驅動器名冊。**加一個驅動器只需在這裡加一行**,掃描層與引擎一個字不用改。
DRIVER_BUILDERS: Final[Mapping[str, Callable[..., RotationDriver]]] = {
    # 價格驅動器(KARST-036):訊號全部由四隻因子 ETF 與大市自身的收價算出來
    "factor_momentum": FactorMomentumDriver,
    "relative_strength": RelativeStrengthDriver,
    "inverse_volatility": InverseVolatilityDriver,
    "trend_switch": TrendSwitchDriver,
    # 宏觀驅動器(KARST-040):訊號來自宏觀快照,全部免費序列
    "vix_level": VixLevelDriver,
    "vix_term": VixTermDriver,
    "credit_trend": CreditTrendDriver,
    "curve_trend": CurveTrendDriver,
    "rate_trend": RateTrendDriver,
    "fed_expectation": FedExpectationDriver,
}

# 哪幾個是宏觀驅動器。報告與掃描腳本靠這一張分得出「價格那批」與「宏觀那批」。
MACRO_DRIVER_KEYS: Final[tuple[str, ...]] = (
    "vix_level",
    "vix_term",
    "credit_trend",
    "curve_trend",
    "rate_trend",
    "fed_expectation",
)

PRICE_DRIVER_KEYS: Final[tuple[str, ...]] = (
    "factor_momentum",
    "relative_strength",
    "inverse_volatility",
    "trend_switch",
)

# 每個驅動器的可掃描參數名(次序即掃描格上軸的次序),以及哪幾個是無序軸。
# **這裡只講「有哪幾個參數」,不講「掃哪幾個取值」**——取值無預設,由呼叫方寫明。
DRIVER_PARAMETERS: Final[Mapping[str, tuple[str, ...]]] = {
    "factor_momentum": ("lookback_months", "mode"),
    "relative_strength": ("lookback_months", "fallback"),
    "inverse_volatility": ("lookback_days", "power"),
    "trend_switch": ("ma_days", "tilt"),
    # 宏觀驅動器:一條「門檻或回望期」軸 × 一條「押幾重」軸。兩條都有序,
    # 所以 3×3 鄰域講得通,平原判讀有意思。
    "vix_level": ("threshold", "tilt"),
    "vix_term": ("threshold", "tilt"),
    "credit_trend": ("lookback_days", "tilt"),
    "curve_trend": ("lookback_days", "tilt"),
    "rate_trend": ("lookback_days", "tilt"),
    "fed_expectation": ("lookback_days", "tilt"),
}

# 無序軸:取值之間沒有「移一步」可言(``winner`` 與 ``rank`` 不是一步之遙),
# 所以同軸任何兩個取值皆算相鄰(見 ``karst.sweep.grid.SweepAxis``)。
DRIVER_UNORDERED_PARAMETERS: Final[Mapping[str, tuple[str, ...]]] = {
    "factor_momentum": ("mode",),
    "relative_strength": ("fallback",),
    "inverse_volatility": (),
    "trend_switch": (),
    # 宏觀驅動器兩條軸皆有序:門檻由低到高、回望期由短到長、押注比重由輕到重,
    # 「移一步」在三者都講得通。
    "vix_level": (),
    "vix_term": (),
    "credit_trend": (),
    "curve_trend": (),
    "rate_trend": (),
    "fed_expectation": (),
}


def macro_series_needed(driver: RotationDriver | str) -> tuple[str, ...]:
    """一個驅動器要看哪幾條宏觀序列。收驅動器本身或者它的名。

    掃描腳本靠這一條算出「這次掃描要由宏觀快照讀哪幾條序列」,不必逐個驅動器
    手抄一張表——手抄的表遲早會與驅動器本身講的不一致。
    """
    if isinstance(driver, str):
        name = driver.strip()
        builder = DRIVER_BUILDERS.get(name)
        if builder is None:
            raise ContractViolation(
                f"沒有「{name}」這個驅動器;有的是:{'、'.join(sorted(DRIVER_BUILDERS))}"
            )
        return tuple(getattr(builder, "__dataclass_fields__", {})["needs_macro"].default)
    return tuple(getattr(driver, "needs_macro", ()))


def build_driver(key: str, **params: Any) -> RotationDriver:
    """按名冊砌一個驅動器。名不在冊即當場拒收,不猜。"""
    name = str(key or "").strip()
    builder = DRIVER_BUILDERS.get(name)
    if builder is None:
        raise ContractViolation(
            f"沒有「{name}」這個驅動器;有的是:{'、'.join(sorted(DRIVER_BUILDERS))}"
        )
    expected = set(DRIVER_PARAMETERS[name])
    given = set(params)
    missing = sorted(expected - given)
    if missing:
        raise ContractViolation(
            f"驅動器「{name}」缺參數:{'、'.join(missing)};參數無預設值,要用的一律寫明"
        )
    unknown = sorted(given - expected)
    if unknown:
        raise ContractViolation(f"驅動器「{name}」不認得這幾個參數:{'、'.join(unknown)}")
    return builder(**params)


# ----------------------------------------------------------------------
# 參數、敞口、換倉紀錄、結果
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FactorRotationParams:
    """跑一次因子輪動回測的全部參數(驅動器自己的參數不在這裡,在驅動器裡)。

    三個欄位刻意沒有預設值:

    - ``cadence`` 換倉節奏——D-009 第 7 條,引擎與策略皆不設預設。
    - ``warmup_bars`` **熱身期**——頭幾根 K 線不讓驅動器話事。回望 12 個月的驅動器
      在第一年算不出訊號,而各個驅動器要的熱身長短不同;把它做成一個**寫明的、
      整次掃描共用的**數,整個掃描格的每一格就走同一段日子,L 這條軸才乾淨。
    - ``warmup_weights`` 熱身期那段日子用的權重——同樣要寫明。掃描一律寫四格等權,
      即熱身期與「各佔 25%」那個對照一模一樣,分別由熱身期結束那一刻才開始出現。

    ``costs`` 是交易成本合約(手續費型別 + 費率 + 滑點,見 ``engine.TradingCosts``),
    照原樣交落引擎——**輪動這條路換手是固定權重的一百倍,成本正是它要過的那一關**
    (KARST-036 收檔留下的問題)。留空即沿用 ``fees``(按成交金額比例、無滑點)。
    """

    cadence: str
    warmup_bars: int
    warmup_weights: Mapping[str, float]
    initial_cash: float = 100_000.0
    fees: float = 0.0
    costs: TradingCosts | None = None

    def __post_init__(self) -> None:
        if self.cadence is None or not str(self.cadence).strip():
            raise CadenceNotSpecified(
                "缺換倉節奏(rebalance cadence):"
                f"{sorted(CADENCES)} 揀一個。因子輪動策略不設預設節奏(D-009 第 7 條)"
            )
        cadence = str(self.cadence).strip()
        if cadence not in CADENCES:
            raise ContractViolation(f"換倉節奏只收 {sorted(CADENCES)},收到 {self.cadence!r}")

        try:
            warmup = int(self.warmup_bars)
        except (TypeError, ValueError) as exc:
            raise ContractViolation(f"熱身期要是整數根 K 線,收到 {self.warmup_bars!r}") from exc
        if warmup < 0:
            raise ContractViolation(f"熱身期不可為負,收到 {self.warmup_bars!r}")

        weights = dict(self.warmup_weights or {})
        if not weights:
            raise ContractViolation(
                "缺熱身期權重:熱身那段日子四格各佔多少要寫明,無預設值(D-008 第 3 條)"
            )
        cleaned = normalise_weights(weights, tuple(weights))
        if sum(cleaned.values()) <= 0.0:
            raise ContractViolation("熱身期權重全部是零;要全期持現金請把熱身期設為 0")

        initial_cash = float(self.initial_cash)
        if not np.isfinite(initial_cash) or initial_cash <= 0.0:
            raise ContractViolation(f"起始本金要是正數,收到 {self.initial_cash!r}")
        fees = float(self.fees)
        if not np.isfinite(fees) or fees < 0.0:
            raise ContractViolation(f"手續費率不可為負,收到 {self.fees!r}")
        costs = resolve_costs(self.costs, fees, "因子輪動參數的交易成本")

        object.__setattr__(self, "cadence", cadence)
        object.__setattr__(self, "warmup_bars", warmup)
        object.__setattr__(self, "warmup_weights", cleaned)
        object.__setattr__(self, "initial_cash", initial_cash)
        object.__setattr__(self, "fees", fees)
        object.__setattr__(self, "costs", costs)


@dataclass(frozen=True, slots=True)
class RotationExposure:
    """一格因子敞口解析之後的樣子。**沒有權重那一欄**——輪動的權重不是常數。

    這正是它與 ``factor_mix.FactorExposure`` 的分別:那邊一格一個寫死的權重,
    這邊的權重逐次換倉由驅動器算。其餘(代號按日解析成實體編號、蓋住因子的
    哪一版)兩邊一模一樣,走的是 ``store.resolve_ticker`` 同一條路(D-026 第 2 條)。
    """

    sleeve: FactorSleeve
    entity_id: int
    entity_kind: str
    factor_version_id: int
    factor_version_no: int

    @property
    def factor_name(self) -> str:
        return self.sleeve.factor_name

    @property
    def weight_key(self) -> str:
        return self.sleeve.weight_key


@dataclass(frozen=True, slots=True)
class RotationRebalance:
    """一次換倉的帳:決策日驅動器見到什麼、決定了什麼、下一根 K 線怎樣執行。

    ``source`` 講明這一格權重是誰決定的:驅動器、熱身期,還是「數據不足」退回
    熱身期權重。三者分得清,報告才講得出驅動器真正話事的次數。
    """

    decision_date: str
    execution_date: str
    source: str
    weights: tuple[tuple[str, float], ...]
    entity_weights: tuple[tuple[int, float], ...]

    @property
    def cash_weight(self) -> float:
        return float(max(0.0, 1.0 - sum(weight for _, weight in self.weights)))

    def as_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "decision_date": self.decision_date,
            "execution_date": self.execution_date,
            "source": self.source,
        }
        row.update({key: value for key, value in self.weights})
        row["cash"] = self.cash_weight
        return row


@dataclass(frozen=True, slots=True)
class FactorRotationResult:
    """一次因子輪動回測的結果,連同追溯得回去的來歷。

    形狀與 ``karst.runs.RunStore.record_simulation`` 收的一模一樣(逐日淨值、
    逐日持倉、逐筆交易),所以落痕一句就接得通,與因子混合走同一條路。
    """

    equity_curve: pd.Series
    holdings: pd.DataFrame
    orders: tuple[Order, ...]
    rebalances: tuple[RotationRebalance, ...]
    params: FactorRotationParams
    exposures: tuple[RotationExposure, ...]
    driver_key: str
    driver_name: str
    driver_description: str
    engine_name: str
    macro_series: tuple[str, ...] = ()
    """這次成績用過哪幾條宏觀序列(KARST-040)。價格驅動器一律是空的。

    報告靠這一欄講得出「這條淨值線用過外部數據」,亦是 ``EXTERNAL_DATA`` 那張
    清單在單次運行上的落點。
    """

    @property
    def total_return(self) -> float:
        return float(self.equity_curve.iloc[-1] / self.equity_curve.iloc[0] - 1.0)

    @property
    def factor_version_ids(self) -> tuple[int, ...]:
        """這次成績蓋住的四個因子版本(追溯深度,D-021 第 8 條)。"""
        return tuple(exposure.factor_version_id for exposure in self.exposures)

    @property
    def driver_rebalances(self) -> int:
        """驅動器真正話事的換倉次數(其餘是熱身期或數據不足)。"""
        return sum(1 for r in self.rebalances if r.source == SOURCE_DRIVER)

    def weights_frame(self) -> pd.DataFrame:
        """逐次換倉那四格權重走過的路。人眼審計靠這一張。"""
        return pd.DataFrame([rebalance.as_row() for rebalance in self.rebalances])

    def orders_frame(self) -> pd.DataFrame:
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


# ----------------------------------------------------------------------
# 解析與目標比重表
# ----------------------------------------------------------------------


def resolve_rotation_exposures(
    store: DefinitionStore,
    sleeves: Sequence[FactorSleeve],
    *,
    on_date: date | datetime | str,
) -> tuple[RotationExposure, ...]:
    """把四格敞口解析成「實體編號 × 因子版本」。權重不在這一步——它逐次換倉才算。

    代號一律經 ``store.resolve_ticker`` **按那一日**解析(D-026 第 2 條),與股票、
    與因子混合走的是同一條路、同一張映射表。
    """
    if not sleeves:
        raise ContractViolation("因子輪動最少要有兩格敞口才有東西可以互相調配")

    exposures: list[RotationExposure] = []
    seen: set[int] = set()
    for sleeve in sleeves:
        entity_id = int(store.resolve_ticker(sleeve.ticker, on_date))
        if entity_id in seen:
            raise ContractViolation(
                f"{on_date} 的代號 {sleeve.ticker} 解析到實體 {entity_id},"
                "但這個實體已經佔了另一格敞口;同一個可投資對象不可佔兩格"
            )
        seen.add(entity_id)
        entity = store.get_entity(entity_id)
        version = store.get_factor_version(sleeve.factor_name)
        exposures.append(
            RotationExposure(
                sleeve=sleeve,
                entity_id=entity_id,
                entity_kind=entity.entity_kind,
                factor_version_id=version.factor_version_id,
                factor_version_no=version.version_no,
            )
        )
    return tuple(exposures)


def rotation_targets(
    *,
    panel: PricePanel,
    exposures: Sequence[RotationExposure],
    driver: RotationDriver,
    params: FactorRotationParams,
    market: pd.Series | None = None,
    market_ticker: str | None = None,
    macro: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, tuple[RotationRebalance, ...]]:
    """目標比重表:換倉的**執行日**那一行寫比重,其餘一律 ``NaN``。

    與因子混合**同一條路**——同一個排期函式(``factor_mix_schedule``)、同一個
    「``NaN`` = 不下單、0 = 清倉到零」的約定、同一張交給引擎的表。唯一分別是那
    一行的數字由驅動器算,不是由參數集抄。所以換驅動器改的只是這一行的內容,
    引擎與目標比重路徑一個字不用改(驗收條件三)。

    每一次換倉:
    1. 由 ``closes.loc[:決策日]`` 切一個 ``DriverView``——驅動器**看不見之後的日子**;
    2. 熱身期未過就用熱身期權重,過了就叫驅動器;驅動器喊回望期不夠亦退回熱身
       期權重,但記成「數據不足」,不當作驅動器作過決定;
    3. 權重過一次驗關口(``normalise_weights``),再寫入執行日那一行。
    """
    keys = tuple(exposure.weight_key for exposure in exposures)
    entity_of = {exposure.weight_key: exposure.entity_id for exposure in exposures}
    columns = [int(entity) for entity in panel.entity_ids]
    unknown = [entity for entity in entity_of.values() if entity not in set(columns)]
    if unknown:
        raise ContractViolation(
            f"敞口的實體 {unknown} 不在價格面板裡;沒有價格就落不到注,不猜、不當零"
        )

    closes = panel.close[[entity_of[key] for key in keys]].copy()
    closes.columns = list(keys)
    dates = panel.dates
    position_of = {pd.Timestamp(day): index for index, day in enumerate(dates)}

    targets = pd.DataFrame(np.nan, index=dates, columns=columns, dtype=float)
    rebalances: list[RotationRebalance] = []

    for decision_day, execution_day in factor_mix_schedule(dates, params.cadence):
        decision = pd.Timestamp(decision_day)
        history = closes.loc[:decision]
        view = DriverView(
            decision_date=decision,
            history=history,
            keys=keys,
            market=None if market is None else market.loc[:decision],
            market_ticker=market_ticker,
            # 宏觀面板同樣切到決策日為止:與收價走同一條規矩,偷看之後的日子
            # 在這裡連表達都表達不出(D-021 第 3 條)。
            macro=None if macro is None else macro.loc[:decision],
        )

        if position_of[decision] < params.warmup_bars:
            source = SOURCE_WARMUP
            raw: Mapping[str, float] = params.warmup_weights
        else:
            try:
                raw = driver.weights(view)
                source = SOURCE_DRIVER
            except InsufficientHistory:
                raw = params.warmup_weights
                source = SOURCE_INSUFFICIENT

        weights = normalise_weights(raw, keys)
        targets.loc[execution_day, :] = 0.0  # 不屬任何一格的一律清倉
        for key, weight in weights.items():
            targets.loc[execution_day, entity_of[key]] = weight

        rebalances.append(
            RotationRebalance(
                decision_date=decision.strftime("%Y-%m-%d"),
                execution_date=pd.Timestamp(execution_day).strftime("%Y-%m-%d"),
                source=source,
                weights=tuple((key, float(weights[key])) for key in keys),
                entity_weights=tuple(
                    sorted((int(entity_of[key]), float(weights[key])) for key in keys)
                ),
            )
        )

    return targets, tuple(rebalances)


# ----------------------------------------------------------------------
# 跑一次回測
# ----------------------------------------------------------------------


def _prepare_macro(
    driver: RotationDriver,
    macro: pd.DataFrame | None,
    *,
    dates: Sequence[Any],
) -> pd.DataFrame | None:
    """核對並對齊宏觀面板(KARST-040)。

    三件事,缺一不可:

    1. **驅動器要的序列一條都不可以少。** 缺任何一條即當場拒收——不是靜靜地跑出
       一條「訊號從來沒有講過話」的淨值線,那種成績表最誤導。
    2. **把宏觀面板重新索引到價格面板那批日子。** 宏觀快照對齊的是主日曆,而價格
       面板可能再窄一點(例如頭幾日有實體未有價而被丟掉)。兩邊的日子不是同一批,
       「回望 20 個交易日」在兩張表裡就各指一段——重新索引之後才對得上。
       索引不到的日子留空,驅動器讀到即當數據不足,不當零。
    3. **欄名一律大寫**,與 ``karst.data.macro`` 的序列代號同一個寫法。
    """
    needed = tuple(getattr(driver, "needs_macro", ()) or ())
    if macro is None:
        if needed:
            raise ContractViolation(
                f"驅動器「{getattr(driver, 'name', driver)}」要看宏觀序列 "
                f"{'、'.join(needed)},但今次沒有給宏觀面板;"
                "跑的時候寫明 macro=(見 karst.data.macro.read_macro_panel)"
            )
        return None

    if not isinstance(macro, pd.DataFrame):
        raise ContractViolation(f"宏觀面板要是 DataFrame,收到 {type(macro).__name__}")

    frame = macro.copy()
    frame.columns = pd.Index([str(column).strip().upper() for column in frame.columns])
    missing = [code for code in needed if code not in frame.columns]
    if missing:
        raise ContractViolation(
            f"宏觀面板缺這幾條序列:{'、'.join(missing)};"
            f"驅動器「{getattr(driver, 'name', driver)}」要看它們,"
            "缺了就不是同一個訊號,不猜、不當零"
        )

    index = pd.DatetimeIndex(pd.to_datetime(frame.index))
    frame.index = index
    return frame.sort_index().reindex(pd.DatetimeIndex(dates))


# ----------------------------------------------------------------------
# 策略合約:這條策略真正獨有的那幾件(KARST-091)
# ----------------------------------------------------------------------

#: 宏觀面板在 ``RunRequest.extras`` 裡叫什麼。策略只認得這個名,不認得檔案路徑
#: 亦不認得宏觀快照庫——讀檔那一步在執行台外面(D-007 第 3 條)。
MACRO_INPUT: Final[str] = "macro"

#: 驅動器參數的值域正本。以前散在十個驅動器各自的 ``__post_init__`` 裡,掃描腳本
#: 要改一個範圍就要翻十個類;現在一張表講完,而驅動器自己那一關照樣留住(同一組
#: 取值過兩次是重複,不是矛盾——驅動器仍然可以獨立砌出來用)。
#:
#: 鍵是 ``(驅動器, 參數名)``:同一個參數名在不同驅動器可以有不同值域——逆波幅的
#: 回望日數最少 2 日(一日算不出波幅),信用利差的最少 1 日。合成一格會靜靜地
#: 放寬其中一邊。
_DRIVER_PARAM_SPECS: Final[dict[tuple[str, str], dict[str, Any]]] = {
    ("factor_momentum", "lookback_months"): {
        "kind": KIND_INTEGER, "lower": 1, "lower_inclusive": True,
        "what": "比較各因子報酬的回望期(月)", "label": "回望期(月)",
    },
    ("factor_momentum", "mode"): {
        "kind": KIND_TEXT, "choices": ("winner", "rank"),
        "what": "整注押第一(winner)還是按名次分注(rank)", "label": "排名用法",
    },
    ("relative_strength", "lookback_months"): {
        "kind": KIND_INTEGER, "lower": 1, "lower_inclusive": True,
        "what": "與大市比較報酬的回望期(月)", "label": "回望期(月)",
    },
    ("relative_strength", "fallback"): {
        "kind": KIND_TEXT, "choices": ("cash", "equal"),
        "what": "四格全部跑輸大市時持現金(cash)還是等權(equal)", "label": "全輸時的處置",
    },
    ("inverse_volatility", "lookback_days"): {
        "kind": KIND_INTEGER, "lower": 2, "lower_inclusive": True,
        "what": "計波幅的回望期(交易日)", "label": "回望期(日)",
    },
    ("inverse_volatility", "power"): {
        "kind": KIND_NUMBER, "lower": 0.0,
        "what": "波幅倒數的次方:越大注越集中在最穩那格", "label": "集中程度",
    },
    ("trend_switch", "ma_days"): {
        "kind": KIND_INTEGER, "lower": 2, "lower_inclusive": True,
        "what": "大市均線的日數", "label": "均線日數",
    },
    ("trend_switch", "tilt"): {
        "kind": KIND_NUMBER, "lower": 0.0, "upper": 1.0, "upper_inclusive": True,
        "what": "押向其中一邊的比重", "label": "押注比重",
    },
    ("vix_level", "threshold"): {
        "kind": KIND_NUMBER, "lower": 0.0,
        "what": "VIX 高於它即當恐慌", "label": "VIX 門檻",
    },
    ("vix_term", "threshold"): {
        "kind": KIND_NUMBER, "lower": 0.0,
        "what": "期限結構比率高於它即當恐慌", "label": "期限結構門檻",
    },
    ("credit_trend", "lookback_days"): {
        "kind": KIND_INTEGER, "lower": 1, "lower_inclusive": True,
        "what": "看信用利差走向的回望期(交易日)", "label": "回望期(日)",
    },
    ("curve_trend", "lookback_days"): {
        "kind": KIND_INTEGER, "lower": 1, "lower_inclusive": True,
        "what": "看孳息曲線走向的回望期(交易日)", "label": "回望期(日)",
    },
    ("rate_trend", "lookback_days"): {
        "kind": KIND_INTEGER, "lower": 1, "lower_inclusive": True,
        "what": "看利率走向的回望期(交易日)", "label": "回望期(日)",
    },
    ("fed_expectation", "lookback_days"): {
        "kind": KIND_INTEGER, "lower": 1, "lower_inclusive": True,
        "what": "看利率預期走向的回望期(交易日)", "label": "回望期(日)",
    },
}

# 五個宏觀驅動器 + 趨勢開關那格押注比重共用同一個值域。
for _macro_key in ("vix_level", "vix_term", "credit_trend", "curve_trend",
                   "rate_trend", "fed_expectation"):
    _DRIVER_PARAM_SPECS[(_macro_key, "tilt")] = {
        "kind": KIND_NUMBER, "lower": 0.0, "upper": 1.0, "upper_inclusive": True,
        "what": "押向避險那一邊的比重", "label": "押注比重",
    }
del _macro_key


def driver_param_field(driver_key: str, name: str) -> ParamField:
    """一個驅動器參數在參數規格裡那一格。**短名一律明碼**。

    通用的百分點短名會把回望期 ``1`` 個月印成 ``100``——對讀庫的人是誤導,所以
    輪動這一線全部用 ``SLUG_VERBATIM``:數字就是數字。這一格是運行編號的原料,
    所以「印成什麼」與「值域是什麼」同樣要緊。
    """
    key = str(driver_key or "").strip()
    spec = _DRIVER_PARAM_SPECS.get((key, str(name).strip()))
    if spec is None:
        raise ContractViolation(
            f"驅動器「{key}」的參數「{name}」沒有值域規格;"
            "參數無預設值亦無隱含值域,要掃的一律先寫明(D-008 第 3 條)"
        )
    return ParamField(
        name=str(name).strip(),
        text_style=TEXT_AUTO,
        slug_style=SLUG_VERBATIM,
        **spec,
    )


@dataclass(frozen=True, slots=True)
class FactorRotationContract:
    """因子輪動策略的**策略合約**(見 ``karst.executor.contract``)。

    與因子混合蓋住同一四格因子敞口,分別只在「那一行比重由誰算」:混合照抄參數集,
    輪動每期問驅動器。所以登記那一段直接借用混合那份(``factor_specs``),不另開
    一套因子。

    **一個合約對一個驅動器。** 驅動器不是可掃軸,是「這次掃的是哪一套做法」——
    十個驅動器混在同一幅格裡,鄰域就沒有意思了(見 ``rotation_grid``)。

    以下幾格是整次掃描共用、但**照樣會改變成績**的設定,所以照樣入參數集(否則
    換一個熱身期重掃會撞回同一個運行編號,靜靜地讀回舊成績):熱身期、熱身期權重、
    交易成本、宏觀快照編號。它們不是掃描格的軸,所以不入參數集的**名**——名只由
    軸砌出來。

    ``initial_cash``、``fees``、``warmup_bars``、``warmup_weights`` 容許明寫
    ``None``,那是「這份合約只用來登記」(見 ``for_setup``);一叫 ``plan()`` 就
    當場拒收,不會靜靜地用一個猜出來的本金跑出一條淨值。
    """

    driver_key: str
    sleeves: tuple[FactorSleeve, ...]
    warmup_bars: int | None
    warmup_weights: Mapping[str, float] | None
    market_ticker: str | None
    initial_cash: float | None
    fees: float | None
    costs: TradingCosts | None = None
    macro_snapshot_id: str | None = None

    strategy_type: ClassVar[str] = FACTOR_ROTATION_STRATEGY_TYPE
    #: 這條策略交不出選股痕跡:四格敞口固定,每期變的只是比重,沒有「由三千隻收
    #: 到三十隻」那個漏斗(D-013)。空的就是空的,不硬套一個兩層殼扮有選股。
    funnel_stages: ClassVar[tuple[str, ...]] = ()
    engine_path: ClassVar[str] = ENGINE_TARGETS

    def __post_init__(self) -> None:
        key = str(self.driver_key or "").strip()
        if key not in DRIVER_PARAMETERS:
            raise ContractViolation(
                f"沒有「{key}」這個驅動器;有的是:{'、'.join(sorted(DRIVER_PARAMETERS))}"
            )
        sleeves = tuple(self.sleeves)
        if len(sleeves) < 2:
            raise ContractViolation("因子輪動最少要有兩格敞口才有東西可以互相調配")
        object.__setattr__(self, "driver_key", key)
        object.__setattr__(self, "sleeves", sleeves)
        object.__setattr__(
            self,
            "market_ticker",
            str(self.market_ticker).strip() if self.market_ticker else None,
        )
        object.__setattr__(
            self,
            "macro_snapshot_id",
            str(self.macro_snapshot_id).strip() if self.macro_snapshot_id else None,
        )

    @classmethod
    def for_setup(
        cls,
        driver_key: str,
        sleeves: Sequence[FactorSleeve] = FACTOR_ETF_SLEEVES,
    ) -> "FactorRotationContract":
        """只用來登記的一份合約:登記碰不到帳戶設定與熱身期,所以那幾格明寫留空。"""
        return cls(
            driver_key=driver_key,
            sleeves=tuple(sleeves),
            warmup_bars=None,
            warmup_weights=None,
            market_ticker=None,
            initial_cash=None,
            fees=None,
            costs=None,
            macro_snapshot_id=None,
        )

    @property
    def weight_keys(self) -> tuple[str, ...]:
        return tuple(sleeve.weight_key for sleeve in self.sleeves)

    @property
    def param_names(self) -> tuple[str, ...]:
        """這個驅動器自己那幾個參數(即掃描格上的軸,節奏除外)。"""
        return DRIVER_PARAMETERS[self.driver_key]

    @property
    def macro_series(self) -> tuple[str, ...]:
        """這個驅動器要看哪幾條宏觀序列(空的即它只看價格)。"""
        return macro_series_needed(self.driver_key)

    def param_spec(self) -> ParamSpec:
        """驅動器 + 它自己那幾個參數 + 熱身期 + 節奏(+ 成本、宏觀那幾格)。

        **一格預設值都沒有**(D-008 第 3 條)。次序刻意與參數集裡讀出來的次序一致,
        方便人眼對照;參數集的名只由掃描格的軸砌出來,與這裡的次序無關。
        """
        fields: list[ParamField] = [
            ParamField(
                name=DRIVER_KEY,
                kind=KIND_TEXT,
                what="每期由哪一套做法決定四格比重",
                label="驅動器",
                choices=tuple(sorted(DRIVER_BUILDERS)),
                text_style=TEXT_VERBATIM,
                slug_style=SLUG_VERBATIM,
            )
        ]
        fields.extend(driver_param_field(self.driver_key, name) for name in self.param_names)
        fields.append(
            ParamField(
                name=WARMUP_BARS_KEY,
                kind=KIND_INTEGER,
                what="頭幾根 K 線不讓驅動器話事(回望期未夠長的那一段)",
                label="熱身期(K 線根數)",
                lower=0,
                lower_inclusive=True,
                text_style=TEXT_AUTO,
                slug_style=SLUG_VERBATIM,
            )
        )
        fields.extend(
            ParamField(
                name=f"{WARMUP_PREFIX}{key}",
                kind=KIND_NUMBER,
                what=f"熱身期那段日子 {key} 佔組合的比重",
                label=f"熱身期權重({key})",
                lower=0.0,
                upper=1.0,
                lower_inclusive=True,
                upper_inclusive=True,
                text_style=TEXT_FOUR_PLACES,
                slug_style=SLUG_VERBATIM,
            )
            for key in self.weight_keys
        )
        fields.append(
            ParamField(
                name=CADENCE_PARAM,
                kind=KIND_TEXT,
                what="幾耐讓驅動器重新決定一次四格比重",
                label="換倉節奏",
                choices=tuple(sorted(CADENCES)),
                text_style=TEXT_VERBATIM,
                slug_style=SLUG_VERBATIM,
                slot=SLOT_CADENCE,
            )
        )
        fields.extend(cost_fields(self.costs))
        if self.macro_snapshot_id:
            # 換一份宏觀數據就是另一次運行,所以編號要入參數集(KARST-040)。
            # 價格驅動器一格都不寫、名亦一字不改,KARST-036/043 那批舊運行照樣撞得回去。
            fields.append(
                ParamField(
                    name=MACRO_SNAPSHOT_KEY,
                    kind=KIND_TEXT,
                    what="這次用的宏觀數據快照編號",
                    label="宏觀快照",
                    choices=(self.macro_snapshot_id,),
                    text_style=TEXT_VERBATIM,
                    slug_style=SLUG_VERBATIM,
                )
            )
            fields.append(
                ParamField(
                    name=MACRO_SERIES_KEY,
                    kind=KIND_TEXT,
                    what="這個驅動器由宏觀快照讀哪幾條序列",
                    label="宏觀序列",
                    choices=(MACRO_SERIES_SEPARATOR.join(self.macro_series),),
                    text_style=TEXT_VERBATIM,
                    slug_style=SLUG_VERBATIM,
                )
            )
        return ParamSpec(fields=tuple(fields))

    def factor_specs(self, snapshot_id: str) -> tuple[FactorSpec, ...]:
        """四條因子,與因子混合**同一份**——輪動與混合蓋住的是同一四格敞口。

        另開一套只會令同一個敞口在庫裡有兩條因子鏈,之後誰都講不出兩者的分別。
        """
        return FactorMixContract.for_setup(self.sleeves).factor_specs(snapshot_id)

    def needs_entities(self, params: Mapping[str, Any]) -> EntityRequest:
        """四格敞口持得到;大市那條線**只做訊號,一股不持**;宏觀序列連實體都不是。

        「大市不可以同時是持倉」那一關不在這裡自己寫一次——同一個實體佔兩格會被
        執行台的實體解析當場擋住(``DuplicateExposureEntity``),全倉只此一份。
        """
        return EntityRequest(
            exposures=tuple(sleeve.ticker for sleeve in self.sleeves),
            signals=(self.market_ticker,) if self.market_ticker else (),
            series=self.macro_series,
        )

    def build_driver(self, values: Mapping[str, Any]) -> RotationDriver:
        """由一組已驗取值砌出這一格的驅動器。"""
        return build_driver(
            self.driver_key, **{name: values[name] for name in self.param_names}
        )

    def params_from(self, values: Mapping[str, Any]) -> FactorRotationParams:
        """把一組已驗取值收成 ``FactorRotationParams``。"""
        missing = [
            label
            for label, value in (
                ("起始本金", self.initial_cash),
                ("手續費率", self.fees),
                ("熱身期", self.warmup_bars),
                ("熱身期權重", self.warmup_weights),
            )
            if value is None
        ]
        if missing:
            raise ContractViolation(
                f"這份因子輪動合約只用來登記({'、'.join(missing)}留空),跑不動;"
                "要跑一次回測請明寫那幾格"
            )
        # 要看宏觀的驅動器沒有宏觀快照編號即當場拒收:編號是這次成績來歷的一部分,
        # 亦入參數集(換一份宏觀數據就要另一個運行編號),不可留空。登記那一步碰
        # 不到宏觀數據,所以這一關留到真的要跑才把。
        if self.macro_series and not self.macro_snapshot_id:
            raise ContractViolation(
                f"驅動器「{self.driver_key}」用宏觀數據,但沒有寫明宏觀快照編號;"
                "編號是這次成績來歷的一部分,亦入參數集,不可留空"
            )
        return FactorRotationParams(
            cadence=values[CADENCE_PARAM],
            warmup_bars=int(self.warmup_bars),
            warmup_weights=dict(self.warmup_weights or {}),
            initial_cash=float(self.initial_cash),
            fees=float(self.fees),
        )

    def plan(self, request: RunRequest) -> TargetPlan:
        """策略本體:驅動器逐期在四格敞口之間移權,砌一張目標比重表。**純函數。**

        不開庫、不讀檔、不 import 第三方引擎——哪一件引擎在背後跑,本檔一個字
        都不提(D-007 第 3 條)。

        交易成本不在計劃裡:它入的是引擎參數,由 ``CostedEngine`` 在參數交到引擎
        之前補上(見 ``karst.engine.costed``)。
        """
        params = self.params_from(request.params)
        driver = self.build_driver(request.params)
        panel = request.panel

        exposures = tuple(
            RotationExposure(
                sleeve=sleeve,
                entity_id=request.entity(sleeve.ticker).entity_id,
                entity_kind=request.entity(sleeve.ticker).entity_kind,
                factor_version_id=request.factor(sleeve.factor_name).factor_version_id,
                factor_version_no=request.factor(sleeve.factor_name).version_no,
            )
            for sleeve in self.sleeves
        )

        market: pd.Series | None = None
        if self.market_ticker:
            market = panel.close[request.entity(self.market_ticker).entity_id]
        elif getattr(driver, "needs_market", False):
            raise ContractViolation(
                f"驅動器「{getattr(driver, 'name', driver)}」要看大市那一條線,"
                f"但今次沒有給大市代號;寫明 market_ticker(例如 {DEFAULT_MARKET_TICKER!r})"
            )

        macro_frame = _prepare_macro(
            driver, request.extras.get(MACRO_INPUT), dates=panel.dates
        )
        targets, rebalances = rotation_targets(
            panel=panel,
            exposures=exposures,
            driver=driver,
            params=params,
            market=market,
            market_ticker=self.market_ticker,
            macro=macro_frame,
        )
        return TargetPlan(
            targets=targets,
            cadence=params.cadence,
            initial_cash=params.initial_cash,
            fees=params.fees,
            rebalances=rebalances,
            selection=None,
            extras={
                "params": params,
                "exposures": exposures,
                "driver": driver,
                "macro_series": self.macro_series,
            },
        )

