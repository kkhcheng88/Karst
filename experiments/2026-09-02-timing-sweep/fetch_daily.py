"""KARST-145: fetch daily adjusted closes for the panel universe via yfinance.

Batch download, capped retries, failure log. Writes parquet to data/ (not in git).

Usage:
  python fetch_daily.py --tickers tickers.txt --out data/daily_close.parquet
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent

BATCH = 60
MAX_RETRIES = 3          # hard cap, written down before any download
RETRY_SLEEP = 5.0        # seconds
START = "2004-01-01"     # extra year of warm-up before the 2005 study window
END = "2026-09-02"


def download_batch(tickers, start, end):
    """Return (close_df, ok_list). Raises on total failure."""
    df = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,      # split+dividend adjusted -> total-return series
        progress=False,
        threads=4,             # bounded concurrency
        group_by="column",
        actions=False,
    )
    if df is None or len(df) == 0:
        return pd.DataFrame(), []
    if isinstance(df.columns, pd.MultiIndex):
        close = df["Close"]
    else:
        close = df[["Close"]].rename(columns={"Close": tickers[0]})
    close = close.dropna(axis=1, how="all")
    return close, list(close.columns)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", default=START)
    ap.add_argument("--end", default=END)
    args = ap.parse_args()

    tick_path = Path(args.tickers)
    tickers = [t.strip() for t in tick_path.read_text(encoding="utf-8").splitlines() if t.strip()]
    tickers = sorted(set(tickers))
    print(f"universe size: {len(tickers)}", flush=True)

    frames = []
    failed = []
    for i in range(0, len(tickers), BATCH):
        chunk = tickers[i:i + BATCH]
        got = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                close, ok = download_batch(chunk, args.start, args.end)
                got = close
                break
            except Exception as exc:  # noqa: BLE001
                print(f"  batch {i//BATCH} attempt {attempt} failed: {exc}", flush=True)
                if attempt == MAX_RETRIES:
                    got = pd.DataFrame()
                else:
                    time.sleep(RETRY_SLEEP)
        if got is None or got.empty:
            failed.extend(chunk)
            print(f"  batch {i//BATCH}: ALL FAILED ({len(chunk)})", flush=True)
            continue
        missing = [t for t in chunk if t not in got.columns]
        failed.extend(missing)
        frames.append(got)
        print(f"  batch {i//BATCH}: got {got.shape[1]}/{len(chunk)}, rows {got.shape[0]}", flush=True)

    if not frames:
        print("nothing downloaded", file=sys.stderr)
        sys.exit(1)

    panel = pd.concat(frames, axis=1).sort_index()
    panel = panel.loc[:, ~panel.columns.duplicated()]
    panel.index = pd.to_datetime(panel.index).tz_localize(None)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(out)

    meta = {
        "requested": len(tickers),
        "downloaded": int(panel.shape[1]),
        "failed_count": len(failed),
        "failed": sorted(failed),
        "first_date": str(panel.index.min().date()),
        "last_date": str(panel.index.max().date()),
        "rows": int(panel.shape[0]),
        "auto_adjust": True,
        "max_retries": MAX_RETRIES,
        "batch_size": BATCH,
    }
    (out.parent / (out.stem + "_meta.json")).write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in meta.items() if k != "failed"}, indent=2))


if __name__ == "__main__":
    main()
