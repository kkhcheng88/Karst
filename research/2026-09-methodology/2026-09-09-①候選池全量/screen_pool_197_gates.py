# -*- coding: utf-8 -*-
"""KARST-197 第一步:按 D-172 / D-173 的新閘,由 5,104 家宇宙重篩候選池。

**與舊篩(KARST-184 screen_step1/step2)的分別**——只有閘改了,觸發條件一格未動:

  觸發(不變):2026-06-01 → 2026-09-04 窗口內相對 SPY 跌逾 25%
  閘一(不變):近 60 日中位成交金額 ≥ 300 萬美元
  閘二(改):滾動四季經營現金流 > 0
  取消:市值 ≥ 3 億美元(D-172,用戶裁決「市值 5億以上 << I think actually no need this at all」)
  降為標籤:淨負債 ÷ 經營現金流 ≤ 3 倍、現金投資 ≥ 短債 × 2(D-173,用戶裁決)
  降為標籤:財務透明度(能不能建帳、申報有沒有落後)——建不到帳的照樣列出,標「資料不足」

價格層直接沿用 KARST-184 的 screen_step1_raw.csv(同一窗口、同一批日線),
**刻意不重抓**:重抓會令窗口移位,前後差異就混入了「窗口不同」這個與閘無關的原因。
價格日期記在輸出的 _meta。

輸出:screen_pool_197_gates.csv(319 家觸發+流動性候選的逐家閘結果)
"""
import datetime as dt
import json
import os
import sys

import pandas as pd

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa: E402

RAW = (r"C:\projects\Karst\research\2026-09-methodology"
       r"\2026-09-08-①候選池走通\screen_step1_raw.csv")
OUT = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"

TRIGGER_REL_SPY = -0.25
MIN_DOLLAR_VOL = 3e6

OCF_TAGS = ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]


def gate_row(t: str) -> dict:
    r = dict(ticker=t)
    try:
        fin = IE.build_financials(t)
    except Exception as e:
        r["buildable"] = False
        r["gate_ocf"] = False
        r["note"] = "建帳失敗:%s: %s" % (type(e).__name__, e)
        return r
    r["buildable"] = True
    facts = IE.load_facts(fin.cik)
    ocf_q = IE.quarterize(IE.duration_series(facts, OCF_TAGS))
    ocf_ttm, _ = IE.ttm(ocf_q, fin.asof) if ocf_q else (None, [])
    short_debt = IE._latest(IE.instant_series(facts, IE.DEBT_CUR_TAGS), fin.asof)
    nd = fin.net_debt
    r.update(name=fin.name, cik=fin.cik, asof=str(fin.asof),
             rev_ttm=fin.rev_ttm, ebit_ttm=fin.ebit_ttm,
             cash=fin.cash, investments=fin.investments, debt=fin.debt,
             lease_debt=fin.lease_debt, short_debt=short_debt, net_debt=nd,
             ocf_ttm=ocf_ttm, capex_ttm=fin.capex_ttm, sbc_ttm=fin.sbc_ttm,
             diluted_shares=fin.diluted_shares,
             fin_notes="; ".join(fin.notes) if fin.notes else "")
    # 唯一的財務閘
    r["gate_ocf"] = bool(ocf_ttm is not None and ocf_ttm > 0)
    # 以下全部只作標籤,不剔人
    r["net_debt_to_ocf"] = (nd / ocf_ttm) if (ocf_ttm and ocf_ttm > 0) else None
    if nd < 0:
        r["debt_label"] = "淨現金"
    elif ocf_ttm and ocf_ttm > 0:
        x = nd / ocf_ttm
        r["debt_label"] = ("低(≤3 倍)" if x <= 3 else
                           "中(3–6 倍)" if x <= 6 else "高(>6 倍)")
    else:
        r["debt_label"] = "算不出(經營現金流不正)"
    r["refi_cover_label"] = ("充裕" if (fin.cash + fin.investments) >= short_debt * 2
                             else "不足(現金投資 < 短債 ×2)")
    r["transparent_label"] = ("齊" if (fin.rev_ttm and fin.ebit_ttm is not None)
                              else "資料不足(缺收入或營業利潤)")
    return r


def main():
    raw = pd.read_csv(RAW)
    trig = raw[raw["rel_spy"] <= TRIGGER_REL_SPY].copy()
    cand = trig[trig["med_dollar_vol_60d"] >= MIN_DOLLAR_VOL].copy()
    cand = cand.sort_values("rel_spy")
    print("宇宙 %d 家 → 觸發(相對 SPY ≤ -25%%)%d 家 → 過成交額線 %d 家"
          % (len(raw), len(trig), len(cand)), flush=True)
    rows = []
    for i, t in enumerate(cand["ticker"].tolist(), 1):
        rows.append(gate_row(t))
        if i % 25 == 0:
            print("  %d/%d" % (i, len(cand)), flush=True)
    g = pd.DataFrame(rows)
    m = cand.merge(g, on="ticker", how="left", suffixes=("", "_sec"))
    for c in ("gate_ocf", "buildable"):
        m[c] = m[c].fillna(False)
    m["gate_liquidity"] = True
    m["in_pool"] = m["gate_ocf"]
    m = m.sort_values(["in_pool", "rel_spy"], ascending=[False, True])
    m.to_csv(os.path.join(OUT, "screen_pool_197_gates.csv"),
             index=False, encoding="utf-8-sig")
    meta = dict(
        universe=int(len(raw)), triggered=int(len(trig)), liquidity_ok=int(len(cand)),
        in_pool=int(m["in_pool"].sum()),
        price_source="KARST-184 screen_step1_raw.csv(窗口 2026-06-01 → 2026-09-04,"
                     "yfinance 日線,抓於 2026-09-08)",
        gates=["觸發:相對 SPY 窗口跌幅 ≤ -25%(口徑不變)",
               "近 60 日中位成交金額 ≥ 300 萬美元(示例值,待參數對齊)",
               "滾動四季經營現金流 > 0"],
        dropped_gates=["市值 ≥ 3 億美元(D-172 取消)",
                       "淨負債 ÷ 經營現金流 ≤ 3 倍(D-173 降為標籤)",
                       "現金投資 ≥ 短債 × 2(D-173 降為標籤)",
                       "財務透明度 / 申報新鮮度(降為標籤,建不到帳者照列)"],
        run_at=str(dt.datetime.now()),
    )
    with open(os.path.join(OUT, "screen_pool_197_gates.meta.json"), "w",
              encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print("入池 %d 家 / 候選 %d 家;建不到帳 %d 家"
          % (m["in_pool"].sum(), len(m), int((~m["buildable"].astype(bool)).sum())),
          flush=True)


if __name__ == "__main__":
    main()
