"""thesis/narrative_flow_tracker.py -- PAPER (no real capital) NAV tracker for the "narrative-flow"
paper strategy: front-testing whether a narrative/flow-driven TARGET ALLOCATION (modelled on a
zsxq KOL's own practice) has alpha, with deliberately dumb execution isolated from that bet.

Two things are kept strictly separate, per the 2026-07-17 design:
  1. COMPOSITION is the bet -- thesis/paper/narrative_flow.yaml is a dated journal: every
     reallocation is one entry with an effective_date, target weights, and a one-line rationale
     pointing at its source (a zsxq capture, a KOL post, etc). This file is the thing being
     validated; it is never touched by this tracker.
  2. EXECUTION is deliberately dumb -- no dip-buy timing. Entry price for a journal version =
     the close on the first trading day AFTER its effective_date (backtest/results/
     2026-07-16_leader_dip_reversion.md already showed leader-dip execution timing carries no
     excess return of its own -- this tracker intentionally skips that lever so any measured
     alpha is attributable to composition choices, not execution cleverness).

Unlike aa_strict_paper_tracker.py (which carries state forward day by day because its regime
math needs yesterday's rolling betas), this tracker is fully STATELESS and recomputes the whole
NAV history from the journal + price data every run -- the journal only has one or a handful of
versions, so full recompute is cheap and avoids state/journal drift bugs entirely. The output log
is REWRITTEN (not appended) each run.

Per-version day t position: value_i(t) = weight_i% * price_i(t) / price_i(entry_date). Weights
don't drift-rebalance day to day (matches paper_league.py's sizing-kind convention) -- they ride
naturally until the next journal version fires. CASH weight earns a flat 0% (same convention
paper_league.py/paper_ledger.py already use for undeployed sleeve %).

NAV(t) = version_start_nav * (sum_i w_i/100 * price_i(t)/price_i(entry) + cash_frac_of_100)

Benchmark: QQQ buy-and-hold, NAV=100 pinned to the SAME start date as journal version 1's entry
date (so the two lines are comparable from day 0, not re-based per version).

State: none persisted -- recomputed from thesis/paper/narrative_flow.yaml + price history only.
Output: thesis/.raw/narrative_flow_paper_log.jsonl (gitignored, full rewrite each run) --
  {"date", "version", "narrative_flow_nav", "qqq_bh_nav"} per trading day since version 1's entry.
  Mirrored (never recomputed a second time) by thesis/paper_league.py's "narrative-flow" and
  "qqq-bh-nf" STRATEGIES entries, same pattern as aa-strict/spy-bh.

Run: python thesis/narrative_flow_tracker.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.data import load  # noqa: E402 -- yfinance-first price loader, same one beta_check.py uses

ROOT = os.path.dirname(os.path.abspath(__file__))          # thesis/
JOURNAL_PATH = os.path.join(ROOT, "paper", "narrative_flow.yaml")
LOG_PATH = os.path.join(ROOT, ".raw", "narrative_flow_paper_log.jsonl")

CASH_KEY = "CASH"


def _load_journal():
    with open(JOURNAL_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    versions = sorted(data.get("journal") or [], key=lambda v: v["effective_date"])
    if not versions:
        raise ValueError(f"{JOURNAL_PATH}: no journal entries -- nothing to track")
    for v in versions:
        total = sum(float(x) for x in v["weights"].values())
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"{JOURNAL_PATH}: version {v['version']} weights sum to {total}, "
                              "not 100 -- fix the journal before tracking")
    return data.get("benchmark", "QQQ"), data.get("initial_nav", 100.0), versions


def _load_prices(tickers):
    closes = {}
    failed = []
    for tk in tickers:
        try:
            closes[tk] = load(tk, adjusted=True)["close"]
        except Exception as exc:
            failed.append((tk, str(exc)))
    return closes, failed


def run():
    benchmark, initial_nav, versions = _load_journal()
    all_tickers = sorted({tk for v in versions for tk in v["weights"] if tk != CASH_KEY} | {benchmark})
    closes, failed = _load_prices(all_tickers)
    if failed:
        for tk, err in failed:
            print(f"[narrative_flow] WARNING: failed to load {tk}: {err}")

    bench_close = closes.get(benchmark)
    if bench_close is None or len(bench_close) == 0:
        print(f"[narrative_flow] benchmark {benchmark!r} has no price data -- aborting, no log written")
        return

    rows = []
    version_start_nav = float(initial_nav)
    bench_start_price = None
    pending_notes = []

    for vi, v in enumerate(versions):
        eff_date = str(v["effective_date"])
        weights = {tk: float(w) for tk, w in v["weights"].items()}
        cash_frac = weights.get(CASH_KEY, 0.0) / 100.0
        asset_weights = {tk: w for tk, w in weights.items() if tk != CASH_KEY}

        # entry_date = first trading day STRICTLY AFTER eff_date, per any asset's own calendar
        # (falls back to the benchmark's calendar if a version happens to hold cash-only, though
        # that shouldn't occur in practice).
        calendar = None
        for tk in asset_weights:
            s = closes.get(tk)
            if s is not None and len(s):
                calendar = s.index if calendar is None else calendar.union(s.index)
        if calendar is None:
            calendar = bench_close.index
        future = calendar[calendar.date > datetime.strptime(eff_date, "%Y-%m-%d").date()]
        if len(future) == 0:
            pending_notes.append(f"version {v['version']} (effective {eff_date}): no trading day "
                                  "after the effective date has a close yet -- not executed, left "
                                  "out of the log until tomorrow's data lands")
            continue
        entry_date = future[0]

        entry_price = {}
        ok = True
        for tk in asset_weights:
            s = closes.get(tk)
            if s is None or entry_date not in s.index:
                pending_notes.append(f"version {v['version']}: {tk} has no close on entry date "
                                      f"{entry_date.date()} -- version left unmarked")
                ok = False
                continue
            entry_price[tk] = float(s.loc[entry_date])
        if not ok:
            continue

        if bench_start_price is None:
            if entry_date not in bench_close.index:
                pending_notes.append(f"version {v['version']}: benchmark {benchmark} has no close "
                                      f"on {entry_date.date()} -- benchmark line starts later")
            else:
                bench_start_price = float(bench_close.loc[entry_date])
                bench_start_date = entry_date

        # this version's active window: [entry_date, next version's entry_date) or to the last
        # available trading day if this is the latest version.
        next_eff = versions[vi + 1]["effective_date"] if vi + 1 < len(versions) else None
        window = calendar[calendar >= entry_date]
        if next_eff is not None:
            next_cutoff = datetime.strptime(str(next_eff), "%Y-%m-%d").date()
            window = window[window.date < next_cutoff]

        version_end_nav = version_start_nav
        for day in window:
            acc = cash_frac
            missing = False
            for tk, w in asset_weights.items():
                s = closes.get(tk)
                if s is None or day not in s.index or entry_price.get(tk) is None:
                    missing = True
                    break
                acc += (w / 100.0) * (float(s.loc[day]) / entry_price[tk])
            if missing:
                continue
            nav = version_start_nav * acc
            version_end_nav = nav
            bench_nav = None
            if bench_start_price is not None and day in bench_close.index and day >= bench_start_date:
                bench_nav = float(initial_nav) * (float(bench_close.loc[day]) / bench_start_price)
            rows.append({
                "date": day.date().isoformat(), "version": v["version"],
                "narrative_flow_nav": round(nav, 4),
                "qqq_bh_nav": round(bench_nav, 4) if bench_nav is not None else None,
            })
        version_start_nav = version_end_nav

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"==== {datetime.now():%Y-%m-%d %H:%M} ====")
    print("=== narrative-flow PAPER tracker (no real capital -- composition-vs-benchmark) ===")
    if rows:
        last = rows[-1]
        bench_s = f"{last['qqq_bh_nav']:.2f}" if last["qqq_bh_nav"] is not None else "n/a"
        print(f"as of {last['date']} (journal version {last['version']}): "
              f"narrative-flow NAV={last['narrative_flow_nav']:.2f}  vs {benchmark} B&H NAV={bench_s}")
    else:
        print("no rows written yet -- see notes below")
    for n in pending_notes:
        print(f"  note: {n}")
    print(f"wrote {LOG_PATH} ({len(rows)} row(s), full rewrite)")


if __name__ == "__main__":
    run()
