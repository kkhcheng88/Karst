# -*- coding: utf-8 -*-
"""抓 SPY 日線落 data/prices/spy_daily.csv。

價格庫 data/prices/daily/ 刻意不收 ETF(RULES.md 的 I3:沒有年報),所以 SPY 要另抓。
參數照日線價格庫 README 第四節:yfinance、auto_adjust=False、actions=False。
"""
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(r"C:\projects\Karst")
OUT = ROOT / "data" / "prices" / "spy_daily.csv"

def main():
    df = yf.download(
        "SPY",
        start="2007-01-01",
        end=None,
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )
    if df is None or len(df) == 0:
        print("FAIL: yfinance 回空表")
        sys.exit(1)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    keep = ["date", "open", "high", "low", "close", "adj_close", "volume"]
    df = df[[c for c in keep if c in df.columns]]
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"rows={len(df)} first={df['date'].iloc[0]} last={df['date'].iloc[-1]}")
    print(f"wrote {OUT}")

if __name__ == "__main__":
    main()
