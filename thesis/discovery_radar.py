"""Full-market transcript constraint-language DISCOVERY radar (not a backtest).

User framing (2026-07-10, objective B correction): "It doesn't need to map with GICS. The
transcript itself is similar to the analyst article to give us hints on what is potentially
missing or undergoing price action. It is for us to study the subject matter and validate it.
And once validate it form the early new thesis."

Surfaces tickers with RECENT + PERSISTENT supply-constraint language in their own earnings-call
transcripts that are NOT already covered by an existing Phase-3 theme (thesis/themes.yaml).
Sector label shown is INFORMATIONAL ONLY (quick triage context for the human reviewer) -- it
plays no role in the ranking/filtering logic itself, unlike the (separate, GICS-mapped) sector
rotation experiment.

Output is a CANDIDATE list only. Nothing here is auto-added to any thesis -- each candidate
needs the same manual research + validation discipline used today for CIEN/ARM/TXN/ADI
(specific verbatim evidence the SUBJECT itself has a bottleneck, not just "flagged by a scanner").

    python thesis/discovery_radar.py [--min-quarters 2] [--recent-quarters 3] [--top 40]
"""
import argparse
import os
import re
import sqlite3
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from backtest.experiments.exp_sector_constraint_language import (  # noqa: E402
    scan_transcript_constraints, classify_sectors)
from thesis.corpus import DB as CORPUS_DB, CONSTRAINT_PHRASES  # noqa: E402

THEMES_PATH = os.path.join(ROOT, "thesis", "themes.yaml")
OUT_MD = os.path.join(ROOT, "backtest", "results", "2026-07-10_discovery_radar.md")


def existing_thesis_tickers() -> set:
    themes = (yaml.safe_load(open(THEMES_PATH, encoding="utf-8")) or {}).get("themes", {}) or {}
    out = set()
    for cfg in themes.values():
        out |= set(cfg.get("tickers") or [])
    return out


def _quarter_sort_key(q):
    return (int(q[:4]), int(q[5]))


def build_radar(min_quarters=2, recent_quarters=3, top=40):
    scan_df = scan_transcript_constraints()
    flagged = scan_df[scan_df["flagged"]].copy()

    covered = existing_thesis_tickers()
    print(f"[radar] {len(covered)} tickers already in existing themes -> excluded", flush=True)
    flagged = flagged[~flagged["ticker"].isin(covered)]

    all_quarters = sorted(scan_df["quarter"].unique(), key=_quarter_sort_key)
    recent_set = set(all_quarters[-recent_quarters:])
    print(f"[radar] 'recent' = {sorted(recent_set)}", flush=True)

    per_ticker = flagged.groupby("ticker").agg(
        n_quarters_flagged=("quarter", "nunique"),
        last_quarter=("quarter", "max"),
        total_matches=("n_kept", "sum"),
    ).reset_index()
    per_ticker = per_ticker[per_ticker["n_quarters_flagged"] >= min_quarters]
    per_ticker = per_ticker[per_ticker["last_quarter"].isin(recent_set)]
    per_ticker = per_ticker.sort_values(
        ["n_quarters_flagged", "total_matches"], ascending=False).head(top)

    tickers = per_ticker["ticker"].tolist()
    sector_map = classify_sectors(tickers)  # cache-hot from 2026-07-10 full run, near-instant
    per_ticker["sector"] = per_ticker["ticker"].map(sector_map)
    return per_ticker.reset_index(drop=True)


def sample_snippets(ticker, n=2):
    con = sqlite3.connect(CORPUS_DB)
    match = " OR ".join(f'"{p}"' for p in CONSTRAINT_PHRASES)
    rows = con.execute(
        "SELECT snippet(docs_fts_en,4,'[',']','...',15) FROM docs_fts_en "
        "JOIN docs d ON d.slug = docs_fts_en.slug "
        "WHERE d.primary_ticker=? AND docs_fts_en MATCH ? ORDER BY d.published DESC LIMIT ?",
        (ticker, match, n)).fetchall()
    con.close()
    return [re.sub(r"\s+", " ", r[0]) for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-quarters", type=int, default=2)
    ap.add_argument("--recent-quarters", type=int, default=3)
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()

    radar = build_radar(args.min_quarters, args.recent_quarters, args.top)
    lines = ["# Transcript Discovery Radar -- candidates NOT in any Phase-3 thesis yet (2026-07-10)\n",
              "> Discovery only, nothing auto-added. sector = informational triage label, NOT part "
              "of ranking. Each candidate needs manual research + verbatim validation (same bar as "
              "CIEN/ARM/TXN/ADI today) before it can become a thesis.\n",
              "| ticker | sector | n_quarters_flagged | last_quarter | total_matches |",
              "|---|---|---|---|---|"]
    for _, r in radar.iterrows():
        lines.append(f"| {r['ticker']} | {r['sector']} | {r['n_quarters_flagged']} | "
                     f"{r['last_quarter']} | {r['total_matches']} |")
    lines.append("\n## Sample matched snippets (top 15 candidates, most recent 2 transcripts each)\n")
    for _, r in radar.head(15).iterrows():
        lines.append(f"\n### {r['ticker']} ({r['sector']})")
        for s in sample_snippets(r["ticker"]):
            lines.append(f"- ...{s}...")
    report = "\n".join(lines)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"\n[main] wrote {OUT_MD}")


if __name__ == "__main__":
    main()
