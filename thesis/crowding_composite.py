"""thesis/crowding_composite.py -- Feature-5 (sentiment/crowding) composite for the magnifier
rubric (Fable 交接書 P2-17 / docs/2026-07-12_dashboard_design_v3.md backlog item #17: "擁擠 |
三輸入複合(analyst 出席數 pctile / GS flow Z / bull-ratio)").

WHY: every quantitative proxy tried before analyst-attendance was either snapshot-only (yfinance
heldPercentInstitutions/numberOfAnalystOpinions) or backtested with no edge (dollar-volume
turnover) -- see backtest/results/2026-07-11_institutional_ownership_crowding_axis.md. The
2026-07-12 feasibility probe (backtest/experiments/exp_analyst_attendance.py,
backtest/results/2026-07-12_analyst_attendance_crowding_probe.md) validated a free, Karst-native
proxy: the distinct count of sell-side analysts who ask a question on a name's own earnings call,
pulled from thesis/corpus.db's transcript full text. Direction confirmed: MU's 20-year LOW
attendance quarter landed exactly at its "dead cyclical" price bottom (2023-09-27, 4 analysts);
USAC (Discovery Radar's "2nd percentile, undiscovered" name) has the lowest average attendance of
any comparator tested. More analysts show up <=> more crowded/covered.

KNOWN PRE-EXISTING BUG (this module's first job, before assembling the composite): the probe
found all 4 NVDA 2025 quarters (02-26/05-28/08-27/11-19) failed to parse (0 analysts). Root
cause, confirmed by inspecting the raw transcript text: those 4 quarters tag the conference-call
operator by their own FIRST NAME ("Christa:", "Sarah:") instead of the literal "Operator:" tag
that exp_analyst_attendance.py's _qa_boundary() requires to find the prepared-remarks/Q&A
boundary. Every other NVDA quarter observed (2018-2026) opens with the SAME structural pattern --
the very first dialogue speaker in the transcript is always the operator, literal-tagged or not --
so the fix generalizes: try the literal "Operator" tag first (unchanged behaviour for the ~95% of
transcripts that already parse fine); only if that yields ZERO occurrences, fall back to treating
the FIRST speaker's own tag as the operator role. See _qa_boundary() below.

Per the task instruction, exp_analyst_attendance.py itself is NOT modified -- this module
re-implements the extractor (adapted from it) with the fix applied, self-contained.

THREE INPUTS -- each converted to a 0-100 "higher number = more crowded" reading before averaging
(direction stated explicitly per input, per instruction):
  1. analyst_attendance_pctile (available). TEMPORAL, per ticker: percentile rank of the LATEST
     successfully-parsed quarter's distinct-analyst count within that ticker's OWN full corpus.db
     history (all successfully-parsed quarters; requires >= MIN_QUARTERS or the ticker is excluded,
     not fabricated -- controls for each name's own secular coverage trend, per the probe's
     finding that raw counts drift across eras). Theme-level = median across covered tickers.
     Direction: latest count HIGH vs this name's own history -> MORE crowded (HIGH pctile).
  2. gs_flow_z (NOT AVAILABLE). Searched the repo (backtest/data.py, thesis/*.py,
     backtest/experiments/*.py, docs/*.md) for any Goldman Sachs prime-brokerage/flow data
     ingestion -- none exists. The only repo mentions are forward-looking PROSE: docs/2026-07-12_
     dashboard_design_v3.md ("P1-2 落地前先顯示 bull-ratio", i.e. this input was explicitly
     deferred) and docs/2026-07-13_fable_session_handover.md backlog item #17 (this very task).
     Marked 'not_available' for every theme -- not fabricated, per hard instruction.
  3. bull_ratio (available). CROSS-SECTIONAL (not temporal -- no per-theme report history long
     enough for an own-history percentile), computed today from thesis/.raw/gooptions/
     research-manifest.json: share of reports, among those whose primary_ticker sits in the
     theme's ticker list, tagged thesisType == 'bull'. Empirically this manifest carries ONLY
     'bull' (39) and 'neutral' (84) values -- NO 'bear' category exists in this corpus (confirmed
     by direct inspection), consistent with thesis/DESIGN.md's observation that gooptions-style
     Tier-2 research skews bullish by construction. Requires >= MIN_REPORTS (>=1) matching report
     or 'not_available'; n_bull/n_total is ALWAYS printed alongside the ratio so a thin (e.g. 1/1)
     read is never mistaken for a robust one. Direction: MORE of the available commentary on this
     theme's names is bullish -> MORE crowded/consensus (thesis/DESIGN.md discipline #4: bullish
     coverage is itself a crowding signal, not confirmation).

composite_pctile = mean of whichever of {1, 3} are available for a theme (2 is never available
today, honestly disclosed). A theme with NEITHER available is 'insufficient_data', never defaulted
to a fabricated number.

Run: python thesis/crowding_composite.py   (PYTHONUTF8=1 recommended)
Writes: thesis/.raw/crowding_composite.json (gitignored, regenerable by re-running this script)
Prints: the same theme table written into the paired backtest/results/*.md report.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402
import yaml  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(ROOT)
CORPUS_DB = os.path.join(ROOT, "corpus.db")
THEMES_PATH = os.path.join(ROOT, "themes.yaml")
MANIFEST_PATH = os.path.join(ROOT, ".raw", "gooptions", "research-manifest.json")
OUT_JSON = os.path.join(ROOT, ".raw", "crowding_composite.json")

MIN_QUARTERS = 8     # >=2yr of quarterly transcripts before a ticker's attendance pctile counts
MIN_REPORTS = 1       # >=1 matching gooptions report before a theme's bull_ratio counts (n always shown)

# ---------------------------------------------------------------------------------------------
# Transcript analyst-attendance extractor -- adapted from backtest/experiments/
# exp_analyst_attendance.py (NOT modified there; the operator-tag generalization fix below is
# NEW, added here per task instruction). All other logic (header-block roster parse, speaker-tag
# Q&A-boundary parse, name cleaning) is carried over unchanged because the probe already verified
# it (1.6% failure rate across 434 quarters / 6 tickers) -- only the NVDA-2025-class bug is fixed.
# ---------------------------------------------------------------------------------------------

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


def _clean_name(raw: str) -> str:
    raw = raw.strip().strip("[]").strip()
    raw = re.sub(r"^[QA]\s*[-–]\s*", "", raw)
    return NAME_SPLIT_RE.split(raw, maxsplit=1)[0].strip()


def _extract_header_block(body: str, key: str) -> set[str] | None:
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
    out = []
    for p in body.split("\n\n"):
        m = SPEAKER_RE.match(p)
        if m:
            out.append((m.group(1).strip(), p))
    return out


def _qa_boundary(speakers: list[tuple[str, str]]) -> tuple[int | None, str]:
    """Index of the operator turn that hands off to Q&A, plus the tag used as "the operator" for
    exclusion purposes downstream. Returns (None, tag) if no boundary can be located.

    FIX (this module, 2026-07-13): the original exp_analyst_attendance.py hardcodes the literal
    tag "Operator". That breaks on transcripts where the call operator is tagged by their own
    first name instead (confirmed on NVDA transcript-NVDA-2025-{02-26,05-28,08-27,11-19}: opens
    "Christa: Good afternoon..." / "Sarah: Good afternoon..." -- the SAME person reappears to hand
    off every question, e.g. "Christa: ... And your first question comes from C.J. Muse ..." --
    structurally identical to the "Operator:"-tagged format, just a different literal string).
    The operator is, in every transcript observed across eras (confirmed on NVDA 2018-2026 and
    spot-checked on MU/AVGO/USAC/WST/FSLR), the very FIRST dialogue speaker in the document. So:
    try the literal "Operator" tag first (identical behaviour to the original for the ~95% of
    transcripts that already parse fine); only fall back to "whichever tag the first speaker
    used" when NO literal "Operator" tag exists anywhere in the transcript at all.
    """
    if not speakers:
        return None, "Operator"
    op_idx = [i for i, (t, _) in enumerate(speakers) if t == "Operator"]
    operator_tag = "Operator"
    if not op_idx:
        operator_tag = speakers[0][0]
        op_idx = [i for i, (t, _) in enumerate(speakers) if t == operator_tag]
    phrase_idx = [i for i in op_idx[1:] if FIRST_Q_RE.search(speakers[i][1])]
    if phrase_idx:
        return phrase_idx[0], operator_tag
    if len(op_idx) >= 2:
        return op_idx[1], operator_tag
    return None, operator_tag


def extract_analysts(body: str) -> tuple[set[str], str]:
    """Returns (set of analyst names, method: 'speakertag' | 'header_roster_fallback' | 'failed')."""
    speakers = _dialogue_speakers_ordered(body)
    boundary, operator_tag = _qa_boundary(speakers)
    execs = _extract_header_block(body, "Executives")
    if boundary is not None:
        pre_roster = {_clean_name(t) for t, _ in speakers[:boundary] if t != operator_tag}
        exclude = pre_roster | {operator_tag}
        if execs:
            exclude |= {_clean_name(e) for e in execs}
        post = {_clean_name(t) for t, _ in speakers[boundary + 1:]}
        candidates = {
            c for c in post
            if c and c not in exclude and c.lower() not in GENERIC_TAGS and len(c) > 1
        }
        if candidates:
            return candidates, "speakertag"
    roster = _extract_header_block(body, "Analysts")
    if roster:
        return {_clean_name(r) for r in roster if _clean_name(r)}, "header_roster_fallback"
    return set(), "failed"


def get_transcripts(con: sqlite3.Connection, ticker: str) -> list[tuple[str, str, str]]:
    rows = con.execute(
        "SELECT d.id, d.slug, d.published FROM docs d "
        "WHERE d.thesistype='transcript' AND d.primary_ticker=? ORDER BY d.published",
        (ticker,),
    ).fetchall()
    out = []
    for did, slug, pub in rows:
        r = con.execute("SELECT body FROM docs_fts_en WHERE rowid=?", (did,)).fetchone()
        out.append((slug, pub, r[0] if r else ""))
    return out


def attendance_series(con: sqlite3.Connection, ticker: str) -> pd.DataFrame:
    rows = []
    for slug, pub, body in get_transcripts(con, ticker):
        names, method = extract_analysts(body)
        rows.append({"ticker": ticker, "slug": slug, "published": pub,
                      "n_analysts": len(names), "method": method})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["published"] = pd.to_datetime(df["published"])
        df = df.sort_values("published").reset_index(drop=True)
    return df


def ticker_attendance_pctile(con: sqlite3.Connection, ticker: str) -> dict:
    """Own-history percentile of the LATEST successfully-parsed quarter's analyst count.
    status: 'ok' | 'insufficient_history' | 'no_transcripts'."""
    df = attendance_series(con, ticker)
    if df.empty:
        return {"status": "no_transcripts", "pctile": None, "n_quarters_ok": 0,
                "latest_n_analysts": None, "latest_date": None}
    ok = df[df["method"] != "failed"]
    n_ok = len(ok)
    if n_ok < MIN_QUARTERS:
        return {"status": "insufficient_history", "pctile": None, "n_quarters_ok": n_ok,
                "latest_n_analysts": None, "latest_date": None}
    latest = ok.iloc[-1]
    hist = ok["n_analysts"]
    pctile = float((hist <= latest["n_analysts"]).mean() * 100.0)
    return {
        "status": "ok", "pctile": round(pctile, 1), "n_quarters_ok": n_ok,
        "latest_n_analysts": int(latest["n_analysts"]),
        "latest_date": str(latest["published"].date()),
    }


# ---------------------------------------------------------------------------------------------
# bull_ratio -- cross-sectional read from thesis/.raw/gooptions/research-manifest.json
# ---------------------------------------------------------------------------------------------

def load_manifest_items() -> list[dict]:
    if not os.path.exists(MANIFEST_PATH):
        return []
    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("items", []) or []


def _primary_tickers(item: dict) -> set[str]:
    p = item.get("primary_ticker")
    if isinstance(p, list):
        return set(p)
    if p:
        return {p}
    return set(item.get("primary_tickers") or [])


def theme_bull_ratio(items: list[dict], theme_tickers: set[str]) -> dict:
    matched = [it for it in items if _primary_tickers(it) & theme_tickers]
    n_total = len(matched)
    if n_total < MIN_REPORTS:
        return {"status": "not_available", "ratio": None, "n_bull": 0, "n_total": n_total}
    n_bull = sum(1 for it in matched if it.get("thesisType") == "bull")
    return {"status": "ok", "ratio": round(n_bull / n_total, 3), "n_bull": n_bull, "n_total": n_total}


# ---------------------------------------------------------------------------------------------
# themes.yaml
# ---------------------------------------------------------------------------------------------

def load_active_themes() -> dict:
    with open(THEMES_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    themes = data.get("themes", {}) or {}
    return {slug: t for slug, t in themes.items() if t.get("status", "active") == "active"}


# ---------------------------------------------------------------------------------------------
# NVDA 2025 before/after regression check (acceptance criterion #1) -- NVDA is intentionally
# excluded from every active theme's ticker list (it is the "incumbent"/downstream-demand name
# every thesis note explicitly excludes, e.g. ai-power-grid/tpu-custom-silicon notes), so this
# does NOT feed the composite -- it is a standalone validation of the operator-tag fix.
# ---------------------------------------------------------------------------------------------

def _qa_boundary_literal_operator_only(speakers: list[tuple[str, str]]) -> int | None:
    """Reproduces the ORIGINAL exp_analyst_attendance.py boundary logic exactly (literal
    "Operator" tag only, no fallback) -- used solely to compute the 'before' side of the NVDA
    2025 regression check below. Confirmed empirically: none of the 4 affected 2025 quarters
    contain a literal "Operator" tag at all (op_idx is always empty), so this always returns
    None for them -> extract_analysts' caller treats that as 0 analysts / method='failed',
    matching the probe's reported result exactly."""
    op_idx = [i for i, (t, _) in enumerate(speakers) if t == "Operator"]
    if not op_idx:
        return None
    phrase_idx = [i for i in op_idx[1:] if FIRST_Q_RE.search(speakers[i][1])]
    if phrase_idx:
        return phrase_idx[0]
    if len(op_idx) >= 2:
        return op_idx[1]
    return None


def nvda_2025_before_after(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute(
        "SELECT d.id, d.slug, d.published FROM docs d WHERE d.thesistype='transcript' "
        "AND d.primary_ticker='NVDA' AND d.published >= '2025-01-01' AND d.published < '2026-01-01' "
        "ORDER BY d.published",
    ).fetchall()
    out = []
    for did, slug, pub in rows:
        r = con.execute("SELECT body FROM docs_fts_en WHERE rowid=?", (did,)).fetchone()
        body = r[0] if r else ""
        speakers = _dialogue_speakers_ordered(body)
        before_boundary = _qa_boundary_literal_operator_only(speakers)
        before_n, before_method = (0, "failed") if before_boundary is None else (None, "speakertag")
        after_names, after_method = extract_analysts(body)
        out.append({"slug": slug, "published": pub, "before_n_analysts": before_n,
                    "before_method": before_method,
                    "after_n_analysts": len(after_names), "after_method": after_method})
    return out


# ---------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------

def run():
    con = sqlite3.connect(f"file:{CORPUS_DB}?mode=ro", uri=True)
    manifest_items = load_manifest_items()
    themes = load_active_themes()

    print(f"=== crowding_composite: {len(themes)} active themes, corpus.db={CORPUS_DB}, "
          f"manifest_items={len(manifest_items)} ===\n")

    # --- NVDA 2025 regression check (acceptance criterion, NVDA not in any active theme) ---
    print("--- NVDA 2025 parser-fix regression check (NVDA feeds no active theme; standalone check) ---")
    nvda_check = nvda_2025_before_after(con)
    for r in nvda_check:
        print(f"  {r['slug']:<26} before={r['before_n_analysts']:>2} ({r['before_method']:<7})  "
              f"after={r['after_n_analysts']:>2} ({r['after_method']})")
    print()

    ticker_cache: dict[str, dict] = {}

    def get_ticker_attendance(sym: str) -> dict:
        if sym not in ticker_cache:
            ticker_cache[sym] = ticker_attendance_pctile(con, sym)
        return ticker_cache[sym]

    theme_rows = {}
    for slug, t in sorted(themes.items()):
        tickers = t.get("tickers") or []
        tick_set = set(tickers)

        # input 1: attendance
        per_ticker = {sym: get_ticker_attendance(sym) for sym in tickers}
        usable = {sym: v for sym, v in per_ticker.items() if v["status"] == "ok"}
        skipped = {sym: v for sym, v in per_ticker.items() if v["status"] != "ok"}
        if usable:
            pctiles = pd.Series([v["pctile"] for v in usable.values()])
            attendance = {"status": "ok", "value": round(float(pctiles.median()), 1),
                          "tickers_used": sorted(usable.keys()),
                          "tickers_skipped": {sym: v["status"] for sym, v in skipped.items()}}
        else:
            attendance = {"status": "ticker覆蓋不足" if tickers else "no_tickers", "value": None,
                          "tickers_used": [], "tickers_skipped": {sym: v["status"] for sym, v in skipped.items()}}

        # input 2: GS flow -- never available
        gs_flow = {"status": "not_available", "value": None,
                   "reason": "repo 內無任何 GS prime-brokerage/flow 數據源(見 module docstring),唔造數"}

        # input 3: bull_ratio
        br = theme_bull_ratio(manifest_items, tick_set)
        bull_ratio = {"status": br["status"],
                      "value": round(br["ratio"] * 100.0, 1) if br["ratio"] is not None else None,
                      "n_bull": br["n_bull"], "n_total": br["n_total"]}

        available_vals = [x["value"] for x in (attendance, bull_ratio) if x["status"] == "ok" and x["value"] is not None]
        if available_vals:
            composite = round(sum(available_vals) / len(available_vals), 1)
            comp_status = "ok"
        else:
            composite = None
            comp_status = "insufficient_data"

        theme_rows[slug] = {
            "composite_pctile": composite,
            "composite_status": comp_status,
            "n_inputs_available": len(available_vals),
            "inputs": {
                "attendance": attendance,
                "gs_flow": gs_flow,
                "bull_ratio": bull_ratio,
            },
        }

    # ---- print summary table ----
    header = f"{'theme':<32}{'composite':>10}{'attendance':>12}{'bull_ratio':>14}{'gs_flow':>12}{'n_in':>6}"
    print(header)
    print("-" * len(header))
    for slug in sorted(theme_rows):
        r = theme_rows[slug]
        comp_s = f"{r['composite_pctile']:.1f}" if r["composite_pctile"] is not None else "n/a"
        att = r["inputs"]["attendance"]
        att_s = f"{att['value']:.1f}" if att["value"] is not None else "n/a"
        br = r["inputs"]["bull_ratio"]
        br_s = f"{br['value']:.1f}({br['n_bull']}/{br['n_total']})" if br["value"] is not None else f"n/a(0/{br['n_total']})"
        print(f"{slug:<32}{comp_s:>10}{att_s:>12}{br_s:>14}{'n/a':>12}{r['n_inputs_available']:>6}")

    ranked = sorted(
        [(slug, r["composite_pctile"]) for slug, r in theme_rows.items() if r["composite_pctile"] is not None],
        key=lambda x: x[1], reverse=True,
    )
    print(f"\nMost crowded (top 3): {ranked[:3]}")
    print(f"Least crowded (bottom 3): {ranked[-3:]}")

    n_att_ok = sum(1 for r in theme_rows.values() if r["inputs"]["attendance"]["status"] == "ok")
    n_br_ok = sum(1 for r in theme_rows.values() if r["inputs"]["bull_ratio"]["status"] == "ok")
    n_composite_ok = sum(1 for r in theme_rows.values() if r["composite_status"] == "ok")
    print(f"\nCoverage: attendance ok {n_att_ok}/{len(theme_rows)}, bull_ratio ok {n_br_ok}/{len(theme_rows)}, "
          f"gs_flow ok 0/{len(theme_rows)}, composite computed {n_composite_ok}/{len(theme_rows)}")

    # ---- write JSON ----
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "attendance": "per-ticker temporal own-history percentile of latest successfully-parsed "
                           "quarter's distinct-analyst Q&A count (corpus.db); theme = median across "
                           f"tickers with >= {MIN_QUARTERS} successfully-parsed quarters. Higher = more crowded.",
            "gs_flow": "not_available -- no GS prime-brokerage/flow data source exists in this repo.",
            "bull_ratio": "cross-sectional: share of gooptions research-manifest.json reports (primary_ticker "
                           "in theme tickers) tagged thesisType=='bull' (corpus has only bull/neutral, no bear). "
                           f"Requires >= {MIN_REPORTS} matching report. Higher = more crowded/consensus.",
            "composite": "mean of whichever of {attendance, bull_ratio} are available (gs_flow never "
                          "available today); themes with neither are 'insufficient_data', never fabricated.",
            "nvda_2025_fix": "operator-tag generalization -- see module docstring _qa_boundary().",
        },
        "nvda_2025_regression_check": nvda_check,
        "themes": theme_rows,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"\nWrote {OUT_JSON}")
    con.close()
    return theme_rows, nvda_check, (n_att_ok, n_br_ok, n_composite_ok, len(theme_rows))


if __name__ == "__main__":
    run()
