"""由逐日淨值算得出的比率:下行波幅、Sortino、換手。

年化一律用 **252 個交易日**,與 ``karst.runs.window`` 同一個常數
(``TRADING_DAYS_PER_YEAR``)——同一次運行的年化回報與 Sortino 不可以兩個
分母,否則兩個數字擺在同一張卡上就對不上。

Sortino 的目標回報**無預設值**:要用的一律寫明(與換倉節奏同制,CONTEXT.md)。
坊間慣例默默當 0,但無風險利率是 0 還是 4%,同一條淨值線可以差出一倍的
Sortino;既然差得出,就不可以由本層代用戶決定。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..errors import ContractViolation
from ..runs.window import TRADING_DAYS_PER_YEAR, normalise_equity


def daily_returns(equity: pd.Series) -> pd.Series:
    """逐日回報。第一日沒有前一日,不算在內(不是 0)。"""
    series = normalise_equity(equity)
    return series.pct_change().iloc[1:]


def years_of(equity: pd.Series) -> float:
    """這一段有幾多年:交易日數減一,除 252。"""
    series = normalise_equity(equity)
    if len(series) < 2:
        raise ContractViolation("一日的淨值算不出年化,請揀闊一點的一段")
    return (len(series) - 1) / TRADING_DAYS_PER_YEAR


def downside_deviation(equity: pd.Series, *, target_annual_return: float) -> float:
    """年化下行波幅:只數跑輸目標那些日子,跑贏的一律當 0。

    目標由年化折算成逐日(幾何折算,與年化回報同一個口徑),逐日缺口平方
    取平均開方,再乘 √252 年化。
    """
    returns = daily_returns(equity)
    daily_target = (1.0 + float(target_annual_return)) ** (1.0 / TRADING_DAYS_PER_YEAR) - 1.0
    shortfall = np.minimum(returns.to_numpy() - daily_target, 0.0)
    return float(np.sqrt(np.mean(shortfall**2)) * np.sqrt(TRADING_DAYS_PER_YEAR))


def annual_volatility(equity: pd.Series) -> float:
    """年化波幅(上下都數)。策略詳情頁第七項用,不在八項之內。"""
    returns = daily_returns(equity)
    return float(returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))


def sortino_ratio(
    equity: pd.Series, *, annual_return: float, risk_free_rate: float
) -> float | None:
    """Sortino = (年化回報 − 無風險利率) ÷ 年化下行波幅。

    期內一日都未跌穿目標,分母是零,Sortino 算不出——此時回 ``None``,
    **不回無限大、不回 0**:算不出就講算不出。
    """
    deviation = downside_deviation(equity, target_annual_return=risk_free_rate)
    if deviation <= 0.0:
        return None
    return float((float(annual_return) - float(risk_free_rate)) / deviation)


def turnover(equity: pd.Series, *, traded_value: float) -> float:
    """年化換手:一年之內把組合換足幾多轉。

    ``traded_value`` 是期內買賣**雙邊**的成交金額合計。一買一賣才算換足一轉,
    所以先除 2 得單邊金額,再除以期內平均淨值得「換了幾多轉」,最後除年數年化。
    1.0 即一年換足一轉;原型顯示的百分比就是這個數乘 100。
    """
    series = normalise_equity(equity)
    average_equity = float(series.mean())
    if average_equity <= 0.0:  # pragma: no cover - normalise_equity 已擋非正數
        raise ContractViolation("平均淨值不是正數,算不出換手")
    return float(traded_value) / 2.0 / average_equity / years_of(series)
