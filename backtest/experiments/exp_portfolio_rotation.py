"""Causal weekly sector rotation -- the decisive test: does COMPOSITION beat buy-and-hold?

The oracle (exp_portfolio_oracle.py) showed the weekly ceiling is astronomical but a noise
mirage; the free premium (EW vs SPY) is only ~+0.6pp/yr. Here we test how much a REAL,
look-ahead-safe signal captures. Signals use data THROUGH week t-1, applied to week t's return.

Strategies (9 core SPDR, total-return, weekly, cost 5bp/unit turnover):
  EW / SPY               -- baselines
  MOM(K) top-3           -- cross-sectional momentum: hold top-3 by trailing-K-week return
  MOM+TREND top-3        -- top-3 by momentum AND > 40w SMA; the rest -> CASH (offense when
                            timed, cash when nothing qualifies -- the user's composition idea)
Valuation tilt deferred (sector-level valuation needs constituent-PE aggregation; keep the
first causal test to the cleanest, established signals -- momentum + trend -- to avoid overfit).

Reported: net CAGR/Sharpe/MaxDD, turnover, vs SPY/EW/oracle-3, full-period + last-10y, DSR.

Run: python backtest/experiments/exp_portfolio_rotation.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exp_portfolio_oracle import SECTORS, weekly_returns
from metrics import ann_sharpe, cagr, deflated_sharpe_ratio, max_drawdown

COST_BPS = 5.0
NTOP = 3
SMA_W = 40


def port(W, sec):
    """weights (n x k) applied to sector returns (n x k) -> net return series + turnover/yr."""
    r = (W * sec).sum(axis=1)
    turn = np.abs(np.diff(W, axis=0, prepend=np.zeros((1, W.shape[1])))).sum(axis=1)
    rnet = r - turn * COST_BPS / 1e4
    return rnet, float(turn.mean() * 52)


def metr(r, ppy=52):
    r = np.asarray(r, float)
    eq = np.cumprod(1 + r)
    return {"CAGR": cagr(eq, ppy), "Sharpe": ann_sharpe(r, ppy), "MaxDD": max_drawdown(eq)}


def mom_weights(P, sec, K, trend=False, freq=1):
    """P: sector price index (n x k, start 1). Momentum as of t-1 = P[t-1]/P[t-1-K]-1.
    Rebalance every `freq` weeks (freq=1 weekly, 4 monthly); hold target weights between."""
    n, k = sec.shape
    mom = np.full((n, k), np.nan)
    mom[K + 1:] = P[K:-1] / P[:-K - 1] - 1.0                 # ends at t-1 (shifted)
    sma = pd.DataFrame(P).rolling(SMA_W).mean().to_numpy()
    above = np.zeros((n, k), bool)
    above[1:] = P[:-1] > sma[:-1]                            # trend as of t-1
    W = np.zeros((n, k))
    last, start = None, K + 1
    for t in range(start, n):
        if (t - start) % freq == 0 or last is None:
            m = mom[t]
            if not np.all(np.isnan(m)):
                order = np.argsort(-np.nan_to_num(m, nan=-9))[:NTOP]
                picks = [int(i) for i in order]
                if trend:
                    picks = [i for i in picks if above[t, i]]
                w = np.zeros(k)
                for i in picks:
                    w[i] = 1.0 / NTOP                        # trend: dropped picks -> cash (0)
                last = w
        if last is not None:
            W[t] = last
    return W


def sub(r, lo):
    return r[lo:]


def run():
    rets, d0, d1 = weekly_returns()
    sec = rets[SECTORS].to_numpy()
    spy = rets["SPY"].to_numpy()
    n, k = sec.shape
    P = np.cumprod(1 + sec, axis=0)

    Wew = np.full((n, k), 1.0 / k)
    strategies = {
        "SPY": (spy, None),
        "EW 9 sectors": port(Wew, sec),
        "MOM-13 top3 wk": port(mom_weights(P, sec, 13), sec),
        "MOM-26 top3 wk": port(mom_weights(P, sec, 26), sec),
        "MOM-26 top3 monthly": port(mom_weights(P, sec, 26, freq=4), sec),
        "MOM-26+TREND monthly": port(mom_weights(P, sec, 26, trend=True, freq=4), sec),
    }
    # normalize SPY entry to (returns, turnover)
    series = {name: (v[0] if isinstance(v, tuple) else v) for name, v in strategies.items()}
    turns = {name: (v[1] if isinstance(v, tuple) and v[1] is not None else 0.0) for name, v in strategies.items()}

    recent = n - 520  # last ~10y
    trial_sharpes = [ann_sharpe(series[s]) for s in series if s.startswith("MOM")]

    print(f"\n=== CAUSAL weekly sector rotation -- {len(SECTORS)} sectors, {d0}->{d1}, {n} weeks ===")
    print(f"cost {COST_BPS}bp/unit turnover, top-{NTOP}, ann=52 (net of cost)\n")
    hdr = f"{'strategy':20}{'CAGR':>7}{'Sharpe':>7}{'MaxDD':>8}{'turn/yr':>8} | {'CAGR_10y':>9}{'Sh_10y':>7}  {'DSR':>5}"
    print(hdr)
    print("-" * len(hdr))
    spy_full, spy_10 = metr(spy)["CAGR"], metr(sub(spy, recent))["CAGR"]
    for name in strategies:
        r = series[name]
        f, rc = metr(r), metr(sub(r, recent))
        dsr = ""
        if name.startswith("MOM"):
            dsr = f"{deflated_sharpe_ratio(r, trial_sharpes):.2f}"
        print(f"{name:20}{f['CAGR']*100:6.1f}%{f['Sharpe']:7.2f}{f['MaxDD']*100:7.1f}%{turns[name]:8.1f} | "
              f"{rc['CAGR']*100:8.1f}%{rc['Sharpe']:7.2f}  {dsr:>5}")

    print(f"\n  benchmarks: SPY {spy_full*100:.1f}% (10y {spy_10*100:.1f}%), EW {metr(series['EW 9 sectors'])['CAGR']*100:.1f}%")
    print("  oracle top-3 (ceiling, from the oracle study) was ~155% net -- causal capture is the gap-closer.")
    print("  Verdict: rotation has edge only if a causal variant beats SPH net-of-cost, holds in the last")
    print("  10y, and survives DSR. Prior (from the ceiling study): lands near EW, modest beat at best.")


if __name__ == "__main__":
    run()
