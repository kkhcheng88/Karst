# -*- coding: utf-8 -*-
"""印 cache/stats_summary.json 各節(供人手抄進執行紀錄;不印公司名)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "cache" / "stats_summary.json").read_text(encoding="utf-8"))
KEYS = sys.argv[1:] or list(d.keys())
for k in KEYS:
    if k not in d:
        print("== %s:（無）" % k)
        continue
    print("== %s" % k)
    print(json.dumps(d[k], ensure_ascii=False, indent=1)[:2600])
