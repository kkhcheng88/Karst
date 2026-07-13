"""thesis/news_watch.py -- narrow-band kill-axis news watcher.

Motivation (user-set design, 2026-07-13): news is CONTEXT, not a signal. A generic news feed is a
noise generator -- forbidden. This watcher listens ONLY to the specific keyword axes distilled from
each active theme's kill_condition (thesis/themes.yaml), configured by hand in
thesis/news_watch_keywords.yaml (thesis/DESIGN.md's non-negotiable #3: "falsifiable kill_condition").

Trigger case: on 2026-07-13, SK Hynix's "HBM ASP came in below expectations" news crashed the Korean
stock 15% (US memory names -5% premarket) -- but NO price sensor caught it (a 5% premarket move is a
"normal day" for a high-vol name). The only way to catch it is knowing "HBM ASP" is a kill axis
keyword for the memory-supercycle theme. This script's first live run (2026-07-13) verified it
catches exactly that story.

Pipeline per theme (thesis/news_watch_keywords.yaml order = themes.yaml's rough confidence-desc
order, used as the tie-break priority when the global cap truncates):
  1. fetch Google News RSS per query (free, no key): one polite (0.5-1s) delay between requests.
     A single query's network/parse failure is caught and recorded in failed_queries -- it does NOT
     abort the run (thesis/DESIGN.md discipline: partial data beats a crashed batch job).
  2. keep only items published within the last 48h (defense-in-depth: the RSS "when:2d" server-side
     window is a hint, not a guarantee -- this script re-checks pubDate itself).
  3. title must contain at least one significant token from the query (the "narrow band" filter --
     Google's own relevance ranking is looser than a literal title match; this is deliberately
     stricter, per spec, to keep noise out. Known limitation: short ambiguous tokens (e.g. "HBM" as
     a ticker collision with an unrelated Swiss healthcare fund) can false-positive; downstream reads
     this as CONTEXT to verify, not ground truth).
  4. near-duplicate collapse: the same real-world story reported by multiple outlets collapses to one
     item (title-similarity via difflib, scored after stripping the trailing " - <source>" suffix
     Google News appends).
  5. cross-run dedup against thesis/.raw/news_watch_seen.json (title-similarity within the same
     theme, pruned to a 14-day rolling window) -- a story already surfaced does not get re-pushed.
  6. cap 3 items/theme/day, 8 items globally/day (theme order = priority when truncating).

Output: thesis/.raw/news_watch.json ({generated_at, items[], failed_queries[], ...}, gitignored,
regenerable) + a stdout Traditional-Chinese summary. Downstream (the premarket briefing) reads the
json -- wiring that is a separate task, not this script's job.

Run: python thesis/news_watch.py [--verbose] [--simulate-failure "<query substring>"]
     (--simulate-failure is a test hook: forces that one query's fetch to fail, to prove a single
     query's network failure does not crash the whole run -- see thesis/daily_news_watch.cmd)
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))            # thesis/
KEYWORDS_PATH = os.path.join(ROOT, "news_watch_keywords.yaml")
OUT_PATH = os.path.join(ROOT, ".raw", "news_watch.json")
SEEN_PATH = os.path.join(ROOT, ".raw", "news_watch_seen.json")

RSS_BASE = "https://news.google.com/rss/search"
UA = "Mozilla/5.0 (compatible; Karst-research/1.0; private research; news_watch.py)"
LOOKBACK_HOURS = 48
PER_THEME_CAP = 3
GLOBAL_CAP = 8
SEEN_RETENTION_DAYS = 14
DUP_SIMILARITY_THRESHOLD = 0.6
PAUSE_MIN, PAUSE_MAX = 0.5, 1.0  # polite delay between query fetches, seconds

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "to", "and", "or", "vs", "with", "by", "at",
    "is", "are", "new", "its",
}


# ============================================================================
# fetch + parse
# ============================================================================

def build_rss_url(query: str) -> str:
    q = urllib.parse.quote(f"{query} when:{LOOKBACK_HOURS // 24}d")
    return f"{RSS_BASE}?q={q}&hl=en-US&gl=US&ceid=US:en"


def fetch_rss(query: str, force_bad_host: bool = False, timeout: int = 20) -> str:
    """Raises on any network/HTTP failure -- caller is responsible for catching per-query."""
    url = build_rss_url(query)
    if force_bad_host:
        # test hook for --simulate-failure: point at a host that cannot resolve/respond
        url = url.replace("https://news.google.com", "https://news.google.invalid-test-host")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, text/xml"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def parse_items(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        return []
    out = []
    for it in channel.findall("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub_raw = (it.findtext("pubDate") or "").strip()
        src_el = it.find("source")
        source_name = (src_el.text or "").strip() if src_el is not None and src_el.text else None
        source_url = src_el.get("url") if src_el is not None else None
        try:
            published_dt = parsedate_to_datetime(pub_raw) if pub_raw else None
            if published_dt is not None and published_dt.tzinfo is None:
                published_dt = published_dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            published_dt = None
        if not title or not link or published_dt is None:
            continue
        out.append({
            "title": title,
            "link": link,
            "published_dt": published_dt,
            "source_name": source_name,
            "source_url": source_url,
        })
    return out


# ============================================================================
# filtering
# ============================================================================

def significant_tokens(query: str) -> list[str]:
    words = re.split(r"\s+", query.lower())
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


def title_matches_query(title: str, query: str) -> bool:
    tokens = significant_tokens(query)
    if not tokens:
        return True
    title_l = title.lower()
    return any(t in title_l for t in tokens)


def within_lookback(published_dt: datetime, now: datetime) -> bool:
    return (now - published_dt) <= timedelta(hours=LOOKBACK_HOURS) and published_dt <= now + timedelta(hours=1)


def normalize_title_core(title: str, source_name: str | None) -> str:
    """Strip Google News' trailing ' - <Source Name>' suffix, then normalize for similarity
    comparison (lowercase, punctuation stripped, whitespace collapsed)."""
    core = title
    if source_name:
        suffix = f" - {source_name}"
        if core.endswith(suffix):
            core = core[: -len(suffix)]
    else:
        # fall back: strip a trailing ' - <Words>' pattern generically
        core = re.sub(r"\s+-\s+[^-]{2,40}$", "", core)
    core = re.sub(r"[^\w\s]", " ", core.lower())
    core = re.sub(r"\s+", " ", core).strip()
    return core


def is_near_duplicate(core: str, existing_cores: list[str]) -> bool:
    for other in existing_cores:
        if difflib.SequenceMatcher(None, core, other).ratio() >= DUP_SIMILARITY_THRESHOLD:
            return True
    return False


# ============================================================================
# seen-state (cross-run dedup)
# ============================================================================

def load_seen() -> list[dict]:
    if not os.path.exists(SEEN_PATH):
        return []
    try:
        with open(SEEN_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("seen", [])
    except (OSError, json.JSONDecodeError):
        return []


def prune_seen(seen: list[dict], now: datetime) -> list[dict]:
    cutoff = now - timedelta(days=SEEN_RETENTION_DAYS)
    kept = []
    for entry in seen:
        try:
            ts = datetime.fromisoformat(entry["first_seen"])
        except (KeyError, ValueError):
            continue
        if ts >= cutoff:
            kept.append(entry)
    return kept


def is_seen(theme: str, core: str, seen: list[dict]) -> bool:
    for entry in seen:
        if entry.get("theme") != theme:
            continue
        if difflib.SequenceMatcher(None, core, entry.get("title_core", "")).ratio() >= DUP_SIMILARITY_THRESHOLD:
            return True
    return False


def save_seen(seen: list[dict]) -> None:
    os.makedirs(os.path.dirname(SEEN_PATH), exist_ok=True)
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"seen": seen}, f, ensure_ascii=False, indent=2)


# ============================================================================
# main pipeline
# ============================================================================

def load_keywords() -> dict:
    with open(KEYWORDS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["themes"]


def run(verbose: bool = False, simulate_failure: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    themes = load_keywords()
    seen = prune_seen(load_seen(), now)

    failed_queries: list[dict] = []
    per_theme_selected: dict[str, list[dict]] = {}
    queries_run = 0

    for theme, spec in themes.items():
        queries = spec.get("queries", [])
        candidates: list[dict] = []
        candidate_cores: list[str] = []
        for i, q in enumerate(queries):
            query_text = q["query"]
            direction = q["direction"]
            if i > 0:
                time.sleep(random.uniform(PAUSE_MIN, PAUSE_MAX))
            queries_run += 1
            force_bad = bool(simulate_failure) and simulate_failure.lower() in query_text.lower()
            try:
                xml_text = fetch_rss(query_text, force_bad_host=force_bad)
                items = parse_items(xml_text)
            except Exception as e:  # noqa: BLE001 -- one bad query must never sink the whole run
                failed_queries.append({"theme": theme, "query": query_text, "error": f"{type(e).__name__}: {e}"})
                if verbose:
                    print(f"[news_watch]   FAILED  {theme} / \"{query_text}\": {type(e).__name__}: {e}")
                continue
            if verbose:
                print(f"[news_watch]   fetched {theme} / \"{query_text}\": {len(items)} raw items")

            for it in items:
                if not within_lookback(it["published_dt"], now):
                    continue
                if not title_matches_query(it["title"], query_text):
                    continue
                core = normalize_title_core(it["title"], it["source_name"])
                if is_near_duplicate(core, candidate_cores):
                    continue
                if is_seen(theme, core, seen):
                    continue
                candidate_cores.append(core)
                candidates.append({
                    "theme": theme,
                    "query": query_text,
                    "direction": direction,
                    "title": it["title"],
                    "source": it["source_name"],
                    "url": it["link"],
                    "published": it["published_dt"].isoformat(),
                    "_core": core,
                })

        candidates.sort(key=lambda c: c["published"], reverse=True)
        per_theme_selected[theme] = candidates[:PER_THEME_CAP]

    # global cap: flatten in theme (= keywords.yaml, roughly confidence-desc) order
    final_items: list[dict] = []
    for theme in themes:
        for c in per_theme_selected.get(theme, []):
            if len(final_items) >= GLOBAL_CAP:
                break
            final_items.append(c)
        if len(final_items) >= GLOBAL_CAP:
            break

    # record newly-surfaced items into seen state
    for c in final_items:
        seen.append({"theme": c["theme"], "title_core": c["_core"], "url": c["url"],
                      "first_seen": now.isoformat()})
    save_seen(seen)

    for c in final_items:
        c.pop("_core", None)

    report = {
        "generated_at": now.isoformat(),
        "lookback_hours": LOOKBACK_HOURS,
        "themes_scanned": len(themes),
        "queries_run": queries_run,
        "items": final_items,
        "failed_queries": failed_queries,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


DIRECTION_ZH = {"kill-confirming": "轉弱", "kill-relieving": "紓緩"}


def print_summary(report: dict) -> None:
    items = report["items"]
    print(f"[news_watch] {report['generated_at']} -- 掃咗 {report['themes_scanned']} 個主題 / "
          f"{report['queries_run']} 條 query,past {report['lookback_hours']}h")
    if not items:
        print("[news_watch] 今日冇捉到新命中(可能全部已喺 seen 狀態,或者過去 48h 冇相關新聞)")
    else:
        by_theme: dict[str, list[dict]] = {}
        for it in items:
            by_theme.setdefault(it["theme"], []).append(it)
        for theme, its in by_theme.items():
            print(f"[news_watch] == {theme} ({len(its)}) ==")
            for it in its:
                zh_dir = DIRECTION_ZH.get(it["direction"], it["direction"])
                print(f"[news_watch]   [{zh_dir}] {it['title']} ({it['source']}, {it['published']})")
                print(f"[news_watch]        query=\"{it['query']}\"  {it['url']}")
    if report["failed_queries"]:
        print(f"[news_watch] {len(report['failed_queries'])} 條 query 失敗(唔影響其餘結果):")
        for f in report["failed_queries"]:
            print(f"[news_watch]   {f['theme']} / \"{f['query']}\": {f['error']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verbose", action="store_true", help="print per-query fetch detail")
    ap.add_argument("--simulate-failure", metavar="QUERY_SUBSTR", default=None,
                     help="test hook: force any query containing this substring to fail (network "
                          "error), to prove one query's failure doesn't crash the run")
    args = ap.parse_args()
    report = run(verbose=args.verbose, simulate_failure=args.simulate_failure)
    print_summary(report)
    print(f"[news_watch] wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
