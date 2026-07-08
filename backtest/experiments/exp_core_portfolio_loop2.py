"""LOOP 2 — pre-registered architecture grid over the loop-1 sleeve lab.

Imports (does not modify) exp_core_portfolio_lab.py. Runs the ORCHESTRATOR-PRE-REGISTERED
grid exactly — no additions, no tuning:

  ARCH-A   passive-plus-overlay: 75% S1 + 10% S2 LEAP premium budget + 15% cash.
           S4 covered-call sold on 50% of base (the <=50% cap, taken at the cap) when
           RSI-2>90 (next-bar). FEAR DEPLOYMENT: in quadrant Q2 (SPY>200SMA & VIX-proxy>28),
           deploy up to 10pp of NAV from cash into EXTRA S1 (next-bar); unwind (sell exactly
           the extra units) when VIX-proxy<18 (next-bar).
  ARCH-A2  = A, but the fear vehicle is a CSP: sell 20D/21DTE put with 10pp collateral on
           quadrant-Q2 entry (next-bar) instead of buying extra S1. The put self-liquidates
           (50% PT or expiry, assignment sold next close) — NO forced VIX<18 unwind (a 21DTE
           short put is self-expiring; forcing an early close would add an unregistered rule).
           Re-entry allowed only while Q2 persists.
  ARCH-A3  = A + GREED-TRIM: F&G>80 (data 2011+ only; pre-2011 flag=False, never
           missing-as-signal) -> sell base worth 20pp of NAV to cash; buy back (same dollar
           ledger) when F&G<55. Next-bar both ways.
  ARCH-B   options-core: 0% base; 15% S2 premium budget + 85% cash; CSP with 30% collateral
           ONLY in quadrant Q2; rest cash. "CSP ladder" implemented as the loop-1
           SINGLE-POSITION non-overlapping CSP at 30% collateral, re-entering immediately
           while Q2 persists — a conservative reading (same average exposure as a 3x10pp
           ladder, less entry-date diversification within an episode). Documented, not hidden.
  ARCH-C   base+LEAP minimal: 85% S1 + 10% S2 + 5% cash. Nothing else.
  Baselines: 100% S1;  SPY B&H TR-net (the benchmark itself).

QUADRANT MAPPING (2x2, partition of all post-warmup days; Q2 fixed by the brief):
  Q1 = SPY>200SMA & VIX-proxy<=28   (calm/mid uptrend)
  Q2 = SPY>200SMA & VIX-proxy>28    (fear spike, trend intact)  <- the brief's quadrant (2)
  Q3 = SPY<=200SMA & VIX-proxy>28   (bear panic)
  Q4 = SPY<=200SMA & VIX-proxy<=28  (quiet downtrend)
  NA = warmup days (SMA/VIX-proxy not yet defined) — excluded from attribution.

CASH RATE — PIECEWISE era averages (approx 3M T-bill, no HK withholding on treasury
interest), the loop-2 headline (constant-3% fictionalized ZIRP in loop 1):
  1996-2000 5.0% | 2001-2004 1.8% | 2005-2007 4.6% | 2008 1.5% | 2009-2015 0.1%
  2016-2019 1.9% | 2020-2021 0.1% | 2022-2026 4.6%
0%-rate pessimistic bound re-run for the top-2 configs (by FULL Sharpe, piecewise, raw gate).
NOTE: BSM pricing r stays 0.03 as loop 1 (pre-registered "costs as loop 1"; the piecewise
directive concerns CASH YIELD, not option-pricing inputs).

S2 GATE VARIANTS (both run for EVERY arch — single pre-registered hysteresis variant):
  raw  = loop-1 GATED+DIP (enter: >200SMA & RSI-2<10 within 5d; exit: <200SMA)
  hyst = same entry; exit only if close < 200SMA*0.98 for 5 CONSECUTIVE days.

MANDATORY MECHANICS (all implemented):
  - Base is NEVER sold on trend signals. Only A3's greed-trim sells base; S4 assignment is
    cash-settled inside the sleeve (economically sell-at-strike/rebuy — loop-1 treatment).
  - Next-bar execution everywhere. Costs as loop 1 (ETF 5bps/side, options 0.5%/side of
    premium, assignment slip 5bps). Zero-cost twin of every config gives total cost drag.
  - Combiner: stake-tracking day-loop engine, rebalance-at-events semantics (sleeve stakes
    re-budgeted to target weight ONLY at the sleeve's own entry/roll events, floating
    between events). Improvement over loop-1's rebalance_at_events, documented: the exit-day
    sleeve return (final option move + exit cost) is now APPLIED to the stake before the
    sweep-to-cash (loop 1 knowingly swept the stale stake). Impact quantified in the sanity
    check vs loop-1 section-D numbers.
  - Funding cap: sleeve top-ups draw from CASH only (min(target, cash)); the engine never
    sells base to fund an option sleeve.

KNOWN APPROXIMATIONS (documented, consistent with loop 1):
  - S3-committed collateral earns NO interest while a put is live (loop-1 sleeve mechanics).
    Pessimistic for A2/B in high-rate eras; the exact foregone-carry pp/yr is measured and
    reported per config (forgone_carry telemetry).
  - S4/S3 same-day settle-and-re-enter keeps the prior trade's notional for the follow-on
    trade (entry detected via in_pos False->True flip). Second-order (notional drifts slowly).
  - S4's P&L timeline is the loop-1 notional-normalized sleeve scaled by 0.5*base-MV at each
    detected entry; trade timing is portfolio-independent (entry gate = RSI-2>90 next-bar,
    non-overlapping), only notional scales.

    python backtest/experiments/exp_core_portfolio_loop2.py
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from exp_core_portfolio_lab import (  # noqa: E402
    TD, DIV_NET_YR, ETF_COST_SIDE, OPT_COST_SIDE, CACHE_DIR, WINDOWS,
    load_spy_close, load_fear_greed, sma, rsi2, vix_proxy, iv_proxy_1y,
    iv_proxy_short_dte, build_gates, sim_s2_leap, sim_s3_csp, sim_s4_short_call,
    spy_bh_total_return, cagr, ann_sharpe, max_drawdown, jensen_alpha,
    window_mask, rebase_nav,
)

# ---------------------------------------------------------------- piecewise cash rate
RATE_ERAS = [
    (1996, 2000, 0.050), (2001, 2004, 0.018), (2005, 2007, 0.046), (2008, 2008, 0.015),
    (2009, 2015, 0.001), (2016, 2019, 0.019), (2020, 2021, 0.001), (2022, 2026, 0.046),
]


def piecewise_rate(index: pd.DatetimeIndex) -> np.ndarray:
    yr = index.year.values
    r = np.zeros(len(index))
    for y0, y1, v in RATE_ERAS:
        r[(yr >= y0) & (yr <= y1)] = v
    return r


# ---------------------------------------------------------------- S2 gate variants
def build_hold(close: pd.Series, hysteresis: bool):
    """Stateful GATED+DIP hold series. raw: exact mirror of lab build_gates. hyst: exit
    only when close < 0.98*200SMA for 5 consecutive days. Returns (next-bar gate array,
    unshifted hold array, n_entries, n_exits)."""
    sma200 = sma(close, 200)
    r2 = rsi2(close)
    above = (close > sma200)
    trig = (r2 < 10).rolling(5, min_periods=1).max().astype(bool)
    if hysteresis:
        bb = close < (0.98 * sma200)
        exit_sig = (bb.rolling(5, min_periods=5).sum() == 5)
    else:
        exit_sig = ~above
    n = len(close)
    hold = np.zeros(n, dtype=bool)
    h = False
    av, tv, ev = above.values, trig.values, exit_sig.values
    for i in range(n):
        if (not h) and av[i] and tv[i]:
            h = True
        elif h and ev[i]:
            h = False
        hold[i] = h
    hold_s = pd.Series(hold, index=close.index)
    gate = hold_s.shift(1).astype("boolean").fillna(False).astype(bool).values
    prev = hold_s.shift(1).fillna(False).astype(bool)
    n_ent = int(((~prev) & hold_s).sum())
    n_ex = int((prev & (~hold_s)).sum())
    return gate, hold, n_ent, n_ex


def entry_flips(in_pos: np.ndarray) -> np.ndarray:
    f = np.zeros(len(in_pos), dtype=bool)
    prev = False
    for i in range(len(in_pos)):
        cur = bool(in_pos[i])
        if cur and not prev:
            f[i] = True
        prev = cur
    return f


# ---------------------------------------------------------------- portfolio engine
def run_engine(close: np.ndarray, rate_d: np.ndarray, cfg: dict,
               s2p: dict | None, s3p: dict | None, s4p: dict | None,
               sigs: dict, etf_cost: float) -> dict:
    """Stake-tracking day loop. Order within day t (all signals from t-1 / pre-shifted):
    cash interest -> dividend drip -> S2 stake (ret/reset/sweep) -> S3 stake -> S4 P&L ->
    A3 greed-trim -> fear deployment -> NAV. Sleeve rets already contain option costs;
    etf_cost applies to engine-level base trades (initial buy, fear deploy/unwind, trim)."""
    n = len(close)
    div_d = DIV_NET_YR / TD
    w_base, w_s2, w_s3 = cfg["w_base"], cfg["w_s2"], cfg["w_s3"]
    cash = 1.0 - w_base
    units = (w_base * (1.0 - etf_cost) / close[0]) if w_base > 0 else 0.0
    extra = 0.0            # fear-deployed extra base units (A/A3)
    s2s = s3s = 0.0        # sleeve stakes ($ of NAV-unit scale)
    s4not = 0.0            # open covered-call notional
    deployed = trimmed = False
    ledger = 0.0           # A3 trim proceeds awaiting re-entry
    nav = np.empty(n)
    nav[0] = cash + units * close[0]
    bw = np.zeros(n); w2 = np.zeros(n); w3 = np.zeros(n); s4l = np.zeros(n, dtype=bool)
    bw[0] = units * close[0] / nav[0]
    to = 0.0               # engine-level |flows| / NAV (rebalances, deploys, trims, sweeps)
    forgone = 0.0          # interest the committed S3 collateral did NOT earn (telemetry)
    nde = ntr = 0
    dep_days = 0
    q2p = sigs["quad2_prev"]; vxp = sigs["vix_prev"]; fgp = sigs["fg_prev"]

    for t in range(1, n):
        cash *= 1.0 + rate_d[t] / TD
        units *= 1.0 + div_d
        extra *= 1.0 + div_d
        c = close[t]

        if s2p is not None and w_s2 > 0:
            i2, r2_, rs2 = s2p["in_pos"], s2p["ret"], s2p["reset"]
            if i2[t]:
                if rs2[t]:
                    fresh = not bool(i2[t - 1])
                    prev_val = s2s
                    if s2s > 0:
                        s2s *= 1.0 + r2_[t]
                        cash += s2s
                        s2s = 0.0
                    navnow = cash + (units + extra) * c + s3s
                    tgt = max(min(w_s2 * navnow, cash), 0.0)
                    to += abs(tgt - prev_val) / navnow
                    s2s = tgt
                    cash -= tgt
                    if fresh:
                        s2s *= 1.0 + r2_[t]   # entry-day ret = entry cost (see docstring)
                else:
                    s2s *= 1.0 + r2_[t]
            elif i2[t - 1]:
                s2s *= 1.0 + r2_[t]           # exit-day move + exit cost, THEN sweep
                cash += s2s
                to += s2s / max(cash + (units + extra) * c + s3s, 1e-9)
                s2s = 0.0

        if s3p is not None and w_s3 > 0:
            i3, r3_, rs3 = s3p["in_pos"], s3p["ret"], s3p["reset"]
            if i3[t]:
                if rs3[t]:
                    navnow = cash + (units + extra) * c + s2s
                    tgt = max(min(w_s3 * navnow, cash), 0.0)
                    to += tgt / navnow
                    s3s = tgt
                    cash -= tgt
                    s3s *= 1.0 + r3_[t]
                else:
                    s3s *= 1.0 + r3_[t]
            elif i3[t - 1]:
                s3s *= 1.0 + r3_[t]
                cash += s3s
                to += s3s / max(cash + (units + extra) * c + s2s, 1e-9)
                s3s = 0.0
            forgone += s3s * rate_d[t] / TD

        if s4p is not None:
            i4 = s4p["in_pos"]
            if i4[t] or i4[t - 1]:
                cash += s4not * s4p["dnav"][t]
            if i4[t] and not i4[t - 1]:
                s4not = 0.5 * (units + extra) * c   # <=50%-of-base cap, taken at the cap
            s4l[t] = bool(i4[t])

        if cfg["trim"]:
            f = fgp[t]
            if (not trimmed) and (not math.isnan(f)) and f > 80 and units > 0:
                navnow = cash + (units + extra) * c + s2s + s3s
                amt = min(0.20 * navnow, units * c)
                units -= amt / c
                rec = amt * (1.0 - etf_cost)
                cash += rec
                ledger = rec
                trimmed = True
                ntr += 1
                to += amt / navnow
            elif trimmed and (not math.isnan(f)) and f < 55:
                navnow = cash + (units + extra) * c + s2s + s3s
                amt = min(ledger, cash)
                units += amt * (1.0 - etf_cost) / c
                cash -= amt
                trimmed = False
                to += amt / navnow

        if cfg["fear_s1"]:
            if (not deployed) and bool(q2p[t]):
                navnow = cash + (units + extra) * c + s2s + s3s
                amt = min(0.10 * navnow, cash)
                if amt > 1e-12:
                    extra += amt * (1.0 - etf_cost) / c
                    cash -= amt
                    deployed = True
                    nde += 1
                    to += amt / navnow
            elif deployed and (not math.isnan(vxp[t])) and vxp[t] < 18:
                navnow = cash + (units + extra) * c + s2s + s3s
                val = extra * c
                cash += val * (1.0 - etf_cost)
                extra = 0.0
                deployed = False
                to += val / navnow
            if deployed:
                dep_days += 1

        nav[t] = cash + (units + extra) * c + s2s + s3s
        bw[t] = (units + extra) * c / nav[t]
        w2[t] = s2s / nav[t]
        w3[t] = s3s / nav[t]

    ret = np.zeros(n)
    ret[0] = nav[0] - 1.0
    ret[1:] = nav[1:] / nav[:-1] - 1.0
    years = (n - 1) / TD
    return {"nav": nav, "ret": ret, "base_w": bw, "s2_w": w2, "s3_w": w3, "s4_live": s4l,
            "turnover_yr": to / years, "n_deploys": nde, "dep_days": dep_days,
            "n_trims": ntr, "forgone_carry_ppyr": forgone / years * 100}


# ---------------------------------------------------------------- metrics
def worst63(nav_slice: np.ndarray) -> float:
    nv = np.asarray(nav_slice, float)
    nv = nv[~np.isnan(nv)]
    if len(nv) < 64:
        return float("nan")
    r = nv[63:] / nv[:-63] - 1.0
    return float(r.min())


def metrics_row(nav, ret, bh_r, mask):
    nv = rebase_nav(nav[mask])
    rt = ret[mask]
    bh = bh_r[mask]
    a, b, t_ = jensen_alpha(rt, bh)
    ex = rt - bh
    te = float(np.nanstd(ex, ddof=1) * math.sqrt(TD))
    return {"cagr": cagr(nv), "sh": ann_sharpe(rt), "dd": max_drawdown(nv), "a": a,
            "beta": b, "t": t_, "te": te, "w63": worst63(nv)}


def prow(wname, label, m):
    print(f"  [{wname:14}] {label:24} CAGR {m['cagr']*100:+7.2f}%  Sh {m['sh']:5.2f}  "
          f"DD {m['dd']*100:6.1f}%  a {m['a']*100:+6.2f}%(t{m['t']:+5.1f})  b {m['beta']:4.2f}  "
          f"TE {m['te']*100:5.1f}%  W63 {m['w63']*100:6.1f}%")


# ---------------------------------------------------------------- main
CFGS = [
    ("ARCH-A",  dict(w_base=0.75, w_s2=0.10, w_s3=0.00, s4=True,  fear_s1=True,  trim=False, s3src=None)),
    ("ARCH-A2", dict(w_base=0.75, w_s2=0.10, w_s3=0.10, s4=True,  fear_s1=False, trim=False, s3src="quad2")),
    ("ARCH-A3", dict(w_base=0.75, w_s2=0.10, w_s3=0.00, s4=True,  fear_s1=True,  trim=True,  s3src=None)),
    ("ARCH-B",  dict(w_base=0.00, w_s2=0.15, w_s3=0.30, s4=False, fear_s1=False, trim=False, s3src="quad2")),
    ("ARCH-C",  dict(w_base=0.85, w_s2=0.10, w_s3=0.00, s4=False, fear_s1=False, trim=False, s3src=None)),
]


def main():
    close_s = load_spy_close()
    close = close_s.values
    idx = close_s.index
    n = len(close)
    fg = load_fear_greed()
    print(f"LOOP 2 | SPY {idx.min().date()} -> {idx.max().date()}, {n} days | F&G rows {len(fg)}")

    rate_pw = piecewise_rate(idx)
    print("Piecewise cash rate eras: " + " | ".join(f"{a}-{b}:{v*100:.1f}%" for a, b, v in RATE_ERAS)
          + f"  (sample mean {rate_pw.mean()*100:.2f}%/yr; BSM pricing r stays 0.03 as loop 1)")

    # --- signals ---
    sma200 = sma(close_s, 200)
    above_raw = (close_s > sma200).values
    vx = vix_proxy(close_s).values
    quad2_raw = above_raw & (vx > 28)
    valid = (~np.isnan(vx)) & (~np.isnan(sma200.values))
    qlab = np.where(~valid, "NA",
           np.where(above_raw & (vx > 28), "Q2",
           np.where(above_raw, "Q1",
           np.where(vx > 28, "Q3", "Q4"))))
    qdays = {q: int((qlab == q).sum()) for q in ["Q1", "Q2", "Q3", "Q4", "NA"]}
    print(f"Quadrant days: {qdays}  (Q2 = brief's quadrant-2: >200SMA & VIXproxy>28)")

    fga = fg.reindex(idx).ffill().values.astype(float)
    quad2_prev = np.zeros(n, dtype=bool); quad2_prev[1:] = quad2_raw[:-1]
    vix_prev = np.full(n, np.nan); vix_prev[1:] = vx[:-1]
    fg_prev = np.full(n, np.nan); fg_prev[1:] = fga[:-1]
    sigs = {"quad2_prev": quad2_prev, "vix_prev": vix_prev, "fg_prev": fg_prev}

    # --- gates: raw (loop-1) + hysteresis variant ---
    gate_raw, hold_raw, ent_raw, ex_raw = build_hold(close_s, hysteresis=False)
    gate_hys, hold_hys, ent_hys, ex_hys = build_hold(close_s, hysteresis=True)
    lab_gates = build_gates(close_s)
    assert np.array_equal(gate_raw, lab_gates["gated_dip_leap"].values), "raw gate != lab build_gates"
    rsi_ob_gate = lab_gates["rsi2_ob_entry"].values
    quad2_gate_nb = np.zeros(n, dtype=bool); quad2_gate_nb[1:] = quad2_raw[:-1]  # next-bar CSP entry gate

    # --- sleeve sims: S2 x {raw,hyst} x {cost,0} ; quad2-CSP x {cost,0} ; S4 x {cost,0} ---
    iv1y = iv_proxy_1y(close_s).values
    ivsh = iv_proxy_short_dte(close_s).values
    big_shares = np.full(n, 1e9)  # S4 coverage enforced at ENGINE sizing (0.5*base), sleeve = P&L timeline
    S2 = {}
    for gname, garr in [("raw", gate_raw), ("hyst", gate_hys)]:
        for cost in (OPT_COST_SIDE, 0.0):
            S2[(gname, cost)] = sim_s2_leap(close, iv1y, garr, cost_pct=cost)
    S3Q = {cost: sim_s3_csp(close, ivsh, quad2_gate_nb, cost_pct=cost,
                            assign_slip=(ETF_COST_SIDE if cost > 0 else 0.0))
           for cost in (OPT_COST_SIDE, 0.0)}
    S4_ = {cost: sim_s4_short_call(close, ivsh, rsi_ob_gate, big_shares, cost_pct=cost)
           for cost in (OPT_COST_SIDE, 0.0)}

    def s2pack(g, c):
        s = S2[(g, c)]
        return {"ret": s["ret"], "in_pos": s["in_pos"], "reset": (s["entered"] | s["rolled"])}

    def s3pack(c):
        s = S3Q[c]
        return {"ret": s["ret"], "in_pos": s["in_pos"], "reset": entry_flips(s["in_pos"])}

    def s4pack(c):
        s = S4_[c]
        dnav = np.zeros(n); dnav[1:] = np.diff(s["nav"])
        return {"dnav": dnav, "in_pos": s["in_pos"]}

    # --- benchmark + regression checks vs loop-1 cache ---
    bh_nav, bh_ret = spy_bh_total_return(close)
    print(f"\n{'='*110}\n0. SANITY / REGRESSION CHECKS vs loop-1\n{'='*110}")
    cache_f = os.path.join(CACHE_DIR, "sleeve_returns_loop1.npz")
    if os.path.exists(cache_f):
        c1 = np.load(cache_f, allow_pickle=True)
        ok_gate = np.array_equal(gate_raw, c1["gated_dip"])
        ok_s2 = np.allclose(S2[("raw", OPT_COST_SIDE)]["ret"], c1["s2_ret"], atol=1e-12)
        ok_bh = np.allclose(bh_ret, c1["bh_ret"], atol=1e-12)
        print(f"  cached-vs-rebuilt: raw gate identical={ok_gate}  s2_ret identical={ok_s2}  bh identical={ok_bh}")
        assert ok_gate and ok_s2 and ok_bh
    else:
        print("  loop-1 cache absent -> regenerated sims are the source of truth this run")

    base_cfg = dict(w_base=1.0, w_s2=0.0, w_s3=0.0, s4=False, fear_s1=False, trim=False, s3src=None)
    s1_100 = run_engine(close, rate_pw, base_cfg, None, None, None, sigs, ETF_COST_SIDE)
    ratio = s1_100["nav"][-1] / (np.cumprod(1.0 + (np.diff(close) / close[:-1] + DIV_NET_YR / TD))[-1] * (1 - ETF_COST_SIDE))
    print(f"  engine 100%S1 vs analytic drip NAV final ratio: {ratio:.6f} (multiplicative-vs-additive drip cross-term)")

    s2only_cfg = dict(w_base=0.0, w_s2=0.10, w_s3=0.0, s4=False, fear_s1=False, trim=False, s3src=None)
    chk = run_engine(close, np.full(n, 0.03), s2only_cfg, s2pack("raw", OPT_COST_SIDE), None, None, sigs, ETF_COST_SIDE)
    a_c, _, t_c = jensen_alpha(chk["ret"], bh_ret)
    print(f"  engine S2@10%/cash3% (exit-day ret now applied): CAGR {cagr(chk['nav'])*100:.2f}%  "
          f"Sh {ann_sharpe(chk['ret']):.2f}  a {a_c*100:+.2f}%(t{t_c:+.1f})  "
          f"[loop-1 combiner: 6.85%/0.93/+4.61 — small gap = the exit-day fix, direction as expected]")

    # ------------------------------------------------------------ whipsaw audit
    print(f"\n{'='*110}\n1. WHIPSAW AUDIT — S2 200SMA gate: raw vs hysteresis (exit only if close<0.98*200SMA 5 consecutive days)\n{'='*110}")
    years = (n - 1) / TD
    for gname, hold, ne, nx in [("raw", hold_raw, ent_raw, ex_raw), ("hyst", hold_hys, ent_hys, ex_hys)]:
        spells = []
        run = 0
        for v in hold:
            if v:
                run += 1
            elif run:
                spells.append(run); run = 0
        if run:
            spells.append(run)
        s2c = S2[(gname, OPT_COST_SIDE)]
        print(f"  [{gname:4}] gate entries {ne} ({ne/years:.2f}/yr)  exits {nx} ({nx/years:.2f}/yr)  "
              f"hold {hold.mean()*100:5.1f}% of days  avg spell {np.mean(spells):6.1f}d  "
              f"| sleeve: entries {s2c['n_entries']}  rolls {s2c['n_rolls']}")
    for gname in ("raw", "hyst"):
        p_c = run_engine(close, rate_pw, s2only_cfg, s2pack(gname, OPT_COST_SIDE), None, None, sigs, ETF_COST_SIDE)
        p_0 = run_engine(close, rate_pw, s2only_cfg, s2pack(gname, 0.0), None, None, sigs, 0.0)
        a_, _, t_ = jensen_alpha(p_c["ret"], bh_ret)
        drag = (cagr(p_0["nav"]) - cagr(p_c["nav"])) * 100
        print(f"  [{gname:4}] S2@10%+cash(piecewise): CAGR {cagr(p_c['nav'])*100:+.2f}%  Sh {ann_sharpe(p_c['ret']):.2f}  "
              f"a {a_*100:+.2f}%(t{t_:+.1f})  totalCostDrag {drag:.2f}pp/yr (incl. rolls; raw-hyst diff = churn cost)")

    # ------------------------------------------------------------ the grid
    print(f"\n{'='*110}\n2. PRE-REGISTERED GRID — piecewise cash rate headline, both S2-gate variants, all windows\n{'='*110}")
    results = {}
    tele = {}
    drags = {}
    for gname in ("raw", "hyst"):
        for cname, c in CFGS:
            cfg = dict(w_base=c["w_base"], w_s2=c["w_s2"], w_s3=c["w_s3"],
                       fear_s1=c["fear_s1"], trim=c["trim"])
            packs_c = (s2pack(gname, OPT_COST_SIDE),
                       s3pack(OPT_COST_SIDE) if c["s3src"] else None,
                       s4pack(OPT_COST_SIDE) if c["s4"] else None)
            packs_0 = (s2pack(gname, 0.0),
                       s3pack(0.0) if c["s3src"] else None,
                       s4pack(0.0) if c["s4"] else None)
            out = run_engine(close, rate_pw, cfg, *packs_c, sigs, ETF_COST_SIDE)
            out0 = run_engine(close, rate_pw, cfg, *packs_0, sigs, 0.0)
            results[(cname, gname)] = out
            drags[(cname, gname)] = (cagr(out0["nav"]) - cagr(out["nav"])) * 100
            tele[(cname, gname)] = out

    mask_by_w = {wname: window_mask(idx, ws, we) for wname, ws, we in WINDOWS}
    print("\n--- baselines (gate-independent) ---")
    for wname, ws, we in WINDOWS:
        mask = mask_by_w[wname]
        prow(wname, "SPY B&H TR-net", metrics_row(bh_nav, bh_ret, bh_ret, mask))
        prow(wname, "100% S1", metrics_row(s1_100["nav"], s1_100["ret"], bh_ret, mask))
    for gname in ("raw", "hyst"):
        print(f"\n--- S2 gate = {gname.upper()} ---")
        for cname, c in CFGS:
            out = results[(cname, gname)]
            for wname, ws, we in WINDOWS:
                prow(wname, f"{cname} [{gname}]", metrics_row(out["nav"], out["ret"], bh_ret, mask_by_w[wname]))
            ex_line = (f"      expo: base {out['base_w'].mean()*100:5.1f}%  s2 {out['s2_w'].mean()*100:4.1f}%  "
                       f"s3 {out['s3_w'].mean()*100:4.1f}%  s4live {out['s4_live'].mean()*100:4.1f}%  "
                       f"| turnover {out['turnover_yr']:.2f}x/yr  costDrag {drags[(cname, gname)]:.2f}pp/yr")
            if c["fear_s1"]:
                ex_line += f"  | fear-deploys {out['n_deploys']} ({out['dep_days']}d total)"
            if c["trim"]:
                ex_line += f"  trims {out['n_trims']}"
            if c["s3src"]:
                ex_line += f"  | S3 forgone collateral carry ~{out['forgone_carry_ppyr']:.2f}pp/yr (see docstring)"
            print(ex_line)

    # ------------------------------------------------------------ per-quadrant attribution
    print(f"\n{'='*110}\n3. PER-QUADRANT ATTRIBUTION — arithmetic daily excess (config - SPY TR) summed per quadrant, pp/yr of the FULL sample\n{'='*110}")
    print("   (arithmetic contributions add up to total annualized arithmetic excess, NOT the CAGR gap — geometric compounding differs)")
    yrs_full = n / TD
    print(f"   quadrant day-shares: " + "  ".join(f"{q} {qdays[q]/n*100:4.1f}%" for q in ["Q1", "Q2", "Q3", "Q4", "NA"]))
    hdr = f"   {'config':22} " + "".join(f"{q:>9}" for q in ["Q1", "Q2", "Q3", "Q4", "NA"]) + f"{'TOTAL':>9}"
    print(hdr)
    att_rows = [("100% S1", s1_100, "-")] + [(f"{cn} [{g}]", results[(cn, g)], g)
                                             for g in ("raw", "hyst") for cn, _ in CFGS]
    for label, out, _ in att_rows:
        ex = out["ret"] - bh_ret
        vals = [float(np.nansum(ex[qlab == q]) / yrs_full * 100) for q in ["Q1", "Q2", "Q3", "Q4", "NA"]]
        print(f"   {label:22} " + "".join(f"{v:+9.2f}" for v in vals) + f"{sum(vals):+9.2f}")

    # ------------------------------------------------------------ 0%-rate sensitivity, top-2
    print(f"\n{'='*110}\n4. 0%-CASH-RATE SENSITIVITY (pessimistic bound) — top-2 configs by FULL Sharpe (piecewise, raw gate)\n{'='*110}")
    full_mask = mask_by_w["FULL 1996-2026"]
    ranking = sorted(((cn, metrics_row(results[(cn, 'raw')]["nav"], results[(cn, 'raw')]["ret"], bh_ret, full_mask)["sh"])
                      for cn, _ in CFGS), key=lambda kv: -kv[1])
    top2 = [ranking[0][0], ranking[1][0]]
    print(f"  ranking by FULL Sharpe (raw): " + ", ".join(f"{k} {v:.2f}" for k, v in ranking) + f" -> top-2 = {top2}")
    rate0 = np.zeros(n)
    for cname in top2:
        c = dict(CFGS)[cname]
        cfg = dict(w_base=c["w_base"], w_s2=c["w_s2"], w_s3=c["w_s3"], fear_s1=c["fear_s1"], trim=c["trim"])
        for gname in ("raw", "hyst"):
            out = run_engine(close, rate0, cfg, s2pack(gname, OPT_COST_SIDE),
                             s3pack(OPT_COST_SIDE) if c["s3src"] else None,
                             s4pack(OPT_COST_SIDE) if c["s4"] else None, sigs, ETF_COST_SIDE)
            for wname, ws, we in WINDOWS:
                prow(wname, f"{cname} [{gname}] 0%", metrics_row(out["nav"], out["ret"], bh_ret, mask_by_w[wname]))

    # ------------------------------------------------------------ cache for loop 3
    save = {"dates_days_since_epoch": idx.values.astype("datetime64[D]").astype(np.int64),
            "close": close, "bh_ret": bh_ret, "bh_nav": bh_nav, "qlab": qlab.astype(str),
            "s1_100_nav": s1_100["nav"], "rate_piecewise": rate_pw}
    for (cname, gname), out in results.items():
        save[f"{cname}_{gname}_nav"] = out["nav"]
    np.savez(os.path.join(CACHE_DIR, "loop2_configs.npz"), **save)
    print(f"\nCached loop-2 config NAVs -> {CACHE_DIR}/loop2_configs.npz")
    print(f"{'='*110}\nDONE loop 2.")


if __name__ == "__main__":
    main()
