# -*- coding: utf-8 -*-
"""由 批1/docs/ 的申報全文抽出「步一步四」要用的段落,逐家寫一份 extracts/<TICKER>.md。

只抽衝擊前申報(檔內已寫死申報日與界線),每段附行號與來源檔名,方便卡上寫出處。
匹配規矩:關鍵詞命中後取上下窗各 3 行、每段截 420 字;每節最多 8 段。
"""
import glob
import os
import re
import sys

BASE = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①v3全量回測/批1"
DOCS = BASE + "/docs"
OUT = BASE + "/extracts"

SECTIONS = [
    ("A 收入與分部", r"(net sales|total revenues?|net revenues?|reportable segment)"),
    ("B 客戶集中與合約", r"(accounted for|largest customer|significant customer|"
                    r"customer concentration|long[- ]term contract|contract term|renewal|"
                    r"termination for convenience|remaining performance obligation|backlog|"
                    r"deferred revenue)"),
    ("C 定價與毛利", r"(pricing|price increase|rebate|discount|gross margin|"
                 r"gross profit margin)"),
    ("D 競爭與替代", r"(competition|competitors|generic|alternative)"),
    ("E 財務與槓桿", r"(leverage|indebtedness|maturit|interest expense|credit facility|"
                 r"dividend|covenant)"),
    ("F 資本開支與產能", r"(capital expenditure|capital spending|capacity)"),
    ("G 需求與量", r"(units sold|subscribers?|members?|net additions|retention|"
                r"churn|same[- ]store|usage)"),
]

WINDOW = 2
CAP = 340
PER_SECTION = 5


def blocks(text):
    return text.splitlines()


def extract(path):
    lines = blocks(open(path, encoding="utf-8").read())
    head = lines[0][:200] if lines else ""
    out = [f"# {os.path.basename(path)}", head, ""]
    for title, pat in SECTIONS:
        rx = re.compile(pat, re.I)
        hits = []
        seen = set()
        for i, ln in enumerate(lines):
            if len(ln) < 25:
                continue
            if rx.search(ln):
                a, b = max(0, i - WINDOW), min(len(lines), i + WINDOW + 1)
                key = a // 2
                if key in seen:
                    continue
                seen.add(key)
                seg = " ".join(lines[a:b])[:CAP]
                hits.append(f"  L{i+1}: {seg}")
                if len(hits) >= PER_SECTION:
                    break
        out.append(f"## {title}")
        out.extend(hits if hits else ["  (無命中)"])
        out.append("")
    return "\n".join(out)


def main(tickers):
    os.makedirs(OUT, exist_ok=True)
    for tk in tickers:
        parts = []
        for p in sorted(glob.glob(f"{DOCS}/{tk}_*.txt")):
            parts.append(extract(p))
        with open(f"{OUT}/{tk}.md", "w", encoding="utf-8") as f:
            f.write("\n\n".join(parts))
        print(tk, os.path.getsize(f"{OUT}/{tk}.md"), "bytes")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        args = sorted({os.path.basename(p).split("_")[0] for p in glob.glob(f"{DOCS}/*.txt")})
    main(args)
