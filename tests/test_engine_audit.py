"""KARST-037 驗收:出場原因、兩條查帳序列、引擎層收浮點尾數。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。
玩具數據:合成 K 線,固定種子,不連外部數據(D-027);要用資料庫的一條開 tmp 庫。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_engine_audit.py -q``
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from karst import FormulaProcedure
from karst.engine import (
    BAR_CONSISTENCY_TOLERANCE,
    EXIT_STOP,
    EXIT_TARGET,
    EXIT_UNCLOSED,
    BarPanel,
    BreakoutEntry,
    MeasuredMoveTarget,
    MonthlyLossBreaker,
    RiskFractionSizing,
    RuleStrategyParams,
    SwingLowStop,
    run_rule_strategy,
)
from karst.errors import ContractViolation, ImmutabilityViolation, NotFound
from karst.gateway import Gateway
from karst.runs import AUDIT_SERIES_KINDS, RunStore
from karst.store import FORMAL_RUN, RUN_ARTIFACT_KINDS
from karst.strategies import trend_swing

REPO_ROOT = Path(__file__).resolve().parents[1]
TREND_SWING_SOURCE = REPO_ROOT / "karst" / "strategies" / "trend_swing.py"

SEED = 20260828
ROWS, COLUMNS = 500, 60
INITIAL_CASH = 1_000_000.0

N_BREAK = 40
SWING_LOOKBACK = 10
MIN_REWARD_RISK = 1.0
RISK_PER_TRADE = 0.06
MAX_POSITION = 0.25
BREAKER_DD = 0.06

# 落痕那一條要用的身份(與 KARST-026 同一套五件)
STRATEGY = "趨勢波段"
PARAM_SET = "示例-KARST-037"
FACTOR = "趨勢·收市價突破前 N 日最高(不含當日)"
ENGINE_VERSION = "0.1.0"


def _params() -> RuleStrategyParams:
    """五件規則一次過寫齊,一個都沒有預設值。"""
    return RuleStrategyParams(
        entry=BreakoutEntry(lookback_days=N_BREAK),
        stop=SwingLowStop(
            lookback_days=SWING_LOOKBACK, min_stop_fraction=0.01, max_stop_fraction=0.25
        ),
        target=MeasuredMoveTarget(min_reward_risk=MIN_REWARD_RISK),
        sizing=RiskFractionSizing(
            risk_per_trade=RISK_PER_TRADE,
            max_position_fraction=MAX_POSITION,
            equity_basis="current_equity",
        ),
        breaker=MonthlyLossBreaker(max_monthly_drawdown=BREAKER_DD),
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
def run(panel):
    """五件規則全開跑一次。"""
    return run_rule_strategy(panel=panel, params=_params())


@pytest.fixture()
def runs(tmp_path):
    """一個乾淨的定義庫連運行留痕,身份五件已登記齊。"""
    # 快照登記要經唯一入口簽章(KARST-087),所以庫身由那道門開出來
    with Gateway.open(str(tmp_path / "karst.sqlite")).store as store:
        store.register_factor(
            FACTOR,
            scale_kind="boolean",
            procedure=FormulaProcedure(
                formula="close[t] > max(high[t-N .. t-1])",
                input_data_version="2026-08-27-a1b2c3d4e5f6",
            ),
        )
        store.register_strategy(STRATEGY, strategy_type="technical", factor_refs=[FACTOR])
        store.register_param_set(
            STRATEGY,
            param_set_name=PARAM_SET,
            rebalance_cadence="daily",
            values={"entry.breakout_lookback_days": str(N_BREAK)},
        )
        snapshot_id = store.register_snapshot(
            source="yfinance", taken_on="2026-08-27", content_hash="a1b2c3d4e5f67890"
        )
        yield RunStore(store, root=tmp_path / "runs"), snapshot_id


class _WithoutAuditSeries:
    """一份只交得出三條序列的運行結果:用來證明查帳序列不入運行編號。"""

    def __init__(self, result) -> None:
        self.equity_curve = result.equity_curve
        self.holdings = result.holdings
        self.orders = result.orders
        self.engine_name = result.engine_name


def _record(runs_and_snapshot, simulation):
    runs, snapshot_id = runs_and_snapshot
    return runs.record_simulation(
        simulation,
        strategy_name=STRATEGY,
        param_set_name=PARAM_SET,
        snapshot_id=snapshot_id,
        engine_version=ENGINE_VERSION,
        origin=FORMAL_RUN,
    )


def _round_trips(result) -> list[tuple]:
    """把訂單按實體配成一買一賣的來回。期末仍持有的那注沒有賣出,不成一對。"""
    opened: dict[int, object] = {}
    pairs: list[tuple] = []
    for order in sorted(result.orders, key=lambda item: (item.trade_date, item.entity_id)):
        if order.side == "buy":
            opened[order.entity_id] = order
        else:
            pairs.append((opened.pop(order.entity_id), order))
    return pairs


# ======================================================================
# 驗收條件 1:引擎交回的每筆賣出帶出場原因,策略層案例表直接取用,
#             karst/strategies/trend_swing.py 內不再有第二份出場規約
# ======================================================================
def test_every_sell_carries_the_exit_reason_the_engine_marked(panel, run):
    sells = [order for order in run.orders if order.side == "sell"]
    buys = [order for order in run.orders if order.side == "buy"]
    assert len(sells) > 10 and len(buys) > 10

    # (a) 每一筆賣出都帶原因,而且只有止蝕與目標兩種——熔斷不是出場原因,
    #     它只攔新入場,不平已有的倉;期末未平沒有賣出,自然不會在賣單上出現
    assert {order.exit_reason for order in sells} == {EXIT_STOP, EXIT_TARGET}
    assert all(order.exit_reason is None for order in buys)
    counts = run.exit_reason_counts
    assert counts[EXIT_STOP] > 0 and counts[EXIT_TARGET] > 0
    assert sum(counts.values()) == len(sells)

    frame = run.orders_frame()
    assert "exit_reason" in frame.columns
    assert frame.loc[frame["side"] == "sell", "exit_reason"].notna().all()
    assert frame.loc[frame["side"] == "buy", "exit_reason"].isna().all()

    # (b) 策略層的案例表直接取用同一份出場原因:同一個入場,案例講的收場日子、
    #     收場價與原因,與引擎真的賣出那一筆一模一樣
    cases = {
        (case.entity_id, case.entry_date): case
        for case in trend_swing.entry_cases(panel, run.params)
    }
    assert len(cases) > len(sells)          # 案例不受現金與熔斷所限,一定多過成交
    # 期末未平是案例的收場,不是一筆賣出——案例表有,賣單上永遠不會有
    assert any(case.exit_reason == EXIT_UNCLOSED for case in cases.values())
    assert EXIT_UNCLOSED not in {order.exit_reason for order in sells}
    checked = 0
    for buy, sell in _round_trips(run):
        case = cases[(buy.entity_id, buy.trade_date)]
        assert case.exit_reason == sell.exit_reason
        assert case.exit_date == sell.trade_date
        assert case.exit_price == pytest.approx(sell.price, rel=1e-12)
        checked += 1
    assert checked > 10

    # (c) 出場原因的名住引擎,策略層只是轉引——不是另一份同名的抄本
    from karst.engine import rules as engine_rules

    for name in ("EXIT_STOP", "EXIT_TARGET", "EXIT_UNCLOSED", "EXIT_REASONS"):
        assert getattr(trend_swing, name) is getattr(engine_rules, name)

    # (d) 策略層再無第二份出場規約:它連高低價都不再讀
    #     (判「今日有沒有穿止蝕/觸目標」非讀高低價不可,讀不到就抄不了)
    tree = ast.parse(TREND_SWING_SOURCE.read_text(encoding="utf-8"))
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not ({"high", "low"} & attributes)
    assigned = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    } | {
        node.target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert not ({"EXIT_STOP", "EXIT_TARGET", "EXIT_UNCLOSED", "EXIT_REASONS"} & assigned)


# ======================================================================
# 驗收條件 2:逐日注碼基數與逐日熔斷狀態經運行留痕落痕並讀得回,
#             運行編號不因此改變定義
# ======================================================================
def test_the_two_audit_series_are_recorded_and_read_back(runs, run):
    store, snapshot_id = runs

    # (a) 先錄一次「交不出查帳序列」的同一次運行,拿住它的編號
    bare = _record(runs, _WithoutAuditSeries(run))
    assert store.audit_kinds(bare.run_id) == ()
    with pytest.raises(NotFound):
        store.sizing_basis(bare.run_id)

    # (b) 同一次運行連查帳序列再錄一次:編號一個字都沒有變
    record = _record(runs, run)
    assert record.run_id == bare.run_id
    assert store.list_runs(STRATEGY) == [record]
    # 運行編號的定義仍然是那五件,序列種類仍然是那三條——多存兩條不入編號
    assert RUN_ARTIFACT_KINDS == ("equity", "holdings", "orders")
    assert set(record.artifacts) == set(RUN_ARTIFACT_KINDS)
    assert (record.strategy_version_no, record.param_set_name) == (1, PARAM_SET)
    assert record.snapshot_id == snapshot_id

    # (c) 兩條都讀得回,而且與引擎交回來那一份逐格對得上
    assert store.audit_kinds(record.run_id) == AUDIT_SERIES_KINDS == (
        "sizing_basis", "breaker_blocked"
    )
    basis = store.sizing_basis(record.run_id)
    blocked = store.breaker_blocked(record.run_id)
    assert len(basis) == len(blocked) == record.trading_days
    pd.testing.assert_index_equal(basis.index, run.equity_curve.index, check_names=False)
    assert np.array_equal(basis.to_numpy(), run.sizing_basis.to_numpy())
    assert np.array_equal(blocked.to_numpy(), run.breaker_blocked.to_numpy())
    assert blocked.dtype == np.dtype(bool)
    assert int(blocked.sum()) == run.blocked_days > 0
    assert basis.min() < run.params.initial_cash < basis.max()   # 基數真的在動

    # (d) 落檔之後核對得到:三條序列與兩條查帳序列都與落痕那一刻一字不差
    assert store.verify_run(record.run_id) == ()
    assert store.verify_audit_series(record.run_id) == ()

    # (e) 查帳序列一樣不可改寫:同一次運行、不同內容即拒收
    with pytest.raises(ImmutabilityViolation):
        store.record_run(
            strategy_name=STRATEGY,
            param_set_name=PARAM_SET,
            snapshot_id=snapshot_id,
            engine_name=run.engine_name,
            engine_version=ENGINE_VERSION,
            equity_curve=run.equity_curve,
            holdings=run.holdings,
            orders=run.orders,
            origin=FORMAL_RUN,
            audit_series={"sizing_basis": run.sizing_basis * 2.0},
        )


# ======================================================================
# 驗收條件 3:K 線面板浮點尾數由引擎層壓回,越界拋錯;策略層對應程式碼移除
# ======================================================================
def test_float_tails_are_squeezed_back_at_the_engine_door():
    dates = pd.bdate_range("2024-01-02", periods=6)
    entity_ids = [11, 22]
    close = np.array(
        [[100.0, 200.0], [101.0, 199.0], [103.0, 201.0],
         [102.0, 205.0], [106.0, 204.0], [108.0, 209.0]]
    )
    open_ = close * 0.99
    high = np.maximum(open_, close)
    low = np.minimum(open_, close)

    frame = lambda values: pd.DataFrame(values, index=dates, columns=entity_ids)  # noqa: E731

    # (a) 最後一個 bit 的尾數:最高價低過收價一個 ulp、最低價高過開價一個 ulp,
    #     兩邊都壓回包絡線,不拋錯(這正是真實已調整價的情況)
    tail_high = high.copy()
    tail_low = low.copy()
    tail_high[2, 0] = np.nextafter(close[2, 0], 0.0)
    tail_low[3, 1] = np.nextafter(open_[3, 1], np.inf)
    assert tail_high[2, 0] < close[2, 0] and tail_low[3, 1] > open_[3, 1]

    panel = BarPanel.from_frames(
        open=frame(open_), high=frame(tail_high), low=frame(tail_low), close=frame(close)
    )
    assert panel.high.to_numpy()[2, 0] == close[2, 0]
    assert panel.low.to_numpy()[3, 1] == open_[3, 1]
    assert np.array_equal(panel.open.to_numpy(), open_)      # 開收價一格不動
    assert np.array_equal(panel.close.to_numpy(), close)

    # (b) 越界超過容差:當場拋錯,不會把一根真的壞 K 線靜靜修好
    broken_high = high.copy()
    broken_high[2, 0] = close[2, 0] * (1.0 - 1e-6)
    with pytest.raises(ContractViolation, match="容差"):
        BarPanel.from_frames(
            open=frame(open_), high=frame(broken_high), low=frame(low), close=frame(close)
        )
    # 容差寫得明,亦調得動:講明收得到 1e-5 就收得到
    widened = BarPanel.from_frames(
        open=frame(open_), high=frame(broken_high), low=frame(low),
        close=frame(close), tolerance=1e-5,
    )
    assert widened.high.to_numpy()[2, 0] == close[2, 0]

    # (c) 容差住引擎,策略層那份壓回碼已經移除,只是把容差傳過去
    from karst.engine import rules as engine_rules

    assert trend_swing.BAR_CONSISTENCY_TOLERANCE is engine_rules.BAR_CONSISTENCY_TOLERANCE
    assert BAR_CONSISTENCY_TOLERANCE == 1e-9
    assert not hasattr(trend_swing, "_coerce_bar_consistency")
    tree = ast.parse(TREND_SWING_SOURCE.read_text(encoding="utf-8"))
    functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "_coerce_bar_consistency" not in functions


# ======================================================================
# 驗收條件 4:既有測試照過,示例運行編號與成績不變
#             (真實那次由 experiments/2026-08-28-trend-swing-real/run_backtest.py 證;
#              這裡守住同一件事的機制:同一個面板 × 同一組參數重跑,一字不差)
# ======================================================================
def test_rerunning_the_same_inputs_changes_nothing(panel, run, runs):
    store, _ = runs
    again = run_rule_strategy(panel=panel, params=_params())

    # (a) 成績一字不差:淨值逐格相等,不是「約等於」
    assert np.array_equal(again.equity_curve.to_numpy(), run.equity_curve.to_numpy())
    assert again.total_return == run.total_return
    assert again.max_drawdown == run.max_drawdown
    assert again.worst_month_drawdown == run.worst_month_drawdown
    assert again.blocked_days == run.blocked_days
    assert again.entry_signals == run.entry_signals

    # (b) 逐筆成交連出場原因都一樣
    assert len(again.orders) == len(run.orders) > 0
    for theirs, ours in zip(again.orders, run.orders, strict=True):
        assert theirs == ours

    # (c) 兩條查帳序列亦一字不差
    assert np.array_equal(again.sizing_basis.to_numpy(), run.sizing_basis.to_numpy())
    assert np.array_equal(again.breaker_blocked.to_numpy(), run.breaker_blocked.to_numpy())

    # (d) 落痕兩次:同一個運行編號,重錄不會多一筆,核對全對
    first = _record(runs, run)
    second = _record(runs, again)
    assert first.run_id == second.run_id
    assert [record.run_id for record in store.list_runs(STRATEGY)] == [first.run_id]
    assert store.verify_run(first.run_id) == ()
    assert store.verify_audit_series(first.run_id) == ()
