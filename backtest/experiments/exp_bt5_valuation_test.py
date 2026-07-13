"""BT-5 — Expectations-gap valuation discrimination test (ex-ante, pre-registered judge).

Tests whether `thesis/valuation.py` v1's E_norm / P_base@14x reading correctly discriminates
KNOWN-OUTCOME historical cases: trough/enterable names should read "non-dangerous" (P_base>=0.4),
top/blow-up names should read "dangerous" (P_base<0.4 or E_norm<=0 -> N/A-binary).

The JUDGE (6 cases, test dates, expected directions, PASS rule) is pre-registered in
`backtest/results/2026-07-13_bt5_valuation_discrimination.md` §2 BEFORE any P_base was computed.
This script only executes the arithmetic and scores against that frozen judge.

METHODOLOGY (see report §3): copies valuation.py's口徑 (median margin x conservative revenue, /EV,
x14) but on ANNUAL data instead of quarterly, because defeatbeta's quarterly statements only reach
~2022-06 (too shallow for point-in-time on 2021-2024 test dates) while its ANNUAL statements reach
FY2019. market_capitalization() is a genuine point-in-time series (daily close x historical shares,
back to 1994). NO LOOK-AHEAD: a fiscal year is included only if FYE+90d <= test date (10-K would have
been filed); market cap taken at test date; NVO's DKK financials use the test-date DKK/USD rate.

Re-run:  PYTHONUTF8=1 python backtest/experiments/exp_bt5_valuation_test.py
"""
from __future__ import annotations

import contextlib
import io
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

with contextlib.redirect_stdout(io.StringIO()):
    from defeatbeta_api.data.ticker import Ticker
import yfinance as yf

# --- valuation.py constants (copied口徑) ---
TAX_RATE = 0.21
BASE_MULT = 14
FILING_LAG_DAYS = 90        # no-look-ahead: FYE + this <= test date to include a fiscal year
REV_WINDOW_YEARS = 3        # annual analog of valuation.py's 12-quarter (3yr) revenue-median window

# --- pre-registered judge (frozen in report §2 before any computation) ---
# type: "trough" -> expect non-dangerous (P_base>=0.4);  "top" -> expect dangerous (P_base<0.4 or N/A)
CASES = [
    {"ticker": "MU",   "test_date": "2022-12-30", "type": "trough",
     "note": "$49.98 trough -> 23.1x survivor"},
    {"ticker": "WDC",  "test_date": "2022-12-30", "type": "trough",
     "note": "$23.85 trough -> 26.78x survivor"},
    {"ticker": "FSLR", "test_date": "2022-07-01", "type": "trough",
     "note": "IRA-pre low, CdTe-moat survivor"},
    {"ticker": "WOLF", "test_date": "2021-11-16", "type": "top",
     "note": "ATH $141.87 -> 2025-06 Chapter 11"},
    {"ticker": "SMCI", "test_date": "2024-03-13", "type": "top",
     "note": "$118.807 top -> -85% (accounting)"},
    {"ticker": "NVO",  "test_date": "2024-06-25", "type": "top",
     "note": "$142.74 top -> -56% (CagriSema)"},
]

# NVO reports in DKK; point-in-time DKK/USD (yfinance DKKUSD=X, 2024-06-25 close). Hardcoded for
# reproducibility; script also tries a live fetch and warns if it drifts materially.
NVO_FX_HARDCODE = 0.143895


def _num(x):
    if x is None:
        return None
    if isinstance(x, str):
        s = x.strip()
        if s in ("", "*"):
            return None
        try:
            return float(s)
        except ValueError:
            return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _fin_currency(sym: str) -> str:
    try:
        cur = yf.Ticker(sym).info.get("financialCurrency")
        return cur if cur else "USD"
    except Exception:
        return "USD"


def _pit_fx(cur: str, test_date: str) -> float:
    """Point-in-time FX: 1 unit of `cur` in USD at test_date. USD -> 1.0."""
    if cur == "USD":
        return 1.0
    if cur == "DKK":
        # try live, fall back to documented hardcode
        try:
            td = pd.Timestamp(test_date)
            h = yf.download(f"{cur}USD=X", start=(td - timedelta(days=7)).date().isoformat(),
                            end=(td + timedelta(days=3)).date().isoformat(), progress=False)
            if h is not None and len(h) > 0:
                closes = h["Close"]
                val = float(closes.iloc[-1].iloc[0] if hasattr(closes.iloc[-1], "iloc") else closes.iloc[-1])
                if abs(val - NVO_FX_HARDCODE) / NVO_FX_HARDCODE < 0.03:
                    return val
        except Exception:
            pass
        return NVO_FX_HARDCODE
    raise RuntimeError(f"no point-in-time FX wired for {cur}")


def _annual_cols_asof(df: pd.DataFrame, test_date: str):
    """Return year-column labels whose FYE + FILING_LAG_DAYS <= test_date, sorted desc by FYE."""
    td = pd.Timestamp(test_date)
    cols = []
    for c in df.columns:
        if c in ("Breakdown", "TTM"):
            continue
        try:
            fye = pd.Timestamp(c)
        except Exception:
            continue
        if fye + pd.Timedelta(days=FILING_LAG_DAYS) <= td:
            cols.append((fye, c))
    cols.sort(key=lambda t: t[0], reverse=True)
    return cols  # list of (fye_timestamp, col_label)


def _row_val(df, breakdown, col):
    r = df[df["Breakdown"] == breakdown]
    if len(r) == 0:
        return None
    return _num(r[col].iloc[0])


def compute_case(case: dict) -> dict:
    sym, test_date, ctype = case["ticker"], case["test_date"], case["type"]
    out = {"ticker": sym, "test_date": test_date, "type": ctype, "note": case["note"]}

    with contextlib.redirect_stdout(io.StringIO()):
        t = Ticker(sym)
        ais = t.annual_income_statement().df()
        abs_ = t.annual_balance_sheet().df()
        mc = t.market_capitalization()

    # --- included fiscal years (no look-ahead) ---
    inc_cols = _annual_cols_asof(ais, test_date)
    if not inc_cols:
        out["error"] = "no fiscal year filed as of test date"
        return out
    fy_labels = [c for _, c in inc_cols]
    out["included_fys"] = [str(pd.Timestamp(c).date()) for c in fy_labels]

    # --- margin median over ALL included FYs ---
    margins, rev_by_fy = [], []
    for _, c in inc_cols:
        rev = _row_val(ais, "Total Revenue", c)
        oi = _row_val(ais, "Operating Income", c)
        if rev is not None and oi is not None and rev > 0:
            margins.append(oi / rev)
            rev_by_fy.append((c, rev))
    if not margins:
        out["error"] = "no usable annual margin"
        return out
    margin_median = float(np.median(margins))

    # --- revenue term: min(latest FY rev, median of most-recent-3 FY revs) ---
    latest_fy_rev = rev_by_fy[0][1]  # inc_cols is desc, rev_by_fy follows same order
    recent_revs = [r for _, r in rev_by_fy[:REV_WINDOW_YEARS]]
    rev_3y_median = float(np.median(recent_revs))
    if latest_fy_rev <= rev_3y_median:
        revenue_used = latest_fy_rev
        rev_basis = "latest FY (already <= 3yr median)"
    else:
        revenue_used = rev_3y_median
        rev_basis = f"3yr median (damped; latest FY {(latest_fy_rev/rev_3y_median-1)*100:.0f}% above)"

    # --- net debt from latest included FY balance sheet ---
    bs_cols = _annual_cols_asof(abs_, test_date)
    if not bs_cols:
        out["error"] = "no balance sheet as of test date"
        return out
    bs_label = bs_cols[0][1]
    total_debt = _row_val(abs_, "Total Debt", bs_label)
    cash = _row_val(abs_, "Cash, Cash Equivalents & Short Term Investments", bs_label)
    if cash is None:
        cash = _row_val(abs_, "Cash And Cash Equivalents", bs_label)
    if total_debt is None or cash is None:
        out["error"] = "missing Total Debt/Cash on latest FY BS"
        return out
    net_debt = total_debt - cash
    out["bs_date"] = str(pd.Timestamp(bs_label).date())

    # --- point-in-time market cap ---
    dc = [c for c in mc.columns if "date" in c.lower()][0]
    vc = "market_capitalization"
    m = mc.copy()
    m[dc] = pd.to_datetime(m[dc])
    sub = m[m[dc] <= pd.Timestamp(test_date)].sort_values(dc)
    if len(sub) == 0:
        out["error"] = "no market cap as of test date"
        return out
    market_cap = float(sub.iloc[-1][vc])
    out["mc_date"] = str(sub.iloc[-1][dc].date())

    # --- FX (DKK financials -> USD; market cap already USD) ---
    fin_cur = _fin_currency(sym)
    fx = _pit_fx(fin_cur, test_date)
    out["fin_currency"] = fin_cur
    out["fx"] = fx

    # --- assemble (valuation.py口徑) ---
    e_norm = margin_median * revenue_used * fx
    nopat = e_norm * (1 - TAX_RATE)
    ev = market_cap + net_debt * fx
    p_base = (nopat * BASE_MULT / ev) if ev != 0 else None

    if e_norm <= 0:
        cls = "N/A-binary (option framing)"
    elif ev <= 0:
        cls = "N/A (EV<=0)"
    elif p_base is None:
        cls = "N/A"
    elif p_base >= 0.8:
        cls = "supercycle 白送"
    elif p_base >= 0.4:
        cls = "買緊部分希望"
    else:
        cls = "大部分係希望"

    out.update({
        "margin_median": margin_median, "latest_fy_rev": latest_fy_rev,
        "rev_3y_median": rev_3y_median, "revenue_used": revenue_used, "rev_basis": rev_basis,
        "e_norm_usd": e_norm, "nopat_usd": nopat, "net_debt_usd": net_debt * fx,
        "market_cap_usd": market_cap, "ev_usd": ev, "p_base": p_base, "classification": cls,
    })

    # --- pre-registered judge ---
    dangerous = cls in ("大部分係希望", "N/A-binary (option framing)", "N/A (EV<=0)")
    if ctype == "trough":
        out["expected"] = "non-dangerous (P_base>=0.4)"
        out["pass"] = (not dangerous)
    else:  # top
        out["expected"] = "dangerous (P_base<0.4 or N/A)"
        out["pass"] = dangerous
    return out


def _fmt_usd(x):
    if x is None:
        return "N/A"
    ax = abs(x); sign = "-" if x < 0 else ""
    if ax >= 1e9:
        return f"{sign}${ax/1e9:.2f}B"
    if ax >= 1e6:
        return f"{sign}${ax/1e6:.1f}M"
    return f"{sign}${ax:,.0f}"


def main():
    rows = [compute_case(c) for c in CASES]
    n_pass = sum(1 for r in rows if r.get("pass"))
    n_total = len(rows)

    print("=" * 100)
    print(f"BT-5 Expectations-Gap discrimination test — {date.today().isoformat()}")
    print("=" * 100)
    for r in rows:
        if "error" in r:
            print(f"\n[{r['ticker']} @ {r['test_date']}]  ERROR: {r['error']}")
            continue
        verdict = "PASS" if r["pass"] else "FAIL"
        print(f"\n[{r['ticker']} @ {r['test_date']}]  type={r['type']}  ({r['note']})")
        print(f"  included FYs: {', '.join(r['included_fys'])}   BS: {r['bs_date']}   MC date: {r['mc_date']}")
        print(f"  margin_median = {r['margin_median']*100:.1f}%   revenue_used = {_fmt_usd(r['revenue_used']*r['fx'])}"
              f"  [{r['rev_basis']}]   FX({r['fin_currency']}) = {r['fx']}")
        print(f"  E_norm = {_fmt_usd(r['e_norm_usd'])}   NOPAT = {_fmt_usd(r['nopat_usd'])}   "
              f"net_debt = {_fmt_usd(r['net_debt_usd'])}   mktcap = {_fmt_usd(r['market_cap_usd'])}   EV = {_fmt_usd(r['ev_usd'])}")
        pb = "N/A" if r["p_base"] is None else f"{r['p_base']:.3f}x"
        print(f"  P_base@14x = {pb}   -> classification: {r['classification']}")
        print(f"  expected: {r['expected']}   ==>  {verdict}")

    print("\n" + "=" * 100)
    print(f"RESULT: {n_pass}/{n_total} PASS  ->  {'GATE OPEN (can wire sizing)' if n_pass == n_total else 'GATE CLOSED (display-only)'}")
    print("=" * 100)
    # compact one-line-per-case for the report evidence table
    print("\n[report-evidence]")
    for r in rows:
        if "error" in r:
            print(f"{r['ticker']}|{r['test_date']}|ERROR:{r['error']}")
            continue
        pb = "N/A" if r["p_base"] is None else f"{r['p_base']:.3f}x"
        print(f"{r['ticker']}|{r['test_date']}|{r['type']}|Pbase={pb}|{r['classification']}|{'PASS' if r['pass'] else 'FAIL'}")
    return rows, n_pass, n_total


if __name__ == "__main__":
    main()
