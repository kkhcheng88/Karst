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
from types import SimpleNamespace

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
    VERDICTS,
    CellPlan,
    SweepAxis,
    SweepPoint,
    SweepProvenance,
    judge,
    draw_heatmap,
    product_grid,
    projection,
    run_sweep,
    simplex_grid,
    write_report,
)

# KARST-047 的新面:軸型與山脊。套件門面(``karst.sweep.__init__``)不在本票可改的
# 檔案之內,所以這幾個名由子模組直接取。
from karst.sweep.grid import (
    CHOICE,
    CONTINUOUS,
    ProductGrid,
    choice_axis,
    continuous_axis,
    layer_label,
)
from karst.sweep.report import draw_layer_projections
from karst.sweep.verdict import RIDGE, CellScore

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


# ======================================================================
# KARST-047 驗收:鄰域分連續軸與選擇軸,山脊不再被判成孤峰
#
# 一樣是明明白白鋪出來的形狀,所以每一格該判什麼有唯一答案:
#
# * 一條**山脊**:只在「持現金 + 月度」那一層,回望期 4 至 6 個月鋪成高地;
#   同一個回望期換去其餘三層,全部掉到地面。
# * 一個**孤峰**:「均分 + 月度」層的回望期 8、傾斜 0.5 一格獨高,四周全是地面。
# * 其餘是地面。
# ======================================================================

LOOKBACKS = (1, 2, 3, 4, 5, 6, 7, 8, 9)
TILTS = (0.5, 1.0)
RIDGE_LOOKBACKS = (4, 5, 6)
RIDGE_LAYER = ("cash", "monthly")
PEAK_CELL_LAYERED = (8, 0.5, "equal", "monthly")

GROUND = 0.005
SHOULDER = 0.01  # 山脊那一層,山脊以外的回望期
RIDGE_TOP = 0.05
PEAK_TOP = 0.06

MIN_TRADES_LAYERED = 30
MARGIN_LAYERED = 0.005
# 72 格,分位刻意揀一個令門檻**落在 0.01 與 0.05 之間**的數(0.91 內插到約
# 0.0344):判讀不靠浮點剛好相等,靠真正的高低之分。
QUANTILE_LAYERED = 0.91


def _layered_axes(kind_of_choice: str):
    """回望期與傾斜是連續軸;退路與節奏是選擇軸(或者按呼叫方要求全部當連續)。"""
    return [
        continuous_axis("lookback_months", LOOKBACKS),
        continuous_axis("tilt", TILTS),
        SweepAxis(name="fallback", values=("cash", "equal"), ordered=False, kind=kind_of_choice),
        SweepAxis(name="cadence", values=("monthly", "quarterly"), ordered=True, kind=kind_of_choice),
    ]


def _layered_value(point: SweepPoint) -> float:
    lookback = int(point.get("lookback_months"))
    layer = (str(point.get("fallback")), str(point.get("cadence")))
    if (lookback, float(point.get("tilt")), *layer) == PEAK_CELL_LAYERED:
        return PEAK_TOP
    if layer != RIDGE_LAYER:
        return GROUND
    return RIDGE_TOP if lookback in RIDGE_LOOKBACKS else SHOULDER


def _layered_scores(grid) -> list[CellScore]:
    return [
        CellScore(point=point, value=_layered_value(point), trades=50)
        for point in grid.points()
    ]


def _layered_judgement(grid):
    return judge(
        _layered_scores(grid),
        grid,
        objective="annual_excess:SPY",
        min_trades=MIN_TRADES_LAYERED,
        lonely_peak_margin=MARGIN_LAYERED,
        plateau_quantile=QUANTILE_LAYERED,
    )


@pytest.fixture()
def layered():
    """同一批成績、兩套軸型:新口徑(有選擇軸)與舊口徑(三條軸一視同仁)。"""
    axis_aware = ProductGrid(_layered_axes(CHOICE))
    all_continuous = ProductGrid(_layered_axes(CONTINUOUS))
    return {
        "grid": axis_aware,
        "verdict": _layered_judgement(axis_aware),
        "old_grid": all_continuous,
        "old_verdict": _layered_judgement(all_continuous),
    }


def _point(lookback: int, tilt: float, fallback: str, cadence: str) -> SweepPoint:
    return SweepPoint(
        values=(
            ("lookback_months", lookback),
            ("tilt", tilt),
            ("fallback", fallback),
            ("cadence", cadence),
        )
    )


# ----------------------------------------------------------------------
# 驗收條件 1:每條軸標明連續或選擇,鄰域只沿連續軸取,選擇軸分層各出判讀
# ----------------------------------------------------------------------


def test_every_axis_declares_its_kind_and_the_neighbourhood_stays_on_the_continuous_ones(layered):
    grid, verdict = layered["grid"], layered["verdict"]

    # 每條軸講得出自己是連續還是選擇,而且報告印得出那一句。
    assert grid.axis_kinds == {
        "lookback_months": CONTINUOUS,
        "tilt": CONTINUOUS,
        "fallback": CHOICE,
        "cadence": CHOICE,
    }
    assert grid.continuous_axes == ("lookback_months", "tilt")
    assert grid.choice_axes == ("fallback", "cadence")
    described = grid.describe()
    assert "lookback_months(連續)" in described and "fallback(選擇)" in described
    assert "選擇軸釘死不動" in described

    # 鄰域只沿連續軸走:回望期 ±1 × 傾斜 ±1,退路與節奏一步都不移。
    centre = _point(5, 0.5, "cash", "monthly")
    neighbours = grid.neighbours(centre)
    assert len(neighbours) == 5  # 3 × 2 − 自己
    assert {int(n.get("lookback_months")) for n in neighbours} == {4, 5, 6}
    assert all(n.get("fallback") == "cash" and n.get("cadence") == "monthly" for n in neighbours)
    # 舊口徑會把另外三層都當鄰居——這正是本票要修的那件事。
    assert len(layered["old_grid"].neighbours(centre)) == 23

    # 選擇軸把格切成四層,每層各出一份判讀。
    assert len(grid.layers()) == 4
    assert verdict.layer_keys() == grid.layers()
    assert verdict.cell_for(centre).layer_name == "fallback=cash、cadence=monthly"

    layer_table = verdict.layer_frame()
    assert len(layer_table) == 4
    assert set(layer_table["格數"]) == {len(LOOKBACKS) * len(TILTS)}
    for key, slice_ in verdict.layers():
        assert len(slice_) == len(LOOKBACKS) * len(TILTS)
        assert {cell.layer for cell in slice_.cells} == {key}
    # 高地成片只在山脊那一層;另外三層加起來只有一格,而那一格正是那個孤峰。
    high = dict(zip(layer_table["層"], layer_table["高地格數"], strict=True))
    assert high["fallback=cash、cadence=monthly"] == len(RIDGE_LOOKBACKS) * len(TILTS)
    assert high["fallback=equal、cadence=monthly"] == 1
    assert high["fallback=cash、cadence=quarterly"] == 0
    assert high["fallback=equal、cadence=quarterly"] == 0


# ----------------------------------------------------------------------
# 驗收條件 2:裁決多一種「山脊」,定義寫明並在報告上區分
# ----------------------------------------------------------------------


def test_a_ridge_is_smooth_along_the_continuous_axis_but_falls_away_in_every_other_layer(layered):
    verdict, old = layered["verdict"], layered["old_verdict"]

    assert RIDGE == "山脊" and RIDGE in VERDICTS
    ridged = {
        (int(c.point.get("lookback_months")), float(c.point.get("tilt")))
        for c in verdict.ridges
    }
    assert ridged == {(months, tilt) for months in RIDGE_LOOKBACKS for tilt in TILTS}
    assert all(c.layer == (("fallback", "cash"), ("cadence", "monthly")) for c in verdict.ridges)

    # 山脊的兩個條件,逐個查得到:沿連續軸站得住,換一層即跌穿門檻。
    core = verdict.cell_for(_point(5, 0.5, "cash", "monthly"))
    assert core.verdict == RIDGE
    assert core.neighbourhood_mean == pytest.approx(RIDGE_TOP)
    assert core.neighbourhood_mean >= verdict.plateau_threshold
    assert core.weakest_sibling_mean is not None
    assert core.weakest_sibling_mean < verdict.plateau_threshold
    assert core.layer_drop == pytest.approx(core.neighbourhood_mean - core.weakest_sibling_mean)
    assert len(core.sibling_means) == 3  # 其餘三層各一格

    # 它不是平原:換一套做法就沒有了。這批成績一格平原都判不出。
    assert verdict.plateaus == ()
    # 它亦不是孤峰:沿連續軸四周一樣高。
    assert not core.is_local_peak

    # 真的一格獨高的,照舊判孤峰——先後不變,山脊只從本來會判平原的那批分出來。
    peak = verdict.cell_for(_point(*PEAK_CELL_LAYERED))
    assert peak.verdict == LONELY_PEAK
    assert peak.is_local_peak and peak.lift > MARGIN_LAYERED

    # 定義寫得出,報告印得到。
    assert "山脊" in verdict.axes_line() and "跌穿高地門檻" in verdict.axes_line()

    # 同一批成績、舊口徑(三條軸一視同仁):同一格判不出山脊,鄰域平均被別層沖淡。
    assert old.choice_axes == ()
    assert old.ridges == ()
    before = old.cell_for(_point(5, 0.5, "cash", "monthly"))
    assert before.verdict != RIDGE
    assert before.neighbourhood_mean < core.neighbourhood_mean
    assert before.neighbourhood_mean < old.plateau_threshold  # 高地資格被沖走


def test_the_report_and_the_projection_tell_ridges_apart_from_plateaus_and_peaks(layered, tmp_path):
    verdict = layered["verdict"]

    # 投影圖的表分得出山脊,亦講得出一個色塊壓住幾層。
    frame = projection(verdict, "lookback_months", "fallback")
    assert {"ridges", "plateaus", "lonely_peaks", "layers"} <= set(frame.columns)
    assert frame["ridges"].sum() == len(verdict.ridges)
    assert frame["layers"].max() == 2  # 節奏那一層被壓在同一個色塊裡

    pytest.importorskip("matplotlib")
    # 逐層各出一套投影圖:四層就是四套,檔名認得出是哪一層。
    per_layer = draw_layer_projections(
        verdict, tmp_path / "圖", title="山脊測試", subtitle="測試用"
    )
    assert len(per_layer) == 4
    for key, paths in per_layer.items():
        assert len(paths) == 1  # 兩條連續軸 = 一對 = 一張
        assert paths[0].exists() and paths[0].stat().st_size > 1000
        assert layer_label(key).split("=")[-1].split("、")[0] in paths[0].name

    single = draw_heatmap(
        verdict,
        tmp_path / "跨層.png",
        x_axis="lookback_months",
        y_axis="fallback",
        title="跨層",
    )
    assert single.exists()


class _StubSweep:
    """報告只向掃描表要這幾件事(來歷、格數、逐格運行編號)。

    分層那幾節的內容全部來自**判讀**本身,所以為住印一份報告而真跑 72 格引擎是
    白花時間——這裡給一個形狀正確的替身,報告的字照樣是真的砌出來。
    """

    def __init__(self, judgement) -> None:
        self._judgement = judgement
        self.provenance = SweepProvenance(
            strategies=(STRATEGY,),
            strategy_versions=(1,),
            snapshots=("2026-08-28-stub",),
            periods=(PERIOD,),
            engines=(ENGINE[0],),
            engine_versions=(ENGINE[1],),
            param_set_names=("掃描-替身",),
        )
        self.reused = 0
        self.seconds = 1.0
        self.risk_free_rate = RISK_FREE
        self.benchmark_tickers = ("SPY",)

    def __len__(self) -> int:
        return len(self._judgement)

    @property
    def executed(self) -> int:
        return len(self)

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {**cell.point.as_dict(), "run_id": f"run-{index:04d}"}
                for index, cell in enumerate(self._judgement.cells)
            ]
        )

    def cell_for(self, point):
        for index, cell in enumerate(self._judgement.cells):
            if cell.point == point:
                return SimpleNamespace(run_id=f"run-{index:04d}", point=point)
        raise AssertionError(f"替身沒有這一格:{point.label}")


def test_the_written_report_separates_the_layers_and_names_the_ridges(layered, tmp_path):
    verdict = layered["verdict"]
    out = tmp_path / "報告"
    path = write_report(
        _StubSweep(verdict), verdict, out, title="山脊測試報告", top=3
    )
    text = path.read_text(encoding="utf-8")

    # 軸型與山脊的定義印得出——裁決講得出根據。
    assert "lookback_months(連續)" in text and "fallback(選擇)" in text
    assert "鄰域只沿連續軸取" in text
    # 分層判讀一層一行,連同那一層的高地格數。
    assert "### 分層判讀" in text
    for key in verdict.layer_keys():
        assert layer_label(key) in text
    # 山脊自己一節,寫得出換去最差那一層跌幾多。
    assert "### 山脊" in text and "換去最差那一層" in text
    assert "山脊 6 格" in text  # 判讀撮要照樣逐種裁決報數
    # 分層判讀表落了 CSV,一層一行。
    layers = pd.read_csv(out / "分層判讀表.csv")
    assert len(layers) == 4
    assert (out / "判讀表.csv").exists() and (out / "掃描表.csv").exists()


# ----------------------------------------------------------------------
# 驗收條件 3:KARST-043 兩個驅動器 60 格重判(不重跑),交出分層判讀與新舊對照
# ----------------------------------------------------------------------


def test_the_karst_043_sixty_cells_are_rejudged_with_old_and_new_verdicts_side_by_side():
    root = Path(__file__).resolve().parents[1]
    results = root / "experiments" / "2026-08-28-axis-aware-verdict" / "results"
    filed = root / "experiments" / "2026-08-28-costs-and-regrid" / "results"
    if not results.exists():
        pytest.skip("未跑過重判腳本:experiments/2026-08-28-axis-aware-verdict/rejudge_axis_aware.py")

    for driver, choice in (("relative_strength", "fallback"), ("factor_momentum", "mode")):
        table = pd.read_csv(results / f"dense-{driver}" / "新舊裁決對照表.csv")
        # 60 格重判,不重跑:格數與 KARST-043 那次一模一樣。
        assert len(table) == 60
        assert {"舊裁決", "新裁決", "層", "舊鄰域平均", "新鄰域平均", "換層代價"} <= set(table.columns)

        # 舊裁決欄要與 KARST-043 當日落檔的判讀表逐格對得上——本票不改舊判讀。
        before = pd.read_csv(filed / f"dense-{driver}" / "判讀表.csv")
        keys = ["lookback_months", choice, "cadence"]
        merged = table.merge(before[[*keys, "verdict"]], on=keys, how="left")
        assert len(merged) == 60
        assert (merged["舊裁決"] == merged["verdict"]).all()

        # 新口徑判得出山脊,而且那幾格從前不是山脊(從前根本沒有這個標籤)。
        ridges = table[table["新裁決"] == "山脊"]
        assert len(ridges) >= 1
        assert not (ridges["舊裁決"] == "山脊").any()
        # 換一層的代價逐格寫得出。
        assert ridges["換層代價"].notna().all() and (ridges["換層代價"] > 0).all()

        # 分層判讀:兩條選擇軸切出四層,每層 15 格。
        layers = pd.read_csv(results / f"dense-{driver}" / "分層判讀.csv")
        assert len(layers) == 4
        assert set(layers["格數"]) == {15}


# ----------------------------------------------------------------------
# 驗收條件 4:既有二維規則型掃描(KARST-013 式 3×3)判讀不變
# ----------------------------------------------------------------------


def test_a_two_axis_rule_grid_is_judged_exactly_as_before(bench):
    grid, verdict = bench["grid"], bench["verdict"]

    # 沒有明寫軸型的格,每條軸都是連續軸:只有一層,鄰域沿全部軸取。
    assert grid.axis_kinds == {"fast": CONTINUOUS, "slow": CONTINUOUS}
    assert grid.choice_axes == ()
    assert grid.layers() == ((),)
    assert len(grid.neighbours(SweepPoint(values=(("fast", 4), ("slow", 4))))) == 8

    # 山脊要有選擇軸才可能成立,所以規則型格永遠判不出山脊。
    assert verdict.choice_axes == ()
    assert verdict.ridges == ()
    assert "不會出現山脊" in verdict.axes_line()

    # 三種形狀逐格照舊:平原一片、孤峰一格、無效一列。
    assert _cell(verdict, *PEAK_CELL).verdict == LONELY_PEAK
    assert _cell(verdict, *PLATEAU_CENTRE).verdict == PLATEAU
    # 平原那兩格是 KARST-029 當日判出來的原數(高地那一片邊上的格,鄰域被無效那
    # 一列拉低,所以只有中間兩格站得住)——本票一格都不准移。
    assert {
        (int(c.point.get("fast")), int(c.point.get("slow"))) for c in verdict.plateaus
    } == {(2, 3), (3, 3)}
    assert all(c.verdict == INVALID for c in verdict.cells if int(c.point.get("fast")) == THIN_FAST)

    # 換層的欄位在,但一格都用不著——沒有選擇軸就沒有別的層可以比。
    frame = verdict.frame()
    assert {"layer", "weakest_sibling_mean", "layer_drop"} <= set(frame.columns)
    assert frame["weakest_sibling_mean"].isna().all()
    assert (frame["layer"] == "全格(沒有選擇軸)").all()


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
