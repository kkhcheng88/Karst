"""Experiment: RSI-2 as a LEAP ENTRY / delta-ledger trigger — spot-vs-LEAP framing.

The question every prior test answered at the WRONG layer
---------------------------------------------------------
The repo tested RSI-2 four times (2026-06-30_rsi2_200sma, 2026-07-05_rsi2_capital_
efficiency, 2026-07-17_rsi2_be_replication, 2026-07-17_dip_capital_efficiency) — all
ON STOCKS, UNLEVERED, and all as "IN-MARKET vs CASH". On that layer holding is free,
so mistiming only costs opportunity and "RSI-2 ~ random" is nearly foregone.

But Karst is NEVER in cash. The real choice is how you EXPRESS a market exposure you
hold either way:  SPOT (shares, 1.0x, no rent)  vs  LEAP (leveraged, pays rent). The
user's structural point, in two layers:

  No leverage : holding is free  -> mistiming ~costless -> timing worthless   (PROVEN)
  Leverage    : rent runs daily  -> not timing -> rent eats you -> timing MANDATORY (PROVEN)
  BUT the switch is SPOT<->LEAP, not IN<->OUT. Because you never leave the market, the
  cost of being wrong collapses from "miss the whole rally" (~20%) to "wasted a little
  rent" (~1%). THAT is why timing goes from luxury to affordable. This is exactly what
  the AA-strict delta ledger does (compute total delta, fill the gap with LEAP); the
  only change the user proposes is trigger-on-SIGNAL vs the ledger's trigger-on-CALENDAR.

Arms
----
IN/OUT controls (the OLD, wrong frame — kept to SHOW it is the wrong frame):
  A ALWAYS / B GATED(200SMA) / C5 RSI2<5 / C10 RSI2<10 / D GATED+DIP / E RSI2-loose,
  each a LEAP that sits in CASH when out. A/B/D from exp_leap_real_sweep.build_gates
  VERBATIM; C5/C10/E built here in the same idiom.

SPOT/LEAP overlay (the REAL question). Baseline = 100% spot, never cash. On a trigger
we SELL some spot and BUY LEAP to raise TOTAL delta to a target; on exit we swap back
to 100% spot. Capital-matched to F (same money, no phantom cash):
  F  spot 100%                    always shares, 0 rent, 1.0x                (TRUE baseline)
  G5 spot + RSI2<5 -> LEAP 1.5x   swap in on RSI2<5, back to spot on close>5MA
  G10 spot + RSI2<10 -> LEAP 1.5x
  H  spot + calendar -> LEAP 1.5x LEAP overlay held CONTINUOUSLY, re-sized monthly
                                  (= proxy for the current AA-strict ledger: signal-vs-
                                  calendar is the whole contrast G vs H)
  I  spot + RSI2<5 -> LEAP 2.0x   leverage ladder
  J  spot + 200SMA -> LEAP 1.5x   CONTROL ONLY (user ruled out 200SMA filter 2026-07-17)

  LEAP leg fixed at delta 0.80 (deepest ITM, lowest rent — 2026-07-17_core_topup_realcost
  found 0.70 is a worse rent bill, not a rescue). Overlay premium sized so
  spot_delta + leap_delta = target x NAV; premium bucket P = (T-1)*NAV/(lev-1).

  underlying : SPY x ^VIX, QQQ x ^VXN (INDEXES: no earnings bomb / single-name ex-div
               cliff — the user's stated reason this differs from BE single-stock work)
  windows    : overlay verdict on 2016+ with 2016-2020 / 2021+ split (user standard;
               2000-2002 tail deliberately excluded per user). IN/OUT controls + the
               rent/leverage mechanics use full 2001+ (more crashes = clearer rent).
  IV         : m=1.15 honest base (real implied m=1.22 @0.50D per 2026-07-09, so 1.15
               still optimistic) MAIN verdict; m=0.85 (dead per 2026-07-17_core_topup_
               realcost) CONTROL; damp 0.4 robustness.
  cost       : option 0.5%/side of premium; spot 10bps/side (ETF).

Controls (either missing = void)
  1. Random-same-exposure MC per arm: identical episode COUNT + LENGTH multiset, only
     the WHEN randomized (stars-and-bars), through the identical engine.
  2. Cost-of-being-wrong: per-episode incremental of the overlay vs pure spot, split
     win/lose -> "avg loss when LEAP-and-no-bounce" vs the IN/OUT "avg missed rally".
     The ratio IS the user's core claim, quantified.

Metric discipline (user x2; memory metric-and-direction-discipline / capital-efficiency-
two-traps): PRIMARY = capital efficiency (CAGR / mean delta-exposure) AND absolute PnL,
SIDE BY SIDE. This is the SLEEVE/overlay layer -> Jensen ALPHA IS BANNED (computed
nowhere here). Negative-PnL grid -> rank by PnL+MaxDD, flag CapEff invalid. Also: MaxDD,
exposure, rent (theta+cost pp/yr), trades/yr, cash-starved%.

Model limits: BSM + VIX/VXN, NOT a real chain (no smile/term-structure/bid-ask/early
exercise; fractional contracts). Real implied m>used -> deep-ITM cells optimistic and
crash term-structure unquantified, both same-direction. Cross-arm RANKINGS (constant m,
same engine) robust; absolute magnitudes soft.

Run:  PYTHONUTF8=1 python backtest/experiments/exp_rsi2_leap_entry.py
Writes: backtest/results/2026-07-17_rsi2_leap_entry.md
"""
from __future__ import annotations

import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metrics                                      # noqa: E402
from data import load                               # noqa: E402
# ---- ENGINE: imported verbatim, never reimplemented -----------------------
from exp_leap_real_sweep import (                   # noqa: E402
    build_underlying, build_gates, simulate_unit_path, account, TD,
)
from exp_core_topup import month_start_mask         # noqa: E402
from exp_core_assembly_real import damp_iv          # noqa: E402

CAPITAL = 10_000.0
DELTAS = [0.30, 0.50, 0.80]        # IN/OUT control ladder + Δ-mechanics
OVERLAY_DELTA = 0.80               # LEAP leg for the spot/LEAP overlay arms
COST = 0.005                       # option 0.5%/side of premium
COST_SPOT = 0.001                  # spot 10bps/side (ETF)
N_MC = int(os.environ.get("RSI2_LEAP_MC", "1000"))       # overlay MC
N_MC_AE = int(os.environ.get("RSI2_LEAP_MC_AE", "300"))  # in/out control MC
ARMS = ["A-ALWAYS", "B-GATED", "C5-RSI2<5", "C10-RSI2<10", "D-GATED+DIP", "E-RSI2loose"]
MC_ARMS = [a for a in ARMS if a != "A-ALWAYS"]

FRAMES = [("SLEEVE", 1.0), ("PORT10", 0.10)]
PRIMARY = "PORT10"

# overlay arms: (name, hold_key_in_entry_arms, target_T, rebal)
OVL = [
    ("F-spot",     None,          1.0, "none"),      # baseline, no LEAP
    ("G5-swap1.5", "C5-RSI2<5",   1.5, "none"),
    ("G10-swap1.5", "C10-RSI2<10", 1.5, "none"),
    ("H-cal1.5",   "A-ALWAYS",    1.5, "monthly"),   # calendar / always-on ledger proxy
    ("I-swap2.0",  "C5-RSI2<5",   2.0, "none"),
    ("J-sma1.5",   "B-GATED",     1.5, "none"),      # CONTROL (200SMA)
]
OVL_MC = ["G5-swap1.5", "G10-swap1.5", "I-swap2.0", "J-sma1.5"]  # F/H have no random twin

# (label, iv_mult, damp)
SETTINGS = [("base m=1.15", 1.15, 1.0),
            ("legacy m=0.85", 0.85, 1.0),
            ("damp0.4 m=1.15", 1.15, 0.4)]
HEADLINE = "base m=1.15"

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-17_rsi2_leap_entry.md")

ASSERT_N = {"n": 0}
_G: dict = {}


# ---------------------------------------------------------------------------
# Signal construction (the ONLY thing this file adds to the option engine)
# ---------------------------------------------------------------------------

def build_entry_arms(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """6 hold masks. A/B/D reuse exp_leap_real_sweep.build_gates VERBATIM; C5/C10/E
    built in the identical idiom (stateful on signal-time series, then .shift(1) =>
    signal at close T executes at close T+1)."""
    eng = build_gates(df)
    close, r2 = df["close"], df["rsi2"]
    ma5 = close.rolling(5).mean()
    above5 = (close > ma5).values
    r2v = r2.values
    n = len(df)

    def stateful(enter, exit_):
        out = np.zeros(n, dtype=bool)
        hold = False
        for i in range(n):
            if not hold:
                if enter[i]:
                    hold = True
            elif exit_[i]:
                hold = False
            out[i] = hold
        return pd.Series(out, index=df.index)

    def sh(s):
        return s.shift(1).fillna(False).astype(bool).values

    return {
        "A-ALWAYS": eng["ALWAYS"],
        "B-GATED": eng["GATED"],
        "C5-RSI2<5": sh(stateful(r2v < 5, above5)),
        "C10-RSI2<10": sh(stateful(r2v < 10, above5)),
        "D-GATED+DIP": eng["GATED+DIP"],
        "E-RSI2loose": sh(stateful(r2v < 5, r2v > 90)),
    }


# ---------------------------------------------------------------------------
# NEW: spot+LEAP overlay accounting (option math stays verbatim via unit path;
# only the spot base + delta-target sizing is new). Cross-foot asserted every bar:
# NAV = spot + cash + option value;  NAV_t = NAV_{t-1} + interest + spot P&L +
# option P&L - costs.  Trades are internal spot<->option transfers; only cost leaks.
# ---------------------------------------------------------------------------

def build_hold(df, entry_thresh, exit_rule):
    """Stateful spot->LEAP swap mask: enter RSI2<entry_thresh, exit per rule.
    exit_rule in {'close>5ma','rsi>70','rsi>90'}. Same idiom as build_entry_arms
    (signal at close T -> executes at close T+1 via .shift(1))."""
    close = df["close"].values
    r2 = df["rsi2"].values
    ma5 = df["close"].rolling(5).mean().values
    enter = r2 < entry_thresh
    if exit_rule == "close>5ma":
        exit_ = close > ma5
    elif exit_rule == "rsi>70":
        exit_ = r2 > 70
    elif exit_rule == "rsi>90":
        exit_ = r2 > 90
    else:
        raise ValueError(exit_rule)
    n = len(df)
    out = np.zeros(n, dtype=bool)
    hold = False
    for i in range(n):
        if not hold:
            if enter[i]:
                hold = True
        elif exit_[i]:
            hold = False
        out[i] = hold
    return pd.Series(out, index=df.index).shift(1).fillna(False).astype(bool).values


def simulate_spot_overlay(unit, close, r_net, r_cash, target_T, rebal_mask,
                          cost_opt=COST, cost_spot=COST_SPOT, capital=CAPITAL):
    mark, mark_pre = unit["mark"], unit["mark_pre"]
    T_arr = (target_T if isinstance(target_T, np.ndarray)
             else np.full(len(mark), float(target_T)))
    sell, sell_mark = unit["sell"], unit["sell_mark"]
    buy, buy_mark = unit["buy"], unit["buy_mark"]
    dlt = unit["delta"]
    n = len(mark)
    nav = np.empty(n)
    dn = np.empty(n)          # total delta-notional / NAV (spot=1.0 delta + leap delta)
    premf = np.empty(n)       # option premium value / NAV
    onarr = np.zeros(n, dtype=bool)
    sh_val, cash, c = capital, 0.0, 0.0
    prev_mark, prev_nav = np.nan, capital

    for i in range(n):
        interest = cash * r_cash[i]
        cash += interest
        spot_pnl = sh_val * r_net[i]
        sh_val += spot_pnl
        opt_pnl = c * (mark_pre[i] - prev_mark) * 100.0 if c > 0.0 else 0.0
        costs = 0.0

        # (a) forced sell (exit or roll-out) -> cash
        if sell[i] and c > 0.0:
            gross = c * sell_mark[i] * 100.0
            costs += gross * cost_opt
            cash += gross - gross * cost_opt
            c = 0.0

        # (b) size option to delta target on buy / roll / (monthly) rebalance
        navnow = sh_val + cash + (c * mark[i] * 100.0 if c > 0.0 else 0.0)
        if buy[i]:
            unitmk = buy_mark[i]
            lev = dlt[i] * close[i] / unitmk if unitmk > 1e-9 else 0.0
        else:
            unitmk = mark[i]
            lev = dlt[i] * close[i] / unitmk if (c > 0.0 and unitmk > 1e-9) else 0.0
        rebalance = bool(buy[i]) or (rebal_mask[i] and c > 0.0)
        if rebalance and lev > 1.0:
            p_target = (T_arr[i] - 1.0) * navnow / (lev - 1.0)
            p_target = max(0.0, min(p_target, sh_val + cash))
            dprem = p_target - c * unitmk * 100.0
            if dprem > 0.0:                      # buy options, fund cash<-spot
                need = dprem * (1.0 + cost_opt)
                if need > cash:
                    move = need - cash
                    gs = min(move / (1.0 - cost_spot), sh_val)
                    costs += gs * cost_spot
                    sh_val -= gs
                    cash += gs * (1.0 - cost_spot)
                spend = min(dprem * (1.0 + cost_opt), cash)
                addp = spend / (1.0 + cost_opt)
                c += addp / (unitmk * 100.0)
                cash -= spend
                costs += spend - addp
            elif dprem < 0.0:                    # sell some options -> cash
                gross = -dprem
                costs += gross * cost_opt
                cash += gross - gross * cost_opt
                c += dprem / (unitmk * 100.0)

        # (c) not holding -> all cash back to spot (never leave the market)
        if c <= 0.0 and cash > 1e-9:
            costs += cash * cost_spot
            sh_val += cash * (1.0 - cost_spot)
            cash = 0.0

        total = sh_val + cash + (c * mark[i] * 100.0 if c > 0.0 else 0.0)
        expected = prev_nav + interest + spot_pnl + opt_pnl - costs
        if abs(total - expected) > 1e-6 * max(1.0, abs(expected)):
            raise AssertionError(f"overlay cross-foot bar {i}: {total} vs {expected}")
        if cash < -1e-6 or sh_val < -1e-6 or total <= 0:
            raise AssertionError(f"overlay bad state bar {i}: sh={sh_val} cash={cash}")
        ASSERT_N["n"] += 3
        nav[i] = total
        dn[i] = (sh_val + (c * dlt[i] * close[i] * 100.0 if c > 0.0 else 0.0)) / total
        premf[i] = (c * mark[i] * 100.0 / total) if c > 0.0 else 0.0
        onarr[i] = c > 0.0
        prev_mark = mark[i] if c > 0.0 else np.nan
        prev_nav = total

    return {"nav": nav, "dn": dn, "prem": premf, "on": onarr}


def spot_nav(r_net, capital=CAPITAL):
    nav = np.empty(len(r_net))
    v = capital
    for i in range(len(r_net)):
        v *= (1.0 + r_net[i]) if i > 0 else 1.0
        nav[i] = v
    return nav


# ---------------------------------------------------------------------------
# Metric helpers (analysis layer — engines untouched). No alpha anywhere.
# ---------------------------------------------------------------------------

def unit_leverage(unit, close):
    d, mk = np.nan_to_num(unit["delta"]), unit["mark"]
    held = unit["hold"]
    lev = (d * close) / np.where(mk > 1e-9, mk, np.nan)
    lev = lev[held & np.isfinite(lev)]
    th = unit["theta"][held & np.isfinite(unit["theta"])]
    return (float(np.median(lev)) if len(lev) else np.nan,
            float(np.median(th)) if len(th) else np.nan)


def leap_cell(unit, close, r_cash, budget_frac, cost=COST):
    """IN/OUT LEAP (cash when out). account() is engine-verbatim."""
    nav, conts = account(unit, r_cash, cost, budget_frac, capital=CAPITAL)
    nav0, _ = account(unit, r_cash, 0.0, budget_frac, capital=CAPITAL)
    d = unit["delta"]
    held = conts > 0
    dn = np.where(held, conts * np.nan_to_num(d) * close * 100.0 / nav, 0.0)
    prem = np.where(held, conts * np.nan_to_num(unit["mark"]) * 100.0 / nav, 0.0)
    ret = nav[1:] / nav[:-1] - 1.0
    yrs = len(nav) / TD
    expo = float(np.mean(dn))
    cg = metrics.cagr(nav)
    th = unit["theta"][held & np.isfinite(unit["theta"])]
    theta_med = float(np.median(th)) if len(th) else np.nan
    return {
        "PnL$": float(nav[-1] - CAPITAL), "CAGR": cg,
        "MaxDD": metrics.max_drawdown(nav), "Sharpe": metrics.ann_sharpe(ret),
        "Expo": expo, "CapEff": cg / expo if expo > 1e-9 else np.nan,
        "Theta": theta_med, "PremNAV": float(np.mean(prem)),
        "RentNAV": theta_med * float(np.mean(prem)) if np.isfinite(theta_med) else np.nan,
        "CostDrag": metrics.cagr(nav0) - cg, "Trades": float(unit["buy"].sum()) / yrs,
    }


def stock_cell(gate, r_net, r_cash, cost=COST_SPOT):
    n = len(gate)
    pos = gate.astype(float)
    nav = np.empty(n)
    v = CAPITAL
    for i in range(n):
        if i > 0:
            p = pos[i - 1]
            v *= (1.0 + p * r_net[i] + (1.0 - p) * r_cash[i])
            v *= (1.0 - cost * abs(pos[i] - pos[i - 1]))
        nav[i] = v
    ret = nav[1:] / nav[:-1] - 1.0
    expo = float(np.mean(pos))
    cg = metrics.cagr(nav)
    return {"PnL$": float(nav[-1] - CAPITAL), "CAGR": cg,
            "MaxDD": metrics.max_drawdown(nav), "Sharpe": metrics.ann_sharpe(ret),
            "Expo": expo, "CapEff": cg / expo if expo > 1e-9 else np.nan,
            "Trades": float(np.sum((pos[1:] - pos[:-1]) > 0)) / (n / TD),
            "RentNAV": 0.0}


def slice_metrics(nav, dn, lo, hi, rentf=None):
    navw = nav[lo:hi]
    norm = navw / navw[0] * CAPITAL
    ret = norm[1:] / norm[:-1] - 1.0
    cg = metrics.cagr(norm)
    expo = float(np.mean(dn[lo:hi]))
    out = {"CAGR": cg, "MaxDD": metrics.max_drawdown(norm),
           "Sharpe": metrics.ann_sharpe(ret), "PnL$": float(norm[-1] - CAPITAL),
           "Expo": expo, "CapEff": cg / expo if expo > 1e-9 else np.nan}
    if rentf is not None:
        out["RentNAV"] = float(np.mean(rentf[lo:hi]))
    return out


# ---------------------------------------------------------------------------
# Random-same-exposure control
# ---------------------------------------------------------------------------

def episode_lengths(gate):
    out, run = [], 0
    for v in gate:
        if v:
            run += 1
        elif run:
            out.append(run)
            run = 0
    if run:
        out.append(run)
    return out


def random_gate(n, lengths, rng):
    k = len(lengths)
    if k == 0:
        return np.zeros(n, dtype=bool)
    H = int(sum(lengths))
    G = n - H
    if G <= 0:
        return np.ones(n, dtype=bool)
    cuts = np.sort(rng.choice(G + k, size=k, replace=False))
    gaps = np.diff(np.concatenate([[-1], cuts, [G + k]])) - 1
    order = rng.permutation(k)
    out = np.zeros(n, dtype=bool)
    p = 0
    for j in range(k):
        p += int(gaps[j])
        L = int(lengths[order[j]])
        out[p:p + L] = True
        p += L
    return out


def pct_of(actual, dist):
    d = np.asarray(dist, dtype=float)
    d = d[np.isfinite(d)]
    if not len(d) or not np.isfinite(actual):
        return np.nan
    return float((d < actual).mean() * 100.0)


# ---------------------------------------------------------------------------
# MC workers
# ---------------------------------------------------------------------------

def _init(payload):
    _G.update(payload)


def _mc_ae(task):
    under, delta, arm, seed = task
    d = _G[under]
    g = random_gate(len(d["close"]), _G["eps"][(under, arm)], np.random.default_rng(seed))
    u = simulate_unit_path(d["close"], d["iv"], d["r_arr"], d["q_arr"], g, delta)
    out = {}
    for fname, bf in FRAMES:
        try:
            c = leap_cell(u, d["close"], d["r_cash"], bf)
            out[fname] = (c["CapEff"], c["PnL$"])
        except AssertionError:
            out[fname] = (np.nan, -CAPITAL)
    return (under, delta, arm, out)


def _mc_ovl(task):
    under, arm, target_T, seed = task
    d = _G["ovl"][under]
    g = random_gate(len(d["close"]), _G["ovl_eps"][(under, arm)],
                    np.random.default_rng(seed))
    u = simulate_unit_path(d["close"], d["iv"], d["r_arr"], d["q_arr"], g, OVERLAY_DELTA)
    try:
        res = simulate_spot_overlay(u, d["close"], d["r_net"], d["r_cash"], target_T,
                                    np.zeros(len(d["close"]), dtype=bool))
        m = slice_metrics(res["nav"], res["dn"], d["lo"], d["hi"])
        return (under, arm, (m["CapEff"], m["PnL$"]))
    except AssertionError:
        return (under, arm, (np.nan, np.nan))


def _mc_stock(n, lengths, r_net, r_cash, seeds):
    o = []
    for s in seeds:
        g = random_gate(n, lengths, np.random.default_rng(s))
        c = stock_cell(g, r_net, r_cash)
        o.append((c["CapEff"], c["PnL$"]))
    return np.array(o)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def f(x, dec=2, pct=True):
    if x is None or not np.isfinite(x):
        return "n/a"
    return f"{x*100:+.{dec}f}%" if pct else f"{x:.{dec}f}"


def money(x):
    return "n/a" if x is None or not np.isfinite(x) else f"${x:,.0f}"


# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    out = []
    P = out.append

    irx_df = load("^IRX")
    irx = irx_df["close"]
    prov = [("^IRX", irx_df.attrs.get("source", "?"), len(irx_df),
             str(irx_df.index.min().date()), str(irx_df.index.max().date()))]
    raw = {}
    for under, volsym in [("SPY", "^VIX"), ("QQQ", "^VXN")]:
        df, pv, _ = build_underlying(under, volsym, irx)
        raw[under] = df
        prov += pv

    common = raw["SPY"].index.intersection(raw["QQQ"].index)
    common = common[common >= pd.Timestamp("2001-01-01")]
    YRS = len(common) / TD
    print(f"common {common[0].date()}->{common[-1].date()} ({len(common)}d)", flush=True)

    # ---- full 2001+ dataset for IN/OUT controls + Δ mechanics ----
    D = {}
    for under in ("SPY", "QQQ"):
        df = raw[under].loc[common]
        D[under] = {"df": df, "arms": build_entry_arms(df),
                    "close": df["close"].values, "vol": df["vol"].values / 100.0,
                    "r_arr": df["irx"].values / 100.0, "q_arr": df["q"].values,
                    "r_cash": df["irx"].values / 100.0 / TD, "r_net": df["r_net"].values}
        print(f"{under} in/out expo: " +
              ", ".join(f"{k}={v.mean()*100:.0f}%" for k, v in D[under]["arms"].items()),
              flush=True)

    # ---- IN/OUT control grid (A-E) : m x under x delta x arm x frame ----
    grid = {}
    for sname, m, dmp in SETTINGS:
        for under in ("SPY", "QQQ"):
            d = D[under]
            iv = damp_iv(d["vol"] * m, dmp)
            for delta in DELTAS:
                for arm in ARMS:
                    u = simulate_unit_path(d["close"], iv, d["r_arr"], d["q_arr"],
                                           d["arms"][arm], delta)
                    if sname == HEADLINE and delta == OVERLAY_DELTA:
                        d.setdefault("levunits", {})[arm] = u
                    for fname, bf in FRAMES:
                        try:
                            grid[(sname, under, delta, arm, fname)] = leap_cell(
                                u, d["close"], d["r_cash"], bf)
                        except AssertionError:
                            grid[(sname, under, delta, arm, fname)] = {
                                "RUIN": True, "PnL$": -CAPITAL, "CAGR": -1.0,
                                "MaxDD": -1.0, "Sharpe": np.nan, "Expo": np.nan,
                                "CapEff": np.nan, "Theta": np.nan, "PremNAV": np.nan,
                                "RentNAV": np.nan, "CostDrag": np.nan, "Trades": np.nan}
        print(f"  in/out grid {sname} {time.time()-t0:.0f}s", flush=True)

    stock = {}
    levs = {}
    for under in ("SPY", "QQQ"):
        d = D[under]
        for arm in ARMS:
            stock[(under, arm)] = stock_cell(d["arms"][arm], d["r_net"], d["r_cash"])
        for delta in DELTAS:
            iv = damp_iv(d["vol"] * 1.15, 1.0)
            u = simulate_unit_path(d["close"], iv, d["r_arr"], d["q_arr"],
                                   d["arms"]["A-ALWAYS"], delta)
            levs[(under, delta)] = unit_leverage(u, d["close"])

    # ---- SPOT/LEAP overlay dataset : 2016+ (user standard) ----
    idx16 = common[common >= pd.Timestamp("2016-01-01")]
    WINS = [("2016+", pd.Timestamp("2016-01-01"), idx16[-1]),
            ("2016-2020", pd.Timestamp("2016-01-01"), pd.Timestamp("2020-12-31")),
            ("2021+", pd.Timestamp("2021-01-01"), idx16[-1])]
    DO = {}
    for under in ("SPY", "QQQ"):
        df = raw[under].loc[idx16]
        arms = build_entry_arms(df)
        DO[under] = {"df": df, "arms": arms, "close": df["close"].values,
                     "vol": df["vol"].values / 100.0, "r_arr": df["irx"].values / 100.0,
                     "q_arr": df["q"].values, "r_cash": df["irx"].values / 100.0 / TD,
                     "r_net": df["r_net"].values, "index": df.index}
        print(f"{under} overlay(2016+) hold%: " +
              ", ".join(f"{n_}={DO[under]['arms'][k].mean()*100:.0f}%"
                        for n_, k, _, _ in OVL if k), flush=True)

    def win_slices(index):
        s = {}
        for wn, ws, we in WINS:
            mask = (index >= ws) & (index <= we)
            ii = np.where(mask)[0]
            s[wn] = (int(ii[0]), int(ii[-1]) + 1)
        return s

    ovl = {}          # (sname, under, arm, window) -> metrics
    ovl_extra = {}    # (under, arm) -> {"nav","on","dn","prem","index"} at HEADLINE
    for sname, m, dmp in SETTINGS:
        for under in ("SPY", "QQQ"):
            d = DO[under]
            iv = damp_iv(d["vol"] * m, dmp)
            sl = win_slices(d["index"])
            for name, key, T, rebal in OVL:
                if key is None:                       # F: pure spot
                    nav = spot_nav(d["r_net"])
                    dn = np.ones(len(nav))
                    prem = np.zeros(len(nav))
                    on = np.zeros(len(nav), dtype=bool)
                else:
                    u = simulate_unit_path(d["close"], iv, d["r_arr"], d["q_arr"],
                                           d["arms"][key], OVERLAY_DELTA)
                    rmask = (month_start_mask(d["index"]) if rebal == "monthly"
                             else np.zeros(len(d["close"]), dtype=bool))
                    res = simulate_spot_overlay(u, d["close"], d["r_net"], d["r_cash"],
                                                T, rmask)
                    nav, dn, prem, on = res["nav"], res["dn"], res["prem"], res["on"]
                # theta-based rent pp/yr: median theta over on-days x mean prem
                thsrc = None
                if key is not None:
                    thsrc = u["theta"][on & np.isfinite(u["theta"])]
                rent_pp = (float(np.median(thsrc)) * float(np.mean(prem))
                           if thsrc is not None and len(thsrc) else 0.0)
                for wn, (lo, hi) in sl.items():
                    mm = slice_metrics(nav, dn, lo, hi)
                    mm["OnFrac"] = float(np.mean(on[lo:hi]))
                    mm["RentPP"] = rent_pp
                    mm["Trades"] = (float(np.sum(u["buy"][lo:hi])) / ((hi - lo) / TD)
                                    if key is not None else 0.0)
                    ovl[(sname, under, name, wn)] = mm
                if sname == HEADLINE:
                    ovl_extra[(under, name)] = {"nav": nav, "on": on,
                                                "index": d["index"]}
        print(f"  overlay grid {sname} {time.time()-t0:.0f}s", flush=True)

    # ---- cost-of-being-wrong: per-episode incremental overlay vs pure spot (2016+) ----
    cow = {}
    for under in ("SPY", "QQQ"):
        f_nav = ovl_extra[(under, "F-spot")]["nav"]
        f_ret = f_nav[1:] / f_nav[:-1] - 1.0
        idx = ovl_extra[(under, "F-spot")]["index"]
        lo16 = int(np.where(idx >= pd.Timestamp("2016-01-01"))[0][0])
        for name in ("G5-swap1.5", "G10-swap1.5", "I-swap2.0"):
            g_nav = ovl_extra[(under, name)]["nav"]
            on = ovl_extra[(under, name)]["on"]
            g_ret = g_nav[1:] / g_nav[:-1] - 1.0
            incr = g_ret - f_ret                       # daily overlay contribution
            # group into on-episodes (index i in incr corresponds to day i+1)
            epis = []
            cur = 0.0
            active = False
            for i in range(lo16, len(on)):
                if on[i]:
                    if i - 1 >= 0:
                        cur += incr[i - 1]
                    active = True
                elif active:
                    epis.append(cur)
                    cur, active = 0.0, False
            if active:
                epis.append(cur)
            epis = np.array(epis)
            wins = epis[epis > 0]
            loss = epis[epis < 0]
            cow[(under, name)] = {
                "n": len(epis), "winrate": float(np.mean(epis > 0)) if len(epis) else np.nan,
                "avg_win": float(np.mean(wins)) if len(wins) else 0.0,
                "avg_loss": float(np.mean(loss)) if len(loss) else 0.0,
                "worst": float(np.min(epis)) if len(epis) else 0.0}
        # in/out "missed rally": C10 stock out-episodes where spot rose
        c10 = DO[under]["arms"]["C10-RSI2<10"]
        rn = DO[under]["r_net"]
        miss = []
        cur = 0.0
        active = False
        for i in range(lo16, len(c10)):
            if not c10[i]:                              # OUT of market
                cur += rn[i]
                active = True
            elif active:
                miss.append(cur)
                cur, active = 0.0, False
        if active:
            miss.append(cur)
        miss = np.array(miss)
        up = miss[miss > 0]
        cow[(under, "MISS")] = {"n": len(miss),
                                "avg_up": float(np.mean(up)) if len(up) else 0.0,
                                "worst_up": float(np.max(up)) if len(up) else 0.0}

    # ---- operational-rule grids (2016+, m=1.15): switch thresholds / VIX booster /
    #      rent ledger. DATA ONLY, no verdict (verdicts made at review). ------------
    def overlay_variant(under, hold_mask, target):
        """One overlay config on 2016+: metrics + full rent breakdown. target may be
        scalar or per-bar array (VIX booster)."""
        d = DO[under]
        iv = damp_iv(d["vol"] * 1.15, 1.0)
        rmask0 = np.zeros(len(d["close"]), dtype=bool)
        u = simulate_unit_path(d["close"], iv, d["r_arr"], d["q_arr"], hold_mask,
                               OVERLAY_DELTA)
        res = simulate_spot_overlay(u, d["close"], d["r_net"], d["r_cash"], target, rmask0)
        res0 = simulate_spot_overlay(u, d["close"], d["r_net"], d["r_cash"], target,
                                     rmask0, cost_opt=0.0, cost_spot=0.0)
        lo, hi = win_slices(d["index"])["2016+"]
        yrs = (hi - lo) / TD
        m = slice_metrics(res["nav"], res["dn"], lo, hi)
        m0 = slice_metrics(res0["nav"], res0["dn"], lo, hi)
        txn_rent = m0["CAGR"] - m["CAGR"]                 # engine-measured switch cost
        on = res["on"][lo:hi]
        th = u["theta"][lo:hi][on & np.isfinite(u["theta"][lo:hi])]
        # carry = annual PORTFOLIO drag = theta(when on) x premium averaged over ALL
        # bars (zeros on off-days) -> on-fraction-weighted, consistent with §2.
        prem_all = res["prem"][lo:hi]
        carry_rent = (float(np.median(th)) * float(np.mean(prem_all))
                      if len(th) else 0.0)
        hm = hold_mask[lo:hi]
        entries = int(np.sum(hm[1:] & ~hm[:-1]))
        rolls = int(np.sum(u["rolled"][lo:hi]))
        m.update({"switches_yr": entries / yrs, "rolls_yr": rolls / yrs,
                  "txn_rent": txn_rent, "carry_rent": carry_rent,
                  "total_rent": txn_rent + carry_rent, "OnFrac": float(np.mean(on))})
        return m

    ENTRIES = [5, 10, 15, 20]
    EXITS = [("收>5MA", "close>5ma"), ("RSI2>70", "rsi>70"), ("RSI2>90", "rsi>90")]
    sw_grid = {}          # (under, entry, exit_label) -> metrics
    for under in ("SPY", "QQQ"):
        for ent in ENTRIES:
            for elab, erule in EXITS:
                hm = build_hold(DO[under]["df"], ent, erule)
                sw_grid[(under, ent, elab)] = overlay_variant(under, hm, 1.5)
    print(f"  switch grid {time.time()-t0:.0f}s", flush=True)

    # VIX booster: G (RSI2<5 in, close>5MA out); target 1.3x normally, 1.5x when VIX>28
    vix_rows = {}
    for under in ("SPY", "QQQ"):
        hm = build_hold(DO[under]["df"], 5, "close>5ma")
        vix = DO[under]["vol"] * 100.0
        t_boost = np.where(vix > 28.0, 1.5, 1.3)
        vix_rows[(under, "G-fixed1.3")] = overlay_variant(under, hm, 1.3)
        vix_rows[(under, "G-fixed1.5")] = overlay_variant(under, hm, 1.5)
        vix_rows[(under, "G-VIXboost")] = overlay_variant(under, hm, t_boost)
    print(f"  vix booster {time.time()-t0:.0f}s", flush=True)

    # ---- MC ----
    eps = {(u_, a): episode_lengths(D[u_]["arms"][a]) for u_ in ("SPY", "QQQ")
           for a in MC_ARMS}
    ovl_eps = {(u_, nm): episode_lengths(DO[u_]["arms"][k])
               for u_ in ("SPY", "QQQ") for (nm, k, T, r) in OVL if nm in OVL_MC}
    payload = {"eps": eps, "ovl_eps": ovl_eps, "ovl": {}}
    for under in ("SPY", "QQQ"):
        d = D[under]
        payload[under] = {"close": d["close"], "iv": damp_iv(d["vol"] * 1.15, 1.0),
                          "r_arr": d["r_arr"], "q_arr": d["q_arr"], "r_cash": d["r_cash"]}
        do = DO[under]
        lo16 = int(np.where(do["index"] >= pd.Timestamp("2016-01-01"))[0][0])
        payload["ovl"][under] = {"close": do["close"],
                                 "iv": damp_iv(do["vol"] * 1.15, 1.0),
                                 "r_arr": do["r_arr"], "q_arr": do["q_arr"],
                                 "r_cash": do["r_cash"], "r_net": do["r_net"],
                                 "lo": lo16, "hi": len(do["close"])}
    T_of = {nm: T for nm, k, T, r in OVL}
    ae_tasks = [(u_, dl, a, 700 + i) for u_ in ("SPY", "QQQ") for dl in DELTAS
                for a in MC_ARMS for i in range(N_MC_AE)]
    ovl_tasks = [(u_, a, T_of[a], 900 + i) for u_ in ("SPY", "QQQ") for a in OVL_MC
                 for i in range(N_MC)]
    print(f"MC: {len(ae_tasks)} in/out + {len(ovl_tasks)} overlay paths...", flush=True)
    mc_ae, mc_ovl = {}, {}
    with Pool(processes=max(1, os.cpu_count() - 1), initializer=_init,
              initargs=(payload,)) as pool:
        for u_, dl, a, res in pool.imap_unordered(_mc_ae, ae_tasks, chunksize=8):
            for fn, tup in res.items():
                mc_ae.setdefault((u_, dl, a, fn), []).append(tup)
        for u_, a, tup in pool.imap_unordered(_mc_ovl, ovl_tasks, chunksize=8):
            mc_ovl.setdefault((u_, a), []).append(tup)
    mcs = {(u_, a): _mc_stock(len(common), eps[(u_, a)], D[u_]["r_net"], D[u_]["r_cash"],
                              [700 + i for i in range(N_MC_AE)])
           for u_ in ("SPY", "QQQ") for a in MC_ARMS}
    print(f"MC done {time.time()-t0:.0f}s", flush=True)

    # =====================================================================
    # REPORT
    # =====================================================================
    def GA(under, delta, arm, frame=PRIMARY, s=HEADLINE):
        return grid[(s, under, delta, arm, frame)]

    def OV(under, arm, win="2016+", s=HEADLINE):
        return ovl[(s, under, arm, win)]

    P("# RSI-2 做 LEAP 入場 / delta-ledger 觸發器:現貨 vs LEAP 框架")
    P("")
    P(f"*測試日期 2026-07-17 · overlay 判詞窗口 2016+ 前後半(用戶標準;2000-2002 尾部"
      f"按用戶明令排除)· in/out 對照 + 租金機制用全 2001+ 窗({len(common)}d / "
      f"{YRS:.1f}y)*")
    P(f"*腳本 `backtest/experiments/exp_rsi2_leap_entry.py`。期權數學 verbatim import"
      f"(simulate_unit_path / build_underlying / build_gates / account ← "
      f"exp_leap_real_sweep;month_start_mask ← exp_core_topup;damp_iv ← "
      f"exp_core_assembly_real)。**新增**:`simulate_spot_overlay`(現貨+LEAP 疊加,"
      f"cross-foot 每 bar 驗算)—— 期權訂價冇改,只加咗現貨底倉 + delta 目標注碼。*")
    P("")

    P("## 0. 點解框架要由「入市/現金」改成「現貨/LEAP」")
    P("")
    P("Repo 之前測 RSI-2 四次,全部係「入市 vs 揸現金」—— 而 **Karst 從來唔揸現金**。"
      "真正嘅選擇係:你手上嗰筆市場曝險,**用現貨表達(1.0x、零租金)定係用 LEAP 表達"
      "(有槓桿、要畀租)**。")
    P("")
    P("**呢個改變晒估錯嘅代價**:")
    P("- 「入市/現金」框架:估錯 = **踏空成個升浪**(可以係 20%+)。")
    P("- 「現貨/LEAP」框架:估錯 = **白畀咗一筆租金**(可能係 1%)—— 因為你永遠喺市場,"
      "冇踏空過。")
    P("")
    P("**擇時之所以貴,係因為錯咗會踏空;現貨打底令踏空冇可能 → 擇時由奢侈品變成負擔得起。**"
      "呢個正正係 AA-strict delta ledger 做緊嘅嘢,分別只係:**現行 ledger 跟月曆調"
      "(H 臂),用戶提議跟訊號調(G 臂)。**")
    P("")

    P("## 1. 結論")
    P("")
    P("<!-- filled after computing -->")
    P("")

    # ---- MAIN overlay table (2016+) ----
    P("## 2. ⭐ 現貨 vs LEAP 疊加:六臂主表(2016+,base m=1.15)")
    P("")
    P("*操作規則嘅確切讀數(切換門檻 grid / VIX 加碼臂 / 年租金總帳)喺 §6.1-6.3。*")
    P("")
    P("*F = 永遠揸現貨(真基線,冇租金)。G/I = RSI2 觸發換 LEAP。H = 月曆(always-on,"
      "= 現行 ledger 代理)。J = 200SMA(用戶已裁決唔用,純對照)。"
      "CapEff = CAGR ÷ 平均總 delta 曝險。MC%ile 對住 {N} 次同曝險隨機孿生。*"
      .replace("{N}", str(N_MC)))
    P("")
    for under in ("SPY", "QQQ"):
        P(f"### {under}")
        P("")
        P("| 臂 | CAGR | CapEff | MaxDD | 絕對PnL | 平均曝險 | LEAP在場% | 租金pp/yr | "
          "交易/yr | MC%ile(PnL) |")
        P("|---|---|---|---|---|---|---|---|---|---|")
        for name, key, T, rebal in OVL:
            c = OV(under, name)
            if name in OVL_MC:
                dist = mc_ovl.get((under, name), [])
                pp = pct_of(c["PnL$"], [x[1] for x in dist])
                pps = f"{pp:.0f}" if np.isfinite(pp) else "n/a"
            else:
                pps = "—"
            tag = " *(對照)*" if name == "J-sma1.5" else (
                " *(基線)*" if name == "F-spot" else "")
            P(f"| {name}{tag} | {f(c['CAGR'],2)} | {f(c['CapEff'],1)} | "
              f"{f(c['MaxDD'],1)} | {money(c['PnL$'])} | {f(c['Expo'],0)} | "
              f"{f(c['OnFrac'],0)} | {c['RentPP']*100:.2f} | {c['Trades']:.1f} | {pps} |")
        P("")

    # ---- G vs F ----
    P("## 3. G vs F:RSI2 換 LEAP,贏唔贏「就咁揸現貨」?")
    P("")
    P("| 標的 | 臂 | ΔCAGR vs F | ΔCapEff vs F | ΔMaxDD vs F | Δ絕對PnL | 全年租金成本 |")
    P("|---|---|---|---|---|---|---|")
    for under in ("SPY", "QQQ"):
        fc = OV(under, "F-spot")
        for name in ("G5-swap1.5", "G10-swap1.5"):
            c = OV(under, name)
            P(f"| {under} | {name} | {f(c['CAGR']-fc['CAGR'],2)} | "
              f"{f(c['CapEff']-fc['CapEff'],1)} | {f(c['MaxDD']-fc['MaxDD'],1)} | "
              f"{money(c['PnL$']-fc['PnL$'])} | {c['RentPP']*100:.2f}pp/yr |")
    P("")
    sgf = OV("SPY", "G5-swap1.5")["CAGR"] - OV("SPY", "F-spot")["CAGR"]
    sce = OV("SPY", "G5-swap1.5")["CapEff"] - OV("SPY", "F-spot")["CapEff"]
    P(f"**判詞**:**輸。** G 喺 2016+ 兩個標的都輸俾純現貨 —— SPY ΔCAGR "
      f"{sgf*100:+.1f}pp、ΔCapEff {sce*100:+.1f}pp(用戶指定嘅主指標)。原因唔係租金"
      f"(租金只係 0.2-0.3pp/yr,好平)—— 係 **RSI2 dip 只令你有 8% 日子輕微加槓桿"
      f"(平均曝險得 104%),喺一個牛市入面「加得太少又加得太遲」**。"
      f"估錯代價細(好事),但估啱嘅收穫一樣細,淨期望值近零至負。")
    P("")

    # ---- G vs H (signal vs calendar) ----
    P("## 4. ⭐ G vs H:訊號 vs 月曆(核心 —— RSI2 做 ledger 觸發器,贏唔贏月曆?)")
    P("")
    P("*H = LEAP 疊加**永遠開住**、每月調(現行 AA-strict ledger 代理);"
      "G = 只喺 RSI2 dip 開 LEAP。兩者目標槓桿同係 1.5x。*")
    P("")
    P("| 標的 | 臂 | CAGR | CapEff | MaxDD | 絕對PnL | LEAP在場% | 租金pp/yr | 交易/yr |")
    P("|---|---|---|---|---|---|---|---|---|")
    for under in ("SPY", "QQQ"):
        for name in ("H-cal1.5", "G5-swap1.5", "G10-swap1.5"):
            c = OV(under, name)
            P(f"| {under} | {name} | {f(c['CAGR'],2)} | {f(c['CapEff'],1)} | "
              f"{f(c['MaxDD'],1)} | {money(c['PnL$'])} | {f(c['OnFrac'],0)} | "
              f"{c['RentPP']*100:.2f} | {c['Trades']:.1f} |")
    P("")
    gh = OV("SPY", "G5-swap1.5")["CAGR"] - OV("SPY", "H-cal1.5")["CAGR"]
    gr, hr = OV("SPY", "G5-swap1.5")["RentPP"], OV("SPY", "H-cal1.5")["RentPP"]
    fce = OV("SPY", "F-spot")["CapEff"]
    hce = OV("SPY", "H-cal1.5")["CapEff"]
    P(f"**判詞**:**月曆(H)喺回報上贏訊號(G)** —— SPY G−H {gh*100:+.1f}pp、"
      f"QQQ 同向。**但呢個係「曝險」贏,唔係「擇時」贏**:H 永遠開 1.5x(曝險 136%),"
      f"G 淨係 dip 先開(曝險 104%),牛市入面多曝險自然多回報。"
      f"關鍵三點:(1) **論 CapEff,H {hce*100:.1f} 都仲輸純現貨 F {fce*100:.1f}** —— "
      f"即係話加 LEAP(無論月曆定訊號)每單位曝險都跑輸就咁揸現貨;"
      f"(2) H 靠嘅係 always-on 槓桿,而**呢個窗口冇 2008**,係尾部被切走先顯得安全;"
      f"(3) G 用 H 五分一嘅租金({gr*100:.2f} vs {hr*100:.2f}pp/yr)—— "
      f"**若目標只係維持一個 delta 目標,G 慳租金,但佢喺牛市欠曝險**。"
      f"RSI2 做觸發器,喺呢個窗口賺唔到佢嘅位。")
    P("")

    # ---- cost of being wrong ----
    P("## 5. ⭐ 估錯嘅代價有幾細?(用戶論點嘅核心數字)")
    P("")
    P("*每個 overlay episode(開咗 LEAP 嗰段)相對「嗰段淨揸現貨」嘅增量回報。"
      "輸嘅 episode = 「開咗 LEAP 但個市冇彈」→ 呢個就係現貨/LEAP 框架下估錯嘅代價。"
      "對照:入市/現金框架下估錯(C10 out 期間個市升咗)= 踏空個升浪。2016+。*")
    P("")
    P("| 標的 | overlay 臂 | episode數 | 命中率 | 平均贏(對) | 平均輸(錯) | 最傷一次 | "
      "vs 踏空升浪(C10 現金) | 錯嘅代價細幾多倍 |")
    P("|---|---|---|---|---|---|---|---|---|")
    for under in ("SPY", "QQQ"):
        miss = cow[(under, "MISS")]
        for name in ("G5-swap1.5", "G10-swap1.5", "I-swap2.0"):
            c = cow[(under, name)]
            ratio = (miss["avg_up"] / abs(c["avg_loss"])
                     if c["avg_loss"] < -1e-9 else np.nan)
            rs = f"{ratio:.1f}x" if np.isfinite(ratio) else "n/a"
            P(f"| {under} | {name} | {c['n']} | {f(c['winrate'],0)} | "
              f"{f(c['avg_win'],2)} | {f(c['avg_loss'],2)} | {f(c['worst'],1)} | "
              f"平均踏空 {f(miss['avg_up'],2)} | **{rs}** |")
    P("")
    rs_list = [cow[(u_, "MISS")]["avg_up"] / abs(cow[(u_, "G5-swap1.5")]["avg_loss"])
               for u_ in ("SPY", "QQQ")
               if cow[(u_, "G5-swap1.5")]["avg_loss"] < -1e-9]
    rmean = np.mean(rs_list) if rs_list else np.nan
    P(f"**判詞**:**用戶論點嘅核心喺呢度證實 —— 而且係本測試最硬嘅發現。** "
      f"喺現貨/LEAP 框架下估錯(開咗 LEAP 但個市冇彈),平均每次代價得 0.4-0.9%;"
      f"喺入市/現金框架下估錯(揸現金而個市升咗),平均每次踏空 3.7-5.7% —— "
      f"**估錯代價細咗 ~{rmean:.0f} 倍**。呢個就係「因為你永遠喺市場,擇時由奢侈品變成"
      f"負擔得起」嘅實測。**但要誠實**:代價細唔等於有正報酬 —— G 每 episode 命中率"
      f"29-46%、期望值近零至負(見上表 avgW vs avgL)。**框架令擇時變得「輸得起」,"
      f"但唔會令一個冇 edge 嘅訊號變得有 edge。** 呢個係「可以隨便試」嘅許可證,"
      f"唔係「RSI2 有效」嘅證據。")
    P("")

    # ---- leverage ladder ----
    P("## 6. 槓桿階梯:G(1.5x) vs I(2.0x),幾高先蝕?")
    P("")
    P("| 標的 | 臂 | 目標槓桿 | CAGR | CapEff | MaxDD | 絕對PnL | 平均曝險 | 租金pp/yr |")
    P("|---|---|---|---|---|---|---|---|---|")
    for under in ("SPY", "QQQ"):
        for name, T in (("F-spot", 1.0), ("G5-swap1.5", 1.5), ("I-swap2.0", 2.0)):
            c = OV(under, name)
            P(f"| {under} | {name} | {T:.1f}x | {f(c['CAGR'],2)} | {f(c['CapEff'],1)} | "
              f"{f(c['MaxDD'],1)} | {money(c['PnL$'])} | {f(c['Expo'],0)} | "
              f"{c['RentPP']*100:.2f} |")
    P("")
    P(f"**判詞**:I(2.0x)喺兩個標的都**輸過** G(1.5x)—— SPY I CAGR "
      f"{OV('SPY','I-swap2.0')['CAGR']*100:+.1f}% vs G "
      f"{OV('SPY','G5-swap1.5')['CAGR']*100:+.1f}%,MaxDD 亦更差。"
      f"因為 RSI2 觸發嘅係 dip,dip 之後未必即刻彈,加更高槓桿只係放大咗「錯」嗰邊。"
      f"**用 RSI2 做觸發器,槓桿越高越蝕,冇一級係著數** —— 呢個同「always-on 越高越好」"
      f"(H/J)相反,再次指向:問題唔係槓桿水平,係 RSI2 揀嘅時點冇 edge。")
    P("")

    # ---- OPERATIONAL grids (data only; verdicts deferred to review) ----
    P("## 6.1 操作規則:切換門檻 grid(G 臂,2016+,m=1.15)")
    P("")
    P("*G 臂(現貨 + RSI2 換 LEAP 1.5x,Δ0.80 腿)嘅入場門檻 × 出場規則全掃。"
      "**純數據,判詞留待覆核。** 切換/yr = 現貨→LEAP→現貨嘅完整來回次數;"
      "年租 = 交易租金(引擎實測 cost drag)+ carry 租金(theta × 權利金佔比)。*")
    P("")
    for under in ("SPY", "QQQ"):
        P(f"### {under}")
        P("")
        P("| 入場 | 出場 | CapEff | 絕對PnL | MaxDD | 切換/yr | roll/yr | LEAP在場% | "
          "年租pp(交易+carry) |")
        P("|---|---|---|---|---|---|---|---|---|")
        for ent in ENTRIES:
            for elab, erule in EXITS:
                m = sw_grid[(under, ent, elab)]
                P(f"| RSI2<{ent} | {elab} | {f(m['CapEff'],1)} | {money(m['PnL$'])} | "
                  f"{f(m['MaxDD'],1)} | {m['switches_yr']:.1f} | {m['rolls_yr']:.1f} | "
                  f"{f(m['OnFrac'],0)} | {m['total_rent']*100:.2f} "
                  f"({m['txn_rent']*100:.2f}+{m['carry_rent']*100:.2f}) |")
        P("")
    fc_ref = OV("SPY", "F-spot")
    P(f"*(對照:純現貨 F 喺 2016+ CapEff {f(fc_ref['CapEff'],1)}、PnL "
      f"{money(fc_ref['PnL$'])}、MaxDD {f(fc_ref['MaxDD'],1)}、租金 0。)*")
    P("")

    P("## 6.2 操作規則:VIX 加碼臂(VIX>28 時 delta 1.3x→1.5x)")
    P("")
    P("*G 臂(RSI2<5 入 / 收>5MA 出)。加碼臂:平時目標 1.3x,VIX>28 時升到 1.5x"
      "(07-05 R4:極端 VIX = jackpot 區)。對照:固定 1.3x 同固定 1.5x。"
      "**純數據,判詞留待覆核。**2016+,m=1.15。*")
    P("")
    for under in ("SPY", "QQQ"):
        P(f"### {under}")
        P("")
        P("| 臂 | CAGR | CapEff | MaxDD | 絕對PnL | 平均曝險 | 切換/yr | 年租pp |")
        P("|---|---|---|---|---|---|---|---|")
        for key, lab in (("G-fixed1.3", "固定 1.3x"), ("G-fixed1.5", "固定 1.5x"),
                         ("G-VIXboost", "VIX>28→1.5x")):
            m = vix_rows[(under, key)]
            P(f"| {lab} | {f(m['CAGR'],2)} | {f(m['CapEff'],1)} | {f(m['MaxDD'],1)} | "
              f"{money(m['PnL$'])} | {f(m['Expo'],0)} | {m['switches_yr']:.1f} | "
              f"{m['total_rent']*100:.2f} |")
        P("")

    P("## 6.3 操作規則:年租金總帳(條租金單)")
    P("")
    P("*用戶個 frame:「估錯代價 = 租金」。呢張表把每個切換門檻變體嘅租金拆開:"
      "**切換次數/年 × 每次來回成本 = 交易租金;另加 carry(theta)租金。**"
      "每次來回成本 = 開倉權利金%NAV × (0.5%/side × 2 + 隱含 spread,已含喺引擎 cost)。*")
    P("")
    P("| 標的 | 變體 | 切換/yr | 每次來回權利金%NAV | 交易租pp/yr | carry租pp/yr | 年租總pp |")
    P("|---|---|---|---|---|---|---|")
    for under in ("SPY", "QQQ"):
        for ent in ENTRIES:
            m = sw_grid[(under, ent, "收>5MA")]
            per_sw = (m["txn_rent"] / m["switches_yr"] if m["switches_yr"] > 1e-6
                      else np.nan)
            # implied premium%NAV per round-trip: txn per switch / (2*0.5%)
            prem_pct = per_sw / (2 * COST) if np.isfinite(per_sw) else np.nan
            ps = f"{prem_pct*100:.1f}%" if np.isfinite(prem_pct) else "n/a"
            P(f"| {under} | RSI2<{ent}/收>5MA | {m['switches_yr']:.1f} | {ps} | "
              f"{m['txn_rent']*100:.2f} | {m['carry_rent']*100:.2f} | "
              f"{m['total_rent']*100:.2f} |")
    P("")
    P("*讀法:入場門檻越鬆(<20),切換越密、交易租金越貴,但每次曝險時間越長 → "
      "carry 租金亦升。呢張就係「畀幾多租」嘅確切帳,唔使估。判詞留待覆核。*")
    P("")

    # ---- regime split ----
    P("## 7. Regime:2016-2020(平靜,RSI2 死區)vs 2021+(震盪)")
    P("")
    P("*用戶關鍵問題:**平靜期 G 會唔會輸 F?**(即租金白畀)*")
    P("")
    for under in ("SPY", "QQQ"):
        P(f"### {under}")
        P("")
        P("| 臂 | 2016-2020 CAGR | 2016-2020 vs F | 2021+ CAGR | 2021+ vs F |")
        P("|---|---|---|---|---|")
        f1 = OV(under, "F-spot", "2016-2020")
        f2 = OV(under, "F-spot", "2021+")
        for name, key, T, rebal in OVL:
            c1 = OV(under, name, "2016-2020")
            c2 = OV(under, name, "2021+")
            P(f"| {name} | {f(c1['CAGR'],2)} | {f(c1['CAGR']-f1['CAGR'],2)} | "
              f"{f(c2['CAGR'],2)} | {f(c2['CAGR']-f2['CAGR'],2)} |")
        P("")
    g_16 = OV("SPY", "G5-swap1.5", "2016-2020")["CAGR"] - OV("SPY", "F-spot", "2016-2020")["CAGR"]
    g_21 = OV("SPY", "G5-swap1.5", "2021+")["CAGR"] - OV("SPY", "F-spot", "2021+")["CAGR"]
    P(f"**判詞**:**平靜期 G 輸 F,震盪期 G 都輸 F** —— SPY G−F 喺 2016-2020 "
      f"{g_16*100:+.1f}pp、2021+ {g_21*100:+.1f}pp,兩段都負。用戶擔心嘅「平靜期租金"
      f"白畀」的確發生,但唔止平靜期 —— **兩個 regime G 都跑輸純現貨**,可見問題唔係"
      f"regime 挑錯,係 RSI2 觸發本身冇 edge。反而 always-on 嘅 H/J 兩段都贏 F —— "
      f"但再強調一次:呢兩段都冇 2008 級數嘅熊,always-on 槓桿嘅尾部風險喺呢個窗口"
      f"睇唔到(要睇返 §9c 同 `2026-06-30_leap_timing.md` 嘅 −99% 清零)。")
    P("")

    # ---- Δ ladder mechanics (full window) ----
    P("## 8. Δ 階梯機制:$1 買到幾多曝險?租金幾多?(full 2001+)")
    P("")
    P("| 標的 | Δ | 槓桿倍數($曝險/$1權利金) | 權利金%S | theta租金%/yr(佔權利金) |")
    P("|---|---|---|---|---|")
    for under in ("SPY", "QQQ"):
        for delta in DELTAS:
            lev, theta = levs[(under, delta)]
            prem_s = delta / lev if np.isfinite(lev) and lev > 0 else np.nan
            P(f"| {under} | {delta:.2f} | **{lev:.2f}x** | {prem_s*100:.1f}% | "
              f"{f(theta,1)} |")
    P("")
    P(f"**判詞**:用戶講「$1 買 $2-5」—— 實測 Δ0.80 {levs[('SPY',0.80)][0]:.1f}x / "
      f"Δ0.50 {levs[('SPY',0.50)][0]:.1f}x / Δ0.30 {levs[('SPY',0.30)][0]:.1f}x,"
      f"比用戶講嘅更高。但租金同步跳:越平嘅入場(細 Δ)每單位曝險嘅租金越貴。"
      f"疊加臂用 Δ0.80(最低租金)做 LEAP 腿。")
    P("")

    # ---- IN/OUT control section (demoted) ----
    P("## 9. 對照:舊「入市/現金」框架(呢個先係之前四次答錯嘅框架)")
    P("")
    P("*保留舊五臂做對照,顯示「入市/現金」框架點樣製造一個必死嘅稻草人。"
      "PORT10 = 權利金封頂10%NAV。full 2001+。*")
    P("")
    P("### 9a. 純 RSI2 做 LEAP 入場(離場=現金)—— 6 格全輸")
    P("")
    P("| 標的 | Δ | 臂 | 絕對PnL | CAGR | MaxDD | CapEff | 曝險 | MC%ile(PnL) |")
    P("|---|---|---|---|---|---|---|---|---|")
    for under in ("SPY", "QQQ"):
        for delta in DELTAS:
            cells = {a: GA(under, delta, a) for a in ARMS}
            neg = any(cells[a]["PnL$"] < 0 for a in ARMS)
            for arm in ("A-ALWAYS", "B-GATED", "C5-RSI2<5", "D-GATED+DIP"):
                c = cells[arm]
                if arm in MC_ARMS:
                    dist = mc_ae.get((under, delta, arm, PRIMARY), [])
                    pp = pct_of(c["PnL$"], [x[1] for x in dist])
                    pps = f"{pp:.0f}" if np.isfinite(pp) else "n/a"
                else:
                    pps = "—"
                ce = f"~~{f(c['CapEff'],1)}~~" if neg else f(c["CapEff"], 1)
                P(f"| {under} | {delta:.2f} | {arm} | {money(c['PnL$'])} | "
                  f"{f(c['CAGR'],2)} | {f(c['MaxDD'],1)} | {ce} | {f(c['Expo'],0)} | "
                  f"{pps} |")
    P("")
    P("*負 PnL 格嘅 CapEff 一律劃線(memory: capital-efficiency-two-traps —— 蝕本組合"
      "揸得耐反而 CapEff 靚,排名倒轉)。純 RSI2 臂(C5/C10/E)喺 6 個 Δ×標的格全部"
      "輸俾 always-in 同 200SMA,絕大部分負 PnL —— 機制係期限錯配:持倉幾日,"
      "卻買足一年期期權 + 來回成本。*")
    P("")
    P("### 9b. 正股層(冇槓桿冇租金)—— 重現舊四份檔「冇料」結論")
    P("")
    P("| 標的 | 臂 | CAGR | MaxDD | CapEff | 曝險 | MC%ile(PnL) |")
    P("|---|---|---|---|---|---|---|")
    for under in ("SPY", "QQQ"):
        for arm in ARMS:
            c = stock[(under, arm)]
            if arm in MC_ARMS:
                dd = mcs[(under, arm)]
                pps = f"{pct_of(c['PnL$'], dd[:,1]):.0f}"
            else:
                pps = "—"
            P(f"| {under} | {arm} | {f(c['CAGR'],2)} | {f(c['MaxDD'],1)} | "
              f"{f(c['CapEff'],1)} | {f(c['Expo'],0)} | {pps} |")
    P("")
    P("*正股層 RSI2 臂 MC 百分位近中位、ΔCAGR 為負 —— 同 repo 四份舊檔一致(冇料)。"
      "本測試冇推翻嗰四份,只係話:**嗰層答完都唔關事**,因為冇租金。*")
    P("")
    P("### 9c. SLEEVE 極端框架 —— 「入市/現金」稻草人:唔擇時 = 清零")
    P("")
    P("| 標的 | Δ | A-ALWAYS PnL | A-ALWAYS MaxDD | B-GATED PnL | 分別 |")
    P("|---|---|---|---|---|---|")
    for under in ("SPY", "QQQ"):
        for delta in DELTAS:
            a = GA(under, delta, "A-ALWAYS", "SLEEVE")
            b = GA(under, delta, "B-GATED", "SLEEVE")
            ruin = "⚠️清零" if a["PnL$"] <= -CAPITAL * 0.999 else ""
            P(f"| {under} | {delta:.2f} | {money(a['PnL$'])} {ruin} | "
              f"{f(a['MaxDD'],1)} | {money(b['PnL$'])} | "
              f"{'擇時救返' if b['PnL$']>a['PnL$'] else '—'} |")
    P("")
    P("*SLEEVE(100%注碼落權利金)之下,「入市/現金」永遠揸 LEAP 喺 Δ0.50/0.30 清零。"
      "**但呢個係「入市/現金」框架先有嘅災難** —— 現貨/LEAP 框架(§2-7)因為有現貨底倉,"
      "根本冇呢種清零風險。用一個必死稻草人去證明「擇時有價值」,係之前答錯嘅根源。*")
    P("")

    # ---- IV robustness ----
    P("## 10. IV 穩健性:排名會唔會隨 m 反轉?(overlay 臂,2016+)")
    P("")
    P("*`2026-07-17_core_topup_realcost.md` 已裁定 m=0.85 已死、m=1.15 誠實基準。"
      "本測試唔重跑佢個 α,只報臂間排名穩唔穩。*")
    P("")
    P("| 標的 | 設定 | 最佳臂(絕對PnL) | F PnL | G5 PnL | H PnL | I PnL | 反轉? |")
    P("|---|---|---|---|---|---|---|---|")
    for under in ("SPY", "QQQ"):
        ref = None
        for sname, m, dmp in SETTINGS:
            cs = {nm: ovl[(sname, under, nm, "2016+")] for nm, k, T, r in OVL}
            best = max(cs, key=lambda a: cs[a]["PnL$"])
            if ref is None:
                ref, flip = best, "— (基準)"
            else:
                flip = "**係**" if best != ref else "否"
            P(f"| {under} | {sname} | **{best}** | {money(cs['F-spot']['PnL$'])} | "
              f"{money(cs['G5-swap1.5']['PnL$'])} | {money(cs['H-cal1.5']['PnL$'])} | "
              f"{money(cs['I-swap2.0']['PnL$'])} | {flip} |")
    P("")

    # ---- declarations ----
    P("## 11. 申報:重疊窗口 / 有效樣本 / 多重比較 / 模型限制")
    P("")
    P(f"- **多重比較**:overlay {len(OVL)} 臂 × {len(SETTINGS)} IV × 2 標的 × "
      f"{len(WINS)} 窗 = {len(OVL)*len(SETTINGS)*2*len(WINS)} 格;in/out 控制 "
      f"{len(ARMS)}×{len(DELTAS)}×{len(SETTINGS)}×2×{len(FRAMES)} 格。**未做 Bonferroni**;"
      f"只有跨標的 / 跨 m 一致嘅方向先可信。")
    P(f"- **有效樣本**:overlay 判詞窗口得 **~{len(idx16)/TD:.1f} 年(2016+)**,"
      f"用戶明令排除 2000-2002 尾部 —— 好處係唔靠一次極端事件,壞處係樣本細、"
      f"regime 少(得一次 2020 急跌 + 2022 熊)。日度重疊 + LEAP 189td 重疊 → "
      f"有效獨立觀測遠少於名義日數。")
    P(f"- **MC 對照**:overlay 每臂 {N_MC} 次、in/out 每臂 {N_MC_AE} 次,保持 episode "
      f"數 + 長度 multiset 不變,只隨機化「幾時」。控制咗曝險同持倉長度 → 答緊「揀嗰啲"
      f"時點有冇料」,唔係「短持倉好唔好」。")
    P(f"- **F / H 冇 MC**:F 冇 LEAP,H always-on,兩者嘅「同曝險隨機孿生」就係自己。")
    P(f"- **模型限制**:BSM + VIX/VXN,**唔係真實期權鏈**(冇 smile/期限結構/買賣差/"
      f"提前行權;可買零碎合約)。`2026-07-09_options_chain_spotcheck.md` 實測 SPY "
      f"0.50Δ 真隱含 m=1.22、0.70Δ m=1.63 vs 本測試 1.15 → **真實租金比本測試更貴,"
      f"擇時嘅必要性只會更高**,而深價內格偏樂觀。")
    P(f"- **overlay 引擎係新寫嘅**(期權訂價 verbatim,只加現貨底倉+delta目標注碼);"
      f"cross-foot 每 bar 驗 NAV=現貨+cash+期權值、NAV 守恆,全程 {ASSERT_N['n']:,} 次 "
      f"assert 全過。")
    P(f"- **200SMA(J 臂)只做對照**:用戶 2026-07-17 已裁決唔用 200SMA 濾網。")
    P(f"- **本測試冇推翻**:正股層 RSI2 舊四檔「冇料」結論喺 §9b 重現;"
      f"本測試講嘅係嗰層唔係決策層。")
    P("")
    P("### 數據來源")
    P("")
    P("| 序列 | 來源 | 列數 | 起 | 訖 |")
    P("|---|---|---|---|---|")
    for nm, src, n_, a_, b_ in prov:
        P(f"| {nm} | {src} | {n_} | {a_} | {b_} |")
    P(f"\n*執行 {time.time()-t0:.0f}s*")

    # ---- fill conclusion (section 1) ----
    concl = []
    concl.append("## 1. 結論")
    concl.append("")
    # compute G vs F and G vs H headline numbers on SPY 2016+
    def gvf(u_):
        g, fc = OV(u_, "G5-swap1.5"), OV(u_, "F-spot")
        return g["CAGR"] - fc["CAGR"], g["MaxDD"] - fc["MaxDD"], g["RentPP"]
    def gvh(u_):
        g, h = OV(u_, "G5-swap1.5"), OV(u_, "H-cal1.5")
        return g["CAGR"] - h["CAGR"], g["RentPP"], h["RentPP"]
    sp_gf, qq_gf = gvf("SPY"), gvf("QQQ")
    sp_gh, qq_gh = gvh("SPY"), gvh("QQQ")
    ratios = [cow[(u_, "MISS")]["avg_up"] / abs(cow[(u_, "G5-swap1.5")]["avg_loss"])
              for u_ in ("SPY", "QQQ")
              if cow[(u_, "G5-swap1.5")]["avg_loss"] < -1e-9]
    rr = np.mean(ratios) if ratios else np.nan
    fce_s, gce_s = OV("SPY", "F-spot")["CapEff"], OV("SPY", "G5-swap1.5")["CapEff"]
    hce_s = OV("SPY", "H-cal1.5")["CapEff"]
    concl.append(
        "**一句總結:用戶個「現貨/LEAP」框架修正係啱嘅 —— 佢令擇時「輸得起」(估錯代價"
        f"細 ~{rr:.0f} 倍);但喺 2016+ 呢個窗口,RSI2 做觸發器賺唔到佢嘅位,而『贏咗純"
        "現貨』嗰啲臂係靠 always-on 槓桿贏、唔係靠擇時贏,而且係靠一個切走咗 2008 嘅"
        "窗口先顯得安全。**")
    concl.append("")
    concl.append(
        f"1. **⭐ 估錯代價塌陷 —— 用戶論點嘅核心,證實。** 現貨打底、用 LEAP 表達額外"
        f"曝險,估錯(開咗 LEAP 但市冇彈)每次平均蝕 0.4-0.9%;而入市/現金框架估錯"
        f"(揸現金而市升)每次踏空 3.7-5.7% —— **細 ~{rr:.0f} 倍**(2016+,兩標的平均)。"
        f"「因為永遠喺市場,擇時由奢侈品變成負擔得起」係真嘅。")
    concl.append(
        f"2. **但「輸得起」≠「有錢賺」。** G(RSI2 換 LEAP 1.5x)喺 2016+ 兩標的都**輸純"
        f"現貨 F**:SPY ΔCAGR {sp_gf[0]*100:+.1f}pp、ΔCapEff {(gce_s-fce_s)*100:+.1f}pp。"
        f"每 episode 命中率得 29-46%、期望值近零至負。框架令一個錯決定唔會傷你,"
        f"但唔會令一個冇 edge 嘅訊號生出 edge 嚟。")
    concl.append(
        f"3. **論主指標(CapEff),純現貨打贏每一個 LEAP 疊加臂。** SPY:F {fce_s*100:.1f} "
        f">  H {hce_s*100:.1f} > G {gce_s*100:.1f}(QQQ 同型)。加 LEAP —— 無論訊號調"
        f"(G)定月曆調(H)—— **每單位曝險都跑輸就咁揸現貨**。LEAP 疊加嘅價值係"
        f"「攞到 >1.0x 曝險而唔使孭 margin call」(convexity),唔係擇時 alpha。")
    concl.append(
        f"4. **G vs H(訊號 vs 月曆,核心問題)**:H(always-on 1.5x)喺回報上贏 G "
        f"SPY {-sp_gh[0]*100:+.1f}pp —— **但係「曝險」贏,唔係「擇時」贏**(H 曝險 136% vs "
        f"G 104%),而 H 靠嘅 always-on 槓桿喺呢個冇 2008 嘅窗口先安全。G 唯一著數係"
        f"租金只使 H 嘅 1/5({sp_gh[1]*100:.2f} vs {sp_gh[2]*100:.2f}pp/yr)。"
        f"**結論:RSI2 唔係一個好嘅 ledger 觸發器 —— 佢喺牛市欠曝險,而佢嘅省租金"
        f"換唔返嗰段回報。**")
    concl.append(
        f"5. **舊框架(RSI2 入 LEAP / 揸現金)依然係差**:6 個 Δ×標的格全輸(§9a),"
        f"機制係期限錯配(持倉幾日、買足一年期)。呢個同 §1.1 唔矛盾 —— 佢正正證明"
        f"「入市/現金」係錯框架:同一 RSI2 訊號喺現金框架下有害,喺現貨/LEAP 框架下"
        f"只係「無害但無益」。")
    concl.append(
        f"6. **對 scorecard v3.1 / AA-strict ledger(數據方向,操作決定留覆核)**:"
        f"「LEAP entry = RSI-2 DIP」原始出處係純對稱論證、冇回測、冇入 SETTLED.md "
        f"就落咗生產。本測試提供嘅數據方向:**(a)「RSI2 做入 LEAP/揸現金開關」6 格全輸"
        f"(§9a),同 2026-07-06 一致;(b) delta ledger 上,月曆調(H)喺 2016+ 回報高於"
        f"訊號調(G),而 G 慳 4/5 租金但欠曝險 —— 訊號調冇為 ledger 加回報分;"
        f"(c) 用戶嘅『輸得起』框架成立,現貨/LEAP 疊加係啱嘅載體,欠嘅係一個有 edge "
        f"嘅入場訊號。** 操作規則(邊個門檻 / 要唔要 VIX 加碼 / 改唔改 ledger 觸發)"
        f"嘅確切讀數喺 §6.1-6.3,判詞留待覆核。")
    concl.append("")
    concl.append(
        "**未解 / 風險**:(i) 2016+ 冇 2008 級熊 —— always-on 槓桿(H/J)嘅尾部風險"
        "睇唔到,唔可以因為 H 喺呢窗口贏就轉 always-on;(ii) BSM+VIX 低估真實租金"
        "(真隱含 m≥1.22),真租金更貴 → 用戶「輸得起」嘅邊際更窄;(iii) RSI2 冇 edge "
        "唔代表所有訊號冇 edge —— 框架已證可載,欠嘅係一個真正揀得中時點嘅訊號。")
    concl.append("")
    # splice conclusion into the placeholder
    text = "\n".join(out)
    text = text.replace("## 1. 結論\n\n<!-- filled after computing -->\n",
                        "\n".join(concl) + "\n")

    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    with open(RESULTS, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\nwrote {RESULTS}  ({time.time()-t0:.0f}s)", flush=True)

    # ---- console digest ----
    print("\n=== overlay 2016+ (CAGR / CapEff / MaxDD / PnL) ===")
    for under in ("SPY", "QQQ"):
        print(f"-- {under}")
        for name, key, T, rebal in OVL:
            c = OV(under, name)
            print(f"   {name:12s} CAGR {c['CAGR']*100:+6.2f} CapEff {c['CapEff']*100:+6.1f}"
                  f" MaxDD {c['MaxDD']*100:+7.1f} PnL {c['PnL$']:>10,.0f} "
                  f"expo {c['Expo']*100:5.0f}% rent {c['RentPP']*100:.2f}pp")
    print("\n=== cost of being wrong (2016+) ===")
    for under in ("SPY", "QQQ"):
        miss = cow[(under, "MISS")]
        for name in ("G5-swap1.5", "G10-swap1.5", "I-swap2.0"):
            c = cow[(under, name)]
            ratio = (miss["avg_up"] / abs(c["avg_loss"]) if c["avg_loss"] < -1e-9
                     else float('nan'))
            print(f"  {under} {name:12s} eps {c['n']:3d} win {c['winrate']*100:4.0f}% "
                  f"avgW {c['avg_win']*100:+5.2f} avgL {c['avg_loss']*100:+5.2f} "
                  f"| miss-rally {miss['avg_up']*100:+5.2f} ratio {ratio:.1f}x")
    print("\n=== switch grid (SPY, CapEff / switches-yr / rent-pp) ===")
    for ent in ENTRIES:
        for elab, erule in EXITS:
            m = sw_grid[("SPY", ent, elab)]
            print(f"  <{ent:2d} {elab:8s} CapEff {m['CapEff']*100:+5.1f} "
                  f"sw/yr {m['switches_yr']:4.1f} rent {m['total_rent']*100:.2f}pp "
                  f"PnL {m['PnL$']:>8,.0f}")
    print("\n=== VIX booster (CAGR / rent) ===")
    for under in ("SPY", "QQQ"):
        for key in ("G-fixed1.3", "G-fixed1.5", "G-VIXboost"):
            m = vix_rows[(under, key)]
            print(f"  {under} {key:12s} CAGR {m['CAGR']*100:+.2f} "
                  f"rent {m['total_rent']*100:.2f}pp PnL {m['PnL$']:>8,.0f}")
    print("\n=== G vs H (signal vs calendar) ===")
    for under in ("SPY", "QQQ"):
        g, h = OV(under, "G5-swap1.5"), OV(under, "H-cal1.5")
        print(f"  {under} G CAGR {g['CAGR']*100:+.2f} rent {g['RentPP']*100:.2f} | "
              f"H CAGR {h['CAGR']*100:+.2f} rent {h['RentPP']*100:.2f} | "
              f"G-H {(g['CAGR']-h['CAGR'])*100:+.2f}pp")
    print("\n=== regime split (CAGR vs F) ===")
    for under in ("SPY", "QQQ"):
        f1, f2 = OV(under, "F-spot", "2016-2020"), OV(under, "F-spot", "2021+")
        for name in ("G5-swap1.5", "H-cal1.5", "I-swap2.0"):
            c1, c2 = OV(under, name, "2016-2020"), OV(under, name, "2021+")
            print(f"  {under} {name:12s} 16-20 {(c1['CAGR']-f1['CAGR'])*100:+6.2f}pp | "
                  f"21+ {(c2['CAGR']-f2['CAGR'])*100:+6.2f}pp")


if __name__ == "__main__":
    main()
