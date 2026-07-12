"""Expectations-gap valuation v0 — Mauboussin "expectations investing", not Graham deep-value.

Karst's entire system has NO valuation step (thesis_valuation.py has never been built). This is
v0: for every active thesis theme, measure how much future growth the market is ALREADY PAYING
FOR, vs. what a cycle-neutral ("supercycle never arrives") normal earning power would justify.

Philosophy: this is NOT "is the stock cheap in absolute terms" (Graham). It is "how much
expectation is embedded in the current price" (Mauboussin). The magnifier reading is
"supercycle-free coverage": if the AI/memory/space/etc. supercycle theses NEVER pay off and the
business reverts to mid-cycle normal margins, how much of today's EV is already covered by that
boring baseline?

Method
------
1. Universe: top 1-2 expressive tickers per active theme (thesis/themes.yaml `tickers` list,
   first 1-2 entries) + 4 WATCH-only names (KALU/MCHP/AVT/PTEN) not yet promoted to a theme.
2. Data: defeatbeta FIRST (repo convention for fundamentals; backtest/data.py is yfinance-first
   for PRICES only — fundamentals are a separate code path). yfinance financials are the FALLBACK,
   only used if defeatbeta fails; the report marks which tickers (if any) used it.
   - Quarterly revenue + operating income: Ticker(sym).quarterly_income_statement().df()
     ("Total Revenue" / "Operating Income" rows). We use "Operating Income", NOT the "EBIT" row
     defeatbeta also exposes -- verified on XOM/MU that "EBIT" can run >25% above "Operating
     Income" for names with material non-operating income (equity-affiliate earnings etc.); using
     Operating Income keeps E_norm a read on the CORE business, not one-off/non-operating items.
   - Net debt: defeatbeta's own "Net Debt" balance-sheet row is frequently MASKED ('*' placeholder)
     or absent (confirmed on MU/GEV/ASTS/AEHR/FSLR/WST etc.). Instead we compute it directly from
     "Total Debt" - "Cash, Cash Equivalents & Short Term Investments" (both rows are clean/complete
     across the full 28-ticker universe as tested) -- matches the task's literal "total debt - cash"
     definition anyway.
   - Market cap: Ticker(sym).market_capitalization(), latest daily row.
3. Per ticker:
   E_norm      = median(quarterly Operating Income / Total Revenue, ALL available quarters)
                 x TTM revenue                              (normalized operating earning power)
   NOPAT_norm  = E_norm x (1 - 0.21)                         (flat US corporate tax, not effective rate)
   EV          = market_cap + net_debt
   P_base      = (NOPAT_norm x 14) / EV                      ("supercycle-free coverage" @ 14x NOPAT)
                 also reported @ 10x / 18x for sensitivity
   g_implied   = ((EV x 1.10^5) / (14 x NOPAT_norm))^(1/5) - 1   (5yr growth the market is pricing
                 in, discounting the terminal 14x-NOPAT value back at a 10% WACC)
   classification:
     E_norm <= 0            -> "N/A-binary (option framing)"   (no normalized earning power to anchor on)
     P_base >= 0.8           -> "supercycle 白送" (free lunch -- mid-cycle earnings alone justify most of EV)
     0.4 <= P_base < 0.8      -> "買緊部分希望" (buying partial hope)
     P_base < 0.4            -> "大部分係希望" (mostly hope -- most of EV is a bet on the supercycle)

Known biases (see report caveats section for the full writeup):
  - 14x is a BASELINE ASSUMPTION for a no-growth, average-quality operating business. It is not
    "the right multiple" for any specific name -- that's why 10x/18x sensitivities are reported too.
  - EBIT margin is NOT stationary across a cycle -- median-of-history is a compromise, not a law.
  - TTM revenue at a CYCLE PEAK inflates E_norm (E_norm = margin x TTM revenue uses the CURRENT,
    possibly cyclically-elevated, revenue level as the multiplier) -- flagged explicitly per-ticker
    where cycle_stage is late/peak (see MU commentary).

Run: python backtest/experiments/exp_expectations_gap_v0.py
Output: backtest/results/2026-07-12_expectations_gap_v0.md
"""
from __future__ import annotations

import contextlib
import io
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with contextlib.redirect_stdout(io.StringIO()):
    from defeatbeta_api.data.ticker import Ticker

import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_MD = os.path.join(ROOT, "backtest", "results", "2026-07-12_expectations_gap_v0.md")

TAX_RATE = 0.21
MULTIPLES = (10, 14, 18)
BASE_MULT = 14
WACC = 0.10
HORIZON = 5
MIN_QUARTERS_OK = 12

# theme -> top 1-2 expressive tickers, from thesis/themes.yaml "tickers" list order (first 1-2
# entries per theme; single-ticker themes use that one ticker).
THEMES = {
    "memory-supercycle": ["MU", "SNDK"],
    "photonics-optical": ["COHR", "LITE"],
    "ai-power-grid": ["GEV", "BE"],
    "advanced-packaging": ["AMKR", "ASX"],
    "space-satellite": ["RKLB", "ASTS"],
    "rare-earth-materials": ["MP", "USAR"],
    "tpu-custom-silicon": ["AVGO", "TSM"],
    "oil-gas-energy": ["XOM", "CVX"],
    "semicap-equipment": ["AEHR"],
    "aerospace-specialty-alloys": ["ATI", "CRS"],
    "euv-lithography-monopoly": ["ASML"],
    "us-solar-manufacturing": ["FSLR"],
    "gas-compression-equipment": ["USAC"],
    "specialty-siding-pricing-power": ["LPX"],
    "glp1-biologics-packaging": ["WST"],
}
WATCH = ["KALU", "MCHP", "AVT", "PTEN"]

SPECIAL_FOCUS = ["USAC", "FSLR", "ASML", "ATI", "MU"]


_FX_CACHE: dict = {}


def _fin_currency(sym: str) -> str:
    """Financial-statements currency (NOT trading currency -- ADRs trade USD but report TWD/EUR)."""
    try:
        cur = yf.Ticker(sym).info.get("financialCurrency")
        return cur if cur else "USD"
    except Exception:
        return "USD"


def _fx_to_usd(cur: str) -> float:
    """Spot FX rate: 1 unit of `cur` in USD. USD -> 1.0. Raises if unavailable."""
    if cur == "USD":
        return 1.0
    if cur in _FX_CACHE:
        return _FX_CACHE[cur]
    rate = getattr(yf.Ticker(f"{cur}USD=X").fast_info, "last_price", None)
    if rate is None or rate <= 0:
        raise RuntimeError(f"no FX rate for {cur}USD=X")
    _FX_CACHE[cur] = float(rate)
    return _FX_CACHE[cur]


def _num(x):
    """Coerce defeatbeta Decimal / str values to float. '*' (masked) or unparsable -> None."""
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
    return v if v == v else None  # filter NaN


def _from_defeatbeta(sym: str) -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        t = Ticker(sym)
        qis = t.quarterly_income_statement().df()
        qbs = t.quarterly_balance_sheet().df()
        mc_df = t.market_capitalization()

    period_cols = [c for c in qis.columns if c not in ("Breakdown", "TTM")]
    rev_row = qis[qis["Breakdown"] == "Total Revenue"]
    oi_row = qis[qis["Breakdown"] == "Operating Income"]
    if len(rev_row) == 0 or len(oi_row) == 0:
        raise RuntimeError("missing Total Revenue/Operating Income row")

    rev = {c: _num(rev_row[c].iloc[0]) for c in period_cols}
    oi = {c: _num(oi_row[c].iloc[0]) for c in period_cols}

    margins = []
    for c in period_cols:
        r, o = rev.get(c), oi.get(c)
        if r is not None and o is not None and r > 0:
            margins.append(o / r)
    n_quarters = len(margins)
    if n_quarters == 0:
        raise RuntimeError("no usable quarterly margin data")
    ebit_margin_median = float(np.median(margins))

    ttm_rev = _num(rev_row["TTM"].iloc[0]) if "TTM" in qis.columns else None
    if ttm_rev is None:
        recent4 = [rev[c] for c in period_cols[:4] if rev.get(c) is not None]
        ttm_rev = sum(recent4) if len(recent4) == 4 else None
    if ttm_rev is None or ttm_rev <= 0:
        raise RuntimeError("no usable TTM revenue")

    bs_cols = [c for c in qbs.columns if c != "Breakdown"]
    if not bs_cols:
        raise RuntimeError("empty balance sheet")
    latest_bs = bs_cols[0]
    td_row = qbs[qbs["Breakdown"] == "Total Debt"]
    cash_row = qbs[qbs["Breakdown"] == "Cash, Cash Equivalents & Short Term Investments"]
    if len(cash_row) == 0:
        cash_row = qbs[qbs["Breakdown"] == "Cash And Cash Equivalents"]
    total_debt = _num(td_row[latest_bs].iloc[0]) if len(td_row) else None
    cash = _num(cash_row[latest_bs].iloc[0]) if len(cash_row) else None
    if total_debt is None or cash is None:
        raise RuntimeError("missing/masked Total Debt or Cash balance-sheet row")
    net_debt = total_debt - cash

    if mc_df is None or len(mc_df) == 0:
        raise RuntimeError("no market_capitalization data")
    market_cap = _num(mc_df["market_capitalization"].iloc[-1])
    if market_cap is None or market_cap <= 0:
        raise RuntimeError("market_cap unreadable")

    # Currency alignment: statements can be TWD (TSM/ASX ADRs) or EUR (ASML) while market cap is
    # USD. Convert the two statement-currency ABSOLUTE figures (TTM revenue, net debt) to USD at
    # spot; the margin term is dimensionless so E_norm inherits USD via ttm_rev.
    fin_cur = _fin_currency(sym)
    fx = _fx_to_usd(fin_cur)
    src = "defeatbeta" if fin_cur == "USD" else f"defeatbeta ({fin_cur}→USD @{fx:.4f})"

    return {
        "ebit_margin_median": ebit_margin_median,
        "ttm_revenue": ttm_rev * fx,
        "net_debt": net_debt * fx,
        "market_cap": market_cap,
        "n_quarters": n_quarters,
        "bs_date": str(latest_bs),
        "fin_currency": fin_cur,
        "source": src,
    }


def _from_yfinance(sym: str) -> dict:
    """Fallback path -- only exercised if defeatbeta fails for a ticker."""
    t = yf.Ticker(sym)
    qf = t.quarterly_income_stmt
    qbs = t.quarterly_balance_sheet
    if qf is None or qf.empty:
        raise RuntimeError("yfinance quarterly_income_stmt empty")
    if "Total Revenue" not in qf.index or "Operating Income" not in qf.index:
        raise RuntimeError("yfinance missing Total Revenue/Operating Income row")
    period_cols = list(qf.columns)
    margins = []
    for c in period_cols:
        r = _num(qf.loc["Total Revenue", c])
        o = _num(qf.loc["Operating Income", c])
        if r is not None and o is not None and r > 0:
            margins.append(o / r)
    n_quarters = len(margins)
    if n_quarters == 0:
        raise RuntimeError("no usable yfinance quarterly margin data")
    ebit_margin_median = float(np.median(margins))

    recent4 = [_num(qf.loc["Total Revenue", c]) for c in period_cols[:4]]
    recent4 = [v for v in recent4 if v is not None]
    if len(recent4) < 4:
        raise RuntimeError("yfinance <4 quarters revenue for TTM")
    ttm_rev = sum(recent4)

    if qbs is None or qbs.empty:
        raise RuntimeError("yfinance quarterly_balance_sheet empty")
    bs_cols = list(qbs.columns)
    latest_bs = bs_cols[0]
    cash_label = None
    for cand in ("Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"):
        if cand in qbs.index:
            cash_label = cand
            break
    if "Total Debt" not in qbs.index or cash_label is None:
        raise RuntimeError("yfinance missing Total Debt/Cash balance-sheet row")
    total_debt = _num(qbs.loc["Total Debt", latest_bs])
    cash = _num(qbs.loc[cash_label, latest_bs])
    if total_debt is None or cash is None:
        raise RuntimeError("yfinance Total Debt/Cash unreadable")
    net_debt = total_debt - cash

    market_cap = _num(getattr(t.fast_info, "market_cap", None))
    if market_cap is None or market_cap <= 0:
        raise RuntimeError("yfinance fast_info.market_cap unreadable")

    fin_cur = _fin_currency(sym)
    fx = _fx_to_usd(fin_cur)
    src = "yfinance(fallback)" if fin_cur == "USD" else f"yfinance(fallback, {fin_cur}→USD @{fx:.4f})"

    return {
        "ebit_margin_median": ebit_margin_median,
        "ttm_revenue": ttm_rev * fx,
        "net_debt": net_debt * fx,
        "market_cap": market_cap,
        "n_quarters": n_quarters,
        "bs_date": str(pd.Timestamp(latest_bs).date()),
        "fin_currency": fin_cur,
        "source": src,
    }


def compute(sym: str) -> dict:
    row = {"ticker": sym}
    try:
        d = _from_defeatbeta(sym)
    except Exception as e1:
        try:
            d = _from_yfinance(sym)
            d["fallback_reason"] = f"defeatbeta failed: {str(e1)[:120]}"
        except Exception as e2:
            row["error"] = f"defeatbeta: {str(e1)[:90]} | yfinance: {str(e2)[:90]}"
            return row
    row.update(d)

    e_norm = d["ebit_margin_median"] * d["ttm_revenue"]
    nopat_norm = e_norm * (1 - TAX_RATE)
    ev = d["market_cap"] + d["net_debt"]
    row["e_norm"] = e_norm
    row["nopat_norm"] = nopat_norm
    row["ev"] = ev

    for m in MULTIPLES:
        row[f"p_{m}x"] = (nopat_norm * m / ev) if ev != 0 else None

    if nopat_norm > 0 and ev > 0:
        row["g_implied"] = ((ev * (1 + WACC) ** HORIZON) / (BASE_MULT * nopat_norm)) ** (1 / HORIZON) - 1
    else:
        row["g_implied"] = None

    p_base = row.get(f"p_{BASE_MULT}x")
    if e_norm <= 0:
        row["classification"] = "N/A-binary (option framing)"
    elif ev <= 0:
        row["classification"] = "N/A (EV<=0 -- net cash exceeds market cap)"
    elif p_base is None:
        row["classification"] = "N/A"
    elif p_base >= 0.8:
        row["classification"] = "supercycle 白送"
    elif p_base >= 0.4:
        row["classification"] = "買緊部分希望"
    else:
        row["classification"] = "大部分係希望"
    return row


def run():
    ticker_themes: dict[str, list[str]] = {}
    for theme, tks in THEMES.items():
        for tk in tks:
            ticker_themes.setdefault(tk, []).append(theme)
    for tk in WATCH:
        ticker_themes.setdefault(tk, []).append("WATCH")

    rows = []
    for sym in ticker_themes:
        print(f"computing {sym} ...")
        r = compute(sym)
        r["themes"] = ", ".join(ticker_themes[sym])
        rows.append(r)

    ok_rows = [r for r in rows if "error" not in r]
    fail_rows = [r for r in rows if "error" in r]
    fb_rows = [r for r in ok_rows if str(r.get("source", "")).startswith("yfinance(fallback")]
    thin_rows = [r for r in ok_rows if r["n_quarters"] < MIN_QUARTERS_OK]

    print(f"\n{len(ok_rows)}/{len(rows)} tickers computed OK "
          f"({len(fb_rows)} used yfinance fallback, {len(thin_rows)} have <{MIN_QUARTERS_OK}q data)")
    for r in fail_rows:
        print(f"  FAIL {r['ticker']}: {r['error']}")

    write_report(rows, ok_rows, fail_rows, fb_rows, thin_rows)
    print(f"\nwrote {OUT_MD}")
    return rows


def _fmt_usd(x):
    if x is None:
        return "N/A"
    ax = abs(x)
    sign = "-" if x < 0 else ""
    if ax >= 1e9:
        return f"{sign}${ax/1e9:,.2f}B"
    if ax >= 1e6:
        return f"{sign}${ax/1e6:,.1f}M"
    return f"{sign}${ax:,.0f}"


def _fmt_pct(x, digits=1):
    return "N/A" if x is None else f"{x*100:.{digits}f}%"


def _fmt_mult(x):
    return "N/A" if x is None else f"{x:.2f}x"


def write_report(rows, ok_rows, fail_rows, fb_rows, thin_rows):
    ranked = sorted(ok_rows, key=lambda r: (r.get(f"p_{BASE_MULT}x") is None, -(r.get(f"p_{BASE_MULT}x") or -999)))

    n_mostly_hope = sum(1 for r in ok_rows if r["classification"] == "大部分係希望")
    n_partial = sum(1 for r in ok_rows if r["classification"] == "買緊部分希望")
    n_free = sum(1 for r in ok_rows if r["classification"] == "supercycle 白送")
    n_binary = sum(1 for r in ok_rows if r["classification"] == "N/A-binary (option framing)")

    lines = []
    lines.append("# Expectations-Gap Valuation v0 — 2026-07-12")
    lines.append("")
    lines.append("Script: `backtest/experiments/exp_expectations_gap_v0.py` "
                  "(`python backtest/experiments/exp_expectations_gap_v0.py`)")
    lines.append("")
    lines.append("## What this is (and isn't)")
    lines.append("")
    lines.append("Mauboussin-style **expectations investing**, not Graham deep-value: the question is "
                  "\"how much future growth/performance is the current price already paying for,\" not "
                  "\"is this stock cheap in absolute terms.\" The headline number, **P_base@14x "
                  "(\"supercycle-free coverage\")**, asks: if every one of these supercycle theses "
                  "(AI/memory/space/rare-earth/etc.) never plays out and each business just prints its "
                  "own **normalized, mid-cycle** operating earnings forever, what fraction of today's "
                  "Enterprise Value does that boring baseline already justify? P_base >= 0.8 = the "
                  "supercycle is basically a free option on top of a fairly-covered EV. P_base < 0.4 = "
                  "most of the EV is a bet that the supercycle actually happens.")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append("```")
    lines.append("E_norm      = median(quarterly Operating Income / Total Revenue) x TTM revenue")
    lines.append("NOPAT_norm  = E_norm x (1 - 0.21)")
    lines.append("EV          = market_cap + net_debt   (net_debt = Total Debt - Cash&STI, latest quarter)")
    lines.append("P_base      = NOPAT_norm x 14 / EV     (also reported @ 10x / 18x)")
    lines.append("g_implied   = ((EV x 1.10^5) / (14 x NOPAT_norm)) ^ (1/5) - 1")
    lines.append("```")
    lines.append("")
    lines.append("Classification: P_base>=0.8 \"supercycle 白送\" / 0.4-0.8 \"買緊部分希望\" / "
                  "<0.4 \"大部分係希望\" / E_norm<=0 \"N/A-binary (option framing)\".")
    lines.append("")
    lines.append("Universe: top 1-2 expressive tickers per active theme in `thesis/themes.yaml` "
                  "+ 4 WATCH-only names (KALU/MCHP/AVT/PTEN).")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- {len(ok_rows)}/{len(rows)} tickers computed successfully "
                  f"({len(fail_rows)} failed -- see below).")
    lines.append(f"- Classification split (of {len(ok_rows)} OK): "
                  f"**{n_mostly_hope} 大部分係希望** (mostly hope), "
                  f"{n_partial} 買緊部分希望 (partial hope), "
                  f"{n_free} supercycle 白送 (free lunch), "
                  f"{n_binary} N/A-binary (option framing).")
    lines.append(f"- {len(fb_rows)} ticker(s) used the yfinance fallback "
                  f"({', '.join(r['ticker'] for r in fb_rows) if fb_rows else 'none -- defeatbeta covered all'}).")
    thin_desc = ", ".join("{}({}q)".format(r["ticker"], r["n_quarters"]) for r in thin_rows) if thin_rows else "none"
    lines.append(f"- {len(thin_rows)} ticker(s) have <{MIN_QUARTERS_OK} quarters of data ({thin_desc}).")
    if fail_rows:
        lines.append(f"- FAILED (0 usable data, both sources): "
                      f"{', '.join(r['ticker'] for r in fail_rows)}.")
    lines.append("")
    # ---- theme-level rollup: a theme's coverage = its BEST expressive ticker's P_base ----
    lines.append("## Theme-level rollup (15 active themes)")
    lines.append("")
    lines.append("A theme's reading = the BEST P_base@14x among its expressive tickers (generous "
                  "reading: if even the best-covered expression of the theme is mostly hope, the theme "
                  "is). \"N/A-binary\" only when ALL the theme's computed tickers have E_norm <= 0.")
    lines.append("")
    lines.append("| Theme | Best ticker | P_base@14x | Theme classification |")
    lines.append("|---|---|---:|---|")
    theme_class_counts = {}
    by_theme_rows = []
    for theme in THEMES:
        t_rows = [r for r in ok_rows if theme in r["themes"].split(", ")]
        if not t_rows:
            by_theme_rows.append((theme, "-", None, "N/A (no data)"))
            continue
        pos = [r for r in t_rows if (r.get("e_norm") or 0) > 0 and r.get("p_14x") is not None]
        if not pos:
            best = max(t_rows, key=lambda r: r.get("p_14x") if r.get("p_14x") is not None else -999)
            by_theme_rows.append((theme, best["ticker"], best.get("p_14x"), "N/A-binary (option framing)"))
            continue
        best = max(pos, key=lambda r: r["p_14x"])
        pb = best["p_14x"]
        cls = ("supercycle 白送" if pb >= 0.8 else "買緊部分希望" if pb >= 0.4 else "大部分係希望")
        by_theme_rows.append((theme, best["ticker"], pb, cls))
    by_theme_rows.sort(key=lambda x: (x[2] is None, -(x[2] if x[2] is not None else -999)))
    for theme, tk, pb, cls in by_theme_rows:
        theme_class_counts[cls] = theme_class_counts.get(cls, 0) + 1
        lines.append(f"| {theme} | {tk} | {_fmt_mult(pb)} | {cls} |")
    lines.append("")
    rollup_desc = ", ".join(f"{v} {k}" for k, v in sorted(theme_class_counts.items(), key=lambda kv: -kv[1]))
    lines.append(f"**Theme-level split ({len(THEMES)} themes): {rollup_desc}.**")
    lines.append("")
    lines.append("## Full table (sorted by P_base@14x, descending)")
    lines.append("")
    lines.append("| Theme | Ticker | EBIT margin (median) | E_norm | P_base@14x | P@10x | P@18x | "
                  "g_implied(5y) | Classification | #Q | Source |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|")
    for r in ranked:
        src = r["source"] + (" *" if r.get("fallback_reason") else "")
        lines.append(
            f"| {r['themes']} | **{r['ticker']}** | {_fmt_pct(r['ebit_margin_median'])} | "
            f"{_fmt_usd(r['e_norm'])} | {_fmt_mult(r.get('p_14x'))} | {_fmt_mult(r.get('p_10x'))} | "
            f"{_fmt_mult(r.get('p_18x'))} | {_fmt_pct(r.get('g_implied'))} | {r['classification']} | "
            f"{r['n_quarters']} | {src} |"
        )
    lines.append("")
    if fail_rows:
        lines.append("### Failed tickers (excluded from table above)")
        lines.append("")
        for r in fail_rows:
            lines.append(f"- **{r['ticker']}** ({r.get('themes','')}) — {r['error']}")
        lines.append("")

    lines.append("## Caveats (read before trusting any number above)")
    lines.append("")
    lines.append("1. **14x is a baseline assumption, not truth.** It approximates a no-growth, "
                  "average-quality operating business capitalizing its NOPAT in perpetuity "
                  "(~7% earnings yield). It is not calibrated per-sector or per-quality; that's why "
                  "10x/18x sensitivities are reported alongside -- treat P_base as a RANGE, not a point.")
    lines.append("2. **EBIT margin is not stationary.** median(margin) across history smooths cyclicality "
                  "but does NOT predict where margin normalizes to next cycle -- it's a backward-looking "
                  "compromise, not a structural forecast.")
    lines.append("3. **TTM revenue at a cycle peak inflates E_norm.** E_norm = median_margin x **TTM** "
                  "revenue. If a name's current TTM revenue is itself cyclically elevated (e.g. a memory "
                  "or commodity name mid-upcycle), E_norm overstates \"normal\" earning power even though "
                  "the margin term is median-smoothed -- the revenue term isn't. This directly inflates "
                  "P_base and understates how much hope is priced in. See the MU commentary below for a "
                  "worked example of how to read this bias.")
    lines.append(f"4. **Net debt is computed manually** (Total Debt − Cash&STI, latest balance-sheet "
                  f"quarter), NOT from defeatbeta's own \"Net Debt\" row -- that row is masked (`*`) or "
                  f"absent for a large share of this universe (MU, GEV, ASTS, AEHR, FSLR, WST, RKLB, "
                  f"USAR, TSM, ASML and others all showed a masked/missing Net Debt row on inspection). "
                  f"Total Debt and Cash rows were clean across the full universe.")
    lines.append("5. **\"Operating Income,\" not the \"EBIT\" row defeatbeta also exposes.** Spot-checked "
                  "on XOM/MU: EBIT can run >25% above Operating Income for names with material "
                  "non-operating income (e.g. equity-affiliate earnings) -- Operating Income keeps "
                  "E_norm anchored to the core, controllable business.")
    thin_note = (", ".join("{} ({}q)".format(r["ticker"], r["n_quarters"]) for r in thin_rows)
                 if thin_rows else "none")
    lines.append(f"6. **Data depth is short of the \"ideal 28+ quarters\" target** -- defeatbeta's "
                  f"quarterly_income_statement tops out at 16-17 quarter COLUMNS for large/established "
                  f"names (~4yr), and some quarters inside that window are masked (`*`), so USABLE "
                  f"quarters (what #Q counts) can be fewer still. Below the {MIN_QUARTERS_OK}-quarter "
                  f"floor: {thin_note}. Fewer quarters = the median-margin estimate has seen fewer "
                  f"cycle phases and is less trustworthy -- USAR's 2 usable quarters in particular make "
                  f"its margin figure nearly meaningless (it lands in N/A-binary regardless).")
    lines.append("7. **g_implied is undefined (N/A) whenever NOPAT_norm <= 0** -- for those names the "
                  "market isn't pricing a growth rate off a normalized earnings base at all; it's pricing "
                  "a binary/optionality outcome (hence the separate \"N/A-binary\" classification bucket, "
                  "which should be read qualitatively, not compared numerically to the P_base scale).")
    lines.append("8. **Currency alignment**: TSM/ASX report in TWD and ASML in EUR while their ADR "
                  "market caps are USD. TTM revenue and net debt for those names are converted to USD "
                  "at the SPOT FX rate on the run date (rate shown in the Source column) -- a spot "
                  "conversion of a trailing-12m flow is itself an approximation, and FX moves add noise "
                  "to their P_base that USD names don't have. (The first draft of this run SKIPPED this "
                  "conversion and produced garbage for all three -- e.g. TSM P_base of -200x -- which is "
                  "why the check exists.)")
    lines.append("9. Raw EV/market-cap/margin inputs are a SNAPSHOT as of the day this script was run; "
                  "re-running later will move the numbers (that's the point -- re-run to check whether "
                  "the expectations gap has closed or widened).")
    lines.append("")

    lines.append("## Special-focus commentary (5 tickers)")
    lines.append("")
    by_sym = {r["ticker"]: r for r in ok_rows}

    # USAC
    r = by_sym.get("USAC")
    lines.append("### USAC — thesis claims \"cheapest / most-undiscovered\" in the gas-compression theme")
    lines.append("")
    if r:
        lines.append(f"P_base@14x = **{_fmt_mult(r.get('p_14x'))}**, classification = "
                      f"**{r['classification']}**, EBIT margin(median) = {_fmt_pct(r['ebit_margin_median'])}, "
                      f"g_implied = {_fmt_pct(r.get('g_implied'))}, {r['n_quarters']}q data.")
        lines.append("")
        lines.append("`thesis/themes.yaml` flags USAC at the **2nd percentile** of its own 3y ttm_pe "
                      "history (~27.1x) — \"全批候選入面估值最平\" (cheapest across the whole candidate "
                      "batch), i.e. a MULTIPLE-based (relative-to-own-history) cheap read. "
                      + (f"This P_base reading PARTLY confirms that framing: {_fmt_pct(r.get('p_14x'), 0)} "
                         f"of USAC's EV is covered by normalized operating earnings at a cycle-agnostic "
                         f"14x NOPAT (full coverage would need ~{(1/(r.get('p_14x') or 1))*14:.0f}x), which "
                         f"puts it in the top tier of the supercycle-thesis names in this table -- so "
                         f"\"cheapest in the batch\" holds RELATIVELY. But note it is NOT the cheapest here "
                         f"in absolute coverage terms (AVT/FSLR/LPX/XOM/CVX all print higher P_base), and "
                         f"its balance sheet does the heavy lifting: net debt {_fmt_usd(r['net_debt'])} vs "
                         f"{_fmt_usd(r['market_cap'])} market cap means most of the EV is debt -- the "
                         f"equity is a leveraged slice of a well-covered asset, not a bargain on an "
                         f"unlevered basis."
                         if (r.get("p_14x") or 0) >= 0.4 else
                         "This P_base reading is LESS supportive than the ttm_pe-percentile framing suggests "
                         "-- own-history PE being at a 3y low can just mean the whole SECTOR de-rated, not "
                         "that the absolute earnings-power coverage is strong. Worth reconciling the two "
                         "reads before leaning on \"cheapest in the batch\" as the full story."))
    else:
        lines.append("Data unavailable -- see failed-tickers list above.")
    lines.append("")

    # FSLR
    r = by_sym.get("FSLR")
    lines.append("### FSLR — 22nd percentile own-history ttm_pe")
    lines.append("")
    if r:
        lines.append(f"P_base@14x = **{_fmt_mult(r.get('p_14x'))}**, classification = "
                      f"**{r['classification']}**, EBIT margin(median) = {_fmt_pct(r['ebit_margin_median'])}, "
                      f"g_implied = {_fmt_pct(r.get('g_implied'))}, {r['n_quarters']}q data.")
        lines.append("")
        lines.append("A 22nd-percentile ttm_pe (cheap-ish vs FSLR's own trading history) lines up "
                      + ("with a P_base that also shows meaningful supercycle-free coverage -- the market "
                         "isn't demanding much US-solar-manufacturing-thesis growth to justify today's EV; "
                         "the base business (IRA-protected US module pricing) covers a large chunk of it "
                         "on its own." if (r.get("p_14x") or 0) >= 0.4 else
                         "with a P_base showing LESS coverage than the cheap-multiple read implies -- most "
                         "of FSLR's EV still requires the thesis (US manufacturing tariff/IRA moat holding) "
                         "to keep delivering, not just a mean-reversion-in-multiple trade."))
    else:
        lines.append("Data unavailable -- see failed-tickers list above.")
    lines.append("")

    # ASML
    r = by_sym.get("ASML")
    lines.append("### ASML — 98th percentile own-history ttm_pe (\"most-discussed semiconductor monopoly story\")")
    lines.append("")
    if r:
        g = r.get("g_implied")
        lines.append(f"P_base@14x = **{_fmt_mult(r.get('p_14x'))}**, classification = "
                      f"**{r['classification']}**, EBIT margin(median) = {_fmt_pct(r['ebit_margin_median'])}, "
                      f"g_implied = **{_fmt_pct(g)}** (5yr), {r['n_quarters']}q data.")
        lines.append("")
        if g is not None and g > 0.15:
            lines.append(f"Yes — g_implied of {_fmt_pct(g)}/yr for 5 years is a demanding growth ask on top "
                          f"of an already-elevated base, consistent with the 98th-percentile ttm_pe: the "
                          f"EUV-monopoly narrative is fully in the price, and P_base confirms it -- only a "
                          f"{_fmt_pct(r.get('p_14x'), 0)} slice of EV is covered by normalized (non-growing) "
                          f"earnings power, the rest is a bet that ASML keeps compounding at a rate few "
                          f"monopoly franchises sustain for half a decade.")
        elif g is not None:
            lines.append(f"g_implied of {_fmt_pct(g)}/yr is more moderate than the 98th-percentile ttm_pe "
                          f"headline suggests -- worth checking whether the multiple extreme is being driven "
                          f"by a temporarily depressed E_norm (cyclical trough in the EUV/lithography "
                          f"capex cycle) rather than by outright growth over-payment.")
        else:
            lines.append("g_implied is undefined (NOPAT_norm <= 0) -- see N/A-binary note in caveats.")
    else:
        lines.append("Data unavailable -- see failed-tickers list above.")
    lines.append("")

    # ATI
    r = by_sym.get("ATI")
    lines.append("### ATI — 98th percentile own-history ttm_pe (aerospace specialty alloys)")
    lines.append("")
    if r:
        g = r.get("g_implied")
        lines.append(f"P_base@14x = **{_fmt_mult(r.get('p_14x'))}**, classification = "
                      f"**{r['classification']}**, EBIT margin(median) = {_fmt_pct(r['ebit_margin_median'])}, "
                      f"g_implied = **{_fmt_pct(g)}** (5yr), {r['n_quarters']}q data.")
        lines.append("")
        if g is not None and g > 0.15:
            lines.append(f"Yes, similarly demanding: {_fmt_pct(g)}/yr implied growth backs up the "
                          f"98th-percentile ttm_pe read -- the aerospace-supply-chain-tightness thesis "
                          f"(narrowbody build-rate ramp, titanium/specialty-alloy bottleneck) has to keep "
                          f"delivering above-trend growth for 5 more years just to justify the current EV "
                          f"at a cycle-neutral 14x multiple; P_base of {_fmt_mult(r.get('p_14x'))} means "
                          f"the bulk of the price is that forward bet, not today's normalized earnings.")
        elif g is not None:
            lines.append(f"g_implied of {_fmt_pct(g)}/yr is more moderate than the 98th-percentile ttm_pe "
                          f"headline alone would suggest -- worth reconciling against whether E_norm is "
                          f"itself temporarily depressed.")
        else:
            lines.append("g_implied is undefined (NOPAT_norm <= 0) -- see N/A-binary note in caveats.")
    else:
        lines.append("Data unavailable -- see failed-tickers list above.")
    lines.append("")

    # MU
    r = by_sym.get("MU")
    lines.append("### MU — TTM revenue at cycle peak (worked example of the E_norm inflation bias)")
    lines.append("")
    if r:
        lines.append(f"P_base@14x = **{_fmt_mult(r.get('p_14x'))}**, classification = "
                      f"**{r['classification']}**, EBIT margin(median) = {_fmt_pct(r['ebit_margin_median'])}, "
                      f"TTM revenue = {_fmt_usd(r['ttm_revenue'])}, g_implied = {_fmt_pct(r.get('g_implied'))}, "
                      f"{r['n_quarters']}q data.")
        lines.append("")
        lines.append("`thesis/themes.yaml` flags MU's `cycle_stage` as **late** with capex at 2.66x — a "
                      "supply-response signal that a memory upcycle is maturing. MU's TTM revenue "
                      f"({_fmt_usd(r['ttm_revenue'])}) is running near the TOP of its own multi-year range "
                      "(the most recent quarters carry the heaviest weight in a trailing-12m sum), so "
                      "E_norm = median_margin x TTM_revenue is being multiplied by a CYCLICALLY ELEVATED "
                      "revenue base even though the margin term is itself median-smoothed across the cycle. "
                      "**How to read this**: P_base as computed here is a BEST-CASE / upper-bound "
                      "supercycle-free coverage reading for MU specifically -- if TTM revenue mean-reverts "
                      "down toward a mid-cycle level (as it did in the 2022-2023 memory downturn, visible "
                      "in the same quarterly series used above), true E_norm and hence true P_base would be "
                      "LOWER than what's printed in the table. Do not read MU's P_base at face value the way "
                      "you would for a name with a flatter revenue history (e.g. XOM, ASML) -- it embeds "
                      "this peak-revenue bias by construction.")
    else:
        lines.append("Data unavailable -- see failed-tickers list above.")
    lines.append("")

    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    run()
