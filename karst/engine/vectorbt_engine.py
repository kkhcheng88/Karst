"""vectorbt 適配器:全倉**唯一**一個 ``import vectorbt`` 的地方。

D-007 第 3 條、D-011 第 2 條:引擎收在自家介面之後,日後商品化只換這一檔,
語意層一字不用改。進來的是 Karst 的型別,出去的也是 Karst 的型別——
``vbt.Portfolio`` 一步都不會離開本檔。

本檔載兩條路(規格 6.3):

- **排名再平衡類**(``VectorbtEngine``)——``from_orders`` 配目標比重與共用現金,
  淺路,全程不需要動用 ``from_order_func``。
- **規則類**(``VectorbtRuleEngine``)——``from_order_func`` 配 ``pre_segment_func_nb``,
  五件規則一次過表達。組合層熔斷只有在這一層才看得見現金與權益,注碼基數亦只有
  在這一層才拿得到當下權益(規格 6.2,KARST-013 推翻 A-005 的理由)。
- 另加一條**對照臂**(``VectorbtSignalMatrixEngine``)——同一套規則走
  ``from_signals``,用來證明兩條路在「同基數、無熔斷」之下算得出同一個數;
  它表達不到熔斷與當下權益基數,遇上就當場拒收,不會默默算個假數出來。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import vectorbt as vbt
from numba import njit
from vectorbt.portfolio.enums import Direction, NoOrder, SizeType, StopEntryPrice
from vectorbt.portfolio.nb import order_nb

from .contracts import Order, PricePanel, RankingRebalanceParams, SimulationOutput
from .rules import (
    BarPanel,
    RuleNotExpressible,
    RuleSignals,
    RuleSimulationOutput,
    RuleStrategyParams,
)

# vectorbt 的買賣方向碼 → Karst 自己的說法。這張表就是防漏的最後一格。
_SIDES: dict[int, str] = {0: "buy", 1: "sell"}

# 熔斷狀態陣列(每組一份)的兩格。
_MONTH_START = 0   # 本月起點權益 = 上月最後一根收市的權益
_BLOCKED = 1       # 本月已落閘?1.0 = 停止新入場


class VectorbtEngine:
    """以 ``Portfolio.from_orders`` 跑「每期按因子排名選前 N 隻等權再平衡」。"""

    name = "vectorbt"

    def simulate(
        self,
        panel: PricePanel,
        targets: pd.DataFrame,
        params: RankingRebalanceParams,
    ) -> SimulationOutput:
        portfolio = vbt.Portfolio.from_orders(
            close=panel.close,          # 逐日估值用收價
            size=targets,
            size_type="targetpercent",  # 目標比重,不是股數(規格 6.3)
            price=panel.open,           # 成交在執行日那根 K 線的開價(D-021 第 3 條)
            direction="longonly",
            group_by=True,              # 全部實體同屬一個組合
            cash_sharing=True,          # 共用現金:同日賣出所得即時可用來買入
            call_seq="auto",            # 先賣後買。漏了它,買單會因現金未到位而被
            #                             默默部分拒絕——KARST-009 兩個「不寫就默默錯」之一
            init_cash=params.initial_cash,
            fees=params.fees,
            freq="1D",
        )
        return SimulationOutput(
            equity_curve=pd.Series(
                np.asarray(portfolio.value(), dtype=float), index=panel.dates, name="equity"
            ),
            holdings=pd.DataFrame(
                np.asarray(portfolio.assets(), dtype=float),
                index=panel.dates,
                columns=list(panel.entity_ids),
            ),
            orders=_orders(portfolio, panel),
        )


@njit(cache=True)
def _pre_segment_rules_nb(c, open_, close, month_id, state, basis, blocked, max_monthly_drawdown):
    """規則 5:組合層月度虧損熔斷。只有這一層看得見組合的現金與持倉。

    順帶把當日的**注碼基數**記低——記的是開市那一刻的權益(現金 + 持倉按開價估值),
    不是收市價估的權益:今日成交在開價,用收價估值等於偷看未來。
    """
    i = c.i
    g = c.group

    # 估值價設為今日開價(即今日的成交價),令 value_now 就是今日開市的權益
    for col in range(c.from_col, c.to_col):
        c.last_val_price[col] = open_[i, col]

    # 本函式跑的時候,現金與持倉仍是上一根收市的狀態,所以兩個數都算得準
    equity = c.last_cash[g]
    prev_equity = c.last_cash[g]
    for col in range(c.from_col, c.to_col):
        position = c.last_position[col]
        if position != 0.0:
            equity += position * open_[i, col]
            if i > 0:
                prev_equity += position * close[i - 1, col]

    if i == 0:
        state[_MONTH_START] = equity
        state[_BLOCKED] = 0.0
    elif month_id[i] != month_id[i - 1]:
        state[_MONTH_START] = prev_equity     # 新一個月:起點 = 上月最後一根收市的權益
        state[_BLOCKED] = 0.0

    if state[_BLOCKED] == 0.0 and state[_MONTH_START] > 0.0 and max_monthly_drawdown > 0.0:
        if equity / state[_MONTH_START] - 1.0 <= -max_monthly_drawdown:
            state[_BLOCKED] = 1.0             # 落閘;要到下個月第一根才解除

    basis[i] = equity
    blocked[i] = state[_BLOCKED]
    return ()


@njit(cache=True)
def _order_rules_nb(
    c, open_, high, low, entries, stop_level, target_level,
    position_stop, position_target, blocked,
    risk_per_trade, max_position_fraction, fixed_equity_basis, fees,
):
    """規則 1 至 4 的落點。手上有貨就只看離場,手上無貨才看入場。

    ``from_order_func`` 沒有內建止蝕/目標,兩者要逐根 K 線自己判——連跳空穿價
    (開市已經越過價位)都要自己擺位。這就是走這條路要付的代價(規格 6.2)。
    """
    i, col = c.i, c.col
    position = c.position_now

    if position > 0.0:
        stop = position_stop[col]
        target = position_target[col]
        bar_open = open_[i, col]
        if stop == stop and low[i, col] <= stop:          # stop == stop 即非 NaN
            price = bar_open if bar_open <= stop else stop   # 跳空穿價就以開市價成交
            position_stop[col] = np.nan
            position_target[col] = np.nan
            return order_nb(size=-position, price=price, fees=fees,
                            size_type=SizeType.Amount, direction=Direction.LongOnly)
        if target == target and high[i, col] >= target:
            price = bar_open if bar_open >= target else target
            position_stop[col] = np.nan
            position_target[col] = np.nan
            return order_nb(size=-position, price=price, fees=fees,
                            size_type=SizeType.Amount, direction=Direction.LongOnly)
        return NoOrder

    if not entries[i, col]:
        return NoOrder
    if blocked[i] == 1.0:                                  # 規則 5:本月已熔斷,不開新倉
        return NoOrder

    price = open_[i, col]                                  # 成交在這根 K 線的開價
    stop_distance = price - stop_level[i, col]
    if not (stop_distance > 0.0):
        return NoOrder

    # 規則 4:基數預設取當下權益;fixed_equity_basis > 0 即改用固定基數(對照臂)
    equity = c.value_now if fixed_equity_basis <= 0.0 else fixed_equity_basis
    shares = risk_per_trade * equity / stop_distance
    cap = max_position_fraction * equity / price
    if shares > cap:
        shares = cap
    if not (shares > 0.0):
        return NoOrder

    position_stop[col] = stop_level[i, col]
    position_target[col] = target_level[i, col]
    return order_nb(size=shares, price=price, fees=fees,
                    size_type=SizeType.Amount, direction=Direction.LongOnly)


class VectorbtRuleEngine:
    """以 ``Portfolio.from_order_func`` 跑規則類策略:五件規則一次過表達。"""

    name = "vectorbt-order-func"

    def simulate_rules(
        self,
        panel: BarPanel,
        signals: RuleSignals,
        params: RuleStrategyParams,
    ) -> RuleSimulationOutput:
        rows, columns = panel.close.shape
        position_stop = np.full(columns, np.nan)
        position_target = np.full(columns, np.nan)
        state = np.zeros(2)
        basis = np.zeros(rows)
        blocked = np.zeros(rows)
        fixed_basis = 0.0 if params.sizing.uses_current_equity else params.initial_cash

        portfolio = vbt.Portfolio.from_order_func(
            panel.close,
            _order_rules_nb,
            panel.open.to_numpy(),
            panel.high.to_numpy(),
            panel.low.to_numpy(),
            signals.entries,
            signals.stop_level,
            signals.target_level,
            position_stop,
            position_target,
            blocked,
            params.sizing.risk_per_trade,
            params.sizing.max_position_fraction,
            fixed_basis,
            params.fees,
            pre_segment_func_nb=_pre_segment_rules_nb,
            pre_segment_args=(
                panel.open.to_numpy(),
                panel.close.to_numpy(),
                signals.month_id,
                state,
                basis,
                blocked,
                params.max_monthly_drawdown,
            ),
            group_by=True,          # 全部實體同屬一個組合,熔斷才有「組合層」可言
            cash_sharing=True,      # 共用現金
            call_seq="random",      # 同日多個訊號公平抽籤;種子由參數定死
            seed=params.tie_break_seed,
            init_cash=params.initial_cash,
            freq="1D",
        )
        return _rule_output(portfolio, panel, basis, blocked > 0.0)


class VectorbtSignalMatrixEngine:
    """**對照臂**:同一套規則走 ``from_signals``,用來證明差距不是實作誤差。

    這條路表達不到兩件事(規格 6.2、KARST-013):組合層熔斷、當下權益基數——
    ``SignalContext`` 看不見現金與權益。遇上這兩件即當場拒收:寧可拒答,
    也不可以默默算出一個假數當真數用。
    """

    name = "vectorbt-signals"

    def simulate_rules(
        self,
        panel: BarPanel,
        signals: RuleSignals,
        params: RuleStrategyParams,
    ) -> RuleSimulationOutput:
        if params.breaker_on:
            raise RuleNotExpressible(
                "訊號矩陣路徑(from_signals)表達不到組合層月度熔斷:它看不見組合的現金與權益。"
                "要開熔斷就走 from_order_func 那條路(規格 6.2)"
            )
        if params.sizing.uses_current_equity:
            raise RuleNotExpressible(
                "訊號矩陣路徑(from_signals)的注碼基數只能是起始本金:SignalContext 看不見當下權益。"
                "要用當下權益做基數就走 from_order_func 那條路(規格 6.2)"
            )

        fill = panel.open.to_numpy()
        equity = params.initial_cash
        with np.errstate(invalid="ignore", divide="ignore"):
            stop_distance = fill - signals.stop_level
            # 與 _order_rules_nb 逐個運算符對齊,好令兩條路算出同一個浮點數
            shares = params.sizing.risk_per_trade * equity / stop_distance
            cap = params.sizing.max_position_fraction * equity / fill
            shares = np.minimum(shares, cap)
            usable = signals.entries & np.isfinite(shares) & (stop_distance > 0.0) & (shares > 0.0)
        size = np.where(usable, shares, np.nan)

        portfolio = vbt.Portfolio.from_signals(
            close=panel.close,
            open=panel.open,
            high=panel.high,
            low=panel.low,
            entries=signals.entries,
            exits=np.zeros_like(signals.entries),      # 只靠止蝕/目標離場
            size=size,
            size_type="amount",
            price=panel.open,                          # 成交在這根 K 線的開價
            sl_stop=signals.stop_fraction,             # 規則 2
            tp_stop=signals.target_fraction,           # 規則 3
            stop_entry_price=StopEntryPrice.FillPrice,  # 止蝕/目標以成交價為基準,換算回原本的絕對價位
            fees=params.fees,
            direction="longonly",
            group_by=True,
            cash_sharing=True,
            call_seq="random",
            seed=params.tie_break_seed,
            init_cash=params.initial_cash,
            freq="1D",
        )
        rows = len(panel.dates)
        return _rule_output(
            portfolio,
            panel,
            np.full(rows, params.initial_cash),        # 這條路的注碼基數由頭到尾是起始本金
            np.zeros(rows, dtype=np.bool_),            # 熔斷:表達不到,所以永遠無閘
        )


def _rule_output(
    portfolio: "vbt.Portfolio",
    panel: BarPanel,
    basis: np.ndarray,
    blocked: np.ndarray,
) -> RuleSimulationOutput:
    """把引擎的輸出翻譯成 Karst 的型別,一個第三方型別都不准漏出去。"""
    dates = panel.dates
    return RuleSimulationOutput(
        equity_curve=pd.Series(np.asarray(portfolio.value(), dtype=float), index=dates, name="equity"),
        holdings=pd.DataFrame(
            np.asarray(portfolio.assets(), dtype=float), index=dates, columns=list(panel.entity_ids)
        ),
        cash=pd.Series(np.asarray(portfolio.cash(), dtype=float), index=dates, name="cash"),
        sizing_basis=pd.Series(np.asarray(basis, dtype=float), index=dates, name="sizing_basis"),
        breaker_blocked=pd.Series(np.asarray(blocked, dtype=bool), index=dates, name="breaker_blocked"),
        orders=_orders(portfolio, panel),
    )


def _orders(portfolio: "vbt.Portfolio", panel: PricePanel | BarPanel) -> tuple[Order, ...]:
    """把引擎的成交記錄翻譯成 Karst 的訂單型別,一筆不漏、一個第三方型別不留。"""
    records = portfolio.orders.records
    if len(records) == 0:
        return ()

    dates = panel.dates
    entity_ids = list(panel.entity_ids)
    bar_positions = records["idx"].to_numpy(dtype=int)
    column_positions = records["col"].to_numpy(dtype=int)
    sides = records["side"].to_numpy(dtype=int)
    shares = records["size"].to_numpy(dtype=float)
    prices = records["price"].to_numpy(dtype=float)
    fees = records["fees"].to_numpy(dtype=float)

    orders = [
        Order(
            trade_date=pd.Timestamp(dates[bar]).strftime("%Y-%m-%d"),
            entity_id=int(entity_ids[column]),
            side=_SIDES[int(side)],
            shares=float(size),
            price=float(price),
            fees=float(fee),
        )
        for bar, column, side, size, price, fee in zip(
            bar_positions, column_positions, sides, shares, prices, fees, strict=True
        )
    ]
    orders.sort(key=lambda order: (order.trade_date, order.entity_id, order.side))
    return tuple(orders)
