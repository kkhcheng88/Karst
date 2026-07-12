"""thesis/magnifier_staleness.py -- detects when a magnifier node's score needs re-examination.

Per-node schema (thesis/themes.yaml, e.g. ai-power-grid's `nodes:` block, added 2026-07-12) each
carries `last_scored`. This script checks TWO triggers (user's own framing, 2026-07-12) and flags
a node as stale when either fires AFTER its last_scored date:

  1. NEW TRANSCRIPT for any of the node's tickers (thesis/corpus.db, thesistype='transcript') --
     re-uses the same data constraint_scan.py already reads.
  2. NEW ARTICLE touching any of the node's tickers (thesis/.raw/gooptions/research-manifest.json
     byTicker index -- {slug, role, publishedAt, issue} per ticker, already structured).

This does NOT re-score anything -- scoring is a human/session judgment call (NHITL, same
principle as theme_signal.py), not a formula. It only tells you WHICH nodes have new evidence
sitting unread. Nodes with tickers: [] (ETF-only legs like uranium-fuel/ipp-utilities) are
skipped for trigger checks (no per-ticker transcript/article to watch) -- they stay on whatever
cadence a human decides, noted as a known v1 gap rather than silently mis-handled.

Output: appends NEW stale flags (deduped against a state file, so reruns don't re-flag the same
trigger every week) to thesis/.raw/magnifier_review_queue.md -- persistent, tracked in git, same
human-triage-checklist convention as constraint_scan_queue.md.

Run: python thesis/magnifier_staleness.py
"""
from __future__ import annotations

import datetime
import json
import os
import sqlite3

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
THEMES_PATH = os.path.join(ROOT, "themes.yaml")
CORPUS_DB = os.path.join(ROOT, "corpus.db")
MANIFEST_PATH = os.path.join(ROOT, ".raw", "gooptions", "research-manifest.json")
STATE_PATH = os.path.join(ROOT, ".raw", "magnifier_staleness_state.json")
QUEUE_PATH = os.path.join(ROOT, ".raw", "magnifier_review_queue.md")


def _load_nodes():
    """slug -> [{name, tickers, last_scored}, ...] for every theme that has a nodes: block."""
    themes = (yaml.safe_load(open(THEMES_PATH, encoding="utf-8")) or {}).get("themes", {}) or {}
    out = {}
    for slug, t in themes.items():
        nodes = t.get("nodes")
        if nodes:
            out[slug] = nodes
    return out


def _latest_transcript_by_ticker():
    """ticker -> latest transcript 'published' date string, across the whole corpus."""
    con = sqlite3.connect(CORPUS_DB)
    rows = con.execute(
        "SELECT primary_ticker, MAX(published) FROM docs WHERE thesistype='transcript' "
        "AND primary_ticker IS NOT NULL AND primary_ticker != '' GROUP BY primary_ticker"
    ).fetchall()
    con.close()
    return {tk: pub for tk, pub in rows if pub}


def _latest_article_by_ticker():
    """ticker -> latest gooptions article publishedAt date string."""
    if not os.path.exists(MANIFEST_PATH):
        print(f"[magnifier_staleness] no gooptions manifest at {MANIFEST_PATH} -- "
              f"skipping article trigger")
        return {}
    manifest = json.load(open(MANIFEST_PATH, encoding="utf-8"))
    by_ticker = manifest.get("byTicker", {})
    out = {}
    for tk, entries in by_ticker.items():
        dates = [e.get("publishedAt") for e in entries if e.get("publishedAt")]
        if dates:
            out[tk] = max(dates)
    return out


def _load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)


def run():
    node_map = _load_nodes()
    if not node_map:
        print("[magnifier_staleness] no theme has a nodes: block yet -- nothing to check")
        return
    transcript_dates = _latest_transcript_by_ticker()
    article_dates = _latest_article_by_ticker()
    state = _load_state()
    today_str = datetime.date.today().isoformat()

    new_flags = []
    for slug, nodes in node_map.items():
        for node in nodes:
            name = node["name"]
            tickers = node.get("tickers") or []
            # YAML auto-parses unquoted dates to datetime.date; normalize to ISO string
            last_scored = str(node.get("last_scored", "1900-01-01"))
            key = f"{slug}/{name}"
            if not tickers:
                continue  # ETF-only leg -- no per-ticker trigger available, v1 known gap
            reasons = []
            for tk in tickers:
                t_date = transcript_dates.get(tk)
                if t_date and t_date > last_scored:
                    reasons.append(f"{tk} transcript {t_date}")
                a_date = article_dates.get(tk)
                if a_date and a_date > last_scored:
                    reasons.append(f"{tk} article {a_date}")
            if not reasons:
                continue
            trigger_sig = "|".join(sorted(reasons))
            if state.get(key) == trigger_sig:
                continue  # already flagged this exact evidence set, skip
            new_flags.append((slug, name, reasons))
            state[key] = trigger_sig

    _save_state(state)
    if not new_flags:
        print("[magnifier_staleness] no new stale nodes this run")
        return

    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    with open(QUEUE_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n## {today_str} magnifier staleness check\n")
        for slug, name, reasons in new_flags:
            f.write(f"- [ ] **{slug}/{name}** stale -- new evidence: {'; '.join(reasons)}\n")
    print(f"[magnifier_staleness] {len(new_flags)} node(s) newly stale -> {QUEUE_PATH}")
    for slug, name, reasons in new_flags:
        print(f"  {slug}/{name}: {'; '.join(reasons)}")


if __name__ == "__main__":
    run()
