# -*- coding: utf-8 -*-
"""KARST-231 附件:不執行 inject_transcripts.py 的情況下,算出它會注入什麼(唯讀)。

用途:核對 inline / 路徑兩種模式的分配,以及注入後包的大小,寫入覆蓋核查檔。
不寫任何檔。
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
A3 = os.path.dirname(HERE)
PK = os.path.join(A3, "packets")
LIMIT = 300 * 1024

files = sorted(glob.glob(os.path.join(HERE, "E*.json")) + glob.glob(os.path.join(HERE, "B*.json")))
inline = bypath = nopk = 0
pk_sizes = []
new_sizes = []
worst = []
for f in files:
    with open(f, encoding="utf-8") as fh:
        doc = json.load(fh)
    pkf = os.path.join(PK, doc["event_id"] + ".json")
    if not os.path.exists(pkf):
        nopk += 1
        continue
    with open(pkf, encoding="utf-8") as fh:
        packet = json.load(fh)
    base = len(json.dumps(packet, ensure_ascii=False).encode("utf-8"))
    pk_sizes.append(base)
    packet["2_觸發資料"]["earnings_call_transcript"] = doc["segments"]
    new = len(json.dumps(packet, ensure_ascii=False).encode("utf-8"))
    new_sizes.append(new)
    if new <= LIMIT:
        inline += 1
    else:
        bypath += 1
        worst.append((doc["event_id"], round(new / 1024)))

pk_sizes.sort()
new_sizes.sort()
print("逐字稿檔數", len(files), "有包可注入", inline + bypath, "無包(後備)", nopk)
print("inline", inline, "| 走 300KB 路徑模式", bypath)
print("包大小 現況(KB) min", round(pk_sizes[0] / 1024), "med",
      round(pk_sizes[len(pk_sizes) // 2] / 1024), "max", round(pk_sizes[-1] / 1024))
print("包大小 注入後(KB) min", round(new_sizes[0] / 1024), "med",
      round(new_sizes[len(new_sizes) // 2] / 1024), "max", round(new_sizes[-1] / 1024))
print("超 300KB 者(已去識別,只列 event_id):", sorted(worst, key=lambda x: -x[1])[:10])
