# -*- coding: utf-8 -*-
"""KARST-160 第三步:十倍股起點(t0)特徵 vs 同期同宇宙非十倍股。
格級(cell-level)口徑:每一格 = (公司, 月底 t0, 5 年窗)。照 RULES.md 第五節。
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = r"C:\projects\Karst"
BASE = os.path.join(ROOT, "experiments", "2026-09-02-tenbagger-scan")
OUT = os.path.join(BASE, "out")
P_EXIST = os.path.join(ROOT, "experiments", "2026-09-02-timing-sweep", "data", "daily_close.parquet")
P_NEW = os.path.join(ROOT, "experiments", "2026-09-02-narrative-layers-v2", "data", "new_close.parquet")
P_PANEL = os.path.join(ROOT, "experiments", "2026-09-02-panel-scale-fix", "out", "panel_monthly_v2.parquet")
P_SPLIT = os.path.join(ROOT, "experiments", "2026-09-02-fourpiece-test", "data", "splits.parquet")
P_CHAIN = os.path.join(ROOT, "experiments", "2026-09-02-chain-layers", "chain_membership_v0.csv")
CONTAMINATED = {"CPWR", "EP", "PARA"}


def split_factor(panel):
    """F(t) = t 之後所有拆股比率之積。把申報原值股數還原到今日基準。"""
    sp = pd.read_parquet(P_SPLIT)
    sp["report_date"] = pd.to_datetime(sp["report_date"])
    out = np.ones(len(panel))
    idx = pd.Series(np.arange(len(panel)), index=pd.MultiIndex.from_arrays(
        [panel["ticker"].values, panel["month_end"].values]))
    for sym, g in sp.groupby("symbol"):
        if sym in CONTAMINATED:
            continue
        m = panel["ticker"].values == sym
        if not m.any():
            continue
        me = panel.loc[m, "month_end"].values
        f = np.ones(m.sum())
        for d, r in zip(g["report_date"].values, g["ratio"].values):
            f *= np.where(me < d, r, 1.0)
        out[m] = f
    return out


def auc(x, y):
    """秩 AUC:x 高者屬 y=1 的傾向。缺值剔除。"""
    ok = np.isfinite(x)
    x, y = x[ok], y[ok]
    if y.sum() == 0 or (1 - y).sum() == 0:
        return np.nan, 0, 0
    r = pd.Series(x).rank().to_numpy()
    n1, n0 = y.sum(), (1 - y).sum()
    a = (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    return float(a), int(n1), int(n0)


def main():
    wm = pd.read_parquet(os.path.join(OUT, "window_multiples.parquet"))
    wm = wm[wm.horizon == "5y"][["ticker", "t0", "multiple"]].copy()
    wm["is10x"] = (wm.multiple >= 10).astype(int)
    wm["year"] = wm.t0.dt.year

    px = pd.read_parquet(P_EXIST).join(pd.read_parquet(P_NEW), how="outer").sort_index()
    pan = pd.read_parquet(P_PANEL, columns=[
        "ticker", "month_end", "diluted_shares", "revenue_ttm", "cfo_ttm",
        "capex_ttm", "assets", "in_index"])
    pan = pan.sort_values(["ticker", "month_end"]).reset_index(drop=True)
    pan["sf"] = split_factor(pan)
    pan["shares_adj"] = pan["diluted_shares"] * pan["sf"]
    pan.loc[pan.ticker.isin(CONTAMINATED), "shares_adj"] = np.nan

    g = pan.groupby("ticker", sort=False)
    pan["shares_chg_12m"] = pan["shares_adj"] / g["shares_adj"].shift(12) - 1
    pan["rev_growth_12m"] = pan["revenue_ttm"] / g["revenue_ttm"].shift(12) - 1
    pan["capex_intensity"] = pan["capex_ttm"] / pan["assets"]
    pan["capex_int_chg_36m"] = pan["capex_intensity"] - g["capex_intensity"].shift(36)
    pan["cfo_positive"] = (pan["cfo_ttm"] > 0).astype(float)
    pan.loc[pan["cfo_ttm"].isna(), "cfo_positive"] = np.nan

    # t0 收市價 → 市值
    pxs = px.stack(future_stack=True).rename("close").reset_index()
    pxs.columns = ["date", "ticker", "close"]
    pan = pan.merge(pxs.rename(columns={"date": "month_end"}), on=["ticker", "month_end"], how="left")
    pan["mcap"] = pan["close"] * pan["shares_adj"]
    pan["log_mcap"] = np.log10(pan["mcap"].where(pan["mcap"] > 0))

    chain = pd.read_csv(P_CHAIN, encoding="utf-8-sig", engine="python", on_bad_lines="skip")
    themes = chain.groupby("ticker")["theme"].apply(lambda s: "|".join(sorted(set(s)))).to_dict()
    pan["in_chain"] = pan["ticker"].map(lambda t: 1.0 if t in themes else 0.0)

    cells = wm.merge(pan, left_on=["ticker", "t0"], right_on=["ticker", "month_end"], how="inner")
    cells.to_parquet(os.path.join(OUT, "t0_cells.parquet"), index=False)

    FEATS = {
        "log_mcap": "起點市值(log10 美元)",
        "shares_chg_12m": "前 12 個月股數變化",
        "rev_growth_12m": "營業額 TTM 12 個月增速",
        "cfo_positive": "經營現金流為正(1/0)",
        "capex_int_chg_36m": "資本開支/資產 36 個月變化",
        "in_chain": "在 v0 鏈表某鏈位(1/0)",
        "in_index": "起點時為標普成分(1/0)",
    }

    rows = []
    y = cells["is10x"].to_numpy()
    for f, label in FEATS.items():
        x = pd.to_numeric(cells[f], errors="coerce").to_numpy(dtype=float)
        a, n1, n0 = auc(x, y)
        ok = np.isfinite(x)
        q = lambda mask, p: (np.nanpercentile(x[ok & mask], p) if (ok & mask).sum() else np.nan)
        m1, m0 = (y == 1), (y == 0)
        rows.append({
            "feature": f, "label": label,
            "n_10x_cells": n1, "n_non10x_cells": n0,
            "median_10x": round(float(q(m1, 50)), 4), "median_non10x": round(float(q(m0, 50)), 4),
            "p25_10x": round(float(q(m1, 25)), 4), "p75_10x": round(float(q(m1, 75)), 4),
            "p25_non10x": round(float(q(m0, 25)), 4), "p75_non10x": round(float(q(m0, 75)), 4),
            "AUC": round(a, 4) if a == a else None,
            "separation_abs": round(abs(a - 0.5), 4) if a == a else None,
        })
    tab = pd.DataFrame(rows).sort_values("separation_abs", ascending=False)
    tab.to_csv(os.path.join(OUT, "t0_features.csv"), index=False, encoding="utf-8-sig")
    print(tab[["feature", "median_10x", "median_non10x", "AUC", "n_10x_cells", "n_non10x_cells"]].to_string(index=False))

    # 年份分層 AUC(避免「十倍股集中在某幾年」的混淆)
    yr = []
    for f in FEATS:
        aa = []
        for year, gg in cells.groupby("year"):
            x = pd.to_numeric(gg[f], errors="coerce").to_numpy(dtype=float)
            a, n1, n0 = auc(x, gg["is10x"].to_numpy())
            if a == a and n1 >= 5:
                aa.append((a, n1 + n0))
        if aa:
            w = np.array([n for _, n in aa], dtype=float)
            yr.append({"feature": f, "n_years": len(aa),
                       "AUC_year_weighted": round(float(np.average([a for a, _ in aa], weights=w)), 4),
                       "AUC_year_median": round(float(np.median([a for a, _ in aa])), 4)})
    ytab = pd.DataFrame(yr)
    ytab["separation_abs"] = (ytab["AUC_year_weighted"] - 0.5).abs()
    ytab = ytab.sort_values("separation_abs", ascending=False)
    ytab.to_csv(os.path.join(OUT, "t0_features_by_year.csv"), index=False, encoding="utf-8-sig")
    print()
    print(ytab.to_string(index=False))

    json.dump({"cells": int(len(cells)), "cells_10x": int(y.sum()),
               "tickers_with_panel": int(cells.ticker.nunique())},
              open(os.path.join(OUT, "t0_features_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
