"""按因子排名選前 N 隻等權——按知情時點讀值,到目標比重表為止。

取值那一路是 ``factorvalues.FactorValueSource``:簽名與單一定義庫原本那個
``latest_known_values`` 一字不差,分別只在它**兩個住處一齊看**——定義庫的
``factor_value`` 表(小批人手值)與因子值批次的 Parquet 檔(D-032、KARST-071)。
本檔不改核心,亦沒有一個字提到背後跑的是哪個引擎。

兩條紀律寫死在這裡:

1. **知情時間為閘**(D-021 第 3 條):每個決策日只看見「截至該日收工為止」
   已知的最新值。因此逐個決策日問一次,不是一次讀全部再自己截。
2. **缺失=不參與**(D-021 第 4 條):沒有值的實體不入排名,不填補、不當零。
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from ..store import DefinitionStore
from .contracts import Rebalance, RankingRebalanceParams
from .factorvalues import FactorValueSource
from .funnel import STAGE_SCOPE, STAGE_SELECTED, SelectionTraceBuilder


def read_factor_panel(
    store: DefinitionStore,
    factor_name: str,
    decision_dates: Sequence[pd.Timestamp],
    *,
    version_no: int | None = None,
    entity_ids: Sequence[int] | None = None,
) -> pd.DataFrame:
    """逐個決策日按知情時間讀出因子值,砌成「決策日 × 實體編號」的表。

    ``as_of`` 傳日期(不是時間戳),取值那一層會當「該日收工為止」處理;
    當日稍後才知道的值,那一日看不見。

    值住表定住檔,呼叫方不必知道:``FactorValueSource`` 兩邊一齊看。整段決策日
    共用同一個來源,所以一條因子只讀一次——揀出來的值與逐日各讀一次完全相同。
    """
    wanted = None if entity_ids is None else [int(entity) for entity in entity_ids]
    columns_hint = None if wanted is None else wanted
    source = FactorValueSource(store)

    readings: dict[pd.Timestamp, pd.Series] = {}
    for day in decision_dates:
        stamp = pd.Timestamp(day)
        frame = source.latest_known_values(
            factor_name,
            stamp.date(),  # 傳純日期 → 閘定在該日收工
            version_no=version_no,
            entity_ids=wanted,
        )
        readings[stamp] = pd.Series(
            frame["value"].to_numpy(dtype=float),
            index=frame["entity_id"].to_numpy(dtype=int),
            dtype=float,
        )

    if not readings:
        return pd.DataFrame(index=pd.DatetimeIndex([]), columns=columns_hint or [], dtype=float)

    panel = pd.DataFrame(readings).T
    panel.index = pd.DatetimeIndex(panel.index)
    if columns_hint is not None:
        panel = panel.reindex(columns=columns_hint)
    else:
        panel = panel.reindex(columns=sorted(int(column) for column in panel.columns))
    return panel.astype(float)


def build_targets(
    *,
    dates: pd.DatetimeIndex,
    factor_panel: pd.DataFrame,
    schedule: Sequence[tuple[pd.Timestamp, pd.Timestamp]],
    params: RankingRebalanceParams,
    entity_ids: Sequence[int],
    trace: SelectionTraceBuilder | None = None,
    factor_name: str | None = None,
) -> tuple[pd.DataFrame, tuple[Rebalance, ...]]:
    """目標比重表:換倉的**執行日**那一行寫比重,其餘一律 ``NaN``。

    ``NaN`` 的意思是「這一根 K 線不下單」;寫 0 的意思是「清倉到零」——兩者
    不可混為一談。每次換倉把全部持倉拉回 ``1/N`` 等權,沒入選的一律歸零。

    同分怎樣排:先按分數,再按實體編號由細到大。同一批數據跑一百次,揀中的
    是同一批股票。

    交一個 ``trace`` 進來,順手把選股痕跡記低(KARST-056):範圍與入選兩層,
    加逐股的因子分數與當日排名。**這條路上的分數是真正的因子分數**,所以
    ``factor_name`` 就是分數名。記痕跡是同一趟計算的副產品,不是另跑一次
    ——畫面見到的排名,與引擎據以落注的排名必然是同一份。
    """
    columns = [int(entity) for entity in entity_ids]
    known = set(columns)
    targets = pd.DataFrame(np.nan, index=dates, columns=columns, dtype=float)
    ascending = params.direction == "low"

    rebalances: list[Rebalance] = []
    for decision_day, execution_day in schedule:
        scores = _scores_on(factor_panel, decision_day, known)
        chosen = _pick(scores, ascending=ascending, top_n=params.top_n)

        targets.loc[execution_day, :] = 0.0  # 沒入選的一律清倉
        weight = 0.0
        if chosen:
            weight = 1.0 / len(chosen)
            targets.loc[execution_day, chosen] = weight

        rebalances.append(
            Rebalance(
                decision_date=pd.Timestamp(decision_day).strftime("%Y-%m-%d"),
                execution_date=pd.Timestamp(execution_day).strftime("%Y-%m-%d"),
                selected=tuple(chosen),
                weight=weight,
            )
        )

        if trace is not None:
            trace.stage(decision_day, STAGE_SCOPE, columns)
            trace.stage(decision_day, STAGE_SELECTED, chosen)
            if factor_name:
                trace.score(
                    decision_day,
                    factor_name,
                    {int(entity): float(value) for entity, value in scores.items()},
                    higher_is_better=not ascending,
                )
    return targets, tuple(rebalances)


def _scores_on(factor_panel: pd.DataFrame, decision_day: pd.Timestamp, known: set[int]) -> pd.Series:
    """決策日那一行的因子值,剔走沒有值的與面板無價的實體。"""
    if decision_day not in factor_panel.index:
        return pd.Series(dtype=float)
    row = factor_panel.loc[decision_day].dropna()  # dropna 就是「不參與」那一步
    return row[[column for column in row.index if int(column) in known]]


def _pick(scores: pd.Series, *, ascending: bool, top_n: int) -> list[int]:
    if scores.empty:
        return []
    table = pd.DataFrame(
        {
            "entity_id": scores.index.to_numpy(dtype=int),
            "score": scores.to_numpy(dtype=float),
        }
    ).sort_values(by=["score", "entity_id"], ascending=[ascending, True], kind="mergesort")
    return [int(entity) for entity in table["entity_id"].to_numpy()[:top_n]]
