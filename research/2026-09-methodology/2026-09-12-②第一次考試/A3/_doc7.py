# -*- coding: utf-8 -*-
"""第七步證據:被截斷文件的槽位現況 + masking_check.transcript_date 覆蓋。"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "packets"
DOCS = HERE.parent / "A" / "edgar_cache"


def main() -> None:
    for slot in ("E016", "E070", "E056", "E067"):
        d = json.loads((OUT / ("%s.json" % slot)).read_text(encoding="utf-8"))
        print(slot, d["event_id"], d["1_事件識別"]["accessionNumber"],
              "swap", d["1_事件識別"]["swapped_in"])
        for lab, v in d["3_截止前文件"].items():
            if isinstance(v, dict):
                p = DOCS / v["local_gz"]
                t = gzip.open(p, "rt", encoding="utf-8").read()
                has = [k for k, rx in (("Item7", r"(?i)item\s*7"), ("Item2", r"(?i)item\s*2\b"),
                                       ("MDA", r"(?i)management.{0,3}s discussion|MD&A"))
                       if re.search(rx, t)]
                print("   ", lab, v["form"], v["filingDate"], "lines", t.count("\n") + 1,
                      "sec", has)
            else:
                print("   ", lab, v)
    n_td = 0
    for p in sorted(OUT.glob("E*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        n_td += int("transcript_date" in d["masking_check"])
    print("masking_check 帶 transcript_date 的包數:", n_td)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
