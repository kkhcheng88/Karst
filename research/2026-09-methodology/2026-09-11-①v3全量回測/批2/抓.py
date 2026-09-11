# -*- coding: utf-8 -*-
"""KARST-213 批 2:按自訂正則抽上下文(只讀衝擊前文件,不含任何結果)。

用法:python 抓.py <E??> <TICKER> "<regex>" [窗寬=300] [每個檔最多=3]
"""
import json
import os
import re
import sys

B2 = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①v3全量回測/批2"


def main():
    eid, tk, pat = sys.argv[1], sys.argv[2], sys.argv[3]
    win = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    cap = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    spec = json.load(open("%s/docs/%s_%s_docs.json" % (B2, eid, tk), encoding="utf-8"))
    print("=== %s %s cutoff=%s re=%s" % (eid, tk, spec["cutoff"], pat))
    rx = re.compile(pat)
    for d in spec["docs"]:
        if not d.get("path") or not os.path.exists(d["path"]):
            continue
        text = open(d["path"], encoding="utf-8", errors="ignore").read()
        print("-- %s %s" % (d["form"], d.get("filingDate")))
        n = 0
        for m in rx.finditer(text):
            a = max(0, m.start() - win // 3)
            b = min(len(text), m.start() + win)
            print("   %s" % re.sub(r"\s+", " ", text[a:b]).strip())
            n += 1
            if n >= cap:
                break
        if n == 0:
            print("   (無命中)")


if __name__ == "__main__":
    main()
