# -*- coding: utf-8 -*-
"""KARST-236 第 0 步:備份九包 + 記 84 包修改前 sha256。

- 九包(E017/E021/E022/E024/E025/E047/E057/E073 修;E006 只備份對照)→
  `A3/cache/packets_before_fix235/`
- 84 包 sha256 → `A3/cache/packets_sha_before_fix235.json`
只讀包、只寫 cache,不改任何既有包。不列公司名或代號。
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKT = HERE / "packets"
BK = HERE / "cache" / "packets_before_fix235"
NINE = ["E017", "E021", "E022", "E024", "E025", "E047", "E057", "E073", "E006"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    BK.mkdir(parents=True, exist_ok=True)
    shas = {}
    for p in sorted(PKT.glob("*.json")):
        shas[p.stem] = sha(p)
    (HERE / "cache" / "packets_sha_before_fix235.json").write_text(
        json.dumps(shas, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8")
    n = 0
    for eid in NINE:
        src = PKT / ("%s.json" % eid)
        if not src.exists():
            print("MISSING", eid)
            continue
        shutil.copy2(src, BK / src.name)
        n += 1
    print("n_packets_sha", len(shas))
    print("n_backed_up", n)
    for eid in NINE:
        print(" ", eid, shas.get(eid))


if __name__ == "__main__":
    main()
