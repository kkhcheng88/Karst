# -*- coding: utf-8 -*-
"""KARST-228:第二批「每條只印頭一個命中」查詢(Opus 臂未清項)。"""
import os, sys, io, gzip, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_rg import targets

Q = [
    ("E025", r"close our aerial|discontinue|Karma"),
    ("E041", r"seasonality in the third quarter"),
    ("E049", r"524\.1|572\.1|540\.7|513\.9"),
    ("E049", r"upsized its expedited service"),
    ("E057", r"not party to any|spot|long-term contract|competitive"),
    ("E065", r"volume decrease|19 ?%|-10 ?%|10 ?%"),
    ("E065", r"Wal-Mart|Walmart|25 ?% of"),
    ("E073", r"stabilization|reaffirming"),
    ("E009", r"129 net|DUC|30 net|65 net"),
    ("E017", r"764|321|526|142"),
    ("E017", r"15 ?% of"),
    ("E033", r"15 ?%|69 ?%|rifaximin"),
    ("E073", r"67 ?% and 17|two customers"),
]

for e, pat in Q:
    print("### %s /%s/" % (e, pat))
    rx = re.compile(pat, re.I)
    shown = 0
    for path, label in targets(e):
        if path.endswith(".packet.txt"):
            L = io.open(path, encoding="utf-8").read().split("\n")
        elif os.path.exists(path):
            L = gzip.open(path, "rt", encoding="utf-8", errors="replace").read().split("\n")
        else:
            continue
        off = 10 ** 9
        if path.endswith(".packet.txt"):
            for i, l in enumerate(L, 1):
                if l.startswith("[2_觸發資料.ex991_full_text]"):
                    off = i
                    break
        for i, ln in enumerate(L, 1):
            if rx.search(ln):
                loc = ("EX-99.1 第%d行(packet.txt:%d)" % (i - off + 1, i)) if i > off else ("%s:%d" % (label.split(" / ")[0], i))
                print("   @%s | %s" % (loc, ln.strip()[:230]))
                shown += 1
                break
        if shown >= 3:
            break
    if not shown:
        print("   NOT FOUND")
