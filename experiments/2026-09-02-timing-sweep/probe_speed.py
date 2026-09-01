"""KARST-145 speed probe: time the pieces of one sweep cell."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

import engine as E
import run_sweep as R

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

t = time.time()
close = pd.read_parquet(DATA / "daily_close.parquet").sort_index()
close = close.drop(columns=[c for c in R.DIRTY if c in close.columns])
close.index = pd.to_datetime(close.index)
print(f"load parquet          {time.time()-t:8.2f}s  shape={close.shape}")

t = time.time()
monthly = pd.read_parquet(R.ORACLE / "stock_monthly.parquet")
fwd = pd.read_parquet(R.FWD / "member_forward.parquet")
print(f"load panels           {time.time()-t:8.2f}s")

t = time.time()
sig = E.build_signals(close)
print(f"build_signals         {time.time()-t:8.2f}s")

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
print(f"  study days={end_i-start_i}  n_years={n_years:.2f}  start_i={start_i}")

t = time.time()
sc_fwd = E.pool_forward_yield(fwd)
print(f"pool_forward_yield    {time.time()-t:8.2f}s  rows={len(sc_fwd)}")
t = time.time()
sc_vol = E.pool_low_vol(monthly)
print(f"pool_low_vol          {time.time()-t:8.2f}s  rows={len(sc_vol)}")

t = time.time()
pool = E.top_n_pool(sc_fwd, 3)
print(f"top_n_pool(n=3)       {time.time()-t:8.2f}s  months={len(pool)} "
      f"avg_pool={np.mean([len(v) for v in pool.values()]):.1f}")
months = sorted(pool)
mei = R.month_effective_index(dates, months)

t = time.time()
cell = E.run_cell(close_arr, ret_arr, valid_arr, col_of, dates, pool, mei,
                  sig["entries"]["dd_10"], "trail_20", None, 0, 0.20, False,
                  10, spy_col, start_i)
dt_cell = time.time() - t
print(f"run_cell (1)          {dt_cell:8.2f}s  entries={cell['n_entries']} "
      f"avg_hold={cell['avg_hold_days']:.1f}")

# the per-cell monthly resample in run_sweep
pk = cell["pick_ret"][start_i:end_i]
t = time.time()
mdf = pd.DataFrame({"d": dates[start_i:end_i], "pk": pk, "spy": ret_arr[start_i:end_i, spy_col]})
mm = mdf.set_index("d").resample("ME").apply(lambda s: (1 + s).prod() - 1)
dt_res = time.time() - t
print(f"monthly resample      {dt_res:8.2f}s")

# random benchmark cost (one proxy/top_n/k combo)
rng = np.random.default_rng(1)
t = time.time()
Rr, rt = R.bench_pool_series(ret_arr, valid_arr, col_of, dates, pool, months, mei,
                             k=10, rng=rng, paths=R.RANDOM_PATHS)
print(f"rand bench (1 combo)  {time.time()-t:8.2f}s  -> x12 combos")

t = time.time()
pew = R.bench_pool_series(ret_arr, valid_arr, col_of, dates, pool, months, mei)
print(f"pool_ew bench (1)     {time.time()-t:8.2f}s  -> x4 combos")

print()
print(f"ESTIMATE 504 cells: run_cell {dt_cell*504/60:.1f} min + "
      f"resample {dt_res*504/60:.1f} min")
