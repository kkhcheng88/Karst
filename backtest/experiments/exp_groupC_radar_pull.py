"""Pull constraint-language matches for Group C (energy/materials) discovery radar tickers.
Dumps wide-context snippets (body around match) per ticker, spread across quarters, to a text file
for manual verbatim review. Not a permanent pipeline script -- one-off review aid.
"""
import sqlite3
import re
import json

DB = r"C:\projects\Investment\Karst\thesis\corpus.db"
OUT = r"C:\projects\Investment\Karst\backtest\experiments\exp_groupC_radar_pull_output.txt"

TICKERS = ["USAC", "NOV", "TNRSF", "TS", "HAL", "EPD", "PTEN", "BTU", "KMI", "ALB"]

CONSTRAINT_PHRASES = ["sold out", "on allocation", "fully allocated", "supply constrained",
    "capacity constrained", "at capacity", "tight supply", "supply is tight",
    "lead times", "lead time", "supply shortage", "unable to meet demand",
    "demand exceeds supply", "outstripping supply", "take or pay", "long-term agreement",
    "pricing power", "constrained"]

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

match_q = " OR ".join(f'"{p}"' for p in CONSTRAINT_PHRASES)

out_lines = []

for ticker in TICKERS:
    out_lines.append(f"\n{'='*100}\n### TICKER: {ticker}\n{'='*100}")
    rows = con.execute(
        "SELECT d.slug, d.published, docs_fts_en.body AS body FROM docs_fts_en "
        "JOIN docs d ON d.slug = docs_fts_en.slug "
        "WHERE d.primary_ticker=? AND d.thesistype='transcript' AND docs_fts_en MATCH ? "
        "ORDER BY d.published DESC",
        (ticker, match_q)
    ).fetchall()
    out_lines.append(f"Total matching transcripts: {len(rows)}")

    if not rows:
        out_lines.append("NO MATCHES FOUND.")
        continue

    # spread across quarters: take up to 8, prioritizing spread (not just most recent)
    n = len(rows)
    if n <= 8:
        selected = list(rows)
    else:
        # pick evenly spaced indices across the sorted (desc) list to get spread across time
        idxs = sorted(set(int(round(i * (n - 1) / 7)) for i in range(8)))
        selected = [rows[i] for i in idxs]

    for row in selected:
        slug = row["slug"]
        published = row["published"]
        body = row["body"] or ""
        out_lines.append(f"\n--- {slug} | published={published} ---")
        # find all phrase occurrences, print +-250 chars context, dedupe overlapping
        lower_body = body.lower()
        spans = []
        for phrase in CONSTRAINT_PHRASES:
            for m in re.finditer(re.escape(phrase.lower()), lower_body):
                spans.append((m.start(), m.end(), phrase))
        spans.sort()
        # merge nearby spans (within 100 chars) to avoid duplicate context blocks
        merged = []
        for s in spans:
            if merged and s[0] - merged[-1][1] < 150:
                merged[-1] = (merged[-1][0], max(merged[-1][1], s[1]), merged[-1][2] + "," + s[2])
            else:
                merged.append(list(s))
        # cap number of context blocks per doc to keep output manageable
        for s in merged[:6]:
            start = max(0, s[0] - 250)
            end = min(len(body), s[1] + 250)
            ctx = body[start:end].replace("\n", " ")
            out_lines.append(f"  [{s[2]}] ...{ctx}...")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))

print(f"Wrote {len(out_lines)} lines to {OUT}")
