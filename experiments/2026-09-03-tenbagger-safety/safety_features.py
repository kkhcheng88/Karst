# -*- coding: utf-8 -*-
"""KARST-166 第二步:三個安全邊際特徵、分辨力、誤殺率、死亡率、市值分組。

照 CRITERIA.md。格級口徑、知情時點、拆股對齊、AUC 算法全部沿用 KARST-160
(直接 import features_t0.py 的 split_factor 與 auc,不自寫一套)。

輸出 out/:
  safety_cells.parquet       每格的三個特徵與門檻通過與否
  auc_table.csv              全樣本與逐年加權 AUC + 判詞
  auc_by_year.csv            逐年 AUC 明細
  threshold_table.csv        三個門檻 + 兩個組合的誤殺率 / 剔走率
  mortality.csv              死亡率(有 / 無安全邊際)
  by_mcap_tercile.csv        市值三分位組內 AUC 與誤殺率
  control_arm.csv            KARST-160 三項對照臂(同一批可算格)
  summary.json               覆蓋與關鍵數字
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(r"C:\projects\Karst")
SCAN = ROOT / "experiments" / "2026-09-02-tenbagger-scan"
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SCAN))
import features_t0 as f160  # noqa: E402  KARST-160 的口徑,原封不動

P_PANEL = ROOT / "experiments" / "2026-09-02-panel-scale-fix" / "out" / "panel_monthly_v2.parquet"
P_EXIST = ROOT / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
P_NEW = ROOT / "experiments" / "2026-09-02-narrative-layers-v2" / "data" / "new_close.parquet"

RUNWAY_CAP = 99.0
MIN_CELLS, MIN_10X, AUC_LINE = 1000, 50, 0.05

FEATS = {
    "s1_net_cash_to_mcap": "S1 淨現金對市值",
    "s2_runway_yrs": "S2 現金跑道(年,自由現金流口徑)",
    "s3_tangible_nav_to_mcap": "S3 有形資產淨值對市值",
    "s2b_runway_cfo_yrs": "S2b 現金跑道(年,只看經營現金流)",
    "s3b_book_nav_to_mcap": "S3b 帳面淨值對市值(不扣無形)",
}
CONTROL = {
    "log_mcap": "對照 起點市值(log10 美元)",
    "in_index": "對照 起點時為標普成分",
    "shares_chg_12m": "對照 前 12 個月股數變化",
}


def auc_pair(df, col, ycol="is10x"):
    """全樣本 AUC 與逐年加權 AUC(CRITERIA 第四節)。"""
    x = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
    y = df[ycol].to_numpy()
    a_all, n1, n0 = f160.auc(x, y)
    per_year = []
    for yr, g in df.groupby("year"):
        xx = pd.to_numeric(g[col], errors="coerce").to_numpy(dtype=float)
        a, k1, k0 = f160.auc(xx, g[ycol].to_numpy())
        if a == a and k1 >= 5:
            per_year.append((int(yr), a, k1 + k0, k1))
    if per_year:
        w = np.array([n for _, _, n, _ in per_year], dtype=float)
        a_yr = float(np.average([a for _, a, _, _ in per_year], weights=w))
    else:
        a_yr = float("nan")
    return a_all, a_yr, n1, n0, per_year


def verdict(a_all, a_yr, n1, n0):
    if n1 < MIN_10X or (n1 + n0) < MIN_CELLS:
        return "量不出", "覆蓋不足"
    if a_yr != a_yr or a_all != a_all:
        return "量不出", "逐年加權算不出"
    if (a_all - 0.5) * (a_yr - 0.5) <= 0:
        return "量不出", "全樣本與逐年加權分處 0.5 兩側"
    if abs(a_yr - 0.5) < AUC_LINE:
        return "不存在", f"偏離 {abs(a_yr - 0.5):.3f} < {AUC_LINE}"
    d = "數值大的一邊才是十倍股" if a_yr > 0.5 else "數值細的一邊才是十倍股"
    return "存在", d


def build_cells() -> pd.DataFrame:
    wm = pd.read_parquet(SCAN / "out" / "window_multiples.parquet")
    wm = wm[wm.horizon == "5y"][["ticker", "t0", "multiple"]].copy()
    wm["is10x"] = (wm.multiple >= 10).astype(int)
    wm["year"] = wm.t0.dt.year

    pan = pd.read_parquet(P_PANEL, columns=[
        "ticker", "month_end", "diluted_shares", "cash", "lt_debt", "equity",
        "cfo_ttm", "capex_ttm", "assets", "in_index"])
    pan = pan.sort_values(["ticker", "month_end"]).reset_index(drop=True)
    pan["in_index"] = pd.to_numeric(pan["in_index"], errors="coerce").astype(float)
    pan["sf"] = f160.split_factor(pan)
    pan["shares_adj"] = pan["diluted_shares"] * pan["sf"]
    pan.loc[pan.ticker.isin(f160.CONTAMINATED), "shares_adj"] = np.nan
    g = pan.groupby("ticker", sort=False)
    pan["shares_chg_12m"] = pan["shares_adj"] / g["shares_adj"].shift(12) - 1

    ex = pd.read_parquet(OUT / "panel_extra_v1.parquet")
    pan = pan.merge(ex, on=["ticker", "month_end"], how="left")

    px = pd.read_parquet(P_EXIST).join(pd.read_parquet(P_NEW), how="outer").sort_index()
    pxs = px.stack(future_stack=True).rename("close").reset_index()
    pxs.columns = ["date", "ticker", "close"]
    pan = pan.merge(pxs.rename(columns={"date": "month_end"}),
                    on=["ticker", "month_end"], how="left")
    pan["mcap"] = pan["close"] * pan["shares_adj"]
    pan["log_mcap"] = np.log10(pan["mcap"].where(pan["mcap"] > 0))

    c = wm.merge(pan, left_on=["ticker", "t0"], right_on=["ticker", "month_end"],
                 how="inner")

    # ---- S1 淨現金對市值 ---------------------------------------------------
    st = c["st_debt"].fillna(0.0)                       # 缺 → 當 0(CRITERIA 三)
    total_debt = c["lt_debt"] + st                      # lt_debt 缺 → 整條缺
    c["total_debt"] = total_debt
    c["s1_net_cash_to_mcap"] = (c["cash"] - total_debt) / c["mcap"]

    # ---- S2 現金跑道 -------------------------------------------------------
    fcf = c["cfo_ttm"] - c["capex_ttm"]
    burn = (-fcf).clip(lower=0.0)
    runway = np.where(burn > 0, c["cash"] / burn.replace(0, np.nan), RUNWAY_CAP)
    runway = pd.Series(runway, index=c.index).clip(upper=RUNWAY_CAP)
    runway[c["cash"].isna() | fcf.isna()] = np.nan
    c["s2_runway_yrs"] = runway
    c["s2_infinite"] = (burn <= 0) & fcf.notna() & c["cash"].notna()

    burn_b = (-c["cfo_ttm"]).clip(lower=0.0)
    rb = np.where(burn_b > 0, c["cash"] / burn_b.replace(0, np.nan), RUNWAY_CAP)
    rb = pd.Series(rb, index=c.index).clip(upper=RUNWAY_CAP)
    rb[c["cash"].isna() | c["cfo_ttm"].isna()] = np.nan
    c["s2b_runway_cfo_yrs"] = rb

    # ---- S3 有形資產淨值對市值 --------------------------------------------
    tang = c["equity"] - c["goodwill"].fillna(0.0) - c["intangibles"].fillna(0.0)
    c["s3_tangible_nav_to_mcap"] = tang / c["mcap"]
    c["s3b_book_nav_to_mcap"] = c["equity"] / c["mcap"]

    # ---- 門檻 --------------------------------------------------------------
    c["T1"] = np.where(c["s1_net_cash_to_mcap"].notna(),
                       c["s1_net_cash_to_mcap"] > 0, np.nan)
    c["T2"] = np.where(c["s2_runway_yrs"].notna(), c["s2_runway_yrs"] >= 2, np.nan)
    c["T3"] = np.where(c["s3_tangible_nav_to_mcap"].notna(),
                       c["s3_tangible_nav_to_mcap"] >= 0.30, np.nan)
    t = c[["T1", "T2", "T3"]]
    n_known = t.notna().sum(axis=1)
    n_pass = (t == 1).sum(axis=1)
    c["T_strict"] = np.where(n_known == 3, (n_pass == 3).astype(float), np.nan)
    c["T_prac"] = np.where(n_known >= 1, (n_pass == n_known).astype(float), np.nan)
    return c, px


def mortality(c, px):
    """CRITERIA 第六節。細(<25 億)且不在指數的格,其後五年跌逾 90% 或退市。"""
    grp = c[(c.mcap < 2.5e9) & (c.in_index == 0)].copy()
    dates = px.index.to_numpy()
    panel_last = pd.Timestamp(dates[-1])
    dead = np.zeros(len(grp), dtype=bool)
    delisted = np.zeros(len(grp), dtype=bool)
    drop90 = np.zeros(len(grp), dtype=bool)
    last_valid = {}
    for tk in grp.ticker.unique():
        s = px[tk].dropna() if tk in px.columns else pd.Series(dtype=float)
        last_valid[tk] = s.index[-1] if len(s) else pd.NaT
    for pos, (i, r) in enumerate(grp.iterrows()):
        tk = r.ticker
        if tk not in px.columns:
            continue
        s = px[tk]
        end = r.t0 + pd.DateOffset(years=5)
        seg = s.loc[(s.index > r.t0) & (s.index <= end)].dropna()
        if len(seg) and r.close and r.close > 0:
            drop90[pos] = (seg.min() / r.close - 1) <= -0.90
        lv = last_valid.get(tk)
        if lv is not pd.NaT and lv is not None and pd.notna(lv):
            delisted[pos] = (lv < end) and (lv < panel_last - pd.Timedelta(days=90))
        dead[pos] = drop90[pos] or delisted[pos]
    grp["dead"] = dead
    grp["drop90"] = drop90
    grp["delisted"] = delisted
    return grp


def main() -> None:
    c, px = build_cells()
    c.to_parquet(OUT / "safety_cells.parquet", index=False)

    # ---- 分辨力 ------------------------------------------------------------
    rows, yr_rows = [], []
    for col, label in {**FEATS, **CONTROL}.items():
        a_all, a_yr, n1, n0, per_year = auc_pair(c, col)
        v, note = verdict(a_all, a_yr, n1, n0)
        ok = c[col].notna()
        m1, m0 = ok & (c.is10x == 1), ok & (c.is10x == 0)
        rows.append(dict(
            feature=col, label=label, arm="安全邊際" if col in FEATS else "對照",
            n_cells=int(n1 + n0), n_10x=int(n1),
            median_10x=round(float(c.loc[m1, col].median()), 4) if m1.any() else None,
            median_non10x=round(float(c.loc[m0, col].median()), 4) if m0.any() else None,
            p25_10x=round(float(c.loc[m1, col].quantile(.25)), 4) if m1.any() else None,
            p75_10x=round(float(c.loc[m1, col].quantile(.75)), 4) if m1.any() else None,
            AUC_full=round(a_all, 4) if a_all == a_all else None,
            AUC_year_weighted=round(a_yr, 4) if a_yr == a_yr else None,
            separation=round(abs(a_yr - 0.5), 4) if a_yr == a_yr else None,
            verdict=v, note=note))
        for yy, a, n, k1 in per_year:
            yr_rows.append(dict(feature=col, year=yy, AUC=round(a, 4),
                                n_cells=n, n_10x=k1))
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "auc_table.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(yr_rows).to_csv(OUT / "auc_by_year.csv", index=False,
                                 encoding="utf-8-sig")

    # ---- 誤殺率 vs 剔走率 --------------------------------------------------
    th_rows = []
    for th, name in [("T1", "T1 淨現金為正"), ("T2", "T2 跑道 ≥2 年"),
                     ("T3", "T3 有形淨值 ≥ 市值三成"),
                     ("T_strict", "T-嚴格 三條全算得出且全過"),
                     ("T_prac", "T-實務 算得出的都要過")]:
        ok = c[th].notna()
        cut = ok & (c[th] == 0)                 # 不合門檻 = 被剔走
        n_all, n_10 = int(ok.sum()), int((ok & (c.is10x == 1)).sum())
        if n_10 == 0:
            continue
        fk = float((cut & (c.is10x == 1)).sum()) / n_10
        cull = float(cut.sum()) / n_all
        th_rows.append(dict(
            threshold=th, label=name,
            n_cells_with_fields=n_all, n_10x_with_fields=n_10,
            false_kill_rate=round(fk, 4), cull_rate=round(cull, 4),
            ratio=round(fk / cull, 3) if cull > 0 else None,
            pass_rate_10x=round(1 - fk, 4),
            pass_rate_all=round(1 - cull, 4)))
    pd.DataFrame(th_rows).to_csv(OUT / "threshold_table.csv", index=False,
                                 encoding="utf-8-sig")

    # ---- 死亡率 ------------------------------------------------------------
    grp = mortality(c, px)
    mrows = []
    for key, sub in [("有安全邊際(T-實務過)", grp[grp.T_prac == 1]),
                     ("無安全邊際(T-實務不過)", grp[grp.T_prac == 0]),
                     ("欄位算不出", grp[grp.T_prac.isna()]),
                     ("全體細而不在指數", grp)]:
        if not len(sub):
            continue
        mrows.append(dict(
            group=key, n_cells=int(len(sub)),
            death_rate=round(float(sub.dead.mean()), 4),
            drop90_rate=round(float(sub.drop90.mean()), 4),
            delisted_rate=round(float(sub.delisted.mean()), 4),
            ten_x_rate=round(float(sub.is10x.mean()), 4),
            n_10x=int(sub.is10x.sum())))
    md = pd.DataFrame(mrows)
    md.to_csv(OUT / "mortality.csv", index=False, encoding="utf-8-sig")

    # 逐個門檻的死亡率差
    mth = []
    for th in ["T1", "T2", "T3", "T_strict", "T_prac"]:
        a = grp[grp[th] == 1]
        b = grp[grp[th] == 0]
        if len(a) < 30 or len(b) < 30:
            mth.append(dict(threshold=th, note="任一組不足 30 格,量不出",
                            n_pass=len(a), n_fail=len(b)))
            continue
        mth.append(dict(
            threshold=th, n_pass=int(len(a)), n_fail=int(len(b)),
            death_pass=round(float(a.dead.mean()), 4),
            death_fail=round(float(b.dead.mean()), 4),
            death_diff_pp=round(float((b.dead.mean() - a.dead.mean()) * 100), 2),
            tenx_pass=round(float(a.is10x.mean()), 4),
            tenx_fail=round(float(b.is10x.mean()), 4),
            tenx_diff_pp=round(float((a.is10x.mean() - b.is10x.mean()) * 100), 2)))
    pd.DataFrame(mth).to_csv(OUT / "mortality_by_threshold.csv", index=False,
                             encoding="utf-8-sig")

    # ---- 市值三分位組內 ----------------------------------------------------
    cc = c[c.log_mcap.notna()].copy()
    cc["terc"] = cc.groupby("year")["log_mcap"].transform(
        lambda s: pd.qcut(s, 3, labels=["細", "中", "大"], duplicates="drop")
        if s.notna().sum() >= 30 else pd.Series(index=s.index, dtype="object"))
    trows = []
    for terc, sub in cc.groupby("terc", observed=True):
        for col in list(FEATS) + list(CONTROL):
            a_all, a_yr, n1, n0, _ = auc_pair(sub, col)
            trows.append(dict(tercile=terc, feature=col, n_cells=int(n1 + n0),
                              n_10x=int(n1),
                              AUC_full=round(a_all, 4) if a_all == a_all else None,
                              AUC_year_weighted=round(a_yr, 4) if a_yr == a_yr else None))
        for th in ["T1", "T2", "T3", "T_prac"]:
            ok = sub[th].notna()
            cut = ok & (sub[th] == 0)
            n10 = int((ok & (sub.is10x == 1)).sum())
            if n10 == 0 or ok.sum() == 0:
                continue
            fk = float((cut & (sub.is10x == 1)).sum()) / n10
            cull = float(cut.sum()) / int(ok.sum())
            trows.append(dict(tercile=terc, feature=th + " 誤殺/剔走",
                              n_cells=int(ok.sum()), n_10x=n10,
                              AUC_full=round(fk, 4), AUC_year_weighted=round(cull, 4)))
    pd.DataFrame(trows).to_csv(OUT / "by_mcap_tercile.csv", index=False,
                               encoding="utf-8-sig")

    # ---- 覆蓋 --------------------------------------------------------------
    summary = dict(
        cells_total=int(len(c)), cells_10x=int(c.is10x.sum()),
        tickers=int(c.ticker.nunique()),
        coverage={col: dict(
            cells=int(c[col].notna().sum()),
            cells_10x=int((c[col].notna() & (c.is10x == 1)).sum()),
            share_of_all_10x=round(float((c[col].notna() & (c.is10x == 1)).sum()
                                         / max(1, c.is10x.sum())), 4))
                  for col in FEATS},
        st_debt_missing_share=round(float(c.st_debt.isna().mean()), 4),
        goodwill_missing_share=round(float(c.goodwill.isna().mean()), 4),
        intangibles_missing_share=round(float(c.intangibles.isna().mean()), 4),
        s2_infinite_share=round(float(c.s2_infinite.mean()), 4),
        mortality_group_cells=int(len(grp)),
        price_panel_last=str(px.index[-1].date()),
    )
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")

    print(tab[["feature", "median_10x", "median_non10x", "AUC_full",
               "AUC_year_weighted", "n_10x", "verdict"]].to_string(index=False))
    print()
    print(pd.DataFrame(th_rows).to_string(index=False))
    print()
    print(md.to_string(index=False))


if __name__ == "__main__":
    main()
