# -*- coding: utf-8 -*-
"""最後兩條:COIN 2022-06-14 8-K 與 Cigna 2018-02-01 8-K 正文核。"""
from __future__ import annotations

import re
import ssl
import sys
import urllib.request

UA = {"User-Agent": "Karst research kaho@example.com"}
CTX = ssl._create_unverified_context()  # noqa: SLF001

URLS = [
 ("COIN_20220614", "https://www.sec.gov/Archives/edgar/data/1679788/000167978822000077/coin-20220614.htm",
  ["Celsius", "market", "trading", "bitcoin"]),
 ("CIGNA_20180201", "https://www.sec.gov/Archives/edgar/data/701221/000095015918000039/ex99-1.htm",
  ["Amazon", "Berkshire", "JPMorgan", "venture"]),
 ("AETNA_INDEX", "https://www.sec.gov/Archives/edgar/data/1122304/000112230418000011/",
  ["exhibit", "index"]),
]


def fetch(u: str) -> str:
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
        raw = r.read().decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"\s+", " ", t)


def main() -> None:
    for k, u, kws in URLS:
        try:
            t = fetch(u)
            print(k, len(t), {w: (w.lower() in t.lower()) for w in kws}, flush=True)
            print("   >>>", t[:400], flush=True)
            for w in kws:
                i = t.lower().find(w.lower())
                if i >= 0:
                    print("   ...", t[max(0, i - 130):i + 200], flush=True)
        except Exception as e:  # noqa: BLE001
            print(k, "ERR", type(e).__name__, str(e)[:70], flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
