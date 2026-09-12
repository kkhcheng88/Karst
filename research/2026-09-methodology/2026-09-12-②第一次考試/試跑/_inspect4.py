# -*- coding: utf-8 -*-
"""Read-only: verify the 4 malformed ds rows restore to 27 columns."""
import csv, re
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
BAD = ["E033", "E041", "E065", "E073"]
THOU = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")

for eid in BAD:
    p = ROOT / "試跑" / "ds" / "rows" / (eid + ".csv")
    raw = p.read_text(encoding="utf-8").splitlines()
    line = raw[1]
    n = len(next(csv.reader([line])))
    fixed = THOU.sub("", line)
    f = next(csv.reader([fixed]))
    print(eid, "raw_n=", n, "after_thou_strip_n=", len(f))
    if len(f) > 27:
        f = f[:26] + [",".join(f[26:])]
    elif len(f) < 27:
        print("   SHORT:", len(f))
        print("   last field:", f[-1][:200])
    print("   persistence_overall=", f[9], "pred_g2=", f[10:16])
    print("   col23 head:", f[23][:120])
