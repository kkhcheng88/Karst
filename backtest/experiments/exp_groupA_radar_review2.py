# -*- coding: utf-8 -*-
import sqlite3
import json
import re

DB = r"C:\projects\Investment\Karst\thesis\corpus.db"

CONSTRAINT_PHRASES = ["sold out", "on allocation", "fully allocated", "supply constrained",
    "capacity constrained", "at capacity", "tight supply", "supply is tight",
    "lead times", "lead time", "supply shortage", "unable to meet demand",
    "demand exceeds supply", "outstripping supply", "take or pay", "long-term agreement",
    "pricing power", "constrained"]

TICKERS = ["ARW", "ATI", "CRS", "RS", "STLD", "KALU", "TEX", "OSK", "GNRC", "SPXC", "CAT"]

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

match_expr = " OR ".join(f'"{p}"' for p in CONSTRAINT_PHRASES)

# compile phrase regex (longest first to avoid partial overlap issues)
phrases_sorted = sorted(CONSTRAINT_PHRASES, key=len, reverse=True)
phrase_re = re.compile("(" + "|".join(re.escape(p) for p in phrases_sorted) + ")", re.IGNORECASE)

N_QUOTES = 8
CTX = 260

out_lines = []

for t in TICKERS:
    rows = con.execute(
        "SELECT d.slug, d.published, d.title, docs_fts_en.body as body "
        "FROM docs_fts_en JOIN docs d ON d.slug=docs_fts_en.slug "
        "WHERE d.primary_ticker=? AND d.thesistype='transcript' AND docs_fts_en MATCH ? "
        "ORDER BY d.published ASC",
        (t, match_expr)).fetchall()
    n = len(rows)
    out_lines.append(f"\n{'='*100}\n{t}: {n} matching transcripts (published range {rows[0]['published'] if n else '-'} to {rows[-1]['published'] if n else '-'})\n{'='*100}")
    if n == 0:
        continue
    # stratified sample across time
    if n <= N_QUOTES:
        idxs = list(range(n))
    else:
        idxs = sorted(set(round(i * (n - 1) / (N_QUOTES - 1)) for i in range(N_QUOTES)))
    for idx in idxs:
        r = rows[idx]
        body = r["body"]
        out_lines.append(f"\n--- {t} | {r['published']} | {r['slug']} | {r['title']} ---")
        # find first 2 distinct phrase occurrences in this doc
        found = 0
        seen_spans = []
        for m in phrase_re.finditer(body):
            if found >= 2:
                break
            s, e = m.start(), m.end()
            # skip if overlapping a previous shown span too closely
            if any(abs(s - ps) < 100 for ps in seen_spans):
                continue
            seen_spans.append(s)
            lo = max(0, s - CTX)
            hi = min(len(body), e + CTX)
            snippet = body[lo:hi].replace("\n", " ")
            out_lines.append(f"  [match: '{m.group(0)}']  ...{snippet}...")
            found += 1
        if found == 0:
            out_lines.append("  (no phrase found via regex - fallback needed)")

with open(r"C:\projects\Investment\Karst\backtest\experiments\_groupA_context_quotes.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))

print("done, wrote _groupA_context_quotes.txt")
