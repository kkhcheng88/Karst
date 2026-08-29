"""KARST-077 驗收:D-034「失敗運行」判準的純函數,三個案例,只證行得通。

``is_failed_run`` 不碰庫、不碰序列——純數字進、純判斷出,所以不用真實運行
也測得到。真實庫上的判定結果另見 ``experiments/2026-08-29-failed-runs/README.md``。
"""

from __future__ import annotations

from karst.web.data import is_failed_run


def test_年化贏其中一隻基準不算失敗運行():
    """贏 SPY、輸 QQQ:不是「同時」輸給兩隻,不算失敗運行。"""
    assert is_failed_run(0.10, {"SPY": 0.08, "QQQ": 0.15}) is False


def test_年化同時輸兩隻基準即失敗運行():
    assert is_failed_run(0.05, {"SPY": 0.08, "QQQ": 0.15}) is True


def test_基準缺一隻不判不歸入失敗():
    """該次運行的快照缺一隻基準(或者算不出它的年化回報),寧可不判,
    也不可以拿一隻基準都不齊的數字定它失敗。"""
    assert is_failed_run(0.05, {"SPY": 0.08}) is None
    assert is_failed_run(0.05, {"QQQ": 0.15, "SPY": None}) is None
    assert is_failed_run(None, {"SPY": 0.08, "QQQ": 0.15}) is None
