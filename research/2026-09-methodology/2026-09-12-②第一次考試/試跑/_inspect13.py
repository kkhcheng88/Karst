# -*- coding: utf-8 -*-
"""Read-only: measure verb-noun distance in each guidance text, print best snippets."""
import csv, gzip, re
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
CACHE = ROOT / "A" / "edgar_cache"

NOUN = re.compile(r"(?i)\b(guidance|outlook)\b")
VERB = re.compile(r"(?i)\b(lower(?:ed|s|ing)?|reduce[ds]?|reducing|cut|cuts)\b")

rows = list(csv.DictReader(open(ROOT / "試跑" / "結果對照.csv", encoding="utf-8")))
for r in rows:
    for m in re.finditer(r"(Q\+\d) (有下修|無|查不到)\(([\d-]+);", r["guide_detail"]):
        qk, verdict, acc = m.group(1), m.group(2), m.group(3)
        p = CACHE / (acc.replace("-", "") + "__EX991.txt.gz")
        if not p.exists():
            print("--", r["event_id"], qk, acc, "no cache")
            continue
        txt = gzip.open(p, "rt", encoding="utf-8").read()
        best = None
        for n in NOUN.finditer(txt):
            for v in VERB.finditer(txt):
                d = min(abs(v.start() - n.end()), abs(n.start() - v.end()))
                if best is None or d < best[0]:
                    best = (d, txt[max(0, min(v.start(), n.start()) - 60):
                                   max(v.end(), n.end()) + 60].replace("\n", " "))
        if best is None:
            print("--", r["event_id"], qk, acc, "無 noun 或 verb; chars=%d nouns=%d" % (
                len(txt), len(NOUN.findall(txt))))
        else:
            print("--", r["event_id"], qk, acc, "| 最近距離=%d | %s" % (best[0], best[1][:230]))
