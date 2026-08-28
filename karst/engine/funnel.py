"""選股漏斗(selection funnel)的層次,與一次運行的逐日選股痕跡。

D-013 第 1 條把一個策略的選股漏斗定為**至多四層**——非結構化量化/基本面、
技術量化、圖形、技術分析理論——逐層篩選,上一層的輸出是下一層的宇宙。畫面
上那條漏斗在四層之外前後各加一格:最前是「範圍」(這一日這套策略看得見什麼),
最後是「持倉」(扣除倉位上限與風控之後,收工時手上實際有什麼)。

**本檔是那幾層的單一正本**:層的鍵、次序、中文名只此一份。引擎、留痕、網頁殼
同取這一處,不各自鑄一套(D-002 單一正本)。

一次運行的痕跡兩張長表:

``candidates`` 候選名單
    決策日 × 層 × 實體編號。一列的意思是「這一日這一隻到達了這一層」。
    「持倉」那一層**不在這張表**——它由逐日持倉那條序列讀得回,存兩份就會有
    兩個講法。

``factor_scores`` 逐股分數
    決策日 × 實體編號 × 分數名 → 數值,連當日的橫斷面排名。``score_name``
    講明那個數字是什麼:排名再平衡路徑寫的是**因子名**(那正是一個因子分數),
    規則路徑寫的是決定入不入場的那兩個數(突破幅度、計劃賠率)。一個數字叫
    什麼名,由算它出來的那條路徑講,本檔不代它起名——**寧可寫清楚是什麼,
    不硬套一個「因子分數」的殼**。

兩張表都**不入運行編號**:編號蓋的仍然是策略版本 × 參數集 × 期間 × 數據快照 ×
引擎版本那五件(規格 7.4),多存兩張表不會令同一次運行變成另一次運行。舊運行
沒有這兩張表,照樣讀得回、照樣畫得出原來那兩層。

缺失=不參與(D-021 第 4 條):某一日某一隻沒有分數,就沒有那一列,不填 0、
不當中位數。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from ..errors import ContractViolation

# ----------------------------------------------------------------------
# 層的鍵、次序、中文名
# ----------------------------------------------------------------------

STAGE_SCOPE: Final[str] = "scope"
STAGE_FUNDAMENTAL: Final[str] = "fundamental"
STAGE_TECHNICAL: Final[str] = "technical"
STAGE_PATTERN: Final[str] = "pattern"
STAGE_THEORY: Final[str] = "theory"
STAGE_SELECTED: Final[str] = "selected"
STAGE_HELD: Final[str] = "held"

# 由闊到窄。中間四格就是 D-013 那四層;最前的範圍與最後的持倉不是選股層,
# 是漏斗的兩個端點。
FUNNEL_STAGES: Final[tuple[str, ...]] = (
    STAGE_SCOPE,
    STAGE_FUNDAMENTAL,
    STAGE_TECHNICAL,
    STAGE_PATTERN,
    STAGE_THEORY,
    STAGE_SELECTED,
    STAGE_HELD,
)

STAGE_LABELS: Final[dict[str, str]] = {
    STAGE_SCOPE: "範圍",
    STAGE_FUNDAMENTAL: "基本面關",
    STAGE_TECHNICAL: "技術關",
    STAGE_PATTERN: "圖形關",
    STAGE_THEORY: "理論關",
    STAGE_SELECTED: "入選",
    STAGE_HELD: "持倉",
}

# D-013 那四層本身(不含範圍與持倉兩個端點)。到達其中任何一層而未入選,
# 就是詞彙表「選股快照」那四個狀態裡的「觀察」。
GATE_STAGES: Final[tuple[str, ...]] = (
    STAGE_FUNDAMENTAL,
    STAGE_TECHNICAL,
    STAGE_PATTERN,
    STAGE_THEORY,
)

# 落得到痕跡的層:持倉那一層由逐日持倉序列讀回,不入這張表。
TRACE_STAGES: Final[tuple[str, ...]] = tuple(
    stage for stage in FUNNEL_STAGES if stage != STAGE_HELD
)

# 逐股在漏斗上的狀態(詞彙表「選股快照」:未過/觀察/入選/持倉)。
STATUS_HELD: Final[str] = "持倉"
STATUS_SELECTED: Final[str] = "入選"
STATUS_WATCH: Final[str] = "觀察"
STATUS_OUT: Final[str] = "未過"

# 兩張長表的欄位。與 ``karst.runs.registry`` 那邊**同名同義**——引擎砌出來的
# 表因此可以原封不動倒去落痕那一層,兩邊各自寫死一份名,誰都不用 import 誰
# (與逐筆交易 ``Order`` / ``ORDER_COLUMNS`` 同一個做法)。
CANDIDATE_COLUMNS: Final[tuple[str, ...]] = ("decision_date", "stage", "entity_id")
SCORE_COLUMNS: Final[tuple[str, ...]] = (
    "decision_date",
    "entity_id",
    "score_name",
    "score",
    "rank",
)


def _day(value: object) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


@dataclass(frozen=True, slots=True)
class SelectionTrace:
    """一次運行的選股痕跡:逐個決策日,各層的候選名單與逐股分數。

    形狀就是落痕那一層收的形狀,所以 ``record_simulation`` 一句就接得通:
    結果物件上有 ``candidates`` / ``factor_scores`` 兩件,它自己會拿走。
    """

    candidates: pd.DataFrame
    factor_scores: pd.DataFrame

    @property
    def decision_dates(self) -> tuple[str, ...]:
        days = set(self.candidates["decision_date"]) | set(
            self.factor_scores["decision_date"]
        )
        return tuple(sorted(days))

    @property
    def stages(self) -> tuple[str, ...]:
        """這次運行真有痕跡的層,由闊到窄。"""
        present = set(self.candidates["stage"])
        return tuple(stage for stage in TRACE_STAGES if stage in present)

    @property
    def score_names(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.factor_scores["score_name"])))

    def frames(self) -> dict[str, pd.DataFrame]:
        return {"candidates": self.candidates, "factor_scores": self.factor_scores}


class SelectionTraceBuilder:
    """逐個決策日砌痕跡。兩種餵法:一日一批,或者整塊面板一次過。

    整塊面板那兩個方法是為逐根 K 線都做決策的路徑而設——規則路徑一次運行有
    近三千個決策日,逐日 for 一次 pandas 會慢到人等得出。
    """

    def __init__(self) -> None:
        self._stage_rows: list[tuple[str, str, int]] = []
        self._score_rows: list[pd.DataFrame] = []

    # ---- 一日一批 ----

    def stage(self, decision_date: object, stage: str, entity_ids: Sequence[int]) -> None:
        """記低「這一日,這一批到達了這一層」。"""
        if stage not in TRACE_STAGES:
            raise ContractViolation(
                f"選股漏斗只有 {list(TRACE_STAGES)} 這幾層落得到痕跡,收到 {stage!r};"
                f"「{STAGE_LABELS[STAGE_HELD]}」那一層由逐日持倉序列讀回,不另存一份"
            )
        day = _day(decision_date)
        for entity_id in entity_ids:
            self._stage_rows.append((day, stage, int(entity_id)))

    def score(
        self,
        decision_date: object,
        score_name: str,
        values: Mapping[int, float],
        *,
        higher_is_better: bool = True,
    ) -> None:
        """記低這一日的一組分數。留空的一隻不入表(缺失=不參與)。"""
        if not values:
            return
        series = pd.Series(
            {int(key): float(value) for key, value in values.items()}, dtype=float
        )
        # 留空、±inf 一律當「這一日這一隻沒有分數」:沒有那一列,不填 0(D-021 第 4 條)
        series = series[np.isfinite(series.to_numpy(dtype=float))]
        if series.empty:
            return
        self._append_scores(
            [_day(decision_date)] * len(series),
            series.index.to_numpy(dtype=np.int64),
            score_name,
            series.to_numpy(dtype=float),
            series.rank(ascending=not higher_is_better, method="min").to_numpy(),
        )

    # ---- 整塊面板一次過 ----

    def stage_panel(
        self,
        stage: str,
        dates: Sequence[object],
        entity_ids: Sequence[int],
        mask: np.ndarray,
    ) -> None:
        """整塊「日期 × 實體」的真假面板,真的那幾格即到達這一層。"""
        if stage not in TRACE_STAGES:
            raise ContractViolation(
                f"選股漏斗只有 {list(TRACE_STAGES)} 這幾層落得到痕跡,收到 {stage!r}"
            )
        days = [_day(day) for day in dates]
        entities = np.asarray(entity_ids, dtype=np.int64)
        rows, columns = np.nonzero(np.asarray(mask, dtype=bool))
        for row, column in zip(rows.tolist(), columns.tolist()):
            self._stage_rows.append((days[row], stage, int(entities[column])))

    def score_panel(
        self,
        score_name: str,
        dates: Sequence[object],
        entity_ids: Sequence[int],
        values: np.ndarray,
        *,
        higher_is_better: bool = True,
    ) -> None:
        """整塊「日期 × 實體」的分數面板。留空的一格不入表。

        排名逐日橫斷面算(同分取較前那個名次),然後**只取有數的那幾格**——
        沒有分數的一格不會變成一個「排最尾」的假名次。
        """
        days = [_day(day) for day in dates]
        entities = np.asarray([int(entity) for entity in entity_ids], dtype=np.int64)
        matrix = np.asarray(values, dtype=float)
        matrix = np.where(np.isfinite(matrix), matrix, np.nan)

        frame = pd.DataFrame(matrix, index=days, columns=entities.tolist())
        ranks = frame.rank(
            axis=1, ascending=not higher_is_better, method="min"
        ).to_numpy(dtype=float)

        rows, columns = np.nonzero(np.isfinite(matrix))
        if rows.size == 0:
            return
        self._append_scores(
            [days[row] for row in rows.tolist()],
            entities[columns],
            score_name,
            matrix[rows, columns],
            ranks[rows, columns],
        )

    # ---- 收工 ----

    def _append_scores(
        self,
        days: Sequence[str],
        entities: np.ndarray,
        score_name: str,
        scores: np.ndarray,
        ranks: np.ndarray,
    ) -> None:
        name = str(score_name).strip()
        if not name:
            raise ContractViolation("分數要有名:一堆數字沒有名,畫面就講不出那一欄是什麼")
        self._score_rows.append(
            pd.DataFrame(
                {
                    "decision_date": list(days),
                    "entity_id": entities.astype(np.int64),
                    "score_name": name,
                    "score": scores.astype(float),
                    "rank": ranks.astype(np.int64),
                }
            )
        )

    def build(self) -> SelectionTrace | None:
        """砌好兩張表。一列都沒有即回 ``None``——沒有痕跡就不要交一份空的。"""
        if not self._stage_rows and not self._score_rows:
            return None
        candidates = pd.DataFrame(
            self._stage_rows, columns=list(CANDIDATE_COLUMNS)
        ).astype({"decision_date": "object", "stage": "object", "entity_id": "int64"})
        candidates = (
            candidates.drop_duplicates()
            .sort_values(list(CANDIDATE_COLUMNS))
            .reset_index(drop=True)
        )
        if self._score_rows:
            scores = pd.concat(self._score_rows, ignore_index=True)
        else:
            scores = pd.DataFrame(columns=list(SCORE_COLUMNS))
        scores = scores.astype(
            {
                "decision_date": "object",
                "entity_id": "int64",
                "score_name": "object",
                "score": "float64",
                "rank": "int64",
            }
        )
        scores = scores.sort_values(
            ["decision_date", "score_name", "rank", "entity_id"]
        ).reset_index(drop=True)
        return SelectionTrace(candidates=candidates, factor_scores=scores[list(SCORE_COLUMNS)])
