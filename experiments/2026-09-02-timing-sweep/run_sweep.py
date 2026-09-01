"""KARST-145: full timing-layer sweep.

All parameters and the reading rules are frozen in CRITERIA.md and committed
before any result is inspected. This script only executes that spec.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import engine as E

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

ORACLE = Path(r"C:\projects\Karst\experiments\2026-09-01-stock-oracle-curve\data")
FWD = Path(r"C:\projects\Karst\experiments\2026-09-02-forward-yield-build\data")

# ---- frozen parameters ---------------------------------------------------
STUDY_START = "2005-01-01"
STUDY_END = "2026-08-31"
DIRTY = ["CPWR", "EP"]              # same two names KARST-143 dropped
BENCH_TICKERS = ["SPY", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
COST_BPS_MAIN = 15.0
COST_GRID = [0.0, 15.0, 25.0, 50.0]
RANDOM_PATHS = 2000
RANDOM_SEED = 20260902

TOP_N_GRID = [3, 5]
K_GRID = [6, 10, 15]

EXIT_SPECS = {
    # key -> (state_signal_name | None, max_hold_days, trail_stop, drop_out)
    "rsi2d_gt90":  ("rsi2d_gt90", 0, 0.0, False),
    "death_cross": ("death_cross", 0, 0.0, False),
    "trail_10":    (None, 0, 0.10, False),
    "trail_20":    (None, 0, 0.20, False),
    "time_3m":     (None, 63, 0.0, False),
    "time_6m":     (None, 126, 0.0, False),
    "drop_out":    (None, 0, 0.0, True),
}


def month_effective_index(dates: pd.DatetimeIndex, months: list) -> np.ndarray:
    """For each trading day, the index of the pool month that becomes effective
    that day (-1 otherwise). A month-end score set takes effect on the first
    trading day strictly after that month end."""
    out = np.full(len(dates), -1, dtype=np.int64)
    dvals = dates.values
    for mi, m in enumerate(months):
        pos = np.searchsorted(dvals, np.datetime64(pd.Timestamp(m)), side="right")
        if pos < len(dates):
            out[pos] = mi
    return out


def bench_pool_series(ret_arr, valid_arr, col_of, dates, pool_by_month, months, mei, k=None,
                      rng=None, paths=1):
    """Equal-weight pool benchmark (k=None) or random-k benchmark (k set).

    Returns (daily_ret 1d array, turnover 1d array) for k=None, or
    (daily_ret 2d array [days x paths], flat turnover) for random.
    """
    n_days = len(dates)
    if k is None:
        r = np.zeros(n_days)
        tno = np.zeros(n_days)
        prev: set[int] = set()
        cur: list[int] = []
        for i in range(n_days):
            if mei[i] >= 0:
                syms = pool_by_month[months[mei[i]]]
                new = [col_of[s] for s in syms if s in col_of and valid_arr[i, col_of[s]]]
                if new:
                    w = 1.0 / len(new)
                    inter = len(set(new) & prev)
                    denom = max(len(new), len(prev), 1)
                    tno[i] = (denom - inter) / denom
                    prev = set(new)
                    cur = new
            if cur:
                r[i] = float(np.mean(ret_arr[i, cur]))
        return r, tno

    R = np.zeros((n_days, paths))
    cur_mat = None
    for i in range(n_days):
        if mei[i] >= 0:
            syms = pool_by_month[months[mei[i]]]
            new = [col_of[s] for s in syms if s in col_of and valid_arr[i, col_of[s]]]
            if len(new) >= k:
                idx = np.array(new)
                picks = np.array([rng.choice(len(idx), size=k, replace=False) for _ in range(paths)])
                W = np.zeros((len(idx), paths))
                for p in range(paths):
                    W[picks[p], p] = 1.0 / k
                cur_mat = (idx, W)
        if cur_mat is not None:
            idx, W = cur_mat
            R[i] = ret_arr[i, idx] @ W
    tno = np.zeros(n_days)
    tno[mei >= 0] = 1.0          # random arm rebalances fully each month
    return R, tno


def main():
    t0 = time.time()
    close = pd.read_parquet(DATA / "daily_close.parquet").sort_index()
    close = close.drop(columns=[c for c in DIRTY if c in close.columns])
    close.index = pd.to_datetime(close.index)

    monthly = pd.read_parquet(ORACLE / "stock_monthly.parquet")
    fwd = pd.read_parquet(FWD / "member_forward.parquet")

    sig = E.build_signals(close)
    dates = close.index
    cols = list(close.columns)
    col_of = {c: i for i, c in enumerate(cols)}
    close_arr = close.to_numpy(dtype=float)
    ret_arr = close.pct_change().fillna(0.0).to_numpy(dtype=float)
    valid_arr = (close.notna() & (close > 0)).to_numpy()
    spy_col = col_of["SPY"]

    start_i = int(np.searchsorted(dates.values, np.datetime64(pd.Timestamp(STUDY_START))))
    end_i = int(np.searchsorted(dates.values, np.datetime64(pd.Timestamp(STUDY_END)), side="right"))
    n_years = (dates[end_i - 1] - dates[start_i]).days / 365.25

    scored = {
        "fwd_yield": E.pool_forward_yield(fwd),
        "low_vol": E.pool_low_vol(monthly),
    }

    # trim everything to the study window
    def clip(a):
        return a[start_i:end_i]

    ret_c = ret_arr[start_i:end_i]
    spy_ret = ret_c[:, spy_col]
    xlk_ret = ret_c[:, col_of["XLK"]]

    results = []
    bench_cache = {}
    rng_master = np.random.default_rng(RANDOM_SEED)

    for proxy, sc in scored.items():
        for top_n in TOP_N_GRID:
            pool = E.top_n_pool(sc, top_n)
            months = sorted(pool)
            mei = month_effective_index(dates, months)
            avg_pool = float(np.mean([len(v) for v in pool.values()]))

            pew_r, pew_t = bench_pool_series(ret_arr, valid_arr, col_of, dates, pool, months, mei)
            bench_cache[(proxy, top_n, "pool_ew")] = (
                E.cagr(E.apply_cost(clip(pew_r), clip(pew_t), COST_BPS_MAIN), n_years)
            )

            for k in K_GRID:
                rng = np.random.default_rng(RANDOM_SEED + k + top_n * 7 + hash(proxy) % 1000)
                Rr, rt = bench_pool_series(ret_arr, valid_arr, col_of, dates, pool, months, mei,
                                           k=k, rng=rng, paths=RANDOM_PATHS)
                Rr = Rr[start_i:end_i]
                rtc = clip(rt)
                net = Rr - rtc[:, None] * (COST_BPS_MAIN / 10000.0) * 2.0
                growth = np.prod(1.0 + net, axis=0)
                cg = np.where(growth > 0, np.power(np.maximum(growth, 1e-12), 1.0 / n_years) - 1.0, -1.0)
                bench_cache[(proxy, top_n, k, "rand")] = (
                    float(np.percentile(cg, 5)), float(np.percentile(cg, 50)), float(np.percentile(cg, 95))
                )

            for ekey, esig in sig["entries"].items():
                for xkey, (state_name, max_hold, trail, drop_out) in EXIT_SPECS.items():
                    xstate = sig["exits_state"][state_name] if state_name else None
                    for k in K_GRID:
                        cell = E.run_cell(
                            close_arr, ret_arr, valid_arr, col_of, dates, pool, mei,
                            esig, xkey, xstate, max_hold, trail, drop_out, k, spy_col, start_i,
                        )
                        pr = clip(cell["port_ret"])
                        pk = clip(cell["pick_ret"])
                        tn = clip(cell["turnover"])
                        sf = clip(cell["slots_filled"])
                        # self-picked sleeve turnover: same trades, but the sleeve is
                        # k*w of the book -> per-sleeve turnover is turnover*k/max(filled,1)
                        pk_t = np.where(sf > 0, tn * k / np.maximum(sf, 1), 0.0)

                        row = {
                            "proxy": proxy, "entry": ekey, "exit": xkey,
                            "top_n": top_n, "k": k,
                            "n_entries": cell["n_entries"],
                            "avg_hold_days": round(cell["avg_hold_days"], 1),
                            "avg_slots_filled": round(float(sf.mean()), 2),
                            "pct_days_empty": round(float((sf == 0).mean()) * 100, 1),
                            "pct_days_full": round(float((sf == k).mean()) * 100, 1),
                            "turnover_ann": round(float(tn.sum()) / n_years, 3),
                            "maxdd_port": round(E.max_drawdown(E.apply_cost(pr, tn, COST_BPS_MAIN)) * 100, 2),
                            "maxdd_pick": round(E.max_drawdown(E.apply_cost(pk, pk_t, COST_BPS_MAIN)) * 100, 2),
                        }
                        for bp in COST_GRID:
                            row[f"port_cagr_{int(bp)}"] = round(
                                E.cagr(E.apply_cost(pr, tn, bp), n_years) * 100, 3)
                            row[f"pick_cagr_{int(bp)}"] = round(
                                E.cagr(E.apply_cost(pk, pk_t, bp), n_years) * 100, 3)
                        # monthly mean of the self-picked sleeve vs SPY, KARST-143 style
                        mdf = pd.DataFrame({"d": dates[start_i:end_i],
                                            "pk": E.apply_cost(pk, pk_t, COST_BPS_MAIN),
                                            "spy": spy_ret})
                        mm = mdf.set_index("d").resample("ME").apply(lambda s: (1 + s).prod() - 1)
                        row["pick_month_mean_pct"] = round(float(mm["pk"].mean()) * 100, 3)
                        row["spy_month_mean_pct"] = round(float(mm["spy"].mean()) * 100, 3)
                        results.append(row)

    df = pd.DataFrame(results)

    spy_cagr = E.cagr(spy_ret, n_years) * 100
    xlk_cagr = E.cagr(xlk_ret, n_years) * 100
    df["spy_cagr"] = round(spy_cagr, 3)
    df["xlk_cagr"] = round(xlk_cagr, 3)
    df["pool_ew_cagr"] = [round(bench_cache[(r.proxy, r.top_n, "pool_ew")] * 100, 3)
                          for r in df.itertuples()]
    df["rand_p5"] = [round(bench_cache[(r.proxy, r.top_n, r.k, "rand")][0] * 100, 3)
                     for r in df.itertuples()]
    df["rand_p50"] = [round(bench_cache[(r.proxy, r.top_n, r.k, "rand")][1] * 100, 3)
                      for r in df.itertuples()]
    df["rand_p95"] = [round(bench_cache[(r.proxy, r.top_n, r.k, "rand")][2] * 100, 3)
                      for r in df.itertuples()]
    for c, b in [("vs_spy", "spy_cagr"), ("vs_xlk", "xlk_cagr"), ("vs_pool", "pool_ew_cagr")]:
        df[c] = (df["pick_cagr_15"] - df[b]).round(3)
    df["port_vs_spy"] = (df["port_cagr_15"] - df["spy_cagr"]).round(3)
    df["port_vs_xlk"] = (df["port_cagr_15"] - df["xlk_cagr"]).round(3)
    df["beats_rand"] = df["pick_cagr_15"] > df["rand_p95"]

    df.to_csv(OUT / "sweep.csv", index=False, encoding="utf-8")
    meta = {
        "cells": int(len(df)),
        "study_start": str(dates[start_i].date()),
        "study_end": str(dates[end_i - 1].date()),
        "n_years": round(n_years, 2),
        "trading_days": int(end_i - start_i),
        "tickers_in_price_panel": int(close.shape[1]),
        "spy_cagr_pct": round(spy_cagr, 3),
        "xlk_cagr_pct": round(xlk_cagr, 3),
        "runtime_sec": round(time.time() - t0, 1),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
