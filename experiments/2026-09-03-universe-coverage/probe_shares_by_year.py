# -*- coding: utf-8 -*-
"""KARST-173:封面頁股數在時間上的覆蓋——免費路能否為早年算市值(唯讀)。"""
from __future__ import annotations

import gzip
import json

import pandas as pd

import common as C

CACHE = C.REPO / "data" / "sec" / "companyfacts"


def main() -> None:
    p = C.panel()
    p["filed_year"] = p["filed_date"].dt.year
    tbl = p.groupby("filed_year").agg(
        列數=("entity_id", "size"),
        有股數=("shares_outstanding", lambda s: int(s.notna().sum())),
        實體數=("entity_id", "nunique"))
    tbl["有股數比例"] = (tbl["有股數"] / tbl["列數"]).round(4)
    print("=== 面板 v3 逐個申報年:封面頁股數覆蓋 ===")
    print(tbl.to_string())

    print("\n=== 每年 1 月 1 日之前有過股數的實體數(累計口徑)===")
    have = p[p["shares_outstanding"].notna()].groupby("entity_id")["filed_date"].min()
    for y in range(2010, 2027):
        cut = pd.Timestamp(f"{y}-01-01")
        print(y, int((have <= cut).sum()))

    print("\n=== 5,257 家之中,companyfacts 有 dei:EntityCommonStockSharesOutstanding 的比例 ===")
    ent = pd.read_parquet(C.UNIVERSE / "entities.parquet", columns=["entity_id", "multi_class"])
    n_has, n_no, n_missing_file = 0, 0, 0
    no_tag_multi = 0
    mc = dict(zip(ent["entity_id"], ent["multi_class"]))
    for cik in ent["entity_id"]:
        f = CACHE / f"CIK{cik}.json.gz"
        if not f.exists():
            n_missing_file += 1
            continue
        with gzip.open(f, "rb") as fh:
            doc = json.load(fh)
        dei = ((doc.get("facts") or {}).get("dei") or {})
        if "EntityCommonStockSharesOutstanding" in dei:
            n_has += 1
        else:
            n_no += 1
            if mc.get(cik):
                no_tag_multi += 1
    print("有此標籤", n_has, "無此標籤", n_no, "(其中多類別股", no_tag_multi, ")",
          "無快取檔", n_missing_file)


if __name__ == "__main__":
    main()
