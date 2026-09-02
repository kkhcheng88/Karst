# -*- coding: utf-8 -*-
"""KARST-166 第三步:穩健性核對(不改判準,只核 CRITERIA 第三節的缺值處理有沒有造出結論)。

三項:
 1. `st_debt` 缺值當 0 這條規則,對 S1 的 AUC 有幾大影響(只留 st_debt 有數的格重算);
 2. 商譽/無形資產缺值當 0 這條規則,對 S3 的影響(只留兩欄都有數的格重算);
 3. 三個門檻互相剔走的是不是同一批格(重疊表)。
輸出 out/robustness.csv、out/threshold_overlap.csv
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(r"C:\projects\Karst")
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(ROOT / "experiments" / "2026-09-02-tenbagger-scan"))
import features_t0 as f160  # noqa: E402

import safety_features as sf  # noqa: E402


def main() -> None:
    c = pd.read_parquet(OUT / "safety_cells.parquet")
    rows = []

    def add(name, sub, col):
        a_all, a_yr, n1, n0, _ = sf.auc_pair(sub, col)
        rows.append(dict(check=name, feature=col, n_cells=int(n1 + n0), n_10x=int(n1),
                         AUC_full=round(a_all, 4) if a_all == a_all else None,
                         AUC_year_weighted=round(a_yr, 4) if a_yr == a_yr else None))

    add("主口徑(缺值當 0)", c, "s1_net_cash_to_mcap")
    add("只留 st_debt 有數的格", c[c.st_debt.notna()], "s1_net_cash_to_mcap")
    add("主口徑(缺值當 0)", c, "s3_tangible_nav_to_mcap")
    add("只留商譽與無形都有數的格",
        c[c.goodwill.notna() & c.intangibles.notna()], "s3_tangible_nav_to_mcap")
    add("主口徑", c, "s2_runway_yrs")
    add("只留有燒錢的格(跑道非無限)", c[~c.s2_infinite.astype(bool)], "s2_runway_yrs")
    pd.DataFrame(rows).to_csv(OUT / "robustness.csv", index=False, encoding="utf-8-sig")

    # 三個門檻剔走的是不是同一批格
    ov = []
    for a in ["T1", "T2", "T3"]:
        for b in ["T1", "T2", "T3"]:
            m = c[a].notna() & c[b].notna()
            cut_a, cut_b = m & (c[a] == 0), m & (c[b] == 0)
            ov.append(dict(a=a, b=b, n_both_computable=int(m.sum()),
                           cut_a=int(cut_a.sum()), cut_b=int(cut_b.sum()),
                           cut_both=int((cut_a & cut_b).sum()),
                           jaccard=round(float((cut_a & cut_b).sum()
                                               / max(1, (cut_a | cut_b).sum())), 4)))
    pd.DataFrame(ov).to_csv(OUT / "threshold_overlap.csv", index=False,
                            encoding="utf-8-sig")

    # 「不欠債」與「不燒錢」拆開看:2×2 十倍率
    c["burning"] = np.where(c.s2_infinite.astype(bool), "不燒錢(自由現金流≥0)", "燒錢")
    c.loc[c.s2_runway_yrs.isna(), "burning"] = None
    c["netcash"] = np.where(c.T1 == 1, "淨現金為正", "淨負債")
    c.loc[c.T1.isna(), "netcash"] = None
    sub = c[c.burning.notna() & c.netcash.notna()]
    cross = sub.groupby(["netcash", "burning"]).agg(
        n_cells=("is10x", "size"), n_10x=("is10x", "sum")).reset_index()
    cross["ten_x_rate"] = (cross.n_10x / cross.n_cells).round(4)
    # 格數會被同一家公司連續幾十個月重數,所以同時報公司數(真正的有效樣本)
    comp = sub.groupby(["netcash", "burning"]).agg(
        n_tickers=("ticker", "nunique")).reset_index()
    hit = sub[sub.is10x == 1].groupby(["netcash", "burning"]).agg(
        n_tickers_10x=("ticker", "nunique")).reset_index()
    cross = cross.merge(comp, on=["netcash", "burning"], how="left") \
                 .merge(hit, on=["netcash", "burning"], how="left")
    cross["ten_x_ticker_rate"] = (cross.n_tickers_10x / cross.n_tickers).round(4)
    cross.to_csv(OUT / "cross_netcash_burn.csv", index=False, encoding="utf-8-sig")
    names = sub[sub.is10x == 1].groupby(["netcash", "burning"])["ticker"] \
        .apply(lambda s: "|".join(sorted(set(s)))).reset_index()
    names.to_csv(OUT / "cross_netcash_burn_names.csv", index=False,
                 encoding="utf-8-sig")

    print(pd.DataFrame(rows).to_string(index=False))
    print()
    print(pd.DataFrame(ov).to_string(index=False))
    print()
    print(cross.to_string(index=False))


if __name__ == "__main__":
    main()
