"""KARST-165 唯讀掃描第二輪:用面板自己的股數序列判斷拆股事件是不是屬於這家公司。

道理:一次真拆股,公司自己申報的股數(SEC XBRL diluted_shares)一定會跟着跳同一個倍數。
一次屬於別家公司的拆股(代號被重用),股數序列一動不動,但拆股因子照樣被乘上去。
所以:拆股因子在某個申報日前後變了 K 倍,而原始股數沒有跟着變 —— 那一次拆股不屬於這家公司。
"""
import json
import pathlib

import numpy as np
import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
OUT = REPO / "experiments" / "2026-09-03-ticker-reuse" / "out"
OUT.mkdir(parents=True, exist_ok=True)

splits = pd.read_parquet(REPO / "experiments/2026-09-02-fourpiece-test/data/splits.parquet")
splits["report_date"] = pd.to_datetime(splits["report_date"])
panel = pd.read_parquet(
    REPO / "experiments/2026-09-02-fundamentals-panel/out/panel_monthly.parquet",
    columns=["ticker", "cik", "month_end", "diluted_shares", "diluted_shares_filed",
             "diluted_shares_end"])
panel["month_end"] = pd.to_datetime(panel["month_end"])
panel["filed"] = pd.to_datetime(panel["diluted_shares_filed"])

sp = {s: g[["report_date", "ratio"]].to_numpy() for s, g in splits.groupby("symbol")}


def factor(sym, filed):
    arr = sp.get(sym)
    if arr is None or pd.isna(filed):
        return 1.0
    out = 1.0
    for d, r in arr:
        if d > filed:
            out *= float(r)
    return out


rows = []
for t, g in panel.groupby("ticker", sort=True):
    if t not in sp:
        continue
    g = g.dropna(subset=["diluted_shares", "filed"]).sort_values("month_end")
    if len(g) < 4:
        continue
    fac = np.array([factor(t, f) for f in g["filed"]])
    sh = g["diluted_shares"].to_numpy(float)
    # 逐一拆股事件:比較事件前後最近的兩個申報,股數比 vs 因子比
    for d, r in sp[t]:
        d = pd.Timestamp(d)
        before = g[g["filed"] < d]
        after = g[g["filed"] > d]
        if before.empty or after.empty:
            continue
        b = before.iloc[-1]
        a = after.iloc[0]
        sh_ratio = float(a["diluted_shares"]) / float(b["diluted_shares"])
        gap_days = int((pd.Timestamp(a["filed"]) - pd.Timestamp(b["filed"])).days)
        # 一次 1:N 反向拆股,股數應該乘 r(r<1 即股數減少)
        expected = float(r)
        # 股數有沒有跟着動?用對數距離量
        moved = abs(np.log10(sh_ratio / expected)) if sh_ratio > 0 else np.nan
        stayed = abs(np.log10(sh_ratio)) if sh_ratio > 0 else np.nan
        rows.append({
            "ticker": t, "cik": int(g["cik"].iloc[0]),
            "split_date": d.date().isoformat(), "ratio": float(r),
            "ratio_log10": round(float(np.log10(r)), 3),
            "shares_before": float(b["diluted_shares"]),
            "shares_after": float(a["diluted_shares"]),
            "filed_before": pd.Timestamp(b["filed"]).date().isoformat(),
            "filed_after": pd.Timestamp(a["filed"]).date().isoformat(),
            "gap_days": gap_days,
            "shares_ratio": round(sh_ratio, 6),
            "dist_to_split": round(float(moved), 3),
            "dist_to_flat": round(float(stayed), 3),
        })

ev = pd.DataFrame(rows)
# 判定:拆股倍數 >=10 倍,而股數在事件前後幾乎不動(對數距離 < 0.3,即 2 倍以內)
ev["big"] = ev["ratio_log10"].abs() >= 1.0
ev["shares_flat"] = ev["dist_to_flat"] < 0.3
ev["shares_followed"] = ev["dist_to_split"] < 0.3
ev["verdict"] = np.where(
    ev["big"] & ev["shares_flat"], "不屬於本公司(股數無跟隨)",
    np.where(ev["big"] & ev["shares_followed"], "屬於本公司(股數跟隨)",
             np.where(ev["big"], "不確定", "細幅,不判")))
ev.to_csv(OUT / "split_vs_shares.csv", index=False, encoding="utf-8")

print("panel 覆蓋到的拆股事件:", len(ev), "涉及", ev.ticker.nunique(), "個代號")
print(ev["verdict"].value_counts().to_string())
print("\n=== 判為不屬於本公司的事件 ===")
bad = ev[ev.verdict.str.startswith("不屬於")]
print(bad.to_string(index=False))
print("\n=== 判為不確定的大事件 ===")
print(ev[ev.verdict == "不確定"].to_string(index=False))
