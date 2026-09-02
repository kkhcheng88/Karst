"""KARST-165 唯讀掃描第三輪:拆股事件落在公司申報窗口之外 = 代號重用的直接證據。

一家公司被收購或者除牌之後不再申報。拆股事件表按代號索引,所以代號後來的使用者做的拆股
會被套到前一家公司身上。判準:事件日期在該 CIK 最後一次申報之後(或者最早一次申報之前),
而且事件倍數夠大(10 倍或以上)——那次拆股一定不屬於面板裡這家公司。
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
             "revenue_filed", "assets_filed"])
panel["month_end"] = pd.to_datetime(panel["month_end"])
for c in ["diluted_shares_filed", "revenue_filed", "assets_filed"]:
    panel[c] = pd.to_datetime(panel[c])
panel["any_filed"] = panel[["diluted_shares_filed", "revenue_filed",
                            "assets_filed"]].max(axis=1)

# 每個代號在面板裡的申報窗口(該 CIK 真正有申報的日子)
win = (panel.dropna(subset=["any_filed"]).groupby("ticker")
       .agg(cik=("cik", lambda s: int(s.iloc[0])),
            first_filed=("any_filed", "min"), last_filed=("any_filed", "max"),
            panel_first=("month_end", "min"), panel_last=("month_end", "max"),
            cells=("month_end", "size")))

# 10-K 快取的申報窗口(獨立第二來源)
recs = []
with (REPO / "data/sec/10k_text/manifest.jsonl").open(encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line:
            d = json.loads(line)
            recs.append((d["ticker"], int(d["cik"]), d["filingDate"]))
man = pd.DataFrame(recs, columns=["ticker", "cik", "filingDate"])
man_win = man.groupby("ticker")["filingDate"].agg(k10_first="min", k10_last="max")

rows = []
for _, e in splits.iterrows():
    t, d, r = e["symbol"], e["report_date"], float(e["ratio"])
    if t not in win.index:
        continue
    w = win.loc[t]
    mw = man_win.loc[t] if t in man_win.index else None
    after_last = d > w["last_filed"]
    before_first = d < w["first_filed"]
    k10_after = (mw is not None) and (d.date().isoformat() > mw["k10_last"])
    rows.append({
        "ticker": t, "cik": int(w["cik"]),
        "split_date": d.date().isoformat(), "ratio": r,
        "ratio_log10": round(float(np.log10(r)), 3) if r > 0 else None,
        "cik_first_filed": w["first_filed"].date().isoformat(),
        "cik_last_filed": w["last_filed"].date().isoformat(),
        "k10_last": mw["k10_last"] if mw is not None else None,
        "panel_cells": int(w["cells"]),
        "panel_first": w["panel_first"].date().isoformat(),
        "panel_last": w["panel_last"].date().isoformat(),
        "after_last_filing": bool(after_last),
        "before_first_filing": bool(before_first),
        "after_last_10k": bool(k10_after),
        "big": abs(np.log10(r)) >= 1.0 if r > 0 else False,
    })
ev = pd.DataFrame(rows)
ev["suspect"] = ev["after_last_filing"] & ev["big"]
ev.to_csv(OUT / "split_vs_filing_window.csv", index=False, encoding="utf-8")

print("有面板申報窗口的拆股事件:", len(ev), "涉及", ev.ticker.nunique(), "個代號")
print("事件日在該公司最後一次申報之後:", int(ev["after_last_filing"].sum()))
print("  其中倍數 >=10 倍(污染面板的那種):", int(ev["suspect"].sum()))
print("事件日在該公司最早一次申報之前:", int(ev["before_first_filing"].sum()))
print("\n=== 判定重用的事件 ===")
print(ev[ev.suspect].to_string(index=False))
print("\n=== 事件在最後申報之後但倍數細 ===")
print(ev[ev.after_last_filing & ~ev.big].to_string(index=False))
