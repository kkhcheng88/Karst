# -*- coding: utf-8 -*-
"""KARST-173:那 16 家「有面板無股數」,到底是原料沒有,還是面板 v3 沒接上(唯讀)。"""
from __future__ import annotations

import gzip
import json
import pathlib

import pandas as pd

import common as C

CACHE = C.REPO / "data" / "sec" / "companyfacts"
CASES = ["MSTR", "SHOP", "OKTA", "W", "VEEV", "MDB"]


def main() -> None:
    d = pd.read_csv(C.OUT / "tenbagger_t0_v3.csv", dtype={"entity_id": str})
    d["t0"] = pd.to_datetime(d["t0"])
    p = C.panel()
    for tk in CASES:
        r = d[d["ticker"] == tk]
        if r.empty:
            continue
        r = r.iloc[0]
        eid = str(r["entity_id"]).split(".")[0].zfill(10)
        t0 = r["t0"]
        sub = p[(p["entity_id"] == eid)]
        before = sub[sub["filed_date"] <= t0]
        print(f"--- {tk} t0={t0.date()} entity={eid} ---")
        print("  面板列(t0 前):", len(before), " 有股數的:",
              int(before["shares_outstanding"].notna().sum()),
              " 全期有股數的:", int(sub["shares_outstanding"].notna().sum()))
        f = CACHE / f"CIK{eid}.json.gz"
        if not f.exists():
            print("  快取無此檔")
            continue
        with gzip.open(f, "rb") as fh:
            doc = json.load(fh)
        dei = ((doc.get("facts") or {}).get("dei") or {})
        tag = dei.get("EntityCommonStockSharesOutstanding")
        if not tag:
            print("  companyfacts 內無 dei:EntityCommonStockSharesOutstanding")
            continue
        pts = []
        for unit, arr in (tag.get("units") or {}).items():
            for pt in arr:
                pts.append((pt.get("filed"), pt.get("end"), pt.get("val"), pt.get("form")))
        pts.sort()
        early = [x for x in pts if x[0] <= t0.date().isoformat()]
        print(f"  原料封面股數點:{len(pts)} 個,其中申報日 <= t0 的 {len(early)} 個")
        if early:
            print("   最早三個:", early[:3])
            print("   最後一個:", early[-1])


if __name__ == "__main__":
    main()
