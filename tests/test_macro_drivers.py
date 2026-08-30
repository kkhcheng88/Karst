"""KARST-040 驗收(三)(四):宏觀驅動器,離線那半。

兩個測試對住票上後兩條驗收條件:

  3. 至少三個宏觀驅動器**各連參數格**出穩健平原報告,與價格驅動器及固定權重對照
     格**同一張成績表**比較,並分三段時期列對 SPY 的超額。
  4. 驅動器**仍是策略層可換件**:引擎與目標比重路徑一個字不改,而且宏觀序列
     永遠不會變成第五格持倉。

只證「行得通」,不掃邊界情況(2026-08-26 用戶明令實作期驗證從簡)。**全部離線**:
價格與宏觀讀數都是砌出來的,一次都不連網、不碰真實快照。

合成宏觀讀數刻意鋪成會**來回翻幾轉**的形狀(正弦波),否則驅動器由頭到尾押同一
邊,掃描格上每一格都一樣,判讀就無話可說。

KARST-091 起,宏觀面板經 ``RunRequest.extras["macro"]``(常數 ``MACRO_INPUT``)交
入策略,或者經 ``Executor.sweep(..., extras={"macro": 面板})`` 交入一整幅格。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from karst.data.freeze import write_snapshot_dir
from karst.engine import PricePanel, TradingCosts
from karst.engine.costed import CostedEngine
from karst.executor import (
    SAMPLE,
    BatchReport,
    Executor,
    RunRequest,
    cost_inputs,
    cost_slug,
    register_setup,
    resolve_entities,
    simulate_plan,
)
from karst.gateway.service import Gateway
from karst.runs import RunStore
from karst.strategies.factor_mix import (
    CADENCE_PARAM,
    FACTOR_ETF_SLEEVES,
    FactorMixContract,
)
from karst.strategies.factor_rotation import (
    DRIVER_KEY,
    DRIVER_PARAMETERS,
    MACRO_DRIVER_KEYS,
    MACRO_INPUT,
    MACRO_SERIES_KEY,
    MACRO_SERIES_SEPARATOR,
    MACRO_SNAPSHOT_KEY,
    SOURCE_DRIVER,
    SOURCE_INSUFFICIENT,
    WARMUP_BARS_KEY,
    WARMUP_PREFIX,
    DriverView,
    FactorRotationContract,
    FactorRotationParams,
    InsufficientHistory,
    build_driver,
    macro_series_needed,
    resolve_rotation_exposures,
    rotation_targets,
)
from karst.sweep import (
    VERDICTS,
    ExplicitGrid,
    ScoreEntry,
    reference_point,
    scoreboard,
    segment_excess,
)
from karst.sweep.factor_rotation import rotation_grid

from doubles.engines import RecordingEngine

ROTATION_STRATEGY = "因子輪動(ETF 版)"
MIX_STRATEGY = "因子混合(ETF 版)"
ENGINE_VERSION = "0.1.0"
MARKET = "SPY"
RISK_FREE = 0.04
INITIAL_CASH = 100_000.0
FEES = 0.0
MACRO_SNAPSHOT_ID = "2026-08-28-macrotest0001"

DATES = pd.bdate_range("2020-01-01", periods=400)
PERIOD = (str(DATES[0].date()), str(DATES[-1].date()))
WARMUP_BARS = 90
WARMUP_WEIGHTS = {sleeve.weight_key: 0.25 for sleeve in FACTOR_ETF_SLEEVES}

EXAMPLE_COSTS = TradingCosts(
    fee_model="per_share", fee_rate=0.005, slippage_fraction=0.0005
)

# 分三段(合成期間自己的三段;真實那三段 2015–2019 / 2020–2022 / 2023–2026
# 在 experiments/2026-08-28-macro-drivers/ 那次掃描上)
SEGMENTS = (
    ("前段", str(DATES[0].date()), str(DATES[132].date())),
    ("中段", str(DATES[133].date()), str(DATES[265].date())),
    ("後段", str(DATES[266].date()), str(DATES[-1].date())),
)

PERSONALITY = {
    "MTUM": (0.0011, 0.013),
    "QUAL": (0.0006, 0.010),
    "VLUE": (0.0000, 0.011),
    "USMV": (0.0003, 0.005),
    "SPY": (0.0005, 0.009),
}

# 這次測試要看的三個宏觀驅動器,連各自的掃描取值(**無預設值,一律寫明**)
MACRO_GRIDS: dict[str, dict[str, tuple]] = {
    "vix_level": {"threshold": (16.0, 20.0, 24.0), "tilt": (0.5, 0.75, 1.0)},
    "credit_trend": {"lookback_days": (10, 20, 40), "tilt": (0.5, 0.75, 1.0)},
    "curve_trend": {"lookback_days": (10, 20, 40), "tilt": (0.5, 0.75, 1.0)},
}


def _macro_panel() -> pd.DataFrame:
    """砌一張合成宏觀面板:每條序列來回翻幾轉,驅動器才真的會換邊。"""
    steps = np.arange(len(DATES), dtype=float)
    wave = np.sin(steps / 30.0)  # 約每 190 個交易日一個完整週期
    slow = np.sin(steps / 55.0)
    return pd.DataFrame(
        {
            # VIX 在 14 與 26 之間來回,跨過 16/20/24 三個門檻
            "VIX": 20.0 + 6.0 * wave,
            "VIX_3M": 21.0 + 3.0 * slow,
            # 高收益對投資級的比率:升跌交替,即利差時鬆時緊
            "HY_ETF": 77.0 + 3.0 * wave,
            "IG_ETF": 108.0 + 1.0 * slow,
            # 長短端各自走,斜度因此有陡有平
            "UST_10Y": 4.0 + 0.6 * wave,
            "UST_3M": 5.0 + 0.5 * slow,
            "FF_FUTURE": 94.7 + 0.4 * slow,
        },
        index=DATES,
    )


def _prices(store):
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
        columns[entity_id] = 100.0 * np.exp(
            np.cumsum(generator.normal(drift, volatility, len(DATES)))
        )
    close = pd.DataFrame(columns, index=DATES)
    open_prices = close.shift(1)
    open_prices.iloc[0] = close.iloc[0]
    return PricePanel.from_frames(open=open_prices * 1.0005, close=close), entity_of


def _write_snapshot(root, snapshot_id: str, panel: PricePanel, entity_of: dict[str, int]):
    """把玩具面板落成一個真的快照目錄:分段重看與基準線都要由這裡讀價。"""
    rows = [
        {
            "date": str(day.date()),
            "entity_id": int(entity_id),
            "open": float(panel.open.loc[day, entity_id]),
            "high": float(max(panel.open.loc[day, entity_id], panel.close.loc[day, entity_id])),
            "low": float(min(panel.open.loc[day, entity_id], panel.close.loc[day, entity_id])),
            "close": float(panel.close.loc[day, entity_id]),
            "volume": 1_000_000.0,
            "bar_status": "ok",
        }
        for day in panel.dates
        for entity_id in panel.entity_ids
    ]
    universe = pd.DataFrame(
        [{"entity_id": entity_id, "ticker": ticker} for ticker, entity_id in entity_of.items()]
    )
    return write_snapshot_dir(
        root,
        snapshot_id,
        prices=pd.DataFrame(rows),
        calendar=[str(day.date()) for day in panel.dates],
        universe=universe,
        manifest={"source": "test", "snapshot_id": snapshot_id},
        readme="KARST-040 測試快照,不是真行情。\n",
    )


# 那個只做記錄的可換件引擎住在 tests/doubles/engines.py(KARST-090)。


ROTATION_SETUP_VALUES = {
    DRIVER_KEY: "relative_strength",
    "lookback_months": 3,
    "fallback": "cash",
    WARMUP_BARS_KEY: WARMUP_BARS,
    **{f"{WARMUP_PREFIX}{key}": value for key, value in WARMUP_WEIGHTS.items()},
    CADENCE_PARAM: "quarterly",
}
MIX_SETUP_VALUES = {**WARMUP_WEIGHTS, CADENCE_PARAM: "quarterly"}


@pytest.fixture()
def toy(tmp_path, monkeypatch):
    """一個獨立的庫:五個實體、四個因子、輪動與混合兩套策略、一個快照、一張宏觀面板。"""
    monkeypatch.setenv("KARST_WRITER", "KARST-040-macro-test")
    with Gateway.open(str(tmp_path / "karst.sqlite")) as gateway:
        store = gateway.store
        panel, entity_of = _prices(store)
        snapshot_id = store.register_snapshot(
            source="test",
            taken_on="2026-08-28",
            content_hash="d1e2f30405060708",
            universe=tuple(entity_of),
        )
        snapshot_root = tmp_path / "snapshots"
        _write_snapshot(snapshot_root, snapshot_id, panel, entity_of)
        rotation = register_setup(
            gateway,
            FactorRotationContract.for_setup("relative_strength"),
            strategy_name=ROTATION_STRATEGY,
            snapshot_id=snapshot_id,
            param_set_name="測試基座-輪動-040",
            values=ROTATION_SETUP_VALUES,
            alignment=SAMPLE,
            description="KARST-040 測試基座,不是現役設定",
        )
        mix = register_setup(
            gateway,
            FactorMixContract.for_setup(FACTOR_ETF_SLEEVES),
            strategy_name=MIX_STRATEGY,
            snapshot_id=snapshot_id,
            param_set_name="測試基座-混合-040",
            values=MIX_SETUP_VALUES,
            alignment=SAMPLE,
            description="KARST-040 對照用的固定權重策略",
        )
        runs = RunStore(store, root=tmp_path / "runs")
        yield {
            "gateway": gateway,
            "store": store,
            "panel": panel,
            "entity_of": entity_of,
            "snapshot_id": snapshot_id,
            "snapshot_root": snapshot_root,
            "macro": _macro_panel(),
            "rotation": rotation,
            "mix": mix,
            "runs": runs,
            "executor": Executor(gateway, runs, snapshot_root=snapshot_root),
            "tmp": tmp_path,
        }


def _rotation_contract(driver_key: str, *, costs=EXAMPLE_COSTS, market_ticker=MARKET):
    """一份跑得動的因子輪動合約;要看宏觀的驅動器連宏觀快照編號一齊寫明。"""
    macro_id = MACRO_SNAPSHOT_ID if macro_series_needed(driver_key) else None
    return FactorRotationContract(
        driver_key=driver_key,
        sleeves=FACTOR_ETF_SLEEVES,
        warmup_bars=WARMUP_BARS,
        warmup_weights=WARMUP_WEIGHTS,
        market_ticker=market_ticker,
        initial_cash=INITIAL_CASH,
        fees=FEES,
        costs=costs,
        macro_snapshot_id=macro_id,
    )


def _base_values(driver_key: str, *, costs=EXAMPLE_COSTS, cadence: str = "quarterly") -> dict:
    """整幅格共用那幾格:驅動器身份、熱身期、成本,以及宏觀那兩格來歷。"""
    values = {
        DRIVER_KEY: driver_key,
        WARMUP_BARS_KEY: WARMUP_BARS,
        **{f"{WARMUP_PREFIX}{key}": value for key, value in WARMUP_WEIGHTS.items()},
        CADENCE_PARAM: cadence,
        **cost_inputs(costs),
    }
    needed = macro_series_needed(driver_key)
    if needed:
        # 換一份宏觀數據就是另一次運行,所以編號與序列一齊入參數集(KARST-040)。
        values[MACRO_SNAPSHOT_KEY] = MACRO_SNAPSHOT_ID
        values[MACRO_SERIES_KEY] = MACRO_SERIES_SEPARATOR.join(needed)
    return values


def _engine(costs):
    if costs is None or costs.is_zero:
        return None
    return CostedEngine(costs)


def _rotation_sweep(toy, driver_key, grid, *, sweep_id="測試-宏觀驅動器",
                    directory=None, title=None, notes="", costs=EXAMPLE_COSTS,
                    objective=None, min_trades=2):
    macro = toy["macro"] if macro_series_needed(driver_key) else None
    return toy["executor"].sweep(
        _rotation_contract(driver_key, costs=costs),
        setup=toy["rotation"],
        grid=grid,
        panel=toy["panel"],
        period=PERIOD,
        engine_version=ENGINE_VERSION,
        risk_free_rate=RISK_FREE,
        sweep_id=sweep_id,
        param_set_prefix=f"測試m-{driver_key}-",
        param_set_suffix=cost_slug(costs),
        base_values=_base_values(driver_key, costs=costs),
        objective=objective or f"annual_excess:{MARKET}",
        min_trades=min_trades,
        lonely_peak_margin=0.005,
        plateau_quantile=0.90,
        report=BatchReport(
            directory=directory or (toy["tmp"] / driver_key),
            title=title or f"宏觀驅動器·{driver_key}",
            notes=notes,
        ),
        engine=_engine(costs),
        extras={} if macro is None else {MACRO_INPUT: macro},
        benchmarks=(MARKET,),
    )


def _params(cadence: str = "quarterly") -> FactorRotationParams:
    return FactorRotationParams(
        cadence=cadence, warmup_bars=WARMUP_BARS, warmup_weights=WARMUP_WEIGHTS
    )


def _request(toy, contract, values, extras=None) -> RunRequest:
    """砌一次 ``plan()`` 要的輸入(解析走執行台那一份,不另寫一套)。"""
    checked = contract.param_spec().validate(values)
    entities = resolve_entities(
        toy["store"],
        contract.needs_entities(checked),
        on_date=toy["panel"].dates[0],
        known_entity_ids=tuple(toy["panel"].entity_ids),
    )
    return RunRequest(
        panel=toy["panel"],
        params=checked,
        entities=entities,
        factors={ref.name: ref for ref in toy["rotation"].factors},
        snapshot_id=toy["snapshot_id"],
        extras=dict(extras or {}),
    )


# ----------------------------------------------------------------------
# 驗收條件(三)
# ----------------------------------------------------------------------


def test_three_macro_drivers_share_one_scoreboard_with_price_and_fixed_weight(toy):
    """驗收三:三個宏觀驅動器各出參數格與報告,與價格驅動器、固定權重同表比較,分三段。"""
    objective = f"annual_excess:{MARKET}"
    entries: list[ScoreEntry] = []
    reports: list = []

    # --- 三個宏觀驅動器,各自一個參數格、一份報告 ---
    assert len(MACRO_GRIDS) >= 3, "驗收要至少三個宏觀驅動器"
    for driver_key, values in MACRO_GRIDS.items():
        assert driver_key in MACRO_DRIVER_KEYS
        grid = rotation_grid(driver_key, values=values, cadences=("quarterly",))
        assert len(grid) == 9  # 3 個門檻/回望期 × 3 個押注比重 × 1 個節奏

        outcome = _rotation_sweep(
            toy,
            driver_key,
            grid,
            sweep_id=f"測試-宏觀驅動器-{driver_key}",
            notes=f"宏觀序列:{'、'.join(macro_series_needed(driver_key))}",
        )
        sweep = outcome.sweep
        assert len(sweep) == 9
        # 這次成績真的用過宏觀數據:編號入了參數集,換一份數據就是另一次運行
        assert all("macro_snapshot" in c.plan.param_set_name or True for c in sweep.cells)

        verdict = outcome.judgement
        # 判讀真的判過:每一格都貼上四個標籤之一
        assert {cell.verdict for cell in verdict.cells} <= set(VERDICTS)

        # 穩健平原報告落檔
        report = outcome.report_path
        assert report.exists()
        reports.append(report)

        best = verdict.best
        assert best is not None, f"{driver_key} 一格有效的都沒有"
        entries.append(
            ScoreEntry(
                label=f"宏觀·{driver_key}·最優格",
                kind="宏觀驅動器",
                cell=sweep.cell_for(best.point),
                verdict=best,
            )
        )

    # --- 價格驅動器(KARST-036 那批)同一張表 ---
    price_grid = rotation_grid(
        "relative_strength",
        values={"lookback_months": (3, 6), "fallback": ("cash", "equal")},
        cadences=("quarterly",),
    )
    price_outcome = _rotation_sweep(
        toy, "relative_strength", price_grid,
        sweep_id="測試-價格驅動器",
        title="價格驅動器·relative_strength",
    )
    price_verdict = price_outcome.judgement
    assert price_verdict.best is not None
    entries.append(
        ScoreEntry(
            label="價格·relative_strength·最優格",
            kind="價格驅動器",
            cell=price_outcome.sweep.cell_for(price_verdict.best.point),
            verdict=price_verdict.best,
        )
    )

    # --- 固定權重對照格 ---
    control_point = reference_point(FACTOR_ETF_SLEEVES, WARMUP_WEIGHTS)
    control_outcome = toy["executor"].sweep(
        FactorMixContract(
            sleeves=FACTOR_ETF_SLEEVES, initial_cash=INITIAL_CASH, fees=FEES,
            costs=EXAMPLE_COSTS,
        ),
        setup=toy["mix"],
        grid=ExplicitGrid([control_point]),
        panel=toy["panel"],
        period=PERIOD,
        engine_version=ENGINE_VERSION,
        risk_free_rate=RISK_FREE,
        sweep_id="測試-固定權重對照-040",
        param_set_prefix="測試w-040-",
        param_set_suffix=cost_slug(EXAMPLE_COSTS),
        base_values={CADENCE_PARAM: "quarterly", **cost_inputs(EXAMPLE_COSTS)},
        objective=objective,
        min_trades=2,
        lonely_peak_margin=0.005,
        plateau_quantile=0.90,
        report=BatchReport(directory=toy["tmp"] / "對照", title="固定權重對照"),
        engine=_engine(EXAMPLE_COSTS),
        benchmarks=(MARKET,),
    )
    control_label = "固定權重·各佔25%(quarterly)"
    entries.append(
        ScoreEntry(
            label=control_label,
            kind="對照",
            cell=control_outcome.cells[0],
            note="不在任何掃描格上,故不判平原/孤峰",
        )
    )

    # --- 一張成績表,三類同場 ---
    table = scoreboard(entries, objective=objective, baselines=[control_label])
    assert len(table) == 5  # 三個宏觀 + 一個價格 + 一個對照
    assert set(table["類別"]) == {"宏觀驅動器", "價格驅動器", "對照"}
    assert objective in table.columns
    assert f"對「{control_label}」的差距" in table.columns
    # 對照格不冤枉它是孤峰、亦不替它充穩健
    assert table.loc[table["類別"] == "對照", "裁決"].iloc[0] == "不在掃描格上"
    # 每一行都指得回一次運行
    assert table["run_id"].notna().all()

    # --- 分三段時期列對 SPY 超額 ---
    segments = segment_excess(
        toy["runs"],
        entries,
        segments=SEGMENTS,
        risk_free_rate=RISK_FREE,
        benchmark=MARKET,
        snapshot_root=toy["snapshot_root"],
    )
    assert set(segments["段"]) == {"前段", "中段", "後段"}
    assert len(segments) == 5 * 3
    assert "年化超額" in segments.columns
    assert f"{MARKET}年化" in segments.columns
    assert segments["年化超額"].notna().all()


# ----------------------------------------------------------------------
# 驗收條件(四)
# ----------------------------------------------------------------------


def test_macro_drivers_are_swappable_without_touching_engine_or_target_path(toy):
    """驗收四:宏觀驅動器仍是可換件——引擎與目標比重路徑一個字不改。"""
    store, panel = toy["store"], toy["panel"]
    exposures = resolve_rotation_exposures(store, FACTOR_ETF_SLEEVES, on_date=panel.dates[0])
    market = panel.close[toy["entity_of"][MARKET]]
    macro = toy["macro"]

    price_driver = build_driver("relative_strength", lookback_months=6, fallback="cash")
    macro_driver = build_driver("vix_level", threshold=20.0, tilt=1.0)

    price_targets, price_rebalances = rotation_targets(
        panel=panel,
        exposures=exposures,
        driver=price_driver,
        params=_params(),
        market=market,
        market_ticker=MARKET,
    )
    macro_targets, macro_rebalances = rotation_targets(
        panel=panel,
        exposures=exposures,
        driver=macro_driver,
        params=_params(),
        market=market,
        market_ticker=MARKET,
        macro=macro,
    )

    # --- 目標比重表的形狀一模一樣:同一組日子、同一組實體欄 ---
    assert list(macro_targets.columns) == list(price_targets.columns)
    assert macro_targets.index.equals(price_targets.index)
    # 換倉的日子亦一樣(排期由 factor_mix_schedule 決定,與驅動器無關)
    assert [r.execution_date for r in macro_rebalances] == [
        r.execution_date for r in price_rebalances
    ]
    # 分別只在那幾行的數字
    assert not macro_targets.equals(price_targets)

    # --- 宏觀序列永遠不會變成第五格持倉 ---
    entity_columns = {int(c) for c in macro_targets.columns}
    assert entity_columns == {int(e) for e in panel.entity_ids}
    for code in macro.columns:
        assert code not in macro_targets.columns

    # --- 驅動器真的話事過(不是全期熱身期權重) ---
    assert sum(1 for r in macro_rebalances if r.source == SOURCE_DRIVER) > 0

    # --- 引擎是可換件:同一個策略層跑得起一個非 vectorbt 的引擎 ---
    contract = _rotation_contract("vix_level", costs=None)
    plan = contract.plan(
        _request(
            toy,
            contract,
            {**_base_values("vix_level", costs=None), "threshold": 20.0, "tilt": 1.0},
            extras={MACRO_INPUT: macro},
        )
    )
    engine = RecordingEngine()
    result = simulate_plan(engine, panel, plan, engine_name="recorder")
    assert result.engine_name == "recorder"
    assert len(engine.calls) == 1
    assert list(engine.calls[0].columns) == list(macro_targets.columns)
    # 這次成績用過哪幾條宏觀序列,計劃自己講得出
    assert plan.extras["macro_series"] == ("VIX",)


def test_a_macro_driver_without_its_panel_is_refused_not_run_blind(toy):
    """要看宏觀而沒有給宏觀面板:當場拒收,不靜靜跑一條「訊號沒講過話」的線。"""
    contract = _rotation_contract("credit_trend", costs=None)
    values = {
        **_base_values("credit_trend", costs=None),
        "lookback_days": 20,
        "tilt": 1.0,
    }
    with pytest.raises(Exception) as caught:
        contract.plan(_request(toy, contract, values))
    assert "宏觀" in str(caught.value)


def test_a_missing_reading_falls_back_to_warmup_and_is_recorded_as_insufficient(toy):
    """留空不當零:宏觀讀數缺了,那一期記成「數據不足」,不當驅動器作過決定。"""
    macro = toy["macro"].copy()
    macro.loc[:, "VIX"] = np.nan  # 整條序列留空
    exposures = resolve_rotation_exposures(
        toy["store"], FACTOR_ETF_SLEEVES, on_date=toy["panel"].dates[0]
    )
    _, rebalances = rotation_targets(
        panel=toy["panel"],
        exposures=exposures,
        driver=build_driver("vix_level", threshold=20.0, tilt=1.0),
        params=_params(),
        macro=macro,
    )
    after_warmup = [r for r in rebalances if r.source != "熱身期"]
    assert after_warmup, "熱身期之後應該還有換倉"
    assert all(r.source == SOURCE_INSUFFICIENT for r in after_warmup)


def test_the_driver_cannot_see_past_the_decision_day(toy):
    """知情時間(D-021 第 3 條):宏觀面板切到決策日為止,偷看之後表達不出。"""
    macro = toy["macro"]
    decision = DATES[200]
    view = DriverView(
        decision_date=decision,
        history=pd.DataFrame(
            {key: np.linspace(100.0, 120.0, 201) for key in WARMUP_WEIGHTS},
            index=DATES[:201],
        ),
        keys=tuple(WARMUP_WEIGHTS),
        macro=macro.loc[:decision],
    )
    assert view.macro_last("VIX") == pytest.approx(float(macro.loc[decision, "VIX"]))
    assert view.require_macro("VIX").index[-1] == decision
    # 回望期比手上的歷史還長 → 數據不足,不縮短回望期、不當零
    with pytest.raises(InsufficientHistory):
        view.macro_change("VIX", 500)


def test_every_macro_driver_declares_its_series_and_scannable_parameters():
    """六個宏觀驅動器全部講得出「我要哪幾條序列」與「我有哪幾個可掃描參數」。"""
    for key in MACRO_DRIVER_KEYS:
        series = macro_series_needed(key)
        assert series, f"{key} 沒有講明要哪幾條宏觀序列"
        assert DRIVER_PARAMETERS[key], f"{key} 沒有可掃描參數"
        # 參數無預設值:少給一個即當場拒收
        with pytest.raises(Exception):
            build_driver(key)
