"""
One-off fact extraction: scan local EDGAR submissions cache for filings
in the 2026-08-01 to 2026-08-31 window that are commonly associated with
forced-selling / index-eligibility events (spin-offs, bankruptcies,
delistings, completed M&A, stock-for-stock mergers, new listings, and
large-holder position changes).

No judgment calls are made here beyond the category matching rules
spelled out below. Output is a CSV of individual filings plus a plain
English summary.
"""
import csv
import json
import os
from pathlib import Path

SUBMISSIONS_DIR = Path(r"C:\projects\Karst\data\sec\submissions")
OUT_DIR = Path(r"C:\projects\Karst\research\2026-09-methodology")
CSV_PATH = OUT_DIR / "2026-08-forced-selling-filings.csv"
SUMMARY_PATH = OUT_DIR / "2026-08-forced-selling-summary.txt"

WINDOW_START = "2026-08-01"
WINDOW_END = "2026-08-31"

FORM10_FORMS = {"10-12B", "10-12B/A", "10-12G", "10-12G/A"}
S4_425_FORMS = {"S-4", "S-4/A", "425"}
FORM_8A_FORMS = {"8-A12B"}
SC13D_FORMS = {"SC 13D", "SC 13D/A", "SCHEDULE 13D", "SCHEDULE 13D/A"}


def in_window(filing_date):
    return WINDOW_START <= filing_date <= WINDOW_END


def classify(form, items):
    """Return list of category numbers (a filing can match >1 category)."""
    cats = []
    item_list = [i.strip() for i in items.split(",")] if items else []

    if form in FORM10_FORMS:
        cats.append(1)
    if form == "8-K" and "1.03" in item_list:
        cats.append(2)
    if form == "8-K" and "3.01" in item_list:
        cats.append(3)
    if form == "8-K" and "2.01" in item_list:
        cats.append(4)
    if form in S4_425_FORMS:
        cats.append(5)
    if form in FORM_8A_FORMS:
        cats.append(6)
    if form in SC13D_FORMS:
        cats.append(7)
    return cats


def main():
    rows = []
    sc13d_count = 0
    company_count = 0
    latest_filing_date_seen = ""

    json_files = sorted(SUBMISSIONS_DIR.glob("*.json"))

    for fp in json_files:
        company_count += 1
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        items_list = recent.get("items", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        name = data.get("name", "")
        cik = data.get("cik", "")
        tickers = ";".join(data.get("tickers", []) or [])

        n = len(forms)
        for i in range(n):
            filing_date = dates[i] if i < len(dates) else ""
            if filing_date > latest_filing_date_seen:
                latest_filing_date_seen = filing_date

            if not in_window(filing_date):
                continue

            form = forms[i] if i < len(forms) else ""
            items = items_list[i] if i < len(items_list) else ""
            accession = accessions[i] if i < len(accessions) else ""
            primary_doc = primary_docs[i] if i < len(primary_docs) else ""

            cats = classify(form, items)
            if not cats:
                continue

            for cat in cats:
                if cat == 7:
                    sc13d_count += 1
                    continue  # SC 13D: count only, do not list row-by-row
                rows.append({
                    "category": cat,
                    "form": form,
                    "items": items,
                    "filingDate": filing_date,
                    "cik": cik,
                    "name": name,
                    "tickers": tickers,
                    "accessionNumber": accession,
                    "primaryDocument": primary_doc,
                })

    rows.sort(key=lambda r: (r["category"], r["filingDate"]))

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "category", "form", "items", "filingDate", "cik", "name",
            "tickers", "accessionNumber", "primaryDocument",
        ])
        writer.writeheader()
        writer.writerows(rows)

    cat_names = {
        1: "Form 10 (10-12B/10-12G spin-off registration)",
        2: "8-K Item 1.03 (bankruptcy)",
        3: "8-K Item 3.01 (delisting / non-compliance notice)",
        4: "8-K Item 2.01 (completed acquisition or disposition)",
        5: "S-4/425 (stock-for-stock merger documents)",
        6: "8-A12B (new securities listing registration)",
    }
    counts = {c: 0 for c in cat_names}
    for r in rows:
        counts[r["category"]] += 1

    lines = []
    lines.append("2026-08 forced-selling-related EDGAR filing scan")
    lines.append("Window: %s to %s" % (WINDOW_START, WINDOW_END))
    lines.append("Companies scanned (local submissions cache files): %d" % company_count)
    lines.append("Latest filingDate observed anywhere in cache (any date, any form): %s" % latest_filing_date_seen)
    lines.append("")
    lines.append("Counts by category:")
    for c in sorted(cat_names):
        lines.append("  %d. %s: %d" % (c, cat_names[c], counts[c]))
    lines.append("  7. SC 13D / SC 13D/A (large holder position changes): %d" % sc13d_count)
    lines.append("")
    lines.append("Total row-level filings written to CSV (excludes SC 13D count-only category): %d" % len(rows))
    lines.append("CSV: %s" % CSV_PATH.name)

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
