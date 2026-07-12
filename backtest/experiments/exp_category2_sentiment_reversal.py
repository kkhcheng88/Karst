"""Objective A, category 2 (2026-07-10/11, v3 -- fixed peak-vs-trough comparison + more cases).

For macro-crisis-driven oracle episodes (recovery bounces, NOT commodity/constraint-driven), test
whether the CRASHED sector's OWN transcripts show a detectable sentiment TURNING POINT (distress
language peaking) AROUND/BEFORE the sector's price genuinely turns -- and, critically, whether that
peak reading would have been READABLE (transcript actually published) early enough to matter.

v1 (2026-07-10): window stopped exactly AT the episode start date, likely clipping the real turning
point. v2 (2026-07-11): extended window past the start; but its "first quarter after the peak with a
LOWER reading" heuristic for picking a "recovery quarter" turned out to be broken -- in both tested
cases (GFC, covid) neg_ratio declined smoothly/monotonically over many quarters with no sharp V, so
the heuristic just grabbed the LAST quarter in the window (an arbitrary stopping point, not a real
signal), producing misleading "-284d / -349d lagged" results.

v3 fix (this version): drop the "recovery quarter" search entirely. Compare directly:
  PEAK-distress-quarter's last-transcript-publish-date  vs  price-relative-to-SPY trough date
(independent, from price data) -- this tests the classic contrarian "sentiment extremes mark/precede
price bottoms" idea head-on, without needing a visible "recovery" inflection in the text series.
Hand-computed on v2's own data this gives: GFC = -15 days (coincident, no real lead), covid = +106
days (~3.5mo genuine lead) -- both cleaner and more plausible than v2's numbers.

v3 also adds 4 more testable episodes (beyond the original XLF GFC + XLF covid pair) to check
whether the pattern is stable or episode-specific, per user request ("攞多幾個案例" 2026-07-11):
  - XLK 2022-23 (tech, 2022 rate-hike selloff -> 2023 AI-led recovery) -- different crisis mechanism
    (valuation compression, not systemic financial/pandemic crisis)
  - XLC 2022-23 (communication services, same macro window, different sector -- cross-check)
  - XLY 2009-10 (consumer discretionary, GFC recovery, different sector than XLF -- cross-check
    whether GFC's "coincident" finding is financials-specific or general)
  - XLK 2008-09 (tech, GFC recovery, another GFC cross-check)

Scope limitation (verified, not assumed): transcript corpus starts 2005-10-11 -> 2000-01 dot-com
episode DROPPED (zero coverage). ALSO DROPPED: the XLK 2019-08-30 "covid" episode (v1 mislabeling --
that start date predates the covid crash entirely, can't test the hypothesis). ALSO CONSIDERED and
EXCLUDED: XLU 2015-16 defensive rotation -- doesn't fit this methodology (utilities didn't crash in
their OWN business/transcripts; money rotated in as a macro-fear safety trade, so there's no "distress
in the sector's own words" to test a peak against).

Signal: real Loughran-McDonald Master Dictionary (2,355 negative / 354 positive words, verified
authentic via pysentiment2's bundled LM.csv). Per-transcript negative-word-ratio aggregated to a
sector-quarter average.

    python backtest/experiments/exp_category2_sentiment_reversal.py
"""
import os
import re
import sqlite3
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from thesis.corpus import DB as CORPUS_DB  # noqa: E402
from backtest.experiments.exp_sector_constraint_language import classify_sectors  # noqa: E402
from backtest.data import load  # noqa: E402

LM_CSV_CANDIDATES = [
    r"C:\Users\Kaho\AppData\Local\Programs\Python\Python312\Lib\site-packages\pysentiment2\static\LM.csv",
]
OUT_MD = os.path.join(ROOT, "backtest", "results", "2026-07-11_category2_sentiment_reversal_v3.md")

EPISODES = [
    {"sector": "Financial Services", "etf": "XLF", "start": "2009-02-27", "label": "GFC recovery bounce"},
    {"sector": "Financial Services", "etf": "XLF", "start": "2020-10-01", "label": "covid recovery bounce"},
    {"sector": "Technology", "etf": "XLK", "start": "2022-12-30", "label": "2022 rate-hike selloff -> 2023 AI recovery"},
    {"sector": "Communication Services", "etf": "XLC", "start": "2022-11-01", "label": "2022 selloff -> 2023 recovery"},
    {"sector": "Consumer Cyclical", "etf": "XLY", "start": "2009-02-27", "label": "GFC recovery bounce"},
    {"sector": "Technology", "etf": "XLK", "start": "2008-12-31", "label": "GFC recovery bounce"},
]
LOOKBACK_QUARTERS = 6
LOOKFORWARD_QUARTERS = 3   # NEW: extend past the official start to catch a lagged turning point


def load_lm_words():
    path = next((p for p in LM_CSV_CANDIDATES if os.path.exists(p)), None)
    if path is None:
        raise FileNotFoundError("LM.csv not found -- pip install pysentiment2 first")
    df = pd.read_csv(path)
    neg = set(df.loc[df["Negative"] > 0, "Word"].str.upper())
    pos = set(df.loc[df["Positive"] > 0, "Word"].str.upper())
    print(f"[lm] loaded real Loughran-McDonald dict: {len(neg)} negative, {len(pos)} positive words")
    return neg, pos


def _quarter_of(date_str):
    y, m = int(date_str[:4]), int(date_str[5:7])
    return f"{y}Q{(m - 1) // 3 + 1}"


def _quarter_window(start_date, n_before, n_after):
    """Quarters from n_before-before to n_after-after the quarter containing start_date.
    Returns (quarters_list, start_quarter_label)."""
    y, m = int(start_date[:4]), int(start_date[5:7])
    q0 = (m - 1) // 3 + 1
    start_q = f"{y}Q{q0}"
    out = []
    yy, qq = y, q0
    for _ in range(n_before):
        qq -= 1
        if qq == 0:
            qq, yy = 4, yy - 1
        out.append((yy, qq))
    out = list(reversed(out))
    out.append((y, q0))
    yy, qq = y, q0
    for _ in range(n_after):
        qq += 1
        if qq == 5:
            qq, yy = 1, yy + 1
        out.append((yy, qq))
    return [f"{yy}Q{qq}" for yy, qq in out], start_q


def score_sector_transcripts(sector_tickers, neg_words, pos_words):
    con = sqlite3.connect(CORPUS_DB)
    placeholders = ",".join("?" * len(sector_tickers))
    rows = con.execute(
        f"SELECT d.primary_ticker, d.published, docs_fts_en.body FROM docs_fts_en "
        f"JOIN docs d ON d.slug = docs_fts_en.slug "
        f"WHERE d.thesistype='transcript' AND d.primary_ticker IN ({placeholders})",
        sector_tickers).fetchall()
    con.close()
    out = []
    for ticker, published, body in rows:
        tokens = re.findall(r"[A-Za-z']+", body.upper())
        n = len(tokens)
        if n < 200:
            continue
        neg_n = sum(1 for t in tokens if t in neg_words)
        pos_n = sum(1 for t in tokens if t in pos_words)
        out.append({"ticker": ticker, "quarter": _quarter_of(published), "published": published,
                    "neg_ratio": neg_n / n, "pos_ratio": pos_n / n, "net": (pos_n - neg_n) / n})
    return pd.DataFrame(out)


def price_relative_trough(etf, search_start, search_end):
    """Find the date the ETF's price-relative-to-SPY series bottoms within [search_start, search_end]
    -- the actual, independent price-data answer to 'when did the sector genuinely turn?'"""
    px = load(etf)["close"]
    spy = load("SPY")["close"]
    both = pd.concat([px.rename("etf"), spy.rename("spy")], axis=1).dropna()
    both = both.loc[search_start:search_end]
    if len(both) == 0:
        return None
    rel = both["etf"] / both["spy"]
    rel = rel / rel.iloc[0]  # rebase to 1.0 at window start
    trough_date = rel.idxmin()
    return trough_date, float(rel.min()), float(rel.iloc[-1])


def main():
    neg_words, pos_words = load_lm_words()
    lines = ["# Category 2 v3 -- peak-vs-trough comparison + more cases (2026-07-11)\n",
              "> v3 fix: dropped v2's unreliable 'recovery quarter' search; now compares the PEAK-distress-"
              "quarter's last-transcript-publish-date directly against the independent price-relative "
              "trough date. 4 new episodes added (XLK/XLC 2022-23, XLY/XLK GFC) beyond the original XLF "
              "GFC+covid pair, to test whether the pattern is stable across episodes/sectors. "
              "Real Loughran-McDonald dictionary "
              f"({len(neg_words)} negative / {len(pos_words)} positive words, verified authentic).\n"]

    con = sqlite3.connect(CORPUS_DB)
    all_tickers = [r[0] for r in con.execute(
        "SELECT DISTINCT primary_ticker FROM docs WHERE thesistype='transcript'").fetchall()]
    con.close()
    sector_map = classify_sectors(all_tickers)

    for ep in EPISODES:
        qs, start_q = _quarter_window(ep["start"], LOOKBACK_QUARTERS, LOOKFORWARD_QUARTERS)
        print(f"\n[episode] {ep['etf']} {ep['label']} start={ep['start']} (={start_q}) window={qs}", flush=True)
        sector_tickers = [t for t, s in sector_map.items() if s == ep["sector"]]

        df = score_sector_transcripts(sector_tickers, neg_words, pos_words)
        dfw = df[df["quarter"].isin(qs)]
        trend = dfw.groupby("quarter").agg(
            neg_ratio=("neg_ratio", "mean"), n_companies=("ticker", "nunique"),
            pub_min=("published", "min"), pub_max=("published", "max")).reindex(qs)

        lines.append(f"\n## {ep['etf']} -- {ep['label']} (official episode start {ep['start']} = {start_q})\n")
        lines.append("| quarter | is_start | n_companies | mean neg_ratio | transcripts published |")
        lines.append("|---|---|---|---|---|")
        for q, row in trend.iterrows():
            marker = " <-- START" if q == start_q else ""
            if pd.isna(row["n_companies"]):
                lines.append(f"| {q}{marker} | | 0 | n/a | n/a |")
            else:
                lines.append(f"| {q}{marker} | | {row['n_companies']:.0f} | {row['neg_ratio']*100:.3f}% | "
                             f"{row['pub_min']} .. {row['pub_max']} |")

        # v3: compare the PEAK-distress-quarter's last-transcript-publish-date directly against the
        # independently-computed price-relative-to-SPY trough date. Tests the contrarian "sentiment
        # extremes mark/precede price bottoms" idea without needing a visible "recovery" inflection
        # in the text series (v2's heuristic for that was unreliable -- see module docstring).
        valid = trend.dropna(subset=["neg_ratio"])
        if len(valid) >= 3:
            peak_q = valid["neg_ratio"].idxmax()
            peak_row = trend.loc[peak_q]
            lines.append(f"\n- **Peak distress quarter: {peak_q}** (neg_ratio {peak_row['neg_ratio']*100:.3f}%, "
                         f"transcripts published {peak_row['pub_min']}..{peak_row['pub_max']})")

            search_start = pd.Timestamp(ep["start"]) - pd.DateOffset(months=9)
            search_end = pd.Timestamp(ep["start"]) + pd.DateOffset(months=9)
            pt = price_relative_trough(ep["etf"], search_start, search_end)
            if pt:
                trough_date, trough_val, end_val = pt
                signal_available = pd.Timestamp(peak_row["pub_max"])
                lead_days = (trough_date - signal_available).days
                lines.append(f"- **Price-relative trough (independent, from price data)**: "
                             f"{trough_date.date()} ({ep['etf']}/SPY ratio bottomed at {trough_val:.3f}, "
                             f"rebased=1.0 at window start, ended window at {end_val:.3f})")
                lines.append(f"- **Real lead time**: peak-quarter signal fully available (last transcript "
                             f"published) {signal_available.date()} vs price trough {trough_date.date()} = "
                             f"**{lead_days:+d} days** "
                             f"({'signal LED price by ' + str(lead_days) + 'd -- genuinely actionable' if lead_days > 30 else 'signal roughly COINCIDENT with price trough -- little/no real lead time' if abs(lead_days) <= 30 else 'signal LAGGED price -- not actionable, price already moved first'})")
        else:
            lines.append("\n- Not enough valid quarters in this window to identify a peak.")

    report = "\n".join(lines)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"\n[main] wrote {OUT_MD}")


if __name__ == "__main__":
    main()
