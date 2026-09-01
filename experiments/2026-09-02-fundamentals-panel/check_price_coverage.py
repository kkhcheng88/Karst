# -*- coding: utf-8 -*-
"""KARST-146 step 6: how many panel companies have accounts but NO price?

The SEC gives back the ACCOUNTS of delisted companies. It does not give back
their PRICES. This script counts the gap so the report can state it, and lists
every free price source that was actually checked.

The production database is opened READ-ONLY (mode=ro).

Run:  PYTHONUTF8=1 python check_price_coverage.py
"""
from __future__ import annotations

import json
import pathlib
import sqlite3

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"

DB = REPO / "karst.sqlite"


def db_tickers() -> tuple[set[str], list[str]]:
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        names = [r[0] for r in con.execute(
            "select name from sqlite_master where type in ('table','view')")]
        found: set[str] = set()
        used: list[str] = []
        for tbl in names:
            cols = [c[1].lower() for c in con.execute(f'pragma table_info("{tbl}")')]
            key = next((c for c in ("ticker", "symbol") if c in cols), None)
            if not key:
                continue
            has_price = any(c in cols for c in
                            ("close", "close_unadjusted", "adj_close", "px_close"))
            if not has_price:
                continue
            try:
                vals = {r[0] for r in con.execute(
                    f'select distinct "{key}" from "{tbl}"') if r[0]}
            except sqlite3.Error:
                continue
            if vals:
                found |= {str(v).upper() for v in vals}
                used.append(f"{tbl}({key}, {len(vals)} 個代號)")
        return found, used
    finally:
        con.close()


def parquet_tickers() -> tuple[set[str], list[str]]:
    found: set[str] = set()
    used: list[str] = []
    cands = [
        REPO / "experiments/2026-09-01-stock-oracle-curve/data/stock_monthly.parquet",
        REPO / "experiments/2026-09-02-tenbagger-casecontrol/data/prices_monthly.parquet",
    ]
    # Snapshot prices.parquet is keyed on entity_id, not ticker; the snapshot's
    # own universe.parquet is the ticker list that actually has bars in it.
    cands += sorted((REPO / "data" / "snapshots").glob("*/universe.parquet"))
    cands += sorted((REPO / "experiments").glob("*/data/*price*.parquet"))
    cands += sorted((REPO / "experiments").glob("*/data/*monthly*.parquet"))
    for p in cands:
        if not p.exists():
            continue
        try:
            df = pd.read_parquet(p)
        except Exception:  # noqa: BLE001
            continue
        col = None
        for c in ("ticker", "symbol"):
            if c in df.columns:
                col = c
                break
        if not col:
            # No ticker column at all - skip rather than guess off the index.
            continue
        vals = {str(v).upper() for v in df[col].dropna().unique()}
        if vals:
            found |= vals
            used.append(f"{p.relative_to(REPO).as_posix()}({len(vals)} 個代號)")
    return found, used


def main() -> None:
    panel = pd.read_parquet(OUT / "panel_monthly.parquet",
                            columns=["ticker", "month_end"])
    uni = pd.read_csv(OUT / "universe_cik.csv", dtype=str).fillna("")
    in_panel = set(panel.ticker.unique())

    d_t, d_src = db_tickers()
    p_t, p_src = parquet_tickers()
    priced = d_t | p_t

    delisted = set(uni.loc[uni.left_on != "", "ticker"])
    no_price = sorted(in_panel - priced)
    delisted_no_price = sorted(set(no_price) & delisted)

    pd.DataFrame({"ticker": no_price}).merge(
        uni[["ticker", "joined_on", "left_on", "cik", "cik_source"]],
        on="ticker", how="left").to_csv(
        OUT / "accounts_but_no_price.csv", index=False, encoding="utf-8")

    res = dict(
        panel_tickers=len(in_panel),
        priced_tickers_anywhere=len(priced & in_panel),
        accounts_but_no_price=len(no_price),
        accounts_but_no_price_and_delisted=len(delisted_no_price),
        price_sources_checked=d_src + p_src,
    )
    (OUT / "price_gap.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    for k, v in res.items():
        print(k, ":", v)


if __name__ == "__main__":
    main()
