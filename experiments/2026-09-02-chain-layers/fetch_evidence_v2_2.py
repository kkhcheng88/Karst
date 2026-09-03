# -*- coding: utf-8 -*-
"""KARST-169 步驟二:抓公告類申報(8-K / 6-K / 20-F)作轉向日佐證。

這些不是 10-K,不入 data/sec/10k_text 共用快取(該快取按 README 只收 10-K 全文)。
本腳本只抽出要引用的句子,存為衍生物 out_v2_2/evidence_raw/<label>.txt,正本靠 URL 指回 EDGAR。

EDGAR:User-Agent `Casy Limited kaho.career@gmail.com`,≤8 req/s。
跑法: set PYTHONUTF8=1 && python fetch_evidence_v2_2.py
"""
from __future__ import annotations

import io
import json
import re
import time
from pathlib import Path

import requests
from lxml import html as LH

HERE = Path(__file__).resolve().parent
OUT = HERE / "out_v2_2"
RAW = OUT / "evidence_raw"
RAW.mkdir(parents=True, exist_ok=True)

UA = "Casy Limited kaho.career@gmail.com"
HEADERS = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
RATE = 8.0
_next = [0.0]
_WS = re.compile(r"[ \t\r\n ]+")
_sess = requests.Session()
_sess.headers.update(HEADERS)

DOCS = [
    ("CORZ_8K_2024-03-06", "1839341", "000162828024009396"),
    ("WULF_8K_2024-12-23", "1083301", "000095014224002980"),
    ("WULF_8K_2024-12-26", "1083301", "000095014224002999"),
    ("CIFR_8K_2025-09-25_item101", "1819989", "000095010325012168"),
    ("CIFR_8K_2025-09-25_item801", "1819989", "000119312525216393"),
    ("IREN_6K_2023-10-05", "1878848", "000114036123047077"),
    ("IREN_6K_2023-10-06", "1878848", "000114036123047243"),
    ("IREN_20F_FY2024", "1878848", "000162828024038677"),
    ("IREN_6K_2024-02-07", "1878848", "000114036124005947"),
    ("IREN_6K_2024-02-08", "1878848", "000114036124006216"),
    ("IREN_6K_2024-02-14", "1878848", "000114036124007666"),
    ("IREN_6K_2024-02-26", "1878848", "000114036124009334"),
    ("IREN_6K_2023-08-11", "1878848", "000114036123039183"),
    ("IREN_6K_2023-08-29", "1878848", "000114036123041550"),
]


def throttle():
    now = time.monotonic()
    slot = max(now, _next[0])
    _next[0] = slot + 1.0 / RATE
    w = slot - time.monotonic()
    if w > 0:
        time.sleep(w)


def get(url):
    last = None
    for i in range(3):
        throttle()
        try:
            r = _sess.get(url, timeout=90)
            r.raise_for_status()
            return r
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.0 + i)
    raise RuntimeError("%s: %s" % (url, last))


def clean(raw):
    doc = LH.fromstring(raw)
    for bad in doc.xpath("//script|//style"):
        bad.getparent().remove(bad)
    return _WS.sub(" ", " ".join(doc.itertext()))


def main():
    index = {}
    for label, cik, acc in DOCS:
        base = "https://www.sec.gov/Archives/edgar/data/%s/%s" % (cik, acc)
        meta = get(base + "/index.json").json()
        items = meta["directory"]["item"]
        texts = []
        for it in items:
            name = it["name"]
            if not name.lower().endswith((".htm", ".html")):
                continue
            if name.lower().startswith("r") and name.lower().endswith(".htm"):
                continue  # XBRL viewer fragments
            url = "%s/%s" % (base, name)
            try:
                txt = clean(get(url).content)
            except Exception as exc:  # noqa: BLE001
                txt = "FETCH-FAIL %s" % exc
            texts.append("### %s\n%s" % (url, txt))
        blob = "\n\n".join(texts)
        with io.open(RAW / (label + ".txt"), "w", encoding="utf-8") as f:
            f.write(blob)
        index[label] = {"cik": cik, "accession": acc, "base": base,
                        "docs": [it["name"] for it in items], "chars": len(blob)}
        print("%-30s %6d chars, %d files" % (label, len(blob), len(items)))
    (OUT / "evidence_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
