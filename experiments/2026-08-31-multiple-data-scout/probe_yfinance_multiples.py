"""KARST-121 樣本驗證:yfinance 的倍數欄位到底給到什麼。

要答的一條事實:免費而且本倉已經在用的 yfinance,能不能供倍數情緒儀用?
量度方式很簡單——同一個代號抓兩次沒有意義,關鍵是「它有沒有歷史」。
本腳本只抓一次快照,把欄位原樣寫出,證明它給的是「今日一個數」而不是序列。

跑法(Windows PowerShell):
    $env:PYTHONUTF8 = "1"; python probe_yfinance_multiples.py

輸出:yfinance_multiples_snapshot.json(小檔,故意放實驗目錄根部——
`experiments/*/data/` 已被 .gitignore 擋走,大檔才放那裡)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

# 十一隻 SPDR 行業 ETF(本倉 SECTOR_ETF_UNIVERSE)加 SPY,再加兩隻個股作對照
SECTOR_ETFS = ("XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC")
PROBE_TICKERS = ("SPY", *SECTOR_ETFS, "AAPL", "NVDA")

# 倍數情緒儀關心的欄位:trailing 與 forward 兩邊都問,看哪邊有數
FIELDS = (
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "priceToSalesTrailing12Months",
    "trailingEps",
    "forwardEps",
    "enterpriseToRevenue",
    "enterpriseToEbitda",
)


def probe() -> dict:
    rows = {}
    for ticker in PROBE_TICKERS:
        try:
            info = yf.Ticker(ticker).info
        except Exception as exc:  # noqa: BLE001 - 勘察腳本,失手記低就算
            rows[ticker] = {"error": repr(exc)}
            continue
        rows[ticker] = {field: info.get(field) for field in FIELDS}
    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": (
            "yfinance 的 info 只給當下一個數,沒有任何歷史序列;"
            "本檔本身就是一個 vintage 快照——今日開始逐日儲存,才會慢慢長成 point-in-time 序列。"
        ),
        "fields": list(FIELDS),
        "rows": rows,
    }


def main() -> None:
    out_dir = Path(__file__).parent
    result = probe()
    out_path = out_dir / "yfinance_multiples_snapshot.json"
    out_path.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    have_forward = sum(1 for r in result["rows"].values() if r.get("forwardPE") is not None)
    have_trailing = sum(1 for r in result["rows"].values() if r.get("trailingPE") is not None)
    print(f"抓了 {len(result['rows'])} 個代號")
    print(f"有 trailingPE 的:{have_trailing}")
    print(f"有 forwardPE 的:{have_forward}")
    print(f"落檔:{out_path}")


if __name__ == "__main__":
    main()
