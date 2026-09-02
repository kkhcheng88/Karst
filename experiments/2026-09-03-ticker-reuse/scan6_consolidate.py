"""KARST-165 收口:三個獨立訊號合併,出代號重用清單與拆股修補清單。

訊號:
  R1 CIK 首次申報日晚於代號加入指數的日子 —— 那個 CIK 當時還未存在,不可能是它
  R2 成分期內的營收中位數 < 1 億美元,或者市值中位數 < 3 億美元 —— 指數成分股不可能這麼細
  R3 成分期內的市值 / 營收比 > 200 倍 —— 大市值配微型營收,兩邊來自不同公司
  R4 拆股事件日在代號離開指數之後而且倍數 >= 10 倍 —— 那次拆股屬代號後來的使用者
"""
import json
import pathlib

import numpy as np
import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
OUT = REPO / "experiments" / "2026-09-03-ticker-reuse" / "out"
OUT.mkdir(parents=True, exist_ok=True)

uni = pd.read_csv(REPO / "experiments/2026-09-02-fundamentals-panel/out/universe_cik.csv",
                  dtype=str)
mcap = pd.read_csv(OUT / "implied_mcap_screen.csv")
splits = pd.read_parquet(REPO / "experiments/2026-09-02-fourpiece-test/data/splits.parquet")
splits["report_date"] = pd.to_datetime(splits["report_date"])
panel = pd.read_parquet(
    REPO / "experiments/2026-09-02-fundamentals-panel/out/panel_monthly.parquet",
    columns=["ticker", "month_end"])
cells = panel.groupby("ticker").size()

import re
pat = re.compile(r"申報期\s*(\d{4}-\d{2}-\d{2})~(\d{4}-\d{2}-\d{2})")
npat = re.compile(r"候選 CIK \d+\(([^)]+)\)")
uni["filed_from"] = uni["cik_note"].map(
    lambda s: pat.search(s).group(1) if isinstance(s, str) and pat.search(s) else None)
uni["cand_name"] = uni["cik_note"].map(
    lambda s: npat.search(s).group(1) if isinstance(s, str) and npat.search(s) else None)

meta = {}
for p in ["experiments/2026-09-02-narrative-layers/out/ticker_meta.json",
          "experiments/2026-09-02-narrative-layers-v2/out/ticker_meta_new.json"]:
    f = REPO / p
    if f.exists():
        meta.update(json.loads(f.read_text(encoding="utf-8")))

mm = mcap.set_index("ticker")
rows = []
for _, r in uni.iterrows():
    t = r["ticker"]
    if pd.isna(r["cik"]):
        continue
    mk = mm.loc[t] if t in mm.index else None
    rev = float(mk["median_rev_ttm_usd_m"]) if mk is not None and pd.notna(
        mk.get("median_rev_ttm_usd_m")) else None
    cap = float(mk["median_mcap_usd_m"]) if mk is not None and pd.notna(
        mk.get("median_mcap_usd_m")) else None
    ff, jo = r["filed_from"], r["joined_on"]
    r1 = bool(isinstance(ff, str) and isinstance(jo, str) and ff > jo)
    r2 = bool((rev is not None and rev < 100) or (cap is not None and 0 < cap < 300))
    r3 = bool(rev and cap and rev > 0 and cap / rev > 200)
    sev = splits[splits.symbol == t]
    lo = r["left_on"]
    r4 = bool(len(sev) and isinstance(lo, str) and any(
        (str(d.date()) > lo) and abs(np.log10(x)) >= 1.0
        for d, x in zip(sev["report_date"], sev["ratio"])))
    score = sum([r1, r2, r3, r4])
    if score == 0:
        continue
    rows.append({
        "ticker": t, "index_joined": r["joined_on"], "index_left": r["left_on"],
        "delisted_or_removed": r["delisted_or_removed"],
        "resolved_cik": r["cik"], "cik_source": r["cik_source"],
        "cik_first_filed": r["filed_from"],
        "cik_name_today": r["cand_name"],
        "yfinance_name_today": (meta.get(t, {}) or {}).get("longName"),
        "median_mcap_usd_m": cap, "median_rev_ttm_usd_m": rev,
        "R1_cik_born_after_index_join": r1,
        "R2_too_small_for_index": r2,
        "R3_mcap_rev_absurd": r3,
        "R4_split_after_index_exit": r4,
        "signals": score,
        "panel_cells": int(cells.get(t, 0)),
    })
res = pd.DataFrame(rows).sort_values(["signals", "ticker"], ascending=[False, True])
res["verdict"] = np.where(res.signals >= 2, "確證重用", "嫌疑,要人手核")
res.to_csv(OUT / "ticker_reuse.csv", index=False, encoding="utf-8")

pd.set_option("display.width", 260, "display.max_colwidth", 34)
print("命中至少一個訊號的代號:", len(res))
print(res["verdict"].value_counts().to_string())
print("\n=== 全清單 ===")
print(res[["ticker", "index_joined", "index_left", "resolved_cik", "cik_source",
           "cik_name_today", "median_mcap_usd_m", "median_rev_ttm_usd_m",
           "R1_cik_born_after_index_join", "R2_too_small_for_index",
           "R3_mcap_rev_absurd", "R4_split_after_index_exit",
           "signals", "panel_cells", "verdict"]].to_string(index=False))

# ---- 修補清單 ----
fix = []
confirmed = set(res[res.verdict == "確證重用"]["ticker"])
for _, r in res.iterrows():
    sev = splits[splits.symbol == r["ticker"]]
    for _, e in sev.iterrows():
        il = r["index_left"]
        after = isinstance(il, str) and str(e["report_date"].date()) > il
        fix.append({
            "ticker": r["ticker"], "split_date": str(e["report_date"].date()),
            "ratio": float(e["ratio"]),
            "ratio_log10": round(float(np.log10(e["ratio"])), 3) if e["ratio"] > 0 else None,
            "index_left": r["index_left"],
            "event_after_index_exit": after,
            "resolved_cik": r["resolved_cik"],
            "correct_owner": ("代號後來的使用者(不是成分期那家)" if after
                              else "成分期那家(事件在成分期內)"),
            "ticker_verdict": r["verdict"],
            "panel_cells_of_ticker": r["panel_cells"],
            "action": ("由拆股事件表剔走(對成分期那家而言)" if after
                       else "保留,但要以 CIK 重新索引後再核"),
        })
fx = pd.DataFrame(fix)
fx.to_csv(OUT / "split_fixes_proposed.csv", index=False, encoding="utf-8")
print("\n=== 修補清單 ===")
print(fx.to_string(index=False))
print("\n確證重用的代號共", len(confirmed), ":", sorted(confirmed))
print("確證重用代號的面板格數合計:",
      int(res[res.verdict == "確證重用"]["panel_cells"].sum()))
