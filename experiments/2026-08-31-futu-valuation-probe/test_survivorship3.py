#!/usr/bin/env python3
"""A-022 verification, decisive round.

Round 2 established two things:
  * plate_value is one shared series per plate (4 carriers, 0 mismatches over
    4982-7462 common dates);
  * the aggregation is reproduced exactly (0.00% error) by
    aggregate_positive = sum(market cap) / sum(earnings) over members whose
    P/E is positive — negative-earnings members are excluded, and the result
    is therefore cap-weighted.

It also found step changes in Banks - Regional plate_value dated 2023-03-10
(SVB seized), 2023-04-25 (First Republic's Q1 deposit-flight disclosure) and
2023-05-02 (first session after First Republic was seized on 05-01).

The decisive question: can those steps be produced by the members that still
exist today?  Rebuild the same aggregate day by day from TODAY's surviving
members only.

  * If the surviving-only aggregate is smooth across those dates while the
    real plate_value steps, the step must come from members that are gone ->
    the series was computed with the composition of the day -> A-022 HOLDS.
  * If the surviving-only aggregate steps in the same places, the steps are an
    artefact of surviving members (earnings sign flips, TTM rolls) and the test
    cannot distinguish the two regimes -> verdict stays unverified.

Read-only quote calls, paced under 30 req / 30 s.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.expanduser("~"), ".claude", "skills", "futuapi", "scripts")))

from common import create_quote_context, RET_OK  # noqa: E402

PACE = 1.1
PLATE = "US.LIST2456"          # Banks - Regional
WINDOW = ("2023-02-15", "2023-06-15")
EVENTS = [("SVB seized", "2023-03-10"),
          ("Signature seized", "2023-03-12"),
          ("FRC Q1 disclosure", "2023-04-25"),
          ("FRC seized", "2023-05-01")]
OUT = {}


def pace(t0):
    time.sleep(max(0.0, PACE - (time.time() - t0)))


def main():
    ctx = create_quote_context()
    try:
        # 1. today's surviving members, biggest first (cap-weighted aggregate is
        #    dominated by them, so the first page is the part that matters)
        t0 = time.time()
        ret, data = ctx.get_valuation_plate_stock_list(
            PLATE, valuation_type=1, num=50, sort_id=51, sort_type=1)
        pace(t0)
        if ret != RET_OK:
            print("plate list failed:", data)
            return
        rows = data.get("stock_list") or []
        print("plate total members today = %s ; pulling top %d by market cap"
              % (data.get("count"), len(rows)))
        caps = {r["symbol"]: r.get("market_cap") for r in rows}

        # 2.每隻現存成員的日頻 PE 歷史 + 板塊共用序列
        pe_hist = {}
        plate_series = {}
        for n, r in enumerate(rows, 1):
            sym = r["symbol"]
            t0 = time.time()
            ret, vd = ctx.get_valuation_detail(sym, valuation_type=1, interval_type=10)
            pace(t0)
            if ret != RET_OK:
                continue
            h = ((vd or {}).get("trend") or {}).get("historical_items") or []
            if not h:
                continue
            pe_hist[sym] = {x["time_str"]: x["value"] for x in h}
            for x in h:
                if x.get("plate_value") is not None:
                    plate_series.setdefault(x["time_str"], x["plate_value"])
            if n % 15 == 0:
                print("  ...%d/%d pulled" % (n, len(rows)))
        print("members with history: %d ; plate_value days: %d"
              % (len(pe_hist), len(plate_series)))

        # 3. 在窗口內逐日重建「只用現存成員」的同一條公式
        #    aggregate_positive = sum(cap_i) / sum(cap_i / pe_i)  over pe_i > 0
        #    市值歷史攞唔到,用今日市值做固定權重 —— 對「有冇斷層」呢個問題足夠:
        #    固定權重下唔會憑空造出單日跳飛,除非成員自己嘅 PE 跳飛。
        days = sorted(d for d in plate_series if WINDOW[0] <= d <= WINDOW[1])
        recon = {}
        nmem = {}
        for d in days:
            num = 0.0
            den = 0.0
            k = 0
            for sym, series in pe_hist.items():
                v = series.get(d)
                c = caps.get(sym)
                if v and c and v > 0:
                    num += c
                    den += c / v
                    k += 1
            if den:
                recon[d] = num / den
                nmem[d] = k

        print("\nday        plate_value  surviving-only  members")
        prev_pv = prev_rc = None
        table = []
        for d in days:
            pv = plate_series[d]
            rc = recon.get(d)
            dpv = (pv / prev_pv - 1) * 100 if prev_pv else 0.0
            drc = (rc / prev_rc - 1) * 100 if (prev_rc and rc) else 0.0
            table.append({"date": d, "plate_value": pv, "surviving_only": rc,
                          "members": nmem.get(d), "d_plate_pct": dpv,
                          "d_surv_pct": drc})
            prev_pv, prev_rc = pv, rc

        # 只列出板塊序列單日變動 >5% 的日子,加上事件日前後
        flag = {t["date"] for t in table if abs(t["d_plate_pct"]) > 5}
        for _, ev in EVENTS:
            for t in table:
                if abs((days.index(t["date"]) if t["date"] in days else -99)
                       - (days.index(min([d for d in days if d >= ev],
                                         default=days[-1])))) <= 2:
                    flag.add(t["date"])
        for t in table:
            if t["date"] in flag:
                print("%s  %10.3f  %13s  %5s   dPV=%+7.2f%%  dSURV=%+7.2f%%" % (
                    t["date"], t["plate_value"],
                    ("%.3f" % t["surviving_only"]) if t["surviving_only"] else "-",
                    t["members"], t["d_plate_pct"], t["d_surv_pct"]))

        print("\n--- verdict inputs ---")
        for label, ev in EVENTS:
            after = [t for t in table if t["date"] >= ev]
            if not after:
                continue
            i = table.index(after[0])
            if i == 0:
                continue
            a, b = table[i - 1], table[i]
            print("%-20s %s -> %s : plate_value %+7.2f%% | surviving-only %+7.2f%%"
                  % (label, a["date"], b["date"], b["d_plate_pct"], b["d_surv_pct"]))

        OUT["plate"] = PLATE
        OUT["members_today"] = data.get("count")
        OUT["members_pulled"] = len(pe_hist)
        OUT["table"] = table
        OUT["events"] = EVENTS
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        with open("survivorship_probe3.json", "w", encoding="utf-8") as f:
            json.dump(OUT, f, ensure_ascii=False, indent=1)
        print("\nwritten: survivorship_probe3.json")


if __name__ == "__main__":
    main()
