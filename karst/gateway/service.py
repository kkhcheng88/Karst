"""唯一入口(single gateway):全平台唯一一條寫入通道。

D-020 第 4 條:所有策略定義、參數、因子定義一律經同一套命令入庫,由它
**查合約、蓋版本時間戳、留血統**;人手與 agent 同一道門。

本層做三件事,一件不多:

1. **查合約** —— 交由單一定義庫的合約檢查(缺刻度型、缺產生程序、缺換倉節奏、
   前視一類即場拒收),寫不入就是寫不入,不做默認補值。
2. **蓋版本時間戳** —— 版本號、父版本、落庫時間由庫層自動蓋(git 式版本鏈,
   D-021 第 9 條);唯一入口另蓋寫入者與寫入時間。
3. **留血統** —— 每一列留一個寫入者簽章;沒有簽章的列 ``verify`` 一掃即現形。
"""

from __future__ import annotations

import getpass
import os
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..models import FormulaProcedure, MaterialProcedure, Procedure
from ..store import DefinitionLocation, DefinitionStore, FactorVersion, ParamSet, StrategyVersion
from . import ledger

WRITER_ENV = "KARST_WRITER"
STORE_ENV = "KARST_STORE"
DEFAULT_STORE = "karst.sqlite"


def default_store_path() -> str:
    return os.environ.get(STORE_ENV) or DEFAULT_STORE


def default_writer() -> str:
    named = os.environ.get(WRITER_ENV)
    if named and named.strip():
        return named.strip()
    try:
        return getpass.getuser()
    except Exception:  # pragma: no cover - 無登入身分的環境
        return "unknown"


@dataclass(frozen=True, slots=True)
class WriteReceipt:
    """一次經唯一入口寫入的收據:寫了什麼、蓋了哪一版、誰寫的。"""

    kind: str
    name: str
    version_no: int
    parent_version_id: int | None
    created_at: str
    writer: str
    signed_rows: tuple[str, ...]


class Gateway:
    """唯一入口。``Gateway.open(path)`` 開,支援 ``with`` 語法。"""

    def __init__(self, store: DefinitionStore, key: bytes, *, writer: str, path: str) -> None:
        self._store = store
        self._key = key
        self._writer = writer
        self._path = path

    @classmethod
    def open(cls, path: str | None = None, *, writer: str | None = None) -> "Gateway":
        store_path = path or default_store_path()
        return cls(
            DefinitionStore.open(store_path),
            ledger.load_or_create_key(store_path),
            writer=writer or default_writer(),
            path=store_path,
        )

    def close(self) -> None:
        self._store.close()

    def __enter__(self) -> "Gateway":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def store(self) -> DefinitionStore:
        return self._store

    @property
    def path(self) -> str:
        return self._path

    @property
    def writer(self) -> str:
        return self._writer

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._store.connection

    # ------------------------------------------------------------------
    # 因子定義
    # ------------------------------------------------------------------

    def register_factor(
        self,
        name: str,
        *,
        scale_kind: str | None = None,
        procedure: Procedure | None = None,
        description: str | None = None,
    ) -> tuple[FactorVersion, WriteReceipt]:
        version = self._store.register_factor(
            name, scale_kind=scale_kind, procedure=procedure, description=description
        )
        signed = self._sign(
            ("factor", (version.factor_id,)),
            ("factor_version", (version.factor_version_id,)),
        )
        return version, self._receipt("因子", version.name, version.version_no,
                                      version.parent_version_id, version.created_at, signed)

    def new_factor_version(
        self,
        name: str,
        *,
        scale_kind: str | None = None,
        procedure: Procedure | None = None,
        description: str | None = None,
    ) -> tuple[FactorVersion, WriteReceipt]:
        version = self._store.new_factor_version(
            name, scale_kind=scale_kind, procedure=procedure, description=description
        )
        signed = self._sign(("factor_version", (version.factor_version_id,)))
        return version, self._receipt("因子", version.name, version.version_no,
                                      version.parent_version_id, version.created_at, signed)

    def write_factor_values(
        self,
        name: str,
        rows: Sequence[Mapping[str, object]],
        *,
        version_no: int | None = None,
        snapshot_id: str | None = None,
    ) -> int:
        """經同一道門寫因子值,回傳寫入列數。

        值本身不逐列蓋簽章(行數與定義不同一個量級),它靠三重防線:
        寫入時的合約檢查(前視、非有限數)、trigger 鎖死不可改不可刪,
        以及它掛住的因子版本已有簽章。
        """
        return self._store.write_factor_values(
            name, rows, version_no=version_no, snapshot_id=snapshot_id
        )

    # ------------------------------------------------------------------
    # 策略定義與參數集
    # ------------------------------------------------------------------

    def register_strategy(
        self,
        name: str,
        *,
        strategy_type: str | None = None,
        factor_refs: Sequence[str] | None = None,
        description: str | None = None,
    ) -> tuple[StrategyVersion, WriteReceipt]:
        version = self._store.register_strategy(
            name,
            strategy_type=strategy_type,
            factor_refs=factor_refs,
            description=description,
        )
        signed = self._sign(
            ("strategy", (version.strategy_id,)),
            ("strategy_version", (version.strategy_version_id,)),
            *self._ref_rows(version),
        )
        return version, self._receipt("策略", version.name, version.version_no,
                                      version.parent_version_id, version.created_at, signed)

    def new_strategy_version(
        self,
        name: str,
        *,
        factor_refs: Sequence[str] | None = None,
        description: str | None = None,
    ) -> tuple[StrategyVersion, WriteReceipt]:
        version = self._store.new_strategy_version(
            name, factor_refs=factor_refs, description=description
        )
        signed = self._sign(
            ("strategy_version", (version.strategy_version_id,)),
            *self._ref_rows(version),
        )
        return version, self._receipt("策略", version.name, version.version_no,
                                      version.parent_version_id, version.created_at, signed)

    def register_param_set(
        self,
        strategy_name: str,
        *,
        param_set_name: str,
        rebalance_cadence: str | None = None,
        values: Mapping[str, object] | None = None,
        strategy_version_no: int | None = None,
    ) -> tuple[ParamSet, WriteReceipt]:
        param_set = self._store.register_param_set(
            strategy_name,
            param_set_name=param_set_name,
            rebalance_cadence=rebalance_cadence,
            values=values,
            strategy_version_no=strategy_version_no,
        )
        signed = self._sign(
            ("param_set", (param_set.param_set_id,)),
            *[("param_value", (param_set.param_set_id, key)) for key in param_set.values],
        )
        return param_set, self._receipt("參數集", param_set.name, param_set.version_no,
                                        param_set.parent_version_id, param_set.created_at, signed)

    @staticmethod
    def _ref_rows(version: StrategyVersion) -> list[tuple[str, tuple[object, ...]]]:
        return [
            ("strategy_factor_ref", (version.strategy_version_id, factor.factor_version_id))
            for factor in version.factors
        ]

    # ------------------------------------------------------------------
    # 核對與落點
    # ------------------------------------------------------------------

    def verify(self) -> list[ledger.Finding]:
        """全庫核對:揪出繞過唯一入口寫入、或落庫後被改動的列。"""
        return ledger.verify(self._conn, self._key)

    def locate(self, kind: str, name: str) -> DefinitionLocation:
        return self._store.locate_definition(kind, name)

    # ------------------------------------------------------------------

    def _sign(self, *rows: tuple[str, tuple[object, ...]]) -> tuple[str, ...]:
        signed: list[str] = []
        for table, primary_key in rows:
            key_text = ledger.record_write(
                self._conn, self._key, table, primary_key, writer=self._writer
            )
            signed.append(f"{table}[{key_text}]")
        return tuple(signed)

    def _receipt(
        self,
        kind: str,
        name: str,
        version_no: int,
        parent_version_id: int | None,
        created_at: str,
        signed: tuple[str, ...],
    ) -> WriteReceipt:
        return WriteReceipt(
            kind=kind,
            name=name,
            version_no=version_no,
            parent_version_id=parent_version_id,
            created_at=created_at,
            writer=self._writer,
            signed_rows=signed,
        )


def build_procedure(
    *,
    formula: str | None = None,
    input_data_version: str | None = None,
    material: str | None = None,
    judge_version: str | None = None,
) -> Procedure | None:
    """把命令列給的產生程序砌成合約要的形狀;一格都沒有就回 None(留待合約拒收)。"""
    formula_given = bool(formula or input_data_version)
    material_given = bool(material or judge_version)
    if formula_given and material_given:
        raise ValueError("產生程序只可揀一派:公式派(公式+輸入數據版本)或數值派(材料+判官版本)")
    if formula_given:
        return FormulaProcedure(formula=formula or "", input_data_version=input_data_version or "")
    if material_given:
        return MaterialProcedure(material=material or "", judge_version=judge_version or "")
    return None
