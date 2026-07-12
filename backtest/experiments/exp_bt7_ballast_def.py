"""BT-7: ballast (defensive sleeve) DEFINITION comparison — is XLP/XLU/XLV
equal-weight (the current Karst-AA ballast, `docs/2026-07-12_all_active_design_response.md`
§2.3/§8c) still the right composition, or does a pre-registered alternative
discharge the ballast's DUTIES better?

Background
----------
§8c of the AA design doc lists the ballast's 5 duties (non-zero-beta equity /
downside capture <1 / orthogonal to the T(thesis) sleeve / liquidity / no
option-rent-but-has-income) and pre-registers BT-7 as the test: "trio vs
trio+USMV vs 五隻分散版 vs 純 min-vol, HK 稅後, 判官 = downside capture + 三壓力
窗 DD + 對 QQQ 相關 + 淨回報；預先註冊，唔准鬥靚回報擇優". This script is that
test. **The judge is duty-fulfillment, not prettier absolute returns — ranking
is by pre-registered criteria, never by hunting for the highest-CAGR candidate.**

Candidates (pre-registered, fixed set)
-----------------------------------------
  B1  XLP/XLU/XLV equal-weight                    (incumbent / current AA spec)
  B2  XLP/XLU/XLV/USMV equal-weight                (adds min-vol factor)
  B3  XLP/XLU/XLV/VIG equal-weight                 (adds dividend-growth factor;
                                                     corrected from an earlier
                                                     5-way XLP/XLU/XLV/VIG/XLRE
                                                     draft — XLRE (2015-10 listing)
                                                     and GLD (not equity, breaks
                                                     the non-zero-beta-equity
                                                     mandate) were both rejected)
  B4  USMV alone                                   (pure min-vol, low-yield,
                                                     tax-efficient extreme)
  B5  DIA alone                                    (SPDR Dow Jones ETF — a formal
                                                     nominated candidate, NOT a
                                                     control; hypothesis to test,
                                                     not assume: lower yield than
                                                     the trio -> smaller tax
                                                     leakage, lower tech content
                                                     than SPY -> lower QQQ corr,
                                                     value/cyclical tilt -> maybe
                                                     strong in a 2022-style
                                                     rate-hike tape)
  B6  Mag7 equal-weight, MONTHLY rebalanced        (AAPL/MSFT/GOOGL/AMZN/NVDA/
                                                     META/TSLA, self-assembled
                                                     because MAGS the ETF only
                                                     listed 2023 -- too short a
                                                     history to be useful here;
                                                     META's 2012-05-18 listing is
                                                     the binding constraint on
                                                     this candidate's window)
                                                     **EXPLICIT NEGATIVE CONTROL**
                                                     — put through the exact same
                                                     5 judges as everyone else,
                                                     predicted (not assumed) to
                                                     fail downside-capture and
                                                     QQQ-orthogonality badly; its
                                                     purpose is to quantify what
                                                     "using an offense asset as
                                                     ballast" costs, not to be a
                                                     real B1-replacement option.

B5/B6 were added mid-assignment via an explicit spec-update instruction from
the task coordinator (same authoritative instruction channel as the original
assignment, received before this script's first execution) — judges and tax
treatment are UNCHANGED by that addendum, only the candidate roster grew, so
this remains a pre-registered-candidates study, not a post-hoc adjustment.

Method (mirror / increment / horizon)
--------------------------------------
Mirror     : static long-only equal-weight buy-and-hold baskets (NOT a
             200SMA-gated switching study like `exp_ballast_parking.py` — BT-7
             asks "which basket IS the ballast", not "when do you park in it").
             B1-B5 rebalance DAILY (equal-weight composite of daily returns);
             B6 rebalances MONTHLY per spec (concentrated 7-stock synthetic
             index — daily rebalance of single-name mega-caps would be an
             unrealistic execution assumption the other ETF-based baskets
             don't share).
Increment  : each candidate differs from B1 only in its member set (B2 =
             B1+USMV, B3 = B1+VIG, B4 = USMV alone, B5 = DIA alone, B6 = Mag7
             synthetic) — HK tax formula, judge definitions, common-window
             discipline held fixed across all six.
Horizon    : continuous multi-year buy-and-hold, no timing/rotation between
             ballast candidates (§8c point 3: "防守股之間擇時：唔做").

Common-window discipline (STRICT — this is the core methodological constraint)
--------------------------------------------------------------------------------
USMV IPO'd 2011-10-20, VIG IPO'd 2006-05-02, XLP/XLU/XLV 1998-12-22, DIA
1998-01-20, META 2012-05-18 (binding constraint for B6's Mag7 synthetic — all
verified via `data.load()`, not assumed). Different candidates therefore have
DIFFERENT native histories. **Every continuous aggregate metric (downside
capture, rolling QQQ correlation, HK-net CAGR, tax leakage, Sharpe, MaxDD, beta)
is computed on a shared "league" window, with B1 ALWAYS recomputed on that same
restricted window as the anchor** — never a raw B1-full-history number compared
against a short-history candidate's number. Three leagues:
  League A (USMV window) = XLP∩XLU∩XLV∩USMV common index -> {B1(anchor), B2, B4, B5}
  League B (VIG window)  = XLP∩XLU∩XLV∩VIG  common index -> {B1(anchor), B3, B5}
  League C (Mag7 window) = XLP∩XLU∩XLV∩Mag7(7-way) common index -> {B1(anchor), B5, B6}
DIA (B5) has the longest native history of any candidate (1998-01-20, even
before XLP/XLU/XLV) so it is never the binding constraint and can legitimately
sit in all three leagues as a genuine head-to-head vs the B1 anchor in each.
B2/B4 are never compared directly against B3 or B6 (different windows) — only
each candidate's standing vs the SAME-WINDOW B1 anchor is used for ranking
within its own league(s). The 3 discrete stress-window judge (below) is the
one exception: it uses FIXED absolute calendar dates identical for every
candidate, so no window-matching is needed there — only a data-availability
check (candidates that IPO'd after a stress window get "n/a, pre-inception",
never a fabricated number).

Judges (pre-registered — 4 duty criteria ranked + 1 reference-only)
-----------------------------------------------------------------------
  1. Downside capture vs SPY (ratio of avg return in SPY-down months; full
     league window AND 3y-rolling summary) — LOWER is better (duty: falls less
     than SPY in a decline).
  2. Performance in 3 stress windows (2011-08 European debt-ceiling/downgrade
     correction, 2020 COVID crash, 2022 rate-hike full year) — ranked by
     average excess return vs SPY over the windows each candidate has data
     for (n/a windows excluded from that candidate's average, flagged).
     2008 (GFC) is reported SEPARATELY, B1-only, per this study's original
     pre-registered spec (unchanged by the B5/B6 addendum) — DIA (B5)
     technically has 2008 data too but is intentionally excluded from that
     sub-report to keep the pre-registered scope stable (see Caveats).
  3. 126-trading-day rolling correlation to QQQ (orthogonality to the T
     sleeve) — LOWER is better (ballast's value is partly "not being the same
     bet" as the AI-heavy long book).
  4. HK after-tax net CAGR (`r_net = r_adj - 0.30*dy`, repo-standard formula)
     + annualized dividend-tax leakage in pp (CAGR_gross - CAGR_net) — one of
     4 EQUALLY-weighted judges, not a tie-breaker.
  5. (REFERENCE ONLY, not ranked) Sharpe, MaxDD.
Total judge score per league = sum of ranks (1=best) across judges 1-4.

Internal coupling readout (required, static approximation)
------------------------------------------------------------
Lower ballast beta -> the LEAP overlay sleeve must supply more of the AA
design's target portfolio delta -> pays more rent. Using
`backtest/results/2026-07-12_leap_rent_delta_ledger.md`'s AA arithmetic
(ballast weight 45% (bull-case midpoint) x beta + thesis weight 25% x beta1.20
= base sleeve delta; SPY 0.50-delta rent-per-$1-delta-notional annualized =
11.64%), for each candidate X vs the B1 anchor in the SAME league window:
    delta_beta            = beta_B1(league) - beta_X(league)
    delta_needed_from_LEAP = 0.45 * delta_beta        (fraction of NAV)
    rent_change_pp/yr      = 11.64% * delta_needed_from_LEAP
This is a STATIC, first-order approximation (fixed weights taken verbatim from
the ledger's own illustrative assumptions, not re-fit here) and is
level-independent of the target-delta band (100/115/130%) by construction.

Additionally, EVERY candidate (incl. B1) gets a "熊市 delta 地台" (bear-market
delta floor) column: `floor = 0.60*beta_X(league) + 0.25*1.20`, i.e. the
portfolio's minimum equity exposure if this candidate were the ballast AND the
LEAP sleeve were fully gated OUT (a full bear-market de-risk). This makes
concrete, in one number, why putting a high-beta "offense" asset in the
ballast seat removes the portfolio's ability to de-risk in a bear market —
B6 (Mag7) is expected (not assumed — verified against the actual computed
numbers below) to show a floor near or above 100%, which is the specific
teaching point this column exists to demonstrate.

Cross-foot (hard asserts): NAV > 0 every bar of every candidate/league
simulation; league window indices verified as true index intersections (no
reindex-introduced NaNs).

Run:  PYTHONUTF8=1 python backtest/experiments/exp_bt7_ballast_def.py
Writes: backtest/results/2026-07-13_bt7_ballast_definition.md
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import metrics                                     # noqa: E402
from data import load                              # noqa: E402

TD = 252
RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-13_bt7_ballast_definition.md")

MAG7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

CANDIDATES = {
    "B1": ["XLP", "XLU", "XLV"],
    "B2": ["XLP", "XLU", "XLV", "USMV"],
    "B3": ["XLP", "XLU", "XLV", "VIG"],
    "B4": ["USMV"],
    "B5": ["DIA"],
    "B6": MAG7,
}
CAND_LABEL = {
    "B1": "B1 XLP/XLU/XLV",
    "B2": "B2 XLP/XLU/XLV/USMV",
    "B3": "B3 XLP/XLU/XLV/VIG",
    "B4": "B4 USMV(單獨)",
    "B5": "B5 DIA(單獨)",
    "B6": "B6 Mag7等權合成(月度reb, 負面對照)",
}
MONTHLY_REBAL = {"B6"}   # everyone else rebalances daily (equal_weight_basket)

# beta-rent coupling constants, taken verbatim from
# backtest/results/2026-07-12_leap_rent_delta_ledger.md (§5 AA arithmetic table)
BALLAST_WEIGHT = 0.45        # bull-case ballast allocation midpoint
THESIS_DELTA_TERM = 0.25 * 1.20   # thesis weight 25% x thesis beta 1.20 (held fixed)
RENT_PER_DELTA_050 = 0.1164  # SPY 0.50-delta rent / $1 delta-notional, annualized
BEAR_FLOOR_WEIGHT = 0.60     # 熊市 delta 地台 ballast weight (LEAP fully gated out)

STRESS_WINDOWS = [
    ("2011-08 歐債", pd.Timestamp("2011-08-01"), pd.Timestamp("2011-10-03")),
    ("2020 COVID", pd.Timestamp("2020-02-19"), pd.Timestamp("2020-03-23")),
    ("2022 加息年", pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31")),
]
STRESS_2008 = ("2008 GFC(B1限定)", pd.Timestamp("2008-01-01"), pd.Timestamp("2008-12-31"))

ASSERT_N = {"n": 0}


# ---------------------------------------------------------------------------
# Data — HK-net total-return series (r_net) + gross/pretax (r_adj), repo-
# standard formula (`exp_ballast_parking.build_core_only`), extended here to
# also keep r_adj so the tax-leakage-in-pp judge can be computed directly.
# ---------------------------------------------------------------------------

def build_core_only(symbol: str):
    raw = load(symbol)
    adj = load(symbol, adjusted=True)
    prov = [(symbol, raw.attrs.get("source", "?"), len(raw),
             str(raw.index.min().date()), str(raw.index.max().date())),
            (f"{symbol}(adj)", adj.attrs.get("source", "?"), len(adj),
             str(adj.index.min().date()), str(adj.index.max().date()))]
    close = raw["close"]
    r_adj = adj["close"].pct_change()
    r_raw = close.pct_change()
    dy = (r_adj - r_raw).clip(lower=0.0)
    dy = dy.where(dy > 1e-4, 0.0)          # 1bp threshold: kill adjustment rounding noise
    r_net = r_adj - 0.30 * dy              # HK 30% withholding on dividends
    df = pd.DataFrame({"close": close, "r_net": r_net, "r_adj": r_adj}).dropna()
    return df, prov


def equal_weight_basket(dfs: dict, symbols: list) -> pd.DataFrame:
    """Equal-weight, daily-rebalanced composite of r_net/r_adj on the members'
    common trading-day intersection. Single-member baskets pass through."""
    idx = dfs[symbols[0]].index
    for s in symbols[1:]:
        idx = idx.intersection(dfs[s].index)
    r_net = pd.concat([dfs[s]["r_net"].reindex(idx) for s in symbols], axis=1).mean(axis=1)
    r_adj = pd.concat([dfs[s]["r_adj"].reindex(idx) for s in symbols], axis=1).mean(axis=1)
    out = pd.DataFrame({"r_net": r_net, "r_adj": r_adj}, index=idx)
    assert not out.isna().any().any(), f"NaN in basket {symbols} on its own intersection index"
    return out


def nav_from_ret(r: pd.Series) -> np.ndarray:
    rv = r.values.astype("float64").copy()
    rv[0] = 0.0
    nav = np.cumprod(1.0 + rv)
    assert np.all(nav > 0), "non-positive NAV in nav_from_ret"
    ASSERT_N["n"] += len(nav)
    return nav


def monthly_rebalance_basket(dfs: dict, symbols: list) -> pd.DataFrame:
    """Equal-weight basket rebalanced at the first trading day of each
    calendar month; weights drift with price WITHIN a month (true monthly-
    rebalance buy-and-hold), used only for B6's concentrated 7-stock synthetic
    per spec ("Mag7 等權合成組合...月度 rebalance")."""
    idx = dfs[symbols[0]].index
    for s in symbols[1:]:
        idx = idx.intersection(dfs[s].index)
    idx = idx.sort_values()
    n = len(idx)
    nav_net = {s: nav_from_ret(dfs[s]["r_net"].reindex(idx)) for s in symbols}
    nav_gross = {s: nav_from_ret(dfs[s]["r_adj"].reindex(idx)) for s in symbols}

    month_codes = np.array([d.year * 12 + d.month for d in idx])
    rebal_pos = set(np.where(np.diff(month_codes, prepend=month_codes[0] - 1) != 0)[0].tolist())

    def simulate(nav_dict):
        shares = {s: (1.0 / len(symbols)) / nav_dict[s][0] for s in symbols}
        port_val = np.empty(n)
        for i in range(n):
            if i in rebal_pos and i != 0:
                pv_today = sum(shares[s] * nav_dict[s][i] for s in symbols)
                for s in symbols:
                    shares[s] = (pv_today / len(symbols)) / nav_dict[s][i]
            port_val[i] = sum(shares[s] * nav_dict[s][i] for s in symbols)
        assert np.all(port_val > 0), "non-positive NAV in monthly_rebalance_basket"
        ASSERT_N["n"] += n
        return port_val

    pv_net = simulate(nav_net)
    pv_gross = simulate(nav_gross)
    r_net = pd.Series(pv_net, index=idx).pct_change()
    r_net.iloc[0] = 0.0
    r_adj = pd.Series(pv_gross, index=idx).pct_change()
    r_adj.iloc[0] = 0.0
    out = pd.DataFrame({"r_net": r_net, "r_adj": r_adj}, index=idx)
    assert not out.isna().any().any(), f"NaN in monthly-rebal basket {symbols}"
    return out


# ---------------------------------------------------------------------------
# Downside capture (monthly) — full-window + 3y-rolling (36mo, min 4 down-months)
# ---------------------------------------------------------------------------

def monthly_ret_from_nav(nav: np.ndarray, idx: pd.DatetimeIndex) -> pd.Series:
    s = pd.Series(nav, index=idx)
    m = s.resample("ME").last()
    return m.pct_change().dropna()


def downside_capture(cand_m: pd.Series, spy_m: pd.Series) -> float:
    idx = cand_m.index.intersection(spy_m.index)
    c, s = cand_m.reindex(idx), spy_m.reindex(idx)
    down = s < 0
    if int(down.sum()) < 3:
        return np.nan
    return float(c[down].mean() / s[down].mean())


def rolling_downside_capture(cand_m: pd.Series, spy_m: pd.Series,
                             window: int = 36, min_down: int = 4) -> pd.Series:
    idx = cand_m.index.intersection(spy_m.index)
    c, s = cand_m.reindex(idx), spy_m.reindex(idx)
    vals, outidx = [], []
    for i in range(window, len(idx) + 1):
        cw, sw = c.iloc[i - window:i], s.iloc[i - window:i]
        down = sw < 0
        if int(down.sum()) < min_down:
            vals.append(np.nan)
        else:
            vals.append(float(cw[down].mean() / sw[down].mean()))
        outidx.append(idx[i - 1])
    return pd.Series(vals, index=outidx)


def rolling_corr_126(cand_r: pd.Series, qqq_r: pd.Series, window: int = 126) -> pd.Series:
    idx = cand_r.index.intersection(qqq_r.index)
    c, q = cand_r.reindex(idx), qqq_r.reindex(idx)
    return c.rolling(window).corr(q)


def window_return(r: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> float:
    seg = r[(r.index >= start) & (r.index <= end)]
    if len(seg) == 0:
        return np.nan
    return float(np.prod(1.0 + seg.fillna(0.0)) - 1.0)


# ---------------------------------------------------------------------------
# League-level metrics bundle
# ---------------------------------------------------------------------------

def league_metrics(cand_r_net: pd.Series, cand_r_adj: pd.Series,
                   spy_r_net_full: pd.Series, qqq_r_net_full: pd.Series,
                   idx: pd.DatetimeIndex) -> dict:
    nav_net = nav_from_ret(cand_r_net.reindex(idx))
    nav_gross = nav_from_ret(cand_r_adj.reindex(idx))
    spy_matched = spy_r_net_full.reindex(idx)
    nav_spy = nav_from_ret(spy_matched)

    cagr_net = metrics.cagr(nav_net)
    cagr_gross = metrics.cagr(nav_gross)
    leakage_pp = (cagr_gross - cagr_net) * 100.0
    sharpe = metrics.ann_sharpe(cand_r_net.reindex(idx).values[1:])
    maxdd = metrics.max_drawdown(nav_net)
    _, beta, _ = metrics.jensen_alpha(cand_r_net.reindex(idx).values[1:],
                                       spy_matched.values[1:])

    cand_m = monthly_ret_from_nav(nav_net, idx)
    spy_m = monthly_ret_from_nav(nav_spy, idx)
    dc_full = downside_capture(cand_m, spy_m)
    dc_roll = rolling_downside_capture(cand_m, spy_m)
    dc_roll_valid = dc_roll.dropna()

    corr = rolling_corr_126(cand_r_net.reindex(idx), qqq_r_net_full.reindex(idx))
    corr_valid = corr.dropna()

    return {
        "CAGR_net": cagr_net, "CAGR_gross": cagr_gross, "LeakagePP": leakage_pp,
        "Sharpe": sharpe, "MaxDD": maxdd, "Beta": beta,
        "DC_full": dc_full,
        "DC_roll_mean": float(dc_roll_valid.mean()) if len(dc_roll_valid) else np.nan,
        "DC_roll_median": float(dc_roll_valid.median()) if len(dc_roll_valid) else np.nan,
        "DC_roll_n": int(len(dc_roll_valid)),
        "Corr_mean": float(corr_valid.mean()) if len(corr_valid) else np.nan,
        "Corr_median": float(corr_valid.median()) if len(corr_valid) else np.nan,
        "Days": len(idx),
    }


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _p(x, dec=1):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:+.{dec}f}%"


def _p0(x, dec=1):
    """Non-signed percent (for ratios/levels, not deltas)."""
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:.{dec}f}%"


def _n(x, dec=2):
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.{dec}f}"


def rank_col(values: dict, higher_better: bool) -> dict:
    """values: {cand: number (nan allowed)} -> {cand: rank int (1=best)}, nan
    ranked last (worst) without crashing the sum."""
    items = [(k, v) for k, v in values.items()]
    finite = [(k, v) for k, v in items if np.isfinite(v)]
    finite.sort(key=lambda kv: kv[1], reverse=higher_better)
    ranks = {}
    for i, (k, v) in enumerate(finite, start=1):
        ranks[k] = i
    worst_rank = len(finite) + 1
    for k, v in items:
        if k not in ranks:
            ranks[k] = worst_rank
    return ranks


def build_ranks(league: dict, members: list, stress_avg_excess_fn) -> dict:
    dc_vals = {c: league[c]["DC_full"] for c in members}
    stress_vals = {c: stress_avg_excess_fn(c) for c in members}
    corr_vals = {c: league[c]["Corr_median"] for c in members}
    cagr_vals = {c: league[c]["CAGR_net"] for c in members}
    r_dc = rank_col(dc_vals, higher_better=False)       # lower DC = better
    r_stress = rank_col(stress_vals, higher_better=True)  # higher excess = better
    r_corr = rank_col(corr_vals, higher_better=False)   # lower corr = better
    r_cagr = rank_col(cagr_vals, higher_better=True)    # higher CAGR = better
    total = {c: r_dc[c] + r_stress[c] + r_corr[c] + r_cagr[c] for c in members}
    return {"DC": r_dc, "Stress": r_stress, "Corr": r_corr, "CAGR": r_cagr, "Total": total}


def coupling_rows(league_name: str, league_dict: dict, members: list, anchor: str = "B1") -> list:
    beta_anchor = league_dict[anchor]["Beta"]
    rows = []
    for c in members:
        beta_x = league_dict[c]["Beta"]
        d_beta = beta_anchor - beta_x
        d_needed = BALLAST_WEIGHT * d_beta
        d_rent_pp = RENT_PER_DELTA_050 * d_needed * 100.0
        floor = BEAR_FLOOR_WEIGHT * beta_x + THESIS_DELTA_TERM
        rows.append({"cand": c, "league": league_name, "beta_anchor": beta_anchor,
                     "beta_x": beta_x, "d_beta": d_beta, "d_needed": d_needed,
                     "d_rent_pp": d_rent_pp, "floor": floor})
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    prov_all = []

    all_syms = sorted({s for syms in CANDIDATES.values() for s in syms} | {"SPY", "QQQ"})
    dfs = {}
    for sym in all_syms:
        df, prov = build_core_only(sym)
        dfs[sym] = df
        prov_all += prov
    print(f"loaded {len(all_syms)} symbols ({time.time()-t0:.0f}s)", flush=True)

    spy_r_net = dfs["SPY"]["r_net"]
    qqq_r_net = dfs["QQQ"]["r_net"]

    baskets = {}
    for c, syms in CANDIDATES.items():
        if c in MONTHLY_REBAL:
            baskets[c] = monthly_rebalance_basket(dfs, syms)
        else:
            baskets[c] = equal_weight_basket(dfs, syms)

    # League windows: intersection of each member's basket index (B5/DIA has
    # the longest native history of any candidate so is never the binding
    # constraint; B1 recomputed on each league's window as the anchor).
    league_a_members = ["B1", "B2", "B4", "B5"]
    league_b_members = ["B1", "B3", "B5"]
    league_c_members = ["B1", "B5", "B6"]

    def intersect_indices(members):
        idx = baskets[members[0]].index
        for m in members[1:]:
            idx = idx.intersection(baskets[m].index)
        return idx

    league_a_idx = intersect_indices(league_a_members)
    league_b_idx = intersect_indices(league_b_members)
    league_c_idx = intersect_indices(league_c_members)
    print(f"League A (USMV window): {league_a_idx[0].date()} -> {league_a_idx[-1].date()} "
          f"({len(league_a_idx)}d)", flush=True)
    print(f"League B (VIG window): {league_b_idx[0].date()} -> {league_b_idx[-1].date()} "
          f"({len(league_b_idx)}d)", flush=True)
    print(f"League C (Mag7 window): {league_c_idx[0].date()} -> {league_c_idx[-1].date()} "
          f"({len(league_c_idx)}d)", flush=True)
    for lidx in (league_a_idx, league_b_idx, league_c_idx):
        assert lidx.is_monotonic_increasing

    # Table A: each candidate's OWN native full window (context only, NOT for ranking)
    native_idx = {c: baskets[c].index for c in CANDIDATES}
    table_a = {}
    for c in CANDIDATES:
        m = league_metrics(baskets[c]["r_net"], baskets[c]["r_adj"], spy_r_net, qqq_r_net,
                           native_idx[c])
        table_a[c] = m
        print(f"{c} native window {native_idx[c][0].date()}->{native_idx[c][-1].date()} "
              f"({len(native_idx[c])}d): CAGR_net {m['CAGR_net']*100:.2f}% "
              f"beta {m['Beta']:.2f}", flush=True)

    league_a = {c: league_metrics(baskets[c]["r_net"], baskets[c]["r_adj"], spy_r_net,
                                  qqq_r_net, league_a_idx) for c in league_a_members}
    league_b = {c: league_metrics(baskets[c]["r_net"], baskets[c]["r_adj"], spy_r_net,
                                  qqq_r_net, league_b_idx) for c in league_b_members}
    league_c = {c: league_metrics(baskets[c]["r_net"], baskets[c]["r_adj"], spy_r_net,
                                  qqq_r_net, league_c_idx) for c in league_c_members}
    print(f"League metrics done ({time.time()-t0:.0f}s)", flush=True)

    # ------------------------------------------------------------------
    # Stress windows (fixed absolute dates, ALL candidates + SPY, n/a for
    # pre-inception rather than fabricated numbers)
    # ------------------------------------------------------------------
    stress_rows = {}   # cand -> {window_name: (cret, sret, excess)}
    for c in CANDIDATES:
        r = baskets[c]["r_net"]
        row = {}
        for wname, ws, we in STRESS_WINDOWS:
            cret = window_return(r, ws, we)
            sret = window_return(spy_r_net, ws, we)
            excess = cret - sret if np.isfinite(cret) and np.isfinite(sret) else np.nan
            row[wname] = (cret, sret, excess)
        stress_rows[c] = row
    # 2008, B1 only (unchanged pre-registered scope)
    b1_2008 = window_return(baskets["B1"]["r_net"], STRESS_2008[1], STRESS_2008[2])
    spy_2008 = window_return(spy_r_net, STRESS_2008[1], STRESS_2008[2])

    def stress_avg_excess(cand: str) -> float:
        vals = [v[2] for v in stress_rows[cand].values() if np.isfinite(v[2])]
        return float(np.mean(vals)) if vals else np.nan

    # ------------------------------------------------------------------
    # Ranking within each league (1=best), judges 1/2/3/4 only (Sharpe/MaxDD
    # are reference, NOT ranked)
    # ------------------------------------------------------------------
    ranks_a = build_ranks(league_a, league_a_members, stress_avg_excess)
    ranks_b = build_ranks(league_b, league_b_members, stress_avg_excess)
    ranks_c = build_ranks(league_c, league_c_members, stress_avg_excess)
    print(f"League A total ranks (1=best): {ranks_a['Total']}", flush=True)
    print(f"League B total ranks (1=best): {ranks_b['Total']}", flush=True)
    print(f"League C total ranks (1=best): {ranks_c['Total']}", flush=True)

    # ------------------------------------------------------------------
    # Beta-rent coupling + bear-market delta floor (static approximation),
    # every candidate incl. B1, one row per (league, candidate)
    # ------------------------------------------------------------------
    coupling = (coupling_rows("A", league_a, league_a_members)
                + coupling_rows("B", league_b, league_b_members)
                + coupling_rows("C", league_c, league_c_members))
    b6_floor = next(r["floor"] for r in coupling if r["cand"] == "B6")
    print(f"B6 (Mag7) 熊市 delta 地台 = {b6_floor*100:.1f}%", flush=True)

    # ------------------------------------------------------------------
    # Write results markdown
    # ------------------------------------------------------------------
    L = []
    add = L.append
    add("# Result — BT-7: ballast (defensive sleeve) definition comparison — "
        "B1 XLP/XLU/XLV vs 5 pre-registered alternatives (incl. 1 negative control)")
    add("")
    add("**Date:** 2026-07-13  **Script:** `backtest/experiments/exp_bt7_ballast_def.py`  "
        "**Status:** active")
    add("")
    add("## Question")
    add("")
    add("Karst-AA 設計（`docs/2026-07-12_all_active_design_response.md` §2.3/§8c）目前將 "
        "ballast（防守／壓艙 sleeve）定義死做 XLP/XLU/XLV 等權。用戶追問：「防守」應該點定義？"
        "要唔要機制／擇時？§8c 已經預先註冊呢個 BT-7 測試：候選 basket 按「職責達成度」對比"
        "（唔係鬥靚回報擇優）。任務中途用戶再加兩個候選：B5 DIA（正式提名，非對照）、B6 Mag7 "
        "月度 rebalance 合成組合（明文標示反面對照組，示範「offense 資產擺 ballast 位」嘅代價）。")
    add("")
    add("## Method")
    add("")
    add("- **候選（預先註冊，六個，唔准再加減）**：")
    add("  - B1 = XLP/XLU/XLV 等權（現行）")
    add("  - B2 = B1 + USMV 等權（加 min-vol 因子）")
    add("  - B3 = B1 + VIG 等權（加股息增長因子——原稿 B3 係五隻 XLP/XLU/XLV/VIG/XLRE，因 "
        "XLRE 2015-10 先上市窗太短、GLD「唔係股票，違反非零 beta equity mandate」被拒，喺 "
        "prompt 已更正做四隻版）")
    add("  - B4 = USMV 單獨（純 min-vol、低息、稅務效率極端案例）")
    add("  - B5 = DIA 單獨（**正式提名候選**——假設：低息過 trio 稅漏細、科技含量低過 SPY "
        "對 QQQ 相關應該低啲、2022 型加息市可能係強項——全部用數證實或推翻，唔假設）")
    add("  - B6 = Mag7 等權月度 rebalance 合成組合（AAPL/MSFT/GOOGL/AMZN/NVDA/META/TSLA；"
        "自砌因 MAGS ETF 2023 年先上市，數據太短；**明文負面對照組**，預期喺 downside "
        "capture、QQQ 相關兩項判官大敗——收錄目的係量化示範「offense 資產擺 ballast 位會點」，"
        "唔係真落選候選）")
    add("- **Mirror/Increment/Horizon**：B1-B5 靜態長倉等權、逐日重平衡 buy-and-hold（唔係 "
        "200SMA 閘控嘅停泊研究，BT-7 問「邊個籃子先係防守」，唔係「幾時泊入去」）；B6 因為係"
        "集中 7 隻大型股嘅合成組合，逐日重平唔現實，改用**月度 rebalance**（首個交易日重設等權，"
        "月內權重隨價格自然漂移）——呢個係 B1-B5 同 B6 之間，喺重平頻率呢個維度上，刻意唔一致"
        "嘅一點，因為兩者本身資產性質唔同（ETF 籃子 vs 集中股票組合），見 Caveats。")
    add("- **HK 稅**：全部候選用 repo 標準 `r_net = r_adj - 0.30*dy`（1bp 門檻殺 adjustment 捨入"
        "雜訊），同 `exp_ballast_parking.py` 完全一致嘅公式。")
    add("")
    add("## 共同窗口聲明（Common-window discipline — 硬性約束）")
    add("")
    add("USMV 2011-10-20、VIG 2006-05-02、XLP/XLU/XLV 1998-12-22、DIA 1998-01-20、META "
        "2012-05-18（Mag7 七隻入面上市最遲，係 B6 窗口嘅硬約束）上市——全部由 `data.load()` "
        "實測，唔係假設。連續型聚合指標（downside capture／QQQ 相關／HK淨 CAGR／稅漏／Sharpe／"
        "MaxDD／beta）**一律喺「League」共同窗口計，B1 每次都喺嗰個窗重新計一份做錨**：")
    add(f"- **League A（USMV 窗）** = XLP∩XLU∩XLV∩USMV = "
        f"{league_a_idx[0].date()} → {league_a_idx[-1].date()}（{len(league_a_idx)} 個交易日）"
        "，含 {B1(錨), B2, B4, B5}。")
    add(f"- **League B（VIG 窗）** = XLP∩XLU∩XLV∩VIG = "
        f"{league_b_idx[0].date()} → {league_b_idx[-1].date()}（{len(league_b_idx)} 個交易日）"
        "，含 {B1(錨), B3, B5}。")
    add(f"- **League C（Mag7 窗）** = XLP∩XLU∩XLV∩Mag7(7隻) = "
        f"{league_c_idx[0].date()} → {league_c_idx[-1].date()}（{len(league_c_idx)} 個交易日）"
        "，含 {B1(錨), B5, B6}——B5 (DIA) 歷史最長，喺三個 league 都唔係約束者，先可以合法咁"
        "同時出現喺三個 league 度同 B1 錨逐一對比。")
    add("- B2/B4 同 B3/B6 **從無直接對比**（唔同窗口）——排名淨係喺各自 league 入面同 B1 錨做；"
        "B5 因為歷史夠長，係唯一喺三個 league 都有齊數嘅非錨候選。")
    add("- 三個壓力窗（judge 2）例外：用固定絕對日期，對每個候選一致，唔需要窗口配對——只需要"
        "數據存在性檢查（未上市 = n/a，唔會捏造數字）。")
    add("")
    add("## Data provenance (`backtest/data.py` `load()`)")
    add("")
    add("| Series | Source | Rows | From | To |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in prov_all:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")

    # -- Table A: native full-window context (NOT for ranking) --------------
    add("## Table A — 各候選自身原生全窗（背景脈絡，唔用嚟排名）")
    add("")
    add("| 候選 | 原生窗 | CAGR(HK淨) | 稅漏 pp/yr | Sharpe | MaxDD | β vs SPY |")
    add("|---|---|---|---|---|---|---|")
    for c in CANDIDATES:
        m = table_a[c]
        add(f"| {CAND_LABEL[c]} | {native_idx[c][0].date()}→{native_idx[c][-1].date()} | "
            f"{_p(m['CAGR_net'])} | {m['LeakagePP']:+.2f} | {_n(m['Sharpe'])} | "
            f"{_p(m['MaxDD'])} | {_n(m['Beta'])} |")
    add("")

    def emit_league_table(title: str, window_note: str, league: dict, members: list,
                          ranks: dict):
        add(f"## {title}")
        add("")
        add(window_note)
        add("")
        add("| 候選 | DC 全窗 | DC 3y-rolling(中位/n) | 三壓力窗平均超額(vs SPY) | "
            "QQQ corr 126d(中位) | HK淨CAGR | 稅漏pp/yr | Sharpe(參考) | MaxDD(參考) | "
            "β vs SPY |")
        add("|---|---|---|---|---|---|---|---|---|---|")
        for c in members:
            m = league[c]
            se = stress_avg_excess(c)
            add(f"| {CAND_LABEL[c]} | {_p0(m['DC_full'])} | "
                f"{_p0(m['DC_roll_median'])}(n={m['DC_roll_n']}) | {_p(se)} | "
                f"{_n(m['Corr_median'])} | {_p(m['CAGR_net'])} | {m['LeakagePP']:+.2f} | "
                f"{_n(m['Sharpe'])} | {_p(m['MaxDD'])} | {_n(m['Beta'])} |")
        add("")
        add("排名（1=最佳；judge 1-4 排名，Sharpe/MaxDD 唔計分，純參考）：")
        add("")
        add("| 候選 | DC 排名 | 壓力窗排名 | QQQ相關排名 | HK淨CAGR排名 | **總分** |")
        add("|---|---|---|---|---|---|")
        for c in members:
            add(f"| {CAND_LABEL[c]} | {ranks['DC'][c]} | {ranks['Stress'][c]} | "
                f"{ranks['Corr'][c]} | {ranks['CAGR'][c]} | **{ranks['Total'][c]}** |")
        add("")

    emit_league_table(
        "判官表 1/3 — League A（USMV 窗，B1 vs B2 vs B4 vs B5）",
        f"共同窗：{league_a_idx[0].date()} → {league_a_idx[-1].date()}"
        f"（{len(league_a_idx)} 交易日）。B1 喺呢度係喺 League A 窗重新計嘅錨，唔係全歷史數字。",
        league_a, league_a_members, ranks_a)
    emit_league_table(
        "判官表 2/3 — League B（VIG 窗，B1 vs B3 vs B5）",
        f"共同窗：{league_b_idx[0].date()} → {league_b_idx[-1].date()}"
        f"（{len(league_b_idx)} 交易日）。B1 喺呢度係喺 League B 窗重新計嘅錨（同 League A 嘅 "
        "B1 數值唔同——唔同窗口，兩個都係合法嘅獨立錨，唔可以互相比較）。",
        league_b, league_b_members, ranks_b)
    emit_league_table(
        "判官表 3/3 — League C（Mag7 窗，B1 vs B5 vs B6【負面對照】）",
        f"共同窗：{league_c_idx[0].date()} → {league_c_idx[-1].date()}"
        f"（{len(league_c_idx)} 交易日，由 META 2012-05-18 上市決定）。B6 係明文負面對照組，"
        "呢張表嘅目的係用真實數字驗證/推翻「offense 資產做 ballast 會大敗」呢個預期，唔係揀"
        "佢做真候選。",
        league_c, league_c_members, ranks_c)

    # -- Stress window detail table -----------------------------------------
    add("## 三壓力窗明細表（固定絕對日期，全部候選 + SPY 錨；n/a = 未上市，唔係計算失敗）")
    add("")
    hdr = "| 候選 | " + " | ".join(f"{w[0]}（{w[1].date()}→{w[2].date()}）" for w in STRESS_WINDOWS) + " |"
    add(hdr)
    add("|---|" + "---|" * len(STRESS_WINDOWS))
    for c in CANDIDATES:
        cells = []
        for wname, ws, we in STRESS_WINDOWS:
            cret, sret, excess = stress_rows[c][wname]
            if not np.isfinite(cret):
                cells.append("n/a(未上市)")
            else:
                cells.append(f"{_p(cret)} (SPY {_p(sret)}, 超額 {_p(excess)})")
        add(f"| {CAND_LABEL[c]} | " + " | ".join(cells) + " |")
    add("")
    add(f"**2008 GFC（{STRESS_2008[1].date()}→{STRESS_2008[2].date()}，本 study 規格只報 B1，"
        f"B5/B6 加入後此規則不變）**：B1 {_p(b1_2008)} vs SPY {_p(spy_2008)}"
        f"（超額 {_p(b1_2008 - spy_2008)}）。B2/B4 因 USMV 2011-10 先上市、B6 因 META 2012-05 "
        "先上市，遠喺 2008 之後，天然無數據，唔存在「漏報」；B3 嘅成員 VIG、B5 嘅 DIA 技術上 "
        "2008 已上市（有真實數據），但本 study 依原定規格淨報 B1，唔擴大範圍——呢個係預先"
        "註冊決定，唔係事後選擇性隱藏。")
    add("")

    # -- 稅漏表 (Tax leakage table) -------------------------------------------
    add("## 稅漏表 — HK 30% 股息預扣稅年化滲漏（pp/yr = CAGR_gross − CAGR_net）")
    add("")
    add("| 候選 | 窗 | CAGR(稅前 r_adj) | CAGR(HK淨 r_net) | 稅漏 pp/yr |")
    add("|---|---|---|---|---|")
    for label, league, members in [("League A", league_a, league_a_members),
                                    ("League B", league_b, league_b_members),
                                    ("League C", league_c, league_c_members)]:
        for c in members:
            m = league[c]
            add(f"| {CAND_LABEL[c]} | {label} | {_p(m['CAGR_gross'])} | {_p(m['CAGR_net'])} | "
                f"{m['LeakagePP']:+.2f} |")
    add("")
    add("高息 XLU 系（B1/B2/B3 皆含）vs 低息 USMV（B4）vs DIA（B5，藍籌股息中等）vs Mag7"
        "（B6，多數低息/無息）嘅稅差係本測試焦點之一——見上表逐候選、逐 league 獨立呈現，唔淨係"
        "報一個 pooled 數字。")
    add("")

    # -- beta-租金咬合表 + 熊市 delta 地台 ------------------------------------
    add("## beta-租金咬合表（內部咬合讀數，STATIC APPROXIMATION）+ 熊市 delta 地台")
    add("")
    add(f"租金咬合公式：`Δneeded_from_LEAP = {BALLAST_WEIGHT:.2f} × (β_B1(league) − "
        f"β_X(league))`；`Δrent pp/NAV/yr = {RENT_PER_DELTA_050*100:.2f}% × "
        "Δneeded_from_LEAP`（SPY 0.50Δ 每 $1 delta-notional 年租，取自 "
        "`backtest/results/2026-07-12_leap_rent_delta_ledger.md` §5，115% band 下嘅例子作錨；"
        "此邊際 rent-per-beta-point 計算同目標 delta 水平（100/115/130%）無關，係 "
        "level-independent 嘅一階近似——band 只係語境，唔影響呢條數）。")
    add(f"熊市 delta 地台公式：`floor = {BEAR_FLOOR_WEIGHT:.2f} × β_X(league) + "
        f"{THESIS_DELTA_TERM:.2f}`（LEAP 全閘出時嘅組合最低曝險——ballast 權重假設由 45% 提升到 "
        "60%，模擬防守股占比喺去槓桿情境下自然上升；thesis sleeve 25%×β1.20 一項固定不變）。"
        "ballast 45%／thesis 25%×β1.20／熊市地台 60% 三組假設原封不動照搬自 leap_rent ledger "
        "同用戶最新指示，屬示意假設，唔係重新擬合嘅數字。")
    add("")
    add("| 候選 | League | β_B1(league,錨) | β_X(league) | Δβ(B1−X) | Δneeded_from_LEAP | "
        "Δrent pp/NAV/yr(若由 B1 換成呢個候選) | **熊市 delta 地台** |")
    add("|---|---|---|---|---|---|---|---|")
    for row in coupling:
        add(f"| {CAND_LABEL[row['cand']]} | {row['league']} | {_n(row['beta_anchor'])} | "
            f"{_n(row['beta_x'])} | {row['d_beta']:+.2f} | {_p(row['d_needed'])} | "
            f"{row['d_rent_pp']:+.2f} | {_p0(row['floor'])} |")
    add("")
    add(f"**教學位驗證**：B6（Mag7）喺 League C 嘅熊市 delta 地台 = {_p0(b6_floor)}"
        + (" —— 已驗證 >100%，即使 LEAP 全部閘出、ballast 都仲要用 offense 級 beta 頂住成個組合"
           "曝險，完全冇得喺熊市減磅，正正係「offense 資產擺 ballast 位」嘅代價量化。"
           if b6_floor > 1.0 else
           " —— 實測結果未過 100%，同賽前預期唔完全一致，數字如上，唔強行套教學敘事，"
           "以實測為準。"))
    add("")

    # -- Cross-foot -----------------------------------------------------------
    add("## Cross-foot verification")
    add("")
    add(f"- {ASSERT_N['n']:,} bar-level NAV>0 assertions across all candidate/league NAV "
        "builds (incl. B6's monthly-rebalance simulation), ALL passed.")
    add("- 每個 basket 嘅組成標的索引交集喺 `equal_weight_basket()`/`monthly_rebalance_basket()` "
        "內部 assert 冇 NaN——複合報酬只喺全部成員都有數嗰啲交易日先計。")
    add("- League A/B/C 索引各自驗證 `is_monotonic_increasing`。")
    add("")

    # -- Conclusions ------------------------------------------------------------
    add("## 結論")
    add("")
    a_winner = min(ranks_a["Total"], key=ranks_a["Total"].get)
    b_winner = min(ranks_b["Total"], key=ranks_b["Total"].get)
    c_winner = min(ranks_c["Total"], key=ranks_c["Total"].get)
    add(f"- **League A（B1 vs B2 vs B4 vs B5，USMV 窗）總分（1=最佳）**：" +
        "、".join(f"{CAND_LABEL[c]}={ranks_a['Total'][c]}" for c in league_a_members) +
        f"。最低分（職責達成最好）= **{CAND_LABEL[a_winner]}**。")
    add(f"- **League B（B1 vs B3 vs B5，VIG 窗）總分**：" +
        "、".join(f"{CAND_LABEL[c]}={ranks_b['Total'][c]}" for c in league_b_members) +
        f"。最低分 = **{CAND_LABEL[b_winner]}**。")
    add(f"- **League C（B1 vs B5 vs B6【負面對照】，Mag7 窗）總分**：" +
        "、".join(f"{CAND_LABEL[c]}={ranks_c['Total'][c]}" for c in league_c_members) +
        f"。最低分 = **{CAND_LABEL[c_winner]}**——**B6 唔論排名高低都唔係真候選**，佢存在嘅"
        "目的係量化對照，結果解讀見下。")
    add("- 判官係預先註冊嘅職責達成度（downside capture、三壓力窗、QQQ 正交、HK 淨回報+稅漏"
        "各佔一票），**唔係揀 CAGR 最高嗰個**——HK 淨 CAGR 只係四項之一，唔係唯一票。")
    add("- **B5（DIA）角色**：正式候選，同時喺 League A 同 League B 都有齊數同 B1 直接對比——"
        "具體邊項贏邊項輸見上面判官表 1/2；係咪值得換 B1，睇 League A/B 嘅總分差距，唔靠呢度"
        "單一句話下判斷。")
    add("- **B6（Mag7）角色**：明文負面對照組——結果只用嚟量化「用 offense 資產做 ballast」嘅"
        "代價（downside capture、QQQ 相關、熊市 delta 地台三個讀數），**唔會、亦唔應該被讀成"
        "「B6 輸咗所以淘汰」——佢由頭到尾都唔係一個候選人，係一把量尺**。")
    add("- （逐項邊個贏邊個輸嘅具體數字見上面三張判官表；本段刻意唔喺 script 內自動生成「換唔"
        "換 B1」嘅最終建議文字，避免 script 自己下判斷變成隱性 return-chasing——最終建議見對話"
        "回覆 [結論] 段，基於呢啲表逐項核對後撰寫。）")
    add("")

    # -- Caveats --------------------------------------------------------------
    add("## 誠實 Caveat")
    add("")
    add(f"- **USMV 歷史短**：2011-10-20 先上市，League A 窗只有 {len(league_a_idx)} 個交易日"
        "（~15年），唔含 2000 dot-com、2008 GFC、2011 歐債任何一個熊市——B2/B4 嘅 downside "
        "capture／壓力窗判斷樣本天然偏向 2012+ 嘅牛市為主 regime，結論外推去下一次危機有限度。")
    add(f"- **VIG 歷史中等**：2006-05-02 上市，League B 窗 {len(league_b_idx)} 個交易日"
        "（~20年），含 2008 GFC 但唔含 2000 dot-com；B3 嘅 2008 數字本 study 冇獨立報（跟原定"
        "規格淨報 B1）。")
    add(f"- **B6 窗口最短**：由 META 2012-05-18 上市決定，League C 窗只有 {len(league_c_idx)} "
        "個交易日（~14年），完全冇 2008 GFC；但 B6 本身係負面對照組，唔係用嚟做長期資產配置"
        "決策，呢個短窗對佢嘅「教學」目的影響有限——2020 COVID + 2022 兩個壓力窗仍然覆蓋到。")
    add("- **B5（DIA）歷史最長但唔係『萬能錨』**：DIA 1998-01-20 上市，早過 XLP/XLU/XLV，喺"
        "三個 league 都唔係約束者，所以佢嘅數字喺三個 league 之間可以互相對照趨勢（但唔可以"
        "直接跨 league 數值相減——common-window 規矩依然適用，B5-in-A 同 B5-in-B 係兩個獨立"
        "讀數，唔係同一個窗口嘅同一條數）。")
    add("- **B6 月度 vs 其他候選逐日 rebalance 唔一致**：呢個唔係疏忽，係因為 7 隻集中大型股"
        "逐日重平唔現實（交易成本/滑點喺呢個規模下唔可忽略，逐日重平會嚴重高估合成組合嘅"
        "真實可執行回報），但都要意識到：呢個令 B6 同 B1-B5 嘅比較唔係 100% 純粹「淨係換咗"
        "成員」嘅乾淨 increment——重平頻率呢個變數都變咗。呢點喺 B6 係負面對照組（唔係候選）"
        "嘅前提下影響有限，但唔應該被忽略。")
    add("- **單一歷史路徑**：冇 bootstrap／冇 Monte Carlo／冇多重測試修正（Bonferroni/DSR）——"
        "本 study 係 6 個 pre-registered 候選嘅單一路徑驗證，唔係大格網 sweep。")
    add("- **預先註冊聲明**：候選集合（B1-B4）同判官標準喺任務指派時已經寫死；B5/B6 喺同一次"
        "任務指派入面（測試執行前）由用戶正式加入，判官標準同稅務處理全部不變——呢個係任務"
        "指派範圍內嘅正式擴充，唔係睇完初步結果先改嘅 post-hoc 調整。")
    add("- **等權重、逐日重平衡係建模簡化**（B1-B5 適用）：真實執行唔會逐日重平所有成員，籃子"
        "內部重平假設無額外成本；本 study 冇對權重方案做任何搜索（等權係指定，唔係擇優）。")
    add("- **beta-租金咬合表／熊市 delta 地台都係 STATIC 一階近似**：用嘅係固定 45%/60%/25%/"
        "β1.20 假設（來自 leap_rent ledger 嘅示意數字 + 用戶最新指示的地台權重，非重新擬合），"
        "冇考慮 target-delta band 唔同、冇考慮 beta 本身隨 regime 波動（Table A 嘅原生窗 beta "
        "同 League 窗 beta 有機會唔同，讀者留意兩表唔係同一個數字）。")
    add("- **壓力窗定義係本 study 自訂**：2011-08 歐債 = 2011-08-01→2011-10-03（SPY 修正段）、"
        "2020 COVID = 2020-02-19→2020-03-23（急跌段）、2022 = 全年（「加息年」）——三個窗長度"
        "唔一（急性事件 vs 全年），讀者要意識到「平均超額」跨三個唔同長度嘅窗計，唔係嚴格同質"
        "嘅平均。")
    add("- **QQQ 相關性判官**：用 126 交易日 rolling correlation 嘅中位數（唔係全窗單一 Pearson "
        "相關），中位數本身可能隱藏尾部（危機期相關性飆升嘅片段）——本 study 冇獨立報 rolling "
        "correlation 嘅危機期子集。")
    add("")

    # -- Implication ------------------------------------------------------------
    add("## Implication")
    add("")
    add("（見對話回覆——若 B5 喺其所屬 league 總分明顯低過 B1（贏 3/4 或以上判官項），屬「體檢"
        "唔合格，換籃子有充分理由」的證據；若總分打平或 B1 仍然最低分，維持現行 XLP/XLU/XLV "
        "等權係合理決定。B6 嘅讀數（downside capture、QQQ 相關、熊市 delta 地台）直接餵返 §8c "
        "點 4「內部咬合」嘅可測錶盤——量化示範「ballast 揀錯資產」嘅代價量級，供設計文件引用做"
        "反面教材，唔需要另外做決策。）")
    add("")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS}  ({time.time()-t0:.0f}s total, {ASSERT_N['n']:,} asserts)",
          flush=True)


if __name__ == "__main__":
    main()
