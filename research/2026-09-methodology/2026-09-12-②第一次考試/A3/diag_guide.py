# -*- coding: utf-8 -*-
"""Diagnostic: run the guidance parser on one sentence and show what it picked."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s6_improve_text as S   # noqa: E402


def main() -> None:
    s = sys.argv[1]
    print("sentence:", s[:200])
    print("GUIDE_KW:", bool(S.GUIDE_KW.search(s)),
          "REV_KW pos:", (S.REV_KW.search(s).start() if S.REV_KW.search(s) else None))
    print("RANGE_RX:", [(m.group(0), m.start()) for m in S.RANGE_RX.finditer(s)])
    km = S.REV_KW.search(s)
    if km:
        print("_range_near:", S._range_near(s, km.start()))
        print("_num_near:", S._num_near(s, km.start()))
    print("NUM_RX:", [(m.group(0), m.group(1), m.group(2)) for m in S.NUM_RX.finditer(s)][:12])
    print("parsed:", S.parse_guidance("Header line.\n" + s))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
