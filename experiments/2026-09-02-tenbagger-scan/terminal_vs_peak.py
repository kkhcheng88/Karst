# -*- coding: utf-8 -*-
"""KARST-160:窗內最高價 vs 窗末價——量「必須賣在最高點」這個假設值幾多。"""
import json
import os

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

ROOT = r"C:\projects\Karst"
OUT = os.path.join(ROOT, "experiments", "2026-09-02-tenbagger-scan", "out")
P_EXIST = os.path.join(ROOT, "experiments", "2026-09-02-timing-sweep", "data", "daily_close.parquet")
P_NEW = os.path.join(ROOT, "experiments", "2026-09-02-narrative-layers-v2", "data", "new_close.parquet")
P_UNIV = os.path.join(ROOT, "experiments", "2026-09-02-narrative-layers-v2", "out", "universe_v2.json")
DROP = {"ARKB", "CTA", "KAP", "PXD"}

px = pd.read_parquet(P_EXIST).join(pd.read_parquet(P_NEW), how="outer").sort_index()
uni = json.load(open(P_UNIV, encoding="utf-8"))
cols = [t for t in uni["universe_stocks"] if t not in DROP and t in px.columns]
px = px[cols]
idx = px.index
s = pd.Series(idx, index=idx)
me = pd.DatetimeIndex(sorted(s.groupby([idx.year, idx.month]).max().values))
me = me[me >= pd.Timestamp("2009-01-01")]
arr = px.to_numpy(float)
pos = {d: i for i, d in enumerate(idx)}

rows = []
for h in (3, 5):
    for t0 in me:
        end = t0 + relativedelta(years=h)
        if end > idx.max():
            continue
        i0, i1 = pos[t0], idx.searchsorted(end, side="right") - 1
        if i1 <= i0:
            continue
        p0, seg = arr[i0], arr[i0:i1 + 1]
        with np.errstate(invalid="ignore", divide="ignore"):
            peak = np.nanmax(seg, axis=0) / p0
            term = arr[i1] / p0
        ok = np.isfinite(p0) & (p0 > 0) & np.isfinite(peak) & np.isfinite(term)
        for j in np.where(ok)[0]:
            rows.append((h, cols[j], t0, float(peak[j]), float(term[j]), t0.month))

d = pd.DataFrame(rows, columns=["h", "ticker", "t0", "peak_mult", "term_mult", "m"])
d["year"] = d.t0.dt.year
d["first_m"] = d.groupby(["h", "year"])["m"].transform("min")
res = {}
for h in (3, 5):
    dh = d[d.h == h]
    for arm, dd in [("任何月入場", dh), ("只准一月入場", dh[dh.m == dh.first_m])]:
        per_peak = dd.groupby(["ticker", "year"])["peak_mult"].max()
        per_term = dd.groupby(["ticker", "year"])["term_mult"].max()
        n_years = dd["year"].nunique()
        res[f"{h}y|{arm}"] = {
            "格年組合數": int(len(per_peak)),
            "窗內最高價達十倍的比例": round(float((per_peak >= 10).mean()), 4),
            "窗末價達十倍的比例": round(float((per_term >= 10).mean()), 4),
            "窗末價達五倍的比例": round(float((per_term >= 5).mean()), 4),
            "窗末價中位倍數": round(float(per_term.median()), 3),
            "窗內最高價中位倍數": round(float(per_peak.median()), 3),
            "起點年份數": int(n_years),
        }
json.dump(res, open(os.path.join(OUT, "terminal_vs_peak.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
