# -*- coding: utf-8 -*-
"""KARST-148 step 1: build the quarterly signal table.

Everything here follows CRITERIA.md sections 1-3 literally. No scores are looked
at; this file only turns the frozen definitions into columns.

Output (data/, not in git):
  signals.parquet   one row per (rebalance month-end, ticker) in the eligible pool
  splits.parquet    split events used for the share-basis correction
  pool_counts.csv   per-quarter sector counts + "in the index but no price" count
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA = HERE / "data"
OUT = HERE / "out"
DATA.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

PANEL = REPO / "experiments" / "2026-09-02-fundamentals-panel" / "out" / "panel_monthly.parquet"
DAILY = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
MONTHLY = REPO / "experiments" / "2026-09-01-stock-oracle-curve" / "data" / "stock_monthly.parquet"

REBALANCE_MONTHS = (2, 5, 8, 11)
FIRST_REBALANCE = pd.Timestamp("2010-02-28")     # CRITERIA sec.4.3
LAST_SIGNAL = pd.Timestamp("2026-05-31")         # 2026-08-31 rebalance has no holding period


def load_splits(symbols: list[str]) -> pd.DataFrame:
    cache = DATA / "splits.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    from defeatbeta_api.client.duckdb_client import get_duckdb_client
    from defeatbeta_api.client.hugging_face_client import HuggingFaceClient
    cli = get_duckdb_client()
    hf = HuggingFaceClient()
    url = hf.get_url_path("stock_split_events")
    in_list = ",".join("'" + s.replace("'", "''") + "'" for s in symbols)
    df = cli.query(f"SELECT symbol, report_date, split_factor FROM '{url}' "
                   f"WHERE symbol IN ({in_list})")
    num = df["split_factor"].str.split(":", expand=True).astype(float)
    df["ratio"] = num[0] / num[1]
    df["report_date"] = pd.to_datetime(df["report_date"])
    df = df[["symbol", "report_date", "ratio"]].sort_values(["symbol", "report_date"])
    df.to_parquet(cache, index=False)
    return df


def main() -> None:
    daily = pd.read_parquet(DAILY)
    daily.index = pd.to_datetime(daily.index)
    monthly = pd.read_parquet(MONTHLY, columns=["symbol", "month_end", "etf", "close"])
    sector = monthly.dropna(subset=["etf"]).groupby("symbol")["etf"].last()

    cols = ["ticker", "month_end", "in_index", "assets", "cfo_ttm", "net_income_ttm",
            "diluted_shares", "diluted_shares_filed"]
    panel = pd.read_parquet(PANEL, columns=cols)
    panel["month_end"] = pd.to_datetime(panel["month_end"])

    tradable = set(daily.columns) & set(sector.index)
    universe = sorted(set(panel["ticker"]) & tradable)
    print(f"universe {len(universe)}")

    splits = load_splits(universe)

    # ---- asset growth: same month-end one year earlier, point-in-time both legs
    a = panel[["ticker", "month_end", "assets"]].copy()
    a["month_end"] = a["month_end"] + pd.offsets.DateOffset(years=1) + pd.offsets.MonthEnd(0)
    a = a.rename(columns={"assets": "assets_prev"})
    panel = panel.merge(a, on=["ticker", "month_end"], how="left")

    reb_dates = sorted(d for d in panel["month_end"].unique()
                       if pd.Timestamp(d).month in REBALANCE_MONTHS
                       and FIRST_REBALANCE <= pd.Timestamp(d) <= LAST_SIGNAL)
    print(f"rebalance dates {len(reb_dates)}: {pd.Timestamp(reb_dates[0]).date()} .. "
          f"{pd.Timestamp(reb_dates[-1]).date()}")

    mclose = monthly.set_index(["symbol", "month_end"])["close"]

    # ---- split factor lookup: product of ratios strictly after the filing date
    sp = {s: g[["report_date", "ratio"]].to_numpy() for s, g in splits.groupby("symbol")}

    def split_factor(sym: str, filed: pd.Timestamp) -> float:
        arr = sp.get(sym)
        if arr is None or pd.isna(filed):
            return 1.0
        f = 1.0
        for d, r in arr:
            if d > filed:
                f *= float(r)
        return f

    rows, counts = [], []
    for m in reb_dates:
        m = pd.Timestamp(m)
        q = panel[(panel["month_end"] == m) & panel["in_index"]].copy()
        n_index = len(q)
        n_no_price = int((~q["ticker"].isin(tradable)).sum())
        q = q[q["ticker"].isin(universe)].copy()
        q["sector"] = q["ticker"].map(sector)
        q["px"] = [mclose.get((t, m), np.nan) for t in q["ticker"]]
        filed = pd.to_datetime(q["diluted_shares_filed"], errors="coerce")
        q["shares_adj"] = [
            sh * split_factor(t, f) if pd.notna(sh) else np.nan
            for t, sh, f in zip(q["ticker"], q["diluted_shares"], filed)
        ]
        q["mcap"] = q["shares_adj"] * q["px"]
        q["profit"] = np.where(q["assets"] > 0, q["cfo_ttm"] / q["assets"], np.nan)
        q["ey"] = np.where(q["mcap"] > 0, q["net_income_ttm"] / q["mcap"], np.nan)
        q["growth"] = np.where(q["assets_prev"] > 0, q["assets"] / q["assets_prev"] - 1.0, np.nan)

        elig = (q["sector"].notna() & q["profit"].notna() & q["ey"].notna()
                & q["px"].notna() & (q["px"] > 0))
        q = q[elig].copy()
        q["month_end"] = m
        rows.append(q[["month_end", "ticker", "sector", "profit", "ey", "growth",
                       "px", "mcap", "assets", "assets_prev"]])

        c = {"month_end": m, "in_index": n_index, "in_index_no_price": n_no_price,
             "eligible": len(q), "growth_missing": int(q["growth"].isna().sum())}
        for s, n in q["sector"].value_counts().items():
            c[s] = int(n)
        counts.append(c)

    sig = pd.concat(rows, ignore_index=True)
    sig.to_parquet(DATA / "signals.parquet", index=False)
    cnt = pd.DataFrame(counts).fillna(0)
    cnt.to_csv(OUT / "pool_counts.csv", index=False, encoding="utf-8")
    print(f"signal rows {len(sig)}, quarters {sig['month_end'].nunique()}")
    print(cnt[["month_end", "in_index", "in_index_no_price", "eligible",
               "growth_missing"]].head(8).to_string(index=False))
    print("...")
    print(cnt[["month_end", "in_index", "in_index_no_price", "eligible",
               "growth_missing"]].tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
