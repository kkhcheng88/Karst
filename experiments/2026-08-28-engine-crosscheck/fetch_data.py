"""KARST-059 第一步:抓日線落本目錄的 CSV。

**不入定義庫、不寫 data/、不碰 karst.sqlite。** 這一票的整條路徑只用記憶體內的
面板呼叫引擎,所以數據就住在本目錄,誰都看得見、誰都覆算得到。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-engine-crosscheck/fetch_data.py

取值:``auto_adjust=True``,即除權除息還原後的已調整價——與倉內快照同一個口徑
(``rules.BarPanel`` 那段浮點尾數註解講的就是這種價)。
"""

from __future__ import annotations

from pathlib import Path

import yfinance as yf

HERE = Path(__file__).resolve().parent

# 規則路徑取 AAPL。票的窗口是 2023-01-03~2023-03-31;多抓半年是為了讓
# 50 日突破回望在窗口第一根就已經滿額(不然窗口前三分之二根本發不出訊號)。
# 多抓的那半年只做回望暖身,對照本身兩邊都跑同一面板,不影響結論。
RULE_TICKER = "AAPL"
RULE_START = "2022-06-01"
RULE_END = "2023-04-01"        # yfinance 的 end 不含當日

# 排名路徑取兩隻 ETF。
RANK_TICKERS = ("SPY", "QQQ")
RANK_START = "2022-09-01"
RANK_END = "2023-04-01"


def grab(ticker: str, start: str, end: str) -> None:
    frame = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        actions=False,
    )
    if isinstance(frame.columns, type(frame.columns)) and frame.columns.nlevels > 1:
        frame.columns = frame.columns.droplevel(-1)   # yfinance 1.3 的雙層欄名
    frame = frame[["Open", "High", "Low", "Close"]].astype(float)
    frame.index.name = "date"
    out = HERE / f"{ticker}.csv"
    frame.to_csv(out, float_format="%.10f")
    print(f"{ticker}: {len(frame)} 根 K 線 {frame.index[0].date()} ~ {frame.index[-1].date()} -> {out.name}")


def main() -> None:
    grab(RULE_TICKER, RULE_START, RULE_END)
    for ticker in RANK_TICKERS:
        grab(ticker, RANK_START, RANK_END)


if __name__ == "__main__":
    main()
