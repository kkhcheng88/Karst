# -*- coding: utf-8 -*-
"""Read-only: E073 field boundary detail."""
import csv
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
line = (ROOT / "試跑" / "ds" / "rows" / "E073.csv").read_text(encoding="utf-8").splitlines()[1]
f = next(csv.reader([line]))
for i in [4, 5, 17, 18, 23, 24, 25, 26]:
    print(i, "|", f[i][:400])
    print("   ...tail:", f[i][-200:])
