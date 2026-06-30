"""Experiment: CSP on QQQ/SPY — validate VRP + test entry timing.

20-delta put, 30 DTE (~21 trading days), 50% PT, no SL, single-leg (no wheel),
capital $50k/underlying, cost 1.5%/side of premium. Three entry timings:
  - unconditional (always have a put on)
  - low IV rank (<=25% of trailing 252d) — video 56/57 says low IV is best for short puts
  - RSI-2 dip (RSI(2)<10) — the entry alpha we just measured
Reports total trades, total profit ($), win%, PF, plus NAV CAGR/Sharpe/alpha/DD.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import metrics  # noqa: E402
from data import load  # noqa: E402
from engine import buy_hold  # noqa: E402
from options_engine import simulate_csp  # noqa: E402
from signals import rsi  # noqa: E402

PAIRS = [("QQQ", "^VXN", 0.006), ("SPY", "^VIX", 0.013)]
TARGET_DELTA, DTE, PT, CAP, WARM = 0.20, 21, 0.50, 50000.0, 252


def iv_rank(v, win=252):
    s = pd.Series(v)
    lo, hi = s.rolling(win).min(), s.rolling(win).max()
    return ((s - lo) / (hi - lo)).values


def main():
    print(f"CSP {int(TARGET_DELTA*100)}-delta put, {DTE}td, {int(PT*100)}% PT, no SL, "
          f"single-leg, ${CAP:,.0f}/underlying, cost 1.5%/side")
    for under, volsym, q in PAIRS:
        c = load(under)["close"]
        vv = load(volsym)["close"]
        df = pd.concat({"close": c, "vol": vv}, axis=1).dropna()
        ivr = iv_rank(df["vol"].values)
        r2 = rsi(df["close"], 2).values

        sub = df.iloc[WARM:]
        S = sub["close"].values
        Vol = sub["vol"].values
        bh_ret = buy_hold(S)[0]
        gates = {
            "unconditional": None,
            "low-IV-rank<=25%": ivr[WARM:] <= 0.25,
            "RSI2<10 dip": r2[WARM:] < 10,
        }
        print(f"\n### {under}  ({sub.index.min().date()}->{sub.index.max().date()})")
        print("  entry-gate         | Trades  TotalP/L   Win%   PF | CAGR  Alpha   aT  Shrp | MaxDD  AvgDD")
        for name, g in gates.items():
            nav, tr = simulate_csp(S, Vol, gate=g, target_delta=TARGET_DELTA,
                                   dte_init=DTE, pt=PT, q=q, capital=CAP)
            ret = np.zeros(len(nav))
            ret[1:] = nav[1:] / nav[:-1] - 1
            a, b, ta = metrics.jensen_alpha(ret, bh_ret)
            win = float((tr > 0).mean()) if len(tr) else float("nan")
            pf = (tr[tr > 0].sum() / abs(tr[tr < 0].sum())) if (len(tr) and tr[tr < 0].sum() != 0) else float("inf")
            print(f"  {name:18} | {len(tr):6d} {tr.sum():9,.0f} {win*100:5.0f}% {pf:5.2f} | "
                  f"{metrics.cagr(nav)*100:5.2f}% {a*100:5.2f}% {ta:5.1f} {metrics.ann_sharpe(ret):5.2f} | "
                  f"{metrics.max_drawdown(nav)*100:5.1f}% {metrics.avg_drawdown(nav)*100:5.1f}%")


if __name__ == "__main__":
    main()
