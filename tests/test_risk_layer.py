"""KARST-025 驗收:共用風控層——單筆風險、月度熔斷、賠率門檻抽成一層。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。
玩具數據:合成 K 線與合成因子,固定種子,不連外部數據;資料庫一律經
``karst/store.py`` 的 API 開(D-027 第 4 條護欄二)。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_risk_layer.py -q``
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from karst import DefinitionStore, FormulaProcedure
from karst.engine import (
    BacktestResult,
    BarPanel,
    BreakoutEntry,
    MonthlyLossBreaker,
    PricePanel,
    SwingLowStop,
    run_ranking_rebalance,
    run_rule_strategy,
)
from karst.errors import ContractViolation
from karst.risk import (
    RISK_RULES,
    RiskRuleNotReferenced,
    RiskSettings,
    build_rule_params,
    read_risk_settings,
    reference_risk_rules,
    referenced_rule_keys,
    register_risk_layer,
    risk_settings_of,
    sweep_grid,
    sweep_risk_settings,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SEED = 20260828
ROWS, COLUMNS = 320, 24
INITIAL_CASH = 1_000_000.0

# 策略自己那幾格(不屬共用風控層):入場突破、止蝕波段、持倉上限、注碼基數取誰。
ENTRY = BreakoutEntry(lookback_days=30)
STOP = SwingLowStop(lookback_days=10, min_stop_fraction=0.01, max_stop_fraction=0.25)
MAX_POSITION = 0.25

FACTOR = "動量·玩具 12-1 月"
PROCEDURE = FormulaProcedure(
    formula="close[-21] / close[-252] - 1",
    input_data_version="2026-08-28-toy000000000",
)
RANKING_DATES = pd.bdate_range("2026-01-02", periods=90)


def _params(risk: RiskSettings):
    """把風控取值餵入引擎那五件既有規則型別。三個風控數只有這一條路進得了引擎。"""
    return build_rule_params(
        risk=risk,
        entry=ENTRY,
        stop=STOP,
        max_position_fraction=MAX_POSITION,
        equity_basis="current_equity",
        initial_cash=INITIAL_CASH,
        fees=0.0,
        tie_break_seed=SEED,
    )


@pytest.fixture(scope="module")
def panel() -> BarPanel:
    """玩具 K 線面板:分段趨勢 + 一個全市場共同因子(好令壞月份成群出現)。"""
    generator = np.random.default_rng(SEED)
    dates = pd.bdate_range("2024-01-02", periods=ROWS)
    entity_ids = list(range(801, 801 + COLUMNS))

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
def store(tmp_path):
    with DefinitionStore.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


@pytest.fixture()
def toy_factor(store):
    """一個玩具因子:策略要引用最少一個因子才登記得到。"""
    entity_ids = [
        store.register_entity(
            kind="company", display_name=f"Toy {index} Inc.", cik=str(950000 + index)
        )
        for index in range(5)
    ]
    store.register_factor(FACTOR, scale_kind="cardinal", procedure=PROCEDURE)
    half = len(RANKING_DATES) // 2
    rows = []
    for position, day in enumerate(RANKING_DATES):
        stamp = day.strftime("%Y-%m-%d")
        high_first = position < half
        for rank, entity_id in enumerate(entity_ids):
            score = len(entity_ids) - rank if high_first else rank + 1
            rows.append(
                {
                    "entity_id": entity_id,
                    "event_time": stamp,
                    "knowledge_time": stamp,
                    "value": float(score),
                }
            )
    store.write_factor_values(FACTOR, rows)
    return entity_ids


# 驗收條件 1:三類風控規則各自只有一個定義正本,庫內查不到第二份影像
# (D-013 第 4 條、D-002 第 4 條)
def test_each_risk_rule_has_exactly_one_definition(store):
    # (a) 程式那一邊:三條規則,一條不多一條不少,名與參數名皆不重覆
    assert list(RISK_RULES) == ["per_trade_risk", "monthly_loss_cap", "reward_risk_floor"]
    names = [rule.name for rule in RISK_RULES.values()]
    param_keys = [rule.param_key for rule in RISK_RULES.values()]
    assert names == ["單筆風險上限", "月度虧損熔斷", "賠率門檻"]
    assert len(set(names)) == len(set(param_keys)) == 3

    # (b) 落庫:重覆登記回同一批列,不會生出第二份影像
    first = register_risk_layer(store)
    again = register_risk_layer(store)
    assert [r.risk_rule_id for r in first] == [r.risk_rule_id for r in again]
    assert len(store.list_risk_rules()) == 3
    assert [record.key for record in first] == list(RISK_RULES)

    # (c) 全庫掃名:每條規則的名一字不差地只出現在一處
    for record in first:
        assert store.find_name_occurrences(record.name) == ["risk_rule.name(1 列)"]

    # (d) 取值不在規則那一邊:登記列只有「這條規則是什麼」,沒有一個數
    assert not any(
        re.search(r"\d", f"{record.key}{record.param_key}") for record in first
    )

    # (e) 落庫之後改不得——連直接改庫都擋(單一正本)
    with pytest.raises(sqlite3.IntegrityError):
        store._conn.execute(
            "UPDATE risk_rule SET name = '別的名' WHERE risk_rule_id = ?",
            (first[0].risk_rule_id,),
        )


# 驗收條件 2:兩套策略同時引用同一份定義而各設不同參數,改一邊參數不影響另一邊
# (D-013 第 4 條)
def test_two_strategies_share_one_definition_with_their_own_params(store, toy_factor):
    register_risk_layer(store)
    store.register_strategy("趨勢波段·玩具", strategy_type="technical", factor_refs=[FACTOR])
    store.register_strategy("錯殺·玩具", strategy_type="meanrev", factor_refs=[FACTOR])

    # 甲三條全用;乙不用熔斷——同一層規則,可用可不用
    swing = RiskSettings(per_trade_risk=0.02, monthly_loss_cap=0.06, reward_risk_floor=1.5)
    oversold = RiskSettings(per_trade_risk=0.01, monthly_loss_cap=None, reward_risk_floor=2.5)

    swing_refs = reference_risk_rules(store, "趨勢波段·玩具", swing)
    oversold_refs = reference_risk_rules(store, "錯殺·玩具", oversold)
    assert [r.key for r in swing_refs] == ["per_trade_risk", "monthly_loss_cap", "reward_risk_floor"]
    assert [r.key for r in oversold_refs] == ["per_trade_risk", "reward_risk_floor"]

    # 兩套策略指住的是**同一列**定義,不是各自一份影像
    shared = {r.key: r.risk_rule_id for r in swing_refs}
    assert all(shared[r.key] == r.risk_rule_id for r in oversold_refs)
    assert len(store.list_risk_rules()) == 3

    # 取值各自住在自己的參數集裡(參數集另有自己的參數,風控那幾格帶 risk. 字首)
    for name, risk, cadence in (
        ("趨勢波段·玩具", swing, "daily"),
        ("錯殺·玩具", oversold, "daily"),
    ):
        store.register_param_set(
            name,
            param_set_name="基準",
            rebalance_cadence=cadence,
            values={**risk.to_param_values(), "entry.lookback_days": "30"},
        )
    assert risk_settings_of(store, "趨勢波段·玩具", "基準") == swing
    assert risk_settings_of(store, "錯殺·玩具", "基準") == oversold

    # 改甲的參數(參數集出新版):乙一個字都不變,規則定義亦一列不變
    tightened = RiskSettings(per_trade_risk=0.005, monthly_loss_cap=0.03, reward_risk_floor=1.5)
    store.register_param_set(
        "趨勢波段·玩具",
        param_set_name="基準",
        rebalance_cadence="daily",
        values={**tightened.to_param_values(), "entry.lookback_days": "30"},
    )
    assert risk_settings_of(store, "趨勢波段·玩具", "基準") == tightened
    assert risk_settings_of(store, "錯殺·玩具", "基準") == oversold
    assert risk_settings_of(store, "趨勢波段·玩具", "基準", set_version_no=1) == swing
    assert len(store.list_risk_rules()) == 3
    assert referenced_rule_keys(store, "錯殺·玩具") == ("per_trade_risk", "reward_risk_floor")

    # 餵入引擎:同一份定義,兩套策略各自的取值,互不相干
    swing_params = _params(tightened)
    oversold_params = _params(oversold)
    assert swing_params.sizing.risk_per_trade == 0.005
    assert oversold_params.sizing.risk_per_trade == 0.01
    assert swing_params.breaker == MonthlyLossBreaker(max_monthly_drawdown=0.03)
    assert oversold_params.breaker is None          # 不引用即明寫關掉,不是預設 0
    assert oversold_params.target.min_reward_risk == 2.5
    assert read_risk_settings(swing_params) == tightened

    # 參數無預設值:不引用而又走規則路徑,當場拋錯,不會有一個數頂上去
    with pytest.raises(RiskRuleNotReferenced, match="賠率門檻"):
        _params(RiskSettings(per_trade_risk=0.02, monthly_loss_cap=0.06, reward_risk_floor=None))
    with pytest.raises(ContractViolation):
        RiskSettings(per_trade_risk=1.5, monthly_loss_cap=None, reward_risk_floor=1.0)


# 驗收條件 3:策略完全不引用風控層照樣跑得出回測,不引用不報錯
# (D-013 第 4 條「策略可用可不用」)
def test_a_strategy_that_references_nothing_still_backtests(store, toy_factor):
    register_risk_layer(store)
    store.register_strategy("因子混合·玩具", strategy_type="multifactor", factor_refs=[FACTOR])

    # 一條風控規則都沒有引用——不是錯,只是這套策略不用這一層
    assert store.strategy_risk_rules("因子混合·玩具") == []
    assert referenced_rule_keys(store, "因子混合·玩具") == ()

    # 目標比重路徑(適配層 A)本來就無風控:照樣跑得出一次完整回測
    generator = np.random.default_rng(SEED)
    steps = generator.normal(0.0004, 0.01, (len(RANKING_DATES), len(toy_factor)))
    close = pd.DataFrame(
        100.0 * np.exp(np.cumsum(steps, axis=0)), index=RANKING_DATES, columns=toy_factor
    )
    open_prices = close.shift(1)
    open_prices.iloc[0] = 100.0
    price_panel = PricePanel.from_frames(open=open_prices * 1.002, close=close)

    result = run_ranking_rebalance(
        store=store,
        panel=price_panel,
        factor_name=FACTOR,
        cadence="monthly",
        top_n=2,
        direction="high",
    )
    assert isinstance(result, BacktestResult)
    assert result.equity_curve.notna().all()
    assert np.isfinite(result.total_return)
    assert len(result.orders) > 0

    # 不引用是**結構上**不引用:目標比重那條路一個檔都不認得風控層
    for name in ("runner.py", "contracts.py", "selection.py", "cadence.py"):
        source = (REPO_ROOT / "karst" / "engine" / name).read_text(encoding="utf-8")
        assert not re.search(r"^\s*(?:import|from).*\brisk\b", source, re.M), name


# 驗收條件 4:三類規則的參數皆可掃描,交得出一次多組參數掃描的結果(D-008)
def test_all_three_risk_params_can_be_swept(panel):
    base = _params(RiskSettings(per_trade_risk=0.06, monthly_loss_cap=0.05, reward_risk_floor=1.0))
    grid = sweep_grid(
        per_trade_risk=[0.03, 0.06],
        monthly_loss_cap=[None, 0.05],       # None 那一格 = 這組不引用熔斷
        reward_risk_floor=[1.0, 1.5],
    )
    assert grid.combinations == 8

    result = sweep_risk_settings(panel=panel, params=base, grid=grid)
    frame = result.frame()
    assert len(result) == len(frame) == 8
    assert frame.shape[1] == 9
    assert len({cell.settings for cell in result.cells}) == 8

    # 三條規則各自都真的咬得住:
    # 賠率門檻 → 入場訊號張數;熔斷 → 落閘日數;單筆風險 → 注碼(訂單張數)
    by_floor = frame.groupby("reward_risk_floor")["entry_signals"].nunique()
    assert (by_floor == 1).all()                                    # 同一門檻,訊號張數一致
    assert frame.loc[frame.reward_risk_floor == 1.0, "entry_signals"].iloc[0] > (
        frame.loc[frame.reward_risk_floor == 1.5, "entry_signals"].iloc[0]
    )
    assert (frame.loc[frame.monthly_loss_cap.isna(), "blocked_days"] == 0).all()
    assert (frame.loc[frame.monthly_loss_cap.notna(), "blocked_days"] > 0).all()
    same_but_risk = frame[(frame.reward_risk_floor == 1.0) & frame.monthly_loss_cap.isna()]
    assert same_but_risk["orders"].nunique() == 2

    # 每一格都是一次真回測,成績各不相同;掃描本身不替用戶揀「最優」
    assert frame["total_return"].notna().all()
    assert frame["total_return"].nunique() == 8
    assert result.engine_name == "vectorbt-order-func"
    assert not hasattr(result, "best")

    # 同一組取值重跑一字不差(固定種子;掃描次序亦固定)
    again = sweep_risk_settings(panel=panel, params=base, grid=grid)
    pd.testing.assert_frame_equal(frame, again.frame())

    # 掃描取值一律明寫,沒有預設值;規則路徑要的那兩條不准掃 None
    with pytest.raises(ContractViolation, match="一個都沒有"):
        sweep_grid(per_trade_risk=[], monthly_loss_cap=[None], reward_risk_floor=[1.0])
    with pytest.raises(ContractViolation, match="不可以掃 None"):
        sweep_grid(per_trade_risk=[0.02], monthly_loss_cap=[None], reward_risk_floor=[None])


def test_sweep_moves_only_the_three_risk_numbers(panel):
    """掃描格與格之間只差三個風控數:其餘參數一字不動,差異賴不到別處。"""
    base = _params(RiskSettings(per_trade_risk=0.06, monthly_loss_cap=0.05, reward_risk_floor=1.0))
    swapped = RiskSettings(
        per_trade_risk=0.03, monthly_loss_cap=None, reward_risk_floor=1.5
    ).apply(base)

    assert swapped.entry == base.entry == ENTRY
    assert swapped.stop == base.stop == STOP
    assert swapped.sizing.max_position_fraction == base.sizing.max_position_fraction
    assert swapped.sizing.equity_basis == base.sizing.equity_basis == "current_equity"
    assert (swapped.initial_cash, swapped.fees, swapped.tie_break_seed) == (
        base.initial_cash,
        base.fees,
        base.tie_break_seed,
    )
    assert read_risk_settings(base) != read_risk_settings(swapped)

    # 換走三個數之後照樣跑得出一次回測
    result = run_rule_strategy(panel=panel, params=swapped)
    assert result.blocked_days == 0
    assert np.isfinite(result.total_return)
