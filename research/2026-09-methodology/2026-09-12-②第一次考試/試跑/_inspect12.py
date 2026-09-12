# -*- coding: utf-8 -*-
"""Read-only: print guidance detail/snippets from the generated CSV."""
import csv
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
rows = list(csv.DictReader(open(ROOT / "試跑" / "結果對照.csv", encoding="utf-8")))
for r in rows:
    print("==", r["event_id"], r["ticker"], "| 指引:", r["guide_down"])
    print("   detail:", r["guide_detail"])
    if r["guide_snip"]:
        print("   snip:", r["guide_snip"][:500])
