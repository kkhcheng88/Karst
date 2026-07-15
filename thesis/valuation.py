"""thesis/valuation.py — Expectations-gap valuation, v1 (production).

Production version of `backtest/experiments/exp_expectations_gap_v0.py` (that script stays
UNTOUCHED as the historical record of the 2026-07-12 one-off run -- see its own docstring for the
full Mauboussin "expectations investing" framing). Spec: `docs/2026-07-12_valuation_expectations_gap_
spec.md` Sec3a. Motivation: v0 was a one-off snapshot both `thesis/dashboard_render.py` and
`thesis/paper_ledger.py` read from a frozen markdown file; this makes the pipeline re-runnable and
fixes v0's own documented cycle-top bias.

The three core readings (unchanged from v0):
  E_norm      = normalized ("the business isn't dreaming") operating earning power
  P_base@14x  = supercycle-free coverage: how much of today's EV a boring, non-growing business
                already justifies at a cycle-neutral 14x NOPAT (also reported @10x/18x)
  g_implied   = the 5yr growth rate the market is pricing in on top of that normalized base

v0 -> v1: THE ONLY METHODOLOGY CHANGE
--------------------------------------
E_norm = median(quarterly Operating Income / Total Revenue) x <revenue term>. v0's revenue term was
raw TTM revenue -- v0's own caveat #3 flagged that this inflates E_norm (and hence P_base) for any
name whose TTM revenue is itself sitting at a CYCLE PEAK (MU was the worked example: TTM revenue
near the top of its own multi-year range even though the margin term is median-smoothed).

v1's revenue term = min(TTM revenue, 3-year median revenue), i.e. the CONSERVATIVE of the two:
  - "3-year median revenue" = median(quarterly revenue over the most recent min(12, available)
    quarters) x 4 -- the same "median across available quarters" idiom v0 already uses for the
    margin term, applied here to revenue instead.
  - At a CYCLE PEAK (TTM > 3yr median) the lower 3yr-median figure wins -> E_norm is damped exactly
    where v0 flagged the bias.
  - At a trough or flat revenue history (TTM <= 3yr median) TTM wins UNCHANGED -- v1 can only ever
    be equal to or MORE conservative than v0, never less.
  - The spec's own wording ("TTM 同 3 年平均取中位") does not nail an unambiguous formula (it could
    also mean "median of {TTM, 3yr average}", a two-point median that just re-derives the average).
    This min() choice is the documented fallback the production task brief specified when the spec
    text alone doesn't fully pin the formula: simple, monotonically conservative, and directionally
    correct on the one case the spec calls out (MU).
Everything else -- NOPAT, EV, P_base@10/14/18x, g_implied, classification thresholds, defeatbeta-
first/yfinance-fallback data path, FX handling for non-USD reporters -- is copied from v0 unchanged.

Universe
--------
Read LIVE from `thesis/themes.yaml` (NOT a hardcoded snapshot like v0): for each active theme, its
top `TOP_N_PER_THEME` (=2) tickers from the theme's `tickers:` list, in list order -- this is v0's
own "top 1-2 expressive tickers per theme" selection logic, reproduced dynamically so it doesn't go
stale as themes.yaml evolves. Verified 2026-07-13: themes.yaml's 15 active themes' `tickers:` lists
still produce the IDENTICAL 24-ticker set v0 hardcoded. Plus the same 4 WATCH-only names v0 used
(KALU/MCHP/AVT/PTEN, discovery-radar candidates not yet promoted into a theme) -- there is no
machine-readable WATCH registry in themes.yaml, only a prose comment at the file's bottom ("2026-07-11
discovery radar 40候選"), so this list is carried forward by hand; update WATCH below if that comment
changes.

Outputs
-------
1. `thesis/.raw/valuation_report.json` -- machine-readable, gitignored (regenerable by re-running).
   Per-ticker block + `theme_rollup` (slug -> {best_ticker, p_base, classification}, field names
   matching what `dashboard_render.load_expectations_gap()` / `paper_ledger.load_expectations_gap()`
   already read out of the markdown table, so a future JSON-native reader needs no field remapping).
2. `backtest/results/<date>_expectations_gap_v1.md` -- human-readable, v0-format-compatible: same
   "## Theme-level rollup (N active themes)" section header + `| slug | ticker | P.PPx | classification |`
   row shape v0 used, so `dashboard_render.py`'s EXPGAP_ROW_RE keeps parsing it unmodified.

   ****KNOWN GAP, READ BEFORE ASSUMING THIS "JUST WORKS"****: both `dashboard_render.py` and
   `paper_ledger.py` DISCOVER the latest report via `glob.glob(".../*_expectations_gap_v0.md")` --
   a glob hardcoded to the "_v0.md" suffix. A file named "..._expectations_gap_v1.md" (per this
   task's naming brief) will NOT be picked up by that glob. The row-level REGEX is unaffected (it's
   format-compatible, verified by direct test), but end-to-end auto-discovery is not, until someone
   widens those two globs to "*_expectations_gap_v*.md" -- both files are explicitly out of scope
   for this task ("唔改 dashboard_render.py/paper_ledger.py"), so that widening is a deliberate
   follow-up, not done here. Until then, v0's frozen 2026-07-12 file remains what those two scripts
   actually read.

CLI
---
  python thesis/valuation.py --run           compute the full universe; write both outputs above.
  python thesis/valuation.py --compare-v0    print + report a per-ticker v0-vs-v1 classification
                                              diff table (which tickers moved bucket + why). Loads
                                              the just-computed rows if combined with --run, else
                                              re-reads the last --run's JSON.
  python thesis/valuation.py --run --compare-v0    does both; the diff table is ALSO embedded in the
                                              v1 markdown report (conclusions get filed, not just
                                              printed).

Schedule: see `thesis/weekly_valuation.cmd` (WEEKLY cadence, mirrors thesis/weekly_risk_check.cmd's
cost profile; the spec's own recommendation is quarterly-is-enough since valuation isn't an intraday
signal, but weekly costs nothing extra to run and stays fresher). NOT registered as a scheduled task
here -- the .cmd documents (but does not execute) the schtasks registration command.
"""
from __future__ import annotations

import argparse
import contextlib
import glob
import io
import json
import os
import re
import sys
from datetime import date

import numpy as np
import pandas as pd
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))            # thesis/
REPO_ROOT = os.path.dirname(ROOT)                              # Karst/
sys.path.insert(0, REPO_ROOT)

with contextlib.redirect_stdout(io.StringIO()):
    from defeatbeta_api.data.ticker import Ticker

import yfinance as yf

THEMES_PATH = os.path.join(ROOT, "themes.yaml")
RAW_DIR = os.path.join(ROOT, ".raw")
JSON_OUT = os.path.join(RAW_DIR, "valuation_report.json")
RESULTS_DIR = os.path.join(REPO_ROOT, "backtest", "results")
V0_GLOB = os.path.join(RESULTS_DIR, "*_expectations_gap_v0.md")
SPEC_DOC = "docs/2026-07-12_valuation_expectations_gap_spec.md"

TAX_RATE = 0.21
MULTIPLES = (10, 14, 18)
BASE_MULT = 14
WACC = 0.10
HORIZON = 5
MIN_QUARTERS_OK = 12
REV_WINDOW_Q = 12    # "3-year median revenue" window = 12 quarterly columns (v1's only new knob)

# ---- solvency gate reading (2026-07-15) --------------------------------------------------
# 判決:backtest/results/2026-07-15_solvency_gate_probe.md -- GO-as-gate(條件版:solvency 單獨
# 冇跑輸料,但「pe 平 ∧ solvency 爆」126d excess -14.9% vs pe_low alone -2.9%;「solvency 爆但
# 唔平」+3.9% = 無條件 gate 會錯殺,USAC 後來 +67.6% 就係錯殺面證據)。所以呢度只讀數 + 旗標,
# 唔喺 valuation 呢層做否決——真正嘅「只對 pe-cheap 候選降級」邏輯喺
# thesis/dashboard_render.py 嘅 pick_ticker(揀 ticker 嗰步)先做。
LEV_BAD = 4.0   # NetDebt(手動重構) / EBITDA(TTM) > 4x -- 槓桿爆錶閾值
COV_BAD = 2.0   # EBIT / 利息支出(TTM) < 2x -- 利息覆蓋唔夠閾值

TOP_N_PER_THEME = 2  # v0's ticker-selection logic: first 1-2 tickers per theme's `tickers:` list
WATCH = ["KALU", "MCHP", "AVT", "PTEN"]  # v0's 4 WATCH-only names -- see module docstring

_FX_CACHE: dict = {}


# ============================================================================
# fetch helpers -- ported from exp_expectations_gap_v0.py (v0 itself stays untouched); the ONLY
# behavioural addition here is also returning a quarterly revenue WINDOW for the 3yr-median calc.
# ============================================================================


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


def _median_annualized(values: list) -> float:
    """median(values) x 4 -- annualizes a set of quarterly figures via their median quarter,
    mirroring the median-margin idiom already used elsewhere in this module."""
    return float(np.median(values)) * 4.0


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

    # v1 addition: 3-year median revenue window (see module docstring "v0 -> v1" section).
    rev_window_vals = [rev[c] for c in period_cols[:REV_WINDOW_Q] if rev.get(c) is not None]
    n_rev_window = len(rev_window_vals)
    median_revenue_3y = _median_annualized(rev_window_vals) if rev_window_vals else None

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

    fin_cur = _fin_currency(sym)
    fx = _fx_to_usd(fin_cur)
    src = "defeatbeta" if fin_cur == "USD" else f"defeatbeta ({fin_cur}→USD @{fx:.4f})"

    return {
        "ebit_margin_median": ebit_margin_median,
        "ttm_revenue": ttm_rev * fx,
        "median_revenue_3y": (median_revenue_3y * fx) if median_revenue_3y is not None else None,
        "n_rev_window": n_rev_window,
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
    rev = {c: _num(qf.loc["Total Revenue", c]) for c in period_cols}
    oi = {c: _num(qf.loc["Operating Income", c]) for c in period_cols}
    margins = []
    for c in period_cols:
        r, o = rev.get(c), oi.get(c)
        if r is not None and o is not None and r > 0:
            margins.append(o / r)
    n_quarters = len(margins)
    if n_quarters == 0:
        raise RuntimeError("no usable yfinance quarterly margin data")
    ebit_margin_median = float(np.median(margins))

    recent4 = [rev.get(c) for c in period_cols[:4]]
    recent4 = [v for v in recent4 if v is not None]
    if len(recent4) < 4:
        raise RuntimeError("yfinance <4 quarters revenue for TTM")
    ttm_rev = sum(recent4)

    rev_window_vals = [rev[c] for c in period_cols[:REV_WINDOW_Q] if rev.get(c) is not None]
    n_rev_window = len(rev_window_vals)
    median_revenue_3y = _median_annualized(rev_window_vals) if rev_window_vals else None

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
        "median_revenue_3y": (median_revenue_3y * fx) if median_revenue_3y is not None else None,
        "n_rev_window": n_rev_window,
        "net_debt": net_debt * fx,
        "market_cap": market_cap,
        "n_quarters": n_quarters,
        "bs_date": str(pd.Timestamp(latest_bs).date()),
        "fin_currency": fin_cur,
        "source": src,
    }


# ============================================================================
# solvency gate reading -- fetch logic ported from
# backtest/experiments/exp_solvency_gate_probe.py (_quarterly_frame/_annual_frame), the probe
# whose judgement this wiring implements (see LEV_BAD/COV_BAD comment above). Quarterly TTM
# preferred; annual fiscal-year figures fill whatever quarterly leg is thin/unavailable. This
# is a WEEKLY SNAPSHOT (latest reading only), not a backtest time series.
# ============================================================================


def _is_financial_sector(sym: str) -> bool:
    """銀行/保險:NetDebt/EBITDA 同利息覆蓋對佢哋無意義(2026-07-15 探測 v1 run JPM/MTG 正正
    咁樣炸,設計上剔除)。用 yfinance sector/industry 判斷,攞唔到就唔當金融股(fail-open,
    唔靜默剔除非金融名)。"""
    try:
        info = yf.Ticker(sym).info
    except Exception:
        return False
    sector = (info.get("sector") or "").lower()
    industry = (info.get("industry") or "").lower()
    return "financial" in sector or "bank" in industry or "insurance" in industry


def _getdf(obj):
    """`net_debt_ttm()`/`ttm_ebitda()`/`debt_to_equity()` 喺呢個 defeatbeta_api 版本已經直接
    返回 DataFrame(冇 `.df()`),但 `quarterly_income_statement()`/`annual_*_statement()` 返回
    有 `.df()` 嘅 Statement object——兩種都要頂到,唔可以假設淨係一種(同
    exp_solvency_gate_probe.py 嘅 `_getdf` 一致)。"""
    return obj.df() if hasattr(obj, "df") else obj


def _wide_to_tidy(wide_df: pd.DataFrame, rows_wanted: list) -> pd.DataFrame:
    """defeatbeta income/balance-sheet表係 WIDE 格式(Breakdown 欄 + 逐期末日期欄,損益表仲有個
    TTM 欄)。跟 exp_solvency_gate_probe.py 原式照抄:tidy 成逐 period_end 一行、逐個要嘅
    row 一個 float 欄;缺行 -> NaN 欄;masked '*' 格 -> NaN。"""
    sub = wide_df[wide_df["Breakdown"].isin(rows_wanted)].drop_duplicates("Breakdown")
    sub = sub.set_index("Breakdown").reindex(rows_wanted)
    cols = [c for c in sub.columns if c != "TTM"]
    out = sub[cols].T
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def _solvency_reading(sym: str) -> dict:
    """NetDebt/EBITDA + 利息覆蓋嘅最新讀數(週更 snapshot,唔係回測時間序列)。
    返回 net_debt_ebitda / interest_coverage / solvency_flag / solvency_reason 四個欄位;
    攞唔到嘅數 = None,唔造假。金融股:flag=None + reason(跳過,唔評估)。"""
    out = {"net_debt_ebitda": None, "interest_coverage": None,
           "solvency_flag": None, "solvency_reason": None}
    if _is_financial_sector(sym):
        out["solvency_reason"] = "金融股(銀行/保險)跳過——NetDebt/EBITDA 同利息覆蓋對佢哋無意義"
        return out

    net_debt = ebitda = ebit = int_exp = None
    with contextlib.redirect_stdout(io.StringIO()):
        t = Ticker(sym)
        # ---- quarterly TTM leg: net debt (手動重構) / EBITDA ----
        try:
            nd = _getdf(t.net_debt_ttm()).sort_values("report_date")
            d2e = _getdf(t.debt_to_equity()).sort_values("report_date")
            eb = _getdf(t.ttm_ebitda()).sort_values("report_date")
            cash = _num(nd.iloc[-1].get("cash_and_short_term_investments")) if len(nd) else None
            total_debt = _num(d2e.iloc[-1].get("total_debt")) if len(d2e) else None
            if cash is not None and total_debt is not None:
                net_debt = total_debt - cash
            if len(eb):
                ebitda = _num(eb.iloc[-1].get("ttm_ebitda_usd"))
        except Exception:
            pass
        # ---- quarterly TTM leg: EBIT / 利息支出(季度滾存 4 季) ----
        try:
            inc = t.quarterly_income_statement().df()
            tidy = _wide_to_tidy(inc, ["EBIT", "Interest Expense"])
            ebit_ttm = tidy["EBIT"].rolling(4, min_periods=4).sum().dropna()
            int_ttm = tidy["Interest Expense"].rolling(4, min_periods=4).sum().dropna()
            if len(ebit_ttm):
                ebit = float(ebit_ttm.iloc[-1])
            if len(int_ttm):
                int_exp = float(int_ttm.iloc[-1])
        except Exception:
            pass
        # ---- annual fallback:補返季度攞唔到嘅任何一條腿(史淺名/季度表冧咗) ----
        if net_debt is None or ebitda is None or ebit is None or int_exp is None:
            try:
                abs_ = t.annual_balance_sheet().df()
                ais = t.annual_income_statement().df()
                bs_t = _wide_to_tidy(abs_, ["Total Debt",
                    "Cash, Cash Equivalents & Short Term Investments"])
                is_t = _wide_to_tidy(ais, ["EBIT", "EBITDA", "Interest Expense"])
                if net_debt is None and len(bs_t):
                    last = bs_t.iloc[-1]
                    td = _num(last.get("Total Debt"))
                    csti = _num(last.get("Cash, Cash Equivalents & Short Term Investments"))
                    if td is not None and csti is not None:
                        net_debt = td - csti
                if ebitda is None and len(is_t):
                    ebitda = _num(is_t.iloc[-1].get("EBITDA"))
                if ebit is None and len(is_t):
                    ebit = _num(is_t.iloc[-1].get("EBIT"))
                if int_exp is None and len(is_t):
                    int_exp = _num(is_t.iloc[-1].get("Interest Expense"))
            except Exception:
                pass

    if ebitda is not None and ebitda > 0 and net_debt is not None:
        out["net_debt_ebitda"] = net_debt / ebitda
    if int_exp is not None and int_exp > 0 and ebit is not None:
        out["interest_coverage"] = ebit / int_exp

    has_any = ebitda is not None or (ebit is not None and int_exp is not None)
    if not has_any:
        out["solvency_reason"] = "攞唔到 EBITDA/EBIT/利息支出數據,solvency 讀數缺席"
        return out

    lev_bad = (ebitda is not None and ebitda <= 0) or (
        out["net_debt_ebitda"] is not None and out["net_debt_ebitda"] > LEV_BAD)
    cov_bad = (int_exp is not None and int_exp > 0 and ebit is not None and ebit <= 0) or (
        out["interest_coverage"] is not None and out["interest_coverage"] < COV_BAD)
    out["solvency_flag"] = bool(lev_bad or cov_bad)
    return out


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

    # ---- v1's one methodology change: conservative revenue term ----
    ttm_rev = d["ttm_revenue"]
    med_rev = d.get("median_revenue_3y")
    if med_rev is not None and med_rev > 0:
        if ttm_rev <= med_rev:
            revenue_used = ttm_rev
            revenue_basis = "TTM (already <= 3yr median; no damping needed)"
        else:
            damp_pct = (ttm_rev / med_rev - 1) * 100
            revenue_used = med_rev
            revenue_basis = f"3yr median (damped; TTM was {damp_pct:.0f}% above 3yr median)"
    else:
        revenue_used = ttm_rev
        revenue_basis = "TTM (3yr median unavailable -- too few revenue-window quarters)"
    row["revenue_used"] = revenue_used
    row["revenue_basis"] = revenue_basis

    e_norm = d["ebit_margin_median"] * revenue_used
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

    # ---- solvency gate reading (2026-07-15,見 LEV_BAD/COV_BAD 註解) ----
    # 獨立於上面 valuation 嘅 try/except:一個 ticker 嘅 solvency 讀取失敗唔應該累到成個
    # valuation row 都跟住報錯(兩者數據來源部分重疊但唔係同一條 fetch 路徑)。
    try:
        row.update(_solvency_reading(sym))
    except Exception as e:
        row.update({"net_debt_ebitda": None, "interest_coverage": None, "solvency_flag": None,
                    "solvency_reason": f"solvency 讀取失敗: {str(e)[:90]}"})
    return row


# ============================================================================
# universe
# ============================================================================


def load_universe():
    """Live read of thesis/themes.yaml -- see module docstring. Returns
    (ticker -> [theme_slug, ...], [theme_slug in themes.yaml order])."""
    with open(THEMES_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    themes = data.get("themes", {}) or {}
    theme_order = list(themes.keys())
    ticker_themes: dict = {}
    for slug, t in themes.items():
        tks = (t or {}).get("tickers") or []
        for tk in tks[:TOP_N_PER_THEME]:
            ticker_themes.setdefault(str(tk), []).append(slug)
    for tk in WATCH:
        ticker_themes.setdefault(tk, []).append("WATCH")
    return ticker_themes, theme_order


# ============================================================================
# formatting
# ============================================================================


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


# ============================================================================
# theme rollup (shared by JSON + MD writers) -- SAME "best ticker's P_base@14x" logic as v0
# ============================================================================


def build_theme_rollup(ok_rows, theme_order):
    by_slug_rows = {}
    for r in ok_rows:
        for slug in r["themes"]:
            by_slug_rows.setdefault(slug, []).append(r)
    rollup = {}
    for slug in theme_order:
        t_rows = by_slug_rows.get(slug, [])
        if not t_rows:
            rollup[slug] = {"best_ticker": None, "p_base": None, "classification": "N/A (no data)"}
            continue
        pos = [r for r in t_rows if (r.get("e_norm") or 0) > 0 and r.get("p_14x") is not None]
        if not pos:
            best = max(t_rows, key=lambda r: r.get("p_14x") if r.get("p_14x") is not None else -999)
            rollup[slug] = {"best_ticker": best["ticker"], "p_base": best.get("p_14x"),
                             "classification": "N/A-binary (option framing)"}
            continue
        best = max(pos, key=lambda r: r["p_14x"])
        pb = best["p_14x"]
        cls = ("supercycle 白送" if pb >= 0.8 else
               "買緊部分希望" if pb >= 0.4 else
               "大部分係希望")
        rollup[slug] = {"best_ticker": best["ticker"], "p_base": pb, "classification": cls}
    return rollup


# ============================================================================
# v0 baseline parsing (for --compare-v0) -- v0's file format is frozen/historical, parsed here
# read-only; exp_expectations_gap_v0.py itself is never touched.
# ============================================================================


def parse_v0_full_table():
    """{ticker: classification} from the latest backtest/results/*_expectations_gap_v0.md FULL
    table (ticker-level, not the theme rollup -- diffing needs per-ticker granularity). Returns
    ({}, None) if no v0 report exists."""
    matches = sorted(glob.glob(V0_GLOB))
    if not matches:
        return {}, None
    path = matches[-1]
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    m = re.search(r"## Full table.*?\n\n(.*?)(?:\n##\s|\Z)", text, re.DOTALL)
    if not m:
        return {}, os.path.basename(path)
    block = m.group(1)
    lines = [ln for ln in block.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return {}, os.path.basename(path)
    header_cells = [c.strip() for c in lines[0].strip().strip("|").split("|")]
    if "Ticker" not in header_cells or "Classification" not in header_cells:
        return {}, os.path.basename(path)
    tk_idx = header_cells.index("Ticker")
    cls_idx = header_cells.index("Classification")
    out = {}
    for ln in lines[2:]:  # skip header row + markdown separator row
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) <= max(tk_idx, cls_idx):
            continue
        tk = cells[tk_idx].replace("*", "").strip()
        cls = cells[cls_idx].strip()
        if tk:
            out[tk] = cls
    return out, os.path.basename(path)


def compute_diff(ok_rows, v0_map):
    """Per-ticker classification changes v0 -> v1. Includes an honesty check: if a ticker's
    revenue_basis shows the 3yr-median damp did NOT fire, a classification change can't be
    attributed to the v1 formula change -- flag it as 'market-move' (EV/price moved between the
    v0 snapshot date and today) rather than silently implying the revenue fix caused it."""
    diffs = []
    for r in ok_rows:
        tk = r["ticker"]
        v0_cls = v0_map.get(tk)
        v1_cls = r.get("classification")
        if v0_cls is None or v0_cls == v1_cls:
            continue
        damped = "damped" in (r.get("revenue_basis") or "")
        reason = ("revenue term now min(TTM, 3yr median) -- damps cycle-peak E_norm inflation"
                  if damped else
                  "NOT explained by the revenue-conservatism change (3yr median wasn't binding for "
                  "this ticker) -- likely reflects market/price movement between the v0 snapshot "
                  "date and today, not the v0->v1 formula change")
        diffs.append({"ticker": tk, "v0": v0_cls, "v1": v1_cls,
                       "revenue_basis": r.get("revenue_basis"), "reason": reason})
    return diffs


# ============================================================================
# writers
# ============================================================================


def write_json(rows, ok_rows, fail_rows, theme_order, today):
    tickers_out = {}
    for r in ok_rows:
        tickers_out[r["ticker"]] = {
            "themes": r["themes"],
            "ebit_margin_median": r.get("ebit_margin_median"),
            "ttm_revenue": r.get("ttm_revenue"),
            "median_revenue_3y": r.get("median_revenue_3y"),
            "n_rev_window_quarters": r.get("n_rev_window"),
            "revenue_used": r.get("revenue_used"),
            "revenue_basis": r.get("revenue_basis"),
            "e_norm": r.get("e_norm"),
            "nopat_norm": r.get("nopat_norm"),
            "net_debt": r.get("net_debt"),
            "market_cap": r.get("market_cap"),
            "ev": r.get("ev"),
            "p_10x": r.get("p_10x"),
            "p_base": r.get("p_14x"),
            "p_18x": r.get("p_18x"),
            "g_implied": r.get("g_implied"),
            "classification": r.get("classification"),
            "net_debt_ebitda": r.get("net_debt_ebitda"),
            "interest_coverage": r.get("interest_coverage"),
            "solvency_flag": r.get("solvency_flag"),
            "solvency_reason": r.get("solvency_reason"),
            "n_quarters": r.get("n_quarters"),
            "fin_currency": r.get("fin_currency"),
            "bs_date": r.get("bs_date"),
            "source": r.get("source") + (" (yfinance fallback)" if r.get("fallback_reason") else ""),
        }
    theme_rollup = build_theme_rollup(ok_rows, theme_order)
    payload = {
        "as_of": today,
        "method": "v1",
        "spec": SPEC_DOC,
        "base_multiple": BASE_MULT,
        "multiples": list(MULTIPLES),
        "wacc": WACC,
        "horizon_years": HORIZON,
        "rev_window_quarters": REV_WINDOW_Q,
        "v0_to_v1_change": ("E_norm revenue term = min(TTM revenue, 3yr median revenue) instead of "
                             "raw TTM revenue -- damps the cycle-top inflation bias v0 flagged."),
        "tickers": tickers_out,
        "theme_rollup": theme_rollup,
        "watch_only": WATCH,
        "failed": {r["ticker"]: r["error"] for r in fail_rows},
        "n_ok": len(ok_rows),
        "n_total": len(rows),
    }
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(JSON_OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, default=str)
    return JSON_OUT


def write_md(rows, ok_rows, fail_rows, theme_order, today, diffs, v0_file):
    ranked = sorted(ok_rows, key=lambda r: (r.get(f"p_{BASE_MULT}x") is None,
                                             -(r.get(f"p_{BASE_MULT}x") or -999)))
    n_mostly_hope = sum(1 for r in ok_rows if r["classification"] == "大部分係希望")
    n_partial = sum(1 for r in ok_rows if r["classification"] == "買緊部分希望")
    n_free = sum(1 for r in ok_rows if r["classification"] == "supercycle 白送")
    n_binary = sum(1 for r in ok_rows if r["classification"] == "N/A-binary (option framing)")
    fb_rows = [r for r in ok_rows if r.get("fallback_reason")]
    thin_rows = [r for r in ok_rows if r["n_quarters"] < MIN_QUARTERS_OK]

    lines = []
    lines.append(f"# Expectations-Gap Valuation v1 — {today}")
    lines.append("")
    lines.append("Script: `thesis/valuation.py` (`python thesis/valuation.py --run`). Production "
                  "version of `backtest/experiments/exp_expectations_gap_v0.py` "
                  f"(2026-07-12 one-off run, kept as historical record). Spec: `{SPEC_DOC}`.")
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
    lines.append("## Method (v1)")
    lines.append("")
    lines.append("```")
    lines.append("revenue_term = min(TTM revenue, 3yr median revenue)      <- v1's ONLY change vs v0")
    lines.append("3yr median revenue = median(quarterly revenue, most recent min(12,available) qtrs) x 4")
    lines.append("E_norm      = median(quarterly Operating Income / Total Revenue) x revenue_term")
    lines.append("NOPAT_norm  = E_norm x (1 - 0.21)")
    lines.append("EV          = market_cap + net_debt   (net_debt = Total Debt - Cash&STI, latest quarter)")
    lines.append("P_base      = NOPAT_norm x 14 / EV     (also reported @ 10x / 18x)")
    lines.append("g_implied   = ((EV x 1.10^5) / (14 x NOPAT_norm)) ^ (1/5) - 1")
    lines.append("```")
    lines.append("")
    lines.append("**v0 -> v1 change (the only one):** v0 used raw TTM revenue in E_norm, which v0's "
                  "own caveats flagged as inflated for any name whose TTM revenue sits at a cycle peak "
                  "(worked example: MU). v1 takes the CONSERVATIVE of TTM vs. a 3-year median revenue "
                  "-- at a cycle peak the lower 3yr-median wins (damped); at a trough or flat history "
                  "TTM wins unchanged. v1 can only be equal to or MORE conservative than v0, never less.")
    lines.append("")
    lines.append("Classification: P_base>=0.8 \"supercycle 白送\" / 0.4-0.8 \"買緊"
                  "部分希望\" / <0.4 \"大部分係希望\" / "
                  "E_norm<=0 \"N/A-binary (option framing)\".")
    lines.append("")
    lines.append(f"Universe: top {TOP_N_PER_THEME} expressive tickers per active theme, read LIVE from "
                  "`thesis/themes.yaml` (not a hardcoded snapshot) + 4 WATCH-only names "
                  f"({', '.join(WATCH)}).")
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
    thin_desc = ", ".join(f"{r['ticker']}({r['n_quarters']}q)" for r in thin_rows) if thin_rows else "none"
    lines.append(f"- {len(thin_rows)} ticker(s) have <{MIN_QUARTERS_OK} quarters of margin data ({thin_desc}).")
    damped = [r for r in ok_rows if "damped" in (r.get("revenue_basis") or "")]
    damped_desc = ", ".join(r["ticker"] for r in damped) if damped else "none"
    lines.append(f"- {len(damped)} ticker(s) had the v1 cycle-peak damp actually BIND "
                  f"(3yr-median revenue < TTM revenue, so v1's revenue term is lower than v0's would be): "
                  f"{damped_desc}.")
    if fail_rows:
        lines.append(f"- FAILED (0 usable data, both sources): "
                      f"{', '.join(r['ticker'] for r in fail_rows)}.")
    lines.append("")

    lines.append(f"## Theme-level rollup ({len(theme_order)} active themes)")
    lines.append("")
    lines.append("A theme's reading = the BEST P_base@14x among its expressive tickers (generous "
                  "reading: if even the best-covered expression of the theme is mostly hope, the theme "
                  "is). \"N/A-binary\" only when ALL the theme's computed tickers have E_norm <= 0.")
    lines.append("")
    lines.append("| Theme | Best ticker | P_base@14x | Theme classification |")
    lines.append("|---|---|---:|---|")
    rollup = build_theme_rollup(ok_rows, theme_order)
    by_theme_rows = [(slug, rollup[slug]["best_ticker"] or "-", rollup[slug]["p_base"],
                       rollup[slug]["classification"]) for slug in theme_order]
    by_theme_rows.sort(key=lambda x: (x[2] is None, -(x[2] if x[2] is not None else -999)))
    theme_class_counts = {}
    for slug, tk, pb, cls in by_theme_rows:
        theme_class_counts[cls] = theme_class_counts.get(cls, 0) + 1
        lines.append(f"| {slug} | {tk} | {_fmt_mult(pb)} | {cls} |")
    lines.append("")
    rollup_desc = ", ".join(f"{v} {k}" for k, v in sorted(theme_class_counts.items(), key=lambda kv: -kv[1]))
    lines.append(f"**Theme-level split ({len(theme_order)} themes): {rollup_desc}.**")
    lines.append("")

    lines.append("## Full table (sorted by P_base@14x, descending)")
    lines.append("")
    lines.append("| Theme | Ticker | EBIT margin (median) | E_norm | Revenue basis | P_base@14x | "
                  "P@10x | P@18x | g_implied(5y) | Classification | #Q | Source |")
    lines.append("|---|---|---:|---:|---|---:|---:|---:|---:|---|---:|---|")
    for r in ranked:
        src = r["source"] + (" *" if r.get("fallback_reason") else "")
        lines.append(
            f"| {', '.join(r['themes'])} | **{r['ticker']}** | {_fmt_pct(r['ebit_margin_median'])} | "
            f"{_fmt_usd(r['e_norm'])} | {r.get('revenue_basis','N/A')} | {_fmt_mult(r.get('p_14x'))} | "
            f"{_fmt_mult(r.get('p_10x'))} | {_fmt_mult(r.get('p_18x'))} | {_fmt_pct(r.get('g_implied'))} | "
            f"{r['classification']} | {r['n_quarters']} | {src} |"
        )
    lines.append("")
    if fail_rows:
        lines.append("### Failed tickers (excluded from table above)")
        lines.append("")
        for r in fail_rows:
            lines.append(f"- **{r['ticker']}** ({', '.join(r.get('themes', []))}) — {r['error']}")
        lines.append("")

    lines.append("## Solvency 閘讀數(槓桿/利息覆蓋)")
    lines.append("")
    lines.append("判決:`backtest/results/2026-07-15_solvency_gate_probe.md`(GO-as-gate 條件版)—— "
                  "solvency 差單獨冇跑輸料,但「pe 平(自身歷史分位 ≤20)∧ solvency 爆」126d excess "
                  "-14.9%(vs pe_low alone -2.9%);「solvency 爆但唔平」反而 +3.9%,證明無條件 gate "
                  "會錯殺(USAC 動機案例:淨負債 \\$2.98B、睇落全場最平但槓桿股權切片)。所以呢度**只讀數"
                  "同旗標**,唔喺 valuation 呢層做否決——真正「只對 pe-cheap 買入候選降級」嘅邏輯喺 "
                  "`thesis/dashboard_render.py` 嘅 `pick_ticker`(揀 ticker 嗰步)先做。"
                  f"閾值:NetDebt/EBITDA > {LEV_BAD:.0f}x 或 EBITDA≤0,OR EBIT/利息支出 < {COV_BAD:.0f}x。"
                  "金融股(銀行/保險)跳過,對佢哋呢兩條比率無意義。")
    lines.append("")
    solv_flagged = [r for r in ok_rows if r.get("solvency_flag") is True]
    solv_skipped = [r for r in ok_rows if r.get("solvency_flag") is None and r.get("solvency_reason")]
    if solv_flagged:
        lines.append(f"**{len(solv_flagged)} 隻名槓桿或利息覆蓋爆錶**(睇落平未必真係平,可能係"
                      "槓桿假象——業務語言:「睇落平但槓桿爆錶」):")
        lines.append("")
        lines.append("| Ticker | 主題 | NetDebt/EBITDA | EBIT/利息覆蓋 |")
        lines.append("|---|---|---:|---:|")
        for r in sorted(solv_flagged, key=lambda r: r["ticker"]):
            nde = r.get("net_debt_ebitda")
            cov = r.get("interest_coverage")
            nde_s = f"{nde:.2f}x" if nde is not None else "EBITDA≤0"
            cov_s = f"{cov:.2f}x" if cov is not None else "n/a"
            lines.append(f"| **{r['ticker']}** | {', '.join(r.get('themes', []))} | {nde_s} | {cov_s} |")
    else:
        lines.append("(本輪冇名觸發 solvency 旗標。)")
    lines.append("")
    if solv_skipped:
        lines.append(f"{len(solv_skipped)} 隻名 solvency 讀數缺席或跳過:" +
                      "; ".join(f"{r['ticker']}({r['solvency_reason']})" for r in solv_skipped) + "。")
        lines.append("")

    lines.append("## v0 -> v1 classification changes")
    lines.append("")
    if v0_file is None:
        lines.append("No v0 baseline report found under `backtest/results/*_expectations_gap_v0.md` "
                      "-- nothing to diff against.")
    else:
        lines.append(f"Baseline: `{v0_file}` (2026-07-12 snapshot). **Caveat: a classification change "
                      "can reflect BOTH the v1 revenue-conservatism formula change AND ordinary "
                      "market/price movement between the v0 snapshot date and today** -- the "
                      "\"revenue basis\" and \"reason\" columns below distinguish which applies per "
                      "ticker (only rows where the 3yr-median damp actually bound are attributable to "
                      "the formula change).")
        lines.append("")
        if not diffs:
            lines.append("**0 tickers changed classification bucket.**")
        else:
            lines.append(f"**{len(diffs)} ticker(s) changed classification bucket:**")
            lines.append("")
            lines.append("| Ticker | v0 classification | v1 classification | v1 revenue basis | Reason |")
            lines.append("|---|---|---|---|---|")
            for d in diffs:
                lines.append(f"| {d['ticker']} | {d['v0']} | {d['v1']} | {d['revenue_basis']} | {d['reason']} |")
    lines.append("")

    lines.append("## Caveats (read before trusting any number above)")
    lines.append("")
    lines.append("1. **14x is a baseline assumption, not truth.** 10x/18x sensitivities are reported "
                  "alongside -- treat P_base as a RANGE, not a point.")
    lines.append("2. **EBIT margin is not stationary.** median(margin) across history smooths cyclicality "
                  "but does NOT predict where margin normalizes to next cycle.")
    lines.append("3. **v1's revenue-conservatism fix has its own limits.** \"3-year median revenue\" is "
                  "median(quarterly revenue) x 4 over whatever is available up to 12 quarters -- for "
                  "thin-history names (<12 quarters, e.g. recent IPOs) the window isn't really 3 years, "
                  "and the median itself is noisier the fewer quarters it's drawn from. min(TTM, 3yr "
                  "median) is a DAMPING heuristic, not a structural forecast of where revenue normalizes.")
    lines.append(f"4. **Net debt is computed manually** (Total Debt − Cash&STI, latest balance-sheet "
                  f"quarter), NOT from defeatbeta's own \"Net Debt\" row (frequently masked/absent).")
    lines.append("5. **\"Operating Income,\" not the \"EBIT\" row defeatbeta also exposes** -- keeps "
                  "E_norm anchored to the core, controllable business (v0 caveat, spot-checked on XOM/MU).")
    lines.append(f"6. **Data depth**: defeatbeta's quarterly_income_statement tops out at 16-17 quarter "
                  f"COLUMNS for large/established names (~4yr); some quarters are masked. Below the "
                  f"{MIN_QUARTERS_OK}-quarter margin floor: {thin_desc}.")
    lines.append("7. **g_implied is undefined (N/A) whenever NOPAT_norm <= 0** -- those names are priced "
                  "as a binary/optionality outcome, not off a normalized growth rate (hence the separate "
                  "\"N/A-binary\" bucket, read qualitatively, not numerically comparable to P_base).")
    lines.append("8. **Currency alignment**: non-USD reporters (TSM/ASX in TWD, ASML in EUR) are FX-"
                  "converted at the SPOT rate on the run date -- a spot conversion of a trailing flow is "
                  "itself an approximation.")
    lines.append("9. **This is a SNAPSHOT** as of the run date -- re-run to check whether the "
                  "expectations gap has closed or widened. NOT a timing tool: it answers \"what's priced "
                  "in,\" not \"when does it re-rate\" (that's cycle_stage + constraint-language's job).")
    lines.append("10. **Universe is read live from themes.yaml** -- if a theme's ticker list or the "
                  "15-theme registry changes, this report's ticker set and theme count change with it "
                  "(unlike v0, which was a frozen hardcoded snapshot).")
    lines.append("")

    out_path = os.path.join(RESULTS_DIR, f"{today}_expectations_gap_v1.md")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return out_path


# ============================================================================
# run / CLI
# ============================================================================


def run():
    ticker_themes, theme_order = load_universe()
    rows = []
    for sym, themes in ticker_themes.items():
        print(f"computing {sym} ...")
        r = compute(sym)
        r["themes"] = themes
        rows.append(r)

    ok_rows = [r for r in rows if "error" not in r]
    fail_rows = [r for r in rows if "error" in r]
    today = date.today().isoformat()

    v0_map, v0_file = parse_v0_full_table()
    diffs = compute_diff(ok_rows, v0_map) if v0_map else []

    json_path = write_json(rows, ok_rows, fail_rows, theme_order, today)
    md_path = write_md(rows, ok_rows, fail_rows, theme_order, today, diffs, v0_file)
    return rows, ok_rows, fail_rows, theme_order, json_path, md_path, diffs, v0_file


def load_ok_rows_from_json():
    if not os.path.exists(JSON_OUT):
        return None
    with open(JSON_OUT, encoding="utf-8") as fh:
        payload = json.load(fh)
    ok_rows = []
    for tk, d in payload.get("tickers", {}).items():
        row = dict(d)
        row["ticker"] = tk
        ok_rows.append(row)
    return ok_rows


def print_diff_table(diffs, v0_file):
    if v0_file is None:
        print("\nNo v0 baseline report found under backtest/results/*_expectations_gap_v0.md -- "
              "nothing to compare.")
        return
    print(f"\n## v0 ({v0_file}) -> v1 classification changes: {len(diffs)} ticker(s)\n")
    if not diffs:
        print("(no classification changed)")
        return
    print(f"{'Ticker':<8}{'v0':<18}{'v1':<18}{'Revenue basis (v1)'}")
    for d in diffs:
        print(f"{d['ticker']:<8}{d['v0']:<18}{d['v1']:<18}{d['revenue_basis']}")
        print(f"    reason: {d['reason']}")


def main():
    ap = argparse.ArgumentParser(description="Expectations-gap valuation v1 (production).")
    ap.add_argument("--run", action="store_true", help="compute the full universe; write JSON + MD")
    ap.add_argument("--compare-v0", action="store_true",
                     help="print the v0-vs-v1 per-ticker classification diff table")
    args = ap.parse_args()
    if not args.run and not args.compare_v0:
        ap.print_help()
        return

    ok_rows = None
    diffs, v0_file = None, None
    if args.run:
        rows, ok_rows, fail_rows, theme_order, json_path, md_path, diffs, v0_file = run()
        print(f"\n{len(ok_rows)}/{len(rows)} tickers computed OK ({len(fail_rows)} failed)")
        for r in fail_rows:
            print(f"  FAIL {r['ticker']}: {r['error']}")
        print(f"wrote {json_path}")
        print(f"wrote {md_path}")

    if args.compare_v0:
        if diffs is None:
            ok_rows = load_ok_rows_from_json()
            if ok_rows is None:
                print("No thesis/.raw/valuation_report.json found -- run --run first "
                      "(python thesis/valuation.py --run).")
                return
            v0_map, v0_file = parse_v0_full_table()
            diffs = compute_diff(ok_rows, v0_map) if v0_map else []
        print_diff_table(diffs, v0_file)


if __name__ == "__main__":
    main()
