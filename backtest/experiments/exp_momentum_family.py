"""MOMENTUM / TREND family — time-series momentum timer (buy strength, opposite polarity to RSI-2's
buy-weakness). Same capital-efficiency + full-grid + two-halves rigor as the mean-rev family.

  ABS trend  : hold basket when price > SMA(entry_period); exit to cash when price < SMA(exit_period).
  RS  trend  : same on the basket/SPY ratio — hold basket when it's out-trending SPY (relative momentum).

Grid = entry SMA {50,100,150,200} × exit SMA {50,100,150,200} (asymmetric = hysteresis). Per cell:
部署CAGR% / 條件Sharpe / 曝險%, vs each basket's B&H. 4 categories. FULL + H1 2016-2020 + H2 2021-now.
10bps/turnover, signal shifted (next bar), look-ahead-safe.

    python backtest/experiments/exp_momentum_family.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as D  # noqa: E402

ENTRY_SMA = [50, 100, 150, 200]
EXIT_SMA = [50, 100, 150, 200]
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


def trend_pos(price, Pe, Px):
    se = price.rolling(Pe).mean().values
    sx = price.rolling(Px).mean().values
    p = price.values
    pos = np.zeros(len(p)); inp = False
    for i in range(len(p)):
        if se[i] != se[i] or sx[i] != sx[i]:
            pos[i] = 1.0 if inp else 0.0; continue
        if not inp and p[i] > se[i]:
            inp = True
        elif inp and p[i] < sx[i]:
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


def grid(bret, price, pos_of):
    print(f"{'ent\\exit':<9}" + "".join(f"{'<SMA'+str(x):>16}" for x in EXIT_SMA))
    for Pe in ENTRY_SMA:
        row = f">SMA{Pe:<4}"
        for Px in EXIT_SMA:
            dep, csh, exp = capeff(bret, pos_of(price, Pe, Px))
            row += f"{dep*100:>+5.0f}/{csh:>4.2f}/{exp*100:>3.0f}".rjust(16)
        print(row)


def block(label, bret, price):
    idx = bret.index
    for seg, sub in [("FULL 2016+", bret), ("H1 2016-2020", bret[idx < SPLIT]), ("H2 2021-now", bret[idx >= SPLIT])]:
        c, s, d = bh(sub)
        print(f"\n  --- {label} · {seg}  (B&H {c*100:+.1f}%/{s:.2f}/{d*100:.0f}%) 部署CAGR%/條件Sharpe/曝險% ---")
        grid(sub, price, lambda p, Pe, Px: trend_pos(p, Pe, Px).reindex(sub.index, method="ffill"))


def run():
    spy_idx = (1 + basket_ret(["SPY"])).cumprod()
    for name, syms in CATS:
        bret = basket_ret(syms)
        idx = (1 + bret).cumprod()
        print(f"\n========== {name} ==========")
        block("ABS 趨勢 (price vs SMA)", bret, idx)
        ratio = (idx / spy_idx.reindex(idx.index).ffill()).dropna()
        block("RS 趨勢 (basket/SPY vs SMA)", bret, ratio)
    print("\nREAD: 動能=買強勢揸趨勢(同 RSI-2 買弱勢反極)。部署CAGR/條件Sharpe 高過 B&H = 趨勢擇時抵。"
          "\n兩半都贏=穩健。留意動能同均值回歸應 regime 互補(RSI-2 死嗰半、動能可能靚)。")


if __name__ == "__main__":
    run()
