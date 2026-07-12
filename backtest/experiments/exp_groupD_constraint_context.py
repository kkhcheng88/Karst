"""
Group D discovery-radar review: pull constraint-language quotes with wide context
for 11 tickers (LEN, LEN-B, TOL, FSS, IIIN, LPX, MHK, EQR, AVB, ESS, WST).

Writes one text file per ticker to backtest/results/_scratch_groupD/<ticker>.txt
containing, for a time-spread sample of matching transcripts, the surrounding
~250-char context around each constraint-phrase hit (deduped/merged when hits
overlap), so a human/agent can judge STRONG vs FOLD vs WEAK vs UNCLEAR by reading
real sentences in context (not just short FTS snippets).
"""
import re
import sqlite3
from pathlib import Path

DB = r"C:\projects\Investment\Karst\thesis\corpus.db"
OUTDIR = Path(r"C:\projects\Investment\Karst\backtest\results\_scratch_groupD")
OUTDIR.mkdir(parents=True, exist_ok=True)

CONSTRAINT_PHRASES = [
    "sold out", "on allocation", "fully allocated", "supply constrained",
    "capacity constrained", "at capacity", "tight supply", "supply is tight",
    "lead times", "lead time", "supply shortage", "unable to meet demand",
    "demand exceeds supply", "outstripping supply", "take or pay", "long-term agreement",
    "pricing power", "constrained",
]

TICKERS = ["LEN", "LEN-B", "TOL", "FSS", "IIIN", "LPX", "MHK", "EQR", "AVB", "ESS", "WST"]

CONTEXT = 220
MAX_DOCS_PER_TICKER = 8
MAX_HITS_PER_DOC = 4


def find_hits(body: str):
    """Return list of (start, end, phrase) for each phrase occurrence, case-insensitive."""
    hits = []
    lower = body.lower()
    for p in CONSTRAINT_PHRASES:
        start = 0
        while True:
            idx = lower.find(p, start)
            if idx == -1:
                break
            hits.append((idx, idx + len(p), p))
            start = idx + len(p)
    hits.sort()
    return hits


def merge_hits(hits):
    """Merge overlapping/nearby hits (within CONTEXT of each other) into single windows."""
    if not hits:
        return []
    merged = []
    cur_start, cur_end, phrases = hits[0][0], hits[0][1], [hits[0][2]]
    for s, e, p in hits[1:]:
        if s <= cur_end + CONTEXT:
            cur_end = max(cur_end, e)
            phrases.append(p)
        else:
            merged.append((cur_start, cur_end, phrases))
            cur_start, cur_end, phrases = s, e, [p]
    merged.append((cur_start, cur_end, phrases))
    return merged


def pick_spread(docs, n):
    """Pick up to n docs spread across the list (already sorted by published asc)."""
    if len(docs) <= n:
        return docs
    idxs = [round(i * (len(docs) - 1) / (n - 1)) for i in range(n)]
    idxs = sorted(set(idxs))
    return [docs[i] for i in idxs]


def main():
    con = sqlite3.connect(DB)
    match = " OR ".join(f'"{p}"' for p in CONSTRAINT_PHRASES)
    for ticker in TICKERS:
        rows = con.execute(
            "SELECT d.slug, d.published, docs_fts_en.body FROM docs_fts_en "
            "JOIN docs d ON d.slug = docs_fts_en.slug "
            "WHERE d.primary_ticker = ? AND d.thesistype='transcript' AND docs_fts_en MATCH ? "
            "ORDER BY d.published ASC",
            (ticker, match),
        ).fetchall()

        out_path = OUTDIR / f"{ticker.replace('/', '_')}.txt"
        with out_path.open("w", encoding="utf-8") as f:
            f.write(f"TICKER: {ticker}\n")
            f.write(f"Total matching transcripts: {len(rows)}\n")
            if rows:
                f.write(f"Date range: {rows[0][1]} .. {rows[-1][1]}\n")
            f.write("=" * 100 + "\n\n")

            sample = pick_spread(rows, MAX_DOCS_PER_TICKER)
            for slug, published, body in sample:
                hits = find_hits(body)
                merged = merge_hits(hits)[:MAX_HITS_PER_DOC]
                f.write(f"--- DOC: {slug}  | published: {published} | total_raw_hits={len(hits)} ---\n")
                for (s, e, phrases) in merged:
                    ctx_start = max(0, s - CONTEXT)
                    ctx_end = min(len(body), e + CONTEXT)
                    snippet = body[ctx_start:ctx_end].replace("\n", " ")
                    snippet = re.sub(r"\s+", " ", snippet).strip()
                    f.write(f"  [phrases: {', '.join(sorted(set(phrases)))}]\n")
                    f.write(f"  ...{snippet}...\n\n")
                f.write("\n")
        print(f"{ticker}: {len(rows)} matching transcripts -> sampled {len(sample)} -> {out_path}")


if __name__ == "__main__":
    main()
