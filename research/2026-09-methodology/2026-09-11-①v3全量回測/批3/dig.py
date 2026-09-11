# -*- coding: utf-8 -*-
"""KARST-214(批 3)取證小工具:在衝擊前 10-K 純文字內找一段,印出上下文。

用法:PYTHONUTF8=1 python dig.py <檔案> <正則> [前後字數=160] [最多幾段=6]
只讀;不動任何既有檔。行 6 那份 XBRL 標頭(head 之前)一律跳過,免得印刷式雜訊。
"""
import io
import os
import re
import sys

HEAD = 3000  # 前 3000 字(XBRL context 段)不搜


def main():
    path = sys.argv[1]
    pat = sys.argv[2]
    pad = int(sys.argv[3]) if len(sys.argv) > 3 else 160
    cap = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    t = io.open(path, encoding="utf-8", errors="replace").read()
    body = t[HEAD:]
    print("### %s | 全文 %d 字" % (os.path.basename(path), len(t)))
    n = 0
    for m in re.finditer(pat, body, re.I):
        s = max(0, m.start() - pad)
        e = min(len(body), m.end() + pad)
        snip = re.sub(r"\s+", " ", body[s:e]).strip()
        # 跳過 XBRL context / taxonomy 那一大段雜訊
        if snip.count("us-gaap:") >= 2 or "fasb.org" in snip or "iso4217" in snip:
            continue
        print("--- @%d ---" % (m.start() + HEAD))
        print(snip)
        n += 1
        if n >= cap:
            print("(已達上限 %d 段)" % cap)
            break
    if n == 0:
        print("(找不到)")


if __name__ == "__main__":
    main()
