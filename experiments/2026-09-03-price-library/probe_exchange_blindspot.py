"""KARST-171 順手一查:E3(交易所欄空白即剔)這條規則的盲點有多大。

起因:舊價格檔盤點時發現 AEP(American Electric Power)有代號、entityType=operating、
交年報,但 submissions 的 exchanges 欄是空白,因此被 E3 剔出宇宙。
本腳本抽 400 個「有代號但不在實體表」的 CIK,量這一類佔多少。唯讀,不寫 data/。
"""

import json
import os
import random

import pandas as pd

ANN = {"10-K", "10-K405", "10-KSB", "10-KSB405", "20-F", "40-F"}


def main() -> None:
    ct = json.load(open(r"C:\projects\Karst\data\sec\company_tickers.json"))
    ent = pd.read_parquet(r"C:\projects\Karst\data\universe\entities.parquet")
    ids = set(ent["entity_id"])
    missing = sorted({c for c in ct.values() if c not in ids})
    print("有代號但不在實體表的 CIK:", len(missing))
    random.seed(171)
    samp = random.sample(missing, 400)
    cnt = {"no_file": 0, "no_exch": 0, "otc_only": 0, "major_exch": 0}
    hits = []
    for c in samp:
        p = rf"C:\projects\Karst\data\sec\submissions\CIK{c}.json"
        if not os.path.exists(p):
            cnt["no_file"] += 1
            continue
        d = json.load(open(p))
        ex = [x for x in (d.get("exchanges") or []) if x]
        ann = bool(set(d["filings"]["recent"]["form"]) & ANN)
        if not ex:
            cnt["no_exch"] += 1
            if ann and d.get("entityType") == "operating":
                hits.append((c, d.get("name"), d.get("sicDescription")))
        elif set(ex) <= {"OTC"}:
            cnt["otc_only"] += 1
        else:
            cnt["major_exch"] += 1
    print(cnt)
    print("抽樣中「交易所欄空白 + 有年報 + operating」:", len(hits), "/ 400")
    for x in hits[:15]:
        print("  ", x)
    out = {"sampled": 400, "missing_total": len(missing), "counts": cnt,
           "blank_exchange_with_annual_report": len(hits),
           "examples": hits[:30]}
    with open(
        r"C:\projects\Karst\experiments\2026-09-03-price-library\out\exchange_blindspot.json",
        "w", encoding="utf-8",
    ) as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
