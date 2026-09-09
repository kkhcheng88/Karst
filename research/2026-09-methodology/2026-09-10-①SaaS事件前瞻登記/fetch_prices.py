# -*- coding: utf-8 -*-
"""KARST-200 步驟二:抓價。

抓一個「軟件類候選超集」的日線,存成本票目錄下的快取,供籃子計算用。
超集 = data/universe/entities.parquet 內 SIC 7372(prepackaged software)全體
       + 手工補入的幾家新聞點名但 SIC 不在 7372 的公司
       + SPY(大市尺)、IGV(軟件 ETF,只作參考)

口徑(照倉內既定規矩):
- yfinance(auto_adjust=False, actions=False),用 adj_close(拆股加除息調整),
  與 data/prices/daily 生產線口徑一致。
- 美東時間判市場狀態;未收市即丟棄當日未完成那根日線(KARST-195 第七項)。
"""
import datetime
import json
import sys
import zoneinfo

import pandas as pd
import yfinance as yf

OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-10-①SaaS事件前瞻登記"
START = "2024-06-01"   # 要夠長:2026-02 要算 200 日線,故由 2024 年中起

# 新聞點名但不在 SIC 7372 的補入名單(逐個在總覽第二節說明理由)
EXTRA = [
    "WDAY", "DAY", "FIVN", "EGHT", "VRNT", "PEGA", "YEXT", "OLO", "SEMR",
    "ZI", "TOST", "WIX", "SQSP", "IBM", "ZM", "RNG", "SMAR", "CFLT",
    "ATLASSIAN_PLACEHOLDER", "TEAM", "GTLB", "SNOW", "MDB", "DDOG", "NET",
    "ADSK", "INTU", "ADBE", "ORCL", "CRM", "NOW", "HUBS", "ASAN", "MNDY",
    "PCTY", "PAYC", "DOCU", "DOMO", "BRZE", "KVYO", "FRSH", "ESTC", "TWLO",
    "BILL", "TYL", "MANH", "GWRE", "WK", "ALRM", "AMPL", "WEAV", "ZETA",
    "BLKB", "NICE", "PATH", "PCOR", "SPT", "S", "OKTA", "APPF", "NCNO",
    "QTWO", "SPSC", "VEEV", "DBX", "BOX", "SAP", "DT", "CVLT", "PRGS",
    "SSNC", "ACIW", "CCC", "VERX", "INTA", "SAIL", "RBRK", "KLTR", "AVPT",
    "BASE", "AI", "PD", "LPSN", "CXM", "NABL", "EVCM", "DH", "COUR",
    "DUOL", "SHOP", "GLBE", "LSPD", "XYZ",
]

MARKET = ["SPY", "IGV"]


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
    ent = pd.read_parquet("C:/projects/Karst/data/universe/entities.parquet")
    sic7372 = sorted(
        ent[ent.sic.astype(str) == "7372"].primary_ticker.dropna().astype(str).unique()
    )
    tickers = sorted(
        {t for t in sic7372 + EXTRA + MARKET if t.isascii() and t.replace(".", "").replace("-", "").isalnum()}
    )
    now = et_now()
    state = market_state(now)
    end = (now.date() + datetime.timedelta(days=1)).isoformat()

    print(f"ET now={now.isoformat()} state={state} tickers={len(tickers)}", file=sys.stderr)

    raw = yf.download(
        tickers,
        start=START,
        end=end,
        auto_adjust=False,
        actions=False,
        progress=False,
        group_by="column",
        threads=True,
    )
    adj = raw["Adj Close"].copy()
    vol = raw["Volume"].copy()
    adj.index = pd.to_datetime(adj.index).date
    vol.index = pd.to_datetime(vol.index).date

    # 未收市即丟棄當日那一根(KARST-195 第七項)
    dropped = None
    if state in ("open", "pre") and len(adj.index) and adj.index[-1] == now.date():
        dropped = str(adj.index[-1])
        adj = adj.iloc[:-1]
        vol = vol.iloc[:-1]

    adj.to_parquet(f"{OUT}/prices_adjclose.parquet")
    vol.to_parquet(f"{OUT}/prices_volume.parquet")

    meta = {
        "ticket": "KARST-200",
        "source": "yfinance(auto_adjust=False, actions=False) 的 Adj Close",
        "fetchedAt_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "et_now": now.isoformat(),
        "market_state": state,
        "dropped_incomplete_bar": dropped,
        "price_date": str(adj.index[-1]),
        "start": START,
        "n_tickers_requested": len(tickers),
        "n_tickers_with_data": int(adj.notna().any().sum()),
        "sic7372_count": len(sic7372),
        "note": "價格日 = 最後一根已完成日線。市場開市時已按美東時間退回上一交易日。",
    }
    with open(f"{OUT}/prices.meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
