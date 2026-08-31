#!/usr/bin/env python3
"""A-022 verification, round 2.

Round 1 raised two problems that have to be settled before any verdict:

  (a) the Banks - Regional carrier (US.MFG) showed plate_value around 0.5-2.9,
      which is not a believable industry P/E — so first confirm which plate the
      carrier is actually attached to, and whether a second member of the same
      plate carries the identical series.

  (b) the aggregation formula behind plate_value was never identified, so the
      "today's members reproduce the past value" test could not be scored.
      Identify it on TODAY's data, where composition is known exactly, by
      testing simple mean / median / cap-weighted mean / aggregate
      (sum market cap / sum earnings) against the observed plate_value.

Then the decisive read: does plate_value show a break at the known failure
dates (SVB 2023-03-10, Signature 2023-03-12, First Republic 2023-05-01)?

Read-only quote calls, paced under 30 req / 30 s.
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


def pace(t0):
    time.sleep(max(0.0, PACE - (time.time() - t0)))


def vdetail(ctx, sym, interval=10):
    t0 = time.time()
    ret, vd = ctx.get_valuation_detail(sym, valuation_type=1, interval_type=interval)
    pace(t0)
    if ret != RET_OK:
        return None
    return vd


def probe4_carrier_identity(ctx, syms):
    """Which plate is each carrier attached to, and is plate_value shared?"""
    print("\n=== probe 4: carrier plate identity + shared-series check ===")
    got = {}
    for sym in syms:
        vd = vdetail(ctx, sym)
        if not vd:
            print("  %-10s no data" % sym)
            continue
        pd_ = vd.get("plate_distribution") or {}
        h = ((vd.get("trend") or {}).get("historical_items") or [])
        got[sym] = {
            "plate": pd_.get("plate"),
            "plate_name": pd_.get("plate_name"),
            "plate_average_value": pd_.get("plate_average_value"),
            "plate_stock_item_count": pd_.get("plate_stock_item_count"),
            "own_pe": (vd.get("trend") or {}).get("current_value"),
            "series": {x["time_str"]: x.get("plate_value") for x in h},
            "first": h[0]["time_str"] if h else None,
            "last": h[-1]["time_str"] if h else None,
            "points": len(h),
        }
        g = got[sym]
        print("  %-10s plate=%s %s  plate_avg=%s  members=%s  own_pe=%s  pts=%d %s..%s" % (
            sym, g["plate"], g["plate_name"], g["plate_average_value"],
            g["plate_stock_item_count"], g["own_pe"], g["points"],
            g["first"], g["last"]))

    syms_ok = [s for s in got if got[s]["series"]]
    for i in range(len(syms_ok)):
        for j in range(i + 1, len(syms_ok)):
            a, b = syms_ok[i], syms_ok[j]
            if got[a]["plate"] != got[b]["plate"]:
                continue
            common = sorted(set(got[a]["series"]) & set(got[b]["series"]))
            mism = [d for d in common
                    if got[a]["series"][d] != got[b]["series"][d]]
            print("  shared-series %s vs %s (plate %s): common=%d mismatches=%d"
                  % (a, b, got[a]["plate"], len(common), len(mism)))
            if mism[:3]:
                print("     e.g.", [(d, got[a]['series'][d], got[b]['series'][d])
                                    for d in mism[:3]])
    OUT["probe4"] = {s: {k: v for k, v in g.items() if k != "series"}
                     for s, g in got.items()}
    return got


def probe5_formula(ctx, plate):
    """Identify the aggregation formula on TODAY's composition."""
    print("\n=== probe 5: identify aggregation formula on %s ===" % plate)
    t0 = time.time()
    ret, data = ctx.get_valuation_plate_stock_list(
        plate, valuation_type=1, num=50, sort_id=51, sort_type=1)
    pace(t0)
    if ret != RET_OK:
        print("  failed:", data)
        return
    rows = data.get("stock_list") or []
    print("  count=%s members=%d" % (data.get("count"), len(rows)))

    pv = None
    for r in rows:
        vd = vdetail(ctx, r["symbol"], interval=1)
        if vd:
            pd_ = vd.get("plate_distribution") or {}
            pv = pd_.get("plate_average_value")
            print("  observed plate_average_value = %s (via %s)" % (pv, r["symbol"]))
            break
    if pv is None:
        print("  could not read plate_average_value")
        return

    vals = [(r["symbol"], r.get("valuation_val"), r.get("market_cap"))
            for r in rows if r.get("valuation_val") is not None]
    pe = [v for _, v, _ in vals]
    pos = [(s, v, c) for s, v, c in vals if v and v > 0]

    cands = {}
    cands["mean_all"] = statistics.fmean(pe)
    cands["median_all"] = statistics.median(pe)
    if pos:
        cands["mean_positive"] = statistics.fmean([v for _, v, _ in pos])
        cands["median_positive"] = statistics.median([v for _, v, _ in pos])
        capsum = sum(c for _, _, c in pos if c)
        if capsum:
            cands["capw_mean_positive"] = sum(
                v * c for _, v, c in pos if c) / capsum
            earn = sum((c / v) for _, v, c in pos if c and v)
            if earn:
                cands["aggregate_positive"] = capsum / earn
    capsum_all = sum(c for _, _, c in vals if c)
    earn_all = sum((c / v) for _, v, c in vals if c and v)
    if capsum_all and earn_all:
        cands["aggregate_all"] = capsum_all / earn_all

    print("  candidate aggregations vs observed %.4f:" % pv)
    best = None
    for k, v in sorted(cands.items()):
        err = abs(v - pv) / abs(pv) * 100 if pv else float("inf")
        print("    %-22s %12.4f   err=%8.2f%%" % (k, v, err))
        if best is None or err < best[1]:
            best = (k, err, v)
    print("  -> closest: %s (err %.2f%%)" % (best[0], best[1]))
    OUT["probe5"] = {"plate": plate, "observed": pv, "candidates": cands,
                     "closest": best[0], "closest_err_pct": best[1],
                     "members": len(vals)}


def probe6_break(ctx, carrier, events):
    """Look for a level break in plate_value at known failure dates."""
    print("\n=== probe 6: plate_value break test on carrier %s ===" % carrier)
    vd = vdetail(ctx, carrier)
    if not vd:
        print("  no data")
        return
    h = ((vd.get("trend") or {}).get("historical_items") or [])
    ser = [(x["time_str"], x.get("plate_value")) for x in h
           if x.get("plate_value") is not None]
    idx = {d: i for i, (d, _) in enumerate(ser)}
    print("  series %d pts %s..%s" % (len(ser), ser[0][0], ser[-1][0]))
    OUT["probe6_series_len"] = len(ser)
    res = []
    for label, day in events:
        near = [d for d, _ in ser if d >= day]
        if not near:
            continue
        d0 = near[0]
        i = idx[d0]
        lo, hi = max(0, i - 10), min(len(ser), i + 11)
        window = ser[lo:hi]
        before = [v for _, v in ser[max(0, i - 20):i] if v]
        after = [v for _, v in ser[i:i + 20] if v]
        rec = {
            "event": label, "event_date": day, "anchor": d0,
            "mean_20d_before": statistics.fmean(before) if before else None,
            "mean_20d_after": statistics.fmean(after) if after else None,
        }
        if rec["mean_20d_before"] and rec["mean_20d_after"]:
            rec["shift_pct"] = (rec["mean_20d_after"] / rec["mean_20d_before"] - 1) * 100
        print("  %-22s %s: 20d before=%.3f  20d after=%.3f  shift=%s" % (
            label, day, rec["mean_20d_before"] or float("nan"),
            rec["mean_20d_after"] or float("nan"),
            ("%.1f%%" % rec["shift_pct"]) if rec.get("shift_pct") is not None else "-"))
        print("     window:", ", ".join("%s=%.3f" % (d, v) for d, v in window if v))
        res.append(rec)
    OUT["probe6"] = res


def main():
    ctx = create_quote_context()
    try:
        got = probe4_carrier_identity(
            ctx, ["US.MFG", "US.FITB", "US.RF", "US.KEY", "US.AAPL"])
        probe5_formula(ctx, "US.LIST2075")
        carrier = "US.FITB" if "US.FITB" in got else "US.MFG"
        probe6_break(ctx, carrier, [
            ("SVB failure", "2023-03-10"),
            ("Signature failure", "2023-03-12"),
            ("First Republic seized", "2023-05-01"),
        ])
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        with open("survivorship_probe2.json", "w", encoding="utf-8") as f:
            json.dump(OUT, f, ensure_ascii=False, indent=1)
        print("\nwritten: survivorship_probe2.json")


if __name__ == "__main__":
    main()
