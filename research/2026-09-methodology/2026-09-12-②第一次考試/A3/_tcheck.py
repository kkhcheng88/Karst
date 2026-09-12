# -*- coding: utf-8 -*-
"""逐字稿欄位大小與 masking_check 欄位抽查。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "packets"


def main() -> None:
    mx = 0
    for p in sorted(OUT.glob("E*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        t = d["2_觸發資料"]["earnings_call_transcript"]
        if isinstance(t, dict):
            mx = max(mx, len(json.dumps(t, ensure_ascii=False)))
        elif isinstance(t, str) and t != "查不到":
            mx = max(mx, len(t))
    print("max transcript field chars", mx)
    d = json.loads((OUT / "E001.json").read_text(encoding="utf-8"))
    t = d["2_觸發資料"]["earnings_call_transcript"]
    print("type", type(t).__name__, sorted(t) if isinstance(t, dict) else "")
    print("masking keys", sorted(d["masking_check"]))
    print("date keys", sorted(d["1_事件識別"]))
    c = json.loads((OUT.parent / "cache" / "enrich_counts.json").read_text(encoding="utf-8"))
    print({k: c[k] for k in ("packets", "swaps", "swap_same_year_bucket", "backup_used",
                             "backup_left", "doc_slots_total", "transcript_dump_path_only")})
    print(c["hashes"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
