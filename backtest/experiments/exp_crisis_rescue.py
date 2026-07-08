"""A-型危機救援 event study (Phase-3 WS2, real data, event-study not t-stat game).

Hypothesis under test: generational-panic-level fear (VIX close > 40) + a BEATEN "epicenter"
sector (systemically-important, e.g. XLF/XLE — the kind that drags the whole economy, not a
supply-shock energy spike) + a policy backstop -> violent mean reversion. We already have the
negative prior at a SHALLOWER fear threshold: `2026-07-06_sector_capeff.md` H2 found buying the
worst-63d-return sector PAIR (naive, no systemic filter) whenever SPY>200SMA & VIX>28 loses to
SPY by -2.45%/episode (t-2.52, n=14). This script asks whether going to a MUCH higher VIX bar
(35/40/45) AND filtering for a genuinely systemic epicenter changes that verdict. n here is
necessarily tiny (this is a study of ~8-12 crisis episodes over 26 years) — the per-episode
table below IS the product; the aggregate stats are a secondary summary, not the finding.

PRE-REGISTERED SPEC (see task brief, reproduced for the record):
  Episode def   : ^VIX daily close first > threshold; same episode does not re-trigger for the
                  next 60 trading days. Thresholds {35, 40, 45} all run; 40 is the primary/main
                  table. Window: 1999-01-01+ (9 original SPDR sectors have data from
                  1998-12-22, so 63-trading-day trailing returns are available from ~1999Q1).
  Legs (each episode, 4-way comparison):
    L1 = naive residual   -- buy the trigger-day worst-2-by-trailing-63d-return sectors
                             (equal weight). This IS the H2 mechanism, just at a higher VIX bar.
    L2 = SPY control       -- buy SPY on the same trigger date (the discipline benchmark).
    L3 = epicenter leg     -- of the worst-2, keep only the ones that are XLF or XLE (systemic,
                             economy-wide-chain sectors); if NEITHER worst-2 sector is XLF/XLE,
                             this leg (and L4) is skipped for that episode and flagged N/A.
    L4 = right-side epicenter -- same target sector(s) as L3, but entry delayed until ^VIX
                             closes back BELOW 30 (waits for the panic to visibly crest before
                             buying), then buys at that close+1.
  Exit          : ALL of 21/63/126/252 trading days reported (no cherry-picking a horizon).
  Cost          : 5bps/side (repo standard ETF cost), applied to every entry and exit.
  Execution lag : signal at close T -> trade executes at close T+1 (repo convention, applied
                  uniformly: L1/L2/L3 entry lag off the trigger date; L4 entry lag off its own
                  VIX<30 signal date). Horizon exit = entry_exec_date + h TRADING days (a fixed
                  holding period from execution, no extra lag on the exit itself since it is not
                  a signal-triggered exit).
  Excess        : for every leg, computed against SPY bought on THAT SAME leg's own dates (so
                  L4's excess uses a SPY leg dated off L4's later, right-side entry -- not off
                  the original trigger date). This isolates "is buying this sector at this time
                  better than buying SPY at this time", the increment discipline used throughout
                  this repo (`validation-mirror-and-increment`).

NO t-stat cosmetics: n<10 in most cells. Conclusions use direction + consistency + named
exceptions language, not p-values as the arbiter. A ttest is still printed as a secondary
descriptive alongside the per-episode table (never as the sole verdict).

Universe : XLK/XLF/XLE/XLV/XLI/XLP/XLU/XLY/XLB (9 original SPDR sectors, no ffill-before-
           inception needed -- all 9 predate 1999) + SPY + ^VIX. `backtest/data.py` `load(sym,
           adjusted=True)` for equities (total-return); `^VIX` loaded raw (index, no dividends).

Run: python backtest/experiments/exp_crisis_rescue.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load  # noqa: E402

COST = 0.0005  # 5bps/side, repo standard
DEDUP_TD = 60          # trading days before an episode can re-trigger
RIGHT_SIDE_VIX = 30.0  # L4 waits for VIX close < this before entering
HORIZONS = [21, 63, 126, 252]
THRESHOLDS = [35, 40, 45]
MAIN_THRESHOLD = 40
SYSTEMIC = {"XLF", "XLE"}
SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB"]
WINDOW_START = "1999-01-01"

# Narrative-only (this repo's own knowledge, NOT data) — one-line policy-response annotation
# per crisis, matched to the nearest triggering episode by date. Labeled clearly in the report
# as narrative, not a backtested quantity.
NARRATIVE = [
    ("1999-08-01", "1999-10-31", "1998 LTCM/Russia-default hangover + Y2K liquidity jitters; "
                                  "Fed had already cut 3x in autumn 1998, kept policy easy into Y2K."),
    ("2001-09-01", "2001-10-31", "9/11 attack; markets closed 4 trading days, Fed slashed rates "
                                  "aggressively post-reopen, huge Fed/Treasury liquidity injections, "
                                  "airline/insurance federal backstops."),
    ("2002-06-01", "2002-10-31", "WorldCom/Enron accounting scandals + post-dot-com bear low; "
                                  "Sarbanes-Oxley passed July 2002, Fed cutting toward 1.25%/1.0%."),
    ("2008-09-01", "2009-03-31", "Lehman collapse/GFC; TARP ($700B), AIG bailout, Fed QE1 launched "
                                  "Nov 2008, Fannie/Freddie conservatorship, TALF."),
    ("2010-04-15", "2010-06-30", "'Flash Crash' (May 6) + Greek sovereign-debt crisis; EU/IMF first "
                                  "Greek bailout (May 2010), ECB launches SMP bond-buying."),
    ("2011-07-15", "2011-10-15", "US S&P credit-rating downgrade (Aug 5) + EU sovereign-debt "
                                  "escalation (Italy/Spain spreads); Fed announces Operation Twist "
                                  "Sept 2011."),
    ("2015-08-01", "2015-09-30", "China yuan devaluation + global growth scare ('Black Monday' "
                                  "Aug 24); PBoC stimulus/RRR cuts, no major US policy response — "
                                  "largely self-resolving."),
    ("2018-01-15", "2018-03-01", "'Volmageddon' — short-vol ETN (XIV) blowup on a rates-scare "
                                  "spike; no policy backstop, a market-structure event not a "
                                  "systemic-economy one."),
    ("2020-02-15", "2020-04-30", "COVID-19 crash; Fed cuts to zero + unlimited QE, CARES Act "
                                  "($2.2T fiscal), PPP loans, corporate-bond-buying facilities — "
                                  "the largest policy backstop in the sample."),
    ("2011-11-01", "2011-12-15", "Extension of the Aug 2011 EU crisis: Italy's Berlusconi resigns, "
                                  "MF Global collapses; ECB LTRO liquidity operations follow "
                                  "in Dec 2011."),
    ("2018-12-01", "2019-01-15", "Dec 2018 selloff; Fed rate-hike scare (Powell 'long way from "
                                  "neutral' comment) + government-shutdown fear, Fed pivots dovish "
                                  "early Jan 2019 ('patient' language)."),
    ("2020-06-05", "2020-06-20", "June 2020 single-day selloff (Jun 11): COVID resurgence fear "
                                  "in reopening US states + a cautious Fed SEP projecting rates "
                                  "near zero through 2022; no new policy action, self-resolving."),
    ("2020-10-01", "2020-11-08", "Pre-election COVID second-wave fear (ahead of the Nov 9 "
                                  "Pfizer-vaccine announcement); no new policy action, market was "
                                  "pricing election + winter-wave uncertainty."),
    ("2021-01-20", "2021-02-10", "GameStop/meme-stock short-squeeze volatility event; retail-"
                                  "options-driven vol spike, not a macro/policy crisis — a useful "
                                  "structural (non-systemic) negative control."),
    ("2022-01-01", "2022-10-31", "Inflation/rate-hike bear market; Fed HIKING (75bp moves), the "
                                  "OPPOSITE of a rescue put — a useful negative control if it "
                                  "triggers here."),
    ("2024-08-01", "2024-08-15", "Aug 2024 yen-carry-trade unwind (BoJ hike) + a weak US jobs "
                                  "report reigniting recession fear; no policy action, resolved "
                                  "within weeks."),
    ("2025-03-15", "2025-05-15", "April 2025 'Liberation Day' reciprocal-tariff shock; violent "
                                  "swings, eventual 90-day tariff pause announced, Fed on hold — "
                                  "policy response was trade-deal not monetary."),
]


def narrate(date: pd.Timestamp) -> str:
    for lo, hi, note in NARRATIVE:
        if pd.Timestamp(lo) <= date <= pd.Timestamp(hi):
            return note
    return "(no narrative match in lookup table — check NARRATIVE list / episode date)"


# ============================================================================
# 1. Data
# ============================================================================

def load_all():
    closes = {s: load(s, adjusted=True)["close"] for s in SECTORS}
    closes["SPY"] = load("SPY", adjusted=True)["close"]
    idx = closes["SPY"].index
    df = pd.DataFrame({k: v.reindex(idx) for k, v in closes.items()}, index=idx)
    vix = load("^VIX")["close"].reindex(idx).ffill(limit=3)
    mask = idx >= WINDOW_START
    return df.loc[mask], vix.loc[mask]


def net_ret(entry_px: float, exit_px: float, cost: float = COST) -> float:
    if entry_px is None or exit_px is None or np.isnan(entry_px) or np.isnan(exit_px):
        return float("nan")
    return (exit_px * (1 - cost)) / (entry_px * (1 + cost)) - 1.0


# ============================================================================
# 2. Episode detection
# ============================================================================

def find_episodes(vix: pd.Series, threshold: float) -> list[dict]:
    idx = vix.index
    v = vix.to_numpy()
    n = len(v)
    episodes = []
    last_trigger_i = -DEDUP_TD - 1
    i = 0
    while i < n:
        if not np.isnan(v[i]) and v[i] > threshold and (i - last_trigger_i) > DEDUP_TD:
            episodes.append(dict(trigger_i=i, trigger_date=idx[i], vix_trigger=float(v[i])))
            last_trigger_i = i
        i += 1
    return episodes


def episode_context(df: pd.DataFrame, vix: pd.Series, ep: dict) -> dict:
    """Fill in worst-2 sectors, epicenter presence, VIX peak, and the right-side (L4) entry."""
    idx = df.index
    n = len(idx)
    i = ep["trigger_i"]

    # worst-2 by trailing 63d return as of the trigger close (uses data through close i only).
    tr63 = {}
    for s in SECTORS:
        px = df[s].to_numpy()
        if i >= 63 and not np.isnan(px[i]) and not np.isnan(px[i - 63]):
            tr63[s] = px[i] / px[i - 63] - 1.0
    worst2 = sorted(tr63.items(), key=lambda kv: kv[1])[:2]
    ep["worst2"] = worst2  # [(sector, trailing63d_ret), ...]

    epicenter_secs = [s for s, _ in worst2 if s in SYSTEMIC]
    ep["epicenter_secs"] = epicenter_secs

    # VIX peak: max close from trigger day through the earlier of (VIX<30 first close after
    # trigger) or a 90-trading-day cap (documented operationalization, not a free parameter).
    v = vix.to_numpy()
    cap = min(i + 90, n - 1)
    j = i
    reentry_i = None
    while j <= cap:
        if not np.isnan(v[j]) and v[j] < RIGHT_SIDE_VIX and j > i:
            reentry_i = j
            break
        j += 1
    peak_end = reentry_i if reentry_i is not None else cap
    window = v[i:peak_end + 1]
    valid = window[~np.isnan(window)]
    ep["vix_peak"] = float(valid.max()) if len(valid) else float("nan")
    ep["reentry_i"] = reentry_i  # index where VIX first closes <30 after trigger (None = never)
    return ep


# ============================================================================
# 3. Leg returns
# ============================================================================

def leg_return(df: pd.DataFrame, sectors: list[str], entry_i: int, horizon: int, n_rows: int):
    """Equal-weight buy `sectors` at close[entry_i+1] (exec lag), sell at close[entry_i+1+horizon].
    Returns (leg_ret, spy_ret_same_dates, excess) or (nan, nan, nan) if data insufficient."""
    exec_i = entry_i + 1
    exit_i = exec_i + horizon
    if exec_i >= n_rows or exit_i >= n_rows:
        return float("nan"), float("nan"), float("nan")
    rets = []
    for s in sectors:
        ep_ = df[s].to_numpy()[exec_i]
        xp_ = df[s].to_numpy()[exit_i]
        r = net_ret(ep_, xp_)
        if not np.isnan(r):
            rets.append(r)
    if not rets:
        return float("nan"), float("nan"), float("nan")
    leg_ret = float(np.mean(rets))
    spy = df["SPY"].to_numpy()
    spy_ret = net_ret(spy[exec_i], spy[exit_i])
    excess = leg_ret - spy_ret if not np.isnan(spy_ret) else float("nan")
    return leg_ret, spy_ret, excess


def build_episode_table(df: pd.DataFrame, vix: pd.Series, threshold: float) -> list[dict]:
    n_rows = len(df)
    eps = find_episodes(vix, threshold)
    rows = []
    for ep in eps:
        ep = episode_context(df, vix, ep)
        worst2_secs = [s for s, _ in ep["worst2"]]
        epicenter_secs = ep["epicenter_secs"]
        row = dict(ep)
        # L1 naive residual (worst-2)
        row["L1"] = {h: leg_return(df, worst2_secs, ep["trigger_i"], h, n_rows) for h in HORIZONS}
        # L2 SPY control (same trigger date)
        row["L2"] = {h: leg_return(df, ["SPY"], ep["trigger_i"], h, n_rows) for h in HORIZONS}
        # L3 epicenter leg (subset of worst-2 that's systemic); N/A if none
        if epicenter_secs:
            row["L3"] = {h: leg_return(df, epicenter_secs, ep["trigger_i"], h, n_rows) for h in HORIZONS}
        else:
            row["L3"] = None
        # L4 right-side epicenter (same target, delayed entry to VIX<30 close)
        if epicenter_secs and ep["reentry_i"] is not None:
            row["L4"] = {h: leg_return(df, epicenter_secs, ep["reentry_i"], h, n_rows) for h in HORIZONS}
            row["L4_entry_date"] = df.index[ep["reentry_i"]]
        else:
            row["L4"] = None
            row["L4_entry_date"] = None
        # L5 right-side naive worst-2 (backlog item #1): same entry-timing rule as L4 (wait for
        # VIX close < 30), but the TARGET is the plain worst-2 (L1's object), no systemic filter.
        # Tests whether the systemic-epicenter screen matters once you fix the "left vs right
        # side" confound -- i.e. does naive worst-2 lose to epicenter-only once both are entered
        # on the same right-side timing rule? Available whenever VIX re-entered <30 within the
        # 90td cap, independent of whether an epicenter sector was present in the worst-2.
        if ep["reentry_i"] is not None:
            row["L5"] = {h: leg_return(df, worst2_secs, ep["reentry_i"], h, n_rows) for h in HORIZONS}
            row["L5_entry_date"] = df.index[ep["reentry_i"]]
        else:
            row["L5"] = None
            row["L5_entry_date"] = None
        row["narrative"] = narrate(ep["trigger_date"])
        rows.append(row)
    return rows


# ============================================================================
# 4. Reporting
# ============================================================================

def fmt_pct(x):
    return "  N/A " if (x is None or np.isnan(x)) else f"{x*100:+6.2f}%"


def print_episode_table(rows: list[dict], threshold: float):
    print(f"\n=== Episodes @ VIX>{threshold} close, n={len(rows)} ===")
    for row in rows:
        w2 = ", ".join(f"{s}({r*100:+.1f}%)" for s, r in row["worst2"])
        epi = "/".join(row["epicenter_secs"]) if row["epicenter_secs"] else "NONE (L3/L4 skipped)"
        l4d = row["L4_entry_date"].date() if row["L4_entry_date"] is not None else (
            "never<30(N/A)" if row["epicenter_secs"] else "N/A(no epicenter)")
        l5d = row["L5_entry_date"].date() if row["L5_entry_date"] is not None else "never<30(N/A)"
        print(f"\n  {row['trigger_date'].date()}  VIX@trigger={row['vix_trigger']:.1f}  "
              f"VIX peak(to reentry/90td cap)={row['vix_peak']:.1f}")
        print(f"    worst-2 (63d trailing ret): {w2}")
        print(f"    epicenter (XLF/XLE in worst-2): {epi}   L4 entry date: {l4d}   L5 entry date: {l5d}")
        print(f"    narrative: {row['narrative']}")
        header = f"    {'leg':6}" + "".join(f"{'h='+str(h)+'d':>12}" for h in HORIZONS)
        print(header)
        for leg_name in ["L1", "L2", "L3", "L4", "L5"]:
            leg = row[leg_name]
            if leg is None:
                print(f"    {leg_name:6}" + "".join(f"{'N/A':>12}" for _ in HORIZONS) + "  (excess vs SPY same dates)")
                continue
            cells = []
            for h in HORIZONS:
                ret, spy_ret, exc = leg[h]
                cells.append(f"{fmt_pct(ret)}/{fmt_pct(exc)}")
            print(f"    {leg_name:6}" + " ".join(f"{c:>18}" for c in cells) + "  (ret/excess-vs-SPY)")


def aggregate(rows: list[dict], leg_name: str, h: int):
    excs = []
    for row in rows:
        leg = row[leg_name]
        if leg is None:
            continue
        _, _, exc = leg[h]
        if not np.isnan(exc):
            excs.append(exc)
    excs = np.array(excs)
    if len(excs) == 0:
        return dict(n=0, mean=np.nan, median=np.nan, win=np.nan, worst=np.nan, t=np.nan, p=np.nan)
    t, p = (stats.ttest_1samp(excs, 0.0) if len(excs) >= 2 and excs.std(ddof=1) > 0 else (np.nan, np.nan))
    return dict(n=len(excs), mean=float(excs.mean()), median=float(np.median(excs)),
                win=float((excs > 0).mean()), worst=float(excs.min()), t=t, p=p)


def aggregate_excluding(rows: list[dict], leg_name: str, h: int, exclude_dates: set) -> dict:
    """Same as aggregate() but drops episodes whose trigger_date is in exclude_dates -- used for
    the 2020-10-28 sensitivity check (backlog item #1: L4's edge is partly carried by that single
    episode's outsized excess; this reports what's left once it's dropped)."""
    filtered = [row for row in rows if row["trigger_date"] not in exclude_dates]
    return aggregate(filtered, leg_name, h)


def print_summary(rows: list[dict], threshold: float):
    print(f"\n=== Summary @ VIX>{threshold}, n_episodes={len(rows)} (n<10 in most cells -- "
          f"direction/consistency language, NOT a t-stat verdict) ===")
    print(f"  {'leg':6}{'h':>6}{'n':>5}{'mean exc%':>11}{'median exc%':>13}{'win%':>7}{'worst exc%':>11}{'t (desc.)':>12}")
    for leg_name in ["L1", "L2", "L3", "L4", "L5"]:
        for h in HORIZONS:
            a = aggregate(rows, leg_name, h)
            tstr = f"{a['t']:+.2f}" if not (isinstance(a['t'], float) and np.isnan(a['t'])) else "n/a"
            print(f"  {leg_name:6}{h:>6}{a['n']:>5}{a['mean']*100 if not np.isnan(a['mean']) else float('nan'):>11.2f}"
                  f"{a['median']*100 if not np.isnan(a['median']) else float('nan'):>13.2f}"
                  f"{a['win']*100 if not np.isnan(a['win']) else float('nan'):>7.1f}"
                  f"{a['worst']*100 if not np.isnan(a['worst']) else float('nan'):>11.2f}{tstr:>12}")


def run():
    print("Loading data (9 original SPDR sectors + SPY, total-return; ^VIX)...")
    df, vix = load_all()
    print(f"  Calendar: {df.index[0].date()} -> {df.index[-1].date()}, {len(df)} rows")
    print(f"  VIX: {vix.first_valid_index().date()} -> {vix.last_valid_index().date()}")

    all_rows = {}
    for threshold in THRESHOLDS:
        rows = build_episode_table(df, vix, threshold)
        all_rows[threshold] = rows
        print_episode_table(rows, threshold)
        print_summary(rows, threshold)

    print("\n=== Threshold sensitivity (episode count + headline direction) ===")
    for threshold in THRESHOLDS:
        rows = all_rows[threshold]
        n = len(rows)
        l1_63 = aggregate(rows, "L1", 63)
        l3_63 = aggregate(rows, "L3", 63)
        l4_63 = aggregate(rows, "L4", 63)
        print(f"  VIX>{threshold}: n_episodes={n}  h=63d mean-excess  L1={l1_63['mean']*100 if not np.isnan(l1_63['mean']) else float('nan'):+.2f}%"
              f"  L3={l3_63['mean']*100 if not np.isnan(l3_63['mean']) else float('nan'):+.2f}%"
              f"  L4={l4_63['mean']*100 if not np.isnan(l4_63['mean']) else float('nan'):+.2f}%")

    # ------------------------------------------------------------------
    # Backlog item #1 (docs/2026-07-08_phase3_ws2_crisis.md, section 4): L5 = right-side entry +
    # naive worst-2 (no systemic filter), run at the main threshold (VIX>40), plus a sensitivity
    # check that drops the 2020-10-28 episode (the single biggest driver of L4's/L5's aggregate
    # excess) to see how much of the "right-side beats left-side" finding survives.
    # ------------------------------------------------------------------
    main_rows = all_rows[MAIN_THRESHOLD]
    print(f"\n=== L4 vs L5 @ VIX>{MAIN_THRESHOLD} -- does the systemic-epicenter filter matter "
          f"once both legs use the SAME right-side entry timing? ===")
    print(f"  {'leg':6}{'h':>6}{'n':>5}{'mean exc%':>11}{'median exc%':>13}{'win%':>7}{'worst exc%':>11}")
    for leg_name in ["L4", "L5"]:
        for h in HORIZONS:
            a = aggregate(main_rows, leg_name, h)
            print(f"  {leg_name:6}{h:>6}{a['n']:>5}"
                  f"{a['mean']*100 if not np.isnan(a['mean']) else float('nan'):>11.2f}"
                  f"{a['median']*100 if not np.isnan(a['median']) else float('nan'):>13.2f}"
                  f"{a['win']*100 if not np.isnan(a['win']) else float('nan'):>7.1f}"
                  f"{a['worst']*100 if not np.isnan(a['worst']) else float('nan'):>11.2f}")

    exclude = {pd.Timestamp("2020-10-28")}
    print(f"\n=== Sensitivity: drop 2020-10-28 episode, VIX>{MAIN_THRESHOLD}, L4 & L5 ===")
    print(f"  {'leg':6}{'h':>6}{'n':>5}{'mean exc%':>11}{'median exc%':>13}{'win%':>7}{'worst exc%':>11}")
    for leg_name in ["L4", "L5"]:
        for h in HORIZONS:
            a = aggregate_excluding(main_rows, leg_name, h, exclude)
            print(f"  {leg_name:6}{h:>6}{a['n']:>5}"
                  f"{a['mean']*100 if not np.isnan(a['mean']) else float('nan'):>11.2f}"
                  f"{a['median']*100 if not np.isnan(a['median']) else float('nan'):>13.2f}"
                  f"{a['win']*100 if not np.isnan(a['win']) else float('nan'):>7.1f}"
                  f"{a['worst']*100 if not np.isnan(a['worst']) else float('nan'):>11.2f}")


if __name__ == "__main__":
    run()
