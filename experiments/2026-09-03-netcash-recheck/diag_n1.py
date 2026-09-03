# -*- coding: utf-8 -*-
"""KARST-176 附錄診斷(判準第十一節「增補」):四步全部不跌穿 0.55 之後,
在**同一批第④步的格**上換 KARST-173 的口徑與量度,看關係在哪一步消失。

不改任何判詞、不改四步的門檻。只答一條:KARST-173 量不到關係,是不是它自己的
口徑(N1 = 現金 + 短投 − 負債總額)或者家數口徑造成。

輸出 out/:
  diag_n1.csv    同一批格上,S1(N2 口徑)對 N1 口徑的四數並列
  diag_n1.json   家數口徑與對照組配對方式的對照
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import common176 as K

EXTRA = ["entity_id", "filed_date", "cash_and_equivalents", "short_term_investments",
         "liabilities", "lt_debt", "st_debt", "currency"]


def main() -> None:
    c = pd.read_parquet(K.OUT / "cells_new.parquet")
    p = pd.read_parquet(K.P_PANEL_V3, columns=EXTRA)
    p = p[p["filed_date"].notna()].sort_values(["filed_date", "entity_id"]).reset_index(drop=True)

    left = c[["entity_id", "t0"]].copy()
    left["t0"] = pd.to_datetime(left["t0"]).astype("datetime64[us]")
    left["_i"] = np.arange(len(left))
    left = left.sort_values("t0")
    m = pd.merge_asof(left, p, left_on="t0", right_on="filed_date",
                      by="entity_id", direction="backward").set_index("_i")
    for col in ["cash_and_equivalents", "short_term_investments", "liabilities"]:
        c[f"x_{col}"] = np.nan
        c.loc[m.index, f"x_{col}"] = m[col].to_numpy()

    usd = c["v3_currency"].eq("USD")
    # N1(KARST-173 票面口徑):現金 + 短投 − 負債總額
    n1 = c["x_cash_and_equivalents"] + c["x_short_term_investments"].fillna(0.0) - c["x_liabilities"]
    c["n1_ratio"] = np.where(usd & c["x_liabilities"].notna(), n1 / c["mcap"], np.nan)
    # N2 = 本票四步用的 S1(補後)
    c["n2_ratio"] = c["s1_step4"]

    rows, years = [], []
    for col, label in [("n2_ratio", "④格級 · N2 口徑(現金 − 總債務)= 本票 S1"),
                       ("n1_ratio", "④格級 · N1 口徑(現金 + 短投 − 負債總額)")]:
        r, per = K.four_numbers(c, col, label)
        rows.append(r)
        for yy, a, n, k1 in per:
            years.append(dict(feature=col, year=yy, AUC=round(a, 4), n_cells=n, n_10x=k1))
    tab = pd.DataFrame(rows)
    tab.to_csv(K.OUT / "diag_n1.csv", index=False, encoding="utf-8-sig")

    # ---- 家數口徑:把格塌成公司,看關係還在不在 ---------------------------
    out = {}
    for col, key in [("n2_ratio", "N2"), ("n1_ratio", "N1")]:
        ok = c[col].notna()
        g = c[ok].copy()
        g["pos"] = g[col] > 0
        # 每家取「最早一個可算的 t0」作代表(不揀最好那一格,免得又造一次事後偏差)
        first = g.sort_values(["entity_id", "t0"]).groupby("entity_id", as_index=False).head(1)
        is10 = first.groupby("entity_id")["is10x"].max()
        # 公司層:該公司在整段期間有沒有任何一格通往十倍
        any10 = c.groupby("entity_id")["is10x"].max()
        first = first.set_index("entity_id")
        first["any10x"] = any10.reindex(first.index)
        a = first[first.any10x == 1]["pos"]
        b = first[first.any10x == 0]["pos"]
        out[key] = {
            "十倍公司可算家數": int(len(a)),
            "十倍公司淨現金為正比率": round(float(a.mean()), 4) if len(a) else None,
            "非十倍公司可算家數": int(len(b)),
            "非十倍公司淨現金為正比率": round(float(b.mean()), 4) if len(b) else None,
            "差(百分點)": round(float((a.mean() - b.mean()) * 100), 2) if len(a) and len(b) else None,
        }
    out["備註"] = ("家數口徑取每家最早一個可算的 t0 作代表,分十倍公司與非十倍公司兩組;"
                   "與 KARST-173 不同的是,這裡的十倍公司與對照組來自同一個宇宙、同一批格。")
    (K.OUT / "diag_n1.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    pd.DataFrame(years).to_csv(K.OUT / "diag_n1_by_year.csv", index=False,
                               encoding="utf-8-sig")

    print(tab[["step", "n_cells", "n_10x", "AUC_full", "AUC_year_weighted", "verdict",
               "netcash_pos_10x", "netcash_pos_all", "false_kill_10x"]].to_string(index=False))
    print()
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
