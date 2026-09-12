# -*- coding: utf-8 -*-
"""獨立核查用的逐檔價格快取:只讀 data/prices/daily,只留指定 entity。
回傳 {cik: (dates[D], adj_close, close, open)};結果快取在 audit_out/px_small.parquet。
"""
import glob, os, sys
import numpy as np
import pandas as pd

ROOT = r"C:\projects\Karst"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "audit_out")
CACHE = os.path.join(OUT, "px_small.parquet")
_MEM = {}


def _wanted():
    """樣本 20 宗 + 主/後備清單的 cik 集合。"""
    import json
    sys.path.insert(0, HERE)
    import audit_common as C
    s = C.load_sample()
    ciks = {r["cik"] for rs in s["groups"].values() for r in rs}
    main, back = C.load_picks_md()
    ciks |= {r["cik"] for r in main + back}
    return ciks


def build():
    ciks = _wanted()
    parts = sorted(glob.glob(os.path.join(ROOT, "data", "prices", "daily", "part_*.parquet")))
    frames = []
    for p in parts:
        d = pd.read_parquet(p, columns=["entity_id", "date", "series_role", "adj_close", "close", "open"])
        d = d[(d["series_role"] == "primary") & d["entity_id"].isin(ciks)]
        if len(d):
            frames.append(d[["entity_id", "date", "adj_close", "close", "open"]])
        del d
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values(["entity_id", "date"]).reset_index(drop=True)
    os.makedirs(OUT, exist_ok=True)
    out.to_parquet(CACHE, index=False)
    return out


def get():
    if _MEM:
        return _MEM
    if not os.path.exists(CACHE):
        build()
    d = pd.read_parquet(CACHE)
    d["date"] = pd.to_datetime(d["date"])
    for eid, g in d.groupby("entity_id", sort=False):
        _MEM[eid] = (g["date"].values.astype("datetime64[D]"),
                     g["adj_close"].to_numpy(float),
                     g["close"].to_numpy(float),
                     g["open"].to_numpy(float))
    return _MEM


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    d = build()
    print("rows", len(d), "entities", d["entity_id"].nunique(), "→", CACHE)
