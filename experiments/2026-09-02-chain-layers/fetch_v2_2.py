# -*- coding: utf-8 -*-
"""KARST-169 步驟一:把 v2.2 要用的年報補入共用快取,並列出 8-K 申報索引。

D-134 單一快取:全文只入 C:\\projects\\Karst\\data\\sec\\10k_text\\<TICKER>_<accession>.txt.gz,
manifest.jsonl 逐行 append(別隊同時在寫,只准 append)。抓前先查 manifest。
EDGAR:User-Agent `Casy Limited kaho.career@gmail.com`,≤8 req/s,fetchedBy = KARST-169。

**不碰 data/sec/submissions/**(KARST-167 隊同時在寫),submissions 快取寫入本票目錄 out_v2_2/。

跑法: set PYTHONUTF8=1 && python fetch_v2_2.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from lxml import html as LH

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out_v2_2"
OUT.mkdir(parents=True, exist_ok=True)

CACHE = REPO / "data" / "sec" / "10k_text"
MANIFEST = CACHE / "manifest.jsonl"

UA = "Casy Limited kaho.career@gmail.com"
HEADERS = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
RATE = 8.0
_next = [0.0]

TICKETS = "KARST-169"

TARGETS = {
    "CORZ": "0001839341",
    "IREN": "0001878848",
    "WULF": "0001083301",
    "CIFR": "0001819989",
    "HOOD": "0001783879",
}

# 只補 2023 年之後申報的 10-K(轉向期在 2023–2025)
MIN_FILING_DATE = "2023-01-01"

_WS = re.compile(r"[ \t\r\n\u00a0]+")
_sess = requests.Session()
_sess.headers.update(HEADERS)


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
            r = _sess.get(url, timeout=60)
            r.raise_for_status()
            return r
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.0 + i)
    raise RuntimeError("%s: %s" % (url, last))


def read_manifest():
    out = {}
    if not MANIFEST.exists():
        return out
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        acc = rec.get("accession")
        if acc:
            out[(rec.get("ticker"), acc)] = rec
    return out


def append_manifest(rec):
    with open(MANIFEST, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()


def submissions(cik):
    p = OUT / ("subs_%s.json" % cik)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    sub = get("https://data.sec.gov/submissions/CIK%s.json" % cik).json()
    blocks = [sub["filings"]["recent"]]
    for extra in sub["filings"].get("files", []):
        blocks.append(get("https://data.sec.gov/submissions/%s" % extra["name"]).json())
    rows = []
    for b in blocks:
        for form, acc, doc, rdate, fdate, items in zip(
            b["form"], b["accessionNumber"], b["primaryDocument"],
            b["reportDate"], b["filingDate"], b.get("items", [""] * len(b["form"])),
        ):
            rows.append({"form": form, "accession": acc.replace("-", ""), "doc": doc,
                         "reportDate": rdate, "filingDate": fdate, "items": items})
    rows.sort(key=lambda r: r["filingDate"])
    p.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def clean(raw):
    doc = LH.fromstring(raw)
    for bad in doc.xpath("//script|//style"):
        bad.getparent().remove(bad)
    return _WS.sub(" ", " ".join(doc.itertext()))


def main():
    have = read_manifest()
    print("manifest rows: %d" % len(have))
    index = {}
    fetched = []
    for tk, cik in TARGETS.items():
        rows = submissions(cik)
        tens = [r for r in rows if r["form"] == "10-K" and r["filingDate"] >= MIN_FILING_DATE]
        eights = [r for r in rows if r["form"].startswith("8-K")]
        index[tk] = {"cik": cik, "10-K": tens, "8-K_count": len(eights)}
        for r in tens:
            acc = r["accession"]
            cpath = CACHE / ("%s_%s.txt.gz" % (tk, acc))
            if (tk, acc) in have and cpath.exists():
                print("  cache hit %s %s (%s)" % (tk, acc, r["filingDate"]))
                continue
            url = "https://www.sec.gov/Archives/edgar/data/%d/%s/%s" % (int(cik), acc, r["doc"])
            raw = get(url).content
            full = clean(raw)
            blob = full.encode("utf-8")
            cpath.write_bytes(gzip.compress(blob))
            append_manifest({
                "ticker": tk, "cik": cik, "accession": acc, "form": "10-K",
                "filingDate": r["filingDate"], "reportDate": r["reportDate"],
                "url": url, "chars": len(full),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "fetchedBy": TICKETS, "primaryDoc": r["doc"],
            })
            fetched.append("%s %s %s" % (tk, acc, r["filingDate"]))
            print("  FETCHED %s %s (%s)" % (tk, acc, r["filingDate"]))
    (OUT / "filing_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print("newly fetched: %d" % len(fetched))
    for f in fetched:
        print("   ", f)


if __name__ == "__main__":
    raise SystemExit(main())
