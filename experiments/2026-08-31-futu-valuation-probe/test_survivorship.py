#!/usr/bin/env python3
"""A-022 verification: is Futu's plate_value history computed on the composition
that was actually in the industry on each past day, or recomputed with today's
surviving members?

Three probes, cheapest first:

  probe 1  Can a delisted ticker (SVB / Signature / First Republic / SunEdison)
           still be resolved and can its valuation history be pulled?  If Futu
           keeps them, then-composition is at least *possible*; if the codes do
           not resolve at all, retroactive-with-today's-members is more likely.

  probe 2  Structural check on a surviving Banks - Regional name: pull a long
           PE history and look at plate_value across the March 2023 regional
           bank failures for a discontinuity (level jump / variance break).

  probe 3  Calibration: for one plate, reconstruct the aggregation from TODAY's
           members (where composition is known) and see which formula reproduces
           today's plate_value.  Whatever formula wins is then applied to a past
           date; if today's members reproduce the PAST plate_value too, the
           series was recomputed with today's composition (assumption collapses).

Read-only quote calls, paced under the 30 req / 30 s limit.
Usage: python test_survivorship.py
"""
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.expanduser("~"), ".claude", "skills", "futuapi", "scripts")))

from common import create_quote_context, RET_OK  # noqa: E402

PACE = 1.1
OUT = {}

# Codes that were delisted / wiped out, with the month they vanished.
DELISTED = [
    ("US.SIVB", "SVB Financial", "2023-03"),
    ("US.SBNY", "Signature Bank", "2023-03"),
    ("US.FRC", "First Republic Bank", "2023-05"),
    ("US.SUNE", "SunEdison", "2016-04"),
    ("US.SUNEQ", "SunEdison (post-BK)", "2016-04"),
    ("US.LEH", "Lehman Brothers", "2008-09"),
    ("US.SIVBQ", "SVB Financial (post-BK)", "2023-03"),
]


def pace(t0):
    time.sleep(max(0.0, PACE - (time.time() - t0)))


def probe1(ctx):
    print("\n=== probe 1: can delisted codes be resolved / pulled? ===")
    rows = []
    for code, name, gone in DELISTED:
        rec = {"code": code, "name": name, "delisted": gone}
        t0 = time.time()
        ret, data = ctx.get_stock_basicinfo("US", "STOCK", [code])
        rec["basicinfo_ok"] = (ret == RET_OK and data is not None
                               and getattr(data, "shape", [0])[0] > 0)
        rec["basicinfo_msg"] = ("" if rec["basicinfo_ok"] else str(data)[:120])
        pace(t0)

        t0 = time.time()
        ret, vd = ctx.get_valuation_detail(code, valuation_type=1, interval_type=10)
        if ret != RET_OK:
            rec["valuation_ok"] = False
            rec["valuation_msg"] = str(vd)[:120]
        else:
            h = ((vd or {}).get("trend", {}) or {}).get("historical_items", []) or []
            rec["valuation_ok"] = len(h) > 0
            rec["hist_points"] = len(h)
            if h:
                rec["hist_first"] = h[0]["time_str"]
                rec["hist_last"] = h[-1]["time_str"]
                rec["has_plate_value"] = "plate_value" in h[0]
        pace(t0)

        print("  %-10s basicinfo=%-5s valuation=%-5s %s" % (
            code, rec["basicinfo_ok"], rec.get("valuation_ok"),
            rec.get("hist_last", rec.get("valuation_msg", ""))[:70]))
        rows.append(rec)
    OUT["probe1_delisted"] = rows
    return rows


def probe2(ctx, plate="US.LIST2456", anchor="2023-03"):
    """Long plate_value history for Banks - Regional via a surviving member."""
    print("\n=== probe 2: plate_value structure around %s (%s) ===" % (anchor, plate))
    t0 = time.time()
    ret, data = ctx.get_valuation_plate_stock_list(
        plate, valuation_type=1, num=50, sort_id=51, sort_type=1)
    pace(t0)
    if ret != RET_OK:
        print("  plate list failed:", data)
        return
    members = [(r["symbol"], r["name"]) for r in (data.get("stock_list") or [])]
    print("  plate count=%s, first-page members=%d" % (data.get("count"), len(members)))
    OUT["probe2_members_page1"] = members

    picked = None
    for sym, nm in members:
        t0 = time.time()
        ret, vd = ctx.get_valuation_detail(sym, valuation_type=1, interval_type=10)
        pace(t0)
        if ret != RET_OK:
            continue
        h = ((vd or {}).get("trend", {}) or {}).get("historical_items", []) or []
        if h and h[0]["time_str"] < "2020-01-01":
            picked = (sym, nm, h)
            break
    if not picked:
        print("  no member with deep history found")
        return
    sym, nm, h = picked
    print("  using %s (%s): %d pts %s -> %s" % (
        sym, nm, len(h), h[0]["time_str"], h[-1]["time_str"]))

    series = [(x["time_str"], x.get("plate_value")) for x in h
              if x.get("plate_value") is not None]
    OUT["probe2_carrier"] = {"symbol": sym, "name": nm, "points": len(series),
                             "first": series[0][0], "last": series[-1][0]}
    OUT["probe2_plate_value"] = series

    # day-over-day jumps, ranked
    jumps = []
    for i in range(1, len(series)):
        d0, v0 = series[i - 1]
        d1, v1 = series[i]
        if v0:
            jumps.append((abs(v1 - v0) / abs(v0), d0, d1, v0, v1))
    jumps.sort(reverse=True)
    print("  10 largest single-day plate_value moves:")
    for pct, d0, d1, v0, v1 in jumps[:10]:
        print("    %s -> %s  %8.3f -> %8.3f  (%.1f%%)" % (d0, d1, v0, v1, pct * 100))
    OUT["probe2_top_jumps"] = [
        {"from": d0, "to": d1, "v0": v0, "v1": v1, "pct": pct}
        for pct, d0, d1, v0, v1 in jumps[:20]]

    # window around the failures
    win = [(d, v) for d, v in series if "2023-02-20" <= d <= "2023-05-20"]
    print("  plate_value 2023-02-20..2023-05-20: %d pts" % len(win))
    for d, v in win[::5]:
        print("    %s  %8.3f" % (d, v))
    OUT["probe2_window_2023"] = win


def probe3(ctx, plate, past_date):
    """Reconstruct today's-members aggregate and compare with past plate_value."""
    print("\n=== probe 3: calibrate aggregation on %s ===" % plate)
    t0 = time.time()
    ret, data = ctx.get_valuation_plate_stock_list(
        plate, valuation_type=1, num=50, sort_id=51, sort_type=1)
    pace(t0)
    if ret != RET_OK:
        print("  plate list failed:", data)
        return
    rows = data.get("stock_list") or []
    print("  plate count=%s members pulled=%d" % (data.get("count"), len(rows)))

    hist = {}
    plate_series = None
    for r in rows:
        sym = r["symbol"]
        t0 = time.time()
        ret, vd = ctx.get_valuation_detail(sym, valuation_type=1, interval_type=10)
        pace(t0)
        if ret != RET_OK:
            continue
        h = ((vd or {}).get("trend", {}) or {}).get("historical_items", []) or []
        if not h:
            continue
        hist[sym] = {x["time_str"]: x["value"] for x in h}
        if plate_series is None or len(h) > len(plate_series):
            plate_series = {x["time_str"]: x.get("plate_value") for x in h}

    if not plate_series:
        print("  no series")
        return

    def agg_report(day, label):
        vals = [hist[s][day] for s in hist if day in hist[s]]
        pv = plate_series.get(day)
        if not vals or pv is None:
            print("  %s %s: no data (members=%d, plate_value=%s)" % (
                label, day, len(vals), pv))
            return None
        pos = [v for v in vals if v and v > 0]
        rep = {
            "date": day,
            "plate_value": pv,
            "members_with_data": len(vals),
            "mean_all": statistics.fmean(vals),
            "median_all": statistics.median(vals),
            "mean_positive": statistics.fmean(pos) if pos else None,
            "median_positive": statistics.median(pos) if pos else None,
        }
        print("  %s %s  plate_value=%.3f | members=%d mean=%.3f median=%.3f "
              "mean+=%.3f median+=%.3f" % (
                  label, day, pv, len(vals), rep["mean_all"], rep["median_all"],
                  rep["mean_positive"] or float("nan"),
                  rep["median_positive"] or float("nan")))
        return rep

    today = max(plate_series)
    rep_now = agg_report(today, "TODAY")
    rep_past = None
    for cand in sorted(plate_series):
        if cand >= past_date:
            rep_past = agg_report(cand, "PAST ")
            break
    OUT["probe3"] = {"plate": plate, "today": rep_now, "past": rep_past,
                     "members": list(hist.keys())}


def main():
    ctx = create_quote_context()
    try:
        probe1(ctx)
        probe2(ctx)
        probe3(ctx, "US.LIST2075", "2023-03-01")
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        with open("survivorship_probe.json", "w", encoding="utf-8") as f:
            json.dump(OUT, f, ensure_ascii=False, indent=1)
        print("\nwritten: survivorship_probe.json")


if __name__ == "__main__":
    main()
