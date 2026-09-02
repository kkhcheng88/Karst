# -*- coding: utf-8 -*-
"""KARST-160:反例逐家、十倍股逐家的規則命中明細,供報告點名。"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = r"C:\projects\Karst\experiments\2026-09-02-tenbagger-scan"
OUT = os.path.join(BASE, "out")
sys.path.insert(0, BASE)
from meme_filter import apply_rules, RULES  # noqa: E402

BEST = ["R2_無營業額而市值高", "R4_已經跑掉"]


def main():
    Cc = pd.read_parquet(os.path.join(OUT, "filter_cells_counterexamples.parquet"))
    RC = apply_rules(Cc)
    rows = []
    for t, g in Cc[Cc.is_mania].groupby("ticker"):
        r = {"ticker": t, "狂熱期月數": len(g),
             "峰前12個月最高價": round(float(g.close.max()), 2)}
        for k in RULES:
            v = RC.loc[g.index, k].dropna().astype(float)
            r[k] = round(float(v.mean()), 2) if len(v) else None
        both = RC.loc[g.index, BEST].astype(float)
        m = both.max(axis=1).where(both.notna().all(axis=1)).dropna()
        r["R2+R4"] = round(float(m.mean()), 2) if len(m) else None
        rows.append(r)
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(OUT, "counterexample_by_name.csv"), index=False, encoding="utf-8-sig")
    print(d.to_string(index=False))

    # 十倍股在最佳 t0 的命中
    U = pd.read_parquet(os.path.join(OUT, "filter_cells_universe.parquet"))
    RU = apply_rules(U)
    tx = U[U.multiple >= 10]
    best = tx.loc[tx.groupby("ticker")["multiple"].idxmax()]
    b = RU.loc[best.index, list(RULES)].astype(float)
    b.insert(0, "ticker", best["ticker"].values)
    b.insert(1, "t0", best["month_end"].dt.date.values)
    b.insert(2, "multiple", best["multiple"].round(1).values)
    both = RU.loc[best.index, BEST].astype(float)
    b["R2+R4"] = both.max(axis=1).where(both.notna().all(axis=1)).values
    b.to_csv(os.path.join(OUT, "tenbagger_rule_hits.csv"), index=False, encoding="utf-8-sig")
    print()
    print("十倍股 R2+R4 誤殺:", int(np.nansum(b["R2+R4"])), "/",
          int(b["R2+R4"].notna().sum()), "家有齊欄位(共", len(b), "家)")
    killed = b[b["R2+R4"] == 1]
    print("被誤殺的:", ", ".join(f"{r.ticker}({r.multiple:.0f}x)" for r in killed.itertuples()))

    m = json.load(open(os.path.join(OUT, "meme_filter_meta.json"), encoding="utf-8"))
    print()
    print("反例峰月:", m["counterexample_peak_month"])


if __name__ == "__main__":
    main()
