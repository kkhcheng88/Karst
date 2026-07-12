"""Objective A, category 2, recovery-phrase variant (2026-07-11).

Follow-up to exp_category2_sentiment_reversal.py v3, which found that "peak generic-negative-word
quarter vs price-relative trough" is NOT a stable lead-time signal across 6 macro-crisis-recovery
episodes (2/6 led, 1/6 coincident, 3/6 lagged by 4-6 months) -- see
backtest/results/2026-07-11_category2_sentiment_reversal_v3.md for the full writeup.

User's follow-up question (2026-07-11): "so we can't find ANY way to spot an early signal of a
sector's coming reversal from transcripts?" -- the honest answer was NO, not proven; the v3 test only
falsified ONE specific operationalization (generic LM negative-word-ratio PEAK). A cheap, different
angle that hasn't been tested: instead of measuring "how negative", measure the FIRST APPEARANCE of
RECOVERY-SPECIFIC language (management explicitly signaling a turn -- "stabilizing", "green shoots",
"worst is behind us", "bottomed out", etc.) -- these words are near-zero during the depth of a crisis
and should, in principle, appear as management notices the turn BEFORE the market fully re-rates.

Method: for the same 6 episodes/windows as v3, count the fraction of a sector's transcripts per
quarter that mention at least one recovery-signaling phrase. Define a signal quarter MECHANICALLY
(not cherry-picked per episode): the first quarter (in chronological order) where the mention rate
exceeds baseline (mean of the first 3 lookback quarters, the calmest/most pre-crisis portion of the
window) + 1 stdev of those same 3 quarters. Compare that quarter's last-transcript-publish-date to
the independent price-relative-to-SPY trough date, same as v3, for comparability.

    python backtest/experiments/exp_category2_recovery_language.py
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
from backtest.experiments.exp_category2_sentiment_reversal import (  # noqa: E402
    _quarter_window, price_relative_trough, EPISODES, LOOKBACK_QUARTERS, LOOKFORWARD_QUARTERS)

OUT_MD = os.path.join(ROOT, "backtest", "results", "2026-07-11_category2_recovery_language.md")

RECOVERY_PHRASES = [
    "green shoot", "worst is behind", "worst behind us", "turning the corner", "turned the corner",
    "inflection point", "sequential improvement", "improving sequentially", "sequentially improving",
    "return to growth", "returning to growth", "nascent recovery", "signs of stabiliz",
    "beginning to stabiliz", "starting to stabiliz", "bottomed out", "off the bottom",
    "near the bottom", "hit bottom", "past the bottom", "trough",
]
_PATTERN = re.compile("|".join(re.escape(p) for p in RECOVERY_PHRASES))


def _quarter_of(date_str):
    y, m = int(date_str[:4]), int(date_str[5:7])
    return f"{y}Q{(m - 1) // 3 + 1}"


def score_sector_recovery_language(sector_tickers):
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
        low = body.lower()
        if len(low) < 500:
            continue
        hit = bool(_PATTERN.search(low))
        out.append({"ticker": ticker, "quarter": _quarter_of(published), "published": published, "hit": hit})
    return pd.DataFrame(out)


def main():
    lines = ["# Category 2 -- recovery-phrase variant (2026-07-11)\n",
              "> Follow-up to v3 (generic negative-word peak -- found unstable, see "
              "2026-07-11_category2_sentiment_reversal_v3.md). Tests whether FIRST APPEARANCE of "
              "recovery-signaling phrases (management explicitly says the turn is happening) gives a "
              "more reliable lead-time than generic negativity peaking. Same 6 episodes, same windows.\n",
              f"\n> Recovery phrases matched (substring, case-insensitive): {', '.join(RECOVERY_PHRASES)}\n"]

    con = sqlite3.connect(CORPUS_DB)
    all_tickers = [r[0] for r in con.execute(
        "SELECT DISTINCT primary_ticker FROM docs WHERE thesistype='transcript'").fetchall()]
    con.close()
    sector_map = classify_sectors(all_tickers)

    summary_rows = []
    for ep in EPISODES:
        qs, start_q = _quarter_window(ep["start"], LOOKBACK_QUARTERS, LOOKFORWARD_QUARTERS)
        print(f"\n[episode] {ep['etf']} {ep['label']} start={ep['start']} (={start_q})", flush=True)
        sector_tickers = [t for t, s in sector_map.items() if s == ep["sector"]]

        df = score_sector_recovery_language(sector_tickers)
        dfw = df[df["quarter"].isin(qs)]
        trend = dfw.groupby("quarter").agg(
            mention_rate=("hit", "mean"), n_companies=("ticker", "nunique"),
            pub_min=("published", "min"), pub_max=("published", "max")).reindex(qs)

        lines.append(f"\n## {ep['etf']} -- {ep['label']} (official episode start {ep['start']} = {start_q})\n")
        lines.append("| quarter | is_start | n_companies | recovery mention rate | transcripts published |")
        lines.append("|---|---|---|---|---|")
        for q, row in trend.iterrows():
            marker = " <-- START" if q == start_q else ""
            if pd.isna(row["n_companies"]):
                lines.append(f"| {q}{marker} | | 0 | n/a | n/a |")
            else:
                lines.append(f"| {q}{marker} | | {row['n_companies']:.0f} | {row['mention_rate']*100:.1f}% | "
                             f"{row['pub_min']} .. {row['pub_max']} |")

        valid = trend.dropna(subset=["mention_rate"])
        if len(valid) >= 4:
            baseline_qs = valid.index[:3]
            baseline_vals = valid.loc[baseline_qs, "mention_rate"]
            threshold = baseline_vals.mean() + baseline_vals.std(ddof=0)
            after_baseline = valid.iloc[3:]
            breakout = after_baseline[after_baseline["mention_rate"] > threshold]
            lines.append(f"\n- Baseline (first 3 quarters {list(baseline_qs)}): mean="
                         f"{baseline_vals.mean()*100:.1f}%, threshold (mean+1std)={threshold*100:.1f}%")
            if len(breakout):
                sig_q = breakout.index[0]
                sig_row = trend.loc[sig_q]
                lines.append(f"- **First breakout quarter: {sig_q}** (mention_rate "
                             f"{sig_row['mention_rate']*100:.1f}%, transcripts published "
                             f"{sig_row['pub_min']}..{sig_row['pub_max']})")

                search_start = pd.Timestamp(ep["start"]) - pd.DateOffset(months=9)
                search_end = pd.Timestamp(ep["start"]) + pd.DateOffset(months=9)
                pt = price_relative_trough(ep["etf"], search_start, search_end)
                if pt:
                    trough_date, trough_val, end_val = pt
                    signal_available = pd.Timestamp(sig_row["pub_max"])
                    lead_days = (trough_date - signal_available).days
                    verdict = ('signal LED price by ' + str(lead_days) + 'd -- genuinely actionable' if lead_days > 30
                               else 'signal roughly COINCIDENT with price trough' if abs(lead_days) <= 30
                               else 'signal LAGGED price -- not actionable')
                    lines.append(f"- **Price-relative trough (independent)**: {trough_date.date()} "
                                 f"({ep['etf']}/SPY ratio bottomed at {trough_val:.3f})")
                    lines.append(f"- **Real lead time**: {signal_available.date()} vs {trough_date.date()} = "
                                 f"**{lead_days:+d} days** ({verdict})")
                    summary_rows.append({"episode": f"{ep['etf']} {ep['label']}", "sig_q": sig_q,
                                          "lead_days": lead_days, "verdict": verdict})
            else:
                lines.append("- No breakout quarter found in this window (mention rate never exceeded "
                             "baseline+1std) -- no signal to compare.")
                summary_rows.append({"episode": f"{ep['etf']} {ep['label']}", "sig_q": None,
                                      "lead_days": None, "verdict": "NO SIGNAL (never broke out)"})
        else:
            lines.append("\n- Not enough valid quarters in this window.")

    lines.append("\n## Summary\n")
    lines.append("| episode | breakout quarter | lead days | verdict |")
    lines.append("|---|---|---|---|")
    for r in summary_rows:
        lines.append(f"| {r['episode']} | {r['sig_q'] or 'n/a'} | "
                     f"{r['lead_days'] if r['lead_days'] is not None else 'n/a'} | {r['verdict']} |")

    report = "\n".join(lines)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"\n[main] wrote {OUT_MD}")


if __name__ == "__main__":
    main()
