# -*- coding: utf-8 -*-
"""上一份業績稿指引句:30 有句 / 53 有稿無句 / 1 無稿 —— 抽查無句的是真無指引還是解析器漏。

判法:在該份 EX-99.1 全文找指引字眼(outlook / guidance / expect / anticipate / forecast /
we project / full year / fiscal year),有字眼而解析器交白卷者列為疑似漏。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import s15_lib as L

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "packets"

KW = re.compile(r"(?i)\b(outlook|guidance|we expect|expects?|anticipate|forecast|"
                r"we project|projects? (?:revenue|earnings)|full[- ]year|fiscal year)\b")


def main() -> None:
    sus = 0
    tot = 0
    for p in sorted(OUT.glob("E*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        pr = d["2_觸發資料"]["prior_release_guidance"]
        if not isinstance(pr, dict) or not pr.get("accessionNumber"):
            continue
        if pr.get("guidance_sentences"):
            continue
        tot += 1
        txt = L.read_doc(pr.get("local_gz") or "")
        hits = KW.findall(txt)
        if hits:
            sus += 1
            if sus <= 8:
                i = KW.search(txt).start()
                print(p.stem, pr["accessionNumber"], len(txt), len(hits),
                      "|", re.sub(r"\s+", " ", txt[i - 120:i + 200]))
    print("有稿無句 %d;其中稿內有指引字眼(疑似解析器漏) %d" % (tot, sus))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
