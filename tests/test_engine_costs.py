"""KARST-043 驗收:交易成本入引擎——手續費與滑點作可掃描參數。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況(2026-08-26 用戶明令
實作期驗證從簡)。**全部離線**:價格是砌出來的,一次都不連網、不碰真實快照。

成本的定義寫在 ``engine.TradingCosts``,兩條引擎路徑逐字相同:

- 滑點:買入成交價 = 計劃價 × (1 + s),賣出成交價 = 計劃價 × (1 − s);
- 手續費:``per_share`` 每股收 c(一筆 c × 股數)、``fraction_of_value``
  按成交金額收 r(一筆 r × 股數 × 成交價)。

這幾條算式在下面是**逐位核對**的,不是「大致對」——成本一走樣,整份重掃的結論
就會偏,而偏多少沒有人看得出來。
"""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from karst.engine import (
    FEE_MODELS,
    BarPanel,
    BreakoutEntry,
    MeasuredMoveTarget,
    MonthlyLossBreaker,
    PricePanel,
    RankingRebalanceParams,
    RiskFractionSizing,
    RuleStrategyParams,
    SwingLowStop,
    TradingCosts,
    run_rule_strategy,
)
from karst.data.snapshots import write_snapshot_dir
from karst.engine.vectorbt_engine import VectorbtEngine
from karst.errors import ContractViolation
from karst.gateway.service import Gateway
from karst.metrics import run_metrics
from karst.runs import RunStore
from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES
from karst.sweep import (
    PLATEAU,
    CellScore,
    ExplicitGrid,
    FactorMixJob,
    SweepPoint,
    judge,
    reference_point,
    run_sweep,
    write_report,
)
from karst.sweep.factor_mix import cost_slug, cost_values
from karst.sweep.factor_rotation import (
    CostPair,
    FactorRotationJob,
    cost_comparison,
    ensure_factor_rotation_setup,
    provenance_note,
    rotation_grid,
)

# 票上寫明的**示例**成本:每股 US$0.005 加滑點 5 個基點。
# 它只是一組合理的數,不是裁定值——哪一組成本才對是用戶的事(D-008)。
EXAMPLE_COSTS = TradingCosts(
    fee_model="per_share", fee_rate=0.005, slippage_fraction=0.0005
)
VALUE_COSTS = TradingCosts(
    fee_model="fraction_of_value", fee_rate=0.001, slippage_fraction=0.0005
)

ROTATION_STRATEGY = "因子輪動(ETF 版)"
MIX_STRATEGY = "因子混合(ETF 版)"
ENGINE_VERSION = "0.1.0"
MARKET = "SPY"
RISK_FREE = 0.04

DATES = pd.bdate_range("2020-01-01", periods=400)
PERIOD = (str(DATES[0].date()), str(DATES[-1].date()))
WARMUP_BARS = 90
WARMUP_WEIGHTS = {sleeve.weight_key: 0.25 for sleeve in FACTOR_ETF_SLEEVES}

PERSONALITY = {
    "MTUM": (0.0011, 0.013),
    "QUAL": (0.0006, 0.010),
    "VLUE": (0.0000, 0.011),
    "USMV": (0.0003, 0.005),
    "SPY": (0.0005, 0.009),
}


# ----------------------------------------------------------------------
# 驗收條件 1:手續費與滑點是參數集內的可掃描參數,兩條引擎路徑同一定義,
#             成本為零時既有的成績與運行編號逐位不變
# ----------------------------------------------------------------------


def _two_asset_panel() -> PricePanel:
    """兩隻股票、六根 K 線的玩具面板。開價與收價刻意不同,好分得出成交價。"""
    dates = pd.bdate_range("2021-01-04", periods=6)
    close = pd.DataFrame({101: [100.0, 104.0, 108.0, 112.0, 116.0, 120.0],
                          102: [50.0, 51.0, 52.0, 53.0, 54.0, 55.0]}, index=dates)
    open_ = pd.DataFrame({101: [99.0, 103.0, 107.0, 111.0, 115.0, 119.0],
                          102: [49.5, 50.5, 51.5, 52.5, 53.5, 54.5]}, index=dates)
    return PricePanel.from_frames(open=open_, close=close)


def _targets(panel: PricePanel) -> pd.DataFrame:
    """第二根全押、第五根清倉。目標比重表:NaN = 不下單,不是 0。"""
    targets = pd.DataFrame(np.nan, index=panel.dates, columns=list(panel.entity_ids))
    targets.iloc[1] = [0.5, 0.5]
    targets.iloc[4] = [0.0, 0.0]
    return targets


def _simulate(costs: TradingCosts | None, *, fees: float = 0.0):
    panel = _two_asset_panel()
    params = RankingRebalanceParams(
        cadence="daily", top_n=2, direction="high", fees=fees, costs=costs
    )
    return panel, VectorbtEngine().simulate(panel, _targets(panel), params)


def test_costs_are_a_scannable_parameter_shared_by_both_paths_and_free_when_zero():
    # (a) 成本合約三個欄位一個預設值都沒有:要計成本,型別、費率、滑點都要寫明
    for parameter in inspect.signature(TradingCosts).parameters.values():
        assert parameter.default is inspect.Parameter.empty, parameter.name
    assert FEE_MODELS == {"per_share", "fraction_of_value"}
    with pytest.raises(ContractViolation):
        TradingCosts(fee_model="每股", fee_rate=0.005, slippage_fraction=0.0005)
    with pytest.raises(ContractViolation):
        TradingCosts(fee_model="per_share", fee_rate=-0.001, slippage_fraction=0.0)

    # (b) 成本為零:結果與成本入引擎之前**逐位**相同(不是「差不多」)
    _, old = _simulate(None)                       # 舊寫法:連 costs 這一格都沒有
    _, zero = _simulate(TradingCosts.zero())       # 新寫法:明示零成本
    assert np.array_equal(old.equity_curve.to_numpy(), zero.equity_curve.to_numpy())
    assert np.array_equal(old.holdings.to_numpy(), zero.holdings.to_numpy())
    assert len(old.orders) == len(zero.orders) == 4
    for a, b in zip(old.orders, zero.orders, strict=True):
        assert (a.trade_date, a.entity_id, a.side) == (b.trade_date, b.entity_id, b.side)
        assert a.shares == b.shares and a.price == b.price and a.fees == b.fees

    # (c) 每股手續費:訂單表交回「滑點後成交價」與「每股費 × 股數」,逐位對得上
    panel, per_share = _simulate(EXAMPLE_COSTS)
    slip = EXAMPLE_COSTS.slippage_fraction
    for order in per_share.orders:
        quoted = float(panel.open.loc[pd.Timestamp(order.trade_date), order.entity_id])
        sign = 1.0 if order.side == "buy" else -1.0
        assert order.price == pytest.approx(quoted * (1.0 + sign * slip), rel=1e-12)
        assert order.fees == pytest.approx(order.shares * EXAMPLE_COSTS.fee_rate, rel=1e-12)

    # (d) 按成交金額比例的手續費:一筆收 費率 × 股數 × 成交價(成交價已含滑點)
    _, by_value = _simulate(VALUE_COSTS)
    for order in by_value.orders:
        assert order.fees == pytest.approx(
            order.shares * order.price * VALUE_COSTS.fee_rate, rel=1e-9
        )

    # (e) 成本可掃描:掃兩格不同成本,結果不同,而且成本越貴收得越少
    assert per_share.equity_curve.iloc[-1] < zero.equity_curve.iloc[-1]
    assert by_value.equity_curve.iloc[-1] < zero.equity_curve.iloc[-1]

    # (f) 成本只可以有一個講法:舊的 fees 與新的成本合約同時交即拒收
    with pytest.raises(ContractViolation):
        RankingRebalanceParams(
            cadence="daily", top_n=2, direction="high", fees=0.001, costs=EXAMPLE_COSTS
        )

    # (g) 規則路徑**同一份定義**:同樣的算式,在另一條引擎路徑上逐位成立
    rule_panel, rule_orders = _rule_orders(EXAMPLE_COSTS)
    assert rule_orders, "規則路徑要有成交,否則這一條等於沒有驗"
    for order in rule_orders:
        assert order.fees == pytest.approx(order.shares * EXAMPLE_COSTS.fee_rate, rel=1e-12)
        if order.side == "buy":
            quoted = float(rule_panel.open.loc[pd.Timestamp(order.trade_date), order.entity_id])
            assert order.price == pytest.approx(quoted * (1.0 + slip), rel=1e-12)
    _, zero_rule_orders = _rule_orders(TradingCosts.zero())
    assert all(order.fees == 0.0 for order in zero_rule_orders)


def _rule_orders(costs: TradingCosts):
    """規則路徑跑一次,交回 K 線面板與逐筆訂單。"""
    generator = np.random.default_rng(20260828)
    dates = pd.bdate_range("2021-01-04", periods=260)
    steps = generator.normal(0.0012, 0.012, (len(dates), 4))
    close = pd.DataFrame(100.0 * np.exp(np.cumsum(steps, axis=0)), index=dates,
                         columns=[201, 202, 203, 204])
    open_ = close.shift(1)
    open_.iloc[0] = close.iloc[0]
    high = pd.DataFrame(np.maximum(open_.to_numpy(), close.to_numpy()) * 1.01,
                        index=dates, columns=close.columns)
    low = pd.DataFrame(np.minimum(open_.to_numpy(), close.to_numpy()) * 0.99,
                       index=dates, columns=close.columns)
    panel = BarPanel.from_frames(open=open_, high=high, low=low, close=close)
    params = RuleStrategyParams(
        entry=BreakoutEntry(lookback_days=20),
        stop=SwingLowStop(lookback_days=10, min_stop_fraction=0.01, max_stop_fraction=0.25),
        target=MeasuredMoveTarget(min_reward_risk=1.0),
        sizing=RiskFractionSizing(
            risk_per_trade=0.05, max_position_fraction=0.30, equity_basis="current_equity"
        ),
        breaker=MonthlyLossBreaker(max_monthly_drawdown=0.10),
        initial_cash=1_000_000.0,
        fees=0.0,
        tie_break_seed=20260828,
        costs=costs,
    )
    return panel, run_rule_strategy(panel=panel, params=params).orders


# ----------------------------------------------------------------------
# 玩具庫:四隻因子 ETF 加大市,一個快照,輪動與混合兩套策略
# ----------------------------------------------------------------------


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
            "date": str(day.date()), "entity_id": int(entity_id),
            "open": float(panel.open.loc[day, entity_id]),
            "high": float(max(panel.open.loc[day, entity_id], panel.close.loc[day, entity_id])),
            "low": float(min(panel.open.loc[day, entity_id], panel.close.loc[day, entity_id])),
            "close": float(panel.close.loc[day, entity_id]),
            "volume": 1_000_000.0, "bar_status": "ok",
        }
        for day in panel.dates
        for entity_id in panel.entity_ids
    ]
    universe = pd.DataFrame(
        [{"entity_id": entity_id, "ticker": ticker} for ticker, entity_id in entity_of.items()]
    )
    return write_snapshot_dir(
        root, snapshot_id,
        prices=pd.DataFrame(rows),
        calendar=[str(day.date()) for day in panel.dates],
        universe=universe,
        manifest={"source": "test", "snapshot_id": snapshot_id},
        readme="KARST-043 測試快照,不是真行情。\n",
    )


@pytest.fixture()
def toy(tmp_path, monkeypatch):
    monkeypatch.setenv("KARST_WRITER", "KARST-043-costs-test")
    with Gateway.open(str(tmp_path / "karst.sqlite")) as gateway:
        store = gateway.store
        panel, entity_of = _prices(store)
        snapshot_id = store.register_snapshot(
            source="test", taken_on="2026-08-28", content_hash="c1d2e3f405060708",
            universe=tuple(entity_of),
        )
        snapshot_root = tmp_path / "snapshots"
        _write_snapshot(snapshot_root, snapshot_id, panel, entity_of)
        rotation = ensure_factor_rotation_setup(
            gateway, strategy_name=ROTATION_STRATEGY, snapshot_id=snapshot_id,
            setup_param_set_name="測試基座-輪動-043", setup_weights=WARMUP_WEIGHTS,
            cadence="quarterly", description="KARST-043 測試基座,不是現役設定",
        )
        mix = ensure_factor_rotation_setup(
            gateway, strategy_name=MIX_STRATEGY, snapshot_id=snapshot_id,
            setup_param_set_name="測試基座-混合-043", setup_weights=WARMUP_WEIGHTS,
            cadence="quarterly", description="KARST-043 對照用的固定權重策略",
        )
        yield {
            "gateway": gateway, "store": store, "panel": panel, "snapshot_id": snapshot_id,
            "rotation": rotation, "mix": mix, "snapshot_root": snapshot_root,
            "runs": RunStore(store, root=tmp_path / "runs"), "tmp": tmp_path,
        }


def _rotation_job(toy, driver_key: str, costs: TradingCosts | None, cadence: str = "quarterly"):
    return FactorRotationJob(
        gateway=toy["gateway"], panel=toy["panel"], driver_key=driver_key,
        strategy_name=ROTATION_STRATEGY, snapshot_id=toy["snapshot_id"],
        engine_version=ENGINE_VERSION, param_set_prefix=f"測試r-{driver_key}-",
        period_start=PERIOD[0], period_end=PERIOD[1],
        warmup_bars=WARMUP_BARS, warmup_weights=WARMUP_WEIGHTS, cadence=cadence,
        strategy_version_no=toy["rotation"].version_no, market_ticker=MARKET, costs=costs,
    )


def _mix_job(toy, costs: TradingCosts | None, cadence: str = "quarterly"):
    return FactorMixJob(
        gateway=toy["gateway"], panel=toy["panel"], sleeves=FACTOR_ETF_SLEEVES,
        strategy_name=MIX_STRATEGY, snapshot_id=toy["snapshot_id"],
        engine_version=ENGINE_VERSION, param_set_prefix="測試w-",
        period_start=PERIOD[0], period_end=PERIOD[1], cadence=cadence,
        strategy_version_no=toy["mix"].version_no, costs=costs,
    )


def _sweep(toy, grid, job):
    return run_sweep(
        runs=toy["runs"], grid=grid, job=job, risk_free_rate=RISK_FREE,
        benchmarks=(MARKET,), snapshot_root=toy["snapshot_root"],
    )


# ----------------------------------------------------------------------
# 驗收條件 2:以示例成本重跑固定權重對照格與驅動器最優格,
#             交出成本前後的年化(超額)與換手並列表
# ----------------------------------------------------------------------


def test_rerunning_with_the_example_costs_yields_a_before_and_after_table(toy):
    objective = f"annual_excess:{MARKET}"
    driver_point = SweepPoint(values=(("lookback_months", 3), ("fallback", "cash")))
    driver_grid = ExplicitGrid([driver_point])
    mix_point = reference_point(FACTOR_ETF_SLEEVES, WARMUP_WEIGHTS)
    mix_grid = ExplicitGrid([mix_point])

    before_driver = _sweep(toy, driver_grid, _rotation_job(toy, "relative_strength", None))
    after_driver = _sweep(
        toy, driver_grid, _rotation_job(toy, "relative_strength", EXAMPLE_COSTS)
    )
    before_mix = _sweep(toy, mix_grid, _mix_job(toy, None))
    after_mix = _sweep(toy, mix_grid, _mix_job(toy, EXAMPLE_COSTS))

    # 成本入了參數集,所以成本前後是兩個**不同**的運行編號,不是同一個運行改了個數
    assert before_driver.cells[0].run_id != after_driver.cells[0].run_id
    assert before_mix.cells[0].run_id != after_mix.cells[0].run_id
    assert cost_values(None) == {} and cost_slug(None) == ""
    assert set(cost_values(EXAMPLE_COSTS)) == {"fee_model", "fee_rate", "slippage"}

    # 零成本那一格再掃一次,撞回**同一個**運行編號:舊運行逐位不變
    again = _sweep(toy, driver_grid, _rotation_job(toy, "relative_strength", None))
    assert again.cells[0].run_id == before_driver.cells[0].run_id
    assert again.reused == 1

    table = cost_comparison(
        [
            CostPair(
                label="相對強弱對 SPY·最優格", kind="驅動器",
                before=before_driver.cells[0], after=after_driver.cells[0],
            ),
            CostPair(
                label="固定權重·各佔 25%", kind="固定權重",
                before=before_mix.cells[0], after=after_mix.cells[0],
            ),
        ],
        objective=objective,
        costs=EXAMPLE_COSTS,
    )

    assert list(table["名稱"]) == ["相對強弱對 SPY·最優格", "固定權重·各佔 25%"]
    for column in (
        f"成本前{objective}", f"成本後{objective}", "成本代價",
        "成本前換手", "成本後換手", "成本前run_id", "成本後run_id",
    ):
        assert column in table.columns
    # 成本只會令成績變差,不會令它變好
    assert (table["成本代價"] < 0).all()
    # 換手是輪動與固定權重的分別所在:輪動換得多,成本自然吃得深
    rotation_row = table.iloc[0]
    mix_row = table.iloc[1]
    assert rotation_row["成本前換手"] > mix_row["成本前換手"]
    assert abs(rotation_row["成本代價"]) > abs(mix_row["成本代價"])


# ----------------------------------------------------------------------
# 驗收條件 3:加密重掃(不少於 60 格)連成本,出得到穩健平原判讀與分段重看
# ----------------------------------------------------------------------


def test_a_denser_grid_with_costs_supports_a_plateau_verdict_and_segment_reading(toy):
    grid = rotation_grid(
        "relative_strength",
        values={"lookback_months": list(range(1, 16)), "fallback": ["cash", "equal"]},
        cadences=["monthly", "quarterly"],
    )
    # 15 個月 × 2 種退路 × 2 個節奏 = 60 格,達到票上「各不少於 60 格」
    assert len(grid) == 60

    # 回望期逐月之後,「一步之遙」由三個月變成一個月——鄰域的定義本身變密了,
    # 平原才有機會浮出來(這亦即是說:新舊兩次掃描的裁決不可以直接比較)。
    middle = SweepPoint(
        values=(("lookback_months", 6), ("fallback", "cash"), ("cadence", "monthly"))
    )
    neighbours = grid.neighbours(middle)
    lookbacks = {int(point.get("lookback_months")) for point in neighbours}
    assert lookbacks == {5, 6, 7}

    # 判讀在加密格上行得通:鋪一片高地出來,它就要判平原
    plateau_cells = {
        (months, "cash", "monthly") for months in (5, 6, 7)
    } | {(months, "equal", "monthly") for months in (5, 6, 7)}
    scores = []
    for point in grid.points():
        key = (
            int(point.get("lookback_months")),
            str(point.get("fallback")),
            str(point.get("cadence")),
        )
        scores.append(CellScore(point=point, value=0.05 if key in plateau_cells else 0.01,
                                trades=40))
    judgement = judge(
        scores, grid, objective="annual_excess:SPY", min_trades=30,
        lonely_peak_margin=0.005, plateau_quantile=0.90,
    )
    assert judgement.cell_for(middle).verdict == PLATEAU
    assert len(judgement.plateaus) >= 1

    # 連成本真跑一格,分段重看(重看不重跑)得回三段各自的年化
    point = SweepPoint(values=(("lookback_months", 6), ("fallback", "cash")))
    sweep = _sweep(toy, ExplicitGrid([point]), _rotation_job(toy, "relative_strength",
                                                            EXAMPLE_COSTS))
    cell = sweep.cells[0]
    segments = [
        ("前段", PERIOD[0], "2020-12-31"),
        ("中段", "2021-01-01", "2021-06-30"),
        ("後段", "2021-07-01", PERIOD[1]),
    ]
    annuals = [
        run_metrics(
            toy["runs"], cell.run_id, risk_free_rate=RISK_FREE, benchmarks=(),
            start=start, end=end, snapshot_root=toy["snapshot_root"],
        ).annual_return
        for _, start, end in segments
    ]
    assert len(annuals) == 3 and all(np.isfinite(value) for value in annuals)


# ----------------------------------------------------------------------
# 驗收條件 4:報告指得回所用快照、期間、成本參數與各運行編號
# ----------------------------------------------------------------------


def test_the_report_points_back_to_snapshot_period_costs_and_run_ids(toy, tmp_path):
    point = SweepPoint(values=(("lookback_months", 3), ("fallback", "cash")))
    grid = ExplicitGrid([point])
    sweep = _sweep(toy, grid, _rotation_job(toy, "relative_strength", EXAMPLE_COSTS))
    objective = f"annual_excess:{MARKET}"
    judgement = judge(
        sweep.scores(objective), grid, objective=objective,
        min_trades=1, lonely_peak_margin=0.005, plateau_quantile=0.90,
    )
    note = provenance_note(
        snapshot_id=toy["snapshot_id"], period=PERIOD, costs=EXAMPLE_COSTS,
        run_ids=sweep.run_ids(),
    )
    path = write_report(
        sweep, judgement, tmp_path / "報告", title="KARST-043 測試報告", notes=note
    )
    text = path.read_text(encoding="utf-8")

    assert toy["snapshot_id"] in text              # 哪一份數據
    assert PERIOD[0] in text and PERIOD[1] in text  # 哪一段日子
    assert "per_share" in text and "0.005" in text  # 哪一組成本
    assert "5 個基點" in text                        # 滑點寫成人話
    for run_id in sweep.run_ids():                 # 哪幾次運行
        assert run_id in text

    # 零成本那一份報告一樣要講清楚它是零成本,不可以留白讓人以為「未計」
    assert "零(手續費與滑點皆為 0)" in provenance_note(
        snapshot_id=toy["snapshot_id"], period=PERIOD, costs=TradingCosts.zero()
    )


# ----------------------------------------------------------------------
# KARST-046 驗收條件 2:掃描層那道多餘的「先查」刪走,行為一個字不變
# ----------------------------------------------------------------------


def test_the_sweep_registers_straight_through_the_gateway(toy):
    """掃描不再自己先查一句——重覆登記由唯一入口沿用舊版,一列都不會多寫。"""
    store = toy["store"]

    # 基座再叫一次(fixture 已經叫過一次):策略版本與參數集版本都不動
    again = ensure_factor_rotation_setup(
        toy["gateway"], strategy_name=MIX_STRATEGY, snapshot_id=toy["snapshot_id"],
        setup_param_set_name="測試基座-混合-043", setup_weights=WARMUP_WEIGHTS,
        cadence="quarterly", description="KARST-043 對照用的固定權重策略",
    )
    assert again.version_no == toy["mix"].version_no
    assert store.get_param_set(MIX_STRATEGY, "測試基座-混合-043").version_no == 1

    # 掃描格:同一格排兩次,「真正寫入的參數集數目」照樣數得準
    job = _mix_job(toy, None)
    point = reference_point(FACTOR_ETF_SLEEVES, WARMUP_WEIGHTS)

    first = job.plan(point)
    assert job.param_sets_written == 1
    assert first.param_set_version_no == 1

    second = job.plan(point)
    assert second.param_set_name == first.param_set_name
    assert second.param_set_version_no == first.param_set_version_no
    assert job.param_sets_written == 1  # 第二次是沿用,沒有寫

    # 換一個跑法由零重新數:查到的全是現成的,一次都沒有寫入
    fresh = _mix_job(toy, None)
    assert fresh.plan(point).param_set_version_no == 1
    assert fresh.param_sets_written == 0
