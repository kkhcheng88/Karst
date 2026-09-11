# -*- coding: utf-8 -*-
"""KARST-213 批 2:印出五宗事件的標題與敘述(不含任何結果欄)。

用法:python 看事件.py [E??]
"""
import json
import sys

B2 = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①v3全量回測/批2"
IDS = ["E05", "E06", "E07", "E10", "E11"]


def main():
    ids = [sys.argv[1]] if len(sys.argv) > 1 else IDS
    for eid in ids:
        p = json.load(open("%s/packets/%s.json" % (B2, eid), encoding="utf-8"))
        print("==", eid, p.get("name"))
        print("  shock", p.get("shock_start"), "->", p.get("news_shock_end"),
              "| basket", p.get("basket_kind"), "| n", len(p["companies"]),
              "| disc", p["discount"].get("discount_rate"), p["discount"].get("source"))
        print("  narrative:", p.get("narrative"))
        print("  tickers:", ",".join(c["ticker"] for c in p["companies"]))


if __name__ == "__main__":
    main()
