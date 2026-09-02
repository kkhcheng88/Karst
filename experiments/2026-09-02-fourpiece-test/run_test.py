# -*- coding: utf-8 -*-
"""KARST-148 runner: every arm, every benchmark, the neighbourhood grid.

Follows CRITERIA.md sections 3-8 literally. Nothing here decides anything --
the judgement rules in CRITERIA sec.9 are applied in analyse.py afterwards.
"""
from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import pandas as pd

import engine

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA = HERE / "data"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

DAILY = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"

MIN_MEMBERS = 6                    # CRITERIA sec.2.3
TOP_N = 3                          # CRITERIA sec.3.5
DROP_PCT = 0.20                    # CRITERIA sec.3.2
COSTS = (0.0, 15.0, 25.0, 50.0)    # CRITERIA sec.5.1
MAIN_BPS = 15.0
N_PATHS = 2000                     # CRITERIA sec.6.4
SEED = 20260902
WIN_END = pd.Timestamp("2026-08-31")
SPLIT_DATE = pd.Timestamp("2013-01-01")
REV_FIRST_REB = pd.Timestamp("2012-02-29")


# ---------------------------------------------------------------- selection
def sectors_in_play(q: pd.DataFrame) -> set:
    c = q.groupby("sector")["ticker"].size()
    return set(c[c >= MIN_MEMBERS].index)


def discipline(q: pd.DataFrame, pct: float) -> pd.DataFrame:
    """Drop the fastest-inflating ceil(pct * n) names inside each sector.

    Names whose one-year asset growth cannot be computed are NOT dropped
    (CRITERIA sec.3.2): you cannot show a name is extreme without the number.
    """
    keep = []
    for _, g in q.groupby("sector", sort=False):
        k = math.ceil(pct * len(g))
        have = g[g["growth"].notna()].sort_values("growth", ascending=False)
        drop = set(have["ticker"].head(min(k, len(have))))
        keep.append(g[~g["ticker"].isin(drop)])
    return pd.concat(keep) if keep else q.iloc[:0]


def top_per_sector(q: pd.DataFrame, col: str, n: int, ascending: bool,
                   allowed: set) -> list[str]:
    out = []
    for s, g in q.groupby("sector", sort=False):
        if s not in allowed:
            continue
        g = g.sort_values([col, "ticker"], ascending=[ascending, True])
        out.extend(g["ticker"].head(n).tolist())
    return out


def composite_scores(q: pd.DataFrame, use_revision: bool) -> pd.DataFrame:
    q = q.copy()
    g = q.groupby("sector")
    q["r_profit"] = g["profit"].rank(pct=True)
    q["r_ey"] = g["ey"].rank(pct=True)
    q["score"] = q["r_profit"] + q["r_ey"]
    if use_revision:
        q["r_rev"] = g["revision"].rank(pct=True)
        q.loc[q["revision"].isna(), "r_rev"] = 0.5
        q["score"] = q["score"] + q["r_rev"]
    return q


# ---------------------------------------------------------------- metrics
def metrics(gross: np.ndarray, turn: np.ndarray, mask: np.ndarray) -> dict:
    n = int(mask.sum())
    yrs = n / engine.TRADING_DAYS_YEAR
    d = {}
    for b in COSTS:
        net = engine.apply_cost(gross, turn, b)[mask]
        d[f"cagr_{int(b)}"] = engine.cagr(net, yrs)
    net15 = engine.apply_cost(gross, turn, MAIN_BPS)[mask]
    d["mdd_15"] = engine.max_drawdown(net15)
    d["turnover_yr"] = float(turn[mask].sum() / yrs)
    d["days"] = n
    return d


def main() -> None:
    daily = pd.read_parquet(DAILY)
    daily.index = pd.to_datetime(daily.index)
    sig = pd.read_parquet(DATA / "signals.parquet")
    sig["month_end"] = pd.to_datetime(sig["month_end"])

    # revision continuation: net upgrades minus downgrades in the trailing 6 months
    rat = pd.read_parquet(DATA / "ratings.parquet")
    rat = rat[rat["Action"].isin(["up", "down"])].copy()
    rat["v"] = np.where(rat["Action"] == "up", 1, -1)
    rev_rows = []
    for m in sorted(sig["month_end"].unique()):
        m = pd.Timestamp(m)
        lo = m - pd.DateOffset(months=6)
        w = rat[(rat["grade_date"] > lo) & (rat["grade_date"] <= m)]
        if len(w):
            s = w.groupby("symbol")["v"].sum()
            rev_rows.append(pd.DataFrame({"month_end": m, "ticker": s.index,
                                          "revision": s.to_numpy()}))
    rev = pd.concat(rev_rows, ignore_index=True) if rev_rows else \
        pd.DataFrame(columns=["month_end", "ticker", "revision"])
    sig = sig.merge(rev, on=["month_end", "ticker"], how="left")

    cols = list(daily.columns)
    col_of = {c: i for i, c in enumerate(cols)}
    ret_all = daily.pct_change().to_numpy()
    dates = daily.index

    reb = sorted(pd.Timestamp(x) for x in sig["month_end"].unique())
    exec_day = {}
    for m in reb:
        pos = dates.searchsorted(m, side="right") - 1     # last trading day <= m
        if pos + 1 >= len(dates):
            continue
        exec_day[m] = pos + 1                             # execute at NEXT close
    first_exec = min(exec_day.values())
    end_i = int(dates.searchsorted(WIN_END, side="right"))
    win = np.zeros(len(dates), dtype=bool)
    win[first_exec:end_i] = True
    print(f"window {dates[first_exec].date()} .. {dates[end_i - 1].date()} "
          f"({int(win.sum())} days), rebalances {len(exec_day)}")

    ret = ret_all[:end_i]
    win = win[:end_i]
    mask_full = win.copy()
    dts = np.asarray(dates[:end_i])
    mask_a = win & (dts < np.datetime64(SPLIT_DATE))
    mask_b = win & (dts >= np.datetime64(SPLIT_DATE))
    periods = {"全期": mask_full, "甲期(至2012)": mask_a, "乙期(2013起)": mask_b}

    by_month = {m: g for m, g in sig.groupby("month_end")}

    # ------------------------------------------------------------ arm builders
    def picks_for(kind: str, n: int = TOP_N, pct: float = DROP_PCT,
                  first: pd.Timestamp | None = None) -> dict[int, list[int]]:
        out = {}
        for m in reb:
            if first is not None and m < first:
                continue
            if m not in exec_day:
                continue
            q = by_month[m]
            allowed = sectors_in_play(q)
            if kind == "profit":
                names = top_per_sector(q, "profit", n, False, allowed)
            elif kind == "value":
                names = top_per_sector(q, "ey", n, False, allowed)
            elif kind == "growth_rank":
                names = top_per_sector(q[q["growth"].notna()], "growth", n, True, allowed)
            elif kind == "discipline_only":
                d = discipline(q, pct)
                names = d[d["sector"].isin(allowed)]["ticker"].tolist()
            elif kind == "pool":
                names = q[q["sector"].isin(allowed)]["ticker"].tolist()
            elif kind in ("composite", "composite_rev"):
                d = discipline(q, pct)
                d = composite_scores(d, kind == "composite_rev")
                names = top_per_sector(d, "score", n, False, allowed)
            else:
                raise ValueError(kind)
            i = exec_day[m]
            idx = [col_of[t] for t in names if t in col_of
                   and np.isfinite(daily.iloc[i][t])]
            if idx:
                out[i] = idx
        return out

    results = []

    def record(name: str, picks: dict[int, list[int]], note: str = "") -> dict:
        g, t = engine.run_one(ret, picks)
        row_by_period = {}
        for pname, pm in periods.items():
            if pm.sum() < 60:
                continue
            d = metrics(g, t, pm)
            d.update({"arm": name, "period": pname, "note": note})
            results.append(d)
            row_by_period[pname] = d
        n_hold = np.mean([len(v) for v in picks.values()])
        for pname in row_by_period:
            row_by_period[pname]["avg_holdings"] = round(float(n_hold), 1)
        return row_by_period

    # benchmarks -------------------------------------------------------------
    for b in ("SPY", "XLK"):
        g = np.nan_to_num(ret[:, col_of[b]])
        t = np.zeros_like(g)
        for pname, pm in periods.items():
            d = metrics(g, t, pm)
            d.update({"arm": f"基準:{b}含息", "period": pname, "note": "無成本",
                      "avg_holdings": 1})
            results.append(d)

    record("基準:同池等權", picks_for("pool"), "投資紀律剔除前的整個合資格池")

    # tested arms ------------------------------------------------------------
    record("A1 單獨盈利能力", picks_for("profit"))
    record("A2a 單獨投資紀律(剔除臂)", picks_for("discipline_only"), "照 D-126,只剔不排")
    record("A2b 單獨投資紀律(排名臂)", picks_for("growth_rank"), "超出 D-126,診斷用")
    record("A3 單獨行內價值", picks_for("value"))
    record("B 合成(主判)", picks_for("composite"))
    record("C1 合成(2012窗)", picks_for("composite", first=REV_FIRST_REB), "C2 的對照")
    record("C2 合成+修訂延續(2012窗)", picks_for("composite_rev", first=REV_FIRST_REB))

    # neighbourhood ----------------------------------------------------------
    nb = []
    for n in (2, 3, 5):
        for pct in (0.10, 0.20, 0.30):
            g, t = engine.run_one(ret, picks_for("composite", n=n, pct=pct))
            for pname, pm in periods.items():
                d = metrics(g, t, pm)
                d.update({"n": n, "drop_pct": pct, "period": pname})
                nb.append(d)
    pd.DataFrame(nb).to_csv(OUT / "neighbourhood.csv", index=False, encoding="utf-8")

    # random luck band -------------------------------------------------------
    rng = np.random.default_rng(SEED)
    width = 9 * 5
    exec_idx = {}
    for m in reb:
        if m not in exec_day:
            continue
        q = by_month[m]
        allowed = sectors_in_play(q)
        d = discipline(q, DROP_PCT)
        i = exec_day[m]
        groups = []
        for s, g in d.groupby("sector", sort=False):
            if s not in allowed:
                continue
            ok = [col_of[t] for t in g["ticker"] if t in col_of
                  and np.isfinite(daily.iloc[i][t])]
            if len(ok) >= TOP_N:
                groups.append(np.array(ok))
        if not groups:
            continue
        arr = np.full((N_PATHS, width), -1, dtype=np.int64)
        pos = 0
        for gcols in groups:
            pick = np.array([rng.choice(gcols, size=TOP_N, replace=False)
                             for _ in range(N_PATHS)])
            arr[:, pos:pos + TOP_N] = pick
            pos += TOP_N
        exec_idx[i] = arr
    gp, tp = engine.run_paths(ret, exec_idx)
    band = {}
    for pname, pm in periods.items():
        yrs = int(pm.sum()) / engine.TRADING_DAYS_YEAR
        net = engine.apply_cost(gp, tp, MAIN_BPS)[:, pm]
        cg = np.array([engine.cagr(net[p], yrs) for p in range(N_PATHS)])
        band[pname] = {
            "p5": float(np.percentile(cg, 5)),
            "p50": float(np.percentile(cg, 50)),
            "p95": float(np.percentile(cg, 95)),
            "turnover_yr_median": float(np.median(tp[:, pm].sum(axis=1)) / yrs),
        }
        for b in COSTS:
            n2 = engine.apply_cost(gp, tp, b)[:, pm]
            c2 = np.array([engine.cagr(n2[p], yrs) for p in range(N_PATHS)])
            for pc in (5, 50, 95):
                band[pname][f"p{pc}_cagr_{int(b)}"] = float(np.percentile(c2, pc))

    res = pd.DataFrame(results)
    res.to_csv(OUT / "arms.csv", index=False, encoding="utf-8")
    (OUT / "random_band.json").write_text(json.dumps(band, ensure_ascii=False, indent=2),
                                          encoding="utf-8")

    meta = {
        "window": [str(dates[first_exec].date()), str(dates[end_i - 1].date())],
        "rebalances": len(exec_day),
        "universe": int(sig["ticker"].nunique()),
        "paths": N_PATHS, "seed": SEED,
        "revision_coverage": {
            str(pd.Timestamp(m).date()): round(float(g["revision"].notna().mean()), 3)
            for m, g in sig[sig["month_end"] >= REV_FIRST_REB].groupby("month_end")
        },
    }
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    print(res.to_string(index=False))
    print(json.dumps(band, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
