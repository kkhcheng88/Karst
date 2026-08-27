"""由逐筆交易還原「一買一賣」的來回,再算勝率、盈虧比與平均持倉日數。

八項指標之中有三項不是由淨值線算得出的:**勝率、盈虧比、平均持倉日數**。
它們的單位是「一筆交易」,而已保存的逐筆交易只記單邊成交(買或賣),所以要先
把單邊成交配成來回(round trip)。

配法用**先入先出**(FIFO):同一實體先買的先賣。這是最無爭議的一種配法,
亦與券商月結單同制;換一種配法(後入先出、平均成本)算出來的勝率會不同,
故此本檔明文寫死一種,不設選項。

**只計已平倉的來回**。期末仍然持有的倉不入勝率——它未有結果,填一個數落去
就是在猜(與因子值缺失不填 0 同制,D-021 第 4 條)。

一條都不碰引擎:入口只有那三張已保存的表(規格 8.5)。
"""

from __future__ import annotations

from bisect import bisect_left
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from ..errors import ContractViolation


@dataclass(frozen=True, slots=True)
class RoundTrip:
    """一筆已平倉的來回:買入那一刻到賣出那一刻。

    ``profit`` 已扣兩邊費用,正數即贏。``holding_days`` 數的是**交易日**
    (由運行自己那條逐日淨值的日曆數),不是日曆日——持倉三日跨一個週末,
    答案仍然是三日。
    """

    entity_id: int
    entry_date: str
    exit_date: str
    shares: float
    entry_price: float
    exit_price: float
    fees: float
    profit: float
    holding_days: int

    @property
    def is_win(self) -> bool:
        return self.profit > 0.0


@dataclass(frozen=True, slots=True)
class TradeStats:
    """逐筆交易那一層的統計。

    ``win_rate`` 與 ``profit_loss_ratio`` 算不出時是 ``None``,**不是 0**:
    一筆都未平倉就沒有勝率,一次都未蝕過就沒有盈虧比——填 0 會讀成
    「全部輸清」,那是另一回事。
    """

    closed_trades: int
    winning_trades: int
    losing_trades: int
    open_positions: int
    win_rate: float | None
    profit_loss_ratio: float | None
    average_holding_days: float | None
    traded_value: float
    round_trips: tuple[RoundTrip, ...]


def round_trips(
    orders: pd.DataFrame, trading_days: Sequence[str] | pd.DatetimeIndex
) -> tuple[RoundTrip, ...]:
    """把逐筆成交配成已平倉的來回,由買入日排序。

    ``trading_days`` 是這次運行的交易日曆(逐日淨值的索引),只用來數持倉日數。
    """
    frame = _normalise(orders)
    days = _day_strings(trading_days)

    open_lots: dict[int, deque[list]] = {}
    closed: list[RoundTrip] = []

    for row in frame.itertuples(index=False):
        entity_id = int(row.entity_id)
        shares = float(row.shares)
        if shares <= 0.0:
            raise ContractViolation(
                f"{row.trade_date} 實體 {entity_id} 的成交股數是 {shares};"
                "成交方向已由 side 表達,股數要正數"
            )
        fee_per_share = float(row.fees) / shares
        if row.side == "buy":
            open_lots.setdefault(entity_id, deque()).append(
                [str(row.trade_date), shares, float(row.price), fee_per_share]
            )
            continue

        lots = open_lots.get(entity_id)
        remaining = shares
        while remaining > 1e-12:
            if not lots:
                raise ContractViolation(
                    f"{row.trade_date} 賣出實體 {entity_id} 但手上沒有貨;"
                    "本層只配得出多頭來回,沽空的來回配法未裁"
                )
            lot = lots[0]
            matched = min(remaining, lot[1])
            entry_fee = matched * lot[3]
            exit_fee = matched * fee_per_share
            closed.append(
                RoundTrip(
                    entity_id=entity_id,
                    entry_date=lot[0],
                    exit_date=str(row.trade_date),
                    shares=matched,
                    entry_price=lot[2],
                    exit_price=float(row.price),
                    fees=entry_fee + exit_fee,
                    profit=matched * (float(row.price) - lot[2]) - entry_fee - exit_fee,
                    holding_days=_position(days, str(row.trade_date))
                    - _position(days, lot[0]),
                )
            )
            remaining -= matched
            lot[1] -= matched
            if lot[1] <= 1e-12:
                lots.popleft()

    closed.sort(key=lambda t: (t.entry_date, t.exit_date, t.entity_id))
    return tuple(closed)


def trade_stats(
    orders: pd.DataFrame, trading_days: Sequence[str] | pd.DatetimeIndex
) -> TradeStats:
    """勝率、盈虧比、平均持倉日數,連同買賣雙邊的成交金額(算換手用)。

    · 勝率 = 賺錢的來回 ÷ 已平倉的來回(打和不算贏)。
    · 盈虧比 = 平均每筆賺幾多 ÷ 平均每筆蝕幾多(蝕的取絕對值)。
    · 平均持倉日數 = 各來回持倉交易日數的平均。
    """
    trips = round_trips(orders, trading_days)
    frame = _normalise(orders)
    traded_value = float((frame["shares"] * frame["price"]).abs().sum())

    wins = [t.profit for t in trips if t.profit > 0.0]
    losses = [-t.profit for t in trips if t.profit < 0.0]
    closed = len(trips)

    open_positions = 0
    for entity_id, bought in frame[frame["side"] == "buy"].groupby("entity_id")["shares"]:
        sold = float(
            frame.loc[
                (frame["entity_id"] == entity_id) & (frame["side"] == "sell"), "shares"
            ].sum()
        )
        if float(bought.sum()) - sold > 1e-9:
            open_positions += 1

    return TradeStats(
        closed_trades=closed,
        winning_trades=len(wins),
        losing_trades=len(losses),
        open_positions=open_positions,
        win_rate=(len(wins) / closed) if closed else None,
        profit_loss_ratio=(
            (sum(wins) / len(wins)) / (sum(losses) / len(losses))
            if wins and losses
            else None
        ),
        average_holding_days=(
            sum(t.holding_days for t in trips) / closed if closed else None
        ),
        traded_value=traded_value,
        round_trips=trips,
    )


def _normalise(orders: pd.DataFrame) -> pd.DataFrame:
    """核對逐筆交易表,並排成「同一日先買後賣」的次序。"""
    if not isinstance(orders, pd.DataFrame):
        raise ContractViolation(f"逐筆交易要一張 pandas 表,收到 {type(orders).__name__}")
    required = ("trade_date", "entity_id", "side", "shares", "price", "fees")
    missing = [column for column in required if column not in orders.columns]
    if missing:
        raise ContractViolation(f"逐筆交易缺欄位:{'、'.join(missing)}")

    frame = orders.loc[:, list(required)].copy()
    frame["trade_date"] = frame["trade_date"].astype(str)
    frame["entity_id"] = frame["entity_id"].astype(int)
    frame["side"] = [str(s).strip().lower() for s in frame["side"]]
    for column in ("shares", "price", "fees"):
        frame[column] = frame[column].astype(float)
    bad = sorted(set(frame["side"]) - {"buy", "sell"})
    if bad:
        raise ContractViolation(f"成交方向只收 buy / sell,收到 {bad}")
    # 同一日同一實體先買後賣:先買入才配得出當日平倉的來回
    return frame.sort_values(["trade_date", "entity_id", "side"]).reset_index(drop=True)


def _day_strings(trading_days: Sequence[str] | pd.DatetimeIndex) -> list[str]:
    if isinstance(trading_days, pd.DatetimeIndex):
        days = [str(day.date()) for day in trading_days]
    else:
        days = [str(day) for day in trading_days]
    if not days:
        raise ContractViolation("交易日曆是空的,數不到持倉日數")
    return sorted(days)


def _position(days: list[str], day: str) -> int:
    """這一日排在交易日曆的第幾格。不是交易日就取它之後的第一格。"""
    return bisect_left(days, day)
