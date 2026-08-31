"""KARST-135 判讀:平原/孤峰、對照臂逐格答案、最強格、分段穩定性。

輸出 plateau.csv、best_cells.csv 與文字摘要 analysis_out.txt。
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

pd.set_option("display.width", 200)
HERE = pathlib.Path(__file__).resolve().parent
pan = pd.read_csv(HERE / "panorama.csv")
con = pd.read_csv(HERE / "contrast.csv")
corr = pd.read_csv(HERE / "rsi_corr.csv")
vc = pd.read_csv(HERE / "vbt_check.csv")

BARS = ["1D", "3D", "1W", "1M", "3M"]
base = pan[pan["style"] == "基線"].set_index(["bar", "params"])["cagr_pct"]
cells = pan[pan["style"] != "基線"].copy()
w = cells[cells["rsi_kind"] == "wilder"].copy()

print("=== 0. vectorBT 對照(D-095 指定工具,甲式全部格)===")
print(f"格數 {len(vc)},手寫引擎與 vectorBT 年化差:最大 {vc['abs_diff'].max():.4f} "
      f"百分點,中位 {vc['abs_diff'].median():.4f}")

print("\n=== 1. 基線(統一評分期 2000-10 .. 2026-08,25.8 年)===")
print(base.unstack().round(3).reindex(BARS).to_string())

print("\n=== 2. 對照臂:重合率與成績差(mult 對 price)===")
c0 = con[con["pair"] == "mult|price"]
g = c0.groupby(["bar", "style"]).agg(
    n_cells=("agreement", "size"), agree_med=("agreement", "median"),
    jaccard_med=("jaccard", "median"), diff_spy_med=("diff_exc_spy", "median"),
    diff_spy_p10=("diff_exc_spy", lambda s: s.quantile(0.10)),
    diff_spy_p90=("diff_exc_spy", lambda s: s.quantile(0.90)),
    pct_mult_wins=("diff_exc_spy", lambda s: round(float((s > 0).mean()) * 100, 1)),
).round(4).reindex(pd.MultiIndex.from_product([BARS, ["甲", "乙"]]))
print(g.to_string())

print("\n=== 3. 兩臂 RSI2 讀數相關(九隻板塊中位數)===")
print(corr.groupby(["bar", "rsi_kind", "pair"])[["pearson", "spearman", "mean_abs_diff"]]
      .median().round(4).to_string())

print("\n=== 4. 每(臂 × bar × 訊號式)最強格(wilder 主口徑,對 SPY 超額)===")
best = w.loc[w.groupby(["arm", "bar", "style"])["exc_spy"].idxmax()].copy()
best["bar"] = pd.Categorical(best["bar"], BARS, ordered=True)
cols = ["arm", "bar", "style", "params", "cagr_pct", "exc_spy", "t_spy", "exc_ew9",
        "t_ew9", "exc_spy_h1", "exc_spy_h2", "ann_turnover", "pct_in_mkt", "n_rebal"]
best = best.sort_values(["bar", "style", "arm"])
best[cols].to_csv(HERE / "best_cells.csv", index=False, encoding="utf-8-sig")
print(best[cols].to_string(index=False))

# ---------------- 平原 / 孤峰 ----------------
AX = {"甲": ["N", "H"], "乙": ["E", "X", "H"]}
LEV = {"N": [1, 2, 3], "E": [5, 10, 15, 20, 25, 30, 35, 40],
       "X": [50, 55, 60, 65, 70, 75, 80, 85, 90, 95]}
HOLDS = {"1D": [1, 2, 3, 5, 10], "3D": [1, 2, 3], "1W": [1, 2, 3, 4],
         "1M": [1, 2, 3], "3M": [1, 2]}

rows = []
for (arm, bar, kind, style), grp in cells.groupby(["arm", "bar", "rsi_kind", "style"]):
    axes = AX[style]
    lev = {a: (HOLDS[bar] if a == "H" else LEV[a]) for a in axes}
    idx = {a: {v: i for i, v in enumerate(lev[a])} for a in axes}
    key = grp.set_index(axes)["exc_spy"]
    top = grp.loc[grp["exc_spy"].idxmax()]
    pos = tuple(top[a] for a in axes)
    nb_vals = []
    for a in axes:
        i = idx[a][top[a]]
        for step in (-1, 1):
            j = i + step
            if 0 <= j < len(lev[a]):
                q = list(pos)
                q[axes.index(a)] = lev[a][j]
                if tuple(q) in key.index:
                    nb_vals.append(float(key.loc[tuple(q)]))
    rows.append(dict(
        arm=arm, bar=bar, rsi_kind=kind, style=style,
        best_params=top["params"], best_exc_spy=round(float(top["exc_spy"]), 3),
        best_t_spy=float(top["t_spy"]),
        nb_min=round(float(np.min(nb_vals)), 3) if nb_vals else np.nan,
        nb_med=round(float(np.median(nb_vals)), 3) if nb_vals else np.nan,
        drop_med=round(float(top["exc_spy"] - np.median(nb_vals)), 3) if nb_vals else np.nan,
        family_med_exc=round(float(grp["exc_spy"].median()), 3),
        family_p10_exc=round(float(grp["exc_spy"].quantile(0.10)), 3),
        pct_positive=round(float((grp["exc_spy"] > 0).mean()) * 100, 1),
        pct_t_gt2=round(float((grp["t_spy"] > 2).mean()) * 100, 1),
        pct_pos_h1=round(float((grp["exc_spy_h1"] > 0).mean()) * 100, 1),
        pct_pos_h2=round(float((grp["exc_spy_h2"] > 0).mean()) * 100, 1),
        med_h1=round(float(grp["exc_spy_h1"].median()), 3),
        med_h2=round(float(grp["exc_spy_h2"].median()), 3),
        n_cells=len(grp)))
pl = pd.DataFrame(rows)
pl["bar"] = pd.Categorical(pl["bar"], BARS, ordered=True)
pl = pl.sort_values(["style", "bar", "arm", "rsi_kind"])
pl.to_csv(HERE / "plateau.csv", index=False, encoding="utf-8-sig")

print("\n=== 5. 平原/孤峰:最強格 vs ±1 鄰域 + 全族分佈(wilder 主口徑)===")
print(pl[pl["rsi_kind"] == "wilder"].drop(columns=["rsi_kind"]).to_string(index=False))

print("\n=== 6. 口徑穩健性:simple RSI 口徑下同一張表 ===")
print(pl[pl["rsi_kind"] == "simple"][
    ["arm", "bar", "style", "best_params", "best_exc_spy", "best_t_spy",
     "family_med_exc", "pct_positive"]].to_string(index=False))

print("\n=== 7. 分段穩定性:前半(2000-10~2013)vs 後半(2013~2026),對 SPY 超額中位數 ===")
sp = w.groupby(["arm", "bar", "style"])[["exc_spy", "exc_spy_h1", "exc_spy_h2"]].median().round(3)
sp = sp.reset_index()
sp["bar"] = pd.Categorical(sp["bar"], BARS, ordered=True)
print(sp.sort_values(["bar", "style", "arm"]).to_string(index=False))

print("\n=== 8. 事前判讀規則套用:mult 最強 20 格,對照臂同格 ===")
mw = w[w["arm"] == "mult"]
key = c0.set_index(["bar", "rsi_kind", "style", "params"])
out = []
for _, r in mw.nlargest(20, "exc_spy").iterrows():
    c = key.loc[(r["bar"], r["rsi_kind"], r["style"], r["params"])]
    if c["agreement"] > 0.8 and c["b_exc_spy"] > 0:
        v = "贏的是價格"
    elif c["agreement"] > 0.8:
        v = "兩臂皆無"
    else:
        v = "倍數獨有(待驗)"
    out.append(dict(bar=r["bar"], style=r["style"], params=r["params"],
                    mult_exc=round(r["exc_spy"], 3), price_exc=round(c["b_exc_spy"], 3),
                    diff=round(c["diff_exc_spy"], 3), t_mult=r["t_spy"],
                    agree=c["agreement"], jaccard=c["jaccard"], verdict=v))
print(pd.DataFrame(out).to_string(index=False))

print("\n=== 9. 口徑陷阱檢查:mult_raw(月底 pe_lag 正本)對 mult(票面砌法)===")
c2 = con[con["pair"] == "mult_raw|mult"]
print(c2.groupby(["bar", "style"]).agg(
    n=("agreement", "size"), agree_med=("agreement", "median"),
    jaccard_med=("jaccard", "median"),
    raw_exc_med=("a_exc_spy", "median"), mult_exc_med=("b_exc_spy", "median"),
    diff_med=("diff_exc_spy", "median")).round(3).to_string())
c3 = con[con["pair"] == "mult_raw|price"]
print("\nmult_raw 對 price:")
print(c3.groupby(["bar", "style"]).agg(
    n=("agreement", "size"), agree_med=("agreement", "median"),
    raw_exc_med=("a_exc_spy", "median"), price_exc_med=("b_exc_spy", "median"),
    diff_med=("diff_exc_spy", "median"),
    pct_raw_wins=("diff_exc_spy", lambda s: round(float((s > 0).mean()) * 100, 1))
).round(3).to_string())

print("\n=== 10. 1M / 3M 三臂並排(wilder,全族分佈)===")
sub = w[w["bar"].isin(["1M", "3M"])]
print(sub.groupby(["bar", "style", "arm"])["exc_spy"].describe(
    percentiles=[0.1, 0.5, 0.9]).round(3)[["count", "10%", "50%", "90%", "max"]].to_string())

print("\n=== 11. 年換手與成本拖累(中位數)===")
tt = w.groupby(["bar", "style"])["ann_turnover"].median().round(2)
tab = pd.DataFrame({"年換手": tt, "年成本拖累_百分點": (tt * 10 / 10000 * 100).round(3)})
tab = tab.reset_index()
tab["bar"] = pd.Categorical(tab["bar"], BARS, ordered=True)
print(tab.sort_values(["bar", "style"]).to_string(index=False))
