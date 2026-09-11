# -*- coding: utf-8 -*-
"""KARST-213 批 2:核對取證包記錄的衝擊起日收市價(只讀日線,不讀結果欄)。

用法:python 查價.py <E??> <TICKER> [前後日數=6]
"""
import glob
import json
import sys

import pandas as pd

B2 = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①v3全量回測/批2"
PRICES = "C:/projects/Karst/data/prices/daily/part_*.parquet"


def main():
    eid, tk = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    pack = json.load(open("%s/packets/%s.json" % (B2, eid), encoding="utf-8"))
    c = [x for x in pack["companies"] if x["ticker"] == tk][0]
    eid_ = c["entity_id"]
    cut = pd.Timestamp(pack["shock_start"])
    frames = []
    for f in glob.glob(PRICES):
        d = pd.read_parquet(f)
        d = d[d["entity_id"] == eid_]
        if len(d):
            frames.append(d[d["series_role"] == "primary"].drop(columns=["series_role"]))
    px = pd.concat(frames, ignore_index=True)
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values("date")
    w = px[(px["date"] >= cut - pd.Timedelta(days=n)) & (px["date"] <= cut + pd.Timedelta(days=n))]
    print("==", eid, tk, "cutoff", pack["shock_start"], "packet close",
          (c.get("price_block") or {}).get("close"))
    for _, r in w.iterrows():
        print("  ", r["date"].date(), round(float(r["close"]), 4))
    before = px[px["date"] <= cut]
    print("   last close <= cutoff:", before["date"].iloc[-1].date(), round(float(before["close"].iloc[-1]), 4))


if __name__ == "__main__":
    main()
