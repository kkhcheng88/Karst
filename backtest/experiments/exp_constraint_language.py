"""Phase-3 WS4 prototype: "supply-constrained language" scan over earnings-call
transcripts (defeatbeta_api), pre-registered word list, per-ticker per-quarter score.

Feasibility probe only -- not a production signal yet. See
backtest/results/2026-07-08_constraint_language_probe.md for the writeup.

Usage:
    PYTHONUTF8=1 python backtest/experiments/exp_constraint_language.py
"""
from __future__ import annotations

import io
import os
import re
import sys
import contextlib
import json
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from defeatbeta_api.data.ticker import Ticker  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
OUT_JSON = RESULTS_DIR / "2026-07-08_constraint_language_probe_data.json"

# --- pre-registered word list (v0), bidirectional --------------------------
# Constrained direction: language consistent with supply tightness / demand
# outstripping supply.
CONSTRAINED_PHRASES = [
    r"lead times? (?:are |is |have been |has been )?(?:extending|stretched|stretching|lengthening|elongating)",
    r"extending lead times?",
    r"on allocation",
    r"\ballocation\b",
    r"sold out",
    r"capacity constrained",
    r"capacity constraints?",
    r"cannot meet demand",
    r"unable to meet demand",
    r"supply tight(?:ness)?",
    r"tight supply",
    r"price increase(?:s)? (?:are )?sticking",
    r"take-or-pay",
    r"prepay(?:ment)?s?",
    r"undersupply",
    r"supply shortage",
    r"demand (?:continues to |is )?outstrip(?:ping)? supply",
]

# Loosening direction: language consistent with supply catching up / demand
# softening (contra-signal).
LOOSENING_PHRASES = [
    r"inventory correction",
    r"demand softness",
    r"soft(?:ening)? demand",
    r"capacity (?:coming|come) online",
    r"pricing pressure",
    r"discount(?:ing)?",
    r"excess inventory",
    r"inventory (?:build|glut)",
    r"oversupply",
]

CONSTRAINED_RE = [re.compile(p, re.IGNORECASE) for p in CONSTRAINED_PHRASES]
LOOSENING_RE = [re.compile(p, re.IGNORECASE) for p in LOOSENING_PHRASES]

# --- ticker groups (sector) --------------------------------------------------
SECTORS = {
    "memory": ["MU", "WDC", "STX"],
    "semis_equip_foundry": ["TSM", "AMAT", "NVDA", "AVGO"],
    "power_grid": ["ETN", "VST", "CEG"],
    "industrial_other": ["CAT", "UNP", "LLY", "XOM", "JPM"],
}
ALL_TICKERS = [t for grp in SECTORS.values() for t in grp]

MIN_FISCAL_YEAR = 2018  # scan window: FY2018Q1 onward (keeps runtime sane,
                         # covers the 2024-2026 validation window with headroom)


def _quiet(fn, *a, **kw):
    """Call fn while swallowing defeatbeta's stdout/stderr banner+logging."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*a, **kw)


def score_transcript(text: str) -> dict:
    words = re.findall(r"\w+", text)
    n_words = max(len(words), 1)
    c_hits = sum(len(p.findall(text)) for p in CONSTRAINED_RE)
    l_hits = sum(len(p.findall(text)) for p in LOOSENING_RE)
    return {
        "n_words": n_words,
        "constrained_hits": c_hits,
        "loosening_hits": l_hits,
        # per-1000-words normalized net score
        "score_per_1000w": 1000.0 * (c_hits - l_hits) / n_words,
    }


def scan_ticker(tk: str) -> list[dict]:
    out = []
    try:
        t = _quiet(Ticker, tk)
        tr = _quiet(t.earning_call_transcripts)
        lst = _quiet(tr.get_transcripts_list)
    except Exception as e:
        print(f"[{tk}] FAILED to list transcripts: {e}")
        return out

    for _, row in lst.iterrows():
        fy, fq = int(row["fiscal_year"]), int(row["fiscal_quarter"])
        if fy < MIN_FISCAL_YEAR:
            continue
        try:
            df = _quiet(tr.get_transcript, fy, fq)
        except Exception as e:
            print(f"[{tk}] {fy}Q{fq} FAILED to fetch: {e}")
            continue
        if df is None or len(df) == 0:
            continue
        text = " ".join(str(x) for x in df["content"].tolist())
        if len(text) < 500:
            # partial/placeholder transcript (e.g. not yet fully ingested)
            print(f"[{tk}] {fy}Q{fq} SKIPPED (only {len(text)} chars, likely incomplete)")
            continue
        s = score_transcript(text)
        s.update({
            "ticker": tk,
            "fiscal_year": fy,
            "fiscal_quarter": fq,
            "report_date": str(row["report_date"]),
        })
        out.append(s)
        print(f"[{tk}] {fy}Q{fq} ({row['report_date']}): "
              f"words={s['n_words']} c={s['constrained_hits']} "
              f"l={s['loosening_hits']} score/1000w={s['score_per_1000w']:.3f}")
    return out


def main():
    all_rows = []
    for tk in ALL_TICKERS:
        all_rows.extend(scan_ticker(tk))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, indent=2)
    print(f"\nWrote {len(all_rows)} ticker-quarter rows -> {OUT_JSON}")


if __name__ == "__main__":
    main()
