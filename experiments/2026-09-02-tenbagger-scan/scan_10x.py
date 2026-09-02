# -*- coding: utf-8 -*-
"""KARST-160 第一步:倉內 728 家滾動三年/五年窗十倍股盤點。
照 RULES.md 第二至四節。只讀既有原料,產物落 out/。"""
import json
import os
import sys

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

ROOT = r"C:\projects\Karst"
OUT = os.path.join(ROOT, "experiments", "2026-09-02-tenbagger-scan", "out")
os.makedirs(OUT, exist_ok=True)

P_EXIST = os.path.join(ROOT, "experiments", "2026-09-02-timing-sweep", "data", "daily_close.parquet")
P_NEW = os.path.join(ROOT, "experiments", "2026-09-02-narrative-layers-v2", "data", "new_close.parquet")
P_UNIV = os.path.join(ROOT, "experiments", "2026-09-02-narrative-layers-v2", "out", "universe_v2.json")
P_CHAIN = os.path.join(ROOT, "experiments", "2026-09-02-chain-layers", "chain_membership_v0.csv")

DROP_NON_EQUITY = {"ARKB", "CTA", "KAP", "PXD"}
THRESHOLDS = [2.0, 3.0, 5.0, 10.0]
HORIZONS = {3: "3y", 5: "5y"}


def load_prices():
    a = pd.read_parquet(P_EXIST)
    b = pd.read_parquet(P_NEW)
    px = a.join(b, how="outer")
    px = px.sort_index()
    uni = json.load(open(P_UNIV, encoding="utf-8"))
    stocks = [t for t in uni["universe_stocks"] if t not in DROP_NON_EQUITY]
    keep = [t for t in stocks if t in px.columns]
    missing = sorted(set(stocks) - set(keep))
    return px[keep], keep, missing


def month_end_grid(index):
    """每個月最後一個有價交易日。"""
    s = pd.Series(index, index=index)
    g = s.groupby([index.year, index.month]).max()
    return pd.DatetimeIndex(sorted(g.values))


def main():
    px, tickers, missing = load_prices()
    idx = px.index
    last_date = idx.max()
    grid = month_end_grid(idx)
    grid = grid[(grid >= pd.Timestamp("2009-01-01"))]

    # 每個 t0 對應的窗末 index 位置(完整窗才算)
    pos = {d: i for i, d in enumerate(idx)}
    arr = px.to_numpy(dtype=float)
    cols = list(px.columns)

    rows = []          # 逐 (ticker, t0, horizon) 的倍數
    for h, hname in HORIZONS.items():
        for t0 in grid:
            end = t0 + relativedelta(years=h)
            if end > last_date:
                continue
            i0 = pos[t0]
            i1 = idx.searchsorted(end, side="right") - 1
            if i1 <= i0:
                continue
            p0 = arr[i0]
            seg = arr[i0:i1 + 1]
            with np.errstate(invalid="ignore", divide="ignore"):
                pk = np.nanmax(seg, axis=0)
                mult = pk / p0
            valid = np.isfinite(p0) & (p0 > 0) & np.isfinite(mult)
            # 峰頂位置
            for j in np.where(valid)[0]:
                rows.append((cols[j], hname, t0, float(mult[j]), i0, i1))

    df = pd.DataFrame(rows, columns=["ticker", "horizon", "t0", "multiple", "i0", "i1"])
    df.to_parquet(os.path.join(OUT, "window_multiples.parquet"), index=False)
    print("窗格數", len(df))

    # ---- 分年基礎率 ----
    df["year"] = df["t0"].dt.year
    base_rows = []
    for hname in HORIZONS.values():
        d = df[df.horizon == hname]
        for y, g in d.groupby("year"):
            per = g.groupby("ticker")["multiple"].max()
            n = len(per)
            rec = {"horizon": hname, "start_year": int(y), "n_names": n,
                   "median_peak_multiple": round(float(per.median()), 3)}
            for th in THRESHOLDS:
                k = int((per >= th).sum())
                rec[f"n_ge_{int(th)}x"] = k
                rec[f"share_ge_{int(th)}x"] = round(k / n, 4) if n else None
            base_rows.append(rec)
    base = pd.DataFrame(base_rows).sort_values(["horizon", "start_year"])
    base.to_csv(os.path.join(OUT, "base_rate_by_year.csv"), index=False, encoding="utf-8-sig")

    # ---- 全期十倍股名單(取最佳窗格) ----
    chain = pd.read_csv(P_CHAIN, encoding="utf-8-sig", engine="python", on_bad_lines="skip")
    chain_map = chain.groupby("ticker")["theme"].apply(lambda s: "|".join(sorted(set(s)))).to_dict()

    names = []
    for hname in HORIZONS.values():
        d = df[df.horizon == hname]
        best = d.loc[d.groupby("ticker")["multiple"].idxmax()]
        best = best[best.multiple >= 10.0]
        for _, r in best.iterrows():
            j = cols.index(r.ticker)
            seg = arr[int(r.i0):int(r.i1) + 1, j]
            k = int(np.nanargmax(seg))
            peak_i = int(r.i0) + k
            peak_date = idx[peak_i]
            peak_px = float(arr[peak_i, j])
            after = arr[peak_i:, j]
            after = after[np.isfinite(after)]
            trough = float(np.nanmin(after)) if len(after) else np.nan
            today = float(pd.Series(arr[:, j]).ffill().iloc[-1])
            names.append({
                "horizon": hname,
                "ticker": r.ticker,
                "t0": r.t0.date().isoformat(),
                "t0_price": round(float(arr[int(r.i0), j]), 4),
                "peak_date": peak_date.date().isoformat(),
                "peak_price": round(peak_px, 4),
                "multiple": round(float(r.multiple), 2),
                "maxdd_after_peak": round(trough / peak_px - 1, 4),
                "today_vs_peak": round(today / peak_px - 1, 4),
                "chain_theme": chain_map.get(r.ticker, ""),
            })
    nm = pd.DataFrame(names).sort_values(["horizon", "multiple"], ascending=[True, False])
    nm.to_csv(os.path.join(OUT, "tenbagger_names.csv"), index=False, encoding="utf-8-sig")

    # ---- 全期匯總 ----
    summary = {
        "universe_requested": len(tickers) + len(missing),
        "universe_priced": len(tickers),
        "universe_missing_price": missing,
        "price_last_date": last_date.date().isoformat(),
        "grid_months": int(len(grid)),
    }
    for hname in HORIZONS.values():
        d = df[df.horizon == hname]
        per = d.groupby("ticker")["multiple"].max()
        summary[hname] = {
            "n_names_measurable": int(len(per)),
            "n_ge_10x": int((per >= 10).sum()),
            "share_ge_10x_anywindow": round(float((per >= 10).mean()), 4),
            "n_ge_5x": int((per >= 5).sum()),
            "share_ge_5x_anywindow": round(float((per >= 5).mean()), 4),
            "median_best_multiple": round(float(per.median()), 3),
            "start_year_min": int(d.year.min()),
            "start_year_max": int(d.year.max()),
        }
    json.dump(summary, open(os.path.join(OUT, "scan_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1)[:1500])
    print("十倍股名單行數", len(nm))


if __name__ == "__main__":
    main()
