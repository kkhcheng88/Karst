"""KARST-157 第一步:建宇宙(零回報輸入)。

三個來源合併去重:
  1. 既有 574 家(experiments/2026-09-02-timing-sweep/data/daily_close.parquet 的欄,減 ETF)
  2. 舊倉人手鏈位表 chain_membership_v0.csv 全部代碼(含已退役行,建宇宙時不篩)
  3. 主題 ETF 的持股名單(yfinance funds_data.top_holdings;只作宇宙來源,不入分層)

輸出 out/universe_v2.json:new_tickers(要新抓的)、existing(既有 parquet 已有的)、
etf_holdings_raw(逐隻 ETF 抓到什麼)、dropped_non_us(過濾走的非美股代碼)。

用法:python build_universe.py
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
EXISTING_PARQUET = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
MANUAL_CSV = REPO / "experiments" / "2026-09-02-chain-layers" / "chain_membership_v0.csv"
OUT = HERE / "out"

# 既有 parquet 內的 ETF(不是股票,不入分層宇宙,但 SPY 與板塊 ETF 作基準要留)
BENCH_ETFS = ["SPY", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
OTHER_ETFS_IN_PARQUET = ["QQQ", "XLC", "XLRE", "IWM", "MDY", "RSP", "VTI", "DIA", "EFA", "AGG"]

# 主題 ETF:只作宇宙來源(當前持股名單=事後名單,誠實聲明第三項)
THEME_ETFS = [
    # 用戶點名的四條主題
    "QTUM",           # 量子
    "URA", "URNM", "URNJ", "NLR",   # 鈾/核電
    "WGMI", "BITQ", "BLOK",         # 加密礦/區塊鏈
    # 其餘主題(補宇宙廣度)
    "ARKQ", "ARKG", "ARKW", "ARKF", "ARKK",
    "TAN", "ICLN", "LIT", "COPX", "REMX", "XME", "SIL", "GDX",
    "PAVE", "ITB", "JETS", "DRIV", "HACK", "CIBR", "SKYY", "FINX",
    "IBUY", "ESPO", "BOTZ", "SMH", "SOXX", "XBI", "IHI", "IGV",
    "PPA", "ITA", "XAR", "MOO", "XOP", "OIH", "AIQ", "IPO",
]

US_TICKER = re.compile(r"^[A-Z]{1,5}$")


def load_existing() -> list[str]:
    df = pd.read_parquet(EXISTING_PARQUET, columns=None)
    return sorted(df.columns.astype(str))


def read_manual_rows() -> list[dict]:
    """人手表用 csv 模組逐行讀:note 欄有未加引號的逗號(例如 TLN 那行),
    pandas 直接讀會 tokenize 失敗。前五欄固定,其餘全部併回 note。"""
    import csv

    rows: list[dict] = []
    with open(MANUAL_CSV, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        assert header[:5] == ["theme", "ticker", "valid_from", "valid_to", "role"], header
        for rec in reader:
            if not rec or not rec[0].strip():
                continue
            rows.append({
                "theme": rec[0].strip(),
                "ticker": rec[1].strip().upper(),
                "valid_from": rec[2].strip(),
                "valid_to": rec[3].strip(),
                "role": rec[4].strip() if len(rec) > 4 else "",
                "note": ",".join(rec[5:]) if len(rec) > 5 else "",
            })
    return rows


def load_manual() -> list[str]:
    return sorted({r["ticker"] for r in read_manual_rows() if r["ticker"]})


def fetch_etf_holdings() -> tuple[dict[str, list[str]], list[str]]:
    holdings: dict[str, list[str]] = {}
    dropped: set[str] = set()
    for etf in THEME_ETFS:
        try:
            fd = yf.Ticker(etf).funds_data
            th = fd.top_holdings
        except Exception as exc:  # noqa: BLE001
            print(f"  {etf}: FAILED {type(exc).__name__} {exc}", flush=True)
            holdings[etf] = []
            continue
        if th is None or len(th) == 0:
            print(f"  {etf}: empty", flush=True)
            holdings[etf] = []
            continue
        syms = [str(s).strip().upper() for s in th.index]
        keep = [s for s in syms if US_TICKER.match(s)]
        dropped.update(s for s in syms if not US_TICKER.match(s))
        holdings[etf] = keep
        print(f"  {etf}: {len(keep)}/{len(syms)} us", flush=True)
        time.sleep(0.3)
    return holdings, sorted(dropped)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    existing_cols = load_existing()
    etfs_in_parquet = set(BENCH_ETFS) | set(OTHER_ETFS_IN_PARQUET)
    existing_stocks = [c for c in existing_cols if c not in etfs_in_parquet]

    manual = load_manual()
    print(f"existing parquet cols: {len(existing_cols)}  (stocks {len(existing_stocks)})", flush=True)
    print(f"manual table tickers: {len(manual)}", flush=True)

    print("fetching theme ETF holdings...", flush=True)
    holdings, dropped = fetch_etf_holdings()
    etf_names = sorted({s for v in holdings.values() for s in v})
    print(f"theme ETF us names: {len(etf_names)}, dropped non-us {len(dropped)}", flush=True)

    all_stocks = sorted(set(existing_stocks) | set(manual) | set(etf_names))
    # 主題 ETF 本身不入股票宇宙
    all_stocks = [t for t in all_stocks if t not in set(THEME_ETFS) | etfs_in_parquet]
    new = sorted(set(all_stocks) - set(existing_cols))

    payload = {
        "existing_parquet": str(EXISTING_PARQUET),
        "existing_cols": len(existing_cols),
        "existing_stocks": len(existing_stocks),
        "manual_tickers": manual,
        "manual_count": len(manual),
        "manual_not_in_existing": sorted(set(manual) - set(existing_cols)),
        "theme_etfs": THEME_ETFS,
        "etf_holdings_raw": holdings,
        "etf_names": etf_names,
        "dropped_non_us": dropped,
        "universe_stocks": all_stocks,
        "universe_stock_count": len(all_stocks),
        "new_tickers": new,
        "new_count": len(new),
        "bench_etfs": BENCH_ETFS,
    }
    (OUT / "universe_v2.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items()
                      if k not in ("manual_tickers", "etf_holdings_raw", "etf_names",
                                   "universe_stocks", "new_tickers", "dropped_non_us",
                                   "manual_not_in_existing")}, indent=2))
    print(f"NEW to fetch: {len(new)}")


if __name__ == "__main__":
    main()
