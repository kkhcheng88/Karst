"""KARST-036 驗收:因子輪動驅動器——按訊號在四隻因子 ETF 之間動態移權。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況(2026-08-26 用戶明令
實作期驗證從簡)。**全部離線**:價格是砌出來的,一次都不連網、不碰真實快照。

合成價格刻意鋪成四種脾性,好令四個驅動器真的分得出高下:動能那隻升得最急、
質素次之、價值原地打轉、低波升得慢但最穩;大市(SPY)介乎中間。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from karst.engine import PricePanel
from karst.engine.contracts import SimulationOutput
from karst.gateway.service import Gateway
from karst.runs import RunStore
from karst.strategies.factor_mix import (
    FACTOR_ETF_SLEEVES,
    FactorMixParams,
    factor_mix_targets,
    resolve_exposures,
)
from karst.strategies.factor_rotation import (
    DRIVER_PARAMETERS,
    EXTERNAL_DATA,
    PRICE_DRIVER_KEYS,
    macro_series_needed,
    SOURCE_DRIVER,
    DriverView,
    FactorRotationParams,
    build_driver,
    resolve_rotation_exposures,
    rotation_targets,
    run_factor_rotation,
)
from karst.sweep import (
    LONELY_PEAK,
    VERDICTS,
    CellScore,
    ExplicitGrid,
    FactorMixJob,
    judge,
    reference_point,
    run_sweep,
    write_report,
)
from karst.sweep.factor_rotation import (
    FactorRotationJob,
    ScoreEntry,
    ensure_factor_rotation_setup,
    rotation_grid,
    scoreboard,
)

from doubles.engines import RecordingEngine

ROTATION_STRATEGY = "因子輪動(ETF 版)"
MIX_STRATEGY = "因子混合(ETF 版)"
ENGINE_VERSION = "0.1.0"
MARKET = "SPY"
RISK_FREE = 0.04

DATES = pd.bdate_range("2020-01-01", periods=400)
PERIOD = (str(DATES[0].date()), str(DATES[-1].date()))

# 熱身期:最長的回望期是 3 個月(約 63 根),90 根綽綽有餘,而且整份測試共用
# 同一個數——每一格於是走同一段日子。
WARMUP_BARS = 90
WARMUP_WEIGHTS = {sleeve.weight_key: 0.25 for sleeve in FACTOR_ETF_SLEEVES}

# 四隻因子 ETF 的脾性:(年漂移, 日波幅)。動能最急、低波最穩、價值原地打轉。
PERSONALITY = {
    "MTUM": (0.0011, 0.013),
    "QUAL": (0.0006, 0.010),
    "VLUE": (0.0000, 0.011),
    "USMV": (0.0003, 0.005),
    "SPY": (0.0005, 0.009),
}


# 那個只做記錄的可換件引擎住在 tests/doubles/engines.py(KARST-090)。


def _prices(store) -> tuple[PricePanel, dict[str, int]]:
    """登記五個實體與代號,砌一張玩具價格面板(四隻因子 ETF 加大市)。"""
    generator = np.random.default_rng(20260828)
    entity_of: dict[str, int] = {}
    columns: dict[int, np.ndarray] = {}

    members = [(s.ticker, s.display_name) for s in FACTOR_ETF_SLEEVES]
    members.append((MARKET, "SPDR S&P 500 ETF Trust"))
    for ticker, display in members:
        entity_id = store.register_entity(kind="etf", display_name=display, local_code=ticker)
        store.register_ticker(entity_id, ticker, valid_from=str(DATES[0].date()))
        entity_of[ticker] = entity_id
        drift, volatility = PERSONALITY[ticker]
        steps = generator.normal(drift, volatility, len(DATES))
        columns[entity_id] = 100.0 * np.exp(np.cumsum(steps))

    close = pd.DataFrame(columns, index=DATES)
    open_prices = close.shift(1)
    open_prices.iloc[0] = close.iloc[0]
    return PricePanel.from_frames(open=open_prices * 1.0005, close=close), entity_of


@pytest.fixture()
def toy(tmp_path, monkeypatch):
    """一個獨立的庫:五個實體、四個因子、輪動與混合兩套策略、一個快照。"""
    monkeypatch.setenv("KARST_WRITER", "KARST-036-rotation2-test")
    with Gateway.open(str(tmp_path / "karst.sqlite")) as gateway:
        store = gateway.store
        panel, entity_of = _prices(store)
        snapshot_id = store.register_snapshot(
            source="test",
            taken_on="2026-08-28",
            content_hash="b1c2d3e4f5060708",
            universe=tuple(entity_of),
        )
        rotation = ensure_factor_rotation_setup(
            gateway,
            strategy_name=ROTATION_STRATEGY,
            snapshot_id=snapshot_id,
            setup_param_set_name="測試基座-輪動",
            setup_weights=WARMUP_WEIGHTS,
            cadence="quarterly",
            description="KARST-036 測試基座,不是現役設定",
        )
        mix = ensure_factor_rotation_setup(
            gateway,
            strategy_name=MIX_STRATEGY,
            snapshot_id=snapshot_id,
            setup_param_set_name="測試基座-混合",
            setup_weights=WARMUP_WEIGHTS,
            cadence="quarterly",
            description="KARST-036 對照用的固定權重策略",
        )
        yield {
            "gateway": gateway,
            "store": store,
            "panel": panel,
            "entity_of": entity_of,
            "snapshot_id": snapshot_id,
            "rotation": rotation,
            "mix": mix,
            "runs": RunStore(store, root=tmp_path / "runs"),
            "tmp": tmp_path,
        }


def _params(cadence: str = "quarterly") -> FactorRotationParams:
    return FactorRotationParams(
        cadence=cadence, warmup_bars=WARMUP_BARS, warmup_weights=WARMUP_WEIGHTS
    )


# 每個驅動器一組**寫明的**參數(無預設值,測試一樣要寫出來)。
DRIVER_CASES = {
    "factor_momentum": {"lookback_months": 3, "mode": "winner"},
    "relative_strength": {"lookback_months": 3, "fallback": "cash"},
    "inverse_volatility": {"lookback_days": 63, "power": 1.0},
    "trend_switch": {"ma_days": 50, "tilt": 1.0},
}


def _rotation_job(toy, driver_key: str, cadence: str | None = None) -> FactorRotationJob:
    return FactorRotationJob(
        gateway=toy["gateway"],
        panel=toy["panel"],
        driver_key=driver_key,
        strategy_name=ROTATION_STRATEGY,
        snapshot_id=toy["snapshot_id"],
        engine_version=ENGINE_VERSION,
        param_set_prefix=f"測試r-{driver_key}-",
        period_start=PERIOD[0],
        period_end=PERIOD[1],
        warmup_bars=WARMUP_BARS,
        warmup_weights=WARMUP_WEIGHTS,
        cadence=cadence,
        strategy_version_no=toy["rotation"].version_no,
        market_ticker=MARKET,
    )


# ----------------------------------------------------------------------
# 驗收條件 1:四個驅動器同一套快照、同一期間、同一節奏跑得出完整回測,
#             成績表列齊八項指標與對固定權重最佳格的差距
# ----------------------------------------------------------------------


def test_four_drivers_run_on_one_snapshot_and_land_on_one_scoreboard(toy):
    runs = toy["runs"]
    entries: list[ScoreEntry] = []

    for driver_key, params in DRIVER_CASES.items():
        grid = rotation_grid(
            driver_key,
            values={name: [params[name]] for name in DRIVER_PARAMETERS[driver_key]},
            cadences=["quarterly"],
        )
        sweep = run_sweep(
            runs=runs,
            grid=grid,
            job=_rotation_job(toy, driver_key),
            sweep_id=f"測試-驅動器對照-{driver_key}",
            risk_free_rate=RISK_FREE,
            benchmarks=(),
        )
        assert len(sweep) == 1
        cell = sweep.cells[0]
        # 完整回測:有淨值、有成交、八項指標算得出。
        assert cell.trades > 0
        assert cell.metrics.trading_days == len(DATES)
        entries.append(
            ScoreEntry(label=driver_key, kind="驅動器", cell=cell, verdict=None)
        )

    # 對照:固定權重,同一套快照、同一期間、同一節奏,走因子混合那條原路。
    mix_job = FactorMixJob(
        gateway=toy["gateway"],
        panel=toy["panel"],
        sleeves=FACTOR_ETF_SLEEVES,
        strategy_name=MIX_STRATEGY,
        snapshot_id=toy["snapshot_id"],
        engine_version=ENGINE_VERSION,
        param_set_prefix="測試w-",
        period_start=PERIOD[0],
        period_end=PERIOD[1],
        strategy_version_no=toy["mix"].version_no,
    )
    fixed = run_sweep(
        runs=runs,
        grid=ExplicitGrid(
            [
                reference_point(
                    FACTOR_ETF_SLEEVES,
                    {"weight_quality": 0.0, "weight_value": 0.0,
                     "weight_momentum": 1.0, "weight_low_vol": 0.0},
                    cadence="quarterly",
                )
            ],
            label="對照格(固定權重最優)",
        ),
        job=mix_job,
        sweep_id="測試-固定權重對照",
        risk_free_rate=RISK_FREE,
        benchmarks=(),
    )
    entries.append(
        ScoreEntry(label="固定權重·全押動能", kind="對照", cell=fixed.cells[0])
    )

    # 同一套快照、同一期間:五行的來歷對得上。
    assert {entry.cell.plan.snapshot_id for entry in entries} == {toy["snapshot_id"]}
    assert {(e.cell.plan.period_start, e.cell.plan.period_end) for entry in entries
            for e in [entry]} == {PERIOD}

    table = scoreboard(entries, objective="annual_return", baselines=["固定權重·全押動能"])
    assert len(table) == 5
    # 八項指標齊。
    for column in (
        "total_return", "annual_return", "max_drawdown", "win_rate",
        "profit_loss_ratio", "sortino", "average_holding_days", "turnover",
    ):
        assert column in table.columns
    # 對固定權重那一格的差距,逐行算得出,而且真的是「本行減對照」。
    gap = "對「固定權重·全押動能」的差距"
    assert gap in table.columns
    baseline = float(table.loc[table["名稱"] == "固定權重·全押動能", "annual_return"].iloc[0])
    for _, row in table.iterrows():
        assert row[gap] == pytest.approx(float(row["annual_return"]) - baseline)
    assert float(table.loc[table["名稱"] == "固定權重·全押動能", gap].iloc[0]) == 0.0


# ----------------------------------------------------------------------
# 驗收條件 2:每個驅動器連參數格出穩健平原報告,孤峰按 KARST-029 判準標出
# ----------------------------------------------------------------------


def test_each_driver_gets_a_plateau_report_and_lonely_peaks_are_marked(toy, tmp_path):
    grid = rotation_grid(
        "factor_momentum",
        values={"lookback_months": [1, 2, 3], "mode": ["winner", "rank"]},
        cadences=["quarterly"],
    )
    assert len(grid.points()) == 6

    sweep = run_sweep(
        runs=toy["runs"],
        grid=grid,
        job=_rotation_job(toy, "factor_momentum"),
        sweep_id="測試-動能驅動器格",
        risk_free_rate=RISK_FREE,
        benchmarks=(),
    )
    verdict = judge(
        sweep.scores("annual_return"),
        grid,
        objective="annual_return",
        min_trades=4,
        lonely_peak_margin=0.02,
        plateau_quantile=0.80,
    )
    # 判讀走的正是 KARST-029 那一套:每一格貼一個標籤,鄰域平均含自己與不含自己
    # 兩個數都在。
    assert len(verdict) == 6
    assert {cell.verdict for cell in verdict.cells} <= set(VERDICTS)
    frame = verdict.frame()
    assert {"neighbourhood_mean", "neighbour_mean", "lift", "verdict"} <= set(frame.columns)

    out = tmp_path / "報告"
    report = write_report(
        sweep, verdict, out, title="因子動量排名(測試)", top=3,
    )
    text = report.read_text(encoding="utf-8")
    assert (out / "掃描表.csv").exists() and (out / "判讀表.csv").exists()
    # 三個門檻與相鄰的定義一定要印得出,否則裁決講不出根據。
    assert verdict.thresholds_line() in text
    # KARST-048 起這個格自報軸型:模式與節奏是選擇軸,鄰域只沿回望期走。
    assert "相鄰 = 每條連續軸最多移一步且不可全部不動,選擇軸釘死不動" in text
    assert "lookback_months(連續)" in text and "mode(選擇)" in text

    # 孤峰按同一套判準標出:在**這個輪動格自己的相鄰定義**上鋪一格獨高的成績,
    # 判讀就要把它叫做孤峰(價格數據不一定配合,所以這一格是明明白白鋪出來的)。
    peak = grid.points()[0]
    scores = [
        CellScore(point=point, value=(1.0 if point == peak else 0.1), trades=10)
        for point in grid.points()
    ]
    rigged = judge(
        scores, grid, objective="annual_return",
        min_trades=4, lonely_peak_margin=0.05, plateau_quantile=0.80,
    )
    assert rigged.cell_for(peak).verdict == LONELY_PEAK
    assert rigged.cell_for(peak).is_local_peak


# ----------------------------------------------------------------------
# 驗收條件 3:驅動器是策略層可換件——換驅動器不改引擎、不改因子混合的目標比重路徑
# ----------------------------------------------------------------------


def test_swapping_the_driver_changes_only_the_weights_not_the_path(toy):
    store, panel = toy["store"], toy["panel"]

    class HalfAndHalfDriver:
        """一個**住在測試裡**的驅動器:證明外人寫的件插得進來,karst 一個字不用改。"""

        key = "half_and_half"
        name = "一半一半(測試自訂)"
        needs_market = False

        def weights(self, view: DriverView):
            head = view.keys[:2]
            return {key: (0.5 if key in head else 0.0) for key in view.keys}

        def describe(self) -> str:
            return "測試自訂:頭兩格各一半"

    engine_a, engine_b = RecordingEngine(), RecordingEngine()
    built_in = build_driver("factor_momentum", **DRIVER_CASES["factor_momentum"])

    result_a = run_factor_rotation(
        store=store, panel=panel, driver=built_in, params=_params(),
        engine=engine_a, market_ticker=MARKET,
    )
    result_b = run_factor_rotation(
        store=store, panel=panel, driver=HalfAndHalfDriver(), params=_params(),
        engine=engine_b, market_ticker=MARKET,
    )

    targets_a, targets_b = engine_a.calls[0], engine_b.calls[0]
    # 換驅動器,交給引擎的表**形狀一模一樣**:同一批日子、同一批實體編號、
    # 同一批換倉日;改變的只是那幾行的數字。
    assert targets_a.index.equals(targets_b.index)
    assert list(targets_a.columns) == list(targets_b.columns) == list(panel.entity_ids)
    rows_a = targets_a.dropna(how="all").index
    assert rows_a.equals(targets_b.dropna(how="all").index)
    assert not targets_a.loc[rows_a].equals(targets_b.loc[rows_a])
    # 自訂驅動器的決定原原本本落到表上。
    keys = [sleeve.weight_key for sleeve in FACTOR_ETF_SLEEVES]
    exposures = resolve_rotation_exposures(store, FACTOR_ETF_SLEEVES, on_date=panel.dates[0])
    entity_of = {e.weight_key: e.entity_id for e in exposures}
    last = rows_a[-1]
    assert targets_b.loc[last, entity_of[keys[0]]] == pytest.approx(0.5)
    assert targets_b.loc[last, entity_of[keys[3]]] == pytest.approx(0.0)
    # 大市那隻只做訊號,一股不持。
    assert targets_a.loc[last, toy["entity_of"][MARKET]] == pytest.approx(0.0)

    # 走的是**因子混合那條目標比重路徑**:同一個排期,連換倉日都一模一樣。
    mix_params = FactorMixParams(cadence="quarterly", weights=WARMUP_WEIGHTS)
    mix_targets, _ = factor_mix_targets(
        dates=panel.dates,
        entity_ids=panel.entity_ids,
        exposures=resolve_exposures(
            store, FACTOR_ETF_SLEEVES, mix_params, on_date=panel.dates[0]
        ),
        cadence="quarterly",
    )
    assert mix_targets.dropna(how="all").index.equals(rows_a)
    assert list(mix_targets.columns) == list(targets_a.columns)

    # 引擎收到的是同一個型別、同一組引擎參數;策略層沒有為新驅動器改過引擎。
    assert result_a.engine_name == result_b.engine_name == "recorder"
    assert result_a.driver_name != result_b.driver_name


# ----------------------------------------------------------------------
# 驗收條件 4:所需外部數據列明來源、免費與否、知情時間處置
# ----------------------------------------------------------------------


def test_no_external_data_is_needed_and_signals_never_peek_past_the_decision_day(toy):
    # KARST-036 這四個驅動器的訊號全部由快照裡的 ETF 收價算出來,一條外部序列
    # 都不用——所以它們**自己**沒有來源要列、沒有費用要付。
    # (KARST-040 之後 EXTERNAL_DATA 不再是空的:那張清單是**全檔**共用的,
    #  宏觀驅動器逐條列在那裡。這裡要守住的是「價格驅動器不碰外部數據」。)
    for key in PRICE_DRIVER_KEYS:
        assert macro_series_needed(key) == (), f"{key} 是價格驅動器,不應要外部序列"

    # 清單本身仍然逐條講明三件事,而且一條付費來源都沒有。
    for row in EXTERNAL_DATA:
        assert set(row) >= {"序列", "來源", "免費", "知情時間"}
        assert row["免費"].startswith("是")

    store, panel = toy["store"], toy["panel"]
    seen: list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]] = []

    class PeekRecorder:
        """把驅動器每次見到的最後一日記低,再照樣交一組等權出去。"""

        key = "peek_recorder"
        name = "偷看記錄器(測試)"
        needs_market = True

        def weights(self, view: DriverView):
            seen.append(
                (
                    pd.Timestamp(view.decision_date),
                    pd.Timestamp(view.history.index[-1]),
                    pd.Timestamp(view.require_market().index[-1]),
                )
            )
            return {key: 0.25 for key in view.keys}

        def describe(self) -> str:
            return "測試用:只記錄,不判斷"

    exposures = resolve_rotation_exposures(store, FACTOR_ETF_SLEEVES, on_date=panel.dates[0])
    _, rebalances = rotation_targets(
        panel=panel,
        exposures=exposures,
        driver=PeekRecorder(),
        params=_params(),
        market=panel.close[toy["entity_of"][MARKET]],
        market_ticker=MARKET,
    )

    assert seen, "驅動器一次都未被叫過"
    # 知情時間處置(D-021 第 3 條):驅動器見到的最後一根 K 線**就是**決策日那一根,
    # 四隻因子與大市兩邊都是——它根本拿不到之後的價格。
    for decision, last_factor, last_market in seen:
        assert last_factor == decision
        assert last_market == decision

    # 而成交在決策日**之後那一根** K 線;兩者永不同根。
    positions = {pd.Timestamp(day): index for index, day in enumerate(panel.dates)}
    driven = [r for r in rebalances if r.source == SOURCE_DRIVER]
    assert driven, "熱身期之後應該有驅動器話事的換倉"
    for rebalance in rebalances:
        decision = pd.Timestamp(rebalance.decision_date)
        execution = pd.Timestamp(rebalance.execution_date)
        assert positions[execution] == positions[decision] + 1

    # 要看大市的驅動器,沒有大市那條線就當場拒收,不會靜靜地當零。
    with pytest.raises(Exception):
        run_factor_rotation(
            store=store,
            panel=panel,
            driver=build_driver("trend_switch", **DRIVER_CASES["trend_switch"]),
            params=_params(),
            engine=RecordingEngine(),
            market_ticker=None,
        )
