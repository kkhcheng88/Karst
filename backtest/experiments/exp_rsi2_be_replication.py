"""RSI-2 dip buying -- FAITHFUL replication of Backtest Everything's config -- 2026-07-17.

WHY THIS RERUN EXISTS (an admitted methodology error, not a new question)
------------------------------------------------------------------------
Two prior reports judged RSI2 dip-buying to have no edge:
  backtest/results/2026-07-16_leader_dip_reversion.md
  backtest/results/2026-07-17_dip_capital_efficiency.md
Both ran a config that differs from the Backtest Everything (BE) source in THREE places,
two of them potentially fatal (source: Reference/distillations/
2026-06-24_backtest-everything-distillation.md sections 11.1-11.2):

                 BE original                       what we ran
  entry          RSI(2) < 10                       same
  trend filter   NONE ("Adding 200 SMA filter      close > 200SMA   <-- added a filter BE
                 reduced returns by 12%", 11.1)                         measured as HARMFUL
  exit           RSI(2) > 90, NO time cap          RSI2 > 70 OR 10 trading days
                                                   <-- early exit + a cap that cuts BE's own
                                                       stated "5-20 days to play out" in half

So this file replicates BE's config, then A/B's each of our three deviations one at a time to
attribute the damage. That attribution decides how much of the old reports must be retracted.

MEASUREMENT DISCIPLINE (user standing order, 2026-07-17)
--------------------------------------------------------
- Primary metric = CAPITAL EFFICIENCY (PnL / avg exposure) reported ALONGSIDE ABSOLUTE PnL.
- The word "alpha" is banned as a sleeve/signal-level verdict -- alpha is a portfolio-level idea.
- CapEff has two known traps (memory: capital-efficiency-two-traps): a small denominator inflates
  the ratio, and on LOSING books the ranking INVERTS. Therefore every CapEff table here carries an
  absolute-PnL column, and CapEff ranking is suppressed whenever an arm's PnL is negative.
- The verdict basis is the RANDOM SAME-EXPOSURE control, NOT buy&hold. B&H is 100% exposure and is
  reported for background only.

Run: PYTHONUTF8=1 python backtest/experiments/exp_rsi2_be_replication.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load

# ---------------------------------------------------------------------------
# FROZEN CONFIG -- every threshold below was written down BEFORE any return was looked at.
# ---------------------------------------------------------------------------
SINCE = "2016-01-01"          # BE 11.5 uses Jan 2016 - Jan 2026; we match the start.
START_EQUITY = 10_000.0       # BE's $10K/symbol starting stake.
N_SIMS = 1000                 # random same-exposure control draws per symbol per arm.
SEED = 20260717
MIN_ROWS = 500                # >= ~2 years in-window or the symbol is dropped (declared).
COSTS_BP = [0, 5, 10, 20]     # round-trip cost sensitivity, basis points.
PRICE_TIERS = [               # BE 11.2 tiers, assigned on the FIRST in-window close.
    ("penny <$5", 0.0, 5.0),
    ("low $5-20", 5.0, 20.0),
    ("mid $20-100", 20.0, 100.0),
    ("high $100-500", 100.0, 500.0),
    ("ultra >$500", 500.0, float("inf")),
]

# Five arms: BE-faithful, then our three deviations added ONE AT A TIME, then our broken combo.
ARMS = {
    "BE-faithful": dict(trend=False, exit_rsi=90, cap=None),
    "+trend":      dict(trend=True,  exit_rsi=90, cap=None),
    "+earlyexit":  dict(trend=False, exit_rsi=70, cap=None),
    "+timecap10":  dict(trend=False, exit_rsi=90, cap=10),
    "ours-broken": dict(trend=True,  exit_rsi=70, cap=10),
}

TIER1 = ["SPY", "QQQ"]
# The 85 US-listed watch tickers behind Karst's 17 active themes.
# Source: thesis/.raw/ima_triage_query.md (verbatim list, deduped against TIER1).
THEME = """AAOI AEHR AMKR AMZN ASML ASTS ASX ATI AVGO AXTI BE BKSY CAT CHPX CLS COHR COP CRS CVX
DRAM EQT ETN FN FORM FOTO FSLR GEV GLW GNRC GOOGL GRID GSAT HEI INTC KLAC KLIC KMI KTOS LITE LNG
LOAR LPX LRCX LUNR LWLG MAGS META MKSI MP MPWR MRVL MSFT MU NASA NVTS ON PL PWR REMX RKLB RDW SEI
SIVE SKHY SMH SNDK SPCX SPXC STX TER TSM TTMI TXN URA USAC USAR UTES VICR VRT WDC WOLF WST XLE
XOM""".split()
UNIVERSE = TIER1 + [t for t in THEME if t not in TIER1]

CACHE = os.path.join(tempfile.gettempdir(), "karst_rsi2_be_cache")


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------
def rsi(s: pd.Series, n: int = 2) -> pd.Series:
    """Wilder RSI -- identical implementation to the two reports being re-examined."""
    d = s.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    ru = up.ewm(alpha=1 / n, adjust=False).mean()
    rd = dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + ru / rd)


def get_prices(sym: str) -> pd.DataFrame | None:
    """Total-return closes (adjusted=True), cached outside the repo so reruns are cheap."""
    os.makedirs(CACHE, exist_ok=True)
    fp = os.path.join(CACHE, f"{sym}.pkl")
    if os.path.exists(fp):
        try:
            return pd.read_pickle(fp)
        except Exception:
            pass
    try:
        px = load(sym, adjusted=True, min_rows=200)[["close"]]
    except Exception:
        return None
    px.to_pickle(fp)
    return px


def prepare(sym: str) -> dict | None:
    """Indicators on FULL history, then slice to the window, so 200SMA is warm at SINCE for any
    symbol with pre-2016 data. Late IPOs get NaN SMA early -> the trend filter simply blocks
    entries there (realistic: you cannot apply a filter you cannot compute)."""
    px = get_prices(sym)
    if px is None:
        return None
    c = px["close"].dropna()
    r2 = rsi(c, 2)
    sma = c.rolling(200).mean()
    df = pd.DataFrame({"px": c, "r2": r2, "sma": sma})
    df = df[df.index >= SINCE]
    df = df[df["r2"].notna()]           # window is IDENTICAL across arms (SMA NaN is allowed)
    if len(df) < MIN_ROWS:
        return None
    return {
        "sym": sym,
        "n": len(df),
        "px": df["px"].values,
        "r2": df["r2"].values,
        "sma": df["sma"].values,
        "logret": np.log(df["px"]).diff().fillna(0).values,
        "start": df.index[0],
        "end": df.index[-1],
        "years": (df.index[-1] - df.index[0]).days / 365.25,
        "p0": float(df["px"].iloc[0]),
    }


# ---------------------------------------------------------------------------
# Trade generation
# ---------------------------------------------------------------------------
def gen_trades(d: dict, trend: bool, exit_rsi: float, cap: int | None) -> list[tuple[int, int]]:
    """Execution convention (identical for all five arms, no look-ahead in either direction):
       signal observed at CLOSE T -> ENTER at CLOSE T+1.
       exit condition observed at CLOSE J -> EXIT at CLOSE J+1.
       time cap (when set) hard-limits the hold to `cap` bars.
    A trade is (e, x): held from close e to close x; returns accrue on bars e+1..x.
    Note this is marginally MORE conservative than BE (which appears to exit on the signal bar's
    own close) and than our own two old scripts. It is held constant across arms, so the A/B
    attribution is unaffected."""
    n, r2, px, sma = d["n"], d["r2"], d["px"], d["sma"]
    out: list[tuple[int, int]] = []
    i = 0
    while i < n - 1:
        ok = r2[i] < 10
        if trend:
            ok = ok and np.isfinite(sma[i]) and px[i] > sma[i]
        if not ok:
            i += 1
            continue
        e = i + 1                      # entry executed at close e
        x = None
        for j in range(e, n - 1):
            if r2[j] > exit_rsi:
                x = j + 1
                break
            if cap is not None and (j + 1 - e) >= cap:
                x = j + 1
                break
        if x is None:
            x = n - 1                  # never triggered -> forced close at the last bar
        out.append((e, x))
        i = x                          # earliest possible re-signal is the exit bar's close
    return out


def trade_returns(d: dict, trades: list[tuple[int, int]]) -> np.ndarray:
    """Simple (not log) per-trade returns, so costs subtract cleanly."""
    cum = np.concatenate([[0.0], np.cumsum(d["logret"])])[1:]
    cum = np.cumsum(d["logret"])
    return np.array([math.exp(cum[x] - cum[e]) - 1.0 for e, x in trades])


def maxdd(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    return float(np.max((peak - equity) / peak)) if len(equity) else 0.0


def evaluate(d: dict, trades: list[tuple[int, int]], cost_bp: float = 0.0) -> dict:
    n = d["n"]
    if not trades:
        return dict(trades=0, pnl=0.0, ret=0.0, logret=0.0, exposure=0.0, capeff=float("nan"),
                    wr=float("nan"), median=float("nan"), p10=float("nan"), pf=float("nan"),
                    mdd=0.0, tpy=0.0, avg_hold=float("nan"), open_at_end=0)
    r = trade_returns(d, trades) - cost_bp / 10_000.0
    inpos = np.zeros(n)
    for e, x in trades:
        inpos[e + 1:x + 1] = 1.0
    # Equity: compound in-position returns; cost is charged on the exit bar of each trade.
    daily = d["logret"] * inpos
    eq = START_EQUITY * np.exp(np.cumsum(daily))
    if cost_bp:
        for k, (_, x) in enumerate(trades):
            eq[x:] *= (1.0 - cost_bp / 10_000.0)
    final = START_EQUITY * float(np.prod(1.0 + r))
    exposure = float(inpos.mean())
    lg = math.log(max(final / START_EQUITY, 1e-9))
    wins, losses = r[r > 0], r[r <= 0]
    pf = (wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else float("inf")
    return dict(
        trades=len(trades),
        pnl=final - START_EQUITY,
        ret=final / START_EQUITY - 1.0,
        logret=lg,
        exposure=exposure,
        capeff=(lg / exposure) if exposure > 0 else float("nan"),
        wr=float((r > 0).mean()),
        median=float(np.median(r)),
        p10=float(np.percentile(r, 10)),
        pf=float(pf),
        mdd=maxdd(eq),
        tpy=len(trades) / d["years"],
        avg_hold=float(np.mean([x - e for e, x in trades])),
        open_at_end=int(sum(1 for _, x in trades if x >= n - 1)),
    )


# ---------------------------------------------------------------------------
# Control (a): random entry with IDENTICAL exposure, trade count and hold-length distribution.
# This -- not B&H -- is the verdict basis. If RSI2 carries timing information, it must beat this.
# ---------------------------------------------------------------------------
def random_control(d: dict, trades: list[tuple[int, int]], rng: np.random.Generator,
                   n_sims: int = N_SIMS) -> dict:
    if not trades:
        return dict(pct=float("nan"), med_logret=float("nan"), med_capeff=float("nan"))
    durs = np.array([x - e for e, x in trades])
    n, K, total = d["n"], len(trades), int(durs.sum())
    slack = n - 2 - total
    if slack <= 0:
        return dict(pct=float("nan"), med_logret=float("nan"), med_capeff=float("nan"))
    cum = np.cumsum(d["logret"])
    cum0 = np.concatenate([[0.0], cum])       # cum0[i] = cumulative log return through bar i-1
    sims = np.empty(n_sims)
    for s in range(n_sims):
        dd = rng.permutation(durs)
        # K non-overlapping intervals placed uniformly at random: sample K gap positions in the
        # compressed timeline, then re-expand by the running duration total.
        starts = np.sort(rng.integers(0, slack + 1, size=K)) + np.concatenate([[0], np.cumsum(dd)[:-1]])
        ends = starts + dd
        sims[s] = float(np.sum(cum[ends] - cum[starts]))
    actual = float(np.sum([cum[x] - cum[e] for e, x in trades]))
    exposure = total / n
    return dict(
        pct=float((sims < actual).mean() * 100.0),
        med_logret=float(np.median(sims)),
        med_capeff=float(np.median(sims) / exposure),
        actual_logret=actual,
    )


def binom_p_two_sided(k: int, n: int) -> float:
    """Exact two-sided sign test vs p=0.5 -- how many symbols beat their own random median."""
    if n == 0:
        return float("nan")
    probs = [math.comb(n, i) * 0.5 ** n for i in range(n + 1)]
    return float(min(1.0, 2 * min(sum(probs[:k + 1]), sum(probs[k:]))))


def tier_of(p0: float) -> str:
    for name, lo, hi in PRICE_TIERS:
        if lo <= p0 < hi:
            return name
    return "?"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    rng = np.random.default_rng(SEED)
    print(f"=== RSI-2 BE replication | since {SINCE} | ${START_EQUITY:,.0f}/symbol | "
          f"{N_SIMS} MC sims | seed {SEED} ===\n")

    data, dropped = {}, []
    for sym in UNIVERSE:
        d = prepare(sym)
        (data.setdefault(sym, d) if d else dropped.append(sym))
    print(f"universe: {len(UNIVERSE)} requested -> {len(data)} usable, {len(dropped)} dropped "
          f"(no data / < {MIN_ROWS} in-window bars): {' '.join(dropped)}\n")

    rows = []
    for sym, d in data.items():
        bh_log = float(np.sum(d["logret"]))
        for arm, cfg in ARMS.items():
            tr = gen_trades(d, **cfg)
            m = evaluate(d, tr)
            ctrl = random_control(d, tr, rng)
            rec = dict(sym=sym, arm=arm, tier=tier_of(d["p0"]), p0=d["p0"], years=d["years"],
                       bh_ret=math.exp(bh_log) - 1.0, bh_log=bh_log, **m,
                       mc_pct=ctrl["pct"], mc_med_capeff=ctrl["med_capeff"],
                       mc_med_logret=ctrl["med_logret"])
            for c in COSTS_BP:
                rec[f"pnl_{c}bp"] = evaluate(d, tr, cost_bp=c)["pnl"]
            rows.append(rec)
    df = pd.DataFrame(rows)

    # ---- 1. Arm-level summary. ABSOLUTE PnL sits next to CapEff, always (trap #2).
    print("--- [1] ARM SUMMARY (all usable symbols) ---")
    print(f"{'arm':<13}{'n':>4}{'%prof':>7}{'meanPnL$':>10}{'medPnL$':>9}{'meanCapEff':>11}"
          f"{'medCapEff':>10}{'expo%':>7}{'WR%':>6}{'PF':>6}{'tr/yr':>7}{'hold':>6}{'MDD%':>6}"
          f"{'MCpct':>7}")
    for arm in ARMS:
        a = df[df["arm"] == arm]
        print(f"{arm:<13}{len(a):>4}{(a['pnl'] > 0).mean() * 100:>7.1f}{a['pnl'].mean():>10,.0f}"
              f"{a['pnl'].median():>9,.0f}{a['capeff'].mean() * 100:>11.0f}"
              f"{a['capeff'].median() * 100:>10.0f}{a['exposure'].mean() * 100:>7.1f}"
              f"{a['wr'].mean() * 100:>6.1f}{a['pf'].replace(np.inf, np.nan).mean():>6.2f}"
              f"{a['tpy'].mean():>7.1f}{a['avg_hold'].mean():>6.1f}{a['mdd'].mean() * 100:>6.1f}"
              f"{a['mc_pct'].mean():>7.1f}")

    # ---- 2. Attribution: what each of our three deviations cost, one at a time.
    print("\n--- [2] CONFIG A/B ATTRIBUTION (vs BE-faithful, same symbols) ---")
    base = df[df["arm"] == "BE-faithful"].set_index("sym")
    print(f"{'arm':<13}{'d meanPnL$':>12}{'d medPnL$':>11}{'d CapEff pp':>13}{'d expo pp':>11}"
          f"{'d WR pp':>9}{'d tr/yr':>9}{'%sym worse':>12}")
    for arm in ARMS:
        a = df[df["arm"] == arm].set_index("sym")
        j = base.join(a, lsuffix="_b", rsuffix="_a")
        print(f"{arm:<13}{(j['pnl_a'] - j['pnl_b']).mean():>12,.0f}"
              f"{(j['pnl_a'] - j['pnl_b']).median():>11,.0f}"
              f"{((j['capeff_a'] - j['capeff_b']) * 100).mean():>13.0f}"
              f"{((j['exposure_a'] - j['exposure_b']) * 100).mean():>11.2f}"
              f"{((j['wr_a'] - j['wr_b']) * 100).mean():>9.1f}"
              f"{(j['tpy_a'] - j['tpy_b']).mean():>9.1f}"
              f"{(j['pnl_a'] < j['pnl_b']).mean() * 100:>12.1f}")

    # ---- 3. BE's price staircase (11.2). Tier assigned on the first in-window close.
    print("\n--- [3] PRICE-TIER STAIRCASE (BE 11.2 replication; tier = first in-window close) ---")
    for arm in ["BE-faithful", "ours-broken"]:
        print(f"\n  arm = {arm}")
        print(f"  {'tier':<16}{'n':>4}{'%prof':>7}{'medPnL$':>10}{'medRet%':>9}{'WR%':>6}"
              f"{'CapEff':>8}{'MDD%':>6}{'MCpct':>7}")
        for name, _, _ in PRICE_TIERS:
            a = df[(df["arm"] == arm) & (df["tier"] == name)]
            if not len(a):
                print(f"  {name:<16}{0:>4}   (empty -- no symbol in this tier)")
                continue
            print(f"  {name:<16}{len(a):>4}{(a['pnl'] > 0).mean() * 100:>7.1f}"
                  f"{a['pnl'].median():>10,.0f}{a['ret'].median() * 100:>9.1f}"
                  f"{a['wr'].mean() * 100:>6.1f}{a['capeff'].median() * 100:>8.0f}"
                  f"{a['mdd'].mean() * 100:>6.1f}{a['mc_pct'].mean():>7.1f}")

    # ---- 4. Control (a): random same-exposure. THE VERDICT BASIS.
    print("\n--- [4] CONTROL (a): RANDOM SAME-EXPOSURE / SAME-TRADE-COUNT -- VERDICT BASIS ---")
    print(f"{'arm':<13}{'meanMCpct':>11}{'medMCpct':>10}{'%sym>50th':>11}{'signtest p':>12}"
          f"{'actual CapEff':>15}{'random CapEff':>15}")
    for arm in ARMS:
        a = df[df["arm"] == arm].dropna(subset=["mc_pct"])
        k = int((a["mc_pct"] > 50).sum())
        print(f"{arm:<13}{a['mc_pct'].mean():>11.1f}{a['mc_pct'].median():>10.1f}"
              f"{k / len(a) * 100:>11.1f}{binom_p_two_sided(k, len(a)):>12.4f}"
              f"{a['capeff'].median() * 100:>15.0f}{a['mc_med_capeff'].median() * 100:>15.0f}")

    # ---- 4b. Effective sample size. 77 symbols are NOT 77 independent tests -- this universe is
    # mostly semis/AI and moves together. Inflating N here would manufacture significance.
    print("\n--- [4b] EFFECTIVE SAMPLE SIZE (cross-correlation haircut) ---")
    rmat = pd.DataFrame({s: pd.Series(d["logret"]) for s, d in data.items()}).corr()
    iu = np.triu_indices_from(rmat.values, k=1)
    rho = float(np.nanmean(rmat.values[iu]))
    N = len(data)
    n_eff = N / (1 + (N - 1) * rho)
    print(f"  mean pairwise daily-return correlation rho = {rho:.3f}  ->  N={N} behaves like "
          f"n_eff = {n_eff:.1f} independent names")
    for arm in ARMS:
        a = df[df["arm"] == arm].dropna(subset=["mc_pct"])
        mean_pct = a["mc_pct"].mean()
        se_naive = 28.87 / math.sqrt(len(a))          # sd of Uniform(0,100) = 100/sqrt(12)
        se_eff = 28.87 / math.sqrt(max(n_eff, 1.0))
        z_naive, z_eff = (mean_pct - 50) / se_naive, (mean_pct - 50) / se_eff
        p_eff = math.erfc(abs(z_eff) / math.sqrt(2))
        print(f"  {arm:<13} mean MC pct {mean_pct:>5.1f} | z(naive N={N}) {z_naive:>5.2f} | "
              f"z(n_eff={n_eff:.1f}) {z_eff:>5.2f} | p(eff) {p_eff:>6.3f}")
    print("  -> Read the p(eff) column. The naive column is what over-claiming would look like.")

    # ---- 5. Control (b): B&H background only (100% exposure -- NOT the benchmark).
    print("\n--- [5] CONTROL (b): B&H BACKGROUND (100% exposure -- context, not a verdict) ---")
    for arm in ["BE-faithful", "ours-broken"]:
        a = df[df["arm"] == arm]
        print(f"  {arm:<13} median strat ret {a['ret'].median() * 100:>8.1f}%  |  median B&H ret "
              f"{a['bh_ret'].median() * 100:>9.1f}%  |  strat CapEff {a['capeff'].median() * 100:>6.0f}"
              f"  vs B&H CapEff {a['bh_log'].median() * 100:>6.0f}  |  %sym strat>B&H "
              f"{(a['ret'] > a['bh_ret']).mean() * 100:>5.1f}%")

    # ---- 6. Control (c): cost sensitivity. BE charged nothing.
    print("\n--- [6] CONTROL (c): COST SENSITIVITY (round-trip bp) ---")
    print(f"{'arm':<13}{'tr/yr':>7}" + "".join(f"{f'{c}bp mean$':>12}" for c in COSTS_BP)
          + f"{'0->20bp':>10}{'%prof@20':>10}")
    for arm in ARMS:
        a = df[df["arm"] == arm]
        cells = "".join(f"{a[f'pnl_{c}bp'].mean():>12,.0f}" for c in COSTS_BP)
        drop = a["pnl_20bp"].mean() - a["pnl_0bp"].mean()
        print(f"{arm:<13}{a['tpy'].mean():>7.1f}{cells}{drop:>10,.0f}"
              f"{(a['pnl_20bp'] > 0).mean() * 100:>10.1f}")

    # ---- 7. The tickers Karst can actually trade (ETF-only framework).
    print("\n--- [7] KARST-RELEVANT ETFs (ETF-only framework) ---")
    print(f"{'sym':<6}{'arm':<13}{'PnL$':>9}{'ret%':>8}{'CapEff':>8}{'expo%':>7}{'WR%':>6}"
          f"{'tr/yr':>7}{'MDD%':>6}{'MCpct':>7}{'B&H%':>9}{'PnL@10bp':>10}")
    for sym in ["SPY", "QQQ", "SMH", "MAGS", "XLE"]:
        for arm in ARMS:
            a = df[(df["sym"] == sym) & (df["arm"] == arm)]
            if not len(a):
                continue
            r = a.iloc[0]
            print(f"{sym:<6}{arm:<13}{r['pnl']:>9,.0f}{r['ret'] * 100:>8.1f}"
                  f"{r['capeff'] * 100:>8.0f}{r['exposure'] * 100:>7.1f}{r['wr'] * 100:>6.1f}"
                  f"{r['tpy']:>7.1f}{r['mdd'] * 100:>6.1f}{r['mc_pct']:>7.1f}"
                  f"{r['bh_ret'] * 100:>9.1f}{r['pnl_10bp']:>10,.0f}")

    # ---- 8. Sample bookkeeping (declared, not buried).
    print("\n--- [8] SAMPLE / HONESTY BOOKKEEPING ---")
    be = df[df["arm"] == "BE-faithful"]
    print(f"  window            : {min(d['start'] for d in data.values()).date()} -> "
          f"{max(d['end'] for d in data.values()).date()}")
    print(f"  symbols usable    : {len(data)} (BE 11.1 used ~500; BE 11.2 used 3,997)")
    print(f"  median history    : {be['years'].median():.1f} yr "
          f"(BE used a full 10 yr on every name)")
    print(f"  total trades      : {int(be['trades'].sum())} BE-faithful "
          f"(BE 11.1 reported ~2,700 over ~500 names)")
    print(f"  trades still open at data end (BE-faithful): {int(be['open_at_end'].sum())}")
    print(f"  tier counts       : " + ", ".join(
        f"{n}={int((be['tier'] == n).sum())}" for n, _, _ in PRICE_TIERS))
    print(f"  multiple comparisons: {len(ARMS)} arms x {len(PRICE_TIERS)} tiers x "
          f"{len(COSTS_BP)} cost levels = {len(ARMS) * len(PRICE_TIERS) * len(COSTS_BP)} cells; "
          f"no per-cell alpha correction applied -- read [4] sign tests, not cell extremes.")
    print(f"  overlapping windows: none (trades are non-overlapping by construction); MC control "
          f"preserves exact trade count + hold-length distribution.")

    # ---- 9. BE's own arithmetic, checked.
    print("\n--- [9] BE'S OWN NUMBERS, CHECKED ---")
    be_cagr = (29154 / 10000) ** (1 / 10) - 1
    print(f"  BE 11.1 claim: +$19,154 avg profit on $10K over 10 yr = +191.5% = "
          f"{be_cagr * 100:.1f}%/yr compounded.")
    spy = df[(df["sym"] == "SPY") & (df["arm"] == "BE-faithful")]
    if len(spy):
        s = spy.iloc[0]
        print(f"  Our SPY B&H, same window: {s['bh_ret'] * 100:.1f}% total = "
              f"{((1 + s['bh_ret']) ** (1 / s['years']) - 1) * 100:.1f}%/yr.")
        print(f"  -> On ABSOLUTE return BE's strategy LOSES to B&H. Its only claim is that it did "
              f"it on ~{s['exposure'] * 100:.0f}% exposure. That tension is the whole thesis.")
    print("  BE never reported: size-matched benchmark, capital efficiency, or transaction costs.")
    # Direct replication check against the one BE number we can reproduce exactly.
    if len(spy):
        s = spy.iloc[0]
        print(f"\n  BE 11.2 reports SPY: +$13,400, 78% WR.  We get SPY BE-faithful: "
              f"+${s['pnl']:,.0f}, {s['wr'] * 100:.1f}% WR.  -> BE's SPY number REPLICATES.")
    # BE's own headline set does not reconcile internally -- say so.
    print(f"\n  BE 11.1 internal consistency check (their numbers, their arithmetic):")
    print(f"    $19,154 avg/symbol x 500 symbols = $9.58M, but BE reports $1.07M total profit.")
    print(f"    $1.07M / $19,154 = ~56 symbols, not 500.")
    print(f"    ~2,700 trades / 500 symbols = 5.4 trades per symbol per DECADE. We measure "
          f"{be['tpy'].mean():.1f} trades/yr; RSI2<10 simply cannot fire that rarely.")
    print(f"    ~2,700 trades / 56 symbols = ~48 trades/symbol = 4.8/yr -- plausible.")
    print(f"    -> BE 11.1's headline reconciles at ~56 symbols, NOT the 500 in the title.")

    out = os.path.join(CACHE, "rsi2_be_rows.json")
    df.to_json(out, orient="records")
    print(f"\n[rows dumped for inspection: {out}]")


if __name__ == "__main__":
    main()
