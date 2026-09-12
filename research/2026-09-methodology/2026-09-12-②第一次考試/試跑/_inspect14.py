# -*- coding: utf-8 -*-
"""Read-only: print every guidance/outlook context in selected EX-99.1 texts."""
import gzip, re
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
CACHE = ROOT / "A" / "edgar_cache"
NOUN = re.compile(r"(?i)\b(guidance|outlook)\b")

ACC = {
    "E073 Q+1": "0001654954-25-000292",
    "E073 Q+2": "0001654954-25-004020",
    "E065 Q+1": "0000021076-23-000013",
    "E057 Q+1": "0001193125-22-276092",
    "E009 Q+1": "0000893538-16-000214",
}
for k, acc in ACC.items():
    txt = gzip.open(CACHE / (acc.replace("-", "") + "__EX991.txt.gz"), "rt", encoding="utf-8").read()
    print("=====", k, acc, "chars", len(txt))
    for m in NOUN.finditer(txt):
        print("   ...", re.sub(r"\s+", " ", txt[max(0, m.start() - 150): m.end() + 150]).strip())
