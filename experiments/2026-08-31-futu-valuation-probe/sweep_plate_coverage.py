#!/usr/bin/env python3
"""Sweep every INDUSTRY plate of a market through get_valuation_plate_stock_list.

Answers: does the valuation endpoint actually cover the whole industry taxonomy,
how many constituents per plate, and how often forward_value is populated.

Rate limit is 30 requests / 30s for this endpoint (and 10/30s for plate-list),
so we pace at ~1.1s between calls and use a single quote context.

Usage:  python sweep_plate_coverage.py [MARKET] [OUT.json]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.expanduser("~"), ".claude", "skills", "futuapi", "scripts")))

from common import create_quote_context, RET_OK, Plate, Market  # noqa: E402

PACE = 1.1  # seconds between valuation calls -> ~27 req / 30s


def main(market_name="US", out_path="plate_coverage_US.json"):
    market = getattr(Market, market_name)
    ctx = create_quote_context()
    try:
        ret, plates = ctx.get_plate_list(market, Plate.INDUSTRY)
        if ret != RET_OK:
            print("plate_list failed:", plates)
            return
        codes = [(r["code"], r["plate_name"]) for _, r in plates.iterrows()]
        print("industry plates:", len(codes))

        results = []
        for n, (code, name) in enumerate(codes, 1):
            t0 = time.time()
            ret, data = ctx.get_valuation_plate_stock_list(
                code, valuation_type=1, num=50, sort_id=51, sort_type=1)
            if ret != RET_OK:
                results.append({"code": code, "name": name, "ok": False,
                                "error": str(data)})
            else:
                rows = (data or {}).get("stock_list", []) or []
                fwd = sum(1 for r in rows
                          if r.get("forward_value") not in (None, "", 0))
                results.append({
                    "code": code, "name": name, "ok": True,
                    "count": (data or {}).get("count"),
                    "page_rows": len(rows),
                    "rows_with_forward": fwd,
                    "next_key": (data or {}).get("next_key"),
                })
            if n % 20 == 0:
                print("  ...%d/%d" % (n, len(codes)))
            time.sleep(max(0.0, PACE - (time.time() - t0)))

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"market": market_name, "results": results}, f,
                      ensure_ascii=False, indent=1)

        ok = [r for r in results if r["ok"] and (r.get("count") or 0) > 0]
        empty = [r for r in results if r["ok"] and not (r.get("count") or 0)]
        failed = [r for r in results if not r["ok"]]
        tot_rows = sum(r["page_rows"] for r in ok)
        tot_fwd = sum(r["rows_with_forward"] for r in ok)
        print("plates with data : %d / %d" % (len(ok), len(results)))
        print("plates empty     : %d" % len(empty))
        print("plates errored   : %d" % len(failed))
        print("constituents seen: %d (first page, cap 50/plate)" % tot_rows)
        print("with forward_value: %d (%.1f%%)" % (
            tot_fwd, 100.0 * tot_fwd / tot_rows if tot_rows else 0))
        big = [r for r in ok if (r.get("count") or 0) > 50]
        print("plates over one page (>50 constituents): %d" % len(big))
        for r in failed[:5]:
            print("  FAIL", r["code"], r["name"], r["error"][:80])
        for r in empty[:5]:
            print("  EMPTY", r["code"], r["name"])
    finally:
        try:
            ctx.close()
        except Exception:
            pass


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "US"
    o = sys.argv[2] if len(sys.argv) > 2 else "plate_coverage_%s.json" % m
    main(m, o)
