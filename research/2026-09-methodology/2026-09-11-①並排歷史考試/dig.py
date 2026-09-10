# -*- coding: utf-8 -*-
"""KARST-210 取證助手:在 204 已抽好的衝擊前 10-K 純文字裡找關鍵詞的上下文。

純文字檔幾乎沒有換行(整份是一兩條長行),故按**字元窗**搜,不按行。

⚠ **兩個真實陷阱,都親身踩過**:
(一)`docs/` 之下**每個事件一個資料夾**,遞歸 glob 會**跨事件資料夾**搜——例如 `docs/E08/`
裡有一份 NVDA 10-K 2025-02-26,申報日晚於 DeepSeek 界線,本來會靜靜進入 E07 的搜尋結果。
故輸出檔名**必帶事件資料夾名**。
(二)**同一事件資料夾內也可能混有界線後的申報**。傳第 5 個參數 `界線日` 會把申報日在該日或
之後的檔案標成 `!! 界線後,不得引用`;不傳則印 `!! 未傳界線日` 提醒自己核對。

用法:PYTHONUTF8=1 python dig.py <TICKER> <regex> [前後字元數] [最多幾筆] [界線日 YYYY-MM-DD]
"""
import glob
import os
import re
import sys

DOCS = ("C:/projects/Karst/research/2026-09-methodology/"
        "2026-09-10-①行業殺錯事件籃子/checklist_test/docs")


def main():
    tk, pat = sys.argv[1], sys.argv[2]
    win = int(sys.argv[3]) if len(sys.argv) > 3 else 420
    cap = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    cutoff = sys.argv[5] if len(sys.argv) > 5 else None
    fs = glob.glob(f"{DOCS}/**/{tk}__*.txt", recursive=True)
    rx = re.compile(pat, re.I)
    for f in fs:
        t = open(f, encoding="utf-8", errors="replace").read()
        bn = os.path.basename(f)
        evd = os.path.basename(os.path.dirname(f))
        m = re.search(r"_(\d{4}-\d{2}-\d{2})_", bn)
        d = m.group(1) if m else None
        if not d:
            flag = "  !! 日期未知,引用前先核申報日"
        elif cutoff and d >= cutoff:
            flag = "  !! 界線後(申報日 %s >= %s),不得引用" % (d, cutoff)
        elif not cutoff:
            flag = "  !! 未傳界線日,自行核對申報日"
        else:
            flag = "  ok 界線前(申報日 %s < %s)" % (d, cutoff)
        print("### FILE [%s] %s len %d %s" % (evd, bn, len(t), flag))
        n = 0
        for m in rx.finditer(t):
            if m.start() > 0 and t[m.start() - 1].isalnum() and m.group()[0].isalnum():
                continue
            ctx = t[max(0, m.start() - win):m.start() + win]
            if ctx.count("Member") > 2 or "us-gaap:" in ctx:
                continue
            n += 1
            if n > cap:
                print("... (cap %d)" % cap)
                break
            print("[%d] %s" % (m.start(), t[max(0, m.start() - win):m.start() + win]))
            print("-" * 70)


if __name__ == "__main__":
    main()
