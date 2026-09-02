# -*- coding: utf-8 -*-
"""KARST-155 step 3: the return test.

Runs CRITERIA.md sections 6-11 literally. No parameter is chosen here; every
number the criteria name is reported, and only the one pre-named cell decides
the verdict.

Output (out/):
  matched_events.parquet  per event x horizon x benchmark matched difference
  matched_returns.csv     direction x field x tier x horizon x benchmark, by period
  verdict.json            the pre-named cell and the verdict word
  portfolio.json          long-short annualised vs the four benchmarks
  portfolio_monthly.csv   monthly series of every arm and benchmark
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
PANEL = REPO / "experiments" / "2026-09-02-fundamentals-panel" / "out" / "panel_monthly.parquet"
DAILY = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
MONTHLY = REPO / "experiments" / "2026-09-01-stock-oracle-curve" / "data" / "stock_monthly.parquet"

HORIZONS = (3, 6, 12)
TIERS = (0.02, 0.05)
SPLIT_DATE = pd.Timestamp("2017-01-01")
COST_BP = 15e-4
N_PATHS = 2000
SEED = 20260902
PORT_START = pd.Timestamp("2010-01-31")
PORT_END = pd.Timestamp("2026-07-31")


def cluster_t(d: np.ndarray, clusters: np.ndarray):
    """CRITERIA sec.8: SE = sqrt(sum_c (sum_{i in c} (d_i - dbar))^2) / N."""
    n = len(d)
    if n < 2:
        return np.nan, np.nan, n, 0
    dbar = float(d.mean())
    dev = d - dbar
    s = pd.Series(dev).groupby(pd.Series(clusters)).sum().to_numpy()
    se = float(np.sqrt((s ** 2).sum())) / n
    t = dbar / se if se > 0 else np.nan
    return dbar, t, n, int(len(s))


def ew_turnover(n_prev: int, n_cur: int, overlap: np.ndarray | int):
    """L1/2 turnover between two equal-weight sets."""
    ov = np.atleast_1d(np.asarray(overlap, dtype=float))
    if n_cur == 0:
        return np.zeros_like(ov)
    if n_prev == 0:
        return np.ones_like(ov)
    return 0.5 * (ov * abs(1 / n_cur - 1 / n_prev)
                  + (n_cur - ov) / n_cur + (n_prev - ov) / n_prev)


def main() -> None:
    ev = pd.read_parquet(OUT / "events.parquet")
    ev["rev_filed_dt"] = pd.to_datetime(ev["rev_filed_dt"])
    ev["entry_month_end"] = pd.to_datetime(ev["entry_month_end"])

    daily = pd.read_parquet(DAILY)
    daily.index = pd.to_datetime(daily.index)
    mclose = daily.resample("ME").last()
    months = mclose.index
    mpos = {m: i for i, m in enumerate(months)}

    panel = pd.read_parquet(PANEL, columns=["ticker", "month_end", "in_index"])
    panel["month_end"] = pd.to_datetime(panel["month_end"])

    mon = pd.read_parquet(MONTHLY, columns=["symbol", "etf"])
    sector_map = mon.dropna(subset=["etf"]).groupby("symbol")["etf"].last()

    panel_tickers = sorted(set(panel["ticker"]))
    tickers = [t for t in panel_tickers
               if t in mclose.columns and t in sector_map.index]
    tidx = {t: i for i, t in enumerate(tickers)}
    nT, nM = len(tickers), len(months)
    print(f"tradable panel tickers with a sector: {nT}; months {nM}", flush=True)

    sectors = sorted(set(sector_map[t] for t in tickers))
    sidx = {s: i for i, s in enumerate(sectors)}
    sec_of = np.array([sidx[sector_map[t]] for t in tickers])

    px = mclose.reindex(columns=tickers).to_numpy(dtype=float)
    R = {}
    for h in HORIZONS + (1,):
        fwd = np.full_like(px, np.nan)
        if h < nM:
            fwd[:nM - h] = px[h:] / px[:nM - h] - 1.0
        fwd[~np.isfinite(fwd)] = np.nan
        R[h] = fwd
    bench_px = {b: mclose[b].to_numpy(dtype=float) for b in ("SPY", "XLK") + tuple(sectors)}
    BR = {}
    for h in HORIZONS + (1,):
        BR[h] = {}
        for b, s in bench_px.items():
            f = np.full(nM, np.nan)
            if h < nM:
                f[:nM - h] = s[h:] / s[:nM - h] - 1.0
            BR[h][b] = f

    # alive / in-index masks
    alive = np.zeros((nM, nT), dtype=bool)
    inidx = np.zeros((nM, nT), dtype=bool)
    for t, m, f in zip(panel["ticker"], panel["month_end"], panel["in_index"]):
        i, j = mpos.get(m), tidx.get(t)
        if i is None or j is None:
            continue
        alive[i, j] = True
        if f:
            inidx[i, j] = True

    # "any revision event in the trailing 12 months as of month end m"
    def trailing_mask(sub: pd.DataFrame) -> np.ndarray:
        mk = np.zeros((nM, nT), dtype=bool)
        for t, d in zip(sub["ticker"], sub["rev_filed_dt"]):
            j = tidx.get(t)
            if j is None:
                continue
            lo = int(months.searchsorted(d, side="right"))
            hi = int(months.searchsorted(d + pd.DateOffset(months=12),
                                         side="right"))
            mk[lo:hi, j] = True
        return mk

    recent_any = trailing_mask(ev[["ticker", "rev_filed_dt"]].drop_duplicates())
    sd = ev[(ev.tier == 0.02) & ev.silent & (ev.direction == "down")]
    recent_sd = trailing_mask(sd[["ticker", "rev_filed_dt"]].drop_duplicates())

    # ---- control-group mean RAW return per (sector, month, horizon) --------
    # CRITERIA sec.7: same sector ETF, same entry month, priced, and no
    # revision event of any kind in the trailing 12 months.
    ctrl_mean = {}
    ctrl_n = {}
    for h in HORIZONS:
        ok = np.isfinite(R[h]) & alive & (~recent_any)
        vals = np.where(ok, R[h], 0.0)
        cm = np.zeros((nM, len(sectors)))
        cn = np.zeros((nM, len(sectors)))
        for si in range(len(sectors)):
            col = sec_of == si
            cn[:, si] = ok[:, col].sum(axis=1)
            cm[:, si] = vals[:, col].sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            cm = np.where(cn > 0, cm / np.maximum(cn, 1), np.nan)
        ctrl_mean[h], ctrl_n[h] = cm, cn

    # ---- per-event matched differences -------------------------------------
    use = ev[ev.has_price & ev.sector.notna()].copy()
    use = use[use["ticker"].isin(tidx)]
    use = use[use["entry_month_end"].isin(mpos)]
    rows = []
    for r in use.itertuples():
        i, j = mpos[r.entry_month_end], tidx[r.ticker]
        si = sidx[r.sector]
        for h in HORIZONS:
            sr = R[h][i, j]
            if not np.isfinite(sr):
                continue
            cm, cn = ctrl_mean[h][i, si], ctrl_n[h][i, si]
            if not np.isfinite(cm) or cn == 0:
                continue
            for bench in ("sector", "spy"):
                bname = "SPY" if bench == "spy" else r.sector
                br = BR[h][bname][i]
                if not np.isfinite(br):
                    continue
                rows.append((r.ticker, r.field, r.tier, r.direction, r.silent,
                             r.standard_transition, r.sector, r.entry_month_end,
                             r.rev_filed_dt, h, bench, sr - br, cm - br,
                             int(cn), sr - cm,
                             f"{r.sector}|{r.entry_month_end:%Y-%m}"))
    md = pd.DataFrame(rows, columns=[
        "ticker", "field", "tier", "direction", "silent", "standard_transition",
        "sector", "entry", "event_date", "horizon", "bench", "resid", "ctrl",
        "ctrl_n", "d", "cluster"])
    md.to_parquet(OUT / "matched_events.parquet", index=False)
    print(f"matched rows: {len(md):,}", flush=True)

    def summarise(sub: pd.DataFrame, period: str) -> dict:
        dbar, t, n, nc = cluster_t(sub["d"].to_numpy(), sub["cluster"].to_numpy())
        return dict(period=period, n=n, clusters=nc,
                    mean_diff=None if n < 2 else round(dbar, 5),
                    t=None if n < 2 or not np.isfinite(t) else round(t, 3),
                    mean_resid=round(float(sub["resid"].mean()), 5) if n else None,
                    mean_ctrl=round(float(sub["ctrl"].mean()), 5) if n else None)

    periods = {"all": (pd.Timestamp("2000-01-01"), pd.Timestamp("2100-01-01")),
               "2009-2016": (pd.Timestamp("2009-01-01"), SPLIT_DATE),
               "2017-2026": (SPLIT_DATE, pd.Timestamp("2100-01-01"))}
    out_rows = []
    for tier in TIERS:
        for silent in (True, False):
            for direction in ("down", "up"):
                base = md[(md.tier == tier) & (md.silent == silent)
                          & (md.direction == direction)]
                if len(base) == 0:
                    continue
                for field in ("ALL", "revenue", "net_income", "cfo", "assets"):
                    b2 = base if field == "ALL" else base[base.field == field]
                    for h in HORIZONS:
                        for bench in ("sector", "spy"):
                            b3 = b2[(b2.horizon == h) & (b2.bench == bench)]
                            for pname, (lo, hi) in periods.items():
                                s = b3[(b3.event_date >= lo) & (b3.event_date < hi)]
                                if len(s) == 0:
                                    continue
                                rec = summarise(s, pname)
                                rec.update(tier=tier, silent=silent,
                                           direction=direction, field=field,
                                           horizon=h, bench=bench)
                                out_rows.append(rec)
    tab = pd.DataFrame(out_rows)[
        ["tier", "silent", "direction", "field", "horizon", "bench", "period",
         "n", "clusters", "mean_diff", "t", "mean_resid", "mean_ctrl"]]
    tab.to_csv(OUT / "matched_returns.csv", index=False, encoding="utf-8")
    print(f"summary rows: {len(tab)}", flush=True)

    # ---- verdict (CRITERIA sec.10) -----------------------------------------
    core = md[(md.tier == 0.02) & md.silent & (md.direction == "down")
              & (md.horizon == 6) & (md.bench == "sector")]
    main_all = summarise(core, "all")
    main_a = summarise(core[core.event_date < SPLIT_DATE], "2009-2016")
    main_b = summarise(core[core.event_date >= SPLIT_DATE], "2017-2026")
    rob = summarise(core[~core.standard_transition], "all_excl_transition")
    up = md[(md.tier == 0.02) & md.silent & (md.direction == "up")
            & (md.horizon == 6) & (md.bench == "sector")]

    n = main_all["n"]
    dbar, t = main_all["mean_diff"], main_all["t"]
    ann = None if dbar is None else (1 + dbar) ** 2 - 1
    if n < 200:
        verdict, why = "量不出", f"主臂靜默向下事件只有 {n} 宗,少於 200 宗的門檻"
    elif dbar < 0 and t is not None and t <= -2.0 \
            and (main_a["mean_diff"] or 0) < 0 and (main_b["mean_diff"] or 0) < 0:
        verdict, why = "存在", "6 個月配對差為負、聚類 t ≤ −2、兩段同號"
    elif t is not None and abs(ann) < 0.01 and abs(t) < 1:
        verdict, why = "不存在", "配對差年化不足 1 個百分點且 |t| < 1"
    else:
        verdict, why = "量不出", "既未達存在門檻,亦未達不存在門檻"

    verdict_obj = dict(
        pre_named_cell="tier=0.02, silent, down, 6m, sector-ETF residual, "
                       "matched difference, sector x month clustered t",
        full_period=main_all, period_2009_2016=main_a, period_2017_2026=main_b,
        robustness_excl_standard_transition=rob,
        upward_same_cell=summarise(up, "all"),
        annualised_equivalent=None if ann is None else round(ann, 5),
        verdict=verdict, reason=why,
        note="探索票,不產生及格;冠軍格不是結論")
    (OUT / "verdict.json").write_text(
        json.dumps(verdict_obj, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    print(json.dumps(verdict_obj, indent=2, ensure_ascii=False, default=str),
          flush=True)

    # ---- tradable portfolio (CRITERIA sec.11) ------------------------------
    r1 = R[1]
    pmi = [i for i, m in enumerate(months) if PORT_START <= m <= PORT_END]
    rng = np.random.default_rng(SEED)
    recs = []
    prev_long = np.zeros(nT, dtype=bool)
    prev_short = np.zeros(nT, dtype=bool)
    prev_pool = np.zeros(nT, dtype=bool)
    rp_long = np.zeros((N_PATHS, nT), dtype=bool)
    rp_short = np.zeros((N_PATHS, nT), dtype=bool)
    rand_rows = []
    prev_nl = prev_ns = 0

    for i in pmi:
        pool = np.isfinite(r1[i]) & inidx[i]
        npool = int(pool.sum())
        if npool < 20:
            continue
        long_m = pool & (~recent_any[i])
        short_m = pool & recent_sd[i]
        nl, ns = int(long_m.sum()), int(short_m.sum())
        if ns == 0:
            continue
        rets = r1[i]
        lr = float(rets[long_m].mean())
        sr = float(rets[short_m].mean())
        pr = float(rets[pool].mean())
        c_l = float(ew_turnover(int(prev_long.sum()), nl,
                                int((prev_long & long_m).sum()))[0]) * COST_BP
        c_s = float(ew_turnover(int(prev_short.sum()), ns,
                                int((prev_short & short_m).sum()))[0]) * COST_BP
        c_p = float(ew_turnover(int(prev_pool.sum()), npool,
                                int((prev_pool & pool).sum()))[0]) * COST_BP
        recs.append(dict(month_end=months[i], n_pool=npool, n_long=nl, n_short=ns,
                         long_ret=lr, short_ret=sr, pool_ret=pr - c_p,
                         ls_ret=(lr - c_l) - (sr - c_s), long_only_ret=lr - c_l,
                         spy=BR[1]["SPY"][i], xlk=BR[1]["XLK"][i]))

        # luck band: same counts, same rebalance dates, same cost
        pool_ix = np.flatnonzero(pool)
        keys = rng.random((N_PATHS, npool))
        order = np.argsort(keys, axis=1)
        pr_ = rets[pool_ix]
        li = order[:, :nl]
        si_ = order[:, nl:nl + ns]
        rl = pr_[li].mean(axis=1)
        rs = pr_[si_].mean(axis=1)
        cur_l = np.zeros((N_PATHS, nT), dtype=bool)
        cur_s = np.zeros((N_PATHS, nT), dtype=bool)
        rowi = np.arange(N_PATHS)[:, None]
        cur_l[rowi, pool_ix[li]] = True
        cur_s[rowi, pool_ix[si_]] = True
        ov_l = (rp_long & cur_l).sum(axis=1)
        ov_s = (rp_short & cur_s).sum(axis=1)
        cl = ew_turnover(prev_nl, nl, ov_l) * COST_BP
        cs = ew_turnover(prev_ns, ns, ov_s) * COST_BP
        rand_rows.append((rl - cl) - (rs - cs))
        rp_long, rp_short = cur_l, cur_s
        prev_nl, prev_ns = nl, ns
        prev_long, prev_short, prev_pool = long_m, short_m, pool

    pf = pd.DataFrame(recs)
    pf.to_csv(OUT / "portfolio_monthly.csv", index=False, encoding="utf-8")
    band = np.vstack(rand_rows)          # (months, paths)

    def ann_ret(x) -> float:
        s = np.asarray(x, dtype=float)
        s = s[np.isfinite(s)]
        if len(s) == 0:
            return float("nan")
        return float(np.prod(1 + s) ** (12 / len(s)) - 1)

    a_ls = ann_ret(pf["ls_ret"])
    band_ann = np.array([ann_ret(band[:, p]) for p in range(N_PATHS)])
    bench = {"SPY": ann_ret(pf["spy"]), "XLK": ann_ret(pf["xlk"]),
             "same_pool_equal_weight": ann_ret(pf["pool_ret"])}
    port = dict(
        months=int(len(pf)), first=str(pf["month_end"].iloc[0].date()),
        last=str(pf["month_end"].iloc[-1].date()),
        long_short_annualised=round(a_ls, 5),
        long_only_no_revision_annualised=round(ann_ret(pf["long_only_ret"]), 5),
        benchmarks={k: round(v, 5) for k, v in bench.items()},
        diff_vs_benchmarks={k: round(a_ls - v, 5) for k, v in bench.items()},
        luck_band=dict(paths=N_PATHS,
                       p5=round(float(np.percentile(band_ann, 5)), 5),
                       p50=round(float(np.percentile(band_ann, 50)), 5),
                       p95=round(float(np.percentile(band_ann, 95)), 5)),
        diff_vs_luck_median=round(a_ls - float(np.percentile(band_ann, 50)), 5),
        percentile_in_luck_band=round(float((band_ann < a_ls).mean() * 100), 1),
        avg_n_long=round(float(pf["n_long"].mean()), 1),
        avg_n_short=round(float(pf["n_short"].mean()), 1),
        avg_n_pool=round(float(pf["n_pool"].mean()), 1),
        cost_bp=15,
        note="多空組合市場中性,對長倉基準的年化差額不是同類比較;"
             "同類的是運氣帶——同樣隻數、同樣換倉日、同樣成本的隨機多空。")
    (OUT / "portfolio.json").write_text(
        json.dumps(port, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(port, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
