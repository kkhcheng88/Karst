"""KARST-167 步驟三之二:補抓第一次現價快照被 yfinance 限流打回的代號。

第一次跑用 200 個一批、無退讓,結果被 Too Many Requests 打回大半。這裡改為
小批 + 指數退讓 + 多輪,只補仍然缺價的代號,結果併回同一個快照檔。
仍然只取最近一根日線的收市價,不取歷史。
"""

from __future__ import annotations

import glob
import json
import os
import random
import sys
import time
from datetime import date

import pandas as pd
import yfinance as yf

REPO = r"C:\projects\Karst"
UNIVERSE = os.path.join(REPO, "data", "universe")
CHUNK = 40
ROUNDS = 4


def load_snapshot() -> tuple[pd.DataFrame, str]:
    snaps = sorted(glob.glob(os.path.join(UNIVERSE, "price_snapshot_*.csv")))
    if snaps:
        return pd.read_csv(snaps[-1]), snaps[-1]
    return (pd.DataFrame(columns=["ticker", "close", "price_date"]),
            os.path.join(UNIVERSE, f"price_snapshot_{date.today().isoformat()}.csv"))


def wanted() -> list[str]:
    """優先補宇宙名單內的主代號;沒有實體表就用整份代號表。"""
    ent = os.path.join(UNIVERSE, "entities.parquet")
    if os.path.exists(ent):
        frame = pd.read_parquet(ent, columns=["all_tickers"])
        out: set[str] = set()
        for row in frame["all_tickers"]:
            out.update(str(row).split("|"))
        return sorted(t for t in out if t)
    with open(os.path.join(REPO, "data", "sec", "company_tickers.json"), "r", encoding="utf-8") as fh:
        return sorted(json.load(fh).keys())


def main() -> int:
    snap, path = load_snapshot()
    have = set(snap["ticker"].astype(str))
    targets = [t for t in wanted() if t not in have]
    print(f"already_priced={len(have)} to_retry={len(targets)}", flush=True)

    rows: list[dict[str, object]] = []
    for rnd in range(ROUNDS):
        if not targets:
            break
        print(f"--- round {rnd + 1} targets={len(targets)} ---", flush=True)
        still: list[str] = []
        for i in range(0, len(targets), CHUNK):
            batch = targets[i:i + CHUNK]
            got: set[str] = set()
            try:
                frame = yf.download(batch, period="5d", interval="1d", group_by="column",
                                    auto_adjust=False, progress=False, threads=False, timeout=60)
                if frame is not None and not frame.empty and "Close" in frame:
                    close = frame["Close"]
                    if isinstance(close, pd.Series):
                        close = close.to_frame(batch[0])
                    for sym in close.columns:
                        series = close[sym].dropna()
                        if series.empty:
                            continue
                        rows.append({"ticker": str(sym), "close": float(series.iloc[-1]),
                                     "price_date": str(series.index[-1].date())})
                        got.add(str(sym))
            except Exception as exc:  # noqa: BLE001
                print(f"  batch {i} {type(exc).__name__}", flush=True)
            still.extend([t for t in batch if t not in got])
            time.sleep(1.2 + random.random() * 0.8)
            if (i // CHUNK) % 20 == 0:
                print(f"  {i}/{len(targets)} newly_priced={len(rows)}", flush=True)
        targets = still
        if targets:
            time.sleep(20 * (rnd + 1))

    if rows:
        add = pd.DataFrame(rows)
        snap = pd.concat([snap, add], ignore_index=True).drop_duplicates(subset="ticker")
    snap.to_csv(path, index=False)
    print(f"written {path} rows={len(snap)} still_missing={len(targets)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
