"""KARST-145 post-hoc leakage check -- NOT part of the frozen verdict.

The sweep's strongest number is the *untimed* forward-yield pool (~16-17%/yr vs
SPY 10.9%). That pool ranks on `earn_fwd1 / mcap`, and `earn_fwd1` is the next
quarter's analyst EPS estimate as frozen at the announcement date -- up to 130
days AFTER the month_end it is stamped on. It therefore embeds up to one quarter
of analyst revisions that had not yet formed at ranking time, and revisions are
directional (analysts start high and cut), so the contamination favours ex-post
winners. The repo pre-registered this as assumption A-028, still unverified.

This script re-runs the SAME untimed arm on `earn_lag / mcap` -- already-reported
trailing-twelve-month earnings, which is leakage-free by construction. If the
edge survives, the ~5pp is the value factor. If it collapses, the ~5pp is A-028's
leakage and the whole forward-yield line is unusable.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import engine as E
import run_sweep as R

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def scored_from(fwd: pd.DataFrame, num_col: str, asc: bool = False) -> pd.DataFrame:
    d = fwd[fwd["month_end"].between(fwd["joined_on"], fwd["left_on"], inclusive="left")]
    d = d[(d["mcap"] > 0) & d[num_col].notna()].copy()
    d["score"] = d[num_col] / d["mcap"]
    d["rank_asc"] = asc
    return d[["symbol", "month_end", "etf", "score", "rank_asc"]]


def main():
    close = pd.read_parquet(HERE / "data" / "daily_close.parquet").sort_index()
    close = close.drop(columns=[c for c in R.DIRTY if c in close.columns])
    close.index = pd.to_datetime(close.index)
    fwd = pd.read_parquet(R.FWD / "member_forward.parquet")

    dates = close.index
    col_of = {c: i for i, c in enumerate(close.columns)}
    close_arr = close.to_numpy(dtype=float)
    ret_arr = close.pct_change().fillna(0.0).to_numpy(dtype=float)
    valid_arr = (close.notna() & (close > 0)).to_numpy()
    spy_col = col_of["SPY"]
    si = int(np.searchsorted(dates.values, np.datetime64(pd.Timestamp(R.STUDY_START))))
    ei = int(np.searchsorted(dates.values, np.datetime64(pd.Timestamp(R.STUDY_END)), side="right"))
    n_years = (dates[ei - 1] - dates[si]).days / 365.25
    always = np.ones_like(valid_arr, dtype=bool)

    lines = {
        "earn_fwd1 (next-qtr ESTIMATE, <=130d leakage)": "earn_fwd1",
        "earn_lag  (reported TTM, leakage-free)": "earn_lag",
        "earn_now  (reported, current)": "earn_now",
        "earn_fwd4 (next-4-qtr estimates, <=12m leakage)": "earn_fwd4",
    }

    rows = []
    for label, colname in lines.items():
        if colname not in fwd.columns:
            continue
        sc = scored_from(fwd, colname)
        for top_n in R.TOP_N_GRID:
            pool = E.top_n_pool(sc, top_n)
            months = sorted(pool)
            mei = R.month_effective_index(dates, months)
            pew_r, pew_t = R.bench_pool_series(ret_arr, valid_arr, col_of, dates,
                                               pool, months, mei)
            row = {"line": label, "col": colname, "top_n": top_n,
                   "avg_pool": round(float(np.mean([len(v) for v in pool.values()])), 1),
                   "n_months": len(pool),
                   "pool_ew_15bp": round(E.cagr(E.apply_cost(pew_r[si:ei], pew_t[si:ei], 15.0),
                                                n_years) * 100, 2)}
            for k in R.K_GRID:
                cell = E.run_cell(close_arr, ret_arr, valid_arr, col_of, dates, pool, mei,
                                  always, "drop_out", None, 0, 0.0, True, k, spy_col, si)
                pk, tn = cell["pick_ret"][si:ei], cell["turnover"][si:ei]
                sf = cell["slots_filled"][si:ei]
                pk_t = np.where(sf > 0, tn * k / np.maximum(sf, 1), 0.0)
                row[f"always_in_k{k}"] = round(E.cagr(E.apply_cost(pk, pk_t, 15.0), n_years) * 100, 2)
            rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "leak_check.csv", index=False, encoding="utf-8")
    print(df.to_string(index=False))
    print()
    print(f"SPY {E.cagr(ret_arr[si:ei, spy_col], n_years)*100:.2f}%   "
          f"XLK {E.cagr(ret_arr[si:ei, col_of['XLK']], n_years)*100:.2f}%   "
          f"({n_years:.2f} yrs)")


if __name__ == "__main__":
    main()
