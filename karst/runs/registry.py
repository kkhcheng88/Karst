"""回測運行的序列存取:三條逐日序列落 parquet,登記表只記落點與雜湊。

分工照 D-026 第 1 條:大批數據住 parquet,單一定義庫只登記編號與路徑。一次
運行三份檔,按運行編號分目錄::

    <root>/run-1a2b3c4d5e6f7890/equity.parquet    逐日淨值
                               /holdings.parquet  逐日持倉(長表,只存持有的)
                               /orders.parquet    逐筆交易

保存這三條序列是「檢視視窗」的前提(規格 7.4、8.5):有了逐日淨值,另揀一段
日期重看就不用重跑引擎。

三條之外另收**查帳序列**(audit series):引擎交得出、查帳要用、但不是每條路徑
都有的逐日序列。規則路徑那兩條——逐日注碼基數與逐日熔斷狀態——就住在這裡::

    <root>/run-.../sizing_basis.parquet      逐日注碼基數
                  /breaker_blocked.parquet   逐日熔斷狀態
                  /audit.json                查帳序列的落點與雜湊

查帳序列**不入運行編號**:編號蓋的仍然是策略版本 × 參數集 × 期間 × 數據快照 ×
引擎版本那五件(規格 7.4),多存兩條序列不會令同一次運行變成另一次運行。它們
亦不算「必須保存的三條」——舊運行沒有這兩條,照樣讀得回、照樣核對得到。

**接口是為引擎預留的**:``record_simulation`` 收的東西,形狀就是引擎適配層
交回來的 ``SimulationOutput`` / ``BacktestResult``(逐日淨值 + 逐日持倉 +
逐筆交易)。本檔刻意**不 import 引擎**——引擎是可換件(D-007 第 3 條),留痕
這一層不應該綁死在任何一個引擎的型別上。引擎票接上之前,先用
``karst.runs.synthetic`` 的合成序列走通全程。
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any, Final

import pandas as pd

from ..batches import content_hash
from ..errors import ContractViolation, ImmutabilityViolation, NotFound
from ..models import as_date
from ..store import RUN_ARTIFACT_KINDS, DefinitionStore, RunArtifact, RunRecord
from .window import BASE, WindowStats, normalise_equity, window_stats

# 逐日持倉的長表欄位:一日一實體一列,只存**持有的**——沒有那一列就是當日沒持有
# (與因子值同制,D-021 第 4 條:缺失不填 0)。
HOLDING_COLUMNS = ("date", "entity_id", "shares")

# 逐筆交易的欄位。與引擎適配層 ``Order`` 同名同義,故引擎的訂單可以直接倒進來。
ORDER_COLUMNS = ("trade_date", "entity_id", "side", "shares", "price", "fees")

# 查帳序列(audit series)的種類。名與引擎交回來的欄位同名同義,故一句
# ``record_simulation(result, ...)`` 就自己接得上,不用逐條交代。
SIZING_BASIS = "sizing_basis"
BREAKER_BLOCKED = "breaker_blocked"
AUDIT_SERIES_KINDS: Final[tuple[str, ...]] = (SIZING_BASIS, BREAKER_BLOCKED)

# 查帳序列的欄位:一日一列。日期一律 ISO 字串,與逐日持倉、逐筆交易同制。
AUDIT_COLUMNS = ("date", "value")

# 查帳序列的數值型別:注碼基數是錢,熔斷狀態是有沒有落閘。
_AUDIT_DTYPES: Final[dict[str, str]] = {SIZING_BASIS: "float", BREAKER_BLOCKED: "bool"}

_FILE_NAMES = {
    "equity": "equity.parquet",
    "holdings": "holdings.parquet",
    "orders": "orders.parquet",
}

_AUDIT_FILE_NAMES = {kind: f"{kind}.parquet" for kind in AUDIT_SERIES_KINDS}

# 查帳序列的落點與雜湊住這一份小索引。登記表只認三條序列(``store.py``
# 的 ``RUN_ARTIFACT_KINDS``),查帳序列因此自己記自己的帳——有了它,
# 繞過本層直接改檔一樣核對得出。
AUDIT_INDEX_FILE = "audit.json"


class RunStore:
    """回測運行的門面:落痕、讀回逐日序列、在同一次運行上開檢視視窗。

    ``store`` 是單一定義庫(登記住這裡),``root`` 是序列 parquet 的根目錄。
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

    # ------------------------------------------------------------------
    # 落痕
    # ------------------------------------------------------------------

    def record_run(
        self,
        *,
        strategy_name: str,
        param_set_name: str,
        snapshot_id: str,
        engine_name: str,
        engine_version: str,
        equity_curve: pd.Series,
        holdings: pd.DataFrame,
        orders: Any,
        origin: str,
        sweep_id: str | None = None,
        period_start: date | datetime | str | None = None,
        period_end: date | datetime | str | None = None,
        strategy_version_no: int | None = None,
        param_set_version_no: int | None = None,
        factor_version_ids: Sequence[int] | None = None,
        audit_series: Mapping[str, Any] | None = None,
    ) -> RunRecord:
        """把一次運行的三條序列落檔並登記,回傳它的留痕。

        期間留空即取逐日淨值的頭尾兩日。同一組輸入重錄:序列內容一模一樣即當
        同一次運行,原封不動回舊記錄;內容不同即當改寫,**在動任何檔案之前**
        拒收(運行不可變,D-020 第 7 條)。

        ``origin`` 是來歷,**無預設值**:正式運行寫 ``FORMAL_RUN``,參數掃描其中
        一格寫 ``SWEEP_RUN`` 連 ``sweep_id``(KARST-054)。核在最前——來歷講不出
        就一份檔都不會落。

        ``audit_series`` 是查帳序列(見本檔開頭),``AUDIT_SERIES_KINDS`` 揀名。
        它**不入運行編號**;舊運行補交查帳序列會補寫上去,內容不同一樣拒收。
        """
        origin, sweep_id = self._store.check_run_origin(origin, sweep_id)
        equity = normalise_equity(equity_curve)
        holdings_frame = _normalise_holdings(holdings)
        orders_frame = _normalise_orders(orders)
        audit = _normalise_audit_series(audit_series)

        start = as_date(period_start, "period_start") if period_start is not None else str(
            equity.index[0].date()
        )
        end = as_date(period_end, "period_end") if period_end is not None else str(
            equity.index[-1].date()
        )
        if str(equity.index[0].date()) < start or str(equity.index[-1].date()) > end:
            raise ContractViolation(
                f"逐日淨值由 {equity.index[0].date()} 到 {equity.index[-1].date()},"
                f"蓋不入登記的期間 {start}~{end};期間是留痕的一部分,不可對不上"
            )

        payload = {
            "equity": equity.to_frame("equity"),
            "holdings": holdings_frame,
            "orders": orders_frame,
        }
        hashes = {kind: content_hash(frame) for kind, frame in payload.items()}

        fingerprint = self._store.run_fingerprint(
            strategy_name=strategy_name,
            param_set_name=param_set_name,
            period_start=start,
            period_end=end,
            snapshot_id=snapshot_id,
            engine_name=engine_name,
            engine_version=engine_version,
            strategy_version_no=strategy_version_no,
            param_set_version_no=param_set_version_no,
            factor_version_ids=factor_version_ids,
        )
        run_id = self._store.run_id_for(fingerprint)

        try:
            existing = self._store.get_run(run_id)
        except NotFound:
            existing = None
        if existing is not None:
            differing = [
                kind
                for kind, digest in hashes.items()
                if existing.artifacts[kind].content_hash != digest
            ]
            if differing:
                raise ImmutabilityViolation(
                    f"運行 {run_id} 已經留痕,但今次的{'、'.join(differing)}序列內容不同;"
                    "運行不可改寫——同一組策略版本 × 參數集 × 期間 × 數據快照 × 引擎版本"
                    "本應算出同一個結果,對不上即代表有一件沒有蓋住,請先查明"
                )
            # 三條序列一字不差,但這次多交了查帳序列:補寫上去,內容不同一樣拒收
            self._write_audit_series(run_id, audit)
            return existing

        directory = self._root / run_id
        directory.mkdir(parents=True, exist_ok=True)
        artifacts: list[RunArtifact] = []
        for kind in RUN_ARTIFACT_KINDS:
            frame = payload[kind]
            path = directory / _FILE_NAMES[kind]
            _write_parquet(frame, path, kind=kind, keep_index=(kind == "equity"))
            artifacts.append(
                RunArtifact(
                    kind=kind,
                    path=str(path),
                    content_hash=hashes[kind],
                    rows=int(len(frame)),
                )
            )

        record = self._store.register_run(
            strategy_name=strategy_name,
            param_set_name=param_set_name,
            period_start=start,
            period_end=end,
            snapshot_id=snapshot_id,
            engine_name=engine_name,
            engine_version=engine_version,
            artifacts=artifacts,
            trading_days=int(len(equity)),
            origin=origin,
            sweep_id=sweep_id,
            strategy_version_no=strategy_version_no,
            param_set_version_no=param_set_version_no,
            factor_version_ids=factor_version_ids,
        )
        self._write_audit_series(run_id, audit)
        return record

    def record_simulation(
        self,
        simulation: Any,
        *,
        strategy_name: str,
        param_set_name: str,
        snapshot_id: str,
        engine_version: str,
        origin: str,
        sweep_id: str | None = None,
        engine_name: str | None = None,
        period_start: date | datetime | str | None = None,
        period_end: date | datetime | str | None = None,
        strategy_version_no: int | None = None,
        param_set_version_no: int | None = None,
        factor_version_ids: Sequence[int] | None = None,
    ) -> RunRecord:
        """引擎那道門:收一份引擎交回來的結果,直接落痕。

        ``simulation`` 只需要有 ``equity_curve``、``holdings``、``orders`` 三件
        ——引擎適配層的 ``SimulationOutput`` / ``BacktestResult`` 正是這個形狀,
        故此引擎票接上之後,一句 ``record_simulation(result, ...)`` 就接得通,
        本檔不用改。有 ``engine_name`` 的話連引擎名都不用再講一次。

        結果上另有 ``sizing_basis`` / ``breaker_blocked`` 的話(規則路徑就有),
        兩條**查帳序列**一併落痕,不用另外交代;沒有就當這條路徑交不出,照樣落痕。

        ``origin`` 是來歷,無預設值(見 ``record_run``):掃描運行器逐格填
        ``SWEEP_RUN`` 連掃描編號,其餘一律 ``FORMAL_RUN``。
        """
        missing = [
            field
            for field in ("equity_curve", "holdings", "orders")
            if not hasattr(simulation, field)
        ]
        if missing:
            raise ContractViolation(
                f"運行結果缺:{'、'.join(missing)};留痕要逐日淨值、逐日持倉、逐筆交易三件"
            )
        audit = {
            kind: getattr(simulation, kind)
            for kind in AUDIT_SERIES_KINDS
            if getattr(simulation, kind, None) is not None
        }
        name = engine_name or getattr(simulation, "engine_name", None)
        if not name:
            raise ContractViolation(
                "缺引擎名稱:引擎是可換件(D-007 第 3 條),哪一個引擎跑出來的必須寫明"
            )
        if factor_version_ids is None:
            single = getattr(simulation, "factor_version_id", None)
            if single is not None:
                factor_version_ids = (int(single),)

        return self.record_run(
            strategy_name=strategy_name,
            param_set_name=param_set_name,
            snapshot_id=snapshot_id,
            engine_name=name,
            engine_version=engine_version,
            equity_curve=simulation.equity_curve,
            holdings=simulation.holdings,
            orders=simulation.orders,
            origin=origin,
            sweep_id=sweep_id,
            period_start=period_start,
            period_end=period_end,
            strategy_version_no=strategy_version_no,
            param_set_version_no=param_set_version_no,
            factor_version_ids=factor_version_ids,
            audit_series=audit,
        )

    # ------------------------------------------------------------------
    # 讀回
    # ------------------------------------------------------------------

    def get_run(self, run_id: str) -> RunRecord:
        return self._store.get_run(run_id)

    def list_runs(
        self,
        strategy_name: str | None = None,
        *,
        strategy_version_no: int | None = None,
        origin: str | None = None,
    ) -> list[RunRecord]:
        """歷次運行。``origin`` 收窄到一種來歷(見 ``DefinitionStore.list_runs``)。"""
        return self._store.list_runs(
            strategy_name, strategy_version_no=strategy_version_no, origin=origin
        )

    def equity_curve(self, run_id: str) -> pd.Series:
        """讀回逐日淨值。"""
        frame = self._read(run_id, "equity")
        return normalise_equity(frame)

    def holdings(self, run_id: str) -> pd.DataFrame:
        """讀回逐日持倉(長表:date、entity_id、shares;只有持有的才有列)。"""
        return self._read(run_id, "holdings")

    def orders(self, run_id: str) -> pd.DataFrame:
        """讀回逐筆交易。"""
        return self._read(run_id, "orders")

    def audit_kinds(self, run_id: str) -> tuple[str, ...]:
        """這次運行留了哪幾條查帳序列。回空即一條都沒有(例如排名再平衡那條路)。"""
        index = self._audit_index(run_id)
        return tuple(kind for kind in AUDIT_SERIES_KINDS if kind in index)

    def audit_series(self, run_id: str, kind: str) -> pd.Series:
        """讀回一條查帳序列,日期索引由早到遲。沒有那一條即拋 ``NotFound``。"""
        if kind not in AUDIT_SERIES_KINDS:
            raise ContractViolation(
                f"查帳序列只有 {list(AUDIT_SERIES_KINDS)},收到 {kind!r}"
            )
        entry = self._audit_index(run_id).get(kind)
        if entry is None:
            raise NotFound(f"運行 {run_id} 沒有留下{kind}這一條查帳序列")
        path = Path(entry["path"])
        if not path.exists():
            raise NotFound(f"運行 {run_id} 的 {kind} 查帳序列不在 {path}")
        return _audit_frame_to_series(pd.read_parquet(path, engine="pyarrow"), kind)

    def sizing_basis(self, run_id: str) -> pd.Series:
        """讀回逐日注碼基數:當日開市那一刻的權益(詞彙表「注碼基數」)。"""
        return self.audit_series(run_id, SIZING_BASIS)

    def breaker_blocked(self, run_id: str) -> pd.Series:
        """讀回逐日熔斷狀態:該日有沒有落閘停止新入場(詞彙表「月度虧損熔斷」)。"""
        return self.audit_series(run_id, BREAKER_BLOCKED)

    def equity_on(self, run_id: str, day: date | datetime | str) -> float:
        """某一日的淨值。那日不是這次運行的交易日就拋錯,不猜前一日。"""
        stamp = pd.Timestamp(as_date(day, "day"))
        series = self.equity_curve(run_id)
        if stamp not in series.index:
            raise NotFound(f"運行 {run_id} 沒有 {stamp.date()} 這一個交易日")
        return float(series.loc[stamp])

    def holdings_on(self, run_id: str, day: date | datetime | str) -> dict[int, float]:
        """某一日收工時持有什麼,實體編號 → 股數。全清倉即回空。"""
        stamp = as_date(day, "day")
        frame = self.holdings(run_id)
        rows = frame[frame["date"] == stamp]
        return {int(r.entity_id): float(r.shares) for r in rows.itertuples()}

    def window_stats(
        self,
        run_id: str,
        start: date | datetime | str | None = None,
        end: date | datetime | str | None = None,
        *,
        base: float = BASE,
    ) -> WindowStats:
        """在這次運行的逐日淨值上開一個檢視視窗:**重看,不重跑**(規格 8.5)。

        基準由該段起始日重設為 100;運行本身一個字都不會變。
        """
        return window_stats(self.equity_curve(run_id), start, end, base=base)

    def window_equity(
        self,
        run_id: str,
        start: date | datetime | str | None = None,
        end: date | datetime | str | None = None,
        *,
        base: float = BASE,
    ) -> pd.Series:
        """檢視視窗那一段的淨值線,起點已重設為 100。"""
        return self.window_stats(run_id, start, end, base=base).equity

    # ------------------------------------------------------------------
    # 過時與核對
    # ------------------------------------------------------------------

    def stale_reasons(self, run_id: str) -> tuple[str, ...]:
        """這次運行過時在哪(蓋住的版本不再是最新版)。沒有過時就回空。"""
        return self._store.run_stale_reasons(run_id)

    def is_stale(self, run_id: str) -> bool:
        return self._store.run_is_stale(run_id)

    def missing_series(self, run_id: str) -> tuple[str, ...]:
        """這次運行有哪幾條序列**不在磁碟上**。三條都在就回空。

        與 ``verify_run`` 的分別:那一個是「檔在,但內容改過」,這一個是「檔本身
        不見了」。兩者都不改登記——**定義表不可刪**(D-026):登記是一件已經發生
        的事,序列檔沒有了不等於那次運行沒有跑過。讀取層據此把它標成
        「過時運行(序列缺失)」,列得出它的來歷,但不當它是一次畫得出圖的運行。

        只看檔在不在,不讀內容:一次要問幾千個運行,逐個開 parquet 會拖死開頁。
        """
        record = self._store.get_run(run_id)
        return tuple(
            kind
            for kind in RUN_ARTIFACT_KINDS
            if not Path(record.artifact(kind).path).exists()
        )

    def series_intact(self, run_id: str) -> bool:
        return not self.missing_series(run_id)

    def verify_run(self, run_id: str) -> tuple[str, ...]:
        """重讀三份 parquet 再算一次雜湊,對不上登記的就報出來。

        回空即三條序列與落痕那一刻一模一樣。用來揪出繞過本層直接改檔的人。
        """
        record = self._store.get_run(run_id)
        mismatched: list[str] = []
        for kind in RUN_ARTIFACT_KINDS:
            frame = self._read(run_id, kind)
            if kind == "equity":
                frame = normalise_equity(frame).to_frame("equity")
            if content_hash(frame) != record.artifacts[kind].content_hash:
                mismatched.append(kind)
        return tuple(mismatched)

    def verify_audit_series(self, run_id: str) -> tuple[str, ...]:
        """重讀查帳序列再算一次雜湊,對不上 ``audit.json`` 記住那個就報出來。

        回空即全對(一條都沒留過也是回空——沒有留過就沒有東西會對不上)。
        """
        index = self._audit_index(run_id)
        mismatched: list[str] = []
        for kind, entry in sorted(index.items()):
            path = Path(entry["path"])
            if not path.exists():
                mismatched.append(kind)
                continue
            frame = pd.read_parquet(path, engine="pyarrow")
            if content_hash(frame) != entry["content_hash"]:
                mismatched.append(kind)
        return tuple(mismatched)

    # ------------------------------------------------------------------
    # 查帳序列的落檔與索引
    # ------------------------------------------------------------------

    def _audit_index(self, run_id: str) -> dict[str, dict[str, Any]]:
        """讀回這次運行的查帳序列索引。沒有那份檔即當一條都沒留過。"""
        self._store.get_run(run_id)            # 先確認真有這次運行
        path = self._root / run_id / AUDIT_INDEX_FILE
        if not path.exists():
            return {}
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return {str(kind): dict(entry) for kind, entry in loaded.items()}

    def _write_audit_series(self, run_id: str, audit: Mapping[str, pd.DataFrame]) -> None:
        """把查帳序列寫出去並更新索引。已有同名檔而內容不同即拒收,不覆蓋。"""
        if not audit:
            return
        directory = self._root / run_id
        directory.mkdir(parents=True, exist_ok=True)

        index = {}
        index_path = directory / AUDIT_INDEX_FILE
        if index_path.exists():
            index = {
                str(kind): dict(entry)
                for kind, entry in json.loads(index_path.read_text(encoding="utf-8")).items()
            }
        for kind, frame in sorted(audit.items()):
            path = directory / _AUDIT_FILE_NAMES[kind]
            _write_parquet(frame, path, kind=kind, keep_index=False)
            index[kind] = {
                "path": str(path),
                "content_hash": content_hash(frame),
                "rows": int(len(frame)),
            }
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _read(self, run_id: str, kind: str) -> pd.DataFrame:
        record = self._store.get_run(run_id)
        artifact = record.artifact(kind)
        path = Path(artifact.path)
        if not path.exists():
            raise NotFound(f"運行 {run_id} 的 {kind} 序列不在 {path}")
        return pd.read_parquet(path, engine="pyarrow")


def _write_parquet(frame: pd.DataFrame, path: Path, *, kind: str, keep_index: bool) -> None:
    """寫出一份序列。已經有同名檔就核對內容,對不上即拒收,不覆蓋。"""
    if path.exists():
        existing = pd.read_parquet(path, engine="pyarrow")
        if content_hash(existing) != content_hash(frame):
            raise ImmutabilityViolation(
                f"{path} 已經有一份內容不同的 {kind} 序列;運行的序列檔不覆蓋"
            )
        return
    frame.to_parquet(path, engine="pyarrow", index=keep_index)


def _normalise_audit_series(audit: Mapping[str, Any] | None) -> dict[str, pd.DataFrame]:
    """把查帳序列規範化成一日一列的表:``date`` 加 ``value``。

    種類要在 ``AUDIT_SERIES_KINDS`` 之內;空的一條不收——交一條沒有內容的序列
    等於甚麼都沒查,不如當場講清楚。
    """
    if not audit:
        return {}
    if not isinstance(audit, Mapping):
        raise ContractViolation(
            f"查帳序列要一份「種類 → 序列」的對照,收到 {type(audit).__name__}"
        )

    frames: dict[str, pd.DataFrame] = {}
    for kind, series in audit.items():
        name = str(kind)
        if name not in AUDIT_SERIES_KINDS:
            raise ContractViolation(
                f"查帳序列只有 {list(AUDIT_SERIES_KINDS)},收到 {kind!r}"
            )
        if isinstance(series, pd.DataFrame):
            if series.shape[1] != 1:
                raise ContractViolation(f"查帳序列「{name}」要一條序列,收到 {series.shape[1]} 欄")
            values = series.iloc[:, 0]
        elif isinstance(series, pd.Series):
            values = series
        else:
            raise ContractViolation(
                f"查帳序列「{name}」要一條 pandas 序列,收到 {type(series).__name__}"
            )
        if values.empty:
            raise ContractViolation(f"查帳序列「{name}」是空的")
        if values.isna().any():
            raise ContractViolation(
                f"查帳序列「{name}」有留空的日子;查帳序列逐日都要有數,不猜、不補值"
            )

        index = pd.DatetimeIndex(values.index)
        if index.has_duplicates:
            raise ContractViolation(f"查帳序列「{name}」有重複的交易日")
        frame = pd.DataFrame(
            {
                "date": [as_date(day, "date") for day in index],
                "value": values.to_numpy(dtype=_AUDIT_DTYPES[name]),
            },
            columns=list(AUDIT_COLUMNS),
        )
        frames[name] = frame.sort_values("date").reset_index(drop=True)
    return frames


def _audit_frame_to_series(frame: pd.DataFrame, kind: str) -> pd.Series:
    """把讀回來的查帳序列表還原成一條日期索引的序列。"""
    missing = [column for column in AUDIT_COLUMNS if column not in frame.columns]
    if missing:
        raise ContractViolation(f"查帳序列「{kind}」缺欄位:{'、'.join(missing)}")
    return pd.Series(
        frame["value"].to_numpy(dtype=_AUDIT_DTYPES[kind]),
        index=pd.DatetimeIndex(pd.to_datetime(frame["date"])),
        name=kind,
    ).sort_index()


def _normalise_holdings(holdings: Any) -> pd.DataFrame:
    """把逐日持倉規範化成長表:date、entity_id、shares,一日一實體一列。

    收兩種形狀:引擎慣用的**闊表**(日期 × 實體編號 → 股數)、或者已經是長表。
    股數為 0 或 NaN 的一律不存——沒有那一列就是當日沒持有,與因子值同制。
    """
    if not isinstance(holdings, pd.DataFrame):
        raise ContractViolation(
            f"逐日持倉要一張 pandas 表,收到 {type(holdings).__name__}"
        )
    if holdings.empty:
        raise ContractViolation("逐日持倉是空的;一次運行不會一日都沒持過倉")

    columns = {str(c) for c in holdings.columns}
    if {"entity_id", "shares"} <= columns:
        frame = holdings.copy()
        frame.columns = [str(c) for c in frame.columns]
        if "date" not in frame.columns:
            frame = frame.reset_index()
            frame.columns = ["date", *(str(c) for c in frame.columns[1:])]
        long = frame[list(HOLDING_COLUMNS)]
    else:
        try:
            entity_ids = [int(c) for c in holdings.columns]
        except (TypeError, ValueError) as exc:
            raise ContractViolation(
                "逐日持倉闊表的欄名要是實體編號(整數),不是交易代號——"
                "代號會被回收再發給別人(D-026 第 2 條)"
            ) from exc
        wide = pd.DataFrame(
            holdings.to_numpy(dtype=float),
            index=pd.DatetimeIndex(holdings.index),
            columns=entity_ids,
        ).sort_index()
        stacked = wide.stack()
        stacked.index = stacked.index.set_names(["date", "entity_id"])
        long = stacked.rename("shares").reset_index()

    long = long.copy()
    long["date"] = [as_date(d, "date") for d in long["date"]]
    long["entity_id"] = long["entity_id"].astype(int)
    long["shares"] = long["shares"].astype(float)
    long = long[long["shares"].notna() & (long["shares"] != 0.0)]
    long = long.sort_values(["date", "entity_id"]).reset_index(drop=True)
    if long.empty:
        raise ContractViolation("逐日持倉一列都不剩;一次運行不會一日都沒持過倉")
    return long[list(HOLDING_COLUMNS)]


def _normalise_orders(orders: Any) -> pd.DataFrame:
    """把逐筆交易規範化成一張表。

    收三種:一張表、一串 ``Order`` 那樣的物件(引擎適配層的型別)、或者一串
    ``dict``。一次都沒成交也收——那是一個真結果(訊號從未觸發),不是缺件。
    """
    if isinstance(orders, pd.DataFrame):
        frame = orders.copy()
        frame.columns = [str(c) for c in frame.columns]
        missing = [c for c in ORDER_COLUMNS if c not in frame.columns]
        if missing:
            raise ContractViolation(f"逐筆交易缺欄位:{'、'.join(missing)}")
        records = frame[list(ORDER_COLUMNS)].to_dict("records")
    elif isinstance(orders, Iterable):
        records = [_order_record(o, index) for index, o in enumerate(orders)]
    else:
        raise ContractViolation(
            f"逐筆交易要一張表或者一串成交,收到 {type(orders).__name__}"
        )

    frame = pd.DataFrame(records, columns=list(ORDER_COLUMNS))
    if frame.empty:
        return frame.astype(
            {
                "trade_date": "object",
                "entity_id": "int64",
                "side": "object",
                "shares": "float64",
                "price": "float64",
                "fees": "float64",
            }
        )
    frame["trade_date"] = [as_date(d, "trade_date") for d in frame["trade_date"]]
    frame["entity_id"] = frame["entity_id"].astype(int)
    frame["side"] = [str(s).strip().lower() for s in frame["side"]]
    for column in ("shares", "price", "fees"):
        frame[column] = frame[column].astype(float)
    bad = sorted(set(frame["side"]) - {"buy", "sell"})
    if bad:
        raise ContractViolation(f"成交方向只收 buy / sell,收到 {bad}")
    return frame.sort_values(["trade_date", "entity_id", "side"]).reset_index(drop=True)


def _order_record(order: Any, index: int) -> dict[str, Any]:
    if isinstance(order, Mapping):
        missing = [c for c in ORDER_COLUMNS if c not in order]
        if missing:
            raise ContractViolation(f"第 {index} 筆成交缺欄位:{'、'.join(missing)}")
        return {c: order[c] for c in ORDER_COLUMNS}
    missing = [c for c in ORDER_COLUMNS if not hasattr(order, c)]
    if missing:
        raise ContractViolation(f"第 {index} 筆成交缺欄位:{'、'.join(missing)}")
    return {c: getattr(order, c) for c in ORDER_COLUMNS}
