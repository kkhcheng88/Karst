# -*- coding: utf-8 -*-
"""KARST-160:倉內十倍股由起點到峰頂要幾耐(持有期分佈,倉內版本非文獻)。"""
import json
import os

import pandas as pd

OUT = r"C:\projects\Karst\experiments\2026-09-02-tenbagger-scan\out"
nm = pd.read_csv(os.path.join(OUT, "tenbagger_names.csv"), encoding="utf-8-sig")
nm["days"] = (pd.to_datetime(nm.peak_date) - pd.to_datetime(nm.t0)).dt.days
res = {}
for h in ["3y", "5y"]:
    d = nm[nm.horizon == h]["days"]
    res[h] = {"家數": int(len(d)),
              "到峰頂日數_中位": int(d.median()),
              "到峰頂年數_中位": round(float(d.median()) / 365.25, 2),
              "四分位": [int(d.quantile(.25)), int(d.quantile(.75))],
              "最短": int(d.min()), "最長": int(d.max())}
json.dump(res, open(os.path.join(OUT, "holding_period.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
