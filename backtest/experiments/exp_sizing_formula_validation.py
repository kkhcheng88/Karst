"""Phase-3 WS5 sizing formula validation -- backtest Expectations Investing (Mauboussin &
Rappaport) Table 7.7 conviction-sizing logic ("margin of safety % x convergence speed ->
excess return") against Karst's own historical magnifier case library.

Input case list is hand-picked from backtest/results/2026-07-09_magnifier_case_library.md
(documented trough / rally-start dates + prices). This is NOT a fresh signal backtest --
it is a retrospective test of whether the LOGIC (bigger discount + faster re-rating ==
bigger realized forward return) holds shape in ~20-25 historical supercycle troughs.

Method, per case:
  1. trough_date / trough_px  = the case library's documented rally-start (local low).
  2. prior_peak = max close in the lookback window BEFORE trough_date (up to 5y, or all
     available history if shorter). This is the margin-of-safety proxy's reference point
     -- NOT a DCF fair value (no such value available cheaply for ~20 historical cases).
     margin_of_safety_pct = (prior_peak - trough_px) / prior_peak.
     Cases with < ~180 trading days of pre-trough history are marked N/A (recent
     IPO/uplisting -- no meaningful "prior peak" to discount from).
  3. convergence_days = trading days from trough_date to the first date the close
     reclaims its 200-day SMA and STAYS above it for the next 40 trading days (a
     "sustained reclaim", not a single whipsaw close). If never reclaimed within 3y of
     the trough, marked NOT-CONVERGED (censored at 756 trading days for rank purposes).
     ** This is computed EX-POST (we know what actually happened). It is a proxy for
     "how fast did the market re-rate", not something WS5 could observe live at the
     trough. See caveats in the result file. **
  4. forward_return_1y / 2y = adjusted-close total return from trough_date to
     trough_date + 365 / 730 calendar days (nearest available trading day).

Output: prints a table + Spearman correlations (scipy) between each proxy and forward
returns, plus the book's own Table-7.7 formula applied literally (annualized required
return to close the gap over the REALIZED convergence time) vs the realized 1y/2y return,
for cases that did converge within window.

Run: python backtest/experiments/exp_sizing_formula_validation.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from data import load as load_px

# (ticker, trough_date, cycle_label) -- trough dates transcribed from
# backtest/results/2026-07-09_magnifier_case_library.md "起漲期" column start dates.
CASES = [
    ("FCX",  "2003-03-01", "China commodity supercycle (copper)"),
    ("X",    "2003-03-01", "China commodity supercycle (steel)"),
    ("NUE",  "2003-04-01", "China commodity supercycle (steel, mini-mill)"),
    ("CLF",  "2003-05-01", "China commodity supercycle (iron ore, short window)"),
    ("MEE",  "2003-05-01", "China commodity supercycle (met coal)"),
    ("PXD",  "2009-02-01", "shale/frac-sand supercycle (Permian)"),
    ("CCJ",  "2002-09-01", "uranium cycle 1"),
    ("UEC",  "2008-11-01", "uranium mini-cycle (post-GFC)"),
    ("UUUU", "2008-11-01", "uranium mini-cycle (post-GFC)"),
    ("URG",  "2008-11-01", "uranium mini-cycle (post-GFC) -- weaker peer, negative control"),
    ("NXE",  "2014-01-01", "uranium (company-specific discovery)"),
    ("MU",   "2016-03-01", "memory cycle 1 (2016 DRAM/NAND)"),
    ("ALB",  "2020-03-01", "EV/lithium supercycle"),
    ("LTHM", "2020-03-23", "EV/lithium supercycle"),
    ("SLI",  "2020-03-18", "EV/lithium supercycle (pre-revenue, extreme base effect)"),
    ("DNN",  "2020-03-01", "uranium cycle 3 (COVID low)"),
    ("CCJ",  "2020-03-23", "uranium cycle 3 (COVID low)"),
    ("LLY",  "2020-10-01", "GLP-1 manufacturing supercycle"),
    ("LEU",  "2018-12-01", "HALEU enrichment (policy-driven bottleneck)"),
    ("NVO",  "2021-03-01", "GLP-1 manufacturing supercycle -- later winner-to-loser"),
    ("MU",   "2022-12-01", "memory/HBM cycle 2 (AI)"),
    ("WDC",  "2022-12-01", "NAND/HDD cycle 2 (AI)"),
    ("LITE", "2023-10-01", "AI photonics"),
    ("COHR", "2023-10-01", "AI photonics"),
    ("MP",   "2024-03-01", "rare earths (policy-driven)"),
    ("UROY", "2023-05-01", "uranium royalty -- sub-5x underperformer, negative control"),
    # Negative-control / non-converger candidates -- deep apparent discount, test whether
    # convergence-speed proxy correctly flags "no re-rating" ahead of a bad outcome.
    ("WOLF", "2023-06-01", "SiC power semi -- pre-Chapter 11 apparent discount, negative control"),
    ("SMCI", "2024-11-14", "AI server -- post accounting-scandal crash low"),
]

LOOKBACK_YEARS_PEAK = 5
CONVERGE_HOLD_DAYS = 40      # trading days price must stay above 200sma to count as "converged"
CONVERGE_WINDOW_TDAYS = 756  # ~3y trading days; censoring point if never converges
SMA_WIN = 200


def _nearest_on_or_after(s: pd.Series, target_date: pd.Timestamp):
    idx = s.index[s.index >= target_date]
    if len(idx) == 0:
        return None
    return idx[0]


def analyze_case(ticker: str, trough_date: str, label: str):
    trough_date = pd.Timestamp(trough_date)
    try:
        df = load_px(ticker, source="auto", min_rows=50, adjusted=True)
    except Exception as e:
        return {"ticker": ticker, "trough_date": str(trough_date.date()), "label": label,
                "error": f"load failed: {type(e).__name__}: {str(e)[:120]}"}
    if df is None or len(df) < 50:
        return {"ticker": ticker, "trough_date": str(trough_date.date()), "label": label,
                "error": "no/insufficient price data"}
    s = df["close"].dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()

    # locate trough index position (nearest trading day on/after documented trough date,
    # since the case-library date is a calendar-month marker, not necessarily a trading day)
    t_idx = _nearest_on_or_after(s, trough_date)
    if t_idx is None or t_idx not in s.index:
        return {"ticker": ticker, "trough_date": str(trough_date.date()), "label": label,
                "error": "trough date outside available history"}
    trough_px = float(s.loc[t_idx])
    pos = s.index.get_loc(t_idx)

    # --- margin of safety proxy: discount vs prior peak in trailing lookback window ---
    lb_start = t_idx - pd.DateOffset(years=LOOKBACK_YEARS_PEAK)
    pre = s[(s.index >= lb_start) & (s.index < t_idx)]
    if len(pre) < 180:
        margin_of_safety = None
        prior_peak = None
        mos_note = "N/A (<180 trading days pre-trough history -- recent IPO/uplisting)"
    else:
        prior_peak = float(pre.max())
        margin_of_safety = (prior_peak - trough_px) / prior_peak * 100.0
        mos_note = ""

    # --- convergence speed proxy: sustained reclaim of 200sma after trough ---
    sma200 = s.rolling(SMA_WIN, min_periods=SMA_WIN).mean()
    fwd = s.iloc[pos:pos + CONVERGE_WINDOW_TDAYS + CONVERGE_HOLD_DAYS + 5]
    fwd_sma = sma200.loc[fwd.index]
    converge_days = None
    converge_date = None
    for i in range(len(fwd)):
        if i + CONVERGE_HOLD_DAYS >= len(fwd):
            break
        px_i, sma_i = fwd.iloc[i], fwd_sma.iloc[i]
        if pd.isna(sma_i):
            continue
        if px_i > sma_i:
            hold_slice = fwd.iloc[i:i + CONVERGE_HOLD_DAYS]
            hold_sma = fwd_sma.iloc[i:i + CONVERGE_HOLD_DAYS]
            if (hold_slice.values > hold_sma.values).mean() >= 0.90:  # allow minor whipsaw
                converge_days = i
                converge_date = fwd.index[i]
                break

    # --- forward returns ---
    def _fwd_ret(days):
        target = t_idx + pd.Timedelta(days=days)
        d = _nearest_on_or_after(s, target)
        if d is None:
            return None
        return float(s.loc[d] / trough_px - 1.0) * 100.0

    fwd_1y = _fwd_ret(365)
    fwd_2y = _fwd_ret(730)

    return {
        "ticker": ticker, "trough_date": str(t_idx.date()), "label": label,
        "trough_px": round(trough_px, 3),
        "prior_peak": round(prior_peak, 3) if prior_peak else None,
        "margin_of_safety_pct": round(margin_of_safety, 1) if margin_of_safety is not None else None,
        "mos_note": mos_note,
        "converge_trading_days": converge_days,
        "converge_date": str(converge_date.date()) if converge_date is not None else None,
        "converged": converge_days is not None,
        "fwd_return_1y_pct": round(fwd_1y, 1) if fwd_1y is not None else None,
        "fwd_return_2y_pct": round(fwd_2y, 1) if fwd_2y is not None else None,
        "error": None,
    }


def main():
    rows = []
    for ticker, trough_date, label in CASES:
        print(f"processing {ticker} @ {trough_date} ...", file=sys.stderr)
        r = analyze_case(ticker, trough_date, label)
        rows.append(r)

    out = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.max_rows", 100)
    print("\n=== raw case table ===")
    print(out.to_string(index=False))

    out.to_csv(os.path.join(os.path.dirname(__file__), "..", "results",
                             "_sizing_formula_validation_cases.csv"), index=False)

    clean = out[out["error"].isna()].copy()
    print(f"\nusable cases: {len(clean)} / {len(out)}")

    have_mos = clean[clean["margin_of_safety_pct"].notna()].copy()
    print(f"cases with usable margin-of-safety proxy: {len(have_mos)}")

    # censor non-converged cases at CONVERGE_WINDOW_TDAYS for rank correlation purposes
    have_mos["converge_days_censored"] = have_mos["converge_trading_days"].fillna(CONVERGE_WINDOW_TDAYS)
    have_mos["neg_converge_days"] = -have_mos["converge_days_censored"]

    from scipy import stats

    def _spear(x, y):
        m = x.notna() & y.notna()
        if m.sum() < 4:
            return None, None, int(m.sum())
        rho, p = stats.spearmanr(x[m], y[m])
        return rho, p, int(m.sum())

    print("\n=== Spearman rank correlations ===")
    for target in ["fwd_return_1y_pct", "fwd_return_2y_pct"]:
        rho1, p1, n1 = _spear(have_mos["margin_of_safety_pct"], have_mos[target])
        rho2, p2, n2 = _spear(have_mos["neg_converge_days"], have_mos[target])
        combined = have_mos["margin_of_safety_pct"].rank() + have_mos["neg_converge_days"].rank()
        rho3, p3, n3 = _spear(combined, have_mos[target])
        print(f"target={target}")
        print(f"  margin_of_safety vs target      : rho={rho1}, p={p1}, n={n1}")
        print(f"  neg(converge_days) vs target     : rho={rho2}, p={p2}, n={n2}")
        print(f"  combined rank(mos)+rank(-conv)   : rho={rho3}, p={p3}, n={n3}")

    # book's Table 7.7 formula applied literally, using REALIZED convergence time (ex-post)
    print("\n=== book formula applied literally (ex-post realized convergence time) ===")
    converged = have_mos[have_mos["converged"]].copy()
    converged["converge_years"] = converged["converge_trading_days"] / 252.0
    def _implied_annual_excess(row):
        if row["margin_of_safety_pct"] is None or row["converge_years"] <= 0:
            return None
        discount_frac = row["margin_of_safety_pct"] / 100.0
        price_over_ev = 1.0 - discount_frac
        if price_over_ev <= 0:
            return None
        return ((1.0 / price_over_ev) ** (1.0 / row["converge_years"]) - 1.0) * 100.0
    converged["book_implied_annual_excess_pct"] = converged.apply(_implied_annual_excess, axis=1)
    converged["realized_annualized_to_converge_pct"] = converged.apply(
        lambda r: ((1 + r["fwd_return_1y_pct"] / 100.0) ** (1.0 / max(r["converge_years"], 1/252)) - 1) * 100.0
        if r["converge_years"] <= 1.5 and r["fwd_return_1y_pct"] is not None else None, axis=1)
    print(converged[["ticker", "trough_date", "margin_of_safety_pct", "converge_years",
                      "book_implied_annual_excess_pct", "fwd_return_1y_pct",
                      "fwd_return_2y_pct"]].to_string(index=False))

    converged.to_csv(os.path.join(os.path.dirname(__file__), "..", "results",
                                   "_sizing_formula_validation_converged.csv"), index=False)


if __name__ == "__main__":
    main()
