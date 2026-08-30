"""因子輪動的**掃描格**:一格驅動器參數 = 一個參數集 = 一次運行(KARST-036)。

本檔只剩「這個驅動器要掃哪幾條軸、哪一條有序、哪一條是選擇軸」那一件。怎樣跑一
格已經不在這裡——那件事全條策略線只此一份,住在**策略執行台**(``Executor.sweep``,
KARST-091):以前的 ``FactorRotationJob`` 把登記、查重、跑引擎、落痕各抄一次,而
那四件與因子混合、與正式運行做法一模一樣。

``rotation_grid(...)``
    砌一個驅動器的參數格。**取值無預設**——掃 L 的哪幾個月、M 的哪幾條均線,一律
    由呼叫方寫明。哪一條軸有序(回望期由短到長)、哪一條無序(``winner`` 與
    ``rank`` 不是一步之遙),由驅動器自己在 ``DRIVER_UNORDERED_PARAMETERS`` 講明,
    因為相鄰的定義就是平原與孤峰判讀的地基。**軸型**(連續 / 選擇)同一個道理,
    由 ``DRIVER_CHOICE_PARAMETERS`` 講明:退路、模式與換倉節奏是選擇軸,不入鄰域
    而是把格切成層(KARST-048)。

成績表、分段超額、成本對照與來歷一句(``scoreboard`` 等)搬去了 ``sweep.report``
——它們是**報告**,不是掃描格。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from ..errors import ContractViolation
from ..executor.contract import SLUG_VERBATIM, TEXT_AUTO, value_text
from ..executor.contract import point_slug as contract_point_slug
from ..strategies.factor_rotation import (
    DRIVER_KEY,
    DRIVER_PARAMETERS,
    DRIVER_UNORDERED_PARAMETERS,
)
from .factor_mix import CADENCE_AXIS
from .grid import CHOICE, CONTINUOUS, ProductGrid, SweepAxis, SweepGrid, SweepPoint

__all__ = [
    "CADENCE_AXIS",
    "DRIVER_CHOICE_PARAMETERS",
    "DRIVER_KEY",
    "param_text",
    "point_slug",
    "rotation_grid",
]

# 驅動器參數之中,哪幾個是**選擇軸**(KARST-048)。選擇軸換一個取值即**換一套
# 做法**,不是沿刻度微調:退路由「持現金」改成「均分」、模式由「整注押第一」改成
# 「按名次分注」,鄰格是另一個世界,不是一步之遙。它不入鄰域,改為把格切成層,
# 逐層各出一份判讀(見 ``karst.sweep.grid``、``karst.sweep.verdict``)。
#
# 沒有列出來的參數一律是**連續軸**:回望期、均線日數、門檻、押注比重——這幾條
# 沿住走一步有刻度上的意思。
#
# 換倉節奏(``cadence``)不在這張表:它不是驅動器自己的參數,而是每個格都有的
# 那一條,一律當選擇軸(月度改季度是換一套做法)。
#
# 這張表與 ``DRIVER_UNORDERED_PARAMETERS`` 現時逐項相同,但**兩者不是同一件事**:
# 無序講「這條軸上一步是幾遠」,軸型講「這條軸該不該走一步」。所以照樣分開寫,
# 不由一張表推另一張。
DRIVER_CHOICE_PARAMETERS: Final[Mapping[str, tuple[str, ...]]] = {
    "factor_momentum": ("mode",),  # winner=整注押第一 / rank=按名次分注
    "relative_strength": ("fallback",),  # cash=持現金 / equal=均分
    "inverse_volatility": (),  # 回望日數與次方皆連續
    "trend_switch": (),  # 均線日數與押注比重皆連續
    # 宏觀驅動器:門檻 / 回望日數與押注比重皆連續,一條選擇軸都沒有,
    # 所以層由節奏一條軸切出來(月度、季度兩層)。
    "vix_level": (),
    "vix_term": (),
    "credit_trend": (),
    "curve_trend": (),
    "rate_trend": (),
    "fed_expectation": (),
}


def param_text(value: Any) -> str:
    """參數寫入參數集時的文字。固定寫法,重掃一字不差。

    參數集一律以文字存值(``store`` 會 ``str(value).strip()``),而運行編號正是由
    這串文字算出來的——所以格式一變,同一格就會變成另一個運行。這裡定死:整數就
    是整數(``6``)、小數最多四位並剪走末尾的零(``0.5``)、其餘照原文剪空白。

    寫法的正本住 ``karst.executor.contract``(KARST-090);本檔只轉引。
    """
    return value_text(value, TEXT_AUTO)


def point_slug(point: SweepPoint) -> str:
    """一格的短名(參數集名用)。``lookback_months6-modewinner-cadencemonthly``。

    通用的 ``SweepPoint.slug`` 把 0 至 1 之間的數當權重印成百分點,於是回望期
    ``1`` 個月會印成 ``100``——對讀庫的人是誤導。本層自己用明碼:數字就是數字。

    寫法的正本住 ``karst.executor.contract``(KARST-090);本檔只轉引「明碼」那種。
    """
    return contract_point_slug(point.values, SLUG_VERBATIM)


def rotation_grid(
    driver_key: str,
    *,
    values: Mapping[str, Sequence[Any]],
    cadences: Sequence[str],
) -> SweepGrid:
    """砌一個驅動器的參數格:驅動器自己那幾個參數 × 換倉節奏。

    ``values`` 逐個參數寫明要掃哪些取值——**沒有預設取值**(D-008 第 3 條)。

    **每條軸自報軸型**(KARST-048)。連續軸(回望期、門檻、押注比重)相鄰 = 沿
    住它移一步;選擇軸(退路、模式,加上永遠是選擇軸的換倉節奏)不入鄰域,改為
    把格切成一層層,每層各出一份判讀。哪幾個驅動器參數是選擇軸,見
    ``DRIVER_CHOICE_PARAMETERS``。

    所以一個「回望期 × 退路 × 節奏」的格,某一格的鄰居只有回望期前後那兩格,不
    是七格——「換一套做法」不再被當成「差一步」。要還原軸型之前那個格(舊口徑
    重判、對回舊落檔),用 ``karst.sweep.grid.all_continuous``。
    """
    key = str(driver_key or "").strip()
    if key not in DRIVER_PARAMETERS:
        raise ContractViolation(
            f"沒有「{key}」這個驅動器;有的是:{'、'.join(sorted(DRIVER_PARAMETERS))}"
        )
    if key not in DRIVER_CHOICE_PARAMETERS:
        raise ContractViolation(
            f"驅動器「{key}」未講明哪幾個參數是選擇軸;請在 DRIVER_CHOICE_PARAMETERS 寫明"
            "(一個都沒有就寫空的),軸型不由參數名去猜"
        )
    names = DRIVER_PARAMETERS[key]
    unordered = set(DRIVER_UNORDERED_PARAMETERS.get(key, ()))
    choices = set(DRIVER_CHOICE_PARAMETERS[key])
    stray = sorted(choices - set(names))
    if stray:
        raise ContractViolation(
            f"驅動器「{key}」的選擇軸寫了它沒有的參數:{'、'.join(stray)}"
        )

    missing = [name for name in names if not values.get(name)]
    if missing:
        raise ContractViolation(
            f"驅動器「{key}」這幾個參數沒有寫明要掃哪些取值:{'、'.join(missing)};"
            "掃描不設預設取值"
        )
    extra = [name for name in values if name not in names]
    if extra:
        raise ContractViolation(f"驅動器「{key}」不認得這幾個參數:{'、'.join(extra)}")
    if not cadences:
        raise ContractViolation("換倉節奏要寫明要掃哪幾個;節奏無預設值(D-009 第 7 條)")

    axes = [
        SweepAxis(
            name=name,
            values=tuple(values[name]),
            ordered=name not in unordered,
            kind=CHOICE if name in choices else CONTINUOUS,
        )
        for name in names
    ]
    # 換倉節奏永遠是選擇軸:月度改季度是換一套做法,不是把某個刻度推一格。
    # ``ordered=True`` 對選擇軸沒有作用,照原樣留住只為 ``all_continuous`` 還原得
    # 到軸型之前那個格。
    axes.append(
        SweepAxis(
            name=CADENCE_AXIS,
            values=tuple(str(c).strip() for c in cadences),
            ordered=True,
            kind=CHOICE,
        )
    )
    return ProductGrid(axes)
