# -*- coding: utf-8 -*-
"""核對 pxlib.state_at 與逐 entity 手工切片(不重用 pxlib 的推導碼)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

import pxlib

ROOT = Path(r"C:\projects\Karst")
PRICES = ROOT / "data" / "prices" / "daily"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
PX_FROM = pd.Timestamp("2013-06-01")


def manual(eid: str) -> pd.DataFrame:
    frames = []
    for p in pxlib.parts():
        d = pd.read_parquet(p, columns=["entity_id", "date", "adj_close", "close",
                                        "volume", "series_role"])
        d = d[(d["entity_id"] == eid) & (d["series_role"] == "primary")]
        if len(d):
            frames.append(d)
    g = pd.concat(frames).copy()
    g["date"] = pd.to_datetime(g["date"])
    g = g[g["date"] >= PX_FROM].dropna(subset=["adj_close"]).sort_values("date")
    g = g.reset_index(drop=True)
    g["ret6"] = g["adj_close"].shift(21) / g["adj_close"].shift(147) - 1.0
    g["ret12"] = g["adj_close"].shift(21) / g["adj_close"].shift(273) - 1.0
    g["dist52"] = g["adj_close"] / g["adj_close"].rolling(252, min_periods=60).max() - 1.0
    g["dv60"] = (g["close"] * g["volume"]).rolling(60, min_periods=20).mean()
    return g


def main() -> None:
    picks = json.loads((CACHE / "picks.json").read_text(encoding="utf-8"))
    pop = pd.read_parquet(CACHE / "population_improvement.parquet").set_index("accessionNumber")
    evs = []
    for q in picks["main"][:3] + picks["backup"][:1]:
        m = pop.loc[q["acc"]]
        evs.append((m["cik"], m["reaction_date"], m["ticker"]))
    st, _first = pxlib.state_at({e[1] for e in evs})
    st = st.set_index(["entity_id", "date"])
    bad = 0
    for cik, d1, tk in evs:
        g = manual(cik)
        row = g[g["date"] == pd.Timestamp(d1)]
        if not len(row):
            print("%s %s 該日無行" % (tk, d1))
            continue
        r = row.iloc[0]
        s = st.loc[(cik, pd.Timestamp(d1))]
        for col in ("ret6", "ret12", "dist52", "dv60"):
            a, b = float(r[col]), float(s[col])
            ok = abs(a - b) < 1e-9 or (pd.isna(a) and pd.isna(b))
            if not ok:
                bad += 1
            print("%s %s %s 手工 %.8f pxlib %.8f %s" % (
                tk, d1, col, a, b, "OK" if ok else "**不符**"))
    print("不符項數", bad)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
