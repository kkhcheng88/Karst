"""KARST-165 唯讀掃描:拆股事件表的代號重用污染。

只讀不寫任何既有數據;輸出落 experiments/2026-09-03-ticker-reuse/out/。
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
    columns=["ticker", "cik", "month_end", "diluted_shares"])
panel["month_end"] = pd.to_datetime(panel["month_end"])
fixes = pd.read_csv(REPO / "experiments/2026-09-02-panel-scale-fix/out/scale_fixes.csv")
tick2cik = json.loads((REPO / "data/sec/company_tickers.json").read_text(encoding="utf-8"))

# 10-K 申報紀錄:每個 CIK 的最早/最新 10-K 申報日
recs = []
with (REPO / "data/sec/10k_text/manifest.jsonl").open(encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line:
            d = json.loads(line)
            recs.append((d["ticker"], str(int(d["cik"])), d["filingDate"]))
man = pd.DataFrame(recs, columns=["ticker", "cik", "filingDate"])
cik_span = man.groupby("cik")["filingDate"].agg(["min", "max"])

# 價格序列的頭尾(兩個寬表)
px_span = {}
for p in ["experiments/2026-09-02-timing-sweep/data/daily_close.parquet",
          "experiments/2026-09-02-narrative-layers-v2/data/new_close.parquet"]:
    df = pd.read_parquet(REPO / p)
    df.index = pd.to_datetime(df.index)
    for c in df.columns:
        s = df[c].dropna()
        if len(s):
            a, b = s.index.min(), s.index.max()
            if c in px_span:
                a = min(a, px_span[c][0]); b = max(b, px_span[c][1])
            px_span[c] = (a, b)

panel_span = panel.groupby("ticker")["month_end"].agg(["min", "max"])
panel_cik = panel.groupby("ticker")["cik"].agg(lambda s: str(int(s.iloc[0])))

rows = []
for _, ev in splits.iterrows():
    t, d, r = ev["symbol"], ev["report_date"], float(ev["ratio"])
    cur = tick2cik.get(t)
    cur = str(int(cur)) if cur else None
    pcik = panel_cik.get(t)
    span = cik_span.loc[cur] if cur in cik_span.index else None
    ps = px_span.get(t)
    pn = panel_span.loc[t] if t in panel_span.index else None
    rows.append({
        "ticker": t,
        "split_date": d.date().isoformat(),
        "ratio": r,
        "is_reverse": r < 1,
        "magnitude": round(abs(np.log10(r)), 3) if r > 0 else None,
        "current_cik": cur,
        "panel_cik": pcik,
        "cik_first_10k": span["min"] if span is not None else None,
        "cik_last_10k": span["max"] if span is not None else None,
        "price_first": ps[0].date().isoformat() if ps else None,
        "price_last": ps[1].date().isoformat() if ps else None,
        "panel_first": pn["min"].date().isoformat() if pn is not None else None,
        "panel_last": pn["max"].date().isoformat() if pn is not None else None,
    })
ev = pd.DataFrame(rows)

# 訊號
ev["S1_before_cik_first_10k"] = (
    ev["cik_first_10k"].notna() & (ev["split_date"] < ev["cik_first_10k"]))
ev["S2_outside_price_span"] = (
    ev["price_first"].notna() & ((ev["split_date"] < ev["price_first"])
                                | (ev["split_date"] > ev["price_last"])))
ev["S3_extreme"] = ev["magnitude"].fillna(0) >= 1.0   # 10 倍或以上
ev["S4_cik_mismatch"] = (ev["current_cik"].notna() & ev["panel_cik"].notna()
                         & (ev["current_cik"] != ev["panel_cik"]))
ev.to_csv(OUT / "split_events_scored.csv", index=False, encoding="utf-8")

# S5:面板證據——封面頁股數與原始股數一致,但拆股因子遠離 1
f = fixes.copy()
f["cover_ok"] = f["cover_log10_ratio"].abs() < 0.35
f["sf_far"] = (f["split_factor"].notna()
               & (np.log10(f["split_factor"].replace(0, np.nan)).abs() >= 1.0))
s5 = f[f["cover_ok"] & f["sf_far"]]
s5g = (s5.groupby(["ticker", "cik"])
       .agg(cells=("month_end", "size"), split_factor=("split_factor", "first"),
            first_month=("month_end", "min"), last_month=("month_end", "max"),
            action=("action", lambda s: ",".join(sorted(set(s)))))
       .reset_index())
s5g.to_csv(OUT / "panel_evidence_cover_vs_split.csv", index=False, encoding="utf-8")

print("=== split events:", len(ev), "on", ev.ticker.nunique(), "tickers")
for c in ["S1_before_cik_first_10k", "S2_outside_price_span", "S3_extreme", "S4_cik_mismatch"]:
    print(f"  {c:26} {int(ev[c].sum())}")
print("\n=== S5 面板證據(封面頁認同原始股數,但拆股因子偏離 10 倍以上)===")
print(s5g.to_string(index=False))
print("\n=== 已知三個代號的事件 ===")
print(ev[ev.ticker.isin(["CPWR", "EP", "PARA"])].to_string(index=False))
print("\n=== S1 或 S2 命中而且 S3 極端 ===")
hit = ev[(ev.S1_before_cik_first_10k | ev.S2_outside_price_span) & ev.S3_extreme]
print(hit.to_string(index=False))
