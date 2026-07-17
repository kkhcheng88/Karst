"""thesis/feishu_triage.py -- screen the Feishu IB-report catalog export against Karst themes.

The vendor sells individual IB reports (~39/day median in the sample export). Buying blind is
waste; today's six real IB PDFs all came out NEUTRAL through INGEST, so the buy-worthy yield is
low and the screen exists to protect the wallet. This script reads the catalog Excel export
(9 columns: title/bank/summary/category/digest/tags/filename/pages/date, one report = 3 rows)
and shortlists only reports touching the 17 active themes.

Rule (2026-07-17, source registry): the vendor's digests are AI-generated -- use them to FIND,
never as evidence. Evidence = the PDF itself, through the normal INGEST pipeline.

Run: PYTHONUTF8=1 python thesis/feishu_triage.py <catalog.xlsx> [--days N]
Output: markdown shortlist to stdout (pipe to a file if wanted).
"""
from __future__ import annotations

import re
import sys
from collections import Counter

import openpyxl

# Theme tickers (from themes.yaml, see thesis/.raw/ima_triage_query.md for the per-theme map)
TICKERS = [
    "AAOI", "AEHR", "AMKR", "AMZN", "ASML", "ASTS", "ASX", "ATI", "AVGO", "AXTI", "BE", "BKSY",
    "CAT", "CHPX", "CLS", "COHR", "COP", "CRS", "CVX", "DRAM", "EQT", "ETN", "FN", "FORM", "FOTO",
    "FSLR", "GEV", "GLW", "GNRC", "GOOGL", "GRID", "GSAT", "HEI", "INTC", "KLAC", "KLIC", "KMI",
    "KTOS", "LITE", "LNG", "LOAR", "LPX", "LRCX", "LUNR", "LWLG", "MAGS", "META", "MKSI", "MP",
    "MPWR", "MRVL", "MSFT", "MU", "NASA", "NVTS", "ON", "PL", "PWR", "QQQ", "RDW", "REMX", "RKLB",
    "SEI", "SIVE", "SKHY", "SMH", "SNDK", "SPCX", "SPXC", "STX", "TER", "TSM", "TTMI", "TXN",
    "URA", "USAC", "USAR", "UTES", "VICR", "VRT", "WDC", "WOLF", "WST", "XLE", "XOM",
]
KEYWORDS = [
    "半导体", "先进封装", "混合键合", "玻璃基板", "CoWoS", "CoPoS", "HBM", "DRAM", "NAND", "EUV",
    "High-NA", "800V", "HVDC", "数据中心", "SiC", "GaN", "光通", "CPO", "硅光", "稀土", "太空",
    "卫星", "GLP-1", "天然气", "台积电", "英伟达", "美光", "博通", "NVIDIA", "TSMC", "Micron",
    "Broadcom", "hyperscaler", "资本开支",
]

# Tickers that collide with English words / domain terms; only count in title/tags, not prose
# (CRS = cytokine release syndrome in biotech prose; GLW/FN etc. are fine)
RISKY = {"ON", "BE", "PL", "ASX", "CAT", "SEI", "CRS", "MP", "URA", "GRID"}


def load_reports(path: str) -> list[dict]:
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.worksheets[0]
    out = []
    for r in ws.iter_rows(values_only=True):
        if r and r[0]:
            out.append({
                "title": str(r[0]), "bank": str(r[1] or ""), "summary": str(r[2] or ""),
                "cat": str(r[3] or ""), "tags": str(r[5] or ""), "fname": str(r[6] or ""),
                "date": str(r[8] or "")[:10],
            })
    return out


def screen(reports: list[dict]) -> list[tuple[int, list[str], dict]]:
    hits = []
    for rep in reports:
        blob = " ".join([rep["title"], rep["summary"], rep["tags"], rep["fname"]])
        blob_u = blob.upper()
        matched: list[str] = []
        for t in TICKERS:
            if re.search(r"\b" + t + r"\b", blob_u):
                if t in RISKY and not re.search(r"\b" + t + r"\b", rep["title"].upper() + " " + rep["tags"].upper()):
                    continue  # risky short ticker only counts in title/tags, not prose
                matched.append(t)
        for k in KEYWORDS:
            if k.isascii():
                # latin keywords need word boundaries ("GaN" must not match "MorGAN")
                if re.search(r"\b" + re.escape(k.upper()) + r"\b", blob_u):
                    matched.append(k)
            elif k in blob:
                matched.append(k)
        if matched:
            hits.append((len(matched), matched, rep))
    hits.sort(key=lambda x: (x[2]["date"], x[0]), reverse=True)
    return hits


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    reports = load_reports(sys.argv[1])
    days = None
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])
        cutoff = sorted({r["date"] for r in reports})[-days:]
        reports = [r for r in reports if r["date"] in cutoff]
    hits = screen(reports)
    print(f"# 飛書研報目錄篩選 — {len(hits)}/{len(reports)} 份掂到 17 個 active theme\n")
    print("| 日期 | 命中 | 投行 | 標題 | 對應 |")
    print("|---|---|---|---|---|")
    for n, matched, rep in hits:
        tags = ", ".join(dict.fromkeys(matched))[:60]
        print(f"| {rep['date']} | {n} | {rep['bank'].split('(')[0][:14]} | {rep['title'][:58]} | {tags} |")
    print(f"\n> 只做「搵」;買咗返嚟先算證據(行 INGEST)。基準預期:六份真投行 PDF 全 NEUTRAL,")
    print(f"> 買之前問「佢有冇 filing 級硬數據 / 二階新名」,冇就唔好買。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
