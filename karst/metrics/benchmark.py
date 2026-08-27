"""基準(benchmark):買入持有的對照尺,由快照日線直接算。

詞彙表:**基準是純對照尺,不是策略**。所以本檔一條策略路徑都不行——不經引擎、
不經選股、不經換倉節奏,只做一件事:第一日買入,一直揸到最後一日。買入持有的
淨值線,其實就是那隻工具的收市價本身,再由視窗起始日重設為 100。

基準取數的快照**必須與運行同一個**(規格 8.4、D-026 第 4 條):快照只存已調整價,
每次派息之後整條歷史會變,兩個快照的價格不可直接比較。所以本檔只收快照編號,
不接受另外餵一條價格線進來。

基準一律 QQQ 與 SPY(D-010 第 4 條、D-020 第 8 條)。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from ..data.snapshots import read_price_panel, read_universe
from ..errors import NotFound
from ..runs.window import BASE, WindowStats, window_stats
from ..store import DefinitionStore

# 基準一律這兩隻(D-010 第 4 條、D-020 第 8 條、規格 8.4)
DEFAULT_BENCHMARK_TICKERS: tuple[str, ...] = ("QQQ", "SPY")


@dataclass(frozen=True, slots=True)
class BenchmarkCurve:
    """一條基準的買入持有結果。

    ``stats`` 與運行那邊用同一個 ``WindowStats``:同一套累計回報、年化、最大回撤
    的算法,兩邊才比得過。
    """

    ticker: str
    entity_id: int
    snapshot_id: str
    stats: WindowStats

    @property
    def equity(self) -> pd.Series:
        """買入持有的淨值線,已由視窗起始日重設為 100。"""
        return self.stats.equity


def benchmark_entity_id(
    store: DefinitionStore,
    snapshot_id: str,
    ticker: str,
    *,
    root: str | Path | None = None,
) -> int:
    """基準代號在**這個快照**裡是哪一個實體編號。

    查的是連同快照一併凍結的宇宙名單,不是今日的代號映射——代號會被回收再發給
    別人(D-026 第 2 條),用今日的映射去讀舊快照就會讀錯一隻。
    """
    symbol = str(ticker or "").strip().upper()
    universe = read_universe(store, snapshot_id, root=root)
    matched = universe.loc[universe["ticker"].str.upper() == symbol]
    if matched.empty:
        raise NotFound(
            f"快照 {snapshot_id} 的宇宙名單裡沒有基準 {symbol};"
            f"名單有:{'、'.join(sorted(universe['ticker']))}"
        )
    return int(matched.iloc[0]["entity_id"])


def benchmark_close(
    store: DefinitionStore,
    snapshot_id: str,
    ticker: str,
    *,
    root: str | Path | None = None,
) -> tuple[int, pd.Series]:
    """基準的逐日收市價(已調整價,D-026 第 4 條),連它的實體編號。

    留空的日子(停牌、未上市)直接略去,不前填——買入持有沒有那一日的價,
    就是那一日不在這條線上。
    """
    entity_id = benchmark_entity_id(store, snapshot_id, ticker, root=root)
    panel = read_price_panel(
        store, snapshot_id, field="close", root=root, entity_ids=[entity_id]
    )
    series = panel[entity_id].dropna()
    if series.empty:
        raise NotFound(f"快照 {snapshot_id} 裡的 {ticker} 一日收市價都沒有")
    return entity_id, series.rename("equity")


def benchmark_curve(
    store: DefinitionStore,
    snapshot_id: str,
    ticker: str,
    start: date | datetime | str | None = None,
    end: date | datetime | str | None = None,
    *,
    root: str | Path | None = None,
    base: float = BASE,
) -> BenchmarkCurve:
    """一條基準在指定一段日子的買入持有結果。

    起訖與運行的檢視視窗用同一對日期,兩邊的累計回報、年化、最大回撤就比得過。
    基準有沒有那一日的日線與運行的交易日曆無關——基準走自己的日子,只要頭尾
    夾在同一段之內。
    """
    entity_id, close = benchmark_close(store, snapshot_id, ticker, root=root)
    return BenchmarkCurve(
        ticker=str(ticker).strip().upper(),
        entity_id=entity_id,
        snapshot_id=str(snapshot_id).strip(),
        stats=window_stats(close, start, end, base=base),
    )
