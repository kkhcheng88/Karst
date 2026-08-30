"""KARST-090:策略執行台自己那幾件的煙霧測試。

因子混合經執行台走完一次正式運行、參數規格那一套值域與文字化,全部在
``tests/test_factor_mix.py`` 驗;本檔只補三件那邊碰不到的:

1. **重判的自檢**——換一個判讀口徑之前,先用**舊口徑**對回落檔那份判讀,對不上
   就不出新判讀(KARST-047)。這是重判唯一的安全閘,沒有它,一份口徑寫錯的
   報告會靜靜地當成「重判過」。
2. **計劃形狀**——策略合約交錯形狀的計劃,執行台當場拒收(不變量 2-5)。
3. **登記要自報已對齊還是示例**(D-038),無預設值。
"""

from __future__ import annotations

import pytest

from karst.errors import ContractViolation
from karst.executor import (
    PlanShapeViolation,
    TargetPlan,
)
from karst.executor.executor import Executor, _verdict_differences
from karst.sweep.grid import ProductGrid, SweepAxis
from karst.sweep.verdict import CellScore, judge

# 判讀的三個門檻。**一個預設值都沒有**:它們是判讀口徑,要明寫,報告亦要印出來。
RUBRIC = {"min_trades": 1, "lonely_peak_margin": 0.5, "plateau_quantile": 0.6}
OBJECTIVE = "年化回報"


@pytest.fixture()
def scored():
    """一個 3×3 的玩具格,連逐格成績。數字是砌出來的,不是任何一次真掃描。"""
    grid = ProductGrid(
        (
            SweepAxis(name="lookback", values=(10, 20, 30)),
            SweepAxis(name="top_n", values=(2, 3, 4)),
        )
    )
    points = list(grid.points())
    scores = [
        CellScore(point=point, value=0.05 + index * 0.01, trades=20)
        for index, point in enumerate(points)
    ]
    return grid, scores


def test_rejudging_checks_itself_against_the_old_rubric_before_it_speaks(scored):
    grid, scores = scored
    executor_free_judge = judge(scores, grid, objective=OBJECTIVE, **RUBRIC)

    # 舊口徑對得回落檔那份:自檢過關,新判讀照出。
    # ``rejudge`` 是靜態方法——重判不碰庫亦不碰引擎,所以起不起執行台都無所謂。
    outcome = Executor.rejudge(
        scores,
        grid,
        objective=OBJECTIVE,
        thresholds=RUBRIC,
        previous=executor_free_judge,
    )
    assert outcome.reproduced is True
    assert outcome.differences == ()
    assert _verdict_differences(executor_free_judge, outcome.judgement) == []

    # 落檔那份其實是另一個口徑判出來的:自檢不過,**拒絕**出新判讀
    other = judge(
        scores, grid, objective=OBJECTIVE,
        **{**RUBRIC, "lonely_peak_margin": 0.0001, "plateau_quantile": 0.1},
    )
    with pytest.raises(ContractViolation, match="自檢"):
        Executor.rejudge(
            scores,
            grid,
            objective=OBJECTIVE,
            thresholds=RUBRIC,
            previous=other,
        )


def test_a_plan_of_the_wrong_shape_is_refused_on_the_spot():
    class _Contract:
        strategy_type = "multifactor"
        funnel_stages = ()
        engine_path = "targets"

    with pytest.raises(PlanShapeViolation, match="TargetPlan"):
        Executor._check_plan(_Contract(), {"targets": "唔係一份計劃"}, {})


def test_a_selection_trace_outside_the_declared_funnel_stages_is_refused():
    class _Contract:
        strategy_type = "multifactor"
        funnel_stages = ("範圍",)
        engine_path = "targets"

    class _Trace:
        stages = ("範圍", "沒有宣告過的一層")
        candidates = None
        factor_scores = None

    plan = TargetPlan(
        targets=None, cadence="monthly", initial_cash=1.0, fees=0.0, selection=_Trace()
    )
    with pytest.raises(PlanShapeViolation, match="宣告以外的層"):
        Executor._check_plan(_Contract(), plan, {})
