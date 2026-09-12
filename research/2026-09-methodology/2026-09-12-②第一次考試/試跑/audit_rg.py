# -*- coding: utf-8 -*-
"""KARST-228 核查工具 v2:在某一事件的「包內文件」與「包列本地文件」中做**正則**搜尋。
用法: PYTHONUTF8=1 python audit_rg.py E001 "<regex>" [maxhits]
"""
import gzip, io, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_lookup import packet_txt_path, local_files, CACHE


def targets(e):
    out = [(packet_txt_path(e), "packet")]
    for fn, label in local_files(e):
        out.append((os.path.join(CACHE, fn), label + " / " + fn))
    return out


def lines_of(path):
    if path.endswith(".packet.txt"):
        return io.open(path, encoding="utf-8").read().split("\n"), True
    if not os.path.exists(path):
        return None, False
    return gzip.open(path, "rt", encoding="utf-8", errors="replace").read().split("\n"), True


def run(e, pat, mx=3, cap=400):
    rx = re.compile(pat, re.I)
    total = 0
    for path, label in targets(e):
        L, ok = lines_of(path)
        if not ok:
            print("   MISSING %s" % label)
            continue
        off = 10 ** 9
        if path.endswith(".packet.txt"):
            for i, l in enumerate(L, 1):
                if l.startswith("[2_觸發資料.ex991_full_text]"):
                    off = i
                    break
        tag = "EX-99.1" if path.endswith(".packet.txt") and off < 10 ** 9 else label
        n = 0
        for i, ln in enumerate(L, 1):
            if rx.search(ln):
                n += 1
                total += 1
                if n <= mx:
                    loc = ("EX-99.1 line %d (packet.txt:%d)" % (i - off + 1, i)) if i > off else ("packet.txt:%d" % i)
                    print("   @%s | %s" % (loc if path.endswith(".packet.txt") else "%s :%d" % (label, i), ln.strip()[:cap]))
        if n:
            print("   [%s] hits=%d" % (tag, n))
    print("   TOTAL=%d" % total)


if __name__ == "__main__":
    e, pat = sys.argv[1], sys.argv[2]
    mx = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    print("### %s /%s/" % (e, pat))
    run(e, pat, mx)
