"""Karst thesis layer -- earnings-call transcript prefetcher.

Contract
--------
Pre-downloads defeatbeta_api earnings-call transcripts for the full thesis
universe (thesis/themes.yaml tickers + a fixed watch-list of chain-head /
comparator names) and lands them one-file-per-transcript under
thesis/.raw/transcripts/<TICKER>/<report_date>.json, following the .raw
"immutable raw source" convention (thesis/.raw/README.md). This is RAW
MATERIAL for the future constraint-language scanner (WS4,
backtest/experiments/exp_constraint_language.py prototype) -- no scoring or
NLP happens here, only fetch + land.

API shape (defeatbeta_api >= 0.0.60, confirmed live 2026-07):
    t   = Ticker(symbol)
    tr  = t.earning_call_transcripts()
    lst = tr.get_transcripts_list()      # columns: symbol, fiscal_year (int),
                                          #   fiscal_quarter (int), report_date (str)
    df  = tr.get_transcript(fiscal_year, fiscal_quarter)
                                          # columns: paragraph_number (int),
                                          #   speaker (str), content (str)

Each row of `lst` -> one call to get_transcript -> one output file:
    thesis/.raw/transcripts/<TICKER>/<report_date>.json
    {
      "symbol": "MU", "fiscal_year": 2026, "fiscal_quarter": 3,
      "report_date": "2026-06-25",
      "n_paragraphs": 214,
      "paragraphs": [{"paragraph_number": 1, "speaker": "...", "content": "..."}, ...]
    }

Resumable: a ticker/report_date is skipped if EITHER (a) the output file
already exists on disk, OR (b) its slug is already indexed in
thesis/corpus.db (2026-07-11: added so the raw .raw/transcripts/ cache can
be deleted/archived/compressed after indexing without breaking incremental
resumability -- previously the ONLY memory of "already fetched" was the raw
file's mere presence on disk, so deleting it would silently make the next
run re-download that ticker's ENTIRE history instead of just new quarters).
Placeholder/incomplete transcripts (very few paragraphs, defeatbeta hasn't
fully ingested them yet -- same heuristic as exp_constraint_language.py) are
skipped and logged, not written, so a later re-run can retry them.

Universe = union of every ticker in thesis/themes.yaml + EXTRA_WATCHLIST
(chain-head / comparator names the constraint-language scan cares about even
where they don't (yet) carry a thesis verdict). Symbols defeatbeta has never
heard of (new listings like SKHY/SIVE, ETFs like DRAM) fail gracefully --
logged as a failure, does not crash the run.

Full-market mode (--universe full, spec 2026-07-09): unknown-unknowns
discovery needs breadth beyond the 63-ticker thematic watch-list. defeatbeta
ships its own full ticker universe via
defeatbeta_api.data.company_meta.CompanyMeta.get_all_tickers() (backed by
the huggingface company_tickers.json dataset, ~10.4k symbols incl. a small
no-CIK ETF supplement + preferred/warrant/unit share classes). full-market
mode filters those obvious non-common-stock rows out (see
build_full_universe()) and walks the remainder in defeatbeta's native idx
order, which is roughly market-cap/prominence sorted -- so a time-boxed
partial run naturally banks the most consequential names first. It is
cursor-resumable (thesis/.raw/transcripts/_full_universe_cursor.json): each
invocation processes up to --limit tickers starting from the saved cursor,
then updates it; re-running the same command continues where it left off.
--sample-n draws a fixed-seed random sample instead (for size/time
benchmarking) and does not touch the cursor.

Usage:
    PYTHONUTF8=1 python thesis/prefetch_transcripts.py
    PYTHONUTF8=1 python thesis/prefetch_transcripts.py --tickers MU,WDC   # subset, for testing
    PYTHONUTF8=1 python thesis/prefetch_transcripts.py --universe full --limit 500
    PYTHONUTF8=1 python thesis/prefetch_transcripts.py --universe full --sample-n 200  # benchmark sample
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import random
import re
import sqlite3
import sys
import time
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import yaml  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    from defeatbeta_api.data.ticker import Ticker  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
THESIS_DIR = REPO_ROOT / "thesis"
THEMES_YAML = THESIS_DIR / "themes.yaml"
OUT_DIR = THESIS_DIR / ".raw" / "transcripts"
CORPUS_DB = THESIS_DIR / "corpus.db"

# Chain-head / comparator names the constraint-language scan cares about even
# where they don't carry a thesis verdict of their own (spec 2026-07-09).
EXTRA_WATCHLIST = [
    "MU", "WDC", "STX", "MRVL", "AVGO", "TSM", "NVDA", "AMAT", "LRCX", "KLAC",
    "ASML", "ETN", "GEV", "VST", "CEG", "VRT", "PWR", "CAT", "UNP", "LLY",
    "XOM", "JPM",
]

MIN_CHARS = 500        # below this: placeholder/not-yet-ingested transcript, skip+log
SLEEP_S = 0.7          # politeness delay between tickers (default/thesis universe)
FULL_SLEEP_S = 0.4     # politeness delay for --universe full (spec: 0.3-0.5s)

FULL_CURSOR_PATH = OUT_DIR / "_full_universe_cursor.json"
FULL_SUMMARY_PATH = OUT_DIR / "_coverage_summary_full.json"

# Obvious non-common-stock share classes to drop from the full-market universe:
# SPAC warrants/units/rights (TICK-WT, TICK-UN, TICK-RT, TICK-U, TICK-R, TICK-WS) and
# preferred-share series (TICK-PA, TICK-PB, ...). Dual-class *common* stock (BRK-B,
# BF-A, MOG-A, ...) is deliberately NOT excluded -- those are real listings with their
# own earnings calls.
_WARRANT_UNIT_RIGHTS_RE = re.compile(r"-(WT|WS|UN|RT|U|R)$")
_PREFERRED_RE = re.compile(r"-P[A-Z]?$")


def _quiet(fn, *a, **kw):
    """Call fn while swallowing defeatbeta's stdout/stderr banner+logging."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*a, **kw)


def build_universe() -> list[str]:
    with open(THEMES_YAML, encoding="utf-8") as f:
        themes = yaml.safe_load(f)
    tks: set[str] = set()
    for _name, theme in themes.get("themes", {}).items():
        for t in theme.get("tickers", []) or []:
            tks.add(str(t).strip().upper())
    tks.update(EXTRA_WATCHLIST)
    return sorted(tks)


def build_full_universe() -> list[str]:
    """Full-market universe: every symbol defeatbeta's own company_tickers.json
    dataset knows about, minus the no-CIK ETF supplement and obvious
    warrant/unit/rights/preferred share classes (see regexes above). Returned in
    defeatbeta's native idx order (roughly market-cap/prominence sorted), with the
    curated default (thesis+watchlist) universe unioned in as a safety net for any
    name defeatbeta's own list happens to be missing.
    """
    infos = _quiet(lambda: __import__(
        "defeatbeta_api.data.company_meta", fromlist=["CompanyMeta"]
    ).CompanyMeta().get_all_companies_info())
    seen: set[str] = set()
    out: list[str] = []
    for r in infos:
        sym = str(r.get("symbol") or "").strip().upper()
        if not sym or sym in seen:
            continue
        if r.get("cik") is None:  # no-CIK ETF supplement baked into the dataset
            continue
        if _WARRANT_UNIT_RIGHTS_RE.search(sym) or _PREFERRED_RE.search(sym):
            continue
        seen.add(sym)
        out.append(sym)
    for sym in build_universe():  # safety net
        if sym not in seen:
            seen.add(sym)
            out.append(sym)
    return out


def _open_corpus_db() -> sqlite3.Connection | None:
    """Read-only connection to corpus.db for the incremental skip-check (2026-07-11).
    Returns None if corpus.db doesn't exist yet (e.g. very first-ever run before any
    `corpus.py build`) -- callers must treat None as "nothing indexed, fall back to
    disk-only check", not an error."""
    if not CORPUS_DB.exists():
        return None
    return sqlite3.connect(CORPUS_DB.as_uri() + "?mode=ro", uri=True)


def _already_indexed(con: sqlite3.Connection | None, tk: str, report_date: str) -> bool:
    """Same slug format + indexed-seek pattern as corpus.py's own _has_slug()."""
    if con is None:
        return False
    slug = f"transcript-{tk}-{report_date}"
    return con.execute("SELECT 1 FROM docs WHERE slug=? LIMIT 1", (slug,)).fetchone() is not None


def fetch_ticker(tk: str, verbose: bool = True, con: sqlite3.Connection | None = None) -> dict:
    """Fetch + land every transcript for `tk`. Returns a per-ticker summary dict.

    verbose=False suppresses per-transcript print lines (used by --universe full,
    where printing every file at ~10k-ticker scale would flood stdout); failures
    and skips are still recorded in the returned summary either way.

    `con`: optional corpus.db read-only connection (see _open_corpus_db). A
    (ticker, report_date) is skipped if EITHER the raw file already exists on disk
    OR corpus.db already has it indexed -- so the raw cache can be deleted/archived
    without forcing a re-download of history already safely captured in corpus.db.
    """
    summary = {
        "ticker": tk,
        "status": "ok",
        "n_listed": 0,
        "n_saved": 0,
        "n_already_had": 0,
        "n_skipped_short": 0,
        "n_failed_fetch": 0,
        "n_bytes_saved": 0,
        "error": None,
    }
    out_dir = OUT_DIR / tk
    try:
        t = _quiet(Ticker, tk)
        tr = _quiet(t.earning_call_transcripts)
        lst = _quiet(tr.get_transcripts_list)
    except Exception as e:
        summary["status"] = "failed_list"
        summary["error"] = f"{type(e).__name__}: {e}"
        return summary

    if lst is None or len(lst) == 0:
        summary["status"] = "empty"
        return summary
    summary["n_listed"] = len(lst)
    out_dir.mkdir(parents=True, exist_ok=True)

    for _, row in lst.iterrows():
        fy, fq = int(row["fiscal_year"]), int(row["fiscal_quarter"])
        report_date = str(row["report_date"])
        out_path = out_dir / f"{report_date}.json"
        if out_path.exists() or _already_indexed(con, tk, report_date):
            summary["n_already_had"] += 1
            continue
        try:
            df = _quiet(tr.get_transcript, fy, fq)
        except Exception as e:
            summary["n_failed_fetch"] += 1
            if verbose:
                print(f"[{tk}] {fy}Q{fq} ({report_date}) FAILED to fetch: "
                      f"{type(e).__name__}: {e}")
            continue
        if df is None or len(df) == 0:
            summary["n_skipped_short"] += 1
            if verbose:
                print(f"[{tk}] {fy}Q{fq} ({report_date}) SKIPPED (empty)")
            continue
        paragraphs = df.to_dict(orient="records")
        n_chars = sum(len(str(p.get("content", ""))) for p in paragraphs)
        if n_chars < MIN_CHARS:
            summary["n_skipped_short"] += 1
            if verbose:
                print(f"[{tk}] {fy}Q{fq} ({report_date}) SKIPPED "
                      f"(only {n_chars} chars, likely incomplete)")
            continue
        record = {
            "symbol": tk,
            "fiscal_year": fy,
            "fiscal_quarter": fq,
            "report_date": report_date,
            "n_paragraphs": len(paragraphs),
            "paragraphs": paragraphs,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        summary["n_saved"] += 1
        summary["n_bytes_saved"] += out_path.stat().st_size
        if verbose:
            print(f"[{tk}] {fy}Q{fq} ({report_date}): saved "
                  f"{len(paragraphs)} paragraphs, {n_chars} chars -> {out_path}")

    return summary


def _print_coverage_report(universe_size: int, results: list[dict], per_ticker: bool = True):
    ok = [r for r in results if r["status"] == "ok" and r["n_listed"] > 0]
    empty = [r for r in results if r["status"] == "empty"]
    failed = [r for r in results if r["status"] == "failed_list"]
    total_saved = sum(r["n_saved"] for r in results)
    total_already = sum(r["n_already_had"] for r in results)
    total_skipped = sum(r["n_skipped_short"] for r in results)
    total_failed_fetch = sum(r["n_failed_fetch"] for r in results)
    total_bytes = sum(r.get("n_bytes_saved", 0) for r in results)

    print("\n" + "=" * 72)
    print("COVERAGE REPORT")
    print("=" * 72)
    print(f"Universe size (this run): {universe_size}")
    print(f"Tickers processed        : {len(results)}")
    print(f"Tickers with transcripts  : {len(ok)}")
    print(f"Tickers empty (0 listed)  : {len(empty)}")
    print(f"Tickers failed to list    : {len(failed)} -> "
          f"{[(r['ticker'], r['error']) for r in failed[:20]]}")
    print(f"Transcripts newly saved   : {total_saved}")
    print(f"Transcripts already had   : {total_already}")
    print(f"Transcripts skipped (short/incomplete): {total_skipped}")
    print(f"Transcripts failed fetch  : {total_failed_fetch}")
    print(f"Bytes newly saved         : {total_bytes} ({total_bytes / 1e6:.1f} MB)")
    if per_ticker:
        print("\nPer-ticker (listed / saved / already_had):")
        for r in results:
            if r["status"] != "ok":
                print(f"  {r['ticker']:6s} {r['status']}"
                      + (f" ({r['error']})" if r["error"] else ""))
            else:
                print(f"  {r['ticker']:6s} listed={r['n_listed']:4d} "
                      f"saved={r['n_saved']:3d} already_had={r['n_already_had']:3d} "
                      f"skipped_short={r['n_skipped_short']:2d} "
                      f"failed_fetch={r['n_failed_fetch']:2d}")


def _load_full_state() -> tuple[dict, dict]:
    cursor = {"last_idx": 0}
    if FULL_CURSOR_PATH.exists():
        with open(FULL_CURSOR_PATH, encoding="utf-8") as f:
            cursor = json.load(f)
    results_by_ticker: dict = {}
    if FULL_SUMMARY_PATH.exists():
        with open(FULL_SUMMARY_PATH, encoding="utf-8") as f:
            prev = json.load(f)
        for r in prev.get("results", []):
            results_by_ticker[r["ticker"]] = r
    return cursor, results_by_ticker


def _save_full_state(cursor: dict, results_by_ticker: dict, universe_size: int) -> None:
    cursor["universe_size"] = universe_size
    cursor["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(FULL_CURSOR_PATH, "w", encoding="utf-8") as f:
        json.dump(cursor, f, indent=2)
    with open(FULL_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "universe_size": universe_size,
                "n_done": len(results_by_ticker),
                "results": list(results_by_ticker.values()),
            },
            f, ensure_ascii=False, indent=2,
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default=None,
                     help="Comma-separated subset (default: full themes.yaml + watchlist union)")
    ap.add_argument("--universe", choices=["default", "full"], default="default",
                     help="'full' = every defeatbeta ticker minus obvious ETFs/preferred/warrants "
                          "(unknown-unknowns discovery, ~9.9k names); "
                          "'default' = thesis.yaml + watchlist (~63 names)")
    ap.add_argument("--limit", type=int, default=None,
                     help="--universe full only: max tickers to process THIS invocation "
                          "(cursor-resumable via _full_universe_cursor.json; omit to run to completion)")
    ap.add_argument("--sample-n", type=int, default=None,
                     help="--universe full only: draw a fixed-seed random sample of N tickers "
                          "instead of the cursor-based sequential walk (for size/time "
                          "benchmarking; does not touch the cursor)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed for --sample-n")
    ap.add_argument("--sleep", type=float, default=None,
                     help="Override politeness delay between tickers (s)")
    ap.add_argument("--progress-every", type=int, default=50,
                     help="--universe full only: print/flush progress every N tickers")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    corpus_con = _open_corpus_db()
    if corpus_con is None:
        print("[prefetch] corpus.db not found yet -- skip-check falls back to disk-only "
              "(fine for a first-ever run; run `python thesis/corpus.py build` first if you "
              "expect corpus.db to already have prior history).")

    if args.tickers:
        universe = [t.strip().upper() for t in args.tickers.split(",")]
        mode = "tickers"
    elif args.universe == "full":
        universe = build_full_universe()
        mode = "full"
    else:
        universe = build_universe()
        mode = "default"

    sleep_s = args.sleep if args.sleep is not None else (FULL_SLEEP_S if mode == "full" else SLEEP_S)

    # -- benchmark sample path (--universe full --sample-n N) ------------------
    if mode == "full" and args.sample_n:
        rng = random.Random(args.seed)
        sample = rng.sample(universe, min(args.sample_n, len(universe)))
        print(f"Full universe: {len(universe)} tickers (filtered, defeatbeta company_tickers.json).")
        print(f"Benchmark sample: {len(sample)} (seed={args.seed}, sleep={sleep_s}s)")
        t_start = time.time()
        results = []
        for i, tk in enumerate(sample):
            t0 = time.time()
            s = fetch_ticker(tk, verbose=False, con=corpus_con)
            s["elapsed_s"] = round(time.time() - t0, 3)
            results.append(s)
            if (i + 1) % args.progress_every == 0 or (i + 1) == len(sample):
                elapsed = time.time() - t_start
                print(f"[sample {i + 1}/{len(sample)}] elapsed={elapsed:.0f}s "
                      f"saved={sum(r['n_saved'] for r in results)} "
                      f"bytes={sum(r['n_bytes_saved'] for r in results)}")
            if i < len(sample) - 1:
                time.sleep(sleep_s)
        sample_path = OUT_DIR / "_sample_benchmark.json"
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(
                {"seed": args.seed, "n": len(sample), "sleep_s": sleep_s,
                 "full_universe_size": len(universe), "results": results},
                f, ensure_ascii=False, indent=2,
            )
        print(f"\nWrote sample benchmark -> {sample_path}")
        _print_coverage_report(len(sample), results, per_ticker=False)
        return

    # -- cursor-resumable full-market walk (--universe full) -------------------
    if mode == "full":
        cursor, results_by_ticker = _load_full_state()
        start_idx = cursor.get("last_idx", 0)
        if start_idx >= len(universe):
            print(f"Full universe already fully walked ({start_idx}/{len(universe)}). Nothing to do.")
            return
        end_idx = len(universe) if args.limit is None else min(start_idx + args.limit, len(universe))
        segment = universe[start_idx:end_idx]
        print(f"Full universe: {len(universe)} tickers (filtered, native idx order).")
        print(f"Resuming at idx {start_idx}; this run covers idx [{start_idx}, {end_idx}) "
              f"= {len(segment)} tickers. sleep={sleep_s}s")
        t_start = time.time()
        try:
            for i, tk in enumerate(segment):
                s = fetch_ticker(tk, verbose=False, con=corpus_con)
                results_by_ticker[tk] = s
                cursor["last_idx"] = start_idx + i + 1
                if (i + 1) % args.progress_every == 0 or (i + 1) == len(segment):
                    elapsed = time.time() - t_start
                    rate = elapsed / (i + 1)
                    remaining = len(universe) - cursor["last_idx"]
                    eta_h = remaining * rate / 3600
                    print(f"[{cursor['last_idx']}/{len(universe)}] "
                          f"this-run={i + 1}/{len(segment)} elapsed={elapsed:.0f}s "
                          f"rate={rate:.2f}s/tk ETA-remainder={eta_h:.1f}h "
                          f"cum_saved={sum(r['n_saved'] for r in results_by_ticker.values())} "
                          f"cum_bytes={sum(r.get('n_bytes_saved', 0) for r in results_by_ticker.values())}")
                    _save_full_state(cursor, results_by_ticker, len(universe))
                if i < len(segment) - 1:
                    time.sleep(sleep_s)
        finally:
            _save_full_state(cursor, results_by_ticker, len(universe))
        print(f"\nStopped at idx {cursor['last_idx']}/{len(universe)}. "
              f"Re-run `--universe full` (same or no --limit) to continue.")
        _print_coverage_report(len(results_by_ticker), list(results_by_ticker.values()), per_ticker=False)
        return

    # -- default / --tickers path (unchanged behaviour) -------------------------
    print(f"Universe: {len(universe)} tickers")
    results = []
    for i, tk in enumerate(universe):
        print(f"\n--- [{i + 1}/{len(universe)}] {tk} ---")
        s = fetch_ticker(tk, verbose=True, con=corpus_con)
        results.append(s)
        if i < len(universe) - 1:
            time.sleep(sleep_s)

    _print_coverage_report(len(universe), results)
    summary_path = OUT_DIR / "_coverage_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nWrote coverage summary -> {summary_path}")
    if corpus_con is not None:
        corpus_con.close()


if __name__ == "__main__":
    main()
