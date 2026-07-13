"""MP Materials (MP) own-history capex/D&A time series, computed to answer the one open item
flagged in backtest/results/2026-07-13_mp_capex_da_review.md monitoring condition #5:
"probe 從來冇計過 MP 自己嘅歷史 capex/D&A 分佈" -- the original probe
(exp_capex_da_probe.py) only ever computed MP's capex/D&A as a SINGLE cross-sectional
snapshot point (2.192x TTM-level, 2.540x TTM-YoY) inside its 15-theme table; it never built
MP's own time series, so "is 2.192x extreme for MP itself" had no answer. This script builds
that missing time series and puts RKLB (probe-judged build-out artifact) and MU (probe-judged
genuine cyclical-peak type) alongside it as controls, using the EXACT SAME data-pull and
parsing code as the original probe -- no second methodology is invented.

Reuse discipline (mirror/increment/horizon -- memory validation-mirror-and-increment):
  This is a descriptive/level-based history probe, same genre as exp_capex_da_probe.py's
  MU deep-dive section, extended to MP+RKLB+MU. It is NOT a new metric: every number below
  is produced by directly importing and calling exp_capex_da_probe's own functions:
    - probe._load_data(tickers)   -> same disk-cached pull (defeatbeta first, yfinance
                                      fallback-if-defeatbeta-totally-empty), same cache file
                                      backtest/.insider_data/capex_da_probe.pkl
    - probe._pull_one / probe._cf_rows (called inside _load_data) -> same field names
                                      (CAPEX_NAMES/DA_NAMES), same _num() '*'/NaN handling
    - probe._ratio_series(capex_d, da_d) -> reused VERBATIM for the annual FY series (this is
                                      the exact function the original MU deep-dive used for its
                                      annual distribution/percentile section)
  The ONE new piece of logic is _rolling_ttm(): defeatbeta's quarterly_cash_flow() gives
  per-quarter capex/D&A PLUS a single extra "TTM" column that is only the latest snapshot,
  not a series. To get a quarterly-grain TTM ratio HISTORY (needed to answer "was 2.192x
  reached before"), this script sums trailing-4-quarter windows over the SAME per-quarter
  dicts _cf_rows() already extracts -- pure aggregation of existing fields, not a new source
  or a new field name. It is verified below to exactly reproduce defeatbeta's own "TTM"
  snapshot column for the latest quarter of all three tickers (capex AND D&A both match to
  the dollar), i.e. this is provably the same convention defeatbeta itself uses, just run
  backwards through history instead of read once.

Gaps are never interpolated: defeatbeta's quarterly_cash_flow has a vendor-side 3-quarter gap
(2022-09-30 .. 2023-03-31 for MP/RKLB; the MU fiscal-calendar-equivalent window) where capex/D&A
are NaN for ALL THREE tickers alike (a vendor coverage wall, not ticker-specific). Any rolling
4-quarter window that touches a NaN quarter is skipped (marked None), never filled.

Run: python backtest/experiments/exp_mp_capex_history.py
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_capex_da_probe as probe  # noqa: E402  (reuse its pull/parse code verbatim)

TICKERS = ["MP", "RKLB", "MU"]
LABEL = {"MP": "MP Materials (probe under review)", "RKLB": "Rocket Lab (probe-judged build-out artifact)",
         "MU": "Micron (probe-judged genuine cyclical-peak type)"}


def _rolling_ttm(q_capex, q_da):
    """Trailing-4-quarter TTM capex/D&A ratio, walked across the FULL per-quarter history.
    Returns [(period_end, ttm_capex, ttm_da, ratio_or_None)], one row per quarter from the 4th
    real quarter onward (chronological order). ratio is None when any of the 4 trailing
    quarters is NaN in the source data (vendor gap) -- explicitly marked, never interpolated."""
    if not q_capex or not q_da:
        return []
    dates = sorted(k for k in q_capex if k != "TTM")
    rows = []
    for i in range(3, len(dates)):
        window = dates[i - 3:i + 1]
        cs = [q_capex.get(d) for d in window]
        ds = [q_da.get(d) for d in window]
        if any(v is None or v != v for v in cs) or any(v is None or v != v for v in ds):
            rows.append((dates[i], None, None, None))
            continue
        tc, td = sum(cs), sum(ds)
        ratio = tc / td if td and td > 0 else None
        rows.append((dates[i], tc, td, ratio))
    return rows


def _percentile_of_last(vals):
    """Same formula as exp_capex_da_probe.mu_deep_dive's annual-distribution percentile:
    share of historical values <= the latest value."""
    if not vals:
        return None
    return 100 * sum(v <= vals[-1] for v in vals) / len(vals)


def _crosscheck_ttm_snapshot(tk, q_capex, q_da, rolling):
    """Confirm _rolling_ttm's last real row reproduces defeatbeta's own single-point 'TTM'
    column exactly (both capex and D&A dollars) -- proof this is the SAME convention, not a
    new one."""
    snap_c, snap_d = q_capex.get("TTM"), q_da.get("TTM")
    real = [r for r in rolling if r[3] is not None]
    if not real or snap_c != snap_c or snap_d != snap_d:
        print(f"  [{tk}] cross-check: SKIPPED (no snapshot or no computable rolling row)")
        return
    last = real[-1]
    ok_c = abs(last[1] - snap_c) < 1.0
    ok_d = abs(last[2] - snap_d) < 1.0
    print(f"  [{tk}] cross-check vs defeatbeta 'TTM' snapshot: "
          f"rolling={last[1]:,.0f}/{last[2]:,.0f} snapshot={snap_c:,.0f}/{snap_d:,.0f} "
          f"-> {'MATCH' if ok_c and ok_d else 'MISMATCH'}")


def run():
    print(f"pulling capex/D&A for {TICKERS} via exp_capex_da_probe._load_data "
          f"(shared disk cache backtest/.insider_data/capex_da_probe.pkl) ...")
    cache = probe._load_data(TICKERS)

    quarterly = {}
    annual = {}
    for tk in TICKERS:
        d = cache[tk]
        print(f"\n{'=' * 90}\n{tk} -- {LABEL[tk]} (source: {d.get('source')})\n{'=' * 90}")

        rolling = _rolling_ttm(d["q_capex"], d["q_da"])
        quarterly[tk] = rolling
        print(f"\n--- Quarterly TTM capex/D&A (rolling trailing-4Q, gaps=None not interpolated) ---")
        print(f"  {'period':12} {'TTM capex($M)':>14} {'TTM D&A($M)':>12} {'ratio':>8}")
        for dt, tc, td, ratio in rolling:
            if ratio is None:
                print(f"  {dt:12} {'GAP':>14} {'GAP':>12} {'GAP':>8}")
            else:
                print(f"  {dt:12} {tc/1e6:>14,.1f} {td/1e6:>12,.1f} {ratio:>8.3f}")
        _crosscheck_ttm_snapshot(tk, d["q_capex"], d["q_da"], rolling)

        real_q = [r[3] for r in rolling if r[3] is not None]
        if real_q:
            pct = _percentile_of_last(real_q)
            print(f"  quarterly-TTM distribution (n={len(real_q)}): min={min(real_q):.3f}x "
                  f"median={np.median(real_q):.3f}x max={max(real_q):.3f}x latest={real_q[-1]:.3f}x "
                  f"latest_percentile={pct:.1f}%")

        arows = probe._ratio_series(d["a_capex"], d["a_da"])  # reused verbatim
        annual[tk] = arows
        print(f"\n--- Annual FY capex/D&A (probe._ratio_series, since first real FY) ---")
        print(f"  {'FY end':12} {'capex($M)':>12} {'D&A($M)':>10} {'ratio':>8}")
        for dt, c, dv, ratio in arows:
            print(f"  {dt:12} {c/1e6:>12,.1f} {dv/1e6:>10,.1f} {ratio:>8.3f}")
        avals = [r[3] for r in arows]
        if avals:
            pct_a = _percentile_of_last(avals)
            print(f"  annual distribution (n={len(avals)}): min={min(avals):.3f}x "
                  f"median={np.median(avals):.3f}x max={max(avals):.3f}x latest_FY={avals[-1]:.3f}x "
                  f"latest_FY_percentile={pct_a:.1f}%")

    # MP's current TTM (2.192x) ranked within its own annual FY series as a 7th inserted point
    # (freshest read alongside the 6 completed FYs) -- supplementary framing, see results doc.
    print(f"\n{'=' * 90}\nMP current TTM (2.192x-equivalent, latest quarterly row) vs MP's own annual FY set\n{'=' * 90}")
    mp_annual_vals = [r[3] for r in annual["MP"]]
    mp_latest_q = [r[3] for r in quarterly["MP"] if r[3] is not None][-1]
    combined = sorted(mp_annual_vals + [mp_latest_q])
    rank = 100 * sum(v <= mp_latest_q for v in combined) / len(combined)
    print(f"  MP annual FY values: {[f'{v:.3f}' for v in mp_annual_vals]}")
    print(f"  MP latest quarterly-TTM: {mp_latest_q:.3f}x")
    print(f"  combined (annual + latest quarterly-TTM as 7th point), rank of latest: {rank:.1f}%")

    return quarterly, annual


if __name__ == "__main__":
    run()
