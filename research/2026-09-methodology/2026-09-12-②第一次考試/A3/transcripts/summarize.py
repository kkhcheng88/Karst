# -*- coding: utf-8 -*-
"""KARST-231 附件:把 coverage.csv 匯總成覆蓋核查檔要用的表(只印數量,無公司名或代號)。"""
import collections
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "coverage.csv"), encoding="utf-8")))

for coh, label in (("main", "主 84"), ("backup", "後備 44")):
    rs = [r for r in rows if r["cohort"] == coh]
    print(f"\n=== {label} 逐年 ===")
    print("year | n | 有 | 越界 | 缺 | 覆蓋率")
    yrs = sorted({int(r["year"]) for r in rs})
    for y in yrs:
        g = [r for r in rs if int(r["year"]) == y]
        a = sum(1 for r in g if r["status"] == "有")
        l = sum(1 for r in g if r["status"] == "越界")
        m = sum(1 for r in g if r["status"] == "缺")
        print(f"{y} | {len(g)} | {a} | {l} | {m} | {round(100*a/len(g))}%")
    a = sum(1 for r in rs if r["status"] == "有")
    l = sum(1 for r in rs if r["status"] == "越界")
    m = sum(1 for r in rs if r["status"] == "缺")
    print(f"合計 | {len(rs)} | {a} | {l} | {m} | {round(100*a/len(rs))}%")

hav = [r for r in rows if r["status"] == "有"]
print("\n=== 有稿 114 宗 ===")
ch = [int(r["n_chars"]) for r in hav]
sg = [int(r["n_segments"]) for r in hav]
ch.sort()
sg.sort()
print("n_chars  min", ch[0], "p25", ch[len(ch)//4], "med", ch[len(ch)//2], "max", ch[-1])
print("n_segs   min", sg[0], "med", sg[len(sg)//2], "max", sg[-1])
print("Q&A: 有明確問答段標記", sum(1 for r in hav if r["has_qna_section"] == "True"),
      "/ 有 Analysts 講者段", sum(1 for r in hav if int(r["n_analyst_segs"] or 0) > 0),
      "/ 兩者皆無", sum(1 for r in hav if r["has_qna_section"] == "False"
                        and int(r["n_analyst_segs"] or 0) == 0))
print("days_from_T0", collections.Counter(r["days_from_T0"] for r in hav))
print("越界 遲幾日 (T1 後)", sorted(int(r["days_from_T0"]) for r in rows if r["status"] == "越界"))
print("\n=== 缺 6 宗 前後最近一稿 ===")
for r in rows:
    if r["status"] == "缺":
        print(" ", r["event_id"], r["cohort"], r["year"], "prev", r["prev_tr_date"],
              "next", r["next_tr_date"], "sq_end", r["signal_q_end"], "T1", r["T1"])
print("\n=== 新聞 (T1 前 30 日) ===")
nv = sorted(int(r["n_news_30d"]) for r in rows if r["n_news_30d"] not in ("", None))
print("有新聞事件數", sum(1 for v in nv if v > 0), "/", len(nv), "| max", max(nv))
