# -*- coding: utf-8 -*-
"""Diagnostic: inspect quarter_rev output for a single CIK."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from s3_xbrl import quarter_rev   # noqa: E402


def main() -> None:
    for cik in sys.argv[1:]:
        s, filed, st, tag, n, nd = quarter_rev(cik)
        ends = sorted(s)
        print("CIK %s status=%r tag=%r ntags=%d derived=%d quarters=%d"
              % (cik, st, tag, n, nd, len(ends)))
        print("  ends:", ends[-10:])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
