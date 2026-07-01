"""Karst thesis corpus -- SQLite FTS5 full-text store over the raw ingested reports.

Layer ① of the 3-layer knowledge design (see thesis/DESIGN.md):
  ① full text  -> here (SQLite FTS5, scales to millions; FNSPID etc. plug in the same way)
  ② source nodes (thin, linked) -> thesis/wiki/sources/*.md  (build_source_nodes.py)
  ③ synthesis   -> thesis/wiki/<thesis>.md  (hand/agent distilled)

Deterministic retrieval (legal-MCP research_cases pattern): search -> get -> verify_quote.
Trigram tokenizer so BOTH Chinese substrings and English/ticker terms match. DB is gitignored
(regenerable): re-run `build` any time (e.g. after downloading new reports).

    python thesis/corpus.py build
    python thesis/corpus.py search "HBM 定價權 bottleneck"
    python thesis/corpus.py ticker MU
    python thesis/corpus.py get 136-trend-core-research-baker-ai-constraint-worldview
    python thesis/corpus.py verify <slug> "a quote to check"
"""
import glob
import os
import re
import sqlite3
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "corpus.db")
SOURCES = {
    "gooptions-research": os.path.join(ROOT, ".raw", "gooptions", "research", "*.md"),
}


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


def connect():
    return sqlite3.connect(DB)


def build():
    if os.path.exists(DB):
        os.remove(DB)
    con = connect()
    con.executescript("""
        CREATE TABLE docs(
            id INTEGER PRIMARY KEY, slug TEXT UNIQUE, source TEXT, tier INTEGER,
            issue TEXT, url TEXT, published TEXT, thesistype TEXT, theme TEXT,
            primary_ticker TEXT, tickers TEXT, title TEXT, path TEXT, body TEXT);
        CREATE TABLE doc_tickers(doc_id INTEGER, ticker TEXT);
        CREATE INDEX ix_dt ON doc_tickers(ticker);
        CREATE VIRTUAL TABLE docs_fts USING fts5(
            slug UNINDEXED, title, theme, thesis, body, tokenize='trigram');
    """)
    n = 0
    for source, pattern in SOURCES.items():
        for path in sorted(glob.glob(pattern)):
            fm, fm_text, title, body = _parse_md(path)
            slug = fm.get("slug") or os.path.splitext(os.path.basename(path))[0]
            tickers = _fm_tickers(fm_text)
            # pull the one-line thesis from the "> **thesis:**" marker if present
            mth = re.search(r"\*\*thesis:\*\*\s*(.+)", body)
            thesis = mth.group(1).strip() if mth else ""
            cur = con.execute(
                "INSERT OR REPLACE INTO docs(slug,source,tier,issue,url,published,thesistype,"
                "theme,primary_ticker,tickers,title,path,body) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (_s(slug), _s(source), fm.get("tier"), _s(fm.get("issue", "")), _s(fm.get("url", "")),
                 _fm_scalar(fm_text, "publishedAt"), _s(fm.get("thesisType", "")), _s(fm.get("theme", "")),
                 _fm_scalar(fm_text, "primary_ticker"), ",".join(tickers), _s(title), _s(path), _s(body)))
            did = cur.lastrowid
            for tk in tickers:
                con.execute("INSERT INTO doc_tickers(doc_id,ticker) VALUES(?,?)", (did, tk))
            con.execute("INSERT INTO docs_fts(slug,title,theme,thesis,body) VALUES(?,?,?,?,?)",
                        (slug, title, fm.get("theme", ""), thesis, body))
            n += 1
    con.commit()
    con.close()
    print(f"[corpus] built {DB}: {n} docs indexed (FTS5 trigram).")


def _fts_query(q):
    # trigram MATCH: OR the tokens (concept-coverage, legal-MCP style) -> bm25 ranks docs that
    # hit more/rarer terms first. Trigram needs >=3 chars/token (2-char CJK terms can't index).
    toks = [f'"{t}"' for t in q.split() if len(t) >= 3]
    return " OR ".join(toks) if toks else f'"{q}"'


def search(q, limit=8):
    con = connect()
    rows = con.execute(
        "SELECT d.slug,d.issue,d.title,d.theme,d.thesistype,d.published,d.tickers,"
        "  snippet(docs_fts,4,'[',']','...',12) "
        "FROM docs_fts JOIN docs d ON d.slug=docs_fts.slug "
        "WHERE docs_fts MATCH ? ORDER BY bm25(docs_fts) LIMIT ?",
        (_fts_query(q), limit)).fetchall()
    con.close()
    print(f"[corpus] search {q!r} -> {len(rows)} hits")
    for slug, issue, title, theme, tt, pub, tks, snip in rows:
        print(f"\n  {issue} [{tt}] {pub}  {title[:60]}")
        print(f"    theme: {theme[:60]} | tickers: {tks[:60]}")
        print(f"    slug: {slug}")
        print(f"    ...{re.sub(chr(10),' ',snip)[:240]}...")
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
    r = con.execute("SELECT slug,issue,title,theme,published,thesistype,tickers,url,body "
                    "FROM docs WHERE slug=? OR slug LIKE ? OR path LIKE ? "
                    "ORDER BY length(slug) LIMIT 1",
                    (slug, f"%{slug}%", f"%{slug}%")).fetchone()
    con.close()
    if not r:
        print(f"[corpus] no doc: {slug}"); return None
    print(f"# {r[2]}\nissue {r[1]} | {r[4]} | {r[5]} | {r[3]}\ntickers: {r[6]}\nurl: {r[7]}\n")
    print(r[8][:4000])
    return r


def verify_quote(slug, quote):
    con = connect()
    r = con.execute("SELECT body FROM docs WHERE slug=? OR slug LIKE ? OR path LIKE ? "
                    "ORDER BY length(slug) LIMIT 1",
                    (slug, f"%{slug}%", f"%{slug}%")).fetchone()
    con.close()
    if not r:
        print("no doc"); return False
    norm = lambda s: re.sub(r"\s+", "", s)
    ok = norm(quote) in norm(r[0])
    print(f"[corpus] verify_quote({slug}): {'FOUND' if ok else 'NOT FOUND'}")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    arg = " ".join(sys.argv[2:])
    if cmd == "build":
        build()
    elif cmd == "search":
        search(arg)
    elif cmd == "ticker":
        by_ticker(arg)
    elif cmd == "get":
        get(arg)
    elif cmd == "verify":
        verify_quote(sys.argv[2], " ".join(sys.argv[3:]))
    else:
        print(__doc__)
