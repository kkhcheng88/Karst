# -*- coding: utf-8 -*-
"""KARST-228:CSV 欄位 vs 卡內第八步總判、第三步點值 的逐項對照。"""
import csv, io, os, re, glob

BASE = r"C:/projects/Karst/research/2026-09-methodology/2026-09-12-②第一次考試"
PAO = os.path.join(BASE, "試跑")

for arm in ("ds", "opus"):
    print("=" * 70)
    print("ARM=%s" % arm)
    for p in sorted(glob.glob(os.path.join(PAO, arm, "rows", "E*.csv"))):
        ev = os.path.basename(p)[:-4]
        rr = list(csv.reader(io.StringIO(io.open(p, encoding="utf-8-sig").read())))
        hdr, row = rr[0], rr[1]
        d = dict(zip(hdr, row)) if len(row) == 27 else {}
        ct = io.open(glob.glob(os.path.join(PAO, arm, "卡-%s-*.md" % ev))[0], encoding="utf-8").read()
        m8 = re.findall(r"persistence_overall[^\n]{0,25}?[:：]\s*\*{0,3}(高|中|低|無法判斷)", ct)
        m3 = re.findall(r"點值\s*\*{0,2}([0-9]+\.[0-9]+)", ct)
        print("  %s csv[persist=%s g2=%s drv=%s]" % (ev, d.get("persistence_overall", "?"), d.get("pred_g2_point", "?"), d.get("top_driver_type", "?")))
        print("       card persistence_overall 出現值=%s  ; card 點值=%s" % (m8[:4], m3[:4]))
