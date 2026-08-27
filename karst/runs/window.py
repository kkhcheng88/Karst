"""檢視視窗(view window):在同一次運行的逐日結果上另揀一段日期重看。

規格 8.5、詞彙表「檢視視窗」:**是重看不是重跑,運行本身不變**。用戶原話
「if I just want to focus on the performance since 2023 then I don't need a rerun?」
——所以這裡一條引擎都不碰,只讀已經保存的逐日淨值。

淨值一律**由該段的起始日重設為 100**:視窗的第一日就是視窗的基準,兩段不同
日期的走勢因此看得出誰跑贏誰,不會被起點金額大小蓋過。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import numpy as np
import pandas as pd

from ..errors import ContractViolation
from ..models import as_date

# 年化用的一年交易日數。逐日序列排的是交易日不是日曆日,故此用 252 不用 365。
TRADING_DAYS_PER_YEAR = 252.0

# 檢視視窗的基準:每段一律由 100 起步(規格 8.5)。
BASE = 100.0


@dataclass(frozen=True, slots=True)
class WindowStats:
    """一段檢視視窗的三個數,連同重設基準後的淨值線。

    ``max_drawdown`` 以**負數**表示(-0.23 即由高位跌 23%),0.0 代表期內未跌破
    過任何高位。三個數全部只由這一段的逐日淨值算出,與運行的全期無關。
    """

    start: str
    end: str
    trading_days: int
    base: float
    total_return: float
    annual_return: float
    max_drawdown: float
    equity: pd.Series


def normalise_equity(equity: pd.Series | pd.DataFrame, label: str = "逐日淨值") -> pd.Series:
    """把一條逐日淨值核對兼規範化:日期索引、由早到遲、正數、無重覆日。

    對不上即當場拒收——淨值有一日是 NaN 或 0,整條線之後的回報就是錯的。
    """
    if isinstance(equity, pd.DataFrame):
        if equity.shape[1] != 1:
            raise ContractViolation(f"{label}要一條序列,收到 {equity.shape[1]} 欄")
        series = equity.iloc[:, 0]
    elif isinstance(equity, pd.Series):
        series = equity
    else:
        raise ContractViolation(
            f"{label}要一條 pandas 序列,收到 {type(equity).__name__}"
        )

    if series.empty:
        raise ContractViolation(f"{label}是空的;沒有逐日序列的運行不成留痕")
    try:
        index = pd.DatetimeIndex(series.index)
    except (TypeError, ValueError) as exc:
        raise ContractViolation(f"{label}的索引要是交易日") from exc
    if index.has_duplicates:
        raise ContractViolation(f"{label}有重複的交易日")

    out = pd.Series(series.to_numpy(dtype=float), index=index, name="equity").sort_index()
    values = out.to_numpy()
    if not np.isfinite(values).all():
        raise ContractViolation(
            f"{label}有非有限數(NaN 或 ±inf);那一日沒有淨值就是序列有洞,不要填 0"
        )
    if (values <= 0.0).any():
        raise ContractViolation(f"{label}有非正數;淨值歸零之後不可再算比率回報")
    return out


def window_slice(
    equity: pd.Series,
    start: date | datetime | str | None = None,
    end: date | datetime | str | None = None,
) -> pd.Series:
    """截出視窗那一段。起訖含頭含尾;留空即由頭或到尾。

    起訖日不必是交易日——落在中間的日子取**該日或之後**的第一根、與**該日或
    之前**的最後一根,即用戶心目中那一段。截出來不夠兩日即拒收:一日算不出回報。
    """
    series = normalise_equity(equity)
    first = pd.Timestamp(as_date(start, "start")) if start is not None else series.index[0]
    last = pd.Timestamp(as_date(end, "end")) if end is not None else series.index[-1]
    if last < first:
        raise ContractViolation(f"檢視視窗的結束日 {last.date()} 早於開始日 {first.date()}")

    window = series.loc[(series.index >= first) & (series.index <= last)]
    if len(window) < 2:
        raise ContractViolation(
            f"檢視視窗 {first.date()}~{last.date()} 只有 {len(window)} 個交易日,"
            "算不出回報;請揀闊一點的一段"
        )
    return window


def rebase(equity: pd.Series, base: float = BASE) -> pd.Series:
    """把一條淨值線的起點重設為 ``base``(預設 100)。"""
    series = normalise_equity(equity)
    return series / float(series.iloc[0]) * float(base)


def max_drawdown(equity: pd.Series) -> float:
    """期內最大回撤,以負數表示。由這一段自己的高位起計,與段外無關。"""
    series = normalise_equity(equity)
    return float((series / series.cummax() - 1.0).min())


def window_stats(
    equity: pd.Series,
    start: date | datetime | str | None = None,
    end: date | datetime | str | None = None,
    *,
    base: float = BASE,
) -> WindowStats:
    """由已保存的逐日淨值,**不重跑引擎**算出任一段的累計回報、年化與最大回撤。

    累計回報 = 段尾 ÷ 段首 - 1,故此把一段切開兩段再相乘,結果與整段一模一樣
    (段首那一日在兩段都是基準日,回報為零,不會重覆計算)。
    """
    window = window_slice(equity, start, end)
    rebased = rebase(window, base)

    total_return = float(window.iloc[-1] / window.iloc[0] - 1.0)
    years = (len(window) - 1) / TRADING_DAYS_PER_YEAR
    annual_return = float((1.0 + total_return) ** (1.0 / years) - 1.0)

    return WindowStats(
        start=str(window.index[0].date()),
        end=str(window.index[-1].date()),
        trading_days=int(len(window)),
        base=float(base),
        total_return=total_return,
        annual_return=annual_return,
        max_drawdown=max_drawdown(window),
        equity=rebased,
    )
