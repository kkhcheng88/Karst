"""逐格跑掃描:每格一個運行編號,同一格重掃不重跑。

一次掃描就是同一套策略、同一段期間、同一個數據快照,只換參數跑很多次。所以:

* **每一格都是一次正正經經的運行**,經 ``karst.runs.RunStore`` 落痕,拿一個運行
  編號。掃描不另開一套帳,亦不繞過留痕——報告上任何一個數字,指得回它是哪一次
  運行算出來的(規格 7.4)。
* **同一格重掃不重跑**。運行編號是「策略版本 × 參數集 × 期間 × 數據快照 ×
  引擎版本」的雜湊(``store.run_fingerprint``),所以掃之前先算得出編號:庫裡已經
  有那一個編號,就直接讀回舊運行,一次引擎都不碰。中途斷了再掃,接得上。
* **超額只算一次基準**。一次掃描全部格的期間與快照按定義相同,QQQ / SPY 的年化
  自然一模一樣;逐格重算一次是白做。基準曲線按(快照 × 代號 × 起訖)入快取,
  真的有一格期間不同就會另算一條,不會靜靜地借錯尺。

**本層不揀最優**(D-008)。它只把整張表跑出來交給 ``karst.sweep.verdict`` 判、
交給 ``karst.sweep.report`` 畫;哪一格該用是用戶的事。
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import pandas as pd

from ..errors import ContractViolation, NotFound
from ..metrics import DEFAULT_BENCHMARK_TICKERS, BenchmarkComparison, RunMetrics, run_metrics
from ..metrics.benchmark import BenchmarkCurve, benchmark_curve
from ..runs import RunStore
from .grid import SweepGrid, SweepPoint
from .verdict import CellScore

# 掃描表固定會有的欄(參數欄排在最前,按掃描格的軸次序)。
METRIC_COLUMNS: tuple[str, ...] = (
    "total_return",
    "annual_return",
    "max_drawdown",
    "win_rate",
    "profit_loss_ratio",
    "sortino",
    "average_holding_days",
    "turnover",
)

TRACE_COLUMNS: tuple[str, ...] = (
    "run_id",
    "trades",
    "closed_trades",
    "trading_days",
    "start",
    "end",
    "reused",
    "seconds",
)


@dataclass(frozen=True, slots=True)
class CellPlan:
    """一格的身份:落痕時蓋住的來歷。運行編號就是由這幾件算出來的。

    期間**不可留空**。``RunStore.record_run`` 容許留空(它會取淨值頭尾兩日),
    但掃描要在跑之前就算得出運行編號來查重,所以期間一定要寫明——寫明了,
    整次掃描的每一格才確定是同一段日子,格與格之間的差異只可能來自參數本身。
    """

    strategy_name: str
    param_set_name: str
    snapshot_id: str
    engine_name: str
    engine_version: str
    period_start: str
    period_end: str
    strategy_version_no: int | None = None
    param_set_version_no: int | None = None
    factor_version_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        for label, value in (
            ("策略名", self.strategy_name),
            ("參數集名", self.param_set_name),
            ("數據快照編號", self.snapshot_id),
            ("引擎名", self.engine_name),
            ("引擎版本", self.engine_version),
            ("期間開始", self.period_start),
            ("期間結束", self.period_end),
        ):
            if not str(value or "").strip():
                raise ContractViolation(
                    f"掃描一格的{label}不可留空;留痕不齊就算不出運行編號,查不了重"
                )
        object.__setattr__(self, "factor_version_ids", tuple(int(i) for i in self.factor_version_ids))


@runtime_checkable
class CellJob(Protocol):
    """掃描要收的「一格怎樣跑」。兩件事:講得出身份、跑得出結果。

    ``plan`` 只做登記與查身份(例如把這一格的參數登記成一個參數集),**不可以
    跑引擎**——查重時只會叫 ``plan``,不會叫 ``simulate``。

    ``simulate`` 回一個 ``karst.runs.RunStore.record_simulation`` 收得的東西:有
    ``equity_curve``、``holdings``、``orders`` 三件即可。
    """

    def plan(self, point: SweepPoint) -> CellPlan: ...

    def simulate(self, point: SweepPoint) -> Any: ...


@dataclass(frozen=True, slots=True)
class SweepCell:
    """掃描表的一格:參數、運行編號、八項指標、成交筆數。

    ``metrics`` 是 ``karst.metrics`` 那份成績單。共用基準時它的 ``annual_excess``
    是空的——超額在本層另算(見 ``annual_excess`` / ``benchmarks``),因為一次掃描
    全部格的基準是同一條,逐格重算是白做。要看超額請讀本格這兩個欄位。
    """

    point: SweepPoint
    run_id: str
    plan: CellPlan
    metrics: RunMetrics
    trades: int
    reused: bool
    seconds: float
    annual_excess: dict[str, float] = field(default_factory=dict)
    benchmarks: dict[str, BenchmarkComparison] = field(default_factory=dict)

    def value_of(self, objective: str) -> float | None:
        return objective_value(self, objective)

    def as_row(self) -> dict[str, Any]:
        row: dict[str, Any] = dict(self.point.as_dict())
        for name in METRIC_COLUMNS:
            row[name] = getattr(self.metrics, name)
        for ticker in sorted(self.annual_excess):
            row[f"annual_excess_{ticker}"] = self.annual_excess[ticker]
        row.update(
            {
                "run_id": self.run_id,
                "trades": self.trades,
                "closed_trades": self.metrics.closed_trades,
                "trading_days": self.metrics.trading_days,
                "start": self.metrics.start,
                "end": self.metrics.end,
                "reused": self.reused,
                "seconds": round(self.seconds, 4),
            }
        )
        return row


@dataclass(frozen=True, slots=True)
class SweepProvenance:
    """這次掃描指得回哪一次運行設定:策略版本 × 期間 × 數據快照(規格 7.4)。

    一次掃描應該只有一套來歷;真的有兩套(例如中途換了快照)就會逐項列出來,
    報告照樣印得出——寧可讓人見到不一致,也不可以靜靜地當作同一次掃描。
    """

    strategies: tuple[str, ...]
    strategy_versions: tuple[int, ...]
    snapshots: tuple[str, ...]
    periods: tuple[tuple[str, str], ...]
    engines: tuple[str, ...]
    engine_versions: tuple[str, ...]
    param_set_names: tuple[str, ...]

    @property
    def consistent(self) -> bool:
        return (
            len(self.strategies) == 1
            and len(self.strategy_versions) <= 1
            and len(self.snapshots) == 1
            and len(self.periods) == 1
            and len(self.engines) == 1
            and len(self.engine_versions) == 1
        )

    def line(self) -> str:
        """報告頂那一行:掃的是哪一套策略的哪一版、哪一段、哪一個快照。"""
        version = (
            f"第 {self.strategy_versions[0]} 版" if len(self.strategy_versions) == 1 else "多個版本"
        )
        period = (
            f"{self.periods[0][0]} 至 {self.periods[0][1]}"
            if len(self.periods) == 1
            else f"{len(self.periods)} 段不同期間"
        )
        engine = (
            f"{self.engines[0]} {self.engine_versions[0]}"
            if len(self.engines) == 1 and len(self.engine_versions) == 1
            else "多個引擎"
        )
        snapshot = self.snapshots[0] if len(self.snapshots) == 1 else "多個快照"
        return (
            f"策略「{'、'.join(self.strategies)}」{version} × 期間 {period}"
            f" × 數據快照 {snapshot} × 引擎 {engine}"
        )


@dataclass(frozen=True, slots=True)
class SweepRun:
    """一次掃描跑完之後的全部東西:逐格成績、來歷、耗時。"""

    cells: tuple[SweepCell, ...]
    grid: SweepGrid
    provenance: SweepProvenance
    seconds: float
    reused: int
    risk_free_rate: float
    benchmark_tickers: tuple[str, ...]

    def __len__(self) -> int:
        return len(self.cells)

    @property
    def executed(self) -> int:
        """真正動過引擎的格數(其餘是讀回舊運行)。"""
        return len(self.cells) - self.reused

    def frame(self) -> pd.DataFrame:
        """整張掃描表。參數欄在前,八項指標在中,運行編號與成交筆數在後。"""
        rows = [cell.as_row() for cell in self.cells]
        if not rows:
            return pd.DataFrame()
        axes = list(self.grid.axis_names)
        excess = sorted({c for row in rows for c in row if c.startswith("annual_excess_")})
        columns = axes + list(METRIC_COLUMNS) + excess + list(TRACE_COLUMNS)
        frame = pd.DataFrame(rows)
        return frame[[c for c in columns if c in frame.columns]]

    def scores(self, objective: str) -> tuple[CellScore, ...]:
        """攤成判讀收的形狀:一格一個目標指標讀數,加成交筆數。"""
        return tuple(
            CellScore(point=cell.point, value=cell.value_of(objective), trades=cell.trades)
            for cell in self.cells
        )

    def cell_for(self, point: SweepPoint) -> SweepCell:
        for cell in self.cells:
            if cell.point == point:
                return cell
        raise ContractViolation(f"這次掃描沒有跑過 {point.label}")

    def run_ids(self) -> tuple[str, ...]:
        return tuple(cell.run_id for cell in self.cells)


def objective_value(cell: SweepCell, objective: str) -> float | None:
    """由一格的成績單取出目標指標。**一律越大越好**。

    收兩種名:八項指標的程式名(``annual_return``、``max_drawdown`` ……),
    以及對某一條基準的年化超額 ``annual_excess:SPY``。最大回撤在本倉以負數表示,
    所以「越大」就是「跌得越少」,方向不用另設參數。
    """
    name = str(objective or "").strip()
    if not name:
        raise ContractViolation("目標指標要寫明")
    if ":" in name:
        head, _, ticker = name.partition(":")
        head = head.strip()
        symbol = ticker.strip().upper()
        if head != "annual_excess":
            raise ContractViolation(
                f"帶基準的目標指標只有 annual_excess:<代號>,收到 {objective!r}"
            )
        if symbol not in cell.annual_excess:
            raise ContractViolation(
                f"這次掃描沒有算過對 {symbol} 的超額;算過的有:"
                f"{'、'.join(sorted(cell.annual_excess)) or '(一條都沒有)'}"
            )
        return float(cell.annual_excess[symbol])
    if name not in METRIC_COLUMNS:
        raise ContractViolation(
            f"沒有「{name}」這一項指標;可揀:{'、'.join(METRIC_COLUMNS)},"
            "或者 annual_excess:<基準代號>"
        )
    value = getattr(cell.metrics, name)
    return None if value is None else float(value)


def run_sweep(
    *,
    runs: RunStore,
    grid: SweepGrid,
    job: CellJob,
    risk_free_rate: float,
    benchmarks: Sequence[str] = DEFAULT_BENCHMARK_TICKERS,
    snapshot_root: str | Path | None = None,
    start: date | datetime | str | None = None,
    end: date | datetime | str | None = None,
    progress: Callable[[int, int, "SweepCell"], None] | None = None,
) -> SweepRun:
    """逐格跑,每格落一次痕,交回整張掃描表。

    ``job`` 講「一格怎樣跑」(見 ``CellJob``)。掃描本身**不認得任何一套策略**:
    因子混合、趨勢波段、日後任何一套,都是砌一個 ``job`` 交進來,本檔一個字不用改。

    ``risk_free_rate`` 無預設值(Sortino 的分子要用它,見 ``karst.metrics``)。
    ``benchmarks`` 有預設,因為基準不是可調參數,是 D-010 第 4 條裁死的 QQQ 與 SPY;
    離線合成數據那類快照裡沒有基準日線,傳 ``()`` 即這次不算超額。

    ``start`` / ``end`` 是檢視視窗:給了就八項指標全部按那一段重算(重看不重跑,
    規格 8.5),運行本身一個字不變。
    """
    if not isinstance(runs, RunStore):
        raise ContractViolation(f"要一個 RunStore,收到 {type(runs).__name__}")
    if not isinstance(grid, SweepGrid):
        raise ContractViolation(f"掃描格要是 SweepGrid,收到 {type(grid).__name__}")
    for method in ("plan", "simulate"):
        if not callable(getattr(job, method, None)):
            raise ContractViolation(
                f"掃描跑法缺 {method}();一格怎樣跑要由呼叫方講明(見 CellJob)"
            )

    points = grid.points()
    if not points:
        raise ContractViolation("這個掃描格一格都沒有")

    tickers = tuple(str(t).strip().upper() for t in benchmarks)
    curves: dict[tuple[str, str, str, str], BenchmarkCurve] = {}
    cells: list[SweepCell] = []
    reused_count = 0
    began = time.perf_counter()

    for index, point in enumerate(points, start=1):
        cell_began = time.perf_counter()
        plan = job.plan(point)
        if not isinstance(plan, CellPlan):
            raise ContractViolation(
                f"{point.label} 的 plan() 要回一個 CellPlan,收到 {type(plan).__name__}"
            )

        fingerprint = runs.store.run_fingerprint(
            strategy_name=plan.strategy_name,
            param_set_name=plan.param_set_name,
            period_start=plan.period_start,
            period_end=plan.period_end,
            snapshot_id=plan.snapshot_id,
            engine_name=plan.engine_name,
            engine_version=plan.engine_version,
            strategy_version_no=plan.strategy_version_no,
            param_set_version_no=plan.param_set_version_no,
            factor_version_ids=plan.factor_version_ids or None,
        )
        expected = runs.store.run_id_for(fingerprint)

        try:
            record = runs.get_run(expected)
            reused = True
        except NotFound:
            simulation = job.simulate(point)
            record = runs.record_simulation(
                simulation,
                strategy_name=plan.strategy_name,
                param_set_name=plan.param_set_name,
                snapshot_id=plan.snapshot_id,
                engine_version=plan.engine_version,
                engine_name=plan.engine_name,
                period_start=plan.period_start,
                period_end=plan.period_end,
                strategy_version_no=plan.strategy_version_no,
                param_set_version_no=plan.param_set_version_no,
                factor_version_ids=plan.factor_version_ids or None,
            )
            reused = False
            if record.run_id != expected:
                raise ContractViolation(
                    f"{point.label} 落痕之後的運行編號 {record.run_id} 與掃描之前算出來的"
                    f" {expected} 對不上;查重靠的正是這個編號,對不上即代表 plan() 與"
                    "真正落痕的來歷不是同一套,請先查明"
                )

        if reused:
            reused_count += 1

        metrics = run_metrics(
            runs,
            record.run_id,
            risk_free_rate=risk_free_rate,
            benchmarks=(),
            start=start,
            end=end,
            snapshot_root=snapshot_root,
        )

        comparisons: dict[str, BenchmarkComparison] = {}
        excess: dict[str, float] = {}
        for ticker in tickers:
            key = (record.snapshot_id, ticker, metrics.start, metrics.end)
            curve = curves.get(key)
            if curve is None:
                curve = benchmark_curve(
                    runs.store,
                    record.snapshot_id,
                    ticker,
                    metrics.start,
                    metrics.end,
                    root=snapshot_root,
                )
                curves[key] = curve
            # 與 karst.metrics.report 那條一模一樣:策略年化減基準年化。
            comparison = BenchmarkComparison(
                ticker=curve.ticker,
                entity_id=curve.entity_id,
                start=curve.stats.start,
                end=curve.stats.end,
                trading_days=curve.stats.trading_days,
                total_return=curve.stats.total_return,
                annual_return=curve.stats.annual_return,
                max_drawdown=curve.stats.max_drawdown,
                excess_total_return=float(metrics.total_return - curve.stats.total_return),
                annual_excess=float(metrics.annual_return - curve.stats.annual_return),
            )
            comparisons[curve.ticker] = comparison
            excess[curve.ticker] = comparison.annual_excess

        cell = SweepCell(
            point=point,
            run_id=record.run_id,
            plan=plan,
            metrics=metrics,
            trades=int(len(runs.orders(record.run_id))),
            reused=reused,
            seconds=time.perf_counter() - cell_began,
            annual_excess=excess,
            benchmarks=comparisons,
        )
        cells.append(cell)
        if progress is not None:
            progress(index, len(points), cell)

    return SweepRun(
        cells=tuple(cells),
        grid=grid,
        provenance=_provenance(cells),
        seconds=time.perf_counter() - began,
        reused=reused_count,
        risk_free_rate=float(risk_free_rate),
        benchmark_tickers=tickers,
    )


def _provenance(cells: Sequence[SweepCell]) -> SweepProvenance:
    def unique(values: Sequence[Any]) -> tuple[Any, ...]:
        out: list[Any] = []
        for value in values:
            if value is not None and value not in out:
                out.append(value)
        return tuple(out)

    return SweepProvenance(
        strategies=unique([c.plan.strategy_name for c in cells]),
        strategy_versions=unique([c.metrics.strategy_version_no for c in cells]),
        snapshots=unique([c.plan.snapshot_id for c in cells]),
        periods=unique([(c.plan.period_start, c.plan.period_end) for c in cells]),
        engines=unique([c.plan.engine_name for c in cells]),
        engine_versions=unique([c.plan.engine_version for c in cells]),
        param_set_names=unique([c.plan.param_set_name for c in cells]),
    )
