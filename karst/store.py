"""單一定義庫的 Python API。

一個 ``DefinitionStore`` 就是一個 sqlite 檔的門面:登記實體與代號、登記因子定義
與出新版、寫入與讀取因子值(讀取一律可按知情時間截止)、登記數據快照。

本層只管「寫得入、讀得回、改不得」;唯一入口(single gateway)的治理與命令列
在另一張票,故此處刻意不做權限與流程,只做合約檢查。
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from . import schema
from .errors import (
    ContractViolation,
    DuplicateDefinition,
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
    "value",
    "snapshot_id",
    "factor_version_id",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DefinitionStore:
    """單一定義庫。用 ``DefinitionStore.open(path)`` 開,支援 ``with`` 語法。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @classmethod
    def open(cls, path: str = ":memory:") -> "DefinitionStore":
        return cls(schema.connect(path))

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "DefinitionStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

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
    # 因子值:日期 × 實體 → 值,事件時間與知情時間雙時間戳
    # ------------------------------------------------------------------

    def write_factor_values(
        self,
        name: str,
        rows: Iterable[Mapping[str, Any]] | pd.DataFrame,
        *,
        version_no: int | None = None,
        snapshot_id: str | None = None,
    ) -> int:
        """寫入因子值。每列要有 entity_id、event_time、knowledge_time、value。

        缺失值**不要寫**——沒有那一列就是「該股該日不參與」(D-021 第 4 條);
        寫 0 或 NaN 一律當錯。知情時間早於事件時間即前視,當場拒收。
        """
        version = self.get_factor_version(name, version_no)
        if isinstance(rows, pd.DataFrame):
            records: Sequence[Mapping[str, Any]] = rows.to_dict("records")
        else:
            records = list(rows)

        payload: list[tuple[Any, ...]] = []
        for index, record in enumerate(records):
            missing = [k for k in ("entity_id", "event_time", "knowledge_time", "value") if k not in record]
            if missing:
                raise ContractViolation(f"第 {index} 列缺欄位:{'、'.join(missing)}")
            event_time = as_timestamp(record["event_time"], "event_time")
            knowledge_time = as_timestamp(record["knowledge_time"], "knowledge_time")
            if knowledge_time < event_time:
                raise ContractViolation(
                    f"第 {index} 列前視:知情時間 {knowledge_time} 早於事件時間 {event_time}"
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
                )
            )

        try:
            with self._conn:
                self._conn.executemany(
                    "INSERT INTO factor_value (factor_version_id, entity_id, event_time,"
                    " knowledge_time, value, snapshot_id) VALUES (?, ?, ?, ?, ?, ?)",
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
            "SELECT entity_id, event_time, knowledge_time, value, snapshot_id, factor_version_id",
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
            SELECT entity_id, event_time, knowledge_time, value, snapshot_id, factor_version_id
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
        """
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


_VERSION_SELECT = """
SELECT v.factor_version_id, v.factor_id, f.name, f.family, v.version_no, v.parent_version_id,
       v.scale_kind, v.procedure_kind, v.formula, v.input_data_version, v.material,
       v.judge_version, v.description, v.created_at
FROM factor_version AS v
JOIN factor AS f ON f.factor_id = v.factor_id
"""


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
