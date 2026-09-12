# -*- coding: utf-8 -*-
"""檢查 s12 要用的 cache 檔欄位/鍵(只印結構,不印公司名)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

for f in ("picks_compare_a2.json", "packets_substitutions.json", "s4_summary.json",
          "turnover_check.json"):
    p = CACHE / f
    if not p.exists():
        print(f, "不存在")
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    print(f, "→", json.dumps(d, ensure_ascii=False)[:600])
for f in ("fetch_log_a3.jsonl", "merger_fetch_log.jsonl"):
    p = CACHE / f
    if not p.exists():
        print(f, "不存在")
        continue
    line = next(p.open(encoding="utf-8"))
    print(f, "first line keys:", list(json.loads(line).keys()))
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
