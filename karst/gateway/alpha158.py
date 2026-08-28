"""Alpha158 入庫:158 條各自登記因子版本,批量寫入因子值(KARST-064)。

算與寫是兩件事,兩件事住在兩個地方。``karst.factors.alpha158`` 只算不入庫
(它連 sqlite 都不認識);本檔負責把那張因子長表接上唯一入口——登記 158 個
因子版本、按 D-021 合約補齊三個時點、逐條因子批量寫 ``factor_value``。
一列都不繞過 ``Gateway``:登記走 ``register_factor`` / ``new_factor_version``,
值走 ``write_factor_values``,所以每個因子版本身上都有寫入者簽章,
``karst verify`` 掃得到(D-020 第 4 條)。

三個時點怎樣填(D-021 第 3 條)
------------------------------

日線因子的三個時點由**那根 K 線**決定,不由時鐘決定(合約明寫「綁 K 線不綁
時鐘」),所以本檔用的是日子的兩個邊,不是憑空編一個收市鐘點:

===========  ================================  =========================
時點          取值                              意思
===========  ================================  =========================
事件時點      那一根 K 線那日的**開頭**          這個值講的是哪一日的事
知情時點      同一日的**結尾**                   該日收工才算知道
可執行時點    下一根可交易 K 線那日的**開頭**    知情之後最早成交得到的一刻
===========  ================================  =========================

寫成 ``2015-01-02T00:00:00`` / ``2015-01-02T23:59:59.999999`` /
``2015-01-05T00:00:00``(``as_timestamp`` 的兩個邊)。這樣「截至某日收工為止
知道的一切」那種查詢(``latest_known_values`` 的知情閘,亦即引擎的決策日閘)
一問就中,而可執行時點必然嚴格晚於知情時點——同日成交寫不出來,前視在形狀上
就表達不到。

**下一根 K 線是哪一根,不在本檔決定**:交由 ``karst.engine.cadence`` 那份正本
(``rebalance_schedule(日曆, "daily")``)排出來。全倉只此一處數「下一根」,
本檔多寫一次就會變成同一件事的第二個講法。日曆最後那一日沒有下一根,排期本來
就會丟掉它——那一日的因子值照樣入庫,可執行時點留空:**值知得到,成交不到**。

窗口未滿與缺值
--------------

留空的格**不寫**(D-021 第 4 條:缺失=沒有那一列),亦**不回填**——不前值填補、
不後值補、不填零。滾動窗口未滿而算不出值的日子(``ROC60`` 頭 60 格、
``BETA``/``RSQR``/``RESI`` 那些常數段)因此在庫內根本沒有那一列,而不是有一列
借了後來的數。

橫斷面百分位
------------

**不入庫**。D-021 第 2 條講明百分位是**合成時**才轉的,庫存原值(第 7 條同理:
中性化是合成參數,庫存原值)。現行做法住在 ``karst.engine.funnel`` 的
``score_panel``:逐日橫斷面排名,只排有數那幾格,沒有分數的一格不會變成一個
「排最尾」的假名次。本檔寫入的正是它要的那些原值。
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
import pandas as pd

from ..errors import ContractViolation, NotFound
from ..factors import ALPHA158_APPROXIMATED, ALPHA158_NAMES, VWAP_APPROXIMATION
from ..factors.alpha158 import ALPHA158_EXPRESSIONS, compute_alpha158_for_entity
from ..models import FormulaProcedure, as_timestamp
from ..store import FAMILY_SEPARATOR

if TYPE_CHECKING:  # pragma: no cover - 只為型別註釋
    from .service import Gateway

#: 158 條共用的族名。族名只是分類,版本鏈與策略引用落在具體定義那一級
#: (CONTEXT.md「因子族」),所以庫內的名是「Alpha158·KMID」這個形狀。
ALPHA158_FAMILY: Final[str] = "Alpha158"

#: 產生程序版本(D-021 第 6、8 條)。追溯到批次 = 因子版本 × 數據快照 ×
#: **產生程序版本**,所以算這批值的那個模組是哪一版,要寫得出來。
#: 改動 ``karst.factors.alpha158`` 的算法就要推這個號,舊值照舊掛舊號。
ALPHA158_PROCEDURE_VERSION: Final[str] = "karst.factors.alpha158@1"

#: 公式出處:158 條表達式的正本在哪(KARST-063 以 pyqlib 0.9.7 官方檔案核實)。
ALPHA158_FORMULA_SOURCE: Final[str] = (
    "qlib 0.9.7 Alpha158DL.get_feature_config()"
    "(github.com/microsoft/qlib/blob/main/qlib/contrib/data/loader.py)"
)


def factor_name(name: str) -> str:
    """官方因子名 → 庫內的「族名·具體定義」全名。"""
    return f"{ALPHA158_FAMILY}{FAMILY_SEPARATOR}{name}"


def factor_description(name: str) -> str:
    """一句說明:公式出處、產生程序版本,近似的那一條連近似做法都寫明。"""
    line = f"Alpha158「{name}」;公式出處 {ALPHA158_FORMULA_SOURCE};產生程序 {ALPHA158_PROCEDURE_VERSION}"
    if name in ALPHA158_APPROXIMATED:
        line += (
            f";近似:日線來源沒有成交量加權平均價,$vwap 以典型價 {VWAP_APPROXIMATION} 代之"
        )
    return line


def factor_procedure(name: str, snapshot_id: str) -> FormulaProcedure:
    """產生程序:公式派——官方表達式原文 + 輸入數據版本(那個數據快照編號)。"""
    return FormulaProcedure(
        formula=ALPHA158_EXPRESSIONS[name],
        input_data_version=str(snapshot_id),
    )


@dataclass(frozen=True, slots=True)
class IngestReport:
    """一次 Alpha158 入庫的成果單。命令列與實驗摘要都由它一份數講出來。"""

    snapshot_id: str
    entity_count: int
    trading_days: int
    factor_count: int
    registered: int
    reused: int
    new_versions: int
    possible_rows: int
    written_rows: int
    missing_rows: int
    not_executable_rows: int
    first_event_date: str
    last_event_date: str
    last_executable_date: str | None
    seconds: float

    @property
    def missing_ratio(self) -> float:
        """缺值比例:算得出的格之中有幾多格留空(沒有那一列)。"""
        if self.possible_rows == 0:
            return 0.0
        return self.missing_rows / self.possible_rows

    def as_dict(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "entity_count": self.entity_count,
            "trading_days": self.trading_days,
            "factor_count": self.factor_count,
            "registered": self.registered,
            "reused": self.reused,
            "new_versions": self.new_versions,
            "possible_rows": self.possible_rows,
            "written_rows": self.written_rows,
            "missing_rows": self.missing_rows,
            "missing_ratio": self.missing_ratio,
            "not_executable_rows": self.not_executable_rows,
            "first_event_date": self.first_event_date,
            "last_event_date": self.last_event_date,
            "last_executable_date": self.last_executable_date,
            "seconds": self.seconds,
        }


def next_bar_by_date(calendar: tuple[str, ...]) -> dict[str, str]:
    """日曆 → 「這一日 → 下一根可交易 K 線那一日」。最後一日不在表內。

    排期交由 ``karst.engine.cadence`` 那份正本算(日度節奏 = 每一根都是決策日,
    每個決策日配它之後下一根)。本檔不自己數「下一根」,免得同一件事有兩個講法。
    """
    from ..engine.cadence import rebalance_schedule

    index = pd.DatetimeIndex(pd.to_datetime(list(calendar)))
    schedule = rebalance_schedule(index, "daily")
    return {
        decision.strftime("%Y-%m-%d"): execution.strftime("%Y-%m-%d")
        for decision, execution in schedule
    }


def _resolve_version(gateway: "Gateway", name: str, snapshot_id: str) -> str:
    """登記或沿用一個因子版本,回傳做過什麼:``registered`` / ``reused`` / ``new_version``。

    同名而產生程序一字不差(同公式、同輸入數據版本)即**沿用**,不無端出新版——
    因子版本編號是策略引用與運行蓋章的原料,多一版就令同一個定義有兩個身分。
    公式或輸入數據版本有一格不同就出新版(舊版一字不變,父版本自動接上),
    這正是庫內既有那幾條因子換快照時的做法。
    """
    full_name = factor_name(name)
    procedure = factor_procedure(name, snapshot_id)
    description = factor_description(name)
    try:
        head = gateway.store.get_factor_version(full_name)
    except NotFound:
        gateway.register_factor(
            full_name, scale_kind="cardinal", procedure=procedure, description=description
        )
        return "registered"

    same = (
        head.procedure.kind == "formula"
        and head.procedure.formula == procedure.formula
        and head.procedure.input_data_version == procedure.input_data_version
    )
    if same:
        return "reused"
    gateway.new_factor_version(
        full_name, scale_kind="cardinal", procedure=procedure, description=description
    )
    return "new_version"


def ingest_alpha158(
    gateway: "Gateway", *, snapshot_id: str, root: str | None = None
) -> IngestReport:
    """把一個價格快照上的 Alpha158 全部 158 條算出來並經唯一入口入庫。

    ``root`` 是快照快取根(留空即管線那個預設落點);``snapshot_id`` 是要算哪
    一份快照,沒有預設——「用哪一批數據」是呼叫方才答得出的事。
    """
    from ..data import read_calendar, read_price_frame

    started = time.perf_counter()
    store = gateway.store
    bars = read_price_frame(store, snapshot_id, root=root)
    calendar = read_calendar(store, snapshot_id, root=root)
    if not calendar:
        raise ContractViolation(f"快照 {snapshot_id} 的日曆是空的,數不出可執行時點")

    next_bar = next_bar_by_date(calendar)
    # 三個時點的字串逐日只砌一次:2,929 個日子砌三次,勝過 550 萬列各砌一次。
    event_at = {day: as_timestamp(day, "event_time") for day in calendar}
    knowledge_at = {day: as_timestamp(day, "knowledge_time", end_of_day=True) for day in calendar}
    executable_at: dict[str, str | None] = {
        day: (as_timestamp(next_bar[day], "executable_time") if day in next_bar else None)
        for day in calendar
    }

    # 逐個實體算一次寬表(日期 × 158 欄);Alpha158 全部是單一實體的時序運算,
    # 實體之間互不影響,所以逐個算完再按因子拼起來寫。
    wides: dict[int, pd.DataFrame] = {}
    for entity_id, group in bars.groupby("entity_id", sort=True):
        ordered = group.sort_values("date", kind="stable")
        wides[int(entity_id)] = compute_alpha158_for_entity(ordered)

    tally: dict[str, int] = {"registered": 0, "reused": 0, "new_version": 0}
    written = 0
    possible = 0
    not_executable = 0

    for name in ALPHA158_NAMES:
        tally[_resolve_version(gateway, name, snapshot_id)] += 1
        frame = _rows_for_factor(name, wides, event_at, knowledge_at, executable_at)
        possible += int(frame.attrs["possible"])
        not_executable += int(frame["executable_time"].isna().sum())
        written += gateway.write_factor_values(
            factor_name(name), frame, snapshot_id=snapshot_id
        )

    last_executable = next_bar.get(calendar[-1])
    return IngestReport(
        snapshot_id=str(snapshot_id),
        entity_count=len(wides),
        trading_days=len(calendar),
        factor_count=len(ALPHA158_NAMES),
        registered=tally["registered"],
        reused=tally["reused"],
        new_versions=tally["new_version"],
        possible_rows=possible,
        written_rows=written,
        missing_rows=possible - written,
        not_executable_rows=not_executable,
        first_event_date=calendar[0],
        last_event_date=calendar[-1],
        last_executable_date=last_executable,
        seconds=time.perf_counter() - started,
    )


def _rows_for_factor(
    name: str,
    wides: Mapping[int, pd.DataFrame],
    event_at: Mapping[str, str],
    knowledge_at: Mapping[str, str],
    executable_at: Mapping[str, str | None],
) -> pd.DataFrame:
    """一條因子在全部實體上的待寫列。留空的格不出現在結果裡。

    ``attrs["possible"]`` 是「本來有幾多格」(實體 × 交易日),用來算缺值比例:
    寫入列數除不出這個分母,因為留空的格根本沒有那一列。
    """
    pieces: list[pd.DataFrame] = []
    possible = 0
    for entity_id, wide in wides.items():
        column = wide[name].to_numpy("float64")
        possible += column.size
        keep = np.isfinite(column)
        if not keep.any():
            continue
        days = wide.index.to_numpy()[keep]
        pieces.append(
            pd.DataFrame(
                {
                    "entity_id": np.full(int(keep.sum()), entity_id, "int64"),
                    "event_time": [event_at[day] for day in days],
                    "knowledge_time": [knowledge_at[day] for day in days],
                    "executable_time": [executable_at[day] for day in days],
                    "value": column[keep],
                }
            )
        )

    if not pieces:
        frame = pd.DataFrame(
            {
                "entity_id": pd.Series(dtype="int64"),
                "event_time": pd.Series(dtype="object"),
                "knowledge_time": pd.Series(dtype="object"),
                "executable_time": pd.Series(dtype="object"),
                "value": pd.Series(dtype="float64"),
            }
        )
    else:
        frame = pd.concat(pieces, ignore_index=True)
    frame.attrs["possible"] = possible
    return frame
