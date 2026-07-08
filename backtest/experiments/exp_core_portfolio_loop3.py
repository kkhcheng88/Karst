"""LOOP 3 — pre-registered grid: REBALANCE FIX x WEIGHTS x WASHOUT branch, on the
loop-2-surviving ARCH-A shape. Fixes the two loop-2 spec bugs, adds nothing else.

Imports (does not modify) exp_core_portfolio_lab.py and exp_core_portfolio_loop2.py.

THE TWO SPEC BUGS FIXED (orchestrator verdicts after loop 2):
  (1) DECAYING BASE: loop-2 had no recycle rule -> ARCH-A's base drifted 75%->43% over
      30y; its -30% MaxDD was an accidental glide path, not a design property.
      FIX = two pre-registered rebalance variants applied to every config:
        R1 = ANNUAL calendar rebalance to target weights (first trading day of each
             year; decision is calendar-known ex ante, so next-bar discipline holds)
             + sweep option P&L into BASE at each S2 roll.
        R2 = BAND rebalance: core-base weight or S2 weight +/-10pp off target at close t
             -> rebalance all sleeves to target at close t+1 (next-bar), + same sweep.
      SWEEP mechanics (both R1/R2): at each S2 ROLL (not fresh entries, not trend
      exits), the stake is re-budgeted to w_s2 x NAV; any proceeds ABOVE the new target
      (realized option P&L) buy BASE units (5bps side) instead of piling into cash.
      Trend-exit proceeds still go to CASH (buying more equity on a sell-signal day is
      not a registered rule; the R1/R2 rebalance recycles it later). Rebalance trades:
      base at 5bps/side; S2 stake adjustments at 0.5%/side of premium traded. Funding
      cap kept from loop 2: S2 top-ups draw from CASH only, never from selling base.
  (2) S4 OVERWEIGHT: loop-2 sold calls on 50% of base and priced them at the raw
      RV-lag-inflated IV proxy (~1.9pp of ARCH-A's alpha; real-data prior says small
      positive skim only). FIX = calls on <=25% of base (cap taken at the cap) AND all
      S4 pricing (strike solve, premium, marks) repriced at 0.85 x IV_proxy_short_dte.
      One sensitivity row: S4 off entirely.

PRE-REGISTERED GRID (run all, report all, nothing else):
  weights  W1 = base75/S2-10/cash15   W2 = base80/S2-10/cash10   W3 = base85/S2-10/cash5
  rebal    R1 (annual+sweep)          R2 (band+/-10pp+sweep)
  washout  B0 (off)                   B1 (on, spec below)
  = 12 configs, all with the HYSTERESIS S2 gate (exit only if close<0.98x200SMA for 5
  consecutive days — loop-2 default; raw gate kept as a stress row), piecewise cash
  rate (loop-2 eras), fear-deploy retained (quadrant Q2 = SPY>200SMA & VIXproxy>28 ->
  10pp cash into S1 shares next-bar, unwind at VIXproxy<18 next-bar).
  Plus, for the single best config (FULL Sharpe): raw-gate row, S4-off row, 0%-cash-rate
  row, costx2 row (options 1%/side, ETF 10bps). Baselines: SPY TR-net, 100% S1.

WASHOUT BOTTOM-FISH BRANCH (B1) — finally testable with real member data:
  BREADTH = % of S&P members above their own 50SMA, built from sp500_px.pkl's ~505
  member Series (only members with >=50 valid closes that day count; day needs >=100
  such members). SURVIVORSHIP CAVEAT (documented, not hidden): these are TODAY's S&P
  members, so 1996-2010 breadth is biased toward survivors; we therefore use only
  LEVEL-RELATIVE thresholds — the EXPANDING-WINDOW percentile of breadth vs its own
  history (>=252 prior obs before the percentile is valid; no look-ahead), which the
  bias largely survives (per exp_breadth_reversion.py's same argument).
  SIGNAL: quadrant Q3 (SPY<200SMA & VIXproxy>28, SMA valid) AND breadth expanding-window
  percentile <= 0.10 (bottom decile). ACTION (next-bar): deploy 5pp of NAV from cash
  into S1 shares, hold EXACTLY 21 trading days, sell at close. Re-arm after exit (signal
  may re-fire). If cash < 0.1% of NAV the deploy is SKIPPED (skip-days counted) — no
  borrowing, no selling base. Deployed slice earns the dividend drip like all shares.
  Prior real-data evidence being tested: washout -> 21d +2.58% ~ 3x baseline, one-sided,
  ~8-12 independent events (exp_breadth_reversion.py).

DISCIPLINE: next-bar everywhere; expanding-window percentiles only; costs as loop 1/2
(ETF 5bps/side, options 0.5%/side of premium); piecewise cash yield; BSM pricing r=0.03
unchanged. Zero-cost twin of every config gives total cost drag. TRIAL REGISTRY: loop-2
ran 11 configs; this loop adds 16 (12 grid + 4 best-config sensitivity rows) -> ~27
tracked configs carried forward for the final deflated-Sharpe assessment.

DEV NOTE (bug caught in first run, fixed before any result was used): the washout
deploy initially credited wo_units without debiting cash (minted ~5% NAV per event,
+6pp/yr fake CAGR on every B1 cell). Symptom: B1-B0 CAGR gap ~36x larger than the
slice P&L arithmetic allows. Fix = the one-line `cash -= amt`. Kept here as a warning:
always cross-foot branch P&L against slice-level arithmetic.

Stages (each bash call must stay <40s; caches under /tmp/karst_loop):
    python exp_core_portfolio_loop3.py breadth   # build+cache member breadth
    python exp_core_portfolio_loop3.py sims      # build+cache sleeve sims
    python exp_core_portfolio_loop3.py grid      # (default) full report, uses caches
"""
from __future__ import annotations

import bisect
import math
import os
import pickle
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from exp_core_portfolio_lab import (  # noqa: E402
    TD, DIV_NET_YR, ETF_COST_SIDE, OPT_COST_SIDE, CACHE_DIR, WINDOWS, DATA_PKL,
    load_spy_close, sma, vix_proxy, iv_proxy_1y, iv_proxy_short_dte, build_gates,
    sim_s2_leap, sim_s4_short_call, spy_bh_total_return, cagr, jensen_alpha,
    ann_sharpe, window_mask,
)
from exp_core_portfolio_loop2 import (  # noqa: E402
    RATE_ERAS, piecewise_rate, build_hold, worst63, metrics_row, prow,
)

BREADTH_CACHE = os.path.join(CACHE_DIR, "breadth_loop3.npz")
SLEEVE_CACHE = os.path.join(CACHE_DIR, "loop3_sleeves.npz")

PCT_MIN_OBS = 252     # expanding-percentile warmup (1 trading yr) — a necessity, not a tuned knob
MIN_MEMBERS = 100     # breadth defined only when >=100 members have a 50SMA that day (data floor)
WASHOUT_HOLD = 21     # pre-registered hold, trading days
WASHOUT_PP = 0.05     # 5pp of NAV
FEAR_PP = 0.10        # loop-2 fear deployment size
BAND = 0.10           # R2 band, +/-10pp absolute weight
S4_FRAC = 0.25        # calls on <=25% of base (cap taken at cap)
S4_IV_HAIRCUT = 0.85  # conservative S4 pricing vs RV-lag-inflated proxy

KNOWN_BOTTOMS = [("2008-11-20", "GFC Nov08"), ("2009-03-09", "GFC final"),
                 ("2011-08-08", "US-downgrade"), ("2018-12-24", "Dec-2018"),
                 ("2020-03-23", "COVID"), ("2022-06-16", "2022-June"),
                 ("2025-04-08", "2025-April")]


# ============================================================================
# breadth (stage 1)
# ============================================================================

def build_breadth(spy_idx: pd.DatetimeIndex):
    if os.path.exists(BREADTH_CACHE):
        z = np.load(BREADTH_CACHE)
        if len(z["breadth"]) == len(spy_idx):
            return z["breadth"], z["pct"], z["nmem"]
    with open(DATA_PKL, "rb") as f:
        d = pickle.load(f)
    cols = {}
    for k, v in d.items():
        if k == "SPY" or not isinstance(v, pd.Series) or len(v) < 60:
            continue
        s = v.astype("float64")
        s = s[~s.index.duplicated()].sort_index()
        s.index = pd.to_datetime(s.index)
        cols[k] = s
    px = pd.DataFrame(cols).reindex(spy_idx)
    sma50 = px.rolling(50, min_periods=50).mean()
    valid = px.notna() & sma50.notna()
    above = (px > sma50) & valid
    num = above.sum(axis=1).values.astype(float)
    den = valid.sum(axis=1).values.astype(float)
    breadth = np.where(den >= MIN_MEMBERS, num / np.maximum(den, 1.0), np.nan)
    # expanding-window percentile, no look-ahead: rank of today within [start..today]
    pct = np.full(len(spy_idx), np.nan)
    buf: list[float] = []
    for t in range(len(spy_idx)):
        v = breadth[t]
        if math.isnan(v):
            continue
        bisect.insort(buf, v)
        if len(buf) >= PCT_MIN_OBS:
            pct[t] = bisect.bisect_right(buf, v) / len(buf)
    np.savez(BREADTH_CACHE, breadth=breadth, pct=pct, nmem=den)
    return breadth, pct, den


# ============================================================================
# sleeve sims (stage 2) — S2 x {hyst,raw} x costs, S4 x {haircut,legacy} x costs
# ============================================================================

def build_sleeves(close_s: pd.Series) -> dict:
    close = close_s.values
    n = len(close)
    if os.path.exists(SLEEVE_CACHE):
        z = np.load(SLEEVE_CACHE)
        if len(z["close"]) == n and np.allclose(z["close"], close):
            return {k: z[k] for k in z.files}
    iv1y = iv_proxy_1y(close_s).values
    ivsh = iv_proxy_short_dte(close_s).values
    gate_raw, _, _, _ = build_hold(close_s, hysteresis=False)
    gate_hys, _, _, _ = build_hold(close_s, hysteresis=True)
    rsi_ob = build_gates(close_s)["rsi2_ob_entry"].values
    big = np.full(n, 1e9)  # coverage enforced at ENGINE sizing (loop-2 convention)
    out = {"close": close}
    for gname, garr in [("hyst", gate_hys), ("raw", gate_raw)]:
        costs = (0.005, 0.0, 0.01) if gname == "hyst" else (0.005, 0.0)
        for cp in costs:
            s = sim_s2_leap(close, iv1y, garr, cost_pct=cp)
            tag = f"s2_{gname}_{int(round(cp*1000)):02d}"
            out[f"{tag}_ret"] = s["ret"]
            out[f"{tag}_inpos"] = s["in_pos"].astype(bool)
            out[f"{tag}_reset"] = (s["entered"] | s["rolled"]).astype(bool)
    for ivtag, ivarr in [("hc", ivsh * S4_IV_HAIRCUT), ("legacy", ivsh)]:
        costs = (0.005, 0.0, 0.01) if ivtag == "hc" else (0.005,)
        for cp in costs:
            s = sim_s4_short_call(close, ivarr, rsi_ob, big, cost_pct=cp)
            dnav = np.zeros(n)
            dnav[1:] = np.diff(s["nav"])
            tag = f"s4_{ivtag}_{int(round(cp*1000)):02d}"
            out[f"{tag}_dnav"] = dnav
            out[f"{tag}_inpos"] = s["in_pos"].astype(bool)
    np.savez(SLEEVE_CACHE, **out)
    return out


def s2pack(sl: dict, gname: str, cp: float) -> dict:
    tag = f"s2_{gname}_{int(round(cp*1000)):02d}"
    return {"ret": sl[f"{tag}_ret"], "in_pos": sl[f"{tag}_inpos"], "reset": sl[f"{tag}_reset"]}


def s4pack(sl: dict, ivtag: str, cp: float) -> dict:
    tag = f"s4_{ivtag}_{int(round(cp*1000)):02d}"
    return {"dnav": sl[f"{tag}_dnav"], "in_pos": sl[f"{tag}_inpos"]}


# ============================================================================
# engine — loop-2's stake-tracking day loop + (sweep-at-roll, R1/R2, washout, S4 cap)
# ============================================================================

def run_engine3(close: np.ndarray, yr: np.ndarray, rate_d: np.ndarray, cfg: dict,
                s2p: dict | None, s4p: dict | None, sigs: dict,
                etf_cost: float, opt_cost: float) -> dict:
    """Order within day t (signals all from t-1 / pre-shifted): cash interest -> div
    drip -> S2 stake (ret / reset+sweep / exit-sweep-to-cash) -> S4 P&L -> fear deploy
    -> washout branch -> R1/R2 rebalance -> NAV. cfg['sweep']=False reproduces the
    loop-2 engine op-for-op (regression-checked against loop2_configs.npz)."""
    n = len(close)
    div_d = DIV_NET_YR / TD
    w_base, w_s2 = cfg["w_base"], cfg["w_s2"]
    sweep = cfg.get("sweep", False)
    reb = cfg.get("reb")            # None | 'R1' | 'R2'
    s4_frac = cfg.get("s4_frac", 0.0)
    fear = cfg.get("fear", False)
    washout = cfg.get("washout", False)

    cash = 1.0 - w_base
    units = (w_base * (1.0 - etf_cost) / close[0]) if w_base > 0 else 0.0
    extra = 0.0                     # fear-deployed units
    wo_units = 0.0                  # washout-deployed units
    wo_left = 0
    wo_cost = wo_frac = 0.0
    wo_t0 = -1
    s2s = 0.0
    s4not = 0.0
    deployed = False
    pending_band = False
    nav = np.empty(n)
    nav[0] = cash + units * close[0]
    bw = np.zeros(n)                # CORE base weight (units only — extras excluded: fear/
    w2 = np.zeros(n)                # washout slices are tactical, with their own exit rules)
    bw[0] = units * close[0] / nav[0]
    to = 0.0
    nde = dep_days = n_reb = wo_skipdays = 0
    wo_events: list[tuple] = []
    q2p, vxp, wop = sigs["quad2_prev"], sigs["vix_prev"], sigs["wo_prev"]
    i2 = s2p["in_pos"] if s2p is not None else None

    for t in range(1, n):
        cash *= 1.0 + rate_d[t] / TD
        units *= 1.0 + div_d
        extra *= 1.0 + div_d
        wo_units *= 1.0 + div_d
        c = close[t]

        # ---- S2 LEAP stake ----
        if s2p is not None and w_s2 > 0:
            r2_, rs2 = s2p["ret"], s2p["reset"]
            if i2[t]:
                if rs2[t]:
                    fresh = not bool(i2[t - 1])
                    prev_val = s2s
                    if not sweep:   # loop-2-exact op order (regression path)
                        if s2s > 0:
                            s2s *= 1.0 + r2_[t]
                            cash += s2s
                            s2s = 0.0
                        navnow = cash + (units + extra + wo_units) * c
                        tgt = max(min(w_s2 * navnow, cash), 0.0)
                        to += abs(tgt - prev_val) / navnow
                        s2s = tgt
                        cash -= tgt
                    else:           # sweep-at-roll: P&L above target -> BASE
                        if s2s > 0:
                            s2s *= 1.0 + r2_[t]
                        proceeds = s2s
                        s2s = 0.0
                        navnow = cash + proceeds + (units + extra + wo_units) * c
                        tgt = max(w_s2 * navnow, 0.0)
                        if (not fresh) and proceeds >= tgt:
                            s2s = tgt
                            rem = proceeds - tgt
                            units += rem * (1.0 - etf_cost) / c
                            to += (abs(tgt - prev_val) + rem) / navnow
                        else:
                            add = min(max(tgt - proceeds, 0.0), cash)
                            s2s = proceeds + add
                            cash -= add
                            to += abs(s2s - prev_val) / navnow
                    if fresh:
                        s2s *= 1.0 + r2_[t]   # entry-day ret = entry cost (loop-2 semantics)
                else:
                    s2s *= 1.0 + r2_[t]
            elif i2[t - 1]:
                s2s *= 1.0 + r2_[t]           # exit-day move + exit cost, then sweep to CASH
                cash += s2s
                to += s2s / max(cash + (units + extra + wo_units) * c, 1e-9)
                s2s = 0.0

        # ---- S4 covered-call overlay (notional set at entry: s4_frac x base MV) ----
        if s4p is not None and s4_frac > 0:
            i4 = s4p["in_pos"]
            if i4[t] or i4[t - 1]:
                cash += s4not * s4p["dnav"][t]
            if i4[t] and not i4[t - 1]:
                s4not = s4_frac * (units + extra) * c

        # ---- fear deploy (loop-2, kept verbatim) ----
        if fear:
            if (not deployed) and bool(q2p[t]):
                navnow = cash + (units + extra + wo_units) * c + s2s
                amt = min(FEAR_PP * navnow, cash)
                if amt > 1e-12:
                    extra += amt * (1.0 - etf_cost) / c
                    cash -= amt
                    deployed = True
                    nde += 1
                    to += amt / navnow
            elif deployed and (not math.isnan(vxp[t])) and vxp[t] < 18:
                navnow = cash + (units + extra + wo_units) * c + s2s
                val = extra * c
                cash += val * (1.0 - etf_cost)
                extra = 0.0
                deployed = False
                to += val / navnow
            if deployed:
                dep_days += 1

        # ---- washout bottom-fish branch (B1) ----
        if washout:
            if wo_left > 0:
                wo_left -= 1
                if wo_left == 0:
                    navnow = cash + (units + extra + wo_units) * c + s2s
                    val = wo_units * c
                    cash += val * (1.0 - etf_cost)
                    wo_events.append((wo_t0, t, wo_frac, val * (1.0 - etf_cost) / wo_cost - 1.0))
                    to += val / navnow
                    wo_units = 0.0
            elif bool(wop[t]):
                navnow = cash + (units + extra) * c + s2s
                amt = min(WASHOUT_PP * navnow, cash)
                if amt > 0.001 * navnow:      # need >=0.1% NAV of free cash to bother
                    wo_units = amt * (1.0 - etf_cost) / c
                    cash -= amt
                    wo_cost = amt
                    wo_frac = amt / navnow
                    wo_t0 = t
                    wo_left = WASHOUT_HOLD
                    to += amt / navnow
                else:
                    wo_skipdays += 1

        # ---- R1/R2 rebalance (R2 signal from t-1 weights -> executed here, next bar) ----
        if reb is not None:
            do_reb = (yr[t] != yr[t - 1]) if reb == "R1" else pending_band
            if do_reb:
                navnow = cash + (units + extra + wo_units) * c + s2s
                if s2p is not None and w_s2 > 0 and i2[t] and s2s > 0:
                    d2 = w_s2 * navnow - s2s
                    if d2 > 0:                # top-up from CASH only (funding cap kept)
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
            if reb == "R2":
                nav_t = cash + (units + extra + wo_units) * c + s2s
                dev = abs(units * c / nav_t - w_base) > BAND
                if (not dev) and s2p is not None and i2[t] and s2s > 0:
                    dev = abs(s2s / nav_t - w_s2) > BAND
                pending_band = dev and not do_reb   # don't re-fire the bar right after a reb

        nav[t] = cash + (units + extra + wo_units) * c + s2s
        bw[t] = units * c / nav[t]
        w2[t] = s2s / nav[t]

    ret = np.zeros(n)
    ret[0] = nav[0] - 1.0
    ret[1:] = nav[1:] / nav[:-1] - 1.0
    years = (n - 1) / TD
    return {"nav": nav, "ret": ret, "base_w": bw, "s2_w": w2,
            "turnover_yr": to / years, "n_deploys": nde, "dep_days": dep_days,
            "n_reb": n_reb, "wo_events": wo_events, "wo_skipdays": wo_skipdays}


# ============================================================================
# washout signal-level event study (config-independent, comparable to the prior)
# ============================================================================

def washout_signal_events(close: np.ndarray, wo_raw: np.ndarray) -> list[tuple]:
    """Next-bar entries on the raw signal, non-overlapping 21-td episodes (mirrors the
    engine's re-arm logic with unlimited cash). Returns (t_entry, t_exit, spy_21d_ret)."""
    n = len(close)
    ev = []
    t = 1
    while t < n:
        if wo_raw[t - 1]:
            te = min(t + WASHOUT_HOLD, n - 1)
            ev.append((t, te, close[te] / close[t] - 1.0))
            t = te + 1
        else:
            t += 1
    return ev


# ============================================================================
# main
# ============================================================================

def tele_line(out: dict, w_base: float, drag: float) -> str:
    bwx = out["base_w"]
    ln = (f"      baseW tgt {w_base*100:.0f}%: min {bwx.min()*100:5.1f} mean {bwx.mean()*100:5.1f} "
          f"max {bwx.max()*100:5.1f} final {bwx[-1]*100:5.1f} | s2W mean {out['s2_w'].mean()*100:4.1f} "
          f"| reb {out['n_reb']:3d} | turnover {out['turnover_yr']:.2f}x/yr | costDrag {drag:.2f}pp/yr "
          f"| fear-deploys {out['n_deploys']} ({out['dep_days']}d)")
    if out["wo_events"] or out["wo_skipdays"]:
        pnls = [e[3] for e in out["wo_events"]]
        ln += (f" | washout {len(out['wo_events'])}ev avg {np.mean(pnls)*100:+.2f}% "
               f"skipdays {out['wo_skipdays']}")
    return ln


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "grid"
    close_s = load_spy_close()
    close = close_s.values
    idx = close_s.index
    n = len(close)
    yr = idx.year.values

    if stage == "breadth":
        breadth, pct, nmem = build_breadth(idx)
        ok = ~np.isnan(breadth)
        print(f"breadth built: {ok.sum()} valid days of {n}; members min {int(nmem[ok].min())} "
              f"max {int(nmem[ok].max())}; first valid {idx[np.argmax(ok)].date()}; "
              f"pct valid from {idx[np.argmax(~np.isnan(pct))].date()}")
        print(f"cached -> {BREADTH_CACHE}")
        return
    if stage == "sims":
        sl = build_sleeves(close_s)
        print(f"sleeve sims cached -> {SLEEVE_CACHE}: {sorted(k for k in sl if k != 'close')}")
        return

    # ---------------- grid stage ----------------
    breadth, pct, nmem = build_breadth(idx)
    sl = build_sleeves(close_s)
    rate_pw = piecewise_rate(idx)
    rate0 = np.zeros(n)
    print(f"LOOP 3 | SPY {idx.min().date()} -> {idx.max().date()}, {n} days | "
          f"piecewise cash (mean {rate_pw.mean()*100:.2f}%/yr) | S4: <=25% of base, IV x0.85 | "
          f"gate: hysteresis (raw as stress)")

    # signals
    sma200 = sma(close_s, 200)
    above_raw = (close_s > sma200).values
    smaval = ~np.isnan(sma200.values)
    vx = vix_proxy(close_s).values
    quad2_raw = above_raw & (vx > 28)
    q3_raw = (~above_raw) & smaval & (vx > 28)
    wo_raw = q3_raw & (pct <= 0.10)
    quad2_prev = np.zeros(n, dtype=bool); quad2_prev[1:] = quad2_raw[:-1]
    vix_prev = np.full(n, np.nan); vix_prev[1:] = vx[:-1]
    wo_prev = np.zeros(n, dtype=bool); wo_prev[1:] = wo_raw[:-1]
    sigs = {"quad2_prev": quad2_prev, "vix_prev": vix_prev, "wo_prev": wo_prev}
    okb = ~np.isnan(breadth)
    print(f"breadth: valid {okb.sum()}/{n} days (from {idx[np.argmax(okb)].date()}), members "
          f"{int(nmem[okb].min())}-{int(nmem[okb].max())} [TODAY's members = survivorship; "
          f"level-relative expanding-percentile thresholds mitigate] | washout-signal days "
          f"(raw): {int(wo_raw.sum())} | Q3 days: {int(q3_raw.sum())}")

    bh_nav, bh_ret = spy_bh_total_return(close)
    mask_by_w = {wname: window_mask(idx, ws, we) for wname, ws, we in WINDOWS}

    # ---------------- sanity / regression vs loop 2 ----------------
    print(f"\n{'='*110}\n0. SANITY — engine reproduces loop-2 ARCH-A [hyst] op-for-op (sweep off, S4 legacy 50%, no reb)\n{'='*110}")
    replica_cfg = dict(w_base=0.75, w_s2=0.10, s4_frac=0.50, fear=True, washout=False,
                       reb=None, sweep=False)
    replica = run_engine3(close, yr, rate_pw, replica_cfg, s2pack(sl, "hyst", 0.005),
                          s4pack(sl, "legacy", 0.005), sigs, ETF_COST_SIDE, OPT_COST_SIDE)
    l2f = os.path.join(CACHE_DIR, "loop2_configs.npz")
    if os.path.exists(l2f):
        l2 = np.load(l2f)
        ref = l2["ARCH-A_hyst_nav"]
        md = float(np.max(np.abs(replica["nav"] / ref - 1.0)))
        print(f"  replica vs loop2 cached ARCH-A[hyst] NAV: max |rel diff| = {md:.2e} "
              f"{'[OK]' if md < 1e-6 else '[!!DIFFERS — engine port broken!!]'}")
        assert md < 1e-6
    else:
        print("  loop-2 cache absent — replica printed for reference only")
    prow("FULL 1996-2026", "loop2-A replica [hyst]", metrics_row(replica["nav"], replica["ret"], bh_ret, mask_by_w["FULL 1996-2026"]))
    rb = replica["base_w"]
    print(f"  DRIFT (the bug): replica base weight min {rb.min()*100:.1f}% mean {rb.mean()*100:.1f}% "
          f"max {rb.max()*100:.1f}% final {rb[-1]*100:.1f}% — the 75%->~43% decay this loop must fix")

    # ---------------- washout signal-level event log ----------------
    print(f"\n{'='*110}\n1. WASHOUT SIGNAL EVENT LOG — signal-level (config-independent), next-bar entry, 21td hold\n{'='*110}")
    ev = washout_signal_events(close, wo_raw)
    fwd21_all = close[WASHOUT_HOLD:] / close[:-WASHOUT_HOLD] - 1.0
    print(f"  baseline: unconditional mean 21d SPY return {np.nanmean(fwd21_all)*100:+.2f}% | "
          f"prior evidence: washout 21d +2.58%, ~8-12 events")
    bot = [(pd.Timestamp(d), lab) for d, lab in KNOWN_BOTTOMS]
    for (t0, te, r) in ev:
        d0 = idx[t0]
        near = [lab for bd, lab in bot if abs((d0 - bd).days) <= 60]
        print(f"    {d0.date()} -> {idx[te].date()}  SPY 21d {r*100:+7.2f}%  "
              f"{('near ' + ','.join(near)) if near else ''}")
    rs = np.array([e[2] for e in ev])
    if len(rs):
        print(f"  N={len(rs)}  mean {rs.mean()*100:+.2f}%  median {np.median(rs)*100:+.2f}%  "
              f"win% {(rs>0).mean()*100:.0f}%  min {rs.min()*100:+.2f}%  max {rs.max()*100:+.2f}%")

    # ---------------- baselines ----------------
    print(f"\n{'='*110}\n2. PRE-REGISTERED GRID — 2 rebalance x 3 weights x 2 washout, hysteresis gate, piecewise cash\n{'='*110}")
    s1_cfg = dict(w_base=1.0, w_s2=0.0, s4_frac=0.0, fear=False, washout=False, reb=None, sweep=False)
    s1_100 = run_engine3(close, yr, rate_pw, s1_cfg, None, None, sigs, ETF_COST_SIDE, OPT_COST_SIDE)
    print("--- baselines ---")
    for wname, _, _ in WINDOWS:
        prow(wname, "SPY B&H TR-net", metrics_row(bh_nav, bh_ret, bh_ret, mask_by_w[wname]))
        prow(wname, "100% S1", metrics_row(s1_100["nav"], s1_100["ret"], bh_ret, mask_by_w[wname]))

    WEIGHTS = [("W1", 0.75), ("W2", 0.80), ("W3", 0.85)]
    packs_c = (s2pack(sl, "hyst", 0.005), s4pack(sl, "hc", 0.005))
    packs_0 = (s2pack(sl, "hyst", 0.0), s4pack(sl, "hc", 0.0))
    results, drags = {}, {}
    for rname in ("R1", "R2"):
        for wkey, wb in WEIGHTS:
            for bkey, wo_on in [("B0", False), ("B1", True)]:
                cfg = dict(w_base=wb, w_s2=0.10, s4_frac=S4_FRAC, fear=True,
                           washout=wo_on, reb=rname, sweep=True)
                out = run_engine3(close, yr, rate_pw, cfg, packs_c[0], packs_c[1], sigs,
                                  ETF_COST_SIDE, OPT_COST_SIDE)
                out0 = run_engine3(close, yr, rate_pw, cfg, packs_0[0], packs_0[1], sigs, 0.0, 0.0)
                key = f"{wkey}-{rname}-{bkey}"
                results[key] = (cfg, out)
                drags[key] = (cagr(out0["nav"]) - cagr(out["nav"])) * 100

    for rname in ("R1", "R2"):
        print(f"\n--- rebalance = {rname} ({'annual+sweep' if rname == 'R1' else 'band +/-10pp+sweep'}) ---")
        for wkey, wb in WEIGHTS:
            for bkey in ("B0", "B1"):
                key = f"{wkey}-{rname}-{bkey}"
                cfg, out = results[key]
                for wname, _, _ in WINDOWS:
                    prow(wname, key, metrics_row(out["nav"], out["ret"], bh_ret, mask_by_w[wname]))
                print(tele_line(out, wb, drags[key]))

    # ---------------- best config + sensitivity block ----------------
    full_mask = mask_by_w["FULL 1996-2026"]
    rank = sorted(((k, metrics_row(o["nav"], o["ret"], bh_ret, full_mask)["sh"])
                   for k, (c, o) in results.items()), key=lambda kv: -kv[1])
    best_key = rank[0][0]
    best_cfg = dict(results[best_key][0])
    print(f"\n{'='*110}\n3. BEST CONFIG (FULL Sharpe) = {best_key}   "
          f"[ranking: {', '.join(f'{k} {v:.3f}' for k, v in rank)}]\n{'='*110}")

    sens = []
    cfg_raw = dict(best_cfg)
    sens.append(("raw-gate", cfg_raw, s2pack(sl, "raw", 0.005), s4pack(sl, "hc", 0.005),
                 s2pack(sl, "raw", 0.0), s4pack(sl, "hc", 0.0), rate_pw, ETF_COST_SIDE, OPT_COST_SIDE))
    cfg_ns4 = dict(best_cfg); cfg_ns4["s4_frac"] = 0.0
    sens.append(("S4-off", cfg_ns4, s2pack(sl, "hyst", 0.005), None,
                 s2pack(sl, "hyst", 0.0), None, rate_pw, ETF_COST_SIDE, OPT_COST_SIDE))
    sens.append(("cash-rate-0%", best_cfg, s2pack(sl, "hyst", 0.005), s4pack(sl, "hc", 0.005),
                 s2pack(sl, "hyst", 0.0), s4pack(sl, "hc", 0.0), rate0, ETF_COST_SIDE, OPT_COST_SIDE))
    sens.append(("cost-x2", best_cfg, s2pack(sl, "hyst", 0.01), s4pack(sl, "hc", 0.01),
                 s2pack(sl, "hyst", 0.0), s4pack(sl, "hc", 0.0), rate_pw, 2 * ETF_COST_SIDE, 2 * OPT_COST_SIDE))
    for label, cfg_x, p2, p4, p2z, p4z, rt, ec, oc in sens:
        out = run_engine3(close, yr, rt, cfg_x, p2, p4, sigs, ec, oc)
        out0 = run_engine3(close, yr, rt, cfg_x, p2z, p4z, sigs, 0.0, 0.0)
        for wname, _, _ in WINDOWS:
            prow(wname, f"{best_key} {label}", metrics_row(out["nav"], out["ret"], bh_ret, mask_by_w[wname]))
        print(tele_line(out, cfg_x["w_base"], (cagr(out0["nav"]) - cagr(out["nav"])) * 100))

    # engine-level washout trade log for the best B1 sibling
    b1_key = best_key.replace("B0", "B1") if best_key.endswith("B0") else best_key
    _, b1_out = results[b1_key]
    print(f"\n--- engine washout trade log, {b1_key} (actual deployed slices) ---")
    for (t0, te, frac, pnl) in b1_out["wo_events"]:
        print(f"    {idx[t0].date()} -> {idx[te].date()}  deployed {frac*100:4.2f}%NAV  "
              f"slice P&L {pnl*100:+7.2f}%")
    print(f"    skip-days (signal on, cash <0.1%NAV): {b1_out['wo_skipdays']}")

    # ---------------- registry ----------------
    ny = (n - 1) / TD
    print(f"\n{'='*110}\n4. TRIAL REGISTRY — loop2 ran 11 configs; loop3 adds 16 (12 grid + 4 sensitivity) "
          f"-> ~27 cumulative.\n   Naive E[max Sharpe | null, 27 indep trials, {ny:.0f}y] ~ "
          f"{math.sqrt(1.0/ny) * math.sqrt(2*math.log(27)):.2f} on FULL — configs are heavily correlated "
          f"(shared base), so judge on the Jensen-alpha t-stats, not raw Sharpe.\n{'='*110}")

    save = {"dates_days_since_epoch": idx.values.astype("datetime64[D]").astype(np.int64),
            "close": close, "bh_nav": bh_nav, "bh_ret": bh_ret}
    for k, (c, o) in results.items():
        save[f"{k}_nav"] = o["nav"]
    np.savez(os.path.join(CACHE_DIR, "loop3_configs.npz"), **save)
    print(f"Cached loop-3 config NAVs -> {CACHE_DIR}/loop3_configs.npz\nDONE loop 3.")


if __name__ == "__main__":
    main()
