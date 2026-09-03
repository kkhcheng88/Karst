# -*- coding: utf-8 -*-
"""KARST-176 共用:AUC、判詞、總債務補算、面板 v3 時點取值。全部唯讀。

判準見同目錄 CRITERIA.md;本檔只實作,不新增定義。
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(r"C:\projects\Karst")
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

SCAN = ROOT / "experiments" / "2026-09-02-tenbagger-scan"
SAFETY = ROOT / "experiments" / "2026-09-03-tenbagger-safety"
sys.path.insert(0, str(SCAN))
import features_t0 as f160  # noqa: E402  KARST-160 的口徑,原封不動

P_PANEL_V2 = ROOT / "experiments" / "2026-09-02-panel-scale-fix" / "out" / "panel_monthly_v2.parquet"
P_EXTRA = SAFETY / "out" / "panel_extra_v1.parquet"
P_EXIST = ROOT / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
P_NEW = ROOT / "experiments" / "2026-09-02-narrative-layers-v2" / "data" / "new_close.parquet"
P_PANEL_V3 = ROOT / "data" / "panel" / "quarterly_v3.parquet"
PRICE_DIR = ROOT / "data" / "prices" / "daily"
UNIVERSE = ROOT / "data" / "universe"
SPLITS = ROOT / "experiments" / "2026-09-02-fourpiece-test" / "data" / "splits.parquet"

CONTAMINATED = f160.CONTAMINATED           # CPWR / EP / PARA
MIN_CELLS, MIN_10X, AUC_LINE = 1000, 50, 0.05

V3_COLS = ["entity_id", "filed_date", "period_end", "cash_and_equivalents",
           "lt_debt", "st_debt", "total_debt", "shares_outstanding", "currency"]


# --------------------------------------------------------------------------
# 判準第二節:AUC 與判詞(照 KARST-166 一字不改)
# --------------------------------------------------------------------------
def auc_pair(df: pd.DataFrame, col: str, ycol: str = "is10x"):
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


def verdict(a_all: float, a_yr: float, n1: int, n0: int):
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


def four_numbers(df: pd.DataFrame, col: str, label: str, note: str = "") -> dict:
    """判準第六節:分辨力、覆蓋、淨現金為正比率、真十倍股被殺比率。"""
    a_all, a_yr, n1, n0, per_year = auc_pair(df, col)
    v, why = verdict(a_all, a_yr, n1, n0)
    ok = df[col].notna()
    pos = ok & (df[col] > 0)
    m1 = ok & (df.is10x == 1)
    rate_10x = float(pos[m1].mean()) if m1.any() else float("nan")
    rate_all = float(pos[ok].mean()) if ok.any() else float("nan")
    # 逐年加權對照組比率:按十倍格的年份分佈加權
    num = den = 0.0
    for yr, g in df[ok].groupby("year"):
        k1 = int((g.is10x == 1).sum())
        if k1 == 0:
            continue
        num += float((g[col] > 0).mean()) * k1
        den += k1
    rate_all_yw = num / den if den else float("nan")
    return dict(
        step=label, note=note,
        n_cells=int(n1 + n0), n_10x=int(n1),
        n_tickers=int(df.loc[ok, "key"].nunique()) if "key" in df.columns else None,
        AUC_full=round(a_all, 4) if a_all == a_all else None,
        AUC_year_weighted=round(a_yr, 4) if a_yr == a_yr else None,
        separation=round(abs(a_yr - 0.5), 4) if a_yr == a_yr else None,
        verdict=v, verdict_note=why,
        netcash_pos_10x=round(rate_10x, 4) if rate_10x == rate_10x else None,
        netcash_pos_all=round(rate_all, 4) if rate_all == rate_all else None,
        netcash_pos_all_yearweighted=round(rate_all_yw, 4) if rate_all_yw == rate_all_yw else None,
        false_kill_10x=round(1 - rate_10x, 4) if rate_10x == rate_10x else None,
        cull_rate_all=round(1 - rate_all, 4) if rate_all == rate_all else None,
        n_years_used=len(per_year)), per_year


# --------------------------------------------------------------------------
# 判準第四節:總債務補算
# --------------------------------------------------------------------------
def fill_total_debt(lt: pd.Series, st: pd.Series):
    """回傳(補後總債務, 標記)。租賃負債原料層沒有標籤,一律補不到。"""
    lt = pd.to_numeric(lt, errors="coerce")
    st = pd.to_numeric(st, errors="coerce")
    orig = lt + st.fillna(0.0)                      # lt 缺 → 整條缺(v3 原口徑)
    filled = orig.copy()
    only_st = lt.isna() & st.notna()
    filled[only_st] = st[only_st]
    tag = pd.Series("tag_absent", index=lt.index, dtype=object)
    tag[lt.notna()] = "orig"
    tag[only_st] = "filled_st_only"
    return orig, filled, tag


# --------------------------------------------------------------------------
# 面板 v3 時點取值
# --------------------------------------------------------------------------
def panel_v3() -> pd.DataFrame:
    p = pd.read_parquet(P_PANEL_V3, columns=V3_COLS)
    p = p[p["filed_date"].notna()].copy()
    orig, filled, tag = fill_total_debt(p["lt_debt"], p["st_debt"])
    p["total_debt_orig"] = orig
    p["total_debt_filled"] = filled
    p["debt_fill_tag"] = tag
    return p.sort_values(["filed_date", "entity_id"]).reset_index(drop=True)


def asof_v3(cells: pd.DataFrame, p3: pd.DataFrame, when: str = "t0",
            key: str = "entity_id") -> pd.DataFrame:
    """每格取 filed_date <= when 的最後一列(時點正確)。"""
    left = cells[[key, when]].copy()
    left[when] = pd.to_datetime(left[when]).astype("datetime64[us]")
    left["_i"] = np.arange(len(left))
    left = left[left[key].notna()].sort_values(when)
    right = p3.rename(columns={"entity_id": key})
    m = pd.merge_asof(left, right, left_on=when, right_on="filed_date",
                      by=key, direction="backward")
    m = m.set_index("_i")
    cols = ["cash_and_equivalents", "lt_debt", "st_debt", "total_debt_orig",
            "total_debt_filled", "debt_fill_tag", "shares_outstanding",
            "currency", "filed_date", "period_end"]
    out = pd.DataFrame(index=np.arange(len(cells)), columns=cols, dtype=object)
    out.loc[m.index, cols] = m[cols].values
    for c in ["cash_and_equivalents", "lt_debt", "st_debt", "total_debt_orig",
              "total_debt_filled", "shares_outstanding"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out.add_prefix("v3_")


# --------------------------------------------------------------------------
# 舊格(判準第三節①)
# --------------------------------------------------------------------------
def old_cells() -> tuple[pd.DataFrame, pd.DataFrame]:
    wm = pd.read_parquet(SCAN / "out" / "window_multiples.parquet")
    wm = wm[wm.horizon == "5y"][["ticker", "t0", "multiple"]].copy()
    wm["is10x"] = (wm.multiple >= 10).astype(int)
    wm["year"] = wm.t0.dt.year

    pan = pd.read_parquet(P_PANEL_V2, columns=[
        "ticker", "cik", "month_end", "diluted_shares", "cash", "lt_debt", "in_index"])
    pan = pan.sort_values(["ticker", "month_end"]).reset_index(drop=True)
    pan["sf"] = f160.split_factor(pan)
    pan["shares_adj"] = pan["diluted_shares"] * pan["sf"]
    pan.loc[pan.ticker.isin(CONTAMINATED), "shares_adj"] = np.nan

    ex = pd.read_parquet(P_EXTRA)[["ticker", "month_end", "st_debt"]]
    pan = pan.merge(ex, on=["ticker", "month_end"], how="left")

    px = pd.read_parquet(P_EXIST).join(pd.read_parquet(P_NEW), how="outer").sort_index()
    pxs = px.stack(future_stack=True).rename("close").reset_index()
    pxs.columns = ["date", "ticker", "close"]
    pan = pan.merge(pxs.rename(columns={"date": "month_end"}),
                    on=["ticker", "month_end"], how="left")
    pan["mcap"] = pan["close"] * pan["shares_adj"]

    c = wm.merge(pan, left_on=["ticker", "t0"], right_on=["ticker", "month_end"],
                 how="inner")
    orig, filled, tag = fill_total_debt(c["lt_debt"], c["st_debt"])
    c["total_debt_orig"] = orig
    c["total_debt_filled"] = filled
    c["debt_fill_tag"] = tag
    c["key"] = c["ticker"]
    c["entity_id"] = c["cik"]
    return c, px
