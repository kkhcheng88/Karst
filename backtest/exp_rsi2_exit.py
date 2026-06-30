"""Experiment: RSI-2 exit-threshold sensitivity (>70 / >80 / >90 / >95).

Same RSI-2 as exp_rsi2_filter, sweeping the exit level. Higher exit = hold the
bounce longer before selling -> more exposure, closer to B&H. Filter on/off,
look-ahead-safe, cost 1bps.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metrics  # noqa: E402
from data import load  # noqa: E402
from engine import backtest, buy_hold  # noqa: E402
from signals import rsi, sma  # noqa: E402

ASSETS = ["SPY", "QQQ", "SPMO"]
ENTRY_TH, RSI_LEN, SMA_LEN, COST = 5, 2, 200, 1.0
EXITS = [70, 80, 90, 95]


def variant(close, use_filter, exit_th):
    r, sm = rsi(close, RSI_LEN), sma(close, SMA_LEN)
    start = sm.first_valid_index()
    c, rr, ss = close.loc[start:], r.loc[start:], sm.loc[start:]
    entry = (rr < ENTRY_TH)
    if use_filter:
        entry = entry & (c > ss)
    exit = (rr > exit_th)
    pos, strat, eq = backtest(c.values, entry.fillna(False).values,
                              exit.fillna(False).values, COST)
    return c, pos, strat, eq


def main():
    data, trials = {}, []
    for sym in ASSETS:
        close = load(sym)["close"]
        for flt in (False, True):
            for ex in EXITS:
                d = variant(close, flt, ex)
                data[(sym, flt, ex)] = d
                trials.append(metrics.ann_sharpe(d[2]))

    print(f"RSI-2 (<{ENTRY_TH} in), exit sweep, SMA200 filter, cost {COST}bps, "
          f"look-ahead-safe  [{len(trials)} variants -> DSR]")
    for sym in ASSETS:
        c0 = data[(sym, False, EXITS[0])][0]
        bh = metrics.summary(*buy_hold(c0.values))
        print(f"\n### {sym}  ({c0.index.min().date()}->{c0.index.max().date()})  "
              f"B&H CAGR {bh['CAGR']*100:.2f}%  Sharpe {bh['Sharpe']:.2f}  "
              f"MaxDD {bh['MaxDD']*100:.1f}%")
        print(f"  exit flt |   CAGR  Sharpe   MaxDD  Expo Trades   DSR")
        for flt in (False, True):
            for ex in EXITS:
                c, pos, strat, eq = data[(sym, flt, ex)]
                s = metrics.summary(strat, eq, pos)
                dsr = metrics.deflated_sharpe_ratio(strat, trials)
                print(f"  >{ex:<3} {'ON ' if flt else 'off'} | "
                      f"{s['CAGR']*100:6.2f}% {s['Sharpe']:6.2f} {s['MaxDD']*100:6.1f}% "
                      f"{s['Exposure']*100:4.0f}% {s['Trades']:6d} {dsr*100:4.0f}%")


if __name__ == "__main__":
    main()
