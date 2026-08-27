"""主日曆與停牌處置。

主日曆(master calendar)= SPY 有成交的日子。全部實體對齊到這條日曆上,
免得「甲股沒有這一日」與「乙股有這一日」在同一張面板裡各自為政。

停牌處置(明文,規格 10.4):
  1. **缺日不填補、留空**——沒有成交的日子不捏造成交價。
  2. 對齊主日曆時,最多以前值填補 **3 個交易日**;超過 3 日一律留 NaN。
  3. 每一根日線自報身分:``actual`` 真有成交 / ``filled`` 前值填補 / ``missing`` 留空。
     所以「哪一根是填出來的」在數據上驗得到,不必翻文件。
  4. 填補出來的那一根寫成 O=H=L=C=前一根收市價、成交量 0——沒有交易就是沒有交易,
     不把上一日的成交量抄過來。
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from .sources import PRICE_FIELDS

# 對齊主日曆時的前值填補上限(交易日)
FFILL_LIMIT = 3

BAR_ACTUAL = "actual"
BAR_FILLED = "filled"
BAR_MISSING = "missing"

PANEL_COLUMNS: tuple[str, ...] = ("date", "entity_id", *PRICE_FIELDS, "bar_status")


def trading_calendar(bars: pd.DataFrame, calendar_ticker: str) -> tuple[str, ...]:
    """由主日曆代號真正有成交的日子取出交易日曆。"""
    symbol = str(calendar_ticker).strip().upper()
    days = bars.loc[bars["ticker"].str.upper() == symbol, "date"]
    if days.empty:
        raise ValueError(f"主日曆代號 {symbol} 在這批數據裡一日都沒有,無法定日曆")
    return tuple(sorted(set(days.astype(str))))


def align_to_calendar(
    bars: pd.DataFrame,
    calendar: Sequence[str],
    *,
    ffill_limit: int = FFILL_LIMIT,
) -> pd.DataFrame:
    """把「日期 × 實體編號」的日線對齊到主日曆,並標明每根日線的身分。

    入表要有 ``date`` / ``entity_id`` 與五個價量欄;出表逐日逐實體齊全
    (缺的那格留 NaN 並標 ``missing``),按日期、實體編號排序。
    """
    days = pd.Index(sorted(set(str(day) for day in calendar)), name="date")
    if days.empty:
        raise ValueError("主日曆是空的,無法對齊")

    blocks: list[pd.DataFrame] = []
    for entity_id, block in bars.groupby("entity_id", sort=True):
        block = (
            block.drop_duplicates(subset="date", keep="last")
            .set_index("date")
            .sort_index()
            .reindex(days)
        )
        actual = block["close"].notna().to_numpy()
        carried = block["close"].ffill(limit=ffill_limit)
        filled = carried.notna().to_numpy() & ~actual

        aligned = pd.DataFrame(index=days)
        carried_values = carried.to_numpy(dtype="float64")
        for field in PRICE_FIELDS:
            original = block[field].to_numpy(dtype="float64")
            if field == "volume":
                # 停牌日沒有交易:成交量是 0,不是抄上一日
                aligned[field] = np.where(actual, original, np.where(filled, 0.0, np.nan))
            else:
                aligned[field] = np.where(
                    actual, original, np.where(filled, carried_values, np.nan)
                )
        aligned["bar_status"] = np.where(
            actual, BAR_ACTUAL, np.where(filled, BAR_FILLED, BAR_MISSING)
        )
        aligned.insert(0, "entity_id", int(entity_id))
        blocks.append(aligned.reset_index())

    if not blocks:
        return pd.DataFrame({column: pd.Series(dtype="object") for column in PANEL_COLUMNS})

    panel = pd.concat(blocks, ignore_index=True)
    panel["entity_id"] = panel["entity_id"].astype("int64")
    panel["date"] = panel["date"].astype("object")
    panel["bar_status"] = panel["bar_status"].astype("object")
    for field in PRICE_FIELDS:
        panel[field] = panel[field].astype("float64")
    return (
        panel.loc[:, list(PANEL_COLUMNS)]
        .sort_values(["date", "entity_id"])
        .reset_index(drop=True)
    )
