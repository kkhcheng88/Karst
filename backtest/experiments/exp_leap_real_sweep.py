"""Experiment: LEAP real-data sweep — SPY x ^VIX & QQQ x ^VXN, pre-registered grid.

Question
--------
Rebuild the LEAP-engine evidence on REAL vol-index IV anchors (^VIX / ^VXN via
backtest/data.py -> yfinance) and REAL total returns (yfinance adjusted close),
replacing the offline sandbox draft (exp_leap_delta_sweep.py) that used an
RV-proxy IV and a price-only SPY pickle. Decide, with bankable data: which delta,
which gate, which sizing frame for the deep-ITM LEAP alpha engine.

Method (pre-registered; the grid IS the experiment — every cell reported)
------
Mirror     : PORTFOLIO frame vs B&H total-return benchmark (HK 30% dividend
             withholding netted) — the way the sleeve would actually be run.
Increment  : real IV anchor + real dividends + real cash rate vs the sandbox
             draft's RV-proxy/price-only run (same grid, so cell-by-cell diff
             isolates the data upgrade).
Horizon    : continuous program, 1y LEAP call rolled at 63 trading days left.

Grid (all cells reported, no cherry-picking):
  underlying x IV : SPY x ^VIX, QQQ x ^VXN  (SPMO excluded: no vol index, short
                    options history — see Caveats)
  delta           : {0.30, 0.50, 0.70, 0.80}  (1y call, roll @ 63 td remaining)
  gate            : ALWAYS
                    GATED           hold iff close > 200SMA, sell on break
                    GATED+DIP       enter iff close > 200SMA AND RSI-2 < 10 within
                                    last 5 days; exit on close < 200SMA
                    GATED+DIP+HYST  same entry; exit only after 5 CONSECUTIVE
                                    closes < 200SMA*0.98 (re-eligibility: close
                                    back above 200SMA, then a fresh dip trigger)
  frame           : SLEEVE (100% of sleeve compounds in the option)
                    PORTFOLIO (premium budget 10% of NAV, re-set to 10% at each
                    entry/roll, remainder in cash at ^IRX)
  cost            : 0.5%/side of option premium (base), 1.0%/side (sensitivity)
  IV -> 1y tenor  : IV_1y = (VIX or VXN)/100 * m, m in {0.85 base, 1.00, 1.15}.
                    Repo convention is NOT pinned: options_engine.py uses raw
                    VIX (m=1.00) but documents it as vega-overstating; the
                    2026-06-30 leap_timing results file recommends ~0.8x for 1y
                    tenor. So m=0.85 base with 1.00 / 1.15 sensitivities.
  cash rate       : ^IRX (13-week T-bill, %/yr) / 252 per day, forward-filled;
                    also used as the BSM pricing r (time-varying). Sensitivity:
                    cash accrual = 0% (pricing r unchanged, isolates cash drag).
  dividends       : BSM q = trailing-12m gross dividend yield, reconstructed from
                    (adjusted-close return - raw-close return) with a 1bp/day
                    threshold to kill adjustment rounding noise (options priced
                    on GROSS yield).
  benchmark       : B&H total return net of HK 30% withholding on dividends
                    (r_net = r_adj - 0.30 * dividend-yield component, deducted
                    on actual ex-div days = an exact version of the daily drip).
                    SPY cells vs SPY B&H net-TR; QQQ cells vs SPY B&H net-TR
                    (core benchmark, main tables) + vs QQQ B&H net-TR (appendix).
  execution       : signal at close T -> executed at close T+1 (all gates shifted
                    one day; rolls are calendar-mechanical, executed at dte=63).
  windows         : FULL (max available: SPY from ~1994-02 after 200SMA + 252d
                    yield warm-up; QQQ x VXN from 2001-01), H1 1996-2010 (QQQ:
                    2001-2010), H2 2011-2026, 2016-2020, 2021+.

Per-cell metrics: CAGR / Sharpe (raw daily returns, repo convention) / MaxDD /
Jensen alpha (annualized, t-stat) vs benchmark / effective leverage (median of
contracts*delta*S*100/NAV over in-position days) / theta bleed %/yr (median
annualized 1-day value decay / premium, per-unit, frame-independent) / roll
count / exposure / cost drag pp/yr (zero-cost shadow CAGR minus actual CAGR).

Cross-foot (hard asserts, every bar of every accounting run):
  NAV == cash + option market value;  cash >= 0;  NAV > 0;
  NAV_t == NAV_{t-1} + cash interest + option P&L - costs (roll conservation).

Engine note: option math uses repo backtest/bsm.py verbatim. A new simulator is
written HERE (not options_engine.simulate_leap) because the engine interface does
not support: time-varying r/q, per-day telemetry (delta/theta/marks) needed for
EffLev/theta-bleed, the PORTFOLIO frame, event flags for roll accounting, or
cross-foot asserts. Structure mirrors simulate_leap (dte countdown, roll@63,
fractional contracts).

Run:  PYTHONUTF8=1 python backtest/experiments/exp_leap_real_sweep.py
Writes: backtest/results/2026-07-06_leap_real_sweep.md (tables + provenance;
narrative Conclusions/Caveats finalized by hand afterwards).
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bsm                     # noqa: E402  (repo BSM — the only option math used)
import metrics                 # noqa: E402
import signals                 # noqa: E402
from data import load          # noqa: E402

TD = 252
CAPITAL = 10_000.0
DTE_INIT = 252                 # 1y LEAP in trading days (repo convention, bsm.py)
ROLL_DTE = 63
DELTAS = [0.30, 0.50, 0.70, 0.80]
GATES = ["ALWAYS", "GATED", "GATED+DIP", "GATED+DIP+HYST"]
IV_MULTS = [0.85, 1.00, 1.15]

# (name, iv_mult, cost_per_side, cash_earns_irx)
SETTINGS = [
    ("base",   0.85, 0.005, True),
    ("iv100",  1.00, 0.005, True),
    ("iv115",  1.15, 0.005, True),
    ("cost10", 0.85, 0.010, True),
    ("cash0",  0.85, 0.005, False),
]
ZC = ("zerocost", 0.85, 0.0, True)          # shadow for cost-drag

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-06_leap_real_sweep.md")

ASSERT_COUNT = {"n": 0, "runs": 0}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def build_underlying(under: str, volsym: str, irx: pd.Series):
    """Join underlying (raw+adj), vol index, IRX; compute signals, q, net-TR."""
    raw = load(under)
    adj = load(under, adjusted=True)
    vol = load(volsym)
    prov = []
    for name, df in [(under, raw), (f"{under}(adj)", adj), (volsym, vol)]:
        prov.append((name, df.attrs.get("source", "?"), len(df),
                     str(df.index.min().date()), str(df.index.max().date())))

    close = raw["close"]
    r_adj = adj["close"].pct_change()
    r_raw = close.pct_change()
    dy = (r_adj - r_raw).clip(lower=0.0)
    dy = dy.where(dy > 1e-4, 0.0)             # 1bp threshold: kill rounding noise
    r_net = r_adj - 0.30 * dy                 # HK 30% withholding on dividends
    div_cash = dy * close.shift(1)
    q_trail = div_cash.rolling(TD).sum() / close   # trailing-12m gross yield

    df = pd.DataFrame({
        "close": close,
        "sma": close.rolling(200).mean(),
        "rsi2": signals.rsi(close, 2),
        "q": q_trail,
        "r_net": r_net,
    })
    df = df.join(vol["close"].rename("vol"), how="inner")
    df["irx"] = irx.reindex(df.index).ffill()
    df = df.dropna(subset=["close", "sma", "rsi2", "q", "vol", "irx"])
    return df, prov, r_net


def build_gates(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Signal-time gate series, then shift(1) = T+1 close execution."""
    close, sma, r2 = df["close"], df["sma"], df["rsi2"]
    above = (close > sma)
    dip_recent = ((r2 < 10).astype(float).rolling(5, min_periods=1).max() > 0)
    below_hyst = (close < sma * 0.98)

    n = len(df)
    always = pd.Series(True, index=df.index)

    # GATED+DIP: stateful — enter on (above & dip in last 5d), exit on close<SMA200
    gd = np.zeros(n, dtype=bool)
    hold = False
    av, dv = above.values, dip_recent.values
    for i in range(n):
        if not hold and av[i] and dv[i]:
            hold = True
        elif hold and not av[i]:
            hold = False
        gd[i] = hold

    # GATED+DIP+HYST: same entry; exit after 5 CONSECUTIVE closes < SMA200*0.98
    gh = np.zeros(n, dtype=bool)
    hold, cnt = False, 0
    bh = below_hyst.values
    for i in range(n):
        if not hold:
            if av[i] and dv[i]:
                hold, cnt = True, 0
        else:
            cnt = cnt + 1 if bh[i] else 0
            if cnt >= 5:
                hold, cnt = False, 0
        gh[i] = hold

    out = {
        "ALWAYS": always,
        "GATED": above,
        "GATED+DIP": pd.Series(gd, index=df.index),
        "GATED+DIP+HYST": pd.Series(gh, index=df.index),
    }
    return {k: v.shift(1).fillna(False).astype(bool).values for k, v in out.items()}


# ---------------------------------------------------------------------------
# Unit option path (per-contract marks & events; sizing-independent)
# ---------------------------------------------------------------------------

def simulate_unit_path(close, iv, r_arr, q_arr, gate, target_delta,
                       dte_init=DTE_INIT, roll_dte=ROLL_DTE):
    """Daily per-unit option marks + trade events for one delta x gate x IV path.

    Entry/exit/roll timing and strikes are independent of $ sizing, so both
    frames / all cost & cash settings reuse this path (frame = pure accounting).
    """
    n = len(close)
    mark = np.full(n, np.nan)        # end-of-day mark of the held contract
    mark_pre = np.full(n, np.nan)    # today's value of the contract held overnight
    sell = np.zeros(n, dtype=bool)
    sell_mark = np.full(n, np.nan)
    buy = np.zeros(n, dtype=bool)
    buy_mark = np.full(n, np.nan)
    rolled = np.zeros(n, dtype=bool)
    hold_eod = np.zeros(n, dtype=bool)
    delta_eod = np.full(n, np.nan)
    theta_ann = np.full(n, np.nan)

    holding = False
    K = 0.0
    dte = 0
    for i in range(n):
        if holding and i > 0:
            dte -= 1
        S, sig, r, q = close[i], max(iv[i], 1e-4), r_arr[i], q_arr[i]

        if holding:
            mark_pre[i] = bsm.call_price(S, K, max(dte / TD, 1e-6), r, q, sig)

        allowed = bool(gate[i])
        if holding and ((not allowed) or dte <= roll_dte):
            sell[i] = True
            sell_mark[i] = mark_pre[i]
            rolled[i] = allowed and dte <= roll_dte
            holding = False

        if (not holding) and allowed:
            T0 = dte_init / TD
            K = bsm.strike_for_call_delta(S, T0, r, q, sig, target_delta)
            bp = bsm.call_price(S, K, T0, r, q, sig)
            if bp > 1e-12:
                buy[i] = True
                buy_mark[i] = bp
                holding = True
                dte = dte_init

        if holding:
            T_rem = max(dte / TD, 1e-6)
            mk = buy_mark[i] if buy[i] else mark_pre[i]
            mark[i] = mk
            delta_eod[i] = bsm.call_delta(S, K, T_rem, r, q, sig)
            p1 = bsm.call_price(S, K, max(T_rem - 1.0 / TD, 1e-6), r, q, sig)
            theta_ann[i] = (mk - p1) / mk * TD if mk > 1e-9 else np.nan
            hold_eod[i] = True

    return {"mark": mark, "mark_pre": mark_pre, "sell": sell, "sell_mark": sell_mark,
            "buy": buy, "buy_mark": buy_mark, "rolled": rolled, "hold": hold_eod,
            "delta": delta_eod, "theta": theta_ann}


# ---------------------------------------------------------------------------
# Frame accounting (cross-foot asserted every bar)
# ---------------------------------------------------------------------------

def account(unit, r_cash, cost, budget_frac, capital=CAPITAL):
    """NAV path for a sizing frame. budget_frac=1.0 -> SLEEVE; 0.10 -> PORTFOLIO.

    Asserts every bar: NAV = cash + option value; cash >= 0; NAV > 0;
    NAV_t = NAV_{t-1} + interest + option P&L - costs  (roll conservation).
    """
    mark, mark_pre = unit["mark"], unit["mark_pre"]
    sell, sell_mark = unit["sell"], unit["sell_mark"]
    buy, buy_mark = unit["buy"], unit["buy_mark"]
    n = len(mark)
    nav = np.empty(n)
    conts = np.zeros(n)
    cash, c = capital, 0.0
    prev_nav, prev_mark = capital, np.nan

    for i in range(n):
        interest = cash * r_cash[i]
        cash += interest
        costs = 0.0
        pnl = c * (mark_pre[i] - prev_mark) * 100.0 if c > 0.0 else 0.0

        if sell[i]:
            gross = c * sell_mark[i] * 100.0
            cash += gross * (1.0 - cost)
            costs += gross * cost
            c = 0.0
        if buy[i]:
            if c != 0.0:
                raise AssertionError(f"buy with open contracts at bar {i}")
            spend = budget_frac * cash
            prem = spend / (1.0 + cost)
            c = prem / (buy_mark[i] * 100.0)
            cash -= spend
            costs += spend - prem

        v = cash + (c * mark[i] * 100.0 if c > 0.0 else 0.0)
        expected = prev_nav + interest + pnl - costs
        if abs(v - expected) > 1e-7 * max(1.0, abs(expected)):
            raise AssertionError(
                f"cross-foot fail bar {i}: nav={v!r} expected={expected!r}")
        if cash < -1e-9:
            raise AssertionError(f"negative cash bar {i}: {cash!r}")
        if v <= 0:
            raise AssertionError(f"non-positive NAV bar {i}: {v!r}")
        ASSERT_COUNT["n"] += 3
        nav[i] = v
        conts[i] = c
        prev_nav = v
        prev_mark = mark[i] if c > 0.0 else np.nan

    ASSERT_COUNT["runs"] += 1
    return nav, conts


# ---------------------------------------------------------------------------
# Metrics per window
# ---------------------------------------------------------------------------

def window_metrics(nav, conts, unit, close, bench_ret, own_ret, lo, hi):
    navw = nav[lo:hi]
    norm = navw / navw[0] * CAPITAL
    ret = navw[1:] / navw[:-1] - 1.0
    out = {
        "CAGR": metrics.cagr(norm),
        "Sharpe": metrics.ann_sharpe(ret),
        "MaxDD": metrics.max_drawdown(norm),
    }
    a, b, t = metrics.jensen_alpha(ret, bench_ret[lo + 1:hi])
    out["Alpha"], out["Beta"], out["t"] = a, b, t
    if own_ret is not None:
        ao, bo, to = metrics.jensen_alpha(ret, own_ret[lo + 1:hi])
        out["AlphaOwn"], out["tOwn"] = ao, to

    inpos = unit["hold"][lo:hi] & (conts[lo:hi] > 0)
    if inpos.sum() > 0:
        with np.errstate(invalid="ignore", divide="ignore"):
            lev = conts[lo:hi] * unit["delta"][lo:hi] * close[lo:hi] * 100.0 / navw
        lev = lev[inpos & np.isfinite(lev)]
        th = unit["theta"][lo:hi][inpos]
        th = th[np.isfinite(th)]
        out["EffLev"] = float(np.median(lev)) if len(lev) else np.nan
        out["Theta"] = float(np.median(th)) if len(th) else np.nan
    else:
        out["EffLev"], out["Theta"] = np.nan, np.nan
    out["Rolls"] = int(unit["rolled"][lo:hi].sum())
    out["Expo"] = float(inpos.mean())
    return out


def bench_metrics(bench_ret, lo, hi):
    r = bench_ret[lo + 1:hi]
    navb = np.concatenate([[1.0], np.cumprod(1.0 + r)])
    return {"CAGR": metrics.cagr(navb), "Sharpe": metrics.ann_sharpe(r),
            "MaxDD": metrics.max_drawdown(navb)}


def make_windows(under: str, index: pd.DatetimeIndex):
    end = index[-1]
    w = [(f"FULL {index[0].date()}~{end.date()}", index[0], end)]
    h1 = ("H1 1996-2010", "1996-01-01") if under == "SPY" else ("H1 2001-2010", "2001-01-01")
    w += [(h1[0], pd.Timestamp(h1[1]), pd.Timestamp("2010-12-31")),
          ("H2 2011-2026", pd.Timestamp("2011-01-01"), end),
          ("2016-2020", pd.Timestamp("2016-01-01"), pd.Timestamp("2020-12-31")),
          ("2021+", pd.Timestamp("2021-01-01"), end)]
    return w


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _p(x, dec=1):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:+.{dec}f}%"


def _a(m, own=False):
    a = m.get("AlphaOwn" if own else "Alpha")
    t = m.get("tOwn" if own else "t")
    if a is None or not np.isfinite(a):
        return "n/a"
    return f"{a * 100:+.1f}pp (t{t:+.1f})"


def _ruin(m):
    return " **RUIN**" if np.isfinite(m["MaxDD"]) and m["MaxDD"] <= -0.99 else ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    irx_df = load("^IRX")
    irx = irx_df["close"]
    prov_all = [("^IRX", irx_df.attrs.get("source", "?"), len(irx_df),
                 str(irx_df.index.min().date()), str(irx_df.index.max().date()))]

    data = {}
    spy_rnet_full = None
    for under, volsym in [("SPY", "^VIX"), ("QQQ", "^VXN")]:
        df, prov, r_net_full = build_underlying(under, volsym, irx)
        data[under] = {"df": df, "vol": volsym}
        prov_all += prov
        if under == "SPY":
            spy_rnet_full = r_net_full
        print(f"{under} joined: {df.index[0].date()} -> {df.index[-1].date()}, "
              f"{len(df)} days", flush=True)

    # Per-underlying arrays, gates, windows, benchmark returns
    for under, d in data.items():
        df = d["df"]
        d["close"] = df["close"].values
        d["iv_raw"] = df["vol"].values / 100.0
        d["r_arr"] = df["irx"].values / 100.0
        d["q_arr"] = df["q"].values
        d["r_cash"] = d["r_arr"] / TD
        d["gates"] = build_gates(df)
        d["windows"] = make_windows(under, df.index)
        d["bench_spy"] = spy_rnet_full.reindex(df.index).values   # core benchmark
        d["bench_own"] = df["r_net"].values
        d["wslices"] = []
        for wname, ws, we in d["windows"]:
            mask = (df.index >= ws) & (df.index <= we)
            idx = np.where(mask)[0]
            d["wslices"].append((wname, int(idx[0]), int(idx[-1]) + 1))

    # Sanity anchor: SPY B&H net TR 1996 -> end
    sdf = data["SPY"]["df"]
    a_mask = sdf.index >= "1996-01-01"
    a_lo = int(np.where(a_mask)[0][0])
    anchor = bench_metrics(data["SPY"]["bench_own"], a_lo, len(sdf))
    print(f"SANITY SPY B&H TR (HK net) 1996->end: CAGR {anchor['CAGR'] * 100:.2f}% "
          f"Sharpe {anchor['Sharpe']:.2f} MaxDD {anchor['MaxDD'] * 100:.1f}%", flush=True)

    # Unit paths: 2 underlyings x 4 deltas x 4 gates x 3 IV mults = 96 sims
    paths = {}
    for under, d in data.items():
        for m in IV_MULTS:
            tm = time.time()
            iv = d["iv_raw"] * m
            for delta in DELTAS:
                for g in GATES:
                    paths[(under, delta, g, m)] = simulate_unit_path(
                        d["close"], iv, d["r_arr"], d["q_arr"], d["gates"][g], delta)
            print(f"  paths {under} m={m}: {time.time() - tm:.0f}s", flush=True)

    # Accounting + metrics for every setting x frame x cell x window
    R = {}      # R[under][sname][frame][(delta,gate)][wname] -> metrics
    for under, d in data.items():
        R[under] = {}
        zc_nav = {}          # (frame, delta, gate) -> zero-cost NAV (m=0.85)
        for sname, m, cost, cash_on in SETTINGS + [ZC]:
            R[under][sname] = {"SLEEVE": {}, "PORTFOLIO": {}}
            r_cash = d["r_cash"] if cash_on else np.zeros(len(d["close"]))
            for frame, bf in [("SLEEVE", 1.0), ("PORTFOLIO", 0.10)]:
                for delta in DELTAS:
                    for g in GATES:
                        unit = paths[(under, delta, g, m)]
                        nav, conts = account(unit, r_cash, cost, bf)
                        own = d["bench_own"] if under == "QQQ" else None
                        cells = {}
                        for wname, lo, hi in d["wslices"]:
                            cells[wname] = window_metrics(
                                nav, conts, unit, d["close"], d["bench_spy"],
                                own, lo, hi)
                        R[under][sname][frame][(delta, g)] = cells
                        if sname == "zerocost":
                            zc_nav[(frame, delta, g)] = nav
        # cost drag pp/yr per window: zero-cost CAGR - actual CAGR (m=0.85 pair)
        for sname in ("base", "cost10"):
            for frame in ("SLEEVE", "PORTFOLIO"):
                for key, cells in R[under][sname][frame].items():
                    zn = zc_nav[(frame,) + key]
                    for wname, lo, hi in d["wslices"]:
                        zw = zn[lo:hi]
                        cz = metrics.cagr(zw / zw[0] * CAPITAL)
                        cells[wname]["CostDrag"] = (cz - cells[wname]["CAGR"]) * 100
        print(f"accounting {under} done ({time.time() - t0:.0f}s)", flush=True)

    # -----------------------------------------------------------------------
    # Write results markdown
    # -----------------------------------------------------------------------
    L = []
    add = L.append
    add("# Result — LEAP real-data sweep: delta x gate x frame on real ^VIX/^VXN + real total returns")
    add("")
    add("**Date:** 2026-07-06  **Script:** `backtest/experiments/exp_leap_real_sweep.py`  "
        "**Status:** active (supersedes the RV-proxy sandbox draft "
        "`exp_leap_delta_sweep.py` / `2026-07-06_leap_delta_sweep.md`)")
    add("")
    add("## Question")
    add("")
    add("Which LEAP delta {0.30/0.50/0.70/0.80}, which gate {ALWAYS/GATED/GATED+DIP/")
    add("GATED+DIP+HYST}, which sizing frame {SLEEVE/PORTFOLIO 10%} — decided on REAL")
    add("vol-index IV (^VIX/^VXN), real dividends, real cash rates and an HK-net")
    add("total-return benchmark. Pre-registered grid; every cell reported.")
    add("")
    add("## Method")
    add("")
    add("- 1y LEAP call (252 td), roll @ 63 td remaining; fractional contracts; BSM via")
    add("  repo `backtest/bsm.py` (new simulator in the experiment file because")
    add("  `options_engine.simulate_leap` lacks time-varying r/q, telemetry, the")
    add("  PORTFOLIO frame and cross-foot asserts — math is repo `bsm.py` verbatim).")
    add("- IV_1y = volindex/100 x m, m in {0.85 base, 1.00, 1.15}. Repo convention not")
    add("  pinned (options_engine uses m=1.00 but flags it as vega-overstating; the")
    add("  2026-06-30 leap-timing results file recommends ~0.8x for a 1y tenor), so")
    add("  0.85 is the base with 1.00/1.15 bounding it.")
    add("- Pricing r and PORTFOLIO/SLEEVE idle-cash rate = ^IRX (13-wk T-bill)/252,")
    add("  forward-filled; `cash0` sensitivity zeroes only the cash accrual.")
    add("- BSM q = trailing-12m gross dividend yield reconstructed from adjusted-vs-raw")
    add("  close return gaps (1bp/day threshold vs rounding noise). Options priced gross.")
    add("- Benchmark = B&H total return net of HK 30% dividend withholding:")
    add("  r_net = r_adj - 0.30 x dividend component, deducted on actual ex-div days")
    add("  (exact form of the daily-drip spec). QQQ cells: main tables vs SPY net-TR")
    add("  (core benchmark), appendix vs QQQ net-TR (tool mirror).")
    add("- Execution: signal at close T -> trade at close T+1 (all gate series shifted")
    add("  1 day; rolls are calendar-mechanical at dte=63).")
    add("- Costs: % of option premium per side; charged on entry, exit and both legs of")
    add("  a roll. Sharpe = raw daily returns (repo convention, no rf subtraction).")
    add("- EffLev = median over in-position days of contracts x delta x S x 100 / NAV")
    add("  (frame-level). Theta bleed = median annualized 1-day value decay / premium")
    add("  (per-unit, same both frames). Cost drag = zero-cost-shadow CAGR - actual CAGR.")
    add("- Medians (not means) for EffLev/Theta: OTM-crash cells otherwise blow up the")
    add("  mean via near-worthless marks.")
    add("")
    add("## Data provenance (backtest/data.py `load()`)")
    add("")
    add("| Series | Source | Rows | From | To |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in prov_all:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")
    for under, d in data.items():
        df = d["df"]
        add(f"- {under} x {d['vol']} joined sim window: {df.index[0].date()} -> "
            f"{df.index[-1].date()} ({len(df)} days; start = 200SMA + 252d-yield "
            f"warm-up and vol-index availability).")
    add("- SPMO excluded (pre-registered): no vol index, options history too short.")
    add("")
    add("## Benchmarks (B&H total return, HK 30% dividend withholding netted)")
    add("")
    add(f"**Sanity anchor** — SPY B&H TR (HK net) 1996-01→{sdf.index[-1].date()}: "
        f"CAGR **{anchor['CAGR'] * 100:.2f}%**, Sharpe {anchor['Sharpe']:.2f}, "
        f"MaxDD {anchor['MaxDD'] * 100:.1f}%  (pre-registered acceptance band 9–11%).")
    add("")
    for under, d in data.items():
        add(f"### {under} calendar")
        add("")
        add("| Window | SPY net-TR CAGR | Sharpe | MaxDD | "
            f"{under} net-TR CAGR | Sharpe | MaxDD |")
        add("|---|---|---|---|---|---|---|")
        for wname, lo, hi in d["wslices"]:
            bs = bench_metrics(d["bench_spy"], lo, hi)
            bo = bench_metrics(d["bench_own"], lo, hi)
            add(f"| {wname} | {_p(bs['CAGR'], 2)} | {bs['Sharpe']:.2f} | {_p(bs['MaxDD'])} "
                f"| {_p(bo['CAGR'], 2)} | {bo['Sharpe']:.2f} | {_p(bo['MaxDD'])} |")
        add("")

    def main_table(under, frame):
        d = data[under]
        wname = d["wslices"][0][0]
        add(f"### {under} x {d['vol']} — {frame} frame, FULL window ({wname[5:]}), "
            "base setting (IV m=0.85, cost 0.5%/side, cash=^IRX)")
        add("")
        add("| Δ | Gate | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | EffLev | "
            "Theta %/yr | Rolls | Expo | CostDrag pp/yr |")
        add("|---|---|---|---|---|---|---|---|---|---|---|")
        for delta in DELTAS:
            for g in GATES:
                m = R[under]["base"][frame][(delta, g)][wname]
                add(f"| {delta:.2f} | {g} | {_p(m['CAGR'])}{_ruin(m)} | "
                    f"{m['Sharpe']:.2f} | {_p(m['MaxDD'])} | {_a(m)} | "
                    f"{m['EffLev']:.2f}x | {m['Theta'] * 100:+.1f}% | {m['Rolls']} | "
                    f"{m['Expo'] * 100:.0f}% | {m['CostDrag']:+.1f} |")
        add("")

    add("## Results — PORTFOLIO frame (main; premium budget 10% NAV, rest cash @ ^IRX)")
    add("")
    for under in ("SPY", "QQQ"):
        main_table(under, "PORTFOLIO")
    add("## Results — SLEEVE frame (100% compounding; leverage mirror, NOT the sizing "
        "recommendation)")
    add("")
    for under in ("SPY", "QQQ"):
        main_table(under, "SLEEVE")

    add("## Two-halves + sub-windows (PORTFOLIO frame, base setting)")
    add("")
    for under in ("SPY", "QQQ"):
        d = data[under]
        wnames = [w[0] for w in d["wslices"]]
        add(f"### {under} — α vs SPY net-TR (t) per window")
        add("")
        add("| Δ | Gate | " + " | ".join(f"{w} CAGR | α(t)" for w in wnames[1:]) + " |")
        add("|---|---|" + "---|" * (2 * len(wnames[1:])))
        for delta in DELTAS:
            for g in GATES:
                cells = R[under]["base"]["PORTFOLIO"][(delta, g)]
                row = [f"{delta:.2f}", g]
                for w in wnames[1:]:
                    m = cells[w]
                    row += [_p(m["CAGR"]), _a(m)]
                add("| " + " | ".join(row) + " |")
        add("")

    add("### SLEEVE two-halves (CAGR per window; ruin cells flagged)")
    add("")
    for under in ("SPY", "QQQ"):
        d = data[under]
        wnames = [w[0] for w in d["wslices"]]
        add(f"**{under}**")
        add("")
        add("| Δ | Gate | " + " | ".join(wnames[1:]) + " | FULL MaxDD |")
        add("|---|---|" + "---|" * (len(wnames[1:]) + 1))
        for delta in DELTAS:
            for g in GATES:
                cells = R[under]["base"]["SLEEVE"][(delta, g)]
                row = [f"{delta:.2f}", g]
                for w in wnames[1:]:
                    m = cells[w]
                    row.append(f"{_p(m['CAGR'])}{_ruin(m)}")
                row.append(_p(cells[wnames[0]]["MaxDD"]))
                add("| " + " | ".join(row) + " |")
        add("")

    add("## Sensitivity (PORTFOLIO frame, FULL window) — α vs SPY net-TR (t)")
    add("")
    for under in ("SPY", "QQQ"):
        d = data[under]
        wname = d["wslices"][0][0]
        add(f"### {under}")
        add("")
        add("| Δ | Gate | base (m0.85, 0.5%, IRX) | IV m=1.00 | IV m=1.15 | "
            "cost 1.0%/side | cash 0% |")
        add("|---|---|---|---|---|---|---|")
        for delta in DELTAS:
            for g in GATES:
                row = [f"{delta:.2f}", g]
                for sname, *_ in SETTINGS:
                    m = R[under][sname]["PORTFOLIO"][(delta, g)][wname]
                    row.append(_a(m))
                add("| " + " | ".join(row) + " |")
        add("")
    add("SLEEVE-frame sensitivity (same settings) is summarized in Conclusions; "
        "full numbers reproducible by re-running the script.")
    add("")

    add("## QQQ appendix — vs QQQ B&H net-TR (tool mirror), PORTFOLIO frame, base")
    add("")
    d = data["QQQ"]
    wnames = [w[0] for w in d["wslices"]]
    add("| Δ | Gate | FULL CAGR | FULL α_QQQ(t) | " +
        " | ".join(f"{w} α_QQQ(t)" for w in wnames[1:]) + " |")
    add("|---|---|---|---|" + "---|" * len(wnames[1:]))
    for delta in DELTAS:
        for g in GATES:
            cells = R["QQQ"]["base"]["PORTFOLIO"][(delta, g)]
            row = [f"{delta:.2f}", g, _p(cells[wnames[0]]["CAGR"]),
                   _a(cells[wnames[0]], own=True)]
            for w in wnames[1:]:
                row.append(_a(cells[w], own=True))
            add("| " + " | ".join(row) + " |")
    add("")

    add("## Ranking stability (PORTFOLIO, top-3 cells by α vs SPY net-TR)")
    add("")
    for under in ("SPY", "QQQ"):
        d = data[under]
        wnames = [w[0] for w in d["wslices"]]
        add(f"**{under}**")
        add("")
        for sname, *_ in SETTINGS:
            wlist = wnames if sname == "base" else wnames[:1]
            for w in wlist:
                ranked = sorted(
                    ((k, R[under][sname]["PORTFOLIO"][k][w]) for k in
                     R[under][sname]["PORTFOLIO"]),
                    key=lambda kv: -(kv[1]["Alpha"] if np.isfinite(kv[1]["Alpha"])
                                     else -9e9))
                top = ", ".join(f"{k[0]:.2f}Δ {k[1]} ({_a(m)})"
                                for k, m in ranked[:3])
                add(f"- [{sname}][{w}]: {top}")
        add("")

    add("## Cross-foot verification")
    add("")
    add(f"- {ASSERT_COUNT['runs']} accounting runs, {ASSERT_COUNT['n']:,} bar-level "
        "assertions, ALL passed:")
    add("  NAV = cash + option market value (identity); cash >= 0; NAV > 0;")
    add("  NAV_t = NAV_(t-1) + cash interest + option P&L - costs (roll-day value")
    add("  conservation, rel. tol 1e-7). Any violation raises and aborts the run.")
    add("")
    add("## Conclusions")
    add("")
    add("(TO FILL — hand-written after number review)")
    add("")
    add("## Caveats")
    add("")
    add("(TO FILL)")
    add("")
    add("## Implication")
    add("")
    add("(TO FILL)")
    add("")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS}  ({time.time() - t0:.0f}s total, "
          f"{ASSERT_COUNT['n']:,} asserts / {ASSERT_COUNT['runs']} runs)", flush=True)


if __name__ == "__main__":
    main()
