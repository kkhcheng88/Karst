# -*- coding: utf-8 -*-
"""KARST-160:鏈表覆蓋率的分母,令「29% 十倍股在鏈表」這個數字讀得懂。"""
import json

import pandas as pd

ROOT = r"C:\projects\Karst"
u = json.load(open(rf"{ROOT}\experiments\2026-09-02-narrative-layers-v2\out\universe_v2.json",
                   encoding="utf-8"))
uni = set(u["universe_stocks"]) - {"ARKB", "CTA", "KAP", "PXD"}
c = pd.read_csv(rf"{ROOT}\experiments\2026-09-02-chain-layers\chain_membership_v0.csv",
                encoding="utf-8-sig", engine="python", on_bad_lines="skip")
ch = set(c.ticker.unique())
print("宇宙家數", len(uni))
print("鏈表代號數", len(ch), "其中在宇宙內", len(ch & uni))
print("宇宙之中在鏈表的比例", round(len(ch & uni) / len(uni), 4))
nm = pd.read_csv(rf"{ROOT}\experiments\2026-09-02-tenbagger-scan\out\tenbagger_names.csv",
                 encoding="utf-8-sig")
for h in ["3y", "5y"]:
    d = nm[nm.horizon == h]
    print(h, "十倍股家數", len(d), "在鏈表", int(d.chain_theme.notna().sum()),
          "比例", round(float(d.chain_theme.notna().mean()), 4))
