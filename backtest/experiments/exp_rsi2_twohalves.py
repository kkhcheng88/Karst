"""Mean-rev family — TWO-HALVES robustness on the DAILY RSI-2 basket timer (the "easy" deployable
core: 大盤指數 + Mag7). Split 2016-2025 into H1 2016-2020 vs H2 2021-present, run the SAME daily
RSI-2 entry×exit grid on each half. Edge in BOTH halves = robust; edge in one = regime luck.

RSI-2 computed on the FULL daily price index (no half-boundary cold-start), position sliced per half.
Cell = 部署CAGR% / 條件Sharpe / 曝險%, vs each half's B&H. 10bps/turnover, signal shifted (next bar).

    python backtest/experiments/exp_rsi2_twohalves.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as D  # noqa: E402
from signals import rsi  # noqa: E402

ENTRIES = [20, 15, 10, 5]
EXITS = [75, 80, 85, 90]
COST = 0.001
START = "2016-01-01"
SPLIT = pd.Timestamp("2021-01-01")
CATS = [
    ("大盤指數 (SPY/QQQ/SPMO)", ["SPY", "QQQ", "SPMO"]),
    ("細價股 (IWM/IJR)", ["IWM", "IJR"]),
    ("板塊ETF (11 SPDR)", ["XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLB", "XLY", "XLC", "XLRE"]),
    ("Mag7", ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]),
]


def basket_ret(syms):
    cols = {}
    for s in syms:
        try:
            cols[s] = D.load(s, min_rows=200)["close"].pct_change()
        except Exception:
            pass
    r = pd.DataFrame(cols).mean(axis=1)
    return r[r.index >= START].dropna()


def rsi_pos(price, E, X):
    r2 = rsi(price, 2).values
    pos = np.zeros(len(r2)); inp = False
    for i in range(len(r2)):
        if r2[i] != r2[i]:
            pos[i] = 1.0 if inp else 0.0; continue
        if not inp and r2[i] < E:
            inp = True
        elif inp and r2[i] > X:
            inp = False
        pos[i] = 1.0 if inp else 0.0
    return pd.Series(pos, index=price.index).shift(1).fillna(0)


def capeff(bret, pos):
    pos = pos.reindex(bret.index).fillna(0)
    strat = pos * bret - COST * pos.diff().abs().fillna(0)
    exp = pos.mean()
    inm = pos.values > 0.5
    n = int(inm.sum())
    if n < 15:
        return float("nan"), float("nan"), exp
    r_in = strat[inm]
    dep = (1 + r_in).prod() ** (252 / n) - 1
    csh = r_in.mean() / r_in.std() * np.sqrt(252) if r_in.std() else float("nan")
    return dep, csh, exp


def bh(bret):
    if len(bret) < 60:
        return float("nan"), float("nan"), float("nan")
    n = len(bret); eq = (1 + bret).cumprod()
    return eq.iloc[-1] ** (252 / n) - 1, bret.mean() / bret.std() * np.sqrt(252), (eq / eq.cummax() - 1).min()


def grid(bret, idx):
    print(f"{'ent\\exit':<8}" + "".join(f"{'>'+str(x):>16}" for x in EXITS))
    for E in ENTRIES:
        row = f"<{E:<7}"
        for X in EXITS:
            pos = rsi_pos(idx, E, X).reindex(bret.index, method="ffill")
            dep, csh, exp = capeff(bret, pos)
            row += f"{dep*100:>+5.0f}/{csh:>4.2f}/{exp*100:>3.0f}".rjust(16)
        print(row)


def run():
    for name, syms in CATS:
        bret = basket_ret(syms)
        idx = (1 + bret).cumprod()
        h1, h2 = bret[bret.index < SPLIT], bret[bret.index >= SPLIT]
        c1, s1, d1 = bh(h1); c2, s2, d2 = bh(h2)
        print(f"\n========== {name} ==========")
        print(f"  H1 2016-2020  B&H: CAGR {c1*100:+.1f}% / Sharpe {s1:.2f} / MaxDD {d1*100:.0f}%")
        print(f"  H2 2021-now   B&H: CAGR {c2*100:+.1f}% / Sharpe {s2:.2f} / MaxDD {d2*100:.0f}%")
        print("\n  --- H1 2016-2020 (部署CAGR%/條件Sharpe/曝險%) ---")
        grid(h1, idx)
        print("\n  --- H2 2021-now  (部署CAGR%/條件Sharpe/曝險%) ---")
        grid(h2, idx)
    print("\nREAD: 兩半都贏該半 B&H = 穩健;得一半 = regime 運氣。重點睇大盤 + Mag7 鬆入場(<20/<15)。")


if __name__ == "__main__":
    run()
