"""KARST-024 驗收:引擎適配層 B,規則與風控路徑。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。
玩具數據:合成 K 線,固定種子,不連外部數據,不開任何資料庫連線(D-027)。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_engine_rules.py -q``
"""

from __future__ import annotations

import inspect
import re
from dataclasses import fields
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from karst.engine import (
    BarPanel,
    BreakoutEntry,
    MeasuredMoveTarget,
    MonthlyLossBreaker,
    Order,
    RiskFractionSizing,
    RuleBacktestResult,
    RuleEngine,
    RuleNotExpressible,
    RuleNotSpecified,
    RuleSignals,
    RuleSimulationOutput,
    RuleStrategyParams,
    SwingLowStop,
    TradingCosts,
    build_rule_signals,
    run_rule_strategy,
    run_rule_strategy_on_signal_matrix,
)
from karst.errors import ContractViolation

from doubles.engines import RecordingRuleEngine

REPO_ROOT = Path(__file__).resolve().parents[1]

SEED = 20260828
ROWS, COLUMNS = 500, 60
INITIAL_CASH = 1_000_000.0

# 五件規則的基準參數組。一組數字兩條路徑共用,兩次運行只差注碼基數與熔斷。
N_BREAK = 40          # 規則 1:突破前 40 日最高
SWING_LOOKBACK = 10   # 規則 2:前 10 日波段低位
MIN_REWARD_RISK = 1.0  # 規則 3:賠率門檻
RISK_PER_TRADE = 0.06  # 規則 4:單筆風險 6% 注碼基數
MAX_POSITION = 0.25   # 規則 4:單一持倉市值上限
BREAKER_DD = 0.06     # 規則 5:月內回落 6% 即停止該月新入場


def _params(*, equity_basis: str, breaker: float | None) -> RuleStrategyParams:
    """五件規則一次過寫齊。一個參數都沒有預設值,五件都要明寫。"""
    return RuleStrategyParams(
        entry=BreakoutEntry(lookback_days=N_BREAK),
        stop=SwingLowStop(
            lookback_days=SWING_LOOKBACK, min_stop_fraction=0.01, max_stop_fraction=0.25
        ),
        target=MeasuredMoveTarget(min_reward_risk=MIN_REWARD_RISK),
        sizing=RiskFractionSizing(
            risk_per_trade=RISK_PER_TRADE,
            max_position_fraction=MAX_POSITION,
            equity_basis=equity_basis,
        ),
        breaker=None if breaker is None else MonthlyLossBreaker(max_monthly_drawdown=breaker),
        initial_cash=INITIAL_CASH,
        fees=0.0,
        tie_break_seed=SEED,
    )


@pytest.fixture(scope="module")
def panel() -> BarPanel:
    """玩具 K 線面板:分段趨勢 + 一個全市場共同因子(好令壞月份成群出現)。"""
    generator = np.random.default_rng(SEED)
    dates = pd.bdate_range("2024-01-02", periods=ROWS)
    entity_ids = list(range(701, 701 + COLUMNS))

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


@pytest.fixture(scope="module")
def control_arm(panel) -> tuple[RuleBacktestResult, RuleBacktestResult]:
    """對照臂:注碼基數改回起始本金、熔斷關掉,兩條路徑各跑一次。"""
    params = _params(equity_basis="initial_cash", breaker=None)
    return (
        run_rule_strategy_on_signal_matrix(panel=panel, params=params),
        run_rule_strategy(panel=panel, params=params),
    )


@pytest.fixture(scope="module")
def breaker_arm(panel) -> tuple[RuleBacktestResult, RuleBacktestResult]:
    """同一組參數、注碼基數同為當下權益,熔斷關一次開一次。"""
    return (
        run_rule_strategy(panel=panel, params=_params(equity_basis="current_equity", breaker=None)),
        run_rule_strategy(
            panel=panel, params=_params(equity_basis="current_equity", breaker=BREAKER_DD)
        ),
    )


# 驗收條件 1:把注碼基數改回起始本金並關掉熔斷之後,結果與訊號矩陣路徑吻合到
# 小數點後十四位(規格 6.2,重現 KARST-013 的對照臂)
def test_control_arm_matches_the_signal_matrix_path(panel, control_arm):
    signal_matrix, order_func = control_arm

    assert signal_matrix.engine_name == "vectorbt-signals"
    assert order_func.engine_name == "vectorbt-order-func"
    assert signal_matrix.entry_signals == order_func.entry_signals > 0
    assert len(order_func.orders) > 0

    # 總報酬與最大回撤:小數點後十四位一模一樣
    assert round(order_func.total_return, 14) == round(signal_matrix.total_return, 14)
    assert round(order_func.max_drawdown, 14) == round(signal_matrix.max_drawdown, 14)

    # 逐日淨值整條曲線都對得上(以相對誤差計,遠嚴過十四位小數)
    theirs = signal_matrix.equity_curve.to_numpy()
    ours = order_func.equity_curve.to_numpy()
    assert np.max(np.abs(ours - theirs) / np.abs(theirs)) < 1e-13

    # 逐筆訂單一張不多一張不少,連股數與成交價都對得上
    assert len(order_func.orders) == len(signal_matrix.orders)
    for ours_order, theirs_order in zip(order_func.orders, signal_matrix.orders, strict=True):
        assert ours_order.trade_date == theirs_order.trade_date
        assert ours_order.entity_id == theirs_order.entity_id
        assert ours_order.side == theirs_order.side
        assert ours_order.shares == pytest.approx(theirs_order.shares, rel=1e-12)
        assert ours_order.price == pytest.approx(theirs_order.price, rel=1e-12)

    # 對照臂只可以是對照臂:熔斷與當下權益基數,訊號矩陣路徑根本表達不到,
    # 問它就當場拒收,不會默默算個假數出來(規格 6.2 推翻 A-005 的理由)
    with pytest.raises(RuleNotExpressible, match="熔斷"):
        run_rule_strategy_on_signal_matrix(
            panel=panel, params=_params(equity_basis="initial_cash", breaker=BREAKER_DD)
        )
    with pytest.raises(RuleNotExpressible, match="當下權益"):
        run_rule_strategy_on_signal_matrix(
            panel=panel, params=_params(equity_basis="current_equity", breaker=None)
        )


# 驗收條件 2:熔斷開啟時月內最深回撤較關閉時收窄(規格 6.2、KARST-013)
def test_breaker_narrows_the_worst_month_drawdown(breaker_arm):
    without, with_breaker = breaker_arm

    assert without.blocked_days == 0
    assert with_breaker.blocked_days > 0

    # 月內最深回撤:開熔斷之後明顯收窄(兩個數字貼在票上)
    assert with_breaker.worst_month_drawdown > without.worst_month_drawdown
    assert with_breaker.worst_month_drawdown - without.worst_month_drawdown > 0.01

    # 收窄的是**月內**回撤,不是全期回撤——熔斷管的只是單月失血
    assert with_breaker.worst_month_drawdown > -BREAKER_DD * 3
    assert without.worst_month_drawdown < -BREAKER_DD

    # 兩次運行除了熔斷之外一模一樣
    assert without.params.sizing == with_breaker.params.sizing
    assert without.params.breaker is None
    assert with_breaker.params.breaker == MonthlyLossBreaker(max_monthly_drawdown=BREAKER_DD)


# 驗收條件 3:五件規則在同一次運行中全部生效,而且查得出任何一日的注碼基數
# 就是當日權益(規格 6.2 兩條結論)
def test_five_rules_all_bite_in_one_run(panel, breaker_arm):
    _, result = breaker_arm
    signals = build_rule_signals(panel, result.params)

    dates = [day.strftime("%Y-%m-%d") for day in panel.dates]
    entity_ids = list(panel.entity_ids)
    opens = panel.open.to_numpy()
    highs = panel.high.to_numpy()
    lows = panel.low.to_numpy()
    closes = panel.close.to_numpy()
    basis = result.sizing_basis.to_numpy()
    blocked = result.breaker_blocked.to_numpy()

    def cell(order: Order) -> tuple[int, int]:
        return dates.index(order.trade_date), entity_ids.index(order.entity_id)

    buys = [order for order in result.orders if order.side == "buy"]
    sells = [order for order in result.orders if order.side == "sell"]
    assert len(buys) > 10 and len(sells) > 10

    # --- 規則 1 入場突破:每一張入場單的前一根 K 線,收市價都高於前 N 日最高 ---
    prior_high = panel.high.rolling(N_BREAK, min_periods=N_BREAK).max().shift(1).to_numpy()
    for order in buys:
        row, column = cell(order)
        assert signals.entries[row, column]
        assert closes[row - 1, column] > prior_high[row - 1, column]
        # 成交價正正是這根 K 線的開價(D-021 第 3 條),不是收價
        assert order.price == pytest.approx(opens[row, column])

    # --- 規則 2 止蝕、規則 3 目標:兩種離場都真的出現過 ---
    live: dict[int, tuple[float, float]] = {}
    stop_exits = target_exits = 0
    for order in sorted(result.orders, key=lambda item: (item.trade_date, item.entity_id)):
        row, column = cell(order)
        if order.side == "buy":
            live[column] = (signals.stop_level[row, column], signals.target_level[row, column])
            continue
        stop, target = live.pop(column)
        if lows[row, column] <= stop:
            assert order.price == pytest.approx(min(opens[row, column], stop))
            stop_exits += 1
        else:
            assert highs[row, column] >= target
            assert order.price == pytest.approx(max(opens[row, column], target))
            target_exits += 1
    assert stop_exits > 0
    assert target_exits > 0

    # 止蝕價與目標價都是真絕對價位:止蝕 = 前波段低位,目標 = 入場參考價 + 區間高度
    swing_low = panel.low.rolling(SWING_LOOKBACK, min_periods=SWING_LOOKBACK).min().to_numpy()
    row, column = cell(buys[0])
    assert signals.stop_level[row, column] == pytest.approx(swing_low[row - 1, column])
    assert signals.target_level[row, column] > closes[row - 1, column]

    # --- 規則 4 注碼:基數就是當日權益,查得出來 ---
    # 當日權益 = 上一根收市的現金 + 上一根收市的持倉 × 今日開價(今日成交價)
    rebuilt = np.empty_like(basis)
    rebuilt[0] = result.params.initial_cash
    cash = result.cash.to_numpy()
    holdings = result.holdings.to_numpy()
    rebuilt[1:] = cash[:-1] + (holdings[:-1] * opens[1:]).sum(axis=1)
    assert np.max(np.abs(basis - rebuilt) / rebuilt) < 1e-12

    # 而且它真的在動:基數若是起始本金,這一格會是 0
    moved = int((np.abs(basis - result.params.initial_cash) > 1e-6).sum())
    assert moved > len(basis) * 0.5
    assert basis.min() < result.params.initial_cash < basis.max()

    # 逐張入場單:股數 = 風險比例 × 當日基數 / 止蝕距離,超過持倉上限就封頂。
    # 當日現金不夠應付全部入場單時,引擎只買得到一部分——那些日子只查「不會超注」;
    # 現金足夠的日子,注碼要分毫不差。
    def wanted_shares(order: Order) -> float:
        row, column = cell(order)
        stop_distance = opens[row, column] - signals.stop_level[row, column]
        return min(
            RISK_PER_TRADE * basis[row] / stop_distance,
            MAX_POSITION * basis[row] / opens[row, column],
        )

    for order in buys:
        assert order.shares <= wanted_shares(order) * (1.0 + 1e-9)   # 永不超注

    fully_funded = 0
    for day in sorted({order.trade_date for order in buys}):
        same_day = [order for order in buys if order.trade_date == day]
        row = dates.index(day)
        opening_cash = result.params.initial_cash if row == 0 else cash[row - 1]
        # 單靠開市現金已經買得起全部應下的注(不計同日賣出所得),才算現金充裕
        if sum(wanted_shares(order) * order.price for order in same_day) > opening_cash:
            continue
        for order in same_day:
            assert order.shares == pytest.approx(wanted_shares(order), rel=1e-9)
        fully_funded += len(same_day)
    assert fully_funded >= 10

    # --- 規則 5 熔斷:落閘那些日子,一張新入場單都沒有 ---
    assert blocked.sum() > 0
    assert not any(blocked[cell(order)[0]] for order in buys)
    # 而且它真的攔住了東西:落閘日之中有日子本來是有入場訊號的
    assert signals.entries[blocked.astype(bool)].any()


# 驗收條件 4:適配層對外只收 Karst 自己的型別,合約層無第三方引擎型別(D-007 第 3 條)
def test_rule_contracts_stay_behind_our_own_interface(panel, breaker_arm):
    # (a) 全個 karst/ 與 tests/ 裡面,只有適配器一個檔認得 vectorbt
    adapter = REPO_ROOT / "karst" / "engine" / "vectorbt_engine.py"
    importers = sorted(
        path
        for folder in ("karst", "tests")
        for path in (REPO_ROOT / folder).rglob("*.py")
        if re.search(r"^\s*(?:import|from)\s+vectorbt\b", path.read_text(encoding="utf-8"), re.M)
    )
    assert importers == [adapter]

    # (b) 規則合約層連 numba 都不認得——它只是一份「名詞」清單
    for name in ("rules.py", "rule_runner.py", "protocol.py"):
        source = (REPO_ROOT / "karst" / "engine" / name).read_text(encoding="utf-8")
        assert not re.search(r"^\s*(?:import|from)\s+(?:vectorbt|numba)\b", source, re.M), name

    # (c) 交出來的結果全部是 Karst 自己的型別,一個第三方型別都沒有漏出來
    _, result = breaker_arm
    leaked = [
        type(value).__module__
        for value in (
            result.equity_curve,
            result.holdings,
            result.cash,
            result.sizing_basis,
            result.breaker_blocked,
            result.params,
            result.params.entry,
            result.params.stop,
            result.params.target,
            result.params.sizing,
            result.params.breaker,
            *result.orders,
        )
        if type(value).__module__.split(".")[0] not in {"karst", "pandas", "builtins"}
    ]
    assert leaked == []

    # (d) 五件規則一個參數都沒有預設值:缺就拋錯,不代用戶決定
    #
    # 唯一一個豁免是 ``costs``:交易成本合約是後加的(KARST-043),舊有的
    # ``fees`` 那個數字要繼續行得通,所以它留空即等於「按成交金額比例、無滑點」
    # ——與成本入引擎之前逐位相同。豁免的只是「可以不寫」,**不是**「可以只寫一半」:
    # ``TradingCosts`` 自己三個欄位一個預設值都沒有,見下面的斷言。
    for contract in (
        RuleStrategyParams,
        BreakoutEntry,
        SwingLowStop,
        MeasuredMoveTarget,
        RiskFractionSizing,
        MonthlyLossBreaker,
        TradingCosts,
    ):
        for parameter in inspect.signature(contract).parameters.values():
            if contract is RuleStrategyParams and parameter.name == "costs":
                continue
            assert parameter.default is inspect.Parameter.empty, (contract.__name__, parameter.name)
    assert [field.name for field in fields(RuleStrategyParams)] == [
        "entry", "stop", "target", "sizing", "breaker", "initial_cash", "fees",
        "tie_break_seed", "costs",
    ]
    # 留空即無成本;成本講兩次即拒收
    assert _params(equity_basis="current_equity", breaker=None).costs == TradingCosts.zero()
    with pytest.raises(ContractViolation):
        RuleStrategyParams(
            entry=BreakoutEntry(lookback_days=20),
            stop=SwingLowStop(lookback_days=10, min_stop_fraction=0.01, max_stop_fraction=0.25),
            target=MeasuredMoveTarget(min_reward_risk=1.5),
            sizing=RiskFractionSizing(
                risk_per_trade=0.02, max_position_fraction=0.20, equity_basis="current_equity"
            ),
            breaker=None,
            initial_cash=100_000.0,
            fees=0.001,
            tie_break_seed=1,
            costs=TradingCosts(
                fee_model="per_share", fee_rate=0.005, slippage_fraction=0.0005
            ),
        )
    with pytest.raises(TypeError):
        RuleStrategyParams(entry=BreakoutEntry(lookback_days=20))  # 少寫幾件即湊不齊
    with pytest.raises(RuleNotSpecified):
        _params(equity_basis="", breaker=None)                     # 注碼基數留白即拒收

    # (e) 整件換走引擎:規則定義一個字都不用改
    fake = RecordingRuleEngine(name="fake")
    assert isinstance(fake, RuleEngine)
    swapped = run_rule_strategy(
        panel=panel, params=_params(equity_basis="current_equity", breaker=BREAKER_DD), engine=fake
    )
    assert swapped.engine_name == "fake"
    assert swapped.entry_signals == result.entry_signals
    assert fake.seen_signals is not None


# 假引擎住在 tests/doubles/engines.py(KARST-090)。
