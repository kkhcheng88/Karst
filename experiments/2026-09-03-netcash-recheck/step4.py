# -*- coding: utf-8 -*-
"""KARST-176 第④步:全換——小型股名單 v1 + 面板 v3 + 新價格庫,重建格級 AUC。

格的定義照 KARST-160 RULES 第二節重建(判準第三節④)。
輸出 out/:
  cells_new.parquet   新格連 S1
  step4.csv           四數表
  step4_by_year.csv   逐年 AUC 明細
  step4_build.json    建格與覆蓋的過程數字
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import common176 as K

Y_FIRST, Y_LAST = 2009, 2021          # 完整五年窗:t0 + 5 曆年 <= 2026-09-01
PANEL_LAST = pd.Timestamp("2026-09-01")
TOL_DAYS = 30                         # 窗尾資料容差


def load_prices(ids: set[str]) -> pd.DataFrame:
    frames = []
    for p in sorted(K.PRICE_DIR.glob("part_*.parquet")):
        df = pd.read_parquet(p, columns=["entity_id", "ticker", "date", "close",
                                         "adj_close", "series_role"])
        df = df[df["entity_id"].isin(ids) & (df["series_role"] == "primary")]
        if len(df):
            df["date"] = pd.to_datetime(df["date"])
            frames.append(df[["entity_id", "ticker", "date", "close", "adj_close"]])
    px = pd.concat(frames, ignore_index=True)
    px = px[px["date"] >= pd.Timestamp("2008-12-01")]
    px = px.sort_values(["entity_id", "date"]).drop_duplicates(["entity_id", "date"])
    return px.reset_index(drop=True)


def build_cells(px: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    recs = []
    stat = dict(entities_with_price=0, month_ends_seen=0,
                skipped_no_window=0, skipped_truncated=0, skipped_bad_price=0)
    for eid, g in px.groupby("entity_id", sort=False):
        stat["entities_with_price"] += 1
        d = g["date"].to_numpy()
        a = g["adj_close"].to_numpy(dtype=float)
        cl = g["close"].to_numpy(dtype=float)
        tks = g["ticker"].to_numpy()
        ym = (g["date"].dt.year * 100 + g["date"].dt.month).to_numpy()
        # 每月最後一個有價交易日
        last_idx = np.flatnonzero(np.r_[ym[1:] != ym[:-1], True])
        for i in last_idx:
            y = int(ym[i] // 100)
            if y < Y_FIRST or y > Y_LAST:
                continue
            stat["month_ends_seen"] += 1
            if not np.isfinite(a[i]) or a[i] <= 0:
                stat["skipped_bad_price"] += 1
                continue
            t0 = pd.Timestamp(d[i])
            end = t0 + pd.DateOffset(years=5)
            if end > PANEL_LAST:
                stat["skipped_no_window"] += 1
                continue
            j = int(np.searchsorted(d, np.datetime64(end), side="right"))
            if j - i < 2:
                stat["skipped_no_window"] += 1
                continue
            if pd.Timestamp(d[j - 1]) < end - pd.Timedelta(days=TOL_DAYS):
                stat["skipped_truncated"] += 1
                continue
            w = a[i + 1:j]
            w = w[np.isfinite(w)]
            if not len(w):
                stat["skipped_bad_price"] += 1
                continue
            recs.append((eid, tks[i], t0, y, float(w.max() / a[i]),
                         float(cl[i]) if np.isfinite(cl[i]) else np.nan))
    c = pd.DataFrame(recs, columns=["entity_id", "ticker", "t0", "year",
                                    "multiple", "close"])
    c["is10x"] = (c["multiple"] >= 10).astype(int)
    c["key"] = c["entity_id"]
    return c, stat


def split_factor_after(c: pd.DataFrame) -> np.ndarray:
    sp = pd.read_parquet(K.SPLITS)
    sp["report_date"] = pd.to_datetime(sp["report_date"], errors="coerce")
    fac = np.ones(len(c))
    tk = c["ticker"].to_numpy()
    t0v = c["t0"].to_numpy()
    for sym, g in sp.groupby("symbol"):
        if sym in K.CONTAMINATED:
            continue
        m = tk == sym
        if not m.any():
            continue
        f = np.ones(int(m.sum()))
        for d, r in zip(g["report_date"].to_numpy(), g["ratio"].to_numpy()):
            f *= np.where(t0v[m] < d, r, 1.0)
        fac[m] = f
    return fac


def main() -> None:
    v1 = pd.read_csv(K.UNIVERSE / "universe_smallcap_v1.csv", dtype={"entity_id": str})
    ids = set(v1["entity_id"].str.zfill(10))
    print(f"小型股名單 v1:{len(ids)} 家")

    px = load_prices(ids)
    print(f"價格列 {len(px):,},實體 {px.entity_id.nunique()}")

    c, stat = build_cells(px)
    del px
    print(f"新格 {len(c):,}、十倍格 {int(c.is10x.sum())}、實體 {c.entity_id.nunique()}")

    p3 = K.panel_v3()
    v3 = K.asof_v3(c, p3, when="t0", key="entity_id")
    c = pd.concat([c.reset_index(drop=True), v3], axis=1)

    fac = split_factor_after(c)
    c["split_factor"] = fac
    sp_syms = set(pd.read_parquet(K.SPLITS)["symbol"].unique())
    c["split_table_absent"] = ~c["ticker"].isin(sp_syms)
    c["mcap"] = c["close"] * c["v3_shares_outstanding"] * fac
    c.loc[c.ticker.isin(K.CONTAMINATED), "mcap"] = np.nan

    usd = c["v3_currency"].eq("USD")
    c["s1_step4_pre"] = np.where(
        usd, (c["v3_cash_and_equivalents"] - c["v3_total_debt_orig"]) / c["mcap"], np.nan)
    c["s1_step4"] = np.where(
        usd, (c["v3_cash_and_equivalents"] - c["v3_total_debt_filled"]) / c["mcap"], np.nan)
    c["s1_step4_nocur"] = (c["v3_cash_and_equivalents"] - c["v3_total_debt_filled"]) / c["mcap"]

    r4_pre, y4_pre = K.four_numbers(c, "s1_step4_pre", "④全換(補前)")
    r4, y4 = K.four_numbers(c, "s1_step4", "④全換(補後)")
    r4n, _ = K.four_numbers(c, "s1_step4_nocur", "④附A 不設美元限制(對照)")

    tab = pd.DataFrame([r4_pre, r4, r4n])
    tab.to_csv(K.OUT / "step4.csv", index=False, encoding="utf-8-sig")
    yr = []
    for name, per in [("④補前", y4_pre), ("④補後", y4)]:
        for yy, a, n, k1 in per:
            yr.append(dict(step=name, year=yy, AUC=round(a, 4), n_cells=n, n_10x=k1))
    pd.DataFrame(yr).to_csv(K.OUT / "step4_by_year.csv", index=False,
                            encoding="utf-8-sig")

    stat.update({
        "格數": int(len(c)), "十倍格": int(c.is10x.sum()),
        "涉及實體": int(c.entity_id.nunique()),
        "有市值的格": int(c["mcap"].notna().sum()),
        "有股數的格": int(c["v3_shares_outstanding"].notna().sum()),
        "有現金的格": int(c["v3_cash_and_equivalents"].notna().sum()),
        "有總債務的格(補前)": int(c["v3_total_debt_orig"].notna().sum()),
        "有總債務的格(補後)": int(c["v3_total_debt_filled"].notna().sum()),
        "非美元的格": int((c["v3_currency"].notna() & ~usd).sum()),
        "拆股表不覆蓋的格": int(c["split_table_absent"].sum()),
        "S1可算格(補前)": int(c["s1_step4_pre"].notna().sum()),
        "S1可算格(補後)": int(c["s1_step4"].notna().sum()),
        "S1可算十倍格(補後)": int((c["s1_step4"].notna() & (c.is10x == 1)).sum()),
    })
    (K.OUT / "step4_build.json").write_text(
        json.dumps(stat, ensure_ascii=False, indent=1), encoding="utf-8")

    keep = ["entity_id", "ticker", "t0", "year", "multiple", "is10x", "close",
            "mcap", "split_factor", "split_table_absent",
            "v3_cash_and_equivalents", "v3_total_debt_orig", "v3_total_debt_filled",
            "v3_shares_outstanding", "v3_currency", "s1_step4_pre", "s1_step4"]
    c[keep].to_parquet(K.OUT / "cells_new.parquet", index=False, compression="zstd")

    print(tab[["step", "n_cells", "n_10x", "AUC_full", "AUC_year_weighted",
               "verdict", "netcash_pos_10x", "netcash_pos_all",
               "false_kill_10x"]].to_string(index=False))
    print()
    print(json.dumps(stat, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
