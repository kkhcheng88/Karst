"""Phase-3 WS4 probe: does 10-K/10-Q (or 40-F/6-K for foreign private issuers)
full-text "supply-constrained language" ADD anything over the earnings-call
transcript scan (exp_constraint_language.py)? Same pre-registered word list,
applied to EDGAR filing text (MD&A + Risk Factors), compared quarter-by-quarter
against the transcript score for the SAME company.

Question: for a super-cycle candidate, does the 10-K/10-Q flip constrained
EARLIER or LATER than the transcript? Does it carry constrained language the
transcript never uses (increment)? Does the *change* in filing text (this
filing's newly-added constrained phrases vs the prior same-series filing --
the Lazy-Prices angle) turn positive earlier than either level?

Method: mirror = same word list, same per-1000-words scoring as
exp_constraint_language.py (imported directly so the two can't drift).
Increment = phrase-level presence/absence diff between a filing and the
PRECEDING filing of the same series (10-K vs prior 10-K, 10-Q vs prior 10-Q;
CCJ's 40-F vs prior 40-F, quarterly 6-K vs prior quarterly 6-K) -- this is the
"what's NEW in this filing" signal, not the level.

6 cases, one script, parameterized by CASES below -- 5 real supply/demand
super-cycle candidates spanning different bottleneck archetypes, + 1 deliberate
NEGATIVE CONTROL (a narrative/milestone-driven theme with no supply/demand
bottleneck at all, to test whether the framework correctly finds ~nothing):
  MU   (memory, cyclical-commodity)         filing window 2021-07 ~ 2024-12
  LLY  (GLP-1 demand supercycle, pharma)    filing window 2021-01 ~ 2023-06
  VST  (AI-datacenter power, IPP)           filing window 2022-01 ~ 2024-03
  CCJ  (uranium supply-gap, FPI/40-F)       filing window 2021-01 ~ 2023-06
  AXTI (InP/GaAs substrate, photonics)      filing window 2022-01 ~ 2024-06
  RGTI (quantum computing -- NEGATIVE CONTROL, narrative-driven, no real
        supply/demand bottleneck) filing window 2023-01 ~ 2024-09

CCJ is a Canadian MJDS filer: no 10-K/10-Q exists in EDGAR (confirmed via
defeatbeta sec_filing() -- only 40-F/6-K/144/3/4/5/13G form types are present).
Quarterly MD&A is furnished as an exhibit inside a 6-K bundle (content-sniffed
by looking for "management's discussion and analysis" in each exhibit's OWN
TITLE, not a broad body-text scan -- a broad scan false-matched the exhibit
that only CITES the MD&A, not the MD&A itself); the annual MD&A + AIF (which
carries the risk section, titled "Risks that can affect our business" --
CCJ does NOT use the US "Risk Factors" heading at all) are furnished inside
the 40-F. This is itself a data-availability finding, not just plumbing --
see results doc.

Section-boundary extraction for the US-regime tickers (MU/LLY/VST/AXTI/RGTI)
turned out to be the hard part of this probe: naive regex matching of
"Item 7. Management's..." picks up dozens of in-body CROSS-REFERENCE
citations to the same item (ToC entries, "see Item 7...", quoted citations)
well before it ever finds the one real section header, and different filing
agents render the SEC-mandated item numbering in genuinely incompatible ways
(ALL CAPS vs Title Case; period vs dash between item number and title; a
stray space injected mid-word or mid-number by a tag boundary). See
_is_citation()'s docstring for the disambiguation heuristic this converged on
after multiple false starts (documented inline, not just in git history,
because the failure modes are non-obvious and will recur on any 7th ticker).

Fetches EDGAR directly via urllib (same pattern as thesis/insider_edgar.py),
SEC-compliant User-Agent, polite pause between requests. Transcripts fetched
via defeatbeta_api (same as exp_constraint_language.py), NOT read from the
thesis/.raw/transcripts/ cache, so this script is self-contained/rerunnable.

Usage:
    PYTHONUTF8=1 python backtest/experiments/exp_filing_signal.py
See backtest/results/2026-07-09_filing_vs_transcript_signal.md for the writeup.
"""
from __future__ import annotations

import contextlib
import html
import io
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp_constraint_language import CONSTRAINED_RE, LOOSENING_RE  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
OUT_JSON = Path(__file__).resolve().parent / "_filing_signal_data.json"

_UA = {"User-Agent": "Karst-research/1.0 (contact research@karst.local)"}
_PAUSE = 0.25

CASES = [
    dict(ticker="MU", regime="us", narrative="memory supercycle (AI/HBM); gooptions narrative forms ~2025-2026",
         filing_start="2021-07-01", filing_end="2024-12-31",
         tx_start="2020-07-01", tx_end="2025-06-30"),
    dict(ticker="LLY", regime="us", narrative="GLP-1 demand supercycle; Zepbound approved 2023-11, mania narrative 2023H2+",
         filing_start="2021-01-01", filing_end="2023-06-30",
         tx_start="2020-01-01", tx_end="2023-12-31"),
    dict(ticker="VST", regime="us", narrative="AI-datacenter power demand / IPP re-rating; narrative forms ~2024",
         filing_start="2022-01-01", filing_end="2024-03-31",
         tx_start="2021-01-01", tx_end="2024-09-30"),
    dict(ticker="CCJ", regime="ccj", narrative="uranium/nuclear-revival supply gap; narrative firms ~2023H2",
         filing_start="2021-01-01", filing_end="2023-06-30",
         tx_start="2020-01-01", tx_end="2023-12-31"),
    dict(ticker="AXTI", regime="us", narrative="InP/GaAs substrate bottleneck (optical/photonics upstream); "
                                                "AXTI ~$2->$140 run, China gallium/InP export-control overlay",
         filing_start="2022-01-01", filing_end="2024-06-30",
         tx_start="2021-01-01", tx_end="2024-12-31"),
    dict(ticker="RGTI", regime="us", narrative="NEGATIVE CONTROL: quantum computing, narrative/milestone-driven "
                                                "(not a supply/demand super-cycle) -- Google Willow 2024-12 spike",
         filing_start="2023-01-01", filing_end="2024-09-30",
         tx_start="2022-01-01", tx_end="2025-03-31"),
]

# NB: filers are NOT consistent about header casing -- MU/AMAT-style iXBRL docs
# render real section headers in ALL CAPS ("ITEM 2. MANAGEMENT..."), while
# LLY/VST-style docs use Title Case ("Item 7. Management's Discussion...").
# Every pattern here MUST be case-insensitive end-to-end or it silently misses
# one filer's convention (caught in dev: MU returned empty mda/risk before this
# was made (?i)).
#
# _SEP replaces a bare "\." between the item number and its title, for two
# independent reasons found across different filing agents' HTML:
#  1. a stray space before the period ("ITEM 3 . QUANTITATIVE...", a tag
#     boundary landing between the number and the period) -- a bare "3\."
#     silently fails to match, and the section then runs uncapped to the next
#     pattern that DOES match (or the cap), swallowing everything after it
#     (caught on AXTI's 10-Qs: MD&A ballooned to 212K+ chars, engulfing Item
#     3/4/Part II whole).
#  2. some agents (RGTI's earliest 10-Qs, a Donnelley-style template) use a
#     dash instead of a period entirely -- "ITEM 2 - MANAGEMENT'S DISCUSSION
#     AND ANALYSIS..." -- with NO period at all between item number and title.
_SEP = r"\s*[.\-‐‑‒–—]\s*"
# NB the separator char is REQUIRED (not "...]?...") -- making it fully
# optional let "Item 7 Management's..." (bare, no punctuation at all) match
# too, which picked up a late stray mention in VST's FY2021 10-K that isn't a
# real header or a recognized citation and broke the "last non-citation
# wins" selection. Every real filing agent puts SOME separator character
# between the item number and its title; requiring one is not a regression.
MDA_END_PATTERNS = [rf"(?i)item\s+3{_SEP}quantitative", rf"(?i)item\s+7A{_SEP}quantitative", rf"(?i)item\s+8{_SEP}financial"]
RISK_END_PATTERNS = [rf"(?i)item\s+1B\b", rf"(?i)item\s+2{_SEP}unregistered", rf"(?i)item\s+2{_SEP}properties"]
# Deliberately just "Item N. Management" -- NOT the full canonical title
# ("...Discussion and Analysis of Financial Condition and Results of
# Operations"). The fuller phrase was tried and reverted: some filing agents'
# HTML splits a word across two tags (AXTI's 2022 10-K renders "Condition" as
# "Condit<...></...>ion", which collapses to "Condit ion" with a stray space
# after tag-stripping), silently breaking any regex that requires the long
# phrase verbatim -- and there's no way to predict which word a given vendor's
# renderer will split. "Item N. Management" is specific enough on its own
# (no other SEC item starts with "Management" for items 2 or 7); the
# real-vs-citation discrimination is all done by _is_citation() below, which
# only looks at what precedes the match, so shortening the match itself loses
# no precision.
MDA_START_PATTERN = rf"(?i)item\s+(?:2|7){_SEP}management"
RISK_START_PATTERN = rf"(?i)item\s+1A{_SEP}risk factors"
SECTION_CAP = 220_000  # chars; safety net against a runaway/no-match section.
# RGTI's genuine Risk Factors section is ~154.6K chars (long risk-factor list
# typical of a speculative pre-revenue small-cap) -- 150K silently truncated
# it short of its real "Item 1B" boundary before this was raised.


def _quiet(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*a, **kw)


def _get(url: str, retries: int = 3) -> str:
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=_UA)
            return urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(0.6 * (i + 1))
    raise RuntimeError(f"fetch failed after {retries} tries: {url}: {last}")


def _clean(raw_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def score_text(text: str) -> dict:
    words = re.findall(r"\w+", text)
    n_words = max(len(words), 1)
    c_hits = sum(len(p.findall(text)) for p in CONSTRAINED_RE)
    l_hits = sum(len(p.findall(text)) for p in LOOSENING_RE)
    fired_c = [bool(p.search(text)) for p in CONSTRAINED_RE]
    fired_l = [bool(p.search(text)) for p in LOOSENING_RE]
    return {
        "n_words": n_words, "constrained_hits": c_hits, "loosening_hits": l_hits,
        "score_per_1000w": 1000.0 * (c_hits - l_hits) / n_words,
        "fired_constrained": fired_c, "fired_loosening": fired_l,
    }


_QUOTE_CHARS = "“\""  # curly (MU/LLY-style generators) and straight (VST-style) open quotes
# Every filing repeats each item's canonical title MANY times as an in-body
# CROSS-REFERENCE ("see Item 7...", "under Item 1A...", "addressed in Item
# 7...", `see "Item 2. ..."`) well beyond the one real section header. Cross-
# refs are reliably introduced by a citation/reference word -- real headers
# never are (they're preceded by a ToC page number, a "Table of Contents"
# page-break artifact, or the tail of the immediately preceding item, e.g.
# "Item 6. [RESERVED] Not applicable. Item 7. ..."). Curly quotes catch some
# of these ("see "Item 2...""); this word-based check catches the rest
# (plain "See Item 7...", no quotes at all -- caught on VST's FY2023 10-K,
# which has ten "Item 7. Management's..." occurrences and only one is real).
_CITATION_WORD_RE = re.compile(r"(?i)\b(see|under|within|addressed|discussed|pursuant|included|include)\b")
_TRAILING_AND_RE = re.compile(r"(?i)\band\s*$")
_SENTENCE_END_RE = re.compile(r"[.!?]")
# The period inside "Item 7A." / "Part I." is NOT a sentence boundary -- it's
# part of the citation itself ("...suppliers. See "Part I. Financial
# Information..." has TWO periods; only the first is real). Without this
# exclusion, the scan below finds the "Part I." period as "last", throws away
# everything before it (including "See" and the opening quote) and wrongly
# clears the citation (caught on MU's 10-Q, which regressed once sentence-
# boundary-awareness was added for AXTI/VST).
_ITEM_PART_ABBREV_RE = re.compile(r"(?i)\b(item\s+\d+[a-z]?|part\s+(?:[ivxlc]+|\d+))\s*$")
# trailing \s* -- same stray-space-before-period issue as above ("Item 3 .")
# can leave a trailing space here too.


def _is_citation(text: str, match_start: int, lookback: int = 90) -> bool:
    """A citation word/quote/"and"-continuation only counts if it sits in the
    SAME, still-open sentence/clause as the "Item ..." match -- i.e. no REAL
    sentence-ending punctuation between the trigger and the match. This one
    rule replaces a chain of narrower fixes:
      - "...statements included in this Annual Report on Form 10-K. Item 7A.
        Quantitative..." -- "included" is in an already-CLOSED sentence (the
        period intervenes); this is a real boundary, not a citation (caught
        on AXTI's 10-K, which broke a lookback-window-only version of this
        check that doesn't care about the period).
      - "...related notes included in Item 8. Financial Statements..." --
        "included" governs "Item 8" directly, NO period in between; this IS
        a citation (caught on VST's FY2023 10-K).
      - "...Item 6. [RESERVED] Not applicable. Item 7. MANAGEMENT'S..." --
        no citation word at all in the open clause; real header.
    Restricting to the open clause is also why a short lookback is fine even
    for the compound-citation case ("See Item 1. Business ..., and Item 1A.
    Risk Factors...") -- "and" sits in the clause opened by "See", which
    never closed, so it's still caught regardless of how far back "See" is."""
    before = text[max(0, match_start - lookback):match_start]
    idx = None
    for pm in re.finditer(_SENTENCE_END_RE, before):
        if pm.group() == "." and _ITEM_PART_ABBREV_RE.search(before[:pm.start()]):
            continue  # "Item 7A."/"Part I." -- not a real sentence end
        idx = pm.end()
    open_clause = before[idx:] if idx is not None else before
    if any(q in open_clause for q in _QUOTE_CHARS) or _CITATION_WORD_RE.search(open_clause):
        return True
    return bool(_TRAILING_AND_RE.search(open_clause))


def _last_match_start(text: str, pattern: str):
    """Last occurrence of `pattern` that is NOT an in-body cross-reference
    citation (see _is_citation). ToC entries are not filtered (they don't
    read as citations) but always sit EARLIER than the real body, so taking
    the LAST non-citation match still resolves to the real header."""
    ms = [m for m in re.finditer(pattern, text) if not _is_citation(text, m.start())]
    return ms[-1] if ms else None


def _section_end(text: str, start_pos: int, end_patterns: list[str]) -> int:
    """Nearest real boundary after start_pos, skipping cross-ref citations to
    the next item that appear INSIDE the current section's own body (e.g. "...
    can be found in Item 8. Financial Statements...") -- same problem as
    _last_match_start, same fix."""
    best = None
    for pat in end_patterns:
        for m in re.finditer(pat, text):
            if m.start() <= start_pos:
                continue
            if _is_citation(text, m.start()):
                continue
            if best is None or m.start() < best:
                best = m.start()
            break  # first non-citation occurrence after start is nearest candidate for this pattern
    if best is None:
        best = min(len(text), start_pos + SECTION_CAP)
    return min(best, start_pos + SECTION_CAP)


def _extract_sections_us(text: str) -> dict:
    out = {"mda": "", "risk": ""}
    m = _last_match_start(text, MDA_START_PATTERN)
    if m:
        end = _section_end(text, m.end(), MDA_END_PATTERNS)
        out["mda"] = text[m.start():end]
    m = _last_match_start(text, RISK_START_PATTERN)
    if m:
        end = _section_end(text, m.end(), RISK_END_PATTERNS)
        out["risk"] = text[m.start():end]
    return out


# --- US-filer (10-K/10-Q) fetch -----------------------------------------

def _index(base: str) -> dict:
    return json.loads(_get(base + "/index.json"))


def _primary_doc_url_us(base: str) -> str | None:
    idx = _index(base)
    items = idx["directory"]["item"]
    cands = [it for it in items if re.match(r"^[a-z][a-z0-9]*-\d{8}\.htm$", it["name"])]
    if not cands:
        # Filing-agent naming is NOT standardized across issuers -- MU/LLY/VST use
        # "ticker-YYYYMMDD.htm", but AXTI uses "axti20251231_10k.htm" (no hyphen,
        # "_10k" suffix) and RGTI uses "rgti-20251231x10k.htm" ("x10k" suffix).
        # Rather than enumerate every vendor's convention, fall back to the
        # largest real .htm file in the filing (R*.htm are tiny XBRL-viewer
        # rendering fragments; exhibits/certifications are always far smaller
        # than the filing body itself -- verified: AXTI body 3.2MB vs largest
        # exhibit 49KB).
        cands = [it for it in items if it["name"].lower().endswith(".htm")
                 and not re.match(r"^r\d+\.htm$", it["name"], re.I)
                 and "index" not in it["name"].lower()]
    if not cands:
        return None
    if len(cands) > 1:
        cands.sort(key=lambda it: int(it.get("size") or 0), reverse=True)
    return base + "/" + cands[0]["name"]


def fetch_us_filing(base: str) -> dict:
    url = _primary_doc_url_us(base)
    if not url:
        return {"error": "no primary doc found", "mda": "", "risk": ""}
    raw = _get(url)
    text = _clean(raw)
    secs = _extract_sections_us(text)
    return {"url": url, "doc_chars": len(text), **secs}


# --- CCJ (40-F/6-K) fetch --------------------------------------------------

def _ccj_probe_exhibits(base: str, needle_res: list[str], max_probe: int = 8):
    """Fetch index.json, probe .htm exhibits (largest-first, skip the tiny
    cover-page '*6k.htm'/'*40f.htm' wrapper and image files) for one whose
    OWN TITLE (first ~250 chars -- the "EXHIBIT 99.X <Company> <Year> <Title>"
    line every Cameco exhibit opens with) matches any of needle_res. Returns
    (name, cleaned_text) or (None, None).

    NB the window used to be the first ~4000 chars, which is wrong: CCJ's
    Annual Information Form (ex99.1) mentions "management's discussion and
    analysis" in its own front matter well within the first 4000 chars (cross-
    referencing the OTHER exhibit), so the MD&A probe stopped at the AIF
    instead of continuing on to find the real MD&A exhibit (ex99.3) -- caught
    because fetch_ccj_annual's mda_url and aif_url came back identical for
    every 40-F. Matching on the short title-only window fixes this."""
    idx = _index(base)
    items = [it for it in idx["directory"]["item"] if it["name"].endswith(".htm")
             and not re.search(r"6k\.htm$|40f\.htm$|f10k\.htm$", it["name"])]
    items.sort(key=lambda it: int(it.get("size") or 0), reverse=True)
    for it in items[:max_probe]:
        try:
            raw = _get(base + "/" + it["name"])
        except Exception:
            continue
        text = _clean(raw)
        head = text[:250]
        if any(re.search(nr, head, re.I) for nr in needle_res):
            return it["name"], text
        time.sleep(_PAUSE)
    return None, None


def fetch_ccj_quarterly(base: str) -> dict:
    name, text = _ccj_probe_exhibits(base, [r"management.?s discussion and analysis"])
    if not text:
        return {"error": "no MD&A exhibit found", "mda": "", "risk": ""}
    return {"url": base + "/" + name, "doc_chars": len(text), "mda": text[:SECTION_CAP], "risk": ""}


def fetch_ccj_annual(base: str) -> dict:
    mname, mtext = _ccj_probe_exhibits(base, [r"management.?s discussion and analysis"])
    aname, atext = _ccj_probe_exhibits(base, [r"annual information form"])
    risk = ""
    if atext:
        # Cameco's AIF titles its risk section "Risks that can affect our
        # business" (confirmed from the AIF's own ToC), NOT "Risk Factors" --
        # the generic US-filer phrase never appears as a heading in this
        # document at all (its one hit, previously mistaken for the section,
        # was an incidental "risk factors" mention inside an Audit Committee
        # Charter appendix). This is itself a CCJ/FPI-regime finding: risk
        # terminology isn't standardized outside the US Item-1A convention.
        m = _last_match_start(atext, r"(?i)risks that (?:can|may) affect our business")
        if m:
            end = _section_end(atext, m.end(), [r"(?i)legal proceedings", r"(?i)investor information",
                                                  r"(?i)governance", r"(?i)appendix"])
            risk = atext[m.start():end]
    out = {"mda": (mtext or "")[:SECTION_CAP], "risk": risk[:SECTION_CAP],
           "mda_url": (base + "/" + mname) if mname else None,
           "aif_url": (base + "/" + aname) if aname else None}
    if not mtext and not risk:
        out["error"] = "no MD&A/AIF exhibit found"
    return out


# --- filing enumeration via defeatbeta sec_filing() ------------------------

def list_filings(ticker: str):
    from defeatbeta_api.data.ticker import Ticker
    f = _quiet(Ticker(ticker).sec_filing)
    if hasattr(f, "data"):
        f = f.data
    return f


def list_transcripts(ticker: str, start: str, end: str):
    from defeatbeta_api.data.ticker import Ticker
    t = _quiet(Ticker, ticker)
    tr = _quiet(t.earning_call_transcripts)
    lst = _quiet(tr.get_transcripts_list)
    rows = []
    for _, row in lst.iterrows():
        rd = str(row["report_date"])
        if not (start <= rd <= end):
            continue
        try:
            df = _quiet(tr.get_transcript, int(row["fiscal_year"]), int(row["fiscal_quarter"]))
        except Exception as e:
            print(f"[{ticker}] transcript {row['fiscal_year']}Q{row['fiscal_quarter']} FAILED: {e}")
            continue
        if df is None or len(df) == 0:
            continue
        text = " ".join(str(x) for x in df["content"].tolist())
        if len(text) < 500:
            print(f"[{ticker}] transcript {row['fiscal_year']}Q{row['fiscal_quarter']} SKIPPED ({len(text)} chars)")
            continue
        s = score_text(text)
        s.update({"fiscal_year": int(row["fiscal_year"]), "fiscal_quarter": int(row["fiscal_quarter"]),
                   "report_date": rd})
        rows.append(s)
    return sorted(rows, key=lambda r: r["report_date"])


# --- diff (Lazy-Prices increment) across a same-series sequence ------------

def diff_series(rows: list[dict]) -> list[dict]:
    """rows: sorted list of {..., fired_constrained, fired_loosening}. Returns
    per-row added/dropped phrase indices vs the PRECEDING row in this series
    (first row has no diff)."""
    out = []
    prev = None
    for r in rows:
        if prev is None:
            out.append({"added_c": [], "dropped_c": [], "added_l": [], "dropped_l": []})
        else:
            fc, pc = r["fired_constrained"], prev["fired_constrained"]
            fl, pl = r["fired_loosening"], prev["fired_loosening"]
            out.append({
                "added_c": [i for i in range(len(fc)) if fc[i] and not pc[i]],
                "dropped_c": [i for i in range(len(fc)) if pc[i] and not fc[i]],
                "added_l": [i for i in range(len(fl)) if fl[i] and not pl[i]],
                "dropped_l": [i for i in range(len(fl)) if pl[i] and not fl[i]],
            })
        prev = r
    return out


def nearest_transcript_before(filing_date: str, tx_rows: list[dict], max_gap_days: int = 45):
    from datetime import date
    fd = date.fromisoformat(filing_date)
    best = None
    for r in tx_rows:
        rd = date.fromisoformat(r["report_date"])
        gap = (fd - rd).days
        if 0 <= gap <= max_gap_days:
            if best is None or gap < best[1]:
                best = (r, gap)
    return best


# --- per-case driver ---------------------------------------------------------

def run_us_case(cfg: dict) -> dict:
    tk = cfg["ticker"]
    f = list_filings(tk)
    sub = f[f["form_type"].isin(["10-K", "10-Q"])].copy()
    import pandas as pd
    sub["fd"] = pd.to_datetime(sub["filing_date"])
    sub = sub[(sub["fd"] >= cfg["filing_start"]) & (sub["fd"] <= cfg["filing_end"])].sort_values("filing_date")

    filing_rows = {"10-K": [], "10-Q": []}
    for _, r in sub.iterrows():
        form, fd, rd, url = r["form_type"], r["filing_date"], str(r["report_date"]), r["filing_url"]
        print(f"[{tk}] fetching {form} filed {fd} (period {rd}) ...")
        try:
            res = fetch_us_filing(url)
        except Exception as e:
            print(f"[{tk}] {form} {fd} FAILED: {e}")
            res = {"error": str(e), "mda": "", "risk": ""}
        combined = (res.get("mda", "") + " " + res.get("risk", "")).strip()
        s = score_text(combined) if combined else {
            "n_words": 0, "constrained_hits": 0, "loosening_hits": 0, "score_per_1000w": 0.0,
            "fired_constrained": [False] * len(CONSTRAINED_RE), "fired_loosening": [False] * len(LOOSENING_RE)}
        s_mda = score_text(res.get("mda", "")) if res.get("mda") else None
        s_risk = score_text(res.get("risk", "")) if res.get("risk") else None
        row = {"form": form, "filing_date": fd, "period_end": rd,
               "mda_chars": len(res.get("mda", "")), "risk_chars": len(res.get("risk", "")),
               "mda_score": s_mda["score_per_1000w"] if s_mda else None,
               "risk_score": s_risk["score_per_1000w"] if s_risk else None,
               "combined_score": s["score_per_1000w"], "combined_words": s["n_words"],
               "constrained_hits": s["constrained_hits"], "loosening_hits": s["loosening_hits"],
               "fired_constrained": s["fired_constrained"], "fired_loosening": s["fired_loosening"],
               "url": res.get("url"), "error": res.get("error")}
        filing_rows[form].append(row)
        time.sleep(_PAUSE)

    for form in filing_rows:
        filing_rows[form].sort(key=lambda r: r["filing_date"])
        diffs = diff_series(filing_rows[form])
        for row, d in zip(filing_rows[form], diffs):
            row["diff"] = d

    print(f"[{tk}] fetching transcripts {cfg['tx_start']}..{cfg['tx_end']} ...")
    tx_rows = list_transcripts(tk, cfg["tx_start"], cfg["tx_end"])

    all_filings = sorted(filing_rows["10-K"] + filing_rows["10-Q"], key=lambda r: r["filing_date"])
    for row in all_filings:
        m = nearest_transcript_before(row["filing_date"], tx_rows)
        if m:
            tx, gap = m
            row["nearest_tx_report_date"] = tx["report_date"]
            row["nearest_tx_score"] = tx["score_per_1000w"]
            row["nearest_tx_gap_days"] = gap
        else:
            row["nearest_tx_report_date"] = None

    return {"ticker": tk, "regime": "us", "narrative": cfg["narrative"],
            "filing_rows": filing_rows, "all_filings_sorted": all_filings, "tx_rows": tx_rows}


def run_ccj_case(cfg: dict) -> dict:
    tk = cfg["ticker"]
    print(f"[{tk}] fetching transcripts {cfg['tx_start']}..{cfg['tx_end']} ...")
    tx_rows = list_transcripts(tk, cfg["tx_start"], cfg["tx_end"])
    tx_report_dates = [r["report_date"] for r in tx_rows]

    f = list_filings(tk)
    import pandas as pd
    six_k = f[f["form_type"] == "6-K"].copy()
    six_k["fd"] = pd.to_datetime(six_k["filing_date"])
    forty_f = f[f["form_type"] == "40-F"].copy()
    forty_f["fd"] = pd.to_datetime(forty_f["filing_date"])

    quarterly_rows = []
    for rd in tx_report_dates:
        if not (cfg["filing_start"] <= rd <= cfg["filing_end"]):
            continue
        rdt = pd.Timestamp(rd)
        cand = six_k[(six_k["fd"] - rdt).abs() <= pd.Timedelta(days=3)]
        matched = False
        for _, r in cand.iterrows():
            print(f"[{tk}] probing quarterly 6-K filed {r['filing_date']} (matches transcript {rd}) ...")
            try:
                res = fetch_ccj_quarterly(r["filing_url"])
            except Exception as e:
                print(f"[{tk}] 6-K {r['filing_date']} FAILED: {e}")
                res = {"error": str(e), "mda": "", "risk": ""}
            if res.get("mda"):
                matched = True
                s = score_text(res["mda"])
                quarterly_rows.append({"form": "6-K(quarterly)", "filing_date": r["filing_date"],
                                        "period_end": rd, "mda_chars": len(res["mda"]), "risk_chars": 0,
                                        "mda_score": s["score_per_1000w"], "risk_score": None,
                                        "combined_score": s["score_per_1000w"], "combined_words": s["n_words"],
                                        "constrained_hits": s["constrained_hits"], "loosening_hits": s["loosening_hits"],
                                        "fired_constrained": s["fired_constrained"], "fired_loosening": s["fired_loosening"],
                                        "url": res.get("url"), "error": None,
                                        "nearest_tx_report_date": rd, "nearest_tx_gap_days": 0})
                break
            time.sleep(_PAUSE)
        if not matched:
            print(f"[{tk}] NO MD&A exhibit found among 6-Ks near transcript {rd} -- gap marked")
            quarterly_rows.append({"form": "6-K(quarterly)", "filing_date": None, "period_end": rd,
                                    "mda_chars": 0, "risk_chars": 0, "mda_score": None, "risk_score": None,
                                    "combined_score": None, "combined_words": 0, "constrained_hits": 0,
                                    "loosening_hits": 0, "fired_constrained": [False] * len(CONSTRAINED_RE),
                                    "fired_loosening": [False] * len(LOOSENING_RE), "url": None,
                                    "error": "no matching 6-K/MD&A exhibit found",
                                    "nearest_tx_report_date": rd, "nearest_tx_gap_days": 0})
        time.sleep(_PAUSE)

    annual_rows = []
    ff = forty_f[(forty_f["fd"] >= cfg["filing_start"]) & (forty_f["fd"] <= cfg["filing_end"])].sort_values("filing_date")
    for _, r in ff.iterrows():
        print(f"[{tk}] probing 40-F filed {r['filing_date']} (period {r['report_date']}) ...")
        try:
            res = fetch_ccj_annual(r["filing_url"])
        except Exception as e:
            print(f"[{tk}] 40-F {r['filing_date']} FAILED: {e}")
            res = {"error": str(e), "mda": "", "risk": ""}
        combined = (res.get("mda", "") + " " + res.get("risk", "")).strip()
        s = score_text(combined) if combined else {
            "n_words": 0, "constrained_hits": 0, "loosening_hits": 0, "score_per_1000w": 0.0,
            "fired_constrained": [False] * len(CONSTRAINED_RE), "fired_loosening": [False] * len(LOOSENING_RE)}
        s_mda = score_text(res["mda"]) if res.get("mda") else None
        s_risk = score_text(res["risk"]) if res.get("risk") else None
        annual_rows.append({"form": "40-F", "filing_date": r["filing_date"], "period_end": str(r["report_date"]),
                             "mda_chars": len(res.get("mda", "")), "risk_chars": len(res.get("risk", "")),
                             "mda_score": s_mda["score_per_1000w"] if s_mda else None,
                             "risk_score": s_risk["score_per_1000w"] if s_risk else None,
                             "combined_score": s["score_per_1000w"], "combined_words": s["n_words"],
                             "constrained_hits": s["constrained_hits"], "loosening_hits": s["loosening_hits"],
                             "fired_constrained": s["fired_constrained"], "fired_loosening": s["fired_loosening"],
                             "url": res.get("mda_url"), "error": res.get("error")})
        m = nearest_transcript_before(r["filing_date"], tx_rows, max_gap_days=210)
        if m:
            tx, gap = m
            annual_rows[-1]["nearest_tx_report_date"] = tx["report_date"]
            annual_rows[-1]["nearest_tx_gap_days"] = gap
        time.sleep(_PAUSE)

    quarterly_rows.sort(key=lambda r: r["period_end"])
    annual_rows.sort(key=lambda r: r["filing_date"])
    for series in (quarterly_rows, annual_rows):
        diffs = diff_series(series)
        for row, d in zip(series, diffs):
            row["diff"] = d

    filing_rows = {"6-K(quarterly)": quarterly_rows, "40-F": annual_rows}
    all_filings = sorted(quarterly_rows + [r for r in annual_rows],
                          key=lambda r: r["filing_date"] or r["period_end"])
    return {"ticker": tk, "regime": "ccj", "narrative": cfg["narrative"],
            "filing_rows": filing_rows, "all_filings_sorted": all_filings, "tx_rows": tx_rows}


def main():
    results = {}
    for cfg in CASES:
        print(f"\n===== CASE {cfg['ticker']} =====")
        if cfg["regime"] == "us":
            results[cfg["ticker"]] = run_us_case(cfg)
        else:
            results[cfg["ticker"]] = run_ccj_case(cfg)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(f"\nWrote case data -> {OUT_JSON}")


if __name__ == "__main__":
    main()
