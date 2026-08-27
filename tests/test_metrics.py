"""KARST-030 驗收:基準與指標兩層計算。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。

測試用的數據是砌出來的:基準日線走一條固定的複利線(算得出的答案可以逐個
對),逐筆交易砌成兩贏兩輸的四個來回(勝率、盈虧比、平均持倉日數三個數因此
有唯一答案)。逐日淨值沿用 KARST-026 的合成序列。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from karst import DefinitionStore, FormulaProcedure, NotFound
from karst.data.pipeline import UNIVERSE_COLUMNS
from karst.data.calendar import BAR_ACTUAL, PANEL_COLUMNS
from karst.data.snapshots import read_price_panel, write_snapshot_dir
from karst.metrics import (
    benchmark_curve,
    facade_metrics,
    run_metrics,
    trade_stats,
)
from karst.runs import RunStore, synthetic_simulation
from karst.runs.synthetic import SyntheticSimulation
from karst.runs.window import TRADING_DAYS_PER_YEAR

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

CALENDAR = tuple(str(day.date()) for day in pd.bdate_range("2020-01-02", "2023-12-29"))
PERIOD = (CALENDAR[0], CALENDAR[-1])


@pytest.fixture()
def store(tmp_path):
    with DefinitionStore.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


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
    rows = []
    for ticker, step in BENCH_DAILY.items():
        entity_id = universe[ticker]
        for index, day in enumerate(CALENDAR):
            close = 100.0 * step**index
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
def test_facade_follows_the_active_setup(runs, store, strategy, universe, snapshot_id):
    active = _record(runs, universe, snapshot_id, param_set_name=ACTIVE_SET, seed=7)
    other = _record(runs, universe, snapshot_id, param_set_name=OTHER_SET, seed=21)
    assert active.run_id != other.run_id

    # 未指定現役設定就沒有門面數字——不會隨手挑一次頂上
    with pytest.raises(NotFound):
        facade_metrics(runs, STRATEGY, risk_free_rate=RISK_FREE)

    store.set_active_setup(STRATEGY, ACTIVE_SET)
    first = facade_metrics(runs, STRATEGY, risk_free_rate=RISK_FREE)
    assert first.run_id == active.run_id
    assert first.is_active_setup is True
    assert first.param_set_name == ACTIVE_SET

    # 換現役設定:門面八個數隨之更換
    store.set_active_setup(STRATEGY, OTHER_SET)
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
    history = store.active_setup_history(STRATEGY)
    assert [s.param_set_name for s in history] == [ACTIVE_SET, OTHER_SET]


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
