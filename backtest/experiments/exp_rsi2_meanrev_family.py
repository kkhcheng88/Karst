"""Mean-reversion family — beyond RSI-2's one corner. Two increments the user asked for, in the
SAME capital-efficiency + full-grid form as the F&G test (`exp_fg_timed_capeff.py`):

  A. HORIZON = RSI-2 on different candle sizes (daily / weekly / monthly) — same signal, different
     clock. Answers "does the bounce edge exist at longer horizons?" (user: RSI-2 on 3D/W/M K).
  B. RELATIVE-TO-SPY = RSI-2 on the basket/SPY ratio — long the basket when it's short-term OVERSOLD
     vs SPY. The tradeable version of "vs other stocks" (user: only vs SPY + vs itself matter).

Per basket per variant: full entry RSI2<{20,15,10,5} × exit RSI2>{75,80,85,90} grid,
cell = 部署CAGR% / 條件Sharpe / 曝險% (capital efficiency), vs each basket's B&H.
4 categories (大盤指數/細價股/板塊ETF/Mag7). 2016-01-01+ (standing rule), 10bps/turnover,
signal shifted (act next bar), look-ahead-safe.

    python backtest/experiments/exp_rsi2_meanrev_family.py
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
    """State machine on a price series at ITS frequency: enter when RSI2<E, hold until RSI2>X.
    Shift(1) at that frequency = act next bar (no look-ahead)."""
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


def capeff(bret, pos_daily):
    pos = pos_daily.reindex(bret.index).ffill().fillna(0)
    strat = pos * bret - COST * pos.diff().abs().fillna(0)
    exp = pos.mean()
    inm = pos.values > 0.5
    n = int(inm.sum())
    if n < 20:
        return float("nan"), float("nan"), exp
    r_in = strat[inm]
    dep = (1 + r_in).prod() ** (252 / n) - 1
    csh = r_in.mean() / r_in.std() * np.sqrt(252) if r_in.std() else float("nan")
    return dep, csh, exp


def bh(bret):
    n = len(bret); eq = (1 + bret).cumprod()
    return eq.iloc[-1] ** (252 / n) - 1, bret.mean() / bret.std() * np.sqrt(252), (eq / eq.cummax() - 1).min()


def grid(title, bret, pos_fn):
    """pos_fn(E,X) -> daily position series."""
    print(f"\n----- {title} -----")
    print(f"{'ent\\exit':<8}" + "".join(f"{'>'+str(x):>16}" for x in EXITS))
    for E in ENTRIES:
        row = f"<{E:<7}"
        for X in EXITS:
            dep, csh, exp = capeff(bret, pos_fn(E, X))
            row += f"{dep*100:>+5.0f}/{csh:>4.2f}/{exp*100:>3.0f}".rjust(16)
        print(row)


def run():
    spy_ret = basket_ret(["SPY"])
    spy_idx = (1 + spy_ret).cumprod()

    for name, syms in CATS:
        bret = basket_ret(syms)
        idx = (1 + bret).cumprod()
        c, s, d = bh(bret)
        print(f"\n========== {name} ==========   B&H({START}+): CAGR {c*100:+.1f}% / Sharpe {s:.2f} / MaxDD {d*100:.0f}%")
        print("  每格 部署CAGR%/條件Sharpe/曝險%")

        # A. self RSI-2 on daily / weekly / monthly candles
        for tf_lbl, freq in [("A1 日K (2日反轉)", None), ("A2 週K (~2週反轉)", "W-FRI"), ("A3 月K (~2月反轉)", "ME")]:
            if freq is None:
                price = idx
            else:
                price = idx.resample(freq).last().dropna()
            grid(f"{tf_lbl}  self-RSI2", bret, lambda E, X, p=price: rsi_pos(p, E, X).reindex(bret.index, method="ffill"))

        # B. RSI-2 on basket/SPY ratio — long basket when oversold vs SPY
        ratio = (idx / spy_idx.reindex(idx.index).ffill()).dropna()
        grid("B  相對SPY-RSI2 (弱過SPY就買)", bret, lambda E, X: rsi_pos(ratio, E, X).reindex(bret.index, method="ffill"))

    print("\nREAD: 部署CAGR=落場年化賺率;條件Sharpe=落場風險調整;曝險=幾多時間有貨。同該籃 B&H 比。"
          "\nA1/A2/A3 = 同一 RSI-2 換 K 線大細(反彈時鐘)。B = 相對 SPY 超賣先買(你真買嗰批)。"
          f"\n窗 {START}+,10bps/turnover,訊號 shift 一格(次棒執行)。")


if __name__ == "__main__":
    run()
