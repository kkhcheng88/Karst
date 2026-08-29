"""Alpha158 入庫:158 條各自登記因子版本,值落一個壓縮檔(KARST-064、068)。

算與寫是兩件事,兩件事住在兩個地方。``karst.factors.alpha158`` 只算不入庫
(它連 sqlite 都不認識);本檔負責把那張因子長表接上唯一入口——登記 158 個
因子版本、按 D-021 合約補齊三個時點、把 158 條的值拼成**一個批次檔**。
一列都不繞過 ``Gateway``:登記走 ``register_factor`` / ``new_factor_version``,
值走 ``write_factor_batch``,所以每個因子版本、每一列批次登記身上都有寫入者
簽章,``karst verify`` 掃得到(D-020 第 4 條)。

值住哪裡(D-032)
----------------

158 條的值**不逐行入 sqlite**,而是一個「數據快照 × 因子庫批次」一個 Parquet 檔
(``data/factors/<快照編號>/alpha158.parquet``),定義庫只留登記與內容雜湊。
KARST-064 逐行入表那次,555 萬個值把定義庫由 40 MB 撐到 1.6 GB——一個值本身
只需 8 字節,連三個 ISO 時點入表卻要近 300 字節。做法與運行的逐日序列、選股
痕跡一字不差,``karst verify`` 重讀檔案再算一次雜湊來核。

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
知道的一切」那種查詢(取值口 ``karst.factorvalues`` 的知情閘,亦即引擎的決策日閘)
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
``BETA``/``RSQR``/``RESI`` 那些常數段)因此在檔內根本沒有那一列,而不是有一列
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
from pathlib import Path
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

#: 因子庫批次名:158 條的值同住一個檔(D-032「一批一檔」)。檔名就是它,
#: 落點 ``data/factors/<快照編號>/alpha158.parquet``。
#:
#: 158 條分不分 158 個檔?不分。它們同一份輸入、同一套程序、同一次算完,
#: 拆開就是同一件事切成 158 份帳:158 個檔頭、158 列登記、讀十條因子開十個檔。
#: 一個檔內按因子版本排好,讀一條因子照樣只讀它那一段(parquet 逐段跳得過)。
ALPHA158_BATCH: Final[str] = "alpha158"

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
    batch_key: str
    batch_path: str
    content_hash: str
    file_bytes: int
    #: 逐個批次檔的落點(KARST-066 補:大宇宙分批寫,一個檔裝不下)。單一批次時
    #: 只有一項,與 ``batch_key``/``batch_path``/``content_hash``/``file_bytes``
    #: 那四格描述的是同一份;多過一項時,那四格改為彙總(見 ``__post_init__`` 呼叫處)。
    batches: tuple[dict[str, object], ...] = ()

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
            "batch_key": self.batch_key,
            "batch_path": self.batch_path,
            "content_hash": self.content_hash,
            "file_bytes": self.file_bytes,
            "batches": list(self.batches),
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
    gateway: "Gateway",
    *,
    snapshot_id: str,
    root: str | None = None,
    factor_root: str | None = None,
) -> IngestReport:
    """把一個價格快照上的 Alpha158 全部 158 條算出來並經唯一入口入庫。

    ``root`` 是快照快取根(留空即管線那個預設落點),``factor_root`` 是因子值
    批次檔的落點(留空即 ``data/factors``);``snapshot_id`` 是要算哪一份快照,
    沒有預設——「用哪一批數據」是呼叫方才答得出的事。
    """
    from ..data import read_calendar, read_price_frame
    from ..factorstore import BATCH_COLUMNS

    started = time.perf_counter()
    store = gateway.store
    bars = read_price_frame(store, snapshot_id, root=root)
    calendar = read_calendar(store, snapshot_id, root=root)
    if not calendar:
        raise ContractViolation(f"快照 {snapshot_id} 的日曆是空的,數不出可執行時點")

    next_bar = next_bar_by_date(calendar)
    # 三個時點逐日只砌一次:2,929 個日子砌三次,勝過 550 萬列各砌一次。
    # 兩個邊仍然由 ``as_timestamp`` 那份正本講(日子的開頭與結尾),這裡只是把
    # 它的答案收成時間戳——檔內存的是時間戳不是字串(見 ``karst.factorstore``)。
    event_at = {day: _stamp(as_timestamp(day, "event_time")) for day in calendar}
    knowledge_at = {
        day: _stamp(as_timestamp(day, "knowledge_time", end_of_day=True)) for day in calendar
    }
    executable_at = {
        day: (
            _stamp(as_timestamp(next_bar[day], "executable_time"))
            if day in next_bar
            else _NOT_EXECUTABLE
        )
        for day in calendar
    }

    # 逐個實體算一次寬表(日期 × 158 欄);Alpha158 全部是單一實體的時序運算,
    # 實體之間互不影響,所以逐個算完再按因子拼起來寫。
    wides: dict[int, pd.DataFrame] = {}
    for entity_id, group in bars.groupby("entity_id", sort=True):
        ordered = group.sort_values("date", kind="stable")
        wides[int(entity_id)] = compute_alpha158_for_entity(ordered)

    # 每個實體那條日子軸的三個時點各砌一條整列,之後 158 條因子逐條只是切片。
    stamps = {
        entity_id: (
            np.array([event_at[day] for day in wide.index], dtype=_STAMP),
            np.array([knowledge_at[day] for day in wide.index], dtype=_STAMP),
            np.array([executable_at[day] for day in wide.index], dtype=_STAMP),
        )
        for entity_id, wide in wides.items()
    }

    tally: dict[str, int] = {"registered": 0, "reused": 0, "new_version": 0}
    entity_count = len(wides)

    # 逐條先登記版本(要 factor_version_id 才切得出那條的值)。與拼值分開做,
    # 因為登記不吃記憶體,而拼值那步——大宇宙(標普 500)158 條 × 625 實體 ×
    # 幾千個交易日合共兩億幾千萬列,一次過拼一張表會撐爆記憶體(KARST-066 實測
    # 撞過一次:270,753,657 列要 6 GB 一條時間戳陣列,三條時間戳連值連編號
    # 遠遠不止)。做法是分批:每批算好幾條因子的值就拼、寫、放手,不留到最後
    # 158 條一次過拼。批多大由「這個宇宙大不大」決定,不是憑空一個常數——
    # 十二隻那個量級批出來剛好是原本的一整批(批次名不變,行為不變)。
    version_ids: list[int] = []
    for name in ALPHA158_NAMES:
        tally[_resolve_version(gateway, name, snapshot_id)] += 1
        version_ids.append(store.get_factor_version(factor_name(name)).factor_version_id)

    rows_upper_bound_per_factor = max(1, entity_count * len(calendar))
    chunk_size = max(1, min(len(ALPHA158_NAMES), _TARGET_ROWS_PER_CHUNK // rows_upper_bound_per_factor))
    chunks = [
        list(zip(ALPHA158_NAMES[i : i + chunk_size], version_ids[i : i + chunk_size]))
        for i in range(0, len(ALPHA158_NAMES), chunk_size)
    ]

    possible = 0
    written = 0
    not_executable = 0
    written_batches = []
    for index, chunk in enumerate(chunks):
        parts: dict[str, list[np.ndarray]] = {column: [] for column in BATCH_COLUMNS}
        for name, version_id in chunk:
            possible += _collect_factor(name, version_id, wides, stamps, parts)
        frame = pd.DataFrame({column: np.concatenate(parts[column]) for column in BATCH_COLUMNS})
        parts.clear()
        written += len(frame)
        not_executable += int(np.isnat(frame["executable_time"].to_numpy(_STAMP)).sum())

        batch_key = ALPHA158_BATCH if len(chunks) == 1 else f"{ALPHA158_BATCH}-{index:02d}"
        batch = gateway.write_factor_batch(
            frame,
            batch_key=batch_key,
            snapshot_id=snapshot_id,
            procedure_version=ALPHA158_PROCEDURE_VERSION,
            root=factor_root,
        )
        del frame
        written_batches.append(
            {
                "batch_key": batch.batch_key,
                "path": batch.path,
                "content_hash": batch.content_hash,
                "rows": batch.rows,
                "file_bytes": Path(batch.path).stat().st_size,
            }
        )

    wides.clear()
    stamps.clear()

    last_executable = next_bar.get(calendar[-1])
    first = written_batches[0]
    if len(written_batches) == 1:
        batch_key_out = first["batch_key"]
        batch_path_out = first["path"]
        content_hash_out = first["content_hash"]
    else:
        batch_key_out = f"{ALPHA158_BATCH}(分 {len(written_batches)} 檔)"
        batch_path_out = str(Path(first["path"]).parent)
        content_hash_out = "、".join(item["content_hash"][:12] for item in written_batches)
    file_bytes_out = sum(item["file_bytes"] for item in written_batches)

    return IngestReport(
        snapshot_id=str(snapshot_id),
        entity_count=entity_count,
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
        batch_key=batch_key_out,
        batch_path=batch_path_out,
        content_hash=content_hash_out,
        file_bytes=file_bytes_out,
        batches=tuple(written_batches),
    )


#: 檔內時點的型別:微秒時間戳(見 ``karst.factorstore``)。
_STAMP: Final[str] = "datetime64[us]"

#: 一批寫入的目標列數上限(KARST-066)。標普 500 這個量級(625 實體、約 2,900
#: 交易日)一條因子上限約 181 萬列,158 條一次過拼要兩億幾千萬列,一條時間戳
#: 陣列就要 6 GB——這個上限把單次拼表的記憶體壓在幾 GB 量級。小宇宙(十二隻)
#: 算出來的批量遠超過 158 條的總數,分母公式自然收斂回「一批就是全部」,批次名
#: 不變,行為與 KARST-064/068 那時一字不差。
_TARGET_ROWS_PER_CHUNK: Final[int] = 20_000_000

#: 沒有下一根可交易 K 線那一日:可執行時點留空(詞彙表「不可執行值」)。
_NOT_EXECUTABLE: Final[np.datetime64] = np.datetime64("NaT", "us")


def _stamp(text: str) -> np.datetime64:
    return np.datetime64(text, "us")


def _collect_factor(
    name: str,
    factor_version_id: int,
    wides: Mapping[int, pd.DataFrame],
    stamps: Mapping[int, tuple[np.ndarray, np.ndarray, np.ndarray]],
    parts: dict[str, list[np.ndarray]],
) -> int:
    """把一條因子在全部實體上的值切出來,append 落批次表那幾條欄。

    回的是「本來有幾多格」(實體 × 交易日),用來算缺值比例:寫入列數除不出這個
    分母,因為留空的格根本沒有那一列。
    """
    possible = 0
    for entity_id, wide in wides.items():
        column = wide[name].to_numpy("float64")
        possible += column.size
        keep = np.isfinite(column)
        kept = int(keep.sum())
        if kept == 0:
            continue
        event, knowledge, executable = stamps[entity_id]
        parts["factor_version_id"].append(np.full(kept, int(factor_version_id), "int32"))
        parts["entity_id"].append(np.full(kept, int(entity_id), "int32"))
        parts["event_time"].append(event[keep])
        parts["knowledge_time"].append(knowledge[keep])
        parts["executable_time"].append(executable[keep])
        parts["value"].append(column[keep])
    return possible
