"""Split exp_mr_roundtrip.py's combined entry/exit into 2 INDEPENDENT rules, so we can
see which family (RSI2 vs VIX+F&G) is actually doing the work, rather than a blended
OR-condition that mixes them (finding #3: blending opposite-polarity gauges can cancel
or mask signal — worth checking on the entry/exit combo too, not just F&G vs VIX alone).

  Rule A "rsi2"   : entry RSI2(2)<10           exit RSI2(2)>90         (pure MR, no vol gate)
  Rule B "vix_fg" : entry VIX>30                exit F&G>80             (pure vol/sentiment)
  Rule C "combo"  : entry VIX>30 or RSI2<10&VIX>25   exit RSI2>90 or F&G>80  (= exp_mr_roundtrip,
                    kept as a reference row so combined vs isolated is visible side by side)

Same flat-baseline, look-ahead-safe, 5bps-cost convention as exp_mr_roundtrip.py. Average
exposure is CALCULATED per rule (not assumed) — same discipline as that script.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

import metrics  # noqa: E402
from exp_topdays_exposure import ASSETS, build_frame, load_fg, mkt_returns, relever, strat_from_pos  # noqa: E402


def _stateful_position(entry: np.ndarray, exit_: np.ndarray) -> np.ndarray:
    n = len(entry)
    pos = np.zeros(n)
    in_mkt = False
    for i in range(1, n):
        if not in_mkt and entry[i - 1]:
            in_mkt = True
        elif in_mkt and exit_[i - 1]:
            in_mkt = False
        pos[i] = 1.0 if in_mkt else 0.0
    return pos


def rsi2_position(df) -> np.ndarray:
    entry = (df["rsi2"] < 10).values
    exit_ = (df["rsi2"] > 90).values
    return _stateful_position(entry, exit_)


def vix_fg_position(df) -> np.ndarray:
    entry = (df["vix"] > 30).values
    exit_ = (df["fg"] > 80).values
    return _stateful_position(entry, exit_)


def combo_position(df) -> np.ndarray:
    entry = ((df["vix"] > 30) | ((df["rsi2"] < 10) & (df["vix"] > 25))).values
    exit_ = ((df["rsi2"] > 90) | (df["fg"] > 80)).values
    return _stateful_position(entry, exit_)


RULES = [
    ("rsi2 (entry RSI2<10, exit RSI2>90)", rsi2_position),
    ("vix_fg (entry VIX>30, exit F&G>80)", vix_fg_position),
    ("combo (both, OR'd — reference)", combo_position),
]


def main():
    fg = load_fg()
    cache = {sym: build_frame(sym, fg) for sym in ASSETS}

    trials = []
    for sym in ASSETS:
        df = cache[sym]
        mkt_ret = mkt_returns(df)
        for _, fn in RULES:
            pos = fn(df)
            strat, _ = strat_from_pos(mkt_ret, pos, start=0.0)
            trials.append(metrics.ann_sharpe(strat))

    for sym in ASSETS:
        df = cache[sym]
        mkt_ret = mkt_returns(df)
        bh_eq = np.cumprod(1.0 + mkt_ret)
        bh = metrics.summary(mkt_ret, bh_eq)
        print(f"\n### {sym}  ({df.index.min().date()}->{df.index.max().date()})  "
              f"B&H(exposure=1.0) CAGR {bh['CAGR']*100:.2f}%  Sharpe {bh['Sharpe']:.2f}  "
              f"MaxDD {bh['MaxDD']*100:.1f}%")
        print("  rule                                  N  Win% AvgExp | raw: Alpha    t  Sharpe  MaxDD  | "
              "relevered: Alpha     t  Sharpe   MaxDD")
        for label, fn in RULES:
            pos = fn(df)
            strat, eq = strat_from_pos(mkt_ret, pos, start=0.0)
            sm = metrics.summary(strat, eq, pos)
            ts = metrics.trade_stats(pos, strat)
            a, b, ta = metrics.jensen_alpha(strat, mkt_ret)
            pos_r, strat_r, eq_r = relever(pos, mkt_ret)
            smr = metrics.summary(strat_r, eq_r, pos_r)
            ar, br, tar = metrics.jensen_alpha(strat_r, mkt_ret)
            dsr = metrics.deflated_sharpe_ratio(strat, trials)
            print(f"  {label:38} {ts['N']:3d} {ts['WinRate']*100:4.0f}% {sm['Exposure']*100:5.1f}% | "
                  f"{a*100:6.2f}% {ta:5.1f} {sm['Sharpe']:6.2f} {sm['MaxDD']*100:6.1f}% | "
                  f"{ar*100:7.2f}% {tar:5.1f} {smr['Sharpe']:6.2f} {smr['MaxDD']*100:7.1f}%  DSR={dsr*100:3.0f}%")


if __name__ == "__main__":
    main()
