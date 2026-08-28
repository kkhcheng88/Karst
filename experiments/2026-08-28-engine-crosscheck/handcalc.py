"""KARST-059 的手算那一邊:純 pandas,**一個 karst 的函式都不 import**。

這是外部對照的整個重點。引擎自己跟自己對得上只證明一致,不證明對;所以這一份
由零寫起,只按落了檔的規則定義行事:

* 規則 1 入場突破:收市價高於**前 N 日**最高(不含當日)。
* 規則 2 止蝕:過去 M 日最低價(含當日),一個絕對價位;止蝕距離兩道閘用真正
  成交價(次日開價)做分母。
* 規則 3 目標:訊號日收市 + 前 N 日區間高度;賠率 =(目標−收市)/(收市−止蝕),
  低過門檻不入場。
* 規則 4 注碼:股數 =(注碼基數 × 單筆風險)/(成交價 − 止蝕價),再受單一持倉
  市值上限封頂;注碼基數 = 當日**開市**那一刻的權益(現金 + 持倉 × 開價)。
* 規則 5 熔斷:月內權益由本月起點(上月最後一根收市的權益)回落達門檻,即停止
  該月餘下日子的新入場,不強制平倉。
* 成交時點(D-021 第 3 條):訊號在收市成形,**下一根 K 線的開價**成交。
* 出場規約:最低價跌穿止蝕即止蝕,最高價觸目標即目標,同一根兩者皆中一律當
  止蝕;跳空穿價以開市價成交;行到最後一根未收場即期末未平,不落賣單。

刻意寫成慢版逐日迴圈:看得懂比跑得快重要,而且與引擎的向量化路徑不同構,
撞啱同一個錯的機會低得多。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# 出場原因用同一批英文碼,對照表才對得起來。
EXIT_STOP = "stop"
EXIT_TARGET = "target"
EXIT_UNCLOSED = "unclosed"


def load_bars(path: str | Path, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """由 CSV 讀一隻股票的開高低收,順手做四價包絡線的浮點尾數壓平。

    壓平那一步與引擎入口那條容差是同一個口徑:高價不可低過開收價、低價不可高過
    開收價。這是**輸入資料的衛生**,不是演算法的一部分——兩邊餵同一批 K 線才對
    得起來,所以手算這邊照樣做一次。
    """
    frame = pd.read_csv(path, index_col=0, parse_dates=True)
    frame = frame[["Open", "High", "Low", "Close"]].astype(float).sort_index()
    if start is not None:
        frame = frame.loc[frame.index >= pd.Timestamp(start)]
    if end is not None:
        frame = frame.loc[frame.index <= pd.Timestamp(end)]
    high = frame[["High", "Open", "Close"]].max(axis=1)
    low = frame[["Low", "Open", "Close"]].min(axis=1)
    out = pd.DataFrame(
        {"Open": frame["Open"], "High": high, "Low": low, "Close": frame["Close"]},
        index=frame.index,
    )
    if not np.isfinite(out.to_numpy()).all():
        raise ValueError(f"{path} 有非有限價格")
    if (out.to_numpy() <= 0.0).any():
        raise ValueError(f"{path} 有非正價格")
    return out


@dataclass(frozen=True)
class HandParams:
    """手算這一邊的全部取值。與引擎那份參數一格一格對得上,但型別是自己的。"""

    breakout_lookback_days: int
    swing_lookback_days: int
    min_stop_fraction: float
    max_stop_fraction: float
    max_position_fraction: float
    per_trade_risk: float
    reward_risk_floor: float
    monthly_loss_cap: float | None
    initial_cash: float


def rule_signals(bars: pd.DataFrame, params: HandParams) -> pd.DataFrame:
    """規則 1、2、3 逐日算一次,結果對齊到**成交那一根**(訊號日的下一根)。

    逐日迴圈,不用 rolling,免得與引擎那邊的向量寫法犯同一個窗口錯。
    """
    n_break = params.breakout_lookback_days
    swing = params.swing_lookback_days
    opens = bars["Open"].to_numpy()
    highs = bars["High"].to_numpy()
    lows = bars["Low"].to_numpy()
    closes = bars["Close"].to_numpy()
    rows = len(bars)

    signal = np.zeros(rows, dtype=bool)
    stop_abs = np.full(rows, np.nan)
    target_abs = np.full(rows, np.nan)
    reward_risk = np.full(rows, np.nan)
    stop_fraction = np.full(rows, np.nan)
    target_fraction = np.full(rows, np.nan)

    for t in range(rows):
        if t < n_break or t < swing - 1 or t + 1 >= rows:
            continue                                  # 回望不夠、或者無下一根可成交
        prior_high = highs[t - n_break : t].max()      # 前 N 日,不含當日
        prior_low = lows[t - n_break : t].min()
        swing_low = lows[t - swing + 1 : t + 1].min()  # 過去 M 日最低,含當日
        close = closes[t]
        fill = opens[t + 1]                            # 次日開價成交

        stop_abs[t] = swing_low
        target_abs[t] = close + (prior_high - prior_low)
        plan_risk = close - swing_low
        plan_reward = target_abs[t] - close
        if plan_risk <= 0.0:
            continue
        reward_risk[t] = plan_reward / plan_risk
        stop_fraction[t] = (fill - swing_low) / fill
        target_fraction[t] = (target_abs[t] - fill) / fill

        if closes[t] <= prior_high:
            continue                                   # 規則 1 沒有突破
        if not (params.min_stop_fraction <= stop_fraction[t] <= params.max_stop_fraction):
            continue                                   # 止蝕太貼或太遠,兩邊皆不做
        if not target_fraction[t] > 0.0:
            continue
        if not reward_risk[t] >= params.reward_risk_floor:
            continue                                   # 賠率不夠
        signal[t] = True

    plan = pd.DataFrame(
        {
            "signal": signal,
            "stop_level": stop_abs,
            "target_level": target_abs,
            "reward_risk": reward_risk,
            "stop_fraction": stop_fraction,
            "target_fraction": target_fraction,
        },
        index=bars.index,
    )
    # 對齊到成交那一根:第 i 行講的是「第 i 根 K 線要做的事」
    aligned = plan.shift(1)
    aligned["signal"] = aligned["signal"].fillna(False).astype(bool)
    return aligned


@dataclass
class HandTrade:
    """手算這一邊的一筆交易(入場到收場)。"""

    entry_date: pd.Timestamp
    entry_price: float
    shares: float
    stop_level: float
    target_level: float
    exit_date: pd.Timestamp | None = None
    exit_price: float | None = None
    exit_reason: str | None = None


def run_rule_handcalc(bars: pd.DataFrame, params: HandParams) -> dict:
    """逐日行完整條規則路徑,交出淨值、現金、注碼基數、熔斷狀態、逐筆交易。

    一根 K 線之內的次序:先按開價估權益(注碼基數),再結算離場,再判熔斷,
    最後才開新倉;日終按收價估值入淨值。
    """
    plan = rule_signals(bars, params)
    dates = bars.index
    opens = bars["Open"].to_numpy()
    highs = bars["High"].to_numpy()
    lows = bars["Low"].to_numpy()
    closes = bars["Close"].to_numpy()
    entries = plan["signal"].to_numpy()
    stop_levels = plan["stop_level"].to_numpy()
    target_levels = plan["target_level"].to_numpy()
    months = np.array([d.year * 12 + d.month for d in dates], dtype=np.int64)

    cash = float(params.initial_cash)
    open_trade: HandTrade | None = None
    trades: list[HandTrade] = []

    equity = np.zeros(len(dates))
    cash_series = np.zeros(len(dates))
    basis_series = np.zeros(len(dates))
    blocked_series = np.zeros(len(dates), dtype=bool)
    orders: list[dict] = []

    month_start_equity = float(params.initial_cash)

    breaker_latched = False

    for i in range(len(dates)):
        if i > 0 and months[i] != months[i - 1]:
            month_start_equity = equity[i - 1]          # 上月最後一根收市的權益
            breaker_latched = False                     # 新一個月,閘解除

        # 開市那一刻手上有沒有倉。**這一格決定同一根能不能再開倉**:入場價是開價,
        # 而離場是開市之後才發生的事,所以開市那一刻舊倉仍在,就開不了新倉。
        held_at_open = open_trade is not None
        shares_held = open_trade.shares if open_trade is not None else 0.0
        basis = cash + shares_held * opens[i]           # 開市那一刻的權益 = 注碼基數
        basis_series[i] = basis

        # --- 離場(規則 2、3;跳空穿價以開市價成交)---------------------------
        if open_trade is not None:
            stop = open_trade.stop_level
            target = open_trade.target_level
            hit_stop = lows[i] <= stop
            hit_target = highs[i] >= target
            price = None
            reason = None
            if hit_stop:                                # 同一根兩者皆中一律當止蝕
                price = opens[i] if opens[i] <= stop else stop
                reason = EXIT_STOP
            elif hit_target:
                price = opens[i] if opens[i] >= target else target
                reason = EXIT_TARGET
            if price is not None:
                cash += open_trade.shares * price
                open_trade.exit_date = dates[i]
                open_trade.exit_price = float(price)
                open_trade.exit_reason = reason
                orders.append(
                    {
                        "trade_date": str(dates[i].date()),
                        "side": "sell",
                        "shares": open_trade.shares,
                        "price": float(price),
                        "exit_reason": reason,
                    }
                )
                open_trade = None

        # --- 熔斷(規則 5):只攔新入場,不平已有的倉 -------------------------
        # 落閘之後**直到下個月第一根 K 線才解除**——所以是一個閂,不是逐日重判。
        blocked = False
        if params.monthly_loss_cap is not None and month_start_equity > 0.0:
            shares_held = open_trade.shares if open_trade is not None else 0.0
            live = cash + shares_held * opens[i]
            if (live / month_start_equity - 1.0) <= -params.monthly_loss_cap:
                breaker_latched = True
            blocked = breaker_latched
        blocked_series[i] = blocked

        # --- 入場(規則 1、4)------------------------------------------------
        if entries[i] and not held_at_open and open_trade is None and not blocked:
            fill = opens[i]
            stop = stop_levels[i]
            target = target_levels[i]
            if fill - stop > 0.0:                       # 隔晚已跌穿止蝕就不入場
                risk_amount = basis * params.per_trade_risk
                shares = risk_amount / (fill - stop)
                cap_shares = basis * params.max_position_fraction / fill
                shares = min(shares, cap_shares)        # 單一持倉市值上限封頂
                if shares * fill > cash:                # 現金不夠就買到現金為止
                    shares = cash / fill
                if shares > 0.0:
                    cash -= shares * fill
                    open_trade = HandTrade(
                        entry_date=dates[i],
                        entry_price=float(fill),
                        shares=float(shares),
                        stop_level=float(stop),
                        target_level=float(target),
                    )
                    trades.append(open_trade)
                    orders.append(
                        {
                            "trade_date": str(dates[i].date()),
                            "side": "buy",
                            "shares": float(shares),
                            "price": float(fill),
                            "exit_reason": None,
                        }
                    )

        shares_held = open_trade.shares if open_trade is not None else 0.0
        cash_series[i] = cash
        equity[i] = cash + shares_held * closes[i]

    if open_trade is not None:                          # 期末未平:不落賣單,照收市估值
        open_trade.exit_date = dates[-1]
        open_trade.exit_price = float(closes[-1])
        open_trade.exit_reason = EXIT_UNCLOSED

    return {
        "equity": pd.Series(equity, index=dates, name="equity"),
        "cash": pd.Series(cash_series, index=dates, name="cash"),
        "sizing_basis": pd.Series(basis_series, index=dates, name="sizing_basis"),
        "blocked": pd.Series(blocked_series, index=dates, name="blocked"),
        "orders": pd.DataFrame(orders, columns=["trade_date", "side", "shares", "price", "exit_reason"]),
        "trades": pd.DataFrame(
            [
                {
                    "entry_date": str(t.entry_date.date()),
                    "entry_price": t.entry_price,
                    "shares": t.shares,
                    "stop_level": t.stop_level,
                    "target_level": t.target_level,
                    "exit_date": None if t.exit_date is None else str(t.exit_date.date()),
                    "exit_price": t.exit_price,
                    "exit_reason": t.exit_reason,
                }
                for t in trades
            ],
            columns=[
                "entry_date", "entry_price", "shares", "stop_level", "target_level",
                "exit_date", "exit_price", "exit_reason",
            ],
        ),
        "entry_signals": int(entries.sum()),
    }


def monthly_execution_bars(dates: pd.DatetimeIndex) -> list[int]:
    """月度節奏的執行日位置:每月最後一根 K 線是決策日,它的下一根是執行日。

    最後一個決策日若已經無下一根 K 線,那一次換倉不做——因子看得見,成交不到。
    """
    periods = pd.Series([d.year * 12 + d.month for d in dates], index=range(len(dates)))
    executions: list[int] = []
    for position in range(len(dates)):
        is_month_end = position == len(dates) - 1 or periods[position + 1] != periods[position]
        if is_month_end and position + 1 < len(dates):
            executions.append(position + 1)
    return executions


def run_ranking_handcalc(
    opens: pd.DataFrame,
    closes: pd.DataFrame,
    execution_bars: list[int],
    initial_cash: float,
) -> dict:
    """兩隻 ETF 月度等權再平衡,逐日手算。

    執行日按**開價**把每一隻拉回 1/N 等權,其餘日子不下單;日終按收價估值。
    """
    columns = list(opens.columns)
    weight = 1.0 / len(columns)
    dates = opens.index
    open_values = opens.to_numpy()
    close_values = closes.to_numpy()

    cash = float(initial_cash)
    shares = np.zeros(len(columns))
    equity = np.zeros(len(dates))
    holdings = np.zeros((len(dates), len(columns)))
    orders: list[dict] = []
    executions = set(execution_bars)

    for i in range(len(dates)):
        if i in executions:
            live = cash + float(np.dot(shares, open_values[i]))
            for column in range(len(columns)):
                want = weight * live / open_values[i, column]
                delta = want - shares[column]
                if delta != 0.0:
                    cash -= delta * open_values[i, column]
                    shares[column] = want
                    orders.append(
                        {
                            "trade_date": str(dates[i].date()),
                            "entity_id": columns[column],
                            "side": "buy" if delta > 0 else "sell",
                            "shares": abs(float(delta)),
                            "price": float(open_values[i, column]),
                        }
                    )
        holdings[i] = shares
        equity[i] = cash + float(np.dot(shares, close_values[i]))

    return {
        "equity": pd.Series(equity, index=dates, name="equity"),
        "holdings": pd.DataFrame(holdings, index=dates, columns=columns),
        "cash": pd.Series(
            [equity[i] - float(np.dot(holdings[i], close_values[i])) for i in range(len(dates))],
            index=dates,
            name="cash",
        ),
        "orders": pd.DataFrame(orders, columns=["trade_date", "entity_id", "side", "shares", "price"]),
    }
