"""單一定義庫的 Python API。

一個 ``DefinitionStore`` 就是一個 sqlite 檔的門面:登記實體與代號、登記因子定義
與出新版、寫入與讀取因子值(讀取一律可按知情時間截止)、登記數據快照。

本層只管「寫得入、讀得回、改不得」;唯一入口(single gateway)的治理與命令列
在另一張票,故此處刻意不做權限與流程,只做合約檢查。
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Final

import pandas as pd

from . import schema
from .errors import (
    ContractViolation,
    DuplicateDefinition,
    ImmutabilityViolation,
    NotFound,
    TickerNotResolved,
)
from .models import (
    ENTITY_KINDS,
    NOT_APPLICABLE,
    SCALE_KINDS,
    Entity,
    FactorVersion,
    FormulaProcedure,
    MaterialProcedure,
    Procedure,
    Snapshot,
    TickerPeriod,
    _NotApplicable,
    as_date,
    as_finite_float,
    as_timestamp,
    open_ended,
)

# 因子名稱分隔符:「族名·具體定義」(CONTEXT.md 因子族)
FAMILY_SEPARATOR = "·"

_VALUE_COLUMNS = (
    "entity_id",
    "event_time",
    "knowledge_time",
    "executable_time",
    "value",
    "snapshot_id",
    "factor_version_id",
)


# 策略類型(strategy type):策略總覽頁的八類,一套策略只屬一個類型(KARST-015 原型)
STRATEGY_TYPES: Final[dict[str, str]] = {
    "fundamental": "基本面選股",
    "technical": "技術趨勢",
    "multifactor": "多因子",
    "event": "事件驅動",
    "meanrev": "均值回歸",
    "follow": "組合跟隨",
    "macro": "宏觀配置",
    "options": "期權策略",
}

# 換倉節奏(rebalance cadence)。**選單正本不在本檔**:它住在引擎合約
# (``karst.engine.contracts.CADENCES``),定義庫與引擎同取那一處(KARST-044)。
#
# 本檔以前另存一份日/月/季的清單,於是同一件事有兩個講法——引擎認得週度,定義庫
# 收不到,週度參數集登記不了(KARST-043 撞到)。兩份清單就是兩個真相,遲早各走各路。
#
# 本檔只補一件引擎不需要的東西:**給人看的中文名**。名不是選單:正本多一個節奏而
# 這裡漏了中文名,就用取值本身頂上,不會反過來令那個節奏收不到。
_CADENCE_LABELS: Final[dict[str, str]] = {
    "daily": "每日",
    "weekly": "每週",
    "monthly": "每月",
    "quarterly": "每季",
}


def rebalance_cadences() -> dict[str, str]:
    """換倉節奏選單:取值 → 中文名,由引擎那份正本推出來,本檔不另存一份。

    **不設預設值**(CONTEXT.md 換倉節奏;用戶反問「Why we need a default?」)——
    這是一張選單,不是一個預設值。

    正本要等到本函式被叫的那一刻才匯入:``karst.engine`` 反過來要匯入本檔,
    寫在檔頭會兜成一個圈。
    """
    from .engine.contracts import CADENCES

    return {
        cadence: _CADENCE_LABELS.get(cadence, cadence) for cadence in sorted(CADENCES)
    }


def __getattr__(name: str) -> Any:
    """``REBALANCE_CADENCES`` 是即場由正本推出來的,不是本檔另存的第二份清單。"""
    if name == "REBALANCE_CADENCES":
        return rebalance_cadences()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# 策略引用因子的寫法:「名稱」取最新版,「名稱@版本號」釘死某一版
FACTOR_REF_SEPARATOR = "@"

# 一次回測運行必須保存的三條序列(規格 7.4):逐日淨值、逐日持倉、逐筆交易。
# 三條缺一不可——缺了逐日序列,「檢視視窗」就只能靠重跑,那正是本票要廢掉的做法。
RUN_ARTIFACT_KINDS: Final[tuple[str, ...]] = ("equity", "holdings", "orders")

# 運行編號的字首。編號本身是內容雜湊,不帶日期——同一組輸入隔年再跑仍然同一個編號。
RUN_ID_PREFIX: Final[str] = "run-"
RUN_ID_HASH_LENGTH: Final[int] = 16

# 運行的來歷(run origin):這次運行是**正式運行**,還是參數掃描其中一格。
# 取值那一面是 schema.py 的 CHECK 約束(單一正本),這裡只給程式一個名字用。
#
# 分得出來歷,是因為庫身有一格記住它——不是因為誰的名字改得好(假設 A-006 的教訓:
# 靠參數集名前綴認掃描格,前綴一改,掃描格就會扮成一套策略的門面成績而且錯得無聲)。
FORMAL_RUN: Final[str] = "formal"
SWEEP_RUN: Final[str] = "sweep"
RUN_ORIGINS: Final[tuple[str, ...]] = (FORMAL_RUN, SWEEP_RUN)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class StrategyVersion:
    """一個策略定義的其中一版。落庫後不可改,只可出新版(D-021 第 9 條同制)。

    ``factors`` 是它引用的因子版本——引用只存編號,因子定義的正本仍然只有一份
    (D-002 第 4 條單一定義)。
    """

    strategy_version_id: int
    strategy_id: int
    name: str
    strategy_type: str
    version_no: int
    parent_version_id: int | None
    factors: tuple[FactorVersion, ...]
    description: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class ParamSet:
    """掛在一個策略版本上的一組參數:名稱→值,必帶換倉節奏,無預設值。"""

    param_set_id: int
    strategy_version_id: int
    name: str
    version_no: int
    parent_version_id: int | None
    rebalance_cadence: str
    values: dict[str, str]
    created_at: str


@dataclass(frozen=True, slots=True)
class RunArtifact:
    """一次運行其中一條序列的落點:parquet 在哪、內容雜湊是什麼、幾多列。

    ``kind`` 三選一:``equity`` 逐日淨值、``holdings`` 逐日持倉、``orders`` 逐筆交易。
    內容雜湊是「同一輸入得同一結果」的憑據——重錄時對不上即當改寫,拒收。
    """

    kind: str
    path: str
    content_hash: str
    rows: int


@dataclass(frozen=True, slots=True)
class RunRecord:
    """一次回測運行的留痕(規格 7.4)。

    運行編號(run id)由「策略版本 × 參數集 × 期間 × 數據快照 × 引擎版本」
    的內容雜湊而來:同一組輸入永遠得同一個編號,改任何一件即另一次運行。

    ``factors`` 是運行**當時**蓋住的因子版本(D-021 第 9 條)。因子或策略日後
    出新版,這裡一字不變——只是比對之下查得出它已經過時。

    ``origin`` 是來歷:``FORMAL_RUN`` 正式運行,``SWEEP_RUN`` 參數掃描其中一格
    (D-029:運行清單與策略總覽的門面成績只算正式運行)。``sweep_id`` 是掃描格
    所屬那次掃描的編號;正式運行一律 ``None``,掃描格只有第 8 版遷移之前那批舊列
    才會是 ``None``(當時庫內未有這一格,回填不出)。
    """

    run_id: str
    strategy_name: str
    strategy_type: str
    strategy_version_id: int
    strategy_version_no: int
    param_set_id: int
    param_set_name: str
    param_set_version_no: int
    rebalance_cadence: str
    param_values: dict[str, str]
    period_start: str
    period_end: str
    snapshot_id: str
    engine_name: str
    engine_version: str
    factors: tuple[FactorVersion, ...]
    trading_days: int
    artifacts: dict[str, RunArtifact]
    fingerprint: str
    origin: str
    sweep_id: str | None
    created_at: str

    @property
    def is_sweep_cell(self) -> bool:
        """這次運行是不是參數掃描其中一格。問庫身那一格,不看名字。"""
        return self.origin == SWEEP_RUN

    def artifact(self, kind: str) -> RunArtifact:
        try:
            return self.artifacts[kind]
        except KeyError as exc:
            raise NotFound(f"運行 {self.run_id} 沒有 {kind} 序列") from exc


@dataclass(frozen=True, slots=True)
class ActiveSetup:
    """現役設定(active setup):一套策略當下跟隨哪一個參數集(規格 7.5)。

    指的是**參數集的某一版**(``param_set_id``),不是參數集的名。名一樣但出了
    新版就是另一組取值——門面數字不可以因為誰出了新版而悄悄換口徑。

    ``seq_no`` 是這套策略的第幾次指定,由 1 起。舊指定一字不變、只加新的,
    故此換過什麼、由哪一刻起,全部查得回。
    """

    strategy_id: int
    strategy_name: str
    seq_no: int
    strategy_version_id: int
    strategy_version_no: int
    param_set_id: int
    param_set_name: str
    param_set_version_no: int
    rebalance_cadence: str
    note: str | None
    designated_at: str


@dataclass(frozen=True, slots=True)
class RiskRuleRecord:
    """共用風控層一條規則在庫內的登記列(D-013 第 4 條;KARST-025)。

    只有「這條規則是什麼」,**沒有取值**——取值屬用戶領域,住在該策略自己的
    參數集,由 ``param_key`` 那個名指過去(D-008 第 3 條)。
    """

    risk_rule_id: int
    key: str
    name: str
    param_key: str
    description: str
    created_at: str


@dataclass(frozen=True, slots=True)
class FactorValueBatchMember:
    """一個因子值批次檔內,某一個因子版本佔了幾多列(D-032;KARST-068)。"""

    factor_version_id: int
    rows: int


@dataclass(frozen=True, slots=True)
class FactorValueBatch:
    """一個因子值批次的登記列:值住 Parquet,庫內只有這一列(D-032;KARST-068)。

    ``batch_key`` 是因子庫批次的名(Alpha158 一整批就是一個),``snapshot_id`` 是
    這批值算自哪一份數據快照;兩者合起來就是那個檔。``procedure_version`` 是算它
    的那套程序是哪一版——追溯到批次要的三件(因子版本 × 數據快照 × 產生程序版本)
    在這一列上齊了兩件,第三件在 ``members``。

    ``content_hash`` 是檔案內容的雜湊,``karst verify`` 重讀檔案再算一次來對。
    """

    batch_key: str
    snapshot_id: str
    procedure_version: str
    path: str
    content_hash: str
    rows: int
    written_at: str
    members: tuple[FactorValueBatchMember, ...]

    @property
    def factor_version_ids(self) -> tuple[int, ...]:
        return tuple(member.factor_version_id for member in self.members)

    def rows_of(self, factor_version_id: int) -> int:
        """某一個因子版本在這個批次檔內佔幾多列;不在檔內即 0。"""
        for member in self.members:
            if member.factor_version_id == int(factor_version_id):
                return member.rows
        return 0


@dataclass(frozen=True, slots=True)
class SnapshotFetch:
    """一個數據快照的抓取登記:幾時抓、抓的是哪一段窗口、抓了幾多(KARST-034)。

    快照編號本身刻意不含抓取時間(同一批數據重抓要得同一個編號),所以
    「幾時抓的」住在這裡。同一個快照只有一列——重抓得回同一個編號時,
    沿用**第一次**凍結那刻的抓取時間,不會被後來那次改寫。

    ``alert_count`` / ``alert_summary`` 是凍結那一刻的**齊全度核對結果**
    (KARST-067):幾多條序列超出門檻、一句講得出是哪幾條。兩格同生共死,而且
    ``None`` 有它自己的意思——**沒有經過齊全度核對**(價格快照沒有主日曆可核,
    第 9 版之前的舊登記亦回填不出),不是「核對過、零警報」。要分得開這兩件事,
    因為「零警報」是一句話,「沒有人核對過」是另一句。
    """

    snapshot_id: str
    fetched_at: str
    window_start: str
    window_end: str
    entity_count: int
    row_count: int
    trading_days: int
    recorded_at: str
    alert_count: int | None
    alert_summary: str | None

    @property
    def window(self) -> str:
        return f"{self.window_start}~{self.window_end}"

    @property
    def audited(self) -> bool:
        """這份快照凍結時有沒有核對過齊全度。"""
        return self.alert_count is not None


@dataclass(frozen=True, slots=True)
class SnapshotRetraction:
    """一個快照的除名登記(KARST-084):它不再算可回測,但檔案與追溯照留。

    ``superseded_by`` 是取代它那個快照的編號;沒有取代者就留 ``None``——那是
    「除名了而且沒有替身」,與「被新一代取代」是兩件事,不可混為一談。
    """

    snapshot_id: str
    reason: str
    superseded_by: str | None
    retracted_by: str
    retracted_at: str


@dataclass(frozen=True, slots=True)
class SnapshotListing:
    """庫內一個數據快照的一覽列:快照登記那一列,連它的抓取登記(如有)。

    ``fetch`` 是 ``None`` 即這個快照不是經唯一入口凍的(例如直接呼叫管線的
    Python 程式)——那是「無此登記」,不是「資料缺失」。
    """

    snapshot_id: str
    source: str
    taken_on: str
    content_hash: str
    path: str | None
    universe: tuple[str, ...]
    created_at: str
    fetch: SnapshotFetch | None

    @property
    def fetched_at(self) -> str | None:
        return None if self.fetch is None else self.fetch.fetched_at

    @property
    def window(self) -> str | None:
        return None if self.fetch is None else self.fetch.window

    @property
    def entity_count(self) -> int:
        """這個快照凍了幾多個實體。

        沒有抓取登記時退回宇宙名單的長度——一個代號一個實體,名單連快照一併
        凍結(D-026 第 6 條),故數目對得上。
        """
        return len(self.universe) if self.fetch is None else self.fetch.entity_count

    @property
    def alert_count(self) -> int | None:
        """凍結時有幾多條序列超出齊全度門檻;``None`` = 沒有核對過(KARST-067)。"""
        return None if self.fetch is None else self.fetch.alert_count

    @property
    def alert_summary(self) -> str | None:
        """那次核對的一句摘要;``None`` = 沒有核對過(KARST-067)。"""
        return None if self.fetch is None else self.fetch.alert_summary


@dataclass(frozen=True, slots=True)
class DefinitionLocation:
    """一項定義的唯一落點(D-002 第 4 條:單一正本、無第二影像)。"""

    kind: str
    name: str
    table: str
    row_key: str
    version_count: int
    latest_version_no: int
    occurrences: tuple[str, ...]

    @property
    def has_second_image(self) -> bool:
        """名稱在庫內出現超過一處,即代表有第二份影像。"""
        return len(self.occurrences) > 1


SnapshotSigner = Callable[[str, Sequence[object]], None]
"""快照登記的簽章手:收「表名 + 主鍵」,替那一列蓋唯一入口的寫入者簽章。

實作住在 ``karst.gateway``——本層不認識鑰匙、不認識寫入者身分,只認識「有沒有人
在門口接手蓋章」這件事。
"""


class DefinitionStore:
    """單一定義庫。用 ``DefinitionStore.open(path)`` 開,支援 ``with`` 語法。

    **數據快照登記是唯一一種「本層自己拒收」的寫入**(KARST-087):
    ``register_snapshot`` 與 ``record_snapshot_fetch`` 要有簽章手才寫得入,而簽章手
    只有唯一入口(``karst.gateway.Gateway``)裝得上。其餘寫入照舊由 ``verify`` 事後
    揪繞過的列。分別在於:定義類的列繞過了還可以按版本鏈重登一次,快照登記繞過了
    就等於整條取數追溯鏈由源頭起無憑無據,而且那批 parquet 已經凍好搬不動了。
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._snapshot_signer: SnapshotSigner | None = None

    @classmethod
    def open(cls, path: str = ":memory:") -> "DefinitionStore":
        return cls(schema.connect(path))

    def attach_snapshot_signer(self, signer: SnapshotSigner) -> None:
        """裝上快照登記的簽章手。**只有唯一入口叫得動這一句**(``Gateway.__init__``)。

        裝上之後,經這個庫身凍出來的快照登記與抓取登記逐列有簽章;沒有裝上,那兩種
        登記一個字都寫不入(見 ``_require_snapshot_gate``)。凍結管線(價格線、宏觀線、
        重凍腳本)照舊收一個庫身、照舊呼叫同樣那兩句,分別只在**那個庫身是不是由那道門
        開出來的**——所以管線一句都不必改,而繞過那道門的凍結由此表達不出來。
        """
        self._snapshot_signer = signer

    def _require_snapshot_gate(self) -> SnapshotSigner:
        signer = self._snapshot_signer
        if signer is None:
            raise ContractViolation(
                "數據快照登記一律經唯一入口(karst.gateway.Gateway);"
                "直接用定義庫登記快照已不受理(KARST-087)。"
                "凍結請用 Gateway.take_snapshot / take_macro_snapshot,"
                "或者把 Gateway.open(...) 開出來那個 gateway.store 交給凍結管線"
            )
        return signer

    def _sign_snapshot_row(self, table: str, primary_key: Sequence[object]) -> None:
        """叫簽章手蓋章,然後核實真的蓋到。

        核實那一句不是多餘:簽章手是外面交來的,一個不做事的簽章手會令這一列靜靜落庫
        而無簽章——那正是本閘要擋的局面。核不到就當場拋錯,由外面那個 ``with self._conn``
        把剛寫的那一列一併回滾:寧可寫不入,不要寫入一列無憑無據的快照登記。
        """
        signer = self._require_snapshot_gate()
        signer(table, tuple(primary_key))
        key_text = "|".join(str(part) for part in primary_key)
        found = self._conn.execute(
            "SELECT 1 FROM gateway_write WHERE table_name = ? AND row_key = ?",
            (table, key_text),
        ).fetchone()
        if found is None:
            raise ContractViolation(
                f"{table}[{key_text}] 的簽章手沒有留下簽章,這一列不會落庫;"
                "唯一入口的簽章是快照登記的入場券,不是事後補的裝飾"
            )

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "DefinitionStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def connection(self) -> sqlite3.Connection:
        """底層連線。給唯一入口蓋簽章用;一般調用方不應該經此寫庫。"""
        return self._conn

    # ------------------------------------------------------------------
    # 實體(entity)與代號歷史映射
    # ------------------------------------------------------------------

    def register_entity(
        self,
        *,
        kind: str,
        display_name: str,
        cik: str | None = None,
        local_code: str | None = None,
    ) -> int:
        """登記一個可投資對象,回傳它的實體編號(entity id)。

        上市公司必須給 CIK(以它為錨,同一 CIK 重複登記回同一個編號);
        ETF 與籃子另編內部代碼,不給就自動編。
        """
        if kind not in ENTITY_KINDS:
            raise ContractViolation(f"實體種類只收 {sorted(ENTITY_KINDS)},收到 {kind!r}")
        if not display_name or not display_name.strip():
            raise ContractViolation("實體必須有名")

        if kind == "company":
            if not cik or not str(cik).strip():
                raise ContractViolation("上市公司必須以 SEC CIK 為錨,不可留空")
            if local_code:
                raise ContractViolation("上市公司以 CIK 為錨,不另編內部代碼")
            cik = str(cik).strip().zfill(10)
            existing = self._conn.execute(
                "SELECT entity_id, entity_kind FROM entity WHERE cik = ?", (cik,)
            ).fetchone()
        else:
            if cik:
                raise ContractViolation("ETF 與籃子不掛 CIK,另編內部代碼")
            local_code = (local_code or self._next_local_code(kind)).strip()
            existing = self._conn.execute(
                "SELECT entity_id, entity_kind FROM entity WHERE local_code = ?",
                (local_code,),
            ).fetchone()

        if existing is not None:
            if existing["entity_kind"] != kind:
                raise DuplicateDefinition(
                    f"這個錨已登記為 {existing['entity_kind']},不可再登記為 {kind}"
                )
            return int(existing["entity_id"])

        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO entity (entity_kind, display_name, cik, local_code, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (kind, display_name.strip(), cik, local_code, _now()),
            )
        return int(cursor.lastrowid)

    def _next_local_code(self, kind: str) -> str:
        prefix = kind.upper()
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM entity WHERE local_code LIKE ?", (f"{prefix}-%",)
        ).fetchone()
        return f"{prefix}-{int(row['n']) + 1:06d}"

    def get_entity(self, entity_id: int) -> Entity:
        row = self._conn.execute(
            "SELECT entity_id, entity_kind, display_name, cik, local_code "
            "FROM entity WHERE entity_id = ?",
            (int(entity_id),),
        ).fetchone()
        if row is None:
            raise NotFound(f"沒有實體編號 {entity_id}")
        return Entity(
            entity_id=int(row["entity_id"]),
            entity_kind=row["entity_kind"],
            display_name=row["display_name"],
            cik=row["cik"],
            local_code=row["local_code"],
        )

    def register_ticker(
        self,
        entity_id: int,
        ticker: str,
        valid_from: date | datetime | str,
        valid_to: date | datetime | str | None = None,
    ) -> TickerPeriod:
        """把一個交易代號掛在某實體的一段日子上(起訖含頭含尾)。

        代號會被回收再發給別人,所以同一代號的兩段日子**不准重疊**——
        重疊即當場拒收,這正是舊倉 GOLD 代號回收事故的防線。
        """
        entity_id = int(entity_id)
        self.get_entity(entity_id)  # 不存在即拋錯
        symbol = (ticker or "").strip().upper()
        if not symbol:
            raise ContractViolation("代號不可留空")

        start = as_date(valid_from, "valid_from")
        end = as_date(valid_to, "valid_to") if valid_to is not None else None
        if end is not None and end < start:
            raise ContractViolation(f"代號 {symbol} 的生效訖 {end} 早於生效起 {start}")

        clash = self._conn.execute(
            "SELECT entity_id, valid_from, valid_to FROM entity_ticker "
            "WHERE ticker = ? AND valid_from <= ? AND COALESCE(valid_to, ?) >= ?",
            (symbol, open_ended(end), open_ended(None), start),
        ).fetchone()
        if clash is not None:
            raise DuplicateDefinition(
                f"代號 {symbol} 在 {clash['valid_from']}~{clash['valid_to'] or '至今'} "
                f"已屬實體 {clash['entity_id']},日子不可重疊"
            )

        with self._conn:
            self._conn.execute(
                "INSERT INTO entity_ticker (entity_id, ticker, valid_from, valid_to) "
                "VALUES (?, ?, ?, ?)",
                (entity_id, symbol, start, end),
            )
        return TickerPeriod(entity_id=entity_id, ticker=symbol, valid_from=start, valid_to=end)

    def close_ticker(
        self,
        entity_id: int,
        ticker: str,
        valid_from: date | datetime | str,
        valid_to: date | datetime | str,
    ) -> None:
        """為一段仍然生效的代號補上生效訖(改代號、退市、被收購時用)。"""
        symbol = (ticker or "").strip().upper()
        start = as_date(valid_from, "valid_from")
        end = as_date(valid_to, "valid_to")
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE entity_ticker SET valid_to = ? "
                "WHERE entity_id = ? AND ticker = ? AND valid_from = ?",
                (end, int(entity_id), symbol, start),
            )
        if cursor.rowcount == 0:
            raise NotFound(f"沒有實體 {entity_id} 由 {start} 起持有 {symbol} 這一段")

    def resolve_ticker(self, ticker: str, on_date: date | datetime | str) -> int:
        """把「某日的某個代號」解析成實體編號。查不到即拋錯,不猜。"""
        symbol = (ticker or "").strip().upper()
        day = as_date(on_date, "on_date")
        row = self._conn.execute(
            "SELECT entity_id FROM entity_ticker "
            "WHERE ticker = ? AND valid_from <= ? AND COALESCE(valid_to, ?) >= ?",
            (symbol, day, open_ended(None), day),
        ).fetchone()
        if row is None:
            raise TickerNotResolved(f"{day} 沒有任何實體持有代號 {symbol}")
        return int(row["entity_id"])

    def ticker_history(self, ticker: str) -> list[TickerPeriod]:
        symbol = (ticker or "").strip().upper()
        rows = self._conn.execute(
            "SELECT entity_id, ticker, valid_from, valid_to FROM entity_ticker "
            "WHERE ticker = ? ORDER BY valid_from",
            (symbol,),
        ).fetchall()
        return [
            TickerPeriod(
                entity_id=int(r["entity_id"]),
                ticker=r["ticker"],
                valid_from=r["valid_from"],
                valid_to=r["valid_to"],
            )
            for r in rows
        ]

    def retract_ticker(self, ticker: str, *, entity_id: int, valid_from: str) -> None:
        """撤回一段**錨錯了**的代號映射(KARST-082)。

        這不是「改寫歷史」的後門,是更正錯配的唯一出路。代號→實體的錨一度取自
        SEC ``company_tickers.json``,那份檔只講代號**今日**屬誰;假設 A-011 崩塌之後
        查明有幾個代號被錨到今日的另一家公司(``BBBY`` 錨到 NEIGHBORHOOD INTELLIGENCE
        而不是 Bed Bath & Beyond)。錯配一日不撤,``resolve_ticker`` 一日仍然把價格
        解析到錯的實體,而且 ``register_ticker`` 的不准重疊那一關會擋住正確那一段寫不進去。

        撤的是**映射**,不是實體:舊實體留在庫內,舊快照仍然引用得到它的實體編號,
        一個字都不會變。查無此段即拋錯,不靜靜當作成功。
        """
        symbol = (ticker or "").strip().upper()
        start = as_date(valid_from, "valid_from")
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM entity_ticker "
                "WHERE entity_id = ? AND ticker = ? AND valid_from = ?",
                (int(entity_id), symbol, start),
            )
        if cursor.rowcount == 0:
            raise NotFound(f"沒有實體 {entity_id} 由 {start} 起持有 {symbol} 這一段,無從撤回")

    # ------------------------------------------------------------------
    # 因子定義與版本鏈
    # ------------------------------------------------------------------

    def register_factor(
        self,
        name: str,
        *,
        scale_kind: str | None = None,
        procedure: Procedure | None = None,
        description: str | None = None,
    ) -> FactorVersion:
        """登記一個新因子的第一版。名稱須寫成「族名·具體定義」。"""
        family, full_name = self._split_name(name)
        row = self._conn.execute(
            "SELECT factor_id FROM factor WHERE name = ?", (full_name,)
        ).fetchone()
        if row is not None:
            raise DuplicateDefinition(
                f"因子「{full_name}」已存在;要改定義請用 new_factor_version 出新版"
            )

        scale_kind = self._check_scale_kind(scale_kind, full_name)
        procedure = self._check_procedure(procedure, full_name)

        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO factor (name, family, created_at) VALUES (?, ?, ?)",
                (full_name, family, _now()),
            )
            factor_id = int(cursor.lastrowid)
            version_id = self._insert_version(
                factor_id=factor_id,
                version_no=1,
                parent_version_id=None,
                scale_kind=scale_kind,
                procedure=procedure,
                description=description,
            )
        return self._version_by_id(version_id)

    def new_factor_version(
        self,
        name: str,
        *,
        scale_kind: str | None = None,
        procedure: Procedure | None = None,
        description: str | None = None,
    ) -> FactorVersion:
        """為既有因子出新一版,父版本自動指向當前最新版(舊版一字不變)。"""
        _, full_name = self._split_name(name)
        head = self.get_factor_version(full_name)
        scale_kind = self._check_scale_kind(scale_kind, full_name)
        procedure = self._check_procedure(procedure, full_name)

        with self._conn:
            version_id = self._insert_version(
                factor_id=head.factor_id,
                version_no=head.version_no + 1,
                parent_version_id=head.factor_version_id,
                scale_kind=scale_kind,
                procedure=procedure,
                description=description,
            )
        return self._version_by_id(version_id)

    def get_factor_version(self, name: str, version_no: int | None = None) -> FactorVersion:
        """取某因子的某一版;``version_no`` 留空取最新版。"""
        _, full_name = self._split_name(name)
        if version_no is None:
            row = self._conn.execute(
                f"{_VERSION_SELECT} WHERE f.name = ? ORDER BY v.version_no DESC LIMIT 1",
                (full_name,),
            ).fetchone()
        else:
            row = self._conn.execute(
                f"{_VERSION_SELECT} WHERE f.name = ? AND v.version_no = ?",
                (full_name, int(version_no)),
            ).fetchone()
        if row is None:
            where = "最新版" if version_no is None else f"第 {version_no} 版"
            raise NotFound(f"沒有因子「{full_name}」的{where}")
        return _row_to_version(row)

    def factor_version_chain(self, name: str, version_no: int | None = None) -> list[FactorVersion]:
        """由指定版本逐級追回第一版,順序為新→舊。"""
        chain: list[FactorVersion] = []
        current: FactorVersion | None = self.get_factor_version(name, version_no)
        while current is not None:
            chain.append(current)
            parent_id = current.parent_version_id
            current = self._version_by_id(parent_id) if parent_id is not None else None
        return chain

    def _split_name(self, name: str) -> tuple[str, str]:
        full_name = (name or "").strip()
        if FAMILY_SEPARATOR not in full_name:
            raise ContractViolation(
                f"因子名稱要寫成「族名{FAMILY_SEPARATOR}具體定義」,收到 {name!r};"
                "族名只是分類,策略引用與版本鏈落在具體定義那一級"
            )
        family, _, specific = full_name.partition(FAMILY_SEPARATOR)
        if not family.strip() or not specific.strip():
            raise ContractViolation(f"因子名稱的族名與具體定義兩邊都不可留空:{name!r}")
        return family.strip(), full_name

    @staticmethod
    def _check_scale_kind(scale_kind: str | None, name: str) -> str:
        if not scale_kind:
            raise ContractViolation(
                f"因子「{name}」缺刻度型(scale kind):基數 cardinal / 序數 ordinal / 是非 boolean 揀一個"
            )
        if scale_kind not in SCALE_KINDS:
            raise ContractViolation(
                f"刻度型只收 {sorted(SCALE_KINDS)},收到 {scale_kind!r}"
            )
        return scale_kind

    @staticmethod
    def _check_procedure(procedure: Procedure | None, name: str) -> Procedure:
        if procedure is None:
            raise ContractViolation(
                f"因子「{name}」缺產生程序:公式派填公式+輸入數據版本,數值派填材料+判官版本"
            )
        if isinstance(procedure, FormulaProcedure):
            missing = [
                label
                for label, value in (("公式", procedure.formula), ("輸入數據版本", procedure.input_data_version))
                if not value or not str(value).strip()
            ]
        elif isinstance(procedure, MaterialProcedure):
            missing = [
                label
                for label, value in (("材料", procedure.material), ("判官版本", procedure.judge_version))
                if not value or not str(value).strip()
            ]
        else:
            raise ContractViolation(
                "產生程序只收 FormulaProcedure 或 MaterialProcedure,"
                f"收到 {type(procedure).__name__}"
            )
        if missing:
            raise ContractViolation(f"因子「{name}」的產生程序缺:{'、'.join(missing)}")
        return procedure

    def _insert_version(
        self,
        *,
        factor_id: int,
        version_no: int,
        parent_version_id: int | None,
        scale_kind: str,
        procedure: Procedure,
        description: str | None,
    ) -> int:
        if isinstance(procedure, FormulaProcedure):
            fields = (procedure.formula, procedure.input_data_version, None, None)
        else:
            fields = (None, None, procedure.material, procedure.judge_version)
        cursor = self._conn.execute(
            "INSERT INTO factor_version (factor_id, version_no, parent_version_id, scale_kind,"
            " procedure_kind, formula, input_data_version, material, judge_version,"
            " description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                factor_id,
                version_no,
                parent_version_id,
                scale_kind,
                procedure.kind,
                *fields,
                description,
                _now(),
            ),
        )
        return int(cursor.lastrowid)

    def _version_by_id(self, factor_version_id: int) -> FactorVersion:
        row = self._conn.execute(
            f"{_VERSION_SELECT} WHERE v.factor_version_id = ?", (int(factor_version_id),)
        ).fetchone()
        if row is None:
            raise NotFound(f"沒有因子版本 {factor_version_id}")
        return _row_to_version(row)

    # ------------------------------------------------------------------
    # 因子值:日期 × 實體 → 值,事件/知情雙時間戳連可執行時點
    # ------------------------------------------------------------------

    def write_factor_values(
        self,
        name: str,
        rows: Iterable[Mapping[str, Any]] | pd.DataFrame,
        *,
        version_no: int | None = None,
        snapshot_id: str | None = None,
    ) -> int:
        """寫入因子值。每列要有 entity_id、event_time、knowledge_time、
        executable_time、value 五格。

        缺失值**不要寫**——沒有那一列就是「該股該日不參與」(D-021 第 4 條);
        寫 0 或 NaN 一律當錯。知情時間早於事件時間即前視,當場拒收。

        ``executable_time`` 是可執行時點(D-021 第 3 條):知情時點之後**下一根
        可交易 K 線**的開市。它**必須給**,但**可以給 ``None``**——沒有下一根
        K 線(那個快照的日曆到此為止)時,值知得到而成交不到,那正是要記下來的
        事實。刻意不設預設值:一列因子值幾時才成交得到,只有寫入它的那個人答得出;
        這裡補一個出來就等於替它答了,而答錯的方向剛好就是前視。
        """
        version = self.get_factor_version(name, version_no)
        if isinstance(rows, pd.DataFrame):
            records: Sequence[Mapping[str, Any]] = rows.to_dict("records")
        else:
            records = list(rows)

        payload: list[tuple[Any, ...]] = []
        for index, record in enumerate(records):
            missing = [
                k
                for k in ("entity_id", "event_time", "knowledge_time", "executable_time", "value")
                if k not in record
            ]
            if missing:
                raise ContractViolation(f"第 {index} 列缺欄位:{'、'.join(missing)}")
            event_time = as_timestamp(record["event_time"], "event_time")
            knowledge_time = as_timestamp(record["knowledge_time"], "knowledge_time")
            if knowledge_time < event_time:
                raise ContractViolation(
                    f"第 {index} 列前視:知情時間 {knowledge_time} 早於事件時間 {event_time}"
                )
            raw_executable = record["executable_time"]
            if raw_executable is None or raw_executable != raw_executable:  # None 或 NaN
                executable_time = None
            else:
                executable_time = as_timestamp(raw_executable, "executable_time")
                if executable_time <= knowledge_time:
                    raise ContractViolation(
                        f"第 {index} 列前視:可執行時點 {executable_time} 不在知情時間 "
                        f"{knowledge_time} 之後;可執行時點是知情之後下一根可交易 K 線的開市"
                    )
            try:
                value = as_finite_float(record["value"], f"第 {index} 列的值")
            except ValueError as exc:
                raise ContractViolation(str(exc)) from exc
            payload.append(
                (
                    version.factor_version_id,
                    int(record["entity_id"]),
                    event_time,
                    knowledge_time,
                    value,
                    record.get("snapshot_id", snapshot_id),
                    executable_time,
                )
            )

        try:
            with self._conn:
                self._conn.executemany(
                    "INSERT INTO factor_value (factor_version_id, entity_id, event_time,"
                    " knowledge_time, value, snapshot_id, executable_time)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    payload,
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateDefinition(
                f"因子「{version.name}」第 {version.version_no} 版有值重複或實體/快照不存在:{exc}"
            ) from exc
        return len(payload)

    def read_factor_values(
        self,
        name: str,
        *,
        version_no: int | None = None,
        as_of: date | datetime | str | None = None,
        start: date | datetime | str | None = None,
        end: date | datetime | str | None = None,
        entity_ids: Sequence[int] | None = None,
    ) -> pd.DataFrame:
        """讀回因子值。``as_of`` 是知情時間閘:該時點之後才知道的值一律看不見。"""
        version = self.get_factor_version(name, version_no)
        sql = [
            "SELECT entity_id, event_time, knowledge_time, executable_time, value,"
            " snapshot_id, factor_version_id",
            "FROM factor_value WHERE factor_version_id = ?",
        ]
        params: list[Any] = [version.factor_version_id]
        if as_of is not None:
            sql.append("AND knowledge_time <= ?")
            params.append(as_timestamp(as_of, "as_of", end_of_day=True))
        if start is not None:
            sql.append("AND event_time >= ?")
            params.append(as_timestamp(start, "start"))
        if end is not None:
            sql.append("AND event_time <= ?")
            params.append(as_timestamp(end, "end", end_of_day=True))
        if entity_ids is not None:
            placeholders = ", ".join("?" for _ in entity_ids)
            sql.append(f"AND entity_id IN ({placeholders})")
            params.extend(int(e) for e in entity_ids)
        sql.append("ORDER BY event_time, entity_id, knowledge_time")
        return self._frame(" ".join(sql), params)

    def latest_known_values(
        self,
        name: str,
        as_of: date | datetime | str,
        *,
        version_no: int | None = None,
        entity_ids: Sequence[int] | None = None,
    ) -> pd.DataFrame:
        """每個實體取截至 ``as_of`` **最新已知**的一個值(D-021 第 5 條:值永久有效直至被取代)。

        沒有值的實體不會出現在結果裡——那就是「不參與」。
        """
        version = self.get_factor_version(name, version_no)
        params: list[Any] = [
            version.factor_version_id,
            as_timestamp(as_of, "as_of", end_of_day=True),
        ]
        entity_filter = ""
        if entity_ids is not None:
            placeholders = ", ".join("?" for _ in entity_ids)
            entity_filter = f"AND entity_id IN ({placeholders})"
            params.extend(int(e) for e in entity_ids)
        sql = f"""
            SELECT entity_id, event_time, knowledge_time, executable_time, value,
                   snapshot_id, factor_version_id
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY entity_id ORDER BY event_time DESC, knowledge_time DESC
                ) AS rank_in_entity
                FROM factor_value
                WHERE factor_version_id = ? AND knowledge_time <= ? {entity_filter}
            )
            WHERE rank_in_entity = 1
            ORDER BY entity_id
        """
        return self._frame(sql, params)

    def value_for(
        self,
        name: str,
        entity_id: int,
        as_of: date | datetime | str,
        *,
        version_no: int | None = None,
    ) -> float | _NotApplicable:
        """單點查詢。查不到即回 ``NOT_APPLICABLE``——是「不參與」,不是 0。"""
        frame = self.latest_known_values(
            name, as_of, version_no=version_no, entity_ids=[int(entity_id)]
        )
        if frame.empty:
            return NOT_APPLICABLE
        return float(frame.iloc[0]["value"])

    def _frame(self, sql: str, params: Sequence[Any]) -> pd.DataFrame:
        rows = self._conn.execute(sql, tuple(params)).fetchall()
        return pd.DataFrame(
            [tuple(row[c] for c in _VALUE_COLUMNS) for row in rows],
            columns=list(_VALUE_COLUMNS),
        )

    # ------------------------------------------------------------------
    # 因子值批次:值住 Parquet,庫內只留登記與雜湊(D-032;KARST-068)
    # ------------------------------------------------------------------

    def register_factor_value_batch(
        self,
        *,
        batch_key: str,
        snapshot_id: str,
        procedure_version: str,
        path: str,
        content_hash: str,
        rows: int,
        members: Mapping[int, int],
    ) -> FactorValueBatch:
        """登記一個因子值批次檔。**同一個名同一個快照,內容一樣即沿用,不再寫一次**。

        內容不一樣即當改寫,當場拒收:同一個批次名在同一個快照上只可以有一份值
        (單一定義,無第二影像)。改了算法就是另一批值,請用另一個批次名——沿用
        原名而覆蓋,會令已經引用過這批值的運行指向一份它從未見過的內容。

        ``members`` 是「因子版本編號 → 那個版本在檔內佔幾多列」;缺值的格根本沒有
        那一列,所以這個行數就是「有值那幾格」,缺值比例不用開檔就數得出。
        """
        key = str(batch_key).strip()
        snapshot = str(snapshot_id).strip()
        if not key or not snapshot:
            raise ContractViolation("因子值批次要有批次名與數據快照編號,兩者都不可留空")
        digest = str(content_hash).strip().lower()
        total = int(rows)
        counted = sum(int(count) for count in members.values())
        if counted != total:
            raise ContractViolation(
                f"因子值批次「{key}」逐個因子版本的行數加起來是 {counted},"
                f"與整份檔的 {total} 列對不上"
            )

        existing = self._factor_value_batch_row(key, snapshot)
        if existing is not None:
            if existing["content_hash"] != digest:
                raise ImmutabilityViolation(
                    f"因子值批次「{key}」在快照 {snapshot} 上已經登記過一份內容不同的檔"
                    f"(登記的雜湊 {existing['content_hash'][:12]},今次 {digest[:12]});"
                    "因子值批次不覆蓋——改了算法就是另一批值,請用另一個批次名"
                )
            return self.get_factor_value_batch(key, snapshot)

        with self._conn:
            self._conn.execute(
                "INSERT INTO factor_value_batch (batch_key, snapshot_id, procedure_version,"
                " path, content_hash, rows, written_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (key, snapshot, str(procedure_version).strip(), str(path), digest, total, _now()),
            )
            self._conn.executemany(
                "INSERT INTO factor_value_batch_member (batch_key, snapshot_id,"
                " factor_version_id, rows) VALUES (?, ?, ?, ?)",
                [
                    (key, snapshot, int(version_id), int(count))
                    for version_id, count in sorted(members.items())
                ],
            )
        return self.get_factor_value_batch(key, snapshot)

    def get_factor_value_batch(self, batch_key: str, snapshot_id: str) -> FactorValueBatch:
        """取一個因子值批次的登記(連檔內載住哪幾個因子版本)。"""
        key = str(batch_key).strip()
        snapshot = str(snapshot_id).strip()
        row = self._factor_value_batch_row(key, snapshot)
        if row is None:
            raise NotFound(f"沒有因子值批次「{key}」在快照 {snapshot} 上的登記")
        return self._factor_value_batch(row)

    def list_factor_value_batches(self) -> list[FactorValueBatch]:
        """庫內全部因子值批次,按批次名、快照排。"""
        rows = self._conn.execute(
            "SELECT * FROM factor_value_batch ORDER BY batch_key, snapshot_id"
        ).fetchall()
        return [self._factor_value_batch(row) for row in rows]

    def factor_value_batches_for(
        self, factor_version_id: int, *, snapshot_id: str | None = None
    ) -> list[FactorValueBatch]:
        """哪幾個批次檔載住這個因子版本;``snapshot_id`` 收窄到某一份快照。"""
        params: list[Any] = [int(factor_version_id)]
        clause = ""
        if snapshot_id is not None:
            clause = " AND m.snapshot_id = ?"
            params.append(str(snapshot_id).strip())
        rows = self._conn.execute(
            "SELECT b.* FROM factor_value_batch_member AS m"
            " JOIN factor_value_batch AS b"
            "   ON b.batch_key = m.batch_key AND b.snapshot_id = m.snapshot_id"
            f" WHERE m.factor_version_id = ?{clause}"
            " ORDER BY b.batch_key, b.snapshot_id",
            tuple(params),
        ).fetchall()
        return [self._factor_value_batch(row) for row in rows]

    def _factor_value_batch_row(self, batch_key: str, snapshot_id: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM factor_value_batch WHERE batch_key = ? AND snapshot_id = ?",
            (batch_key, snapshot_id),
        ).fetchone()

    def _factor_value_batch(self, row: sqlite3.Row) -> FactorValueBatch:
        members = self._conn.execute(
            "SELECT factor_version_id, rows FROM factor_value_batch_member"
            " WHERE batch_key = ? AND snapshot_id = ? ORDER BY factor_version_id",
            (row["batch_key"], row["snapshot_id"]),
        ).fetchall()
        return FactorValueBatch(
            batch_key=row["batch_key"],
            snapshot_id=row["snapshot_id"],
            procedure_version=row["procedure_version"],
            path=row["path"],
            content_hash=row["content_hash"],
            rows=int(row["rows"]),
            written_at=row["written_at"],
            members=tuple(
                FactorValueBatchMember(
                    factor_version_id=int(member["factor_version_id"]),
                    rows=int(member["rows"]),
                )
                for member in members
            ),
        )

    # ------------------------------------------------------------------
    # 數據快照登記
    # ------------------------------------------------------------------

    @staticmethod
    def snapshot_id_for(taken_on: date | datetime | str, content_hash: str) -> str:
        """快照編號的算法:日期 + 內容雜湊前 12 位。落庫前想先知編號時用。"""
        return f"{as_date(taken_on, 'taken_on')}-{str(content_hash).strip().lower()[:12]}"

    def register_snapshot(
        self,
        *,
        source: str,
        taken_on: date | datetime | str,
        content_hash: str,
        path: str | None = None,
        universe: Iterable[str] = (),
    ) -> str:
        """登記一次拉數。快照編號 = 日期 + 內容雜湊前 12 位(D-026 第 3 條)。

        同一來源、同一日、同一內容重覆登記回同一個編號(單一定義);
        內容不同即另一個編號,舊快照永不改動。

        **要有唯一入口的簽章手才寫得入**(KARST-087):落庫與蓋簽章同一次寫入落地,
        蓋不到章就一列都不寫。沿用舊編號那一次一個字都不寫,所以亦不蓋新簽章——
        庫內那一列若當初無簽章,它照舊無簽章,``verify`` 一掃仍然揪得到;沿用不會替
        繞過入口的舊列補一個簽章把痕跡蓋走(補簽另有一道命令,而且會留痕)。
        """
        self._require_snapshot_gate()
        if not source or not source.strip():
            raise ContractViolation("快照必須註明來源")
        if not content_hash or not str(content_hash).strip():
            raise ContractViolation("快照必須有內容雜湊,編號由日期+雜湊組成")
        day = as_date(taken_on, "taken_on")
        digest = str(content_hash).strip().lower()
        snapshot_id = f"{day}-{digest[:12]}"

        existing = self._conn.execute(
            "SELECT source, content_hash FROM data_snapshot WHERE snapshot_id = ?",
            (snapshot_id,),
        ).fetchone()
        if existing is not None:
            if existing["source"] != source.strip() or existing["content_hash"] != digest:
                raise DuplicateDefinition(
                    f"快照編號 {snapshot_id} 已屬另一批數據({existing['source']})"
                )
            return snapshot_id

        with self._conn:
            self._conn.execute(
                "INSERT INTO data_snapshot (snapshot_id, source, taken_on, content_hash, path,"
                " universe, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    snapshot_id,
                    source.strip(),
                    day,
                    digest,
                    path,
                    json.dumps(sorted(universe), ensure_ascii=False),
                    _now(),
                ),
            )
            self._sign_snapshot_row("data_snapshot", (snapshot_id,))
        return snapshot_id

    def get_snapshot(self, snapshot_id: str) -> Snapshot:
        row = self._conn.execute(
            "SELECT snapshot_id, source, taken_on, content_hash, path, universe, created_at "
            "FROM data_snapshot WHERE snapshot_id = ?",
            (snapshot_id,),
        ).fetchone()
        if row is None:
            raise NotFound(f"沒有數據快照 {snapshot_id}")
        return Snapshot(
            snapshot_id=row["snapshot_id"],
            source=row["source"],
            taken_on=row["taken_on"],
            content_hash=row["content_hash"],
            path=row["path"],
            universe=tuple(json.loads(row["universe"])),
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # 策略定義與版本鏈(KARST-022;版本制與因子同制,D-021 第 9 條)
    # ------------------------------------------------------------------

    def register_strategy(
        self,
        name: str,
        *,
        strategy_type: str | None = None,
        factor_refs: Sequence[str] | None = None,
        description: str | None = None,
    ) -> StrategyVersion:
        """登記一個新策略的第一版。類型與引用因子皆必填,缺就拒收。"""
        full_name = self._check_strategy_name(name)
        row = self._conn.execute(
            "SELECT strategy_id FROM strategy WHERE name = ?", (full_name,)
        ).fetchone()
        if row is not None:
            raise DuplicateDefinition(
                f"策略「{full_name}」已存在;要改定義請用 new_strategy_version 出新版"
            )
        kind = self._check_strategy_type(strategy_type, full_name)
        versions = self._resolve_factor_refs(factor_refs, full_name)

        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO strategy (name, strategy_type, created_at) VALUES (?, ?, ?)",
                (full_name, kind, _now()),
            )
            strategy_id = int(cursor.lastrowid)
            version_id = self._insert_strategy_version(
                strategy_id=strategy_id,
                version_no=1,
                parent_version_id=None,
                factor_version_ids=[v.factor_version_id for v in versions],
                description=description,
            )
        return self._strategy_version_by_id(version_id)

    def new_strategy_version(
        self,
        name: str,
        *,
        factor_refs: Sequence[str] | None = None,
        description: str | None = None,
    ) -> StrategyVersion:
        """為既有策略出新一版,父版本自動指向當前最新版(舊版一字不變)。

        類型不隨新版更改——改了類型就是另一套策略,請另立名稱。
        """
        full_name = self._check_strategy_name(name)
        head = self.get_strategy_version(full_name)
        versions = self._resolve_factor_refs(factor_refs, full_name)

        with self._conn:
            version_id = self._insert_strategy_version(
                strategy_id=head.strategy_id,
                version_no=head.version_no + 1,
                parent_version_id=head.strategy_version_id,
                factor_version_ids=[v.factor_version_id for v in versions],
                description=description,
            )
        return self._strategy_version_by_id(version_id)

    def get_strategy_version(self, name: str, version_no: int | None = None) -> StrategyVersion:
        """取某策略的某一版;``version_no`` 留空取最新版。"""
        full_name = (name or "").strip()
        if version_no is None:
            row = self._conn.execute(
                f"{_STRATEGY_SELECT} WHERE s.name = ? ORDER BY v.version_no DESC LIMIT 1",
                (full_name,),
            ).fetchone()
        else:
            row = self._conn.execute(
                f"{_STRATEGY_SELECT} WHERE s.name = ? AND v.version_no = ?",
                (full_name, int(version_no)),
            ).fetchone()
        if row is None:
            where = "最新版" if version_no is None else f"第 {version_no} 版"
            raise NotFound(f"沒有策略「{full_name}」的{where}")
        return self._strategy_version_by_id(int(row["strategy_version_id"]))

    def strategy_version_chain(
        self, name: str, version_no: int | None = None
    ) -> list[StrategyVersion]:
        """由指定版本逐級追回第一版,順序為新→舊。"""
        chain: list[StrategyVersion] = []
        current: StrategyVersion | None = self.get_strategy_version(name, version_no)
        while current is not None:
            chain.append(current)
            parent_id = current.parent_version_id
            current = self._strategy_version_by_id(parent_id) if parent_id is not None else None
        return chain

    @staticmethod
    def _check_strategy_name(name: str) -> str:
        full_name = (name or "").strip()
        if not full_name:
            raise ContractViolation("策略必須有名")
        return full_name

    @staticmethod
    def _check_strategy_type(strategy_type: str | None, name: str) -> str:
        if not strategy_type:
            raise ContractViolation(
                f"策略「{name}」缺類型(strategy type):"
                f"{'、'.join(f'{k}({v})' for k, v in STRATEGY_TYPES.items())} 揀一個"
            )
        if strategy_type not in STRATEGY_TYPES:
            raise ContractViolation(
                f"策略類型只收 {sorted(STRATEGY_TYPES)},收到 {strategy_type!r}"
            )
        return strategy_type

    def _resolve_factor_refs(
        self, factor_refs: Sequence[str] | None, name: str
    ) -> list[FactorVersion]:
        """把「因子名稱[@版本號]」逐個解析成一個確定的因子版本。

        留空版本號即釘死當下最新版——引用一定落在**具體定義 × 版本**那一級,
        不會浮動跟著因子出新版走(D-021 第 9 條:舊運行永不自動更新)。
        """
        refs = [str(r).strip() for r in (factor_refs or []) if str(r).strip()]
        if not refs:
            raise ContractViolation(
                f"策略「{name}」缺引用因子:最少引用一個因子,寫法「因子名稱」或「因子名稱"
                f"{FACTOR_REF_SEPARATOR}版本號」"
            )
        versions: list[FactorVersion] = []
        seen: set[int] = set()
        for ref in refs:
            factor_name, _, version_text = ref.partition(FACTOR_REF_SEPARATOR)
            version_no = None
            if version_text.strip():
                try:
                    version_no = int(version_text)
                except ValueError as exc:
                    raise ContractViolation(
                        f"因子引用 {ref!r} 的版本號不是數字"
                    ) from exc
            version = self.get_factor_version(factor_name, version_no)
            if version.factor_version_id in seen:
                raise ContractViolation(
                    f"策略「{name}」重複引用因子「{version.name}」第 {version.version_no} 版"
                )
            seen.add(version.factor_version_id)
            versions.append(version)
        return versions

    def _insert_strategy_version(
        self,
        *,
        strategy_id: int,
        version_no: int,
        parent_version_id: int | None,
        factor_version_ids: Sequence[int],
        description: str | None,
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO strategy_version (strategy_id, version_no, parent_version_id,"
            " description, created_at) VALUES (?, ?, ?, ?, ?)",
            (strategy_id, version_no, parent_version_id, description, _now()),
        )
        version_id = int(cursor.lastrowid)
        self._conn.executemany(
            "INSERT INTO strategy_factor_ref (strategy_version_id, factor_version_id) "
            "VALUES (?, ?)",
            [(version_id, int(fid)) for fid in factor_version_ids],
        )
        return version_id

    def _strategy_version_by_id(self, strategy_version_id: int) -> StrategyVersion:
        row = self._conn.execute(
            f"{_STRATEGY_SELECT} WHERE v.strategy_version_id = ?", (int(strategy_version_id),)
        ).fetchone()
        if row is None:
            raise NotFound(f"沒有策略版本 {strategy_version_id}")
        ref_rows = self._conn.execute(
            "SELECT factor_version_id FROM strategy_factor_ref WHERE strategy_version_id = ? "
            "ORDER BY factor_version_id",
            (int(strategy_version_id),),
        ).fetchall()
        return StrategyVersion(
            strategy_version_id=int(row["strategy_version_id"]),
            strategy_id=int(row["strategy_id"]),
            name=row["name"],
            strategy_type=row["strategy_type"],
            version_no=int(row["version_no"]),
            parent_version_id=(
                None if row["parent_version_id"] is None else int(row["parent_version_id"])
            ),
            factors=tuple(self._version_by_id(int(r["factor_version_id"])) for r in ref_rows),
            description=row["description"],
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # 參數集(param set):名稱→值,必帶換倉節奏,無預設值
    # ------------------------------------------------------------------

    def register_param_set(
        self,
        strategy_name: str,
        *,
        param_set_name: str,
        rebalance_cadence: str | None = None,
        values: Mapping[str, Any] | None = None,
        strategy_version_no: int | None = None,
    ) -> ParamSet:
        """為某策略版本登記一個參數集;同名再登記即出新版(舊版一字不變)。"""
        strategy = self.get_strategy_version(strategy_name, strategy_version_no)
        set_name = (param_set_name or "").strip()
        if not set_name:
            raise ContractViolation("參數集必須有名")
        cadence = self._check_cadence(rebalance_cadence, set_name)
        cleaned = self._check_param_values(values, set_name)

        head = self._conn.execute(
            "SELECT param_set_id, version_no FROM param_set "
            "WHERE strategy_version_id = ? AND name = ? ORDER BY version_no DESC LIMIT 1",
            (strategy.strategy_version_id, set_name),
        ).fetchone()
        if head is None:
            version_no, parent_id = 1, None
        else:
            version_no, parent_id = int(head["version_no"]) + 1, int(head["param_set_id"])

        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO param_set (strategy_version_id, name, version_no, parent_version_id,"
                " rebalance_cadence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    strategy.strategy_version_id,
                    set_name,
                    version_no,
                    parent_id,
                    cadence,
                    _now(),
                ),
            )
            param_set_id = int(cursor.lastrowid)
            self._conn.executemany(
                "INSERT INTO param_value (param_set_id, param_key, param_value) VALUES (?, ?, ?)",
                [(param_set_id, k, v) for k, v in cleaned.items()],
            )
        return self._param_set_by_id(param_set_id)

    def get_param_set(
        self,
        strategy_name: str,
        param_set_name: str,
        *,
        strategy_version_no: int | None = None,
        set_version_no: int | None = None,
    ) -> ParamSet:
        """取某策略版本的某個參數集;``set_version_no`` 留空取最新版。"""
        strategy = self.get_strategy_version(strategy_name, strategy_version_no)
        set_name = (param_set_name or "").strip()
        if set_version_no is None:
            row = self._conn.execute(
                "SELECT param_set_id FROM param_set WHERE strategy_version_id = ? AND name = ? "
                "ORDER BY version_no DESC LIMIT 1",
                (strategy.strategy_version_id, set_name),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT param_set_id FROM param_set "
                "WHERE strategy_version_id = ? AND name = ? AND version_no = ?",
                (strategy.strategy_version_id, set_name, int(set_version_no)),
            ).fetchone()
        if row is None:
            raise NotFound(
                f"策略「{strategy.name}」第 {strategy.version_no} 版沒有參數集「{set_name}」"
            )
        return self._param_set_by_id(int(row["param_set_id"]))

    def list_param_sets(
        self, strategy_name: str, *, strategy_version_no: int | None = None
    ) -> list[ParamSet]:
        """列出某策略版本的全部參數集(同名只取最新版)。"""
        strategy = self.get_strategy_version(strategy_name, strategy_version_no)
        rows = self._conn.execute(
            "SELECT param_set_id FROM param_set WHERE strategy_version_id = ? "
            "AND version_no = (SELECT MAX(version_no) FROM param_set AS inner_set "
            "                  WHERE inner_set.strategy_version_id = param_set.strategy_version_id"
            "                    AND inner_set.name = param_set.name) ORDER BY name",
            (strategy.strategy_version_id,),
        ).fetchall()
        return [self._param_set_by_id(int(r["param_set_id"])) for r in rows]

    @staticmethod
    def _check_cadence(rebalance_cadence: str | None, name: str) -> str:
        # 校驗取的是引擎那份正本,不是本檔另存的清單(KARST-044)
        roster = rebalance_cadences()
        if not rebalance_cadence:
            raise ContractViolation(
                f"參數集「{name}」缺換倉節奏(rebalance cadence):"
                f"{'、'.join(f'{k}({v})' for k, v in roster.items())} 揀一個;"
                "本平台不設預設值,缺就寫不入"
            )
        if rebalance_cadence not in roster:
            raise ContractViolation(
                f"換倉節奏只收 {sorted(roster)},收到 {rebalance_cadence!r}"
            )
        return rebalance_cadence

    @staticmethod
    def _check_param_values(values: Mapping[str, Any] | None, name: str) -> dict[str, str]:
        items = dict(values or {})
        if not items:
            raise ContractViolation(
                f"參數集「{name}」一個參數都沒有;參數無預設值,要用的一律寫明"
            )
        cleaned: dict[str, str] = {}
        for key, value in items.items():
            clean_key = str(key).strip()
            clean_value = "" if value is None else str(value).strip()
            if not clean_key:
                raise ContractViolation(f"參數集「{name}」有參數名留空")
            if not clean_value:
                raise ContractViolation(
                    f"參數集「{name}」的參數「{clean_key}」沒有值;無預設值,缺就拒收"
                )
            cleaned[clean_key] = clean_value
        return cleaned

    def _param_set_by_id(self, param_set_id: int) -> ParamSet:
        row = self._conn.execute(
            "SELECT param_set_id, strategy_version_id, name, version_no, parent_version_id,"
            " rebalance_cadence, created_at FROM param_set WHERE param_set_id = ?",
            (int(param_set_id),),
        ).fetchone()
        if row is None:
            raise NotFound(f"沒有參數集 {param_set_id}")
        value_rows = self._conn.execute(
            "SELECT param_key, param_value FROM param_value WHERE param_set_id = ? "
            "ORDER BY param_key",
            (int(param_set_id),),
        ).fetchall()
        return ParamSet(
            param_set_id=int(row["param_set_id"]),
            strategy_version_id=int(row["strategy_version_id"]),
            name=row["name"],
            version_no=int(row["version_no"]),
            parent_version_id=(
                None if row["parent_version_id"] is None else int(row["parent_version_id"])
            ),
            rebalance_cadence=row["rebalance_cadence"],
            values={r["param_key"]: r["param_value"] for r in value_rows},
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # 唯一落點(D-002 第 4 條:單一正本、無第二影像)
    # ------------------------------------------------------------------

    def locate_definition(self, kind: str, name: str) -> DefinitionLocation:
        """講出一項定義在庫內的唯一落點,並掃全庫看有沒有第二份影像。"""
        full_name = (name or "").strip()
        if kind == "factor":
            version = self.get_factor_version(full_name)
            table, row_key = "factor", f"factor_id={version.factor_id}"
            count_row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM factor_version WHERE factor_id = ?",
                (version.factor_id,),
            ).fetchone()
            latest = version.version_no
        elif kind == "strategy":
            strategy = self.get_strategy_version(full_name)
            table, row_key = "strategy", f"strategy_id={strategy.strategy_id}"
            count_row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM strategy_version WHERE strategy_id = ?",
                (strategy.strategy_id,),
            ).fetchone()
            latest = strategy.version_no
        else:
            raise ContractViolation(f"落點只查 factor 或 strategy,收到 {kind!r}")
        return DefinitionLocation(
            kind=kind,
            name=full_name,
            table=table,
            row_key=row_key,
            version_count=int(count_row["n"]),
            latest_version_no=latest,
            occurrences=tuple(self.find_name_occurrences(full_name)),
        )

    def find_name_occurrences(self, name: str) -> list[str]:
        """全庫掃描:這個名字一字不差地出現在哪些表的哪些欄。

        單一定義下答案應該只有一處(正本);引用它的表只存編號,不存名字。
        """
        target = (name or "").strip()
        occurrences: list[str] = []
        tables = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()
        for table_row in tables:
            table = table_row["name"]
            for column_row in self._conn.execute(f'PRAGMA table_info("{table}")').fetchall():
                column = column_row["name"]
                if "TEXT" not in str(column_row["type"] or "").upper():
                    continue
                hit = self._conn.execute(
                    f'SELECT COUNT(*) AS n FROM "{table}" WHERE "{column}" = ?', (target,)
                ).fetchone()
                if int(hit["n"]) > 0:
                    occurrences.append(f"{table}.{column}({hit['n']} 列)")
        return occurrences

    # ------------------------------------------------------------------
    # 回測運行留痕(規格 7.4、D-020 第 7 條;KARST-026)
    # ------------------------------------------------------------------

    def run_fingerprint(
        self,
        *,
        strategy_name: str,
        param_set_name: str,
        period_start: date | datetime | str,
        period_end: date | datetime | str,
        snapshot_id: str,
        engine_name: str,
        engine_version: str,
        strategy_version_no: int | None = None,
        param_set_version_no: int | None = None,
        factor_version_ids: Sequence[int] | None = None,
    ) -> str:
        """把一次運行的身份寫成一串**規範化文字**,運行編號就是它的雜湊。

        身份蓋齊五件:策略版本 × 參數集 × 期間 × 數據快照 × 引擎版本。寫的是
        **內容**(策略名+版本號、參數逐項的值、因子名@版本號)而不是庫內流水號,
        故此換一個庫重建同一組定義,算出來仍然是同一個運行編號。

        任何一件查不到即當場拋錯——身份不齊寧可沒有編號,不猜。
        """
        strategy = self.get_strategy_version(strategy_name, strategy_version_no)
        param_set = self.get_param_set(
            strategy.name,
            param_set_name,
            strategy_version_no=strategy.version_no,
            set_version_no=param_set_version_no,
        )
        snapshot = self.get_snapshot(str(snapshot_id or "").strip())

        start = as_date(period_start, "period_start")
        end = as_date(period_end, "period_end")
        if end < start:
            raise ContractViolation(f"回測期間的結束日 {end} 早於開始日 {start}")

        engine = str(engine_name or "").strip()
        version = str(engine_version or "").strip()
        if not engine or not version:
            raise ContractViolation(
                "回測運行必須註明引擎名稱與引擎版本;引擎換版即另一次運行,不可留空"
            )

        if factor_version_ids is None:
            factors = strategy.factors
        else:
            factors = tuple(self._version_by_id(int(fid)) for fid in factor_version_ids)
        if not factors:
            raise ContractViolation(
                f"策略「{strategy.name}」第 {strategy.version_no} 版沒有蓋住任何因子版本"
            )

        identity = {
            "engine": {"name": engine, "version": version},
            "factors": sorted(
                f"{f.name}{FACTOR_REF_SEPARATOR}{f.version_no}" for f in factors
            ),
            "param_set": {
                "name": param_set.name,
                "version_no": param_set.version_no,
                "rebalance_cadence": param_set.rebalance_cadence,
                "values": dict(sorted(param_set.values.items())),
            },
            "period": {"start": start, "end": end},
            "snapshot_id": snapshot.snapshot_id,
            "strategy": {
                "name": strategy.name,
                "type": strategy.strategy_type,
                "version_no": strategy.version_no,
            },
        }
        return json.dumps(identity, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def run_id_for(fingerprint: str) -> str:
        """由身份文字算出運行編號。落庫之前想先知編號時用。"""
        digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        return f"{RUN_ID_PREFIX}{digest[:RUN_ID_HASH_LENGTH]}"

    @staticmethod
    def check_run_origin(origin: str, sweep_id: str | None) -> tuple[str, str | None]:
        """核對一次運行的來歷,回傳規範化之後的 ``(來歷, 掃描編號)``。

        **無預設值**:講不出這次是正式運行還是掃描格,寧可寫不入(KARST-054)。
        掃描格必須連掃描編號——一格指不回它屬於哪一次掃描,參數掃描頁就併不回
        那次掃描;正式運行則必須留空,它本來就不屬於任何一次掃描。
        """
        value = str(origin or "").strip()
        if value not in RUN_ORIGINS:
            raise ContractViolation(
                f"運行來歷只收 {list(RUN_ORIGINS)},收到 {origin!r};"
                "一次運行是正式運行還是掃描格,落庫那一刻就要講得出,無預設值"
            )
        ident = str(sweep_id or "").strip() or None
        if value == FORMAL_RUN and ident is not None:
            raise ContractViolation(
                f"正式運行不屬於任何一次掃描,不可帶掃描編號(收到 {sweep_id!r})"
            )
        if value == SWEEP_RUN and ident is None:
            raise ContractViolation(
                "掃描格要寫明屬於哪一次掃描(掃描編號);沒有它,這一格指不回它那次掃描"
            )
        return value, ident

    def register_run(
        self,
        *,
        strategy_name: str,
        param_set_name: str,
        period_start: date | datetime | str,
        period_end: date | datetime | str,
        snapshot_id: str,
        engine_name: str,
        engine_version: str,
        artifacts: Sequence[RunArtifact],
        trading_days: int,
        origin: str,
        sweep_id: str | None = None,
        strategy_version_no: int | None = None,
        param_set_version_no: int | None = None,
        factor_version_ids: Sequence[int] | None = None,
    ) -> RunRecord:
        """登記一次回測運行,回傳它的留痕。

        同一組輸入重登記:三條序列的內容雜湊一模一樣即當**同一次運行**,原封不動
        回舊記錄(與快照登記同制);雜湊對不上即當改寫,拒收——運行不可變
        (D-020 第 7 條、規格 7.3)。序列本體不經此處,由 ``karst.runs`` 落 parquet。

        ``origin`` 無預設值(見 ``check_run_origin``):正式運行寫 ``FORMAL_RUN``,
        掃描格寫 ``SWEEP_RUN`` 連 ``sweep_id``。來歷**不入運行編號**——同一格參數
        無論由誰跑、屬於哪一次掃描,算出來仍然是同一個運行編號。
        """
        origin, sweep_id = self.check_run_origin(origin, sweep_id)
        fingerprint = self.run_fingerprint(
            strategy_name=strategy_name,
            param_set_name=param_set_name,
            period_start=period_start,
            period_end=period_end,
            snapshot_id=snapshot_id,
            engine_name=engine_name,
            engine_version=engine_version,
            strategy_version_no=strategy_version_no,
            param_set_version_no=param_set_version_no,
            factor_version_ids=factor_version_ids,
        )
        run_id = self.run_id_for(fingerprint)
        checked = self._check_run_artifacts(artifacts, run_id)

        days = int(trading_days)
        if days <= 0:
            raise ContractViolation(
                f"運行 {run_id} 的交易日數是 {days};沒有逐日序列的運行不成留痕"
            )

        existing = self._conn.execute(
            "SELECT run_id FROM backtest_run WHERE run_id = ?", (run_id,)
        ).fetchone()
        if existing is not None:
            # 已經留過痕就照舊回它:運行不可改,連來歷都是落庫那一刻那個
            # (同一格掃描第二次被掃到,讀回舊運行,不會改寫它屬於哪一次掃描)。
            self._assert_same_run(run_id, checked)
            return self.get_run(run_id)

        strategy = self.get_strategy_version(strategy_name, strategy_version_no)
        param_set = self.get_param_set(
            strategy.name,
            param_set_name,
            strategy_version_no=strategy.version_no,
            set_version_no=param_set_version_no,
        )
        if factor_version_ids is None:
            factor_ids = [f.factor_version_id for f in strategy.factors]
        else:
            factor_ids = [int(fid) for fid in factor_version_ids]

        with self._conn:
            self._conn.execute(
                "INSERT INTO backtest_run (run_id, strategy_version_id, param_set_id,"
                " period_start, period_end, snapshot_id, engine_name, engine_version,"
                " fingerprint, trading_days, origin, sweep_id, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    strategy.strategy_version_id,
                    param_set.param_set_id,
                    as_date(period_start, "period_start"),
                    as_date(period_end, "period_end"),
                    str(snapshot_id).strip(),
                    str(engine_name).strip(),
                    str(engine_version).strip(),
                    fingerprint,
                    days,
                    origin,
                    sweep_id,
                    _now(),
                ),
            )
            self._conn.executemany(
                "INSERT INTO run_artifact (run_id, kind, path, content_hash, rows)"
                " VALUES (?, ?, ?, ?, ?)",
                [
                    (run_id, a.kind, a.path, a.content_hash, a.rows)
                    for a in checked.values()
                ],
            )
            self._conn.executemany(
                "INSERT INTO run_factor_ref (run_id, factor_version_id) VALUES (?, ?)",
                [(run_id, fid) for fid in sorted(set(factor_ids))],
            )
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> RunRecord:
        """按運行編號取回一次運行的留痕。"""
        key = str(run_id or "").strip()
        row = self._conn.execute(
            "SELECT r.run_id, r.strategy_version_id, r.param_set_id, r.period_start,"
            " r.period_end, r.snapshot_id, r.engine_name, r.engine_version, r.fingerprint,"
            " r.trading_days, r.origin, r.sweep_id, r.created_at,"
            " s.name AS strategy_name, s.strategy_type,"
            " v.version_no AS strategy_version_no, p.name AS param_set_name,"
            " p.version_no AS param_set_version_no, p.rebalance_cadence"
            " FROM backtest_run AS r"
            " JOIN strategy_version AS v ON v.strategy_version_id = r.strategy_version_id"
            " JOIN strategy AS s ON s.strategy_id = v.strategy_id"
            " JOIN param_set AS p ON p.param_set_id = r.param_set_id"
            " WHERE r.run_id = ?",
            (key,),
        ).fetchone()
        if row is None:
            raise NotFound(f"沒有回測運行 {key}")

        artifact_rows = self._conn.execute(
            "SELECT kind, path, content_hash, rows FROM run_artifact WHERE run_id = ?"
            " ORDER BY kind",
            (key,),
        ).fetchall()
        factor_rows = self._conn.execute(
            "SELECT factor_version_id FROM run_factor_ref WHERE run_id = ?"
            " ORDER BY factor_version_id",
            (key,),
        ).fetchall()
        value_rows = self._conn.execute(
            "SELECT param_key, param_value FROM param_value WHERE param_set_id = ?"
            " ORDER BY param_key",
            (int(row["param_set_id"]),),
        ).fetchall()

        return RunRecord(
            run_id=row["run_id"],
            strategy_name=row["strategy_name"],
            strategy_type=row["strategy_type"],
            strategy_version_id=int(row["strategy_version_id"]),
            strategy_version_no=int(row["strategy_version_no"]),
            param_set_id=int(row["param_set_id"]),
            param_set_name=row["param_set_name"],
            param_set_version_no=int(row["param_set_version_no"]),
            rebalance_cadence=row["rebalance_cadence"],
            param_values={r["param_key"]: r["param_value"] for r in value_rows},
            period_start=row["period_start"],
            period_end=row["period_end"],
            snapshot_id=row["snapshot_id"],
            engine_name=row["engine_name"],
            engine_version=row["engine_version"],
            factors=tuple(
                self._version_by_id(int(r["factor_version_id"])) for r in factor_rows
            ),
            trading_days=int(row["trading_days"]),
            artifacts={
                r["kind"]: RunArtifact(
                    kind=r["kind"],
                    path=r["path"],
                    content_hash=r["content_hash"],
                    rows=int(r["rows"]),
                )
                for r in artifact_rows
            },
            fingerprint=row["fingerprint"],
            origin=row["origin"],
            sweep_id=row["sweep_id"],
            created_at=row["created_at"],
        )

    def list_runs(
        self,
        strategy_name: str | None = None,
        *,
        strategy_version_no: int | None = None,
        origin: str | None = None,
    ) -> list[RunRecord]:
        """列出歷次運行,由早到遲。留空策略名即全庫。

        「檢視運行」要切換到歷次任何一次(規格 8.5),這就是那張清單的來源。

        ``origin`` 收窄到某一種來歷:``FORMAL_RUN`` 只要正式運行(運行清單、策略
        總覽的門面成績、策略詳情頁的歷次運行表三處都是這個口徑,D-029),
        ``SWEEP_RUN`` 只要掃描格。留空即全部——連掃描格,庫內動輒幾千個。
        """
        if origin is not None:
            origin = str(origin).strip()
            if origin not in RUN_ORIGINS:
                raise ContractViolation(
                    f"運行來歷只收 {list(RUN_ORIGINS)},收到 {origin!r}"
                )
        clause = " AND r.origin = ?" if origin is not None else ""
        extra: tuple[object, ...] = (origin,) if origin is not None else ()

        if strategy_name is None:
            rows = self._conn.execute(
                f"SELECT r.run_id FROM backtest_run AS r WHERE 1 = 1{clause}"
                " ORDER BY r.created_at, r.run_id",
                extra,
            ).fetchall()
        elif strategy_version_no is None:
            rows = self._conn.execute(
                "SELECT r.run_id FROM backtest_run AS r"
                " JOIN strategy_version AS v ON v.strategy_version_id = r.strategy_version_id"
                " JOIN strategy AS s ON s.strategy_id = v.strategy_id"
                f" WHERE s.name = ?{clause} ORDER BY r.created_at, r.run_id",
                ((strategy_name or "").strip(), *extra),
            ).fetchall()
        else:
            strategy = self.get_strategy_version(strategy_name, strategy_version_no)
            rows = self._conn.execute(
                "SELECT r.run_id FROM backtest_run AS r"
                f" WHERE r.strategy_version_id = ?{clause}"
                " ORDER BY r.created_at, r.run_id",
                (strategy.strategy_version_id, *extra),
            ).fetchall()
        return [self.get_run(r["run_id"]) for r in rows]

    def count_runs(
        self, strategy_name: str | None = None, *, origin: str | None = None
    ) -> int:
        """數有幾多次運行,不砌留痕。

        「這套策略只跑過參數掃描」那句話要數得出幾多格,但砌四千份留痕再數一次
        是白做——那正是策略總覽開頁要等兩秒的原因。
        """
        if origin is not None:
            origin = str(origin).strip()
            if origin not in RUN_ORIGINS:
                raise ContractViolation(
                    f"運行來歷只收 {list(RUN_ORIGINS)},收到 {origin!r}"
                )
        clause = " AND r.origin = ?" if origin is not None else ""
        extra: tuple[object, ...] = (origin,) if origin is not None else ()
        if strategy_name is None:
            row = self._conn.execute(
                f"SELECT COUNT(*) AS n FROM backtest_run AS r WHERE 1 = 1{clause}",
                extra,
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM backtest_run AS r"
                " JOIN strategy_version AS v ON v.strategy_version_id = r.strategy_version_id"
                " JOIN strategy AS s ON s.strategy_id = v.strategy_id"
                f" WHERE s.name = ?{clause}",
                ((strategy_name or "").strip(), *extra),
            ).fetchone()
        return int(row["n"])

    def run_stale_reasons(self, run_id: str) -> tuple[str, ...]:
        """這次運行有沒有過時,過時在哪。沒有過時就回空。

        過時 = 它蓋住的版本已經不是**最新版**。舊運行內容一字不變、永不自動更新
        (D-021 第 9 條、規格 7.3);要看新版的成績,請跑新一次運行。

        註:比對的是最新版,不是「現役設定」——現役設定是用戶指定紙上交易跟隨的
        那一個參數集,由誰指定是另一回事(詞彙表「現役設定」)。
        """
        record = self.get_run(run_id)
        reasons: list[str] = []

        latest_strategy = self.get_strategy_version(record.strategy_name)
        if latest_strategy.version_no > record.strategy_version_no:
            reasons.append(
                f"策略「{record.strategy_name}」已出到第 {latest_strategy.version_no} 版,"
                f"本運行蓋住的是第 {record.strategy_version_no} 版"
            )

        latest_param_set = self.get_param_set(
            record.strategy_name,
            record.param_set_name,
            strategy_version_no=record.strategy_version_no,
        )
        if latest_param_set.version_no > record.param_set_version_no:
            reasons.append(
                f"參數集「{record.param_set_name}」已出到第 {latest_param_set.version_no} 版,"
                f"本運行蓋住的是第 {record.param_set_version_no} 版"
            )

        for factor in record.factors:
            latest_factor = self.get_factor_version(factor.name)
            if latest_factor.version_no > factor.version_no:
                reasons.append(
                    f"因子「{factor.name}」已出到第 {latest_factor.version_no} 版,"
                    f"本運行蓋住的是第 {factor.version_no} 版"
                )
        return tuple(reasons)

    def run_is_stale(self, run_id: str) -> bool:
        """這次運行是否已經過時(蓋住的版本不再是最新版)。"""
        return bool(self.run_stale_reasons(run_id))

    # ------------------------------------------------------------------
    # 現役設定(規格 7.5、CONTEXT.md「現役設定」;KARST-030)
    # ------------------------------------------------------------------

    def set_active_setup(
        self,
        strategy_name: str,
        param_set_name: str,
        *,
        strategy_version_no: int | None = None,
        param_set_version_no: int | None = None,
        note: str | None = None,
    ) -> ActiveSetup:
        """指定一套策略的現役設定,回傳這一次指定。

        換一個現役設定 = **加一筆新指定**,舊指定一字不變(與運行不可改同制)。
        指同一個參數集版本兩次即當同一件事,原封不動回上一筆,不會白加一列。

        現役設定是**門面數字的來源**:換了它,策略卡與運行詳情那八個數字隨之
        換成新設定那次運行的數(規格 7.5)。
        """
        strategy = self.get_strategy_version(strategy_name, strategy_version_no)
        param_set = self.get_param_set(
            strategy.name,
            param_set_name,
            strategy_version_no=strategy.version_no,
            set_version_no=param_set_version_no,
        )

        current = self._active_setup_row(strategy.strategy_id)
        if current is not None and int(current["param_set_id"]) == param_set.param_set_id:
            return self._active_setup(strategy, param_set, current)

        seq_no = 1 if current is None else int(current["seq_no"]) + 1
        with self._conn:
            self._conn.execute(
                "INSERT INTO active_setup (strategy_id, seq_no, strategy_version_id,"
                " param_set_id, note, designated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    strategy.strategy_id,
                    seq_no,
                    strategy.strategy_version_id,
                    param_set.param_set_id,
                    note,
                    _now(),
                ),
            )
        row = self._active_setup_row(strategy.strategy_id)
        assert row is not None  # 剛剛寫入,不會查不到
        return self._active_setup(strategy, param_set, row)

    def get_active_setup(self, strategy_name: str) -> ActiveSetup:
        """這套策略當下的現役設定。從未指定過即拋錯——**不猜**。

        沒有現役設定的策略就是沒有門面數字:寧可講「未指定」,也不可以隨手
        挑一個參數集充當門面(規格 7.5 防參數擬合美化)。
        """
        strategy = self.get_strategy_version(strategy_name)
        row = self._active_setup_row(strategy.strategy_id)
        if row is None:
            raise NotFound(
                f"策略「{strategy.name}」未指定現役設定;"
                "門面數字只取現役設定那次運行,未指定即沒有門面數字(規格 7.5)"
            )
        return self._active_setup_by_row(row)

    def has_active_setup(self, strategy_name: str) -> bool:
        strategy = self.get_strategy_version(strategy_name)
        return self._active_setup_row(strategy.strategy_id) is not None

    def active_setup_history(self, strategy_name: str) -> list[ActiveSetup]:
        """這套策略歷次指定過的現役設定,由早到遲。"""
        strategy = self.get_strategy_version(strategy_name)
        rows = self._conn.execute(
            "SELECT strategy_id, seq_no, strategy_version_id, param_set_id, note,"
            " designated_at FROM active_setup WHERE strategy_id = ? ORDER BY seq_no",
            (strategy.strategy_id,),
        ).fetchall()
        return [self._active_setup_by_row(row) for row in rows]

    def _active_setup_row(self, strategy_id: int) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT strategy_id, seq_no, strategy_version_id, param_set_id, note,"
            " designated_at FROM active_setup WHERE strategy_id = ?"
            " ORDER BY seq_no DESC LIMIT 1",
            (int(strategy_id),),
        ).fetchone()

    def _active_setup_by_row(self, row: sqlite3.Row) -> ActiveSetup:
        strategy = self._strategy_version_by_id(int(row["strategy_version_id"]))
        param_set = self._param_set_by_id(int(row["param_set_id"]))
        return self._active_setup(strategy, param_set, row)

    @staticmethod
    def _active_setup(
        strategy: StrategyVersion, param_set: ParamSet, row: sqlite3.Row
    ) -> ActiveSetup:
        return ActiveSetup(
            strategy_id=strategy.strategy_id,
            strategy_name=strategy.name,
            seq_no=int(row["seq_no"]),
            strategy_version_id=strategy.strategy_version_id,
            strategy_version_no=strategy.version_no,
            param_set_id=param_set.param_set_id,
            param_set_name=param_set.name,
            param_set_version_no=param_set.version_no,
            rebalance_cadence=param_set.rebalance_cadence,
            note=row["note"],
            designated_at=row["designated_at"],
        )

    @staticmethod
    def _check_run_artifacts(
        artifacts: Sequence[RunArtifact], run_id: str
    ) -> dict[str, RunArtifact]:
        by_kind: dict[str, RunArtifact] = {}
        for artifact in artifacts or ():
            if not isinstance(artifact, RunArtifact):
                raise ContractViolation(
                    f"運行序列只收 RunArtifact,收到 {type(artifact).__name__}"
                )
            if artifact.kind not in RUN_ARTIFACT_KINDS:
                raise ContractViolation(
                    f"運行序列種類只收 {list(RUN_ARTIFACT_KINDS)},收到 {artifact.kind!r}"
                )
            if artifact.kind in by_kind:
                raise ContractViolation(f"運行 {run_id} 的 {artifact.kind} 序列給了兩份")
            if not str(artifact.path or "").strip():
                raise ContractViolation(f"運行 {run_id} 的 {artifact.kind} 序列沒有落點")
            if not str(artifact.content_hash or "").strip():
                raise ContractViolation(
                    f"運行 {run_id} 的 {artifact.kind} 序列沒有內容雜湊;"
                    "沒有雜湊就證不到「同一輸入得同一結果」"
                )
            by_kind[artifact.kind] = artifact

        missing = [kind for kind in RUN_ARTIFACT_KINDS if kind not in by_kind]
        if missing:
            raise ContractViolation(
                f"運行 {run_id} 缺序列:{'、'.join(missing)};"
                "逐日淨值、逐日持倉、逐筆交易三條缺一不可(規格 7.4)"
            )
        return by_kind

    def _assert_same_run(self, run_id: str, incoming: Mapping[str, RunArtifact]) -> None:
        stored = {
            r["kind"]: r["content_hash"]
            for r in self._conn.execute(
                "SELECT kind, content_hash FROM run_artifact WHERE run_id = ?", (run_id,)
            ).fetchall()
        }
        differing = [
            kind
            for kind, artifact in incoming.items()
            if stored.get(kind) != artifact.content_hash
        ]
        if differing:
            raise ImmutabilityViolation(
                f"運行 {run_id} 已經留痕,但今次的{'、'.join(differing)}序列內容不同;"
                "運行不可改寫——同一組策略版本 × 參數集 × 期間 × 數據快照 × 引擎版本"
                "本應算出同一個結果,對不上即代表有一件沒有蓋住,請先查明"
            )

    # ------------------------------------------------------------------
    # 共用風控層的登記(D-013 第 4 條、規格 1.6;KARST-025)
    # ------------------------------------------------------------------

    def register_risk_rules(self, rules: Iterable[Mapping[str, Any]]) -> list[RiskRuleRecord]:
        """登記共用風控層的規則定義,回傳全部登記列。

        內容由風控層(``karst.risk``)提供,本層只負責入庫——所以規則本體的正本
        仍然只有一份,庫裡這幾列是它的登記處,不是第二份定義(D-002 第 4 條)。

        重覆登記回同一批列(與快照登記同制);庫內已有的一條與傳入的內容不符即
        拒收:定義落庫後不可改,只可以由風控層那邊出新的一條。
        """
        wanted: dict[str, tuple[str, str, str]] = {}
        for index, rule in enumerate(rules or ()):
            fields = {}
            for column in ("key", "name", "param_key", "description"):
                value = str(rule.get(column, "") or "").strip()
                if not value:
                    raise ContractViolation(f"第 {index} 條風控規則缺「{column}」;定義不可留空")
                fields[column] = value
            if fields["key"] in wanted:
                raise DuplicateDefinition(f"風控規則「{fields['key']}」在同一批裡出現兩次")
            wanted[fields["key"]] = (
                fields["name"],
                fields["param_key"],
                fields["description"],
            )
        if not wanted:
            raise ContractViolation("一條風控規則都沒有;共用風控層不可以是空的")

        for key, (name, param_key, description) in wanted.items():
            row = self._conn.execute(
                "SELECT name, param_key, description FROM risk_rule WHERE rule_key = ?", (key,)
            ).fetchone()
            if row is None:
                with self._conn:
                    self._conn.execute(
                        "INSERT INTO risk_rule (rule_key, name, param_key, description,"
                        " created_at) VALUES (?, ?, ?, ?, ?)",
                        (key, name, param_key, description, _now()),
                    )
                continue
            if (row["name"], row["param_key"], row["description"]) != (
                name,
                param_key,
                description,
            ):
                raise DuplicateDefinition(
                    f"庫內的風控規則「{key}」與現時的定義對不上"
                    f"(庫內:{row['name']}/{row['param_key']});"
                    "風控規則定義落庫後不可改,全平台只有一個正本"
                )
        return self.list_risk_rules()

    def list_risk_rules(self) -> list[RiskRuleRecord]:
        """庫內全部共用風控規則,按登記次序。"""
        rows = self._conn.execute(
            "SELECT risk_rule_id, rule_key, name, param_key, description, created_at"
            " FROM risk_rule ORDER BY risk_rule_id"
        ).fetchall()
        return [_row_to_risk_rule(row) for row in rows]

    def get_risk_rule(self, rule_key: str) -> RiskRuleRecord:
        """按程式名取一條風控規則的登記列。查不到即拋錯,不猜。"""
        key = str(rule_key or "").strip()
        row = self._conn.execute(
            "SELECT risk_rule_id, rule_key, name, param_key, description, created_at"
            " FROM risk_rule WHERE rule_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            raise NotFound(f"庫內沒有共用風控規則「{key}」;請先登記風控層")
        return _row_to_risk_rule(row)

    def attach_risk_rules(
        self,
        strategy_name: str,
        rule_keys: Sequence[str],
        *,
        strategy_version_no: int | None = None,
    ) -> list[RiskRuleRecord]:
        """記下某策略版本引用了哪幾條風控規則,回傳它引用的全部規則。

        只存編號,不存規則本身(與引用因子同制)。引用可以一條都沒有——
        「策略可用可不用」就是這個意思,不引用不是錯,更不會有預設值頂上。
        重覆引用同一條當同一件事,不會多出一列。
        """
        strategy = self.get_strategy_version(strategy_name, strategy_version_no)
        records = [self.get_risk_rule(key) for key in (rule_keys or ())]
        if records:
            with self._conn:
                self._conn.executemany(
                    # ON CONFLICT DO NOTHING:sqlite 與 Postgres 通用寫法(D-027 護欄一),
                    # 不用 sqlite 專有的 INSERT OR IGNORE。
                    "INSERT INTO strategy_risk_ref (strategy_version_id, risk_rule_id)"
                    " VALUES (?, ?) ON CONFLICT DO NOTHING",
                    [
                        (strategy.strategy_version_id, record.risk_rule_id)
                        for record in records
                    ],
                )
        return self.strategy_risk_rules(strategy.name, strategy_version_no=strategy.version_no)

    def strategy_risk_rules(
        self, strategy_name: str, *, strategy_version_no: int | None = None
    ) -> list[RiskRuleRecord]:
        """這套策略版本引用了哪幾條風控規則;一條都沒有就回空清單。"""
        strategy = self.get_strategy_version(strategy_name, strategy_version_no)
        rows = self._conn.execute(
            "SELECT r.risk_rule_id, r.rule_key, r.name, r.param_key, r.description, r.created_at"
            " FROM strategy_risk_ref AS ref"
            " JOIN risk_rule AS r ON r.risk_rule_id = ref.risk_rule_id"
            " WHERE ref.strategy_version_id = ? ORDER BY r.risk_rule_id",
            (strategy.strategy_version_id,),
        ).fetchall()
        return [_row_to_risk_rule(row) for row in rows]

    def list_strategy_names(self) -> list[str]:
        """庫內全部策略的名稱,按登記次序(KARST-035:逐套策略列風控引用時用)。"""
        rows = self._conn.execute("SELECT name FROM strategy ORDER BY strategy_id").fetchall()
        return [row["name"] for row in rows]

    # ------------------------------------------------------------------
    # 數據快照的抓取登記(D-026 第 3 條;KARST-034)
    # ------------------------------------------------------------------

    def record_snapshot_fetch(
        self,
        snapshot_id: str,
        *,
        fetched_at: str,
        window_start: date | datetime | str,
        window_end: date | datetime | str,
        entity_count: int,
        row_count: int,
        trading_days: int,
        alert_count: int | None,
        alert_summary: str | None,
    ) -> SnapshotFetch:
        """記下一次抓取的隨身資料,回傳這個快照的抓取登記。

        同一個快照重覆登記回**原本那一列**(第一次凍結那刻的抓取時間),不覆寫、
        不多加一列:同一批數據重抓得回同一個編號,而它第一次落地是哪一刻,
        是一件已經發生的事,不會因為有人再抓一次而改變。齊全度那兩格同一個道理
        ——留住的是**第一次凍結那刻核對出來的結果**,後來換一套門檻再凍一次,
        改的是那次核對的結論,不是這一次已經發生的登記。

        ``alert_count`` 與 ``alert_summary`` 是**必給的**(KARST-067),而且兩者
        同生共死:核對過就兩格都有,沒有核對過就兩格都是 ``None``。刻意不給預設值
        ——「這份快照有沒有核對過齊全度」是呼叫方才答得出的事,補一個預設值出來,
        就等於替它答了。

        與快照登記同制,**要有唯一入口的簽章手才寫得入**(KARST-087):這一列答的是
        「幾時抓、抓哪段窗口、當日齊全度核對出什麼」,而快照編號刻意不含抓取時間,
        所以那幾格只此一份,改了沒有第二處對得回。
        """
        self._require_snapshot_gate()
        snapshot = self.get_snapshot(snapshot_id)  # 查無此快照即拋 NotFound,不憑空登記
        # 齊全度那兩格先驗一次,行在「已經登記過就回原本那一列」之前:一句
        # 講不通的登記,不會因為那個快照剛巧已經在案就靜靜過關。
        alerts, summary = _check_completeness_cells(alert_count, alert_summary)
        existing = self.snapshot_fetch(snapshot.snapshot_id)
        if existing is not None:
            return existing

        stamp = str(fetched_at or "").strip()
        if not stamp:
            raise ContractViolation("抓取登記必須有抓取時間;不知幾時抓的就不是一次可追溯的抓取")
        first, last = as_date(window_start, "window_start"), as_date(window_end, "window_end")
        if last < first:
            raise ContractViolation(f"窗口起訖倒轉了:{first}~{last}")
        with self._conn:
            self._conn.execute(
                "INSERT INTO data_snapshot_fetch (snapshot_id, fetched_at, window_start,"
                " window_end, entity_count, row_count, trading_days, recorded_at,"
                " alert_count, alert_summary)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    snapshot.snapshot_id,
                    stamp,
                    first,
                    last,
                    int(entity_count),
                    int(row_count),
                    int(trading_days),
                    _now(),
                    alerts,
                    summary,
                ),
            )
            self._sign_snapshot_row("data_snapshot_fetch", (snapshot.snapshot_id,))
        recorded = self.snapshot_fetch(snapshot.snapshot_id)
        assert recorded is not None  # 剛剛寫入,不會查不到
        return recorded

    def snapshot_fetch(self, snapshot_id: str) -> SnapshotFetch | None:
        """這個快照的抓取登記;不是經唯一入口凍的就回 ``None``。"""
        row = self._conn.execute(
            "SELECT snapshot_id, fetched_at, window_start, window_end, entity_count,"
            " row_count, trading_days, recorded_at, alert_count, alert_summary"
            " FROM data_snapshot_fetch WHERE snapshot_id = ?",
            (str(snapshot_id),),
        ).fetchone()
        return None if row is None else _row_to_snapshot_fetch(row)

    def retract_snapshot(
        self,
        snapshot_id: str,
        *,
        reason: str,
        superseded_by: str | None,
        retracted_by: str,
    ) -> SnapshotRetraction:
        """把一個快照由登記冊除名(KARST-084):**加一列,不是刪一列**。

        除名之後 ``list_snapshots`` 與畫面選單一律略過它——登記冊列得出的只有可回測
        的快照;但 ``get_snapshot`` 一類直連查詢照樣讀得到,快照目錄與 parquet 檔亦
        一個字都不動(D-026 第 3 條:舊快照永不改動),所以追溯永遠指得回。

        為什麼不刪:``data_snapshot_fetch``、``factor_value_batch``、
        ``factor_value_batch_member`` 三張表各有一道 ``BEFORE DELETE`` 閘,寫明
        「登記不可刪,追溯要指得回」。刪走等於把一件發生過的事由帳上抹掉。

        還有運行掛住它就拒收:一個回測運行指住的快照若果由登記冊消失,那次運行就
        再也講不出自己跑的是哪一批數。除名不可以令已發生的運行變成孤兒。
        """
        snapshot = self.get_snapshot(snapshot_id)  # 查無此快照即拋 NotFound
        existing = self._conn.execute(
            "SELECT snapshot_id FROM data_snapshot_retraction WHERE snapshot_id = ?",
            (snapshot.snapshot_id,),
        ).fetchone()
        if existing is not None:
            raise DuplicateDefinition(
                f"快照 {snapshot.snapshot_id} 已經除名;除名登記只加不改"
            )
        if superseded_by is not None:
            self.get_snapshot(superseded_by)  # 取代它那個必須真的在庫內
        runs = self._conn.execute(
            "SELECT COUNT(*) AS n FROM backtest_run WHERE snapshot_id = ?",
            (snapshot.snapshot_id,),
        ).fetchone()["n"]
        if int(runs) > 0:
            raise ContractViolation(
                f"快照 {snapshot.snapshot_id} 仍有 {runs} 次回測運行掛住,不可除名;"
                "運行要講得出自己跑的是哪一批數"
            )
        moment = _now()
        with self._conn:
            self._conn.execute(
                "INSERT INTO data_snapshot_retraction (snapshot_id, reason, superseded_by,"
                " retracted_by, retracted_at) VALUES (?, ?, ?, ?, ?)",
                (
                    snapshot.snapshot_id,
                    str(reason).strip(),
                    superseded_by,
                    str(retracted_by).strip(),
                    moment,
                ),
            )
        return SnapshotRetraction(
            snapshot_id=snapshot.snapshot_id,
            reason=str(reason).strip(),
            superseded_by=superseded_by,
            retracted_by=str(retracted_by).strip(),
            retracted_at=moment,
        )

    def list_snapshot_retractions(self) -> list[SnapshotRetraction]:
        """全部除名登記,新的在前。"""
        return [
            SnapshotRetraction(
                snapshot_id=row["snapshot_id"],
                reason=row["reason"],
                superseded_by=row["superseded_by"],
                retracted_by=row["retracted_by"],
                retracted_at=row["retracted_at"],
            )
            for row in self._conn.execute(
                "SELECT snapshot_id, reason, superseded_by, retracted_by, retracted_at"
                " FROM data_snapshot_retraction ORDER BY retracted_at DESC, snapshot_id DESC"
            ).fetchall()
        ]

    def retired_snapshot_ids(self) -> tuple[str, ...]:
        """已除名的快照編號。要查一個快照是不是已除名,用這一格,不要自己寫 SQL。"""
        return tuple(
            row["snapshot_id"]
            for row in self._conn.execute(
                "SELECT snapshot_id FROM data_snapshot_retraction ORDER BY snapshot_id"
            ).fetchall()
        )

    def list_snapshots(self) -> list[SnapshotListing]:
        """庫內**可回測**的數據快照,新的在前。抓取登記有就併埋,沒有就是 ``None``。

        已除名的快照(``data_snapshot_retraction``)不在此列:登記冊列得出的就是可以
        攞去回測的那幾個(KARST-084)。要連除名那幾個一齊看,用
        ``list_snapshot_retractions``;要直取某一個,``get_snapshot`` 一律讀得到。
        """
        rows = self._conn.execute(
            "SELECT s.snapshot_id, s.source, s.taken_on, s.content_hash, s.path, s.universe,"
            " s.created_at, f.fetched_at, f.window_start, f.window_end, f.entity_count,"
            " f.row_count, f.trading_days, f.recorded_at, f.alert_count, f.alert_summary"
            " FROM data_snapshot AS s"
            " LEFT JOIN data_snapshot_fetch AS f ON f.snapshot_id = s.snapshot_id"
            " WHERE s.snapshot_id NOT IN (SELECT snapshot_id FROM data_snapshot_retraction)"
            " ORDER BY s.taken_on DESC, s.snapshot_id DESC"
        ).fetchall()
        return [
            SnapshotListing(
                snapshot_id=row["snapshot_id"],
                source=row["source"],
                taken_on=row["taken_on"],
                content_hash=row["content_hash"],
                path=row["path"],
                universe=tuple(json.loads(row["universe"])),
                created_at=row["created_at"],
                fetch=None if row["fetched_at"] is None else _row_to_snapshot_fetch(row),
            )
            for row in rows
        ]


def check_param_set(
    name: str,
    rebalance_cadence: str | None,
    values: Mapping[str, Any] | None,
) -> dict[str, str]:
    """參數集合約的預檢,不碰庫。

    唯一入口在寫策略之前先驗一次:免得策略已經落庫、參數集才被拒收,
    留下一個無參數集的半截策略。
    """
    DefinitionStore._check_cadence(rebalance_cadence, name)
    return DefinitionStore._check_param_values(values, name)


_STRATEGY_SELECT = """
SELECT v.strategy_version_id, v.strategy_id, s.name, s.strategy_type, v.version_no,
       v.parent_version_id, v.description, v.created_at
FROM strategy_version AS v
JOIN strategy AS s ON s.strategy_id = v.strategy_id
"""


_VERSION_SELECT = """
SELECT v.factor_version_id, v.factor_id, f.name, f.family, v.version_no, v.parent_version_id,
       v.scale_kind, v.procedure_kind, v.formula, v.input_data_version, v.material,
       v.judge_version, v.description, v.created_at
FROM factor_version AS v
JOIN factor AS f ON f.factor_id = v.factor_id
"""


def _check_completeness_cells(
    alert_count: int | None, alert_summary: str | None
) -> tuple[int | None, str | None]:
    """齊全度那兩格的合約:兩格同生共死,條數不可為負(KARST-067)。

    庫身那條 CHECK 已經擋得住,這裡先擋一次是為了拋得出一句人話——一個
    ``IntegrityError`` 講不出「你是核對過還是沒有核對過」。
    """
    summary = None if alert_summary is None else str(alert_summary).strip()
    if alert_count is None and not summary:
        return None, None
    if alert_count is None or not summary:
        raise ContractViolation(
            "齊全度警報條數與警報摘要要一齊給:核對過就兩格都有,沒有核對過就兩格都留空;"
            "留一格空補不出另一格"
        )
    alerts = int(alert_count)
    if alerts < 0:
        raise ContractViolation(f"齊全度警報條數不可為負:收到 {alert_count!r}")
    return alerts, summary


def _row_to_snapshot_fetch(row: sqlite3.Row) -> SnapshotFetch:
    return SnapshotFetch(
        snapshot_id=row["snapshot_id"],
        fetched_at=row["fetched_at"],
        window_start=row["window_start"],
        window_end=row["window_end"],
        entity_count=int(row["entity_count"]),
        row_count=int(row["row_count"]),
        trading_days=int(row["trading_days"]),
        recorded_at=row["recorded_at"],
        alert_count=None if row["alert_count"] is None else int(row["alert_count"]),
        alert_summary=row["alert_summary"],
    )


def _row_to_risk_rule(row: sqlite3.Row) -> RiskRuleRecord:
    return RiskRuleRecord(
        risk_rule_id=int(row["risk_rule_id"]),
        key=row["rule_key"],
        name=row["name"],
        param_key=row["param_key"],
        description=row["description"],
        created_at=row["created_at"],
    )


def _row_to_version(row: sqlite3.Row) -> FactorVersion:
    if row["procedure_kind"] == "formula":
        procedure: Procedure = FormulaProcedure(
            formula=row["formula"], input_data_version=row["input_data_version"]
        )
    else:
        procedure = MaterialProcedure(
            material=row["material"], judge_version=row["judge_version"]
        )
    return FactorVersion(
        factor_version_id=int(row["factor_version_id"]),
        factor_id=int(row["factor_id"]),
        name=row["name"],
        family=row["family"],
        version_no=int(row["version_no"]),
        parent_version_id=None if row["parent_version_id"] is None else int(row["parent_version_id"]),
        scale_kind=row["scale_kind"],
        procedure=procedure,
        description=row["description"],
        created_at=row["created_at"],
    )
