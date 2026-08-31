#!/usr/bin/env python3
"""Probe helper: summarise a get_valuation_detail --json dump.

The skill scripts write futu SDK log lines around the JSON payload, so we
locate the first '{' and raw_decode from there.
"""
import json
import sys
from collections import Counter


def load(path):
    s = open(path, encoding="utf-8").read()
    i = s.index("{")
    obj, _ = json.JSONDecoder().raw_decode(s[i:])
    return obj


def gaps(items):
    from datetime import date
    ds = [date.fromisoformat(x["time_str"]) for x in items]
    return Counter((ds[k + 1] - ds[k]).days for k in range(len(ds) - 1))


def main(path):
    obj = load(path)
    d = obj.get("data", {})
    if not d:
        print(path, "-> EMPTY DATA")
        return
    t = d.get("trend", {}) or {}
    h = t.get("historical_items", []) or []
    print("== %s" % path)
    print("  valuation_type :", d.get("valuation_type"))
    print("  last_update    :", d.get("last_update_time_str"))
    print("  trend keys     :", list(t.keys()))
    print("  forward_value  :", t.get("forward_value"))
    print("  current/avg/pct:", t.get("current_value"), t.get("average_value"),
          t.get("valuation_percentile"))
    print("  hist points    :", len(h))
    if h:
        print("  hist range     :", h[0]["time_str"], "->", h[-1]["time_str"])
        print("  has plate_value:", "plate_value" in h[0])
        print("  day-gap counts :", gaps(h).most_common(6))
    md = d.get("market_distribution") or {}
    print("  market_dist    : total=%s ranking=%s avg=%s median=%s sections=%d" % (
        md.get("total"), md.get("ranking"), md.get("average_value"),
        md.get("median_value"), len(md.get("sections", []) or [])))
    pl = d.get("plate_distribution") or {}
    if pl:
        print("  plate          :", pl.get("plate"), pl.get("plate_name"),
              "avg=", pl.get("plate_average_value"),
              "rank=", pl.get("plate_ranking"), "/", pl.get("plate_stock_item_count"),
              "items=", len(pl.get("stock_items", []) or []))
    pg = d.get("profit_growth_rate") or {}
    if pg:
        print("  profit_growth  : keys=", list(pg.keys()),
              "periods=", len(pg.get("profit_data", []) or []))
        for row in (pg.get("profit_data", []) or [])[:4]:
            print("      ", row)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
