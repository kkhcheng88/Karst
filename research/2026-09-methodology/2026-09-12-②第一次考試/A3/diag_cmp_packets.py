# -*- coding: utf-8 -*-
"""比較 A/A2/A3 取證包:頂層欄位與 EX-99.1 全文長度(判斷原文是否入庫)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for tag in ("A", "A2", "A3"):
    p = HERE.parent / tag / "packets" / "E001.json"
    if not p.exists():
        print(tag, "無檔案")
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    body = d.get("2_觸發資料", {})
    print(tag, "頂層:", list(d.keys()))
    print("   EX-99.1 全文長度:",
          len(body.get("ex991_full_text", "")) if isinstance(body, dict) else "n/a")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
