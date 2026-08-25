"""量度「表達直觀度」的客觀部分:數兩邊策略核心與資料適配各佔多少行。

只數有效行(去掉空行與純註解行),範圍由原始碼裡的標記界定:
  STRATEGY-CORE / ADAPTER / SWEEP-CORE
"""

from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MARKERS = ["STRATEGY-CORE", "ADAPTER", "SWEEP-CORE"]
FILES = {"vectorbt": "vbt_bakeoff.py", "pybroker": "pb_bakeoff.py"}


def count_block(lines: list[str], marker: str) -> int:
    total, inside = 0, False
    for ln in lines:
        if re.search(rf"---\s*{marker}-BEGIN\s*---", ln):
            inside = True
            continue
        if re.search(rf"---\s*{marker}-END\s*---", ln):
            inside = False
            continue
        if not inside:
            continue
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        total += 1
    return total


def main() -> None:
    out = {}
    for engine, fname in FILES.items():
        with open(os.path.join(HERE, fname), encoding="utf-8") as f:
            lines = f.readlines()
        counts = {m: count_block(lines, m) for m in MARKERS}
        counts["total_file_effective"] = sum(
            1 for ln in lines if ln.strip() and not ln.strip().startswith("#")
        )
        out[engine] = counts
    print(json.dumps(out, ensure_ascii=False, indent=2))
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "linecounts.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
