# -*- coding: utf-8 -*-
"""KARST-220 擴樣本:核對申報全文抓取完整度(28 家 × 年報 + 最近兩份季報)。"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

HERE = r"C:/projects/Karst/research/2026-09-methodology/2026-09-12-暴露差異模組v1/擴樣本"

WANT = ["年報", "季報0", "季報1"]


def main() -> None:
    d = json.load(open(f"{HERE}/out/docs_index_oos.json", encoding="utf-8"))
    g = defaultdict(list)
    for r in d:
        g[(r["event"], r["ticker"])].append(r)
    n_full = 0
    for k in sorted(g):
        rows = sorted(g[k], key=lambda r: WANT.index(r["tag"]) if r["tag"] in WANT else 9)
        have = [r["tag"] for r in rows]
        miss = [t for t in WANT if t not in have]
        if not miss:
            n_full += 1
        desc = " ".join(f"{r['tag']}:{r['form']}({r['filingDate']},{r['chars'] // 1000}k)" for r in rows)
        flag = ("  缺 " + ",".join(miss)) if miss else ""
        print(f"{k[0]} {k[1]:6s} {desc}{flag}")
    print(f"\n三家齊全:{n_full}/{len(g)} 家")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
