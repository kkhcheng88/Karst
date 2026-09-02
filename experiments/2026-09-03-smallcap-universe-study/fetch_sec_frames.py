"""KARST-162 §1/§4:抓證監會 XBRL frames 的封面頁股數(每年一格),用途有二:
1. 數每年有多少個申報人有封面頁股數 —— 宇宙家數的量級參考(上限性質,見 RULES.md §4)
2. 為十倍股名單中面板沒有覆蓋的公司補一個粗略股數(見 RULES.md §2 第三層)

只抓 frames 端點,每年一次請求,合共十四次。不寫入 data/。
"""
import gzip
import io
import json
import os
import time
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
UA = "Karst Research (KARST-162) kaho.career@gmail.com"
YEARS = list(range(2009, 2023))


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return json.loads(raw)


def main():
    counts = []
    shares = {}  # cik -> {year: val}(同年多季取最後一次見到的值)
    seen_year = {}  # year -> set of cik(四季合併,用來數申報人)
    for y in YEARS:
        for q in (1, 2, 3, 4):
            url = (
                "https://data.sec.gov/api/xbrl/frames/dei/"
                f"EntityCommonStockSharesOutstanding/shares/CY{y}Q{q}I.json"
            )
            try:
                d = get_json(url)
            except Exception as e:  # noqa: BLE001
                print(f"{y}Q{q} FAILED {e}")
                continue
            rows = d.get("data", [])
            print(f"{y}Q{q}: {len(rows)} filers")
            for r in rows:
                shares.setdefault(int(r["cik"]), {})[y] = r["val"]
                seen_year.setdefault(y, set()).add(int(r["cik"]))
            time.sleep(0.4)
        counts.append({"year": y, "n_filers": len(seen_year.get(y, ())), "note": "四季合併去重"})

    import pandas as pd

    pd.DataFrame(counts).to_csv(os.path.join(OUT, "sec_filer_counts.csv"), index=False)
    with open(os.path.join(OUT, "sec_cover_shares.json"), "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in shares.items()}, f)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
