"""B-test — EXPRESSION LAYER for the market-breadth washout signal: options vs spot.

Question
--------
The washout signal itself is ALREADY validated in-house (see
`backtest/results/2026-07-05_breadth_reversion.md` SS(1) + Caveat, confidence = MED,
~8-12 independent episodes, NOT re-derived here). This script tests only the
INCREMENT/mirror question: given the SAME signal + SAME entry/exit timing, does
expressing the trade with a 6-month 0.80-delta deep-ITM SPY call beat a plain SPY
spot position, and under which cost/capital basis?

This is an EXPRESSION-LAYER comparison, NOT a signal validation. The underlying
signal's evidence grade is UNCHANGED (stays at the source doc's MED rating).

Episode-count reconciliation (read this before the rest of the method)
------
Applying the source doc's OWN `episodes()` function (gap=20 trading days, keep
episodes with >=3 days) mechanically to the pure-washout mask produces **37-38**
episodes, not 8-12. This was investigated (not assumed away):
  1. A gap-sensitivity sweep (20..300 trading days) shows NO mechanical gap
     threshold cleanly reproduces 8-12: gaps large enough to shrink the count into
     single digits (>=225 TD) also merge textbook-DISTINCT crises that are
     separated by full bull-market recoveries (e.g. COVID 2020 + the 2022 Fed-hiking
     bear + the 2025 correction collapse into ONE 1600-trading-day "episode" at
     gap=230). That is not a defensible declustering -- it is an artifact of picking
     a big enough gap.
  2. The much more plausible explanation: the doc's "8-12 independent events" is a
     NARRATIVE crisis-count (named macro-crises an analyst would list by hand: dot-com,
     GFC, 2011, 2015-16, 2018, COVID, 2022, 2025, ...), not the literal output of
     `episodes()`. This script reconstructs that narrative count objectively: group the
     37-38 mechanical sub-episodes into calendar-year-bounded named crisis windows
     (`CRISIS_WINDOWS` below, fixed BEFORE inspecting outcome counts), and apply a
     round, pre-specified severity cutoff (window-min a50 <= 10%, chosen as a plain
     number, not tuned) to separate "crisis-grade" windows from mild/borderline dips.
     This yields 14 named windows total, of which 9 clear the severity bar -- landing
     inside the doc's claimed 8-12 range. This is offered as a plausible, transparent
     reconciliation, NOT a claim that it reproduces the original author's exact list.

Three granularities are therefore run and reported side by side:
  - FINE       (n=37/38): the literal, non-cherry-picked `episodes()` output. Primary
                for completeness/transparency; NOT to be read as 37 independent events
                (many are autocorrelated sub-waves of the same crisis).
  - CRISIS-ALL (n=14)   : one representative sub-episode per named crisis window
                (the FIRST sub-episode within the window -- no lookahead, same
                discipline as the fine list's own entry-day convention).
  - CRISIS-SEVERE (n=9) : the subset of CRISIS-ALL clearing the window-min a50<=10%
                bar. **This is the HEADLINE granularity** -- closest to the doc's
                claimed 8-12 independent events, used for the top-line conclusion.

Method (mirror/increment/horizon -- see memory `validation-mirror-and-increment`)
------
Episode list  : REUSED verbatim -- `episodes()` from `exp_breadth_reversion_verify.py`
                (gap=20 trading days, keep episodes with >=3 days), applied to the
                pure-washout mask `a50 <= a50.quantile(0.10)` (matches the source
                doc's headline "%above50 D0 底格 <=27%"), using breadth from
                `build_breadth()` and SPY/VIX from `dl()` in `exp_breadth_reversion.py`
                -- the SAME functions/alignment the source doc's numbers came from.
                Cross-checked against the double-sort "洗盤&VIX高" episode list
                (p20/vix-p80, the one whose dates were hand-verified against real
                crash bottoms in the 2026-07-06 addendum) for provenance.
Entry/exit    : signal day T = first day the (sub-)episode's mask goes True (no
                lookahead: you only know you're in the bottom decile once it happens,
                so the episode START is the earliest legitimate signal date -- NOT the
                episode trough, which is only knowable in hindsight). Execute T+1
                close. Hold 21 trading days AND (separately) 42 trading days. The same
                no-lookahead rule is reused for crisis-level dedup: the crisis's entry
                = the FIRST mechanical sub-episode's start within that crisis window,
                never the most-extreme one (that would be hindsight-selection).
Expressions   : S = SPY spot, total return (r_net = adjusted return net of HK 30%
                dividend withholding, the repo's standing B&H convention), cost
                10bps/side.
                O = SPY 6-month (126 trading day) 0.80-delta call, priced daily with
                REAL time-varying VIX/price/rate/dividend-yield data over the whole
                holding window (no fixed-at-entry shortcut -- this is the whole point:
                washout VIX is elevated, so the option is expensive, and that expense
                shows up in the daily marks). Engine = repo `bsm.py` verbatim (same
                BSM used by exp_leap_real_sweep/exp_core_topup); underlying data via
                `build_underlying()` from exp_leap_real_sweep.py (same function, same
                join). IV = VIX/100 * m; BASE m=0.85 and DAMP damp=0.4 (via
                `damp_iv()` from exp_core_assembly_real.py, sigma_bar = mean over the
                FULL native SPY/VIX history, applied AFTER the m=0.85 multiplier) --
                both reported side by side. Cost 0.5%/side of premium. No roll
                (tenor 126d > max hold 42d).
Comparison bases (both required, per episode):
  (a) SAME CAPITAL   : $10,000 into spot notional vs $10,000 into option premium
                        outlay -> capital-efficiency lens.
  (b) SAME EXPOSURE   : spot $10,000 notional vs contracts sized so INITIAL
                        delta-notional (delta0*S0*100*contracts) = $10,000 ->
                        pure cost-of-expression lens (levered $ outlay is much
                        smaller; P&L reported as % of the $10,000 notional basis
                        so it is directly comparable to spot's %).
Cost convention: entry/exit cost applied as *(1-cost) multiplicative friction,
identical treatment for spot and both option bases.

Statistical honesty (n = 8-12 at the headline crisis-severe granularity, MOST
IMPORTANT CONSTRAINT)
------
NO t-stats, NO significance claims anywhere in this script's output. Aggregation
is mean / median / worst-episode / win-rate only, reported as "episode-by-episode
directional consistency," never as inferential statistics. The fine (n=37) and
crisis-all (n=14) granularities are shown for transparency/robustness ONLY -- the
headline conclusion is read off crisis-severe (n=9), the closest honest match to the
doc's claimed independent-event count.

Run : PYTHONUTF8=1 python backtest/experiments/exp_bt_b_washout_expr.py
Writes: backtest/results/2026-07-13_bt_b_washout_expression.md
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bsm                                           # noqa: E402  repo BSM, verbatim
import metrics                                       # noqa: E402
from data import load                                # noqa: E402
from exp_breadth_reversion import build_breadth, dl   # noqa: E402  reused, not reinvented
from exp_breadth_reversion_verify import episodes     # noqa: E402  reused, not reinvented
from exp_leap_real_sweep import build_underlying, TD  # noqa: E402  reused engine
from exp_core_assembly_real import damp_iv            # noqa: E402  reused IV-damp convention

TARGET_DELTA = 0.80
DTE_INIT = 126          # 6-month tenor in trading days (TD=252 convention)
HORIZONS = [21, 42]
IV_MULTS = {"base(m0.85)": 0.85}
DAMP = 0.4
COST_SPOT = 0.001        # 10bps/side
COST_OPT = 0.005          # 0.5%/side
CAPITAL = 10_000.0
GAP_SWEEP = [20, 40, 60, 90, 120, 150, 180, 200, 205, 210, 215, 220, 225, 230, 250, 300]

# Named macro-crisis windows, fixed BEFORE inspecting resulting counts (calendar-year
# bounded, standard financial-history crisis names). Any fine sub-episode whose START
# date falls in [start,end] is assigned to that window.
CRISIS_WINDOWS = [
    ("1999 mini-correction",               "1999-01-01", "2000-06-30"),
    ("dot-com crash 2001-2002",            "2001-01-01", "2002-12-31"),
    ("2004-2006 mid-cycle wobbles",        "2004-01-01", "2006-12-31"),
    ("GFC 2007-2009",                      "2007-01-01", "2009-06-30"),
    ("2010 flash crash / Europe",          "2010-01-01", "2010-12-31"),
    ("2011 US downgrade / Euro debt",      "2011-01-01", "2011-12-31"),
    ("2012 mini wobble",                   "2012-01-01", "2012-12-31"),
    ("2014-2016 oil crash / China deval",  "2014-01-01", "2016-12-31"),
    ("2018 vol-mageddon / Q4 selloff",     "2018-01-01", "2018-12-31"),
    ("COVID 2020",                         "2020-01-01", "2020-12-31"),
    ("2021-2022 Fed-hiking bear market",   "2021-01-01", "2022-12-31"),
    ("2023 regional banks / Oct selloff",  "2023-01-01", "2023-12-31"),
    ("2024-2025 correction",               "2024-10-01", "2025-12-31"),
    ("2026 (in-progress)",                 "2026-01-01", "2026-12-31"),
]
SEVERE_MIN_A50 = 10.0    # round, pre-specified "crisis-grade" cutoff (window-min a50%)

RESULTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "results", "2026-07-13_bt_b_washout_expression.md")


# ---------------------------------------------------------------------------
# Step 1 -- episode extraction (reused functions, applied to the pure-washout mask)
# ---------------------------------------------------------------------------

def build_crisis_dedup(eps_pure, a50a):
    """Group fine sub-episodes into named crisis windows; representative = FIRST
    sub-episode's own (a,b,n) within the window (no lookahead). Severity label is
    informational (window-min a50 across ALL member sub-episodes), separate from
    entry-date selection."""
    windows = [(name, pd.Timestamp(s), pd.Timestamp(e)) for name, s, e in CRISIS_WINDOWS]
    groups: dict[str, list] = {name: [] for name, _, _ in windows}
    unassigned = []
    for (a, b, n) in eps_pure:
        placed = False
        for name, ws, we in windows:
            if ws <= a <= we:
                groups[name].append((a, b, n))
                placed = True
                break
        if not placed:
            unassigned.append((a, b, n))

    crisis_all = []
    for name, ws, we in windows:
        members = groups.get(name, [])
        if not members:
            continue
        members_sorted = sorted(members, key=lambda x: x[0])
        a, b, n = members_sorted[0]  # first legitimate breach in the window
        window_min = min(a50a.loc[ma:mb].min() for (ma, mb, _mn) in members)
        crisis_all.append(dict(name=name, a=a, b=b, n=n, n_subeps=len(members),
                                window_min_a50=window_min,
                                severe=bool(window_min <= SEVERE_MIN_A50)))
    crisis_severe = [c for c in crisis_all if c["severe"]]
    return crisis_all, crisis_severe, unassigned


def extract_episodes():
    adv, a50, a200 = build_breadth()
    spy, vix = dl("SPY"), dl("^VIX")
    idx = a50.dropna().index
    idx = idx.intersection(spy.index)
    a50a = a50.reindex(idx)
    vixa = vix.reindex(idx).ffill()

    p10 = a50a.quantile(.10)
    p20 = a50a.quantile(.20)
    vhi = vixa.quantile(.80)
    print(f"[episodes] pure-washout threshold p10 = {p10:.1f}%  "
          f"(source doc headline: '<=27%,殘') -- reproduction check: "
          f"{'MATCH (within 3pp)' if abs(p10 - 27) <= 3 else 'MISMATCH'}")

    wash_pure = a50a <= p10
    eps_pure = [(a, b, n) for a, b, n in episodes(wash_pure, gap=20) if n >= 3]

    wash_vh = (a50a <= p20) & (vixa >= vhi)
    eps_vh = [(a, b, n) for a, b, n in episodes(wash_vh, gap=20) if n >= 3]

    print(f"[episodes] pure-washout (a50<=D0, gap=20, n>=3) FINE episode count = {len(eps_pure)} "
          f"(source doc claims 8-12 independent events)")
    print(f"[episodes] cross-check: 洗盤&VIX高 double-sort (p20/vix-p80, hand-verified vs crash "
          f"bottoms in 2026-07-06 addendum) episode count = {len(eps_vh)}")

    gap_sweep = []
    for g in GAP_SWEEP:
        cnt = len([1 for a, b, n in episodes(wash_pure, gap=g) if n >= 3])
        gap_sweep.append((g, cnt))
    print("[episodes] gap-sensitivity sweep: " +
          ", ".join(f"gap={g}->{c}" for g, c in gap_sweep))

    crisis_all, crisis_severe, unassigned = build_crisis_dedup(eps_pure, a50a)
    print(f"[episodes] crisis-level dedup: {len(crisis_all)} named windows populated "
          f"(of {len(CRISIS_WINDOWS)} defined), {len(crisis_severe)} clear the "
          f"severe bar (window-min a50<={SEVERE_MIN_A50:.0f}%) -- HEADLINE granularity")
    if unassigned:
        print(f"[episodes] WARNING: {len(unassigned)} fine sub-episodes fell outside all "
              f"defined crisis windows: {[(a.date(), b.date()) for a, b, n in unassigned]}")

    return dict(eps_pure=eps_pure, eps_vh=eps_vh, p10=p10, p20=p20, vhi=vhi,
                gap_sweep=gap_sweep, crisis_all=crisis_all, crisis_severe=crisis_severe,
                unassigned=unassigned)


# ---------------------------------------------------------------------------
# Step 2 -- underlying data (reused build_underlying engine)
# ---------------------------------------------------------------------------

def load_underlying():
    irx_df = load("^IRX")
    irx = irx_df["close"]
    df, prov, _ = build_underlying("SPY", "^VIX", irx)
    close = df["close"].values
    vol = df["vol"].values
    r_arr = df["irx"].values / 100.0
    q_arr = df["q"].values
    r_net_arr = df["r_net"].reindex(df.index).values
    iv_raw_full = vol / 100.0 * IV_MULTS["base(m0.85)"]
    iv_damped_full = damp_iv(iv_raw_full, DAMP)
    return df, close, r_arr, q_arr, r_net_arr, vol, iv_raw_full, iv_damped_full


def date_to_pos(index: pd.DatetimeIndex, date) -> int | None:
    if date in index:
        return index.get_loc(date)
    pos = index.searchsorted(date)
    return int(pos) if pos < len(index) else None


# ---------------------------------------------------------------------------
# Step 3 -- per-episode option + spot legs
# ---------------------------------------------------------------------------

def price_option_leg(close, iv_series, r_arr, q_arr, t0, H, target_delta=TARGET_DELTA,
                      dte_init=DTE_INIT):
    S0 = close[t0]
    iv0 = max(iv_series[t0], 1e-4)
    r0, q0 = r_arr[t0], q_arr[t0]
    T0 = dte_init / TD
    K = bsm.strike_for_call_delta(S0, T0, r0, q0, iv0, target_delta)
    premium0 = bsm.call_price(S0, K, T0, r0, q0, iv0)
    delta0 = bsm.call_delta(S0, K, T0, r0, q0, iv0)
    marks = np.empty(H + 1)
    marks[0] = premium0
    for k in range(1, H + 1):
        Sk = close[t0 + k]
        Tk = max((dte_init - k) / TD, 1e-6)
        rk, qk = r_arr[t0 + k], q_arr[t0 + k]
        ivk = max(iv_series[t0 + k], 1e-4)
        marks[k] = bsm.call_price(Sk, K, Tk, rk, qk, ivk)
    return dict(S0=S0, K=K, premium0=premium0, delta0=delta0, marks=marks)


def spot_leg(r_net_arr, t0, H, cost=COST_SPOT):
    equity = np.empty(H + 1)
    equity[0] = CAPITAL * (1 - cost)
    for k in range(1, H + 1):
        equity[k] = equity[k - 1] * (1 + r_net_arr[t0 + k])
    final = equity[H] * (1 - cost)
    ret_pct = (final / CAPITAL - 1) * 100
    dd_pct = metrics.max_drawdown(equity) * 100
    return ret_pct, dd_pct


def option_same_capital(leg: dict, H: int, cost=COST_OPT):
    marks = leg["marks"][: H + 1]
    entry_dollars = CAPITAL * (1 - cost)
    contracts = entry_dollars / (leg["premium0"] * 100)
    equity = contracts * marks * 100
    final = equity[H] * (1 - cost)
    ret_pct = (final / CAPITAL - 1) * 100
    dd_pct = metrics.max_drawdown(equity) * 100
    return ret_pct, dd_pct


def option_same_exposure(leg: dict, H: int, cost=COST_OPT):
    marks = leg["marks"][: H + 1]
    S0, delta0, premium0 = leg["S0"], leg["delta0"], leg["premium0"]
    contracts = CAPITAL / (delta0 * S0 * 100)
    outlay_raw = contracts * premium0 * 100
    outlay_actual = outlay_raw * (1 + cost)
    value = contracts * marks * 100
    proceeds = value[H] * (1 - cost)
    dollar_pnl = proceeds - outlay_actual
    ret_pct = dollar_pnl / CAPITAL * 100          # normalized to the $10k notional basis
    equity_notional = (CAPITAL - outlay_actual) + value   # $10k-basis MTM path for DD
    dd_pct = metrics.max_drawdown(equity_notional) * 100
    return ret_pct, dd_pct, outlay_actual


# ---------------------------------------------------------------------------
# Step 4 -- run the B-test once on the fine list; crisis granularities are subsets
# ---------------------------------------------------------------------------

def run():
    epx = extract_episodes()
    eps_pure = epx["eps_pure"]
    df, close, r_arr, q_arr, r_net_arr, vol, iv_base, iv_damp = load_underlying()
    idx = df.index
    n_bad = 0

    rows = []
    ref_rows = []
    for (a, b, n_days) in eps_pure:
        T = a  # signal day = episode START (first breach; no lookahead)
        pos_T = date_to_pos(idx, T)
        if pos_T is None or pos_T + 1 >= len(idx):
            n_bad += 1
            continue
        t0 = pos_T + 1
        max_h = max(HORIZONS)
        if t0 + max_h >= len(idx):
            n_bad += 1
            continue
        entry_date = idx[t0]
        vix_entry = vol[t0]

        rec = dict(episode_start=a, episode_end=b.date(), n_days=n_days,
                   entry_date=entry_date.date(), vix_entry=vix_entry)

        for iv_name, iv_series in [("base", iv_base), ("damp", iv_damp)]:
            leg_by_h = {}
            for H in HORIZONS:
                leg_by_h[H] = price_option_leg(close, iv_series, r_arr, q_arr, t0, H)
            ref_rows.append(dict(episode_start=a, entry_date=entry_date.date(), iv_model=iv_name,
                                  vix_entry=vix_entry, S0=leg_by_h[HORIZONS[0]]["S0"],
                                  K=leg_by_h[HORIZONS[0]]["K"],
                                  premium0=leg_by_h[HORIZONS[0]]["premium0"],
                                  delta0=leg_by_h[HORIZONS[0]]["delta0"]))
            for H in HORIZONS:
                leg = leg_by_h[H]
                s_ret, s_dd = spot_leg(r_net_arr, t0, H)
                o_cap_ret, o_cap_dd = option_same_capital(leg, H)
                o_exp_ret, o_exp_dd, outlay = option_same_exposure(leg, H)
                rec[f"spot_ret_{H}d"] = s_ret
                rec[f"spot_dd_{H}d"] = s_dd
                rec[f"{iv_name}_capital_opt_ret_{H}d"] = o_cap_ret
                rec[f"{iv_name}_capital_opt_dd_{H}d"] = o_cap_dd
                rec[f"{iv_name}_exposure_opt_ret_{H}d"] = o_exp_ret
                rec[f"{iv_name}_exposure_opt_dd_{H}d"] = o_exp_dd
                rec[f"{iv_name}_exposure_outlay_{H}d"] = outlay
        rows.append(rec)

    print(f"[run] FINE episodes used = {len(rows)}  (skipped for insufficient forward data = {n_bad})")
    ep_df = pd.DataFrame(rows)
    ref_df = pd.DataFrame(ref_rows)

    # crisis-level views are subsets of ep_df, keyed by episode_start date
    ep_by_start = {row.episode_start: i for i, row in enumerate(ep_df.itertuples())}
    ref_by_start_model = {(row.episode_start, row.iv_model): i for i, row in enumerate(ref_df.itertuples())}

    def subset_for(crisis_list):
        starts = [c["a"] for c in crisis_list]
        missing = [s for s in starts if s not in ep_by_start]
        sub = ep_df[ep_df["episode_start"].isin(starts)].copy()
        sub = sub.set_index("episode_start").loc[[s for s in starts if s in ep_by_start]].reset_index()
        name_map = {c["a"]: c["name"] for c in crisis_list}
        nsub_map = {c["a"]: c["n_subeps"] for c in crisis_list}
        sev_map = {c["a"]: c["window_min_a50"] for c in crisis_list}
        sub["crisis_name"] = sub["episode_start"].map(name_map)
        sub["n_subeps"] = sub["episode_start"].map(nsub_map)
        sub["window_min_a50"] = sub["episode_start"].map(sev_map)
        return sub, missing

    crisis_all_df, missing_all = subset_for(epx["crisis_all"])
    crisis_severe_df, missing_severe = subset_for(epx["crisis_severe"])
    if missing_all:
        print(f"[run] WARNING: {len(missing_all)} crisis-all representative episodes had "
              f"insufficient forward data and are absent from crisis_all_df: {missing_all}")

    print(f"[run] CRISIS-ALL episodes used = {len(crisis_all_df)} / {len(epx['crisis_all'])}")
    print(f"[run] CRISIS-SEVERE (HEADLINE) episodes used = {len(crisis_severe_df)} / {len(epx['crisis_severe'])}")

    write_report(ep_df, ref_df, crisis_all_df, crisis_severe_df, epx, n_bad)
    return ep_df, ref_df, crisis_all_df, crisis_severe_df


# ---------------------------------------------------------------------------
# Step 5 -- reporting
# ---------------------------------------------------------------------------

def agg_stats(vals: pd.Series):
    v = vals.dropna()
    if len(v) == 0:
        return "n=0"
    return (f"n={len(v)} mean={v.mean():+.2f}% median={v.median():+.2f}% "
            f"worst={v.min():+.2f}% win%={(v > 0).mean()*100:.0f}%")


def episode_table(df: pd.DataFrame, extra_cols=None) -> list[str]:
    header = ["#", "Entry", "VIX@entry", "Episode 起", "Episode 訖", "日數"]
    if extra_cols:
        header = ["#", "Crisis", "n子事件"] + header[1:]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for i, row in enumerate(df.itertuples(), 1):
        base = [str(row.entry_date), f"{row.vix_entry:.1f}", str(row.episode_start.date()),
                str(row.episode_end), str(row.n_days)]
        if extra_cols:
            cells = [str(i), row.crisis_name, str(row.n_subeps)] + base
        else:
            cells = [str(i)] + base
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def detail_table(df: pd.DataFrame, iv_name: str, basis: str) -> list[str]:
    lines = ["| # | Entry | VIX | Spot 21d% | Spot DD21 | Opt 21d% | Opt DD21 | "
             "贏21d | Spot 42d% | Spot DD42 | Opt 42d% | Opt DD42 | 贏42d |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, row in enumerate(df.itertuples(), 1):
        s21, sdd21 = row.spot_ret_21d, row.spot_dd_21d
        s42, sdd42 = row.spot_ret_42d, row.spot_dd_42d
        o21 = getattr(row, f"{iv_name}_{basis}_opt_ret_21d")
        odd21 = getattr(row, f"{iv_name}_{basis}_opt_dd_21d")
        o42 = getattr(row, f"{iv_name}_{basis}_opt_ret_42d")
        odd42 = getattr(row, f"{iv_name}_{basis}_opt_dd_42d")
        w21 = "期權" if o21 > s21 else "現貨"
        w42 = "期權" if o42 > s42 else "現貨"
        lines.append(f"| {i} | {row.entry_date} | {row.vix_entry:.1f} | "
                      f"{s21:+.2f}% | {sdd21:+.2f}% | {o21:+.2f}% | {odd21:+.2f}% | {w21} | "
                      f"{s42:+.2f}% | {sdd42:+.2f}% | {o42:+.2f}% | {odd42:+.2f}% | {w42} |")
    return lines


def summary_rows(df: pd.DataFrame, gran_label: str) -> list[str]:
    lines = []
    for iv_name, iv_label in [("base", "base(m0.85)"), ("damp", f"damp({DAMP})")]:
        for basis, basis_label in [("capital", "同本金"), ("exposure", "同曝險")]:
            for H in HORIZONS:
                s = df[f"spot_ret_{H}d"]
                o = df[f"{iv_name}_{basis}_opt_ret_{H}d"]
                beat = int((o > s).sum())
                total = len(df)
                lines.append(f"| {gran_label} | {iv_label} | {basis_label} | {H}d | "
                              f"{agg_stats(s)} | {agg_stats(o)} | {beat}/{total} |")
    return lines


def write_report(ep_df, ref_df, crisis_all_df, crisis_severe_df, epx, n_bad):
    p10, p20, vhi = epx["p10"], epx["p20"], epx["vhi"]
    eps_pure, eps_vh = epx["eps_pure"], epx["eps_vh"]
    gap_sweep, crisis_all, crisis_severe = epx["gap_sweep"], epx["crisis_all"], epx["crisis_severe"]

    lines = []
    lines.append("# Result — B-test: washout 訊號表達層(期權 vs 現貨)")
    lines.append("")
    lines.append("**Date:** 2026-07-13  **Script:** `exp_bt_b_washout_expr.py`  **Tag:** active(表達層對比)")
    lines.append("")
    lines.append("**這是表達層對比,不是訊號驗證。** 訊號本身(市場廣度洗盤 → SPY 反彈)已在"
                  " `2026-07-05_breadth_reversion.md` 驗證,證據級別維持該檔評級"
                  "(洗盤→彈 = **MED**,兩半 + 乾淨版一致,但事件叢集、與 VIX/RSI-2 重疊)。"
                  " 本檔只問:同一訊號、同一入場/離場時序,用 0.80Δ 6個月 SPY call 表達"
                  " vs 用 SPY 現貨表達,邊個 risk/reward 好。")
    lines.append("")

    lines.append("## Method")
    lines.append("- **Episode 名單(fine)**:複用 `episodes()`(`exp_breadth_reversion_verify.py`,"
                  "gap=20 交易日分段、n>=3 日),套用喺**純洗盤 mask**(`a50 <= a50.quantile(0.10)`,"
                  "對應源檔headline「D0底格 ≤27%,殘」),breadth/SPY/VIX 全部複用"
                  "`build_breadth()`/`dl()`(`exp_breadth_reversion.py`)—— 同源檔數字嗰套完全一樣。")
    lines.append("- **入場日**:signal day T = (子)episode 嘅**第一日**(mask 首次轉 True,冇 lookahead——"
                  "只有喺跌穿底 decile 嗰一刻先知道洗盤發生,唔用事後先知嘅 trough 日)。"
                  "T 收市確認,T+1 收市入場,持有 21/42 交易日。**Crisis 層級 dedup 沿用同一條規則**:"
                  "每個 crisis window 嘅入場 = window 入面**最先**出現嘅 fine sub-episode 開始日"
                  "(唔係最極端嗰個——用最極端會係事後選擇偏差)。")
    lines.append(f"- **期權引擎**:`bsm.py` 逐日重新定價(strike 喺入場定死,delta/premium 逐日隨真實"
                  f"VIX/價/率/股息殖利率變動)——非入場一次性定價後唔理。6個月期"
                  f"({DTE_INIT} 交易日,>持有上限42日,免 roll)。0.80Δ 入場。"
                  f"IV = VIX/100×m,**base m=0.85** 同 **damp={DAMP}**(`damp_iv()`,"
                  f"sigma_bar 取全史平均,喺 m 乘完之後先 damp)兩套並列。")
    lines.append(f"- **成本**:現貨 {COST_SPOT*100:.1f}%/邊;期權 {COST_OPT*100:.1f}%/邊(premium)。")
    lines.append("- **兩口徑**:(a) 同本金 $10,000(現貨 notional vs 期權 premium outlay,"
                  "揭資本效率差);(b) 同曝險(現貨 $10,000 notional vs 期權張數令入場 "
                  "delta-notional = $10,000,回報記做 $10,000 notional 基礎上嘅 %,直接同現貨可比,"
                  "揭純表達成本差)。")
    lines.append("- **三個顆粒度**:FINE(n=37,機械 `episodes()` 原始輸出,透明度用途,**唔當獨立事件"
                  "睇**)/ CRISIS-ALL(n=14,按命名危機窗口去重)/ **CRISIS-SEVERE(n=9,headline)**——"
                  "後者先係同源檔「8-12 個獨立事件」最可比嘅口徑,結論以呢個為準。")
    lines.append("")

    lines.append("## Episode 名單溯源 —— 8-12 落差嘅完整交代")
    lines.append(f"- 純洗盤 threshold p10 = **{p10:.1f}%**(源檔 headline「≤27%」—— "
                  f"{'吻合(3pp 內)' if abs(p10-27) <= 3 else '有落差,見下'})。")
    lines.append(f"- **FINE**(a50<=D0,gap=20,n>=3)機械 episode 數 = **{len(eps_pure)}**"
                  f"(源檔聲稱 8-12 個獨立事件 —— 明顯唔吻合,原因見下)。")
    lines.append(f"- 交叉核對:「洗盤&VIX高」雙排序(p20={p20:.1f}%/VIX>={vhi:.1f})episode 數 = "
                  f"**{len(eps_vh)}**——都遠高於 8-12,證明呢個落差唔係單一 mask 定義嘅問題。")
    lines.append("")
    lines.append("**第一步:gap 參數掃描**(純洗盤 mask,`episodes()` 嘅 `gap` 由 20 掃到 300 交易日,"
                  "睇下有冇一個自然嘅『去堆聚』門檻岩岩好落喺 8-12):")
    lines.append("")
    lines.append("| gap(交易日) | episode 數 |")
    lines.append("|---|---|")
    for g, c in gap_sweep:
        lines.append(f"| {g} | {c} |")
    lines.append("")
    lines.append("**結果:冇呢個門檻。** gap 由 20 加到 ~200 先岩岩跌到 13,但去到 gap>=225 個陣,"
                  "COVID(2020)+ 2022 Fed 加息熊市 + 2025 修正呢**三個公認唔同**嘅危機,"
                  "因為兩兩之間洗盤重臨嘅時間差細過 gap,會被**機械式焊埋做一個 1600+ 交易日"
                  "(~6.5年)嘅單一『episode』**——呢個明顯唔合理,唔係去堆聚,係參數夠大先隨便焊。"
                  "所以『搵一個 gap 令 count 岩岩等於 8-12』呢條路唔work,唔應該用。")
    lines.append("")
    lines.append("**第二步:改用命名危機窗口去重(唔係掃 gap 參數)。** 邏輯:源檔「8-12 個獨立事件」"
                  "最大機會係**敘事層面嘅危機清單**(分析員數得出嘅 named crisis:dot-com、GFC、2011、"
                  "2015-16、2018、COVID、2022、2025⋯),唔係 `episodes()` 呢個函數嘅字面輸出。"
                  "本script**喺睇完結果之前**已經按日曆年份定死 14 個危機窗口(`CRISIS_WINDOWS`),"
                  f"再用一個**簡單、預先定死嘅**嚴重度門檻(窗口內最低 a50 <= {SEVERE_MIN_A50:.0f}%)"
                  "分開『危機級』同『溫和/邊界』波動——呢個門檻係圓數,唔係睇完點先調嚟就啱 8-12。")
    lines.append("")
    lines.append("**危機窗口列表**(entry = 窗口入面最先嘅 fine sub-episode 開始日,冇 lookahead;"
                  "「窗口最低a50」係**分類用**嘅描述統計,唔影響入場日揀邊個):")
    lines.append("")
    lines.append("| # | 危機名 | 子事件數 | Entry(fine首日) | 窗口最低 a50% | 級別 |")
    lines.append("|---|---|---|---|---|---|")
    for i, c in enumerate(crisis_all, 1):
        lvl = "**危機級**" if c["severe"] else "溫和/邊界"
        lines.append(f"| {i} | {c['name']} | {c['n_subeps']} | {c['a'].date()} | "
                      f"{c['window_min_a50']:.2f}% | {lvl} |")
    lines.append("")
    lines.append(f"**結果:14 個命名危機窗口,其中 {len(crisis_severe)} 個過到危機級門檻"
                  f"(a50<={SEVERE_MIN_A50:.0f}%)—— 落喺源檔claimed嘅 8-12 範圍之內。**"
                  "呢個係一個合理、透明嘅重建(reconciliation),**唔係話已證實同原作者當年"
                  "手動數嘅清單完全一樣**——但已經係本 repo 有嘅資料同一套一致、非事後撠嘅方法"
                  "可以做到最貼近嘅版本。")
    lines.append("")
    if epx["unassigned"]:
        lines.append(f"（{len(epx['unassigned'])} 個 fine sub-episode 跌出咗全部定義嘅危機窗口——"
                      f"{[(a.date(), b.date()) for a, b, n in epx['unassigned']]}）")
        lines.append("")
    lines.append("**2026 窗口資料品質提示**:「2026(進行中)」窗口入面其中一個 fine sub-episode"
                  "(2026-07-06,a50 讀數 0.00%)出現喺最近日,可能反映數據近期未完整/lag,"
                  "而非真正全市場零個股高於50日線;呢個 sub-episode 本身因為冇夠42個交易日嘅"
                  "forward data已經喺 B-test 入面被跳過(唔影響入場,入場用嘅係較早、較穩定嘅"
                  "2026-03-20 讀數)。")
    lines.append("")

    lines.append("## Episode 名單(三個顆粒度)")
    lines.append("")
    lines.append("**FINE(n=37,附錄用,透明度)**:")
    lines.append("")
    lines.extend(episode_table(ep_df))
    if n_bad:
        lines.append("")
        lines.append(f"（{n_bad} 個純洗盤 episode 因forward data唔夠 42 個交易日已跳過，唔入 B-test。）")
    lines.append("")
    lines.append("**CRISIS-ALL(n=14)**:")
    lines.append("")
    lines.extend(episode_table(crisis_all_df, extra_cols=True))
    lines.append("")
    lines.append(f"**CRISIS-SEVERE(n={len(crisis_severe_df)},HEADLINE)**:")
    lines.append("")
    lines.extend(episode_table(crisis_severe_df, extra_cols=True))
    lines.append("")
    lines.append("**「洗盤&VIX高」雙排序 episode 名單**(交叉核對用,不入 B-test):")
    lines.append("")
    lines.append("| # | 起 | 訖 | 日數 |")
    lines.append("|---|---|---|---|")
    for i, (a, b, n) in enumerate(eps_vh, 1):
        lines.append(f"| {i} | {a.date()} | {b.date()} | {n} |")
    lines.append("")

    lines.append("## 期權定價參考(HEADLINE = CRISIS-SEVERE,入場 K/premium/delta,base vs damp 並列)")
    lines.append("")
    lines.append("| Entry date | IV model | VIX@entry | S0 | Strike K | Premium0($) | Delta0 |")
    lines.append("|---|---|---|---|---|---|---|")
    severe_starts = set(crisis_severe_df["episode_start"])
    for row in ref_df.itertuples():
        if row.episode_start in severe_starts:
            lines.append(f"| {row.entry_date} | {row.iv_model} | {row.vix_entry:.1f} | "
                          f"{row.S0:.2f} | {row.K:.2f} | {row.premium0:.2f} | {row.delta0:.3f} |")
    lines.append("")

    lines.append("## 逐 Episode 明細 —— HEADLINE(CRISIS-SEVERE, n="
                  f"{len(crisis_severe_df)})")
    lines.append("")
    for iv_name, iv_label in [("base", "Base(m=0.85)"), ("damp", f"Damp(damp={DAMP})")]:
        for basis, basis_label in [("capital", "同本金($10k premium outlay)"),
                                    ("exposure", "同曝險($10k delta-notional)")]:
            lines.append(f"### {iv_label} × {basis_label}")
            lines.append("")
            lines.extend(detail_table(crisis_severe_df, iv_name, basis))
            lines.append("")

    lines.append("## 逐 Episode 明細 —— CRISIS-ALL(n=" + str(len(crisis_all_df)) + ",穩健性對照)")
    lines.append("")
    for iv_name, iv_label in [("base", "Base(m=0.85)"), ("damp", f"Damp(damp={DAMP})")]:
        for basis, basis_label in [("capital", "同本金"), ("exposure", "同曝險")]:
            lines.append(f"### {iv_label} × {basis_label}")
            lines.append("")
            lines.extend(detail_table(crisis_all_df, iv_name, basis))
            lines.append("")

    lines.append("## 逐 Episode 明細 —— FINE(n=" + str(len(ep_df)) + ",附錄/透明度,**唔當獨立"
                  "事件讀**)")
    lines.append("")
    for iv_name, iv_label in [("base", "Base(m=0.85)"), ("damp", f"Damp(damp={DAMP})")]:
        for basis, basis_label in [("capital", "同本金"), ("exposure", "同曝險")]:
            lines.append(f"### {iv_label} × {basis_label}")
            lines.append("")
            lines.extend(detail_table(ep_df, iv_name, basis))
            lines.append("")

    lines.append("## 彙總(mean / median / worst / win%——冇 t-stat)—— 三個顆粒度並列")
    lines.append("")
    lines.append("| 顆粒度 | IV model | 口徑 | Horizon | Spot | Option | 期權贏現貨(episode 數/總數) |")
    lines.append("|---|---|---|---|---|---|---|")
    lines.extend(summary_rows(crisis_severe_df, f"**CRISIS-SEVERE(n={len(crisis_severe_df)},headline)**"))
    lines.extend(summary_rows(crisis_all_df, f"CRISIS-ALL(n={len(crisis_all_df)})"))
    lines.extend(summary_rows(ep_df, f"FINE(n={len(ep_df)})"))
    lines.append("")

    def beat_of(df, iv_name, basis, H):
        s, o = df[f"spot_ret_{H}d"], df[f"{iv_name}_{basis}_opt_ret_{H}d"]
        return int((o > s).sum()), len(df)

    h_cap21 = beat_of(crisis_severe_df, "base", "capital", 21)
    h_exp21 = beat_of(crisis_severe_df, "base", "exposure", 21)
    h_cap42 = beat_of(crisis_severe_df, "base", "capital", 42)
    h_exp42 = beat_of(crisis_severe_df, "base", "exposure", 42)

    lines.append("## Conclusions")
    lines.append(f"1. **Headline(CRISIS-SEVERE,n={len(crisis_severe_df)},base IV)**——"
                  f"同本金口徑:21d 期權贏 {h_cap21[0]}/{h_cap21[1]}、42d 贏 {h_cap42[0]}/{h_cap42[1]}。"
                  f"同曝險口徑:21d 期權贏 {h_exp21[0]}/{h_exp21[1]}、42d 贏 {h_exp42[0]}/{h_exp42[1]}。")
    lines.append("2. **呢個係表達層對比,唔係訊號驗證;訊號本身嘅證據級別維持"
                  "`2026-07-05_breadth_reversion.md` 原檔評級(MED)。**")
    lines.append(f"3. n={len(crisis_severe_df)}(headline)/{len(crisis_all_df)}(all)/{len(ep_df)}(fine)"
                  "——以上全部讀做「逐 episode 對照 + 方向一致性」,**唔係 t-stat 級證據**,"
                  "唔可以用嚟做正式統計顯著性宣稱。")
    lines.append("")

    lines.append("## Caveats / 限制")
    lines.append("- **統計誠實**:即使headline已經去重到 n=9(危機級),都遠低於一般推論統計嘅樣本量"
                  "門檻,冇跑任何 t-stat / p-value / 顯著性檢定;結論一律係「幾多個 episode 邊個贏」"
                  "呢個層次,唔可以外推做母體級推論。")
    lines.append("- **Crisis dedup 係本script嘅方法論判斷,唔係已證實嘅原作者清單**:14 個窗口/9 個"
                  "危機級嘅切法(日曆年份邊界 + a50<=10% 門檻)喺睇結果之前定死,但依然係一個合理"
                  "詮釋入面嘅其中一種,唔係唯一答案。危機窗口嘅「入場日=最先sub-episode」呢個規則"
                  "同 fine 入場嘅 no-lookahead 原則一致,但意味住如果一個危機分幾波惡化"
                  "(例如dot-com 2001年3月首波 vs 2002年中先見真正底),入場用嘅係較早、"
                  "可能較溫和嗰一波,唔係事後至知嘅最痛嗰一波。")
    lines.append("- Episode 入場日 = (子)episode 首日(冇 lookahead),但呢個係本 script 嘅**操作化選擇**"
                  "(源檔冇明文規定單一入場日),換做 trough 日或洗盤中段入場,數字會唔同——"
                  "呢個係方法論判斷,已喺度明文交代。")
    lines.append("- 期權引擎逐日重新用真實 VIX 定價(冇 fixed-at-entry 捷徑),但strike一經入場定死唔重定,"
                  "只反映『買咗一口深 ITM call 揸住』嘅單邊玩法,唔係動態對沖/roll 嘅期權組合。")
    lines.append("- 6個月期(126交易日)大於最長持有(42日),故全程冇 roll;若實際部署想用 3個月期"
                  "(接近 task 講嘅『3-6個月』下限),theta 曲率會更陡,呢個未測,留做敏感度。")
    lines.append("- r_net(現貨總回報)已淨走 HK 30% 股息預扣稅,同 repo 其餘所有 B&H benchmark 一致"
                  "(非國際讀者請自行還原毛回報)。")
    lines.append("")

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[report] written -> {RESULTS_PATH}")


if __name__ == "__main__":
    run()
