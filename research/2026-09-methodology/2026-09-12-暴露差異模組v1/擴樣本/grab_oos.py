# -*- coding: utf-8 -*-
"""KARST-220 擴樣本:由 docs/ 的申報全文按關鍵詞抽段,供逐家判斷引用。

用法:`python grab_oos.py E21`
讀 `grab_oos_specs.json` 的同名鍵:{"E21": {"BCS": [{"tag":"英國收入","pat":"..."}, ...]}}
每家逐條掃 docs/E<id>_<ticker>_*.txt,印出命中次數與首 N 段 160 字上下文(含檔名與行號)。

**只讀不改**;原文不入庫。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "docs"
SPECS = HERE / "grab_oos_specs.json"
MAX_HITS = 3
CTX = 170


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("用法:python grab_oos.py E21")
    ev = sys.argv[1]
    prefix = ev.split("#")[0]      # 允許 `E21#2` 這種第二輪抽段鍵,檔案前綴仍用 E21
    specs = json.loads(SPECS.read_text(encoding="utf-8"))
    per = specs[ev]
    ev = prefix
    for ticker, pats in per.items():
        files = sorted(DOCS.glob(f"{ev}_{ticker}_*.txt"))
        print(f"\n{'=' * 78}\n## {ev} {ticker} —— {[f.name for f in files]}")
        for p in pats:
            pat = re.compile(p["pat"], re.I)
            tot, shown = 0, 0
            for f in files:
                for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    for m in pat.finditer(line):
                        tot += 1
                        if shown < MAX_HITS:
                            a = max(0, m.start() - CTX)
                            print(f"  [{p['tag']}] {f.name[:34]}:{i} ...{line[a:m.end() + CTX]}...")
                            shown += 1
            if tot == 0:
                print(f"  [{p['tag']}] 0 命中")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
