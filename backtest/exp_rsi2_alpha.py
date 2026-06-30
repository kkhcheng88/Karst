"""Experiment: RSI-2 with alpha + drawdown-distribution + win-stats, entry {5,10}.

Adds what CAGR/Sharpe alone hide:
- Jensen alpha (vs the underlying) + t-stat -> real skill vs diluted market beta.
- AvgDD (typical underwater depth) alongside MaxDD (worst point).
- Win% / avg win / avg loss / PF -> is a fast exit just 'high win%, tiny wins'?
Entry RSI(2) < 5 and < 10. Filter OFF (the more robust variant). look-ahead-safe.
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
ENTRIES, EXITS = [5, 10], [70, 80, 90, 95]
RSI_LEN, SMA_LEN, COST = 2, 200, 1.0


def variant(close, entry_th, exit_th):
    r, sm = rsi(close, RSI_LEN), sma(close, SMA_LEN)
    start = sm.first_valid_index()
    c, rr = close.loc[start:], r.loc[start:]
    entry = (rr < entry_th).fillna(False).values
    exit = (rr > exit_th).fillna(False).values
    pos, strat, eq = backtest(c.values, entry, exit, COST)
    mkt = buy_hold(c.values)[0]
    return c, pos, strat, eq, mkt


def main():
    cache, trials = {}, []
    for sym in ASSETS:
        close = load(sym)["close"]
        for en in ENTRIES:
            for ex in EXITS:
                d = variant(close, en, ex)
                cache[(sym, en, ex)] = d
                trials.append(metrics.ann_sharpe(d[2]))

    print(f"RSI-2 filter OFF, entry/exit sweep, cost {COST}bps  "
          f"[{len(trials)} variants -> DSR]")
    print("  alpha = annualized Jensen alpha vs underlying; aT = t-stat (|t|>2 ~ sig)")
    for sym in ASSETS:
        c0, _, _, eq0, mkt0 = cache[(sym, ENTRIES[0], EXITS[0])]
        bh = metrics.summary(*buy_hold(c0.values))
        print(f"\n### {sym}  ({c0.index.min().date()}->{c0.index.max().date()})  "
              f"B&H CAGR {bh['CAGR']*100:.2f}%  Sharpe {bh['Sharpe']:.2f}  "
              f"MaxDD {bh['MaxDD']*100:.1f}%")
        print("  in  out |  CAGR  Alpha   aT  Shrp | MaxDD  AvgDD | Win%   PF  AvW   AvL | Exp Trd  DSR")
        for en in ENTRIES:
            for ex in EXITS:
                c, pos, strat, eq, mkt = cache[(sym, en, ex)]
                a, b, ta = metrics.jensen_alpha(strat, mkt)
                ts = metrics.trade_stats(pos, strat)
                sm_ = metrics.summary(strat, eq, pos)
                dsr = metrics.deflated_sharpe_ratio(strat, trials)
                print(f"  <{en:<2} >{ex:<2}| {sm_['CAGR']*100:5.2f}% {a*100:5.2f}% "
                      f"{ta:5.1f} {sm_['Sharpe']:5.2f} | {sm_['MaxDD']*100:5.1f}% "
                      f"{metrics.avg_drawdown(eq)*100:5.1f}% | {ts['WinRate']*100:4.0f}% "
                      f"{ts['PF']:4.2f} {ts['AvgWin']*100:4.1f} {ts['AvgLoss']*100:5.1f} | "
                      f"{sm_['Exposure']*100:3.0f}% {sm_['Trades']:3d} {dsr*100:3.0f}%")


if __name__ == "__main__":
    main()
