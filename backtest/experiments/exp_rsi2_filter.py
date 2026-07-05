"""Experiment: does the 200-SMA trend filter help or hurt RSI-2 on the 3 core ETFs?

Resolves the Layer-2 core open item: distillation §11.5 (filter +258%, BEAT B&H)
vs §11.6 (filter −84%). We re-run it ourselves on SPY/QQQ/SPMO, look-ahead-safe,
with costs, full-period + per-segment, and deflate the Sharpe for multiple testing.

Strategy (Connors RSI-2, long/flat):
  entry: RSI(2) < 5            [+ price > SMA200 when filter ON]
  exit : RSI(2) > 70
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

import metrics  # noqa: E402
from data import load  # noqa: E402
from engine import backtest, buy_hold  # noqa: E402
from signals import rsi, sma  # noqa: E402

ASSETS = ["SPY", "QQQ", "SPMO"]
ENTRY_TH, EXIT_TH, RSI_LEN, SMA_LEN, COST = 5, 70, 2, 200, 1.0


def variant(close, use_filter):
    r = rsi(close, RSI_LEN)
    sm = sma(close, SMA_LEN)
    start = sm.first_valid_index()
    c = close.loc[start:]
    rr, ss = r.loc[start:], sm.loc[start:]
    entry = (rr < ENTRY_TH)
    if use_filter:
        entry = entry & (c > ss)
    exit = (rr > EXIT_TH)
    pos, strat, eq = backtest(c.values, entry.fillna(False).values,
                              exit.fillna(False).values, COST)
    return c, pos, strat, eq


def fmt(d):
    return (f"CAGR {d['CAGR']*100:6.2f}%  Sharpe {d['Sharpe']:5.2f}  "
            f"MaxDD {d['MaxDD']*100:6.1f}%  Expo {d.get('Exposure',0)*100:4.0f}%  "
            f"Trades {d.get('Trades',0):4d}")


def main():
    # First pass: collect all variant Sharpes (the multiple-testing universe).
    data, trial_sharpes = {}, []
    for sym in ASSETS:
        close = load(sym)["close"]
        for flt in (False, True):
            c, pos, strat, eq = variant(close, flt)
            data[(sym, flt)] = (c, pos, strat, eq)
            trial_sharpes.append(metrics.ann_sharpe(strat))

    print(f"\nRSI-2 (<{ENTRY_TH} in / >{EXIT_TH} out), SMA{SMA_LEN} filter, "
          f"cost {COST}bps/side, look-ahead-safe\n" + "=" * 88)
    for sym in ASSETS:
        print(f"\n### {sym}")
        for flt in (False, True):
            c, pos, strat, eq = data[(sym, flt)]
            s = metrics.summary(strat, eq, pos)
            dsr = metrics.deflated_sharpe_ratio(strat, trial_sharpes)
            tag = "filter ON " if flt else "filter OFF"
            print(f"  {tag}  {fmt(s)}  DSR {dsr*100:5.1f}%")
        # Buy & hold benchmark on the same window (filter-OFF window == full).
        c = data[(sym, False)][0]
        bh_ret, bh_eq = buy_hold(c.values)
        bh = metrics.summary(bh_ret, bh_eq)
        print(f"  buy & hold  CAGR {bh['CAGR']*100:6.2f}%  Sharpe {bh['Sharpe']:5.2f}  "
              f"MaxDD {bh['MaxDD']*100:6.1f}%  ({c.index.min().date()}→{c.index.max().date()})")

    # Per-segment (thirds) Sharpe to expose regime-dependence (the §11.5 vs §11.6 crux).
    print("\n" + "=" * 88 + "\nPer-segment annualized Sharpe (regime-dependence check)")
    for sym in ASSETS:
        c = data[(sym, False)][0]
        idx = np.array_split(np.arange(len(c)), 3)
        row = [f"\n### {sym}"]
        for seg in idx:
            lo, hi = seg[0], seg[-1] + 1
            seg_dates = f"{c.index[lo].date()}→{c.index[hi-1].date()}"
            off = metrics.ann_sharpe(data[(sym, False)][2][lo:hi])
            on = metrics.ann_sharpe(data[(sym, True)][2][lo:hi])
            bh = metrics.ann_sharpe(buy_hold(c.values[lo:hi])[0])
            row.append(f"  {seg_dates}: OFF {off:5.2f} | ON {on:5.2f} | B&H {bh:5.2f}")
        print("\n".join(row))


if __name__ == "__main__":
    main()
