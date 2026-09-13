# -*- coding: utf-8 -*-
"""KARST-236 診斷:印出指定包在 fix235_diff.json 的完整改動行(只讀)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    d = json.load(open(HERE / "audit_out_fixed" / "fix235_diff.json",
                       encoding="utf-8"))
    pref = sys.argv[2] if len(sys.argv) > 2 else ""
    for line in d[sys.argv[1]]["diffs"]:
        if line.startswith(pref):
            print(line)
            print()


if __name__ == "__main__":
    main()
