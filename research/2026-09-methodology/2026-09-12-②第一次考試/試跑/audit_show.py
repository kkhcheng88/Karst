# -*- coding: utf-8 -*-
"""KARST-228:印出指定檔案的指定行範圍(檔名可用 packet:<E> 指包內文字檔,否則指 A/edgar_cache/<名>.gz)。"""
import gzip, io, os, sys

BASE = r"C:/projects/Karst/research/2026-09-methodology/2026-09-12-②第一次考試"
CACHE = os.path.join(BASE, "A", "edgar_cache")
TXT = os.path.join(BASE, r"試跑", "_audit_txt")


def lines_of(spec):
    if spec.startswith("packet:"):
        p = os.path.join(TXT, spec.split(":", 1)[1] + ".packet.txt")
        return io.open(p, encoding="utf-8").read().split("\n")
    p = os.path.join(CACHE, spec if spec.endswith(".gz") else spec + ".txt.gz")
    return gzip.open(p, "rt", encoding="utf-8", errors="replace").read().split("\n")


if __name__ == "__main__":
    spec = sys.argv[1]
    a, b = int(sys.argv[2]), int(sys.argv[3])
    L = lines_of(spec)
    print("### %s lines %d-%d (total %d)" % (spec, a, b, len(L)))
    for i in range(max(1, a), min(len(L), b) + 1):
        s = L[i - 1].strip()
        if s:
            print("%6d| %s" % (i, s[:260]))
