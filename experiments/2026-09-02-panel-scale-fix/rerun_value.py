# -*- coding: utf-8 -*-
"""KARST-158 step 2: re-run ONLY the 行內價值 arm (A3) of KARST-148, once on
panel v1 and once on panel v2.

Nothing about KARST-148's criteria is re-decided here. The signal build is the
frozen `fourpiece-test/build_signals.py` module itself, imported and called --
only its PANEL / DATA / OUT module constants are redirected, so 148's own files
are never written. The arm, the benchmarks, the window, the cost ladder and the
2,000-path luck band are copied verbatim out of `fourpiece-test/run_test.py`.

Writes (out/, parquet gitignored):
  out/value_arm_v1_vs_v2.csv     A3 + the four benchmarks, both panels
  out/value_arm_compare.json     the差異表 the ticket asks for
  out/pool_v1.csv / pool_v2.csv  per-quarter eligible-pool counts
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
FOURPIECE = REPO / "experiments" / "2026-09-02-fourpiece-test"
OUT = HERE / "out"
WORK = HERE / "data"
OUT.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)

sys.path.insert(0, str(FOURPIECE))
import build_signals as bs                                    # noqa: E402
import engine                                                 # noqa: E402

DAILY = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
PANEL_V1 = REPO / "experiments" / "2026-09-02-fundamentals-panel" / "out" / "panel_monthly.parquet"
PANEL_V2 = OUT / "panel_monthly_v2.parquet"
SPLITS = FOURPIECE / "data" / "splits.parquet"

# --- run_test.py constants, copied verbatim ---------------------------------
MIN_MEMBERS = 6
TOP_N = 3
DROP_PCT = 0.20
COSTS = (0.0, 15.0, 25.0, 50.0)
MAIN_BPS = 15.0
N_PATHS = 2000
SEED = 20260902
WIN_END = pd.Timestamp("2026-08-31")
SPLIT_DATE = pd.Timestamp("2013-01-01")

import math                                                   # noqa: E402


def sectors_in_play(q: pd.DataFrame) -> set:
    c = q.groupby("sector")["ticker"].size()
    return set(c[c >= MIN_MEMBERS].index)


def discipline(q: pd.DataFrame, pct: float) -> pd.DataFrame:
    keep = []
    for _, g in q.groupby("sector", sort=False):
        k = math.ceil(pct * len(g))
        have = g[g["growth"].notna()].sort_values("growth", ascending=False)
        drop = set(have["ticker"].head(min(k, len(have))))
        keep.append(g[~g["ticker"].isin(drop)])
    return pd.concat(keep) if keep else q.iloc[:0]


def top_per_sector(q, col, n, ascending, allowed) -> list[str]:
    out = []
    for s, g in q.groupby("sector", sort=False):
        if s not in allowed:
            continue
        g = g.sort_values([col, "ticker"], ascending=[ascending, True])
        out.extend(g["ticker"].head(n).tolist())
    return out


def metrics(gross, turn, mask) -> dict:
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


def build_signals_for(panel_path: pathlib.Path, tag: str) -> pd.DataFrame:
    """Call 148's own build_signals.main() with the panel and output redirected."""
    orig = (bs.PANEL, bs.DATA, bs.OUT, bs.load_splits)
    bs.PANEL = panel_path
    bs.DATA = WORK / tag
    bs.OUT = WORK / tag
    bs.DATA.mkdir(parents=True, exist_ok=True)
    bs.load_splits = lambda symbols: pd.read_parquet(SPLITS)   # no copy of raw data
    try:
        bs.main()
    finally:
        bs.PANEL, bs.DATA, bs.OUT, bs.load_splits = orig
    sig = pd.read_parquet(WORK / tag / "signals.parquet")
    sig["month_end"] = pd.to_datetime(sig["month_end"])
    (WORK / tag / "pool_counts.csv").replace(OUT / f"pool_{tag}.csv")
    return sig


def run_panel(sig: pd.DataFrame, daily: pd.DataFrame, tag: str) -> tuple[list, dict]:
    cols = list(daily.columns)
    col_of = {c: i for i, c in enumerate(cols)}
    ret_all = daily.pct_change().to_numpy()
    dates = daily.index

    reb = sorted(pd.Timestamp(x) for x in sig["month_end"].unique())
    exec_day = {}
    for m in reb:
        pos = dates.searchsorted(m, side="right") - 1
        if pos + 1 >= len(dates):
            continue
        exec_day[m] = pos + 1
    first_exec = min(exec_day.values())
    end_i = int(dates.searchsorted(WIN_END, side="right"))
    win = np.zeros(len(dates), dtype=bool)
    win[first_exec:end_i] = True
    print(f"[{tag}] window {dates[first_exec].date()} .. {dates[end_i - 1].date()} "
          f"({int(win.sum())} days), rebalances {len(exec_day)}")

    ret = ret_all[:end_i]
    win = win[:end_i]
    dts = np.asarray(dates[:end_i])
    periods = {"全期": win.copy(),
               "甲期(至2012)": win & (dts < np.datetime64(SPLIT_DATE)),
               "乙期(2013起)": win & (dts >= np.datetime64(SPLIT_DATE))}
    by_month = {m: g for m, g in sig.groupby("month_end")}

    def picks_for(kind: str) -> dict[int, list[int]]:
        out = {}
        for m in reb:
            if m not in exec_day:
                continue
            q = by_month[m]
            allowed = sectors_in_play(q)
            if kind == "value":
                names = top_per_sector(q, "ey", TOP_N, False, allowed)
            elif kind == "pool":
                names = q[q["sector"].isin(allowed)]["ticker"].tolist()
            else:
                raise ValueError(kind)
            i = exec_day[m]
            idx = [col_of[t] for t in names if t in col_of
                   and np.isfinite(daily.iloc[i][t])]
            if idx:
                out[i] = idx
        return out

    rows = []

    def record(name, picks, note=""):
        g, t = engine.run_one(ret, picks)
        for pname, pm in periods.items():
            if pm.sum() < 60:
                continue
            d = metrics(g, t, pm)
            d.update({"panel": tag, "arm": name, "period": pname, "note": note})
            rows.append(d)

    for b in ("SPY", "XLK"):
        g = np.nan_to_num(ret[:, col_of[b]])
        t = np.zeros_like(g)
        for pname, pm in periods.items():
            d = metrics(g, t, pm)
            d.update({"panel": tag, "arm": f"基準:{b}含息", "period": pname,
                      "note": "無成本"})
            rows.append(d)
    record("基準:同池等權", picks_for("pool"), "投資紀律剔除前的整個合資格池")
    record("A3 單獨行內價值", picks_for("value"))

    # ---- luck band, CRITERIA 6.4, copied verbatim --------------------------
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
        band[pname] = {"p5": float(np.percentile(cg, 5)),
                       "p50": float(np.percentile(cg, 50)),
                       "p95": float(np.percentile(cg, 95)),
                       "turnover_yr_median": float(np.median(tp[:, pm].sum(axis=1)) / yrs)}
        band[pname]["_paths"] = cg
    return rows, band


def main() -> None:
    daily = pd.read_parquet(DAILY)
    daily.index = pd.to_datetime(daily.index)

    all_rows, bands, sigs = [], {}, {}
    for tag, path in (("v1", PANEL_V1), ("v2", PANEL_V2)):
        sig = build_signals_for(path, tag)
        sigs[tag] = sig
        rows, band = run_panel(sig, daily, tag)
        all_rows.extend(rows)
        bands[tag] = band

    res = pd.DataFrame(all_rows)
    res.to_csv(OUT / "value_arm_v1_vs_v2.csv", index=False, encoding="utf-8-sig")

    cmp_out = {}
    for period in ("全期", "甲期(至2012)", "乙期(2013起)"):
        row = {}
        for tag in ("v1", "v2"):
            r = res[(res.panel == tag) & (res.period == period)].set_index("arm")
            a3 = float(r.loc["A3 單獨行內價值", "cagr_15"])
            spy = float(r.loc["基準:SPY含息", "cagr_15"])
            xlk = float(r.loc["基準:XLK含息", "cagr_15"])
            pool = float(r.loc["基準:同池等權", "cagr_15"])
            b = bands[tag][period]
            paths = b["_paths"]
            row[tag] = {
                "A3_cagr_15": round(a3, 6),
                "A3_mdd_15": round(float(r.loc["A3 單獨行內價值", "mdd_15"]), 4),
                "A3_turnover_yr": round(float(r.loc["A3 單獨行內價值", "turnover_yr"]), 4),
                "vs_SPY_pp": round((a3 - spy) * 100, 4),
                "vs_XLK_pp": round((a3 - xlk) * 100, 4),
                "vs_pool_pp": round((a3 - pool) * 100, 4),
                "band_p5": round(b["p5"], 6), "band_p50": round(b["p50"], 6),
                "band_p95": round(b["p95"], 6),
                "band_percentile_of_A3": round(float((paths < a3).mean() * 100), 2),
                "above_band_p95": bool(a3 > b["p95"]),
                "inside_band_5_95": bool(b["p5"] <= a3 <= b["p95"]),
                "SPY_cagr_15": round(spy, 6), "XLK_cagr_15": round(xlk, 6),
                "pool_cagr_15": round(pool, 6),
            }
        row["delta_v2_minus_v1"] = {
            k: round(row["v2"][k] - row["v1"][k], 4)
            for k in ("A3_cagr_15", "vs_SPY_pp", "vs_XLK_pp", "vs_pool_pp",
                      "band_percentile_of_A3")
        }
        cmp_out[period] = row

    cmp_out["pool_size"] = {
        tag: {"signal_rows": int(len(sigs[tag])),
              "tickers": int(sigs[tag]["ticker"].nunique()),
              "quarters": int(sigs[tag]["month_end"].nunique())}
        for tag in ("v1", "v2")
    }
    (OUT / "value_arm_compare.json").write_text(
        json.dumps(cmp_out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(cmp_out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
