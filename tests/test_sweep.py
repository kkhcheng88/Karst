"""KARST-029 驗收:參數掃描與穩健平原報告。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。

測試數據是砌出來的,不靠運氣:每一格的淨值走一條固定的複利線,所以年化回報有
閉式解——``(1 + 日率)^252 - 1``。平原、孤峰、無效格三種形狀都是**明明白白鋪出來**
的,於是每一格該判什麼有唯一答案:

* 7 × 7 的格,中間 3 × 3(fast 2–4 × slow 2–4)鋪成一片高地 = **平原**;
* (6, 6) 一格獨高、四周全是基礎值 = **孤峰**;
* fast = 1 那一列每格只成交兩筆 = **無效格**。

不需要連網,亦不觸發任何真實行情。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from karst import FormulaProcedure, NotFound
from karst.gateway.service import Gateway
from karst.runs import RunStore
from karst.sweep import (
    INVALID,
    LONELY_PEAK,
    PLATEAU,
    CellPlan,
    SweepPoint,
    judge,
    draw_heatmap,
    product_grid,
    projection,
    run_sweep,
    simplex_grid,
    write_report,
)

STRATEGY = "掃描試場"
FACTOR = "動量·12-1 月"
CADENCE = "quarterly"
ENGINE = ("synthetic", "0.1.0")
RISK_FREE = 0.04

DAYS = pd.bdate_range("2021-01-04", "2022-12-30")
PERIOD = (str(DAYS[0].date()), str(DAYS[-1].date()))

# 三種日率。年化 = (1 + 日率)^252 - 1,故此基礎 ≈ 5.2%、平原 ≈ 16.3%、孤峰 ≈ 65.5%。
BASE_RATE = 0.0002
PLATEAU_RATE = 0.0006
PEAK_RATE = 0.0020

AXIS = (1, 2, 3, 4, 5, 6, 7)
PLATEAU_CELLS = {(fast, slow) for fast in (2, 3, 4) for slow in (2, 3, 4)}
PLATEAU_CENTRE = (3, 3)
PEAK_CELL = (6, 6)
THIN_FAST = 1  # 這一列每格只持一隻,成交兩筆,低過門檻

MIN_TRADES = 4
LONELY_PEAK_MARGIN = 0.05
# 分位刻意揀一個令門檻**落在基礎值與平原值之間**的數(42 個有效格,0.78 分位
# 內插到約 0.160):判讀因此不靠「浮點剛好相等」,而是靠真正的高低之分。
PLATEAU_QUANTILE = 0.78


def _rate(fast: int, slow: int) -> float:
    if (fast, slow) == PEAK_CELL:
        return PEAK_RATE
    if (fast, slow) in PLATEAU_CELLS:
        return PLATEAU_RATE
    return BASE_RATE


def _entities(fast: int) -> tuple[int, ...]:
    """無效格那一列只持一隻(成交兩筆);其餘持三隻(成交六筆)。"""
    return (101,) if fast == THIN_FAST else (101, 102, 103)


class _Simulation:
    """一份形狀正確的假結果:``RunStore.record_simulation`` 只看這三件。"""

    engine_name = ENGINE[0]

    def __init__(self, rate: float, entity_ids: tuple[int, ...]) -> None:
        base = 100_000.0
        self.equity_curve = pd.Series(
            base * np.power(1.0 + rate, np.arange(len(DAYS), dtype=float)),
            index=DAYS,
            name="equity",
        )
        shares = base / len(entity_ids) / 100.0
        self.holdings = pd.DataFrame(
            [
                {"date": str(day.date()), "entity_id": entity_id, "shares": shares}
                for day in DAYS
                for entity_id in entity_ids
            ],
            columns=["date", "entity_id", "shares"],
        )
        self.orders = pd.DataFrame(
            [
                {
                    "trade_date": str(DAYS[0].date()), "entity_id": entity_id,
                    "side": "buy", "shares": shares, "price": 100.0, "fees": 0.0,
                }
                for entity_id in entity_ids
            ]
            + [
                {
                    "trade_date": str(DAYS[-1].date()), "entity_id": entity_id,
                    "side": "sell", "shares": shares, "price": 100.0 * (1.0 + rate) ** len(DAYS),
                    "fees": 0.0,
                }
                for entity_id in entity_ids
            ],
            columns=["trade_date", "entity_id", "side", "shares", "price", "fees"],
        )


class _Job:
    """掃描要收的「一格怎樣跑」:登記參數集講身份,砌一份假結果做成績。"""

    def __init__(self, gateway, snapshot_id: str, factor_version_id: int) -> None:
        self._gateway = gateway
        self._store = gateway.store
        self._snapshot_id = snapshot_id
        self._factor_version_id = factor_version_id
        self.executed: list[SweepPoint] = []

    def plan(self, point: SweepPoint) -> CellPlan:
        name = f"掃描-{point.slug}"
        values = {axis: str(point.get(axis)) for axis in ("fast", "slow")}
        try:
            existing = self._store.get_param_set(STRATEGY, name)
        except NotFound:
            existing = None
        if existing is not None and dict(existing.values) == values:
            param_set = existing
        else:
            param_set, _ = self._gateway.register_param_set(
                STRATEGY, param_set_name=name, rebalance_cadence=CADENCE, values=values
            )
        return CellPlan(
            strategy_name=STRATEGY,
            param_set_name=param_set.name,
            snapshot_id=self._snapshot_id,
            engine_name=ENGINE[0],
            engine_version=ENGINE[1],
            period_start=PERIOD[0],
            period_end=PERIOD[1],
            strategy_version_no=1,
            param_set_version_no=param_set.version_no,
            factor_version_ids=(self._factor_version_id,),
        )

    def simulate(self, point: SweepPoint) -> _Simulation:
        self.executed.append(point)
        fast, slow = int(point.get("fast")), int(point.get("slow"))
        return _Simulation(_rate(fast, slow), _entities(fast))


@pytest.fixture()
def bench(tmp_path):
    """一個獨立的庫、一個掃描格、一次跑完的掃描與判讀。"""
    with Gateway.open(str(tmp_path / "karst.sqlite"), writer="KARST-029-sweep-test") as gateway:
        store = gateway.store
        snapshot_id = store.register_snapshot(
            source="test", taken_on="2026-08-28", content_hash="a1b2c3d4e5f60000",
            universe=("AAA", "BBB", "CCC"),
        )
        version, _ = gateway.register_factor(
            FACTOR,
            scale_kind="cardinal",
            procedure=FormulaProcedure(
                formula="close[-21] / close[-252] - 1", input_data_version=snapshot_id
            ),
        )
        gateway.register_strategy(
            STRATEGY, strategy_type="multifactor", factor_refs=[f"{FACTOR}@{version.version_no}"]
        )

        runs = RunStore(store, root=tmp_path / "runs")
        grid = product_grid(fast=list(AXIS), slow=list(AXIS))
        job = _Job(gateway, snapshot_id, version.factor_version_id)
        sweep = run_sweep(
            runs=runs, grid=grid, job=job, risk_free_rate=RISK_FREE, benchmarks=()
        )
        verdict = judge(
            sweep.scores("annual_return"),
            grid,
            objective="annual_return",
            min_trades=MIN_TRADES,
            lonely_peak_margin=LONELY_PEAK_MARGIN,
            plateau_quantile=PLATEAU_QUANTILE,
        )
        yield {
            "gateway": gateway, "store": store, "runs": runs, "grid": grid,
            "job": job, "sweep": sweep, "verdict": verdict,
            "snapshot_id": snapshot_id, "tmp": tmp_path,
        }


def _cell(verdict, fast: int, slow: int):
    point = SweepPoint(values=(("fast", fast), ("slow", slow)))
    return verdict.cell_for(point)


# ----------------------------------------------------------------------
# 驗收條件 1:交得出熱力圖,單點最優與其 3×3 鄰域平均兩個數同時列出
# ----------------------------------------------------------------------


def test_a_sweep_yields_a_heatmap_and_names_both_the_peak_and_its_neighbourhood(bench, tmp_path):
    sweep, verdict, grid = bench["sweep"], bench["verdict"], bench["grid"]

    assert len(sweep) == len(AXIS) ** 2 == 49
    # 二維格的鄰域就是 3×3:中心格八個鄰居(規格 6.5)。
    assert len(grid.neighbours(SweepPoint(values=(("fast", 4), ("slow", 4))))) == 8

    best = verdict.best
    assert best is not None
    assert (int(best.point.get("fast")), int(best.point.get("slow"))) == PEAK_CELL
    # 兩個數**同時**列得出:單點最優本身,與它的鄰域平均。
    assert best.value == pytest.approx((1.0 + PEAK_RATE) ** 252 - 1.0, rel=1e-6)
    assert best.neighbourhood_mean is not None
    assert best.neighbourhood_mean < best.value
    assert best.lift == pytest.approx(best.value - best.neighbourhood_mean)
    # 不含自己那個平均亦列得出,免得下一個人要猜是哪一個。
    assert best.neighbour_mean == pytest.approx((1.0 + BASE_RATE) ** 252 - 1.0, rel=1e-6)

    frame = verdict.frame()
    assert {"value", "neighbourhood_mean", "neighbour_mean", "verdict"} <= set(frame.columns)

    pytest.importorskip("matplotlib")
    png = draw_heatmap(
        verdict, tmp_path / "heat.png", x_axis="fast", y_axis="slow", title="測試熱力圖"
    )
    assert png.exists() and png.stat().st_size > 1000


# ----------------------------------------------------------------------
# 驗收條件 2:峰值明顯高於鄰域平均的格,明文標為孤峰(D-016 第 3 條)
# ----------------------------------------------------------------------


def test_a_peak_far_above_its_neighbourhood_is_labelled_a_lonely_peak(bench):
    verdict = bench["verdict"]

    peak = _cell(verdict, *PEAK_CELL)
    assert peak.verdict == LONELY_PEAK
    assert peak.is_local_peak
    assert peak.lift > LONELY_PEAK_MARGIN
    # KARST-013 那次的講法:峰值為鄰域幾多倍(規格 6.5 引的 1.39 倍)。
    assert peak.ratio is not None and peak.ratio > 1.0

    # 平原那一片不是孤峰:中間那格與四周一樣高,所以判平原而不是擬合噪音。
    centre = _cell(verdict, *PLATEAU_CENTRE)
    assert centre.verdict == PLATEAU
    assert not centre.is_local_peak
    assert centre.neighbourhood_mean == pytest.approx(centre.value, rel=1e-9)

    assert [c.point for c in verdict.lonely_peaks] == [peak.point]
    assert PLATEAU_CENTRE in {
        (int(c.point.get("fast")), int(c.point.get("slow"))) for c in verdict.plateaus
    }

    # 單點最優與鄰域平均最高不是同一格——正是「單點最高不等於穩健」那件事。
    assert verdict.most_robust is not None
    assert verdict.most_robust.point != verdict.best.point


# ----------------------------------------------------------------------
# 驗收條件 3:成交筆數低於門檻的格判無效,圖上區分得到,門檻值寫得出
# ----------------------------------------------------------------------


def test_cells_with_too_few_trades_are_invalid_and_the_threshold_is_stated(bench):
    verdict = bench["verdict"]

    thin = [c for c in verdict.cells if int(c.point.get("fast")) == THIN_FAST]
    assert len(thin) == len(AXIS)
    assert all(c.verdict == INVALID for c in thin)
    assert all(c.trades == 2 for c in thin)
    assert all(c.neighbourhood_mean is None for c in thin)

    # 有效格一格都沒有被誤判。
    assert len(verdict.invalid_cells) == len(AXIS)
    assert all(c.trades >= MIN_TRADES for c in verdict.valid_cells)

    # 無效格不入鄰域平均:(2,2) 的鄰居有三格在無效那一列,平均只計得上有效的五格。
    edge = _cell(verdict, 2, 2)
    assert len(edge.neighbours) == 8
    assert len(edge.neighbour_values) == 5

    # 門檻值寫得出——報告與判讀都印同一句。
    line = verdict.thresholds_line()
    assert f"成交少於 {MIN_TRADES} 筆" in line
    assert "孤峰門檻" in line

    # 圖上分得出:投影圖那一列整列無效,不參與色階。
    grid = projection(verdict, "fast", "slow")
    thin_rows = grid[grid["fast"] == THIN_FAST]
    assert len(thin_rows) == len(AXIS)
    assert (thin_rows["invalid"] == thin_rows["cells"]).all()
    assert thin_rows["mean"].isna().all()


# ----------------------------------------------------------------------
# 驗收條件 4:報告指得回它掃的是哪一次運行設定(規格 7.4)
# ----------------------------------------------------------------------


def test_the_report_points_back_to_strategy_version_period_and_snapshot(bench, tmp_path):
    sweep, verdict, runs = bench["sweep"], bench["verdict"], bench["runs"]
    snapshot_id = bench["snapshot_id"]

    provenance = sweep.provenance
    assert provenance.consistent
    assert provenance.strategies == (STRATEGY,)
    assert provenance.strategy_versions == (1,)
    assert provenance.snapshots == (snapshot_id,)
    assert provenance.periods == (PERIOD,)
    assert provenance.engines == (ENGINE[0],)

    out = tmp_path / "報告"
    path = write_report(sweep, verdict, out, title="測試掃描")
    text = path.read_text(encoding="utf-8")
    for token in (STRATEGY, snapshot_id, PERIOD[0], PERIOD[1], ENGINE[0], ENGINE[1]):
        assert token in text
    assert "第 1 版" in text

    # 每一格指得回一次真運行:編號在表上,而且查得回庫。
    table = pd.read_csv(out / "掃描表.csv")
    assert len(table) == len(sweep)
    assert table["run_id"].nunique() == len(sweep)
    for run_id in table["run_id"].head(3):
        record = runs.get_run(str(run_id))
        assert record.snapshot_id == snapshot_id
        assert (record.period_start, record.period_end) == PERIOD

    # 八項指標全列(規格 8.3 的兩層四項)。
    for column in (
        "total_return", "annual_return", "max_drawdown", "win_rate",
        "profit_loss_ratio", "sortino", "average_holding_days", "turnover",
    ):
        assert column in table.columns


# ----------------------------------------------------------------------
# 工作內容明寫的兩件:同一格重掃不重跑、單純形格的相鄰定義
# ----------------------------------------------------------------------


def test_rescanning_the_same_grid_reuses_the_runs_instead_of_rerunning_the_engine(bench):
    sweep, runs, grid, job = bench["sweep"], bench["runs"], bench["grid"], bench["job"]

    assert sweep.executed == len(sweep) and sweep.reused == 0
    assert len(job.executed) == len(sweep)

    again = run_sweep(runs=runs, grid=grid, job=job, risk_free_rate=RISK_FREE, benchmarks=())
    assert again.reused == len(again) and again.executed == 0
    # 引擎一次都沒有再動過。
    assert len(job.executed) == len(sweep)
    assert again.run_ids() == sweep.run_ids()


def test_the_weight_simplex_defines_a_neighbour_as_one_step_moved_between_two_weights():
    grid = simplex_grid(["w1", "w2", "w3", "w4"], step=0.10)
    assert len(grid.points()) == 286  # 十步分去四格的所有分法

    inside = SweepPoint(values=(("w1", 0.3), ("w2", 0.3), ("w3", 0.2), ("w4", 0.2)))
    neighbours = grid.neighbours(inside)
    assert len(neighbours) == 12  # 四格 × 搬去其餘三格
    for neighbour in neighbours:
        moved = [
            round(float(neighbour.get(key)) - float(inside.get(key)), 10)
            for key in ("w1", "w2", "w3", "w4")
        ]
        assert sorted(moved) == [-0.1, 0.0, 0.0, 0.1]  # 一個 −一步、一個 +一步
        assert sum(float(neighbour.get(k)) for k in ("w1", "w2", "w3", "w4")) == pytest.approx(1.0)

    corner = SweepPoint(values=(("w1", 1.0), ("w2", 0.0), ("w3", 0.0), ("w4", 0.0)))
    assert len(grid.neighbours(corner)) == 3  # 角落只搬得出,搬不入

    # 10% 步長排不出「各 25%」:十步分不均四格。要那一格請用 5% 步長。
    assert not any(all(float(p.get(k)) == 0.25 for k in ("w1", "w2", "w3", "w4")) for p in grid.points())
    fine = simplex_grid(["w1", "w2", "w3", "w4"], step=0.05)
    assert len(fine.points()) == 1771
    assert set(grid.points()) <= set(fine.points())
