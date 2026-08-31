#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF 申贖資金流實測 —— 目標:確認富途 OpenAPI 有冇材料砌到「ETF 申贖流歷史」

申贖流定義:在外股數(outstanding units)逐日變化,或 AUM 變化剔除價格變動。

逐項驗:
  probe1  get_snapshot 對 ETF 回咩欄位(有冇 AUM / 在外股數 / 總市值),係咪只有當下值
  probe2  歷史序列:kline 附帶欄位、stock_basicinfo、其他端點有冇市值/在外股數歷史
  probe3  get_capital_flow 對 ETF 得唔得(盤口資金流,非申贖流),深度同欄位
  probe4  get_owner_plate + 其他可能收埋規模史嘅位

只讀行情。限頻:每次呼叫之間 1.1 秒。
"""
import sys
import os
import json
import time

sys.path.insert(0, r"C:\Users\Kaho\.claude\skills\futuapi\scripts")
from common import create_quote_context, safe_close  # noqa: E402
from futu import (  # noqa: E402
    KLType, AuType, PeriodType, KL_FIELD, SubType, Plate,
)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "etf_flow_probe.json")
PACE = 1.1
ETFS = ["US.XLK", "US.SPY", "US.QQQ", "US.XLE", "HK.02800"]
result = {}


def pace():
    time.sleep(PACE)


def rec(ret, data):
    """把 (ret, data) 轉成可 JSON 化嘅摘要"""
    if ret != 0:
        return {"ok": False, "err": str(data)[:300]}
    try:
        import pandas as pd  # noqa: F401
        if hasattr(data, "to_dict"):
            return {"ok": True, "rows": len(data), "cols": list(data.columns),
                    "sample": json.loads(data.head(3).to_json(orient="records"))}
    except Exception:
        pass
    return {"ok": True, "raw": str(data)[:2000]}


ctx = create_quote_context()

# ---------------- probe1: snapshot 欄位 ----------------
p1 = {}
for code in ETFS:
    ret, data = ctx.get_market_snapshot([code])
    pace()
    if ret != 0:
        p1[code] = {"ok": False, "err": str(data)[:300]}
        continue
    row = json.loads(data.to_json(orient="records"))[0]
    # 抽出同「規模」有關嘅欄位
    keys_scale = {k: v for k, v in row.items()
                  if any(t in k.lower() for t in
                         ["trust", "share", "market_val", "asset", "aum", "unit", "nav"])}
    p1[code] = {
        "ok": True,
        "n_fields": len(row),
        "stock_type": row.get("stock_type"),
        "scale_fields": keys_scale,
        "all_field_names": sorted(row.keys()),
    }
result["probe1_snapshot"] = p1

# ---------------- probe2: 歷史序列 ----------------
p2 = {}

# 2a. kline 全欄位 —— 睇下有冇市值/股數欄
try:
    ret, data, page = ctx.request_history_kline(
        "US.XLK", start="2026-08-01", end="2026-08-29",
        ktype=KLType.K_DAY, autype=AuType.QFQ,
        fields=[KL_FIELD.ALL], max_count=50)
    pace()
    p2["kline_all_fields"] = rec(ret, data)
except Exception as e:
    p2["kline_all_fields"] = {"ok": False, "err": str(e)[:300]}

# 2b. stock_basicinfo —— 靜態資料有冇股數
try:
    ret, data = ctx.get_stock_basicinfo("US", "ETF", ["US.XLK", "US.SPY"])
    pace()
    p2["stock_basicinfo_ETF"] = rec(ret, data)
except Exception as e:
    p2["stock_basicinfo_ETF"] = {"ok": False, "err": str(e)[:300]}

# 2c. valuation_detail 對 ETF(上次已知 no_data,再確認一次口徑)
try:
    ret, data = ctx.get_valuation_detail("US.XLK", valuation_type=1, interval_type=3)
    pace()
    p2["valuation_detail_XLK"] = rec(ret, data)
except Exception as e:
    p2["valuation_detail_XLK"] = {"ok": False, "err": str(e)[:300]}

# 2d. 財報介面對 ETF(股數通常喺財報)
for fn, args in [
    ("get_financials_statements", ("US.XLK",)),
    ("get_shareholders_overview", ("US.XLK",)),
    ("get_institution_holding_list", ("US.XLK",)),
    ("get_short_interest", ("US.XLK",)),
    ("get_rehab", ("US.XLK",)),
]:
    if not hasattr(ctx, fn):
        p2[fn] = {"ok": False, "err": "SDK 冇呢個方法"}
        continue
    try:
        out = getattr(ctx, fn)(*args)
        pace()
        p2[fn] = rec(out[0], out[1])
    except Exception as e:
        p2[fn] = {"ok": False, "err": str(e)[:300]}

result["probe2_history"] = p2

# ---------------- probe3: capital_flow 對 ETF ----------------
p3 = {}
for code in ["US.XLK", "US.SPY", "HK.02800"]:
    try:
        ret, data = ctx.get_capital_flow(code, period_type=PeriodType.DAY,
                                         start="2025-09-01", end="2026-08-29")
        pace()
        r = rec(ret, data)
        if r.get("ok") and r.get("rows"):
            recs = json.loads(data.to_json(orient="records"))
            r["first"] = recs[0]
            r["last"] = recs[-1]
        p3[code + "_DAY"] = r
    except Exception as e:
        p3[code + "_DAY"] = {"ok": False, "err": str(e)[:300]}

# 試更深歷史(睇下上限)
try:
    ret, data = ctx.get_capital_flow("US.XLK", period_type=PeriodType.DAY,
                                     start="2015-01-01", end="2026-08-29")
    pace()
    r = rec(ret, data)
    if r.get("ok") and r.get("rows"):
        recs = json.loads(data.to_json(orient="records"))
        r["first"] = recs[0]
        r["last"] = recs[-1]
    p3["US.XLK_DAY_deep"] = r
except Exception as e:
    p3["US.XLK_DAY_deep"] = {"ok": False, "err": str(e)[:300]}

result["probe3_capital_flow"] = p3

# ---------------- probe4: owner_plate 及其他 ----------------
p4 = {}
for fn, args in [
    ("get_owner_plate", (["US.XLK", "US.SPY"],)),
    ("get_capital_distribution", ("US.XLK",)),
    ("get_referencestock_list", ("US.XLK", 1)),
]:
    if not hasattr(ctx, fn):
        p4[fn] = {"ok": False, "err": "SDK 冇呢個方法"}
        continue
    try:
        out = getattr(ctx, fn)(*args)
        pace()
        p4[fn] = rec(out[0], out[1])
    except Exception as e:
        p4[fn] = {"ok": False, "err": str(e)[:300]}

result["probe4_other"] = p4

safe_close(ctx)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print("WROTE", OUT)
