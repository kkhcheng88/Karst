# -*- coding: utf-8 -*-
"""印 A3 交付品的 UTC 時間戳(供執行紀錄的時間戳表)。"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
FILES = ["picks_before_results.md", "population.csv", "population.csv.gz", "entry_pool.csv",
         "thresholds.md", "guidance_audit.md", "controls_operating.csv", ".gitignore"]
for f in FILES:
    p = HERE / f
    if p.exists():
        print("%-28s %s  %.1f MB" % (
            f, pd.Timestamp(p.stat().st_mtime, unit="s", tz="UTC").isoformat(),
            p.stat().st_size / 1e6))
pk = sorted((HERE / "packets").glob("*.json"))
ts = [p.stat().st_mtime for p in pk]
print("%-28s %s … %s (%d 檔)" % (
    "packets/", pd.Timestamp(min(ts), unit="s", tz="UTC").isoformat(),
    pd.Timestamp(max(ts), unit="s", tz="UTC").isoformat(), len(pk)))
for f in ("cache/picks.json", "cache/thresholds_window.parquet",
          "cache/guidance_parsed.jsonl", "cache/acceptance_checks.json",
          "cache/investigations.json", "cache/stats_summary.json"):
    p = HERE / f
    if p.exists():
        print("%-28s %s" % (f, pd.Timestamp(p.stat().st_mtime, unit="s",
                                            tz="UTC").isoformat()))
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
