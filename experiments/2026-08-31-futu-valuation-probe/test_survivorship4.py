#!/usr/bin/env python3
"""A-022 verification, closing round: a bound argument that does not depend on
knowing the exact aggregation formula.

plate_value is some ratio-of-sums over the plate's members.  For any such
aggregate — sum(cap)/sum(earnings), cap-weighted mean, plain mean, median —
the following bound holds on a single day where TTM earnings do not change:

    if every member's own valuation moves within [-a, +a] on that day,
    then any weighted average / ratio-of-sums of those members moves
    within [-a, +a] too.

So: measure every surviving member's own one-day P/E move on the four 2023
event dates.  If the worst surviving member moved far less than plate_value
did, the move cannot have come from surviving members at all — it must come
from members that are no longer in the plate, which means the historical
series was computed on the composition of that day.

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
PLATE = "US.LIST2456"
PAIRS = [("SVB seized", "2023-03-09", "2023-03-10"),
         ("post-Signature", "2023-03-16", "2023-03-17"),
         ("FRC Q1 disclosure", "2023-04-24", "2023-04-25"),
         ("FRC seized (next session)", "2023-05-01", "2023-05-02")]
OUT = {}


def pace(t0):
    time.sleep(max(0.0, PACE - (time.time() - t0)))


def main():
    ctx = create_quote_context()
    try:
        t0 = time.time()
        ret, data = ctx.get_valuation_plate_stock_list(
            PLATE, valuation_type=1, num=50, sort_id=51, sort_type=1)
        pace(t0)
        if ret != RET_OK:
            print("plate list failed:", data)
            return
        rows = data.get("stock_list") or []
        print("plate members today=%s, pulling top %d" % (data.get("count"), len(rows)))

        pe = {}
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
            pe[sym] = {x["time_str"]: x["value"] for x in h}
            for x in h:
                if x.get("plate_value") is not None:
                    plate_series.setdefault(x["time_str"], x["plate_value"])
            if n % 20 == 0:
                print("  ...%d/%d" % (n, len(rows)))
        print("members with history: %d" % len(pe))

        results = []
        for label, d0, d1 in PAIRS:
            pv0, pv1 = plate_series.get(d0), plate_series.get(d1)
            if not pv0 or not pv1:
                print("  %s: plate_value missing" % label)
                continue
            pv_move = (pv1 / pv0 - 1) * 100
            moves = []
            for sym, s in pe.items():
                a, b = s.get(d0), s.get(d1)
                if a and b and a > 0 and b > 0:
                    moves.append((abs(b / a - 1) * 100, sym, a, b))
            moves.sort(reverse=True)
            worst = moves[0] if moves else None
            n_gt = sum(1 for m in moves if m[0] > abs(pv_move))
            rec = {
                "event": label, "from": d0, "to": d1,
                "plate_value_from": pv0, "plate_value_to": pv1,
                "plate_move_pct": pv_move,
                "members_compared": len(moves),
                "worst_member_move_pct": worst[0] if worst else None,
                "worst_member": worst[1] if worst else None,
                "members_moving_more_than_plate": n_gt,
                "top5": [{"symbol": s, "move_pct": m, "from": a, "to": b}
                         for m, s, a, b in moves[:5]],
            }
            results.append(rec)
            print("\n%-26s %s -> %s" % (label, d0, d1))
            print("   plate_value        %8.3f -> %8.3f   (%+7.2f%%)" % (pv0, pv1, pv_move))
            print("   members compared   %d" % len(moves))
            print("   worst member move  %+7.2f%%  (%s)" % (
                worst[0] if worst else float("nan"), worst[1] if worst else "-"))
            print("   members moving more than plate_value: %d" % n_gt)
            for m, s, a, b in moves[:5]:
                print("      %-8s %8.3f -> %8.3f  (%+6.2f%%)" % (s, a, b, (b / a - 1) * 100))

        OUT["plate"] = PLATE
        OUT["members_today"] = data.get("count")
        OUT["members_pulled"] = len(pe)
        OUT["pairs"] = results
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        with open("survivorship_probe4.json", "w", encoding="utf-8") as f:
            json.dump(OUT, f, ensure_ascii=False, indent=1)
        print("\nwritten: survivorship_probe4.json")


if __name__ == "__main__":
    main()
