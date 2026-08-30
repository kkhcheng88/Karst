"""策略執行台(strategy executor):每條策略做法一模一樣的那一截,全部住這裡。

登記、驗參數、解析實體、叫引擎、查重、落痕、算指標、判失敗運行——策略只交一份
**策略合約**(見 ``contract.py``)。三條策略之間唯一真正不同的那四件留在策略那邊,
其餘每一件本來都在三個檔各抄一次(架構審視候選一,D-043)。

對外只掛三個名::

    Executor(gateway, runs, snapshot_root=None)

      .register(contract, *, strategy_name, snapshot_id, param_set_name,
                values, description, alignment) -> Setup
      .run(contract, *, setup, panel, values, period, engine_version,
           risk_free_rate, engine=None, extras=None) -> RunOutcome
      .sweep(contract, *, setup, grid, panel, period, engine_version,
             risk_free_rate, sweep_id, param_set_prefix, param_set_suffix,
             base_values, objective, min_trades, lonely_peak_margin,
             plateau_quantile, report, …) -> BatchOutcome
      .rejudge(table, grid, *, objective, thresholds, previous=None) -> Rejudgement

掃描(``sweep``)是同一條路走 N 次加一次判讀(KARST-091);它與 ``run`` 共用私有的
``_execute_cell``,分別只在來歷那一格(掃描格 + 掃描編號)、收不收選股痕跡、以及
參數由哪裡來三處。一次掃描 = 一個**批次**(D-042),收尾寫一列批次登記。

**一切寫入經唯一入口**(D-020 第 4 條):本檔一句直接寫庫都沒有。
"""

from __future__ import annotations

import hashlib
import statistics
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Final

import pandas as pd

from ..errors import ContractViolation, DuplicateDefinition, NotFound
from ..metrics import DEFAULT_BENCHMARK_TICKERS, RunMetrics, run_metrics
from ..runs import RunStore
from ..store import FORMAL_RUN, SWEEP_RUN, ParamSet, StrategyVersion
from ..store import ALIGNED as _STORE_ALIGNED
from ..store import ALIGNMENTS as _STORE_ALIGNMENTS
from ..store import EXIT_GOVERNANCES as _STORE_EXIT_GOVERNANCES
from ..store import LAYERS as _STORE_LAYERS
from ..store import SAMPLE as _STORE_SAMPLE
from .contract import (
    ENGINE_RULES,
    ENGINE_TARGETS,
    DuplicateExposureEntity,
    EngineNameMismatch,
    EntityNotInPanel,
    FactorVersionRef,
    ParamSpec,
    PlanShapeViolation,
    ResolvedEntity,
    RulePlan,
    RunRequest,
    StrategyContract,
    TargetPlan,
    UnresolvedTicker,
)

# 參數集自報自己是哪一種(D-038)。**無預設值**:未經與用戶對齊的示例取值不得
# 當作現役設定,而「它是哪一種」不是執行台猜得出的事。
#
# 取值的正本住在 ``karst.store``(與運行來歷 FORMAL_RUN/SWEEP_RUN 同制:庫身的
# CHECK 是最終正本,store 給程式一個名字用)。這裡只是轉引,不另寫一份——
# KARST-094 把標記落庫之後,庫、入口、執行台三邊必須認同一套字。
ALIGNED: Final[str] = _STORE_ALIGNED
SAMPLE: Final[str] = _STORE_SAMPLE
ALIGNMENTS: Final[dict[str, str]] = _STORE_ALIGNMENTS

# 補記既有參數集時的依據句(KARST-094):KARST-090 之前登記的參數集從來沒有人
# 申報過,而 D-038 已經講明它們未經與用戶對齊。
SAMPLE_BASIS: Final[str] = "D-038:未經用戶對齊"


@dataclass(frozen=True, slots=True)
class Setup:
    """一次登記的結果:策略版本、參數集、這次蓋住的因子版本。"""

    strategy: StrategyVersion
    param_set: ParamSet
    factors: tuple[FactorVersionRef, ...]
    snapshot_id: str
    alignment: str

    @property
    def factor_version_ids(self) -> tuple[int, ...]:
        return tuple(ref.factor_version_id for ref in self.factors)

    @property
    def is_active_candidate(self) -> bool:
        """這一組取值可不可以拿去做現役設定(D-038)。示例取值一律不可以。"""
        return self.alignment == ALIGNED


@dataclass(frozen=True, slots=True)
class Simulation:
    """引擎跑完之後、落痕之前的那一份結果。

    形狀正是 ``RunStore.record_simulation`` 收的那三件,加選股痕跡與策略自己的
    旁產物(趨勢波段的歷史案例表一類,執行台原樣交出、不解讀)。
    """

    equity_curve: pd.Series
    holdings: pd.DataFrame
    orders: tuple[Any, ...]
    engine_name: str
    selection: Any | None = None
    # 查帳序列(規則路徑才交得出;``RunStore`` 自己去這兩格拿,KARST-037)
    sizing_basis: pd.Series | None = None
    breaker_blocked: pd.Series | None = None
    extras: Mapping[str, Any] = field(default_factory=dict)

    @property
    def candidates(self) -> pd.DataFrame | None:
        return None if self.selection is None else self.selection.candidates

    @property
    def factor_scores(self) -> pd.DataFrame | None:
        return None if self.selection is None else self.selection.factor_scores

    @property
    def total_return(self) -> float:
        return float(self.equity_curve.iloc[-1] / self.equity_curve.iloc[0] - 1.0)

    def orders_frame(self) -> pd.DataFrame:
        """逐筆訂單攤成一張表,方便落檔與人眼核對。"""
        return pd.DataFrame(
            [
                {
                    "trade_date": order.trade_date,
                    "entity_id": order.entity_id,
                    "side": order.side,
                    "shares": order.shares,
                    "price": order.price,
                    "fees": order.fees,
                    "gross_value": order.gross_value,
                }
                for order in self.orders
            ],
            columns=["trade_date", "entity_id", "side", "shares", "price",
                     "fees", "gross_value"],
        )


@dataclass(frozen=True, slots=True)
class RunOutcome:
    """一次運行走完的結果。

    ``reused`` 為真即這一組輸入本來就有一次運行,一次引擎都沒有碰(KARST-052);
    ``failed`` 是失敗運行判定(D-034/D-040),兩隻基準有一隻算不出即 ``None``。
    """

    run_id: str
    record: Any
    reused: bool
    setup: Setup
    metrics: RunMetrics
    failed: bool | None
    simulation: Simulation | None = None


@dataclass(frozen=True, slots=True)
class FailedCell:
    """掃描途中拋錯那一格。

    記下來的用意只有一個:**它沒有靜靜消失**。一格拋錯不中斷整批(否則三千格跑
    到尾段炸掉就要整批重來),但它會以無效格的身份入判讀、入報告、入批次登記的
    錯誤格數——一個高地旁邊若果有幾格其實是炸掉的,讀報告的人有權見到。
    """

    point: Any
    error: str
    detail: str


@dataclass(frozen=True, slots=True)
class BatchReport:
    """一次掃描落哪一份報告。**無預設值**:落到哪、叫什麼名,不是執行台猜得出的。"""

    directory: str | Path
    title: str
    notes: str = ""


@dataclass(frozen=True, slots=True)
class BatchOutcome:
    """一次掃描走完的結果 = 一個**批次**(D-042)。

    ``reused_batch`` 為真即這個掃描編號本來就登記過、而且內容一模一樣,今次沒有
    新開一列(重掃同一幅格不應該多一列帳)。
    """

    sweep_id: str
    sweep: Any
    judgement: Any
    failures: tuple[FailedCell, ...]
    batch: Any
    reused_batch: bool
    report_path: Path

    @property
    def cells(self) -> tuple[Any, ...]:
        return self.sweep.cells

    @property
    def run_ids(self) -> tuple[str, ...]:
        return self.sweep.run_ids()


@dataclass(frozen=True, slots=True)
class Rejudgement:
    """一次重判:先用舊口徑對回落檔自檢,全對才出新判讀(KARST-047、048)。"""

    previous: Any | None
    judgement: Any
    reproduced: bool
    differences: tuple[str, ...] = ()


class Executor:
    """策略執行台。收唯一入口與運行庫,對外掛 register / run / rejudge。"""

    def __init__(
        self,
        gateway: Any,
        runs: RunStore,
        *,
        snapshot_root: str | Path | None = None,
    ) -> None:
        if not isinstance(runs, RunStore):
            raise ContractViolation(f"要一個 RunStore,收到 {type(runs).__name__}")
        if getattr(gateway, "store", None) is None:
            raise ContractViolation(
                "要一個唯一入口(Gateway);一切寫入經它蓋簽章,執行台不直接寫庫(D-020 第 4 條)"
            )
        self._gateway = gateway
        self._store = gateway.store
        self._runs = runs
        self._snapshot_root = snapshot_root

    @property
    def gateway(self) -> Any:
        return self._gateway

    @property
    def runs(self) -> RunStore:
        return self._runs

    # ------------------------------------------------------------------
    # register:登記因子、策略、參數集,全部經唯一入口
    # ------------------------------------------------------------------

    def register(
        self,
        contract: StrategyContract,
        *,
        strategy_name: str,
        snapshot_id: str,
        param_set_name: str,
        values: Mapping[str, Any],
        alignment: str,
        description: str | None = None,
        alignment_basis: str | None = None,
        aligned_on: str | None = None,
    ) -> Setup:
        """一次過登記因子、策略與參數集,回一個 ``Setup``。

        每條因子的產生程序記住這次用的**數據快照編號**:同名因子已在庫而快照不同
        即自動出新版(版本鏈,D-021 第 6、8、9 條);快照相同就原封不動沿用舊版。
        策略同制:引用的因子版本一樣就沿用,不一樣才出新版。參數集的沿用規矩
        (同名同節奏同取值即沿用舊版)住在唯一入口,本層不另抄一份(KARST-046)。

        ``alignment`` 無預設值:一個參數集要講得出它是**已對齊**還是**示例**
        (D-038)。執行台原樣記下,不替策略猜;自 KARST-094 起同時經唯一入口寫入
        對齊標記旁表,庫內查得到、``karst verify`` 核得到。
        """
        return register_setup(
            self._gateway,
            contract,
            strategy_name=strategy_name,
            snapshot_id=snapshot_id,
            param_set_name=param_set_name,
            values=values,
            alignment=alignment,
            description=description,
            alignment_basis=alignment_basis,
            aligned_on=aligned_on,
        )

    # ------------------------------------------------------------------
    # run:一次正式運行
    # ------------------------------------------------------------------

    def run(
        self,
        contract: StrategyContract,
        *,
        setup: Setup,
        panel: Any,
        period: tuple[str, str],
        engine_version: str,
        risk_free_rate: float,
        engine: Any | None = None,
        engine_name: str | None = None,
        values: Mapping[str, Any] | None = None,
        extras: Mapping[str, Any] | None = None,
        benchmarks: Sequence[str] = DEFAULT_BENCHMARK_TICKERS,
    ) -> RunOutcome:
        """跑一次**正式運行**,回運行編號、八項指標與失敗運行判定。

        次序固定:驗參數 → 解析實體 → ``contract.plan()`` → 核對計劃 → 算運行編號
        查重 → 命中即回舊運行(一格都沒改,回同一編號,KARST-052)→ 未命中即叫引擎
        → 落痕(來歷=正式運行)→ 寫選股痕跡 → 算指標與基準 → 判失敗運行。

        ``values`` 留空即由 ``setup.param_set`` 讀回——取值住在參數集,不住在碼裡。
        ``risk_free_rate`` 無預設值:Sortino 的分子要用它(KARST-030)。
        """
        spec = contract.param_spec()
        params = (
            spec.read(setup.param_set) if values is None else spec.validate(values)
        )
        record, reused, simulation, resolved_engine_name = self._execute_cell(
            contract,
            setup=setup,
            params=params,
            panel=panel,
            period=period,
            engine_version=engine_version,
            engine=engine,
            engine_name=engine_name,
            extras=extras,
            origin=FORMAL_RUN,
            sweep_id=None,
        )
        metrics = run_metrics(
            self._runs,
            record.run_id,
            risk_free_rate=risk_free_rate,
            benchmarks=benchmarks,
            snapshot_root=self._snapshot_root,
        )
        return RunOutcome(
            run_id=record.run_id,
            record=record,
            reused=reused,
            setup=setup,
            metrics=metrics,
            failed=self._judge_failed(metrics),
            simulation=simulation,
        )

    @staticmethod
    def _judge_failed(metrics: RunMetrics) -> bool | None:
        """失敗運行判定。呼叫讀取層那**同一份正本**,不另寫第二套(D-034/D-040)。"""
        from ..web.data import is_failed_run

        return is_failed_run(
            metrics.annual_return,
            {
                ticker: comparison.annual_return
                for ticker, comparison in metrics.benchmarks.items()
            },
        )

    def setup_from(
        self,
        contract: StrategyContract,
        *,
        strategy_name: str,
        snapshot_id: str,
        param_set_name: str,
        alignment: str,
        strategy_version_no: int | None = None,
        param_set_version_no: int | None = None,
    ) -> Setup:
        """由庫裡**已經有**的東西砌一份 ``Setup``。**一個字都不寫。**

        重掃、重判、由一次舊運行倒查來歷那幾條路要的是這個:它們接住的是一次已經
        發生過的登記,再登記一次只會把版本鏈無故推前一格,而版本號是運行編號的
        原料——那正是「本來查得回、不用重跑的格白跑一次」的來源。

        因子一律取**現行那一版**,與登記那條路同一個口徑。
        """
        key = str(alignment or "").strip()
        if key not in ALIGNMENTS:
            raise ContractViolation(
                f"參數集要自報是「已對齊」還是「示例」({sorted(ALIGNMENTS)} 揀一個),"
                f"收到 {alignment!r}(D-038)"
            )
        snapshot = str(snapshot_id or "").strip()
        if not snapshot:
            raise ContractViolation("要註明數據快照編號,追溯不可留空(D-021 第 8 條)")
        version = self._store.get_strategy_version(str(strategy_name).strip(), strategy_version_no)
        param_set = self._store.get_param_set(
            version.name,
            str(param_set_name).strip(),
            strategy_version_no=version.version_no,
            set_version_no=param_set_version_no,
        )
        factors = tuple(
            FactorVersionRef(
                name=spec.name,
                factor_version_id=self._store.get_factor_version(spec.name).factor_version_id,
                version_no=self._store.get_factor_version(spec.name).version_no,
            )
            for spec in contract.factor_specs(snapshot)
        )
        return Setup(
            strategy=version,
            param_set=param_set,
            factors=factors,
            snapshot_id=snapshot,
            alignment=key,
        )

    # ------------------------------------------------------------------
    # sweep:一次掃描 = 一個批次(D-042、KARST-091)
    # ------------------------------------------------------------------

    def sweep(
        self,
        contract: StrategyContract,
        *,
        setup: Setup,
        grid: Any,
        panel: Any,
        period: tuple[str, str],
        engine_version: str,
        risk_free_rate: float,
        sweep_id: str,
        param_set_prefix: str,
        param_set_suffix: str,
        base_values: Mapping[str, Any],
        objective: str,
        min_trades: int,
        lonely_peak_margin: float,
        plateau_quantile: float,
        report: "BatchReport",
        engine: Any | None = None,
        engine_name: str | None = None,
        extras: Mapping[str, Any] | None = None,
        benchmarks: Sequence[str] = DEFAULT_BENCHMARK_TICKERS,
        progress: Any | None = None,
    ) -> "BatchOutcome":
        """跑一次**掃描**,即一個**批次**:逐格落痕、判讀、落報告、登記批次。

        逐格走的是與 ``run`` **同一條** ``_execute_cell``,分別只有三格(見該方法的
        說明):來歷是掃描格而不是正式運行、不收選股痕跡、參數由掃描格逐格展開而
        不是由呼叫方交一組。所以「一次掃描」不是另一套編舞,是同一條路走 N 次加
        一次判讀。

        **一格拋錯不中斷整個批次。** 三千格跑到第 2,900 格才炸就要整批重跑,是白
        燒兩晚機。拋錯那一格記入 ``failures``,並以「算不出目標指標」的身份入判讀
        ——即**無效格**,不是靜靜消失:一個掃出來的高地若果旁邊三格其實是炸掉的,
        讀報告的人有權見到。

        **判讀口徑無預設值**(D-008 第 3 條)。目標指標與三個門檻逐格明寫,報告與
        批次登記都會把它們印出來——沒有口徑的「最佳格」是一句空話。

        參數集的名:``param_set_prefix`` + 掃描格那一格的短名 + ``param_set_suffix``。
        短名逐格由**參數規格**自己那一格的寫法砌出來(``ParamField.slug``),所以
        全倉只有這一條路寫得出——寫法一變,同一格重掃就會寫成另一個參數集、白白
        重跑一次。後綴留給「同一幅格、另一套帳戶設定」那類要另開一條命名線的情形
        (交易成本那一截),**無預設值**:不用就明寫空字串。
        """
        from ..sweep.runner import SweepCell, SweepRun, _provenance
        from ..sweep.verdict import CellScore, judge

        identifier = str(sweep_id or "").strip()
        if not identifier:
            raise ContractViolation(
                "這次掃描的掃描編號不可留空;逐格落庫要指得回它屬於哪一次掃描(KARST-054)"
            )
        prefix = str(param_set_prefix or "").strip()
        if not prefix:
            raise ContractViolation(
                "參數集名前綴不可留空;一格一個參數集名,沒有前綴會與別的掃描撞名"
            )
        points = tuple(grid.points())
        if not points:
            raise ContractViolation("這個掃描格一格都沒有")

        spec = contract.param_spec()
        start, end = (str(period[0]).strip(), str(period[1]).strip())
        tickers = tuple(str(t).strip().upper() for t in benchmarks)

        curves: dict[tuple[str, str, str, str], Any] = {}
        cells: list[SweepCell] = []
        failures: list[FailedCell] = []
        verdicts: dict[Any, bool | None] = {}
        reused_count = 0
        began = time.perf_counter()

        for index, point in enumerate(points, start=1):
            cell_began = time.perf_counter()
            try:
                cell, reused, failed = self._sweep_cell(
                    contract,
                    setup=setup,
                    spec=spec,
                    point=point,
                    base_values=base_values,
                    prefix=prefix,
                    suffix=str(param_set_suffix),
                    panel=panel,
                    period=(start, end),
                    engine_version=engine_version,
                    engine=engine,
                    engine_name=engine_name,
                    extras=extras,
                    sweep_id=identifier,
                    risk_free_rate=risk_free_rate,
                    tickers=tickers,
                    curves=curves,
                    began=cell_began,
                )
            except Exception as exc:  # noqa: BLE001 - 一格拋錯不中斷整批(D-043 嫁接第 2 件)
                failures.append(
                    FailedCell(
                        point=point,
                        error=type(exc).__name__,
                        detail=str(exc),
                    )
                )
                continue
            cells.append(cell)
            verdicts[point] = failed
            if reused:
                reused_count += 1
            if progress is not None:
                progress(index, len(points), cell)

        if not cells:
            raise ContractViolation(
                f"這次掃描 {len(points)} 格全部拋錯,一格都沒有跑出成績;"
                f"第一格報的是:{failures[0].error}:{failures[0].detail}"
            )

        run = SweepRun(
            sweep_id=identifier,
            cells=tuple(cells),
            grid=grid,
            provenance=_provenance(cells),
            seconds=time.perf_counter() - began,
            reused=reused_count,
            risk_free_rate=float(risk_free_rate),
            benchmark_tickers=tickers,
        )

        # 拋錯那幾格以「算不出目標指標」的身份入判讀 = 無效格,不是消失。
        scores = list(run.scores(objective)) + [
            CellScore(point=failure.point, value=None, trades=0) for failure in failures
        ]
        judgement = judge(
            scores,
            grid,
            objective=objective,
            min_trades=min_trades,
            lonely_peak_margin=lonely_peak_margin,
            plateau_quantile=plateau_quantile,
        )

        report_path = self._write_batch_report(run, judgement, report, failures)
        batch, reused_batch = self._register_batch(
            run,
            judgement,
            setup=setup,
            failed_by_point=verdicts,
            failures=failures,
            engine_version=engine_version,
            period=(start, end),
            report_path=report_path,
        )
        return BatchOutcome(
            sweep_id=identifier,
            sweep=run,
            judgement=judgement,
            failures=tuple(failures),
            batch=batch,
            reused_batch=reused_batch,
            report_path=report_path,
        )

    def _sweep_cell(
        self,
        contract: StrategyContract,
        *,
        setup: Setup,
        spec: ParamSpec,
        point: Any,
        base_values: Mapping[str, Any],
        prefix: str,
        suffix: str,
        panel: Any,
        period: tuple[str, str],
        engine_version: str,
        engine: Any | None,
        engine_name: str | None,
        extras: Mapping[str, Any] | None,
        sweep_id: str,
        risk_free_rate: float,
        tickers: Sequence[str],
        curves: dict[tuple[str, str, str, str], Any],
        began: float,
    ) -> tuple[Any, bool, bool | None]:
        """跑一格:砌參數集 → 走 ``_execute_cell`` → 算指標與共用基準。

        **超額只算一次基準**:一次掃描全部格的期間與快照按定義相同,QQQ / SPY 的
        年化自然一模一樣,逐格重算是白做。基準曲線按(快照 × 代號 × 起訖)入快取,
        真的有一格期間不同就會另算一條,不會靜靜地借錯尺。
        """
        from ..metrics.benchmark import benchmark_curve
        from ..metrics import BenchmarkComparison
        from ..sweep.runner import CellPlan, SweepCell

        values = {**dict(base_values or {}), **point.as_dict()}
        params = spec.validate(values)
        cadence, texts = spec.as_param_set(values)
        name = prefix + "-".join(
            spec.field(axis).slug(params[axis]) for axis, _ in point.values
        ) + suffix

        # 同名同節奏同取值即沿用舊版,那條規矩住在唯一入口(KARST-046),本層不另抄。
        param_set, _receipt = self._gateway.register_param_set(
            setup.strategy.name,
            param_set_name=name,
            rebalance_cadence=cadence,
            values=texts,
            strategy_version_no=setup.strategy.version_no,
        )
        cell_setup = Setup(
            strategy=setup.strategy,
            param_set=param_set,
            factors=setup.factors,
            snapshot_id=setup.snapshot_id,
            alignment=setup.alignment,
        )

        record, reused, _simulation, resolved_engine = self._execute_cell(
            contract,
            setup=cell_setup,
            params=params,
            panel=panel,
            period=period,
            engine_version=engine_version,
            engine=engine,
            engine_name=engine_name,
            extras=extras,
            origin=SWEEP_RUN,
            sweep_id=sweep_id,
        )

        metrics = run_metrics(
            self._runs,
            record.run_id,
            risk_free_rate=risk_free_rate,
            benchmarks=(),
            snapshot_root=self._snapshot_root,
        )

        comparisons: dict[str, Any] = {}
        excess: dict[str, float] = {}
        for ticker in tickers:
            key = (record.snapshot_id, ticker, metrics.start, metrics.end)
            curve = curves.get(key)
            if curve is None:
                curve = benchmark_curve(
                    self._store,
                    record.snapshot_id,
                    ticker,
                    metrics.start,
                    metrics.end,
                    root=self._snapshot_root,
                )
                curves[key] = curve
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

        plan = CellPlan(
            strategy_name=cell_setup.strategy.name,
            param_set_name=param_set.name,
            snapshot_id=cell_setup.snapshot_id,
            engine_name=resolved_engine,
            engine_version=str(engine_version).strip(),
            period_start=period[0],
            period_end=period[1],
            strategy_version_no=cell_setup.strategy.version_no,
            param_set_version_no=param_set.version_no,
            factor_version_ids=cell_setup.factor_version_ids,
        )
        cell = SweepCell(
            point=point,
            run_id=record.run_id,
            plan=plan,
            metrics=metrics,
            trades=int(len(self._runs.orders(record.run_id))),
            reused=reused,
            seconds=time.perf_counter() - began,
            annual_excess=excess,
            benchmarks=comparisons,
        )
        # 失敗運行判定走**同一份正本**(D-034/D-040):本層有基準年化在手,
        # 但判準不在這裡另寫一次。
        from ..web.data import is_failed_run

        failed = is_failed_run(
            metrics.annual_return,
            {ticker: comparison.annual_return for ticker, comparison in comparisons.items()},
        )
        return cell, reused, failed

    @staticmethod
    def _write_batch_report(
        run: Any, judgement: Any, report: "BatchReport", failures: Sequence["FailedCell"]
    ) -> Path:
        """落報告,回報告檔的路徑。拋錯那幾格在報告裡逐格講出來。"""
        from ..sweep.report import write_report

        notes = str(report.notes or "")
        if failures:
            listed = "、".join(
                f"{failure.point.label}({failure.error})" for failure in failures[:5]
            )
            tail = f",另有 {len(failures) - 5} 格" if len(failures) > 5 else ""
            notes = (
                f"{notes}\n\n" if notes else ""
            ) + (
                f"⚠ 這次掃描有 {len(failures)} 格拋錯,已按無效格入判讀(不中斷整批):"
                f"{listed}{tail}。"
            )
        return write_report(
            run,
            judgement,
            report.directory,
            title=report.title,
            notes=notes,
        )

    def _register_batch(
        self,
        run: Any,
        judgement: Any,
        *,
        setup: Setup,
        failed_by_point: Mapping[Any, bool | None],
        failures: Sequence["FailedCell"],
        engine_version: str,
        period: tuple[str, str],
        report_path: Path,
    ) -> tuple[Any, bool]:
        """經唯一入口寫一列批次登記(D-042、KARST-091)。

        **達標** = 這一格不是失敗運行(年化沒有同時輸給 SPY 與 QQQ,D-034/D-040)。
        兩隻基準有一隻算不出的格既不算達標亦不算失敗——寧可少判,不可拿一隻不齊的
        尺定它成敗;那幾格只入總格數。

        三個中位數只取**達標格**:D-042 明文把最佳批次定義為「達標運行的中位數年化
        最高」,把失敗那批混進中位數即是拿一堆已經判定不成立的成績去拉低(或拉高)
        門面數字。
        """
        qualified = [
            cell for cell in run.cells if failed_by_point.get(cell.point) is False
        ]
        failed_runs = sum(1 for cell in run.cells if failed_by_point.get(cell.point) is True)

        best = judgement.best
        robust = judgement.most_robust
        best_run_id: str | None = None
        if best is not None:
            for cell in run.cells:
                if cell.point == best.point:
                    best_run_id = cell.run_id
                    break

        digest = hashlib.sha256(Path(report_path).read_bytes()).hexdigest()
        return self._gateway.register_sweep_batch(
            run.sweep_id,
            strategy_name=setup.strategy.name,
            strategy_version_no=setup.strategy.version_no,
            period_start=period[0],
            period_end=period[1],
            snapshot_id=setup.snapshot_id,
            engine_name=run.provenance.engines[0] if run.provenance.engines else "",
            engine_version=str(engine_version).strip(),
            cell_count=len(run.cells) + len(failures),
            qualified_cells=len(qualified),
            failed_cells=failed_runs,
            error_cells=len(failures),
            median_annual_return=_median(c.metrics.annual_return for c in qualified),
            median_sortino=_median(c.metrics.sortino for c in qualified),
            median_max_drawdown=_median(c.metrics.max_drawdown for c in qualified),
            objective=judgement.objective,
            min_trades=judgement.min_trades,
            lonely_peak_margin=judgement.lonely_peak_margin,
            plateau_quantile=judgement.plateau_quantile,
            best_point=None if best is None else best.point.label,
            best_run_id=best_run_id,
            representative_point=None if robust is None else robust.point.label,
            report_path=str(report_path),
            report_hash=digest,
        )

    # ------------------------------------------------------------------
    # 一格怎樣走:run 與 sweep 共用同一條路
    # ------------------------------------------------------------------

    def _execute_cell(
        self,
        contract: StrategyContract,
        *,
        setup: Setup,
        params: Mapping[str, Any],
        panel: Any,
        period: tuple[str, str],
        engine_version: str,
        engine: Any | None,
        engine_name: str | None,
        extras: Mapping[str, Any] | None,
        origin: str,
        sweep_id: str | None,
    ) -> tuple[Any, bool, Simulation | None, str]:
        """驗參數 → 解析 → 計劃 → 核計劃 → 查重 → 跑引擎 → 落痕。

        一次運行與一次掃描的一格走的是**同一條路**,差別只有三格:來歷、收不收
        選股痕跡、參數由哪裡來——三格都在呼叫方那一邊,不在這裡。
        """
        if origin not in (FORMAL_RUN, SWEEP_RUN):
            raise ContractViolation(f"來歷只收正式運行或掃描格,收到 {origin!r}")
        start, end = (str(period[0]).strip(), str(period[1]).strip())

        # 1. 引擎:落痕寫的引擎名一定要與真正跑的那件對得上(運行編號的一部分)
        engine = self._engine_for(contract, engine)
        actual_name = getattr(engine, "name", type(engine).__name__)
        expected_name = str(engine_name).strip() if engine_name else actual_name
        if actual_name != expected_name:
            raise EngineNameMismatch(
                f"這一格由「{actual_name}」跑出來,但落痕寫的是「{expected_name}」;"
                "引擎名是運行編號的一部分,不可以對不上(D-007 第 3 條)"
            )

        # 2. 跑之前先算運行編號:庫裡已經有,就一次引擎都不碰(KARST-026、052)
        fingerprint = self._store.run_fingerprint(
            strategy_name=setup.strategy.name,
            param_set_name=setup.param_set.name,
            period_start=start,
            period_end=end,
            snapshot_id=setup.snapshot_id,
            engine_name=expected_name,
            engine_version=str(engine_version).strip(),
            strategy_version_no=setup.strategy.version_no,
            param_set_version_no=setup.param_set.version_no,
            factor_version_ids=setup.factor_version_ids or None,
        )
        expected_run_id = self._store.run_id_for(fingerprint)
        try:
            existing = self._runs.get_run(expected_run_id)
        except NotFound:
            existing = None
        if existing is not None:
            return existing, True, None, expected_name

        # 3. 解析實體(面板第一根 K 線那一日),策略不碰定義庫
        entities = self._resolve_entities(contract, params, panel)

        # 4. 策略本體。純函數:同一個 RunRequest 永遠出同一個 EnginePlan
        request = RunRequest(
            panel=panel,
            params=dict(params),
            entities=entities,
            factors={ref.name: ref for ref in setup.factors},
            snapshot_id=setup.snapshot_id,
            extras=dict(extras or {}),
        )
        plan = contract.plan(request)
        self._check_plan(contract, plan, entities)

        # 5. 叫引擎
        simulation = self._simulate(engine, panel, plan, engine_name=actual_name)

        # 6. 落痕。選股痕跡只有正式運行才收(見 RunStore.record_simulation)
        record = self._runs.record_simulation(
            simulation,
            strategy_name=setup.strategy.name,
            param_set_name=setup.param_set.name,
            snapshot_id=setup.snapshot_id,
            engine_version=str(engine_version).strip(),
            engine_name=expected_name,
            origin=origin,
            sweep_id=sweep_id,
            period_start=start,
            period_end=end,
            strategy_version_no=setup.strategy.version_no,
            param_set_version_no=setup.param_set.version_no,
            factor_version_ids=setup.factor_version_ids or None,
        )
        if record.run_id != expected_run_id:  # pragma: no cover - 兩條路同一份原料
            raise ContractViolation(
                f"落痕之後的運行編號 {record.run_id} 與跑之前算出來的 {expected_run_id} "
                "對不上;查重靠的正是這個編號,對不上即代表登記與落痕不是同一套來歷"
            )
        return record, False, simulation, expected_name

    # ------------------------------------------------------------------
    # 內部零件
    # ------------------------------------------------------------------

    @staticmethod
    def _engine_for(contract: StrategyContract, engine: Any | None) -> Any:
        return engine_for(contract, engine)

    def _resolve_entities(
        self, contract: StrategyContract, params: Mapping[str, Any], panel: Any
    ) -> dict[str, ResolvedEntity]:
        return resolve_entities(
            self._store,
            contract.needs_entities(params),
            on_date=panel.dates[0],
            known_entity_ids=tuple(getattr(panel, "entity_ids", ())),
        )

    @staticmethod
    def _check_plan(
        contract: StrategyContract,
        plan: Any,
        entities: Mapping[str, ResolvedEntity],
    ) -> None:
        """核對計劃的形狀(不變量 2-5)。策略繞不過這一關。"""
        if not isinstance(plan, (TargetPlan, RulePlan)):
            raise PlanShapeViolation(
                f"策略合約的 plan() 要回 TargetPlan 或 RulePlan,收到 {type(plan).__name__}"
            )

        stages = tuple(getattr(contract, "funnel_stages", ()) or ())
        trace = plan.selection
        if trace is not None:
            if not stages:
                raise PlanShapeViolation(
                    "這條策略宣告不用選股漏斗,卻交出了選股痕跡;宣告與產物要對得上(D-013)"
                )
            unknown = [name for name in trace.stages if name not in stages]
            if unknown:
                raise PlanShapeViolation(
                    f"選股痕跡有宣告以外的層:{'、'.join(unknown)};"
                    f"這條策略宣告的是:{'、'.join(stages)}(KARST-056)"
                )

        if isinstance(plan, RulePlan):
            return

        # 只做訊號的實體(大市那條線)在目標比重表裡永遠是 0 或者根本沒有那一欄
        signals = [e.entity_id for e in entities.values() if not e.tradable]
        columns = {int(column) for column in plan.targets.columns}
        for entity_id in signals:
            if entity_id in columns and float(plan.targets[entity_id].fillna(0.0).abs().max()) > 0.0:
                raise PlanShapeViolation(
                    f"實體 {entity_id} 報的是只做訊號,但目標比重表給了它一個非零比重;"
                    "只做訊號的線不可以持有(不變量 4)"
                )

        # 比重只可以寫在**執行日**那一行(D-021 第 3 條)
        if plan.rebalances:
            execution_days = {str(r.execution_date) for r in plan.rebalances}
            written = {
                str(pd.Timestamp(day).strftime("%Y-%m-%d"))
                for day in plan.targets.index[plan.targets.notna().any(axis=1)]
            }
            stray = sorted(written - execution_days)
            if stray:
                raise PlanShapeViolation(
                    f"目標比重寫在了非執行日:{'、'.join(stray[:5])}"
                    f"{'…' if len(stray) > 5 else ''};"
                    "決策日與執行日必須是相鄰兩根 K 線,成交取執行日開價(D-021 第 3 條)"
                )

    @staticmethod
    def _simulate(engine: Any, panel: Any, plan: Any, *, engine_name: str) -> Simulation:
        return simulate_plan(engine, panel, plan, engine_name=engine_name)

    # ------------------------------------------------------------------
    # rejudge:不重跑引擎,只換判讀口徑重判一次落檔的掃描表
    # ------------------------------------------------------------------

    @staticmethod
    def rejudge(
        scores: Sequence[Any],
        grid: Any,
        *,
        objective: str,
        thresholds: Mapping[str, Any],
        previous: Any | None = None,
        previous_grid: Any | None = None,
        previous_objective: str | None = None,
        previous_thresholds: Mapping[str, Any] | None = None,
    ) -> Rejudgement:
        """換一個判讀口徑,把一份落了檔的掃描表重判一次(KARST-047、048)。

        **不碰庫、不碰引擎**——它只讀成績,一格都不重跑,所以它是個靜態方法:
        執行台那三件家當(唯一入口、運行庫、快照根)它一件都用不着。給了
        ``previous``(當日那份判讀表)
        就先用**舊口徑**逐格對回落檔自檢,全對才出新判讀——對不上即代表兩邊讀的
        不是同一份成績,寧可講出來,不出一份看似合理的新判讀(CONTEXT.md「重判」)。

        ``thresholds`` 是判讀的四個門檻(``min_trades``、``lonely_peak_margin``、
        ``plateau_quantile``、``ridge_margin`` 一類),**一個預設值都沒有**:它們
        是判讀的口徑,不是本層代決定的事(D-008 第 3 條),報告一定要印出來。
        """
        from ..sweep.verdict import judge

        reproduced = True
        differences: list[str] = []
        if previous is not None:
            old = judge(
                scores,
                previous_grid if previous_grid is not None else grid,
                objective=previous_objective or objective,
                **dict(previous_thresholds if previous_thresholds is not None else thresholds),
            )
            differences = _verdict_differences(previous, old)
            reproduced = not differences
            if not reproduced:
                raise ContractViolation(
                    f"舊口徑對不回落檔那份判讀,{len(differences)} 格有出入:"
                    f"{'、'.join(differences[:5])}{'…' if len(differences) > 5 else ''};"
                    "自檢不過就不出新判讀(KARST-047)"
                )

        return Rejudgement(
            previous=previous,
            judgement=judge(scores, grid, objective=objective, **dict(thresholds)),
            reproduced=reproduced,
            differences=tuple(differences),
        )


# ----------------------------------------------------------------------
# 四段共用零件。執行台走一次運行用它們,尚未搬完的舊路徑(掃描跑法)亦用它們——
# 所以「怎樣登記」「揀哪一件引擎」「代號怎樣解析」「引擎點樣叫」全倉各只此一份。
# ----------------------------------------------------------------------


def register_setup(
    gateway: Any,
    contract: StrategyContract,
    *,
    strategy_name: str,
    snapshot_id: str,
    param_set_name: str,
    values: Mapping[str, Any],
    alignment: str,
    description: str | None = None,
    alignment_basis: str | None = None,
    aligned_on: str | None = None,
) -> Setup:
    """登記因子、策略、參數集,回一個 ``Setup``。**一切寫入經唯一入口。**

    自 KARST-094 起,``alignment`` 那個申報不再只掛在記憶體:登記完參數集即經唯一
    入口把它寫入對齊標記旁表,逐列蓋簽章(D-038 要求「畫面與紀錄須能分辨」)。
    標記走旁表、不進參數集內容,所以寫它一列,運行編號與既有簽章一位都不動。

    ``alignment_basis`` 是對齊依據那一句。標為**示例**時可以不給——D-038 已經替
    全部未對齊的取值講了那一句(見 ``SAMPLE_BASIS``),再要每個呼叫點抄一次只會
    抄出十個講法。標為**已對齊**時一定要給,連同 ``aligned_on`` 對齊日期:講不出
    依據哪一次對話、哪一日對的,就不算對齊過(D-038),當場拒收而不是填一個預設。
    """
    snapshot = str(snapshot_id or "").strip()
    if not snapshot:
        raise ContractViolation("登記要註明數據快照編號,追溯不可留空(D-021 第 8 條)")
    key = str(alignment or "").strip()
    if key not in ALIGNMENTS:
        raise ContractViolation(
            f"參數集要自報是「已對齊」還是「示例」({sorted(ALIGNMENTS)} 揀一個),"
            f"收到 {alignment!r};未經與用戶對齊的示例取值不得當作現役設定(D-038)"
        )
    name = str(strategy_name or "").strip()
    if not name:
        raise ContractViolation("策略名不可留空")

    factors = _register_factors(gateway, contract, snapshot)
    version = _register_strategy(
        gateway, contract, name, factors, description=description
    )

    spec = contract.param_spec()
    cadence, texts = spec.as_param_set(values)
    param_set, _ = gateway.register_param_set(
        version.name,
        param_set_name=str(param_set_name).strip(),
        rebalance_cadence=cadence,
        values=texts,
        strategy_version_no=version.version_no,
    )
    # 申報落庫(KARST-094)。走旁表,不碰參數集內容:寫這一列,運行編號與既有簽章
    # 一位都不動。同名同值的參數集沿用舊版時,重覆申報同一件事亦不會白加一列。
    basis = str(alignment_basis or "").strip()
    if key == ALIGNED and not basis:
        raise ContractViolation(
            "標為「已對齊」要講明對齊依據一句(alignment_basis):"
            "講不出依據哪一次對話或哪張票,就不算與用戶對齊過(D-038)"
        )
    gateway.mark_param_set_alignment(
        param_set.param_set_id,
        mark=key,
        basis=basis or SAMPLE_BASIS,
        aligned_on=aligned_on,
    )
    return Setup(
        strategy=version,
        param_set=param_set,
        factors=factors,
        snapshot_id=snapshot,
        alignment=key,
    )


def _register_factors(
    gateway: Any, contract: StrategyContract, snapshot_id: str
) -> tuple[FactorVersionRef, ...]:
    """同名因子改用另一個快照即自動出新版(版本鏈,D-021 第 6、8、9 條)。"""
    store = gateway.store
    specs = tuple(contract.factor_specs(snapshot_id))
    if not specs:
        raise ContractViolation(
            "策略合約一條因子都沒有宣告;運行編號要蓋住因子版本,不可以空手"
        )
    for spec in specs:
        stamped = getattr(spec.procedure, "input_data_version", None)
        if stamped is not None and str(stamped) != snapshot_id:
            raise ContractViolation(
                f"因子「{spec.name}」的產生程序寫住輸入數據版本 {stamped},"
                f"但這次的數據快照是 {snapshot_id};追溯對不上(D-021 第 8 條)"
            )
        try:
            gateway.register_factor(
                spec.name,
                scale_kind=spec.scale_kind,
                procedure=spec.procedure,
                description=spec.description,
            )
        except DuplicateDefinition:
            head = store.get_factor_version(spec.name)
            if getattr(head.procedure, "input_data_version", None) != snapshot_id:
                gateway.new_factor_version(
                    spec.name,
                    scale_kind=head.scale_kind,
                    procedure=spec.procedure,
                    description=spec.description,
                )
    return tuple(
        FactorVersionRef(
            name=spec.name,
            factor_version_id=store.get_factor_version(spec.name).factor_version_id,
            version_no=store.get_factor_version(spec.name).version_no,
        )
        for spec in specs
    )


def _register_strategy(
    gateway: Any,
    contract: StrategyContract,
    strategy_name: str,
    factors: Sequence[FactorVersionRef],
    *,
    description: str | None,
) -> StrategyVersion:
    """引用的因子版本一樣就沿用舊策略版本,不一樣才出新版。

    合約兩格必填(``layer``、``exit_governance``)在這裡交去唯一入口(D-058 第 1 條)。
    策略**已經在庫**那條路一樣要過閘,見 ``check_governance``:登記過一次不等於從此
    不用答,否則一條策略只要曾經登記過,合約改成什麼都沒有人核。
    """
    refs = [f"{ref.name}@{ref.version_no}" for ref in factors]
    layer = getattr(contract, "layer", None)
    exit_governance = getattr(contract, "exit_governance", None)
    try:
        version, _ = gateway.register_strategy(
            strategy_name,
            strategy_type=contract.strategy_type,
            layer=layer,
            exit_governance=exit_governance,
            factor_refs=refs,
            description=description,
        )
    except DuplicateDefinition:
        head = gateway.store.get_strategy_version(strategy_name)
        check_governance(gateway, head, layer=layer, exit_governance=exit_governance)
        current = sorted(f"{f.name}@{f.version_no}" for f in head.factors)
        if current == sorted(refs):
            version = head
        else:
            version, _ = gateway.new_strategy_version(
                strategy_name, factor_refs=refs, description=description
            )
    return version


# 補填一條 D-058 之前登記、庫內未有治理宣告的策略時,依據那一句。
GOVERNANCE_BASIS: Final[str] = "D-058:登記時由策略合約宣告"

# 合約與庫內宣告對不上時的講法。**不自動改庫**:哪一邊才對是要人判的事。
_GOVERNANCE_DRIFT: Final[str] = (
    "策略「{name}」的治理宣告對不上:庫內宣告是{recorded},"
    "但策略合約現時宣告的是{declared}。"
    "宣告是加一筆新的、不是靜靜覆蓋——真要改編制請經唯一入口"
    "(gateway.declare_strategy_governance)講明依據宣告一次,"
    "改錯了方向的合約請改回合約(D-054、D-056、D-058)"
)


def check_governance(
    gateway: Any,
    head: StrategyVersion,
    *,
    layer: Any,
    exit_governance: Any,
) -> None:
    """已在庫的策略:合約那兩格與庫內宣告要對得上。

    三種情況三種做法:庫內**未宣告**(D-058 之前登記的)即照合約補一筆,經唯一入口
    留簽章;**對得上**即什麼都不做;**對不上**當場拒收——一邊是庫、一邊是碼,哪一邊
    才是真的不是這裡判得出的事,靜靜覆蓋等於把當日那個判斷抹走。
    """
    recorded = gateway.store.strategy_governance(head.strategy_id)
    if recorded is None:
        gateway.declare_strategy_governance(
            head.name,
            layer=layer,
            exit_governance=exit_governance,
            basis=GOVERNANCE_BASIS,
        )
        return
    if recorded.layer == layer and recorded.exit_governance == exit_governance:
        return
    raise ContractViolation(
        _GOVERNANCE_DRIFT.format(
            name=head.name,
            recorded=f"{_STORE_LAYERS[recorded.layer]}層 / "
                     f"{_STORE_EXIT_GOVERNANCES[recorded.exit_governance]}",
            declared=f"{_STORE_LAYERS.get(layer, layer)}層 / "
                     f"{_STORE_EXIT_GOVERNANCES.get(exit_governance, exit_governance)}",
        )
    )


def engine_for(contract: StrategyContract, engine: Any | None) -> Any:
    """留空即用預設引擎。**遲到這一刻才 import**:換了引擎的人不必裝 vectorbt。"""
    if engine is not None:
        return engine
    if getattr(contract, "engine_path", ENGINE_TARGETS) == ENGINE_RULES:
        from ..engine.vectorbt_engine import VectorbtRuleEngine

        return VectorbtRuleEngine()
    from ..engine.vectorbt_engine import VectorbtEngine

    return VectorbtEngine()


def resolve_entities(
    store: Any,
    request: Any,
    *,
    on_date: Any,
    known_entity_ids: Sequence[int] = (),
) -> dict[str, ResolvedEntity]:
    """代號一律經 ``store.resolve_ticker`` **按面板第一根 K 線那一日**解析。

    ETF 與股票同一條路、同一張映射表(D-026 第 2 條);適配層一個為 ETF 而設的
    分支都沒有,分別只在解析出來那一欄 ``entity_kind``。

    ``known_entity_ids`` 留空即不核對面板——持得到的代號解析出來卻不在面板裡,
    是落不到注的,給了面板就當場拒收。
    """
    known = {int(entity) for entity in known_entity_ids}
    resolved: dict[str, ResolvedEntity] = {}
    seen: dict[int, str] = {}
    for ticker in request.tickers:
        tradable = ticker in request.exposures
        try:
            entity_id = int(store.resolve_ticker(ticker, on_date))
        except NotFound as exc:
            raise UnresolvedTicker(
                f"{on_date} 的代號 {ticker} 解析不到實體;代號只是有生效期的屬性"
                "(D-026 第 2 條),解析不到就落不到注,不猜"
            ) from exc
        if entity_id in seen:
            raise DuplicateExposureEntity(
                f"{on_date} 的代號 {ticker} 解析到實體 {entity_id},"
                f"但 {seen[entity_id]} 已經佔了同一個實體;一個可投資對象不可佔兩格"
            )
        seen[entity_id] = ticker
        if tradable and known and entity_id not in known:
            raise EntityNotInPanel(
                f"代號 {ticker} 解析到實體 {entity_id},但價格面板沒有它;"
                "沒有價格就落不到注,不猜、不當零"
            )
        entity = store.get_entity(entity_id)
        resolved[ticker] = ResolvedEntity(
            ticker=ticker,
            entity_id=entity_id,
            entity_kind=entity.entity_kind,
            tradable=tradable,
        )
    return resolved


def simulate_plan(engine: Any, panel: Any, plan: Any, *, engine_name: str) -> Simulation:
    """兩條引擎路徑在這裡分岔,**全倉只分岔這一次**。

    目標比重路徑要的組合參數,適配層現時只有 ``RankingRebalanceParams`` 一個
    型別——排名那兩格(選幾隻、排名方向)在這條路上用不著,填的是這一格敞口
    的欄數。適配層欠一個「與排名無關」的組合參數型別(乙份設計叫它
    ``TargetWeightsInput``),已在 KARST-031 留言;補上之前,這句填空格全倉
    只此一份(以前因子混合與因子輪動各抄一次)。
    """
    extras = dict(getattr(plan, "extras", {}) or {})

    if isinstance(plan, RulePlan):
        # 規則路徑:訊號、出場規約與兩條查帳序列全部由引擎那一層算,
        # 本層只把結果收成同一個形狀(D-007 第 3 條)。
        from ..engine.rule_runner import run_rule_strategy

        result = run_rule_strategy(panel=panel, params=plan.rule_params, engine=engine)
        return Simulation(
            equity_curve=result.equity_curve,
            holdings=result.holdings,
            orders=tuple(result.orders),
            engine_name=engine_name,
            selection=plan.selection if plan.selection is not None else result.selection,
            sizing_basis=result.sizing_basis,
            breaker_blocked=result.breaker_blocked,
            extras=extras,
        )

    from ..engine.contracts import RankingRebalanceParams

    params = RankingRebalanceParams(
        cadence=plan.cadence,
        top_n=int(plan.targets.shape[1]),
        direction="high",
        initial_cash=plan.initial_cash,
        fees=plan.fees,
    )
    output = engine.simulate(panel, plan.targets, params)
    return Simulation(
        equity_curve=output.equity_curve,
        holdings=output.holdings,
        orders=tuple(output.orders),
        engine_name=engine_name,
        selection=plan.selection,
        extras=extras,
    )


def _median(values: Iterable[float | None]) -> float | None:
    """一批讀數的中位數;一個讀數都沒有就回 ``None``,不回 0。

    0 是一個成績,「沒有成績」不是。批次登記那三格中位數容得下空值,正是為了不
    讓「這次掃描一格都沒有達標」寫成「中位數年化 0%」。
    """
    numbers = [float(value) for value in values if value is not None]
    if not numbers:
        return None
    return float(statistics.median(numbers))


def _verdict_differences(previous: Any, fresh: Any) -> list[str]:
    """兩份判讀逐格對:回不一樣的那幾格的標籤。"""
    old = {cell.point: cell.verdict for cell in previous.cells}
    new = {cell.point: cell.verdict for cell in fresh.cells}
    out: list[str] = []
    for point in sorted(set(old) | set(new), key=lambda p: p.label):
        if old.get(point) != new.get(point):
            out.append(f"{point.label}:{old.get(point)}→{new.get(point)}")
    return out


def as_period(start: date | datetime | str, end: date | datetime | str) -> tuple[str, str]:
    """把一段期間收成兩串 ``YYYY-MM-DD``。期間是留痕的一部分,不可留空。"""
    return (str(pd.Timestamp(start).date()), str(pd.Timestamp(end).date()))
