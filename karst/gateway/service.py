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
from typing import TYPE_CHECKING

from ..errors import ContractViolation, NotFound
from ..models import FormulaProcedure, MaterialProcedure, Procedure
from ..store import (
    ActiveSetup,
    DefinitionLocation,
    DefinitionStore,
    FactorVersion,
    ParamSet,
    RiskRuleRecord,
    StrategyVersion,
)
from . import ledger

if TYPE_CHECKING:  # pragma: no cover - 只為型別註釋
    from ..factorstore import FactorValueStore

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


def completeness_summary(snapshot: object) -> str:
    """把一份宏觀快照的齊全度核對結果,壓成寫得入抓取登記的一句話(KARST-067)。

    有警報就把每一條原文照錄——這一句是要答「哪一條序列停止講話、短了幾多日」,
    答不出就等於沒有寫;零警報就正面講一句「全部合格」,而不是留白。**留白另有
    意思**(見 ``store.SnapshotFetch``):留白 = 沒有人核對過。

    這次用的門檻一併寫在句末:同一批讀數換一套門檻可以換出另一個結論,而登記上
    那一句若果講不出當時用的是哪一把尺,下一個人就對不回。
    """
    alerts = tuple(getattr(snapshot, "alerts", ()))
    thresholds = getattr(snapshot, "thresholds", None)
    described = thresholds.describe() if thresholds is not None else "門檻不詳"
    if alerts:
        return ";".join(alert.message for alert in alerts) + f"({described})"
    return f"{len(getattr(snapshot, 'series', ()))} 條序列全部合格({described})"


@dataclass(frozen=True, slots=True)
class WriteReceipt:
    """一次經唯一入口寫入的收據:寫了什麼、蓋了哪一版、誰寫的。

    ``reused`` 是「這一次其實一個字都沒有寫,回的是庫裡本來那一列」——同名同節奏
    同取值的參數集就是這樣(見 ``register_param_set``)。掃描要數「真正寫入了幾多
    個參數集」,靠的就是這一格,不必自己再查一次庫。
    """

    kind: str
    name: str
    version_no: int
    parent_version_id: int | None
    created_at: str
    writer: str
    signed_rows: tuple[str, ...]
    reused: bool = False


@dataclass(frozen=True, slots=True)
class Countersign:
    """一次補簽:哪一列、由誰補、為什麼補(KARST-087)。"""

    table: str
    row_key: str
    writer: str
    reason: str


@dataclass(frozen=True, slots=True)
class CategoryVerdict:
    """核對報告其中一類的裁決:這一類受治理的列共幾多、清白與否、不合格在哪(KARST-087)。"""

    category: str
    row_count: int
    findings: tuple[ledger.Finding, ...]

    @property
    def clean(self) -> bool:
        return not self.findings

    def describe(self) -> str:
        if self.clean:
            return f"{self.category}:清白({self.row_count} 列)"
        return f"{self.category}:揪到 {len(self.findings)} 處不合格({self.row_count} 列)"


class Gateway:
    """唯一入口。``Gateway.open(path)`` 開,支援 ``with`` 語法。"""

    def __init__(self, store: DefinitionStore, key: bytes, *, writer: str, path: str) -> None:
        self._store = store
        self._key = key
        self._writer = writer
        self._path = path
        # 快照登記那道閘只有這裡開得到(KARST-087)。庫身本身不認識鑰匙與寫入者身分,
        # 它只認識「門口有沒有人接手蓋章」——所以一個不是由這道門開出來的庫身,
        # 凍不出快照登記。價格線、宏觀線、重凍腳本三處由此無一繞得過簽章。
        store.attach_snapshot_signer(self._sign_snapshot_row)

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
        """經同一道門逐值寫因子值入庫,回傳寫入列數。

        值本身不逐列蓋簽章(行數與定義不同一個量級),它靠三重防線:
        寫入時的合約檢查(前視、非有限數)、trigger 鎖死不可改不可刪,
        以及它掛住的因子版本已有簽章。

        **這道門是給小批值用的**:一次幾百列、要即場查得到。因子庫級數的一批
        (Alpha158 一類)走 ``write_factor_batch``——值落 Parquet,庫內只留登記與
        雜湊(D-032)。分界線是量不是意思:兩邊寫的都是同一件事,三個時點連一個
        有限數。
        """
        return self._store.write_factor_values(
            name, rows, version_no=version_no, snapshot_id=snapshot_id
        )

    def factor_values(self, root: str | None = None) -> "FactorValueStore":
        """因子值檔案庫的門面(D-032):值住 Parquet,庫內只留登記與雜湊。

        ``root`` 留空即批次檔的預設落點 ``data/factors``,與快照、運行並列。
        """
        from ..factorstore import DEFAULT_FACTOR_ROOT, FactorValueStore

        return FactorValueStore(self._store, root if root is not None else DEFAULT_FACTOR_ROOT)

    def write_factor_batch(
        self,
        frame: object,
        *,
        batch_key: str,
        snapshot_id: str,
        procedure_version: str,
        root: str | None = None,
    ) -> object:
        """經同一道門寫一個因子值批次:值落 Parquet,登記與雜湊入庫(D-032)。

        與逐值入表那條路(``write_factor_values``)同一套合約——前視、非有限數、
        重複的鍵一律在落檔之前擋。分別只在承載體:一批因子庫級數的值住檔案,
        庫內留的是落點、內容雜湊、行數,而**那一列登記逐格有寫入者簽章**,
        所以有人繞過這道門自己塞一列登記,``verify`` 一掃就見到。
        """
        batch = self.factor_values(root).write_batch(
            frame,
            batch_key=batch_key,
            snapshot_id=snapshot_id,
            procedure_version=procedure_version,
        )
        self._sign_once(
            ("factor_value_batch", (batch.batch_key, batch.snapshot_id)),
            *[
                (
                    "factor_value_batch_member",
                    (batch.batch_key, batch.snapshot_id, member.factor_version_id),
                )
                for member in batch.members
            ],
        )
        return batch

    def ingest_alpha158(
        self, *, snapshot_id: str, root: str | None = None, factor_root: str | None = None
    ) -> object:
        """把一個價格快照上的 Alpha158 全部 158 條算出來、登記、入庫(KARST-064、068)。

        本層一列都不另寫:登記走 ``register_factor`` / ``new_factor_version``、
        值走 ``write_factor_batch``,即與人手逐條登記行的是同一條路,只是不必
        逐條打 158 次。做法住在 ``karst.gateway.alpha158``。

        ``root`` 是價格快照的快取根,``factor_root`` 是因子值批次檔的落點。
        """
        from .alpha158 import ingest_alpha158

        return ingest_alpha158(
            self, snapshot_id=snapshot_id, root=root, factor_root=factor_root
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
        """登記一個參數集。**同名、同節奏、同取值即沿用舊版**,不會多寫一列。

        為什麼這條規矩住在入口,而不是由每套策略各自抄一份:參數集版本號是運行
        編號的原料之一,無端多一版就會把同一次回測記成兩次(D-021 第 9 條、
        CONTEXT.md「運行編號」)。這是任何策略都要的行為,不是某一套策略的內部
        細節——經這道門登記參數集就自動有(D-002 第 4 條單一定義、D-020 第 4 條)。

        比的是**取值本身**,不是名:名一樣而值不同就是另一組取值,一定要出新版;
        節奏亦然,節奏是參數集的一部分。取值一律先按庫層的寫法收成文字再比
        (``str(值).strip()``,見 ``DefinitionStore._check_param_values``),所以
        權重寫 ``0.25`` 還是 ``"0.25"`` 都認得是同一組;兩邊各寫一套收法就會出現
        「明明同值卻比不中」。

        沿用舊版那一次**一個字都不寫**,所以亦不蓋新簽章,收據回的是那一列本來
        就有的簽章。庫內那一列若當初不是經這道門寫入,它照舊沒有簽章,``verify``
        一掃仍然揪得到——沿用不會替繞過入口的列補一個簽章把痕跡蓋走。
        """
        existing = self._existing_param_set(
            strategy_name,
            param_set_name=param_set_name,
            rebalance_cadence=rebalance_cadence,
            values=values,
            strategy_version_no=strategy_version_no,
        )
        if existing is not None:
            return existing, self._receipt(
                "參數集",
                existing.name,
                existing.version_no,
                existing.parent_version_id,
                existing.created_at,
                self._recorded_signatures(existing),
                reused=True,
            )

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

    def _existing_param_set(
        self,
        strategy_name: str,
        *,
        param_set_name: str,
        rebalance_cadence: str | None,
        values: Mapping[str, object] | None,
        strategy_version_no: int | None,
    ) -> ParamSet | None:
        """這個策略版本上有沒有一個同名、同節奏、同取值的參數集?有就回它,無就回 ``None``。

        策略本身查無此名時一樣回 ``None``——真正的拒收留給庫層去講,本層不搶著報錯。
        """
        try:
            head = self._store.get_param_set(
                strategy_name, param_set_name, strategy_version_no=strategy_version_no
            )
        except NotFound:
            return None
        wanted = {str(key).strip(): str(value).strip() for key, value in dict(values or {}).items()}
        if head.rebalance_cadence != rebalance_cadence or dict(head.values) != wanted:
            return None
        return head

    def _recorded_signatures(self, param_set: ParamSet) -> tuple[str, ...]:
        """沿用舊版時,回那幾列**本來就有**的簽章;查不到就不報——不補蓋、不改動。"""
        rows: list[tuple[str, tuple[object, ...]]] = [("param_set", (param_set.param_set_id,))]
        rows += [
            ("param_value", (param_set.param_set_id, key)) for key in param_set.values
        ]
        signed: list[str] = []
        for table, primary_key in rows:
            key_text = "|".join(str(part) for part in primary_key)
            found = self._conn.execute(
                "SELECT 1 FROM gateway_write WHERE table_name = ? AND row_key = ?",
                (table, key_text),
            ).fetchone()
            if found is not None:
                signed.append(f"{table}[{key_text}]")
        return tuple(signed)

    # ------------------------------------------------------------------
    # 現役設定與共用風控規則(KARST-035)
    # ------------------------------------------------------------------

    def designate_active_setup(
        self,
        strategy_name: str,
        *,
        param_set_name: str,
        strategy_version_no: int | None = None,
        param_set_version_no: int | None = None,
        note: str | None = None,
    ) -> tuple[ActiveSetup, WriteReceipt]:
        """指定一套策略的現役設定,並為這一筆指定蓋簽章。

        現役設定決定門面八個數字取哪一次運行(規格 7.5),所以它與策略定義同一
        道門:指定經這裡入庫、留寫入者簽章,``karst verify`` 核對得到。
        """
        setup = self._store.set_active_setup(
            strategy_name,
            param_set_name,
            strategy_version_no=strategy_version_no,
            param_set_version_no=param_set_version_no,
            note=note,
        )
        signed = self._sign_once(("active_setup", (setup.strategy_id, setup.seq_no)))
        return setup, self._receipt(
            "現役設定", setup.strategy_name, setup.seq_no, None, setup.designated_at, signed
        )

    def register_risk_rules(self) -> tuple[tuple[RiskRuleRecord, ...], tuple[str, ...]]:
        """把共用風控層三條規則的正本登記入庫並蓋簽章,回傳(登記列, 簽章)。

        規則本體(叫什麼、管什麼、參數叫什麼名)的正本住在 ``karst/risk``;
        入口只是把它入庫,不在此另寫一份定義(D-002 第 4 條)。
        重覆跑回同一批列,簽章亦照舊那一個,不會多出第二份影像。
        """
        from ..risk import risk_rule_definitions

        rules = tuple(self._store.register_risk_rules(risk_rule_definitions()))
        signed = self._sign_once(
            *[("risk_rule", (rule.risk_rule_id,)) for rule in rules]
        )
        return rules, signed

    def attach_risk_rules(
        self,
        strategy_name: str,
        rule_keys: Sequence[str],
        *,
        strategy_version_no: int | None = None,
    ) -> tuple[tuple[RiskRuleRecord, ...], tuple[str, ...]]:
        """記下某策略版本引用了哪幾條風控規則,並為引用蓋簽章。

        只存編號,不存規則本身(與引用因子同制)。一條都不引用照樣跑得
        (D-013 第 4 條),故此這道命令不是每套策略都要走一次。
        """
        refs = tuple(
            self._store.attach_risk_rules(
                strategy_name, rule_keys, strategy_version_no=strategy_version_no
            )
        )
        version = self._store.get_strategy_version(strategy_name, strategy_version_no)
        signed = self._sign_once(
            *[
                ("strategy_risk_ref", (version.strategy_version_id, ref.risk_rule_id))
                for ref in refs
            ]
        )
        return refs, signed

    @staticmethod
    def _ref_rows(version: StrategyVersion) -> list[tuple[str, tuple[object, ...]]]:
        return [
            ("strategy_factor_ref", (version.strategy_version_id, factor.factor_version_id))
            for factor in version.factors
        ]

    # ------------------------------------------------------------------
    # 數據快照(KARST-034)
    # ------------------------------------------------------------------

    def take_snapshot(
        self,
        *,
        start: str,
        end: str,
        universe: Sequence[object],
        source: object | None = None,
        root: str | None = None,
        taken_on: str | None = None,
        extra_notes: Sequence[str] = (),
        cik_map: dict[str, str] | None = None,
        anchor_valid_to: dict[str, str] | None = None,
    ) -> tuple[object, object]:
        """一句話跑完抓取 → 凍結 → 登記,回傳(快照成果單, 抓取登記)。

        管線本身(``karst.data``)一個字都不改:唯一入口只是**呼叫**它,再把
        「幾時抓、抓的是哪一段窗口」記入抓取登記——快照編號本身不含抓取時間
        (同一批數據重抓要得同一個編號),所以那幾格另有落點。

        ``extra_notes`` 原封不動交給管線寫入快照說明檔:呼叫方知道而管線見不到的
        事(這批數據少了哪些代號、為什麼少),只有這一格講得出(KARST-065)。
        """
        from ..data import build_price_snapshot

        snapshot = build_price_snapshot(
            self._store,
            start=start,
            end=end,
            universe=universe,
            source=source,
            root=root,
            taken_on=taken_on,
            extra_notes=extra_notes,
            cik_map=cik_map,
            anchor_valid_to=anchor_valid_to,
        )
        fetch = self._store.record_snapshot_fetch(
            snapshot.snapshot_id,
            fetched_at=snapshot.fetched_at,
            window_start=snapshot.window_start,
            window_end=snapshot.window_end,
            entity_count=len(snapshot.entity_ids),
            row_count=snapshot.rows,
            trading_days=snapshot.trading_days,
            # 價格快照沒有齊全度核對這回事:主日曆本身就是由它定出來的,
            # 沒有第二把尺可以拿來核它的尾段。兩格留空 = 沒有核對過,
            # 不是「核對過、零警報」(KARST-067)。
            alert_count=None,
            alert_summary=None,
        )
        return snapshot, fetch

    def retract_snapshot(
        self, snapshot_id: str, *, reason: str, superseded_by: str | None
    ) -> object:
        """把一個快照由登記冊除名,並蓋上寫入者簽章(KARST-084)。

        除名是一個**定義級動作**——它決定日後所有回測拿得到哪幾個快照——所以與策略
        定義同一道門:經這裡寫、留簽章,``karst verify`` 核得到。有人繞過這道門直接
        塞一列除名登記,verify 一掃就見到它沒有簽章。

        除的是**登記**,不是檔案:快照目錄與 parquet 一個字都不動(D-026 第 3 條),
        ``get_snapshot`` 照樣讀得到,只是 ``list_snapshots`` 與畫面選單不再列出它。
        """
        retraction = self._store.retract_snapshot(
            snapshot_id,
            reason=reason,
            superseded_by=superseded_by,
            retracted_by=self._writer,
        )
        self._sign(("data_snapshot_retraction", (retraction.snapshot_id,)))
        return retraction

    def retract_run(self, run_id: str, *, reason: str) -> object:
        """把一次運行由清單與計數除名,並蓋上寫入者簽章(KARST-093)。

        除名是一個**定義級動作**——它決定門面成績、歷次運行表、運行選單取哪幾次
        運行——所以與指定現役設定同一道門:經這裡寫、留簽章,``karst verify`` 核得
        到。有人繞過這道門直接塞一列除名登記,verify 一掃就見到它沒有簽章。

        除的是**帳**,不是檔案:``backtest_run`` 那一列、淨值與交易 parquet 一個字
        都不動,``get_run`` 照樣讀得到,只是 ``list_runs`` 與 ``count_runs`` 不再
        算它一份。

        ``reason`` 不設預設值:除名一次運行必須講得出憑什麼,而一個預設理由等於
        沒有理由——日後翻帳只會見到一句人人一樣的空話,查不出當時發生過什麼事。
        """
        retraction = self._store.retract_run(
            run_id,
            reason=reason,
            retracted_by=self._writer,
        )
        self._sign(("backtest_run_retraction", (retraction.run_id,)))
        return retraction

    def register_sweep_batch(
        self,
        sweep_id: str,
        *,
        strategy_name: str,
        strategy_version_no: int,
        period_start: str,
        period_end: str,
        snapshot_id: str,
        engine_name: str,
        engine_version: str,
        cell_count: int,
        qualified_cells: int,
        failed_cells: int,
        error_cells: int,
        median_annual_return: float | None,
        median_sortino: float | None,
        median_max_drawdown: float | None,
        objective: str,
        min_trades: int,
        lonely_peak_margin: float,
        plateau_quantile: float,
        best_point: str | None,
        best_run_id: str | None,
        representative_point: str | None,
        report_path: str,
        report_hash: str,
    ) -> tuple[object, bool]:
        """登記一次掃描的**批次**,並蓋上寫入者簽章(KARST-091;D-042)。

        批次登記是一個**定義級動作**——D-042 明文用「達標運行的中位數年化最高」排
        批次名次,而門面左半那四個數(達標幾條/共幾條、中位年化、中位 Sortino、
        中位最大回撤)全部由這一列讀出來。所以它與指定現役設定同一道門:經這裡寫、
        留簽章,``karst verify`` 核得到。有人繞過這道門直接塞一列看似達標的批次,
        verify 一掃就見到它沒有簽章。

        **它不碰運行。** 掃描編號本來就不入運行編號(KARST-054),所以這是加一列;
        舊掃描事後補登記照樣寫得入,既有運行一個位都不動。

        回 ``(批次, 是不是沿用舊那一列)``:同一個掃描編號、同一份內容再登記一次,
        原封不動沿用舊那一列(重掃同一幅格會走到這裡)。
        """
        batch, reused = self._store.register_sweep_batch(
            sweep_id,
            strategy_name=strategy_name,
            strategy_version_no=strategy_version_no,
            period_start=period_start,
            period_end=period_end,
            snapshot_id=snapshot_id,
            engine_name=engine_name,
            engine_version=engine_version,
            cell_count=cell_count,
            qualified_cells=qualified_cells,
            failed_cells=failed_cells,
            error_cells=error_cells,
            median_annual_return=median_annual_return,
            median_sortino=median_sortino,
            median_max_drawdown=median_max_drawdown,
            objective=objective,
            min_trades=min_trades,
            lonely_peak_margin=lonely_peak_margin,
            plateau_quantile=plateau_quantile,
            best_point=best_point,
            best_run_id=best_run_id,
            representative_point=representative_point,
            report_path=report_path,
            report_hash=report_hash,
        )
        # 沿用舊那一列時亦要走一次:那一列一經落庫即不可改(trigger 擋住),
        # 原本那個簽章照舊有效,``record_write_once`` 蓋過就算數。
        self._sign_once(("sweep_batch", (batch.sweep_id,)))
        return batch, reused

    def take_macro_snapshot(
        self,
        *,
        price_snapshot_id: str,
        thresholds: object,
        source: object | None = None,
        root: str | None = None,
        price_root: str | None = None,
        codes: Sequence[str] | None = None,
        taken_on: str | None = None,
    ) -> tuple[object, object]:
        """宏觀十四序列走同一道門(KARST-057)。

        與價格那條的分別有兩處。一,宏觀序列**要對齊價格快照那條主日曆**,所以
        窗口不是命令列給的,是由指定那個價格快照的日曆讀回來——兩份快照的日子
        對不上,驅動器就會拿住一條有洞的訊號去移權。門在這裡替呼叫方對齊,
        免得每個腳本各自抄一次對齊的做法。

        二,``thresholds`` 是**必給的**齊全度門檻(KARST-061)。凍結那一刻逐條序列
        對主日曆核尾段與留空比例,超出門檻的一條一筆講出來;門檻沒有預設值,
        所以「凍了一份沒有人核對過的宏觀快照」在這道門後面表達不出來。

        那次核對的結論**一併寫入抓取登記**(KARST-067):警報條數與一句摘要。
        以前它只寫在已凍結快照自己的 manifest 與說明檔,``karst data list``
        看不到——要開目錄才知道某份快照當日有沒有序列停止講話。
        """
        from ..data import CALENDAR_TICKER, ALL_SERIES_CODES, build_macro_snapshot, read_calendar

        calendar = read_calendar(self._store, price_snapshot_id, root=price_root)
        if not calendar:
            raise ContractViolation(
                f"價格快照 {price_snapshot_id} 的日曆是空的,宏觀序列無從對齊"
            )
        snapshot = build_macro_snapshot(
            self._store,
            start=calendar[0],
            end=calendar[-1],
            calendar=calendar,
            calendar_ticker=CALENDAR_TICKER,
            thresholds=thresholds,
            codes=tuple(codes) if codes else ALL_SERIES_CODES,
            source=source,
            root=root,
            taken_on=taken_on,
        )
        fetch = self._store.record_snapshot_fetch(
            snapshot.snapshot_id,
            fetched_at=snapshot.fetched_at,
            window_start=snapshot.window_start,
            window_end=snapshot.window_end,
            entity_count=len(snapshot.series),
            row_count=snapshot.rows,
            trading_days=snapshot.trading_days,
            alert_count=len(snapshot.alerts),
            alert_summary=completeness_summary(snapshot),
        )
        return snapshot, fetch

    def list_snapshots(self) -> list:
        return self._store.list_snapshots()

    def countersign_snapshots(self, *, reason: str) -> tuple[Countersign, ...]:
        """替治理清單收窄之前落庫、一個簽章都沒有的快照登記補簽(KARST-087)。

        為什麼要有這一道:治理清單一收入數據快照登記與抓取登記,清單裡即刻多了一批
        收窄之前寫的舊列——它們當日不是經這道門寫的,所以一個簽章都沒有。不補,
        ``verify`` 由第一日起就永遠報紅,而**一份長期報紅的核對報告等於沒有報告**:
        真正的繞過寫入會混在那堆舊帳裡,沒有人看得出來。

        補簽不等於原簽,所以逐列另留一行痕跡(誰、幾時、為什麼),日後查得出一個簽章
        是當日蓋的還是事後補的。補簽只擔保「由補簽那一刻起這一列沒有再被改過」。

        **見到對不上就停手**:任何一列快照類的簽章已經在案而內容對不上(落庫後被改動、
        或者簽章核不過),整道命令一列都不補,當場拋錯。那種情況補簽解決不了,亦不應該
        由補簽把痕跡蓋走——要按版本鏈重新登記,或者由人裁決。
        """
        note = str(reason).strip()
        if not note:
            raise ContractViolation("補簽必須講明為什麼;無理由的補簽等於把一列來歷不明的舊帳洗白")

        tables = tuple(
            table
            for table in ledger.GOVERNED_TABLES
            if ledger.category_of(table) == ledger.CATEGORY_SNAPSHOT
        )
        blocked = [
            finding
            for finding in ledger.verify(self._conn, self._key)
            if finding.category == ledger.CATEGORY_SNAPSHOT and finding.problem != ledger.UNSIGNED
        ]
        if blocked:
            raise ContractViolation(
                "快照類有 "
                + str(len(blocked))
                + " 處簽章對不上,補簽一列都不做:"
                + ";".join(str(finding) for finding in blocked)
                + "。這幾列補簽解決不了,請按版本鏈重新經唯一入口登記,或者交由人裁決"
            )

        done: list[Countersign] = []
        for table, row_key in ledger.unsigned_rows(self._conn, tables):
            ledger.countersign(
                self._conn, self._key, table, row_key, writer=self._writer, reason=note
            )
            done.append(Countersign(table=table, row_key=row_key, writer=self._writer, reason=note))
        return tuple(done)

    # ------------------------------------------------------------------
    # 核對與落點
    # ------------------------------------------------------------------

    def verify(self, *, factor_root: str | None = None) -> list[ledger.Finding]:
        """全庫核對:揪出繞過唯一入口寫入、或落庫後被改動的列,連因子值檔的雜湊。

        兩段:庫內受治理的表逐列核簽章(``ledger.verify``),然後**逐個因子值批次
        檔重讀再算一次雜湊**(D-032:值住檔案,全庫核對照管雜湊)。少了第二段,
        搬出去那 555 萬個值就等於搬出了核對範圍——庫檔清白而值早已被改過。

        檔案由登記那一列自己講出落點,所以 ``factor_root`` 只在讀一個不在預設
        落點的庫時才要給。
        """
        findings = ledger.verify(self._conn, self._key)
        for batch, problem, detail in self.factor_values(factor_root).check_files():
            findings.append(
                ledger.Finding(
                    "factor_value_batch",
                    f"{batch.batch_key}|{batch.snapshot_id}",
                    problem,
                    detail,
                )
            )
        findings.extend(self.snapshot_balance_findings())
        return findings

    def verify_report(self, *, factor_root: str | None = None) -> tuple[CategoryVerdict, ...]:
        """同一次核對,分**定義、因子批次、快照**三類講(KARST-087)。

        為什麼要分:一句「全庫清白」讀不出清白的是什麼。三邊的意思差很遠——定義髒了是
        策略的講法被人改過,因子批次髒了是值檔與登記對不上,快照髒了是取數的源頭被人
        動過。以前快照那一類根本不在治理清單內,所以那句「全庫清白」由頭到尾都沒有覆蓋
        過它,而讀報告的人無從得知。分三類列,「現在清白的是什麼」才答得出。
        """
        findings = self.verify(factor_root=factor_root)
        counts = self._governed_row_counts()
        return tuple(
            CategoryVerdict(
                category=category,
                row_count=counts[category],
                findings=tuple(
                    finding for finding in findings if finding.category == category
                ),
            )
            for category in ledger.CATEGORIES
        )

    def _governed_row_counts(self) -> dict[str, int]:
        """三類各自受治理幾多列。清白與否之外還要講這一格:零列的「清白」不是清白。"""
        counts = {category: 0 for category in ledger.CATEGORIES}
        for table in ledger.GOVERNED_TABLES:
            rows = self._conn.execute(f'SELECT COUNT(*) AS n FROM "{table}"').fetchone()["n"]
            counts[ledger.category_of(table)] += int(rows)
        return counts

    def snapshot_balance_findings(self) -> list[ledger.Finding]:
        """逐個數據快照核三數等式:宇宙表代號數 = 實體數 + 剔除數(KARST-084)。

        對不上就代表有兩個代號錨到同一個實體、其中一條價格序列被靜靜蓋走(D-026 第 2 條
        講明實體編號才是主鍵,代號只是帶生效期的屬性)。讀不到目錄或檔案的快照**略過
        不報**——那是「這部機上沒有這份檔」,不是「這個快照的宇宙表對不上」,兩件事不可
        混為一談。
        """
        from ..data.snapshots import universe_balance
        from ..data.errors import SnapshotBroken

        findings: list[ledger.Finding] = []
        for listing in self._store.list_snapshots():
            try:
                balance = universe_balance(self._store, listing.snapshot_id)
            except (SnapshotBroken, OSError, ValueError, KeyError):
                continue
            if not balance.balances:
                findings.append(
                    ledger.Finding(
                        "data_snapshot",
                        listing.snapshot_id,
                        "宇宙表三數等式對不上",
                        balance.describe(),
                    )
                )
        return findings

    def locate(self, kind: str, name: str) -> DefinitionLocation:
        return self._store.locate_definition(kind, name)

    # ------------------------------------------------------------------

    def _sign_snapshot_row(self, table: str, primary_key: Sequence[object]) -> None:
        """快照登記那道閘的簽章手(KARST-087)。庫身寫完一列即叫這一句,同一次寫入落地。

        用「蓋過就算數」那一種:同一批數據重凍會回同一個快照編號,而那一列一經落庫
        即不可改(trigger 擋住),原本那個簽章照舊有效。內容對不上就當場拋錯,
        不會用新內容蓋一個新簽章把痕跡蓋走。
        """
        ledger.record_write_once(
            self._conn, self._key, table, primary_key, writer=self._writer
        )

    def _sign(self, *rows: tuple[str, tuple[object, ...]]) -> tuple[str, ...]:
        signed: list[str] = []
        for table, primary_key in rows:
            key_text = ledger.record_write(
                self._conn, self._key, table, primary_key, writer=self._writer
            )
            signed.append(f"{table}[{key_text}]")
        return tuple(signed)

    def _sign_once(self, *rows: tuple[str, tuple[object, ...]]) -> tuple[str, ...]:
        """蓋簽章,但同一列蓋過就算數——給那幾種重覆呼叫回同一批列的登記用。"""
        signed: list[str] = []
        for table, primary_key in rows:
            key_text = ledger.record_write_once(
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
        *,
        reused: bool = False,
    ) -> WriteReceipt:
        return WriteReceipt(
            kind=kind,
            name=name,
            version_no=version_no,
            parent_version_id=parent_version_id,
            created_at=created_at,
            writer=self._writer,
            signed_rows=signed,
            reused=reused,
        )


SOURCE_KINDS: tuple[str, ...] = ("yfinance", "csv")


def resolve_universe(tickers: Sequence[str] | None) -> tuple[object, ...]:
    """把命令列給的代號查回起步宇宙名單上的那一員;留空即整份名單。

    **不猜**:名單上沒有的代號當場拒收。一個代號是公司還是 ETF、顯示名叫什麼,
    決定了它以 SEC CIK 還是內部代碼為錨(D-026 第 2 條),不是命令列可以憑空填的。
    """
    from ..data import STARTER_UNIVERSE, UNIVERSE_REGISTRY

    wanted = [str(ticker).strip().upper() for ticker in (tickers or ()) if str(ticker).strip()]
    if not wanted:
        return tuple(STARTER_UNIVERSE)

    known = {member.ticker.upper(): member for member in UNIVERSE_REGISTRY}
    members: list[object] = []
    seen: set[str] = set()
    for ticker in wanted:
        if ticker not in known:
            raise ValueError(
                f"宇宙名單登記上沒有代號 {ticker};"
                f"名單現有:{'、'.join(sorted(known))}。"
                "要加新代號請先在名單登記它是公司還是 ETF——這裡不猜"
            )
        if ticker in seen:
            continue
        seen.add(ticker)
        members.append(known[ticker])
    return tuple(members)


def build_source(kind: str | None, *, bars: str | None = None) -> object:
    """砌一個來源適配器。``yfinance`` 抓真數;``csv`` 由檔案重放同一批數。

    ``csv`` 那條路不是為測試而設的後門——它就是 D-026 第 7 條講的適配器形態:
    別的來源只要交得出同一套欄位(date、ticker、開高低收量),照樣經同一條管線
    入同一種快照。離線時它亦令命令列本身驗得到。
    """
    name = (kind or "yfinance").strip().lower()
    if name == "yfinance":
        from ..data import YFinanceSource

        return YFinanceSource()
    if name == "csv":
        import pandas as pd

        from ..data import StaticSource

        if not bars or not str(bars).strip():
            raise ValueError("來源 csv 要用 --bars 指出日線檔在哪(欄位:date、ticker、開高低收量)")
        return StaticSource(pd.read_csv(str(bars)), name="csv")
    raise ValueError(f"未知來源 {kind!r};現有:{'、'.join(SOURCE_KINDS)}")


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
