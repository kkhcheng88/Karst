"""KARST-032 讀取層:把庫內一次真實運行整理成頁面畫得出的形狀。

**只讀不寫。** 庫一律經 ``karst.store.DefinitionStore`` 開(D-027),序列經
``karst.runs.RunStore`` 讀回,指標經 ``karst.metrics`` 算,K 線經
``karst.data.snapshots`` 讀回。本層自己不碰 sqlite、不碰 parquet 格式,
亦不產生任何數值——所有數字都是上面那幾層算出來的。

頁面上一個寫死的數字都沒有:這裡拿不到的東西,前端就不顯示那一格。
"""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from karst.data.snapshots import read_price_frame, read_universe
from karst.errors import NotFound
from karst.metrics import (
    DEFAULT_BENCHMARK_TICKERS,
    benchmark_curve,
    run_metrics,
    trade_stats,
)
from karst.runs import BASE, RunStore
from karst.store import DefinitionStore

# 一年期無風險利率。Sortino 要它才算得出,而 karst.metrics 刻意不設預設值
# (逼呼叫方講明用了什麼口徑)。這裡明文寫在一處,並隨指標一齊送到頁面顯示,
# 令畫面上那個 Sortino 永遠交代得出它按什麼算。
DEFAULT_RISK_FREE_RATE = 0.04

DEFAULT_DB_FILENAME = "karst.sqlite"
DEFAULT_RUNS_DIRNAME = Path("data") / "runs"
DEFAULT_SNAPSHOTS_DIRNAME = Path("data") / "snapshots"


def _f(value: Any) -> float | None:
    """轉成 JSON 出得去的數:NaN／inf 一律當缺值,不讓它們流到畫面。"""
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _pct(value: Any) -> float | None:
    """比率轉百分點。0.1138 -> 11.38"""
    out = _f(value)
    return None if out is None else out * 100.0


def _day(value: Any) -> str:
    """日期一律出 ISO 字串——庫內有時是字串有時是 Timestamp。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:10]
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def open_read_only_store(db_path: str | Path) -> DefinitionStore:
    """以唯讀連線開庫。

    走 ``sqlite3`` 的 ``mode=ro`` 而不是 ``DefinitionStore.open()``,原因有二:
    一,``open()`` 會執行建表 DDL 並 commit,一個檢視器不應該寫庫;
    二,同一個庫可能正被別的工序寫住,唯讀連線不會跟它爭鎖。
    庫的讀法本身仍然全部經 ``DefinitionStore``(D-027)。
    """
    path = Path(db_path).resolve()
    if not path.is_file():
        raise NotFound(f"找不到定義庫:{path}")
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return DefinitionStore(conn)


class RunReader:
    """一次運行讀出來、整理成頁面要的形狀。"""

    def __init__(
        self,
        store: DefinitionStore,
        *,
        runs_root: str | Path,
        snapshot_root: str | Path,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        benchmarks: Iterable[str] = DEFAULT_BENCHMARK_TICKERS,
    ) -> None:
        self.store = store
        self.runs_root = Path(runs_root)
        self.snapshot_root = Path(snapshot_root)
        self.risk_free_rate = risk_free_rate
        self.benchmarks = tuple(benchmarks)
        self.runs = RunStore(store, self.runs_root)
        self._universe_cache: dict[str, dict[int, dict[str, str]]] = {}
        self._active_cache: dict[str, Any] = {}

    # ---------------- 身份與清單 ----------------

    def _active_setup(self, strategy_name: str):
        """該策略的現役設定;未指定就是 None——不猜、不頂替。"""
        if strategy_name not in self._active_cache:
            try:
                self._active_cache[strategy_name] = self.store.get_active_setup(strategy_name)
            except NotFound:
                self._active_cache[strategy_name] = None
        return self._active_cache[strategy_name]

    def _is_active_setup(self, record) -> bool:
        active = self._active_setup(record.strategy_name)
        if active is None:
            return False
        return (
            active.param_set_id == record.param_set_id
            and active.strategy_version_id == record.strategy_version_id
        )

    def _identity(self, record) -> dict[str, Any]:
        return {
            "runId": record.run_id,
            "strategyName": record.strategy_name,
            "strategyType": record.strategy_type,
            "strategyVersionNo": record.strategy_version_no,
            "paramSetName": record.param_set_name,
            "paramSetVersionNo": record.param_set_version_no,
            "rebalanceCadence": record.rebalance_cadence,
            "periodStart": record.period_start,
            "periodEnd": record.period_end,
            "snapshotId": record.snapshot_id,
            "engineName": record.engine_name,
            "engineVersion": record.engine_version,
            "tradingDays": record.trading_days,
            "createdAt": record.created_at,
            "isActiveSetup": self._is_active_setup(record),
        }

    def list_runs(self, limit: int | None = None) -> dict[str, Any]:
        """庫內運行,新的在前(登記本身由早到遲)。

        參數掃描一次就寫幾百個運行(KARST-029),庫內動輒上千個。按鈕列擺不下,
        所以這裡收窄到最近 ``limit`` 個,並照實回報總數,由頁面講明「共 N 次」。
        過時狀態只為真正列出那幾個算——逐個查一千次會拖死開頁。
        """
        records = list(reversed(self.runs.list_runs()))
        total = len(records)
        shown = records if limit is None else records[:limit]
        out = []
        for record in shown:
            item = self._identity(record)
            reasons = self.runs.stale_reasons(record.run_id)
            item["isStale"] = bool(reasons)
            item["staleReasons"] = list(reasons)
            out.append(item)
        return {"runs": out, "total": total, "shown": len(out)}

    def get_meta(self) -> dict[str, Any]:
        records = self.runs.list_runs()
        return {
            "runCount": len(records),
            "strategies": sorted({r.strategy_name for r in records}),
            "riskFreeRatePct": self.risk_free_rate * 100.0,
            "benchmarks": list(self.benchmarks),
        }

    # ---------------- 代號 ↔ 實體編號 ----------------

    def _universe(self, snapshot_id: str) -> dict[int, dict[str, str]]:
        """該快照一併凍結的宇宙名單。代號會被回收,所以一定要用運行自己那個快照。"""
        if snapshot_id not in self._universe_cache:
            frame = read_universe(self.store, snapshot_id, root=self.snapshot_root)
            self._universe_cache[snapshot_id] = {
                int(row.entity_id): {
                    "symbol": str(row.ticker),
                    "name": str(row.display_name),
                    "kind": str(row.entity_kind),
                }
                for row in frame.itertuples()
            }
        return self._universe_cache[snapshot_id]

    def _label(self, universe: dict[int, dict[str, str]], entity_id: int) -> dict[str, str]:
        known = universe.get(int(entity_id))
        if known:
            return known
        # 名單裡沒有這個實體:照實顯示編號,不虛構一個代號出來
        return {"symbol": f"#{entity_id}", "name": "", "kind": ""}

    # ---------------- 一次運行的全部畫圖資料 ----------------

    def get_run(self, run_id: str) -> dict[str, Any]:
        record = self.runs.get_run(run_id)
        universe = self._universe(record.snapshot_id)

        equity = self.runs.equity_curve(run_id)
        stats = self.runs.window_stats(run_id, base=BASE)
        orders = self.runs.orders(run_id)
        trades = trade_stats(orders, equity.index)

        metrics = run_metrics(
            self.runs,
            run_id,
            risk_free_rate=self.risk_free_rate,
            benchmarks=self.benchmarks,
            snapshot_root=self.snapshot_root,
        )

        identity = self._identity(record)
        reasons = self.runs.stale_reasons(run_id)
        identity["isStale"] = bool(reasons)
        identity["staleReasons"] = list(reasons)
        identity["paramValues"] = dict(record.param_values)
        identity["factors"] = [
            {
                "name": factor.name,
                "family": factor.family,
                "versionNo": factor.version_no,
                "factorId": factor.factor_id,
            }
            for factor in record.factors
        ]

        trade_rows = self._round_trip_rows(trades.round_trips, universe)

        return {
            "run": identity,
            "series": self._series(record, stats),
            "metrics": self._metrics(metrics),
            "trades": trade_rows,
            "tradeMarks": self._trade_marks(orders, trade_rows, universe),
        }

    def _series(self, record, stats) -> dict[str, Any]:
        """策略與兩條基準,三者皆由視窗起始日重設基準 100(design-system 3.8)。"""
        strategy = stats.equity
        out: dict[str, Any] = {
            "base": stats.base,
            "strategy": {
                "label": record.strategy_name,
                "dates": [_day(d) for d in strategy.index],
                "values": [_f(v) for v in strategy.to_numpy()],
            },
            "benchmarks": {},
        }
        for ticker in self.benchmarks:
            try:
                curve = benchmark_curve(
                    self.store,
                    record.snapshot_id,
                    ticker,
                    stats.start,
                    stats.end,
                    root=self.snapshot_root,
                    base=stats.base,
                )
            except (NotFound, KeyError):
                # 該快照的宇宙名單沒有這隻基準:那條線就不畫,不補假數據
                continue
            series = curve.equity
            out["benchmarks"][ticker] = {
                "dates": [_day(d) for d in series.index],
                "values": [_f(v) for v in series.to_numpy()],
                "totalReturnPct": _pct(curve.stats.total_return),
                "annualReturnPct": _pct(curve.stats.annual_return),
                "maxDrawdownPct": _pct(curve.stats.max_drawdown),
            }
        return out

    def _metrics(self, metrics) -> dict[str, Any]:
        """八項指標(D-020 第 8 條:策略層四項 + 運行層四項)。"""
        benchmarks = {
            ticker: {
                "totalReturnPct": _pct(cmp.total_return),
                "annualReturnPct": _pct(cmp.annual_return),
                "maxDrawdownPct": _pct(cmp.max_drawdown),
                "excessTotalReturnPct": _pct(cmp.excess_total_return),
                "annualExcessPct": _pct(cmp.annual_excess),
            }
            for ticker, cmp in metrics.benchmarks.items()
        }
        return {
            "start": metrics.start,
            "end": metrics.end,
            "tradingDays": metrics.trading_days,
            # 策略層四項
            "totalReturnPct": _pct(metrics.total_return),
            "annualReturnPct": _pct(metrics.annual_return),
            "maxDrawdownPct": _pct(metrics.max_drawdown),
            "winRatePct": _pct(metrics.win_rate),
            "profitLossRatio": _f(metrics.profit_loss_ratio),
            # 運行層再加四項
            "annualExcessPct": {k: _pct(v) for k, v in metrics.annual_excess.items()},
            "sortino": _f(metrics.sortino),
            "averageHoldingDays": _f(metrics.average_holding_days),
            "turnover": _f(metrics.turnover),
            # 口徑
            "closedTrades": metrics.closed_trades,
            "riskFreeRatePct": _pct(metrics.risk_free_rate),
            "benchmarks": benchmarks,
        }

    def _round_trip_rows(
        self, round_trips, universe: dict[int, dict[str, str]]
    ) -> list[dict[str, Any]]:
        """逐筆交易。FIFO 配對只出已平倉那些(karst.metrics.trades)。"""
        rows = []
        for index, trip in enumerate(round_trips, start=1):
            label = self._label(universe, trip.entity_id)
            entry_price = _f(trip.entry_price)
            exit_price = _f(trip.exit_price)
            ret_pct = None
            if entry_price and exit_price is not None and entry_price != 0:
                ret_pct = (exit_price / entry_price - 1.0) * 100.0
            rows.append(
                {
                    "id": f"T{index:04d}",
                    "entityId": int(trip.entity_id),
                    "symbol": label["symbol"],
                    "name": label["name"],
                    "entryDate": _day(trip.entry_date),
                    "exitDate": _day(trip.exit_date),
                    "shares": _f(trip.shares),
                    "entryPrice": entry_price,
                    "exitPrice": exit_price,
                    "fees": _f(trip.fees),
                    "profit": _f(trip.profit),
                    "retPct": ret_pct,
                    "holdDays": int(trip.holding_days),
                    "isWin": bool(trip.is_win),
                }
            )
        return rows

    def _trade_marks(
        self,
        orders: pd.DataFrame,
        trade_rows: list[dict[str, Any]],
        universe: dict[int, dict[str, str]],
    ) -> list[dict[str, Any]]:
        """把成交記錄按日子歸堆,好讓標記落在淨值圖對應那一日。"""
        by_entry: dict[tuple[str, int], str] = {}
        by_exit: dict[tuple[str, int], str] = {}
        for row in trade_rows:
            by_entry.setdefault((row["entryDate"], row["entityId"]), row["id"])
            by_exit.setdefault((row["exitDate"], row["entityId"]), row["id"])

        marks: dict[str, dict[str, Any]] = {}
        for order in orders.itertuples():
            day = _day(order.trade_date)
            entity_id = int(order.entity_id)
            side = str(order.side).lower()
            label = self._label(universe, entity_id)
            key = (day, entity_id)
            leg = {
                "id": (by_entry if side == "buy" else by_exit).get(key),
                "entityId": entity_id,
                "sym": label["symbol"],
                "shares": _f(order.shares),
                "px": _f(order.price),
            }
            mark = marks.setdefault(day, {"date": day, "buys": [], "sells": []})
            mark["buys" if side == "buy" else "sells"].append(leg)

        out = []
        for day in sorted(marks):
            mark = marks[day]
            buys, sells = len(mark["buys"]), len(mark["sells"])
            if buys and sells:
                mark["side"] = "both"
            elif sells:
                mark["side"] = "sell"
            else:
                mark["side"] = "buy"
            parts = []
            if buys:
                parts.append(f"買 {buys} 筆")
            if sells:
                parts.append(f"沽 {sells} 筆")
            mark["label"] = "・".join(parts)
            out.append(mark)
        return out

    # ---------------- 蠟燭圖 ----------------

    def get_candles(self, run_id: str, symbol: str) -> dict[str, Any]:
        """某實體在該次運行所綁那個數據快照裡的 K 線,連該次運行的買賣標記。"""
        record = self.runs.get_run(run_id)
        universe = self._universe(record.snapshot_id)

        wanted = symbol.strip().upper()
        entity_id = None
        for eid, info in universe.items():
            if info["symbol"].upper() == wanted:
                entity_id = eid
                break
        if entity_id is None:
            raise NotFound(
                f"數據快照 {record.snapshot_id} 的宇宙名單沒有 {symbol};畫不到它的蠟燭圖"
            )

        frame = read_price_frame(self.store, record.snapshot_id, root=self.snapshot_root)
        rows = frame.loc[frame["entity_id"] == entity_id].sort_values("date")

        candles = []
        volumes = []
        for row in rows.itertuples():
            day = _day(row.date)
            open_, high, low, close = _f(row.open), _f(row.high), _f(row.low), _f(row.close)
            if None in (open_, high, low, close):
                # 停牌／未上市那幾日照 D-026 留空,不補一根假 K 線
                continue
            candles.append(
                {"time": day, "open": open_, "high": high, "low": low, "close": close}
            )
            volume = _f(row.volume)
            if volume is not None:
                volumes.append({"time": day, "value": volume})

        orders = self.runs.orders(run_id)
        mine = orders.loc[orders["entity_id"] == entity_id]
        markers = []
        for order in mine.sort_values("trade_date").itertuples():
            side = str(order.side).lower()
            shares = _f(order.shares)
            price = _f(order.price)
            # 標記文字保持短:同一筆交易的進出場往往只隔幾日,文字一長就疊住對方。
            # 股數與費用在右邊的逐筆交易表看得到,這裡只講方向同成交價。
            price_text = "" if price is None else f"{price:,.2f}"
            markers.append(
                {
                    "time": _day(order.trade_date),
                    "side": side,
                    "text": ("買 " if side == "buy" else "沽 ") + price_text,
                    "shares": shares,
                    "price": price,
                }
            )

        equity = self.runs.equity_curve(run_id)
        trades = trade_stats(orders, equity.index)
        all_rows = self._round_trip_rows(trades.round_trips, universe)
        label = self._label(universe, entity_id)

        return {
            "runId": run_id,
            "entityId": entity_id,
            "symbol": label["symbol"],
            "name": label["name"],
            "kind": label["kind"],
            "snapshotId": record.snapshot_id,
            "candles": candles,
            "volumes": volumes,
            "markers": markers,
            "trades": [r for r in all_rows if r["entityId"] == entity_id],
        }


def build_reader(
    project_root: str | Path | None = None,
    *,
    db_path: str | Path | None = None,
    runs_root: str | Path | None = None,
    snapshot_root: str | Path | None = None,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
) -> RunReader:
    """照專案根組一個唯讀讀取層。路徑一律解成絕對,不靠 cwd。"""
    root = Path(project_root or Path.cwd()).resolve()
    store = open_read_only_store(db_path or root / DEFAULT_DB_FILENAME)
    return RunReader(
        store,
        runs_root=Path(runs_root or root / DEFAULT_RUNS_DIRNAME).resolve(),
        snapshot_root=Path(snapshot_root or root / DEFAULT_SNAPSHOTS_DIRNAME).resolve(),
        risk_free_rate=risk_free_rate,
    )
