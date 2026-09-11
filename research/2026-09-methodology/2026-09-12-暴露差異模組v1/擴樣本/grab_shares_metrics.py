# -*- coding: utf-8 -*-
"""KARST-220 擴樣本:抽每股指標(每股盈利、每股淨值),供沒有市值的家做估值一問。

市值取不到時,提示詞 §六 要求改以每股數值答;每股數值直接由申報正文取,
不靠外站、不靠記憶。用法:`python grab_shares_metrics.py E21`
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent / "docs"
PATS = [
    ("每股盈利", r"(basic|diluted) (statutory )?(earnings|profit) per (ordinary )?share[^.]{0,120}"),
    ("每股淨值", r"(net asset value|tangible net asset value|net book value) per (ordinary )?share[^.]{0,120}"),
    ("每股股息", r"(dividend|dividends) per (ordinary )?share[^.]{0,120}"),
    ("股數", r"(weighted average number of (ordinary )?shares|ordinary shares in issue|shares outstanding)[^.]{0,140}"),
    ("每股面值", r"ADS[s]?[^.]{0,90}(represent|equal)[^.]{0,90}"),
    ("每ADS盈虧", r"(loss|income) per ADS[^.]{0,140}"),
    ("每ADS淨值", r"(net asset|net tangible asset|book value)[^.]{0,40}per ADS[^.]{0,120}"),
    ("ADS數目", r"ADSs? (issued and )?outstanding[^.]{0,140}"),
    ("普通股數目", r"ordinary shares (issued and )?outstanding[^.]{0,140}"),
    ("股東權益", r"total (shareholders['’]?|members['’]? )?(equity|deficit)[^.]{0,120}"),
    ("ADS比率股", r"ADS[^.]{0,120}(represent|equals?)[^.]{0,120}(Class A )?(ordinary )?shares?"),
]


def main() -> None:
    ev = sys.argv[1]
    tickers = sys.argv[2:] or ["BCS", "LYG", "HSBC", "JPM"]
    for tk in tickers:
        print(f"\n{'=' * 74}\n## {ev} {tk}")
        for tag, pat in PATS:
            rx = re.compile(pat, re.I)
            n = 0
            for f in sorted(DOCS.glob(f"{ev}_{tk}_*.txt")):
                for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    m = rx.search(line)
                    if m and n < 2:
                        a = max(0, m.start() - 120)
                        print(f"  [{tag}] {f.name[:30]}:{i} ...{line[a:m.end() + 160]}...")
                        n += 1
            if n == 0:
                print(f"  [{tag}] 0 命中")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
