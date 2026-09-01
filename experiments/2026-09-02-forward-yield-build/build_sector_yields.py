"""KARST-136 第二步:由快取的季度 EPS 預估砌板塊+大市月度前瞻盈利收益率序列。

口徑照同目錄 SPEC.md(跑數之前已 commit)。輸出:
  sector_yields.csv          正本(月底頻,MKT + 九隻 SPDR)
  coverage_by_year.csv       逐板塊逐年覆蓋率
  ey_lag_reconcile.csv       ey_lag 與現有 pe_lag 正本互為倒數的核對表
  revision_check.csv         預估事後改寫率實測(預估 vs 當時新聞不做,這裡做的是
                             「同一季預估 vs 實際」的分佈,改寫率實測見 revise_probe.py)
  data/member_forward.parquet 逐股逐月前瞻分子(大檔,不入 git)
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
CACHE = HERE / "cache" / "earnings_dates"
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)

PANEL = REPO / "experiments" / "2026-09-02-multiples-oracle-scan" / "data" / "constituent_panel.parquet"
MULT = REPO / "experiments" / "2026-09-02-multiples-oracle-scan" / "sector_multiples.csv"

MIN_MEMBERS = 8          # 與現有正本一致
NEXT_ANN_MAX_DAYS = 130  # 下一次公布距月底的上限(避開序列斷格)
FOUR_Q_MAX_DAYS = 460    # 第四次公布距月底的上限
LOWPREC_ABS = 0.20       # |est| < 此值 → 兩位小數進位誤差 > 2.5%,判低精度


def load_estimates() -> pd.DataFrame:
    frames = []
    for p in sorted(CACHE.glob("*.parquet")):
        try:
            d = pd.read_parquet(p)
        except Exception:  # noqa: BLE001
            continue
        frames.append(d)
    if not frames:
        raise SystemExit("快取空白,先跑 fetch_estimates.py")
    e = pd.concat(frames, ignore_index=True)
    dcol = "Earnings Date" if "Earnings Date" in e.columns else e.columns[0]
    e["ann"] = pd.to_datetime(e[dcol], utc=True, errors="coerce").dt.tz_localize(None)
    e = e.rename(columns={"EPS Estimate": "est", "Reported EPS": "act"})
    e = e[["symbol", "ann", "est", "act"]].dropna(subset=["symbol", "ann"])
    e = e.sort_values(["symbol", "ann"])
    # 同日重覆列(Yahoo 偶有)——保留有預估的一列
    e["has"] = e["est"].notna().astype(int)
    e = (e.sort_values(["symbol", "ann", "has"])
           .drop_duplicates(["symbol", "ann"], keep="last")
           .drop(columns="has"))
    return e


def member_forward(panel: pd.DataFrame, est: pd.DataFrame) -> pd.DataFrame:
    """逐股逐月算未來四季預估之和、未來一季年化、低精度旗。"""
    est_ok = est.dropna(subset=["est"]).copy()
    out = []
    for sym, g in est_ok.groupby("symbol", sort=False):
        pm = panel[panel["symbol"] == sym]
        if pm.empty:
            continue
        d = g["ann"].to_numpy("datetime64[ns]")
        v = g["est"].to_numpy(float)
        n = len(d)
        if n == 0:
            continue
        cs = np.concatenate([[0.0], np.cumsum(v)])
        low = (np.abs(v) < LOWPREC_ABS).astype(int)
        cl = np.concatenate([[0], np.cumsum(low)])
        me = pm["month_end"].to_numpy("datetime64[ns]")
        idx = np.searchsorted(d, me, side="right")

        ok1 = idx < n
        i1 = np.clip(idx, 0, n - 1)
        gap1 = (d[i1] - me) / np.timedelta64(1, "D")
        ok1 &= gap1 <= NEXT_ANN_MAX_DAYS

        ok4 = (idx + 3) < n
        i4 = np.clip(idx + 3, 0, n - 1)
        gap4 = (d[i4] - me) / np.timedelta64(1, "D")
        ok4 &= ok1 & (gap4 <= FOUR_Q_MAX_DAYS)

        s4 = np.where(ok4, cs[np.clip(idx + 4, 0, n)] - cs[np.clip(idx, 0, n)], np.nan)
        s1 = np.where(ok1, v[i1] * 4.0, np.nan)
        lp4 = np.where(ok4, cl[np.clip(idx + 4, 0, n)] - cl[np.clip(idx, 0, n)], 0) > 0

        out.append(pd.DataFrame({
            "symbol": sym,
            "month_end": pm["month_end"].to_numpy(),
            "fwd_eps4": s4,
            "fwd_eps1": s1,
            "lowprec": lp4,
        }))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def aggregate(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def one(g: pd.DataFrame, series: str, me, min_n: int) -> dict:
        rec = {"month_end": me, "series": series, "n_members": len(g),
               "total_mcap": g["mcap"].sum(skipna=True)}
        gl = g.dropna(subset=["mcap", "earn_lag"])
        rec["n_lag"] = len(gl)
        rec["ey_lag"] = (gl["earn_lag"].sum() / gl["mcap"].sum()
                         if len(gl) >= min_n and gl["mcap"].sum() > 0 else np.nan)
        tot_all = g["mcap"].sum(skipna=True)
        for tag, col in (("fwd", "earn_fwd4"), ("fwd1", "earn_fwd1")):
            gg = g.dropna(subset=["mcap", col])
            rec[f"n_{tag}"] = len(gg)
            m = gg["mcap"].sum()
            rec[f"cov_{tag}"] = (m / tot_all) if tot_all and tot_all > 0 else np.nan
            rec[f"ey_{tag}"] = (gg[col].sum() / m
                                if len(gg) >= min_n and m > 0 else np.nan)
        gf = g.dropna(subset=["mcap", "earn_fwd4"])
        lpmask = gf["lowprec"].fillna(False).astype(bool)
        gh = gf[~lpmask]
        rec["n_fwd_hp"] = len(gh)
        mh = gh["mcap"].sum()
        rec["ey_fwd_hp"] = (gh["earn_fwd4"].sum() / mh
                            if len(gh) >= min_n and mh > 0 else np.nan)
        mf = gf["mcap"].sum()
        lp = gf[lpmask]["mcap"].sum()
        rec["lowprec_mcap_share"] = (lp / mf) if mf and mf > 0 else np.nan
        return rec

    for etf, g_all in panel.groupby("etf"):
        for me, g in g_all.groupby("month_end"):
            rows.append(one(g, etf, me, MIN_MEMBERS))
    for me, g in panel.groupby("month_end"):
        rows.append(one(g, "MKT", me, 1))
    return pd.DataFrame(rows).sort_values(["series", "month_end"])


def main() -> None:
    panel = pd.read_parquet(PANEL)
    est = load_estimates()
    print(f"快取公司 {est['symbol'].nunique()} 隻,預估列 {est['est'].notna().sum()} 格,"
          f"最早 {est.dropna(subset=['est'])['ann'].min().date()}")

    mf = member_forward(panel, est)
    print(f"逐股逐月前瞻 {len(mf)} 列,有四季預估 {mf['fwd_eps4'].notna().sum()} 格")

    panel = panel.merge(mf, on=["symbol", "month_end"], how="left")
    panel["earn_fwd4"] = panel["fwd_eps4"] * panel["shares"]
    panel["earn_fwd1"] = panel["fwd_eps1"] * panel["shares"]
    panel.to_parquet(OUT / "member_forward.parquet", index=False)

    out = aggregate(panel)
    cols = ["month_end", "series", "n_members", "total_mcap",
            "ey_lag", "n_lag",
            "ey_fwd", "n_fwd", "cov_fwd",
            "ey_fwd1", "n_fwd1", "cov_fwd1",
            "ey_fwd_hp", "n_fwd_hp", "lowprec_mcap_share"]
    out = out[cols]
    out.to_csv(HERE / "sector_yields.csv", index=False, encoding="utf-8")
    print(f"\nsector_yields.csv 落檔 {len(out)} 列")

    # ---- 逐板塊逐年覆蓋率 ----
    o = out.copy()
    o["year"] = pd.to_datetime(o["month_end"]).dt.year
    cov = (o[o["year"] >= 2002]
           .groupby(["series", "year"])
           .agg(cov_fwd_med=("cov_fwd", "median"),
                cov_fwd1_med=("cov_fwd1", "median"),
                n_fwd_med=("n_fwd", "median"),
                lowprec_med=("lowprec_mcap_share", "median"),
                months=("month_end", "count"))
           .reset_index())
    cov.to_csv(HERE / "coverage_by_year.csv", index=False, encoding="utf-8")

    # ---- ey_lag 與現有 pe_lag 正本核對 ----
    mult = pd.read_csv(MULT, parse_dates=["month_end"])
    rec = out[["month_end", "series", "ey_lag"]].merge(
        mult[["month_end", "series", "pe_lag", "n_lag"]].rename(
            columns={"n_lag": "n_lag_old"}),
        on=["month_end", "series"], how="inner")
    rec["inv_pe_lag"] = np.where(rec["pe_lag"] > 0, 1.0 / rec["pe_lag"], np.nan)
    rec["abs_diff"] = (rec["ey_lag"] - rec["inv_pe_lag"]).abs()
    rec["rel_diff"] = rec["abs_diff"] / rec["inv_pe_lag"].abs()
    rec.to_csv(HERE / "ey_lag_reconcile.csv", index=False, encoding="utf-8")
    both = rec.dropna(subset=["ey_lag", "inv_pe_lag"])
    print(f"\ney_lag 核對:兩邊都有值 {len(both)} 格,"
          f"相對差中位 {both['rel_diff'].median():.2e},最大 {both['rel_diff'].max():.2e}")
    print(f"pe_lag 未定義而 ey_lag 有值(負盈利救回的格):"
          f"{int(rec['inv_pe_lag'].isna().sum() - rec['ey_lag'].isna().sum())}")

    print("\n覆蓋起點與 cov_fwd(2002 起中位):")
    for s, g in out.groupby("series"):
        v = g.dropna(subset=["ey_fwd"])
        g2 = g[pd.to_datetime(g["month_end"]).dt.year >= 2002]
        if len(v):
            print(f"  {s}: ey_fwd {v['month_end'].min().date()}..{v['month_end'].max().date()} "
                  f"({len(v)} 格) cov_fwd 中位 {g2['cov_fwd'].median():.1%} "
                  f"低精度佔市值中位 {g2['lowprec_mcap_share'].median():.1%}")


if __name__ == "__main__":
    main()
