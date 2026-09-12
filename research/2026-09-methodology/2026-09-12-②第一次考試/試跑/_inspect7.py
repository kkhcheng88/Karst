# -*- coding: utf-8 -*-
"""Read-only: debug index-page doc-type parsing + E073 split points."""
import csv, re, urllib.request
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")

line = (ROOT / "試跑" / "ds" / "rows" / "E073.csv").read_text(encoding="utf-8").splitlines()[1]
f = next(csv.reader([line]))
for m in re.finditer(r"\);", f[24]):
    print("E073 f24 ');' at", m.start(), "->", f[24][m.start() - 25:m.start() + 8])

url = "https://www.sec.gov/Archives/edgar/data/1295947/000129594715000013/0001295947-15-000013-index.html"
page = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Karst research kaho@example.com"}), timeout=30).read().decode("utf-8", "ignore")
print("page len", len(page), "| has EX-99.1:", page.count("EX-99.1"))
i = page.find("EX-99.1")
print(repr(page[i - 700:i + 300]))
