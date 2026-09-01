"""KARST-145 post-hoc diagnostics -- explicitly NOT part of the frozen verdict.

CRITERIA sec.6 decides the verdict and was committed before any cell was run.
Everything here was added after the sweep, to explain WHY the terrain looks the
way it does. It can only weaken the timing layer's case, never strengthen it
into a pass: sec.6.3 forbids this ticket from producing one at all.

Three diagnostics:
  1. `always_in` arm  -- the same pool, same K, same ranking, but NO entry gate
     (hold the top-K, replace a name only when it leaves the pool). This is the
     apples-to-apples "no timing" comparison at matched concentration, which the
     frozen pool_ew benchmark does not give (pool_ew holds ~27 names, not K).
  2. the random luck band recomputed at 0bp -- as frozen, the random arm rebuilds
     the whole book every month (turnover 24/yr => ~3.6%/yr of cost) while the
     timed cells trade 4-8/yr. Beating the 15bp band therefore overstates skill.
  3. pool_ew at 0bp, for the same reason.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import engine as E
import run_sweep as R

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "out"


def main():
    close = pd.read_parquet(DATA / "daily_close.parquet").sort_index()
    close = close.drop(columns=[c for c in R.DIRTY if c in close.columns])
    close.index = pd.to_datetime(close.index)

    monthly = pd.read_parquet(R.ORACLE / "stock_monthly.parquet")
    fwd = pd.read_parquet(R.FWD / "member_forward.parquet")

    dates = close.index
    cols = list(close.columns)
    col_of = {c: i for i, c in enumerate(cols)}
    close_arr = close.to_numpy(dtype=float)
    ret_arr = close.pct_change().fillna(0.0).to_numpy(dtype=float)
    valid_arr = (close.notna() & (close > 0)).to_numpy()
    spy_col = col_of["SPY"]

    start_i = int(np.searchsorted(dates.values, np.datetime64(pd.Timestamp(R.STUDY_START))))
    end_i = int(np.searchsorted(dates.values, np.datetime64(pd.Timestamp(R.STUDY_END)), side="right"))
    n_years = (dates[end_i - 1] - dates[start_i]).days / 365.25

    def clip(a):
        return a[start_i:end_i]

    always_sig = np.ones_like(valid_arr, dtype=bool)

    scored = {"fwd_yield": E.pool_forward_yield(fwd), "low_vol": E.pool_low_vol(monthly)}

    rows = []
    band0 = {}
    for proxy, sc in scored.items():
        for top_n in R.TOP_N_GRID:
            pool = E.top_n_pool(sc, top_n)
            months = sorted(pool)
            mei = R.month_effective_index(dates, months)

            pew_r, pew_t = R.bench_pool_series(ret_arr, valid_arr, col_of, dates, pool, months, mei)
            band0[f"{proxy}|n{top_n}|pool_ew"] = {
                "cagr_15bp": round(E.cagr(E.apply_cost(clip(pew_r), clip(pew_t), 15.0), n_years) * 100, 3),
                "cagr_0bp": round(E.cagr(clip(pew_r), n_years) * 100, 3),
                "turnover_ann": round(float(clip(pew_t).sum()) / n_years, 2),
                "avg_pool_size": round(float(np.mean([len(v) for v in pool.values()])), 1),
                "maxdd_15bp": round(E.max_drawdown(E.apply_cost(clip(pew_r), clip(pew_t), 15.0)) * 100, 2),
            }

            for k in R.K_GRID:
                rng = np.random.default_rng(
                    R.RANDOM_SEED + k + top_n * 7 + R.PROXY_SEED_OFFSET[proxy])
                Rr, rt = R.bench_pool_series(ret_arr, valid_arr, col_of, dates, pool, months, mei,
                                             k=k, rng=rng, paths=R.RANDOM_PATHS)
                Rr = Rr[start_i:end_i]
                g0 = np.prod(1.0 + Rr, axis=0)
                c0 = np.where(g0 > 0, np.power(np.maximum(g0, 1e-12), 1.0 / n_years) - 1.0, -1.0)
                band0[f"{proxy}|n{top_n}|k{k}|rand_0bp"] = {
                    "p5": round(float(np.percentile(c0, 5)) * 100, 3),
                    "p50": round(float(np.percentile(c0, 50)) * 100, 3),
                    "p95": round(float(np.percentile(c0, 95)) * 100, 3),
                    "turnover_ann": round(float(clip(rt).sum()) / n_years, 2),
                }

                cell = E.run_cell(close_arr, ret_arr, valid_arr, col_of, dates, pool, mei,
                                  always_sig, "drop_out", None, 0, 0.0, True,
                                  k, spy_col, start_i)
                pr, pk = clip(cell["port_ret"]), clip(cell["pick_ret"])
                tn, sf = clip(cell["turnover"]), clip(cell["slots_filled"])
                pk_t = np.where(sf > 0, tn * k / np.maximum(sf, 1), 0.0)
                row = {"arm": "always_in", "proxy": proxy, "top_n": top_n, "k": k,
                       "turnover_ann": round(float(tn.sum()) / n_years, 3),
                       "avg_slots_filled": round(float(sf.mean()), 2),
                       "avg_hold_days": round(cell["avg_hold_days"], 1),
                       "maxdd_pick": round(E.max_drawdown(E.apply_cost(pk, pk_t, 15.0)) * 100, 2)}
                for bp in R.COST_GRID:
                    row[f"pick_cagr_{int(bp)}"] = round(E.cagr(E.apply_cost(pk, pk_t, bp), n_years) * 100, 3)
                    row[f"port_cagr_{int(bp)}"] = round(E.cagr(E.apply_cost(pr, tn, bp), n_years) * 100, 3)
                rows.append(row)

    ai = pd.DataFrame(rows)
    ai.to_csv(OUT / "always_in.csv", index=False, encoding="utf-8")
    (OUT / "bench_gross.json").write_text(json.dumps(band0, indent=2), encoding="utf-8")

    # side-by-side: timed cells vs the always-in arm at the same (proxy, n, k)
    sw = pd.read_csv(OUT / "sweep_flagged.csv")
    cmp_rows = []
    for r in ai.itertuples():
        sub = sw[(sw.proxy == r.proxy) & (sw.top_n == r.top_n) & (sw.k == r.k)]
        cmp_rows.append({
            "proxy": r.proxy, "top_n": r.top_n, "k": r.k,
            "always_in_pick_15": r.pick_cagr_15,
            "timed_median_15": round(float(sub["pick_cagr_15"].median()), 3),
            "timed_max_15": round(float(sub["pick_cagr_15"].max()), 3),
            "timed_cells_beating_always_in": int((sub["pick_cagr_15"] > r.pick_cagr_15).sum()),
            "timed_cells": int(len(sub)),
            "always_in_turnover": r.turnover_ann,
            "timed_median_turnover": round(float(sub["turnover_ann"].median()), 2),
        })
    cmp = pd.DataFrame(cmp_rows)
    cmp.to_csv(OUT / "timing_vs_always_in.csv", index=False, encoding="utf-8")

    print(cmp.to_string(index=False))
    print()
    tot = int(cmp["timed_cells_beating_always_in"].sum())
    print(f"timed cells beating their own no-timing twin: {tot} / {int(cmp['timed_cells'].sum())}")
    print()
    print(json.dumps({k: v for k, v in band0.items() if "pool_ew" in k}, indent=2))


if __name__ == "__main__":
    main()
