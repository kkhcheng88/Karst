"""Karst thesis corpus -- SQLite FTS5 full-text store over the raw ingested reports.

Layer ① of the 3-layer knowledge design (see thesis/DESIGN.md):
  ① full text  -> here (SQLite FTS5, scales to millions; FNSPID etc. plug in the same way)
  ② source nodes (thin, linked) -> thesis/wiki/sources/*.md  (build_source_nodes.py)
  ③ synthesis   -> thesis/wiki/<thesis>.md  (hand/agent distilled)

Sources indexed (SOURCES dict below -- add a new key + {"pattern","kind"} to plug in another):
  gooptions-research  thesis/.raw/gooptions/research/*.md          kind="md" (frontmatter+body)
  transcripts         thesis/.raw/transcripts/<TICKER>/<date>.json kind="transcript"
                      one doc per earnings call; doc_id = transcript-<TICKER>-<date>,
                      ticker/date parsed from the FOLDER PATH (not file content/frontmatter),
                      so an incremental build can decide to skip a file without opening it.

Deterministic retrieval (legal-MCP research_cases pattern): search -> get -> verify_quote.
Two FTS5 tables by language (2026-07-09): English transcripts -> docs_fts_en (porter unicode61:
word+stem, ~2.2x smaller, better English recall); Chinese gooptions -> docs_fts (trigram: substring
match). search() queries BOTH and merges by bm25. DB is gitignored (regenerable): re-run `build`
any time (e.g. after downloading new reports/transcripts).

Incremental by default -- slug (doc_id) existence in the DB is the skip key. These sources are
immutable once fetched (a published report / a closed earnings call never changes), so existence
is enough; no content-hash needed. Re-running `build` only indexes docs not already in the DB.
Pass --rebuild to drop the DB and re-index everything from scratch (e.g. after a schema change).

Scales to full-market (universe headed to ~6-7k tickers / 300-400k transcripts): the skip check
is a per-doc INDEXED seek on docs.slug (UNIQUE -> auto-index), NOT a linear scan of the table and
NOT a load-the-whole-DB-into-a-set. For transcripts the slug is derived from the folder path
(<TICKER>/<date>), so an already-indexed file is skipped WITHOUT being opened/parsed. FTS5 trigram
handles millions of rows; a big first run commits in batches and prints progress every N docs.

    python thesis/corpus.py build                    # incremental (default): index only new docs
    python thesis/corpus.py build --incremental       # same as default, explicit
    python thesis/corpus.py build --rebuild           # drop + full rebuild
    python thesis/corpus.py search "HBM 定價權 bottleneck"
    python thesis/corpus.py ticker MU
    python thesis/corpus.py get 136-trend-core-research-baker-ai-constraint-worldview
    python thesis/corpus.py verify <slug> "a quote to check"
"""
import glob
import json
import os
import re
import sqlite3
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "corpus.db")
SOURCES = {
    "gooptions-research": {
        "pattern": os.path.join(ROOT, ".raw", "gooptions", "research", "*.md"),
        "kind": "md",
    },
    "transcripts": {
        "pattern": os.path.join(ROOT, ".raw", "transcripts", "*", "*.json"),
        "kind": "transcript",
    },
}

SCHEMA_SQL = """
    CREATE TABLE docs(
        id INTEGER PRIMARY KEY, slug TEXT UNIQUE, source TEXT, tier INTEGER,
        issue TEXT, url TEXT, published TEXT, thesistype TEXT, theme TEXT,
        primary_ticker TEXT, tickers TEXT, title TEXT, path TEXT);
    CREATE TABLE doc_tickers(doc_id INTEGER, ticker TEXT);
    CREATE INDEX ix_dt ON doc_tickers(ticker);
    CREATE VIRTUAL TABLE docs_fts USING fts5(
        slug UNINDEXED, title, theme, thesis, body, tokenize='trigram');
    CREATE VIRTUAL TABLE docs_fts_en USING fts5(
        slug UNINDEXED, title, theme, thesis, body, tokenize='porter unicode61');
"""


def _parse_md(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    fm, fm_text, body = {}, "", text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            try:
                fm = yaml.safe_load(fm_text) or {}
            except Exception:
                fm = {}
            body = parts[2]
    mt = re.search(r"(?m)^#\s+(.+)$", body)
    title = mt.group(1).strip() if mt else fm.get("slug", "")
    return fm, fm_text, title, body.strip()


def _parse_transcript(path):
    """Parse a defeatbeta earnings-call transcript JSON (paragraph_number/speaker/content
    records -- see thesis/prefetch_transcripts.py for the exact shape). Ticker + report_date
    are NOT read from here (see module docstring) -- this only supplies title text + body."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    parts = []
    for p in data.get("paragraphs", []) or []:
        speaker = (p.get("speaker") or "").strip()
        content = (p.get("content") or "").strip()
        if not content:
            continue
        parts.append(f"{speaker}: {content}" if speaker else content)
    fy, fq = data.get("fiscal_year"), data.get("fiscal_quarter")
    fyq = f"FY{fy}Q{fq}" if fy and fq else ""
    return "\n\n".join(parts), fyq


def _fm_tickers(fm_text):
    """Read tickers as LITERAL strings (avoid YAML 1.1 coercing ON/NO/OFF/YES -> bool)."""
    m = re.search(r"(?m)^tickers:\s*\[(.*?)\]", fm_text)
    if not m:
        return []
    return [t.strip().strip("'\"") for t in m.group(1).split(",") if t.strip()]


def _fm_scalar(fm_text, key):
    m = re.search(rf"(?m)^{key}:\s*(.+?)\s*$", fm_text)
    if not m:
        return ""
    v = m.group(1).strip().strip("'\"")
    return "" if v in ("None", "null", "~") else v


def _s(v):
    return "" if v is None else str(v)


PROGRESS_EVERY = 1000    # print a progress line every N new docs indexed
COMMIT_EVERY = 5000      # commit in batches so a huge first run is resumable + bounds the journal
SCAN_HEARTBEAT = 50000   # on an all-skip incremental sweep, show life every N files scanned


def connect():
    return sqlite3.connect(DB)


def _has_slug(con, slug):
    """Skip check for incremental build. Indexed seek on docs.slug (UNIQUE -> auto-index):
    O(log N), NOT a linear table scan, and does NOT load the whole slug set into memory --
    this is what lets `build --incremental` stay cheap at full-market scale (100k+ docs).
    Sees rows inserted earlier in this same (uncommitted) transaction, so it also dedups
    within a single run."""
    return con.execute("SELECT 1 FROM docs WHERE slug=? LIMIT 1", (slug,)).fetchone() is not None


def _insert_doc(con, *, slug, source, tier, issue, url, published, thesistype, theme,
                 primary_ticker, tickers, title, path, body, thesis="", english=False):
    cur = con.execute(
        "INSERT OR REPLACE INTO docs(slug,source,tier,issue,url,published,thesistype,"
        "theme,primary_ticker,tickers,title,path) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (_s(slug), _s(source), tier, _s(issue), _s(url), _s(published), _s(thesistype),
         _s(theme), _s(primary_ticker), ",".join(tickers), _s(title), _s(path)))
    did = cur.lastrowid
    for tk in tickers:
        con.execute("INSERT INTO doc_tickers(doc_id,ticker) VALUES(?,?)", (did, tk))
    # Body lives ONLY in the FTS table (contentful), NOT duplicated in docs -> ~6GB saved.
    # FTS rowid is pinned to docs.id so get()/verify_quote() fetch the body by rowid (fast seek).
    # English transcripts -> porter unicode61 (word+stem, smaller); Chinese gooptions -> trigram.
    fts = "docs_fts_en" if english else "docs_fts"
    con.execute(f"INSERT INTO {fts}(rowid,slug,title,theme,thesis,body) VALUES(?,?,?,?,?,?)",
                (did, _s(slug), _s(title), _s(theme), _s(thesis), _s(body)))


def build(mode="incremental"):
    """mode='incremental' (default): only index slugs (doc_ids) not already in the DB.
    mode='rebuild': drop the DB (if present) and re-index every source from scratch."""
    do_rebuild = (mode == "rebuild") or not os.path.exists(DB)
    if do_rebuild and os.path.exists(DB):
        os.remove(DB)
    con = connect()
    if do_rebuild:
        con.executescript(SCHEMA_SQL)

    n_new, n_skip, n_seen = 0, 0, 0
    n_new_by_source = {}
    for source, spec in SOURCES.items():
        pattern, kind = spec["pattern"], spec["kind"]
        paths = sorted(glob.glob(pattern))
        print(f"[corpus] {source}: {len(paths)} files on disk to reconcile...", flush=True)
        for path in paths:
            n_seen += 1
            if n_seen % SCAN_HEARTBEAT == 0:
                print(f"[corpus]   ...scanned {n_seen} files "
                      f"({n_new} new, {n_skip} already indexed)", flush=True)
            if kind == "transcript":
                # ticker/date from the folder path -> slug WITHOUT opening the file, so an
                # already-indexed transcript is skipped by an indexed seek + zero file I/O
                ticker = os.path.basename(os.path.dirname(path))
                date = os.path.splitext(os.path.basename(path))[0]
                slug = f"transcript-{ticker}-{date}"
                if _has_slug(con, slug):
                    n_skip += 1
                    continue
                body, fyq = _parse_transcript(path)
                title = f"{ticker} {fyq} earnings call transcript ({date})".strip()
                _insert_doc(con, slug=slug, source=source, tier=None, issue="", url="",
                            published=date, thesistype="transcript", theme="",
                            primary_ticker=ticker, tickers=[ticker], title=title,
                            path=path, body=body, english=True)
            else:  # kind == "md"  (gooptions-research; future markdown sources plug in here)
                fm, fm_text, title, body = _parse_md(path)
                slug = fm.get("slug") or os.path.splitext(os.path.basename(path))[0]
                if _has_slug(con, slug):
                    n_skip += 1
                    continue
                tickers = _fm_tickers(fm_text)
                # pull the one-line thesis from the "> **thesis:**" marker if present
                mth = re.search(r"\*\*thesis:\*\*\s*(.+)", body)
                thesis = mth.group(1).strip() if mth else ""
                _insert_doc(con, slug=slug, source=source, tier=fm.get("tier"),
                            issue=fm.get("issue", ""), url=fm.get("url", ""),
                            published=_fm_scalar(fm_text, "publishedAt"),
                            thesistype=fm.get("thesisType", ""), theme=fm.get("theme", ""),
                            primary_ticker=_fm_scalar(fm_text, "primary_ticker"),
                            tickers=tickers, title=title, path=path, body=body, thesis=thesis)
            n_new += 1
            n_new_by_source[source] = n_new_by_source.get(source, 0) + 1
            if n_new % PROGRESS_EVERY == 0:
                print(f"[corpus]   indexed {n_new} new docs "
                      f"({n_seen} files scanned, {n_skip} skipped)...", flush=True)
            if n_new % COMMIT_EVERY == 0:
                con.commit()  # batch commit: resumable + bounds the WAL/journal on a huge run
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    n_transcripts = con.execute(
        "SELECT COUNT(*) FROM docs WHERE thesistype='transcript'").fetchone()[0]
    con.close()
    db_mb = os.path.getsize(DB) / 1_048_576 if os.path.exists(DB) else 0
    by_src = ", ".join(f"{k}={v}" for k, v in n_new_by_source.items()) or "none"
    print(f"[corpus] build ({'rebuild' if do_rebuild else 'incremental'}): "
          f"{n_new} new docs indexed ({by_src}); {n_skip} already indexed (skipped).")
    print(f"[corpus] {DB}: {total} docs total ({n_transcripts} transcripts), {db_mb:.1f} MB "
          f"(FTS5: transcripts=porter unicode61, gooptions=trigram).")


def _fts_query(q):
    # trigram MATCH: OR the tokens (concept-coverage, legal-MCP style) -> bm25 ranks docs that
    # hit more/rarer terms first. Trigram needs >=3 chars/token (2-char CJK terms can't index).
    toks = [f'"{t}"' for t in q.split() if len(t) >= 3]
    return " OR ".join(toks) if toks else f'"{q}"'


def search(q, limit=8):
    con = connect()
    # query BOTH FTS tables (trigram gooptions + porter-unicode61 transcripts) and merge by bm25.
    # bm25 is negative (lower=better) in each table; ordering the union by it is good-enough ranking.
    qy = _fts_query(q)
    per = (
        "SELECT d.slug,d.issue,d.title,d.theme,d.thesistype,d.published,d.tickers,"
        "  snippet({fts},4,'[',']','...',12) AS snip, bm25({fts}) AS r "
        "FROM {fts} JOIN docs d ON d.slug={fts}.slug WHERE {fts} MATCH ?")
    rows = con.execute(
        f"SELECT * FROM ({per.format(fts='docs_fts')} "
        f"UNION ALL {per.format(fts='docs_fts_en')}) ORDER BY r LIMIT ?",
        (qy, qy, limit)).fetchall()
    con.close()
    print(f"[corpus] search {q!r} -> {len(rows)} hits")
    for slug, issue, title, theme, tt, pub, tks, snip, _r in rows:
        print(f"\n  {issue} [{tt}] {pub}  {title[:60]}")
        print(f"    theme: {theme[:60]} | tickers: {tks[:60]}")
        print(f"    slug: {slug}")
        print(f"    ...{re.sub(chr(10),' ',snip)[:240]}...")
    return rows


CONSTRAINT_PHRASES = [
    # supply-constraint language, strongest -> weaker (earnings-call primary source)
    "sold out", "on allocation", "fully allocated", "supply constrained",
    "capacity constrained", "at capacity", "tight supply", "supply is tight",
    "lead times", "lead time", "supply shortage", "unable to meet demand",
    "demand exceeds supply", "outstripping supply", "take or pay", "long-term agreement",
    "pricing power", "constrained",
]


def scan(query=None, limit=40):
    """Phrase-mode supply-constraint scan over the ENGLISH transcript corpus (docs_fts_en,
    porter unicode61). Unlike search() (OR of single words = noisy), this matches EXACT
    PHRASES -- 'lead time' won't match 'lead' or 'time' alone. Pass a phrase to scan one;
    omit to scan the default CONSTRAINT_PHRASES set. bm25 ranks transcripts hitting the
    most/rarest constraint phrases first."""
    con = connect()
    phrases = [query] if query else CONSTRAINT_PHRASES
    match = " OR ".join(f'"{p}"' for p in phrases)
    rows = con.execute(
        "SELECT d.primary_ticker, d.published, d.slug, "
        "  snippet(docs_fts_en,4,'[',']','...',18) "
        "FROM docs_fts_en JOIN docs d ON d.slug=docs_fts_en.slug "
        "WHERE docs_fts_en MATCH ? ORDER BY bm25(docs_fts_en) LIMIT ?",
        (match, limit)).fetchall()
    con.close()
    label = query or f"{len(phrases)} constraint phrases"
    print(f"[corpus] scan [{label}] -> {len(rows)} transcript hits")
    for tk, pub, slug, snip in rows:
        print(f"  {tk:6} {pub}  ...{re.sub(chr(10),' ',snip)[:200]}...  ({slug})")
    return rows


def by_ticker(tk, limit=30):
    con = connect()
    rows = con.execute(
        "SELECT d.issue,d.published,d.thesistype,d.title,d.slug FROM doc_tickers t "
        "JOIN docs d ON d.id=t.doc_id WHERE t.ticker=? ORDER BY d.published DESC LIMIT ?",
        (tk.upper(), limit)).fetchall()
    con.close()
    print(f"[corpus] ticker {tk.upper()} -> {len(rows)} reports")
    for issue, pub, tt, title, slug in rows:
        print(f"  {issue} [{tt}] {pub}  {title[:60]}  ({slug})")
    return rows


def get(slug):
    con = connect()
    r = con.execute("SELECT id,slug,issue,title,theme,published,thesistype,tickers,url "
                    "FROM docs WHERE slug=? OR slug LIKE ? OR path LIKE ? "
                    "ORDER BY length(slug) LIMIT 1",
                    (slug, f"%{slug}%", f"%{slug}%")).fetchone()
    if not r:
        con.close(); print(f"[corpus] no doc: {slug}"); return None
    fts = "docs_fts_en" if r[6] == "transcript" else "docs_fts"
    br = con.execute(f"SELECT body FROM {fts} WHERE rowid=?", (r[0],)).fetchone()
    con.close()
    body = br[0] if br else ""
    print(f"# {r[3]}\nissue {r[2]} | {r[5]} | {r[6]} | {r[4]}\ntickers: {r[7]}\nurl: {r[8]}\n")
    print(body[:4000])
    return r


def verify_quote(slug, quote):
    con = connect()
    r = con.execute("SELECT id,thesistype FROM docs WHERE slug=? OR slug LIKE ? OR path LIKE ? "
                    "ORDER BY length(slug) LIMIT 1",
                    (slug, f"%{slug}%", f"%{slug}%")).fetchone()
    if not r:
        con.close(); print("no doc"); return False
    fts = "docs_fts_en" if r[1] == "transcript" else "docs_fts"
    br = con.execute(f"SELECT body FROM {fts} WHERE rowid=?", (r[0],)).fetchone()
    con.close()
    body = br[0] if br else ""
    norm = lambda s: re.sub(r"\s+", "", s)
    ok = norm(quote) in norm(body)
    print(f"[corpus] verify_quote({slug}): {'FOUND' if ok else 'NOT FOUND'}")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    rest = sys.argv[2:]
    arg = " ".join(rest)
    if cmd == "build":
        build(mode="rebuild" if "--rebuild" in rest else "incremental")
    elif cmd == "search":
        search(arg)
    elif cmd == "scan":
        scan(arg if arg else None)
    elif cmd == "ticker":
        by_ticker(arg)
    elif cmd == "get":
        get(arg)
    elif cmd == "verify":
        verify_quote(sys.argv[2], " ".join(sys.argv[3:]))
    else:
        print(__doc__)
