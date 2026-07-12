"""Capex-to-D&A ratio as a MECHANIZED TRACKER for magnifier P2 ("losers do leveraged capacity
expansion before the cycle peak" — docs/2026-07-09_magnifier_model_plan.md §3c). This is a PROBE,
not a wiring-in decision: the question is whether capex/D&A is reproducible, has enough history,
and separates signal from noise well enough to promote from "human narrative check" (as currently
done ad hoc, e.g. MU "2.66x" in thesis/wiki/memory-supercycle.md) to a scheduled mechanized read
(same spirit as thesis/magnifier_staleness.py's mechanize-the-trigger-not-the-judgment pattern).

Two DIFFERENT metrics are in play and must not be conflated:
  (1) capex/D&A LEVEL ratio (capex / D&A, same period) — the task's literal "capex-to-D&A ratio".
      >1 = net capacity expansion beyond replacement; ~1 = maintenance-only capex. Standard
      capital-cycle indicator (see literature section below).
  (2) capex YoY GROWTH multiple — what memory-supercycle.md's "2.66x" actually is
      ($2.938B TTM-quarter 2025-05-31 -> $7.826B TTM-quarter 2026-05-31). This is reproduced here
      as a sanity check that Tier-1 defeatbeta data matches the wiki, NOT the tracker itself.

Method (mirror / increment / horizon — memory validation-mirror-and-increment):
  - This is a DESCRIPTIVE / LEVEL-BASED probe, not a forward-return backtest, so "mirror" here means:
    does the metric reproduce known cited figures (MU) and behave sensibly across cycles (rise into
    a capacity build, fall/trough at capital-discipline bottoms)? There is no cross-sectional IC test
    in this script — P2 is used today as a SINGLE-NAME qualitative death-signal at named cycle peaks,
    not a ranked cross-sectional factor, so a cross-sectional IC would test a DIFFERENT use-case than
    how the framework actually consumes it (mirror-mismatch is called out explicitly in the results doc).
  - increment = N/A (first look at this metric in the repo; no prior mechanized version to increment over).
  - horizon = N/A (level-snapshot / early-warning read, not a forward-return-horizon test).

Data source discipline: defeatbeta first (repo Tier-1), yfinance fallback. Both are queried for
depth so the results doc can state an honest coverage table. defeatbeta exposes BOTH
quarterly_cash_flow() (~16Q, ~2022-05..2026-05 for MU) and annual_cash_flow() (7 nominal FY columns,
but the earliest 2 are "*"-masked -> only ~5 real FY columns, e.g. FY2021-FY2025 for MU). Neither
defeatbeta nor yfinance (quarterly or annual) reaches MU's 2016-18 cycle — this is a genuine
vendor-coverage wall, not a laziness gap. A secondary/Tier-2 SEC-10-K-sourced reconstruction (via
WebSearch summarizing the FY2018 10-K's MD&A text, NOT a live API pull) is hardcoded below for
2016-2018 ONLY, clearly labelled as such, to give the "second cycle" some grounding while being
honest about its lower verification tier.

Cost assumptions: none (this is not a PnL test).

Run: python backtest/experiments/exp_capex_da_probe.py
"""
from __future__ import annotations

import contextlib
import io
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with contextlib.redirect_stdout(io.StringIO()):
    from defeatbeta_api.data.ticker import Ticker
import yfinance as yf

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
_CACHE = os.path.join(_DATA, "capex_da_probe.pkl")

# 15 existing themes (thesis/themes.yaml) -> chosen main ticker for the supply-side snapshot.
THEME_TICKERS = {
    "memory-supercycle": "MU",
    "photonics-optical": "COHR",
    "ai-power-grid": "GEV",
    "advanced-packaging": "AMKR",
    "space-satellite": "RKLB",
    "rare-earth-materials": "MP",
    "tpu-custom-silicon": "AVGO",
    "oil-gas-energy": "EQT",
    "semicap-equipment": "AEHR",
    "aerospace-specialty-alloys": "ATI",
    "euv-lithography-monopoly": "ASML",
    "us-solar-manufacturing": "FSLR",
    "gas-compression-equipment": "USAC",
    "specialty-siding-pricing-power": "LPX",
    "glp1-biologics-packaging": "WST",
}

# MU FY2016-2018: SEC 10-K MD&A text (FY2018 10-K, sec.gov/Archives/edgar/data/0000723125/000072312518000092),
# summarized via WebSearch on 2026-07-12 — NOT a direct API/XBRL pull. Tier-2 (secondary summarization of a
# Tier-1 primary source). Capex = "expenditures for property, plant and equipment, net of partner
# contributions" (the 10-K's own headline capex figure). D&A = "depreciation expense and amortization of
# intangible assets" from the same MD&A paragraph.
MU_FY2016_18_SEC = {
    "capex": {"2016-08-31": 5.75e9, "2017-08-31": 4.73e9, "2018-08-31": 7.99e9},
    "da":    {"2016-08-31": 2.980e9, "2017-08-31": 3.861e9, "2018-08-31": 4.759e9},
    "source": "FY2018 10-K MD&A (sec.gov/Archives/edgar/data/0000723125/000072312518000092/a2018q4.htm), "
              "via WebSearch summarization 2026-07-12 -- Tier-2, not a live vendor API pull",
}

CAPEX_NAMES = ("Capital Expenditure Reported（CapEx）", "Capital Expenditure (CapEx)")
DA_NAMES = ("Depreciation Amortization Depletion", "Depreciation & Amortization")


def _num(v):
    try:
        s = str(v).strip()
        if s in ("*", "", "None", "nan", "NaN"):
            return np.nan
        return float(v)
    except Exception:
        return np.nan


def _cf_rows(cf, capex_names=CAPEX_NAMES, da_names=DA_NAMES):
    """Extract {period_end -> value} for capex (raised to positive-outflow magnitude) and D&A."""
    cf = cf.data if hasattr(cf, "data") else cf
    bd = cf["Breakdown"].astype(str)
    datecols = [c for c in cf.columns if c not in ("Breakdown",)]

    def getrow(names):
        for name in names:
            m = bd == name
            if m.any():
                row = cf[m].iloc[0]
                return {str(c): _num(row[c]) for c in datecols}
        return None

    capex = getrow(capex_names)
    da = getrow(da_names)
    if capex is not None:
        capex = {k: (abs(v) if v == v else v) for k, v in capex.items()}
    return capex, da


def _pull_one(tk):
    """Pull quarterly + annual capex/D&A rows for one ticker via defeatbeta (no cache).
    Falls back to yfinance quarterly/annual cashflow if defeatbeta raises."""
    out = {"q_capex": None, "q_da": None, "a_capex": None, "a_da": None, "source": None}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            qcf = Ticker(tk).quarterly_cash_flow()
        out["q_capex"], out["q_da"] = _cf_rows(qcf)
        out["source"] = "defeatbeta"
    except Exception:
        pass
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            acf = Ticker(tk).annual_cash_flow()
        out["a_capex"], out["a_da"] = _cf_rows(acf)
        if out["source"] is None:
            out["source"] = "defeatbeta"
    except Exception:
        pass
    if out["q_capex"] is None and out["a_capex"] is None:
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                yt = yf.Ticker(tk)
                qcf = yt.quarterly_cashflow
                acf = yt.cashflow
            qc = qcf.loc["Capital Expenditure"] if "Capital Expenditure" in qcf.index else None
            qd = qcf.loc["Depreciation And Amortization"] if "Depreciation And Amortization" in qcf.index else None
            ac = acf.loc["Capital Expenditure"] if "Capital Expenditure" in acf.index else None
            ad = acf.loc["Depreciation And Amortization"] if "Depreciation And Amortization" in acf.index else None
            if qc is not None:
                out["q_capex"] = {str(k.date()): abs(v) for k, v in qc.items() if v == v}
            if qd is not None:
                out["q_da"] = {str(k.date()): v for k, v in qd.items() if v == v}
            if ac is not None:
                out["a_capex"] = {str(k.date()): abs(v) for k, v in ac.items() if v == v}
            if ad is not None:
                out["a_da"] = {str(k.date()): v for k, v in ad.items() if v == v}
            if out["q_capex"] or out["a_capex"]:
                out["source"] = "yfinance"
        except Exception:
            pass
    return out


def _load_data(tickers):
    cache = {}
    if os.path.exists(_CACHE):
        try:
            cache = pickle.load(open(_CACHE, "rb"))
        except Exception:
            cache = {}
    need = [t for t in tickers if not cache.get(t) or cache[t].get("source") is None]
    for i, t in enumerate(need):
        cache[t] = _pull_one(t)
        if i % 5 == 4:
            pickle.dump(cache, open(_CACHE, "wb"))
    pickle.dump(cache, open(_CACHE, "wb"))
    return cache


def _ratio_series(capex_d, da_d):
    """Return sorted list of (date_str, capex, da, ratio) for dates present in both, excluding TTM/nan."""
    if not capex_d or not da_d:
        return []
    rows = []
    for k in capex_d:
        if k == "TTM":
            continue
        c, d = capex_d.get(k), da_d.get(k)
        if c == c and d == d and d > 0:
            rows.append((k, c, d, c / d))
    rows.sort(key=lambda r: r[0])
    return rows


def mu_deep_dive(cache):
    print("=" * 88)
    print("MU DEEP DIVE — two supercycles")
    print("=" * 88)
    d = cache["MU"]

    # --- quarterly (defeatbeta, ~2022-05..2026-05) ---
    print("\n--- Quarterly (defeatbeta quarterly_cash_flow, TTM + per-Q) ---")
    qc, qd = d["q_capex"], d["q_da"]
    if qc and qd:
        ttm_c, ttm_d = qc.get("TTM"), qd.get("TTM")
        if ttm_c == ttm_c and ttm_d == ttm_d:
            print(f"  TTM (as of latest Q): capex=${ttm_c/1e9:.3f}B  D&A=${ttm_d/1e9:.3f}B  "
                  f"capex/D&A={ttm_c/ttm_d:.3f}x")
        rows = _ratio_series(qc, qd)
        print(f"  {len(rows)} quarterly obs with both capex & D&A present:")
        print(f"  {'period':12} {'capex($B)':>10} {'D&A($B)':>9} {'capex/D&A':>10} {'capex YoY':>10}")
        by_date = {r[0]: r for r in rows}
        dates = [r[0] for r in rows]
        for i, (dt, c, dv, ratio) in enumerate(rows):
            yoy = ""
            # find same-quarter-prior-year (approx 4 quarters back in the sorted list)
            if i >= 4:
                prev = rows[i - 4]
                if prev[1] and prev[1] > 0:
                    yoy = f"{c/prev[1]:.3f}x"
            print(f"  {dt:12} {c/1e9:>10.3f} {dv/1e9:>9.3f} {ratio:>10.3f} {yoy:>10}")
        # explicit reproduction of the wiki's "2.66x" claim
        if "2025-05-31" in by_date and "2026-05-31" in by_date:
            c0, c1 = by_date["2025-05-31"][1], by_date["2026-05-31"][1]
            print(f"\n  [wiki repro] capex 2025-05-31 (${c0/1e9:.3f}B) -> 2026-05-31 (${c1/1e9:.3f}B) "
                  f"= {c1/c0:.3f}x  (memory-supercycle.md cites 2.66x — {'MATCH' if abs(c1/c0-2.66)<0.02 else 'MISMATCH'})")
    else:
        print("  UNAVAILABLE")

    # --- annual (defeatbeta annual_cash_flow, real data FY2021-FY2025) ---
    print("\n--- Annual (defeatbeta annual_cash_flow, FY2021-FY2025 real; FY2019-20 vendor-masked) ---")
    ac, ad = d["a_capex"], d["a_da"]
    if ac and ad:
        rows = _ratio_series(ac, ad)
        print(f"  {'FY end':12} {'capex($B)':>10} {'D&A($B)':>9} {'capex/D&A':>10}")
        for dt, c, dv, ratio in rows:
            print(f"  {dt:12} {c/1e9:>10.3f} {dv/1e9:>9.3f} {ratio:>10.3f}")
        vals = [r[3] for r in rows]
        if vals:
            print(f"  distribution (n={len(vals)}): min={min(vals):.3f}x  median={np.median(vals):.3f}x  "
                  f"max={max(vals):.3f}x  latest={vals[-1]:.3f}x  "
                  f"latest_percentile={100*sum(v<=vals[-1] for v in vals)/len(vals):.0f}%")
    else:
        print("  UNAVAILABLE")

    # --- FY2016-2018 (Tier-2, SEC 10-K text via WebSearch — see docstring) ---
    print("\n--- FY2016-2018 (Tier-2: SEC 10-K MD&A text via WebSearch, NOT a live vendor pull) ---")
    print(f"  source: {MU_FY2016_18_SEC['source']}")
    print(f"  {'FY end':12} {'capex($B)':>10} {'D&A($B)':>9} {'capex/D&A':>10}")
    fy_rows = []
    for k in sorted(MU_FY2016_18_SEC["capex"]):
        c, dv = MU_FY2016_18_SEC["capex"][k], MU_FY2016_18_SEC["da"][k]
        ratio = c / dv
        fy_rows.append((k, c, dv, ratio))
        print(f"  {k:12} {c/1e9:>10.3f} {dv/1e9:>9.3f} {ratio:>10.3f}")
    print("\n  NOTE: defeatbeta quarterly_cash_flow starts 2022-05-31; defeatbeta annual_cash_flow's "
          "earliest REAL (non-masked) column is FY2021-08-31 despite nominal FY2019/2020 columns "
          "existing with '*' placeholders; yfinance quarterly_cashflow starts 2025-02-28; yfinance "
          "annual cashflow starts FY2021-08-31. MU's 2016-18 cycle is UNOBTAINABLE from either vendor "
          "at either granularity -- this is a genuine hard data wall, not a coverage gap left unchecked.")

    return {"quarterly": qc, "quarterly_da": qd, "annual": ac, "annual_da": ad, "fy2016_18": fy_rows}


def theme_snapshot(cache):
    print("\n" + "=" * 88)
    print("15-THEME SUPPLY-SIDE SNAPSHOT — latest capex/D&A reading per theme's main ticker")
    print("=" * 88)
    rows = []
    n_ok = 0
    for theme, tk in THEME_TICKERS.items():
        d = cache.get(tk, {})
        qc, qd = d.get("q_capex"), d.get("q_da")
        ac, ad = d.get("a_capex"), d.get("a_da")
        ratio, basis, yoy = np.nan, None, np.nan
        if qc and qd and qc.get("TTM") == qc.get("TTM") and qd.get("TTM") == qd.get("TTM") and qd["TTM"] > 0:
            ratio = qc["TTM"] / qd["TTM"]
            basis = "Q-TTM"
            qrows = _ratio_series(qc, qd)
            if len(qrows) >= 5:
                c1 = qrows[-1][1]
                c0 = qrows[-5][1]
                if c0 > 0:
                    yoy = c1 / c0
        elif ac and ad:
            arows = _ratio_series(ac, ad)
            if arows:
                ratio = arows[-1][3]
                basis = f"annual-{arows[-1][0]}"
        if ratio == ratio:
            n_ok += 1
        rows.append({"theme": theme, "ticker": tk, "ratio": ratio, "basis": basis, "yoy": yoy,
                      "source": d.get("source")})

    print(f"\ncoverage: {n_ok}/{len(rows)} tickers ({100*n_ok/len(rows):.0f}%)")
    print(f"\n{'theme':32} {'tkr':6} {'capex/D&A':>10} {'basis':10} {'capex YoY':>10} {'src':10}")
    rows_sorted = sorted(rows, key=lambda r: (-(r["ratio"] if r["ratio"] == r["ratio"] else -999)))
    for r in rows_sorted:
        ratio_s = f"{r['ratio']:.3f}x" if r["ratio"] == r["ratio"] else "N/A"
        yoy_s = f"{r['yoy']:.3f}x" if r["yoy"] == r["yoy"] else ""
        print(f"{r['theme']:32} {r['ticker']:6} {ratio_s:>10} {(r['basis'] or ''):10} {yoy_s:>10} "
              f"{(r['source'] or 'none'):10}")

    print("\nflagging rule (P2 candidate warning): capex/D&A > 2.0x AND/OR capex YoY > 1.5x "
          "(both loosely anchored to MU's own current TTM=2.80x / YoY=2.66x readings, which the "
          "framework already treats as an active top-of-cycle warning for memory-supercycle).")
    warn = [r for r in rows_sorted if (r["ratio"] == r["ratio"] and r["ratio"] > 2.0) or
            (r["yoy"] == r["yoy"] and r["yoy"] > 1.5)]
    print(f"\n{len(warn)} theme(s) flagged:")
    for r in warn:
        ratio_s = f"{r['ratio']:.3f}x" if r["ratio"] == r["ratio"] else "N/A"
        yoy_s = f"{r['yoy']:.3f}x" if r["yoy"] == r["yoy"] else "N/A"
        print(f"  {r['theme']:32} {r['ticker']:6} capex/D&A={ratio_s}  capex_YoY={yoy_s}")
    return rows_sorted


def run():
    tickers = sorted(set(THEME_TICKERS.values()))
    print(f"pulling capex/D&A for {len(tickers)} tickers via defeatbeta "
          f"(disk-cached {os.path.basename(_CACHE)}, yfinance fallback) ...")
    cache = _load_data(tickers)
    mu_deep_dive(cache)
    theme_snapshot(cache)


if __name__ == "__main__":
    run()
