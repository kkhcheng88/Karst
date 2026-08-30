"""KARST-023 驗收:引擎適配層 A,排名再平衡路徑。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。
玩具數據:合成價格與合成因子,固定種子,不連外部數據。
"""

from __future__ import annotations

import ast
import inspect
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from karst import ContractViolation, DefinitionStore, FormulaProcedure
from karst.engine import (
    CADENCES,
    BacktestResult,
    CadenceNotSpecified,
    Order,
    PortfolioEngine,
    PricePanel,
    RankingRebalanceParams,
    SimulationOutput,
    run_ranking_rebalance,
)

from doubles.engines import RecordingEngine

REPO_ROOT = Path(__file__).resolve().parents[1]

FACTOR = "動量·玩具 12-1 月"
PROCEDURE = FormulaProcedure(
    formula="close[-21] / close[-252] - 1",
    input_data_version="2026-08-27-toy000000000",
)

DATES = pd.bdate_range("2026-01-02", periods=90)


@pytest.fixture()
def store(tmp_path):
    with DefinitionStore.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


@pytest.fixture()
def entity_ids(store):
    return [
        store.register_entity(
            kind="company", display_name=f"Toy {index} Inc.", cik=str(900000 + index)
        )
        for index in range(5)
    ]


@pytest.fixture()
def panel(entity_ids):
    """玩具價格面板。開價刻意與同日收價、與前一日開價都不同,好證得到成交取哪一個。"""
    generator = np.random.default_rng(20260827)
    steps = generator.normal(0.0004, 0.01, (len(DATES), len(entity_ids)))
    close = pd.DataFrame(
        100.0 * np.exp(np.cumsum(steps, axis=0)), index=DATES, columns=entity_ids
    )
    open_prices = close.shift(1)
    open_prices.iloc[0] = 100.0
    return PricePanel.from_frames(open=open_prices * 1.002, close=close)


@pytest.fixture()
def toy_factor(store, entity_ids):
    """玩具因子:前半期由頭到尾遞減,後半期倒轉。換倉時排名一定會翻,揀得出買賣。"""
    version = store.register_factor(FACTOR, scale_kind="cardinal", procedure=PROCEDURE)
    half = len(DATES) // 2
    rows = []
    for position, day in enumerate(DATES):
        stamp = day.strftime("%Y-%m-%d")
        # 可執行時點 = 下一根 K 線;最後一根之後沒有下一根,留空(D-021 第 3 條)
        next_stamp = (
            DATES[position + 1].strftime("%Y-%m-%d") if position + 1 < len(DATES) else None
        )
        high_first = position < half
        for rank, entity_id in enumerate(entity_ids):
            score = len(entity_ids) - rank if high_first else rank + 1
            rows.append(
                {
                    "entity_id": entity_id,
                    "event_time": stamp,
                    "knowledge_time": stamp,
                    "executable_time": next_stamp,
                    "value": float(score),
                }
            )
    store.write_factor_values(FACTOR, rows)
    return version


# 驗收條件 1:用一個玩具因子跑得出一次完整回測,交得出逐日淨值(規格 6.3、A-001)
def test_toy_factor_runs_a_full_backtest_with_a_daily_equity_curve(store, panel, toy_factor):
    result = run_ranking_rebalance(
        store=store,
        panel=panel,
        factor_name=FACTOR,
        cadence="monthly",
        top_n=2,
        direction="high",
    )

    assert isinstance(result, BacktestResult)

    # 逐日淨值:每一根 K 線一個數,無缺口,由起始本金起步
    assert isinstance(result.equity_curve, pd.Series)
    assert list(result.equity_curve.index) == list(panel.dates)
    assert result.equity_curve.notna().all()
    assert result.equity_curve.iloc[0] == pytest.approx(result.params.initial_cash)
    assert np.isfinite(result.total_return)

    # 逐日持倉:日期 × 實體編號
    assert result.holdings.shape == (len(panel.dates), len(panel.entity_ids))
    assert list(result.holdings.columns) == list(panel.entity_ids)

    # 逐筆訂單
    assert len(result.orders) > 0
    assert all(isinstance(order, Order) for order in result.orders)
    orders = result.orders_frame()
    assert set(orders["side"]) <= {"buy", "sell"}
    assert (orders["shares"] > 0).all()

    # 每次換倉等權選 2 隻,而且真的換過手(前半期揀頭兩隻,後半期倒轉)
    assert len(result.rebalances) >= 3
    assert all(len(rebalance.selected) == 2 for rebalance in result.rebalances)
    assert all(rebalance.weight == pytest.approx(0.5) for rebalance in result.rebalances)
    assert result.rebalances[0].selected != result.rebalances[-1].selected

    # 追溯得回因子的哪一版跑出這次成績(D-021 第 8 條)
    assert result.factor_version_id == toy_factor.factor_version_id
    assert result.engine_name == "vectorbt"


# 驗收條件 2:合約層與資料層無任何第三方引擎型別,換引擎時策略與因子定義不用改(D-007 第 3 條)
def test_engine_stays_behind_our_own_interface(store, panel, toy_factor):
    # (a) 全個 karst/ 與 tests/ 裡面,只有適配器一個檔認得 vectorbt
    adapter = REPO_ROOT / "karst" / "engine" / "vectorbt_engine.py"
    importers = sorted(
        path
        for folder in ("karst", "tests")
        for path in (REPO_ROOT / folder).rglob("*.py")
        if re.search(r"^\s*(?:import|from)\s+vectorbt\b", path.read_text(encoding="utf-8"), re.M)
    )
    assert importers == [adapter]

    # (b) 資料層根本不需要引擎:import karst 之後,引擎連載都未載
    probe = subprocess.run(
        [sys.executable, "-c", "import sys, karst; print('vectorbt' in sys.modules)"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    assert probe.stdout.strip() == "False"

    # (c) 交出來的結果全部是 Karst 自己的型別,一個第三方型別都沒有漏出來
    result = run_ranking_rebalance(
        store=store,
        panel=panel,
        factor_name=FACTOR,
        cadence="monthly",
        top_n=2,
        direction="high",
    )
    leaked = [
        type(value).__module__
        for value in (
            result.equity_curve,
            result.holdings,
            result.params,
            *result.orders,
            *result.rebalances,
        )
        if type(value).__module__.split(".")[0] not in {"karst", "pandas", "builtins"}
    ]
    assert leaked == []

    # (d) 整件換走引擎:策略定義(選股邏輯)與因子定義一個字都不用改
    fake = RecordingEngine(name="fake", drift=0.0)
    assert isinstance(fake, PortfolioEngine)
    swapped = run_ranking_rebalance(
        store=store,
        panel=panel,
        factor_name=FACTOR,
        cadence="monthly",
        top_n=2,
        direction="high",
        engine=fake,
    )
    assert swapped.engine_name == "fake"
    assert swapped.rebalances == result.rebalances  # 揀中的股票與日子一模一樣
    assert fake.seen_targets is not None


# 驗收條件 3:換倉節奏必須由參數指定,不指定即報錯,程式內查不到任何預設節奏值(D-009 第 7 條)
def test_cadence_has_no_default_anywhere(store, panel, toy_factor):
    common = {"store": store, "panel": panel, "factor_name": FACTOR, "top_n": 2, "direction": "high"}

    # 不寫就跑不動——連呼叫都湊不齊
    with pytest.raises(TypeError, match="cadence"):
        run_ranking_rebalance(**common)

    # 寫 None 或空白,一樣當缺件拒收,不代用戶決定
    for empty in (None, "", "   "):
        with pytest.raises(CadenceNotSpecified):
            run_ranking_rebalance(cadence=empty, **common)

    # 亂寫一個節奏即報錯,不猜
    with pytest.raises(ContractViolation, match="換倉節奏"):
        run_ranking_rebalance(cadence="fortnightly", **common)

    # 簽名本身沒有預設值
    for target in (run_ranking_rebalance, RankingRebalanceParams):
        parameter = inspect.signature(target).parameters["cadence"]
        assert parameter.default is inspect.Parameter.empty

    # 適配層原始碼裡查不到任何預設節奏值(看語法樹,不看註解與說明文字)
    for path in (REPO_ROOT / "karst" / "engine").rglob("*.py"):
        assert _cadence_defaults(path) == [], path

    # 四種節奏都行得通,揀邊個由呼叫方話事
    for cadence in sorted(CADENCES):
        result = run_ranking_rebalance(cadence=cadence, **common)
        assert len(result.rebalances) >= 1
    # 節奏愈密,換倉次數愈多
    counts = {
        cadence: len(run_ranking_rebalance(cadence=cadence, **common).rebalances)
        for cadence in ("daily", "weekly", "monthly", "quarterly")
    }
    assert counts["daily"] > counts["weekly"] > counts["monthly"] > counts["quarterly"]


# 驗收條件 4:N 與排名方向皆為可掃描參數,改參數不用改碼(D-008)
def test_top_n_and_direction_are_scannable_parameters(store, panel, toy_factor, entity_ids):
    grid = [
        {"top_n": top_n, "direction": direction}
        for top_n in (1, 2, 3)
        for direction in ("high", "low")
    ]
    swept = {
        (combo["top_n"], combo["direction"]): run_ranking_rebalance(
            store=store,
            panel=panel,
            factor_name=FACTOR,
            cadence="monthly",
            **combo,
        )
        for combo in grid
    }

    assert len(swept) == 6
    for (top_n, _direction), result in swept.items():
        assert all(len(rebalance.selected) == top_n for rebalance in result.rebalances)
        assert all(
            rebalance.weight == pytest.approx(1.0 / top_n) for rebalance in result.rebalances
        )

    # 方向真的掉轉了。名單按排名排,第一個就是揀得最前那隻:
    # 前半期分數由頭遞減,取高分即頭兩隻(最高分行先),取低分即尾兩隻(最低分行先)。
    first_high = swept[(2, "high")].rebalances[0].selected
    first_low = swept[(2, "low")].rebalances[0].selected
    assert first_high == (entity_ids[0], entity_ids[1])
    assert first_low == (entity_ids[4], entity_ids[3])
    assert set(first_high).isdisjoint(first_low)

    # 六格參數跑出六條不同的淨值曲線
    finals = {round(float(result.equity_curve.iloc[-1]), 6) for result in swept.values()}
    assert len(finals) == 6


# D-021 第 3 條:可執行時點=知情時點之後的下一根可交易 K 線的**開價**
def test_selection_fills_at_the_next_bar_open(store):
    ids = [
        store.register_entity(kind="company", display_name=f"Bar {i} Inc.", cik=str(800000 + i))
        for i in range(3)
    ]
    dates = pd.bdate_range("2026-03-02", periods=6)  # 3 月 2、3、4、5、6、9 日
    close = pd.DataFrame(
        {ids[0]: [100.0, 101, 102, 103, 104, 105], ids[1]: [50.0] * 6, ids[2]: [20.0] * 6},
        index=dates,
    )
    open_prices = pd.DataFrame(
        {ids[0]: [90.0, 91, 92, 93, 94, 95], ids[1]: [45.0] * 6, ids[2]: [18.0] * 6},
        index=dates,
    )
    panel = PricePanel.from_frames(open=open_prices, close=close)

    # 這個因子只在 3 月 4 日才知道(知情時間),事件時間更早
    store.register_factor(FACTOR, scale_kind="cardinal", procedure=PROCEDURE)
    store.write_factor_values(
        FACTOR,
        [
            {"entity_id": ids[0], "event_time": "2026-02-27", "knowledge_time": "2026-03-04",
             "executable_time": "2026-03-05", "value": 3.0},
            {"entity_id": ids[1], "event_time": "2026-02-27", "knowledge_time": "2026-03-04",
             "executable_time": "2026-03-05", "value": 2.0},
            {"entity_id": ids[2], "event_time": "2026-02-27", "knowledge_time": "2026-03-04",
             "executable_time": "2026-03-05", "value": 1.0},
        ],
    )

    result = run_ranking_rebalance(
        store=store,
        panel=panel,
        factor_name=FACTOR,
        cadence="daily",
        top_n=1,
        direction="high",
    )

    # 3 月 4 日看見因子 → 3 月 5 日(下一根 K 線)成交,不是同日
    decided = [r for r in result.rebalances if r.decision_date == "2026-03-04"]
    assert len(decided) == 1
    assert decided[0].execution_date == "2026-03-05"
    assert decided[0].selected == (ids[0],)

    # 3 月 4 日之前不知道這個因子,那幾根 K 線一張單都不准有(否則就是前視)
    assert all(order.trade_date >= "2026-03-05" for order in result.orders)

    first = result.orders[0]
    assert first.trade_date == "2026-03-05"
    assert first.entity_id == ids[0]
    assert first.side == "buy"

    # 成交價正正是執行日那根 K 線的開價
    assert first.price == pytest.approx(93.0)
    assert first.price == pytest.approx(float(panel.open.loc[dates[3], ids[0]]))
    # 既不是執行日的收價(103),也不是決策日的開價(92)
    assert first.price != pytest.approx(float(panel.close.loc[dates[3], ids[0]]))
    assert first.price != pytest.approx(float(panel.open.loc[dates[2], ids[0]]))

    # 注碼亦以開價計,不是偷看當日收價
    assert first.shares == pytest.approx(result.params.initial_cash / 93.0, rel=1e-6)


def _cadence_defaults(path: Path) -> list[str]:
    """找出這個檔裡有沒有人偷偷給節奏一個預設值。

    看語法樹而不是逐個字搜:說明文字裡的用法示範(``cadence="monthly"``)不算
    預設值,只有真的寫進簽名或賦值那一格才算。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: list[str] = []

    def is_text(node: ast.AST | None) -> bool:
        return isinstance(node, ast.Constant) and isinstance(node.value, str)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = node.args.posonlyargs + node.args.args
            tail = positional[len(positional) - len(node.args.defaults) :]
            pairs = list(zip(tail, node.args.defaults))
            pairs += [
                (argument, default)
                for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults)
                if default is not None
            ]
            offenders += [
                f"{path.name}:{node.name}({argument.arg}=...)"
                for argument, default in pairs
                if "cadence" in argument.arg and is_text(default)
            ]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if "cadence" in node.target.id and is_text(node.value):
                offenders.append(f"{path.name}:{node.target.id}")
        elif isinstance(node, ast.Assign):
            offenders += [
                f"{path.name}:{target.id}"
                for target in node.targets
                if isinstance(target, ast.Name) and "cadence" in target.id and is_text(node.value)
            ]
    return offenders


# 假引擎住在 tests/doubles/engines.py(KARST-090):以前四個測試檔各寫一個,
# 改一次引擎合約要四處跟改,漏改那一份會靜靜地繼續過測試。
