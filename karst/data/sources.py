"""來源適配器(source adapter)。

D-026 第 7 條:每個來源一個適配器,輸出同一套欄位,經同一條管線入快照;
來源名記在快照內。適配器只負責「把外面的形狀搬成我們的形狀」,不做對齊、
不做實體解析、不做凍結——那三件是管線的事。

統一輸出(一列一根日線,代號此時仍未解析成實體編號):

    date(YYYY-MM-DD 字串) / ticker / open / high / low / close / volume

價格一律是**已調整價**(D-026 第 4 條):除權除息由來源的 auto_adjust 處理,
本倉不自建除權除息事件表。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Protocol, runtime_checkable

import pandas as pd

from ..models import as_date
from .errors import DataFetchFailed

PRICE_FIELDS: tuple[str, ...] = ("open", "high", "low", "close", "volume")
BAR_COLUMNS: tuple[str, ...] = ("date", "ticker", *PRICE_FIELDS)


@runtime_checkable
class PriceSource(Protocol):
    """日線來源的合約。"""

    name: str

    def fetch_daily_bars(
        self,
        tickers: Sequence[str],
        start: date | datetime | str,
        end: date | datetime | str,
    ) -> pd.DataFrame:
        """抓一批日線,起訖含頭含尾。缺任何一個代號即拋 ``DataFetchFailed``。"""
        ...


def _empty_bars() -> pd.DataFrame:
    return pd.DataFrame({column: pd.Series(dtype="object") for column in BAR_COLUMNS})


def _check_complete(frame: pd.DataFrame, tickers: Sequence[str], source_name: str) -> None:
    wanted = [t.strip().upper() for t in tickers]
    got = set(frame.loc[frame["close"].notna(), "ticker"].unique())
    missing = [t for t in wanted if t not in got]
    if missing:
        raise DataFetchFailed(
            f"{source_name} 沒有回這幾個代號的日線:{'、'.join(missing)};"
            "抓取失敗不當作「該股不參與」,請重試或修正名單"
        )


class YFinanceSource:
    """yfinance 日線適配器(D-026 第 5 條:價格與日曆由 yfinance)。

    一律 ``auto_adjust=True``——存已調整價、不存當日真實成交價;
    ``actions=False`` 不取事件表,``threads=False`` 照舊倉用法免併發亂序。
    """

    name = "yfinance"
    auto_adjust = True

    def __init__(self, *, timeout: float = 60.0) -> None:
        self.timeout = timeout

    def fetch_daily_bars(
        self,
        tickers: Sequence[str],
        start: date | datetime | str,
        end: date | datetime | str,
    ) -> pd.DataFrame:
        try:
            import yfinance  # noqa: PLC0415 - 只在真正抓數時才需要
        except ImportError as exc:  # pragma: no cover - 未裝套件的環境
            raise DataFetchFailed(f"未安裝 yfinance:{exc}") from exc

        wanted = [str(t).strip().upper() for t in tickers if str(t).strip()]
        if not wanted:
            raise DataFetchFailed("代號名單是空的,無數可抓")

        first = as_date(start, "start")
        last = as_date(end, "end")
        # yfinance 的 end 不含尾,加一日換成「含頭含尾」
        end_exclusive = (date.fromisoformat(last) + timedelta(days=1)).isoformat()

        try:
            raw = yfinance.download(
                wanted,
                start=first,
                end=end_exclusive,
                interval="1d",
                auto_adjust=self.auto_adjust,
                actions=False,
                threads=False,
                progress=False,
                group_by="column",
            )
        except Exception as exc:  # noqa: BLE001 - 對外抓取的錯一律歸一
            raise DataFetchFailed(f"yfinance 抓取失敗({type(exc).__name__}: {exc})") from exc

        if raw is None or raw.empty:
            raise DataFetchFailed(
                f"yfinance 在 {first}~{last} 對 {'、'.join(wanted)} 回了空批次;"
                "空批次一律當失敗,不當作「這段日子沒有交易」"
            )

        frame = _normalise_yfinance(raw, wanted)
        _check_complete(frame, wanted, self.name)
        return frame


def _normalise_yfinance(raw: pd.DataFrame, tickers: Sequence[str]) -> pd.DataFrame:
    """把 yfinance 的寬表(單層或雙層欄)搬成統一的長表。"""
    blocks: list[pd.DataFrame] = []
    multi = isinstance(raw.columns, pd.MultiIndex)
    index = pd.DatetimeIndex(raw.index)
    days = index.strftime("%Y-%m-%d")

    for ticker in tickers:
        columns: dict[str, pd.Series] = {}
        for field in PRICE_FIELDS:
            label = field.capitalize()
            if multi:
                key = (label, ticker)
                if key not in raw.columns:
                    columns = {}
                    break
                series = raw[key]
            else:
                if label not in raw.columns:
                    columns = {}
                    break
                series = raw[label]
            columns[field] = pd.Series(series.to_numpy(), dtype="float64")
        if not columns:
            continue
        block = pd.DataFrame(columns)
        block.insert(0, "ticker", ticker)
        block.insert(0, "date", pd.Series(days, dtype="object"))
        blocks.append(block.loc[block["close"].notna()])

    if not blocks:
        return _empty_bars()
    frame = pd.concat(blocks, ignore_index=True)
    return frame.loc[:, list(BAR_COLUMNS)].sort_values(["date", "ticker"]).reset_index(drop=True)


class StaticSource:
    """離線來源:照給定的長表回數。

    用途有二:測試不必連網;日後要由別的來源(CSV、另一個 API)重放同一批數,
    照這個形狀餵進同一條管線即可——這正是 D-026 第 7 條的適配器形態。
    """

    auto_adjust = True

    def __init__(self, bars: pd.DataFrame, *, name: str = "static") -> None:
        missing = [column for column in BAR_COLUMNS if column not in bars.columns]
        if missing:
            raise ValueError(f"靜態來源缺欄位:{'、'.join(missing)}")
        self.name = name
        self._bars = bars.loc[:, list(BAR_COLUMNS)].copy()
        self._bars["date"] = self._bars["date"].map(lambda value: as_date(value, "date"))
        self._bars["ticker"] = self._bars["ticker"].str.strip().str.upper()

    def fetch_daily_bars(
        self,
        tickers: Sequence[str],
        start: date | datetime | str,
        end: date | datetime | str,
    ) -> pd.DataFrame:
        wanted = [str(t).strip().upper() for t in tickers]
        first, last = as_date(start, "start"), as_date(end, "end")
        frame = self._bars.loc[
            self._bars["ticker"].isin(wanted)
            & (self._bars["date"] >= first)
            & (self._bars["date"] <= last)
        ].copy()
        _check_complete(frame, wanted, self.name)
        return frame.sort_values(["date", "ticker"]).reset_index(drop=True)
