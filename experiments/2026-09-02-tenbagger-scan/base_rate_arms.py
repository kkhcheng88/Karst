# -*- coding: utf-8 -*-
"""KARST-160 第一步之二:基礎率的三條臂,回答「這個數字有多依賴後見之明的入場時機」。
臂 A:年內任何一個月底入場(滾動窗最大值,scan_10x.py 的口徑)
臂 B:只准每年一月底入場(無年內擇時,可與 D-120 口徑對照)
臂 C:臂 A 再剔走三個已知代號重用污染者與起點調整價 < 0.50 美元者
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

CONTAMINATED = {"CPWR", "EP", "PARA"}   # RULES v2 第九節:拆股表 / 代號重用污染
LOW_PX = 0.50
THS = [2.0, 3.0, 5.0, 10.0]


def main():
    df = pd.read_parquet(os.path.join(OUT, "window_multiples.parquet"))
    df["year"] = df["t0"].dt.year
    px = pd.read_parquet(P_EXIST).join(pd.read_parquet(P_NEW), how="outer").sort_index()

    # 補回 t0 價
    t0px = {}
    for t, sub in df.groupby("ticker"):
        s = px[t]
        t0px[t] = s.reindex(sub["t0"].unique())
    df["t0_price"] = [px.at[r.t0, r.ticker] for r in df.itertuples()]

    # 每年第一個 t0(一月底)
    first_t0 = df.groupby(["horizon", "year"])["t0"].transform("min")
    df["is_jan"] = df["t0"] == first_t0

    arms = {}
    for arm, d in [
        ("A_best_month_in_year", df),
        ("B_january_only", df[df.is_jan]),
        ("C_best_month_clean", df[(~df.ticker.isin(CONTAMINATED)) & (df.t0_price >= LOW_PX)]),
    ]:
        rows = []
        for (h, y), g in d.groupby(["horizon", "year"]):
            per = g.groupby("ticker")["multiple"].max()
            n = len(per)
            rec = {"arm": arm, "horizon": h, "start_year": int(y), "n_names": n,
                   "median_peak_multiple": round(float(per.median()), 3)}
            for th in THS:
                k = int((per >= th).sum())
                rec[f"n_ge_{int(th)}x"] = k
                rec[f"share_ge_{int(th)}x"] = round(k / n, 4) if n else None
            rows.append(rec)
        arms[arm] = pd.DataFrame(rows)

    allarms = pd.concat(arms.values()).sort_values(["arm", "horizon", "start_year"])
    allarms.to_csv(os.path.join(OUT, "base_rate_arms.csv"), index=False, encoding="utf-8-sig")

    # 全期匯總
    summ = {}
    for arm, d in [
        ("A_best_month_in_year", df),
        ("B_january_only", df[df.is_jan]),
        ("C_best_month_clean", df[(~df.ticker.isin(CONTAMINATED)) & (df.t0_price >= LOW_PX)]),
    ]:
        summ[arm] = {}
        for h in ["3y", "5y"]:
            per = d[d.horizon == h].groupby("ticker")["multiple"].max()
            a = arms[arm]
            a = a[a.horizon == h]
            summ[arm][h] = {
                "n_names": int(len(per)),
                "n_ge_10x_any_start_year": int((per >= 10).sum()),
                "share_ge_10x_any_start_year": round(float((per >= 10).mean()), 4),
                "annual_base_rate_median": round(float(a["share_ge_10x"].median()), 4),
                "annual_base_rate_mean": round(float(a["share_ge_10x"].mean()), 4),
                "annual_base_rate_min": round(float(a["share_ge_10x"].min()), 4),
                "annual_base_rate_max": round(float(a["share_ge_10x"].max()), 4),
            }
    json.dump(summ, open(os.path.join(OUT, "base_rate_arms_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))

    # 低價 / 污染的十倍股逐個列出,方便報告點名
    flag = df[(df.multiple >= 10) & ((df.t0_price < LOW_PX) | (df.ticker.isin(CONTAMINATED)))]
    fl = flag.groupby(["horizon", "ticker"]).agg(
        max_multiple=("multiple", "max"), min_t0_price=("t0_price", "min")).reset_index()
    fl.to_csv(os.path.join(OUT, "flagged_lowprice_names.csv"), index=False, encoding="utf-8-sig")
    print("被旗標的十倍股(低起點價或代號重用)", fl.ticker.nunique())


if __name__ == "__main__":
    main()
