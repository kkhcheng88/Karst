# -*- coding: utf-8 -*-
"""KARST-228:在指定檔案(gz 或 packet 文字檔)內做區分大小寫不敏感的全文搜尋,印出完整行與行號。
用法: python audit_grep.py <file-spec> <pattern> [maxhits]
"""
import gzip, io, os, re, sys

BASE = r"C:/projects/Karst/research/2026-09-methodology/2026-09-12-②第一次考試"
CACHE = os.path.join(BASE, "A", "edgar_cache")
TXT = os.path.join(BASE, r"試跑", "_audit_txt")


def lines_of(spec):
    if spec.startswith("packet:"):
        return io.open(os.path.join(TXT, spec.split(":", 1)[1] + ".packet.txt"), encoding="utf-8").read().split("\n")
    p = os.path.join(CACHE, spec if spec.endswith(".gz") else spec + ".txt.gz")
    return gzip.open(p, "rt", encoding="utf-8", errors="replace").read().split("\n")


if __name__ == "__main__":
    spec, pat = sys.argv[1], sys.argv[2]
    mx = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    rx = re.compile(pat, re.I)
    L = lines_of(spec)
    print("### %s /%s/ (total %d lines)" % (spec, pat, len(L)))
    n = 0
    for i, ln in enumerate(L, 1):
        if rx.search(ln):
            n += 1
            if n <= mx:
                print("%6d| %s" % (i, ln.strip()[:600]))
    print("   hits=%d" % n)
