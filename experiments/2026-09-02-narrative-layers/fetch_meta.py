"""KARST-152 步驟 0:抓 574 隻股票的板塊(sector)與子行業(industry)近似。

倉內沒有現成 GICS 歸屬表,依 CRITERIA.md 第 1 節用 yfinance info 作近似。
落檔 out/ticker_meta.json,失敗名單一併記錄。

Run: PYTHONUTF8=1 python fetch_meta.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

PARQUET = Path(r"C:\projects\Karst\experiments\2026-09-02-timing-sweep\data\daily_close.parquet")
ETFS = {"SPY", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"}


def main() -> int:
    df = pd.read_parquet(PARQUET)
    tickers = sorted(c for c in df.columns if c not in ETFS)
    print(f"universe: {len(tickers)} stocks")

    dest = OUT / "ticker_meta.json"
    meta: dict[str, dict] = {}
    if dest.exists():
        meta = json.loads(dest.read_text(encoding="utf-8"))

    failed = []
    for i, t in enumerate(tickers, 1):
        if t in meta and meta[t].get("sector"):
            continue
        try:
            info = yf.Ticker(t).info
            meta[t] = {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "shortName": info.get("shortName"),
                "longName": info.get("longName"),
            }
        except Exception as exc:  # noqa: BLE001
            failed.append(t)
            meta[t] = {"sector": None, "industry": None, "error": str(exc)[:200]}
        if i % 25 == 0:
            print(f"  {i}/{len(tickers)}", flush=True)
            dest.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(0.15)

    dest.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    have = sum(1 for v in meta.values() if v.get("industry"))
    print(f"done: {have}/{len(tickers)} have industry; failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
