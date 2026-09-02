"""KARST-157 步驟 1:新增代碼的 yfinance meta 與日線(零回報計算)。

- meta:sector / industry / quoteType / 名稱,落 out/ticker_meta_new.json。
  574 家那批直接沿用 KARST-152 的 out/ticker_meta.json,不重抓(等價重用)。
- 日線:auto_adjust=True,窗口對齊既有 parquet(2004-01-01 ~ 2026-09-02),
  落 data/new_close.parquet(gitignore 擋住)。

Run: PYTHONUTF8=1 python fetch_new_data.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DATA = HERE / "data"
OUT.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

START = "2004-01-01"
END = "2026-09-02"
BATCH = 50
MAX_RETRIES = 3
RETRY_SLEEP = 5.0


def fetch_meta(tickers: list[str]) -> dict[str, dict]:
    dest = OUT / "ticker_meta_new.json"
    meta: dict[str, dict] = {}
    if dest.exists():
        meta = json.loads(dest.read_text(encoding="utf-8"))
    for i, t in enumerate(tickers, 1):
        if t in meta and meta[t].get("fetched"):
            continue
        try:
            info = yf.Ticker(t).info
            meta[t] = {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "shortName": info.get("shortName"),
                "longName": info.get("longName"),
                "quoteType": info.get("quoteType"),
                "fetched": True,
            }
        except Exception as exc:  # noqa: BLE001
            meta[t] = {"sector": None, "industry": None, "quoteType": None,
                       "error": str(exc)[:200], "fetched": True}
        if i % 25 == 0:
            print(f"  meta {i}/{len(tickers)}", flush=True)
            dest.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(0.12)
    dest.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def download_batch(tickers: list[str]) -> pd.DataFrame:
    df = yf.download(tickers, start=START, end=END, auto_adjust=True, progress=False,
                     threads=4, group_by="column", actions=False)
    if df is None or len(df) == 0:
        return pd.DataFrame()
    close = df["Close"] if isinstance(df.columns, pd.MultiIndex) else \
        df[["Close"]].rename(columns={"Close": tickers[0]})
    return close.dropna(axis=1, how="all")


def fetch_prices(tickers: list[str]) -> tuple[pd.DataFrame, list[str]]:
    frames, failed = [], []
    for i in range(0, len(tickers), BATCH):
        chunk = tickers[i:i + BATCH]
        got = pd.DataFrame()
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                got = download_batch(chunk)
                break
            except Exception as exc:  # noqa: BLE001
                print(f"  batch {i//BATCH} attempt {attempt}: {exc}", flush=True)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_SLEEP)
        if got.empty:
            failed.extend(chunk)
            continue
        failed.extend([t for t in chunk if t not in got.columns])
        frames.append(got)
        print(f"  prices batch {i//BATCH}: {got.shape[1]}/{len(chunk)}", flush=True)
    if not frames:
        return pd.DataFrame(), failed
    panel = pd.concat(frames, axis=1).sort_index()
    panel = panel.loc[:, ~panel.columns.duplicated()]
    panel.index = pd.to_datetime(panel.index).tz_localize(None)
    return panel, sorted(failed)


def main() -> int:
    uni = json.loads((OUT / "universe_v2.json").read_text(encoding="utf-8"))
    new = uni["new_tickers"]
    print(f"new tickers: {len(new)}", flush=True)

    meta = fetch_meta(new)
    non_equity = sorted(t for t in new if (meta.get(t) or {}).get("quoteType") not in (None, "EQUITY"))
    print(f"non-equity dropped: {len(non_equity)} {non_equity}", flush=True)

    to_price = [t for t in new if t not in set(non_equity)]
    panel, failed = fetch_prices(to_price)
    if not panel.empty:
        panel.to_parquet(DATA / "new_close.parquet")

    summary = {
        "new_requested": len(new),
        "non_equity_dropped": non_equity,
        "priced_requested": len(to_price),
        "priced_ok": int(panel.shape[1]) if not panel.empty else 0,
        "price_missing": failed,
        "first_date": str(panel.index.min().date()) if not panel.empty else None,
        "last_date": str(panel.index.max().date()) if not panel.empty else None,
        "rows": int(panel.shape[0]) if not panel.empty else 0,
        "auto_adjust": True,
        "window": [START, END],
    }
    (OUT / "new_price_meta.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "price_missing"}, indent=1))
    print(f"price_missing ({len(failed)}): {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
