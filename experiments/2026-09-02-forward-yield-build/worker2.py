"""KARST-136 抓取第二 worker:由名單尾倒序抓,與 fetch_estimates.py 對半分擔。

已快取即跳過;不寫 fetch_log(由主 worker 負責),只補快取。
兩個 worker 在名單中間相遇時最多重覆抓一兩隻,無害。
"""
from __future__ import annotations

import random
import time

import fetch_estimates as fe


def main() -> None:
    syms = list(reversed(fe.symbols()))
    n = 0
    for s in syms:
        if (fe.CACHE / f"{s}.parquet").exists():
            continue
        st, k, msg = fe.fetch_one(s)
        n += 1
        if n % 10 == 0 or st != "ok":
            print(f"[w2 {n}] {s} -> {st} {k} {msg}", flush=True)
        time.sleep(fe.SLEEP_WITHIN + random.random() * 0.4)
        if n % fe.BATCH == 0:
            time.sleep(fe.SLEEP_BETWEEN)
    print("w2 done", n, flush=True)


if __name__ == "__main__":
    main()
