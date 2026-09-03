# -*- coding: utf-8 -*-
"""KARST-172:望一望 companyfacts 的形狀(dei 有沒有 accn、單位、標籤覆蓋)。唯讀。"""
import gzip
import json
import pathlib
from collections import Counter

CACHE = pathlib.Path(r"C:\projects\Karst\data\sec\companyfacts")


def main() -> None:
    files = sorted(CACHE.glob("*.json.gz"))[:40]
    scopes = Counter()
    for p in files[:40]:
        with gzip.open(p, "rb") as f:
            d = json.load(f)
        scopes.update((d.get("facts") or {}).keys())
    print("分類體系出現次數(40 份):", scopes.most_common())

    for p in files:
        with gzip.open(p, "rb") as f:
            d = json.load(f)
        facts = d.get("facts") or {}
        if "dei" in facts and "us-gaap" in facts:
            print("樣本:", d.get("entityName"), p.name)
            dei = facts["dei"]
            print("  dei 標籤:", list(dei)[:8])
            t = dei.get("EntityCommonStockSharesOutstanding")
            if t:
                for unit, pts in t["units"].items():
                    print("  dei 單位", unit, "點數", len(pts), "樣本", pts[-1])
            ug = facts["us-gaap"]
            print("  us-gaap 標籤數:", len(ug))
            for tag in ["Assets", "Liabilities", "CashAndCashEquivalentsAtCarryingValue",
                        "ShortTermInvestments", "LongTermDebtNoncurrent"]:
                if tag in ug:
                    unit = list(ug[tag]["units"])[0]
                    print(f"  {tag}: {len(ug[tag]['units'][unit])} 點,樣本 "
                          f"{ug[tag]['units'][unit][-1]}")
            break


if __name__ == "__main__":
    main()
