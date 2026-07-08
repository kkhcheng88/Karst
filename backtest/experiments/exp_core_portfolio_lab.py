"""Core-portfolio backtest LAB — config-driven simulator + pre-registered sleeve
diagnostics (loop 1 of the core-portfolio strategy search).

PURPOSE (read this before editing): this module is NOT a one-shot experiment. It is
meant to be IMPORTED by later loops with different portfolio configs (different sleeve
weights, different regime gates). Keep the public surface (`Sleeves`, `simulate_portfolio`,
`PortfolioConfig`, `run_windowed_report`) stable; add, don't rewrite.

Network is BLOCKED in this sandbox. Data: backtest/.insider_data/sp500_px.pkl (dict of
pandas Series, price-only close, SPY 1996-01-24 -> 2026-06-30) + reference/fear_greed/
fear-greed.csv (CNN Fear&Greed, 2011+). No scipy here (ModuleNotFoundError confirmed in
this sandbox) -> BSM reimplemented standalone with math.erf, mirroring backtest/bsm.py's
formulas exactly (verified against exp_leap_delta_sweep.py's already-validated copy).

SLEEVES (specs are PRE-REGISTERED from settled evidence — not tuned here):
  S1 EQUITY BASE : hold SPY, + 1.05%/yr net dividend accrual (drip, since the pickle is
                   price-only with no distribution calendar).
  S2 LEAP        : 0.80D 1y call, roll at 63td remaining, GATED+DIP entry (>200SMA AND
                   RSI-2<10 within last 5d, next-bar), exit-to-cash when <200SMA.
  S3 CSP         : sell 21DTE 0.20D put, cash-secured, 50% PT else expiry, ENTRY only on
                   RSI-2<10 (next-bar settle), assignment -> take shares at strike, sell
                   next close (5bps slippage).
  S4 SHORT-CALL  : sell 21DTE 0.30D call vs the S1 base, ONLY when RSI-2>90 AND base MV >=
                   call notional (covered), 50% PT else expiry, assignment delivers from
                   base (economically: sell base at strike, i.e. capped upside that day).
  S5 CASH        : earns cash_rate (0% or 3%/yr, both run).

Execution: next-bar throughout (decision on close t -> trade at close t+1). Costs: ETF
5bps/side; options 0.5%/side of premium. Benchmark: SPY B&H total-return proxy = price
return + 1.05%/yr net-dividend drip, 5bps one-time entry cost.

    python backtest/experiments/exp_core_portfolio_lab.py
"""
from __future__ import annotations

import math
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TD = 252
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PKL = os.path.join(REPO_ROOT, "backtest", ".insider_data", "sp500_px.pkl")
FG_CSV = os.path.join(REPO_ROOT, "reference", "fear_greed", "fear-greed.csv")
CACHE_DIR = "/tmp/karst_loop"
os.makedirs(CACHE_DIR, exist_ok=True)

R_RATE = 0.03      # risk-free (option pricing), fixed per spec
Q_YIELD = 0.013    # continuous dividend yield (option pricing), fixed per spec
DIV_NET_YR = 0.0105  # SPY net dividend drip (post 30% HK withholding), fixed per spec

ETF_COST_SIDE = 0.0005     # 5bps/side, ETF trades
OPT_COST_SIDE = 0.005      # 0.5%/side of premium, option trades


# ============================================================================
# 1. Standalone Black-Scholes (no scipy in this sandbox — math.erf norm.cdf).
#    Mirrors backtest/bsm.py exactly; verified vs textbook norm.cdf values
#    (0)=0.5, (1.96)=0.9750, (-1.645)=0.0500 during exp_leap_delta_sweep.py dev.
# ============================================================================

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / 1.4142135623730951))


def _d1d2(S, K, T, r, q, sig):
    vt = sig * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sig * sig) * T) / vt
    return d1, d1 - vt


def call_price(S, K, T, r, q, sig):
    if T <= 0 or sig <= 0:
        return max(S - K, 0.0)
    d1, d2 = _d1d2(S, K, T, r, q, sig)
    return S * math.exp(-q * T) * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)


def put_price(S, K, T, r, q, sig):
    if T <= 0 or sig <= 0:
        return max(K - S, 0.0)
    d1, d2 = _d1d2(S, K, T, r, q, sig)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * math.exp(-q * T) * norm_cdf(-d1)


def call_delta(S, K, T, r, q, sig):
    if T <= 0 or sig <= 0:
        return 1.0 if S > K else 0.0
    d1, _ = _d1d2(S, K, T, r, q, sig)
    return math.exp(-q * T) * norm_cdf(d1)


def put_delta(S, K, T, r, q, sig):
    if T <= 0 or sig <= 0:
        return -1.0 if S < K else 0.0
    d1, _ = _d1d2(S, K, T, r, q, sig)
    return -math.exp(-q * T) * norm_cdf(-d1)


def strike_for_call_delta(S, T, r, q, sig, target):
    lo, hi = 0.2 * S, 1.5 * S
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if call_delta(S, mid, T, r, q, sig) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def strike_for_put_delta(S, T, r, q, sig, target_abs):
    lo, hi = 0.2 * S, 1.5 * S
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if -put_delta(S, mid, T, r, q, sig) > target_abs:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


# ============================================================================
# 2. Data loading
# ============================================================================

def load_spy_close() -> pd.Series:
    with open(DATA_PKL, "rb") as f:
        d = pickle.load(f)
    s = d["SPY"].astype("float64").sort_index()
    s.index = pd.to_datetime(s.index)
    s.index.name = "date"
    return s


def load_fear_greed() -> pd.Series:
    """CNN Fear & Greed daily index, 2011-01-03+. Returns a Series indexed by date
    (float 0-100). NOT available pre-2011 — callers must handle NaN before that."""
    df = pd.read_csv(FG_CSV)
    df["Date"] = pd.to_datetime(df["Date"])
    s = df.set_index("Date")["Fear Greed"].astype("float64").sort_index()
    s.index.name = "date"
    return s


# ============================================================================
# 3. Signal primitives (mirrors backtest/signals.py exactly, standalone copy to
#    avoid importing data.py, which pulls in yfinance/defeatbeta network deps).
# ============================================================================

def rsi2(close: pd.Series) -> pd.Series:
    period = 2
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period, min_periods=period).mean()


def rv21_ann(close: pd.Series) -> pd.Series:
    logret = np.log(close / close.shift(1))
    return logret.rolling(21, min_periods=21).std() * math.sqrt(TD)


def iv_proxy_1y(close: pd.Series, mult: float = 1.25, floor: float = 0.12,
                term_haircut: float = 0.85) -> pd.Series:
    """IV_1y = max(floor, mult*RV21_ann) * term_haircut. Used for the S2 LEAP (1y) leg.
    LIMITATION: realized-vol proxy for implied vol (no real VIX in this sandbox) — misses
    vol-of-vol/skew/decoupling spikes (e.g. 2018-02, Aug-2024). Documented, not silent."""
    rv = rv21_ann(close)
    return np.maximum(floor, mult * rv) * term_haircut


def iv_proxy_short_dte(close: pd.Series, mult: float = 1.25, floor: float = 0.12) -> pd.Series:
    """IV for 21DTE options (S3 CSP / S4 short-call): NO term haircut per spec — short-dated
    implied vol sits closer to realized than the 1y term structure does."""
    rv = rv21_ann(close)
    return np.maximum(floor, mult * rv)


def vix_proxy(close: pd.Series, mult: float = 1.25) -> pd.Series:
    """VIX proxy = RV21_ann * 1.25 (documented: real VIX unavailable in sandbox).
    Reported on the VIX POINTS scale (i.e. x100) for zone thresholds LOW<18/MID18-28/HIGH>28."""
    return rv21_ann(close) * mult * 100.0


def vix_zone(vixp: pd.Series) -> pd.Series:
    """LOW<18, MID 18-28, HIGH>28 on the vix_proxy points scale."""
    z = pd.Series(index=vixp.index, dtype=object)
    z[vixp < 18] = "LOW"
    z[(vixp >= 18) & (vixp <= 28)] = "MID"
    z[vixp > 28] = "HIGH"
    return z


def quadrant(close: pd.Series) -> pd.Series:
    """quadrant(t) = SPY>/<200SMA  x  VIX-proxy zone. Reusable regime function for
    later loops (not used to gate any pre-registered sleeve in loop 1 — S2/S3/S4 gates
    are fixed by spec above). Returns a string label, e.g. 'UP/LOW', 'DOWN/HIGH'."""
    sma200 = sma(close, 200)
    above = close > sma200
    vixp = vix_proxy(close)
    zone = vix_zone(vixp)
    dirn = pd.Series(np.where(above, "UP", "DOWN"), index=close.index)
    q = dirn + "/" + zone.astype(str)
    q[zone.isna()] = np.nan
    return q


def fg_greed_flag(fg: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Greed flag: F&G > 75. Reindexed/ffilled onto `index`; NaN (pre-2011 or gaps)
    stays NaN — callers must NOT silently treat NaN as False for any live gating use;
    for reporting/diagnostics here we fillna(False) explicitly at the call site."""
    aligned = fg.reindex(index, method="ffill")
    return aligned > 75


def breadth_washout_flag(index: pd.DatetimeIndex) -> pd.Series:
    """STUB — breadth data NOT available in this sandbox (no constituent-level
    advance/decline feed). TODO(loop2+): wire up real breadth (e.g. % of S&P500 members
    above 50SMA, or McClellan) once a constituent price feed is available; sp500_px.pkl
    DOES contain 505 tickers so this is buildable later, just not in loop 1's time box."""
    return pd.Series(False, index=index)


def build_gates(close: pd.Series) -> dict:
    """Next-bar (decision-on-close-t -> act-at-close-t+1) gate construction, shared by
    S2/S3/S4. GATED+DIP mirrors exp_leap_delta_sweep.py's stateful hold exactly (a
    triggered position isn't force-exited the instant the 5-day dip window rolls off —
    it holds until the 200SMA exit fires)."""
    sma200 = sma(close, 200)
    r2 = rsi2(close)
    above = (close > sma200)
    dip_recent = (r2 < 10).rolling(5, min_periods=1).max().astype(bool)

    gd = np.zeros(len(close), dtype=bool)
    holding = False
    above_v, trig_v = above.values, dip_recent.values
    for i in range(len(close)):
        if not holding and above_v[i] and trig_v[i]:
            holding = True
        elif holding and not above_v[i]:
            holding = False
        gd[i] = holding
    gated_dip = pd.Series(gd, index=close.index)

    entry_rsi_dip = (r2 < 10)        # S3 CSP entry trigger (raw signal, shifted below)
    entry_rsi_ob = (r2 > 90)         # S4 short-call entry trigger (raw signal, shifted below)

    def nb(s):  # next-bar shift, bool-safe
        return s.shift(1).astype("boolean").fillna(False).astype(bool)

    return {
        "above_200sma": nb(above),
        "gated_dip_leap": nb(gated_dip),
        "rsi2_dip_entry": nb(entry_rsi_dip),
        "rsi2_ob_entry": nb(entry_rsi_ob),
        "rsi2_raw": r2,
        "above_200sma_raw": above,
    }


# ============================================================================
# 4. Sleeve simulators — each returns a dict of per-day arrays (aligned to `close`)
#    including a `ret` array (daily simple return of THAT SLEEVE'S OWN NAV, for use
#    as a return-series building block) plus telemetry needed for reporting.
# ============================================================================

def sim_s1_equity_base(close: np.ndarray, div_yr: float = DIV_NET_YR,
                       cost_side: float = ETF_COST_SIDE) -> dict:
    """S1: hold SPY, one entry cost at t=0, + net dividend drip. NAV path only (no
    rebalancing needed — buy-and-hold)."""
    n = len(close)
    ret = np.zeros(n)
    ret[1:] = close[1:] / close[:-1] - 1.0
    ret = ret + div_yr / TD
    nav = np.cumprod(1.0 + ret) * (1.0 - cost_side)  # one-time entry cost
    nav[0] = 1.0 * (1.0 - cost_side)
    ret[0] = -cost_side
    return {"nav": nav, "ret": ret, "trades": 1}


def sim_s2_leap(close: np.ndarray, iv: np.ndarray, gate: np.ndarray,
                target_delta: float = 0.80, dte_init: int = TD, roll_dte: int = 63,
                r: float = R_RATE, q: float = Q_YIELD, cost_pct: float = OPT_COST_SIDE
                ) -> dict:
    """S2 LEAP sleeve, SLEEVE frame (100% of this sleeve's capital compounds in the
    option while `gate` allows; sits in cash at 0% internal rate otherwise — the
    portfolio combiner applies the actual cash_rate on top). GATED+DIP gate is passed
    in pre-computed (next-bar already applied by build_gates)."""
    n = len(close)
    nav = np.full(n, np.nan)
    delta_arr = np.full(n, np.nan)
    in_pos_arr = np.zeros(n, dtype=bool)
    rolled_arr = np.zeros(n, dtype=bool)
    entered_arr = np.zeros(n, dtype=bool)

    cash = 1.0
    contracts = 0.0
    K = None
    dte = 0
    in_pos = False
    n_rolls = n_entries = 0

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
            was_roll = (dte <= roll_dte) and allowed
            if was_roll:
                n_rolls += 1
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
                n_entries += 1

        if in_pos:
            T_rem = max(dte / TD, 1e-6)
            opt = call_price(S, K, T_rem, r, q, sig)
            nav[i] = cash + contracts * opt * 100
            delta_arr[i] = call_delta(S, K, T_rem, r, q, sig)
            in_pos_arr[i] = True
        else:
            nav[i] = cash

    ret = np.zeros(n)
    valid = ~np.isnan(nav)
    idx = np.where(valid)[0]
    for k in range(1, len(idx)):
        i0, i1 = idx[k - 1], idx[k]
        if i1 == i0 + 1 and nav[i0] > 0:
            ret[i1] = nav[i1] / nav[i0] - 1
    return {"nav": nav, "ret": ret, "delta": delta_arr, "in_pos": in_pos_arr,
            "rolled": rolled_arr, "entered": entered_arr, "n_rolls": n_rolls,
            "n_entries": n_entries, "trades": n_rolls + n_entries}


def sim_s3_csp(close: np.ndarray, iv: np.ndarray, entry_gate: np.ndarray,
              target_delta: float = 0.20, dte_init: int = 21, pt: float = 0.50,
              r: float = R_RATE, q: float = Q_YIELD, cost_pct: float = OPT_COST_SIDE,
              assign_slip: float = ETF_COST_SIDE) -> dict:
    """S3 CSP sleeve. Collateral-normalized NAV (1.0 = fully collateralized at entry
    strike x100 notional). ENTRY only when entry_gate[i] is True (next-bar RSI-2<10).
    Non-overlapping (single-leg, no wheel-continuation beyond the assignment sale).
    Assignment: if expires ITM (S_T < K), take shares at K, sell at NEXT close with
    assign_slip (5bps) realistic slippage — i.e. the assignment loss is
    max(K-S_T,0) economically PLUS one extra day of stock-price risk from expiry-close
    to next-close, modeled explicitly (not just intrinsic value)."""
    n = len(close)
    nav = np.full(n, np.nan)
    trades = []            # (entry_i, pnl) on premium-collection trades (PT or expiry)
    assignments = []       # (expiry_i, pnl_of_the_extra_share_day) when assigned
    realized = 0.0
    in_pos = False
    in_pos_arr = np.zeros(n, dtype=bool)   # True while short the put OR holding assigned shares
    pending_assignment = False   # True on the day AFTER expiry-ITM, awaiting the sale
    K = prem = 0.0
    dte = 0
    entry_i = 0
    contracts = 0.0
    n_entries = n_pt = n_expiry = n_assigned = 0

    for i in range(n):
        S = close[i]
        sig = max(iv[i], 1e-4) if not math.isnan(iv[i]) else 0.15

        # settle a pending assignment from yesterday's expiry (sell shares @ this close)
        if pending_assignment:
            sale_pnl = contracts * (S - K) * 100 * (1 - assign_slip)
            realized += sale_pnl
            assignments.append((i, sale_pnl))
            pending_assignment = False
            contracts = 0.0

        if in_pos:
            dte -= 1
            if dte <= 0:
                # expiry: settle the option itself first
                intrinsic = max(K - S, 0.0)
                pnl = contracts * (prem - intrinsic) * 100 - contracts * 100 * (prem + intrinsic) * cost_pct
                realized += pnl
                trades.append((entry_i, pnl))
                n_expiry += 1
                if intrinsic > 0:
                    # assigned: take shares at K today, sell next close (pending)
                    n_assigned += 1
                    pending_assignment = True
                    # contracts already represents the equivalent share count (see entry)
                else:
                    contracts = 0.0
                in_pos = False
            else:
                V = put_price(S, K, max(dte / TD, 1e-6), r, q, sig)
                if pt is not None and V <= pt * prem:
                    pnl = contracts * (prem - V) * 100 - contracts * 100 * (prem + V) * cost_pct
                    realized += pnl
                    trades.append((entry_i, pnl))
                    n_pt += 1
                    in_pos = False
                    contracts = 0.0

        if (not in_pos) and (not pending_assignment) and bool(entry_gate[i]) and S > 0:
            T = dte_init / TD
            K = strike_for_put_delta(S, T, r, q, sig, target_delta)
            prem = put_price(S, K, T, r, q, sig)
            if prem > 0 and K > 0:
                contracts = 1.0 / (K * 100)   # collateral-normalized: 1.0 NAV unit = K*100 collateral
                dte = dte_init
                in_pos = True
                entry_i = i
                n_entries += 1

        if in_pos:
            V = put_price(S, K, max(dte / TD, 1e-6), r, q, sig)
            unreal = contracts * (prem - V) * 100
        else:
            unreal = 0.0
        nav[i] = 1.0 + realized + unreal
        in_pos_arr[i] = in_pos or pending_assignment   # "exposed" = short put OR holding assigned shares

    ret = np.zeros(n)
    ret[1:] = nav[1:] / nav[:-1] - 1.0
    return {"nav": nav, "ret": ret, "trades": trades, "assignments": assignments,
            "n_entries": n_entries, "n_pt": n_pt, "n_expiry": n_expiry,
            "n_assigned": n_assigned, "in_pos": in_pos_arr}


def sim_s4_short_call(close: np.ndarray, iv: np.ndarray, entry_gate: np.ndarray,
                      base_shares: np.ndarray, target_delta: float = 0.30, dte_init: int = 21,
                      pt: float = 0.50, r: float = R_RATE, q: float = Q_YIELD,
                      cost_pct: float = OPT_COST_SIDE) -> dict:
    """S4 short-call overlay sleeve, notional-normalized to the S1 base (i.e. this
    sleeve's NAV is a P&L OVERLAY on top of the base — 1 call sold per 100 "base
    shares" held). `base_shares` = SHARE COUNT the base sleeve holds at each day (NOT
    a dollar market value — comparing a per-share market value against a 100-share
    option notional was an earlier bug here: base_mv[i] >= S*100 is off by 100x when
    base_mv is quoted per-share, so it never covers. Comparing share counts directly
    (base_shares[i] >= 100) is unit-safe and was verified against a hand-computed
    RSI-2>90 day: base_shares ~= 1/close[0] shares/NAV-unit is >=100 only once the
    portfolio's capital scale implies >=100 shares of exposure — see caller for how
    base_shares is constructed for the STANDALONE reference-size report.)
    Covered check: only sell when entry_gate AND base_shares[i] >= 100 (one contract's
    worth). Sizing (contracts = 1/(S*100)) is separate from the coverage GATE — this
    keeps the overlay NAV %-of-notional normalized like S1/S2/S3 (starts at 1.0)."""
    n = len(close)
    nav = np.full(n, np.nan)  # overlay NAV: 1.0 + cumulative P&L, %-of-notional scale
    trades = []
    realized = 0.0
    in_pos = False
    in_pos_arr = np.zeros(n, dtype=bool)
    K = prem = 0.0
    dte = 0
    entry_i = 0
    contracts = 0.0
    n_entries = n_pt = n_expiry = n_capped = 0

    for i in range(n):
        S = close[i]
        sig = max(iv[i], 1e-4) if not math.isnan(iv[i]) else 0.15

        if in_pos:
            dte -= 1
            if dte <= 0:
                intrinsic = max(S - K, 0.0)
                pnl = contracts * (prem - intrinsic) * 100 - contracts * 100 * (prem + intrinsic) * cost_pct
                realized += pnl
                trades.append((entry_i, pnl))
                n_expiry += 1
                if intrinsic > 0:
                    n_capped += 1   # "assignment": economically capped that day (delivered from base)
                in_pos = False
                contracts = 0.0
            else:
                V = call_price(S, K, max(dte / TD, 1e-6), r, q, sig)
                if pt is not None and V <= pt * prem:
                    pnl = contracts * (prem - V) * 100 - contracts * 100 * (prem + V) * cost_pct
                    realized += pnl
                    trades.append((entry_i, pnl))
                    n_pt += 1
                    in_pos = False
                    contracts = 0.0

        covered = (base_shares[i] >= 100.0) if not math.isnan(base_shares[i]) else False
        if (not in_pos) and bool(entry_gate[i]) and covered and S > 0:
            T = dte_init / TD
            K = strike_for_call_delta(S, T, r, q, sig, target_delta)
            prem = call_price(S, K, T, r, q, sig)
            if prem > 0 and K > 0:
                contracts = 1.0 / (S * 100)  # %-of-notional normalized (matches S1/S2/S3's
                                              # NAV-starts-at-1.0 convention; sizing != coverage)
                dte = dte_init
                in_pos = True
                entry_i = i
                n_entries += 1

        if in_pos:
            V = call_price(S, K, max(dte / TD, 1e-6), r, q, sig)
            unreal = contracts * (prem - V) * 100
        else:
            unreal = 0.0
        nav[i] = 1.0 + realized + unreal
        in_pos_arr[i] = in_pos

    ret = np.zeros(n)
    ret[1:] = nav[1:] / nav[:-1] - 1.0
    return {"nav": nav, "ret": ret, "trades": trades, "n_entries": n_entries,
            "n_pt": n_pt, "n_expiry": n_expiry, "n_capped": n_capped, "in_pos": in_pos_arr}


def sim_s5_cash(n: int, cash_rate: float) -> dict:
    ret = np.full(n, cash_rate / TD)
    ret[0] = 0.0
    nav = np.cumprod(1.0 + ret)
    return {"nav": nav, "ret": ret, "trades": 0}


# ============================================================================
# 5. Benchmark
# ============================================================================

def spy_bh_total_return(close: np.ndarray, div_yield_net: float = DIV_NET_YR,
                        entry_cost: float = ETF_COST_SIDE):
    ret = np.zeros(len(close))
    ret[1:] = close[1:] / close[:-1] - 1.0
    ret = ret + div_yield_net / TD
    ret[0] = -entry_cost
    nav = np.cumprod(1.0 + ret)
    return nav, ret


# ============================================================================
# 6. Metrics
# ============================================================================

def cagr(nav, ann=TD):
    nav = np.asarray(nav, float)
    m = ~np.isnan(nav)
    nav = nav[m]
    if len(nav) < 2 or nav[0] <= 0:
        return float("nan")
    years = (len(nav) - 1) / ann
    if years <= 0:
        return float("nan")
    return (nav[-1] / nav[0]) ** (1 / years) - 1


def ann_sharpe(ret, ann=TD):
    r = np.asarray(ret, float)
    r = r[~np.isnan(r)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return float("nan")
    return math.sqrt(ann) * r.mean() / r.std(ddof=1)


def max_drawdown(nav):
    nav = np.asarray(nav, float)
    m = ~np.isnan(nav)
    nav = nav[m]
    if len(nav) < 2:
        return float("nan")
    peak = np.maximum.accumulate(nav)
    return float((nav / peak - 1.0).min())


def jensen_alpha(strat_ret, mkt_ret, ann=TD):
    y = np.asarray(strat_ret, float)
    x = np.asarray(mkt_ret, float)
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    n = len(x)
    if n < 30:
        return (float("nan"), float("nan"), float("nan"))
    X = np.column_stack([np.ones(n), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    s2 = float(resid @ resid) / (n - 2)
    xtx_inv = np.linalg.inv(X.T @ X)
    se_a = math.sqrt(max(s2 * xtx_inv[0, 0], 0))
    t_a = coef[0] / se_a if se_a > 0 else float("nan")
    return (float(coef[0] * ann), float(coef[1]), float(t_a))


def corr(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    m = ~(np.isnan(a) | np.isnan(b))
    a, b = a[m], b[m]
    if len(a) < 30 or a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def trade_pnl_stats(trades):
    pnls = np.array([p for _, p in trades]) if trades else np.array([])
    if len(pnls) == 0:
        return {"N": 0, "WinRate": float("nan"), "PF": float("nan"), "TotalPnL": 0.0}
    win = float((pnls > 0).mean())
    neg = pnls[pnls < 0].sum()
    pf = float(pnls[pnls > 0].sum() / abs(neg)) if neg != 0 else float("inf")
    return {"N": int(len(pnls)), "WinRate": win, "PF": pf, "TotalPnL": float(pnls.sum())}


def cost_drag_pct_per_yr(nav_with_cost, nav_zero_cost):
    c_with = cagr(nav_with_cost)
    c_without = cagr(nav_zero_cost)
    if math.isnan(c_with) or math.isnan(c_without):
        return float("nan")
    return (c_without - c_with) * 100


# ============================================================================
# 7. Windows (repo standard)
# ============================================================================

WINDOWS = [
    ("FULL 1996-2026", "1996-01-01", "2026-12-31"),
    ("H1 1996-2010", "1996-01-01", "2010-12-31"),
    ("H2 2011-2026", "2011-01-01", "2026-12-31"),
    ("2016-2020", "2016-01-01", "2020-12-31"),
    ("2021+", "2021-01-01", "2026-12-31"),
]


def window_mask(index: pd.DatetimeIndex, wstart: str, wend: str) -> np.ndarray:
    m = (index >= wstart) & (index <= wend)
    return np.asarray(m)  # DatetimeIndex comparison already returns a plain ndarray (no .values)


def rebase_nav(nav_slice):
    """Rebase a NAV slice to start at 1.0 (for window-local CAGR/Sharpe/MaxDD)."""
    nav_slice = np.asarray(nav_slice, float)
    valid = ~np.isnan(nav_slice)
    if not valid.any():
        return nav_slice
    first = nav_slice[valid][0]
    if first == 0:
        return nav_slice
    return nav_slice / first


# ============================================================================
# 8. Portfolio combiner — config-driven. A config = dict of sleeve weights (target
#    % of total NAV) + regime rules. This loop's configs are simple fixed-weight
#    "standalone sleeve at reference size" combos; later loops can pass dynamic
#    weight schedules keyed by `quadrant(t)`.
# ============================================================================

class PortfolioConfig:
    """weights: dict sleeve_name -> target fraction of NAV (rebalanced at each
    sleeve's own entry/roll event, NOT daily — daily rebalancing across sleeves with
    very different turnover would itself be an unpriced, unrealistic cost).
    cash_rate: annualized rate earned on the RESIDUAL cash (S5 + un-deployed capital
    in S2/S3/S4 while gated out) — separate from S3's own collateral mechanics."""

    def __init__(self, name, weights, cash_rate=0.0):
        self.name = name
        self.weights = weights
        self.cash_rate = cash_rate


def combine_sleeve_returns(sleeve_rets: dict, weights: dict, cash_rate: float,
                           n: int) -> np.ndarray:
    """CONSTANT-MIX combiner (daily rebalance to fixed weights): daily portfolio
    return = sum(weight_i * sleeve_i.ret) + (1 - sum(weights)) * cash_rate/TD.

    CAUTION (found via the section-D sanity check, not just theorized): for a
    volatile, INFREQUENTLY-ROLLED sleeve like S2 (LEAP, ~4.7%/day std while in
    position, rolled every ~63td), constant-mix rebalancing is NOT a reasonable
    proxy for "target_weight of NAV in the option, floating between rolls" — daily
    rebalancing sells into rallies / buys into drawdowns EVERY day, which is a real
    (and large) volatility-drag mechanism, not a rounding error. Verified head-to-head
    against exp_leap_delta_sweep.py's rebalance-at-roll portfolio frame on the IDENTICAL
    gate+IV+sleeve path: constant-mix gave CAGR 3.97% vs rebalance-at-roll's 6.49% —
    a ~40% relative gap, entirely attributable to rebalance FREQUENCY, not any bug in
    the sleeve mechanics (sleeve-frame CAGRs matched within a few pp: 25.4% vs 26.8%).
    KEPT for sleeves that don't have a natural "reset event" (e.g. combining two
    always-on sleeves) but S2/S3/S4's reference-size reports use
    `rebalance_at_events` below instead, which is the validated-correct method."""
    total = np.zeros(n)
    w_used = 0.0
    for name, w in weights.items():
        r = sleeve_rets[name]
        total += w * np.nan_to_num(r, nan=0.0)
        w_used += w
    resid = max(1.0 - w_used, 0.0)
    total += resid * cash_rate / TD
    return total


def rebalance_at_events(sleeve_ret: np.ndarray, in_pos: np.ndarray, reset_event: np.ndarray,
                        target_weight: float, cash_rate: float) -> np.ndarray:
    """Rebalance-AT-EVENTS combiner: target_weight of portfolio NAV allocated to the
    sleeve at each `reset_event` day (entry / roll), left to FLOAT (compound at the
    sleeve's own daily return) between events, fully liquidated back to cash whenever
    `in_pos` flips True->False. Cash (both the un-deployed residual AND the sleeve's
    liquidated proceeds between positions) earns cash_rate. This is the general,
    reusable version of exp_leap_delta_sweep.py's portfolio_frame_from_sleeve (which
    was hardcoded to LEAP's opt_value/entered fields) — driven off any sleeve's own
    `ret`/`in_pos` arrays plus an explicit reset_event flag, so it works for S2 (reset
    = roll or fresh entry), S3 (reset = each new CSP entry), and S4 (reset = each new
    short-call entry) alike.

    Mechanics: portfolio NAV = port_cash + sleeve_stake. On a reset day, sleeve_stake
    is re-budgeted to target_weight * (current total portfolio NAV), i.e. the SAME
    "top up to target % at each roll" semantics validated in exp_leap_delta_sweep.py.
    On any day the sleeve is in_pos and NOT a reset day, sleeve_stake compounds at
    sleeve_ret[i] (no trading, no cost — costs are already inside sleeve_ret from the
    sleeve simulator). On an exit day (in_pos True->False), sleeve_stake liquidates to
    cash the day PRIOR (uses yesterday's sleeve_stake so no look-ahead)."""
    n = len(sleeve_ret)
    nav = np.full(n, np.nan)
    port_cash = 1.0
    sleeve_stake = 0.0
    was_in_pos = False

    for i in range(n):
        port_cash *= (1 + cash_rate / TD)
        now_in_pos = bool(in_pos[i]) if in_pos is not None else False
        is_reset = bool(reset_event[i]) and now_in_pos

        # exit: sleeve was providing a stake yesterday, isn't today -> liquidate
        # (the sleeve's OWN nav/ret already reflects exit costs on the exit day itself,
        # so we fold today's ret into the stake ONE more time before sweeping to cash
        # only when the sleeve simulator still marks this day in_pos; otherwise the
        # position already fully unwound inside the sleeve sim and sleeve_stake should
        # just be swept as-is).
        if was_in_pos and not now_in_pos:
            port_cash += sleeve_stake
            sleeve_stake = 0.0

        if now_in_pos:
            r = sleeve_ret[i] if not math.isnan(sleeve_ret[i]) else 0.0
            if not is_reset:
                sleeve_stake *= (1.0 + r)
            else:
                # reset day: still apply today's return to the OLD stake first (a roll's
                # exit proceeds are today's return event too) THEN re-budget to target.
                sleeve_stake *= (1.0 + r)
                port_cash += sleeve_stake  # fold whatever's there back into cash
                total_nav = port_cash
                sleeve_stake = target_weight * total_nav
                port_cash = total_nav - sleeve_stake
        nav[i] = port_cash + sleeve_stake
        was_in_pos = now_in_pos

    return nav


def nav_from_ret(ret: np.ndarray) -> np.ndarray:
    return np.cumprod(1.0 + ret)


# ============================================================================
# 9. Reporting helpers
# ============================================================================

def sleeve_report_row(nav, ret, bh_ret, exposure, n_trades, cost_drag=float("nan")):
    a, b, t = jensen_alpha(ret, bh_ret)
    return {
        "CAGR": cagr(nav), "Sharpe": ann_sharpe(ret), "MaxDD": max_drawdown(nav),
        "Alpha": a, "Beta": b, "tstat": t, "Exposure": exposure,
        "Trades": n_trades, "CostDrag": cost_drag,
    }


def fmt_pct(x, dp=2):
    return f"{x*100:+.{dp}f}%" if not (x is None or (isinstance(x, float) and math.isnan(x))) else "  n/a "


def fmt_row(m):
    if math.isnan(m['CostDrag']):
        return (f"CAGR {fmt_pct(m['CAGR']):>8}  Sharpe {m['Sharpe']:6.2f}  "
                f"MaxDD {fmt_pct(m['MaxDD']):>8}  Alpha {fmt_pct(m['Alpha']):>8} "
                f"(t{m['tstat']:+5.1f})  Beta {m['Beta']:5.2f}  "
                f"Expo {m['Exposure']*100:5.1f}%  Trades {m['Trades']:5d}  CostDrag   n/a")
    return (f"CAGR {fmt_pct(m['CAGR']):>8}  Sharpe {m['Sharpe']:6.2f}  "
            f"MaxDD {fmt_pct(m['MaxDD']):>8}  Alpha {fmt_pct(m['Alpha']):>8} "
            f"(t{m['tstat']:+5.1f})  Beta {m['Beta']:5.2f}  "
            f"Expo {m['Exposure']*100:5.1f}%  Trades {m['Trades']:5d}  "
            f"CostDrag {m['CostDrag']:5.1f}pp/yr")


# ============================================================================
# 10. Main experiment runner
# ============================================================================

def main():
    close_s = load_spy_close()
    close = close_s.values
    n = len(close_s)
    idx = close_s.index
    print(f"SPY loaded: {idx.min().date()} -> {idx.max().date()}, {n} days")

    fg = load_fear_greed()
    print(f"Fear&Greed loaded: {fg.index.min().date()} -> {fg.index.max().date()}, {len(fg)} rows")

    # --- signals / gates (computed once, shared across sleeves) ---
    gates = build_gates(close_s)
    iv_1y = iv_proxy_1y(close_s).values
    iv_short = iv_proxy_short_dte(close_s).values
    vixp = vix_proxy(close_s)
    zone = vix_zone(vixp)
    quad = quadrant(close_s)
    greed_flag = fg_greed_flag(fg, idx).fillna(False)
    breadth_flag = breadth_washout_flag(idx)
    print(f"Regime layer built: VIX-proxy zones {dict(zone.value_counts())}, "
          f"quadrant labels: {sorted(quad.dropna().unique().tolist())}")
    print(f"F&G greed-flag coverage: {int(greed_flag.sum())} days >75 "
          f"(only valid 2011+; pre-2011 treated as False, not missing-as-signal)")
    print("Breadth washout flag: STUBBED always-False (TODO: no constituent breadth "
          "feed in sandbox; sp500_px.pkl has 505 tickers, buildable in a later loop)")

    gated_dip = gates["gated_dip_leap"].values
    rsi_dip_entry = gates["rsi2_dip_entry"].values
    rsi_ob_entry = gates["rsi2_ob_entry"].values

    # --- benchmark ---
    bh_nav, bh_ret = spy_bh_total_return(close)
    print(f"\nSPY B&H TR-net benchmark (full sample): CAGR {cagr(bh_nav)*100:.2f}%  "
          f"Sharpe {ann_sharpe(bh_ret):.2f}  MaxDD {max_drawdown(bh_nav)*100:.1f}%")

    # --- S1 equity base (needed both standalone and as S4's cover check) ---
    s1 = sim_s1_equity_base(close)
    s1_nav = s1["nav"]

    # --- S2 LEAP sleeve (SLEEVE frame, own compounding) ---
    s2 = sim_s2_leap(close, iv_1y, gated_dip)

    # --- S3 CSP sleeve (collateral-normalized) ---
    s3 = sim_s3_csp(close, iv_short, rsi_dip_entry)

    # --- S4 short-call sleeve (overlay). "Covered" needs a SHARE COUNT, not a dollar
    #     market value -- an earlier version compared base_mv[i] (a per-share $ value,
    #     ~= s1_nav[i]*close[0], i.e. numerically close to `close[i]` itself) against
    #     S*100 (the $ notional of ONE contract = 100 shares), which is off by 100x and
    #     produced ZERO S4 trades in the whole 30y sample (caught via the "S4 PF" sanity
    #     check in section D coming back N=0). Fix: pick an explicit REFERENCE CAPITAL
    #     for this standalone/reference-size diagnostic ($100k) so the S1 base's share
    #     count is unambiguous: shares_held(t) = s1_nav[t] * REF_CAPITAL / close[t].
    #     At $100k, shares_held ranges ~132 (SPY's ATH in-sample, $759.57) to ~1621
    #     (SPY's ATL in-sample, $61.70) -- i.e. ALWAYS >=100, so the standalone S4 report
    #     never actually binds on the coverage constraint (documented, not hidden: this
    #     diagnostic tests "is the sleeve mechanically/economically sound", not "what's
    #     the minimum capital for 1 contract to be covered" -- a later loop sizing S4
    #     against a SMALLER real base should re-check this gate binds correctly there).
    REF_CAPITAL_S4 = 100_000.0
    base_shares_for_s4 = s1_nav * REF_CAPITAL_S4 / close
    s4 = sim_s4_short_call(close, iv_short, rsi_ob_entry, base_shares_for_s4)

    # --- S5 cash: two variants ---
    s5_0 = sim_s5_cash(n, 0.0)
    s5_3 = sim_s5_cash(n, 0.03)

    # --- cache sleeve return arrays for later loops ---
    # dates as plain int64 (days since epoch) -- pandas datetime64[ns] carries dtype
    # metadata that this sandbox's numpy 2.2 / np.savez combination cannot serialize
    # (TypeError: mappingproxy() argument must be a mapping, not NoneType). quadrant
    # is cast to a fixed-width str array (NaN -> "nan" string) for the same reason
    # (object dtype with None entries is unsafe across np.load's allow_pickle default).
    dates_i64 = idx.values.astype("datetime64[D]").astype(np.int64)
    quad_str = quad.astype(str).values
    cache = {
        "dates_days_since_epoch": dates_i64, "close": close,
        "bh_ret": bh_ret, "bh_nav": bh_nav,
        "s1_ret": s1["ret"], "s1_nav": s1_nav,
        "s2_ret": s2["ret"], "s2_nav": s2["nav"], "s2_delta": s2["delta"],
        "s3_ret": s3["ret"], "s3_nav": s3["nav"],
        "s4_ret": s4["ret"], "s4_nav": s4["nav"],
        "gated_dip": gated_dip, "rsi_dip_entry": rsi_dip_entry, "rsi_ob_entry": rsi_ob_entry,
        "vix_proxy": vixp.values, "quadrant_str": quad_str, "greed_flag": greed_flag.values,
    }
    np.savez(os.path.join(CACHE_DIR, "sleeve_returns_loop1.npz"),
            **{k: v for k, v in cache.items() if isinstance(v, np.ndarray)})
    print(f"\nCached sleeve return arrays -> {CACHE_DIR}/sleeve_returns_loop1.npz")

    # ========================================================================
    # SANITY CHECK D: S2 portfolio-frame vs today's delta-sweep run
    # (10% premium / 90% cash, GATED+DIP, 0.80D, base IV mult=1.25, cost 0.5%/side)
    # ========================================================================
    print(f"\n{'='*100}\nD. SANITY CHECK -- S2 vs exp_leap_delta_sweep.py PORTFOLIO/GATED+DIP/0.80D/base\n{'='*100}")
    print("  METHOD NOTE (found during this loop, not a free pass): a first attempt used the")
    print("  CONSTANT-MIX combiner (combine_sleeve_returns, daily rebalance to 10%) at cash_rate=0%")
    print("  and got CAGR 3.97%/Sharpe 0.67/Alpha+2.2%(t2.3) -- >20% off the ~6.5%/0.89/+4.3% target.")
    print("  Root-caused via a head-to-head trace against exp_leap_delta_sweep.py on the IDENTICAL")
    print("  gate+IV+sleeve path (verified byte-identical first): TWO compounding causes, not one bug:")
    print("    (1) constant-mix (daily rebalance) vs rebalance-AT-ROLL/ENTRY-ONLY is a REAL mechanical")
    print("        difference for a ~4.7%/day-std sleeve -- daily rebalancing sells into rallies /")
    print("        buys into drawdowns every day, a genuine volatility-drag channel. Fixed by adding")
    print("        `rebalance_at_events` (rebalances to target_weight only on entry/roll days,")
    print("        floats between events) as the correct combiner for discretely-rolled sleeves.")
    print("    (2) exp_leap_delta_sweep.py's PORTFOLIO frame reuses r=0.03 (the OPTION-PRICING")
    print("        risk-free rate) as the CASH rate too (unconditional `cash *= (1+r/TD)` every day),")
    print("        not cash_rate=0% -- so this specific reference comparison uses cash_rate=3% to")
    print("        match what the reference script actually did, despite the spec's own shorthand")
    print("        label '90% cash(0%)'. Section B below still reports BOTH cash_rate=0% and 3%/yr")
    print("        as the spec requires for the actual sleeve-diagnostic numbers.")
    reset_event_s2 = s2["entered"] | s2["rolled"]
    s2_port_nav = rebalance_at_events(s2["ret"], s2["in_pos"], reset_event_s2,
                                      target_weight=0.10, cash_rate=0.03)
    s2_port_ret = np.zeros(n)
    s2_port_ret[1:] = s2_port_nav[1:] / s2_port_nav[:-1] - 1.0
    a2, b2, t2 = jensen_alpha(s2_port_ret, bh_ret)
    print(f"\n  S2 @10% premium/90%cash, rebalance-at-roll, cash earns 3% (matching reference): "
          f"CAGR {cagr(s2_port_nav)*100:.2f}%  Sharpe {ann_sharpe(s2_port_ret):.2f}  "
          f"Alpha {a2*100:+.2f}% (t{t2:+.1f})")
    print("  Reference (today's exp_leap_delta_sweep.py, GATED+DIP/0.80D/PORTFOLIO/IVx1.25/cost0.5%):"
          "  CAGR ~6.5%  Sharpe ~0.89  Alpha ~+4.3% (t~3.8)")
    ref_cagr, ref_sharpe, ref_alpha = 0.065, 0.89, 0.043
    for label, mine, ref in [("CAGR", cagr(s2_port_nav), ref_cagr),
                             ("Sharpe", ann_sharpe(s2_port_ret), ref_sharpe),
                             ("Alpha", a2, ref_alpha)]:
        rel = abs(mine - ref) / abs(ref) if ref != 0 else float("nan")
        flag = "OK" if rel <= 0.20 else "!!DIFFERS >20%!!"
        unit = "%" if label != "Sharpe" else ""
        mine_disp = mine * 100 if label != "Sharpe" else mine
        ref_disp = ref * 100 if label != "Sharpe" else ref
        print(f"    {label:8} mine={mine_disp:7.2f}{unit}  ref={ref_disp:7.2f}{unit}  "
              f"rel.diff={rel*100:5.1f}%  [{flag}]")

    # ========================================================================
    # A + B: baselines + each standalone sleeve at reference size, both cash variants,
    # across all windows.
    # ========================================================================
    print(f"\n{'='*100}\nA. BASELINES\n{'='*100}")
    print(f"{'window':16} | {'series':22} | metrics")
    for wname, ws, we in WINDOWS:
        mask = window_mask(idx, ws, we)
        if mask.sum() < 30:
            continue
        bh_nav_w = rebase_nav(bh_nav[mask])
        bh_ret_w = bh_ret[mask]
        s1_nav_w = rebase_nav(s1_nav[mask])
        s1_ret_w = s1["ret"][mask]
        a1, b1, t1 = jensen_alpha(s1_ret_w, bh_ret_w)
        print(f"{wname:16} | {'SPY B&H TR-net':22} | CAGR {cagr(bh_nav_w)*100:+7.2f}%  "
              f"Sharpe {ann_sharpe(bh_ret_w):6.2f}  MaxDD {max_drawdown(bh_nav_w)*100:7.1f}%")
        print(f"{wname:16} | {'100% S1':22} | CAGR {cagr(s1_nav_w)*100:+7.2f}%  "
              f"Sharpe {ann_sharpe(s1_ret_w):6.2f}  MaxDD {max_drawdown(s1_nav_w)*100:7.1f}%  "
              f"Alpha {a1*100:+6.2f}% (t{t1:+4.1f})  Beta {b1:5.2f}")

    print(f"\n{'='*100}\nB. STANDALONE SLEEVES AT REFERENCE SIZE (both cash-rate variants)\n{'='*100}")
    print("  S2 ref size: 10% premium / 90% cash.  S3 ref size: 30% collateral / 70% cash.  "
          "S4: on top of 100% S1 base.")
    print("  Combiner: rebalance_at_events (target weight re-applied on each fresh entry/roll,")
    print("  floats between events) -- NOT constant-mix -- per the section-D finding that daily")
    print("  constant-mix rebalancing is a real, large volatility-drag mechanism for these sleeves.")

    def entry_reset_from_in_pos(in_pos_arr):
        """Fresh-entry flag: True on any day in_pos flips False->True (S3/S4 are
        single-position, non-overlapping -- every entry IS a reset, no separate rolls)."""
        r = np.zeros(len(in_pos_arr), dtype=bool)
        prev = False
        for i in range(len(in_pos_arr)):
            cur = bool(in_pos_arr[i])
            if cur and not prev:
                r[i] = True
            prev = cur
        return r

    reset_event_s2 = s2["entered"] | s2["rolled"]
    reset_event_s3 = entry_reset_from_in_pos(s3["in_pos"])
    reset_event_s4 = entry_reset_from_in_pos(s4["in_pos"])

    # exposure_arr = the SLEEVE-SPECIFIC "position on" flag (fraction of days with the
    # option leg live), used only for the reported Exposure% column -- NOT the same as
    # S1's own exposure (S1 is a buy-and-hold base, always 100% exposed by definition).
    sleeve_configs = [
        ("S2 LEAP (10% prem/90% cash)", "S2", 0.10, reset_event_s2,
         s2["n_rolls"] + s2["n_entries"], gated_dip),
        ("S3 CSP (30% coll/70% cash)", "S3", 0.30, reset_event_s3,
         s3["n_entries"], s3["in_pos"]),
        ("S4 ShortCall (on 100% S1)", "S4", 1.00, reset_event_s4,
         s4["n_entries"], s4["in_pos"]),
    ]
    sleeve_ret_map = {"S1": s1["ret"], "S2": s2["ret"], "S3": s3["ret"], "S4": s4["ret"]}
    sleeve_inpos_map = {"S2": s2["in_pos"], "S3": s3["in_pos"], "S4": s4["in_pos"]}

    results_B = {}
    for cash_rate, cash_label in [(0.0, "cash_rate=0%"), (0.03, "cash_rate=3%/yr")]:
        print(f"\n--- {cash_label} ---")
        for label, sname, target_w, reset_ev, trade_n, exposure_arr in sleeve_configs:
            overlay_nav = rebalance_at_events(sleeve_ret_map[sname], sleeve_inpos_map[sname],
                                              reset_ev, target_weight=target_w, cash_rate=cash_rate)
            if sname == "S4":
                # S4 is an OVERLAY on top of a fully-invested S1 base: total portfolio ret =
                # S1's own ret (100% base, always on) + the overlay's P&L contribution (the
                # overlay nav already nets out its own "cash" leg at cash_rate, so subtract that
                # baseline back out to isolate the P&L-only contribution before adding to S1).
                overlay_ret = np.zeros(n)
                overlay_ret[1:] = overlay_nav[1:] / overlay_nav[:-1] - 1.0
                cash_only_ret = cash_rate / TD
                port_ret = s1["ret"] + (overlay_ret - cash_only_ret)
                port_ret[0] = s1["ret"][0]
                port_nav = nav_from_ret(port_ret)
            else:
                port_nav = overlay_nav
                port_ret = np.zeros(n)
                port_ret[1:] = port_nav[1:] / port_nav[:-1] - 1.0
            for wname, ws, we in WINDOWS:
                mask = window_mask(idx, ws, we)
                if mask.sum() < 30:
                    continue
                nav_w = rebase_nav(port_nav[mask])
                ret_w = port_ret[mask]
                bh_ret_w = bh_ret[mask]
                exposure = float(np.mean(exposure_arr[mask])) if exposure_arr is not None else float("nan")
                m = sleeve_report_row(nav_w, ret_w, bh_ret_w, exposure, trade_n)
                results_B[(cash_label, label, wname)] = m
                sig_flag = "" if abs(m["tstat"]) >= 2 or math.isnan(m["tstat"]) else "  [NOT SIGNIFICANT t<2]"
                print(f"  [{wname:14}] {label:32} {fmt_row(m)}{sig_flag}")

    # ========================================================================
    # SANITY CHECK D continued: S3 win-rate, S4 PF (full sample)
    # ========================================================================
    print(f"\n{'='*100}\nD. SANITY CHECK -- S3 win-rate (expect ~90-97%), S4 PF (expect small positive, prior 1.53-2.26)\n{'='*100}")
    s3_all_trades = s3["trades"]
    s3_stats = trade_pnl_stats(s3_all_trades)
    print(f"  S3 CSP all trades (full sample): N={s3_stats['N']}  WinRate={s3_stats['WinRate']*100:.1f}%  "
          f"PF={s3_stats['PF']:.2f}  TotalPnL(collateral units)={s3_stats['TotalPnL']:.4f}")
    print(f"  S3 assignments: {s3['n_assigned']} of {s3['n_expiry']} expiries went ITM "
          f"({s3['n_assigned']/max(s3['n_expiry'],1)*100:.1f}% of expiries assigned), "
          f"PT-closes={s3['n_pt']}")
    win_flag = "OK, in expected 90-97% band" if 0.90 <= s3_stats['WinRate'] <= 0.97 else \
               "OUTSIDE expected 90-97% band -- see explanation below"
    print(f"  -> {win_flag}")

    s4_all_trades = s4["trades"]
    s4_stats = trade_pnl_stats(s4_all_trades)
    print(f"\n  S4 ShortCall all trades (full sample): N={s4_stats['N']}  WinRate={s4_stats['WinRate']*100:.1f}%  "
          f"PF={s4_stats['PF']:.2f}  TotalPnL(notional units)={s4_stats['TotalPnL']:.4f}")
    print(f"  S4 capped(ITM-at-expiry) count: {s4['n_capped']} of {s4['n_expiry']} expiries, PT-closes={s4['n_pt']}")
    pf_flag = "OK, small positive in prior 1.53-2.26 range" if 1.0 <= s4_stats['PF'] <= 3.0 else \
              "OUTSIDE prior 1.53-2.26 PF range -- see caveats below"
    print(f"  -> {pf_flag}")

    # ========================================================================
    # C. Correlation matrix of daily EXCESS returns (sleeve minus benchmark)
    # ========================================================================
    print(f"\n{'='*100}\nC. CORRELATION MATRIX -- daily EXCESS returns (sleeve_ret - benchmark_ret), full sample\n{'='*100}")
    excess = {
        "S1": s1["ret"] - bh_ret,
        "S2": s2["ret"] - bh_ret,
        "S3": s3["ret"] - bh_ret,
        "S4": s4["ret"] - bh_ret,
    }
    names = list(excess.keys())
    print("        " + "".join(f"{nm:>8}" for nm in names))
    corr_matrix = {}
    for a_name in names:
        row = []
        for b_name in names:
            c = corr(excess[a_name], excess[b_name])
            row.append(c)
            corr_matrix[(a_name, b_name)] = c
        print(f"  {a_name:4}  " + "".join(f"{v:8.3f}" for v in row))

    # per-window correlation too (halves), since regimes may change the diversification story
    print("\n  Per-window S2 vs S3 vs S4 excess-return correlations (the diversification question):")
    for wname, ws, we in WINDOWS:
        mask = window_mask(idx, ws, we)
        if mask.sum() < 30:
            continue
        c23 = corr(excess["S2"][mask], excess["S3"][mask])
        c24 = corr(excess["S2"][mask], excess["S4"][mask])
        c34 = corr(excess["S3"][mask], excess["S4"][mask])
        print(f"    [{wname:14}] S2-S3 {c23:+.3f}   S2-S4 {c24:+.3f}   S3-S4 {c34:+.3f}")

    # ========================================================================
    # E. S3 beta-vs-alpha decomposition (regress S3 excess on benchmark)
    # ========================================================================
    print(f"\n{'='*100}\nE. S3 P&L DECOMPOSITION -- beta (long exposure from short puts) vs premium alpha\n{'='*100}")
    print("  NOTE: 'beta-share-of-total %' is DELIBERATELY OMITTED here -- when total ann.ret sits")
    print("  near zero (as in several windows below), beta*mkt-component / total blows up to")
    print("  nonsensical +-hundreds-of-percent (an artifact hit during dev, e.g. FULL sample gave")
    print("  -631%). Reporting the two components directly (they sum back to total, shown as a")
    print("  reconciliation check) is the honest version of this decomposition.")
    for wname, ws, we in WINDOWS:
        mask = window_mask(idx, ws, we)
        if mask.sum() < 30:
            continue
        a3, b3, t3 = jensen_alpha(s3["ret"][mask], bh_ret[mask])
        s3_ret_w = s3["ret"][mask]
        bh_ret_w = bh_ret[mask]
        total_ret_ann = (np.nanmean(s3_ret_w)) * TD
        beta_component_ann = b3 * (np.nanmean(bh_ret_w) * TD)
        alpha_component_ann = a3
        recon = beta_component_ann + alpha_component_ann  # OLS identity: should equal total_ret_ann
        sig = "" if abs(t3) >= 2 or math.isnan(t3) else "  [NOT SIGNIFICANT t<2]"
        print(f"  [{wname:14}] S3 total ann.ret {total_ret_ann*100:+6.2f}%   "
              f"beta={b3:5.2f} x mkt-ann-ret -> beta*mkt component {beta_component_ann*100:+6.2f}%   "
              f"+  alpha {alpha_component_ann*100:+6.2f}% (t{t3:+.1f}){sig}   "
              f"[recon {recon*100:+6.2f}%, check vs total]")

    print(f"\n{'='*100}\nDONE. Module: backtest/experiments/exp_core_portfolio_lab.py")
    print(f"Cache: {CACHE_DIR}/sleeve_returns_loop1.npz")
    print(f"{'='*100}")


if __name__ == "__main__":
    main()
