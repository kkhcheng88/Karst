"""因子混合的**掃描格**:一格權重 = 一個參數集 = 一次運行。

本檔只剩「這條策略要掃一幅什麼形狀的格」那一件——權重單純形格,可另加換倉節奏
一維。怎樣跑一格已經不在這裡:登記、查重、跑引擎、落痕四件事全條策略線只此一份,
住在**策略執行台**(``Executor.sweep``,KARST-091)。

參數集的名怎樣砌亦不在這裡:一格一個名(``{前綴}{格的短名}{成本那一截}``),而
短名的正本住 ``karst.executor.contract``——它同時是運行編號的原料,所以全倉只可
以有一份寫法。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..errors import ContractViolation
from ..executor.contract import TEXT_EIGHT_PLACES, TEXT_FOUR_PLACES, value_text
from ..executor.contract import cost_inputs, cost_slug
from ..strategies.factor_mix import CADENCE_PARAM, FactorSleeve
from .grid import CHOICE, ProductGrid, SimplexGrid, SweepAxis, SweepGrid, SweepPoint, compose

__all__ = [
    "CADENCE_AXIS",
    "cost_inputs",
    "cost_slug",
    "cost_text",
    "reference_point",
    "weight_grid",
    "weight_text",
]

# 換倉節奏在掃描格裡的軸名。權重之外多掃一維節奏時用這個名。
CADENCE_AXIS = CADENCE_PARAM


def weight_grid(
    sleeves: Sequence[FactorSleeve],
    *,
    step: float,
    cadences: Sequence[str] | None = None,
    total: float = 1.0,
) -> SweepGrid:
    """砌因子混合的掃描格:權重單純形格,可另加換倉節奏一維。

    四格權重配 10% 步長是 286 格,5% 是 1771 格。``cadences`` 給了就再乘節奏那一維
    (例如月度與季度,兩個節奏即 572 格)。

    一句要記住:**步長 10% 排不出「各 25%」**——十步分不均四格。要那一格做對照,
    請用 5% 步長,或者把它當**對照格**另外跑一次(見 ``reference_point``)。

    **軸型**(KARST-048):四格權重是**連續軸**(移一步 = 把一步的權重由其中一格
    搬去另一格),換倉節奏是**選擇軸**——月度改季度是換一套做法,不是把某個刻度
    推一格。所以節奏不入鄰域,而是把整個格切成兩層(或者幾層),每層各出一份
    平原判讀,判得出山脊:權重上鋪得平,但換一個節奏就沒有了。
    """
    keys = [sleeve.weight_key for sleeve in sleeves]
    simplex = SimplexGrid(keys, step=step, total=total)
    if not cadences:
        return simplex
    # ``ordered=True`` 對選擇軸沒有作用,照原樣留住只為 ``all_continuous`` 還原得
    # 到軸型之前那個格(舊口徑重判要用)。
    axis = SweepAxis(
        name=CADENCE_AXIS,
        values=tuple(str(c).strip() for c in cadences),
        ordered=True,
        kind=CHOICE,
    )
    return compose(simplex, ProductGrid([axis]))


def reference_point(
    sleeves: Sequence[FactorSleeve],
    weights: Mapping[str, float],
    *,
    cadence: str | None = None,
) -> SweepPoint:
    """砌一個**對照格**:例如四格各 25%。

    對照格不一定在掃描格上(10% 步長就排不出各 25%),但它照樣跑得、照樣落痕、
    照樣有運行編號——報告把它單獨列一行,好讓人見到「掃出來的最優」贏了固定
    比重幾多。
    """
    values: list[tuple[str, Any]] = []
    for sleeve in sleeves:
        if sleeve.weight_key not in weights:
            raise ContractViolation(f"對照格缺「{sleeve.weight_key}」的權重")
        values.append((sleeve.weight_key, float(weights[sleeve.weight_key])))
    if cadence is not None:
        values.append((CADENCE_AXIS, str(cadence).strip()))
    return SweepPoint(values=tuple(values))


def weight_text(value: Any) -> str:
    """權重寫入參數集時的文字。固定寫法,重掃一字不差。

    參數集一律以文字存值(``store`` 會 ``str(value).strip()``),而運行編號正是由
    這串文字算出來的——所以格式一變,同一格就會變成另一個運行。這裡定死:最多四位
    小數,末尾的零剪走(``0.25``、``0.1``、``0``、``1``)。

    寫法的正本住 ``karst.executor.contract``(KARST-090);本檔只轉引。
    """
    return value_text(value, TEXT_FOUR_PLACES)


def cost_text(value: Any) -> str:
    """成本寫入參數集時的文字。與 ``weight_text`` 同一個道理,但**精細得多**。

    權重那個寫法只留四位小數,而成本細得多:滑點 5 個基點是 ``0.0005``,每股
    US$0.005 是 ``0.005``,再細一級就會被四位小數剪成同一串字——兩組不同的成本
    撞成同一個參數集,即撞成同一個運行編號,靜靜地讀回上一次的成績。這裡留八位。

    寫法的正本住 ``karst.executor.contract``(KARST-090);本檔只轉引。
    """
    return value_text(value, TEXT_EIGHT_PLACES)
