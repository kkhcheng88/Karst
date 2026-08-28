"""KARST-026 驗收:回測運行留痕。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。
"""

from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from karst import DefinitionStore, FormulaProcedure, ImmutabilityViolation
from karst.runs import RunStore, synthetic_simulation
from karst.store import FORMAL_RUN, SWEEP_RUN

MOMENTUM = "動量·12-1 月"
MOMENTUM_PROCEDURE = FormulaProcedure(
    formula="close[-21] / close[-252] - 1",
    input_data_version="2026-08-27-a1b2c3d4e5f6",
)
STRATEGY = "趨勢波段"
PARAM_SET = "現役"
PERIOD_START = "2020-01-01"
PERIOD_END = "2026-06-30"
ENGINE = ("vectorbt-adapter", "0.1.0")


@pytest.fixture()
def store(tmp_path):
    with DefinitionStore.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


@pytest.fixture()
def entities(store):
    return tuple(
        store.register_entity(kind="company", display_name=name, cik=cik)
        for name, cik in (("Apple Inc.", "320193"), ("Microsoft Corp.", "789019"))
    )


@pytest.fixture()
def snapshot_id(store):
    return store.register_snapshot(
        source="yfinance", taken_on="2026-06-30", content_hash="a1b2c3d4e5f67890"
    )


@pytest.fixture()
def strategy(store, entities):
    store.register_factor(MOMENTUM, scale_kind="cardinal", procedure=MOMENTUM_PROCEDURE)
    version = store.register_strategy(
        STRATEGY, strategy_type="technical", factor_refs=[MOMENTUM]
    )
    store.register_param_set(
        STRATEGY,
        param_set_name=PARAM_SET,
        rebalance_cadence="monthly",
        values={"top_n": "10", "direction": "high"},
    )
    return version


@pytest.fixture()
def runs(store, tmp_path):
    return RunStore(store, root=tmp_path / "runs")


def _simulation(entities, seed=7):
    return synthetic_simulation(
        start=PERIOD_START, end=PERIOD_END, entity_ids=entities, seed=seed
    )


def _record(runs, entities, snapshot_id, *, seed=7, **overrides):
    fields = {
        "strategy_name": STRATEGY,
        "param_set_name": PARAM_SET,
        "snapshot_id": snapshot_id,
        "engine_name": ENGINE[0],
        "engine_version": ENGINE[1],
        "origin": FORMAL_RUN,
    }
    fields.update(overrides)
    return runs.record_simulation(_simulation(entities, seed), **fields)


# 驗收條件 1:同一組策略版本 × 參數集 × 期間 × 數據快照,兩次運行得同一個唯一名(規格 7.4)
def test_same_inputs_give_the_same_run_id(runs, strategy, entities, snapshot_id):
    first = _record(runs, entities, snapshot_id)
    second = _record(runs, entities, snapshot_id)

    assert first.run_id == second.run_id
    assert first.run_id.startswith("run-")
    # 重錄同一次運行不會多一筆:留痕是同一件事的同一個名
    assert [r.run_id for r in runs.list_runs(STRATEGY)] == [first.run_id]
    # 五件都蓋住了
    assert first.strategy_version_no == 1
    assert first.param_set_name == PARAM_SET
    assert (first.period_start, first.period_end) == (PERIOD_START, PERIOD_END)
    assert first.snapshot_id == snapshot_id
    assert (first.engine_name, first.engine_version) == ENGINE
    # 三條序列與登記的雜湊一字不差
    assert runs.verify_run(first.run_id) == ()

    # 改期間即另一次運行,另一個編號
    other = runs.record_simulation(
        synthetic_simulation(
            start=PERIOD_START, end="2025-06-30", entity_ids=entities, seed=7
        ),
        strategy_name=STRATEGY,
        param_set_name=PARAM_SET,
        snapshot_id=snapshot_id,
        engine_name=ENGINE[0],
        engine_version=ENGINE[1],
        origin=FORMAL_RUN,
    )
    assert other.run_id != first.run_id


# 驗收條件 2:逐日淨值與逐日持倉保存得住,讀得回任何一日的淨值與當日持倉(規格 7.4)
def test_daily_equity_and_holdings_read_back(runs, strategy, entities, snapshot_id):
    record = _record(runs, entities, snapshot_id)
    simulation = _simulation(entities)

    equity = runs.equity_curve(record.run_id)
    assert len(equity) == record.trading_days == len(simulation.equity_curve)
    assert equity.iloc[0] == pytest.approx(float(simulation.equity_curve.iloc[0]))

    some_day = equity.index[len(equity) // 2]
    assert runs.equity_on(record.run_id, some_day) == pytest.approx(
        float(equity.loc[some_day])
    )
    assert set(runs.holdings_on(record.run_id, some_day)) == set(entities)

    orders = runs.orders(record.run_id)
    assert set(orders["side"]) == {"buy", "sell"}
    assert len(orders) == 2 * len(entities)


# 驗收條件 3:由已保存的逐日序列,不重跑就算得出任一子期間,基準由起始日重設(規格 8.5)
def test_window_recomputes_any_subperiod_without_a_rerun(runs, strategy, entities, snapshot_id):
    record = _record(runs, entities, snapshot_id)
    equity = runs.equity_curve(record.run_id)
    middle = str(equity.index[len(equity) // 2].date())

    whole = runs.window_stats(record.run_id)
    early = runs.window_stats(record.run_id, whole.start, middle)
    late = runs.window_stats(record.run_id, middle, whole.end)

    # 每段的基準都由該段起始日重設為 100
    assert early.equity.iloc[0] == pytest.approx(100.0)
    assert late.equity.iloc[0] == pytest.approx(100.0)
    assert late.start == middle

    # 兩段接起來與全期一模一樣
    assert (1 + early.total_return) * (1 + late.total_return) == pytest.approx(
        1 + whole.total_return
    )
    assert whole.total_return == pytest.approx(
        float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    )
    # 全期的回撤至少與任何一段一樣深
    assert whole.max_drawdown <= min(early.max_drawdown, late.max_drawdown) + 1e-12
    assert whole.annual_return == pytest.approx(
        (1 + whole.total_return) ** (252.0 / (whole.trading_days - 1)) - 1.0
    )

    # 重看不重跑:運行本身一個字都沒變
    assert runs.verify_run(record.run_id) == ()


# 驗收條件 4:因子或策略出新版之後,舊運行內容一字不變、只被標為過時(D-020 第 7 條、規格 7.3)
def test_new_version_marks_the_old_run_stale_without_touching_it(
    runs, store, strategy, entities, snapshot_id
):
    record = _record(runs, entities, snapshot_id)
    before = runs.equity_curve(record.run_id)
    assert runs.is_stale(record.run_id) is False

    store.new_factor_version(
        MOMENTUM,
        scale_kind="cardinal",
        procedure=FormulaProcedure(
            formula="close[-21] / close[-126] - 1",
            input_data_version="2026-08-27-a1b2c3d4e5f6",
        ),
    )
    assert runs.is_stale(record.run_id) is True
    assert any("因子" in reason for reason in runs.stale_reasons(record.run_id))

    store.new_strategy_version(STRATEGY, factor_refs=[f"{MOMENTUM}@2"])
    assert any("策略" in reason for reason in runs.stale_reasons(record.run_id))

    # 舊運行一字不變:蓋住的仍然是第 1 版,序列與雜湊全部原封不動
    again = store.get_run(record.run_id)
    assert again.strategy_version_no == 1
    assert [f.version_no for f in again.factors] == [1]
    assert again.artifacts["equity"].content_hash == record.artifacts["equity"].content_hash
    pd.testing.assert_series_equal(runs.equity_curve(record.run_id), before)
    assert runs.verify_run(record.run_id) == ()


# 驗收條件 4(另一面):運行不可改寫
def test_recording_different_results_under_the_same_identity_is_refused(
    runs, store, strategy, entities, snapshot_id
):
    record = _record(runs, entities, snapshot_id, seed=7)

    # 同一組身份、不同結果 = 有一件沒有蓋住,當場拒收
    with pytest.raises(ImmutabilityViolation):
        _record(runs, entities, snapshot_id, seed=99)

    # 繞過本層直接改庫一樣擋
    with pytest.raises(sqlite3.IntegrityError):
        store.connection.execute(
            "UPDATE backtest_run SET engine_version = '9.9.9' WHERE run_id = ?",
            (record.run_id,),
        )
    with pytest.raises(sqlite3.IntegrityError):
        store.connection.execute(
            "DELETE FROM run_artifact WHERE run_id = ?", (record.run_id,)
        )
