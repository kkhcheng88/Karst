# -*- coding: utf-8 -*-
"""KARST-232 第二步(抓取):把補強要用的原文抓回 `A/edgar_cache/`。

單線程、3 請求/秒(票面硬規矩);長工序拆支跑,每支印一行。用法:
    PYTHONUTF8=1 python A3/s15_fetch.py [每支秒數上限]
已快取者跳過,可重複跑,直到印出「未完成 0」。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def main() -> None:
    import s15_lib as L
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 480.0
    plan = json.loads((CACHE / "enrich_plan.json").read_text(encoding="utf-8"))
    jobs = list(plan["fetch_docs"]) + list(plan["build_docs_missing"])
    seen = set()
    uniq = []
    for j in jobs:
        key = (j["cik"], j["accn"], j["tag"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(j)
    log = CACHE / "enrich_fetch_log.jsonl"
    done = set()
    if log.exists():
        for line in log.open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("status") in ("ok", "已快取", "該申報無 EX-99 附件"):
                done.add((r["cik"], r["accn"], r["tag"]))
    todo = [j for j in uniq if (j["cik"], j["accn"], j["tag"]) not in done]
    print("工作 %d;已完成 %d;本支待做 %d" % (len(uniq), len(uniq) - len(todo), len(todo)),
          flush=True)

    t0 = time.time()
    n = ok = fail = 0
    with log.open("a", encoding="utf-8") as f:
        for j in todo:
            if time.time() - t0 > budget:
                break
            if j["tag"] == "EX991":
                fn, st = L.fetch_ex991(j["cik"], j["accn"])
            else:
                fn, st = L.cached(j["cik"], j["accn"], j["doc"], j["tag"])
            f.write(json.dumps(dict(cik=j["cik"], accn=j["accn"], tag=j["tag"],
                                    status=st, file=fn), ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            ok += int(st in ("ok", "已快取"))
            fail += int(st not in ("ok", "已快取"))
            if n % 20 == 0:
                print("  ...%d 用時%.0fs ok=%d fail=%d" % (n, time.time() - t0, ok, fail),
                      flush=True)
    left = len(todo) - n
    print("本支做 %d;ok %d;fail %d;未完成 %d;用時 %.0fs"
          % (n, ok, fail, left, time.time() - t0))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
