# -*- coding: utf-8 -*-
"""KARST-231 附件:對本票交付品逐條自核(唯讀,不寫檔)。

核:
  V1 每個 <event_id>.json 的 report_date <= T1(且 > signal_q_end)——反例即不合格
  V2 檔內欄位齊(segments、report_date、source、抓取時間、段數、字數)
  V3 coverage.csv 與檔案一致(status 有 = 有 json;json 存在 = status 有)
  V4 事件覆蓋數:主 84 + 後備 44 = 128 逐宗有記
  V5 檔內不含 ticker(公司代號)
"""
import csv
import datetime as dt
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A3 = os.path.dirname(HERE)
rows = {r["event_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "coverage.csv"), encoding="utf-8"))}
tickers = set()
for fn in os.listdir(os.path.join(A3, "packets")):
    if fn.endswith(".json"):
        with open(os.path.join(A3, "packets", fn), encoding="utf-8") as fh:
            tickers.add((json.load(fh).get("ticker") or "").upper())
tickers.discard("")

fails = []
jsons = sorted(glob.glob(os.path.join(HERE, "E*.json")) + glob.glob(os.path.join(HERE, "B*.json")))

# V1 + V2 + V5
for f in jsons:
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    eid = d["event_id"]
    if not (d["signal_q_end"] < d["report_date"] <= d["T1"]):
        fails.append(f"V1 {eid} report_date {d['report_date']} 不在 (signal_q_end, T1]")
    for k in ("segments", "report_date", "source", "fetch_time_utc",
              "n_segments", "n_chars", "T1", "signal_q_end"):
        if k not in d:
            fails.append(f"V2 {eid} 缺欄 {k}")
    if d.get("n_segments") != len(d.get("segments", [])):
        fails.append(f"V2 {eid} n_segments 與 segments 長度不符")
    if d.get("n_chars") != sum(len(s["content"]) for s in d.get("segments", [])):
        fails.append(f"V2 {eid} n_chars 不符")
    up = json.dumps({k: v for k, v in d.items() if k != "segments"}, ensure_ascii=False).upper()
    hit = [t for t in tickers if re.search(r'"' + re.escape(t) + r'"', up)]
    if hit:
        fails.append(f"V5 {eid} 檔內出現代號 {hit}")

# V3
have = {os.path.basename(f)[:-5] for f in jsons}
for eid, r in rows.items():
    if (r["status"] == "有") != (eid in have):
        fails.append(f"V3 {eid} status={r['status']} 但 json {'在' if eid in have else '不在'}")

# V4
exp = ["E%03d" % i for i in range(1, 85)] + ["B%03d" % i for i in range(1, 45)]
if set(rows) != set(exp):
    fails.append("V4 事件清單不齊:缺 %s 多 %s" % (sorted(set(exp) - set(rows)), sorted(set(rows) - set(exp))))

print("jsons:", len(jsons), "| coverage rows:", len(rows))
print("status:", {s: sum(1 for r in rows.values() if r["status"] == s) for s in ("有", "越界", "缺")})
print("FAILS:", len(fails))
for x in fails[:20]:
    print("  ", x)
sys.exit(1 if fails else 0)
