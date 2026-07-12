"""Step 1 of the sector-rotation reverse-engineering approach (2026-07-10, objective A
correction): find the biggest historical (sector, 12-month window) relative-outperformance
episodes vs SPY across the 11 SPDR sector ETFs -- the "oracle" targets. Deduplicated to
genuinely DISTINCT episodes per sector (not dozens of overlapping monthly-stepped windows
around the same real event).

Step 2 (separate, NOT built here -- design depends on what these episodes actually look like):
for each top episode, look BACKWARD at transcript language (word-frequency / vocabulary,
NOT limited to CONSTRAINT_PHRASES) in the 2-4 quarters before the episode's start, searching
for any common precursor pattern across episodes.

    python backtest/experiments/exp_oracle_top_gap_episodes.py
"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from backtest.data import load  # noqa: E402

SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "XLC", "XLRE"]
WINDOW_MONTHS = 12
DEDUP_MONTHS = 9   # two episodes for the same ETF must have starts >= this far apart
OUT_CSV = os.path.join(ROOT, "backtest", "experiments", "_top_gap_episodes.csv")
OUT_MD = os.path.join(ROOT, "backtest", "results", "2026-07-10_oracle_top_gap_episodes.md")


def all_windows(spy: pd.Series) -> pd.DataFrame:
    rows = []
    for etf in SECTORS:
        try:
            px = load(etf)["close"]
        except Exception as e:
            print(f"[skip] {etf}: {e}")
            continue
        starts = pd.date_range(px.index.min(), px.index.max(), freq="MS")
        for d in starts:
            t0 = px.index[px.index <= d]
            tN = px.index[px.index <= d + pd.DateOffset(months=WINDOW_MONTHS)]
            s0 = spy.index[spy.index <= d]
            sN = spy.index[spy.index <= d + pd.DateOffset(months=WINDOW_MONTHS)]
            if len(t0) == 0 or len(tN) == 0 or tN[-1] <= t0[-1]:
                continue
            if len(s0) == 0 or len(sN) == 0 or sN[-1] <= s0[-1]:
                continue
            r_etf = px.loc[tN[-1]] / px.loc[t0[-1]] - 1.0
            r_spy = spy.loc[sN[-1]] / spy.loc[s0[-1]] - 1.0
            rows.append({"etf": etf, "start": t0[-1], "end": tN[-1],
                         "sector_ret": r_etf, "spy_ret": r_spy, "rel_return": r_etf - r_spy})
        print(f"[scan] {etf}: {len([r for r in rows if r['etf']==etf])} windows", flush=True)
    return pd.DataFrame(rows)


def dedup_top_episodes(df: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    df = df.sort_values("rel_return", ascending=False).reset_index(drop=True)
    kept = []
    kept_by_etf = {}
    for _, row in df.iterrows():
        etf = row["etf"]
        prior_starts = kept_by_etf.get(etf, [])
        if any(abs((row["start"] - s).days) < DEDUP_MONTHS * 30 for s in prior_starts):
            continue
        kept.append(row)
        kept_by_etf.setdefault(etf, []).append(row["start"])
        if len(kept) >= top_n:
            break
    return pd.DataFrame(kept)


def main():
    spy = load("SPY")["close"]
    df = all_windows(spy)
    df.to_csv(OUT_CSV.replace(".csv", "_all_windows.csv"), index=False)
    top = dedup_top_episodes(df, top_n=30)
    top.to_csv(OUT_CSV, index=False)

    lines = ["# Oracle top-gap episodes -- 11 SPDR sectors vs SPY, 12-month windows (2026-07-10)\n",
              "> Step 1 of reverse-engineering (objective A). These are the biggest, DISTINCT "
              "sector-vs-SPY outperformance episodes in history. Step 2 (separate): look backward "
              "at transcript vocabulary before each start date.\n",
              "| rank | sector | window start | window end | sector ret | SPY ret | relative ret |",
              "|---|---|---|---|---|---|---|"]
    for i, r in top.reset_index(drop=True).iterrows():
        lines.append(f"| {i+1} | {r['etf']} | {r['start'].date()} | {r['end'].date()} | "
                     f"{r['sector_ret']*100:+.1f}% | {r['spy_ret']*100:+.1f}% | "
                     f"{r['rel_return']*100:+.1f}% |")
    report = "\n".join(lines)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"\n[main] wrote {OUT_MD} and {OUT_CSV}")


if __name__ == "__main__":
    main()
