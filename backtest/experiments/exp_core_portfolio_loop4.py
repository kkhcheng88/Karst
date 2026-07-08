"""LOOP 4 — pre-registered SIZING grid E1-E4 on the loop-3 winner W1-R1-B0, plus the
operational write-up pack (O1-O5) for the strategy tree / daily playbook.

Skeleton (FROZEN from loop 3, nothing re-tuned): SPY base + gated 0.80D 1y LEAP premium
sleeve (hysteresis gate: entry >200SMA & RSI-2<10 within 5d; exit only if close<0.98x
200SMA for 5 CONSECUTIVE days) + cash at piecewise era rates; R1 annual calendar
rebalance to target weights + option-P&L sweep to BASE at each S2 roll; S4 covered calls
on <=25% of base priced at 0.85x short-DTE IV proxy (21DTE 0.30D, RSI-2>90 next-bar,
50% PT); fear-deploy in quadrant Q2 (SPY>200SMA raw & VIXproxy>28) from cash into extra
S1, unwind at VIXproxy<18. Washout branch REJECTED in loop 3 — absent here.

PRE-REGISTERED GRID (user explicitly allows flexible leverage; this answers "optimal
sizing"; registry trials 28-31; run all, report all, NO other knobs):
  E1 base75 / S2-prem10 / cash15, fear 10pp   (= loop-3 headline W1-R1-B0, rerun anchor)
  E2 base70 / S2-prem15 / cash15, fear 10pp
  E3 base75 / S2-prem10 / cash15, fear 15pp
  E4 base70 / S2-prem15 / cash15, fear 15pp
Report FULL/H1/H2/2016-20/2021+ CAGR/Sharpe/MaxDD/alpha+t/worst-63d + effective market
exposure = delta-notional/NAV percentiles 50/90/max, where delta-notional = (base+fear
shares at delta 1) + S2 stake x sleeve-leverage (lev = delta*S*contracts*100/sleeveNAV,
recorded inside the sleeve sim — telemetry, not a rule change) - S4 short-call
delta-notional (dexp per unit of sold notional). Zero-cost twins give total cost drag.

OPERATIONAL PACK (for the best-FULL-Sharpe config):
  O1 per-year table 1996-2026: strat ret, SPY TR ret, excess, S2 entries/rolls/exits,
     fear deploys/unwinds, S4 trades.
  O2 quadrant occupancy & flips under the HYSTERESIS trend definition (entry >200SMA,
     back to DOWN only after 5 consecutive closes <0.98x200SMA). NOTE (stated, not
     hidden): the IMPLEMENTED fear gate uses the RAW >200SMA compare (loop-2/3 spec);
     raw occupancy printed alongside for reconciliation.
  O4 monthly excess diagnostics: acf(1), skew, kurtosis, worst-5 months + holdings,
     up/down capture vs SPY TR-net.
  O5 alpha decomposition: one-at-a-time ablations (S2 off / S4 off / fear off /
     rebalance+sweep off) — 4 rows, interactions do NOT sum exactly (reported honestly).
  O3 decision-rule table AS IMPLEMENTED: static text, printed at the end of `ops`.

DISCIPLINE: next-bar everywhere (all engine signals pre-shifted to t-1); costs ETF
5bps/side, options 0.5%/side of premium; piecewise cash; BSM r=0.03. Regression anchors:
rebuilt sleeves must equal loop-3's cached arrays; E1's NAV must equal loop-3's cached
W1-R1-B0 NAV to <1e-9 rel. Engine = op-for-op port of loop-3 run_engine3 with the
washout branch deleted (B0: wo_units was identically 0 — arithmetic unchanged) and
FEAR_PP promoted from module constant to cfg["fear_pp"].

Stages (each bash call <40s; caches under /tmp/karst_loop):
    python3 exp_core_portfolio_loop4.py sims   # build+cache sleeves (with lev/dexp telemetry)
    python3 exp_core_portfolio_loop4.py grid   # E1-E4 report + exposure + best pick
    python3 exp_core_portfolio_loop4.py ops    # O1/O2/O4/O5 pack + O3 text
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
    TD, DIV_NET_YR, ETF_COST_SIDE, OPT_COST_SIDE, CACHE_DIR, WINDOWS, R_RATE, Q_YIELD,
    load_spy_close, sma, vix_proxy, iv_proxy_1y, iv_proxy_short_dte, build_gates,
    call_price, call_delta, strike_for_call_delta, spy_bh_total_return, cagr,
    ann_sharpe, jensen_alpha, window_mask,
)
from exp_core_portfolio_loop2 import (  # noqa: E402
    piecewise_rate, build_hold, metrics_row, prow,
)

SLEEVE_CACHE4 = os.path.join(CACHE_DIR, "loop4_sleeves.npz")
S4_FRAC = 0.25
S4_IV_HAIRCUT = 0.85
BAND = 0.10  # R2 band (kept for engine fidelity; grid uses R1 only)

# (name, w_base, w_s2, fear_pp) — cash is the residual 15% in all four
GRID = [("E1", 0.75, 0.10, 0.10), ("E2", 0.70, 0.15, 0.10),
        ("E3", 0.75, 0.10, 0.15), ("E4", 0.70, 0.15, 0.15)]


# ============================================================================
# sleeve sims with exposure telemetry (arithmetic identical to lab versions;
# regression-checked against loop-3's cached ret/dnav arrays in stage `sims`)
# ============================================================================

def sim_s2_leap_lev(close, iv, gate, target_delta=0.80, dte_init=TD, roll_dte=63,
                    r=R_RATE, q=Q_YIELD, cost_pct=OPT_COST_SIDE) -> dict:
    """lab.sim_s2_leap + lev[i] = delta*S*contracts*100 / sleeveNAV (delta-notional per
    $1 of sleeve stake; 0 when out of position). No behavior change."""
    n = len(close)
    nav = np.full(n, np.nan)
    lev = np.zeros(n)
    in_pos_arr = np.zeros(n, dtype=bool)
    rolled_arr = np.zeros(n, dtype=bool)
    entered_arr = np.zeros(n, dtype=bool)
    cash = 1.0
    contracts = 0.0
    K = None
    dte = 0
    in_pos = False
    for i in range(n):
        if in_pos and i > 0:
            dte -= 1
        S = close[i]
        sig = max(iv[i], 1e-4) if not math.isnan(iv[i]) else 0.15
        allowed = bool(gate[i])
        if in_pos and ((not allowed) or dte <= roll_dte):
            T_rem = max(dte / TD, 1e-6)
            opt = call_price(S, K, T_rem, r, q, sig)
            cash += contracts * opt * 100 * (1 - cost_pct)
            if (dte <= roll_dte) and allowed:
                rolled_arr[i] = True
            contracts, in_pos = 0.0, False
        if (not in_pos) and allowed and cash > 0:
            T = dte_init / TD
            K = strike_for_call_delta(S, T, r, q, sig, target_delta)
            price = call_price(S, K, T, r, q, sig)
            if price > 0:
                contracts = cash / (price * 100 * (1 + cost_pct))
                cash = 0.0
                dte = dte_init
                in_pos = True
                entered_arr[i] = True
        if in_pos:
            T_rem = max(dte / TD, 1e-6)
            opt = call_price(S, K, T_rem, r, q, sig)
            nav[i] = cash + contracts * opt * 100
            if nav[i] > 0:
                lev[i] = contracts * 100 * call_delta(S, K, T_rem, r, q, sig) * S / nav[i]
            in_pos_arr[i] = True
        else:
            nav[i] = cash
    ret = np.zeros(n)
    valid = ~np.isnan(nav)
    vidx = np.where(valid)[0]
    for k in range(1, len(vidx)):
        i0, i1 = vidx[k - 1], vidx[k]
        if i1 == i0 + 1 and nav[i0] > 0:
            ret[i1] = nav[i1] / nav[i0] - 1
    return {"ret": ret, "in_pos": in_pos_arr, "entered": entered_arr,
            "rolled": rolled_arr, "lev": lev}


def sim_s4_short_call_dexp(close, iv, entry_gate, base_shares, target_delta=0.30,
                           dte_init=21, pt=0.50, r=R_RATE, q=Q_YIELD,
                           cost_pct=OPT_COST_SIDE) -> dict:
    """lab.sim_s4_short_call + dexp[i] = delta*S*contracts*100 (short-call delta-notional
    per 1.0 unit of sold notional; 0 when flat). No behavior change."""
    n = len(close)
    nav = np.full(n, np.nan)
    dexp = np.zeros(n)
    realized = 0.0
    in_pos = False
    in_pos_arr = np.zeros(n, dtype=bool)
    K = prem = 0.0
    dte = 0
    contracts = 0.0
    n_entries = 0
    for i in range(n):
        S = close[i]
        sig = max(iv[i], 1e-4) if not math.isnan(iv[i]) else 0.15
        if in_pos:
            dte -= 1
            if dte <= 0:
                intrinsic = max(S - K, 0.0)
                realized += contracts * (prem - intrinsic) * 100 - contracts * 100 * (prem + intrinsic) * cost_pct
                in_pos = False
                contracts = 0.0
            else:
                V = call_price(S, K, max(dte / TD, 1e-6), r, q, sig)
                if pt is not None and V <= pt * prem:
                    realized += contracts * (prem - V) * 100 - contracts * 100 * (prem + V) * cost_pct
                    in_pos = False
                    contracts = 0.0
        covered = (base_shares[i] >= 100.0) if not math.isnan(base_shares[i]) else False
        if (not in_pos) and bool(entry_gate[i]) and covered and S > 0:
            T = dte_init / TD
            K = strike_for_call_delta(S, T, r, q, sig, target_delta)
            prem = call_price(S, K, T, r, q, sig)
            if prem > 0 and K > 0:
                contracts = 1.0 / (S * 100)
                dte = dte_init
                in_pos = True
                n_entries += 1
        if in_pos:
            T_rem = max(dte / TD, 1e-6)
            V = call_price(S, K, T_rem, r, q, sig)
            unreal = contracts * (prem - V) * 100
            dexp[i] = call_delta(S, K, T_rem, r, q, sig) * contracts * 100 * S
        else:
            unreal = 0.0
        nav[i] = 1.0 + realized + unreal
        in_pos_arr[i] = in_pos
    return {"nav": nav, "in_pos": in_pos_arr, "dexp": dexp, "n_entries": n_entries}


def build_sleeves4(close_s: pd.Series) -> dict:
    close = close_s.values
    n = len(close)
    if os.path.exists(SLEEVE_CACHE4):
        z = np.load(SLEEVE_CACHE4)
        if len(z["close"]) == n and np.allclose(z["close"], close):
            return {k: z[k] for k in z.files}
    iv1y = iv_proxy_1y(close_s).values
    ivsh_hc = iv_proxy_short_dte(close_s).values * S4_IV_HAIRCUT
    gate_hys, _, _, _ = build_hold(close_s, hysteresis=True)
    rsi_ob = build_gates(close_s)["rsi2_ob_entry"].values
    big = np.full(n, 1e9)  # coverage enforced at ENGINE sizing (loop-2/3 convention)
    out = {"close": close}
    for cp, tag in [(OPT_COST_SIDE, "05"), (0.0, "00")]:
        s2 = sim_s2_leap_lev(close, iv1y, gate_hys, cost_pct=cp)
        out[f"s2_{tag}_ret"] = s2["ret"]
        out[f"s2_{tag}_inpos"] = s2["in_pos"]
        out[f"s2_{tag}_entered"] = s2["entered"]
        out[f"s2_{tag}_rolled"] = s2["rolled"]
        out[f"s2_{tag}_lev"] = s2["lev"]
        s4 = sim_s4_short_call_dexp(close, ivsh_hc, rsi_ob, big, cost_pct=cp)
        dnav = np.zeros(n)
        dnav[1:] = np.diff(s4["nav"])
        out[f"s4_{tag}_dnav"] = dnav
        out[f"s4_{tag}_inpos"] = s4["in_pos"]
        out[f"s4_{tag}_dexp"] = s4["dexp"]
    np.savez(SLEEVE_CACHE4, **out)
    return out


def s2pack4(sl: dict, tag: str) -> dict:
    return {"ret": sl[f"s2_{tag}_ret"], "in_pos": sl[f"s2_{tag}_inpos"],
            "reset": sl[f"s2_{tag}_entered"] | sl[f"s2_{tag}_rolled"],
            "entered": sl[f"s2_{tag}_entered"], "rolled": sl[f"s2_{tag}_rolled"],
            "lev": sl[f"s2_{tag}_lev"]}


def s4pack4(sl: dict, tag: str) -> dict:
    return {"dnav": sl[f"s4_{tag}_dnav"], "in_pos": sl[f"s4_{tag}_inpos"],
            "dexp": sl[f"s4_{tag}_dexp"]}


# ============================================================================
# engine — op-for-op port of loop-3 run_engine3 (washout branch deleted; B0 meant
# wo_units==0 everywhere, so arithmetic is unchanged) + cfg["fear_pp"] + telemetry:
# daily delta-notional exposure, cash/extra weights, fear/reb/sweep event logs.
# ============================================================================

def run_engine4(close, yr, rate_d, cfg, s2p, s4p, sigs, etf_cost, opt_cost) -> dict:
    n = len(close)
    div_d = DIV_NET_YR / TD
    w_base, w_s2 = cfg["w_base"], cfg["w_s2"]
    fear_pp = cfg.get("fear_pp", 0.10)
    sweep = cfg.get("sweep", False)
    reb = cfg.get("reb")
    s4_frac = cfg.get("s4_frac", 0.0)
    fear = cfg.get("fear", False)

    cash = 1.0 - w_base
    units = (w_base * (1.0 - etf_cost) / close[0]) if w_base > 0 else 0.0
    extra = 0.0
    s2s = 0.0
    s4not = 0.0
    deployed = False
    pending_band = False
    nav = np.empty(n)
    nav[0] = cash + units * close[0]
    bw = np.zeros(n); w2 = np.zeros(n); cw = np.zeros(n); xw = np.zeros(n)
    expo = np.zeros(n)
    bw[0] = units * close[0] / nav[0]
    cw[0] = cash / nav[0]
    expo[0] = bw[0]
    to = 0.0
    nde = dep_days = n_reb = 0
    fear_log: list[tuple] = []   # (t, 'D'|'U', frac_of_nav)
    sweep_log: list[tuple] = []  # (t, swept_to_base_frac_of_nav)
    reb_log: list[int] = []
    q2p, vxp = sigs["quad2_prev"], sigs["vix_prev"]
    i2 = s2p["in_pos"] if s2p is not None else None
    lev2 = s2p["lev"] if s2p is not None else None
    i4 = s4p["in_pos"] if s4p is not None else None
    dx4 = s4p["dexp"] if s4p is not None else None

    for t in range(1, n):
        cash *= 1.0 + rate_d[t] / TD
        units *= 1.0 + div_d
        extra *= 1.0 + div_d
        c = close[t]

        # ---- S2 LEAP stake ----
        if s2p is not None and w_s2 > 0:
            r2_, rs2 = s2p["ret"], s2p["reset"]
            if i2[t]:
                if rs2[t]:
                    fresh = not bool(i2[t - 1])
                    prev_val = s2s
                    if not sweep:
                        if s2s > 0:
                            s2s *= 1.0 + r2_[t]
                            cash += s2s
                            s2s = 0.0
                        navnow = cash + (units + extra) * c
                        tgt = max(min(w_s2 * navnow, cash), 0.0)
                        to += abs(tgt - prev_val) / navnow
                        s2s = tgt
                        cash -= tgt
                    else:
                        if s2s > 0:
                            s2s *= 1.0 + r2_[t]
                        proceeds = s2s
                        s2s = 0.0
                        navnow = cash + proceeds + (units + extra) * c
                        tgt = max(w_s2 * navnow, 0.0)
                        if (not fresh) and proceeds >= tgt:
                            s2s = tgt
                            rem = proceeds - tgt
                            units += rem * (1.0 - etf_cost) / c
                            to += (abs(tgt - prev_val) + rem) / navnow
                            sweep_log.append((t, rem / navnow))
                        else:
                            add = min(max(tgt - proceeds, 0.0), cash)
                            s2s = proceeds + add
                            cash -= add
                            to += abs(s2s - prev_val) / navnow
                    if fresh:
                        s2s *= 1.0 + r2_[t]
                else:
                    s2s *= 1.0 + r2_[t]
            elif i2[t - 1]:
                s2s *= 1.0 + r2_[t]
                cash += s2s
                to += s2s / max(cash + (units + extra) * c, 1e-9)
                s2s = 0.0

        # ---- S4 covered-call overlay ----
        if s4p is not None and s4_frac > 0:
            if i4[t] or i4[t - 1]:
                cash += s4not * s4p["dnav"][t]
            if i4[t] and not i4[t - 1]:
                s4not = s4_frac * (units + extra) * c

        # ---- fear deploy ----
        if fear:
            if (not deployed) and bool(q2p[t]):
                navnow = cash + (units + extra) * c + s2s
                amt = min(fear_pp * navnow, cash)
                if amt > 1e-12:
                    extra += amt * (1.0 - etf_cost) / c
                    cash -= amt
                    deployed = True
                    nde += 1
                    to += amt / navnow
                    fear_log.append((t, "D", amt / navnow))
            elif deployed and (not math.isnan(vxp[t])) and vxp[t] < 18:
                navnow = cash + (units + extra) * c + s2s
                val = extra * c
                cash += val * (1.0 - etf_cost)
                extra = 0.0
                deployed = False
                to += val / navnow
                fear_log.append((t, "U", val / navnow))
            if deployed:
                dep_days += 1

        # ---- R1/R2 rebalance ----
        if reb is not None:
            do_reb = (yr[t] != yr[t - 1]) if reb == "R1" else pending_band
            if do_reb:
                navnow = cash + (units + extra) * c + s2s
                if s2p is not None and w_s2 > 0 and i2[t] and s2s > 0:
                    d2 = w_s2 * navnow - s2s
                    if d2 > 0:
                        add = min(d2, cash)
                        cash -= add
                        s2s += add * (1.0 - opt_cost)
                        to += add / navnow
                    elif d2 < 0:
                        s2s += d2
                        cash += (-d2) * (1.0 - opt_cost)
                        to += (-d2) / navnow
                db = w_base * navnow - units * c
                if db > 0:
                    buy = min(db, cash)
                    units += buy * (1.0 - etf_cost) / c
                    cash -= buy
                    to += buy / navnow
                elif db < 0:
                    units -= (-db) / c
                    cash += (-db) * (1.0 - etf_cost)
                    to += (-db) / navnow
                n_reb += 1
                reb_log.append(t)
            if reb == "R2":
                nav_t = cash + (units + extra) * c + s2s
                dev = abs(units * c / nav_t - w_base) > BAND
                if (not dev) and s2p is not None and i2[t] and s2s > 0:
                    dev = abs(s2s / nav_t - w_s2) > BAND
                pending_band = dev and not do_reb

        nav[t] = cash + (units + extra) * c + s2s
        bw[t] = units * c / nav[t]
        w2[t] = s2s / nav[t]
        cw[t] = cash / nav[t]
        xw[t] = extra * c / nav[t]
        e = (units + extra) * c
        if s2p is not None and s2s > 0:
            e += s2s * lev2[t]
        if s4p is not None and s4_frac > 0 and i4[t]:
            e -= s4not * dx4[t]
        expo[t] = e / nav[t]

    ret = np.zeros(n)
    ret[0] = nav[0] - 1.0
    ret[1:] = nav[1:] / nav[:-1] - 1.0
    years = (n - 1) / TD
    return {"nav": nav, "ret": ret, "base_w": bw, "s2_w": w2, "cash_w": cw,
            "extra_w": xw, "expo": expo, "turnover_yr": to / years, "n_deploys": nde,
            "dep_days": dep_days, "n_reb": n_reb, "fear_log": fear_log,
            "sweep_log": sweep_log, "reb_log": reb_log}


# ============================================================================
# shared setup
# ============================================================================

def load_common():
    close_s = load_spy_close()
    close = close_s.values
    idx = close_s.index
    n = len(close)
    yr = idx.year.values
    sl = build_sleeves4(close_s)
    rate_pw = piecewise_rate(idx)
    sma200 = sma(close_s, 200)
    above_raw = (close_s > sma200).values
    vx = vix_proxy(close_s).values
    quad2_raw = above_raw & (vx > 28)
    quad2_prev = np.zeros(n, dtype=bool); quad2_prev[1:] = quad2_raw[:-1]
    vix_prev = np.full(n, np.nan); vix_prev[1:] = vx[:-1]
    sigs = {"quad2_prev": quad2_prev, "vix_prev": vix_prev}
    bh_nav, bh_ret = spy_bh_total_return(close)
    mask_by_w = {wname: window_mask(idx, ws, we) for wname, ws, we in WINDOWS}
    return dict(close_s=close_s, close=close, idx=idx, n=n, yr=yr, sl=sl,
                rate_pw=rate_pw, sigs=sigs, bh_nav=bh_nav, bh_ret=bh_ret,
                mask_by_w=mask_by_w, vx=vx, above_raw=above_raw,
                smaval=~np.isnan(sma200.values))


def cfg_of(name: str) -> dict:
    wb, ws2, fpp = {k: (a, b, c) for k, a, b, c in GRID}[name]
    return dict(w_base=wb, w_s2=ws2, fear_pp=fpp, s4_frac=S4_FRAC, fear=True,
                reb="R1", sweep=True)


def run_named(name: str, com: dict, zero_cost: bool = False) -> dict:
    tag = "00" if zero_cost else "05"
    ec, oc = (0.0, 0.0) if zero_cost else (ETF_COST_SIDE, OPT_COST_SIDE)
    return run_engine4(com["close"], com["yr"], com["rate_pw"], cfg_of(name),
                       s2pack4(com["sl"], tag), s4pack4(com["sl"], tag), com["sigs"], ec, oc)


def rank_grid(com: dict) -> tuple[str, dict]:
    outs = {name: run_named(name, com) for name, *_ in GRID}
    full = com["mask_by_w"]["FULL 1996-2026"]
    rk = sorted(((k, metrics_row(o["nav"], o["ret"], com["bh_ret"], full)["sh"])
                 for k, o in outs.items()), key=lambda kv: -kv[1])
    return rk[0][0], outs


# ============================================================================
# stages
# ============================================================================

def stage_sims():
    close_s = load_spy_close()
    sl = build_sleeves4(close_s)
    n = len(close_s)
    l3f = os.path.join(CACHE_DIR, "loop3_sleeves.npz")
    if os.path.exists(l3f):
        z3 = np.load(l3f)
        ok2 = np.allclose(sl["s2_05_ret"], z3["s2_hyst_05_ret"], atol=1e-12)
        ok4 = np.allclose(sl["s4_05_dnav"], z3["s4_hc_05_dnav"], atol=1e-12)
        print(f"regression vs loop3 sleeves: s2_hyst_05_ret identical={ok2}  "
              f"s4_hc_05_dnav identical={ok4}")
        assert ok2 and ok4
    else:
        print("loop3 sleeve cache absent — rebuilt sims are source of truth")
    ip = sl["s2_05_inpos"]
    lv = sl["s2_05_lev"][ip]
    print(f"S2 sleeve: in-pos {ip.mean()*100:.1f}% of {n}d, entries {int(sl['s2_05_entered'].sum())}, "
          f"rolls {int(sl['s2_05_rolled'].sum())} | sleeve delta-leverage while in-pos: "
          f"p10 {np.percentile(lv,10):.2f}x med {np.median(lv):.2f}x p90 {np.percentile(lv,90):.2f}x "
          f"max {lv.max():.2f}x")
    i4 = sl["s4_05_inpos"]
    dx = sl["s4_05_dexp"][i4]
    print(f"S4 sleeve: live {i4.mean()*100:.1f}% of days | short-call delta/notional: "
          f"med {np.median(dx):.2f} p90 {np.percentile(dx,90):.2f} max {dx.max():.2f}")
    print(f"cached -> {SLEEVE_CACHE4}")


def expo_stats(expo: np.ndarray) -> str:
    p50, p90 = np.percentile(expo, [50, 90])
    return (f"delta-notional/NAV: mean {expo.mean()*100:5.1f}%  p50 {p50*100:5.1f}%  "
            f"p90 {p90*100:5.1f}%  max {expo.max()*100:5.1f}%")


def stage_grid():
    com = load_common()
    idx, bh_ret, bh_nav = com["idx"], com["bh_ret"], com["bh_nav"]
    print(f"LOOP 4 | SPY {idx.min().date()} -> {idx.max().date()}, {com['n']} days | "
          f"skeleton W1-R1-B0 (hyst gate, R1 annual+sweep, S4<=25% IVx0.85, fear-Q2) | "
          f"piecewise cash mean {com['rate_pw'].mean()*100:.2f}%/yr")
    print(f"grid: " + " | ".join(f"{k}=base{int(a*100)}/S2-{int(b*100)}/fear{int(c*100)}pp"
                                 for k, a, b, c in GRID) + "  (registry trials 28-31)")

    # regression: E1 must reproduce loop-3's cached W1-R1-B0 NAV
    e1 = run_named("E1", com)
    l3f = os.path.join(CACHE_DIR, "loop3_configs.npz")
    if os.path.exists(l3f):
        z3 = np.load(l3f)
        md = float(np.max(np.abs(e1["nav"] / z3["W1-R1-B0_nav"] - 1.0)))
        print(f"\nREGRESSION: E1 vs loop3 W1-R1-B0 NAV max|rel diff| = {md:.2e} "
              f"{'[OK]' if md < 1e-9 else '[!!DIFFERS — engine port broken!!]'}")
        assert md < 1e-9
    else:
        print("\nloop3 config cache absent — E1 stands on its own (no anchor check)")

    print(f"\n--- baselines ---")
    s1_cfg = dict(w_base=1.0, w_s2=0.0, s4_frac=0.0, fear=False, reb=None, sweep=False)
    s1 = run_engine4(com["close"], com["yr"], com["rate_pw"], s1_cfg, None, None,
                     com["sigs"], ETF_COST_SIDE, OPT_COST_SIDE)
    for wname, _, _ in WINDOWS:
        prow(wname, "SPY B&H TR-net", metrics_row(bh_nav, bh_ret, bh_ret, com["mask_by_w"][wname]))
        prow(wname, "100% S1", metrics_row(s1["nav"], s1["ret"], bh_ret, com["mask_by_w"][wname]))

    print(f"\n{'='*110}\nPRE-REGISTERED GRID E1-E4 (all on W1-R1-B0 skeleton)\n{'='*110}")
    outs = {}
    for name, wb, ws2, fpp in GRID:
        out = run_named(name, com)
        out0 = run_named(name, com, zero_cost=True)
        outs[name] = out
        drag = (cagr(out0["nav"]) - cagr(out["nav"])) * 100
        print(f"\n--- {name}: base {wb*100:.0f}% / S2 {ws2*100:.0f}% / cash 15% / fear {fpp*100:.0f}pp ---")
        for wname, _, _ in WINDOWS:
            prow(wname, name, metrics_row(out["nav"], out["ret"], bh_ret, com["mask_by_w"][wname]))
        dep_sz = [f for (_, k, f) in out["fear_log"] if k == "D"]
        print(f"      {expo_stats(out['expo'])}")
        print(f"      baseW mean {out['base_w'].mean()*100:.1f}% final {out['base_w'][-1]*100:.1f}% | "
              f"s2W mean {out['s2_w'].mean()*100:.1f}% | cashW mean {out['cash_w'].mean()*100:.1f}% | "
              f"reb {out['n_reb']} | sweeps-to-base {len(out['sweep_log'])} "
              f"(avg {np.mean([s for _, s in out['sweep_log']])*100:.2f}%NAV) | "
              f"turnover {out['turnover_yr']:.2f}x/yr | costDrag {drag:.2f}pp/yr | "
              f"fear-deploys {out['n_deploys']} ({out['dep_days']}d, avg size {np.mean(dep_sz)*100:.1f}%NAV)")

    full = com["mask_by_w"]["FULL 1996-2026"]
    rk = sorted(((k, metrics_row(o["nav"], o["ret"], bh_ret, full)["sh"]) for k, o in outs.items()),
                key=lambda kv: -kv[1])
    print(f"\nBEST (FULL Sharpe): {rk[0][0]}   [" + ", ".join(f"{k} {v:.3f}" for k, v in rk) + "]")
    save = {"close": com["close"]}
    for k, o in outs.items():
        save[f"{k}_nav"] = o["nav"]
        save[f"{k}_expo"] = o["expo"]
    np.savez(os.path.join(CACHE_DIR, "loop4_configs.npz"), **save)
    print(f"cached -> {CACHE_DIR}/loop4_configs.npz\nDONE grid stage.")


# ---------------------------------------------------------------- ops helpers

def trend_state_hyst(close_s: pd.Series) -> np.ndarray:
    """Hysteresis TREND state (no dip condition): UP when close>200SMA; flips DOWN only
    after 5 consecutive closes <0.98x200SMA; 0 = warmup."""
    sma200 = sma(close_s, 200)
    below = close_s < (0.98 * sma200)
    ex5 = (below.rolling(5, min_periods=5).sum() == 5).fillna(False).values
    above = (close_s > sma200).values
    ok = ~np.isnan(sma200.values)
    n = len(close_s)
    st = np.zeros(n, dtype=int)
    cur = 0
    for i in range(n):
        if not ok[i]:
            continue
        if cur == 0:
            cur = 1 if above[i] else -1
        elif cur == 1:
            if ex5[i]:
                cur = -1
        else:
            if above[i]:
                cur = 1
        st[i] = cur
    return st


def sk_ku(x: np.ndarray) -> tuple[float, float]:
    d = x - x.mean()
    s = d.std(ddof=0)
    return float((d ** 3).mean() / s ** 3), float((d ** 4).mean() / s ** 4 - 3.0)


def stage_ops():
    com = load_common()
    idx, yr, bh_ret, bh_nav = com["idx"], com["yr"], com["bh_ret"], com["bh_nav"]
    n = com["n"]
    best, outs = rank_grid(com)
    out = outs[best]
    sl = com["sl"]
    print(f"OPS PACK for best-FULL-Sharpe config = {best}  "
          f"(cfg: base {cfg_of(best)['w_base']*100:.0f}/S2 {cfg_of(best)['w_s2']*100:.0f}/cash 15, "
          f"fear {cfg_of(best)['fear_pp']*100:.0f}pp)")

    # ---------------- O1: per-year table ----------------
    print(f"\n{'='*110}\nO1. PER-YEAR TABLE — {best} vs SPY TR-net, with alpha-event counts\n{'='*110}")
    ent, rol = sl["s2_05_entered"], sl["s2_05_rolled"]
    ip2 = sl["s2_05_inpos"]
    ex2 = np.zeros(n, dtype=bool); ex2[1:] = ip2[:-1] & ~ip2[1:]
    i4 = sl["s4_05_inpos"]
    e4 = np.zeros(n, dtype=bool); e4[1:] = i4[1:] & ~i4[:-1]; e4[0] = i4[0]
    fdep = np.zeros(n, dtype=int); funw = np.zeros(n, dtype=int)
    for (t, k, f) in out["fear_log"]:
        (fdep if k == "D" else funw)[t] = 1
    years = sorted(set(yr.tolist()))
    ends = {}
    for t in range(n):
        ends[yr[t]] = t
    print(f"  {'year':>4} | {'strat%':>8} {'spy%':>8} {'excess':>8} | "
          f"{'s2ent':>5} {'s2roll':>6} {'s2exit':>6} | {'fearD':>5} {'fearU':>5} | {'s4tr':>4}")
    ylist = []
    for y in years:
        t1 = ends[y]
        nav0 = out["nav"][ends[y - 1]] if (y - 1) in ends else 1.0
        bh0 = bh_nav[ends[y - 1]] if (y - 1) in ends else 1.0
        rs = out["nav"][t1] / nav0 - 1.0
        rb = bh_nav[t1] / bh0 - 1.0
        m = yr == y
        ylist.append((y, rs, rb, rs - rb))
        print(f"  {y:>4} | {rs*100:+8.2f} {rb*100:+8.2f} {(rs-rb)*100:+8.2f} | "
              f"{int(ent[m].sum()):>5} {int(rol[m].sum()):>6} {int(ex2[m].sum()):>6} | "
              f"{int(fdep[m].sum()):>5} {int(funw[m].sum()):>5} | {int(e4[m].sum()):>4}")
    exs = np.array([e for _, _, _, e in ylist])
    pos = int((exs > 0).sum())
    top3 = np.sort(exs)[-3:]
    print(f"  summary: {pos}/{len(exs)} years positive excess | sum of yearly excess "
          f"{exs.sum()*100:+.1f}pp | top-3 years {top3.sum()*100:+.1f}pp "
          f"({top3.sum()/max(exs.sum(),1e-9)*100:.0f}% of sum) | worst year excess {exs.min()*100:+.2f}pp")

    # ---------------- O2: quadrant occupancy & flips (hysteresis trend) ----------------
    print(f"\n{'='*110}\nO2. QUADRANT OCCUPANCY & FLIPS — HYSTERESIS trend x VIX-proxy zones "
          f"(Q1 up/calm, Q2 up/fear>28, Q3 down/fear, Q4 down/calm)\n{'='*110}")
    st = trend_state_hyst(com["close_s"])
    vx = com["vx"]
    lab = np.full(n, "NA", dtype=object)
    okq = (st != 0) & ~np.isnan(vx)
    lab[okq & (st == 1) & (vx <= 28)] = "Q1"
    lab[okq & (st == 1) & (vx > 28)] = "Q2"
    lab[okq & (st == -1) & (vx > 28)] = "Q3"
    lab[okq & (st == -1) & (vx <= 28)] = "Q4"
    nn = int(okq.sum())
    for q in ("Q1", "Q2", "Q3", "Q4"):
        cnt = int((lab == q).sum())
        # longest spell
        best_run, run, r0, best_r0 = 0, 0, 0, 0
        for t in range(n):
            if lab[t] == q:
                if run == 0:
                    r0 = t
                run += 1
                if run > best_run:
                    best_run, best_r0 = run, r0
            else:
                run = 0
        print(f"  {q}: {cnt:5d} days ({cnt/nn*100:5.1f}% of {nn} valid) | longest spell "
              f"{best_run:4d} td  {idx[best_r0].date()} -> {idx[best_r0+best_run-1].date()}")
    chg = np.zeros(n, dtype=bool)
    chg[1:] = (lab[1:] != lab[:-1]) & (lab[1:] != "NA") & (lab[:-1] != "NA")
    per_yr = [int(chg[yr == y].sum()) for y in years]
    print(f"  quadrant flips: total {int(chg.sum())} | per-year mean {np.mean(per_yr):.1f} "
          f"max {max(per_yr)} (in {years[int(np.argmax(per_yr))]})")
    # raw-trend reconciliation (the IMPLEMENTED fear gate uses raw >200SMA)
    lab_r = np.full(n, "NA", dtype=object)
    okr = com["smaval"] & ~np.isnan(vx)
    ar = com["above_raw"]
    lab_r[okr & ar & (vx <= 28)] = "Q1"; lab_r[okr & ar & (vx > 28)] = "Q2"
    lab_r[okr & ~ar & (vx > 28)] = "Q3"; lab_r[okr & ~ar & (vx <= 28)] = "Q4"
    chg_r = np.zeros(n, dtype=bool)
    chg_r[1:] = (lab_r[1:] != lab_r[:-1]) & (lab_r[1:] != "NA") & (lab_r[:-1] != "NA")
    cnts = {q: int((lab_r == q).sum()) for q in ("Q1", "Q2", "Q3", "Q4")}
    print(f"  [raw-trend recon — as the fear gate is implemented] days {cnts} | flips {int(chg_r.sum())} "
          f"({int(chg_r.sum())/len(years):.1f}/yr) — hysteresis cuts trend whipsaw; fear gate itself "
          f"fires on RAW Q2 entry + VIX<18 unwind (one deploy per episode)")

    # ---------------- O4: monthly excess diagnostics ----------------
    print(f"\n{'='*110}\nO4. MONTHLY EXCESS DIAGNOSTICS — {best} vs SPY TR-net\n{'='*110}")
    sm = (1.0 + pd.Series(out["ret"], index=idx)).resample("ME").prod() - 1.0
    bm = (1.0 + pd.Series(bh_ret, index=idx)).resample("ME").prod() - 1.0
    exm = (sm - bm).dropna()
    x = exm.values
    ac1 = float(np.corrcoef(x[:-1], x[1:])[0, 1])
    skw, kur = sk_ku(x)
    up = bm > 0
    upcap = float(sm[up].mean() / bm[up].mean())
    dncap = float(sm[~up].mean() / bm[~up].mean())
    print(f"  N={len(x)} months | mean {x.mean()*100:+.2f}%/mo | std {x.std(ddof=1)*100:.2f}% | "
          f"acf(1) {ac1:+.2f} | skew {skw:+.2f} | ex-kurt {kur:+.2f}")
    print(f"  up-capture {upcap*100:.1f}%  down-capture {dncap*100:.1f}%  "
          f"(monthly mean-ratio vs SPY TR-net)")
    print(f"  worst-5 excess months (what the portfolio held, month-avg):")
    worst = exm.nsmallest(5)
    for dt, e in worst.items():
        m = (idx.year == dt.year) & (idx.month == dt.month)
        print(f"    {dt.strftime('%Y-%m')}  excess {e*100:+6.2f}%  (strat {sm[dt]*100:+6.2f}% vs spy "
              f"{bm[dt]*100:+6.2f}%) | base {out['base_w'][m].mean()*100:4.1f}%  "
              f"S2 {out['s2_w'][m].mean()*100:4.1f}%  cash {out['cash_w'][m].mean()*100:4.1f}%  "
              f"fear-extra {out['extra_w'][m].mean()*100:4.1f}%  s4live {i4[m].mean()*100:3.0f}%d  "
              f"expo p-avg {out['expo'][m].mean()*100:5.1f}%")

    # ---------------- O5: alpha decomposition (one-at-a-time ablations) ----------------
    print(f"\n{'='*110}\nO5. ALPHA DECOMPOSITION — {best} minus one component at a time (FULL window)\n{'='*110}")
    full = com["mask_by_w"]["FULL 1996-2026"]
    mb = metrics_row(out["nav"], out["ret"], bh_ret, full)
    print(f"  {'config':34} {'CAGR':>8} {'Sharpe':>7} {'alpha':>8} {'t':>6}  {'dCAGR':>7} {'dAlpha':>7}")
    print(f"  {best+' (full system)':34} {mb['cagr']*100:+8.2f} {mb['sh']:7.2f} "
          f"{mb['a']*100:+8.2f} {mb['t']:+6.1f}  {'—':>7} {'—':>7}")
    base_cfg = cfg_of(best)
    abls = []
    c1 = dict(base_cfg); c1["w_s2"] = 0.0
    abls.append(("minus S2 LEAP (w_s2=0)", c1, False, True))
    c2 = dict(base_cfg); c2["s4_frac"] = 0.0
    abls.append(("minus S4 covered-call", c2, True, False))
    c3 = dict(base_cfg); c3["fear"] = False
    abls.append(("minus fear-deploy", c3, True, True))
    c4 = dict(base_cfg); c4["reb"] = None; c4["sweep"] = False
    abls.append(("minus rebalance+sweep", c4, True, True))
    tot_d_a = 0.0
    for label, cfgx, use_s2, use_s4 in abls:
        o = run_engine4(com["close"], yr, com["rate_pw"], cfgx,
                        s2pack4(sl, "05") if use_s2 else None,
                        s4pack4(sl, "05") if use_s4 else None,
                        com["sigs"], ETF_COST_SIDE, OPT_COST_SIDE)
        m = metrics_row(o["nav"], o["ret"], bh_ret, full)
        d_c = (mb["cagr"] - m["cagr"]) * 100
        d_a = (mb["a"] - m["a"]) * 100
        tot_d_a += d_a
        print(f"  {label:34} {m['cagr']*100:+8.2f} {m['sh']:7.2f} {m['a']*100:+8.2f} "
              f"{m['t']:+6.1f}  {d_c:+7.2f} {d_a:+7.2f}")
    print(f"  sum of one-at-a-time alpha contributions {tot_d_a:+.2f}pp vs full-system alpha "
          f"{mb['a']*100:+.2f}pp — components interact (sweep needs S2 P&L, fear needs cash), "
          f"so contributions need not sum to total")

    # ---------------- O3: decision rules as implemented ----------------
    print(f"\n{'='*110}\nO3. DECISION-RULE TABLE AS IMPLEMENTED (all: decide on close t -> execute close t+1)\n{'='*110}")
    fpp = cfg_of(best)["fear_pp"]; ws2 = cfg_of(best)["w_s2"]; wb = cfg_of(best)["w_base"]
    rules = [
        ("S2-ENTRY", "gate OFF->ON: close>200SMA AND RSI-2<10 within last 5 sessions",
         f"buy 0.80-delta 12m SPY call, premium = {ws2*100:.0f}% x NAV (cap: available cash)"),
        ("S2-ROLL", "position DTE <= 63 and gate still ON",
         f"sell old, buy fresh 0.80d 1y call re-budgeted to {ws2*100:.0f}% x NAV; proceeds ABOVE "
         "target buy SPY base (sweep); shortfall topped up from cash only"),
        ("S2-EXIT", "close < 0.98x200SMA for 5 CONSECUTIVE days (hysteresis)",
         "sell LEAP at next close; proceeds sit in cash (recycled at next annual rebalance)"),
        ("S4-ENTRY", "RSI-2 > 90 and no open short call",
         "sell 21DTE 0.30-delta SPY call on 25% of base MV (priced/marked at 0.85x IV-proxy)"),
        ("S4-EXIT", "mark <= 50% of premium received (PT) else hold to expiry",
         "buy back at PT; if ITM at expiry the day's base upside is capped (cash-settled)"),
        ("FEAR-DEPLOY", "SPY>200SMA (raw) AND VIX-proxy>28, not already deployed",
         f"buy {fpp*100:.0f}pp of NAV extra SPY from cash (cap: cash); one deploy per episode"),
        ("FEAR-UNWIND", "deployed AND VIX-proxy<18", "sell exactly the deployed units to cash"),
        ("REBALANCE", "first trading day of each calendar year",
         f"S2 stake -> {ws2*100:.0f}% NAV (top-up from cash only), then base -> {wb*100:.0f}% NAV "
         "(buys capped by cash; sells allowed)"),
        ("COSTS/CARRY", "always",
         "ETF 5bps/side; options 0.5% of premium/side; cash earns piecewise T-bill era rate"),
    ]
    for k, sig, act in rules:
        print(f"  {k:12} | {sig}\n  {'':12} | -> {act}")
    print("DONE ops stage.")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "grid"
    if stage == "sims":
        stage_sims()
    elif stage == "grid":
        stage_grid()
    elif stage == "ops":
        stage_ops()
    else:
        raise SystemExit(f"unknown stage {stage}")
