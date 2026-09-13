# -*- coding: utf-8 -*-
"""KARST-235 探路:印出一個取證包的欄位名(只讀,不改)。"""
import glob
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

fs = sorted(glob.glob("packets/*.json"))
print("n_packets", len(fs))
d = json.load(open(fs[0], encoding="utf-8"))
print("TOP", list(d.keys()))
print("ID", list(d["1_事件識別"].keys()))
print("FIN", list(d["4_財務數列"].keys()))
print("NQ", len(d["4_財務數列"]["quarters"]))
print("Q0", json.dumps(d["4_財務數列"]["quarters"][0], ensure_ascii=False))
print("Q7", json.dumps(d["4_財務數列"]["quarters"][-1], ensure_ascii=False))
print("TRIG", list(d["2_觸發資料"].keys()))
print("MASK", json.dumps(d["masking_check"], ensure_ascii=False)[:400])
