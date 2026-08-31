#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF 申贖流後門 —— 第四輪:用週/月 K 線提升精度

日 K 換手率約 0.014(XLK),服務端只留 5 位小數 => 相對精度 ~0.036%,雜訊蓋過中位數申贖。
月 K 換手率約 0.3 => 相對精度 ~0.0017%,理論上好一個數量級。

要證:
  A. 月 K 換手率 = 當月總成交量 ÷ 月底在外股數?
     驗法:月成交量(由日 K 加總)÷ 月 K 換手率,對比日 K 反推嘅月底股數
  B. 精度實際改善幾多
  C. 月頻申贖流訊噪比

只讀行情,呼叫之間 1.1 秒。
"""
import sys
import os
import json
import time

sys.path.insert(0, r"C:\Users\Kaho\.claude\skills\futuapi\scripts")
from common import create_quote_context, safe_close  # noqa: E402
from futu import KLType, AuType, KL_FIELD  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "etf_flow_probe4.json")
PACE = 1.1
FIELDS = [KL_FIELD.DATE_TIME, KL_FIELD.CLOSE, KL_FIELD.TRADE_VOL, KL_FIELD.TURNOVER_RATE]
result = {}
ctx = create_quote_context()


def fetch(code, ktype, start="2018-01-01"):
    rows, page, guard = [], None, 0
    while True:
        kw = dict(ktype=ktype, autype=AuType.QFQ, fields=FIELDS, max_count=1000)
        if page:
            kw["page_req_key"] = page
        ret, df, page = ctx.request_history_kline(code, start=start,
                                                  end="2026-08-31", **kw)
        time.sleep(PACE)
        if ret != 0:
            return None, str(df)[:300]
        rows += json.loads(df.to_json(orient="records"))
        guard += 1
        if not page or guard > 10:
            break
    return rows, None


per = {}
for code in ["US.XLK", "US.SPY", "US.XLE"]:
    e = {}
    day, err = fetch(code, KLType.K_DAY)
    if day is None:
        per[code] = {"ok": False, "err": err}
        continue
    mon, err2 = fetch(code, KLType.K_MON)
    wk, err3 = fetch(code, KLType.K_WEEK)

    # 日 K 反推
    day_u = {}
    day_vol_by_month = {}
    for r in day:
        d = r["time_key"][:10]
        tr, vol = r.get("turnover_rate"), r.get("volume")
        if tr and vol:
            day_u[d] = vol / tr
        if vol:
            day_vol_by_month.setdefault(d[:7], 0)
            day_vol_by_month[d[:7]] += vol

    # 月 K 反推
    mon_rows = []
    for r in (mon or []):
        ym = r["time_key"][:7]
        tr, vol = r.get("turnover_rate"), r.get("volume")
        if not tr or not vol:
            continue
        implied_from_mon = vol / tr
        # 同月最後一個交易日嘅日 K 反推值
        same = sorted(d for d in day_u if d[:7] == ym)
        last_day_u = day_u[same[-1]] if same else None
        mon_rows.append({
            "ym": ym, "tr": tr, "vol_mon_kline": vol,
            "vol_sum_daily": day_vol_by_month.get(ym),
            "implied_units_mon": round(implied_from_mon),
            "implied_units_last_day": round(last_day_u) if last_day_u else None,
            "diff_pct": (round((implied_from_mon / last_day_u - 1) * 100, 4)
                         if last_day_u else None),
            "noise_halfwidth_pct": round(0.5e-5 / tr * 100, 5),
            "close": r.get("close"),
        })
    e["n_months"] = len(mon_rows)
    e["month_rows_recent"] = mon_rows[-18:]

    if mon_rows:
        diffs = sorted(abs(m["diff_pct"]) for m in mon_rows if m["diff_pct"] is not None)
        e["abs_diff_mon_vs_lastday_pct"] = {
            "p50": diffs[len(diffs) // 2], "p90": diffs[len(diffs) * 9 // 10],
            "max": diffs[-1]} if diffs else None
        nb = sorted(m["noise_halfwidth_pct"] for m in mon_rows)
        e["mon_noise_halfwidth_pct"] = {"p10": nb[len(nb) // 10],
                                        "p50": nb[len(nb) // 2],
                                        "p90": nb[len(nb) * 9 // 10]}
        # 月度申贖流訊噪比(用月 K 反推值)
        hit = tot = 0
        mags = []
        for i in range(1, len(mon_rows)):
            a, b = mon_rows[i - 1], mon_rows[i]
            chg = abs(b["implied_units_mon"] - a["implied_units_mon"])
            band = (a["noise_halfwidth_pct"] / 100 * a["implied_units_mon"]
                    + b["noise_halfwidth_pct"] / 100 * b["implied_units_mon"])
            tot += 1
            if chg > band:
                hit += 1
            mags.append((chg, band, b["close"]))
        med_chg = sorted(m[0] for m in mags)[len(mags) // 2]
        med_band = sorted(m[1] for m in mags)[len(mags) // 2]
        e["monthly_snr"] = {
            "n": tot, "above_noise_pct": round(hit / tot * 100, 1),
            "median_abs_flow_units": round(med_chg),
            "median_noise_band_units": round(med_band),
            "median_snr": round(med_chg / med_band, 2),
            "median_flow_usd": round(med_chg * (mon_rows[-1]["close"] or 0)),
            "median_noise_usd": round(med_band * (mon_rows[-1]["close"] or 0)),
        }

    # 週 K 噪聲帶
    if wk:
        wnb = sorted(0.5e-5 / r["turnover_rate"] * 100
                     for r in wk if r.get("turnover_rate"))
        if wnb:
            e["week_noise_halfwidth_pct"] = {"p10": round(wnb[len(wnb) // 10], 5),
                                             "p50": round(wnb[len(wnb) // 2], 5),
                                             "p90": round(wnb[len(wnb) * 9 // 10], 5)}
    per[code] = {"ok": True, **e}

result["per_code"] = per
safe_close(ctx)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print("WROTE", OUT)
