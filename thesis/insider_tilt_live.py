"""thesis/insider_tilt_live.py -- surfaces CURRENTLY ACTIVE insider cluster-buy tilt signals.

ROADMAP A3 / Phase-3 P0-c (docs/ROADMAP_AGENTIC.md line 30): direction locked 2026-07-05
(exp_insider_literature.py / exp_insider_rigor.py) -- small-cap (<$2B market cap) 12-MONTH
portfolio tilt vs IWM, a BOUNDED OVERLAY (not a standalone strategy), NOT the earlier-rejected
21-day tactical version (large-cap-only, regime-fragile, t=1.1 full-sample). Per the roadmap's
own fallback clause ("不過就 display-only"): wire as READ-ONLY DISPLAY regardless of whether the
A/B incremental backtest has formally cleared the DSR bar for SIZING -- this script does NOT
touch sizing.py or any capital-allocation decision, it only surfaces the signal for the user to
read, same NHITL principle as thesis/theme_signal.py.

Signal (reuses backtest/experiments/exp_insider_validate.py's build_events(), unchanged): a
TICKER-DATE cluster event = >=2 distinct insiders filing an open-market Form-4 PURCHASE (code P,
10b5-1 excluded) within a ~21-trading-day window, combined value >= $500k, no re-fire within 63
days of a prior event for the same ticker. This script does NOT re-derive the signal -- it pulls
recent quarters, re-runs the SAME validated build_events(), then filters to:
  1. event date within the trailing HOLD_MONTHS (position still "held" under the 12-month tilt)
  2. market cap at event date < SMALL_CAP_MAX (the ROADMAP A3 cutoff; uses
     exp_insider_mktcap.py's defeatbeta market_capitalization() series, same source already
     validated there)

Output: a dated results file (backtest/results/<date>_insider_tilt_live.md) listing every
currently-active small-cap tilt position, sorted by event recency. This is a SNAPSHOT (overwritten
each run), not a log -- track_record-style historical accounting is out of scope for a v1 display
tool.

Run: python thesis/insider_tilt_live.py
"""
from __future__ import annotations

import datetime
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "backtest", "experiments"))
import exp_insider_validate as IV   # noqa: E402
import exp_insider_mktcap as MC     # noqa: E402

SMALL_CAP_MAX = 2e9
HOLD_MONTHS = 12
RESULTS_DIR = os.path.join(ROOT, "..", "backtest", "results")


def _quarter_str(d):
    return f"{d.year}q{(d.month - 1) // 3 + 1}"


def _recent_quarters(n_back=7):
    """Trailing ~21 months of quarters (buffer: HOLD_MONTHS=12 + the ~21-trading-day cluster
    window + slack for SEC's own publication lag) ending at the current quarter."""
    today = datetime.date.today()
    out, y, q = [], today.year, (today.month - 1) // 3 + 1
    for _ in range(n_back):
        out.append(f"{y}q{q}")
        q -= 1
        if q < 1:
            q = 4
            y -= 1
    return list(reversed(out))


def run():
    quarters = _recent_quarters()
    print(f"[insider_tilt_live] attempting quarters: {quarters}")
    fetched = []
    # probe each quarter for availability FIRST (a quarter not yet published by SEC 404s), then
    # call build_events() ONCE over the full valid range -- calling it per-single-quarter would
    # break the cluster-window/_REENTRY dedup logic, which needs the full date-sorted series per
    # ticker across quarter boundaries to work correctly.
    for q in quarters:
        try:
            IV._load_quarter(q)
            fetched.append(q)
        except Exception as e:
            print(f"[insider_tilt_live] {q} unavailable ({type(e).__name__}: {e}) -- skipping "
                  f"(SEC may not have published it yet)")
    if fetched:
        print(f"[insider_tilt_live] fetched quarters: {fetched}")
    if not fetched:
        print("[insider_tilt_live] no quarters available -- nothing to scan")
        return

    df = IV.build_events(fetched)
    if df.empty:
        print("[insider_tilt_live] no cluster-buy events found in the fetched window")
        return
    today = pd.Timestamp(datetime.date.today())
    cutoff = today - pd.DateOffset(months=HOLD_MONTHS)
    active = df[df["date"] >= cutoff].copy()
    print(f"[insider_tilt_live] {len(df)} total events in window, {len(active)} within trailing "
          f"{HOLD_MONTHS}mo")
    if active.empty:
        print("[insider_tilt_live] no active-window events -- nothing to filter by market cap")
        return

    MC._batch_mcap(active["ticker"].unique().tolist())
    rows = []
    for _, r in active.iterrows():
        s = MC._MCAP.get(r["ticker"])
        if s is None or s.empty:
            continue
        idx = s.index[s.index <= r["date"]]
        if len(idx) == 0:
            continue
        mcap = s.loc[idx[-1]]
        if mcap < SMALL_CAP_MAX:
            rows.append({"ticker": r["ticker"], "date": r["date"], "owners": r["owners"],
                         "value": r["value"], "mcap": mcap})
    tilt = pd.DataFrame(rows).sort_values("date", ascending=False) if rows else pd.DataFrame()
    print(f"[insider_tilt_live] {len(tilt)} active small-cap (<${SMALL_CAP_MAX/1e9:.0f}B) tilt "
          f"position(s)")

    today_str = datetime.date.today().isoformat()
    out_path = os.path.join(RESULTS_DIR, f"{today_str}_insider_tilt_live.md")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Insider small-cap 12-month tilt -- live snapshot ({today_str})\n\n")
        f.write("ROADMAP A3 / P0-c (docs/ROADMAP_AGENTIC.md). Display-only, NOT wired to "
                "sizing.py -- direction-locked signal for manual read, same NHITL principle as "
                "thesis/theme_signal.py. Bounded overlay vs IWM, <$2B market cap at event date, "
                f"event within trailing {HOLD_MONTHS} months (\"still held\" under the tilt).\n\n")
        f.write(f"SEC quarters fetched this run: {fetched}\n\n")
        if tilt.empty:
            f.write("**No active small-cap insider cluster-buy tilt positions this run.**\n")
        else:
            f.write("| ticker | event date | owners | $ value | mcap at event |\n")
            f.write("|---|---|---|---|---|\n")
            for _, r in tilt.iterrows():
                f.write(f"| {r['ticker']} | {r['date'].date()} | {r['owners']} | "
                        f"${r['value']:,.0f} | ${r['mcap']/1e6:,.0f}M |\n")
    print(f"[insider_tilt_live] -> {out_path}")


if __name__ == "__main__":
    run()
