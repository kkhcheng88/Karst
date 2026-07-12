"""EXPLORATORY (not a formal IC pass/fail test -- see thread 2026-07-10): does sector-level
constraint-language DENSITY (fraction of a sector's covered companies whose transcripts mention
supply-constraint phrases) or its MOMENTUM (YoY change in density) show any visible relationship
with the sector's forward returns?

Design (docs/2026-07-09_magnifier_model_plan.md section 3h):
  signal = trailing-4Q density of constraint-phrase mentions, per GICS-equivalent sector
  target = forward 3/6/12mo sector-ETF return, RAW and relative-to-SPY

User's explicit framing (2026-07-10): treat this as UNSUPERVISED/exploratory FIRST -- look for
patterns before committing to a formal supervised IC backtest with pass/fail bars. Also test two
specific concerns raised: (1) is any apparent relationship front-loaded (already priced by the
time the signal could be observed) or does it persist/build over the full horizon -- directly
answers "can we actually react to it"; (2) this is a TRANSCRIPT-only signal -- it structurally
cannot catch market/industry-wide EXOGENOUS news shocks (export bans, disasters) that precede
any company's own earnings commentary -- flagged as an explicit, unaddressed blind spot, not
solved here (that is the IMA/analyst-report layer's job, a separate signal).

Sector classification: defeatbeta Ticker(t).info()['sector'] (local DuckDB cache, ~0.15s/ticker,
Yahoo-style 11-sector taxonomy) mapped 1:1 to the 11 SPDR sector ETFs.

Constraint-phrase matching: reuses thesis/corpus.py's CONSTRAINT_PHRASES list + docs_fts_en
(porter unicode61 FTS5) for the same phrases already validated in this project (see corpus.py
scan()). Adds a NEGATION filter (checks the 8 tokens preceding a match for not/no/without/etc.)
since naive phrase-match would flag "we do NOT expect any supply constraints" as constrained.

    python backtest/experiments/exp_sector_constraint_language.py
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from backtest.data import load  # noqa: E402
from thesis.corpus import CONSTRAINT_PHRASES, DB as CORPUS_DB  # noqa: E402

SECTOR_CACHE = os.path.join(ROOT, "thesis", ".raw", "ticker_sector_cache.json")
RESULTS_MD = os.path.join(ROOT, "backtest", "results", "2026-07-10_sector_constraint_language.md")

SECTOR_TO_ETF = {
    "Technology": "XLK", "Financial Services": "XLF", "Energy": "XLE",
    "Healthcare": "XLV", "Consumer Defensive": "XLP", "Consumer Cyclical": "XLY",
    "Industrials": "XLI", "Communication Services": "XLC", "Utilities": "XLU",
    "Real Estate": "XLRE", "Basic Materials": "XLB",
}
NEGATIONS = {"not", "no", "n't", "without", "unlikely", "never", "avoid", "avoided",
             "avoiding", "isn't", "aren't", "wasn't", "weren't", "don't", "doesn't",
             "didn't", "won't", "wouldn't", "shouldn't", "couldn't", "hasn't", "haven't"}
NEG_WINDOW_TOKENS = 8


# ---------- Step 1: sector classification (cached) ----------------------------------------

def get_transcript_tickers() -> list[str]:
    con = sqlite3.connect(CORPUS_DB)
    rows = con.execute(
        "SELECT DISTINCT primary_ticker FROM docs WHERE thesistype='transcript' "
        "AND primary_ticker IS NOT NULL AND primary_ticker != ''").fetchall()
    con.close()
    return sorted(r[0] for r in rows)


def load_sector_cache() -> dict:
    if os.path.exists(SECTOR_CACHE):
        with open(SECTOR_CACHE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_sector_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(SECTOR_CACHE), exist_ok=True)
    with open(SECTOR_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def classify_sectors(tickers: list[str]) -> dict:
    """Bulk-classify via defeatbeta's local info() (sector field) -- cached so reruns are free."""
    from defeatbeta_api.data.ticker import Ticker
    cache = load_sector_cache()
    todo = [t for t in tickers if t not in cache]
    print(f"[sector] {len(cache)} cached, {len(todo)} to classify...", flush=True)
    t0 = time.time()
    for i, t in enumerate(todo):
        try:
            info = Ticker(t).info()
            cache[t] = info.iloc[0]["sector"] if len(info) else None
        except Exception:
            cache[t] = None
        if (i + 1) % 250 == 0:
            save_sector_cache(cache)
            elapsed = time.time() - t0
            print(f"[sector] {i + 1}/{len(todo)} elapsed={elapsed:.0f}s "
                  f"eta={elapsed / (i + 1) * (len(todo) - i - 1):.0f}s", flush=True)
    save_sector_cache(cache)
    print(f"[sector] done, {len(cache)} total classified.", flush=True)
    return cache


# ---------- Step 2: per-ticker-quarter constraint match with negation filter ---------------

def _quarter_of(date_str: str) -> str:
    y, m = int(date_str[:4]), int(date_str[5:7])
    q = (m - 1) // 3 + 1
    return f"{y}Q{q}"


def _negated_at(body: str, match_start: int) -> bool:
    window = body[max(0, match_start - 80):match_start].lower()
    tokens = re.findall(r"[a-z']+", window)
    return any(t in NEGATIONS for t in tokens[-NEG_WINDOW_TOKENS:])


def scan_transcript_constraints() -> pd.DataFrame:
    """Two-stage: FTS5 MATCH narrows to candidate transcripts (cheap), then a python regex pass
    on ONLY those bodies applies the negation filter (avoids full-corpus regex on 196k rows)."""
    con = sqlite3.connect(CORPUS_DB)
    match = " OR ".join(f'"{p}"' for p in CONSTRAINT_PHRASES)
    rows = con.execute(
        "SELECT d.slug, d.primary_ticker, d.published, docs_fts_en.body "
        "FROM docs_fts_en JOIN docs d ON d.slug = docs_fts_en.slug "
        "WHERE d.thesistype='transcript' AND docs_fts_en MATCH ?", (match,)).fetchall()
    con.close()
    print(f"[scan] {len(rows)} candidate transcripts (pre-negation-filter)", flush=True)
    out = []
    for slug, ticker, published, body in rows:
        n_raw, n_kept = 0, 0
        for p in CONSTRAINT_PHRASES:
            for m in re.finditer(re.escape(p), body, re.IGNORECASE):
                n_raw += 1
                if not _negated_at(body, m.start()):
                    n_kept += 1
        out.append({"ticker": ticker, "quarter": _quarter_of(published), "n_raw": n_raw,
                     "n_kept": n_kept, "flagged": n_kept > 0})
    df = pd.DataFrame(out)
    print(f"[scan] {df['flagged'].sum()}/{len(df)} transcripts flagged after negation filter "
          f"({(df['n_raw'].sum() - df['n_kept'].sum())} raw matches dropped as negated)", flush=True)
    return df


# ---------- Step 3: aggregate to sector-quarter density + momentum -------------------------

def build_sector_quarter_panel(scan_df: pd.DataFrame, sector_map: dict) -> pd.DataFrame:
    scan_df = scan_df.copy()
    scan_df["sector"] = scan_df["ticker"].map(sector_map)
    scan_df["etf"] = scan_df["sector"].map(SECTOR_TO_ETF)
    scan_df = scan_df.dropna(subset=["etf"])

    all_con = sqlite3.connect(CORPUS_DB)
    universe = pd.read_sql(
        "SELECT primary_ticker AS ticker, published FROM docs WHERE thesistype='transcript'",
        all_con)
    all_con.close()
    universe["quarter"] = universe["published"].map(_quarter_of)
    universe["sector"] = universe["ticker"].map(sector_map)
    universe["etf"] = universe["sector"].map(SECTOR_TO_ETF)
    universe = universe.dropna(subset=["etf"])

    covered = universe.groupby(["etf", "quarter"])["ticker"].nunique().rename("n_covered")
    flagged = (scan_df[scan_df["flagged"]].groupby(["etf", "quarter"])["ticker"]
               .nunique().rename("n_flagged"))
    panel = pd.concat([covered, flagged], axis=1).fillna(0).reset_index()
    panel["density"] = panel["n_flagged"] / panel["n_covered"].replace(0, np.nan)
    panel = panel.sort_values(["etf", "quarter"]).reset_index(drop=True)
    panel["density_yoy_delta"] = panel.groupby("etf")["density"].diff(4)
    return panel


# ---------- Step 4: sector ETF forward returns ----------------------------------------------

def _quarter_end_date(q: str) -> pd.Timestamp:
    y, qn = int(q[:4]), int(q[5])
    month = qn * 3
    return pd.Timestamp(year=y, month=month, day=1) + pd.offsets.MonthEnd(0)


def attach_forward_returns(panel: pd.DataFrame) -> pd.DataFrame:
    spy = load("SPY")["close"]
    px_cache = {}
    rows = []
    for _, r in panel.iterrows():
        etf = r["etf"]
        if etf not in px_cache:
            try:
                px_cache[etf] = load(etf)["close"]
            except Exception:
                px_cache[etf] = None
        px = px_cache[etf]
        rec = r.to_dict()
        qend = _quarter_end_date(r["quarter"])
        if px is None:
            rows.append(rec)
            continue
        for months, col in [(1, "fwd_1m"), (3, "fwd_3m"), (6, "fwd_6m"), (12, "fwd_12m")]:
            t0 = px.index[px.index <= qend]
            tN = px.index[px.index <= qend + pd.DateOffset(months=months)]
            s0 = spy.index[spy.index <= qend]
            sN = spy.index[spy.index <= qend + pd.DateOffset(months=months)]
            if len(t0) == 0 or len(tN) == 0 or tN[-1] <= t0[-1]:
                rec[col] = None
                rec[col + "_rel"] = None
                continue
            r_etf = px.loc[tN[-1]] / px.loc[t0[-1]] - 1.0
            if len(s0) and len(sN) and sN[-1] > s0[-1]:
                r_spy = spy.loc[sN[-1]] / spy.loc[s0[-1]] - 1.0
            else:
                r_spy = None
            rec[col] = r_etf
            rec[col + "_rel"] = (r_etf - r_spy) if r_spy is not None else None
        rows.append(rec)
    return pd.DataFrame(rows)


# ---------- Step 5: exploratory summary ------------------------------------------------------

def summarize(df: pd.DataFrame) -> str:
    lines = ["# Sector Constraint-Language Density -- Exploratory Pass (2026-07-10)\n"]
    lines.append("> EXPLORATORY, not a formal IC backtest (user-directed: look for patterns "
                  "before committing to a supervised pass/fail test). No placebo/LM control run "
                  "yet -- that is the next step ONLY if something here looks worth formalizing.\n")

    n_q = df["quarter"].nunique()
    lines.append(f"## Coverage\n- Sector-quarters: {len(df)} rows, {n_q} distinct quarters, "
                 f"{df['etf'].nunique()} sector ETFs\n"
                 f"- Quarter range: {df['quarter'].min()} .. {df['quarter'].max()}\n"
                 f"- Median tickers covered per sector-quarter: {df['n_covered'].median():.0f}\n")

    lines.append("## Descriptive correlations (pooled across all sector-quarters, Spearman)\n")
    lines.append("| signal | fwd_3m_rel | fwd_6m_rel | fwd_12m_rel |")
    lines.append("|---|---|---|---|")
    for sig in ["density", "density_yoy_delta"]:
        cells = []
        for h in ["fwd_3m_rel", "fwd_6m_rel", "fwd_12m_rel"]:
            sub = df[[sig, h]].dropna()
            if len(sub) >= 10:
                rho = sub[sig].corr(sub[h], method="spearman")
                cells.append(f"{rho:+.3f} (n={len(sub)})")
            else:
                cells.append(f"n/a (n={len(sub)})")
        lines.append(f"| {sig} | {cells[0]} | {cells[1]} | {cells[2]} |")

    lines.append("\n## Per-sector correlation (density vs fwd_12m_rel, Spearman, n>=8 only)\n")
    lines.append("| sector ETF | rho | n |")
    lines.append("|---|---|---|")
    for etf, g in df.groupby("etf"):
        sub = g[["density", "fwd_12m_rel"]].dropna()
        if len(sub) >= 8:
            rho = sub["density"].corr(sub["fwd_12m_rel"], method="spearman")
            lines.append(f"| {etf} | {rho:+.3f} | {len(sub)} |")

    lines.append("\n## Return front-loading check (top-tercile density readings)\n"
                 "> Directly answers: is the forward-12m relative return already fully realised "
                 "in month 1 (= priced before you could react), or does it persist/build?\n")
    d = df.dropna(subset=["density"])
    if len(d) >= 15:
        thresh = d["density"].quantile(2 / 3)
        top = d[d["density"] >= thresh]
        m1 = top["fwd_1m_rel"].dropna()
        m12 = top["fwd_12m_rel"].dropna()
        lines.append(f"- Top-tercile density threshold: {thresh:.3f} (n={len(top)} sector-quarters)")
        lines.append(f"- Mean fwd_1m_rel (n={len(m1)}): {m1.mean():+.4f}" if len(m1) else "- fwd_1m_rel: n/a")
        lines.append(f"- Mean fwd_12m_rel (n={len(m12)}): {m12.mean():+.4f}" if len(m12) else "- fwd_12m_rel: n/a")
        if len(m1) and len(m12) and m12.mean() != 0:
            frac = m1.mean() / m12.mean()
            lines.append(f"- Month-1 share of the 12m move: {frac * 100:.0f}% "
                         f"({'FRONT-LOADED -- caution, may already be priced by signal date' if frac > 0.5 else 'spread across the year -- consistent with a slow-diffusion, tradeable signal'})")
    else:
        lines.append("- Not enough top-tercile observations yet.")

    lines.append("\n## Honest caveats\n"
                 "- Transcript-only signal: structurally blind to market/industry-wide exogenous "
                 "shocks that precede any single company's own earnings commentary (export bans, "
                 "disasters) -- that is the IMA/analyst-report layer's job, not tested here.\n"
                 "- 11-sector cross-section is thin (same caveat as thesis/forward_ic.py's own "
                 "9-theme panel) -- correlations here are DESCRIPTIVE, not a significance-tested "
                 "verdict.\n"
                 "- No placebo (random-phrase) or LM-tone control run in this pass -- add before "
                 "trusting any positive-looking correlation above.\n")
    return "\n".join(lines)


def main():
    tickers = get_transcript_tickers()
    print(f"[main] {len(tickers)} tickers with transcripts in corpus.db", flush=True)
    sector_map = classify_sectors(tickers)
    scan_df = scan_transcript_constraints()
    panel = build_sector_quarter_panel(scan_df, sector_map)
    df = attach_forward_returns(panel)
    df.to_csv(os.path.join(ROOT, "backtest", "experiments", "_sector_constraint_panel.csv"), index=False)
    report = summarize(df)
    os.makedirs(os.path.dirname(RESULTS_MD), exist_ok=True)
    with open(RESULTS_MD, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n[main] wrote {RESULTS_MD}")
    print(report)


if __name__ == "__main__":
    main()
