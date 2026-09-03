# -*- coding: utf-8 -*-
"""KARST-172:242 家「有帳目但沒有我們要的欄」到底是什麼。唯讀。"""
from __future__ import annotations

import gzip
import json
import pathlib
from collections import Counter

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
CACHE = REPO / "data" / "sec" / "companyfacts"
PRIMARY = {"10-K", "10-Q", "20-F", "40-F"}


def main() -> None:
    panel = pd.read_parquet(REPO / "data" / "panel" / "quarterly_v3.parquet")
    ids = panel.loc[panel["facts_status"] == "no_usable_period", "entity_id"].unique()
    ent = pd.read_parquet(REPO / "data" / "universe" / "entities.parquet")
    ent = ent.set_index("entity_id")
    forms, tags, foreign, firstyear = Counter(), Counter(), Counter(), Counter()
    for cik in ids:
        p = CACHE / f"CIK{cik}.json.gz"
        if not p.exists():
            continue
        with gzip.open(p, "rb") as f:
            doc = json.load(f)
        facts = doc.get("facts") or {}
        for scope in ("us-gaap", "ifrs-full"):
            for tag, body in (facts.get(scope) or {}).items():
                tags[tag] += 1
                for unit, pts in (body.get("units") or {}).items():
                    for pt in pts[:5]:
                        forms[pt.get("form")] += 1
        if cik in ent.index:
            foreign[bool(ent.at[cik, "is_foreign_filer"])] += 1
            firstyear[str(ent.at[cik, "first_filing_year"])] += 1
    print("實體數:", len(ids))
    print("外國申報人:", dict(foreign))
    print("表格類型(頭 10):", forms.most_common(10))
    print("主要表格出現過的比例:",
          round(sum(v for k, v in forms.items() if k in PRIMARY) / max(sum(forms.values()), 1), 4))
    print("最常見標籤(頭 15):", tags.most_common(15))
    print("首次申報年(頭 8):", firstyear.most_common(8))


if __name__ == "__main__":
    main()
