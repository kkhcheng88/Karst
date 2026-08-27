"""回測運行的序列存取:三條逐日序列落 parquet,登記表只記落點與雜湊。

分工照 D-026 第 1 條:大批數據住 parquet,單一定義庫只登記編號與路徑。一次
運行三份檔,按運行編號分目錄::

    <root>/run-1a2b3c4d5e6f7890/equity.parquet    逐日淨值
                               /holdings.parquet  逐日持倉(長表,只存持有的)
                               /orders.parquet    逐筆交易

保存這三條序列是「檢視視窗」的前提(規格 7.4、8.5):有了逐日淨值,另揀一段
日期重看就不用重跑引擎。

**接口是為引擎預留的**:``record_simulation`` 收的東西,形狀就是引擎適配層
交回來的 ``SimulationOutput`` / ``BacktestResult``(逐日淨值 + 逐日持倉 +
逐筆交易)。本檔刻意**不 import 引擎**——引擎是可換件(D-007 第 3 條),留痕
這一層不應該綁死在任何一個引擎的型別上。引擎票接上之前,先用
``karst.runs.synthetic`` 的合成序列走通全程。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

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

_FILE_NAMES = {
    "equity": "equity.parquet",
    "holdings": "holdings.parquet",
    "orders": "orders.parquet",
}


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
        period_start: date | datetime | str | None = None,
        period_end: date | datetime | str | None = None,
        strategy_version_no: int | None = None,
        param_set_version_no: int | None = None,
        factor_version_ids: Sequence[int] | None = None,
    ) -> RunRecord:
        """把一次運行的三條序列落檔並登記,回傳它的留痕。

        期間留空即取逐日淨值的頭尾兩日。同一組輸入重錄:序列內容一模一樣即當
        同一次運行,原封不動回舊記錄;內容不同即當改寫,**在動任何檔案之前**
        拒收(運行不可變,D-020 第 7 條)。
        """
        equity = normalise_equity(equity_curve)
        holdings_frame = _normalise_holdings(holdings)
        orders_frame = _normalise_orders(orders)

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

        return self._store.register_run(
            strategy_name=strategy_name,
            param_set_name=param_set_name,
            period_start=start,
            period_end=end,
            snapshot_id=snapshot_id,
            engine_name=engine_name,
            engine_version=engine_version,
            artifacts=artifacts,
            trading_days=int(len(equity)),
            strategy_version_no=strategy_version_no,
            param_set_version_no=param_set_version_no,
            factor_version_ids=factor_version_ids,
        )

    def record_simulation(
        self,
        simulation: Any,
        *,
        strategy_name: str,
        param_set_name: str,
        snapshot_id: str,
        engine_version: str,
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
            period_start=period_start,
            period_end=period_end,
            strategy_version_no=strategy_version_no,
            param_set_version_no=param_set_version_no,
            factor_version_ids=factor_version_ids,
        )

    # ------------------------------------------------------------------
    # 讀回
    # ------------------------------------------------------------------

    def get_run(self, run_id: str) -> RunRecord:
        return self._store.get_run(run_id)

    def list_runs(
        self, strategy_name: str | None = None, *, strategy_version_no: int | None = None
    ) -> list[RunRecord]:
        return self._store.list_runs(strategy_name, strategy_version_no=strategy_version_no)

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
