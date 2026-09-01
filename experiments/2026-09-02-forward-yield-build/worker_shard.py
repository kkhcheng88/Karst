"""KARST-136 抓取分片 worker:按 index % mod == rem 取自己那一份。

用法:python worker_shard.py <mod> <rem>
已快取即跳過,不寫 fetch_log(由主 worker 負責),只補快取。
"""
from __future__ import annotations

import random
import sys
import time

import fetch_estimates as fe


def main() -> None:
    mod, rem = int(sys.argv[1]), int(sys.argv[2])
    syms = fe.symbols()
    mine = [s for i, s in enumerate(syms) if i % mod == rem]
    n = 0
    for s in mine:
        if (fe.CACHE / f"{s}.parquet").exists():
            continue
        st, k, msg = fe.fetch_one(s)
        n += 1
        print(f"[s{rem} {n}] {s} -> {st} {k} {msg}", flush=True)
        time.sleep(0.6 + random.random() * 0.4)
    print(f"shard {rem} done {n}", flush=True)


if __name__ == "__main__":
    main()
