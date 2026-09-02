# -*- coding: utf-8 -*-
"""KARST-154 原料抓取:FRED 免費 CSV 端點 + yfinance 價格。

FRED 端點:https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>&cosd=1900-01-01
(公開下載,無需鑰匙。實測 vintage_date 參數被伺服器忽略,故本票用保守公布滯後,
 不用實時版本 —— 見 CRITERIA.md §2。)
"""
import io
import json
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

FRED_SERIES = [
    "UNRATE",                    # 失業率,月,1948-
    "ICSA",                      # 初請失業金,週,1967-
    "T10Y3M",                    # 10 年減 3 個月,日,1982-
    "DBAA",                      # 穆迪 Baa 企業債殖利率,日,1986-
    "DAAA",                      # 穆迪 Aaa 企業債殖利率,日,1983-
    "GACDFSA066MSFRBPHI",        # 費城聯儲製造業現況指數,月,1968-(ISM 替代)
    "RRSFS",                     # 實質零售與餐飲銷售,月,1992-
    "DTB3",                      # 3 個月國庫券,日,1954-(無風險利率)
]

TICKERS = {
    "SP500TR": "^SP500TR",
    "SPY": "SPY",
    "XLK": "XLK",
    "GSPC": "^GSPC",
}


def fred(series_id: str) -> pd.Series:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd=1900-01-01"
    raw = urllib.request.urlopen(url, timeout=60).read().decode()
    df = pd.read_csv(io.StringIO(raw))
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    s = pd.to_numeric(df[series_id], errors="coerce")
    s.index = df[date_col]
    s.name = series_id
    return s.dropna()


def main() -> None:
    frames = {}
    meta = {}
    for sid in FRED_SERIES:
        s = fred(sid)
        frames[sid] = s
        meta[sid] = {"rows": int(len(s)), "first": str(s.index[0].date()), "last": str(s.index[-1].date())}
        print(f"FRED {sid:24s} {len(s):6d}  {s.index[0].date()} -> {s.index[-1].date()}")

    for sid, s in frames.items():
        s.to_frame().to_csv(OUT / f"fred_{sid}.csv")

    import yfinance as yf

    px = {}
    for name, tk in TICKERS.items():
        d = yf.download(tk, start="1985-01-01", end="2026-09-02", auto_adjust=True, progress=False)
        close = d["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.dropna()
        close.name = name
        px[name] = close
        meta[name] = {"rows": int(len(close)), "first": str(close.index[0].date()), "last": str(close.index[-1].date())}
        print(f"YF   {name:24s} {len(close):6d}  {close.index[0].date()} -> {close.index[-1].date()}")

    prices = pd.DataFrame(px)
    prices.index.name = "date"
    prices.to_csv(OUT / "prices.csv")

    (OUT / "fetch_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("寫入", OUT)


if __name__ == "__main__":
    main()
