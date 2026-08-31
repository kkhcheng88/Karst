#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KARST-128 板塊輪動族第二考:ETF 申贖流反推(A-024 線)。

判準先寫死先 commit:experiments/2026-09-01-sector-flow-exam/判準.md
判準提交編號 6ef494c(2026-09-01T01:20:52+08:00),早於本腳本任何一次數據下載。

反推式(判準 §1.2):
    u(t) = 前復權月 K 成交量 ÷ 前復權月 K 換手率     （在外單位數）
必用前復權 AuType.QFQ(A-024 陷阱一:不復權會把拆股當成申購)。

同場做判準 §5.1 三項數據質素檢查:
  1. 反推最新一期單位數 vs get_market_snapshot 的 trust_outstanding_units
  2. get_rehab 拆股記錄,核對前復權序列在拆股日沒有假跳位
  3. 日 K 月底口徑抽查(近 24 個月),作口徑對照,不參與判定

只讀行情,呼叫之間 1.1 秒,不掂任何交易介面。
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, r"C:\Users\Kaho\.claude\skills\futuapi\scripts")
from common import create_quote_context, safe_close  # noqa: E402
from futu import KLType, AuType, KL_FIELD  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PACE = 1.1
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
CODES = [f"US.{s}" for s in SECTORS] + ["US.SPY"]
FIELDS = [KL_FIELD.DATE_TIME, KL_FIELD.CLOSE, KL_FIELD.TRADE_VOL, KL_FIELD.TURNOVER_RATE]
START = "1998-01-01"
END = "2026-08-31"
DAILY_START = "2024-09-01"

ctx = create_quote_context()


def kline(code, ktype, start):
    rows, page, guard = [], None, 0
    while True:
        kw = dict(ktype=ktype, autype=AuType.QFQ, fields=FIELDS, max_count=1000)
        if page:
            kw["page_req_key"] = page
        ret, df, page = ctx.request_history_kline(code, start=start, end=END, **kw)
        time.sleep(PACE)
        if ret != 0:
            print("ERR", code, ktype, str(df)[:200])
            return None
        rows += json.loads(df.to_json(orient="records"))
        guard += 1
        if not page or guard > 12:
            break
    return rows


def main():
    quota = None
    try:
        ret, q = ctx.get_history_kl_quota(get_detail=False)
        time.sleep(PACE)
        quota = str(q)[:300]
    except Exception as exc:  # noqa: BLE001
        quota = "ERR " + str(exc)[:200]
    print("quota:", quota)

    # ── 快照現值(抽查用)──────────────────────────────────────────
    snap = {}
    ret, sdf = ctx.get_market_snapshot(CODES)
    time.sleep(PACE)
    if ret == 0:
        for r in json.loads(sdf.to_json(orient="records")):
            snap[r["code"]] = {
                "trust_outstanding_units": r.get("trust_outstanding_units"),
                "trust_aum": r.get("trust_aum"),
                "trust_netAssetValue": r.get("trust_netAssetValue"),
                "last_price": r.get("last_price"),
                "update_time": r.get("update_time"),
            }
    else:
        print("SNAPSHOT ERR", str(sdf)[:200])

    monthly, rehab, daily_chk = {}, {}, {}
    for code in CODES:
        rows = kline(code, KLType.K_MON, START)
        if not rows:
            monthly[code] = None
            continue
        series = []
        for r in rows:
            tr, vol = r.get("turnover_rate"), r.get("volume")
            u = (vol / tr) if (tr and vol) else None
            series.append({
                "ym": r["time_key"][:7],
                "close": r.get("close"),
                "volume": vol,
                "turnover_rate": tr,
                "units": u,
            })
        monthly[code] = series
        first_u = next((s["ym"] for s in series if s["units"]), None)
        print(f"{code}: {len(series)} 月 K, 首個有效反推月 {first_u}, 尾 {series[-1]['ym']}")

        # 拆股記錄
        try:
            ret, rdf = ctx.get_rehab(code)
            time.sleep(PACE)
            if ret == 0:
                recs = json.loads(rdf.to_json(orient="records"))
                rehab[code] = [
                    {k: v for k, v in x.items()
                     if k in ("ex_div_date", "split_ratio", "join_ratio",
                              "per_cash_div", "forward_adj_factorA", "forward_adj_factorB")}
                    for x in recs
                    if (x.get("split_ratio") not in (None, 0, 1)
                        or x.get("join_ratio") not in (None, 0, 1))
                ]
            else:
                rehab[code] = {"err": str(rdf)[:200]}
        except Exception as exc:  # noqa: BLE001
            rehab[code] = {"err": str(exc)[:200]}

        # 日 K 月底口徑抽查(近 24 個月)
        drows = kline(code, KLType.K_DAY, DAILY_START)
        if drows:
            by = {}
            for r in drows:
                by.setdefault(r["time_key"][:7], []).append(r)
            chk = []
            for ym, ds in sorted(by.items()):
                last = ds[-1]
                if not last.get("turnover_rate") or not last.get("volume"):
                    continue
                u_end = last["volume"] / last["turnover_rate"]
                mon = next((s for s in series if s["ym"] == ym and s["units"]), None)
                if not mon:
                    continue
                chk.append({
                    "ym": ym,
                    "units_month_k": round(mon["units"]),
                    "units_daily_monthend": round(u_end),
                    "diff_pct": round((mon["units"] / u_end - 1) * 100, 4),
                })
            daily_chk[code] = chk

    out = {
        "ticket": "KARST-128",
        "criteria_commit": "6ef494cb1b179b80362d367eb2222e8b02facafa",
        "criteria_committed_at": "2026-09-01T01:20:52+08:00",
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "autype": "QFQ",
        "kl_quota": quota,
        "snapshot_now": snap,
        "rehab_splits": rehab,
        "daily_monthend_crosscheck": daily_chk,
    }
    with open(os.path.join(HERE, "flow_meta.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 原始序列落 CSV(純 ASCII 欄名,方便量度腳本讀)
    lines = ["code,ym,close,volume,turnover_rate,units"]
    for code, series in monthly.items():
        if not series:
            continue
        for s in series:
            lines.append(",".join([
                code, s["ym"],
                "" if s["close"] is None else f"{s['close']:.6f}",
                "" if s["volume"] is None else str(int(s["volume"])),
                "" if s["turnover_rate"] is None else f"{s['turnover_rate']:.8f}",
                "" if s["units"] is None else f"{s['units']:.2f}",
            ]))
    with open(os.path.join(HERE, "flow_units_monthly.csv"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    safe_close(ctx)
    print("WROTE flow_units_monthly.csv / flow_meta.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
