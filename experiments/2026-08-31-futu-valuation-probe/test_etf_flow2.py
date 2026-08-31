#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF 申贖流 —— 後門路徑實測

發現:ETF 日 K 線帶 turnover_rate(換手率)。若 turnover_rate = volume / 在外股數,
      則 在外股數歷史 = volume / turnover_rate,即申贖流史。

要證三件事:
  A. 身分驗證 —— 最近一日反推出嚟嘅股數,同 snapshot 嘅 trust_outstanding_units 對唔對得上
  B. 分母係咪固定 —— 若反推序列長年不變,即富途用今日股數回溯,條路死
  C. 精度 —— turnover_rate 幾多位小數,反推股數嘅誤差帶有幾闊,擋唔擋得住真實申贖規模

只讀行情,呼叫之間 1.1 秒。
"""
import sys
import os
import json
import time
from collections import Counter

sys.path.insert(0, r"C:\Users\Kaho\.claude\skills\futuapi\scripts")
from common import create_quote_context, safe_close  # noqa: E402
from futu import KLType, AuType, KL_FIELD  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "etf_flow_probe2.json")
PACE = 1.1
result = {}

ctx = create_quote_context()

# 先睇歷史 K 線額度,免得食爆
try:
    ret, q = ctx.get_history_kl_quota(get_detail=False)
    time.sleep(PACE)
    result["kl_quota"] = str(q)[:500]
except Exception as e:
    result["kl_quota"] = "ERR " + str(e)[:200]

TARGETS = ["US.XLK", "US.SPY", "HK.02800"]

# 現值:snapshot 嘅在外股數
ret, snap = ctx.get_market_snapshot(TARGETS)
time.sleep(PACE)
cur = {}
if ret == 0:
    for r in json.loads(snap.to_json(orient="records")):
        cur[r["code"]] = {
            "trust_outstanding_units": r.get("trust_outstanding_units"),
            "trust_aum": r.get("trust_aum"),
            "trust_netAssetValue": r.get("trust_netAssetValue"),
            "last_price": r.get("last_price"),
        }
result["snapshot_now"] = cur

per = {}
for code in TARGETS:
    entry = {}
    try:
        ret, df, page = ctx.request_history_kline(
            code, start="2005-01-01", end="2026-08-31",
            ktype=KLType.K_DAY, autype=AuType.NONE,
            fields=[KL_FIELD.DATE_TIME, KL_FIELD.CLOSE, KL_FIELD.TRADE_VOL,
                    KL_FIELD.TRADE_VAL, KL_FIELD.TURNOVER_RATE],
            max_count=1000)
        time.sleep(PACE)
        if ret != 0:
            per[code] = {"ok": False, "err": str(df)[:300]}
            continue
        rows = json.loads(df.to_json(orient="records"))
        # 續頁
        guard = 0
        while page and guard < 12:
            ret2, df2, page = ctx.request_history_kline(
                code, start="2005-01-01", end="2026-08-31",
                ktype=KLType.K_DAY, autype=AuType.NONE,
                fields=[KL_FIELD.DATE_TIME, KL_FIELD.CLOSE, KL_FIELD.TRADE_VOL,
                        KL_FIELD.TRADE_VAL, KL_FIELD.TURNOVER_RATE],
                max_count=1000, page_req_key=page)
            time.sleep(PACE)
            if ret2 != 0:
                break
            rows += json.loads(df2.to_json(orient="records"))
            guard += 1

        entry["n_bars"] = len(rows)
        entry["range"] = [rows[0]["time_key"][:10], rows[-1]["time_key"][:10]] if rows else None

        # C. turnover_rate 小數位分佈
        dec = Counter()
        for r in rows:
            tr = r.get("turnover_rate")
            if tr is None:
                continue
            s = repr(float(tr))
            dec[len(s.split(".")[1]) if "." in s else 0] += 1
        entry["turnover_rate_decimals"] = dict(sorted(dec.items()))

        # 反推在外股數
        series = []
        for r in rows:
            tr, vol = r.get("turnover_rate"), r.get("volume")
            if not tr or not vol:
                continue
            series.append((r["time_key"][:10], vol / tr, r.get("close")))
        entry["n_implied"] = len(series)

        if series:
            # A. 最新一日 vs snapshot
            last_d, last_u, _ = series[-1]
            snap_u = cur.get(code, {}).get("trust_outstanding_units")
            entry["identity_check"] = {
                "last_bar_date": last_d,
                "implied_units": round(last_u),
                "snapshot_units": snap_u,
                "rel_err_pct": (round((last_u / snap_u - 1) * 100, 4)
                                if snap_u else None),
            }
            # B. 序列有冇變化
            us = [u for _, u, _ in series]
            entry["implied_stats"] = {
                "min": round(min(us)), "max": round(max(us)),
                "first": round(us[0]), "last": round(us[-1]),
                "max_over_min": round(max(us) / min(us), 4),
                "n_distinct_rounded_1e5": len({round(u / 1e5) for u in us}),
            }
            # 最近 40 日逐日
            entry["recent_40"] = [
                {"d": d, "units": round(u), "close": c} for d, u, c in series[-40:]
            ]
            # 最近 250 日:相鄰日股數變動(即申贖)
            deltas = []
            for i in range(max(1, len(series) - 250), len(series)):
                d0, u0, _ = series[i - 1]
                d1, u1, c1 = series[i]
                deltas.append({"d": d1, "d_units": round(u1 - u0),
                               "d_pct": round((u1 / u0 - 1) * 100, 4),
                               "usd": round((u1 - u0) * (c1 or 0))})
            deltas_sorted = sorted(deltas, key=lambda x: abs(x["d_units"]), reverse=True)
            entry["biggest_flow_days"] = deltas_sorted[:12]
            small = [abs(x["d_pct"]) for x in deltas]
            small.sort()
            entry["abs_dpct_percentiles"] = {
                "p10": round(small[len(small) // 10], 4),
                "p25": round(small[len(small) // 4], 4),
                "p50": round(small[len(small) // 2], 4),
                "p75": round(small[len(small) * 3 // 4], 4),
                "p90": round(small[len(small) * 9 // 10], 4),
            }
        per[code] = {"ok": True, **entry}
    except Exception as e:
        per[code] = {"ok": False, "err": str(e)[:400]}

result["per_code"] = per

safe_close(ctx)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print("WROTE", OUT)
