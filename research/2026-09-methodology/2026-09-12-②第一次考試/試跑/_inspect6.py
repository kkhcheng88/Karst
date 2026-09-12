# -*- coding: utf-8 -*-
"""Read-only: debug E073 split + population signal_q_end matching."""
import csv, json
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")

line = (ROOT / "試跑" / "ds" / "rows" / "E073.csv").read_text(encoding="utf-8").splitlines()[1]
f = next(csv.reader([line]))
print("E073 f[24] count ');' =", f[24].count(");"), "| count '）；' =", f[24].count("）；"))
i = f[24].find("損益表")
print(repr(f[24][i - 10:i + 12]))

pop = list(csv.DictReader(open(ROOT / "A2" / "population.csv", encoding="utf-8-sig")))
sub = [r for r in pop if r["cik"] == "0001295947" and r["reaction_date"] > "2015-02-05"]
for r in sub[:6]:
    print(repr(r["signal_q_end"]), r["reaction_date"], r["accessionNumber"], r["has_text"], r["fiscal_quarter"])
