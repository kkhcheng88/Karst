"""KARST-060 驗收:賣出當日不可再入場,新入場最早在下一個交易日開市。

背景:KARST-059 用手算對照引擎的時候,把「先離場、後入場」寫成同一根 K 線之內
做得到,於是賣出當日又開一注,淨值自此與引擎分家。查下去是**手算錯、引擎對**——
入場成交取開價,而離場是開市之後才發生的事,開市那一刻舊倉仍然在手,那一注根本
開不成。但那次也發現:這一句只活在實作裡,``rules.py`` 那份「全倉唯一一份出場
規約」沒有明寫。KARST-060 把規約文字補齊,並用這個測試把行為釘死——日後有人改
落單那一層、或者換一個引擎,這裡會先紅。

**引擎邏輯一個字都沒有改**,本檔只是證明它現時就是這樣行。

玩具數據:一隻股票、一條每日 +1 的斜坡,不連外部數據、不開任何資料庫連線(D-027)。
斜坡令突破訊號**每一根都成立**,所以「賣出當日沒有入場」只可能來自規約那一句,
不可能是「那日剛好無訊號」。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_engine_exit_reentry.py -q``
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from karst.engine import (
    BarPanel,
    BreakoutEntry,
    MeasuredMoveTarget,
    RiskFractionSizing,
    RuleStrategyParams,
    SwingLowStop,
    build_rule_signals,
    run_rule_strategy,
)

ROWS = 30
ENTITY = 701
INITIAL_CASH = 1_000_000.0

# 斜坡的形狀:收市每日 +1,開價等於上一日收市(無隔夜跳空),高低價各留半個價位。
STEP = 1.0
WICK = 0.5


@pytest.fixture(scope="module")
def panel() -> BarPanel:
    """每日 +1 的斜坡:每一根都刷新高,所以突破訊號根根成立。"""
    dates = pd.bdate_range("2024-01-02", periods=ROWS)
    close = 100.0 + STEP * np.arange(ROWS)
    open_ = np.empty(ROWS)
    open_[0] = close[0]
    open_[1:] = close[:-1]                       # 開市價 = 上一日收市,不留跳空
    high = np.maximum(open_, close) + WICK
    low = np.minimum(open_, close) - WICK

    frame = lambda values: pd.DataFrame(  # noqa: E731
        values.reshape(-1, 1), index=dates, columns=[ENTITY]
    )
    return BarPanel.from_frames(
        open=frame(open_), high=frame(high), low=frame(low), close=frame(close)
    )


@pytest.fixture(scope="module")
def params() -> RuleStrategyParams:
    """五件規則寫齊。熔斷關掉——本檔要看的只有出場與再入場那一格。"""
    return RuleStrategyParams(
        entry=BreakoutEntry(lookback_days=3),
        stop=SwingLowStop(lookback_days=2, min_stop_fraction=0.005, max_stop_fraction=0.25),
        target=MeasuredMoveTarget(min_reward_risk=1.0),
        sizing=RiskFractionSizing(
            risk_per_trade=0.01, max_position_fraction=0.25, equity_basis="current_equity"
        ),
        breaker=None,
        initial_cash=INITIAL_CASH,
        fees=0.0,
        tie_break_seed=20260829,
    )


def test_賣出當日不可再入場新入場最早在下一交易日開市(panel, params):
    signals = build_rule_signals(panel, params)
    result = run_rule_strategy(panel=panel, params=params)

    dates = [day.strftime("%Y-%m-%d") for day in panel.dates]
    opens = panel.open.to_numpy()
    row_of = {date: index for index, date in enumerate(dates)}

    buys = {row_of[o.trade_date]: o for o in result.orders if o.side == "buy"}
    sells = {row_of[o.trade_date]: o for o in result.orders if o.side == "sell"}

    # 這條斜坡真的行到一買一賣好幾轉,不是空跑一場
    assert len(buys) >= 5, "玩具數據要跑得出幾轉來回,否則證不到什麼"
    assert len(sells) >= 5

    for row in sorted(sells):
        # (一)賣出那一日**確實有入場訊號**——所以「當日沒有買入」只可能是規約
        #      那一句攔住,不可能是那日剛好無訊號
        assert signals.entries[row, 0], f"第 {row} 根賣出當日應該有入場訊號"

        # (二)賣出當日一張買單都沒有
        assert row not in buys, f"第 {row} 根賣出當日不應該再入場"

        # (三)新入場落在**下一個交易日**,成交價是那一根的開價
        assert row + 1 < ROWS, "最後一根賣出的話就驗不到下一日,請加長玩具數據"
        assert row + 1 in buys, f"第 {row} 根賣出之後,下一個交易日應該入得回場"
        assert buys[row + 1].price == pytest.approx(opens[row + 1, 0])

    # 反過來也要成立:沒有一日同時有買單與賣單
    assert not (set(buys) & set(sells)), "同一日不可以既賣出又入場"

    # 賣出全部由規約那三張表決定(這裡是觸目標),不是引擎另判一次
    for row, order in sells.items():
        entered = max(bar for bar in buys if bar < row)
        assert signals.exits.exit_bar[entered, 0] == row
        assert signals.exits.reason_at(entered, 0) == "target"
        assert order.price == pytest.approx(signals.exits.exit_price[entered, 0])
