# -*- coding: utf-8 -*-
"""KARST-191:負債閘資料不足重算——事件層。

讀 out/events.csv(KARST-187 正本,不改),對 `has_total_debt == False` 的
14,482 個事件,逐個用 debt_gatefix_core.fallback_total_debt() 試補總債務:
  - companyfacts 有標籤可用 → 回算出一個數字(可能是 0),重新判 N2 淨現金閘與
    債務比閘
  - companyfacts 也沒有任何債務標籤(或者連快照檔都沒有) → 標「資料不足」,
    這一格獨立存在,不併入過閘也不併入不過閘

輸出 out/events_gatefix.csv:等同 events.csv 加上以下新欄:
  total_debt_gatefix           面板值(若有)或 companyfacts 後備值(若補到)
  total_debt_source_gatefix    "panel" / "companyfacts_fallback" / "資料不足"
  total_debt_reason_gatefix    後備計算的說明或資料不足的原因
  debt_cur_fallback / debt_nc_fallback   後備算出的短債/長債拆件(供人手核)
  資料不足_債務閘               bool,True = 這個事件的負債閘判不出(獨立分類)
  gate_debt_n2_gatefix         bool,只在有值時才可能為 True;資料不足一律 False
  gate_debt_ratio_gatefix      同上,債務比版本

同時輸出 out/build_stats_gatefix.json:空白事件數、補回幾多、仍資料不足幾多。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import debt_gatefix_core as DGF  # noqa: E402

OUT = HERE / "out"


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    ev = pd.read_csv(OUT / "events.csv", encoding="utf-8-sig",
                     parse_dates=["trigger_date", "panel_period_end"],
                     dtype={"entity_id": "string"})
    ev["entity_id"] = ev["entity_id"].str.zfill(10)   # CSV 會吃掉 CIK 的前置零
    n = len(ev)

    has_td = ev["has_total_debt"].to_numpy()
    blank_idx = np.nonzero(~has_td)[0]
    n_blank = len(blank_idx)
    log(f"事件表 {n:,} 列,總債務空白 {n_blank:,} 個,開始逐個用 companyfacts 後備補算")

    total_debt_fb = np.full(n, np.nan)
    debt_cur_fb = np.full(n, np.nan)
    debt_nc_fb = np.full(n, np.nan)
    source = np.array(["panel"] * n, dtype=object)
    reason = np.array([""] * n, dtype=object)

    for k, i in enumerate(blank_idx):
        row = ev.iloc[i]
        r = DGF.fallback_total_debt(
            row["entity_id"],
            row["panel_period_end"].date(),
            row["trigger_date"].date(),
        )
        source[i] = r["status"]
        reason[i] = r["reason"]
        if r["status"] == "companyfacts_fallback":
            total_debt_fb[i] = r["total_debt"]
            debt_cur_fb[i] = r["debt_cur"]
            debt_nc_fb[i] = r["debt_nc"]
        if (k + 1) % 1000 == 0:
            log(f"  {k + 1:,}/{n_blank:,}")

    panel_td = ev["total_debt"].to_numpy(dtype="float64")
    total_debt_gatefix = np.where(has_td, panel_td, total_debt_fb)

    ev["total_debt_gatefix"] = total_debt_gatefix
    ev["total_debt_source_gatefix"] = source
    ev["total_debt_reason_gatefix"] = reason
    ev["debt_cur_fallback"] = debt_cur_fb
    ev["debt_nc_fallback"] = debt_nc_fb
    ev["資料不足_債務閘"] = (source == "資料不足")

    cash = ev["cash"].to_numpy(dtype="float64")
    ttm = ev["ttm_ocf"].to_numpy(dtype="float64")
    resolved = ~ev["資料不足_債務閘"].to_numpy()

    gate_n2 = pd.Series(False, index=ev.index)
    gate_n2.loc[resolved] = (cash[resolved] - total_debt_gatefix[resolved]) >= 0

    gate_ratio = pd.Series(False, index=ev.index)
    ok = resolved & (ttm > 0)
    gate_ratio.loc[ok] = (total_debt_gatefix[ok] / ttm[ok]) <= 3.0

    ev["gate_debt_n2_gatefix"] = gate_n2.to_numpy()
    ev["gate_debt_ratio_gatefix"] = gate_ratio.to_numpy()

    ev.to_csv(OUT / "events_gatefix.csv", index=False, encoding="utf-8-sig")

    n_fixed = int((source == "companyfacts_fallback").sum())
    n_insuff = int(ev["資料不足_債務閘"].sum())
    stats = dict(
        總事件數=int(n),
        原始總債務空白事件數=int(n_blank),
        companyfacts補回事件數=n_fixed,
        仍資料不足事件數=n_insuff,
        補回率=round(n_fixed / n_blank, 4) if n_blank else None,
        補回後過負債閘A_N2=int(ev["gate_debt_n2_gatefix"].sum()),
        補回後過負債閘B_債務比=int(ev["gate_debt_ratio_gatefix"].sum()),
        原始過負債閘A_N2=int(ev["gate_debt_n2"].sum()),
        原始過負債閘B_債務比=int(ev["gate_debt_ratio"].sum()),
    )
    log(json.dumps(stats, ensure_ascii=False, indent=2))
    with open(OUT / "build_stats_gatefix.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
