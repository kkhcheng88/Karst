# -*- coding: utf-8 -*-
"""KARST-228:每條查詢只印第一個命中(檔+行號+片段),供核查表填「在哪裏找到」。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_rg import run, targets
import io, gzip, re

Q = [
    ("E001", r"12\.7|43,431|Insight.*contributed"),
    ("E009", r"172\.5|173\.0|held for sale"),
    ("E009", r"53.{0,4}57 ?MMBoe|53,?000|guidance"),
    ("E017", r"16\.7 million|138 ?%|268 ?%"),
    ("E017", r"Ancestry|royalty"),
    ("E017", r"15 ?%|no customer|concentration"),
    ("E025", r"29\.5|30\.8|24 ?%"),
    ("E025", r"10\.1|9\.6"),
    ("E033", r"Salix segment revenue was|Ortho Dermatologics segment revenue was|Financial Outlook"),
    ("E041", r"variable frequency"),
    ("E049", r"upsized|major competitor in the China service"),
    ("E057", r"87\.20|Average Sales Price"),
    ("E065", r"Streamlined Operating|75 million|100 million"),
    ("E033", r"higher gross selling prices of"),
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
                print("   @%s | %s" % (loc, ln.strip()[:240]))
                shown += 1
                break
        if shown >= 3:
            break
    if not shown:
        print("   NOT FOUND")
