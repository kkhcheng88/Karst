"""
Extraction helper for 2026-07-11 discovery radar review (group B: MCHP, ASMLF, ASML,
AVT, AMAT, ADI, VSH, FSLR).

Pulls a time-spread sample of transcript quotes per ticker matching the constraint-
language phrase list, with wide context windows, for manual verbatim review against
Karst's evidence bar (own-transcript, own-voice, structural -- not analyst-report
metadata tags, not one-off/seasonal/generic business language).

Writes one text file per ticker to backtest/results/_scratch_groupB/<ticker>.txt
for the reviewing agent to read. This script + those scratch files are the audit
trail behind backtest/results/2026-07-11_discovery_radar_review_groupB.md.
"""
import re
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "thesis" / "corpus.db"
OUT_DIR = Path(__file__).resolve().parents[2] / "backtest" / "results" / "_scratch_groupB"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CONSTRAINT_PHRASES = [
    "sold out", "on allocation", "fully allocated", "supply constrained",
    "capacity constrained", "at capacity", "tight supply", "supply is tight",
    "lead times", "lead time", "supply shortage", "unable to meet demand",
    "demand exceeds supply", "outstripping supply", "take or pay", "long-term agreement",
    "pricing power", "constrained",
]

TICKERS = ["MCHP", "ASMLF", "ASML", "AVT", "AMAT", "ADI", "VSH", "FSLR"]

N_QUARTERS = 8
CONTEXT = 220


def get_docs(con, ticker):
    cur = con.cursor()
    match = " OR ".join(f'"{p}"' for p in CONSTRAINT_PHRASES)
    rows = cur.execute(
        "SELECT d.slug, d.published, docs_fts_en.body FROM docs_fts_en "
        "JOIN docs d ON d.slug = docs_fts_en.slug "
        "WHERE d.primary_ticker=? AND d.thesistype='transcript' AND docs_fts_en MATCH ? "
        "ORDER BY d.published ASC",
        (ticker, match),
    ).fetchall()
    seen = set()
    out = []
    for slug, published, body in rows:
        if slug in seen:
            continue
        seen.add(slug)
        out.append((slug, published, body))
    return out


def spread_indices(n, k):
    if n <= k:
        return list(range(n))
    # always include first and last, spread the rest evenly, then force in the
    # 2 most recent explicitly (recency matters for "is this still current")
    idxs = sorted(set(round(i * (n - 1) / (k - 1)) for i in range(k)))
    for extra in (n - 1, n - 2):
        if extra not in idxs and extra >= 0:
            idxs.append(extra)
    return sorted(set(idxs))[-k:] if len(set(idxs)) > k else sorted(set(idxs))


def extract_contexts(body, slug, published):
    out = []
    low = body.lower()
    seen_spans = []
    for phrase in CONSTRAINT_PHRASES:
        start = 0
        hits_this_phrase = 0
        while hits_this_phrase < 3:
            idx = low.find(phrase, start)
            if idx == -1:
                break
            span_start, span_end = idx, idx + len(phrase)
            # skip if overlapping an already-captured window (avoid dup spam from
            # "lead time" also matching inside "lead times")
            if any(not (span_end < s0 or span_start > s1) for s0, s1 in seen_spans):
                start = idx + len(phrase)
                continue
            ctx_start = max(0, idx - CONTEXT)
            ctx_end = min(len(body), idx + len(phrase) + CONTEXT)
            snippet = body[ctx_start:ctx_end].replace("\n", " ")
            out.append((phrase, snippet))
            seen_spans.append((span_start - CONTEXT, span_end + CONTEXT))
            start = idx + len(phrase)
            hits_this_phrase += 1
    return out


def main():
    con = sqlite3.connect(DB)
    for ticker in TICKERS:
        rows = get_docs(con, ticker)
        n = len(rows)
        if n == 0:
            (OUT_DIR / f"{ticker}.txt").write_text(f"{ticker}: NO MATCHES\n", encoding="utf-8")
            print(ticker, "NO MATCHES")
            continue
        idxs = spread_indices(n, N_QUARTERS)
        lines = [f"{ticker}: {n} matching transcripts total, showing {len(idxs)} spread across time\n"]
        for i in idxs:
            slug, published, body = rows[i]
            lines.append(f"\n=== {ticker} | {published} | {slug} ===")
            contexts = extract_contexts(body, slug, published)
            if not contexts:
                lines.append("  (no direct phrase hit found in body re-scan -- check FTS tokenization)")
            for phrase, snippet in contexts:
                lines.append(f"  [{phrase}] ...{snippet}...")
        text = "\n".join(lines)
        (OUT_DIR / f"{ticker}.txt").write_text(text, encoding="utf-8")
        print(ticker, "docs:", n, "sampled:", len(idxs), "-> wrote", f"{ticker}.txt")
    con.close()


if __name__ == "__main__":
    main()
