#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF 申贖流後門 —— 第五輪:釐清月 K 換手率嘅口徑

月 K 反推股數 與 月底日 K 反推股數 中位數差 0.2%(XLK),超出捨入雜訊一個數量級,
即兩者唔係同一個口徑。兩個候選:
  H1  月 tr = 當月各日 tr 相加(每日各用當日股數)-> 月反推值 = 成交量加權調和平均股數
  H2  月 tr = 當月總成交量 ÷ 月底股數        -> 月反推值 = 月底股數

驗法:直接由日 K 算 Σ(daily tr) 同 Σvol/u_monthend,同月 K 嘅 tr 逐月對數。

只讀行情。
"""
import sys
import os
import json
import time

sys.path.insert(0, r"C:\Users\Kaho\.claude\skills\futuapi\scripts")
from common import create_quote_context, safe_close  # noqa: E402
from futu import KLType, AuType, KL_FIELD  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "etf_flow_probe5.json")
PACE = 1.1
FIELDS = [KL_FIELD.DATE_TIME, KL_FIELD.CLOSE, KL_FIELD.TRADE_VOL, KL_FIELD.TURNOVER_RATE]
ctx = create_quote_context()


def fetch(code, ktype, start):
    rows, page, guard = [], None, 0
    while True:
        kw = dict(ktype=ktype, autype=AuType.QFQ, fields=FIELDS, max_count=1000)
        if page:
            kw["page_req_key"] = page
        ret, df, page = ctx.request_history_kline(code, start=start, end="2026-07-31", **kw)
        time.sleep(PACE)
        if ret != 0:
            return None
        rows += json.loads(df.to_json(orient="records"))
        guard += 1
        if not page or guard > 6:
            break
    return rows


out = {}
for code in ["US.XLK", "US.SPY"]:
    day = fetch(code, KLType.K_DAY, "2024-01-01")
    mon = fetch(code, KLType.K_MON, "2024-01-01")
    if not day or not mon:
        out[code] = {"ok": False}
        continue
    by = {}
    for r in day:
        ym = r["time_key"][:7]
        by.setdefault(ym, []).append(r)
    rows = []
    for m in mon:
        ym = m["time_key"][:7]
        ds = by.get(ym)
        if not ds or not m.get("turnover_rate"):
            continue
        sum_tr = sum(x["turnover_rate"] for x in ds if x.get("turnover_rate"))
        sum_vol = sum(x["volume"] for x in ds if x.get("volume"))
        u_end = (ds[-1]["volume"] / ds[-1]["turnover_rate"]
                 if ds[-1].get("turnover_rate") else None)
        h2_tr = sum_vol / u_end if u_end else None
        rows.append({
            "ym": ym, "mon_tr": m["turnover_rate"],
            "H1_sum_daily_tr": round(sum_tr, 6),
            "H1_err_pct": round((sum_tr / m["turnover_rate"] - 1) * 100, 4),
            "H2_vol_over_uend": round(h2_tr, 6) if h2_tr else None,
            "H2_err_pct": (round((h2_tr / m["turnover_rate"] - 1) * 100, 4)
                           if h2_tr else None),
        })
    h1 = sorted(abs(r["H1_err_pct"]) for r in rows)
    h2 = sorted(abs(r["H2_err_pct"]) for r in rows if r["H2_err_pct"] is not None)
    out[code] = {
        "ok": True, "n_months": len(rows),
        "H1_abs_err_pct": {"p50": h1[len(h1) // 2], "p90": h1[len(h1) * 9 // 10], "max": h1[-1]},
        "H2_abs_err_pct": {"p50": h2[len(h2) // 2], "p90": h2[len(h2) * 9 // 10], "max": h2[-1]},
        "rows": rows,
    }

safe_close(ctx)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("WROTE", OUT)
for k, v in out.items():
    if v.get("ok"):
        print(k, "H1", v["H1_abs_err_pct"], "H2", v["H2_abs_err_pct"])
