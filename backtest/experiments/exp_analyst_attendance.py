"""Analyst call-attendance -- feasibility probe for a feature-5 (sentiment/crowding) proxy.

Context (Magnifier rubric, feature 5 "market attention / crowding"): every quantitative proxy
tried so far is snapshot-only (yfinance heldPercentInstitutions/numberOfAnalystOpinions -- see
backtest/results/2026-07-11_institutional_ownership_crowding_axis.md Sec.1) or, once a workable
proxy WAS found (dollar-volume turnover), backtested with NO edge (same file, Sec.3 -- do not
re-test that axis, per user instruction). This probe asks a different, Karst-native question:
Karst's own thesis/corpus.db already stores 79-82 quarters of earnings-call transcripts per name
(2005/2006-2026) INCLUDING the Q&A session, where a sell-side operator introduces every analyst who
asks a question by name. **The distinct count of analysts who show up each quarter is itself a
free, historical, per-name "how much does the Street care about this name right now" time series**
-- nobody has to license 13F/CUSIP data or pay for WhaleWisdom; it is sitting in the corpus already
indexed for a completely different purpose (constraint-language scanning).

METHOD -- two extraction paths, because defeatbeta's transcript source vendor changed formats
partway through history (confirmed empirically on MU: transcripts through 2018-12-18 use path A,
2019-03-20 onward use path B):

  A) HEADER path (older transcripts): body literally starts with
     "Executives: <name> - <title> ...\\n\\nAnalysts: <name> - <firm> <name> - <firm> ...\\n\\n..."
     -- parse the Analysts: block directly (entries split on runs of >=2 spaces / newlines; each
     entry is "Name - Firm" or "Name, Firm"; take the substring before the first " - "/"– "/", ").
     This is a vendor-published roster, not something we infer -- ground truth when present.

  B) SPEAKER-TAG path (newer transcripts, no header): defeatbeta's own paragraph-level `speaker`
     field already carries the analyst's clean name (e.g. "Tim Arcuri: <question text>"), because
     corpus.py's _parse_transcript() flattens each paragraph as "speaker: content" before indexing.
     We recover the roster by paragraph position, ticker/company-agnostically, with NO hardcoded
     exec names:
       - split body on the paragraph separator, regex out the leading "Speaker:" tag of each
       - "Operator" always speaks first (call open) and then AGAIN when it hands off to the first
         Q&A questioner -- so the SET of speakers strictly between the 1st and 2nd "Operator" turns
         is the prepared-remarks roster (IR host + CEO/CFO/etc, whoever they are this quarter)
       - every distinct speaker AFTER the 2nd "Operator" turn, minus that roster and minus
         "Operator" itself, is an analyst (their question paragraph is exactly one turn; a
         follow-up re-uses the same tag, so a straight set-dedup already collapses it to one)
     Falls back to `failed` (0 analysts, method='failed') if fewer than 2 "Operator" turns are
     found (can't locate the prepared-remarks/Q&A boundary) or the header parse yields nothing --
     failures are counted and reported, not silently dropped.

CAVEATS (surfaced up front, not just in the results doc):
  - This is an ATTENDANCE proxy (how many distinct sell-side voices show up), not a crowding proxy
    in the classical institutional-ownership sense, and not sentiment (we don't score whether the
    Q&A was hostile or friendly). Feature 5 wants "is this name over-loved / under-covered" --
    attendance is one plausible ingredient, not a drop-in replacement.
  - Per-name TIME SERIES, not cross-sectional -- survivorship bias (the usual worry for
    cross-sectional universe construction, per backtest-testing-standard memory) does not apply
    here: we are reading MU's own history, not selecting "which stocks are in today's universe".
  - Extraction failure rate is reported per ticker; a name with a high failure rate should not be
    read as "few analysts show up", it should be read as "we couldn't parse this quarter".

Run: python backtest/experiments/exp_analyst_attendance.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DB = REPO_ROOT / "thesis" / "corpus.db"
OUT_DIR = REPO_ROOT / "backtest" / ".insider_data"

MU = "MU"
COMPARATORS = ["NVDA", "AVGO", "USAC", "WST", "FSLR"]

NAME_SPLIT_RE = re.compile(r"\s[-–]\s|,\s")
SPEAKER_RE = re.compile(r"^([^:\n]{1,60}):\s")
NAME_TOK = r"\[?[A-Z][\w'.]*\]?"
HEADER_ENTRY_RE = re.compile(
    rf"({NAME_TOK}(?:\s+{NAME_TOK}){{0,3}})\s*(?:-|,)\s*(.*?)"
    rf"(?=\s+{NAME_TOK}(?:\s+{NAME_TOK}){{0,3}}\s*(?:-|,)\s*|\Z)",
    re.S,
)
FIRST_Q_RE = re.compile(r"first question", re.I)
GENERIC_TAGS = {
    "q", "a", "operator", "unidentified analyst", "unidentified speaker",
    "analyst", "moderator", "executives", "analysts", "",
}

# --------------------------------------------------------------------------- extraction ---
#
# Two signals are combined for every transcript (both format eras -- see module docstring):
#  1) STRUCTURAL Q&A boundary: the operator turn containing "first question" (the universal,
#     vendor-consistent handoff phrase actually said live on the call), falling back to the
#     2nd distinct "Operator" turn if that phrase is never said. Distinct speakers appearing
#     strictly BEFORE this boundary = the prepared-remarks roster (IR host + whichever execs
#     spoke that quarter) to exclude; distinct speakers strictly AFTER it, minus that roster,
#     are Q&A participants.
#  2) The vendor-published "Executives:" header block (pre-2019-style transcripts only), parsed
#     as a second, independent exclusion list -- catches executives who answer a question in
#     Q&A without having spoken during prepared remarks (structurally invisible to signal 1).
# Residual noise (documented, not hidden): (a) an executive who answers in Q&A, is NOT listed
# in the Executives: header, and did not speak in prepared remarks is mis-tagged as an
# "analyst" -- confirmed on one 2008-era MU transcript (CEO S. Appleton); (b) same-transcript
# spelling drift of an exec's own name (e.g. "Ronald C. Foster" vs "Richard C. Foster" later in
# the same document) creates one spurious "extra analyst". Both are 2006-2010-era vendor-data
# artifacts, confirmed rare in the 2015-2026 window this probe cares about (see results doc).


def _clean_name(raw: str) -> str:
    """Normalize a raw speaker tag down to just the person's name: strip a leading role
    prefix baked into some ancient transcripts ('Q - ', 'A - ') and a trailing ' - Firm' /
    ', Firm' suffix some speaker tags carry (e.g. 'Glen Yeung - Citigroup Inc')."""
    raw = raw.strip().strip("[]").strip()
    raw = re.sub(r"^[QA]\s*[-–]\s*", "", raw)
    return NAME_SPLIT_RE.split(raw, maxsplit=1)[0].strip()


def _extract_header_block(body: str, key: str) -> set[str] | None:
    """Generic parser for the 'Executives:' / 'Analysts:' roster block present in pre-2019
    transcripts. Returns None if the block/key isn't present at all (signals a headerless,
    modern-format transcript to the caller). Robust to BOTH newline-separated entries and the
    single-line, space-run-together entries some vendor quarters used (confirmed on MU
    2013-2018): matches each 'Name - Title/Firm' (or 'Name, Title') pair by finding the next
    name-shaped token run followed by a dash/comma, not by splitting on whitespace runs."""
    m = re.search(rf"{key}:\s*(.*?)\n\n", body, re.S)
    if not m:
        return None
    block = m.group(1).strip()
    if not block:
        return set()
    names = {em.group(1).strip() for em in HEADER_ENTRY_RE.finditer(block)}
    names = {n for n in names if n and len(n) > 1}
    if not names:
        for e in re.split(r"\s{2,}|\n", block):
            nm = _clean_name(e)
            if nm and len(nm) > 1:
                names.add(nm)
    return names


def _dialogue_speakers_ordered(body: str) -> list[tuple[str, str]]:
    """[(raw speaker tag, full paragraph text), ...] in document order."""
    out = []
    for p in body.split("\n\n"):
        m = SPEAKER_RE.match(p)
        if m:
            out.append((m.group(1).strip(), p))
    return out


def _qa_boundary(speakers: list[tuple[str, str]]) -> int | None:
    """Index of the Operator turn that hands off to Q&A, or None if it can't be located."""
    op_idx = [i for i, (t, _) in enumerate(speakers) if t == "Operator"]
    phrase_idx = [i for i in op_idx[1:] if FIRST_Q_RE.search(speakers[i][1])]
    if phrase_idx:
        return phrase_idx[0]
    if len(op_idx) >= 2:
        return op_idx[1]
    return None


def extract_analysts(body: str) -> tuple[set[str], str]:
    """Returns (set of analyst names, method: 'speakertag' | 'header_roster_fallback' | 'failed')."""
    speakers = _dialogue_speakers_ordered(body)
    boundary = _qa_boundary(speakers)
    execs = _extract_header_block(body, "Executives")  # None => headerless/modern transcript
    if boundary is not None:
        pre_roster = {_clean_name(t) for t, _ in speakers[:boundary] if t != "Operator"}
        exclude = pre_roster | {"Operator"}
        if execs:
            exclude |= {_clean_name(e) for e in execs}
        post = {_clean_name(t) for t, _ in speakers[boundary + 1 :]}
        candidates = {
            c for c in post
            if c and c not in exclude and c.lower() not in GENERIC_TAGS and len(c) > 1
        }
        if candidates:
            return candidates, "speakertag"
    # fallback: vendor Analysts: roster -- only reliable source left for the rare transcripts
    # (ancient generic "Q -"/"A -" speaker tags, or too few Operator turns) where signal 1 fails.
    roster = _extract_header_block(body, "Analysts")
    if roster:
        return {_clean_name(r) for r in roster if _clean_name(r)}, "header_roster_fallback"
    return set(), "failed"


# ------------------------------------------------------------------------------ corpus IO ---


def get_transcripts(ticker: str) -> list[tuple[str, str, str]]:
    """[(slug, published, body), ...] ordered by published date, read-only."""
    con = sqlite3.connect(f"file:{CORPUS_DB.as_posix()}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT d.id, d.slug, d.published FROM docs d "
        "WHERE d.thesistype='transcript' AND d.primary_ticker=? ORDER BY d.published",
        (ticker,),
    ).fetchall()
    out = []
    for did, slug, pub in rows:
        r = con.execute("SELECT body FROM docs_fts_en WHERE rowid=?", (did,)).fetchone()
        out.append((slug, pub, r[0] if r else ""))
    con.close()
    return out


def build_series(ticker: str) -> pd.DataFrame:
    rows = []
    for slug, pub, body in get_transcripts(ticker):
        names, method = extract_analysts(body)
        rows.append(
            {
                "ticker": ticker,
                "slug": slug,
                "published": pub,
                "n_analysts": len(names),
                "method": method,
                "names": sorted(names),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["published"] = pd.to_datetime(df["published"])
        df = df.sort_values("published").reset_index(drop=True)
    return df


# -------------------------------------------------------------------- cross-check: ttm_pe ---

WIN, MINP = 756, 252


def ttm_pe_percentile(ticker: str) -> pd.Series | None:
    """Same convention as exp_valuation_broad.py: rolling 3y (756d) percentile of ttm_pe,
    reindexed by report_date. Used only as a cross-check ("do the two proxies tell the same
    story"), not as part of the analyst-attendance extraction itself."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            from defeatbeta_api.data.ticker import Ticker

            df = Ticker(ticker).ttm_pe()
    except Exception as e:
        print(f"  [ttm_pe] {ticker} FAILED: {type(e).__name__}: {e}")
        return None
    df = df[["report_date", "ttm_pe"]].copy()
    df["date"] = pd.to_datetime(df["report_date"])
    df = df.set_index("date").sort_index()
    df = df[~df.index.duplicated()]
    pe = df["ttm_pe"].where(df["ttm_pe"] > 0)
    return pe.rolling(WIN, min_periods=MINP).rank(pct=True)


def pe_pctile_near_date(pct_series: pd.Series | None, date: pd.Timestamp, tol_days: int = 120):
    if pct_series is None or pct_series.empty:
        return None
    idx = pct_series.index
    diffs = (idx - date).days.to_numpy()
    import numpy as np

    j = int(abs(diffs).argmin())
    if abs(diffs[j]) > tol_days:
        return None
    v = pct_series.iloc[j]
    return None if pd.isna(v) else round(float(v), 3)


# ----------------------------------------------------------------------------------- main ---


def print_ticker_report(ticker: str, df: pd.DataFrame, pe_pct: pd.Series | None):
    print(f"\n{'=' * 78}\n{ticker}\n{'=' * 78}")
    if df.empty:
        print("  NO TRANSCRIPTS FOUND in corpus.db.")
        return
    n = len(df)
    n_failed = int((df["method"] == "failed").sum())
    n_header = int((df["method"] == "header").sum())
    n_speaker = int((df["method"] == "speakertag").sum())
    print(
        f"  quarters={n}  header={n_header}  speakertag={n_speaker}  "
        f"failed={n_failed} ({n_failed / n:.1%})"
    )
    ok = df[df["method"] != "failed"]
    if not ok.empty:
        print(
            f"  n_analysts: min={ok['n_analysts'].min()} "
            f"median={ok['n_analysts'].median():.1f} max={ok['n_analysts'].max()} "
            f"mean={ok['n_analysts'].mean():.2f}"
        )
    print(f"  {'date':<12} {'n_analysts':>10} {'method':<11} {'pe_pctile':>10}  names")
    for _, r in df.iterrows():
        pep = pe_pctile_near_date(pe_pct, r["published"]) if pe_pct is not None else None
        pep_s = f"{pep:.2f}" if pep is not None else "n/a"
        names_s = ", ".join(r["names"][:6]) + ("..." if len(r["names"]) > 6 else "")
        print(
            f"  {r['published'].date()!s:<12} {r['n_analysts']:>10} {r['method']:<11} "
            f"{pep_s:>10}  {names_s}"
        )


def run():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_series = {}
    for tk in [MU] + COMPARATORS:
        print(f"\n[fetch] {tk} transcripts from corpus.db ...")
        df = build_series(tk)
        pe_pct = ttm_pe_percentile(tk)
        print_ticker_report(tk, df, pe_pct)
        all_series[tk] = df

    out_path = OUT_DIR / "analyst_attendance_series.json"
    payload = {
        tk: df.assign(published=df["published"].astype(str)).to_dict(orient="records")
        for tk, df in all_series.items()
        if not df.empty
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nWrote series cache -> {out_path}")

    # ---- MU cyclical-bottom focus (2022-2023 "dead cyclical" period) ----
    mu = all_series[MU]
    mu_ok = mu[mu["method"] != "failed"]
    print(f"\n{'=' * 78}\nMU FOCUS: cyclical bottom (2022-2023) vs supply-tightness consensus (2024-25)\n{'=' * 78}")
    bottom = mu_ok[(mu_ok["published"] >= "2022-06-01") & (mu_ok["published"] <= "2023-12-31")]
    consensus = mu_ok[(mu_ok["published"] >= "2024-06-01") & (mu_ok["published"] <= "2025-12-31")]
    if not bottom.empty:
        print(f"2022-2023 (price $49-50, 'dead cyclical') mean n_analysts = {bottom['n_analysts'].mean():.2f} "
              f"(n={len(bottom)} quarters, range {bottom['n_analysts'].min()}-{bottom['n_analysts'].max()})")
    if not consensus.empty:
        print(f"2024-2025 (supply-tightness consensus)      mean n_analysts = {consensus['n_analysts'].mean():.2f} "
              f"(n={len(consensus)} quarters, range {consensus['n_analysts'].min()}-{consensus['n_analysts'].max()})")
    hist_all = mu_ok["n_analysts"]
    if not bottom.empty and not hist_all.empty:
        pct_of_bottom_in_full_history = (hist_all <= bottom["n_analysts"].mean()).mean()
        print(f"Full-history (2006-2026) mean={hist_all.mean():.2f}, median={hist_all.median():.1f}, "
              f"min={hist_all.min()} (on {mu_ok.loc[mu_ok['n_analysts'].idxmin(), 'published'].date()}), "
              f"max={hist_all.max()}")


if __name__ == "__main__":
    run()
