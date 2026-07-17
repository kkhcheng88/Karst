"""RSI-2 -- FAITHFUL replication of CONNORS' ORIGINAL config + the control nobody ran -- 2026-07-17.

WHY THIS FILE EXISTS (the third and final attempt at this line)
--------------------------------------------------------------
We have now tested RSI2 dip-buying twice and BOTH times we tested a hybrid that matches NO
published source. Three configs are in play:

                  Connors (his book / video On5v-g_RX8U)   BE 11.1        what we ran (07-16/17)
  trend filter    close > 200SMA  (PART of the strategy)   none           close > 200SMA
  entry           RSI(2) < 5      (DEEP dip)               RSI(2) < 10    RSI(2) < 10
  exit            close > 5-day MA  (1-3 days)             RSI(2) > 90    RSI2>70 or 10 bars

We took Connors' FILTER and BE's ENTRY and neither's EXIT. That hybrid is the "middle" config:
shallow dip + slow exit. Three independent sources say the mechanism runs the OTHER way:
  1. This repo, verbatim (results/2026-07-05_rsi2_capital_efficiency.md, Result 2):
     "Entry<5 vs <10: <5 = deeper dips = higher deployed return at lower exposure"
  2. Connors' book: <5 entry + fast 5MA exit.
  3. The video's hold-time sweep (0-20 days): return-by-exposure falls MONOTONICALLY with hold
     length; best = hold 0 days.
=> DEEP dip + FAST exit = high capital efficiency at low exposure.
   SHALLOW dip + SLOW exit = high exposure, low efficiency.
   We tested the middle twice.

WHAT IS ACTUALLY NEW HERE (our only increment)
----------------------------------------------
Connors did not run a size-matched control. BE did not run one. The video did not run one.
Every one of them benchmarks against buy&hold or against "did it make money", which in a 33-year
bull market is not a control at all. We run the RANDOM SAME-EXPOSURE / SAME-TRADE-COUNT /
SAME-HOLD-LENGTH-DISTRIBUTION Monte Carlo (1000 draws per symbol per arm). Connors' config has to
beat THAT to count as a signal.

  CAVEAT THE USER FLAGGED UP FRONT: exposure here may be <10%. A 10%-exposure random control has
  huge variance, so the MC DISTRIBUTION is reported (p5/p25/p50/p75/p95), not just the median --
  a high percentile on one symbol is not evidence. n_eff (cross-symbol correlation haircut) is
  reported alongside every aggregate p-value.

MEASUREMENT DISCIPLINE (user standing order)
--------------------------------------------
- Primary metric = CAPITAL EFFICIENCY (log PnL / avg exposure) ALWAYS printed next to ABSOLUTE PnL.
- The word "alpha" is banned as a sleeve/signal-level verdict.
- CapEff traps (memory: capital-efficiency-two-traps): (1) a tiny denominator inflates the ratio --
  this arm set is BUILT to trip that trap, hence absolute PnL is mandatory; (2) on LOSING books the
  ranking INVERTS -- so CapEff ranking is suppressed for any arm with negative PnL.
- Verdict basis = the random same-exposure control. NOT buy&hold (B&H = 100% exposure, printed as
  background only).

Run: PYTHONUTF8=1 python backtest/experiments/exp_rsi2_connors.py
"""
from __future__ import annotations

import math
import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load

# ===========================================================================
# FROZEN CONFIG -- every line below was written BEFORE any return was looked at.
# ===========================================================================
SINCE = "1990-01-01"          # video's stated window start; each symbol uses what data allows.
START_EQUITY = 10_000.0
N_SIMS = 1000
SEED = 20260717
MIN_ROWS = 500
COSTS_BP = [0, 5, 10, 20]

# Execution convention, IDENTICAL for every arm (declared, no look-ahead):
#   signal seen at CLOSE i  ->  ENTER at OPEN i+1   (the video's own look-ahead fix)
#   exit condition seen at CLOSE j -> EXIT at CLOSE j (market-on-close; Connors' book rule)
# Note this differs from exp_rsi2_be_replication.py (close-entry, next-close exit). Held constant
# across all arms here, so the ladder comparison is internally consistent; absolute levels are not
# directly comparable to that file.

ARMS = {
    # name              trend   entry  exit_kind  exit_rsi  cap   stop200
    "Connors":          dict(trend=True,  entry=5,  exit_kind="ma5",  exit_rsi=None, cap=None, stop200=False),
    "Connors-nofilter": dict(trend=False, entry=5,  exit_kind="ma5",  exit_rsi=None, cap=None, stop200=False),
    "Connors-0day":     dict(trend=True,  entry=5,  exit_kind="zero", exit_rsi=None, cap=None, stop200=False),
    "BE-faithful":      dict(trend=False, entry=10, exit_kind="rsi",  exit_rsi=90,   cap=None, stop200=False),
    "ours-broken":      dict(trend=True,  entry=10, exit_kind="rsi",  exit_rsi=70,   cap=10,   stop200=False),
    # --- probes of the video's two extra claims (declared as arms 6-7 for multiple-comparison count)
    "Connors-stop200":  dict(trend=True,  entry=5,  exit_kind="ma5",  exit_rsi=None, cap=None, stop200=True),
}
MAIN_ARMS = ["Connors", "Connors-nofilter", "Connors-0day", "BE-faithful", "ours-broken"]

# The 5-arm ladder above CONFOUNDS the entry axis with the exit axis: "Connors" is <5 AND fast-exit,
# "BE-faithful" is <10 AND slow-exit. It therefore cannot answer the actual question -- "is a DEEPER
# dip more capital-efficient, holding the exit fixed?" (results/2026-07-05_rsi2_capital_efficiency.md
# Result 2: "<5 = deeper dips = higher deployed return at lower exposure"). These 3 extra arms
# complete a clean 2x2 (entry x exit) with the 200SMA filter held constant.
DIAG_ARMS = {
    "F-e5-ma5":    dict(trend=True, entry=5,  exit_kind="ma5", exit_rsi=None, cap=None, stop200=False),  # = Connors
    "F-e10-ma5":   dict(trend=True, entry=10, exit_kind="ma5", exit_rsi=None, cap=None, stop200=False),
    "F-e5-rsi90":  dict(trend=True, entry=5,  exit_kind="rsi", exit_rsi=90,   cap=None, stop200=False),
    "F-e10-rsi90": dict(trend=True, entry=10, exit_kind="rsi", exit_rsi=90,   cap=None, stop200=False),
}

# The video's own five numbers, for the replication check (SPY, 1990-2026).
VIDEO = dict(cagr=2.9, mdd=12.0, signals=235, trades=146, wr=81.2)

TIER1 = ["SPY", "QQQ"]
# The 85 US-listed watch tickers behind Karst's 17 active themes.
# Source: thesis/.raw/ima_triage_query.md (verbatim, deduped against TIER1).
# SURVIVORSHIP BIAS DECLARED: this is TODAY's watchlist = known survivors. See report section 9.
THEME = """AAOI AEHR AMKR AMZN ASML ASTS ASX ATI AVGO AXTI BE BKSY CAT CHPX CLS COHR COP CRS CVX
DRAM EQT ETN FN FORM FOTO FSLR GEV GLW GNRC GOOGL GRID GSAT HEI INTC KLAC KLIC KMI KTOS LITE LNG
LOAR LPX LRCX LUNR LWLG MAGS META MKSI MP MPWR MRVL MSFT MU NASA NVTS ON PL PWR REMX RKLB RDW SEI
SIVE SKHY SMH SNDK SPCX SPXC STX TER TSM TTMI TXN URA USAC USAR UTES VICR VRT WDC WOLF WST XLE
XOM""".split()
UNIVERSE = TIER1 + [t for t in THEME if t not in TIER1]

CACHE = os.path.join(tempfile.gettempdir(), "karst_rsi2_connors_cache")


# ===========================================================================
# Indicators / data
# ===========================================================================
def rsi(s: pd.Series, n: int = 2) -> pd.Series:
    """Wilder RSI -- same implementation as every prior RSI2 script in this repo."""
    d = s.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    ru = up.ewm(alpha=1 / n, adjust=False).mean()
    rd = dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + ru / rd)


def get_prices(sym: str, adjusted: bool) -> pd.DataFrame | None:
    os.makedirs(CACHE, exist_ok=True)
    fp = os.path.join(CACHE, f"{sym}_{'adj' if adjusted else 'raw'}.pkl")
    if os.path.exists(fp):
        try:
            return pd.read_pickle(fp)
        except Exception:
            pass
    try:
        px = load(sym, adjusted=adjusted, min_rows=200)[["open", "close"]]
    except Exception:
        return None
    px.to_pickle(fp)
    return px


def prepare(sym: str, adjusted: bool = True, since: str = SINCE,
            until: str | None = None) -> dict | None:
    """Indicators on FULL history, then slice, so the 200SMA is warm at `since` when the symbol has
    older data. Symbols whose history starts inside the window get NaN SMA early -> the trend filter
    blocks entries there (realistic: you cannot apply a filter you cannot compute)."""
    px = get_prices(sym, adjusted)
    if px is None:
        return None
    px = px.dropna()
    c, o = px["close"], px["open"]
    df = pd.DataFrame({
        "o": o, "c": c,
        "r2": rsi(c, 2),
        "ma5": c.rolling(5).mean(),
        "sma": c.rolling(200).mean(),
    })
    df = df[df.index >= since]
    if until:
        df = df[df.index < until]
    df = df[df["r2"].notna() & df["ma5"].notna()]
    if len(df) < MIN_ROWS:
        return None
    lc, lo = np.log(df["c"].values), np.log(df["o"].values)
    return dict(
        sym=sym, n=len(df),
        o=df["o"].values, c=df["c"].values, r2=df["r2"].values,
        ma5=df["ma5"].values, sma=df["sma"].values,
        lc=lc, lo=lo,
        cc=np.diff(lc, prepend=lc[0]),          # close-to-close log return (for B&H + rho)
        start=df.index[0], end=df.index[-1],
        years=(df.index[-1] - df.index[0]).days / 365.25,
        index=df.index,
    )


# ===========================================================================
# Trade generation
# ===========================================================================
def gen_trades(d: dict, trend: bool, entry: float, exit_kind: str, exit_rsi: float | None,
               cap: int | None, stop200: bool, short: bool = False) -> tuple[list, int]:
    """Returns (trades, n_signals). A trade is (e, x): bought at OPEN of bar e, sold at CLOSE of
    bar x. Bars e..x inclusive are 'in position' (hold length = x - e days).
    n_signals counts every bar whose close met the entry condition -- including ones ignored because
    a position was already open. (The video reports 235 signals -> 146 trades; that gap IS this.)"""
    n, r2, c, ma5, sma = d["n"], d["r2"], d["c"], d["ma5"], d["sma"]
    out: list[tuple[int, int]] = []
    # count signals independently of position state
    if short:
        sig = (r2 > entry) & np.isfinite(sma) & (c > sma) if trend else (r2 > entry)
    else:
        sig = (r2 < entry) & np.isfinite(sma) & (c > sma) if trend else (r2 < entry)
    n_signals = int(sig[:n - 1].sum())          # last bar can't be entered (no next open)

    i = 0
    while i < n - 1:
        if not sig[i]:
            i += 1
            continue
        e = i + 1                                # entry executed at OPEN of bar e
        if exit_kind == "zero":
            x = e                                # sell at the CLOSE of the entry bar
        else:
            x = n - 1                            # fallback: forced close at the last bar
            for j in range(e, n):
                if exit_kind == "ma5":
                    hit = (c[j] < ma5[j]) if short else (c[j] > ma5[j])
                else:                            # "rsi"
                    hit = (r2[j] < 100 - exit_rsi) if short else (r2[j] > exit_rsi)
                if hit:
                    x = j
                    break
                if stop200 and np.isfinite(sma[j]) and c[j] < sma[j]:
                    x = j                        # stop-loss: close below the 200SMA
                    break
                if cap is not None and (j - e) >= cap:
                    x = j
                    break
        out.append((e, x))
        i = x                                    # earliest re-signal is the exit bar's own close
    return out, n_signals


def daily_logrets(d: dict, trades: list, short: bool = False) -> np.ndarray:
    """Per-bar log return of the strategy: 0 while flat; on entry bar e it is log(c_e/o_e); on bars
    e+1..x it is the close-to-close return. Sums to log(c_x/o_e) per trade, by construction."""
    r = np.zeros(d["n"])
    s = -1.0 if short else 1.0
    for e, x in trades:
        r[e] = s * (d["lc"][e] - d["lo"][e])
        if x > e:
            r[e + 1:x + 1] = s * d["cc"][e + 1:x + 1]
    return r


def trade_rets(d: dict, trades: list, short: bool = False) -> np.ndarray:
    s = -1.0 if short else 1.0
    return np.array([math.exp(s * (d["lc"][x] - d["lo"][e])) - 1.0 for e, x in trades])


def maxdd(eq: np.ndarray) -> float:
    peak = np.maximum.accumulate(eq)
    return float(np.max((peak - eq) / peak)) if len(eq) else 0.0


def evaluate(d: dict, trades: list, n_signals: int = 0, cost_bp: float = 0.0,
             short: bool = False) -> dict:
    n = d["n"]
    if not trades:
        return dict(trades=0, signals=n_signals, pnl=0.0, ret=0.0, cagr=0.0, logret=0.0,
                    exposure=0.0, capeff=float("nan"), wr=float("nan"), mdd=0.0, tpy=0.0,
                    avg_hold=float("nan"), med_trade=float("nan"), pf=float("nan"))
    r = trade_rets(d, trades, short) - cost_bp / 10_000.0
    dr = daily_logrets(d, trades, short)
    inpos = np.zeros(n)
    for e, x in trades:
        inpos[e:x + 1] = 1.0
    eq = START_EQUITY * np.exp(np.cumsum(dr))
    if cost_bp:
        for _, x in trades:
            eq[x:] *= (1.0 - cost_bp / 10_000.0)
    final = START_EQUITY * float(np.prod(1.0 + r))
    exposure = float(inpos.mean())
    lg = math.log(max(final / START_EQUITY, 1e-9))
    wins, losses = r[r > 0], r[r <= 0]
    pf = (wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else float("inf")
    return dict(
        trades=len(trades), signals=n_signals,
        pnl=final - START_EQUITY, ret=final / START_EQUITY - 1.0,
        cagr=(final / START_EQUITY) ** (1 / d["years"]) - 1.0 if final > 0 else float("nan"),
        logret=lg, exposure=exposure,
        capeff=(lg / exposure) if exposure > 0 else float("nan"),
        wr=float((r > 0).mean()), mdd=maxdd(eq), tpy=len(trades) / d["years"],
        avg_hold=float(np.mean([x - e for e, x in trades])),
        med_trade=float(np.median(r)), pf=float(pf),
    )


# ===========================================================================
# THE CONTROL NOBODY RAN: random entry, IDENTICAL exposure / trade count / hold distribution.
# Fully vectorised over sims. This -- not B&H -- is the verdict basis.
# ===========================================================================
def random_control(d: dict, trades: list, rng: np.random.Generator, n_sims: int = N_SIMS,
                   short: bool = False) -> dict:
    nan = dict(pct=float("nan"), p5=float("nan"), p25=float("nan"), p50=float("nan"),
               p75=float("nan"), p95=float("nan"), med_capeff=float("nan"),
               actual_logret=float("nan"), frac_beat=float("nan"))
    if not trades:
        return nan
    durs = np.array([x - e for e, x in trades])          # hold length in extra bars
    lens = durs + 1                                       # bars occupied
    n, K, total = d["n"], len(trades), int(lens.sum())
    slack = n - total
    if slack <= 0:
        return nan
    s = -1.0 if short else 1.0
    lc, lo = d["lc"], d["lo"]

    dd = rng.permuted(np.tile(durs, (n_sims, 1)), axis=1)          # (S,K) shuffled hold lengths
    ll = dd + 1
    off = np.cumsum(ll, axis=1) - ll                               # space already consumed
    starts = np.sort(rng.integers(0, slack + 1, size=(n_sims, K)), axis=1) + off
    ends = starts + dd
    sims = (s * (lc[ends] - lo[starts])).sum(axis=1)               # (S,) total log return

    actual = float(np.sum([s * (lc[x] - lo[e]) for e, x in trades]))
    exposure = total / n
    return dict(
        pct=float((sims < actual).mean() * 100.0),
        p5=float(np.percentile(sims, 5)), p25=float(np.percentile(sims, 25)),
        p50=float(np.median(sims)), p75=float(np.percentile(sims, 75)),
        p95=float(np.percentile(sims, 95)),
        med_capeff=float(np.median(sims) / exposure),
        actual_logret=actual,
        frac_beat=float((sims >= actual).mean()),
        mu=float(sims.mean()), sd=float(sims.std(ddof=1)),
    )


def binom_p_two_sided(k: int, n: int) -> float:
    if n == 0:
        return float("nan")
    probs = [math.comb(n, i) * 0.5 ** n for i in range(n + 1)]
    return float(min(1.0, 2 * min(sum(probs[:k + 1]), sum(probs[k:]))))


# ===========================================================================
# CONTROL B: random ENTRY, SAME exit rule. Isolates the entry signal.
# ---------------------------------------------------------------------------
# Control A randomises entry AND replays a fixed hold length. But this strategy's exit is itself a
# timing rule -- "sell when close pops back over the 5-day MA" exits at a short-term local high BY
# CONSTRUCTION. So Control A cannot tell "RSI2<5 picks good entries" apart from "the MA5 exit picks
# good exits". Control B keeps the exit rule and replaces ONLY the entry with a coin flip at the same
# trade count. If RSI2<5 carries entry information, it must beat THIS too.
# Exposure is NOT pinned here (it is an OUTCOME of the exit rule) -> exposure is reported alongside.
# ===========================================================================
def make_exit_bar(d: dict, exit_kind: str, exit_rsi: float | None, cap: int | None,
                  stop200: bool) -> np.ndarray:
    """exit_bar[b] = the bar a trade ENTERED at bar b would exit on. Same semantics as gen_trades'
    inner scan, precomputed so random-entry sims are cheap."""
    n = d["n"]
    if exit_kind == "zero":
        return np.arange(n)
    hit = (d["c"] > d["ma5"]) if exit_kind == "ma5" else (d["r2"] > exit_rsi)
    if stop200:
        hit = hit | (np.isfinite(d["sma"]) & (d["c"] < d["sma"]))
    idx = np.where(hit, np.arange(n), n)
    eb = np.minimum.accumulate(idx[::-1])[::-1]        # first hit at or after each bar
    eb = np.minimum(eb, n - 1)                         # never triggered -> forced close at last bar
    if cap is not None:
        eb = np.minimum(eb, np.arange(n) + cap)
        eb = np.minimum(eb, n - 1)
    return eb


def random_entry_same_exit(d: dict, eb: np.ndarray, K: int, rng: np.random.Generator,
                           n_sims: int = N_SIMS) -> dict:
    n, lc, lo = d["n"], d["lc"], d["lo"]
    rets, expos, ks = np.empty(n_sims), np.empty(n_sims), np.empty(n_sims)
    for s in range(n_sims):
        starts = np.sort(rng.choice(n - 1, size=min(K, n - 1), replace=False))
        tot, bars, cnt, last_x = 0.0, 0, 0, -1
        for b in starts:
            if b <= last_x:
                continue                                # already in a position -> signal ignored
            x = int(eb[b])
            tot += lc[x] - lo[b]
            bars += x - b + 1
            cnt += 1
            last_x = x
        rets[s], expos[s], ks[s] = tot, bars / n, cnt
    return dict(med_ret=float(np.median(rets)), p95=float(np.percentile(rets, 95)),
                p5=float(np.percentile(rets, 5)), med_expo=float(np.median(expos)),
                med_k=float(np.median(ks)), rets=rets)


# ===========================================================================
# CONTROL C: SYNCHRONISED calendar shift -- the honest cross-sectional null.
# ---------------------------------------------------------------------------
# The aggregate "% of symbols beating random" needs a correlation haircut, and the n_eff formula
# fed with DAILY-RETURN correlation is only a proxy -- it is almost certainly too harsh, because a
# percentile is a WITHIN-symbol relative measure that cancels most of the common market factor.
# Rather than guess the haircut, we MEASURE it: shift every symbol's whole trade set backwards by
# the SAME delta trading days (all symbols share the 2026-07-16 end date, so position-from-the-end
# is a common calendar) and recompute the aggregate statistic. The spread of that aggregate under
# the null gives an EMPIRICAL n_eff -- no proxy, correlation included by construction.
# Limitation (declared): a symbol wraps circularly when the shift exceeds its own history, which
# desynchronises short-history names.
# ===========================================================================
def sync_shift_null(per_sym: list, deltas: np.ndarray) -> np.ndarray:
    """per_sym: list of (e_arr, d_arr, lc, lo, n, mu, sd). Returns (S,) mean-z under the shift null."""
    S = len(deltas)
    acc = np.zeros((S, len(per_sym)))
    for k, (e_arr, d_arr, lc, lo, n, mu, sd) in enumerate(per_sym):
        M = n - int(d_arr.max()) - 1
        if M <= 1 or sd <= 0:
            acc[:, k] = np.nan
            continue
        new_e = (e_arr[None, :] - deltas[:, None]) % M      # one common wrap point per symbol
        X = (lc[new_e + d_arr[None, :]] - lo[new_e]).sum(axis=1)
        acc[:, k] = (X - mu) / sd
    return np.nanmean(acc, axis=1)


# ===========================================================================
# Main
# ===========================================================================
def main() -> None:
    rng = np.random.default_rng(SEED)
    print(f"=== RSI-2 CONNORS replication + random same-exposure control | since {SINCE} | "
          f"${START_EQUITY:,.0f}/sym | {N_SIMS} sims | seed {SEED} ===")
    print("Execution: signal at CLOSE i -> BUY at OPEN i+1 (video's look-ahead fix); "
          "exit condition at CLOSE j -> SELL at CLOSE j (MOC).\n")

    # -----------------------------------------------------------------
    # [1] REPLICATE THE VIDEO'S FIVE NUMBERS. Three data variants, because the video's
    #     "SPY 1990" is impossible: SPY did not exist before 1993-01-29.
    # -----------------------------------------------------------------
    print("--- [1] REPLICATING THE VIDEO'S SPY NUMBERS (Connors arm: >200SMA, RSI2<5, exit c>MA5) ---")
    print(f"  video reports: CAGR {VIDEO['cagr']}% | MDD ~{VIDEO['mdd']}% | "
          f"{VIDEO['signals']} signals -> {VIDEO['trades']} trades | WR {VIDEO['wr']}%\n")
    print(f"  {'variant':<26}{'window':<24}{'yrs':>5}{'sig':>5}{'trd':>5}{'WR%':>6}{'CAGR%':>7}"
          f"{'MDD%':>6}{'expo%':>7}{'PnL$':>10}{'CapEff':>7}")
    rep = {}
    for label, sym, adj in [("SPY raw close (no div)", "SPY", False),
                            ("SPY total-return (div)", "SPY", True),
                            ("^GSPC index 1990 (no div)", "^GSPC", False)]:
        d = prepare(sym, adjusted=adj)
        if d is None:
            print(f"  {label:<26}  (no data)")
            continue
        tr, nsig = gen_trades(d, **ARMS["Connors"])
        m = evaluate(d, tr, nsig)
        rep[label] = (d, tr, m)
        print(f"  {label:<26}{str(d['start'].date()) + '->' + str(d['end'].date()):<24}"
              f"{d['years']:>5.1f}{m['signals']:>5}{m['trades']:>5}{m['wr'] * 100:>6.1f}"
              f"{m['cagr'] * 100:>7.2f}{m['mdd'] * 100:>6.1f}{m['exposure'] * 100:>7.1f}"
              f"{m['pnl']:>10,.0f}{m['capeff'] * 100:>7.0f}")
    print("\n  -> Compare each row against the video line above. Differences are explained in the")
    print("     report (data vendor / dividend treatment / SPY's 1993 inception / exit timing).")

    # -----------------------------------------------------------------
    # [2] SPY: the full MC distribution, not just a percentile. Exposure is ~10% -> huge variance.
    # -----------------------------------------------------------------
    print("\n--- [2] SPY: FULL RANDOM-CONTROL DISTRIBUTION (the number nobody ran) ---")
    print(f"  {'arm':<17}{'expo%':>7}{'actual':>9}{'rnd p5':>9}{'rnd p25':>9}{'rnd p50':>9}"
          f"{'rnd p75':>9}{'rnd p95':>9}{'pctile':>8}{'p(1-tail)':>10}")
    d_spy = prepare("SPY", adjusted=True)
    for arm in MAIN_ARMS:
        tr, nsig = gen_trades(d_spy, **ARMS[arm])
        m = evaluate(d_spy, tr, nsig)
        ctl = random_control(d_spy, tr, rng)
        print(f"  {arm:<17}{m['exposure'] * 100:>7.1f}{ctl['actual_logret']:>9.3f}"
              f"{ctl['p5']:>9.3f}{ctl['p25']:>9.3f}{ctl['p50']:>9.3f}{ctl['p75']:>9.3f}"
              f"{ctl['p95']:>9.3f}{ctl['pct']:>8.1f}{ctl['frac_beat']:>10.3f}")
    print("  (actual / rnd = TOTAL LOG RETURN over the window. Read the SPREAD p5->p95: at ~10%")
    print("   exposure the random control is enormously wide, so a single percentile proves little.)")

    # -----------------------------------------------------------------
    # [3] Load the universe.
    # -----------------------------------------------------------------
    data, dropped = {}, []
    for sym in UNIVERSE:
        d = prepare(sym, adjusted=True)
        if d:
            data[sym] = d
        else:
            dropped.append(sym)
    print(f"\n--- [3] UNIVERSE: {len(UNIVERSE)} requested -> {len(data)} usable, "
          f"{len(dropped)} dropped (<{MIN_ROWS} bars / no data): {' '.join(dropped)}")
    print(f"  median history {np.median([d['years'] for d in data.values()]):.1f} yr; "
          f"windows are HETEROGENEOUS (each symbol uses its own full history since {SINCE}).")

    rows = []
    trade_store: dict = {}                # (sym, arm) -> (trades, ctl mu/sd) for controls B and C
    for sym, d in data.items():
        for arm, cfg in ARMS.items():
            tr, nsig = gen_trades(d, **cfg)
            m = evaluate(d, tr, nsig)
            ctl = random_control(d, tr, rng)
            trade_store[(sym, arm)] = (tr, ctl)
            rec = dict(sym=sym, arm=arm, years=d["years"],
                       bh_ret=math.exp(d["lc"][-1] - d["lc"][0]) - 1.0,
                       bh_log=float(d["lc"][-1] - d["lc"][0]), **m,
                       mc_pct=ctl["pct"], mc_med_capeff=ctl["med_capeff"],
                       mc_p50=ctl["p50"], mc_p5=ctl["p5"], mc_p95=ctl["p95"])
            for cb in COSTS_BP:
                rec[f"pnl_{cb}bp"] = evaluate(d, tr, nsig, cost_bp=cb)["pnl"]
            rows.append(rec)
    df = pd.DataFrame(rows)

    # -----------------------------------------------------------------
    # [4] THE LADDER. CapEff and ABSOLUTE PnL side by side, always (trap #1 + #2).
    # -----------------------------------------------------------------
    print("\n--- [4] FIVE-ARM LADDER: deep-dip/fast-exit vs shallow-dip/slow-exit ---")
    print(f"  {'arm':<17}{'n':>4}{'%prof':>7}{'medPnL$':>9}{'meanPnL$':>10}{'medCapEff':>10}"
          f"{'expo%':>7}{'WR%':>6}{'hold':>6}{'tr/yr':>7}{'MDD%':>6}{'medCAGR%':>9}")
    for arm in ARMS:
        a = df[df["arm"] == arm]
        neg = (a["pnl"] <= 0).any()
        ce = f"{a['capeff'].median() * 100:>10.0f}" + ("*" if neg else " ")
        print(f"  {arm:<17}{len(a):>4}{(a['pnl'] > 0).mean() * 100:>7.1f}{a['pnl'].median():>9,.0f}"
              f"{a['pnl'].mean():>10,.0f}{ce}{a['exposure'].mean() * 100:>6.1f}"
              f"{a['wr'].mean() * 100:>6.1f}{a['avg_hold'].mean():>6.1f}{a['tpy'].mean():>7.1f}"
              f"{a['mdd'].mean() * 100:>6.1f}{a['cagr'].median() * 100:>9.2f}")
    print("  * = this arm contains symbols with NEGATIVE PnL -> CapEff ranking is NOT valid for it")
    print("    (memory: capital-efficiency-two-traps, trap 2 -- a losing book's ratio inverts).")

    # -----------------------------------------------------------------
    # [4c] THE CLEAN 2x2: entry depth x exit speed, 200SMA filter held CONSTANT.
    # This -- not the 5-arm ladder -- is what answers "deep dip + fast exit vs shallow dip + slow
    # exit", because the ladder moves both axes at once.
    # -----------------------------------------------------------------
    print("\n--- [4c] CLEAN 2x2: ENTRY DEPTH x EXIT SPEED (200SMA filter constant) ---")
    print(f"  {'arm':<14}{'entry':<7}{'exit':<9}{'medCapEff':>10}{'medPnL$':>9}{'meanPnL$':>10}"
          f"{'expo%':>7}{'hold':>6}{'WR%':>6}{'tr/yr':>7}{'MDD%':>6}{'meanMCpct':>10}{'%sym>50':>9}")
    diag = {}
    for arm, cfg in DIAG_ARMS.items():
        recs = []
        for sym, d in data.items():
            tr, nsig = gen_trades(d, **cfg)
            m = evaluate(d, tr, nsig)
            ctl = random_control(d, tr, rng, n_sims=400)
            recs.append(dict(**m, mc_pct=ctl["pct"]))
        a = pd.DataFrame(recs)
        diag[arm] = a
        lab_e = f"<{cfg['entry']}"
        lab_x = "c>MA5" if cfg["exit_kind"] == "ma5" else "RSI2>90"
        print(f"  {arm:<14}{lab_e:<7}{lab_x:<9}{a['capeff'].median() * 100:>10.0f}"
              f"{a['pnl'].median():>9,.0f}{a['pnl'].mean():>10,.0f}{a['exposure'].mean() * 100:>7.1f}"
              f"{a['avg_hold'].mean():>6.1f}{a['wr'].mean() * 100:>6.1f}{a['tpy'].mean():>7.1f}"
              f"{a['mdd'].mean() * 100:>6.1f}{a['mc_pct'].mean():>10.1f}"
              f"{(a['mc_pct'] > 50).mean() * 100:>9.1f}")
    print("\n  Entry axis, exit HELD FIXED (this is the 07-05 claim under a clean test):")
    for xl, a5, a10 in [("exit c>MA5", "F-e5-ma5", "F-e10-ma5"),
                        ("exit RSI2>90", "F-e5-rsi90", "F-e10-rsi90")]:
        x5, x10 = diag[a5], diag[a10]
        print(f"    {xl:<13} <5 CapEff {x5['capeff'].median() * 100:>5.0f} @ expo "
              f"{x5['exposure'].mean() * 100:>4.1f}%  vs  <10 CapEff "
              f"{x10['capeff'].median() * 100:>5.0f} @ expo {x10['exposure'].mean() * 100:>4.1f}%"
              f"   -> deeper dip {'WINS' if x5['capeff'].median() > x10['capeff'].median() else 'LOSES'}"
              f" on CapEff; absolute PnL {x5['pnl'].median():>8,.0f} vs {x10['pnl'].median():>8,.0f}")
    print("  Exit axis, entry HELD FIXED:")
    for el, af, asl in [("entry <5", "F-e5-ma5", "F-e5-rsi90"),
                        ("entry <10", "F-e10-ma5", "F-e10-rsi90")]:
        xf, xs = diag[af], diag[asl]
        print(f"    {el:<13} fast CapEff {xf['capeff'].median() * 100:>5.0f} @ expo "
              f"{xf['exposure'].mean() * 100:>4.1f}%  vs  slow CapEff "
              f"{xs['capeff'].median() * 100:>5.0f} @ expo {xs['exposure'].mean() * 100:>4.1f}%"
              f"   -> faster exit {'WINS' if xf['capeff'].median() > xs['capeff'].median() else 'LOSES'}"
              f" on CapEff; absolute PnL {xf['pnl'].median():>8,.0f} vs {xs['pnl'].median():>8,.0f}")
    print("  * CapEff ranking above is only valid where no arm is net-negative; absolute PnL is")
    print("    printed on every line precisely because the ratio inverts on losing books (trap 2).")

    # -----------------------------------------------------------------
    # [4b] DECAY BY ERA -- the question that decides whether Karst can use this AT ALL.
    # Our 07-17 run used 2016+ and found ~nothing; this run uses 1990+ and finds a lot. Execution
    # (section 9b) does NOT explain the gap, and neither does the arm (every arm wins on 1990+).
    # The only remaining difference is the WINDOW. Short-term reversal is documented to have decayed
    # since the 1990s, so a 33-year average may be describing a market that no longer exists.
    # -----------------------------------------------------------------
    print("\n--- [4b] DECAY BY ERA (Connors arm) -- is the edge still alive, or is it the 1990s? ---")
    ERAS = [("1990-1999", "1990-01-01", "2000-01-01"), ("2000-2009", "2000-01-01", "2010-01-01"),
            ("2010-2019", "2010-01-01", "2020-01-01"), ("2020-2026", "2020-01-01", "2026-12-31")]
    print(f"  {'era':<11}{'sym/n':<9}{'trd':>5}{'WR%':>6}{'actual':>9}{'rnd p50':>9}{'rnd p95':>9}"
          f"{'pctile':>8}{'expo%':>7}{'PnL$':>9}{'CAGR%':>7}")
    for label, a0, a1 in ERAS:                                    # SPY, the video's own instrument
        d = prepare("SPY", adjusted=True, since=a0, until=a1)
        if d is None:
            print(f"  {label:<11}{'SPY':<9}  (insufficient bars)")
            continue
        tr, nsig = gen_trades(d, **ARMS["Connors"])
        m = evaluate(d, tr, nsig)
        ctl = random_control(d, tr, rng)
        print(f"  {label:<11}{'SPY':<9}{m['trades']:>5}{m['wr'] * 100:>6.1f}"
              f"{ctl['actual_logret']:>9.3f}{ctl['p50']:>9.3f}{ctl['p95']:>9.3f}{ctl['pct']:>8.1f}"
              f"{m['exposure'] * 100:>7.1f}{m['pnl']:>9,.0f}{m['cagr'] * 100:>7.2f}")
    print()
    for label, a0, a1 in ERAS:                                    # universe-wide, per era
        pcts, zs, nsym = [], [], 0
        for sym in data:
            de = prepare(sym, adjusted=True, since=a0, until=a1)
            if de is None:
                continue
            tr, nsig = gen_trades(de, **ARMS["Connors"])
            if len(tr) < 10:
                continue
            ctl = random_control(de, tr, rng, n_sims=400)
            if not np.isfinite(ctl["pct"]):
                continue
            pcts.append(ctl["pct"])
            if ctl["sd"] > 0:
                zs.append((ctl["actual_logret"] - ctl["mu"]) / ctl["sd"])
            nsym += 1
        if not pcts:
            continue
        k = int((np.array(pcts) > 50).sum())
        print(f"  {label:<11}{f'{nsym} syms':<9}  mean MC pct {np.mean(pcts):>5.1f} | "
              f"%sym>50 {k / nsym * 100:>5.1f} | sign p {binom_p_two_sided(k, nsym):>7.4f} | "
              f"mean Z {np.mean(zs):>5.2f}")
    print("  -> mean Z is the era's effect SIZE in random-control sigmas. A falling Z across eras")
    print("     means the edge is decaying regardless of what the 33-year average says.")

    # -----------------------------------------------------------------
    # [5] EVERY ARM vs ITS OWN RANDOM CONTROL. The verdict table.
    # -----------------------------------------------------------------
    print("\n--- [5] EVERY ARM vs RANDOM SAME-EXPOSURE CONTROL -- THE VERDICT TABLE ---")
    rmat = pd.DataFrame({s: pd.Series(d["cc"], index=d["index"]) for s, d in data.items()}).corr()
    iu = np.triu_indices_from(rmat.values, k=1)
    rho = float(np.nanmean(rmat.values[iu]))
    N = len(data)
    n_eff = N / (1 + (N - 1) * rho)
    print(f"  {'arm':<17}{'meanMCpct':>10}{'medMCpct':>9}{'%sym>50':>8}{'sign p':>8}"
          f"{'actCapEff':>10}{'rndCapEff':>10}{'z(N)':>7}{'z(neff)':>8}{'p(eff)':>8}")
    for arm in ARMS:
        a = df[df["arm"] == arm].dropna(subset=["mc_pct"])
        if not len(a):
            continue
        k = int((a["mc_pct"] > 50).sum())
        mp = a["mc_pct"].mean()
        z_naive = (mp - 50) / (28.87 / math.sqrt(len(a)))
        z_eff = (mp - 50) / (28.87 / math.sqrt(max(n_eff, 1.0)))
        p_eff = math.erfc(abs(z_eff) / math.sqrt(2))
        print(f"  {arm:<17}{mp:>10.1f}{a['mc_pct'].median():>9.1f}{k / len(a) * 100:>8.1f}"
              f"{binom_p_two_sided(k, len(a)):>8.4f}{a['capeff'].median() * 100:>10.0f}"
              f"{a['mc_med_capeff'].median() * 100:>10.0f}{z_naive:>7.2f}{z_eff:>8.2f}{p_eff:>8.3f}")
    print(f"\n  n_eff(proxy): mean pairwise daily-return rho = {rho:.3f} -> N={N} behaves like "
          f"n_eff = {n_eff:.1f} INDEPENDENT names.")
    print(f"  This proxy is almost certainly TOO HARSH -- a percentile is a within-symbol relative")
    print(f"  measure, so it cancels most of the common market factor that rho is measuring.")
    print(f"  Section [5c] MEASURES the real haircut instead of guessing it.")
    print(f"  Multiple comparisons: {len(ARMS)} arms x {N} symbols = {len(ARMS) * N} cells, "
          f"no per-cell correction -> read the sign test / p(eff), never a single cell's percentile.")

    # -----------------------------------------------------------------
    # [5b] CONTROL B: random ENTRY, same MA5/RSI exit. Does the ENTRY signal carry anything?
    # -----------------------------------------------------------------
    print("\n--- [5b] CONTROL B: RANDOM ENTRY + THE ARM'S OWN EXIT RULE (isolates the entry) ---")
    print("  Control A replays a fixed hold length; but 'sell when close pops over the MA5' exits at")
    print("  a local high BY CONSTRUCTION. Control B keeps the exit rule, coin-flips the ENTRY at the")
    print("  same trade count. This asks: is RSI2<5 doing the work, or is the EXIT doing the work?")
    print(f"  {'sym':<6}{'arm':<17}{'actual':>9}{'rndE p5':>9}{'rndE p50':>10}{'rndE p95':>10}"
          f"{'pctile':>8}{'act expo%':>10}{'rnd expo%':>10}")
    for sym in ["SPY", "QQQ", "SMH", "XLE"]:
        if sym not in data:
            continue
        d = data[sym]
        for arm in MAIN_ARMS:
            tr, _ = trade_store[(sym, arm)][0], None
            tr = trade_store[(sym, arm)][0]
            if not tr:
                continue
            cfg = ARMS[arm]
            eb = make_exit_bar(d, cfg["exit_kind"], cfg["exit_rsi"], cfg["cap"], cfg["stop200"])
            cb = random_entry_same_exit(d, eb, len(tr), rng)
            actual = float(np.sum([d["lc"][x] - d["lo"][e] for e, x in tr]))
            expo = sum(x - e + 1 for e, x in tr) / d["n"]
            pct = float((cb["rets"] < actual).mean() * 100)
            print(f"  {sym:<6}{arm:<17}{actual:>9.3f}{cb['p5']:>9.3f}{cb['med_ret']:>10.3f}"
                  f"{cb['p95']:>10.3f}{pct:>8.1f}{expo * 100:>10.1f}{cb['med_expo'] * 100:>10.1f}")
    print("  (If a row's percentile collapses toward 50 here but was high in [5], the EXIT rule --")
    print("   not the RSI2 entry -- was carrying that arm.)")

    # -----------------------------------------------------------------
    # [5c] CONTROL C: synchronised shift -> EMPIRICAL n_eff. Replaces the rho proxy.
    # -----------------------------------------------------------------
    print("\n--- [5c] CONTROL C: SYNCHRONISED CALENDAR-SHIFT NULL -> EMPIRICAL n_eff ---")
    # EXHAUSTIVE grid, not random draws: p(sync) is then an exact randomisation-test p-value over
    # every calendar alignment ("of all N_SHIFT ways to slide the whole trade pattern through
    # history, what fraction match the true alignment?"). Random deltas made n_eff(emp) jump 15.4
    # -> 4.9 between runs; enumeration removes that sampling noise entirely.
    # Honest limit: adjacent shifts give near-identical draws, so the grid's EFFECTIVE resolution is
    # far below N_SHIFT -- read p(sync) as "~1-2%", never as 3 significant figures.
    N_SHIFT = 5000
    deltas = np.arange(1, N_SHIFT + 1)
    print(f"  {'arm':<17}{'actual meanZ':>14}{'null meanZ p50':>16}{'null p95':>10}{'null p99':>10}"
          f"{'p(sync)':>9}{'sd(null)':>10}{'n_eff(emp)':>11}")
    for arm in ARMS:
        per_sym = []
        zs = []
        for sym, d in data.items():
            tr, ctl = trade_store[(sym, arm)]
            if not tr or not np.isfinite(ctl.get("sd", np.nan)) or ctl["sd"] <= 0:
                continue
            e_arr = np.array([e for e, _ in tr])
            d_arr = np.array([x - e for e, x in tr])
            per_sym.append((e_arr, d_arr, d["lc"], d["lo"], d["n"], ctl["mu"], ctl["sd"]))
            zs.append((ctl["actual_logret"] - ctl["mu"]) / ctl["sd"])
        if not per_sym:
            continue
        null_mz = sync_shift_null(per_sym, deltas)
        act_mz = float(np.mean(zs))
        p_sync = float((null_mz >= act_mz).mean())
        sd_null = float(np.nanstd(null_mz, ddof=1))
        n_eff_emp = 1.0 / (sd_null ** 2) if sd_null > 0 else float("nan")
        print(f"  {arm:<17}{act_mz:>14.3f}{np.nanmedian(null_mz):>16.3f}"
              f"{np.nanpercentile(null_mz, 95):>10.3f}{np.nanpercentile(null_mz, 99):>10.3f}"
              f"{p_sync:>9.3f}{sd_null:>10.3f}{n_eff_emp:>11.1f}")
    print("  meanZ = mean across symbols of (actual - random mean)/(random sd), i.e. how many random-")
    print("  control sigmas the arm sits above its own null, averaged over the universe.")
    print("  p(sync) = fraction of synchronised-shift draws whose meanZ >= the actual meanZ. This p")
    print("  ALREADY contains the cross-symbol correlation -- no n_eff haircut is applied on top.")
    print(f"  n_eff(emp) = 1/sd(null meanZ)^2. Compare with the rho proxy's n_eff = {n_eff:.1f}.")

    # -----------------------------------------------------------------
    # [6] Karst-tradeable ETFs, per arm.
    # -----------------------------------------------------------------
    print("\n--- [6] KARST-TRADEABLE ETFs (ETF-only framework) ---")
    print(f"  {'sym':<6}{'arm':<17}{'PnL$':>9}{'CapEff':>7}{'expo%':>7}{'WR%':>6}{'tr/yr':>7}"
          f"{'MDD%':>6}{'MCpct':>7}{'CAGR%':>7}{'B&H%':>10}{'PnL@10bp':>10}")
    for sym in ["SPY", "QQQ", "SMH", "MAGS", "XLE"]:
        for arm in MAIN_ARMS:
            a = df[(df["sym"] == sym) & (df["arm"] == arm)]
            if not len(a):
                continue
            r = a.iloc[0]
            print(f"  {sym:<6}{arm:<17}{r['pnl']:>9,.0f}{r['capeff'] * 100:>7.0f}"
                  f"{r['exposure'] * 100:>7.1f}{r['wr'] * 100:>6.1f}{r['tpy']:>7.1f}"
                  f"{r['mdd'] * 100:>6.1f}{r['mc_pct']:>7.1f}{r['cagr'] * 100:>7.2f}"
                  f"{r['bh_ret'] * 100:>10.1f}{r['pnl_10bp']:>10,.0f}")

    # -----------------------------------------------------------------
    # [7] Cost sensitivity -- Connors-0day churns, so this is a real question for it.
    # -----------------------------------------------------------------
    print("\n--- [7] COST SENSITIVITY (round-trip bp, mean PnL$ across universe) ---")
    print(f"  {'arm':<17}{'tr/yr':>7}" + "".join(f"{f'{c}bp':>11}" for c in COSTS_BP)
          + f"{'0->20bp':>10}{'%prof@20':>10}")
    for arm in ARMS:
        a = df[df["arm"] == arm]
        cells = "".join(f"{a[f'pnl_{c}bp'].mean():>11,.0f}" for c in COSTS_BP)
        print(f"  {arm:<17}{a['tpy'].mean():>7.1f}{cells}"
              f"{a['pnl_20bp'].mean() - a['pnl_0bp'].mean():>10,.0f}"
              f"{(a['pnl_20bp'] > 0).mean() * 100:>10.1f}")

    # -----------------------------------------------------------------
    # [8] The video's claim (a): a 200SMA stop-loss makes every metric worse.
    # -----------------------------------------------------------------
    print("\n--- [8] VIDEO CLAIM (a): does a 200SMA stop-loss make everything worse? ---")
    b = df[df["arm"] == "Connors"].set_index("sym")
    s = df[df["arm"] == "Connors-stop200"].set_index("sym")
    j = b.join(s, lsuffix="_n", rsuffix="_s")
    print(f"  {'metric':<16}{'Connors':>12}{'+stop200':>12}{'delta':>12}{'%sym worse':>12}")
    for lab, kn, mult, worse_if_lower in [
            ("mean PnL $", "pnl", 1, True), ("median PnL $", "pnl", 1, True),
            ("mean CapEff", "capeff", 100, True), ("mean WR %", "wr", 100, True),
            ("mean MDD %", "mdd", 100, False), ("mean expo %", "exposure", 100, None)]:
        agg = (lambda x: x.median()) if lab.startswith("median") else (lambda x: x.mean())
        vn, vs = agg(j[f"{kn}_n"]) * mult, agg(j[f"{kn}_s"]) * mult
        pw = ((j[f"{kn}_s"] < j[f"{kn}_n"]).mean() if worse_if_lower
              else (j[f"{kn}_s"] > j[f"{kn}_n"]).mean()) * 100 if worse_if_lower is not None else float("nan")
        print(f"  {lab:<16}{vn:>12,.1f}{vs:>12,.1f}{vs - vn:>12,.1f}"
              + (f"{pw:>12.1f}" if worse_if_lower is not None else f"{'--':>12}"))

    # -----------------------------------------------------------------
    # [9] The video's claim (b): the reversal (short RSI2>95) still makes money in a bull market.
    # -----------------------------------------------------------------
    print("\n--- [9] VIDEO CLAIM (b): short RSI2>95 (>200SMA, cover on close<MA5) in a bull market ---")
    print(f"  {'sym':<8}{'trd':>5}{'WR%':>6}{'PnL$':>10}{'CAGR%':>7}{'MDD%':>6}{'expo%':>7}"
          f"{'CapEff':>8}{'MCpct':>7}")
    short_cfg = dict(trend=True, entry=95, exit_kind="ma5", exit_rsi=None, cap=None, stop200=False)
    short_rows = []
    for sym in ["SPY", "QQQ", "SMH", "XLE"]:
        if sym not in data:
            continue
        d = data[sym]
        tr, nsig = gen_trades(d, short=True, **short_cfg)
        m = evaluate(d, tr, nsig, short=True)
        ctl = random_control(d, tr, rng, short=True)
        short_rows.append((sym, m))
        print(f"  {sym:<8}{m['trades']:>5}{m['wr'] * 100:>6.1f}{m['pnl']:>10,.0f}"
              f"{m['cagr'] * 100:>7.2f}{m['mdd'] * 100:>6.1f}{m['exposure'] * 100:>7.1f}"
              f"{m['capeff'] * 100:>8.0f}{ctl['pct']:>7.1f}")
    # universe-wide sign test on the short
    spn = []
    for sym, d in data.items():
        tr, nsig = gen_trades(d, short=True, **short_cfg)
        spn.append(evaluate(d, tr, nsig, short=True)["pnl"])
    spn = np.array(spn)
    print(f"  universe-wide: {(spn > 0).mean() * 100:.1f}% of {len(spn)} symbols profitable short; "
          f"mean PnL ${spn.mean():,.0f}, median ${np.median(spn):,.0f}")

    # -----------------------------------------------------------------
    # [9b] EXECUTION SENSITIVITY -- the single biggest difference vs our 07-17 run.
    # That run entered at the NEXT CLOSE and found ~nothing. This one enters at the NEXT OPEN and
    # finds a lot. If the edge lives only in the overnight gap, it is far less tradeable than it
    # looks (you must accept the opening print). This section decides which it is.
    # -----------------------------------------------------------------
    print("\n--- [9b] EXECUTION SENSITIVITY (Connors config: >200SMA, RSI2<5, exit close>MA5) ---")
    print("  close0 = buy at the CLOSE of the signal bar (Connors' book; needs an MOC estimate)")
    print("  open1  = buy at the NEXT OPEN  (the video's look-ahead fix -- THIS FILE'S MAIN RESULT)")
    print("  close1 = buy at the NEXT CLOSE (what exp_rsi2_be_replication.py did on 07-17)")
    print(f"  {'sym':<6}{'mode':<8}{'trd':>5}{'WR%':>6}{'actual':>9}{'rnd p50':>9}{'rnd p95':>9}"
          f"{'pctile':>8}{'expo%':>7}{'PnL$':>9}{'CAGR%':>7}")
    for sym in ["SPY", "QQQ", "SMH", "XLE"]:
        if sym not in data:
            continue
        d = data[sym]
        n, lc, lo, c, r2, ma5, sma = (d["n"], d["lc"], d["lo"], d["c"], d["r2"], d["ma5"], d["sma"])
        hit = c > ma5
        idx = np.where(hit, np.arange(n), n)
        eb = np.minimum(np.minimum.accumulate(idx[::-1])[::-1], n - 1)
        sig = (r2 < 5) & np.isfinite(sma) & (c > sma)
        for mode in ["close0", "open1", "close1"]:
            trades, i = [], 0
            while i < n - 1:
                if not sig[i]:
                    i += 1
                    continue
                if mode == "close0":
                    e, x, el = i, int(eb[min(i + 1, n - 1)]), lc[i]
                elif mode == "open1":
                    e, x, el = i + 1, int(eb[i + 1]), lo[i + 1]
                else:
                    e = i + 1
                    x, el = int(eb[min(e + 1, n - 1)]), lc[e]
                x = min(max(x, e), n - 1)
                trades.append((e, x, el))
                i = x
            if not trades:
                continue
            durs = np.array([x - e for e, x, _ in trades])
            actual = float(np.sum([lc[x] - el for _, x, el in trades]))
            rets = np.array([math.exp(lc[x] - el) - 1.0 for _, x, el in trades])
            expo = float(np.sum(durs + 1) / n)
            # random control matched to THIS execution convention
            M = n - int(durs.max()) - 1
            starts = rng.integers(0, max(M, 1), size=(N_SIMS, len(trades)))
            ent = lo[starts] if mode == "open1" else lc[starts]
            sims = (lc[starts + durs[None, :]] - ent).sum(axis=1)
            pct = float((sims < actual).mean() * 100)
            fin = START_EQUITY * float(np.prod(1.0 + rets))
            print(f"  {sym:<6}{mode:<8}{len(trades):>5}{(rets > 0).mean() * 100:>6.1f}{actual:>9.3f}"
                  f"{np.median(sims):>9.3f}{np.percentile(sims, 95):>9.3f}{pct:>8.1f}{expo * 100:>7.1f}"
                  f"{fin - START_EQUITY:>9,.0f}{(fin / START_EQUITY) ** (1 / d['years']) - 1:>7.2%}")
    print("  -> If open1 >> close1, the edge is concentrated in the OVERNIGHT/OPENING move after the")
    print("     dip, and our 07-17 close-entry run missed it BY CONSTRUCTION (it bought a day late).")

    # -----------------------------------------------------------------
    # [10] Bookkeeping.
    # -----------------------------------------------------------------
    print("\n--- [10] SAMPLE / HONESTY BOOKKEEPING ---")
    con = df[df["arm"] == "Connors"]
    print(f"  window          : {min(d['start'] for d in data.values()).date()} -> "
          f"{max(d['end'] for d in data.values()).date()} (heterogeneous per symbol)")
    print(f"  symbols usable  : {len(data)}  |  n_eff = {n_eff:.1f} (rho = {rho:.3f})")
    print(f"  Connors trades  : {int(con['trades'].sum())} total across universe; "
          f"{int(con['signals'].sum())} signals (gap = signals fired while already long)")
    print(f"  survivorship    : the 85 theme names are TODAY's watchlist = known survivors. "
          f"Inflates every PnL column; MC percentile / WR / MDD are far less affected "
          f"(within-symbol relative measures).")
    print(f"  overlapping win : trades non-overlapping by construction. MC preserves exact trade "
          f"count + hold-length distribution but NOT the 'post-dip vol is higher' structure -> "
          f"the control is slightly GENEROUS to RSI2.")

    out = os.path.join(CACHE, "rsi2_connors_rows.json")
    df.to_json(out, orient="records")
    print(f"\n[rows: {out}]")


if __name__ == "__main__":
    main()
