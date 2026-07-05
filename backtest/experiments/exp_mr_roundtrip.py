"""The canonical fear/greed MR round-trip — ENTRY and EXIT both taken straight from
HANDOFF findings #5-#7, no assumed/targeted exposure level (exp_exposure_sweep.py's
hold-day sweep picked an arbitrary knob to hit a range of exposures — that's an
assumption; this script removes it).

  ENTRY (finding #5, "fear"):  VIX > 30   OR   (RSI2(2) < 10  AND  VIX > 25)
  EXIT  (finding #7, "lock the bounce" + finding #6, "froth trim"):
                                RSI2(2) > 90   OR   F&G > 80

Both entry and exit are real, findings-grounded MR signals — average exposure is
whatever falls out of running them, not chosen. Flat baseline (0x) between trades,
matching engine.py's stateful long/flat convention (decided on bar i-1, acts on bar i).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

import metrics  # noqa: E402
from exp_topdays_exposure import ASSETS, build_frame, load_fg, mkt_returns, relever, strat_from_pos  # noqa: E402

RSI_EXIT, FG_EXIT = 90, 80


def mr_position(df) -> np.ndarray:
    entry = ((df["vix"] > 30) | ((df["rsi2"] < 10) & (df["vix"] > 25))).values
    exit_ = ((df["rsi2"] > RSI_EXIT) | (df["fg"] > FG_EXIT)).values
    n = len(df)
    pos = np.zeros(n)
    in_mkt = False
    for i in range(1, n):
        if not in_mkt and entry[i - 1]:
            in_mkt = True
        elif in_mkt and exit_[i - 1]:
            in_mkt = False
        pos[i] = 1.0 if in_mkt else 0.0
    return pos


def main():
    fg = load_fg()
    cache = {sym: build_frame(sym, fg) for sym in ASSETS}
    trials = []
    for sym in ASSETS:
        df = cache[sym]
        mkt_ret = mkt_returns(df)
        pos = mr_position(df)
        strat, _ = strat_from_pos(mkt_ret, pos, start=0.0)
        trials.append(metrics.ann_sharpe(strat))

    print(f"ENTRY: VIX>30 or (RSI2<10 & VIX>25)   EXIT: RSI2>{RSI_EXIT} or F&G>{FG_EXIT}")
    for sym in ASSETS:
        df = cache[sym]
        mkt_ret = mkt_returns(df)
        bh_eq = np.cumprod(1.0 + mkt_ret)
        bh = metrics.summary(mkt_ret, bh_eq)
        pos = mr_position(df)
        strat, eq = strat_from_pos(mkt_ret, pos, start=0.0)
        sm = metrics.summary(strat, eq, pos)
        ts = metrics.trade_stats(pos, strat)
        a, b, ta = metrics.jensen_alpha(strat, mkt_ret)
        dsr = metrics.deflated_sharpe_ratio(strat, trials)

        pos_r, strat_r, eq_r = relever(pos, mkt_ret)
        smr = metrics.summary(strat_r, eq_r, pos_r)
        ar, br, tar = metrics.jensen_alpha(strat_r, mkt_ret)

        print(f"\n### {sym}  ({df.index.min().date()}->{df.index.max().date()})  "
              f"B&H(exposure=1.0) CAGR {bh['CAGR']*100:.2f}%  Sharpe {bh['Sharpe']:.2f}  "
              f"MaxDD {bh['MaxDD']*100:.1f}%")
        print(f"  CALCULATED AvgExposure = {sm['Exposure']*100:.1f}%  "
              f"(N trades={ts['N']}, win%={ts['WinRate']*100:.0f}%, avg hold implied "
              f"~{sm['Exposure']*len(df)/max(ts['N'],1):.0f}d/trade)")
        print(f"  raw       : CAGR {sm['CAGR']*100:6.2f}%  Alpha {a*100:6.2f}%  t={ta:5.1f}  "
              f"Sharpe {sm['Sharpe']:5.2f}  MaxDD {sm['MaxDD']*100:6.1f}%  DSR={dsr*100:3.0f}%")
        print(f"  relevered : CAGR {smr['CAGR']*100:6.2f}%  Alpha {ar*100:6.2f}%  t={tar:5.1f}  "
              f"Sharpe {smr['Sharpe']:5.2f}  MaxDD {smr['MaxDD']*100:6.1f}%  "
              f"(scaled x{1/sm['Exposure']:.2f} to match B&H exposure=1.0)")


if __name__ == "__main__":
    main()
