# -*- coding: utf-8 -*-
"""Read-only inspection helper (temporary)."""
import json
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")

for eid in ["E001", "E009"]:
    p = json.load(open(ROOT / "A2" / "packets" / (eid + ".json"), encoding="utf-8"))
    print("=== ", eid, " keys:", list(p.keys()))
    for k in list(p.keys()):
        v = p[k]
        s = json.dumps(v, ensure_ascii=False)
        print("---", k, "len", len(s))
        print(s[:900])
