"""按知情時點取最新已知因子值:定義庫的表與因子值批次兩邊一齊看(KARST-071)。

D-032 之後,因子值有兩個住處:

* **``factor_value`` 表**——小批人手登記的值(``factor write-values`` 那條路);
* **因子值批次**(Parquet)——大批算出來的值,一個「數據快照 × 因子庫批次」一檔,
  定義庫只留落點與內容雜湊(KARST-068)。

選股引擎原本只問前者,所以 Alpha158 遷出表之後就取不到數。本檔把「按知情時點取
最新已知值」這一路改為**同時涵蓋兩邊**,對外那個介面一格不變:同名同參數、同一組
欄位、同一套挑法。

挑法一字不改(D-021)
--------------------

* **知情時間為閘**(第 3 條):只看知情時點 ≤ 決策時點那一刻的值,之後才知道的
  一律看不見;成交仍然按值自己帶住的可執行時點,本檔一格都沒有碰它。
* **值永久有效直至被取代**(第 5 條):每個實體取事件時點最遲那一個值,同一個事件
  時點有多個知情時點就取知情最遲那個——與表那條 SQL 的排序一字不差。
* **缺失=不參與**(第 4 條):沒有值的實體不會出現在結果裡,不填補、不當零。

為什麼要有一層快取
------------------

引擎逐個決策日問一次(知情閘要逐日重定,不可以一次讀完自己截)。批次檔一問就開
一次,一次換倉問一次,季度換倉十二年就是四十七次開檔——同一份檔讀四十七次。
所以本檔的做法是:**一條因子只讀一次**(整段歷史連同三個時點),之後逐日的閘在
記憶體裡開。讀的次數變了,揀出來的值一個都沒有變。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

import pandas as pd

from ..errors import ContractViolation
from ..factorstore import DEFAULT_FACTOR_ROOT, FactorValueStore
from ..models import as_timestamp
from ..store import FACTOR_REF_SEPARATOR, DefinitionStore, FactorVersion

#: 交出去那張表的欄,與 ``DefinitionStore.latest_known_values`` 逐格同名同序——
#: 呼叫方換了取值的來路,不應該連欄位都要改。
VALUE_COLUMNS: tuple[str, ...] = (
    "entity_id",
    "event_time",
    "knowledge_time",
    "executable_time",
    "value",
    "snapshot_id",
    "factor_version_id",
)

_TIME_COLUMNS: tuple[str, ...] = ("event_time", "knowledge_time", "executable_time")

#: 一個值的身份:同一個實體、同一個事件時點、同一個知情時點只可以有一個值
#: (與 ``factor_value`` 的主鍵、批次檔的唯一鍵一字不差)。
_KEY_COLUMNS: tuple[str, ...] = ("entity_id", "event_time", "knowledge_time")

#: 時點交出去時的寫法,與 ``models.as_timestamp`` 一模一樣(可直接字串比較)。
_ISO_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%f"


class FactorValueSource:
    """一條因子的取值來源:表與批次合起來的那一份。

    ``store`` 是單一定義庫。批次檔的落點由庫內那份登記講出來(``path``),所以本類
    不需要另外知道檔放在哪。

    一個實例記住已經讀過的因子(連同實體收窄那一格),同一條因子問第二次不再開檔。
    引擎砌一張因子面板開一個實例即可——快取跟住那次計算生,那次計算完就散。
    """

    def __init__(self, store: DefinitionStore) -> None:
        self._store = store
        self._files = FactorValueStore(store, DEFAULT_FACTOR_ROOT)
        self._cache: dict[tuple[int, tuple[int, ...] | None], pd.DataFrame] = {}

    @property
    def store(self) -> DefinitionStore:
        return self._store

    def latest_known_values(
        self,
        name: str,
        as_of: date | datetime | str,
        *,
        version_no: int | None = None,
        entity_ids: Sequence[int] | None = None,
    ) -> pd.DataFrame:
        """每個實體取截至 ``as_of`` 最新已知的一個值。

        簽名與 ``DefinitionStore.latest_known_values`` 一字不差,分別只在:表裡沒有
        的值,會再去因子值批次裡找。

        ``as_of`` 傳純日期即當「該日收工為止」(引擎的決策日閘就是這樣傳)。
        """
        version = self._store.get_factor_version(name, version_no)
        wanted = None if entity_ids is None else tuple(sorted(int(e) for e in entity_ids))
        key = (version.factor_version_id, wanted)
        frame = self._cache.get(key)
        if frame is None:
            frame = self._load(version, wanted)
            self._cache[key] = frame

        gate = pd.Timestamp(as_timestamp(as_of, "as_of", end_of_day=True))
        gated = frame[frame["knowledge_time"] <= gate]
        if gated.empty:
            return _empty()
        # 排法照表那條 SQL:先按實體,再取事件時點最遲、同事件時點取知情最遲那一個。
        # ``mergesort`` 是穩定排序,同一批數跑一百次揀中的是同一列。
        ordered = gated.sort_values(
            list(_KEY_COLUMNS), ascending=[True, False, False], kind="mergesort"
        )
        latest = ordered.drop_duplicates("entity_id", keep="first")
        return _as_iso(latest)

    # ------------------------------------------------------------------

    def _load(self, version: FactorVersion, entity_ids: tuple[int, ...] | None) -> pd.DataFrame:
        """一條因子的整段歷史:表那邊加批次那邊,時點收成真時間戳好逐日開閘。"""
        pieces = [self._from_table(version, entity_ids), self._from_batches(version, entity_ids)]
        filled = [piece for piece in pieces if not piece.empty]
        if not filled:
            return _empty_stamped()
        if len(filled) == 1:
            return filled[0].reset_index(drop=True)
        combined = pd.concat(filled, ignore_index=True)
        return _one_value_per_key(combined, version)

    def _from_table(
        self, version: FactorVersion, entity_ids: tuple[int, ...] | None
    ) -> pd.DataFrame:
        """``factor_value`` 表那邊(小批人手登記的值)。"""
        frame = self._store.read_factor_values(
            version.name,
            version_no=version.version_no,
            entity_ids=None if entity_ids is None else list(entity_ids),
        )
        if frame.empty:
            return _empty_stamped()
        return _stamp(frame[list(VALUE_COLUMNS)].copy())

    def _from_batches(
        self, version: FactorVersion, entity_ids: tuple[int, ...] | None
    ) -> pd.DataFrame:
        """因子值批次那邊(Parquet)。一份快照一個檔,逐份讀回再拼。

        ``factor_value_batches_for`` 講得出這個因子版本住在哪幾個批次;一個批次都
        沒有就代表這條因子的值不在檔裡(例如玩具因子),回一張空表由表那邊補。
        """
        batches = self._store.factor_value_batches_for(version.factor_version_id)
        if not batches:
            return _empty_stamped()
        reference = f"{version.name}{FACTOR_REF_SEPARATOR}{version.version_no}"
        pieces: list[pd.DataFrame] = []
        for snapshot_id in sorted({batch.snapshot_id for batch in batches}):
            long = self._files.read_long(
                [reference],
                snapshot_id=snapshot_id,
                entity_ids=None if entity_ids is None else list(entity_ids),
            )
            if long.empty:
                continue
            piece = long.copy()
            piece["snapshot_id"] = snapshot_id
            pieces.append(piece[list(VALUE_COLUMNS)])
        if not pieces:
            return _empty_stamped()
        return pd.concat(pieces, ignore_index=True)


def latest_known_values(
    store: DefinitionStore,
    name: str,
    as_of: date | datetime | str,
    *,
    version_no: int | None = None,
    entity_ids: Sequence[int] | None = None,
) -> pd.DataFrame:
    """問一次就算數的寫法(不留快取)。逐日問一整段,請用 ``FactorValueSource``。"""
    return FactorValueSource(store).latest_known_values(
        name, as_of, version_no=version_no, entity_ids=entity_ids
    )


# ----------------------------------------------------------------------


def _one_value_per_key(frame: pd.DataFrame, version: FactorVersion) -> pd.DataFrame:
    """兩邊都有數時,同一個鍵只可以留一個值。

    同一個鍵(實體 × 事件時點 × 知情時點)在兩處各有一個**不同**的值,不是重複,
    是矛盾——同一個因子版本對同一日同一隻股票出了兩個數。當場講出來,不靜靜揀一個。
    """
    duplicated = frame.duplicated(list(_KEY_COLUMNS), keep=False)
    if duplicated.any():
        clash = frame[duplicated].groupby(list(_KEY_COLUMNS))["value"].nunique()
        if (clash > 1).any():
            entity, event_time, knowledge_time = clash[clash > 1].index[0]
            raise ContractViolation(
                f"因子「{version.name}」第 {version.version_no} 版對實體 {int(entity)}、"
                f"事件時點 {event_time}、知情時點 {knowledge_time} 有多過一個值:"
                "定義庫的表與因子值批次講法不一,請先對數"
            )
        frame = frame.drop_duplicates(list(_KEY_COLUMNS), keep="first")
    return frame.reset_index(drop=True)


def _stamp(frame: pd.DataFrame) -> pd.DataFrame:
    """表讀回來那幾格 ISO 字串收成真時間戳,好逐日比較。

    寫 ``format="ISO8601"``:同一欄可以「日子開頭」與帶足微秒兩種長度並存,照第一
    列去猜格式會當場報錯。
    """
    for column in _TIME_COLUMNS:
        frame[column] = pd.to_datetime(frame[column], format="ISO8601").astype("datetime64[us]")
    frame["entity_id"] = frame["entity_id"].astype("int64")
    frame["factor_version_id"] = frame["factor_version_id"].astype("int64")
    frame["value"] = frame["value"].astype("float64")
    return frame


def _as_iso(frame: pd.DataFrame) -> pd.DataFrame:
    """交出去之前,時點寫回 ISO 字串——與表那條路交出來的一模一樣。

    可執行時點留空即 ``None``(不可執行值,見詞彙表):知得到,成交不到。
    """
    out = frame[list(VALUE_COLUMNS)].copy()
    for column in _TIME_COLUMNS:
        stamps = out[column]
        out[column] = stamps.dt.strftime(_ISO_FORMAT).where(stamps.notna(), None)
    out["entity_id"] = out["entity_id"].astype("int64")
    out["factor_version_id"] = out["factor_version_id"].astype("int64")
    return out.sort_values("entity_id").reset_index(drop=True)


def _empty() -> pd.DataFrame:
    """一個實體都取不到值時交出去那張空表(欄位齊全,零列)。"""
    return pd.DataFrame(columns=list(VALUE_COLUMNS))


def _empty_stamped() -> pd.DataFrame:
    """內部用的空表:時點已經是時間戳,好與有數那幾份拼得起。"""
    frame = _empty()
    for column in _TIME_COLUMNS:
        frame[column] = frame[column].astype("datetime64[us]")
    return frame
