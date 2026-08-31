#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF 申贖流後門 —— 第三輪:量化可用性

要答:
  1. 2025-12-05 XLK 隱含股數 +99% 係咪拆股假訊號(對 rehab 拆股表)
  2. 雜訊底 —— turnover_rate 服務端 5 位小數,反推股數嘅捨入誤差帶有幾闊(股數 / 美元)
  3. 訊噪比 —— 日頻 / 週頻 / 月頻 申贖流,幾多比例高於雜訊帶
  4. 平坦段 —— 有冇「零申贖日」落喺誤差帶內(真股數應該係階梯,唔係連續噪聲)

只讀行情,呼叫之間 1.1 秒。
"""
import sys
import os
import json
import time

sys.path.insert(0, r"C:\Users\Kaho\.claude\skills\futuapi\scripts")
from common import create_quote_context, safe_close  # noqa: E402
from futu import KLType, AuType, KL_FIELD  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "etf_flow_probe3.json")
PACE = 1.1
result = {}
ctx = create_quote_context()


def fetch(code, autype):
    rows = []
    page = None
    guard = 0
    while True:
        kw = dict(ktype=KLType.K_DAY, autype=autype,
                  fields=[KL_FIELD.DATE_TIME, KL_FIELD.CLOSE, KL_FIELD.TRADE_VOL,
                          KL_FIELD.TURNOVER_RATE],
                  max_count=1000)
        if page:
            kw["page_req_key"] = page
        ret, df, page = ctx.request_history_kline(code, start="2015-01-01",
                                                  end="2026-08-31", **kw)
        time.sleep(PACE)
        if ret != 0:
            return None, str(df)[:300]
        rows += json.loads(df.to_json(orient="records"))
        guard += 1
        if not page or guard > 12:
            break
    return rows, None


# ---- 1. 拆股表 ----
ret, reh = ctx.get_rehab("US.XLK")
time.sleep(PACE)
splits = []
if ret == 0:
    for r in json.loads(reh.to_json(orient="records")):
        if r.get("split_ratio") or r.get("stk_spo_ratio") or r.get("per_share_trans_ratio"):
            splits.append({k: r[k] for k in
                           ("ex_div_date", "split_ratio", "stk_spo_ratio",
                            "per_share_trans_ratio", "per_cash_div") if k in r})
result["xlk_rehab_split_like"] = splits[-10:]

# ---- 主分析 ----
per = {}
for code in ["US.XLK", "US.SPY"]:
    rows_none, err1 = fetch(code, AuType.NONE)
    rows_qfq, err2 = fetch(code, AuType.QFQ)
    if rows_none is None:
        per[code] = {"ok": False, "err": err1}
        continue

    def implied(rows):
        out = {}
        for r in rows:
            tr, vol = r.get("turnover_rate"), r.get("volume")
            if tr and vol:
                out[r["time_key"][:10]] = (vol / tr, tr, vol, r.get("close"))
        return out

    a = implied(rows_none)
    b = implied(rows_qfq) if rows_qfq else {}
    dates = sorted(a)

    e = {"ok": True, "n": len(dates), "range": [dates[0], dates[-1]]}

    # 1b. 2025-12-05 前後
    win = [d for d in dates if "2025-11-28" <= d <= "2025-12-12"]
    e["window_2025_12"] = [
        {"d": d, "units_none": round(a[d][0]),
         "units_qfq": round(b[d][0]) if d in b else None,
         "tr": a[d][1], "vol": a[d][2], "close_none": a[d][3],
         "close_qfq": b[d][3] if d in b else None}
        for d in win]

    # 2. 雜訊底:捨入半寬 0.5e-5 / tr -> 相對誤差
    bands = []
    for d in dates:
        u, tr, vol, c = a[d]
        rel = (0.5e-5 / tr)          # 股數相對誤差半寬
        bands.append((d, rel, rel * u, rel * u * (c or 0)))
    bands_sorted = sorted(x[1] for x in bands)
    n = len(bands_sorted)
    e["noise_rel_halfwidth_pct"] = {
        "p10": round(bands_sorted[n // 10] * 100, 5),
        "p50": round(bands_sorted[n // 2] * 100, 5),
        "p90": round(bands_sorted[n * 9 // 10] * 100, 5),
    }
    usd_sorted = sorted(x[3] for x in bands)
    e["noise_usd_halfwidth"] = {
        "p10": round(usd_sorted[n // 10]),
        "p50": round(usd_sorted[n // 2]),
        "p90": round(usd_sorted[n * 9 // 10]),
    }

    # 3. 訊噪比:日 / 週(5交易日) / 月(21交易日)
    def snr(step):
        hit = tot = 0
        mags = []
        for i in range(step, len(dates)):
            d0, d1 = dates[i - step], dates[i]
            u0, tr0, _, _ = a[d0]
            u1, tr1, _, c1 = a[d1]
            band = (0.5e-5 / tr0) * u0 + (0.5e-5 / tr1) * u1   # 合成誤差帶(保守:相加)
            chg = abs(u1 - u0)
            tot += 1
            if chg > band:
                hit += 1
            mags.append((chg, band))
        med_chg = sorted(m[0] for m in mags)[len(mags) // 2]
        med_band = sorted(m[1] for m in mags)[len(mags) // 2]
        return {"n": tot, "above_noise_pct": round(hit / tot * 100, 1),
                "median_abs_change_units": round(med_chg),
                "median_noise_band_units": round(med_band),
                "median_snr": round(med_chg / med_band, 2)}

    e["snr_daily"] = snr(1)
    e["snr_weekly"] = snr(5)
    e["snr_monthly"] = snr(21)
    e["snr_quarterly"] = snr(63)

    per[code] = e

result["per_code"] = per
safe_close(ctx)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print("WROTE", OUT)
