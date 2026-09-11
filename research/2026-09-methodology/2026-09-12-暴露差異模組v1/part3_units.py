# -*- coding: utf-8 -*-
"""KARST-218 第三部:由 `docs/part3/` 的申報原文抽出「卡上點名的收入單位」。

**只讀 docs/part3/(已入 .gitignore),不寫任何既有目錄**;抽出結果落本票 `out/part3_單位抽出.csv`。
做法:每家一組關鍵詞(卡上點名的單位),逐份申報找含關鍵詞的句子,原句照錄,不加工。
本檔只做抽取,判詞由人寫在 `表——十一家經營結果.md`。
"""
from __future__ import annotations

import os
import re

import pandas as pd

ROOT = "C:/projects/Karst"
HERE = f"{ROOT}/research/2026-09-methodology/2026-09-12-暴露差異模組v1"
DOCS = f"{HERE}/docs/part3"

KEY = {
    "T": ["wireless service revenues", "postpaid", "net adds", "churn", "ARPU",
          "wireless revenues", "upgrade"],
    "SPG": ["occupancy", "base minimum rent", "comparable propert", "leasing spread",
            "FFO per share", "rental revenue", "re-leas"],
    "ED": ["weather-adjusted", "rate plan", "steam sales", "electric sales",
           "firm gas", "rate base", "revenue requirement"],
    "RMD": ["device", "mask", "flow generator", "gross margin", "unit",
            "sleep", "patients", "resupply"],
    "KO": ["unit case volume", "concentrate sales", "price/mix", "organic revenue",
           "sparkling soft drink", "bottling", "share"],
    "MDLZ": ["volumes", "pricing", "organic net revenue", "market share",
             "gum", "biscuit", "chocolate"],
    "MU": ["bit shipments", "DRAM", "NAND", "average selling price", "HBM",
           "capacity", "inventory"],
    "AAPL": ["iPhone", "Services revenue", "installed base", "Greater China",
             "gross margin", "wearables", "Mac"],
    "SWKS": ["Huawei", "broad markets", "content", "average selling price",
             "design win", "pervasive", "5G"],
    "MSFT": ["remaining performance obligation", "commercial bookings",
             "Microsoft 365", "Azure", "seat", "Copilot", "commercial cloud"],
    "DUOL": ["MAU", "DAU", "paid subscribers", "bookings", "subscription",
             "max", "family plan"],
}

NUM = re.compile(r"(\d[\d,\.]*\s?(?:%|percent|million|billion|basis points)|\$\s?\d[\d,\.]*)",
                 re.I)


def sentences(txt):
    t = re.sub(r"\s+", " ", txt)
    for s in re.split(r"(?<=[.;])\s+", t):
        if 40 <= len(s) <= 400:
            yield s.strip()


def main():
    rows = []
    for fn in sorted(os.listdir(DOCS)):
        if not fn.endswith(".txt"):
            continue
        _, tk, tag = fn.split("_")[0], fn.split("_")[1], fn.split("_")[2]
        if tk not in KEY:
            continue
        with open(os.path.join(DOCS, fn), encoding="utf-8", errors="ignore") as g:
            txt = g.read()
        seen = set()
        for s in sentences(txt):
            low = s.lower()
            for k in KEY[tk]:
                if k.lower() in low and NUM.search(s):
                    key = (k, s[:120])
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(dict(ticker=tk, 關鍵詞=k, tag=tag, 檔名=fn,
                                     原句=s[:400]))
                    break
    d = pd.DataFrame(rows)
    d.to_csv(f"{HERE}/out/part3_單位抽出.csv", index=False, encoding="utf-8-sig")
    print("抽出句子", len(d), "條;每檔平均",
          round(len(d) / max(1, d["檔名"].nunique()), 1))
    print(d.groupby("ticker").size().to_string())


if __name__ == "__main__":
    main()
