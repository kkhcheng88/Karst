"""KARST-148: analyst upgrade/downgrade history for the revision-continuation piece.

CRITERIA sec.3.4 -- yfinance `Ticker.upgrades_downgrades`, one call per universe
name. Cached to data/ratings.parquet so the backtest never re-downloads.
"""
from __future__ import annotations

import pathlib
import time

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)

PANEL = REPO / "experiments" / "2026-09-02-fundamentals-panel" / "out" / "panel_monthly.parquet"
DAILY = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
MONTHLY = REPO / "experiments" / "2026-09-01-stock-oracle-curve" / "data" / "stock_monthly.parquet"


def universe() -> list[str]:
    p = pd.read_parquet(PANEL, columns=["ticker"])
    d = pd.read_parquet(DAILY)
    m = pd.read_parquet(MONTHLY, columns=["symbol", "etf"])
    return sorted(set(p["ticker"]) & set(d.columns) & set(m["symbol"]))


def main() -> None:
    import yfinance as yf

    syms = universe()
    print(f"universe {len(syms)}")
    rows = []
    stats = []
    for i, s in enumerate(syms, 1):
        n = 0
        err = ""
        for attempt in range(2):
            try:
                ud = yf.Ticker(s).upgrades_downgrades
                if ud is not None and len(ud):
                    df = ud.reset_index()
                    df.columns = [str(c) for c in df.columns]
                    date_col = df.columns[0]
                    df = df.rename(columns={date_col: "grade_date"})
                    keep = ["grade_date"] + [c for c in ("Firm", "ToGrade", "FromGrade", "Action")
                                             if c in df.columns]
                    df = df[keep].copy()
                    df["symbol"] = s
                    rows.append(df)
                    n = len(df)
                err = ""
                break
            except Exception as exc:  # noqa: BLE001
                err = f"{type(exc).__name__}: {exc}"[:120]
                time.sleep(1.0)
        stats.append({"symbol": s, "n": n, "err": err})
        if i % 25 == 0:
            print(f"  {i}/{len(syms)} done, {sum(r['n'] for r in stats)} rows so far", flush=True)

    st = pd.DataFrame(stats)
    st.to_csv(DATA / "ratings_fetch_log.csv", index=False)
    if rows:
        out = pd.concat(rows, ignore_index=True)
        out["grade_date"] = pd.to_datetime(out["grade_date"], utc=True, errors="coerce").dt.tz_localize(None)
        out = out.dropna(subset=["grade_date"])
        out.to_parquet(DATA / "ratings.parquet", index=False)
        print(f"rows {len(out)}, symbols with data {out['symbol'].nunique()}, "
              f"span {out['grade_date'].min().date()} .. {out['grade_date'].max().date()}")
    else:
        print("no ratings rows fetched")
    print(f"errors {int((st['err'] != '').sum())}")


if __name__ == "__main__":
    main()
