# -*- coding: utf-8 -*-
"""KARST-209 步驟二:抓價。

抓 IGV+CIBR 合併名單(131 家)加 SPY 的日線,存成本票目錄下的快取。

口徑(全部照 KARST-200,令兩張表可以逐欄對照):
- yfinance(auto_adjust=False, actions=False),用 Adj Close(拆股加除息調整),
  與 data/prices/daily 生產線口徑一致。
- 美東時間判市場狀態;未收市即丟棄當日未完成那根日線(KARST-195 第七項)。
- **價格日截在 2026-09-08**——即 KARST-200 的價格日。本票要與 200 的 35 家逐欄
  對照,兩張表若各用各的價格日,「至今相對大市」那一欄就不是同一把尺。
  (抓取窗本身開到今日,截斷是刻意的一步,不是抓不到。)
"""
import datetime
import json
import sys
import zoneinfo

import pandas as pd
import yfinance as yf

OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①SaaS籃子重定義"
START = "2024-06-01"          # 要夠長:2026-02 要算 200 日線
PRICE_DATE = "2026-09-08"     # 對齊 KARST-200 的價格日
MARKET = ["SPY"]

# CIBR 有幾隻在外地上市,yfinance 用來源那個後綴找不到。同一個證券在它的主場
# 有另一個後綴——換後綴不是猜另一隻股,是那隻股的另一個報價場。
FX_FIX = {"ATO.FP": "ATO.PA", "HO.FP": "HO.PA", "OTEX.CN": "OTEX.TO", "4704.JP": "4704.T"}


def et_now():
    return datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York"))


def market_state(now):
    if now.weekday() >= 5:
        return "closed"
    t = now.time()
    if t < datetime.time(9, 30):
        return "pre"
    if t >= datetime.time(16, 0):
        return "closed"
    return "open"


def main():
    cons = pd.read_csv(f"{OUT}/constituents.csv")
    tickers = sorted({t for t in cons.ticker.astype(str)} | set(MARKET))
    now = et_now()
    state = market_state(now)
    end = (now.date() + datetime.timedelta(days=1)).isoformat()

    print(f"ET now={now.isoformat()} state={state} tickers={len(tickers)}", file=sys.stderr)

    raw = yf.download(tickers, start=START, end=end, auto_adjust=False,
                      actions=False, progress=False, group_by="column", threads=True)
    adj = raw["Adj Close"].copy()
    vol = raw["Volume"].copy()
    adj.index = pd.to_datetime(adj.index).date
    vol.index = pd.to_datetime(vol.index).date

    # 未收市即丟棄當日那一根(KARST-195 第七項)
    dropped = None
    if state in ("open", "pre") and len(adj.index) and adj.index[-1] == now.date():
        dropped = str(adj.index[-1])
        adj, vol = adj.iloc[:-1], vol.iloc[:-1]

    # 外地上市那幾隻:換主場後綴再抓,抓到的欄改名回來源那個代號
    for src, alt in FX_FIX.items():
        if src in adj.columns and adj[src].notna().any():
            continue
        try:
            sub = yf.download([alt], start=START, end=end, auto_adjust=False,
                              actions=False, progress=False, group_by="column", threads=False)
            if len(sub) and "Adj Close" in sub and sub["Adj Close"][alt].notna().any():
                s = sub["Adj Close"][alt].copy()
                s.index = pd.to_datetime(s.index).date
                sv = sub["Volume"][alt].copy()
                sv.index = pd.to_datetime(sv.index).date
                adj[src], vol[src] = s, sv
        except Exception as e:      # 抓不到就照樣留空,表上標查不到
            print(f"FX_FIX {src}->{alt} 失敗: {e}", file=sys.stderr)

    # 截到 KARST-200 的價格日
    cut = datetime.date.fromisoformat(PRICE_DATE)
    before = adj.index[-1]
    adj = adj[adj.index <= cut]
    vol = vol[vol.index <= cut]
    price_date = adj.index[-1]

    adj.to_parquet(f"{OUT}/prices_adjclose.parquet")
    vol.to_parquet(f"{OUT}/prices_volume.parquet")

    have = [t for t in tickers if t in adj.columns and adj[t].notna().any()]
    missing = [t for t in tickers if t not in have]
    meta = {
        "ticket": "KARST-209",
        "source": "yfinance(auto_adjust=False, actions=False) 的 Adj Close",
        "fetchedAt_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "et_now": now.isoformat(),
        "market_state": state,
        "dropped_incomplete_bar": dropped,
        "last_bar_before_truncation": str(before),
        "price_date": str(price_date),
        "price_date_rule": "截在 KARST-200 的價格日 2026-09-08,令兩表同尺",
        "start": START,
        "n_tickers_requested": len(tickers),
        "n_tickers_with_data": len(have),
        "missing_tickers": missing,
    }
    with open(f"{OUT}/prices.meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
