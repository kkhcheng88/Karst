"""KARST-171 步驟二:對 ticker_periods.parquet 全部代號時段抓 yfinance 日線 OHLCV。

規矩(KARST-167 實測):40 個一批、批與批之間 1.2–2 秒退讓。
一批之內失敗的代號,整批跑完之後單獨重試一次;仍然失敗即入 failed.csv,不無限重試。

輸出(全部住 data/,已被 gitignore):
  data/prices/_parts/batch_XXXX.parquet   每批一個,供中斷續跑
  data/prices/_parts/batch_XXXX.json      每批的逐代號狀態

口徑:auto_adjust=False。開高低收是拆股調整後、未除息調整;adj_close 是拆股加除息調整。
生產線 D-026 的 adjusted-close-only 口徑 = 本庫的 adj_close。
"""

import json
import random
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(r"C:\projects\Karst")
UNI = ROOT / "data" / "universe"
PARTS = ROOT / "data" / "prices" / "_parts"
BATCH = 40
TODAY = date.today().isoformat()
FIELDS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


def load_periods() -> pd.DataFrame:
    tp = pd.read_parquet(UNI / "ticker_periods.parquet")
    tp = tp.copy()
    tp["valid_to_eff"] = tp["valid_to"].fillna("")
    tp.loc[tp["valid_to_eff"] == "", "valid_to_eff"] = TODAY
    tp = tp.sort_values(["valid_from", "ticker"]).reset_index(drop=True)
    return tp


def slice_one(raw: pd.DataFrame, ticker: str, vfrom: str, vto: str) -> pd.DataFrame | None:
    try:
        sub = raw.xs(ticker, level=1, axis=1)
    except (KeyError, IndexError):
        return None
    sub = sub.reindex(columns=FIELDS)
    sub = sub.dropna(how="all")
    if sub.empty:
        return None
    idx = pd.to_datetime(sub.index).tz_localize(None).normalize()
    sub = sub.set_axis(idx)
    sub = sub[(sub.index >= pd.Timestamp(vfrom)) & (sub.index <= pd.Timestamp(vto))]
    sub = sub.dropna(subset=["Close"])
    if sub.empty:
        return None
    out = pd.DataFrame(
        {
            "date": sub.index.date,
            "open": sub["Open"].astype("float64").to_numpy(),
            "high": sub["High"].astype("float64").to_numpy(),
            "low": sub["Low"].astype("float64").to_numpy(),
            "close": sub["Close"].astype("float64").to_numpy(),
            "adj_close": sub["Adj Close"].astype("float64").to_numpy(),
            "volume": sub["Volume"].fillna(0).astype("float64").to_numpy(),
        }
    )
    return out


def download(tickers: list[str], start: str, end: str) -> pd.DataFrame | None:
    end_excl = (pd.Timestamp(end) + pd.Timedelta(days=1)).date().isoformat()
    try:
        raw = yf.download(
            tickers,
            start=start,
            end=end_excl,
            auto_adjust=False,
            actions=False,
            progress=False,
            threads=True,
            group_by="column",
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  batch download error: {exc}", flush=True)
        return None
    if raw is None or raw.empty:
        return None
    if raw.columns.nlevels == 1:  # 單一代號
        raw.columns = pd.MultiIndex.from_product([raw.columns, tickers])
    return raw


def run_batch(rows: pd.DataFrame, tag: str) -> tuple[pd.DataFrame, list[dict]]:
    tickers = rows["ticker"].tolist()
    start = min(rows["valid_from"])
    end = max(rows["valid_to_eff"])
    raw = download(tickers, start, end)
    frames, status = [], []
    retry = []
    for r in rows.itertuples():
        got = slice_one(raw, r.ticker, r.valid_from, r.valid_to_eff) if raw is not None else None
        if got is None:
            retry.append(r)
            continue
        got.insert(0, "entity_id", r.entity_id)
        got.insert(1, "ticker", r.ticker)
        frames.append(got)
        status.append(
            {
                "entity_id": r.entity_id,
                "ticker": r.ticker,
                "valid_from": r.valid_from,
                "valid_to": r.valid_to_eff,
                "rows": int(len(got)),
                "first_date": str(got["date"].iloc[0]),
                "last_date": str(got["date"].iloc[-1]),
                "status": "ok",
                "error": "",
                "attempt": 1,
            }
        )
    # 整批跑完再重試一次失敗者(小批 8 個,較長退讓)
    for i in range(0, len(retry), 8):
        chunk = retry[i : i + 8]
        time.sleep(random.uniform(1.5, 2.5))
        raw2 = download(
            [r.ticker for r in chunk],
            min(r.valid_from for r in chunk),
            max(r.valid_to_eff for r in chunk),
        )
        for r in chunk:
            got = slice_one(raw2, r.ticker, r.valid_from, r.valid_to_eff) if raw2 is not None else None
            if got is None:
                status.append(
                    {
                        "entity_id": r.entity_id,
                        "ticker": r.ticker,
                        "valid_from": r.valid_from,
                        "valid_to": r.valid_to_eff,
                        "rows": 0,
                        "first_date": "",
                        "last_date": "",
                        "status": "fail",
                        "error": "no data after one retry",
                        "attempt": 2,
                    }
                )
                continue
            got.insert(0, "entity_id", r.entity_id)
            got.insert(1, "ticker", r.ticker)
            frames.append(got)
            status.append(
                {
                    "entity_id": r.entity_id,
                    "ticker": r.ticker,
                    "valid_from": r.valid_from,
                    "valid_to": r.valid_to_eff,
                    "rows": int(len(got)),
                    "first_date": str(got["date"].iloc[0]),
                    "last_date": str(got["date"].iloc[-1]),
                    "status": "ok",
                    "error": "",
                    "attempt": 2,
                }
            )
    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return data, status


def main() -> None:
    PARTS.mkdir(parents=True, exist_ok=True)
    tp = load_periods()
    n = len(tp)
    nbatch = (n + BATCH - 1) // BATCH
    print(f"代號時段 {n} 段,{nbatch} 批,每批 {BATCH}", flush=True)
    t0 = time.time()
    for b in range(nbatch):
        tag = f"{b:04d}"
        pq = PARTS / f"batch_{tag}.parquet"
        js = PARTS / f"batch_{tag}.json"
        if js.exists():
            continue
        rows = tp.iloc[b * BATCH : (b + 1) * BATCH]
        data, status = run_batch(rows, tag)
        if not data.empty:
            data.to_parquet(pq, index=False, compression="zstd")
        js.write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")
        ok = sum(1 for s in status if s["status"] == "ok")
        el = time.time() - t0
        print(
            f"[{b + 1}/{nbatch}] ok={ok}/{len(rows)} rows={len(data)} 已用 {el / 60:.1f} 分",
            flush=True,
        )
        time.sleep(random.uniform(1.2, 2.0))
    print("全部批次完成", flush=True)


if __name__ == "__main__":
    sys.exit(main())
