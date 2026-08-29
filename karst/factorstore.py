"""因子值檔案庫:值住壓縮檔案,定義庫只留登記與雜湊(D-032;KARST-068)。

一個因子值批次 = 一個「數據快照 × 因子庫批次」的 Parquet 檔::

    <root>/<快照編號>/<因子庫批次>.parquet

檔內是一張長表,一列一個值,六格:因子版本編號、實體編號、事件時點、知情時點、
可執行時點、值。定義庫那邊只有兩列登記(``factor_value_batch`` 連
``factor_value_batch_member``):落點、內容雜湊、行數、產生程序版本,加上這個檔
載住哪幾個因子版本、各佔幾多列。

為什麼搬(D-032)
----------------

一個因子值本身只需 8 字節,但逐行入 sqlite 連三個 ISO 時點差不多要 300 字節。
Alpha158 十二隻十二年 555 萬列,就令定義庫由 40 MB 漲到 1.6 GB;標普 500 擴容
之後同一段窗口外推約 65 GB——備份、全庫核對、網頁殼讀取全部不可用。做法不是新
發明:運行的三條逐日序列、選股痕跡一直都是「大批數據住檔案、定義庫只登記編號
與雜湊」(D-026 第 1 條),本檔只是把因子值接上同一條路。

**D-021 的形狀一格都沒有改**:三個時點照舊逐個值帶住,缺值照舊是「沒有那一列」,
前視照舊在寫入那一刻擋(知情早過事件、可執行不在知情之後,一列都寫不入)。
變的只是承載體——由表變成檔。

時點在檔內是**真時間戳**(``datetime64[us]``),不是 ISO 字串:同一件事,兩種
寫法,分別只在型別。字串一列要 26 字節,時間戳 8 字節,而微秒精度剛好裝得下
知情時點那個 ``23:59:59.999999``——不是為省而省,是省得起而不失真。可執行時點
留空即 ``NaT``,意思與庫內留空一樣:知得到,成交不到(詞彙表「不可執行值」)。

不可覆蓋
--------

同一個批次名在同一個快照上只可以有一份值。原封不動重寫(內容雜湊一樣)當沿用,
一個字都不寫;內容不同即拒收——改了算法就是另一批值,請用另一個批次名。已經
引用過這批值的運行不應該有一日忽然指向一份它從未見過的內容。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from .batches import content_hash
from .errors import ContractViolation, ImmutabilityViolation, NotFound
from .models import as_timestamp
from .store import FACTOR_REF_SEPARATOR, DefinitionStore, FactorValueBatch, FactorVersion

#: 因子值批次檔的落腳處。與快照(``data/snapshots``)、運行(``data/runs``)並列。
DEFAULT_FACTOR_ROOT: Final[Path] = Path("data") / "factors"

#: 檔內的欄。名與 ``factor_value`` 表逐格同名同義——同一件事不應該有兩個講法。
BATCH_COLUMNS: Final[tuple[str, ...]] = (
    "factor_version_id",
    "entity_id",
    "event_time",
    "knowledge_time",
    "executable_time",
    "value",
)

#: 型別。整數收到 32 位(因子版本與實體編號都遠遠用不盡)、時點用微秒時間戳、
#: 值維持 64 位浮點——**值不減精度**:因子值是正本,存細一半就等於改了它。
BATCH_DTYPES: Final[dict[str, str]] = {
    "factor_version_id": "int32",
    "entity_id": "int32",
    "event_time": "datetime64[us]",
    "knowledge_time": "datetime64[us]",
    "executable_time": "datetime64[us]",
    "value": "float64",
}

#: 壓縮法。長表逐欄同質(一大段同一個因子版本、同一個實體),zstd 收得比預設好。
COMPRESSION: Final[str] = "zstd"

#: 唯一鍵:同一個因子版本、同一個實體、同一個事件時點、同一個知情時點只可以有
#: 一個值(與 ``factor_value`` 的主鍵一字不差)。
_KEY_COLUMNS: Final[tuple[str, ...]] = (
    "factor_version_id",
    "entity_id",
    "event_time",
    "knowledge_time",
)

# 全庫核對報得出的兩種不合格。內容由 ``check_files`` 講出來,包裝成 Finding 是
# 唯一入口那一層的事(本檔不認識 gateway,免得兜成一個圈)。
FILE_MISSING: Final[str] = "因子值檔不在登記的落點"
FILE_TAMPERED: Final[str] = "因子值檔落檔後被改動"


class FactorValueStore:
    """因子值檔案庫的門面:寫一批、讀回長表或寬表、核對檔案雜湊。

    ``store`` 是單一定義庫(登記住這裡),``root`` 是批次檔的根目錄。
    """

    def __init__(self, store: DefinitionStore, root: str | Path) -> None:
        self._store = store
        self._root = Path(root)

    @property
    def store(self) -> DefinitionStore:
        return self._store

    @property
    def root(self) -> Path:
        return self._root

    def path_for(self, *, batch_key: str, snapshot_id: str) -> Path:
        """一個批次檔的落點:``<root>/<快照編號>/<因子庫批次>.parquet``。"""
        return self._root / str(snapshot_id).strip() / f"{str(batch_key).strip()}.parquet"

    # ------------------------------------------------------------------
    # 寫入
    # ------------------------------------------------------------------

    def write_batch(
        self,
        frame: pd.DataFrame,
        *,
        batch_key: str,
        snapshot_id: str,
        procedure_version: str,
    ) -> FactorValueBatch:
        """把一批因子值寫成一個檔並登記,回傳那一列登記。

        合約在寫檔**之前**查完(前視、非有限數、重複的鍵),與逐值入表那條路
        同一套規矩:擋得住的一律在落檔之前擋,不會留下一個「寫了一半」的檔。

        原封不動重寫當沿用:檔在、內容雜湊一樣,就一個字都不寫,回原本那列登記。
        """
        normalised = normalise_batch(frame)
        digest = content_hash(normalised)
        path = self.path_for(batch_key=batch_key, snapshot_id=snapshot_id)

        if path.exists():
            existing = _read_file(path)
            if content_hash(existing) != digest:
                raise ImmutabilityViolation(
                    f"{path} 已經有一份內容不同的因子值批次;因子值批次不覆蓋——"
                    "改了算法就是另一批值,請用另一個批次名"
                )
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            normalised.to_parquet(
                path, engine="pyarrow", index=False, compression=COMPRESSION
            )

        members = {
            int(version_id): int(count)
            for version_id, count in normalised["factor_version_id"].value_counts().items()
        }
        return self._store.register_factor_value_batch(
            batch_key=batch_key,
            snapshot_id=snapshot_id,
            procedure_version=procedure_version,
            path=str(path),
            content_hash=digest,
            rows=int(len(normalised)),
            members=members,
        )

    # ------------------------------------------------------------------
    # 讀回:給定快照 × 因子版本 × 日期窗口
    # ------------------------------------------------------------------

    def read_long(
        self,
        names: Sequence[str],
        *,
        snapshot_id: str,
        as_of: date | datetime | str | None = None,
        start: date | datetime | str | None = None,
        end: date | datetime | str | None = None,
        entity_ids: Sequence[int] | None = None,
    ) -> pd.DataFrame:
        """長表:一列一個值,欄照 ``BATCH_COLUMNS``。

        ``names`` 逐個寫「因子名稱」或「因子名稱@版本號」(與策略引用因子同一種
        寫法);留空版本號即當下最新版。``snapshot_id`` 是要讀哪一份快照上那批值,
        **無預設**——同一個因子在兩份快照上是兩批不同的值。

        ``as_of`` 是知情時間閘(D-021:一切查詢以知情時間為閘),``start`` /
        ``end`` 是事件時點的窗口,``entity_ids`` 收窄到某幾隻。三者都留空即整批。

        查不到那個因子版本的批次登記即拋 ``NotFound``——不回一張空表頂替:
        「這個因子在這份快照上沒有算過」與「算過而一格都沒有值」是兩件事。
        """
        versions = [self.resolve(name) for name in names]
        if not versions:
            raise ContractViolation("要讀哪幾條因子:一條都沒有給")

        wanted = {version.factor_version_id: version for version in versions}
        by_path: dict[str, list[int]] = {}
        for version in versions:
            batches = self._store.factor_value_batches_for(
                version.factor_version_id, snapshot_id=snapshot_id
            )
            if not batches:
                raise NotFound(
                    f"因子「{version.name}」第 {version.version_no} 版在快照 "
                    f"{snapshot_id} 上沒有因子值批次的登記"
                )
            for batch in batches:
                by_path.setdefault(batch.path, []).append(version.factor_version_id)

        pieces = [
            _read_file(Path(path), factor_version_ids=ids) for path, ids in sorted(by_path.items())
        ]
        frame = (
            pd.concat(pieces, ignore_index=True)
            if len(pieces) > 1
            else pieces[0].reset_index(drop=True)
        )
        frame = frame[frame["factor_version_id"].isin(list(wanted))]
        frame = _apply_window(
            frame, as_of=as_of, start=start, end=end, entity_ids=entity_ids
        )
        return frame.sort_values(list(_KEY_COLUMNS)).reset_index(drop=True)

    # 寬面板(「日期 × 實體編號 → 值」)不在這裡(KARST-088,架構審視候選五):
    # 它要先揀「同一日同一隻取知情最遲那一個」,那是取值的挑法,不是讀檔。
    # 挑法只可以有一份實作,住在 ``karst.factorvalues.FactorValueReader.panel``。

    def resolve(self, name: str) -> FactorVersion:
        """把「因子名稱[@版本號]」解析成一個確定的因子版本(與策略引用同一種寫法)。"""
        text = str(name).strip()
        factor, _, version_text = text.partition(FACTOR_REF_SEPARATOR)
        version_no: int | None = None
        if version_text.strip():
            try:
                version_no = int(version_text)
            except ValueError as exc:
                raise ContractViolation(f"因子引用 {name!r} 的版本號不是數字") from exc
        return self._store.get_factor_version(factor, version_no)

    # ------------------------------------------------------------------
    # 核對
    # ------------------------------------------------------------------

    def check_files(self) -> list[tuple[FactorValueBatch, str, str]]:
        """重讀每一個登記在案的批次檔,再算一次雜湊。回空即全部對得上。

        回的是「(登記, 問題, 詳情)」三件,包裝成核對報告那一格是唯一入口的事。
        """
        problems: list[tuple[FactorValueBatch, str, str]] = []
        for batch in self._store.list_factor_value_batches():
            path = Path(batch.path)
            if not path.is_file():
                problems.append(
                    (batch, FILE_MISSING, f"登記寫住 {batch.path},但那裡沒有這份檔")
                )
                continue
            frame = _read_file(path)
            if len(frame) != batch.rows:
                problems.append(
                    (
                        batch,
                        FILE_TAMPERED,
                        f"檔內有 {len(frame)} 列,登記的是 {batch.rows} 列",
                    )
                )
                continue
            if content_hash(frame) != batch.content_hash:
                problems.append(
                    (
                        batch,
                        FILE_TAMPERED,
                        f"內容雜湊與登記時不符(登記於 {batch.written_at})",
                    )
                )
        return problems


# ----------------------------------------------------------------------
# 合約檢查與型別規範
# ----------------------------------------------------------------------


def normalise_batch(frame: pd.DataFrame) -> pd.DataFrame:
    """把一批因子值規範化成檔內那張長表,順手把合約查完。

    查的與逐值入表那條路一模一樣(``DefinitionStore.write_factor_values``):

    * 六格齊全,而且**除可執行時點以外一格都不可留空**;
    * 值必須是有限數(禁 NaN、禁 ±inf,D-021 第 10 條採納的三條紀律);
    * 知情時點不可早過事件時點(早過即前視);
    * 可執行時點留空,或者**嚴格晚於**知情時點(同日成交即前視);
    * 同一個因子版本 × 實體 × 事件時點 × 知情時點只可以有一個值。

    次序定死(按上述四格排)是為了雜湊:同一批值寫兩次要得同一個雜湊,否則
    「內容不同即拒收」那道閘會冤枉好人。
    """
    if not isinstance(frame, pd.DataFrame):
        raise ContractViolation(f"因子值批次要一張 pandas 表,收到 {type(frame).__name__}")
    missing = [column for column in BATCH_COLUMNS if column not in frame.columns]
    if missing:
        raise ContractViolation(f"因子值批次缺欄位:{'、'.join(missing)}")

    out = frame[list(BATCH_COLUMNS)].copy()
    for column, dtype in BATCH_DTYPES.items():
        if column.endswith("_time"):
            out[column] = _as_stamps(out[column], column).astype(dtype)
        else:
            out[column] = out[column].astype(dtype)

    for column in ("factor_version_id", "entity_id", "event_time", "knowledge_time"):
        if out[column].isna().any():
            raise ContractViolation(
                f"因子值批次的「{column}」有留空的格;缺值的格根本不應該有那一列"
            )
    values = out["value"].to_numpy("float64")
    if not np.isfinite(values).all():
        raise ContractViolation(
            "因子值批次有非有限數(NaN 或 ±inf);缺值不寫那一列,不寫 NaN、不寫 0"
        )

    lookahead = out["knowledge_time"] < out["event_time"]
    if lookahead.any():
        first = out[lookahead].iloc[0]
        raise ContractViolation(
            f"前視:知情時點 {first['knowledge_time']} 早過事件時點 {first['event_time']}"
            f"(因子版本 {int(first['factor_version_id'])}、實體 {int(first['entity_id'])});"
            f"共 {int(lookahead.sum())} 列"
        )
    executable = out["executable_time"]
    same_bar = executable.notna() & (executable <= out["knowledge_time"])
    if same_bar.any():
        first = out[same_bar].iloc[0]
        raise ContractViolation(
            f"前視:可執行時點 {first['executable_time']} 不在知情時點 "
            f"{first['knowledge_time']} 之後;可執行時點是知情之後下一根可交易 K 線的開市,"
            f"沒有下一根就留空。共 {int(same_bar.sum())} 列"
        )

    out = out.sort_values(list(_KEY_COLUMNS)).reset_index(drop=True)
    duplicated = out.duplicated(list(_KEY_COLUMNS))
    if duplicated.any():
        first = out[duplicated].iloc[0]
        raise ContractViolation(
            f"因子值批次有重複的值:因子版本 {int(first['factor_version_id'])}、"
            f"實體 {int(first['entity_id'])}、事件時點 {first['event_time']}、"
            f"知情時點 {first['knowledge_time']} 出現多過一次;共 {int(duplicated.sum())} 列"
        )
    return out


def _as_stamps(column: pd.Series, field: str) -> pd.Series:
    """一欄時點收成時間戳。收 ISO 字串(長短不一亦可)、``datetime`` 或已經是時間戳。

    寫 ``format="ISO8601"``:同一批值裡「日子開頭」寫成 ``…T00:00:00`` 而「日子
    結尾」帶足微秒,兩種長度撞在一欄,pandas 若果照第一列去猜格式就會當場報錯。
    """
    if pd.api.types.is_datetime64_any_dtype(column):
        return column
    try:
        return pd.to_datetime(column, format="ISO8601")
    except (ValueError, TypeError) as exc:
        raise ContractViolation(f"因子值批次的「{field}」不是有效時間戳:{exc}") from exc


def _read_file(path: Path, *, factor_version_ids: Sequence[int] | None = None) -> pd.DataFrame:
    """讀回一個批次檔,型別逐欄按 ``BATCH_DTYPES`` 收一次。

    收型別不是多此一舉:parquet 讀回來的時間戳精度由讀取方的版本決定,不收一次
    就會出現「同一份檔,今日算出這個雜湊、明日算出另一個」——核對就會冤枉好人。
    """
    filters: list[Any] | None = None
    if factor_version_ids is not None:
        filters = [("factor_version_id", "in", [int(v) for v in factor_version_ids])]
    frame = pd.read_parquet(path, engine="pyarrow", filters=filters)
    frame = frame[list(BATCH_COLUMNS)]
    for column, dtype in BATCH_DTYPES.items():
        if frame[column].dtype != dtype:
            frame[column] = frame[column].astype(dtype)
    return frame.reset_index(drop=True)


def _apply_window(
    frame: pd.DataFrame,
    *,
    as_of: date | datetime | str | None,
    start: date | datetime | str | None,
    end: date | datetime | str | None,
    entity_ids: Sequence[int] | None,
) -> pd.DataFrame:
    """知情時間閘 + 事件時點窗口 + 實體收窄。三者都留空即原樣回。"""
    out = frame
    if as_of is not None:
        gate = pd.Timestamp(as_timestamp(as_of, "as_of", end_of_day=True))
        out = out[out["knowledge_time"] <= gate]
    if start is not None:
        out = out[out["event_time"] >= pd.Timestamp(as_timestamp(start, "start"))]
    if end is not None:
        out = out[
            out["event_time"] <= pd.Timestamp(as_timestamp(end, "end", end_of_day=True))
        ]
    if entity_ids is not None:
        out = out[out["entity_id"].isin([int(e) for e in entity_ids])]
    return out


def batch_frame(pieces: Mapping[int, pd.DataFrame]) -> pd.DataFrame:
    """把「因子版本編號 → 那一條的值」拼成一張批次長表。

    每一份 ``pieces`` 只需要五格(實體、三個時點、值),因子版本編號由鍵補上——
    算的那一層不必逐條記住自己是庫內第幾個版本。
    """
    frames: list[pd.DataFrame] = []
    for version_id, piece in pieces.items():
        one = piece.copy()
        one["factor_version_id"] = np.full(len(one), int(version_id), "int32")
        frames.append(one)
    if not frames:
        raise ContractViolation("因子值批次是空的:一條因子的值都沒有")
    return pd.concat(frames, ignore_index=True)
