"""KARST-167 步驟三:一次現價快照(yfinance),用來乘封面頁股數得近似市值。

票面明文:本票**不抓價格歷史**,只抓一次現價快照。所以這裡取的是最近一根日線的收市價,
逐批下載,存 data/universe/price_snapshot_<日期>.csv 連日期。

不入任何寬表、不做任何時間序列運算。
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date

import pandas as pd
import yfinance as yf

REPO = r"C:\projects\Karst"
TICKERS = os.path.join(REPO, "data", "sec", "company_tickers.json")
OUTDIR = os.path.join(REPO, "data", "universe")
CHUNK = 200


def main() -> int:
    os.makedirs(OUTDIR, exist_ok=True)
    with open(TICKERS, "r", encoding="utf-8") as fh:
        tmap = json.load(fh)
    symbols = sorted(tmap.keys())
    print(f"symbols={len(symbols)}", flush=True)

    rows: list[dict[str, object]] = []
    started = time.time()
    for i in range(0, len(symbols), CHUNK):
        batch = symbols[i:i + CHUNK]
        try:
            frame = yf.download(
                batch, period="5d", interval="1d", group_by="column",
                auto_adjust=False, progress=False, threads=True, timeout=60,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"batch {i} failed {type(exc).__name__}", flush=True)
            continue
        if frame is None or frame.empty:
            print(f"batch {i} empty", flush=True)
            continue
        try:
            close = frame["Close"]
        except Exception:  # noqa: BLE001
            continue
        if isinstance(close, pd.Series):
            close = close.to_frame(batch[0])
        for sym in close.columns:
            series = close[sym].dropna()
            if series.empty:
                continue
            rows.append({
                "ticker": str(sym),
                "close": float(series.iloc[-1]),
                "price_date": str(series.index[-1].date()),
            })
        done = min(i + CHUNK, len(symbols))
        print(f"progress {done}/{len(symbols)} priced={len(rows)} "
              f"{(time.time() - started) / 60:.1f}min", flush=True)

    out = pd.DataFrame(rows).drop_duplicates(subset="ticker")
    snapshot_day = date.today().isoformat()
    path = os.path.join(OUTDIR, f"price_snapshot_{snapshot_day}.csv")
    out.to_csv(path, index=False)
    print(f"written {path} rows={len(out)} of {len(symbols)}", flush=True)
    print(f"elapsed_minutes={(time.time() - started) / 60:.1f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
