"""KARST-142: fetch 10-K MD&A (Item 7) sections from EDGAR free API.

Rules enforced here:
  - User-Agent header required by SEC: "Karst research karst@example.com"
  - rate limit <= 10 req/s (we sleep 0.2s between requests, ~5 req/s)
  - raw texts land in ./texts/ which is gitignored (large-file rule)

Run: PYTHONUTF8=1 python fetch_mdna.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
TEXTS = HERE / "texts"
TEXTS.mkdir(exist_ok=True)
RAW = TEXTS / "raw"
RAW.mkdir(exist_ok=True)

TICKERS_JSON = Path(r"C:\projects\Karst\data\sec\company_tickers.json")

UA = "Karst research karst@example.com"
HEADERS = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
SLEEP = 0.2  # ~5 req/s, well under the 10 req/s cap

# (ticker, fiscal_year_label, arm)  arm: "bottleneck" | "normal"
# Frozen in bottleneck-lexicon-v0.md section 6 before any text was read.
SAMPLE = [
    ("ENPH", 2021, "bottleneck"), ("ENPH", 2019, "normal"),
    ("GNRC", 2021, "bottleneck"), ("GNRC", 2019, "normal"),
    ("ROK", 2022, "bottleneck"), ("ROK", 2019, "normal"),
    ("POWL", 2024, "bottleneck"), ("POWL", 2019, "normal"),
    ("BE", 2024, "bottleneck"), ("BE", 2019, "normal"),
    # ETN was the original 6th name in the frozen sample. Dropped 2026-09-02 for
    # a purely structural reason, before any MD&A text had been read: Eaton
    # incorporates its MD&A by reference from Exhibit 13, so the 10-K body has
    # no Item 7 prose to score. Replaced by CMI (Cummins), same bottleneck
    # thesis (FY2021 semiconductor/supply constraint vs FY2019 normal).
    ("CMI", 2021, "bottleneck"), ("CMI", 2019, "normal"),
]

_session = requests.Session()
_session.headers.update(HEADERS)


def get(url: str) -> requests.Response:
    time.sleep(SLEEP)
    r = _session.get(url, timeout=60)
    r.raise_for_status()
    return r


def load_cik_map() -> dict[str, str]:
    data = json.loads(TICKERS_JSON.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for key, row in data.items():
        if isinstance(row, dict):  # SEC upstream shape: {"0": {ticker, cik_str}}
            out[row["ticker"].upper()] = str(row["cik_str"]).zfill(10)
        else:  # local cache shape: {"NVDA": "0001045810"}
            out[str(key).upper()] = str(row).zfill(10)
    return out


def find_10k(cik: str, fy: int) -> tuple[str, str, str]:
    """Return (accession_nodash, primary_doc, report_date) for the 10-K whose
    period of report falls in fiscal year `fy`."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    sub = get(url).json()
    recent = sub["filings"]["recent"]
    rows = list(zip(
        recent["form"], recent["accessionNumber"],
        recent["primaryDocument"], recent["reportDate"], recent["filingDate"],
    ))
    # older filings live in separate files
    for extra in sub["filings"].get("files", []):
        ex = get(f"https://data.sec.gov/submissions/{extra['name']}").json()
        rows += list(zip(
            ex["form"], ex["accessionNumber"],
            ex["primaryDocument"], ex["reportDate"], ex["filingDate"],
        ))

    cands = []
    for form, acc, doc, rdate, fdate in rows:
        if form != "10-K" or not rdate:
            continue
        y, m = int(rdate[:4]), int(rdate[5:7])
        # fiscal year label: a period ending Jan-Jun belongs to the prior FY label
        fy_label = y if m >= 7 else y - 1
        # calendar-year filers (Dec end) -> fy_label == y, which is what we want
        if m == 12:
            fy_label = y
        if fy_label == fy:
            cands.append((rdate, acc.replace("-", ""), doc, fdate))
    if not cands:
        raise LookupError(f"no 10-K for FY{fy}")
    cands.sort()
    rdate, acc, doc, fdate = cands[-1]
    return acc, doc, f"{rdate} (filed {fdate})"


# NOTE (2026-09-02): EDGAR filings use the curly apostrophe U+2019 in
# "Management's Discussion". Matching only the ASCII "'" silently sent 8 of 12
# documents down the full-document fallback, which would have dragged Item 1A
# Risk Factors into the sample and broken exclusion rule R2 of the lexicon.
APOS = r"[\'‘’ʼ`]?"
ITEM7_START = re.compile(
    rf"item\s*7\s*[.\-:–—]?\s*management{APOS}s\s+discussion", re.I)
# Only Item 7A ends the section. Accepting "Item 8 - Financial Statements" as
# an end marker mis-terminated BE FY2019 on a cross-reference sentence buried
# in the body, yielding the table of contents instead of the MD&A.
ITEM7_END = re.compile(
    r"item\s*7a\s*[.\-:–—]?\s*quantitative\s+and\s+qualitative", re.I)


def extract_mdna(text: str) -> tuple[str, str]:
    """Return (mdna_text, how).

    A 10-K names Item 7 several times: once in the table of contents, several
    times as a cross-reference from other Items, and once as the real section
    heading. Take the candidate that yields the LONGEST Item 7 -> Item 7A span:
    the TOC and cross-reference hits produce spans of a few hundred characters,
    the real body produces tens of thousands.
    """
    starts = [m.start() for m in ITEM7_START.finditer(text)]
    if not starts:
        return text, "FULL-DOC-FALLBACK(no Item 7 marker)"
    spans = []
    for s in starts:
        ends = [m.start() for m in ITEM7_END.finditer(text) if m.start() > s + 2000]
        if ends:
            spans.append((s, ends[0]))
    # The table-of-contents hit pairs with the table-of-contents Item 7A (tiny
    # span, filtered by MIN). A cross-reference hit sitting in Item 1 or 1A
    # pairs with the *body* Item 7A, so it spans the whole Risk Factors
    # section -- much LONGER than the real body. The real heading is therefore
    # the SMALLEST span that is still a plausible MD&A.
    MIN = 15000
    ok = [sp for sp in spans if sp[1] - sp[0] >= MIN]
    if ok:
        s, e = min(ok, key=lambda sp: sp[1] - sp[0])
        return text[s:e], f"Item7..Item7A (min-span of {len(spans)} cands)"
    if spans:
        s, e = max(spans, key=lambda sp: sp[1] - sp[0])
        return text[s:e], f"Item7..Item7A (max-span fallback, {len(spans)} cands)"
    s = starts[-1]
    return text[s:s + 200000], "Item7..EOF-cap"


def main() -> int:
    cikmap = load_cik_map()
    manifest = []
    for ticker, fy, arm in SAMPLE:
        cik = cikmap.get(ticker)
        if not cik:
            print(f"!! {ticker}: no CIK", file=sys.stderr)
            continue
        try:
            acc, doc, period = find_10k(cik, fy)
        except Exception as exc:  # noqa: BLE001
            print(f"!! {ticker} FY{fy}: {exc}", file=sys.stderr)
            continue
        url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}")
        # Cache the raw filing so re-extraction never re-hits EDGAR.
        raw = RAW / f"{ticker}_FY{fy}_{arm}.html"
        if raw.exists():
            html = raw.read_text(encoding="utf-8", errors="replace")
        else:
            try:
                html = get(url).text
            except Exception as exc:  # noqa: BLE001
                print(f"!! {ticker} FY{fy} fetch: {exc}", file=sys.stderr)
                continue
            raw.write_text(html, encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text("\n")
        text = re.sub(r"\xa0", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text)
        mdna, how = extract_mdna(text)

        out = TEXTS / f"{ticker}_FY{fy}_{arm}_mdna.txt"
        out.write_text(mdna, encoding="utf-8")
        rec = {
            "ticker": ticker, "fy": fy, "arm": arm, "cik": cik,
            "period": period, "url": url, "extract": how,
            "chars": len(mdna), "est_tokens": round(len(mdna) / 4),
            "full_doc_chars": len(text),
        }
        manifest.append(rec)
        print(f"OK {ticker} FY{fy} {arm:10s} {rec['chars']:>8d} chars "
              f"~{rec['est_tokens']:>6d} tok  [{how}]  {period}")

    (HERE / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(manifest)}/12 documents fetched -> {TEXTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
