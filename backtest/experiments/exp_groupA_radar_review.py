import sqlite3
import re
import json

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

out = {}
for t in TICKERS:
    rows = con.execute(
        "SELECT d.slug, d.published, d.title, "
        "snippet(docs_fts_en,4,'[',']','...',25) as snip "
        "FROM docs_fts_en JOIN docs d ON d.slug=docs_fts_en.slug "
        "WHERE d.primary_ticker=? AND d.thesistype='transcript' AND docs_fts_en MATCH ? "
        "ORDER BY d.published DESC",
        (t, match_expr)).fetchall()
    out[t] = [dict(r) for r in rows]
    print(f"{t}: {len(rows)} matching transcripts")

with open(r"C:\projects\Investment\Karst\backtest\experiments\_groupA_raw_matches.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("done")
