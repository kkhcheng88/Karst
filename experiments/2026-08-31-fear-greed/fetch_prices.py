"""KARST-120 取數:九隻 SPDR 板塊 ETF 與 SPY 的日線含息價。

沿用 KARST-119 同一套規矩(D-026 第 5 條:價格由 yfinance),
價格取已調整價(含息)。屬探索性數據,只落 experiments/,不入生產庫。
原始日線檔不入 git(照 KARST-113 先例),跑一次本腳本即重新生成。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

OUT = Path(__file__).resolve().parent
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
EXTRA = ["SPY"]
START = "1998-12-01"
END = "2026-08-31"


def main() -> int:
    tickers = SECTORS + EXTRA
    raw = yf.download(
        tickers,
        start=START,
        end=END,
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=False,
    )
    if raw is None or len(raw) == 0:
        print("empty batch, download failed")
        return 1

    frames = []
    for field in ("Open", "Close"):
        block = raw[field]
        long = block.stack(future_stack=True).rename(field.lower())
        frames.append(long)
    out = pd.concat(frames, axis=1).reset_index()
    out.columns = ["date", "ticker", "open", "close"]
    out = out.dropna(subset=["open", "close"])
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None)
    out = out.sort_values(["ticker", "date"]).reset_index(drop=True)
    out.to_parquet(OUT / "prices_daily.parquet", index=False)

    cover = out.groupby("ticker")["date"].agg(["min", "max", "count"])
    print(cover.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
