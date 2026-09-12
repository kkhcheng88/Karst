# -*- coding: utf-8 -*-
"""票 A″ 第 10 步補漏:持續經營疑慮(going concern)在取證包階段核。

v1.1(票 A/A2)的設計是「母體層標未核,抽中者在取證包階段核」;A3 的 s6 改寫時把這一格
漏掉(母體全標未核)。本支就地把 84 個取證包的 EX-99.1 全文掃一次「going concern」,
寫回包內(`2_觸發資料.going_concern_hit` 與摘句),並落 `cache/going_concern_84.json`。

**不改任何已鎖定的抽樣**(鎖定規則只准因第 4/6 步與補三的資料資格換後備);命中者照留,
在執行紀錄列明,交裁。原文不入庫,摘句只 160 字。
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
PACKETS = HERE / "packets"
DOCS = HERE.parent / "A" / "edgar_cache"
GC = re.compile(r"(?i)going\s+concern")


def main() -> None:
    rows = []
    for p in sorted(PACKETS.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        acc = d["1_事件識別"]["accessionNumber"]
        src = d.get("provenance", {}).get("accessionNumber", acc)
        txt = ""
        f = DOCS / ("%s__EX991.txt.gz" % str(src).replace("-", ""))
        if f.exists():
            txt = gzip.open(f, "rt", encoding="utf-8").read()
        m = GC.search(txt)
        snip = "" if not m else re.sub(
            r"\s+", " ", txt[max(0, m.start() - 80):m.end() + 80]).strip()[:160]
        d["2_觸發資料"]["going_concern_hit"] = int(bool(m))
        d["2_觸發資料"]["going_concern_snippet"] = snip
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        rows.append(dict(event_id=d["event_id"], accessionNumber=acc,
                         ex991_chars=len(txt), going_concern_hit=int(bool(m)),
                         snippet=snip))
    (CACHE / "going_concern_84.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    hit = [r for r in rows if r["going_concern_hit"]]
    print("掃 %d 包;命中 %d 個:%s" % (len(rows), len(hit),
                                  [r["event_id"] for r in hit]))
    print("無 EX-99.1 全文的包:", [r["event_id"] for r in rows if r["ex991_chars"] == 0])
    print("→", CACHE / "going_concern_84.json")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
