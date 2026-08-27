"""vectorbt 適配器:全倉**唯一**一個 ``import vectorbt`` 的地方。

D-007 第 3 條、D-011 第 2 條:引擎收在自家介面之後,日後商品化只換這一檔,
語意層一字不用改。進來的是 Karst 的型別,出去的也是 Karst 的型別——
``vbt.Portfolio`` 一步都不會離開本檔。

走的是規格 6.3 那條淺路:``from_orders`` 配目標比重與共用現金,全程不需要
動用 ``from_order_func``(帶組合層風控的規則類策略才要,不在本票)。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import vectorbt as vbt

from .contracts import Order, PricePanel, RankingRebalanceParams, SimulationOutput

# vectorbt 的買賣方向碼 → Karst 自己的說法。這張表就是防漏的最後一格。
_SIDES: dict[int, str] = {0: "buy", 1: "sell"}


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


def _orders(portfolio: "vbt.Portfolio", panel: PricePanel) -> tuple[Order, ...]:
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
