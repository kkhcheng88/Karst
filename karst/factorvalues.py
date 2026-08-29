"""因子取值口:「按知情時點取因子值」全平台只此一條路(KARST-088,架構審視候選五)。

以前這件事有三份實作,各有各的挑法:

* 定義庫 sqlite 那條(``DefinitionStore.latest_known_values`` / ``value_for``)——
  一句 SQL 視窗函數,只看 ``factor_value`` 表;
* 因子值批次那條(``FactorValueStore.read_long`` / ``read_panel``)——只看 Parquet;
* 引擎那份(``engine.factorvalues.FactorValueSource``)——把上面兩者合流。

三份各自實作知情時間閘與「最新一個值」的挑法,而生產上真的有兩處呼叫者各走一條:
引擎選股走合流那份、因子預測力直接走 Parquet 那條。同一個問題兩條路答,分岔了
不會有人發現——這正是本檔要收掉的那件事。

本檔之後:**知情時間閘、可執行時點、不可執行值的處理,全部只住在這裡**;
兩個住處(表與批次)收在介面之後,呼叫者分不出一個值來自哪一邊。

值的兩個住處(D-032)
--------------------

* **``factor_value`` 表**——小批人手登記的值(``factor write-values`` 那條路);
* **因子值批次**(Parquet)——大批算出來的值,一個「數據快照 × 因子庫批次」一檔,
  定義庫只留落點與內容雜湊(KARST-068)。

挑法一字不改(D-021)
--------------------

* **知情時間為閘**(第 3 條):只看知情時點 ≤ 決策時點那一刻的值,之後才知道的
  一律看不見;成交仍然按值自己帶住的可執行時點,本檔一格都沒有碰它。
* **值永久有效直至被取代**(第 5 條):每個實體取事件時點最遲那一個值,同一個事件
  時點有多個知情時點就取知情最遲那個。
* **缺失=不參與**(第 4 條):沒有值的實體不會出現在結果裡,不填補、不當零。
* **不可執行值**照原樣交出去:可執行時點留空即 ``None``,知得到、成交不到;
  要不要因此不算,是用值那一層的事(例如預測力對齊),本檔不代它決定。

指名快照與不指名(兩種問法,一個介面)
--------------------------------------

``snapshot_id`` 沒有預設值,呼叫方一定要答:

* **指名一份快照**——當「我要那一份批次上的值」。該因子版本在那份快照上沒有批次
  登記即拋 ``NotFound``:「這個因子在這份快照上沒有算過」與「算過而一格都沒有值」
  是兩件事,不可以用一張空表頂替。
* **傳 ``None``**——當「全部住處一齊看」。批次那邊逐份快照讀回再拼,一個批次都沒有
  就由表那邊補(例如玩具因子、小批人手值),兩邊都沒有才回空表。

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
from pathlib import Path

import numpy as np
import pandas as pd

from .errors import ContractViolation
from .factorstore import FactorValueStore
from .models import NOT_APPLICABLE, _NotApplicable, as_timestamp
from .store import FACTOR_REF_SEPARATOR, DefinitionStore, FactorVersion

#: 交出去那張長表的欄。前六格與 ``factorstore.BATCH_COLUMNS`` 同名同序(批次檔的
#: 形狀就是這個),尾多一格 ``snapshot_id`` 講出這個值來自哪一份快照——表那邊
#: 本來就逐列記住,批次那邊由登記補上。
VALUE_COLUMNS: tuple[str, ...] = (
    "factor_version_id",
    "entity_id",
    "event_time",
    "knowledge_time",
    "executable_time",
    "value",
    "snapshot_id",
)

#: 「最新已知值」交出去那張表的欄序。與已退役的 ``DefinitionStore.latest_known_values``
#: 逐格同名同序——呼叫方換了取值的來路,不應該連欄位都要改。
LATEST_COLUMNS: tuple[str, ...] = (
    "entity_id",
    "event_time",
    "knowledge_time",
    "executable_time",
    "value",
    "snapshot_id",
    "factor_version_id",
)

_TIME_COLUMNS: tuple[str, ...] = ("event_time", "knowledge_time", "executable_time")

#: 一個值的身份:同一個因子版本、同一個實體、同一個事件時點、同一個知情時點只可以
#: 有一個值(與 ``factor_value`` 的主鍵、批次檔的唯一鍵一字不差)。
_KEY_COLUMNS: tuple[str, ...] = (
    "factor_version_id",
    "entity_id",
    "event_time",
    "knowledge_time",
)

#: 一條因子之內揀「最新那一個」時的鍵(因子版本已經定死,不用再入鍵)。
_LATEST_KEY_COLUMNS: tuple[str, ...] = ("entity_id", "event_time", "knowledge_time")

#: 時點交出去時的寫法,與 ``models.as_timestamp`` 一模一樣(可直接字串比較)。
_ISO_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%f"

#: 表那邊讀回來的欄序(``DefinitionStore.read_factor_values`` 的原樣輸出)。
_TABLE_COLUMNS: tuple[str, ...] = (
    "entity_id",
    "event_time",
    "knowledge_time",
    "executable_time",
    "value",
    "snapshot_id",
    "factor_version_id",
)


class FactorValueReader:
    """按知情時點取因子值的唯一入口:表與批次兩個住處收在它之後。

    ``store`` 是單一定義庫(批次的落點由庫內那份登記講出來),``root`` 是批次檔的
    根目錄——**無預設值**:批次檔放在哪,是呼叫那一層答的事。

    逐日問那兩種(``latest_known`` / ``value_for``)一個實例記住已經讀過的因子(連同
    快照與實體收窄那兩格),同一條因子問第二次不再開檔——引擎逐個決策日問一次,
    靠的就是這一格。砌一張因子面板開一個實例即可:快取跟住那次計算生,那次計算完就散。
    """

    def __init__(self, store: DefinitionStore, root: str | Path) -> None:
        self._store = store
        self._files = FactorValueStore(store, root)
        self._cache: dict[
            tuple[int, str | None, tuple[int, ...] | None], pd.DataFrame
        ] = {}

    @property
    def store(self) -> DefinitionStore:
        return self._store

    @property
    def root(self) -> Path:
        return self._files.root

    # ------------------------------------------------------------------
    # 四種問法:一日一格(``latest_known``)、一日一個數(``value_for``)、
    #           整段長表(``history``)、整段寬面板(``panel``)
    # ------------------------------------------------------------------

    def latest_known(
        self,
        reference: str,
        as_of: date | datetime | str,
        *,
        snapshot_id: str | None,
        entity_ids: Sequence[int] | None,
    ) -> pd.DataFrame:
        """每個實體取截至 ``as_of`` **最新已知**的一個值(詞彙表「最新已知值」)。

        ``reference`` 寫「因子名稱」或「因子名稱@版本號」(與策略引用因子同一種
        寫法);留空版本號即當下最新版。``as_of`` 傳純日期即當「該日收工為止」
        (引擎的決策日閘就是這樣傳)。

        取不到值的實體不會出現在結果裡——那就是「不參與」,不填補、不當零。
        """
        version = self._files.resolve(reference)
        frame = self._load(version, snapshot_id, _wanted(entity_ids))

        gate = pd.Timestamp(as_timestamp(as_of, "as_of", end_of_day=True))
        gated = frame[frame["knowledge_time"] <= gate]
        if gated.empty:
            return _empty(LATEST_COLUMNS)
        # 事件時點最遲、同事件時點取知情最遲那一個。``mergesort`` 是穩定排序,
        # 同一批數跑一百次揀中的是同一列。
        ordered = gated.sort_values(
            list(_LATEST_KEY_COLUMNS), ascending=[True, False, False], kind="mergesort"
        )
        latest = ordered.drop_duplicates("entity_id", keep="first")
        return _as_iso(latest, LATEST_COLUMNS)

    def value_for(
        self,
        reference: str,
        entity_id: int,
        as_of: date | datetime | str,
        *,
        snapshot_id: str | None,
    ) -> float | _NotApplicable:
        """單點查詢:一隻股票、一條因子、一個知情時點,一個數。

        查不到即回 ``NOT_APPLICABLE``——是「不參與」,不是 0。兩者不可混為一談:
        真的是零與根本沒有那一列,對排名的意思完全不同(D-021 第 4 條)。
        """
        frame = self.latest_known(
            reference, as_of, snapshot_id=snapshot_id, entity_ids=[int(entity_id)]
        )
        if frame.empty:
            return NOT_APPLICABLE
        return float(frame.iloc[0]["value"])

    def history(
        self,
        references: Sequence[str],
        *,
        snapshot_id: str | None,
        as_of: date | datetime | str | None,
        start: date | datetime | str | None,
        end: date | datetime | str | None,
        entity_ids: Sequence[int] | None,
    ) -> pd.DataFrame:
        """整段長表:一列一個值,欄照 ``VALUE_COLUMNS``。

        給要看整段歷史那一類用途(因子預測力的對齊就是:它要每一個知情時點各自的
        橫斷面,不是某一日那張面板)。``as_of`` 是知情時間閘,``start`` / ``end``
        是事件時點的窗口,``entity_ids`` 收窄到某幾隻;四者都沒有預設值,不要就
        逐個傳 ``None``。

        時點在這裡是**時間戳**(不是 ISO 字串)——整段歷史是拿來算數的,不是拿來
        對字串的;``latest_known`` 那張面板才寫回字串。
        """
        versions = [self._files.resolve(reference) for reference in references]
        if not versions:
            raise ContractViolation("要讀哪幾條因子:一條都沒有給")

        frame, sorted_already = self._gather(versions, snapshot_id, _wanted(entity_ids))
        frame = _apply_window(frame, as_of=as_of, start=start, end=end)
        if not sorted_already:
            frame = frame.sort_values(list(_KEY_COLUMNS))
        return _in_order(frame).reset_index(drop=True)

    def panel(
        self,
        reference: str,
        *,
        snapshot_id: str | None,
        as_of: date | datetime | str | None,
        start: date | datetime | str | None,
        end: date | datetime | str | None,
        entity_ids: Sequence[int] | None,
    ) -> pd.DataFrame:
        """寬表:一條因子的「事件時點 × 實體編號 → 值」面板(D-021 第 1 條那張表)。

        索引是事件時點那一日,欄名是**實體編號**(不是交易代號——代號會被回收
        再發給別人,D-026 第 2 條)。缺值那一格是 ``NaN``,即該股該日不參與;
        **不填 0、不前值填補**——這裡的空白與長表裡「沒有那一列」是同一件事。

        同一日同一隻若有多個知情時點(值被更晚知道的新值取代,D-021 第 5 條),
        取知情最遲那一個——那正是「截至此刻所知」的意思。
        """
        long = self.history(
            [reference],
            snapshot_id=snapshot_id,
            as_of=as_of,
            start=start,
            end=end,
            entity_ids=entity_ids,
        )
        if long.empty:
            return pd.DataFrame(index=pd.DatetimeIndex([], name="event_time"))
        latest = long.sort_values("knowledge_time").drop_duplicates(
            ["entity_id", "event_time"], keep="last"
        )
        wide = latest.pivot(index="event_time", columns="entity_id", values="value")
        wide.columns = [int(column) for column in wide.columns]
        wide.columns.name = "entity_id"
        return wide.sort_index()

    # ------------------------------------------------------------------
    # 兩個住處合流
    # ------------------------------------------------------------------

    def _load(
        self,
        version: FactorVersion,
        snapshot_id: str | None,
        entity_ids: tuple[int, ...] | None,
    ) -> pd.DataFrame:
        """一條因子的整段歷史(留快取)。逐個決策日開閘就靠它:一條因子只讀一次。"""
        key = (version.factor_version_id, snapshot_id, entity_ids)
        cached = self._cache.get(key)
        if cached is None:
            cached, _ = self._gather([version], snapshot_id, entity_ids)
            self._cache[key] = cached
        return cached

    def _gather(
        self,
        versions: Sequence[FactorVersion],
        snapshot_id: str | None,
        entity_ids: tuple[int, ...] | None,
    ) -> tuple[pd.DataFrame, bool]:
        """兩個住處合流成一張長表;第二件回傳值講出它是否已經按 ``_KEY_COLUMNS`` 排好。

        表那邊排先(同一個鍵兩邊都有值而值相同時,留表那一列),與合流那份舊實作
        一樣。批次那邊**一份快照只開一次檔**,要幾多條因子一次過讀回來——158 條
        Alpha158 同住一個批次,逐條開一次就是同一份檔讀 158 次。
        """
        batch, ordered = self._from_batches(versions, snapshot_id, entity_ids)
        table = self._from_table(versions, snapshot_id, entity_ids)
        if table.empty:
            return batch, ordered
        if batch.empty:
            return table.reset_index(drop=True), False
        by_id = {version.factor_version_id: version for version in versions}
        return _one_value_per_key(pd.concat([table, batch], ignore_index=True), by_id), False

    def _from_table(
        self,
        versions: Sequence[FactorVersion],
        snapshot_id: str | None,
        entity_ids: tuple[int, ...] | None,
    ) -> pd.DataFrame:
        """``factor_value`` 表那邊(小批人手登記的值)。

        表逐列自己記住 ``snapshot_id``,所以指名快照即在這裡收窄——不是問庫要
        另一條查詢,是同一批列篩一次。
        """
        pieces: list[pd.DataFrame] = []
        for version in versions:
            frame = self._store.read_factor_values(
                version.name,
                version_no=version.version_no,
                entity_ids=None if entity_ids is None else list(entity_ids),
            )
            if frame.empty:
                continue
            if snapshot_id is not None:
                frame = frame[frame["snapshot_id"] == str(snapshot_id).strip()]
                if frame.empty:
                    continue
            pieces.append(_stamp(frame[list(_TABLE_COLUMNS)].copy()))
        if not pieces:
            return _empty_stamped(VALUE_COLUMNS)
        if len(pieces) == 1:
            return pieces[0]
        return pd.concat(pieces, ignore_index=True)

    def _from_batches(
        self,
        versions: Sequence[FactorVersion],
        snapshot_id: str | None,
        entity_ids: tuple[int, ...] | None,
    ) -> tuple[pd.DataFrame, bool]:
        """因子值批次那邊(Parquet)。一份快照開一次檔,多份就逐份讀回再拼。

        指名快照而該快照上沒有那條因子版本的批次登記,即拋 ``NotFound``(交由
        ``read_long`` 講那句話);不指名而一個批次都沒有,即當這條因子的值不在檔
        裡(例如玩具因子),回一張空表由表那邊補。
        """
        if snapshot_id is not None:
            return self._one_snapshot(versions, str(snapshot_id).strip(), entity_ids), True

        by_snapshot: dict[str, dict[int, FactorVersion]] = {}
        for version in versions:
            for batch in self._store.factor_value_batches_for(version.factor_version_id):
                by_snapshot.setdefault(batch.snapshot_id, {})[
                    version.factor_version_id
                ] = version
        if not by_snapshot:
            return _empty_stamped(VALUE_COLUMNS), True

        pieces = [
            self._one_snapshot(list(wanted.values()), snapshot, entity_ids)
            for snapshot, wanted in sorted(by_snapshot.items())
        ]
        filled = [piece for piece in pieces if not piece.empty]
        if not filled:
            return _empty_stamped(VALUE_COLUMNS), True
        if len(filled) == 1:
            return filled[0], True
        return pd.concat(filled, ignore_index=True), False

    def _one_snapshot(
        self,
        versions: Sequence[FactorVersion],
        snapshot_id: str,
        entity_ids: tuple[int, ...] | None,
    ) -> pd.DataFrame:
        """一份快照上那幾條因子的批次值,補回 ``snapshot_id`` 那一格。

        快照那一格寫成 categorical(一份檔一個值,逐列存一個 int8 碼而不是一個
        字串指標):一份快照的 Alpha158 是二億七千萬列,逐列存指標就是多兩 GB
        常駐記憶體,而那兩 GB 由頭到尾只講同一句話。
        """
        references = [
            f"{version.name}{FACTOR_REF_SEPARATOR}{version.version_no}" for version in versions
        ]
        long = self._files.read_long(
            references,
            snapshot_id=snapshot_id,
            entity_ids=None if entity_ids is None else list(entity_ids),
        )
        if long.empty:
            return _empty_stamped(VALUE_COLUMNS)
        long["snapshot_id"] = pd.Categorical.from_codes(
            np.zeros(len(long), dtype="int8"), categories=[snapshot_id]
        )
        return _in_order(long)


# ----------------------------------------------------------------------


def _in_order(frame: pd.DataFrame) -> pd.DataFrame:
    """欄序收成 ``VALUE_COLUMNS``;已經是那個次序就原樣交出去,不複製一份。

    不是慳那一兩行:一份快照的 Alpha158 是二億七千萬列,一次 ``frame[欄名]``
    就是整張表再抄一份(十一 GB)——抄的還要是一模一樣的東西。
    """
    if list(frame.columns) == list(VALUE_COLUMNS):
        return frame
    return frame[list(VALUE_COLUMNS)]


def _wanted(entity_ids: Sequence[int] | None) -> tuple[int, ...] | None:
    """實體收窄那一格收成一個定死次序的鍵,好做快取的鍵。"""
    return None if entity_ids is None else tuple(sorted(int(entity) for entity in entity_ids))


def _apply_window(
    frame: pd.DataFrame,
    *,
    as_of: date | datetime | str | None,
    start: date | datetime | str | None,
    end: date | datetime | str | None,
) -> pd.DataFrame:
    """知情時間閘 + 事件時點窗口。實體收窄在讀那一層做完(那樣讀得少)。"""
    out = frame
    if as_of is not None:
        out = out[out["knowledge_time"] <= pd.Timestamp(as_timestamp(as_of, "as_of", end_of_day=True))]
    if start is not None:
        out = out[out["event_time"] >= pd.Timestamp(as_timestamp(start, "start"))]
    if end is not None:
        out = out[out["event_time"] <= pd.Timestamp(as_timestamp(end, "end", end_of_day=True))]
    return out


def _one_value_per_key(
    frame: pd.DataFrame, versions: dict[int, FactorVersion]
) -> pd.DataFrame:
    """兩邊都有數時,同一個鍵只可以留一個值。

    同一個鍵(因子版本 × 實體 × 事件時點 × 知情時點)在兩處各有一個**不同**的值,
    不是重複,是矛盾——同一個因子版本對同一日同一隻股票出了兩個數。當場講出來,
    不靜靜揀一個。
    """
    duplicated = frame.duplicated(list(_KEY_COLUMNS), keep=False)
    if duplicated.any():
        clash = frame[duplicated].groupby(list(_KEY_COLUMNS))["value"].nunique()
        if (clash > 1).any():
            version_id, entity, event_time, knowledge_time = clash[clash > 1].index[0]
            version = versions[int(version_id)]
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
    return frame[list(VALUE_COLUMNS)]


def _as_iso(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """交出去之前,時點寫回 ISO 字串——與已退役的表那條路交出來的一模一樣。

    可執行時點留空的那一格讀回來是缺值標記(不可執行值,見詞彙表):知得到,
    成交不到——留空不等於缺值,值本身照樣在。
    """
    out = frame[list(columns)].copy()
    for column in _TIME_COLUMNS:
        stamps = out[column]
        out[column] = stamps.dt.strftime(_ISO_FORMAT).where(stamps.notna(), None)
    out["entity_id"] = out["entity_id"].astype("int64")
    out["factor_version_id"] = out["factor_version_id"].astype("int64")
    return out.sort_values("entity_id").reset_index(drop=True)


def _empty(columns: Sequence[str]) -> pd.DataFrame:
    """一個值都取不到時交出去那張空表(欄位齊全,零列)。"""
    return pd.DataFrame(columns=list(columns))


def _empty_stamped(columns: Sequence[str]) -> pd.DataFrame:
    """內部用的空表:時點已經是時間戳,好與有數那幾份拼得起。"""
    frame = _empty(columns)
    for column in _TIME_COLUMNS:
        frame[column] = frame[column].astype("datetime64[us]")
    return frame
