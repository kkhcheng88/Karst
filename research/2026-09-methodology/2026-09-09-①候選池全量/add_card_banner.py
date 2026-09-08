"""KARST-188 交檔前補丁:在十四張 B 層卡片頂部加一格抽數口徑警示。

背景:排序表在取數缺陷更正與第二次抽價之後重出過一次(舊版留在
ranking_60.prev.csv),但卡片是照第一次抽數寫的。十四家之中 58 個數值格
變動超過 0.5%,兩家的數二/賠率正負號翻轉(AGX、CRNC)。卡片結論無一改變,
所以內文不動,只在頂部標明「引數字要引正本」。

只在第一行標題之後插入;已插入過的檔會換成最新版標記(可重複執行)。
標點一律用半形,與同目錄其他檔一致。
"""
import glob
import os

BASE = (r"C:\projects\Karst\research\2026-09-methodology"
        "\\2026-09-09-\u2460\u5019\u9078\u6c60\u5168\u91cf")

BANNER = (
    "> \u26a0 **\u672c\u5361\u5167\u6587\u7684\u6a5f\u68b0\u5c64\u6578\u5b57"
    "\u662f\u7b2c\u4e00\u6b21\u62bd\u6578\u7684\u503c\u3002**"
    "\u6392\u5e8f\u8868\u5176\u5f8c\u56e0\u53d6\u6578\u7f3a\u9677\u66f4\u6b63"
    "\u8207\u7b2c\u4e8c\u6b21\u62bd\u50f9\u800c\u91cd\u51fa"
    "(\u820a\u7248\u7559\u5728 `ranking_60.prev.csv`),"
    "\u5341\u56db\u5bb6\u4e4b\u4e2d\u6709 58 \u500b\u6578\u503c\u683c"
    "\u8b8a\u52d5\u8d85\u904e 0.5%;"
    "**\u5341\u56db\u5f35\u5361\u7121\u4e00\u7d50\u8ad6\u56e0\u6b64\u6539"
    "\u8b8a**,\u6240\u4ee5\u5167\u6587\u4fdd\u7559\u539f\u62bd\u6578"
    "\u7684\u6578\u5b57\u3002"
    "**\u8981\u5f15\u7528\u6578\u5b57,\u4e00\u5f8b\u4ee5 "
    "`ranking_60.md`\u3001`card_inputs.md` "
    "\u8207\u7e3d\u89bd\u70ba\u6e96\u3002**"
    "\u539f\u56e0\u8207\u5f8c\u679c\u898b\u7e3d\u89bd 6.3\u3002"
)

MARK = "\u672c\u5361\u5167\u6587\u7684\u6a5f\u68b0\u5c64\u6578\u5b57"


def main():
    files = sorted(glob.glob(os.path.join(
        BASE, "B-*-\u52a0\u6a21\u578b\u5224\u65b7.md")))
    added, replaced = [], []
    for p in files:
        with open(p, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        hit = [i for i, ln in enumerate(lines) if MARK in ln]
        if hit:
            lines[hit[0]] = BANNER
            replaced.append(os.path.basename(p))
        else:
            lines.insert(1, "")
            lines.insert(2, BANNER)
            added.append(os.path.basename(p))
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines))
    print("\u65b0\u52a0:%d\u3001\u66f4\u65b0:%d"
          % (len(added), len(replaced)))


if __name__ == "__main__":
    main()
