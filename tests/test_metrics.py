"""KARST-030 驗收:基準與指標兩層計算。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。

測試用的數據是砌出來的:基準日線走一條固定的複利線(算得出的答案可以逐個
對),逐筆交易砌成兩贏兩輸的四個來回(勝率、盈虧比、平均持倉日數三個數因此
有唯一答案)。逐日淨值沿用 KARST-026 的合成序列。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from karst import ContractViolation, DefinitionStore, FormulaProcedure, NotFound
from karst.gateway import Gateway
from karst.data.calendar import BAR_ACTUAL, PANEL_COLUMNS
from karst.data.freeze import UNIVERSE_COLUMNS, write_snapshot_dir
from karst.data.snapshots import read_price_panel
from karst.metrics import (
    benchmark_curve,
    facade_metrics,
    opening_inventory,
    round_trips,
    run_metrics,
    trade_stats,
    valuation_day,
)
from karst.runs import RunStore, synthetic_simulation
from karst.store import FORMAL_RUN
from karst.runs.synthetic import SyntheticSimulation
from karst.runs.window import BASE, TRADING_DAYS_PER_YEAR

MOMENTUM = "動量·12-1 月"
MOMENTUM_PROCEDURE = FormulaProcedure(
    formula="close[-21] / close[-252] - 1",
    input_data_version="2026-08-27-a1b2c3d4e5f6",
)
STRATEGY = "趨勢波段"
ACTIVE_SET = "現役"
OTHER_SET = "更長窗"
ENGINE = ("vectorbt-adapter", "0.1.0")
RISK_FREE = 0.04

# 基準逐日複利:QQQ 行得急,SPY 行得慢。年化答案因此有閉式解。
BENCH_DAILY = {"QQQ": 1.0004, "SPY": 1.0002}

# 兩間公司的日線(起步價、逐日複利)。期初存貨要按估值日收市價入帳,
# 所以持倉那兩隻也要有價——否則估不到成本(KARST-039)。起步價一高一低,
# 是要令承接回來那兩注一贏一蝕,八項才全部有數(盈虧比要有蝕過才算得出)。
COMPANY_DAILY = {"Apple Inc.": (150.0, 1.0003), "Microsoft Corp.": (80.0, 1.0001)}

CALENDAR = tuple(str(day.date()) for day in pd.bdate_range("2020-01-02", "2023-12-29"))
PERIOD = (CALENDAR[0], CALENDAR[-1])


@pytest.fixture()
def gateway(tmp_path, monkeypatch):
    """唯一入口。指定現役設定要經它,寫入者簽章才蓋得到(D-020 第 4 條)。"""
    monkeypatch.setenv("KARST_WRITER", "KARST-038-test")
    with Gateway.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


@pytest.fixture()
def store(gateway) -> DefinitionStore:
    return gateway.store


@pytest.fixture()
def universe(store):
    """兩隻基準 ETF + 兩間公司。基準是對照尺,不是策略持倉。"""
    ids = {
        ticker: store.register_entity(
            kind="etf", display_name=f"{ticker} ETF", local_code=ticker
        )
        for ticker in BENCH_DAILY
    }
    for name, cik in (("Apple Inc.", "320193"), ("Microsoft Corp.", "789019")):
        ids[name] = store.register_entity(kind="company", display_name=name, cik=cik)
    for ticker in BENCH_DAILY:
        store.register_ticker(ids[ticker], ticker, valid_from=CALENDAR[0])
    return ids


@pytest.fixture()
def snapshot_id(store, universe, tmp_path):
    """砌一個真快照目錄:兩隻基準的日線走固定複利線,兩間公司陪跑。"""
    lines = {universe[ticker]: (100.0, step) for ticker, step in BENCH_DAILY.items()}
    lines.update({universe[name]: line for name, line in COMPANY_DAILY.items()})

    rows = []
    for entity_id, (first_close, step) in lines.items():
        for index, day in enumerate(CALENDAR):
            close = first_close * step**index
            rows.append(
                {
                    "date": day,
                    "entity_id": entity_id,
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "volume": 1_000_000.0,
                    "bar_status": BAR_ACTUAL,
                }
            )
    prices = pd.DataFrame(rows, columns=list(PANEL_COLUMNS))
    universe_frame = pd.DataFrame(
        [
            {
                "ticker": ticker,
                "entity_id": universe[ticker],
                "entity_kind": "etf",
                "anchor": ticker,
                "anchor_source": "local_code",
                "display_name": f"{ticker} ETF",
            }
            for ticker in BENCH_DAILY
        ],
        columns=list(UNIVERSE_COLUMNS),
    )

    root = tmp_path / "snapshots"
    digest = "0123456789abcdef"
    snapshot = DefinitionStore.snapshot_id_for("2026-08-27", digest)
    write_snapshot_dir(
        root,
        snapshot,
        prices=prices,
        calendar=CALENDAR,
        universe=universe_frame,
        manifest={"core": {"source": "test"}},
        readme="測試用快照\n",
    )
    store.register_snapshot(
        source="test",
        taken_on="2026-08-27",
        content_hash=digest,
        path=str(root / snapshot),
        universe=sorted(BENCH_DAILY),
    )
    return snapshot


@pytest.fixture()
def strategy(store, universe):
    store.register_factor(MOMENTUM, scale_kind="cardinal", procedure=MOMENTUM_PROCEDURE)
    version = store.register_strategy(
        STRATEGY, strategy_type="technical", factor_refs=[MOMENTUM]
    )
    for set_name, window in ((ACTIVE_SET, "50"), (OTHER_SET, "120")):
        store.register_param_set(
            STRATEGY,
            param_set_name=set_name,
            rebalance_cadence="monthly",
            values={"breakout_window": window, "direction": "high"},
        )
    return version


@pytest.fixture()
def runs(store, tmp_path):
    return RunStore(store, root=tmp_path / "runs")


# 砌好的四個來回:兩贏兩輸,答案唯一。
# (實體、買入日序、買價、賣出日序、賣價、股數)
TRADE_PLAN = (
    (0, 10, 100.0, 60, 120.0, 100.0),    # 贏 2,000,持 50 個交易日
    (0, 100, 120.0, 130, 110.0, 100.0),  # 蝕 1,000,持 30 個交易日
    (1, 20, 200.0, 200, 260.0, 50.0),    # 贏 3,000,持 180 個交易日
    (1, 300, 260.0, 360, 230.0, 50.0),   # 蝕 1,500,持 60 個交易日
)
EXPECTED_WIN_RATE = 0.5
EXPECTED_PL_RATIO = 2.0  # 平均賺 2,500 ÷ 平均蝕 1,250
EXPECTED_HOLDING_DAYS = 80.0  # (50 + 30 + 180 + 60) / 4
EXPECTED_TRADED_VALUE = 92_500.0

# ---- KARST-039:由 TRADE_PLAN 中間切一刀的檢視視窗 ----
# 這一段之內只有兩張單,兩張都是賣出:第 130 格賣 Apple、第 200 格賣 Microsoft。
# 兩注的買入(第 100、第 20 格)都落在視窗之前,所以非要承接期初存貨不可。
CARRY_START = 110
CARRY_END = 250
CARRY_WINDOW = (CALENDAR[CARRY_START], CALENDAR[CARRY_END])
CARRY_VALUED_ON = CALENDAR[CARRY_START - 1]  # 估值日:視窗之前最後一個交易日
CARRY_EXITS = (
    # (公司、賣出日序、賣價、股數)
    ("Apple Inc.", 130, 110.0, 100.0),
    ("Microsoft Corp.", 200, 260.0, 50.0),
)
# 合成序列每日每隻等額持倉:初始本金 ÷ 實體數 ÷ 假股價 100
CARRY_SHARES_HELD = 100_000.0 / 2.0 / 100.0


def _company_close(name: str, index: int) -> float:
    """那間公司在日曆第 ``index`` 格的收市價。"""
    first_close, step = COMPANY_DAILY[name]
    return first_close * step**index


def _carry_profit(name: str, exit_price: float, shares: float) -> float:
    """承接回來那一注的賺蝕:成本是估值日收市價,費用兩邊都是 0。"""
    return shares * (exit_price - _company_close(name, CARRY_START - 1))


def _window_pieces(runs, run_id, start, end):
    """視窗那一段的交易日曆與成交——即 ``run_metrics`` 餵給配對層那兩份。"""
    equity = runs.equity_curve(run_id)
    window_equity = equity.loc[
        (equity.index >= pd.Timestamp(start)) & (equity.index <= pd.Timestamp(end))
    ]
    orders = runs.orders(run_id)
    in_window = orders.loc[
        (orders["trade_date"].astype(str) >= start)
        & (orders["trade_date"].astype(str) <= end)
    ]
    return equity, window_equity, in_window


def _orders(entity_ids):
    rows = []
    for slot, entry_index, entry_price, exit_index, exit_price, shares in TRADE_PLAN:
        entity_id = entity_ids[slot]
        rows.append(
            {
                "trade_date": CALENDAR[entry_index],
                "entity_id": entity_id,
                "side": "buy",
                "shares": shares,
                "price": entry_price,
                "fees": 0.0,
            }
        )
        rows.append(
            {
                "trade_date": CALENDAR[exit_index],
                "entity_id": entity_id,
                "side": "sell",
                "shares": shares,
                "price": exit_price,
                "fees": 0.0,
            }
        )
    return pd.DataFrame(
        rows, columns=["trade_date", "entity_id", "side", "shares", "price", "fees"]
    )


def _record(runs, universe, snapshot_id, *, param_set_name=ACTIVE_SET, seed=7):
    company_ids = (universe["Apple Inc."], universe["Microsoft Corp."])
    base = synthetic_simulation(
        start=PERIOD[0], end=PERIOD[1], entity_ids=company_ids, seed=seed
    )
    simulation = SyntheticSimulation(
        equity_curve=base.equity_curve,
        holdings=base.holdings,
        orders=_orders(company_ids),
    )
    return runs.record_simulation(
        simulation,
        strategy_name=STRATEGY,
        param_set_name=param_set_name,
        snapshot_id=snapshot_id,
        engine_name=ENGINE[0],
        engine_version=ENGINE[1],
        origin=FORMAL_RUN,
    )


# 驗收條件 1:由一次運行算得出策略卡四項與運行詳情四項,八個數字齊
#            (D-020 第 8 條、規格 8.3)
def test_eight_metrics_come_out_of_one_run(runs, store, strategy, universe, snapshot_id):
    record = _record(runs, universe, snapshot_id)
    metrics = run_metrics(runs, record.run_id, risk_free_rate=RISK_FREE)

    equity = runs.equity_curve(record.run_id)

    # ---- 策略卡四項 ----
    assert metrics.total_return == pytest.approx(
        float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    )
    assert metrics.annual_return == pytest.approx(
        (1.0 + metrics.total_return)
        ** (TRADING_DAYS_PER_YEAR / (metrics.trading_days - 1))
        - 1.0
    )
    assert metrics.max_drawdown < 0.0
    assert metrics.win_rate == pytest.approx(EXPECTED_WIN_RATE)
    assert metrics.profit_loss_ratio == pytest.approx(EXPECTED_PL_RATIO)

    # ---- 運行詳情再加四項 ----
    assert set(metrics.annual_excess) == {"QQQ", "SPY"}
    assert metrics.sortino is not None
    assert metrics.average_holding_days == pytest.approx(EXPECTED_HOLDING_DAYS)
    assert metrics.turnover == pytest.approx(
        EXPECTED_TRADED_VALUE
        / 2.0
        / float(equity.mean())
        / ((len(equity) - 1) / TRADING_DAYS_PER_YEAR)
    )

    # 勝率盈虧比那一項的原料:四個已平倉的來回,兩贏兩輸
    stats = trade_stats(runs.orders(record.run_id), equity.index)
    assert (stats.closed_trades, stats.winning_trades, stats.losing_trades) == (4, 2, 2)
    assert metrics.closed_trades == 4


# 驗收條件 2:對 QQQ 與 SPY 各出一個超額數,基準走買入持有、不經策略路徑
#            (規格 7.5、8.4、詞彙表 benchmark)
def test_excess_against_qqq_and_spy_from_buy_and_hold(
    runs, store, strategy, universe, snapshot_id
):
    record = _record(runs, universe, snapshot_id)
    metrics = run_metrics(runs, record.run_id, risk_free_rate=RISK_FREE)

    for ticker, step in BENCH_DAILY.items():
        curve = benchmark_curve(store, snapshot_id, ticker, *PERIOD)
        # 買入持有 = 由快照的收市價直接算,一條策略路徑都不行
        closes = read_price_panel(store, snapshot_id, field="close")[universe[ticker]]
        assert curve.stats.total_return == pytest.approx(
            float(closes.iloc[-1] / closes.iloc[0] - 1.0)
        )
        assert curve.stats.total_return == pytest.approx(step ** (len(CALENDAR) - 1) - 1.0)
        assert curve.stats.annual_return == pytest.approx(step**TRADING_DAYS_PER_YEAR - 1.0)
        assert curve.equity.iloc[0] == pytest.approx(100.0)

        # 超額 = 策略年化減基準年化(原型 run.html:「策略減 QQQ」)
        assert metrics.excess_against(ticker) == pytest.approx(
            metrics.annual_return - curve.stats.annual_return
        )
        assert metrics.benchmarks[ticker].total_return == pytest.approx(
            curve.stats.total_return
        )

    # 兩條基準各自一個數,不是同一個
    assert metrics.annual_excess["QQQ"] != metrics.annual_excess["SPY"]
    # QQQ 行得急,對它的超額一定細過對 SPY 的
    assert metrics.annual_excess["QQQ"] < metrics.annual_excess["SPY"]


# 驗收條件 3:門面數字取的是現役設定那次運行;換一個現役設定,門面八個數隨之更換
#            (規格 7.5)
def test_facade_follows_the_active_setup(runs, gateway, strategy, universe, snapshot_id):
    active = _record(runs, universe, snapshot_id, param_set_name=ACTIVE_SET, seed=7)
    other = _record(runs, universe, snapshot_id, param_set_name=OTHER_SET, seed=21)
    assert active.run_id != other.run_id

    # 未指定現役設定就沒有門面數字——不會隨手挑一次頂上
    with pytest.raises(NotFound):
        facade_metrics(runs, STRATEGY, risk_free_rate=RISK_FREE)

    gateway.designate_active_setup(STRATEGY, param_set_name=ACTIVE_SET)
    first = facade_metrics(runs, STRATEGY, risk_free_rate=RISK_FREE)
    assert first.run_id == active.run_id
    assert first.is_active_setup is True
    assert first.param_set_name == ACTIVE_SET

    # 換現役設定:門面八個數隨之更換
    gateway.designate_active_setup(STRATEGY, param_set_name=OTHER_SET)
    second = facade_metrics(runs, STRATEGY, risk_free_rate=RISK_FREE)
    assert second.run_id == other.run_id
    assert second.param_set_name == OTHER_SET
    assert second.total_return != first.total_return
    assert second.annual_return != first.annual_return
    assert second.max_drawdown != first.max_drawdown
    assert second.annual_excess["QQQ"] != first.annual_excess["QQQ"]
    assert second.annual_excess["SPY"] != first.annual_excess["SPY"]
    assert second.sortino != first.sortino
    assert second.turnover != first.turnover

    # 舊的那次運行不再是門面,但它本身一個字沒變
    assert run_metrics(runs, active.run_id, risk_free_rate=RISK_FREE).is_active_setup is False
    assert run_metrics(runs, active.run_id, risk_free_rate=RISK_FREE).total_return == (
        pytest.approx(first.total_return)
    )

    # 換過什麼、幾時換,兩筆指定都在
    history = gateway.store.active_setup_history(STRATEGY)
    assert [s.param_set_name for s in history] == [ACTIVE_SET, OTHER_SET]

    # 經入口指定即有寫入者簽章:兩筆指定核對都清白,一列都沒有繞過(KARST-038)。
    # 這個測試的其他定義是玩具數據,由庫層 API 直接砌,故此只看現役設定那一張表。
    assert [f for f in gateway.verify() if f.table == "active_setup"] == []


# 驗收條件 4:八項由已保存的逐日序列算出,計算過程不觸發引擎重跑(規格 8.5)
def test_metrics_read_saved_series_and_never_rerun_the_engine(
    runs, store, strategy, universe, snapshot_id
):
    record = _record(runs, universe, snapshot_id)
    before = runs.equity_curve(record.run_id)

    whole = run_metrics(runs, record.run_id, risk_free_rate=RISK_FREE)
    middle = str(before.index[len(before) // 2].date())
    window = run_metrics(runs, record.run_id, risk_free_rate=RISK_FREE, start=middle)

    # 檢視視窗:同一次運行另揀一段重算,八項全部按那一段出
    assert window.start == middle
    assert window.trading_days < whole.trading_days
    assert window.total_return != whole.total_return
    assert window.annual_excess["QQQ"] != whole.annual_excess["QQQ"]
    assert window.benchmarks["QQQ"].start == middle

    # 重看不重跑:三條序列與落痕那一刻一字不差
    assert runs.verify_run(record.run_id) == ()
    pd.testing.assert_series_equal(runs.equity_curve(record.run_id), before)
    assert store.get_run(record.run_id).artifacts["equity"].content_hash == (
        record.artifacts["equity"].content_hash
    )

    # 指標這一層根本沒有引擎這道門:全個 karst/metrics/ 一個 engine 都不 import
    metrics_dir = Path(__file__).resolve().parents[1] / "karst" / "metrics"
    for source in sorted(metrics_dir.glob("*.py")):
        text = source.read_text(encoding="utf-8")
        assert "engine" not in text, f"{source.name} 提到了引擎"


# ======================================================================
# KARST-039:檢視視窗承接視窗前已開的倉位
# ======================================================================


# KARST-039 驗收條件 1:任一起訖日期(含視窗前已有持倉)算得出八項指標,不拋錯
def test_any_window_computes_eight_metrics_with_positions_carried_in(
    runs, store, strategy, universe, snapshot_id
):
    record = _record(runs, universe, snapshot_id)
    start, end = CARRY_WINDOW
    _, window_equity, in_window = _window_pieces(runs, record.run_id, start, end)

    # 未承接期初存貨的話,這一段只見得到賣出那一邊,配不出來回(KARST-032 撞到的)
    assert list(in_window["side"]) == ["sell", "sell"]
    with pytest.raises(ContractViolation):
        trade_stats(in_window, window_equity.index)

    metrics = run_metrics(
        runs, record.run_id, risk_free_rate=RISK_FREE, start=start, end=end
    )
    assert metrics.opening_lots == 2  # 兩間公司各承接一注

    # 八項齊,一項都不是「算不出」
    assert metrics.total_return == pytest.approx(
        float(window_equity.iloc[-1] / window_equity.iloc[0] - 1.0)
    )
    assert metrics.annual_return == pytest.approx(
        (1.0 + metrics.total_return)
        ** (TRADING_DAYS_PER_YEAR / (metrics.trading_days - 1))
        - 1.0
    )
    assert metrics.max_drawdown < 0.0
    assert metrics.win_rate == pytest.approx(0.5)  # 承接回來兩注:一贏一蝕
    won = _carry_profit("Microsoft Corp.", 260.0, 50.0)
    lost = -_carry_profit("Apple Inc.", 110.0, 100.0)
    assert won > 0.0 and lost > 0.0
    assert metrics.profit_loss_ratio == pytest.approx(won / lost)
    assert set(metrics.annual_excess) == {"QQQ", "SPY"}
    assert metrics.sortino is not None
    assert metrics.average_holding_days == pytest.approx((20.0 + 90.0) / 2.0)
    assert metrics.turnover == pytest.approx(
        (100.0 * 110.0 + 50.0 * 260.0)
        / 2.0
        / float(window_equity.mean())
        / ((len(window_equity) - 1) / TRADING_DAYS_PER_YEAR)
    )
    assert metrics.closed_trades == 2

    # 不是只有這一段行得通:掃一批起訖日期,無一拋錯
    for first in range(0, len(CALENDAR) - 40, 91):
        spot = run_metrics(
            runs, record.run_id, risk_free_rate=RISK_FREE, start=CALENDAR[first]
        )
        assert spot.trading_days >= 2


# KARST-039 驗收條件 2:全期視窗的八項數字與現行結果逐位相同
def test_the_whole_period_numbers_do_not_move(
    runs, store, strategy, universe, snapshot_id
):
    record = _record(runs, universe, snapshot_id)
    equity = runs.equity_curve(record.run_id)
    whole = run_metrics(runs, record.run_id, risk_free_rate=RISK_FREE)

    # 全期沒有「之前」,所以承接不到東西——走的就是未有這一層之前那條路
    assert valuation_day(equity, whole.start) is None
    assert opening_inventory(runs, runs.get_run(record.run_id), equity, whole.start) == ()
    assert whole.opening_lots == 0

    # 八項仍然是 KARST-030 驗收那八個數,一個都沒有郁過
    assert whole.total_return == float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    assert whole.annual_return == pytest.approx(
        (1.0 + whole.total_return) ** (TRADING_DAYS_PER_YEAR / (whole.trading_days - 1))
        - 1.0
    )
    assert whole.max_drawdown < 0.0
    assert whole.win_rate == EXPECTED_WIN_RATE
    assert whole.profit_loss_ratio == pytest.approx(EXPECTED_PL_RATIO)
    assert whole.average_holding_days == EXPECTED_HOLDING_DAYS
    assert whole.turnover == pytest.approx(
        EXPECTED_TRADED_VALUE
        / 2.0
        / float(equity.mean())
        / ((len(equity) - 1) / TRADING_DAYS_PER_YEAR)
    )
    assert whole.closed_trades == 4

    # 明明白白給足全期的起訖,答案與留空逐位相同(同一條路,不是同一個近似值)
    explicit = run_metrics(
        runs,
        record.run_id,
        risk_free_rate=RISK_FREE,
        start=CALENDAR[0],
        end=CALENDAR[-1],
    )
    assert explicit.opening_lots == 0
    for field in (
        "total_return",
        "annual_return",
        "max_drawdown",
        "win_rate",
        "profit_loss_ratio",
        "sortino",
        "average_holding_days",
        "turnover",
        "closed_trades",
        "annual_excess",
    ):
        assert getattr(explicit, field) == getattr(whole, field), field

    # 配對層那道門一樣:不餵期初存貨,與未有這個參數之前一模一樣
    assert trade_stats(runs.orders(record.run_id), equity.index, opening=()) == (
        trade_stats(runs.orders(record.run_id), equity.index)
    )


# KARST-039 驗收條件 3:期初存貨的處置寫明,與 window_stats 的基準重設一致
def test_opening_inventory_is_valued_the_day_before_the_rebase_day(
    runs, store, strategy, universe, snapshot_id
):
    record = _record(runs, universe, snapshot_id)
    start, end = CARRY_WINDOW
    equity, window_equity, in_window = _window_pieces(runs, record.run_id, start, end)
    stats = runs.window_stats(record.run_id, start, end)

    # window_stats 把淨值由視窗第一日重設為 100;期初存貨就在它前一格估值,兩者相鄰
    assert float(stats.equity.iloc[0]) == pytest.approx(BASE)
    assert stats.start == CALENDAR[CARRY_START]
    day = valuation_day(equity, stats.start)
    assert str(day.date()) == CARRY_VALUED_ON
    assert equity.index[equity.index.get_loc(day) + 1] == pd.Timestamp(stats.start)

    # 每一注:股數取估值日收工的持倉,成本取同一日的收市價(同一個快照)
    lots = opening_inventory(runs, runs.get_run(record.run_id), equity, stats.start)
    held = runs.holdings_on(record.run_id, CARRY_VALUED_ON)
    closes = read_price_panel(store, snapshot_id, field="close")
    assert {lot.entity_id for lot in lots} == set(held)
    for lot in lots:
        assert lot.as_of == CARRY_VALUED_ON
        assert lot.shares == pytest.approx(CARRY_SHARES_HELD)
        assert lot.shares == pytest.approx(held[lot.entity_id])
        assert lot.price == pytest.approx(
            float(closes.loc[pd.Timestamp(CARRY_VALUED_ON), lot.entity_id])
        )

    # 承接回來那兩注:成本是估值日收市價、費用只有賣出那一邊、
    # 持倉日數由視窗第一日起數(視窗之前揸過幾耐是上一段的事)
    trips = round_trips(in_window, window_equity.index, opening=lots)
    assert len(trips) == 2
    by_entity = {trip.entity_id: trip for trip in trips}
    for name, exit_index, exit_price, shares in CARRY_EXITS:
        trip = by_entity[universe[name]]
        assert trip.entry_date == CARRY_VALUED_ON
        assert trip.entry_price == pytest.approx(
            _company_close(name, CARRY_START - 1)
        )
        assert trip.exit_date == CALENDAR[exit_index]
        assert trip.shares == pytest.approx(shares)
        assert trip.fees == 0.0
        assert trip.holding_days == exit_index - CARRY_START
        assert trip.profit == pytest.approx(_carry_profit(name, exit_price, shares))

    # 換手只數這一段真正落過的單:承接回來那批貨不當成一次買入
    carried = trade_stats(in_window, window_equity.index, opening=lots)
    assert carried.traded_value == pytest.approx(100.0 * 110.0 + 50.0 * 260.0)
    # 賣剩的仍然揸住,不入來回類指標——它未有結果(未實現由逐日淨值那邊帶出)
    assert carried.open_positions == 2


# KARST-039 驗收條件 4:網頁殼用同一接口即可顯示檢視視窗的八項(本票不改網頁殼)
def test_the_same_call_serves_the_web_shell(
    runs, store, strategy, universe, snapshot_id
):
    record = _record(runs, universe, snapshot_id)
    start, end = CARRY_WINDOW

    # 網頁殼那條路:同一個 run_metrics,只是多給起訖,不另開接口
    metrics = run_metrics(
        runs,
        record.run_id,
        risk_free_rate=RISK_FREE,
        start=start,
        end=end,
        snapshot_root=None,
    )
    payload = {
        "runId": metrics.run_id,
        "start": metrics.start,
        "end": metrics.end,
        "tradingDays": metrics.trading_days,
        # ---- 策略卡四項 ----
        "cumulativeReturn": metrics.total_return,
        "annualReturn": metrics.annual_return,
        "maxDrawdown": metrics.max_drawdown,
        "winRate": metrics.win_rate,
        "profitLossRatio": metrics.profit_loss_ratio,
        # ---- 運行詳情再加四項 ----
        "annualExcess": metrics.annual_excess,
        "sortino": metrics.sortino,
        "averageHoldingDays": metrics.average_holding_days,
        "turnover": metrics.turnover,
    }
    # 送得出街:八項全部是原生數字,不用另外轉一手
    assert json.loads(json.dumps(payload)) == payload
    assert metrics.start == CALENDAR[CARRY_START]
    assert metrics.end == CALENDAR[CARRY_END]
    # 基準跟住同一段走,超額比得過
    assert metrics.benchmarks["QQQ"].start == metrics.start
    assert metrics.benchmarks["SPY"].end == metrics.end
    assert metrics.excess_against("QQQ") == pytest.approx(
        metrics.annual_return - metrics.benchmarks["QQQ"].annual_return
    )


# ----------------------------------------------------------------------
# KARST-045:來回配對的容差按持倉量比例算,不再用一個固定股數
# ----------------------------------------------------------------------

# 日度換倉、單一實體逾兩千筆成交的樣子:逐日細細注買入,最後一次過清倉。
# 每注 0.1 股是刻意揀的——0.1 在二進位存不準,兩千注逐注加落去與一次過乘出來
# 相差 7.1e-12 股,正是 KARST-043 撞到的那種殘差(實測 1.4e-12)。
CHURN_LOTS = 2_000
CHURN_LOT_SHARES = 0.1
CHURN_BUY_PRICE = 100.0
CHURN_SELL_PRICE = 150.0
CHURN_SELL_DAY = CHURN_LOTS // 2  # 每日兩注,所以買完那一日是第 1000 格


def _churn_orders(entity_id):
    """單一實體、逾兩千筆成交的逐筆交易表(買入兩千注,最後一次過賣清)。"""
    rows = [
        {
            "trade_date": CALENDAR[index // 2],
            "entity_id": entity_id,
            "side": "buy",
            "shares": CHURN_LOT_SHARES,
            "price": CHURN_BUY_PRICE,
            "fees": 0.0,
        }
        for index in range(CHURN_LOTS)
    ]
    rows.append(
        {
            "trade_date": CALENDAR[CHURN_SELL_DAY],
            "entity_id": entity_id,
            "side": "sell",
            # 賣出股數由總數一次過乘出來,買入卻是逐注加——兩條路的浮點尾數不同,
            # 這一格之差就是配對層要當成 0 的那件事。
            "shares": CHURN_LOTS * CHURN_LOT_SHARES,
            "price": CHURN_SELL_PRICE,
            "fees": 0.0,
        }
    )
    return pd.DataFrame(
        rows, columns=["trade_date", "entity_id", "side", "shares", "price", "fees"]
    )


def _record_churn(runs, universe, snapshot_id):
    company_ids = (universe["Apple Inc."], universe["Microsoft Corp."])
    base = synthetic_simulation(
        start=PERIOD[0], end=PERIOD[1], entity_ids=company_ids, seed=7
    )
    simulation = SyntheticSimulation(
        equity_curve=base.equity_curve,
        holdings=base.holdings,
        orders=_churn_orders(company_ids[0]),
    )
    return runs.record_simulation(
        simulation,
        strategy_name=STRATEGY,
        param_set_name=ACTIVE_SET,
        snapshot_id=snapshot_id,
        engine_name=ENGINE[0],
        engine_version=ENGINE[1],
        origin=FORMAL_RUN,
    )


# KARST-045 驗收條件 1:日度換倉的合成運行(單一實體逾兩千筆成交)算得出八項指標不拋錯
def test_thousands_of_fills_on_one_entity_still_compute_eight_metrics(
    runs, store, strategy, universe, snapshot_id
):
    # 先證這批數據真的踩得中那條線:殘差大過舊有的 1e-12 絕對容差,
    # 否則這個測試證不到任何事(舊碼一樣會過)。
    lots_total = 0.0
    for _ in range(CHURN_LOTS):
        lots_total += CHURN_LOT_SHARES
    residual = CHURN_LOTS * CHURN_LOT_SHARES - lots_total
    assert residual > 1e-12

    record = _record_churn(runs, universe, snapshot_id)
    orders = runs.orders(record.run_id)
    assert len(orders) > 2_000
    assert orders["entity_id"].nunique() == 1

    metrics = run_metrics(runs, record.run_id, risk_free_rate=RISK_FREE)

    # ---- 八項全部算得出,一項都沒有因為配對中斷而缺 ----
    assert metrics.total_return is not None
    assert metrics.annual_return is not None
    assert metrics.max_drawdown is not None
    assert metrics.win_rate == pytest.approx(1.0)  # 全部注都賺(買 100 賣 150)
    assert metrics.profit_loss_ratio is None  # 一注都未蝕過,盈虧比無得計
    assert set(metrics.annual_excess) == {"QQQ", "SPY"}
    assert metrics.sortino is not None
    assert metrics.average_holding_days is not None
    assert metrics.turnover > 0.0

    # 兩千注全部配得成來回,一注都不剩
    assert metrics.closed_trades == CHURN_LOTS
    stats = trade_stats(orders, runs.equity_curve(record.run_id).index)
    assert stats.open_positions == 0


# KARST-045 驗收條件 2:真正賣出多過持倉的情況仍拋錯,並講明實體與日期
def test_a_real_oversell_still_raises_and_names_the_entity_and_the_day(universe):
    entity_id = universe["Apple Inc."]
    oversell_day = CALENDAR[5]
    orders = pd.DataFrame(
        [
            {
                "trade_date": CALENDAR[1],
                "entity_id": entity_id,
                "side": "buy",
                "shares": 10.0,
                "price": 100.0,
                "fees": 0.0,
            },
            {
                # 手上得十股,賣一百股——差九十股,不是浮點尾數
                "trade_date": oversell_day,
                "entity_id": entity_id,
                "side": "sell",
                "shares": 100.0,
                "price": 150.0,
                "fees": 0.0,
            },
        ],
        columns=["trade_date", "entity_id", "side", "shares", "price", "fees"],
    )
    with pytest.raises(ContractViolation) as caught:
        trade_stats(orders, CALENDAR)
    message = str(caught.value)
    assert "手上沒有貨" in message
    assert str(entity_id) in message
    assert oversell_day in message


# KARST-045 驗收條件 3:既有運行的八項指標逐位不變
def test_the_new_tolerance_leaves_the_existing_numbers_untouched(
    runs, store, strategy, universe, snapshot_id
):
    record = _record(runs, universe, snapshot_id)
    equity = runs.equity_curve(record.run_id)
    stats = trade_stats(runs.orders(record.run_id), equity.index)

    # 四個來回、兩贏兩輸,連同三項來回類指標與成交金額,全部與換容差之前同一個數
    assert (stats.closed_trades, stats.winning_trades, stats.losing_trades) == (4, 2, 2)
    assert stats.open_positions == 0
    assert stats.win_rate == pytest.approx(EXPECTED_WIN_RATE)
    assert stats.profit_loss_ratio == pytest.approx(EXPECTED_PL_RATIO)
    assert stats.average_holding_days == pytest.approx(EXPECTED_HOLDING_DAYS)
    assert stats.traded_value == pytest.approx(EXPECTED_TRADED_VALUE)
