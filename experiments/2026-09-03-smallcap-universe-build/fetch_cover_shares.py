"""KARST-167 步驟二:抓證監會 XBRL frames 的封面頁在外股數(逐季全體申報人)。

一次請求取一整季全體申報人,所以總共只有幾個請求——比逐家抓 companyfacts 平幾千倍。
取最近六季,每個 CIK 保留最近有數那一季作近似市值的股數,另保留相鄰季用作
「相差一千倍以上」的刻度檢查(研究報告 §3.3,RULES.md §六)。

輸出:out/cover_shares.json(CIK -> 逐季股數),不入 data/(它是衍生物不是原料)。
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

REPO = r"C:\projects\Karst"
OUT = os.path.join(REPO, "experiments", "2026-09-03-smallcap-universe-build", "out")
UA = "Casy Limited kaho.career@gmail.com"
TAG = "dei/EntityCommonStockSharesOutstanding/shares"
QUARTERS = [
    "CY2026Q3I", "CY2026Q2I", "CY2026Q1I",
    "CY2025Q4I", "CY2025Q3I", "CY2025Q2I", "CY2025Q1I",
]


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})

    per_quarter: dict[str, dict[str, float]] = {}
    meta: dict[str, object] = {}
    for q in QUARTERS:
        url = f"https://data.sec.gov/api/xbrl/frames/{TAG}/{q}.json"
        time.sleep(0.15)
        resp = session.get(url, timeout=120)
        if resp.status_code != 200:
            print(f"{q} http{resp.status_code} skip", flush=True)
            meta[q] = f"http{resp.status_code}"
            continue
        payload = resp.json()
        block: dict[str, float] = {}
        for row in payload.get("data", []):
            cik = str(row.get("cik")).zfill(10)
            val = row.get("val")
            if val is None:
                continue
            # 同一 CIK 一季可能多列(多個類別),封面頁一般各報一次,取合計
            block[cik] = block.get(cik, 0.0) + float(val)
        per_quarter[q] = block
        meta[q] = len(block)
        print(f"{q} filers={len(block)}", flush=True)

    with open(os.path.join(OUT, "cover_shares.json"), "w", encoding="utf-8") as fh:
        json.dump({"quarters": QUARTERS, "meta": meta, "data": per_quarter}, fh)
    print("written", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
