"""KARST-066 驗收:對齊函數與 IC / ICIR 計算,小樣本手算對照。

三件事要證:

  1. 對齊表的回報起點是**可執行時點那根 K 線的開價**,不是知情當日收價;持有期
     ``horizon`` 個交易日的量法(第 1 日開至第 N 日收)手算對得上。
  2. 逐日 Spearman IC 與 scipy.stats.spearmanr 手算的結果一字不差。
  3. 滾動 ICIR(均值 / 標準差)手算對得上。

全部用小到手推得出答案的玩具數據,不碰倉內真數據。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from karst.errors import ContractViolation
from karst.factorpredict import (
    align_factor_to_forward_returns,
    daily_ic,
    rolling_icir,
    summarize_ic,
)

# ----------------------------------------------------------------------
# 對齊:回報起點用可執行時點的開價
# ----------------------------------------------------------------------


def _price_frame() -> pd.DataFrame:
    """五個交易日、一隻實體(entity_id=1)的玩具日線:開價逐日 +1,收價 = 開價 +0.5。"""
    days = ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"]
    opens = [10.0, 11.0, 12.0, 13.0, 14.0]
    rows = [
        {"date": day, "entity_id": 1, "open": o, "close": o + 0.5}
        for day, o in zip(days, opens)
    ]
    return pd.DataFrame(rows)


def _factor_long_single_row(*, event_day: str, knowledge_day: str, executable_day: str | None) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "factor_version_id": 1,
                "entity_id": 1,
                "event_time": pd.Timestamp(f"{event_day}T00:00:00"),
                "knowledge_time": pd.Timestamp(f"{knowledge_day}T23:59:59.999999"),
                "executable_time": (
                    None if executable_day is None else pd.Timestamp(f"{executable_day}T00:00:00")
                ),
                "value": 0.42,
            }
        ]
    )


def test_forward_return_uses_executable_open_not_knowledge_close():
    # 知情時點是 01-05(收工),可執行時點是下一根 01-06 開市。
    factor_long = _factor_long_single_row(
        event_day="2026-01-05", knowledge_day="2026-01-05", executable_day="2026-01-06"
    )
    aligned = align_factor_to_forward_returns(factor_long, _price_frame(), horizon=1)

    assert len(aligned) == 1
    row = aligned.iloc[0]
    # horizon=1:第 1 日(01-06)開買、第 1 日(01-06)收賣。開=11.0,收=11.5。
    expected = 11.5 / 11.0 - 1.0
    assert row["forward_return"] == pytest.approx(expected)
    # 不是拿知情當日(01-05)的收價來算——01-05 收價是 10.5,若誤用會得出另一個數。
    wrong = 11.5 / 10.5 - 1.0
    assert row["forward_return"] != pytest.approx(wrong)


def test_forward_return_horizon_n_holds_to_the_nth_bar_close():
    factor_long = _factor_long_single_row(
        event_day="2026-01-05", knowledge_day="2026-01-05", executable_day="2026-01-06"
    )
    aligned = align_factor_to_forward_returns(factor_long, _price_frame(), horizon=3)

    # 第 1 日 01-06 開(11.0)買,持有 3 個交易日(01-06、01-07、01-08),
    # 第 3 日 01-08 收(13.5)賣。
    expected = 13.5 / 11.0 - 1.0
    assert aligned.iloc[0]["forward_return"] == pytest.approx(expected)


def test_rows_without_executable_time_are_dropped():
    factor_long = _factor_long_single_row(
        event_day="2026-01-09", knowledge_day="2026-01-09", executable_day=None
    )
    aligned = align_factor_to_forward_returns(factor_long, _price_frame(), horizon=1)
    assert aligned.empty


def test_rows_where_horizon_runs_past_the_calendar_are_dropped():
    # 可執行時點是日曆最後一日(01-09),horizon=2 要用到 01-10 的收價,面板沒有。
    factor_long = _factor_long_single_row(
        event_day="2026-01-08", knowledge_day="2026-01-08", executable_day="2026-01-09"
    )
    aligned = align_factor_to_forward_returns(factor_long, _price_frame(), horizon=2)
    assert aligned.empty


def test_horizon_must_be_a_positive_integer():
    factor_long = _factor_long_single_row(
        event_day="2026-01-05", knowledge_day="2026-01-05", executable_day="2026-01-06"
    )
    with pytest.raises(ContractViolation):
        align_factor_to_forward_returns(factor_long, _price_frame(), horizon=0)


# ----------------------------------------------------------------------
# 逐日 Spearman IC:與 scipy.stats.spearmanr 手算對照
# ----------------------------------------------------------------------


def _aligned_two_days() -> pd.DataFrame:
    """一條因子、一日三隻:第一日因子與回報同向排(部分打亂),第二日完全反向。"""
    rows = [
        # 2026-01-05:因子排名 1,2,3;回報排名 1,3,2(scipy 手算 rho = 0.5)
        {"factor_version_id": 1, "entity_id": 1, "knowledge_time": pd.Timestamp("2026-01-05T23:59:59"), "factor_value": 1.0, "forward_return": 0.01},
        {"factor_version_id": 1, "entity_id": 2, "knowledge_time": pd.Timestamp("2026-01-05T23:59:59"), "factor_value": 2.0, "forward_return": 0.03},
        {"factor_version_id": 1, "entity_id": 3, "knowledge_time": pd.Timestamp("2026-01-05T23:59:59"), "factor_value": 3.0, "forward_return": 0.02},
        # 2026-01-06:因子排名 1,2,3;回報排名 3,2,1(完全反向,rho = -1)
        {"factor_version_id": 1, "entity_id": 1, "knowledge_time": pd.Timestamp("2026-01-06T23:59:59"), "factor_value": 1.0, "forward_return": 0.03},
        {"factor_version_id": 1, "entity_id": 2, "knowledge_time": pd.Timestamp("2026-01-06T23:59:59"), "factor_value": 2.0, "forward_return": 0.02},
        {"factor_version_id": 1, "entity_id": 3, "knowledge_time": pd.Timestamp("2026-01-06T23:59:59"), "factor_value": 3.0, "forward_return": 0.01},
    ]
    return pd.DataFrame(rows)


def test_daily_ic_matches_scipy_spearmanr():
    daily = daily_ic(_aligned_two_days())
    assert len(daily) == 2

    day1 = daily[daily["date"] == pd.Timestamp("2026-01-05")].iloc[0]
    expected1, _ = spearmanr([1.0, 2.0, 3.0], [0.01, 0.03, 0.02])
    assert day1["ic"] == pytest.approx(expected1)
    assert day1["ic"] == pytest.approx(0.5)
    assert day1["n"] == 3

    day2 = daily[daily["date"] == pd.Timestamp("2026-01-06")].iloc[0]
    expected2, _ = spearmanr([1.0, 2.0, 3.0], [0.03, 0.02, 0.01])
    assert day2["ic"] == pytest.approx(expected2)
    assert day2["ic"] == pytest.approx(-1.0)


def test_daily_ic_leaves_single_entity_days_as_nan():
    rows = [
        {"factor_version_id": 1, "entity_id": 1, "knowledge_time": pd.Timestamp("2026-01-05T23:59:59"), "factor_value": 1.0, "forward_return": 0.01},
    ]
    daily = daily_ic(pd.DataFrame(rows))
    assert len(daily) == 1
    assert np.isnan(daily.iloc[0]["ic"])
    assert daily.iloc[0]["n"] == 1


# ----------------------------------------------------------------------
# 滾動 ICIR:均值 / 標準差手算對照
# ----------------------------------------------------------------------


def test_rolling_icir_matches_hand_computed_mean_and_std():
    daily = daily_ic(_aligned_two_days())  # 兩日:IC = 0.5, -1.0
    rolled = rolling_icir(daily, window=2)

    assert len(rolled) == 2
    first = rolled.iloc[0]
    assert np.isnan(first["ic_mean"])  # 窗口未滿

    second = rolled.iloc[1]
    expected_mean = (0.5 + (-1.0)) / 2
    expected_std = np.std([0.5, -1.0], ddof=1)
    expected_icir = expected_mean / expected_std
    assert second["ic_mean"] == pytest.approx(expected_mean)
    assert second["ic_std"] == pytest.approx(expected_std)
    assert second["icir"] == pytest.approx(expected_icir)


def test_rolling_icir_rejects_window_below_two():
    daily = daily_ic(_aligned_two_days())
    with pytest.raises(ContractViolation):
        rolling_icir(daily, window=1)


# ----------------------------------------------------------------------
# 全期摘要
# ----------------------------------------------------------------------


def test_summarize_ic_reports_mean_std_icir_and_sample_days():
    daily = daily_ic(_aligned_two_days())
    summary = summarize_ic(daily).set_index("factor_version_id")

    row = summary.loc[1]
    expected_mean = (0.5 + (-1.0)) / 2
    expected_std = np.std([0.5, -1.0], ddof=1)
    assert row["ic_mean"] == pytest.approx(expected_mean)
    assert row["ic_std"] == pytest.approx(expected_std)
    assert row["icir"] == pytest.approx(expected_mean / expected_std)
    assert row["n_days"] == 2


def test_summarize_ic_excludes_nan_days_from_sample_count():
    rows = [
        {"factor_version_id": 1, "date": pd.Timestamp("2026-01-05"), "ic": 0.4, "n": 5},
        {"factor_version_id": 1, "date": pd.Timestamp("2026-01-06"), "ic": np.nan, "n": 1},
        {"factor_version_id": 1, "date": pd.Timestamp("2026-01-07"), "ic": 0.2, "n": 5},
    ]
    summary = summarize_ic(pd.DataFrame(rows)).set_index("factor_version_id")
    assert summary.loc[1, "n_days"] == 2
    assert summary.loc[1, "ic_mean"] == pytest.approx(0.3)
