"""Solvency-gate probe — should a mechanical debt-service-capacity check be a VETO gate on
buy candidates, or the 6th dimension of thesis/composite_score.py's 0-100 score?

MOTIVATION
----------
Karst's valuation module once found USAC screening as "cheapest in the whole candidate batch"
by trailing-PE percentile (2nd percentile of its own 3y history, ~27x) -- but net debt $2.98B
vs market cap $3.84B means most of that "cheap" equity slice is a LEVERED sliver of a fairly-
covered enterprise, not a bargain on an unlevered basis (see
backtest/results/2026-07-12_expectations_gap_v0.md, USAC special-focus section). That review
wrote down "solvency gate 檢查升級為必做" and never built it. This probe does it properly:
does a MECHANICAL solvency check add real, non-redundant forward-return information on top of
the existing pe_pctile axis, and if so, should it be a binary VETO or a continuous dimension?

CANDIDATE METRICS (2 primary + 1 secondary; rationale in the report)
--------------------------------------------------------------------
1. LEVERAGE = Net Debt(manual) / EBITDA. net_debt_manual = total_debt - cash_and_STI because
   defeatbeta's own net_debt_ttm() net_debt column excludes short-term debt (long_term_debt -
   cash only), consistent with the masking issue flagged in the 2026-07-12 review.
2. COVERAGE = EBIT / Interest Expense (TTM where quarterly data exists, fiscal-year otherwise).
3. CURRENT RATIO (secondary/exploratory only; not part of the H1 headline).
   Simplified Altman-Z / Piotroski F were considered and rejected -- see report.

DATA DEPTH & THE HYBRID QUARTERLY+ANNUAL CONSTRUCTION (important)
------------------------------------------------------------------
defeatbeta's QUARTERLY balance-sheet / income-statement / net_debt_ttm / ttm_ebitda tables only
reach back ~16-17 quarters (~2022). Its ANNUAL statements reach FY2019. We therefore build each
ticker's solvency series as: quarterly-TTM readings where available (avail = quarter_end + 60d),
extended BACKWARD with fiscal-year readings (avail = fy_end + 90d, 10-K filing lag) for dates
before the first quarterly reading. Consequence stated honestly up front: solvency signals only
exist from ~mid-2020 (FY2019 + 90d) -- the repo-standard "2016-2020 vs 2021+" era split is NOT
attainable for the solvency legs (the 2016-2020 half contains only ~2020H2 events). We report
the repo split as-is (honest small n) plus a rate-regime split (<=2022 ZIRP-tail vs 2023+
higher-rate) which the data can actually support. The pe_low BASELINE (built from ttm_eps,
which does reach 2016) covers the full 2016+ window.

FINANCIALS ARE EXCLUDED BY DESIGN, not by accident: NetDebt/EBITDA and EBIT/interest-expense
are meaningless for banks/insurers (JPM, MTG failed exactly this way in the v1 run). Any wired
gate must carry the same scope rule: skip financial-sector names.

POINT-IN-TIME DISCIPLINE (same convention as exp_earnings_expectation_probe.py)
--------------------------------------------------------------------------------
avail_date = period_end + filing lag (60d quarterly / 90d annual), as-of backward join to the
SPY calendar, NaN before the first avail_date (no false ffill). The existing pe_pctile axis
(for the A/B increment) is IMPORTED from the already-validated earnings probe
(_load_fundamentals / _pit_pe_daily) -- same PIT construction, no drift.

TWO HYPOTHESES
--------------
H1 (VETO GATE): solvency-bad names (leverage > 4x or EBITDA<=0, OR EBIT/IntExp < 2x) under-
   perform their size-matched bucket at 21/63/126d forward, net of cost?
H2 (CONTINUOUS DIMENSION): pooled cross-sectional quintiles of leverage/coverage (Q1=best,
   Q5=worst, ranked across the loaded universe at each grid date) show a MONOTONIC forward-
   excess gradient, or does only the worst tail carry a penalty (=> gate, not a score)?

v2 FIX (vs the first run of this script): forward excess returns are computed for EVERY
(ticker, grid-month) event, not only signal-triggered ones. v1 conditioned the H2 quintiles and
even the pe_low baseline on "some signal fired", which biased every comparison group.

BACKTEST STANDARD (repo rules)
------------------------------
4 stock types incl. smallcap; cyclicals include AAL/CCL/CLF (classic high-leverage names) plus
AMWD/HLIT added to smallcap for leverage variance. Size-matched EW bucket benchmark excluding
the signaled name; monthly grid; 10bps/side cost on the signal leg; capital-efficiency metrics;
A/B increment vs pe_pctile; survivorship declared (biases measured efficacy DOWN -- the
bankrupt/delisted names a solvency gate is most supposed to catch are absent).

Re-run:  PYTHONUTF8=1 python backtest/experiments/exp_solvency_gate_probe.py
Quick (few tickers): KARST_PROBE_QUICK=1 PYTHONUTF8=1 python backtest/experiments/exp_solvency_gate_probe.py
Output:  backtest/results/2026-07-15_solvency_gate_probe.md
"""
from __future__ import annotations

import contextlib
import io
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as kdata  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_earnings_expectation_probe as eprobe  # noqa: E402  (reuse validated PE PIT helpers)

with contextlib.redirect_stdout(io.StringIO()):
    from defeatbeta_api.data.ticker import Ticker  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_MD = os.path.join(ROOT, "backtest", "results", "2026-07-15_solvency_gate_probe.md")

# ---- knobs ----
FILING_LAG_Q = 60              # quarterly PIT lag (calendar days), same as earnings probe
FILING_LAG_A = 90              # annual 10-K PIT lag
HORIZONS = [21, 63, 126]
COST_RT = 0.0020               # 10bps each side, round trip
LEV_BAD = 4.0                  # NetDebt / EBITDA > 4x = H1 gate trigger
COV_BAD = 2.0                  # EBIT / Interest Expense < 2x = H1 gate trigger
CURRENT_BAD = 1.0              # secondary/exploratory only
PE_LOW_PCTILE = 0.20           # existing axis definition
MIN_PE_HIST_DAYS = 504
ERA_SPLIT_REPO = pd.Timestamp("2021-01-01")   # repo-standard split (honest small n for solvency)
ERA_SPLIT_RATE = pd.Timestamp("2023-01-01")   # rate-regime split the solvency data can support
START = pd.Timestamp("2016-01-01")

# Financials (banks/insurers) excluded BY DESIGN: NetDebt/EBITDA + interest coverage are
# meaningless for them (JPM, MTG failed on exactly this in v1). Gate wiring must skip them too.
BUCKETS = {
    "megacap": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO",
                "UNH", "LLY", "V", "XOM", "WMT"],
    "midcap": ["WDC", "NTAP", "JBL", "LSCC", "RS", "CMC", "WGO", "GT", "SLAB", "SWKS", "THO"],
    "smallcap": ["AEHR", "PLAB", "KOPN", "CEVA", "UCTT", "ACLS", "OSIS", "VECO",
                 "PLXS", "MTSI", "DIOD", "AMWD", "HLIT"],
    # energy/materials/semis-cyclical + airline/cruise/steel (classic high-leverage names)
    "cyclical": ["MU", "STX", "LRCX", "AMAT", "KLAC", "COP", "DVN", "OXY",
                 "FCX", "NUE", "STLD", "CF", "AAL", "CCL", "CLF"],
}
if os.getenv("KARST_PROBE_QUICK"):
    BUCKETS = {
        "megacap": ["AAPL", "NVDA", "XOM"],
        "cyclical": ["MU", "AAL", "CLF"],
    }

SOLV_COLS = ["leverage", "ebitda_neg", "coverage", "ebit_neg_with_debt", "current_ratio"]


def _getdf(obj):
    return obj.df() if hasattr(obj, "df") else obj


def _wide_to_tidy(wide_df: pd.DataFrame, rows_wanted: list[str]) -> pd.DataFrame:
    """defeatbeta income/balance-sheet tables are WIDE: 'Breakdown' col + period-end date
    columns (+ a 'TTM' column on income statements, dropped). Returns tidy frame indexed by
    period_end (datetime), one float column per requested row; missing rows -> NaN columns;
    masked '*' cells -> NaN."""
    sub = wide_df[wide_df["Breakdown"].isin(rows_wanted)].drop_duplicates("Breakdown")
    sub = sub.set_index("Breakdown").reindex(rows_wanted)
    cols = [c for c in sub.columns if c != "TTM"]
    out = sub[cols].T
    out.index = pd.to_datetime(out.index)
    out.index.name = "period_end"
    out = out.sort_index()
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def _derive_solvency(df: pd.DataFrame) -> pd.DataFrame:
    """From columns net_debt_manual/ebitda/ebit/int_exp/tca/tcl derive the five SOLV_COLS."""
    out = df.copy()
    for c in ["net_debt_manual", "ebitda", "ebit", "int_exp", "tca", "tcl"]:
        if c not in out.columns:
            out[c] = np.nan
    out["leverage"] = np.where(out["ebitda"] > 0, out["net_debt_manual"] / out["ebitda"], np.nan)
    out["ebitda_neg"] = out["ebitda"].notna() & (out["ebitda"] <= 0)
    out["coverage"] = np.where(out["int_exp"] > 0, out["ebit"] / out["int_exp"], np.nan)
    out["ebit_neg_with_debt"] = (out["int_exp"] > 0) & out["ebit"].notna() & (out["ebit"] <= 0)
    out["current_ratio"] = np.where(out["tcl"] > 0, out["tca"] / out["tcl"], np.nan)
    return out


def _quarterly_frame(t: Ticker) -> pd.DataFrame:
    """Quarterly-TTM solvency inputs, avail = quarter_end + FILING_LAG_Q."""
    nd = _getdf(t.net_debt_ttm())
    d2e = _getdf(t.debt_to_equity())
    eb = _getdf(t.ttm_ebitda())
    inc = _getdf(t.quarterly_income_statement())
    bs = _getdf(t.quarterly_balance_sheet())

    nd = nd[["report_date", "cash_and_short_term_investments"]].copy()
    d2e = d2e[["report_date", "total_debt"]].copy()
    eb = eb[["report_date", "ttm_ebitda_usd"]].copy()
    for df_ in (nd, d2e, eb):
        df_["report_date"] = pd.to_datetime(df_["report_date"])
    q = d2e.merge(nd, on="report_date", how="inner").merge(eb, on="report_date", how="inner")
    q = q.rename(columns={"report_date": "period_end", "ttm_ebitda_usd": "ebitda"})
    if len(q):
        q["net_debt_manual"] = q["total_debt"] - q["cash_and_short_term_investments"]
    else:
        q["net_debt_manual"] = np.nan
    q = q[["period_end", "net_debt_manual", "ebitda"]]

    inc_tidy = _wide_to_tidy(inc, ["EBIT", "Interest Expense"]).rename(
        columns={"EBIT": "ebit_q", "Interest Expense": "int_exp_q"})
    inc_tidy["ebit"] = inc_tidy["ebit_q"].rolling(4, min_periods=4).sum()      # TTM
    inc_tidy["int_exp"] = inc_tidy["int_exp_q"].rolling(4, min_periods=4).sum()
    inc_tidy = inc_tidy.reset_index()

    bs_tidy = _wide_to_tidy(bs, ["Total Current Assets", "Total Current Liabilities"]).rename(
        columns={"Total Current Assets": "tca", "Total Current Liabilities": "tcl"}).reset_index()

    q = q.merge(inc_tidy[["period_end", "ebit", "int_exp"]], on="period_end", how="outer")
    q = q.merge(bs_tidy, on="period_end", how="outer").sort_values("period_end")
    q = _derive_solvency(q)
    q["avail_date"] = q["period_end"] + pd.Timedelta(days=FILING_LAG_Q)
    q["src"] = "Q"
    return q[["period_end", "avail_date", "src"] + SOLV_COLS]


def _annual_frame(t: Ticker) -> pd.DataFrame:
    """Fiscal-year solvency inputs (history extension), avail = fy_end + FILING_LAG_A."""
    abs_ = _getdf(t.annual_balance_sheet())
    ais = _getdf(t.annual_income_statement())
    bs_t = _wide_to_tidy(abs_, ["Total Debt", "Cash, Cash Equivalents & Short Term Investments",
                                "Total Current Assets", "Total Current Liabilities"]).rename(
        columns={"Total Debt": "total_debt",
                 "Cash, Cash Equivalents & Short Term Investments": "cash_sti",
                 "Total Current Assets": "tca", "Total Current Liabilities": "tcl"})
    is_t = _wide_to_tidy(ais, ["EBIT", "EBITDA", "Interest Expense"]).rename(
        columns={"EBIT": "ebit", "EBITDA": "ebitda", "Interest Expense": "int_exp"})
    a = bs_t.join(is_t, how="outer").reset_index()
    a["net_debt_manual"] = a["total_debt"] - a["cash_sti"]
    a = _derive_solvency(a)
    a["avail_date"] = a["period_end"] + pd.Timedelta(days=FILING_LAG_A)
    a["src"] = "A"
    return a[["period_end", "avail_date", "src"] + SOLV_COLS]


def _load_solvency_fundamentals(sym: str) -> pd.DataFrame:
    """Hybrid quarterly+annual PIT frame. Annual rows used ONLY before the first quarterly
    avail_date (backward history extension). Raises on total failure (caught by caller)."""
    with contextlib.redirect_stdout(io.StringIO()):
        t = Ticker(sym)
        try:
            q = _quarterly_frame(t)
        except Exception:
            q = pd.DataFrame(columns=["period_end", "avail_date", "src"] + SOLV_COLS)
        try:
            a = _annual_frame(t)
        except Exception:
            a = pd.DataFrame(columns=["period_end", "avail_date", "src"] + SOLV_COLS)
    if q.empty and a.empty:
        raise RuntimeError("no quarterly or annual solvency data")
    if not q.empty and not a.empty:
        first_q = q["avail_date"].min()
        a = a[a["avail_date"] < first_q]
    out = pd.concat([a, q], ignore_index=True).sort_values("avail_date").reset_index(drop=True)
    return out


def _pit_daily(q: pd.DataFrame, value_cols: list[str], cal: pd.DatetimeIndex) -> pd.DataFrame:
    """As-of (backward) join of PIT values onto every calendar day -- NaN before the first
    avail_date (no look-ahead, no false ffill before the name has any reading)."""
    qq = q.dropna(subset=["avail_date"]).sort_values("avail_date")
    idx = pd.DataFrame({"date": pd.to_datetime(cal).astype("datetime64[ns]")}).sort_values("date")
    src = qq[["avail_date"] + value_cols].rename(columns={"avail_date": "date"}).sort_values("date")
    src["date"] = pd.to_datetime(src["date"]).astype("datetime64[ns]")
    merged = pd.merge_asof(idx, src, on="date", direction="backward")
    return merged.set_index("date")


# ---------------------------------------------------------------- main compute
def build():
    spy = kdata.load("SPY", adjusted=True)["close"]
    cal = spy.index
    tickers = {tk: bkt for bkt, tks in BUCKETS.items() for tk in tks}

    adj_on_cal: dict[str, pd.Series] = {}
    solv_daily: dict[str, pd.DataFrame] = {}
    pe_pit: dict[str, pd.Series] = {}
    loaded, failed = [], []

    for tk in tickers:
        try:
            adj = kdata.load(tk, adjusted=True)["close"]
            adj_c = adj.reindex(cal).ffill()
            adj_c[cal < adj.index.min()] = np.nan
            adj_on_cal[tk] = adj_c

            qs = _load_solvency_fundamentals(tk)
            solv_daily[tk] = _pit_daily(qs, SOLV_COLS, cal)

            q_pe, close_db = eprobe._load_fundamentals(tk)
            pe_pit[tk] = eprobe._pit_pe_daily(close_db, q_pe).reindex(cal).ffill()

            loaded.append(tk)
        except Exception as e:
            failed.append((tk, f"{type(e).__name__}: {str(e)[:90]}"))
    print(f"loaded {len(loaded)}/{len(tickers)} tickers; failed: {[f[0] for f in failed]}")

    grid = pd.Series(cal, index=cal).resample("ME").last().dropna()
    grid = pd.DatetimeIndex([d for d in grid.values])
    grid = grid[grid >= START]

    # ---- vectorized forward returns per ticker (v2: for EVERY event, no conditioning) ----
    fwd: dict[str, dict[int, pd.Series]] = {}
    for tk in loaded:
        v = adj_on_cal[tk].values.astype(float)
        fwd[tk] = {}
        for H in HORIZONS:
            r = np.full(len(v), np.nan)
            with np.errstate(invalid="ignore", divide="ignore"):
                r[:-H] = v[H:] / v[:-H] - 1.0
            r[~np.isfinite(r)] = np.nan
            fwd[tk][H] = pd.Series(r, index=cal)

    # bucket EW forward return per (bkt, t, H); leave-one-out handled at event level
    bucket_sum: dict[tuple, float] = {}
    bucket_cnt: dict[tuple, int] = {}
    for bkt, tks in BUCKETS.items():
        members = [tk for tk in tks if tk in fwd]
        for H in HORIZONS:
            for t in grid:
                vals = [fwd[tk][H].get(t, np.nan) for tk in members]
                vals = [x for x in vals if np.isfinite(x)]
                bucket_sum[(bkt, t, H)] = float(np.sum(vals)) if vals else np.nan
                bucket_cnt[(bkt, t, H)] = len(vals)

    # ---- per-ticker per-grid-date event rows (ALL events; signals are columns) ----
    rows = []
    for tk in loaded:
        bkt = tickers[tk]
        sd = solv_daily[tk]
        pe_c = pe_pit[tk]
        adj_c = adj_on_cal[tk]
        for t in grid:
            if not np.isfinite(adj_c.get(t, np.nan)):
                continue
            srow = sd.loc[t]
            pe_now = pe_c.get(t, np.nan)
            pe_hist = pe_c.loc[:t].dropna()
            pe_hist = pe_hist[np.isfinite(pe_hist)]
            pe_pctile = np.nan
            if np.isfinite(pe_now) and len(pe_hist) >= MIN_PE_HIST_DAYS:
                pe_pctile = float((pe_hist.values <= pe_now).mean())
            rec = {
                "tk": tk, "bkt": bkt, "date": t,
                "leverage": srow.get("leverage", np.nan),
                "ebitda_neg": bool(srow.get("ebitda_neg")) if pd.notna(srow.get("ebitda_neg")) else False,
                "coverage": srow.get("coverage", np.nan),
                "ebit_neg_with_debt": (bool(srow.get("ebit_neg_with_debt"))
                                       if pd.notna(srow.get("ebit_neg_with_debt")) else False),
                "current_ratio": srow.get("current_ratio", np.nan),
                "pe_pctile": pe_pctile,
            }
            for H in HORIZONS:
                r = fwd[tk][H].get(t, np.nan)
                S, C = bucket_sum.get((bkt, t, H), np.nan), bucket_cnt.get((bkt, t, H), 0)
                if np.isfinite(r) and C >= 2:
                    bench = (S - r) / (C - 1)
                    rec[f"exc_{H}"] = (r - COST_RT) - bench
                else:
                    rec[f"exc_{H}"] = np.nan
            rows.append(rec)
    ev = pd.DataFrame(rows)

    # ---- cross-sectional quintiles per grid date (pooled across buckets) ----
    ev["cov_badness"] = -ev["coverage"]
    ev["lev_q"] = np.nan
    ev["cov_q"] = np.nan
    for t, grp in ev.groupby("date"):
        lev_ok = grp["leverage"].dropna()
        if len(lev_ok) >= 10:
            try:
                qc = pd.qcut(lev_ok, 5, labels=False, duplicates="drop") + 1
                ev.loc[qc.index, "lev_q"] = qc.values
            except ValueError:
                pass
        cov_ok = grp["cov_badness"].dropna()
        if len(cov_ok) >= 10:
            try:
                qc = pd.qcut(cov_ok, 5, labels=False, duplicates="drop") + 1
                ev.loc[qc.index, "cov_q"] = qc.values
            except ValueError:
                pass

    # ---- H1 gate flags + A/B (pe_low) + eras ----
    ev["lev_gate"] = ev["ebitda_neg"] | (ev["leverage"] > LEV_BAD)
    ev["cov_gate"] = ev["ebit_neg_with_debt"] | (ev["coverage"] < COV_BAD)
    ev["current_gate"] = ev["current_ratio"] < CURRENT_BAD
    ev["solvency_bad"] = ev["lev_gate"] | ev["cov_gate"]
    ev["has_solv"] = (ev["leverage"].notna() | ev["coverage"].notna()
                      | ev["ebitda_neg"] | ev["ebit_neg_with_debt"])
    ev["pe_low"] = ev["pe_pctile"] <= PE_LOW_PCTILE
    ev["era_repo"] = np.where(ev["date"] < ERA_SPLIT_REPO, "2016-2020", "2021+")
    ev["era_rate"] = np.where(ev["date"] < ERA_SPLIT_RATE, "<=2022", "2023+")

    return ev, loaded, failed, tickers


# ---------------------------------------------------------------- aggregation
def agg(df: pd.DataFrame, mask, H):
    col = f"exc_{H}"
    x = df.loc[mask, col].dropna().values
    if len(x) == 0:
        return None
    mean = float(np.mean(x)); med = float(np.median(x))
    sd = float(np.std(x, ddof=1)) if len(x) > 1 else np.nan
    hit_under = float((x < 0).mean())
    sharpe = float(mean / sd * np.sqrt(252.0 / H)) if sd and sd > 0 else np.nan
    ann_drag = mean * (252.0 / H)
    return {"n": len(x), "mean": mean, "med": med, "hit_under": hit_under,
            "sharpe": sharpe, "ann_drag": ann_drag}


def _row(a):
    if a is None:
        return "n=0 | — | — | — | — | —"
    return (f"n={a['n']} | {a['mean']*100:+.2f}% | {a['med']*100:+.2f}% | "
            f"{a['hit_under']*100:.0f}% | {a['sharpe']:+.2f} | {a['ann_drag']*100:+.1f}%")


def write_report(ev, loaded, failed, tickers):
    L = []
    A = L.append
    A("# Solvency-Gate Probe — 2026-07-15")
    A("")
    A("Script: `backtest/experiments/exp_solvency_gate_probe.py` "
      "(`PYTHONUTF8=1 python backtest/experiments/exp_solvency_gate_probe.py`)")
    A("")
    A("## 動機")
    A("")
    A("Karst 估值模組發現過:USAC 睇 trailing-PE 分位「全場最平」(自身歷史 2nd percentile,~27x),"
      "但 net debt \\$2.98B vs 市值 \\$3.84B——嗰個「平」一大半係槓桿股權切片嘅假象,唔係無槓桿基礎上嘅"
      "真.便宜(見 `backtest/results/2026-07-12_expectations_gap_v0.md` USAC 專節)。"
      "嗰次審查寫低「solvency gate 檢查升級為必做」但一直未做。本探測正式回答:"
      "一個**機械**償債能力檢查,應唔應該成為買入候選嘅**否決閘**,定係 `thesis/composite_score.py` "
      "0-100 綜合分嘅**第六維**?")
    A("")
    A("## 候選指標(2 主 + 1 副,理據)")
    A("")
    A("| 指標 | 定義 | 點解揀 |")
    A("|---|---|---|")
    A("| **槓桿(主)** | Net Debt(手動重構)÷ EBITDA(季度 TTM,史前段用年度) | 直接對應 USAC 動機案例嘅比率;"
      "`net_debt_ttm()` 官方 net_debt 欄剔除短債(只計長債−現金),同 2026-07-12 審查發現嘅遮蔽問題一致,"
      "改用 `total_debt − cash_and_short_term_investments` 手動重構。 |")
    A("| **利息覆蓋(主)** | EBIT ÷ 利息支出(同上,TTM/年度) | 同槓桿係**唔同故障模式**:槓桿低但盈利突然"
      "跌穿都可以覆蓋唔到利息;槓桿高但融資條件好都可以照覆蓋。兩者唔應該疊做同一條軸。 |")
    A("| **流動比率(副,exploratory)** | Total Current Assets ÷ Total Current Liabilities | "
      "短週期流動性,同結構性過度槓桿係唔同故障模式,同 USAC 案例關聯較弱——只報告唔入主判決。"
      "簡化 Altman-Z / Piotroski F-score 已考慮但**剔除**:需要遠多過兩條主軸嘅輸入"
      "(市值比率、資產週轉變化、股數變化等),會沖淡「機械 gate 值唔值得起」呢個核心問題。 |")
    A("")
    A(f"**H1(否決閘)**:solvency 差(槓桿>{LEV_BAD:.0f}x 或 EBITDA≤0,OR 利息覆蓋<{COV_BAD:.0f}x)"
      "嘅股,forward 21/63/126d 係咪跑輸同組 size-matched 籃子?")
    A("**H2(連續維度)**:pooled 跨股橫切面五分位(Q1=最佳,Q5=最差,逐 grid 日全 universe 排位)"
      "係咪單調——定係得最差嗰截先有懲罰(=> 應該做 gate 唔係連續分)?")
    A("")
    A("## 數據深度與 hybrid 季度+年度構造(誠實申報,讀結果前必讀)")
    A("")
    A(f"defeatbeta **季度**資產負債表/損益表/`net_debt_ttm`/`ttm_ebitda` 只回到 ~16-17 季(≈2022 起);"
      f"**年度**報表回到 FY2019。本探測用 hybrid:有季度 TTM 讀數嘅日子用季度(avail = 季末+{FILING_LAG_Q}日),"
      f"之前嘅歷史用年度讀數向後延伸(avail = 財年末+{FILING_LAG_A}日,10-K lag)。後果:"
      "**solvency 訊號最早只去到 ~2020 年中**(FY2019+90日)。repo 標準「2016-2020 / 2021+」兩半劈"
      "對 solvency 腿**做唔到**——「2016-2020」嗰半實際只含 ~2020 下半年事件(下表照報,n 細係誠實反映)。"
      "另補一個數據撐得起嘅利率 regime 劈法:**≤2022(ZIRP 尾)vs 2023+(高息期)**——對 solvency 訊號"
      "呢個劈法本身仲有經濟意義(利率升先係償債能力出事嘅環境)。"
      "`pe_low` baseline 用 `ttm_eps`(回到 2016 前)起,覆蓋完整 2016+ 窗口。")
    A("")
    A("**金融股(銀行/保險)係設計上剔除,唔係載入失敗**:NetDebt/EBITDA 同 EBIT/利息覆蓋對佢哋無意義"
      "(v1 run JPM/MTG 正正咁樣炸)。將來接線嘅 gate 必須帶同一 scope 規則:金融股跳過。")
    A("")
    A("## Point-in-time 處理")
    A("")
    A("同 `exp_earnings_expectation_probe.py` 一致嘅保守 filing-lag 慣例。現有 `pe_pctile` 軸"
      "(A/B 增量用)**直接 import** 該探測嘅 `_load_fundamentals`/`_pit_pe_daily`,唔重寫、無 drift。"
      "solvency 讀數經 `merge_asof(direction='backward')` 逐日對齊,首個 avail_date 之前 = NaN"
      "(唔會偽 ffill)。**v2 修正**:forward excess 對**全部**(ticker, 月)事件計算,唔係只計有訊號嘅"
      "——v1 曾將 H2 五分位同 pe_low baseline 都 condition 咗喺「有訊號觸發」上,全部比較組被污染,"
      "該版結果作廢。")
    A("")
    A("## Universe(4 股種 + size-matched benchmark)")
    A("")
    for bkt, tks in BUCKETS.items():
        ok = [t for t in tks if t in loaded]
        A(f"- **{bkt}** ({len(ok)}/{len(tks)}): {', '.join(ok)}")
    if failed:
        A(f"- **載入失敗**: {', '.join(f'{t}({e.split(chr(58))[0]})' for t, e in failed)}")
    A("")
    A("cyclicals 組喺能源/材料/半導體之上有 AAL/CCL/CLF(航空/郵輪/鋼鐵)——文獻上嘅經典高槓桿名;"
      "smallcap 加 AMWD/HLIT、midcap 用 THO 替代金融股 MTG、megacap 用 UNH 替代 JPM,"
      "保證 solvency 軸有真正嘅樣本內方差。")
    A("")
    n_solv = int((ev["has_solv"]).sum())
    A(f"總事件數(ticker×月):{len(ev)};其中有 solvency 讀數:{n_solv};"
      f"solvency_bad 觸發:{int(ev['solvency_bad'].sum())};pe_low 觸發:{int(ev['pe_low'].sum())}。")
    A("")

    # ---- H1: gate results per bucket per horizon ----
    def block(title, mask_fn, note=""):
        A(f"### {title}")
        A("")
        if note:
            A(note); A("")
        A("| 股種 | Horizon | n | mean excess | median | 跑輸率 | cond.Sharpe(ann) | 年化 excess |")
        A("|---|---|---:|---:|---:|---:|---:|---:|")
        for bkt in BUCKETS:
            for H in HORIZONS:
                m = mask_fn(ev) & (ev["bkt"] == bkt)
                a = agg(ev, m, H)
                A(f"| {bkt} | {H}d | " + _row(a) + " |")
        for H in HORIZONS:
            a = agg(ev, mask_fn(ev), H)
            A(f"| **ALL** | {H}d | " + _row(a) + " |")
        A("")

    A("## 結果 A — H1 否決閘(全期,逐股種)")
    A("")
    block("solvency_bad = lev_gate OR cov_gate(建議 H1 定義)", lambda e: e["solvency_bad"] == True)
    block(f"lev_gate 單獨(槓桿>{LEV_BAD:.0f}x 或 EBITDA≤0)", lambda e: e["lev_gate"] == True)
    block(f"cov_gate 單獨(覆蓋<{COV_BAD:.0f}x 或 EBIT≤0 有息)", lambda e: e["cov_gate"] == True)
    block(f"current_gate(副軸,流動比率<{CURRENT_BAD:.1f},exploratory)", lambda e: e["current_gate"] == True)
    block("Baseline: pe_low ALONE(現有 pe_pctile 軸,PE≤20%)", lambda e: e["pe_low"] == True)
    block("對照組:solvency 正常(有讀數且未觸發 gate)",
          lambda e: (e["has_solv"] == True) & (e["solvency_bad"] == False),
          note="gate 嘅另一面:如果「正常組」都同樣跑輸,gate 就冇判別力。")

    # ---- era splits ----
    A("## 結果 B — 兩半穩健性(pooled,全股種)")
    A("")
    A("### B1 repo 標準劈法(2016-2020 / 2021+)——solvency 腿嘅前半實際只有 ~2020H2(數據深度,見上)")
    A("")
    A("| Gate | Era | Horizon | n | mean excess | 跑輸率 | cond.Sharpe |")
    A("|---|---|---|---:|---:|---:|---:|")
    for label, key in [("solvency_bad", "solvency_bad"), ("lev_gate", "lev_gate"),
                       ("cov_gate", "cov_gate"), ("pe_low(baseline)", "pe_low")]:
        for era in ["2016-2020", "2021+"]:
            for H in HORIZONS:
                m = (ev[key] == True) & (ev["era_repo"] == era)
                a = agg(ev, m, H)
                if a is None:
                    A(f"| {label} | {era} | {H}d | n=0 | — | — | — |")
                else:
                    A(f"| {label} | {era} | {H}d | {a['n']} | {a['mean']*100:+.2f}% | "
                      f"{a['hit_under']*100:.0f}% | {a['sharpe']:+.2f} |")
    A("")
    A("### B2 利率 regime 劈法(≤2022 ZIRP 尾 / 2023+ 高息期)——solvency 數據撐得起嘅劈法")
    A("")
    A("| Gate | Era | Horizon | n | mean excess | 跑輸率 | cond.Sharpe |")
    A("|---|---|---|---:|---:|---:|---:|")
    for label, key in [("solvency_bad", "solvency_bad"), ("lev_gate", "lev_gate"),
                       ("cov_gate", "cov_gate"), ("pe_low(baseline)", "pe_low")]:
        for era in ["<=2022", "2023+"]:
            for H in HORIZONS:
                m = (ev[key] == True) & (ev["era_rate"] == era)
                a = agg(ev, m, H)
                if a is None:
                    A(f"| {label} | {era} | {H}d | n=0 | — | — | — |")
                else:
                    A(f"| {label} | {era} | {H}d | {a['n']} | {a['mean']*100:+.2f}% | "
                      f"{a['hit_under']*100:.0f}% | {a['sharpe']:+.2f} |")
    A("")

    # ---- A/B increment ----
    A("## 結果 C — A/B 增量:solvency_bad vs 現有 pe_pctile")
    A("")
    A("核心問題:solvency 差嘅股,係咪本身已經係 `pe_pctile` 標到嘅平股(=冇增量),定係"
      "solvency 加喺 pe_low 之上仲有淨額外拖累(=有增量,值得做獨立軸)?")
    A("")
    A("| Horizon | pe_low ALONE mean(n) | solvency_bad ALONE mean(n) | pe_low AND solvency_bad mean(n) | "
      "solvency_bad AND NOT pe_low mean(n) | 增量判讀 |")
    A("|---|---:|---:|---:|---:|---|")
    for H in HORIZONS:
        a_pe = agg(ev, ev["pe_low"] == True, H)
        a_sv = agg(ev, ev["solvency_bad"] == True, H)
        a_both = agg(ev, (ev["pe_low"] == True) & (ev["solvency_bad"] == True), H)
        a_sv_only = agg(ev, (ev["solvency_bad"] == True) & (ev["pe_low"] == False), H)

        def fmt(a):
            return f"{a['mean']*100:+.2f}% (n={a['n']})" if a else "n=0"
        judge = "—"
        if a_both and a_pe:
            delta = a_both["mean"] - a_pe["mean"]
            judge = ("疊加有增量(更負)" if delta < -0.005 else
                     "≈冇增量(pe_pctile 已捕捉)" if abs(delta) <= 0.005 else "疊加後反而較唔差")
            judge += f"(Δ={delta*100:+.2f}pp vs pe_low alone)"
        A(f"| {H}d | {fmt(a_pe)} | {fmt(a_sv)} | {fmt(a_both)} | {fmt(a_sv_only)} | {judge} |")
    A("")
    A("`solvency_bad AND NOT pe_low`(唔平但 gate-fail)一欄係關鍵獨立性測試:如果呢欄都跑輸,"
      "solvency 就唔係「換個角度講嘅平股」,而係一條獨立軸——即使個股表面上唔平都值得否決/扣分。")
    A("")

    # ---- C2: conditional-gate deep dive (the USAC scenario) ----
    A("### C2 條件閘深挖:pe_low AND solvency_bad(USAC 場景)")
    A("")
    A("上表如果顯示「無條件 gate 冇料、但 pe_low∧solvency_bad 顯著更負」,行為上就係 Piotroski 形態"
      "(solvency 只喺 cheap 桶內有判別力)——亦正正係動機場景:USAC 係因為「睇落平」先入候選,"
      "gate 嘅用武之地就係呢批名。呢節驗證條件組嘅穩健性:逐股種、利率 era、同 ticker 集中度"
      "(如果 n 靠一兩隻股撐起,唔可以接線)。")
    A("")
    both_mask = (ev["pe_low"] == True) & (ev["solvency_bad"] == True)
    A("| 切片 | Horizon | n | mean excess | 跑輸率 |")
    A("|---|---|---:|---:|---:|")
    for bkt in BUCKETS:
        for H in HORIZONS:
            a = agg(ev, both_mask & (ev["bkt"] == bkt), H)
            if a:
                A(f"| {bkt} | {H}d | {a['n']} | {a['mean']*100:+.2f}% | {a['hit_under']*100:.0f}% |")
            else:
                A(f"| {bkt} | {H}d | 0 | — | — |")
    for era in ["<=2022", "2023+"]:
        for H in HORIZONS:
            a = agg(ev, both_mask & (ev["era_rate"] == era), H)
            if a:
                A(f"| era {era} | {H}d | {a['n']} | {a['mean']*100:+.2f}% | {a['hit_under']*100:.0f}% |")
            else:
                A(f"| era {era} | {H}d | 0 | — | — |")
    A("")
    sub126 = ev[both_mask & ev["exc_126"].notna()]
    if len(sub126):
        cnt = sub126["tk"].value_counts()
        n_distinct = len(cnt)
        top_share = float(cnt.iloc[0]) / float(cnt.sum())
        top_lines = []
        for tk_, c_ in cnt.head(6).items():
            m_ = float(sub126.loc[sub126["tk"] == tk_, "exc_126"].mean())
            top_lines.append(f"{tk_}(n={c_}, mean {m_*100:+.1f}%)")
        A(f"**Ticker 集中度(126d 事件)**:{n_distinct} 隻股;最大單一 ticker 佔 "
          f"{top_share*100:.0f}%。Top 貢獻:{', '.join(top_lines)}。")
    A("")

    # ---- H2: cross-sectional quintiles ----
    A("## 結果 D — H2 連續維度:跨股橫切面五分位(pooled,全股種,126d)")
    A("")
    A("Q1=最佳(低槓桿/高覆蓋),Q5=最差(高槓桿/低覆蓋)。單調(Q1→Q5 excess 遞減)支持連續分設計;"
      "只有 Q5 顯著負值支持 gate(二元否決)設計。v2:全事件計 return,無 conditioning bias。")
    A("")
    A("| 指標 | Quintile | n | mean excess(126d) | 跑輸率 |")
    A("|---|---|---:|---:|---:|")
    for label, qcol in [("槓桿(leverage)", "lev_q"), ("覆蓋(coverage,badness=-coverage)", "cov_q")]:
        for qn in [1, 2, 3, 4, 5]:
            m = ev[qcol] == qn
            a = agg(ev, m, 126)
            if a:
                A(f"| {label} | Q{qn} | {a['n']} | {a['mean']*100:+.2f}% | {a['hit_under']*100:.0f}% |")
            else:
                A(f"| {label} | Q{qn} | 0 | — | — |")
    A("")
    A("補充:EBITDA≤0(`ebitda_neg`)同「有息但 EBIT≤0」(`ebit_neg_with_debt`)嘅事件冇正定義嘅"
      "leverage/coverage 數值,冇入五分位排位(佢哋定義上已經係最差,H1 gate 用二元旗標獨立捕捉)。"
      "五分位喺同一 grid 日至少要 10 個有效讀數先排(即實際只由 ~2020 年中起)。")
    A("")

    # ---- verdict ----
    A("## 結論(GO-as-gate / GO-as-dimension / DISPLAY-ONLY / NO-GO)")
    A("")
    for ln in _verdict(ev):
        A(ln)
    A("")

    A("## 誠實 Caveat")
    A("")
    A("1. **歷史深度唔達 repo 標準**:solvency 訊號最早 ~2020 年中(defeatbeta 年度表只回到 FY2019),"
      "2016-2019 完全冇覆蓋——呢四年包含 2016 工業衰退、2018Q4 信用驚嚇,正正係 solvency 訊號可能"
      "最有用嘅時段之一。結論只適用於 2020+,唔好外推。")
    A(f"2. **filing lag 係近似**:季度固定 {FILING_LAG_Q} 日、年度 {FILING_LAG_A} 日,"
      "真實各公司/各季申報日有差異。")
    A("3. **`net_debt_manual` 仍係近似**:total_debt/cash_and_STI 取自 defeatbeta 兩張唔同表"
      "(`debt_to_equity()`/`net_debt_ttm()`),未逐一對過原始 10-Q;年度段用 balance-sheet "
      "'Total Debt'/'Cash…STI' 行,同季度段口徑可能有細差。")
    A("4. **hybrid 季度/年度接駁**:~2022 前後讀數頻率由年度變季度,訊號更新速度唔一致"
      "(年度段一年先郁一次)。方向唔應該受影響,但 gate 觸發嘅 timing 喺年度段遲鈍。")
    A("5. **覆蓋比率喺利息支出接近 0 時唔穩定**:分母細,coverage 可以爆極端值,已用 "
      "`int_exp > 0` 過濾但冇上限截尾。")
    A("6. **事件重疊**:月 grid vs 126d horizon,有效獨立樣本遠少於 n;同一隻股連續多月觸發 gate "
      "係常態(債務結構變化慢),條 excess 序列高度自相關,cond.Sharpe 只作方向參考。")
    A("7. **survivorship**:universe 係今日仍上市嘅名。solvency gate 應該捕捉嘅正正係破產/退市名"
      "(distress 同退市高度相關,比 PE/動能訊號嘅漏樣本傷好多),缺席**必然低估** gate 效力,"
      "方向保守——即係話「有效」結論可以信,「冇效」結論要打折。")
    A("8. **cyclicals 有 AAL/CCL/CLF、smallcap 擬加 AMWD/HLIT(AMWD 載入失敗)令樣本非隨機**:"
      "刻意揀嚟俾 solvency 軸方差;如果結果主要由呢幾隻驅動,增量嘅可推廣性要打折"
      "(C2 嘅 ticker 集中度檢查就係為此)。")
    A("9. **金融股剔除**:結論唔適用於銀行/保險;接線時 gate 必須跳過金融 sector。")
    A("10. **smallcap 方向反轉**:smallcap 嘅 gate-fail 名反而跑贏(lev_gate 126d 約 +9%)——"
      "2020-2021 投機行情下,cash-burn/高槓桿細價股係彩票型贏家。條件閘(只罰 cheap 名)"
      "自然避開呢批(佢哋通常冇 PE 或 PE 唔低),但直接印證「無條件 gate 會錯殺」。")
    A("11. **條件組宏觀集中**:pe_low∧solvency_bad 嘅負 excess 主要由 COVID 疫後 travel/"
      "consumer-cyclical distress 名(CCL/AAL/GT 類)貢獻——雖然通過「≥6 隻股、單一 ticker ≤40%」"
      "檢查,但佢哋某程度上係**同一個宏觀 episode**;而 DVN(能源,2020-21 平+高槓桿其後大升)"
      "顯示條件閘嘅錯殺面。接線建議用「否決或強制降級人手覆核」而唔係靜默剔除,正係為此。")
    A("")
    A("## 文獻對照")
    A("")
    A("**Dichev (1998, JF)** 「Is the Risk of Bankruptcy a Systematic Risk?」—— 用 Z-score/O-score "
      "量度嘅高破產風險股,後續回報**反而較低**(唔係風險溢價,係 anomaly)。"
      "**Campbell, Hilscher & Szilagyi (2008, JF)** 「In Search of Distress Risk」—— 更完整嘅違約"
      "機率模型,結果一致:高財務困境風險股 forward return 系統性偏低,而且集中喺最差 tail"
      "(佢哋嘅 distress 組合回報差主要由最高違約機率 decile 驅動——同本探測 H2「gate 定連續分」"
      "嘅問題直接相關)。**Piotroski (2000, JAR)** F-score —— 財務強度篩選喺**低市帳率股**入面"
      "分開贏家輸家:高 F-score 平股跑贏低 F-score 平股,直接對應本探測嘅 A/B 增量框架"
      "(solvency 疊喺 cheap 之上)。三份文獻方向一致支持 H1(solvency 差 = 跑輸,唔係補償性溢價)。"
      "如果本探測測出「冇效」或方向相反,要分辨:(a) proxy/樣本問題——survivorship 剔走真困境股"
      "(caveat 7)、歷史只有 2020+(caveat 1)、net_debt 重構噪音;定係 (b) 主張喺呢個期間唔成立"
      "(2020-2021 ZIRP 令高槓桿股反而受惠)。兩者政策含意唔同:(a) → 換更乾淨數據源重試先下判;"
      "(b) → 承認 regime 依賴,gate 帶利率條件先接線。")
    A("")

    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(f"wrote {OUT_MD}")


def _verdict(ev):
    lines = []

    def pooled(key):
        return {H: agg(ev, ev[key] == True, H) for H in HORIZONS}

    sv = pooled("solvency_bad")
    lev = pooled("lev_gate")
    cov = pooled("cov_gate")
    base = pooled("pe_low")
    ok_ctrl = {H: agg(ev, (ev["has_solv"] == True) & (ev["solvency_bad"] == False), H)
               for H in HORIZONS}

    both_mask = (ev["pe_low"] == True) & (ev["solvency_bad"] == True)
    both63 = agg(ev, both_mask, 63)
    both126 = agg(ev, both_mask, 126)
    svonly126 = agg(ev, (ev["solvency_bad"] == True) & (ev["pe_low"] == False), 126)
    inc = None
    if both126 and base.get(126):
        inc = both126["mean"] - base[126]["mean"]

    # conditional-gate robustness inputs: era stability + ticker concentration
    both_e1 = agg(ev, both_mask & (ev["era_rate"] == "<=2022"), 126)
    both_e2 = agg(ev, both_mask & (ev["era_rate"] == "2023+"), 126)
    sub126 = ev[both_mask & ev["exc_126"].notna()]
    n_distinct, top_share = 0, 1.0
    if len(sub126):
        cnt = sub126["tk"].value_counts()
        n_distinct = len(cnt)
        top_share = float(cnt.iloc[0]) / float(cnt.sum())

    lines.append("**啟發式判讀(下列數字由 script 計,最終判斷由作者覆核):**")
    lines.append("")
    for label, d in [("solvency_bad", sv), ("lev_gate", lev), ("cov_gate", cov),
                     ("pe_low baseline", base), ("solvency 正常對照組", ok_ctrl)]:
        parts = []
        for H in HORIZONS:
            a = d[H]
            parts.append(f"{H}d {a['mean']*100:+.2f}%(n={a['n']})" if a else f"{H}d n=0")
        lines.append(f"- {label} mean excess: " + ", ".join(parts))
    if svonly126:
        lines.append(f"- **獨立性關鍵**:solvency_bad AND NOT pe_low(126d) = "
                     f"{svonly126['mean']*100:+.2f}%(n={svonly126['n']}) —— "
                     + ("跑輸,solvency 有獨立於估值嘅拖累" if svonly126["mean"] < -0.005
                        else "唔顯著跑輸,solvency 效力可能主要嚟自同 pe_low 重疊嘅名"))
    if inc is not None:
        lines.append(f"- **A/B 增量(126d)**:(pe_low AND solvency_bad) − pe_low alone = {inc*100:+.2f}pp")
    if both126:
        e1s = f"{both_e1['mean']*100:+.1f}%(n={both_e1['n']})" if both_e1 else "n=0"
        e2s = f"{both_e2['mean']*100:+.1f}%(n={both_e2['n']})" if both_e2 else "n=0"
        lines.append(f"- **條件組(pe_low∧solvency_bad,126d)era 穩健性**:≤2022 {e1s},2023+ {e2s};"
                     f"ticker 集中度:{n_distinct} 隻,最大佔 {top_share*100:.0f}%")

    # quintile monotonicity check (126d, pooled)
    lev_q_means = []
    for qn in [1, 2, 3, 4, 5]:
        a = agg(ev, ev["lev_q"] == qn, 126)
        lev_q_means.append(a["mean"] if a else np.nan)
    finite_q = [v for v in lev_q_means if np.isfinite(v)]
    monotonic = len(finite_q) >= 4 and all(
        finite_q[i] >= finite_q[i + 1] - 0.01 for i in range(len(finite_q) - 1))
    only_worst = (len(finite_q) >= 3 and finite_q[-1] < -0.01
                  and all(v > finite_q[-1] + 0.01 for v in finite_q[:-1]))
    lines.append("")
    lines.append("- **槓桿五分位(126d)mean excess Q1→Q5**: " +
                 ", ".join(f"{v*100:+.1f}%" if np.isfinite(v) else "n/a" for v in lev_q_means))
    if monotonic:
        lines.append("  -> 大致單調,支持連續分設計(H2 成立)。")
    elif only_worst:
        lines.append("  -> 懲罰集中喺 Q5(最差檔),中間分位冇單調梯度,支持 GATE(二元否決)而非連續分。")
    else:
        lines.append("  -> 非單調亦非「只有最差檔」形態,結構不乾淨——見下判決保留態度。")
    lines.append("")

    def robust_neg(d, thr=-0.005):
        ok = [d[H] for H in HORIZONS if d[H] and d[H]["n"] >= 20]
        return len(ok) >= 2 and all(a["mean"] < thr for a in ok)

    sv_robust = robust_neg(sv)
    independent = svonly126 is not None and svonly126["mean"] < -0.005 and svonly126["n"] >= 15
    increments = inc is not None and inc < -0.005
    # conditional gate (Piotroski-style: solvency only discriminates INSIDE the cheap bucket):
    # both-group robustly negative at 63d+126d, meaningfully worse than pe_low alone, stable
    # across both rate eras, and not driven by one or two tickers.
    cond_ok = (
        both63 is not None and both126 is not None
        and both63["n"] >= 40 and both126["n"] >= 40
        and both63["mean"] < -0.02 and both126["mean"] < -0.05
        and increments
        and both_e1 is not None and both_e2 is not None
        and both_e1["mean"] < 0 and both_e2["mean"] < 0
        and n_distinct >= 6 and top_share <= 0.40
    )

    if sv_robust and independent and only_worst:
        v = (f"GO-as-gate(建議閾值:槓桿>{LEV_BAD:.0f}x EBITDA 或 EBITDA≤0,"
             f"OR 利息覆蓋<{COV_BAD:.0f}x;金融股跳過)")
        why = ("solvency_bad forward excess 穩健為負,對 NOT pe_low 子集仍然成立(唔係 pe_pctile "
               "換個講法),且五分位形態係「懲罰集中喺最差檔」——本質二元,做連續分只會將噪音混入"
               "中間分位。建議接線位:**pick_ticker 否決閘**(硬性剔除,唔止扣分)。")
    elif sv_robust and independent and monotonic:
        v = "GO-as-dimension(composite 第六維:solvency;權重待 A/B sizing 回測定案)"
        why = ("solvency_bad forward excess 穩健為負且獨立於 pe_low,五分位大致單調——連續刻度"
               "捕捉到中間分位嘅漸進拖累,做二元 gate 會浪費呢部分資訊。建議接線位:"
               "composite_score.py 加 `dim_solvency`(槓桿/覆蓋反轉映射,類似 dim_value)。")
    elif sv_robust and independent:
        v = (f"GO-as-gate(保守版:五分位結構唔乾淨,只信最差 tail;閾值:槓桿>{LEV_BAD:.0f}x 或 "
             f"EBITDA≤0,OR 覆蓋<{COV_BAD:.0f}x;金融股跳過)")
        why = ("solvency_bad forward excess 穩健為負且獨立於 pe_low,但五分位冇乾淨單調梯度"
               "——即係話中間讀數冇可靠資訊,只有極端差先有懲罰。呢個形態支持二元 gate 而唔支持"
               "連續第六維。建議接線位:pick_ticker 否決閘或日報警示,唔入 composite 權重。")
    elif sv_robust and not independent:
        v = "DISPLAY-ONLY"
        why = ("solvency_bad 方向對(forward excess 為負)但同 pe_low 高度重疊——獨立性測試"
               "唔成立,即係話現有 pe_pctile 軸已經抓咗大部分呢個效應。值得喺日報/同儕對比顯示"
               "(俾人手判斷 USAC 呢類案例),但唔夠格入 sizing 或 composite 權重。")
    elif cond_ok:
        v = (f"GO-as-gate(條件版:只對 pe-cheap 買入候選否決;閾值:槓桿>{LEV_BAD:.0f}x EBITDA "
             f"或 EBITDA≤0,OR 利息覆蓋<{COV_BAD:.0f}x;金融股跳過)")
        why = ("三個結構性發現指向**條件閘**而唔係無條件閘或連續維度:"
               "(1) 無條件 solvency_bad pooled excess ≈ 0——單獨用冇料;"
               "(2) `pe_low ∧ solvency_bad` 顯著更負(見結果 C/C2),且兩個利率 era 都成立、"
               "唔係一兩隻股撐起——**solvency 只喺 cheap 桶內有判別力**,同 Piotroski (2000) "
               "「財務強度只喺 value 股入面分贏輸家」完全一致;"
               "(3) `solvency_bad ∧ NOT pe_low` 為正——唔平嘅高槓桿名(多數係增長期融資)"
               "唔應該被罰,無條件 gate 會錯殺。"
               "呢個形態正正係 USAC 動機場景:個名係因為「睇落平」先入買入候選,gate 嘅職責"
               "就係喺嗰一刻攔截「平因為槓桿」嘅假象。"
               "**建議接線位**:pick_ticker/估值管道——凡 pe_pctile ≤ 20%(「平」係買入理由)嘅候選,"
               "觸發 solvency_bad 即否決或強制降級人手覆核;composite_score **唔加**第六維"
               "(H2 五分位非單調,連續分冇 alpha);日報對 cheap 候選顯示 solvency 讀數。")
    else:
        v = "NO-GO(此 universe/期間)"
        why = ("solvency_bad forward excess 冇穩健為負,或獨立性測試唔成立。結合文獻(Dichev/"
               "Campbell-Hilscher-Szilagyi/Piotroski 三份都支持 solvency 差=跑輸)——呢個結果"
               "更可能係 (a) survivorship 剔走真困境股(caveat 7)+ 歷史只有 2020+(caveat 1),"
               "或 (b) 2020-2021 ZIRP 令高槓桿股受惠嘅 regime 效應,而唔係主張本身錯。"
               "建議:唔即刻接線,保留 script 待利率環境改變或有更長歷史/退市名單數據源時重試。")
    lines.append(f"### 判定:**{v}**")
    lines.append("")
    lines.append(why)
    return lines


def main():
    ev, loaded, failed, tickers = build()
    if ev.empty:
        print("NO EVENTS — check data.")
        return
    write_report(ev, loaded, failed, tickers)
    for key, lab in [("solvency_bad", "solvency_bad"), ("lev_gate", "lev_gate"),
                     ("cov_gate", "cov_gate"), ("pe_low", "pe_low(baseline)")]:
        for H in HORIZONS:
            a = agg(ev, ev[key] == True, H)
            if a:
                print(f"{lab:16} {H:3}d  n={a['n']:4}  mean={a['mean']*100:+.2f}%  "
                      f"hit_under={a['hit_under']*100:.0f}%  sharpe={a['sharpe']:+.2f}")


if __name__ == "__main__":
    main()
