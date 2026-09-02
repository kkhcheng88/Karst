# -*- coding: utf-8 -*-
"""KARST-156 step 3: the headline numbers, in one file.

Recomputes the D1 arm and the 2,000-path luck band with the same seed as
run_test.py, and writes where D1 actually sits inside that band, plus the gap to
each benchmark. Nothing here changes any frozen definition.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

import engine
import run_test as rt

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"


def main() -> None:
    daily = pd.read_parquet(rt.DAILY)
    daily.index = pd.to_datetime(daily.index)
    dates = daily.index
    cols = list(daily.columns)
    col_of = {c: i for i, c in enumerate(cols)}
    ret_all = daily.pct_change().to_numpy()

    sig = pd.read_parquet(rt.DATA / "signals.parquet")
    sig["month_end"] = pd.to_datetime(sig["month_end"])

    end_i = int(dates.searchsorted(rt.WIN_END, side="right"))
    ret = ret_all[:end_i]
    exec_day = {}
    for m in sorted(sig["month_end"].unique()):
        pos = dates.searchsorted(pd.Timestamp(m), side="right") - 1
        if pos + 1 < end_i:
            exec_day[pd.Timestamp(m)] = pos + 1

    def window(lo, hi):
        a = min(v for k, v in exec_day.items() if k >= lo)
        later = [v for k, v in exec_day.items() if k > hi]
        b = min(later) if later else end_i
        w = np.zeros(end_i, dtype=bool)
        w[a:b] = True
        return w

    out = {}
    for ver, label in (("a", "A版 攤薄股數"), ("b", "B版 封面頁在外股數")):
        d = sig[["month_end", "ticker", f"shrink_{ver}"]].rename(
            columns={f"shrink_{ver}": "shrink"})
        d = d[d["shrink"].notna()]
        d1_picks, pool_picks, d1_sizes = {}, {}, {}
        for m, g in d.groupby("month_end"):
            m = pd.Timestamp(m)
            if m not in exec_day:
                continue
            i = exec_day[m]
            live = [t for t in g["ticker"]
                    if t in col_of and np.isfinite(ret[i, col_of[t]])]
            g = g[g["ticker"].isin(live)]
            if len(g) < rt.N_DECILE * 3:
                continue
            order = g.sort_values("shrink", ascending=False)["ticker"].tolist()
            chunks = np.array_split(np.arange(len(order)), rt.N_DECILE)
            d1_picks[i] = [col_of[order[j]] for j in chunks[0]]
            pool_picks[i] = [col_of[t] for t in order]
            d1_sizes[i] = len(chunks[0])

        g1, t1 = engine.run_one(ret, d1_picks)
        rng = np.random.default_rng(rt.SEED)
        width = max(d1_sizes.values())
        idx = {}
        for i, allc in pool_picks.items():
            n = d1_sizes[i]
            a = np.full((rt.N_PATHS, width), -1, dtype=np.int64)
            arr = np.asarray(allc)
            for p in range(rt.N_PATHS):
                a[p, :n] = rng.choice(arr, size=n, replace=False)
            idx[i] = a
        gb, tb = engine.run_paths(ret, idx)

        res = {}
        for pname, (lo, hi) in rt.PERIODS.items():
            w = window(lo, hi)
            yrs = int(w.sum()) / engine.TRADING_DAYS_YEAR
            spy = engine.cagr(np.nan_to_num(ret[:, col_of["SPY"]], nan=0.0)[w], yrs)
            xlk = engine.cagr(np.nan_to_num(ret[:, col_of["XLK"]], nan=0.0)[w], yrs)
            for bps in rt.COSTS:
                d1 = float(engine.cagr(engine.apply_cost(g1, t1, bps)[w], yrs))
                nets = gb - tb * (bps / 10000.0)
                cg = np.array([engine.cagr(nets[p][w], yrs) for p in range(rt.N_PATHS)])
                cg0 = np.array([engine.cagr(gb[p][w], yrs) for p in range(rt.N_PATHS)])
                res[f"{pname}|{bps}bp"] = {
                    "D1只做多_年化": round(d1, 5),
                    "減SPY": round(d1 - spy, 5),
                    "減XLK": round(d1 - xlk, 5),
                    "運氣帶百分位_同成本": round(float((cg < d1).mean() * 100), 1),
                    "運氣帶百分位_對零成本帶": round(float((cg0 < d1).mean() * 100), 1),
                    "年換手": round(float(t1[w].sum() / yrs), 2),
                    "運氣帶年換手中位": round(float(np.median(tb[:, w].sum(axis=1)) / yrs), 2),
                }
        out[label] = res
        out[label]["說明"] = (
            "運氣帶每月重抽,換手遠高於 D1,所以同成本比較對 D1 有利;"
            "「對零成本帶」那一欄才是同一口徑的比較——把 D1 的成本照收,"
            "而運氣帶當作零成本,是對 D1 最嚴的一種比法。")

    (OUT / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    print(json.dumps(out["A版 攤薄股數"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
