"""把因子輪動策略接上通用掃描:一格驅動器參數 = 一個參數集 = 一次運行(KARST-036)。

掃描本身不認得任何一套策略(見 ``karst.sweep.runner``);本檔就是「因子輪動怎樣跑
一格」那份接法,與 ``karst.sweep.factor_mix`` 是同一個模子的兩件:

``rotation_grid(...)``
    砌一個驅動器的參數格。**取值無預設**——掃 L 的哪幾個月、M 的哪幾條均線,一律
    由呼叫方寫明。哪一條軸有序(回望期由短到長)、哪一條無序(``winner`` 與
    ``rank`` 不是一步之遙),由驅動器自己在 ``DRIVER_UNORDERED_PARAMETERS`` 講明,
    因為相鄰的定義就是平原與孤峰判讀的地基。

``FactorRotationJob``
    ``plan(point)`` 把這一格的驅動器參數登記成一個參數集(先查再登記,同一格重掃
    不重跑);``simulate(point)`` 砌驅動器跑一次回測。

``scoreboard(...)`` / ``segment_excess(...)``
    成績表與分段超額。兩者都**不裁定哪一格該用**(D-008),只把數擺出來:八項指標、
    對每一個對照的差距、以及分段的年化超額。

一格一個參數集名(``{前綴}{格的短名}``),所以每一格的來歷各自獨立,查重靠名不靠
版本鏈,亦不會在庫裡堆一條幾百版的參數集鏈。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import pandas as pd

from ..engine.contracts import PricePanel, TradingCosts
from ..errors import ContractViolation, NotFound
from ..metrics import RunMetrics, run_metrics
from ..metrics.benchmark import BenchmarkCurve, benchmark_curve
from ..runs import RunStore
from ..store import ParamSet, StrategyVersion
from ..strategies.factor_mix import FACTOR_ETF_SLEEVES, FactorSleeve
from ..strategies.factor_rotation import (
    DRIVER_PARAMETERS,
    DRIVER_UNORDERED_PARAMETERS,
    FactorRotationParams,
    build_driver,
    run_factor_rotation,
)
from .factor_mix import (
    CADENCE_AXIS,
    cost_slug,
    cost_values,
    ensure_factor_mix_setup,
    weight_text,
)
from .grid import ProductGrid, SweepAxis, SweepGrid, SweepPoint
from .runner import METRIC_COLUMNS, CellPlan, SweepCell
from .verdict import CellVerdict

# 驅動器的名字在參數集裡的鍵。**它不是掃描格的一條軸**——一次掃描只掃一個驅動器
# (不同驅動器的參數名根本不同,排不進同一個笛卡兒積),所以驅動器名寫在參數集的
# 值裡做身份,不寫在格上。
DRIVER_KEY: Final[str] = "driver"


def param_text(value: Any) -> str:
    """參數寫入參數集時的文字。固定寫法,重掃一字不差。

    參數集一律以文字存值(``store`` 會 ``str(value).strip()``),而運行編號正是由
    這串文字算出來的——所以格式一變,同一格就會變成另一個運行。這裡定死:整數就
    是整數(``6``)、小數最多四位並剪走末尾的零(``0.5``)、其餘照原文剪空白。
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(int(value))
    if isinstance(value, float):
        if float(value).is_integer():
            return str(int(value))
        return weight_text(value)
    return str(value).strip()


def point_slug(point: SweepPoint) -> str:
    """一格的短名(參數集名用)。``lookback_months6-modewinner-cadencemonthly``。

    通用的 ``SweepPoint.slug`` 把 0 至 1 之間的數當權重印成百分點,於是回望期
    ``1`` 個月會印成 ``100``——對讀庫的人是誤導。本層自己用明碼:數字就是數字。
    """
    return "-".join(f"{name}{param_text(value)}" for name, value in point.values)


def rotation_grid(
    driver_key: str,
    *,
    values: Mapping[str, Sequence[Any]],
    cadences: Sequence[str],
) -> SweepGrid:
    """砌一個驅動器的參數格:驅動器自己那幾個參數 × 換倉節奏。

    ``values`` 逐個參數寫明要掃哪些取值——**沒有預設取值**(D-008 第 3 條)。
    相鄰 = 每個軸最多移一步且不可全部不動(``ProductGrid``);無序的軸(例如
    ``mode``)同軸任何兩個取值皆相鄰。
    """
    key = str(driver_key or "").strip()
    if key not in DRIVER_PARAMETERS:
        raise ContractViolation(
            f"沒有「{key}」這個驅動器;有的是:{'、'.join(sorted(DRIVER_PARAMETERS))}"
        )
    names = DRIVER_PARAMETERS[key]
    unordered = set(DRIVER_UNORDERED_PARAMETERS.get(key, ()))

    missing = [name for name in names if not values.get(name)]
    if missing:
        raise ContractViolation(
            f"驅動器「{key}」這幾個參數沒有寫明要掃哪些取值:{'、'.join(missing)};"
            "掃描不設預設取值"
        )
    extra = [name for name in values if name not in names]
    if extra:
        raise ContractViolation(f"驅動器「{key}」不認得這幾個參數:{'、'.join(extra)}")
    if not cadences:
        raise ContractViolation("換倉節奏要寫明要掃哪幾個;節奏無預設值(D-009 第 7 條)")

    axes = [
        SweepAxis(name=name, values=tuple(values[name]), ordered=name not in unordered)
        for name in names
    ]
    axes.append(
        SweepAxis(name=CADENCE_AXIS, values=tuple(str(c).strip() for c in cadences), ordered=True)
    )
    return ProductGrid(axes)


def ensure_factor_rotation_setup(
    gateway: Any,
    *,
    strategy_name: str,
    sleeves: Sequence[FactorSleeve] = FACTOR_ETF_SLEEVES,
    snapshot_id: str,
    setup_param_set_name: str,
    setup_weights: Mapping[str, Any],
    cadence: str,
    description: str | None = None,
) -> StrategyVersion:
    """確保四個因子與輪動策略已經登記,回傳策略版本。**已經有就一個字都不寫。**

    走的是與因子混合**同一道唯一入口**(D-020 第 4 條)——輪動與混合蓋住的是同一
    四個因子敞口,分別只在策略名與目標比重怎樣算出來。所以這裡直接借用因子混合
    那份登記程序,不另開一套。
    """
    return ensure_factor_mix_setup(
        gateway,
        strategy_name=strategy_name,
        sleeves=sleeves,
        snapshot_id=snapshot_id,
        setup_param_set_name=setup_param_set_name,
        setup_weights=setup_weights,
        cadence=cadence,
        description=description,
    )


class FactorRotationJob:
    """因子輪動策略的掃描跑法(``karst.sweep.runner.CellJob``)。

    一個 job 對一個驅動器。``cadence`` 是固定節奏;掃描格帶 ``cadence`` 軸時,
    那一軸話事,本欄可以留空。
    """

    def __init__(
        self,
        *,
        gateway: Any,
        panel: PricePanel,
        driver_key: str,
        strategy_name: str,
        snapshot_id: str,
        engine_version: str,
        param_set_prefix: str,
        period_start: str,
        period_end: str,
        warmup_bars: int,
        warmup_weights: Mapping[str, float],
        sleeves: Sequence[FactorSleeve] = FACTOR_ETF_SLEEVES,
        cadence: str | None = None,
        strategy_version_no: int | None = None,
        market_ticker: str | None = None,
        initial_cash: float = 100_000.0,
        fees: float = 0.0,
        costs: TradingCosts | None = None,
        engine: Any | None = None,
        engine_name: str = "vectorbt",
    ) -> None:
        if not isinstance(panel, PricePanel):
            raise ContractViolation(f"價格面板要是 PricePanel,收到 {type(panel).__name__}")
        if not sleeves:
            raise ContractViolation("最少要一格因子敞口")
        key = str(driver_key or "").strip()
        if key not in DRIVER_PARAMETERS:
            raise ContractViolation(
                f"沒有「{key}」這個驅動器;有的是:{'、'.join(sorted(DRIVER_PARAMETERS))}"
            )
        if not str(param_set_prefix or "").strip():
            raise ContractViolation(
                "參數集名前綴不可留空;一格一個參數集名,沒有前綴會與別的掃描撞名"
            )
        self._gateway = gateway
        self._store = gateway.store
        self._panel = panel
        self._driver_key = key
        self._sleeves = tuple(sleeves)
        self._strategy_name = str(strategy_name).strip()
        self._snapshot_id = str(snapshot_id).strip()
        self._engine_version = str(engine_version).strip()
        self._prefix = str(param_set_prefix).strip()
        self._period = (str(period_start).strip(), str(period_end).strip())
        self._warmup_bars = int(warmup_bars)
        self._warmup_weights = dict(warmup_weights)
        self._cadence = str(cadence).strip() if cadence else None
        self._strategy_version_no = strategy_version_no
        self._market_ticker = str(market_ticker).strip() if market_ticker else None
        self._initial_cash = float(initial_cash)
        self._fees = float(fees)
        self._costs = costs
        self._engine = engine
        self._engine_name = str(engine_name).strip()
        self._written = 0

    @property
    def driver_key(self) -> str:
        return self._driver_key

    @property
    def costs(self) -> TradingCosts | None:
        return self._costs

    @property
    def param_names(self) -> tuple[str, ...]:
        return DRIVER_PARAMETERS[self._driver_key]

    @property
    def param_sets_written(self) -> int:
        """這次掃描真正寫入庫的參數集數目(其餘是查到現成的,沒有寫)。"""
        return self._written

    def _cadence_of(self, point: SweepPoint) -> str:
        if CADENCE_AXIS in point.names:
            return str(point.get(CADENCE_AXIS)).strip()
        if not self._cadence:
            raise ContractViolation(
                "缺換倉節奏:掃描格沒有 cadence 這一軸,而本跑法亦沒有指定固定節奏。"
                "節奏無預設值(D-009 第 7 條),兩者揀一個寫明"
            )
        return self._cadence

    def _driver_params_of(self, point: SweepPoint) -> dict[str, Any]:
        return {name: point.get(name) for name in self.param_names}

    def _param_set(self, name: str, cadence: str, values: dict[str, str]) -> ParamSet:
        try:
            existing = self._store.get_param_set(
                self._strategy_name, name, strategy_version_no=self._strategy_version_no
            )
        except NotFound:
            existing = None
        if (
            existing is not None
            and existing.rebalance_cadence == cadence
            and dict(existing.values) == values
        ):
            return existing

        param_set, _ = self._gateway.register_param_set(
            self._strategy_name,
            param_set_name=name,
            rebalance_cadence=cadence,
            values=values,
            strategy_version_no=self._strategy_version_no,
        )
        self._written += 1
        return param_set

    def plan(self, point: SweepPoint) -> CellPlan:
        cadence = self._cadence_of(point)
        values = {DRIVER_KEY: self._driver_key}
        values.update(
            {name: param_text(value) for name, value in self._driver_params_of(point).items()}
        )
        # 熱身期是整次掃描共用的設定,但它一樣會改變成績,所以要入參數集——
        # 否則換一個熱身期重掃,會撞回同一個運行編號,靜靜地讀回舊成績。
        values["warmup_bars"] = param_text(self._warmup_bars)
        values.update(
            {f"warmup_{key}": weight_text(value) for key, value in self._warmup_weights.items()}
        )
        # 交易成本同一個道理:成本一改就是另一次運行,所以要入參數集。零成本就一格
        # 都不寫、名亦一字不改,零成本那批舊運行照樣撞得回去(見 cost_values/cost_slug)。
        values.update(cost_values(self._costs))

        param_set = self._param_set(
            f"{self._prefix}{point_slug(point)}{cost_slug(self._costs)}", cadence, values
        )
        factor_version_ids = tuple(
            self._store.get_factor_version(sleeve.factor_name).factor_version_id
            for sleeve in self._sleeves
        )
        strategy = self._store.get_strategy_version(
            self._strategy_name, self._strategy_version_no
        )
        return CellPlan(
            strategy_name=strategy.name,
            param_set_name=param_set.name,
            snapshot_id=self._snapshot_id,
            engine_name=self._engine_name,
            engine_version=self._engine_version,
            period_start=self._period[0],
            period_end=self._period[1],
            strategy_version_no=strategy.version_no,
            param_set_version_no=param_set.version_no,
            factor_version_ids=factor_version_ids,
        )

    def simulate(self, point: SweepPoint) -> Any:
        driver = build_driver(self._driver_key, **self._driver_params_of(point))
        params = FactorRotationParams(
            cadence=self._cadence_of(point),
            warmup_bars=self._warmup_bars,
            warmup_weights=self._warmup_weights,
            initial_cash=self._initial_cash,
            fees=self._fees,
            costs=self._costs,
        )
        result = run_factor_rotation(
            store=self._store,
            panel=self._panel,
            sleeves=self._sleeves,
            driver=driver,
            params=params,
            engine=self._engine,
            market_ticker=self._market_ticker,
        )
        if result.engine_name != self._engine_name:
            raise ContractViolation(
                f"這一格由「{result.engine_name}」跑出來,但落痕寫的是「{self._engine_name}」;"
                "引擎名是運行編號的一部分,不可以對不上(D-007 第 3 條)"
            )
        return result


# ----------------------------------------------------------------------
# 成績表與分段超額
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ScoreEntry:
    """成績表的一行:一個驅動器的最優格,或者一個固定權重的對照格。

    ``verdict`` 是這一格在它自己那個掃描格上的裁決(平原 / 孤峰 / 普通)。對照格
    不在任何掃描格上,所以留空——**不冤枉它是孤峰,亦不替它充穩健**。
    """

    label: str
    kind: str
    cell: SweepCell
    verdict: CellVerdict | None = None
    note: str = ""


def scoreboard(
    entries: Sequence[ScoreEntry],
    *,
    objective: str,
    baselines: Sequence[str] = (),
) -> pd.DataFrame:
    """一張成績表:逐行八項指標、對每一條基準的年化超額,以及對對照的差距。

    ``baselines`` 是要比的那幾行的 ``label``。每一個 baseline 加一欄
    ``對「<label>」的差距``——本行的目標指標減那一行的目標指標。差距是**減出來的
    數,不是裁決**:哪一格該用是用戶的事(D-008)。
    """
    if not entries:
        raise ContractViolation("成績表一行都沒有")

    table = {entry.label: entry for entry in entries}
    if len(table) != len(entries):
        raise ContractViolation("成績表有兩行同名;每一行要一個獨一無二的名")
    missing = [name for name in baselines if name not in table]
    if missing:
        raise ContractViolation(f"要比的對照不在成績表上:{'、'.join(missing)}")

    reference_values = {
        name: table[name].cell.value_of(objective) for name in baselines
    }

    rows: list[dict[str, Any]] = []
    for entry in entries:
        cell = entry.cell
        value = cell.value_of(objective)
        row: dict[str, Any] = {
            "名稱": entry.label,
            "類別": entry.kind,
            "參數": cell.point.label,
            objective: value,
        }
        for name in METRIC_COLUMNS:
            row[name] = getattr(cell.metrics, name)
        for ticker in sorted(cell.annual_excess):
            row[f"annual_excess_{ticker}"] = cell.annual_excess[ticker]
        row["裁決"] = entry.verdict.verdict if entry.verdict is not None else "不在掃描格上"
        row["鄰域平均"] = entry.verdict.neighbourhood_mean if entry.verdict is not None else None
        row["成交筆數"] = cell.trades
        for name in baselines:
            base = reference_values[name]
            row[f"對「{name}」的差距"] = (
                None if value is None or base is None else float(value - base)
            )
        row["run_id"] = cell.run_id
        row["備註"] = entry.note
        rows.append(row)
    return pd.DataFrame(rows)


def segment_excess(
    runs: RunStore,
    entries: Sequence[ScoreEntry],
    *,
    segments: Sequence[tuple[str, str, str]],
    risk_free_rate: float,
    benchmark: str,
    snapshot_root: str | Path | None = None,
) -> pd.DataFrame:
    """分段年化超額:同一批運行,只換檢視視窗重看一次(**重看不重跑**,規格 8.5)。

    ``segments`` 是 ``(段名, 起, 訖)`` 的串——分幾段、怎樣分,由呼叫方寫明,本層
    不設預設分段。每一段的基準按**同一段日子**另算一條買入持有線,兩邊比得過。
    """
    if not segments:
        raise ContractViolation("分段要寫明分哪幾段;本層不設預設分段")

    curves: dict[tuple[str, str, str, str], BenchmarkCurve] = {}
    rows: list[dict[str, Any]] = []
    for entry in entries:
        cell = entry.cell
        for name, start, end in segments:
            metrics: RunMetrics = run_metrics(
                runs,
                cell.run_id,
                risk_free_rate=risk_free_rate,
                benchmarks=(),
                start=start,
                end=end,
                snapshot_root=snapshot_root,
            )
            key = (cell.plan.snapshot_id, benchmark, metrics.start, metrics.end)
            curve = curves.get(key)
            if curve is None:
                curve = benchmark_curve(
                    runs.store,
                    cell.plan.snapshot_id,
                    benchmark,
                    metrics.start,
                    metrics.end,
                    root=snapshot_root,
                )
                curves[key] = curve
            rows.append(
                {
                    "名稱": entry.label,
                    "類別": entry.kind,
                    "段": name,
                    "起": metrics.start,
                    "訖": metrics.end,
                    "交易日": metrics.trading_days,
                    "年化": metrics.annual_return,
                    f"{curve.ticker}年化": curve.stats.annual_return,
                    "年化超額": float(metrics.annual_return - curve.stats.annual_return),
                    "最大回撤": metrics.max_drawdown,
                    "run_id": cell.run_id,
                }
            )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# 成本前後並列(KARST-043)
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CostPair:
    """同一格參數的兩次運行:一次零成本,一次連成本。

    兩次是**兩個獨立的運行編號**,不是同一個運行改了個數——成本入了參數集,
    編號自然不同(見 ``cost_values``)。並列擺出來,「成本吃掉幾多」就是減出來
    的一個數,不用人推。
    """

    label: str
    kind: str
    before: SweepCell
    after: SweepCell
    verdict_before: CellVerdict | None = None
    verdict_after: CellVerdict | None = None
    note: str = ""


def cost_comparison(
    pairs: Sequence[CostPair],
    *,
    objective: str,
    costs: TradingCosts,
) -> pd.DataFrame:
    """成本前後並列表:目標指標(年化超額)與換手,兩邊同一行擺出來。

    換手那兩欄是這張表的重點。KARST-036 收檔時留下的問題正是:輪動的換手是固定
    權重的一百倍,而成本設為零——所以「成本前後的換手幾乎不變、超額卻掉了多少」
    就是那條問題的答案。本函式**只減數,不裁決**哪一組參數該用(D-008)。
    """
    if not pairs:
        raise ContractViolation("並列表一行都沒有")
    labels = {pair.label for pair in pairs}
    if len(labels) != len(pairs):
        raise ContractViolation("並列表有兩行同名;每一行要一個獨一無二的名")

    rows: list[dict[str, Any]] = []
    for pair in pairs:
        before, after = pair.before, pair.after
        value_before = before.value_of(objective)
        value_after = after.value_of(objective)
        rows.append(
            {
                "名稱": pair.label,
                "類別": pair.kind,
                "參數": after.point.label,
                "成本": costs.label,
                f"成本前{objective}": value_before,
                f"成本後{objective}": value_after,
                "成本代價": (
                    None
                    if value_before is None or value_after is None
                    else float(value_after - value_before)
                ),
                "成本前換手": before.metrics.turnover,
                "成本後換手": after.metrics.turnover,
                "成本前年化": before.metrics.annual_return,
                "成本後年化": after.metrics.annual_return,
                "成本前最大回撤": before.metrics.max_drawdown,
                "成本後最大回撤": after.metrics.max_drawdown,
                "成本前裁決": (
                    pair.verdict_before.verdict
                    if pair.verdict_before is not None
                    else "不在掃描格上"
                ),
                "成本後裁決": (
                    pair.verdict_after.verdict
                    if pair.verdict_after is not None
                    else "不在掃描格上"
                ),
                "成本前run_id": before.run_id,
                "成本後run_id": after.run_id,
                "備註": pair.note,
            }
        )
    return pd.DataFrame(rows)


def provenance_note(
    *,
    snapshot_id: str,
    period: tuple[str, str],
    costs: TradingCosts,
    run_ids: Sequence[str] = (),
    extra: str = "",
) -> str:
    """報告要指得回去的那幾件:快照、期間、成本參數、運行編號。

    一份報告的數字若指不回「哪一份數據、哪一段日子、哪一組成本、哪一次運行」,
    下一個人就重現不到,亦查不出它是不是已經過時。所以這幾行是報告的**必印**部分。
    """
    lines = [
        f"- 數據快照:`{snapshot_id}`",
        f"- 期間:{period[0]} 至 {period[1]}",
        f"- 交易成本:{_costs_sentence(costs)}",
    ]
    if run_ids:
        unique = tuple(dict.fromkeys(str(run_id) for run_id in run_ids))
        shown = "、".join(f"`{run_id}`" for run_id in unique[:8])
        tail = f",另有 {len(unique) - 8} 個" if len(unique) > 8 else ""
        lines.append(f"- 運行編號({len(unique)} 個):{shown}{tail}")
    if extra:
        lines.append(extra if extra.startswith("-") else f"- {extra}")
    return "\n".join(lines)


def _costs_sentence(costs: TradingCosts) -> str:
    if costs.is_zero:
        return "零(手續費與滑點皆為 0)"
    if costs.fee_model == "per_share":
        fee = f"每股 US${costs.fee_rate:g}"
    else:
        fee = f"成交金額的 {costs.fee_rate * 10_000:g} 個基點"
    return (
        f"手續費 {fee}(型別 `{costs.fee_model}`)、"
        f"滑點 {costs.slippage_fraction * 10_000:g} 個基點(佔成交價比例)"
    )
