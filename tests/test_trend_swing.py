"""KARST-028 驗收:趨勢波段策略在真實日線上跑出第一次完整回測。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。

驗收條件 1 用**真實**行情(經 karst.data 現有管線抓一個小快照);離線即 skip 並
註明,做法沿用 tests/test_data_yfinance.py——不以合成數據冒充真實抓取,亦不讓
離線變成假綠燈。其餘三條走合成 K 線,不連網。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_trend_swing.py -q``
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from karst.data import (
    DataFetchFailed,
    UniverseMember,
    YFinanceSource,
    build_price_snapshot,
    read_universe,
)
from karst.engine import BarPanel, build_rule_signals
from karst.errors import ContractViolation
from karst.gateway.service import Gateway
from karst.metrics import run_metrics
from karst.risk import (
    RISK_RULES,
    RiskSettings,
    read_risk_settings,
    referenced_rule_keys,
    sweep_grid,
)
from karst.runs import RunStore
from karst.strategies.trend_swing import (
    BREAKOUT_FACTOR_NAME,
    CASE_COLUMNS,
    EXIT_REASONS,
    EXIT_STOP,
    EXIT_TARGET,
    EXIT_UNCLOSED,
    STRATEGY_PARAM_KEYS,
    SWEEP_COLUMNS,
    TREND_SWING_STRATEGY_TYPE,
    TrendSwingParams,
    build_bar_panel,
    case_stats,
    cases_frame,
    entry_cases,
    param_values,
    params_grid,
    read_setup,
    record_trend_swing_run,
    register_trend_swing,
    run_trend_swing,
    sweep_trend_swing,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "karst" / "strategies" / "trend_swing.py"

STRATEGY = "趨勢波段"
PARAM_SET = "示例-驗收"
ENGINE_VERSION = "0.1.0"
CADENCE = "daily"                 # 規則路徑逐根 K 線檢查訊號

# ---------------------------------------------------------------------------
# 示例取值。**示例參數,不是現役設定**——本檔一句 set_active_setup 都沒有。
# 九格策略參數與三格風控參數全部寫在這裡再交去參數集;策略碼裡一個取值都沒有。
# ---------------------------------------------------------------------------
SAMPLE_PARAMS = TrendSwingParams(
    breakout_lookback_days=40,
    swing_lookback_days=10,
    min_stop_fraction=0.01,
    max_stop_fraction=0.25,
    max_position_fraction=0.25,
    equity_basis="current_equity",
    initial_cash=1_000_000.0,
    fees=0.0,
    tie_break_seed=20260828,
)
SAMPLE_RISK = RiskSettings(
    per_trade_risk=0.06,          # 合成場刻意押大,好令熔斷真的落閘
    monthly_loss_cap=0.06,
    reward_risk_floor=1.0,
)

# 真實抓取那半:小宇宙、兩年窗口。窗口收在已收市的年度,重抓得回同一個快照。
REAL_UNIVERSE = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("QQQ", "etf", "Invesco QQQ Trust, Series 1"),
    UniverseMember("AAPL", "company", "Apple Inc."),
    UniverseMember("MSFT", "company", "Microsoft Corporation"),
    UniverseMember("NVDA", "company", "NVIDIA Corporation"),
    UniverseMember("JPM", "company", "JPMorgan Chase & Co."),
)
REAL_WINDOW = ("2023-01-03", "2024-12-31")
BENCHMARK_TICKERS = ("SPY", "QQQ")
REAL_PARAMS = TrendSwingParams(
    breakout_lookback_days=20,
    swing_lookback_days=10,
    min_stop_fraction=0.01,
    max_stop_fraction=0.25,
    max_position_fraction=0.25,
    equity_basis="current_equity",
    initial_cash=1_000_000.0,
    fees=0.0,
    tie_break_seed=20260828,
)
REAL_RISK = RiskSettings(per_trade_risk=0.02, monthly_loss_cap=0.06, reward_risk_floor=1.5)
RISK_FREE_RATE = 0.04             # Sortino 的口徑,無預設值,要明寫

# 合成場的規模:夠大先撐得起「約 500 個歷史案例」那一條。
SEED = 20260828
ROWS, COLUMNS = 900, 40
TOY_SNAPSHOT_HASH = "toy028toy028toy028"


# ----------------------------------------------------------------------
# 合成 K 線(不連網)
# ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def toy_panel() -> BarPanel:
    """玩具 K 線面板:分段趨勢 + 一個全市場共同因子(好令壞月份成群出現)。"""
    generator = np.random.default_rng(SEED)
    dates = pd.bdate_range("2021-01-04", periods=ROWS)
    entity_ids = list(range(901, 901 + COLUMNS))

    market = np.zeros(ROWS)
    position = 0
    while position < ROWS:
        span = int(generator.integers(15, 35))
        market[position:position + span] = generator.normal(0.0, 0.004)
        position += span
    market = market[:, None] + generator.normal(0.0, 0.010, (ROWS, 1))

    drift = np.zeros((ROWS, COLUMNS))
    for column in range(COLUMNS):
        position = 0
        while position < ROWS:
            span = int(generator.integers(25, 60))
            drift[position:position + span, column] = generator.normal(0.0, 0.0022)
            position += span

    steps = drift + market + generator.normal(0.0, 0.018, (ROWS, COLUMNS))
    close = 100.0 * np.exp(np.cumsum(steps, axis=0))
    open_ = np.empty_like(close)
    open_[0] = 100.0
    open_[1:] = close[:-1] * (1.0 + generator.normal(0.0, 0.005, (ROWS - 1, COLUMNS)))
    high = np.maximum(open_, close) * (1.0 + np.abs(generator.normal(0.0, 0.010, close.shape)))
    low = np.minimum(open_, close) * (1.0 - np.abs(generator.normal(0.0, 0.010, close.shape)))

    frame = lambda values: pd.DataFrame(values, index=dates, columns=entity_ids)  # noqa: E731
    return BarPanel.from_frames(
        open=frame(open_), high=frame(high), low=frame(low), close=frame(close)
    )


@pytest.fixture()
def gateway(tmp_path, monkeypatch):
    monkeypatch.setenv("KARST_WRITER", "KARST-028-trendswing")
    with Gateway.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


@pytest.fixture()
def toy(gateway, toy_panel, tmp_path):
    """合成場:快照登記、策略與參數集經唯一入口登記、跑一次、落痕。"""
    store = gateway.store
    snapshot_id = store.register_snapshot(
        source="toy", taken_on="2026-08-28", content_hash=TOY_SNAPSHOT_HASH
    )
    version, param_set = register_trend_swing(
        gateway,
        strategy_name=STRATEGY,
        snapshot_id=snapshot_id,
        param_set_name=PARAM_SET,
        rebalance_cadence=CADENCE,
        values=param_values(SAMPLE_PARAMS, SAMPLE_RISK),
        description="KARST-028 示例參數,不是現役設定",
    )
    params, risk = read_setup(param_set)
    result = run_trend_swing(panel=toy_panel, params=params, risk=risk)
    runs = RunStore(store, root=tmp_path / "runs")
    record = record_trend_swing_run(
        runs,
        result,
        strategy_name=version.name,
        param_set_name=param_set.name,
        snapshot_id=snapshot_id,
        engine_version=ENGINE_VERSION,
        strategy_version_no=version.version_no,
        param_set_version_no=param_set.version_no,
    )
    return {
        "gateway": gateway, "store": store, "panel": toy_panel, "snapshot_id": snapshot_id,
        "strategy": version, "param_set": param_set, "params": params, "risk": risk,
        "result": result, "runs": runs, "record": record,
    }


# ----------------------------------------------------------------------
# 真實抓取那半
# ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def online() -> None:
    try:
        YFinanceSource().fetch_daily_bars(["SPY"], "2024-01-02", "2024-01-05")
    except DataFetchFailed as exc:
        pytest.skip(f"離線或來源不通,跳過真實抓取:{exc}")


@pytest.fixture(scope="module")
def real(online, tmp_path_factory):
    """真實一次:抓快照 → 登記定義 → 跑回測 → 落痕 → 算指標。"""
    root = tmp_path_factory.mktemp("trend-swing")
    with Gateway.open(str(root / "karst.sqlite")) as opened:
        store = opened.store
        snapshot = build_price_snapshot(
            store,
            start=REAL_WINDOW[0],
            end=REAL_WINDOW[1],
            universe=REAL_UNIVERSE,
            source=YFinanceSource(),
            root=root / "snapshots",
        )
        universe = read_universe(store, snapshot.snapshot_id, root=root / "snapshots")
        traded = sorted(
            int(entity_id)
            for ticker, entity_id in zip(universe["ticker"], universe["entity_id"])
            if ticker not in BENCHMARK_TICKERS
        )
        panel = build_bar_panel(
            store, snapshot.snapshot_id, entity_ids=traded, root=root / "snapshots"
        )

        version, param_set = register_trend_swing(
            opened,
            strategy_name=STRATEGY,
            snapshot_id=snapshot.snapshot_id,
            param_set_name=PARAM_SET,
            rebalance_cadence=CADENCE,
            values=param_values(REAL_PARAMS, REAL_RISK),
            description="KARST-028 示例參數,不是現役設定",
        )
        params, risk = read_setup(param_set)
        result = run_trend_swing(panel=panel, params=params, risk=risk)
        runs = RunStore(store, root=root / "runs")
        record = record_trend_swing_run(
            runs,
            result,
            strategy_name=version.name,
            param_set_name=param_set.name,
            snapshot_id=snapshot.snapshot_id,
            engine_version=ENGINE_VERSION,
            strategy_version_no=version.version_no,
            param_set_version_no=param_set.version_no,
        )
        metrics = run_metrics(
            runs,
            record.run_id,
            risk_free_rate=RISK_FREE_RATE,
            snapshot_root=root / "snapshots",
        )
        yield {
            "store": store, "snapshot": snapshot, "panel": panel, "traded": traded,
            "result": result, "runs": runs, "record": record, "metrics": metrics,
        }


# ======================================================================
# 驗收條件 1:在真實日線數據上跑得出一次完整回測,交得出逐日淨值、逐筆交易
#             明細與持倉序列(D-016)
# ======================================================================
def test_a_full_backtest_on_real_daily_bars_yields_equity_orders_and_holdings(real):
    result, panel, record = real["result"], real["panel"], real["record"]

    # 面板真的來自真實日線:兩年美股交易日,十位數的股票數
    assert len(panel.dates) > 400
    assert list(panel.entity_ids) == real["traded"]
    assert str(panel.dates[0].date()) >= REAL_WINDOW[0]
    assert str(panel.dates[-1].date()) <= REAL_WINDOW[1]

    # (a) 逐日淨值:每一根 K 線一個數,無缺口,由起始本金起步
    equity = result.equity_curve
    assert isinstance(equity, pd.Series)
    assert list(equity.index) == list(panel.dates)
    assert equity.notna().all() and (equity > 0).all()
    assert float(equity.iloc[0]) == pytest.approx(result.params.initial_cash)
    assert np.isfinite(result.total_return)

    # (b) 逐筆交易明細:一買一賣都有,欄位齊全
    orders = result.orders_frame()
    assert len(orders) > 0
    assert set(orders["side"]) == {"buy", "sell"}
    assert list(orders.columns) == [
        "trade_date", "entity_id", "side", "shares", "price", "fees",
        "gross_value", "exit_reason",
    ]
    assert (orders["shares"] > 0).all() and (orders["price"] > 0).all()
    assert set(orders["entity_id"]) <= set(panel.entity_ids)

    # (c) 持倉序列:日期 × 實體編號,一格都不缺
    holdings = result.holdings
    assert holdings.shape == (len(panel.dates), len(panel.entity_ids))
    assert holdings.notna().all().all()
    assert (holdings >= 0).all().all()
    assert float(holdings.to_numpy().max()) > 0        # 真的持過貨

    # (d) 三件都落了痕,讀得回,而且與落痕那一刻一字不差
    runs = real["runs"]
    assert runs.verify_run(record.run_id) == ()
    replayed = runs.equity_curve(record.run_id)
    assert len(replayed) == len(equity)
    assert float(replayed.iloc[-1]) == pytest.approx(float(equity.iloc[-1]))
    assert len(runs.orders(record.run_id)) == len(orders)
    assert not runs.holdings(record.run_id).empty

    # (e) 八項指標算得出,連 QQQ／SPY 的超額(重看不重跑)
    metrics = real["metrics"]
    assert np.isfinite(metrics.total_return) and np.isfinite(metrics.annual_return)
    assert metrics.max_drawdown <= 0.0
    assert set(metrics.annual_excess) == {"QQQ", "SPY"}
    assert all(np.isfinite(v) for v in metrics.annual_excess.values())


# ======================================================================
# 驗收條件 2:五件規則與共用風控層在同一次運行中全部生效,運行記錄蓋齊
#             策略版本 × 參數 × 期間 × 數據快照(D-016、規格 7.4)
# ======================================================================
def test_all_five_rules_and_the_shared_risk_layer_fire_in_one_recorded_run(toy):
    panel, result, record = toy["panel"], toy["result"], toy["record"]
    rule_params = result.rule_params
    signals = build_rule_signals(panel, rule_params)
    bar_of = {day.strftime("%Y-%m-%d"): i for i, day in enumerate(panel.dates)}
    column_of = {entity_id: i for i, entity_id in enumerate(panel.entity_ids)}
    orders = result.orders_frame()
    buys = orders[orders["side"] == "buy"]
    sells = orders[orders["side"] == "sell"]
    assert len(buys) > 0 and len(sells) > 0

    # --- 規則 1 入場突破:每一筆買入都落在訊號為真的那一格 ---
    assert result.entry_signals > 0
    for row in buys.itertuples():
        assert signals.entries[bar_of[row.trade_date], column_of[row.entity_id]]

    # --- 規則 2 止蝕 + 規則 3 目標:每一筆賣出都由這兩者其中之一觸發 ---
    # 逐筆按時序配對:賣出對的是它自己那一次入場所訂的計劃,不是那隻股最近一張。
    plans: dict[int, tuple[float, float]] = {}
    stopped = targeted = 0
    for row in orders.itertuples():                    # 已按日期、實體、方向排好
        if row.side == "buy":
            bar, column = bar_of[row.trade_date], column_of[row.entity_id]
            plans[row.entity_id] = (
                float(signals.stop_level[bar, column]),
                float(signals.target_level[bar, column]),
            )
            continue
        stop, target = plans.pop(row.entity_id)
        if row.price <= stop * (1.0 + 1e-9):
            stopped += 1
        elif row.price >= target * (1.0 - 1e-9):
            targeted += 1
        else:                                          # 兩者皆非 = 有第三條路離場
            pytest.fail(f"{row.trade_date} 的賣出價 {row.price} 既非止蝕 {stop} 亦非目標 {target}")
    assert stopped > 0 and targeted > 0

    # 賠率門檻真的攔得住:同一份參數把門檻推高,訊號數必然減少
    higher = result.params.rule_params(
        RiskSettings(
            per_trade_risk=toy["risk"].per_trade_risk,
            monthly_loss_cap=toy["risk"].monthly_loss_cap,
            reward_risk_floor=toy["risk"].reward_risk_floor * 3.0,
        )
    )
    assert build_rule_signals(panel, higher).count < result.entry_signals

    # --- 規則 4 注碼:股數 = 單筆風險 × 注碼基數 / 止蝕距離,受市值上限封頂 ---
    basis = result.sizing_basis
    assert basis.notna().all() and (basis > 0).all()
    assert basis.nunique() > 1                          # 基數會走動 = 當下權益
    assert float(basis.iloc[-1]) != pytest.approx(rule_params.initial_cash)
    # 公式算出來的是**上限**:現金不夠時只落得到部分注碼,但一筆都不可以超出上限。
    exact = 0
    for row in buys.itertuples():
        bar, column = bar_of[row.trade_date], column_of[row.entity_id]
        equity = float(basis.iloc[bar])
        stop = float(signals.stop_level[bar, column])
        wanted = rule_params.sizing.risk_per_trade * equity / (row.price - stop)
        cap = rule_params.sizing.max_position_fraction * equity / row.price
        ceiling = min(wanted, cap)
        assert row.shares <= ceiling * (1.0 + 1e-6)
        exact += row.shares == pytest.approx(ceiling, rel=1e-6)
    assert exact > 0                                   # 現金夠的時候,落的正是公式那個數

    # --- 規則 5 月度虧損熔斷:真的落過閘,而且落閘那些日子一張新單都沒有 ---
    blocked = result.breaker_blocked
    assert result.blocked_days > 0
    blocked_days = {day.strftime("%Y-%m-%d") for day in blocked.index[blocked.to_numpy()]}
    assert blocked_days.isdisjoint(set(buys["trade_date"]))
    # 關掉熔斷即另一個結果:證明它真的有在管事,不是掛住不動
    without = run_trend_swing(
        panel=panel,
        params=result.params,
        risk=RiskSettings(
            per_trade_risk=toy["risk"].per_trade_risk,
            monthly_loss_cap=None,
            reward_risk_floor=toy["risk"].reward_risk_floor,
        ),
    )
    assert without.blocked_days == 0
    assert len(without.orders) != len(result.orders)

    # --- 共用風控層:三條規則的取值只有一條路進得了引擎 ---
    assert read_risk_settings(rule_params) == toy["risk"]
    values = toy["param_set"].values
    for rule in RISK_RULES.values():
        assert rule.param_key in values                 # 三個數住在參數集,帶 risk. 字首
    assert sorted(referenced_rule_keys(toy["store"], STRATEGY)) == sorted(RISK_RULES)
    # 策略層碰都碰不到那三件帶風控取值的規則型別:只有 build_rule_params 砌得出
    symbols = set(_code_symbols(MODULE_PATH))
    assert symbols.isdisjoint(
        {"MeasuredMoveTarget", "MonthlyLossBreaker", "RiskFractionSizing"}
    )
    assert "build_rule_params" in symbols

    # --- 運行記錄蓋齊五件 ---
    assert record.strategy_name == toy["strategy"].name
    assert record.strategy_version_no == toy["strategy"].version_no
    assert record.strategy_type == TREND_SWING_STRATEGY_TYPE
    assert record.param_set_name == toy["param_set"].name
    assert record.param_set_version_no == toy["param_set"].version_no
    assert record.param_values == dict(toy["param_set"].values)
    assert record.period_start == str(panel.dates[0].date())
    assert record.period_end == str(panel.dates[-1].date())
    assert record.snapshot_id == toy["snapshot_id"]
    assert record.engine_name == result.engine_name and record.engine_version == ENGINE_VERSION
    assert [f.name for f in record.factors] == [BREAKOUT_FACTOR_NAME]
    assert record.trading_days == len(panel.dates)
    assert set(record.artifacts) == {"equity", "holdings", "orders"}

    # 同一組輸入重錄回同一個編號;改任何一件即另一次運行
    again = record_trend_swing_run(
        toy["runs"], result,
        strategy_name=toy["strategy"].name, param_set_name=toy["param_set"].name,
        snapshot_id=toy["snapshot_id"], engine_version=ENGINE_VERSION,
        strategy_version_no=toy["strategy"].version_no,
        param_set_version_no=toy["param_set"].version_no,
    )
    assert again.run_id == record.run_id
    other = record_trend_swing_run(
        toy["runs"], result,
        strategy_name=toy["strategy"].name, param_set_name=toy["param_set"].name,
        snapshot_id=toy["snapshot_id"], engine_version="0.2.0",
        strategy_version_no=toy["strategy"].version_no,
        param_set_version_no=toy["param_set"].version_no,
    )
    assert other.run_id != record.run_id


# ======================================================================
# 驗收條件 3:規則在約 500 個歷史案例上驗證過,案例數目與驗證結果貼得出
#             (規格 5.4、6.5)
# ======================================================================
def test_the_entry_rule_is_validated_on_about_five_hundred_historical_cases(toy):
    panel, result = toy["panel"], toy["result"]
    cases = entry_cases(panel, result.rule_params)
    stats = case_stats(cases)

    # (a) 樣本量:入場規則在全部實體 × 全期觸發過的案例,數量級要到約 500(規格 5.4 第 5 條)
    assert stats.cases >= 500
    assert stats.cases == len(cases)
    # 案例不受現金與熔斷所限,所以一定多過回測真做得成的筆數——兩者不是同一回事
    assert stats.cases > len([o for o in result.orders if o.side == "buy"])

    # (b) 逐案例記得住入場日、出場日、出場原因與報酬
    frame = cases_frame(cases)
    assert list(frame.columns) == list(CASE_COLUMNS)
    assert len(frame) == stats.cases
    assert set(frame["exit_reason"]) <= set(EXIT_REASONS)
    assert set(frame["exit_reason_name"]) <= set(EXIT_REASONS.values())
    assert (frame["entry_date"] <= frame["exit_date"]).all()
    assert (frame["signal_date"] < frame["entry_date"]).all()
    assert frame["return_pct"].notna().all() and np.isfinite(frame["return_pct"]).all()
    assert frame["r_multiple"].notna().all() and np.isfinite(frame["r_multiple"]).all()
    # 收得成場的案例最少持一日;持 0 日的只有一種——訊號落在最後一根,無日可行
    closed = frame[frame["exit_reason"] != EXIT_UNCLOSED]
    assert (closed["holding_days"] >= 1).all()
    zero_days = frame[frame["holding_days"] == 0]
    assert (zero_days["exit_reason"] == EXIT_UNCLOSED).all()
    assert (zero_days["entry_date"] == str(panel.dates[-1].date())).all()
    assert stats.by_reason[EXIT_STOP] > 0 and stats.by_reason[EXIT_TARGET] > 0
    assert sum(stats.by_reason.values()) == stats.cases

    # (c) 驗證結果貼得出:勝率與平均賠率都是實數
    assert 0.0 <= stats.win_rate <= 1.0
    assert 0.0 <= stats.closed_win_rate <= 1.0
    assert np.isfinite(stats.average_r_multiple)
    assert np.isfinite(stats.average_reward_risk)
    # 計劃三元素齊全:賠率為正、目標高過入場、止蝕低過入場
    assert (frame["reward_risk"] > 0).all()
    assert (frame["target_price"] > frame["entry_price"]).all()
    assert (frame["stop_price"] < frame["entry_price"]).all()

    # (d) 出場原因判得準:逐案例對回 K 線本體
    columns = {entity_id: i for i, entity_id in enumerate(panel.entity_ids)}
    bars = {day.strftime("%Y-%m-%d"): i for i, day in enumerate(panel.dates)}
    lows, highs = panel.low.to_numpy(), panel.high.to_numpy()
    for case in cases[:: max(1, len(cases) // 40)]:
        column = columns[case.entity_id]
        start, stop_bar = bars[case.entry_date] + 1, bars[case.exit_date]
        window_low = lows[start:stop_bar, column]
        window_high = highs[start:stop_bar, column]
        # 出場之前一根都未穿止蝕、未觸目標
        assert (window_low > case.stop_price).all()
        assert (window_high < case.target_price).all()
        if case.exit_reason == EXIT_STOP:
            assert lows[stop_bar, column] <= case.stop_price
            assert case.r_multiple <= 0.0
        elif case.exit_reason == EXIT_TARGET:
            assert highs[stop_bar, column] >= case.target_price
            assert case.r_multiple > 0.0
        else:
            assert case.exit_reason == EXIT_UNCLOSED
            assert stop_bar == len(panel.dates) - 1

    # (e) 案例數隨參數變:放寬賠率門檻即多幾個案例,規則本身可以逐個取值驗
    loose = result.params.rule_params(
        RiskSettings(
            per_trade_risk=toy["risk"].per_trade_risk,
            monthly_loss_cap=toy["risk"].monthly_loss_cap,
            reward_risk_floor=toy["risk"].reward_risk_floor / 2.0,
        )
    )
    assert case_stats(entry_cases(panel, loose)).cases > stats.cases


# ======================================================================
# 驗收條件 4:交出的參數全部可掃描,票內不寫死任何一個取值(D-008)
# ======================================================================
def test_every_parameter_is_scannable_and_no_value_is_hard_coded(toy):
    panel, gateway = toy["panel"], toy["gateway"]

    # (a) 十二格取值全部住在參數集,讀得回、對得上
    values = toy["param_set"].values
    assert set(STRATEGY_PARAM_KEYS) <= set(values)
    assert {rule.param_key for rule in RISK_RULES.values()} <= set(values)
    params, risk = read_setup(toy["param_set"])
    assert params == SAMPLE_PARAMS and risk == SAMPLE_RISK

    # (b) 掃描 = 多砌幾份參數 + 多叫一次,一行碼都不用改
    grid = params_grid(
        breakout_lookback_days=(20, 40),
        swing_lookback_days=(10, 20),
        min_stop_fraction=(params.min_stop_fraction,),
        max_stop_fraction=(params.max_stop_fraction,),
        max_position_fraction=(params.max_position_fraction,),
        equity_basis=(params.equity_basis,),
        initial_cash=(params.initial_cash,),
        fees=(params.fees,),
        tie_break_seed=(params.tie_break_seed,),
    )
    assert len(grid) == 4
    swept = sweep_trend_swing(
        panel=panel,
        grid=grid,
        risk_grid=sweep_grid(
            per_trade_risk=(0.03, 0.06),
            monthly_loss_cap=(0.06, None),
            reward_risk_floor=(1.0,),
        ),
    )
    assert len(swept) == 4 * 2 * 2 * 1
    frame = swept.frame()
    assert list(frame.columns) == list(SWEEP_COLUMNS)
    assert len(frame) == len(swept)
    # 每一格參數都真的入了數:十六格跑出多過一個結果,而且每個軸都推得動
    assert frame["total_return"].nunique() > 1
    assert frame.groupby("entry.breakout_lookback_days")["entry_signals"].nunique().max() >= 1
    assert frame["entry_signals"].nunique() > 1        # 突破日數 / 賠率門檻推得動訊號數
    assert frame["blocked_days"].nunique() > 1         # 熔斷開關推得動落閘日數
    assert frame["monthly_loss_cap"].isna().any()      # 空白 = 不引用熔斷,不是門檻為零

    # (c) 九格都掃得到:每一格單獨換一個值,砌得出另一份參數
    for field in STRATEGY_PARAM_KEYS:
        assert field in frame.columns

    # (d) 無預設值:簽名一格都沒有預設,參數集缺一格即拒收
    signature = inspect.signature(TrendSwingParams)
    for name in signature.parameters:
        assert signature.parameters[name].default is inspect.Parameter.empty
    _, short = register_trend_swing(
        gateway,
        strategy_name=STRATEGY,
        snapshot_id=toy["snapshot_id"],
        param_set_name="掃描-缺一格",
        rebalance_cadence=CADENCE,
        values={k: v for k, v in values.items() if k != STRATEGY_PARAM_KEYS[0]},
    )
    with pytest.raises(ContractViolation, match="缺參數"):
        TrendSwingParams.from_param_set(short)

    # (e) 策略層原始碼查不到任何一個取值(看語法樹,不看註解與說明文字)
    assert _value_defaults(MODULE_PATH) == []


# ----------------------------------------------------------------------
# 掃原始碼用的兩個小工具(與 tests/test_factor_mix.py 同制)
# ----------------------------------------------------------------------

# 這幾個字出現在名裡,就代表那個名是一格取值。取值一律住參數集,不准在碼裡有數。
_VALUE_TOKENS = (
    "lookback", "fraction", "cash", "fee", "seed", "risk", "reward", "basis", "cap",
)


def _code_symbols(path: Path) -> list[str]:
    """這個檔的碼裡出現過的名與字串(說明文字不算)。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)

    symbols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            symbols.append(node.id)
        elif isinstance(node, ast.Attribute):
            symbols.append(node.attr)
        elif isinstance(node, ast.arg):
            symbols.append(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value not in docstrings:
                symbols.append(node.value)
    return symbols


def _value_defaults(path: Path) -> list[str]:
    """找出有沒有人偷偷給某格參數一個數值(簽名預設、類別欄位、模組常數皆計)。

    說明文字裡的用法示範不算,只有真的寫進簽名或賦值那一格才算。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: list[str] = []

    def is_number(node: ast.AST | None) -> bool:
        return (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        )

    def is_value_name(name: str) -> bool:
        lowered = name.lower()
        return any(token in lowered for token in _VALUE_TOKENS)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = node.args.posonlyargs + node.args.args
            tail = positional[len(positional) - len(node.args.defaults):]
            pairs = list(zip(tail, node.args.defaults))
            pairs += [
                (argument, default)
                for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults)
                if default is not None
            ]
            offenders += [
                f"{path.name}:{node.name}({argument.arg}=...)"
                for argument, default in pairs
                if is_value_name(argument.arg) and is_number(default)
            ]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if is_value_name(node.target.id) and is_number(node.value):
                offenders.append(f"{path.name}:{node.target.id}")
        elif isinstance(node, ast.Assign):
            offenders += [
                f"{path.name}:{target.id}"
                for target in node.targets
                if isinstance(target, ast.Name)
                and is_value_name(target.id)
                and is_number(node.value)
            ]
    return offenders
