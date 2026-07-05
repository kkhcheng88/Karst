"""BREADTH timeframe-matching + RSI-2 DIRECTION (user's two points):
  (1) breadth must match the signal's timeframe — confirm a 2-day RSI-2 with SAME-period (2-day) breadth,
      not a mismatched 10-day breadth.
  (2) RSI-2 LEVEL is ambiguous (80 rising ≠ 80 falling); split by RSI-2 direction.

breadth_2d = (RSP/SPY) 2-day change (SAME timeframe as RSI-2);  breadth_10d = 10-day (my earlier, mismatched).
broad = RSP outperformed (>0, many stocks with the move) · narrow = RSP underperformed (<0, few big names).
Grids side-by-side so you SEE if timeframe-matching changes the picture. + RSI-2 rising/falling split.
Forward SPY 5d/21d mean%(win%)/n. RSP 2003+. yfinance.

    python backtest/experiments/exp_breadth_timeframe.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signals import rsi  # noqa: E402


def dl(tk):
    import yfinance as yf
    v = yf.download(tk, start="2003-01-01", progress=False, auto_adjust=True)["Close"]
    if isinstance(v, pd.DataFrame):
        v = v.iloc[:, 0]
    return v[~v.index.duplicated()].sort_index()


def run():
    spy, rsp = dl("SPY"), dl("RSP")
    idx = spy.index
    r2 = rsi(spy, 2)
    r2_rising = r2 > r2.shift(1)
    b = rsp / spy
    b2 = b / b.shift(2) - 1      # 2-day breadth (matches RSI-2 timeframe)
    b10 = b / b.shift(10) - 1    # 10-day breadth (my earlier, mismatched)
    fwd5 = spy.shift(-5) / spy - 1
    fwd21 = spy.shift(-21) / spy - 1
    print(f"[breadth-tf] {idx[0].date()}→{idx[-1].date()} n={len(idx)}  基準21d {fwd21.mean()*100:+.2f}%(勝{(fwd21>0).mean()*100:.0f})")

    def c(mask):
        m = mask & fwd21.notna(); n = int(m.sum())
        if n < 20:
            return f"{'n<20':>26}"
        return f"{fwd5[m].mean()*100:>+5.2f}%({(fwd5[m]>0).mean()*100:>3.0f}) {fwd21[m].mean()*100:>+5.2f}%({(fwd21[m]>0).mean()*100:>3.0f}) n{n:>4}".rjust(26)

    def grid(title, bsig):
        print(f"\n### {title} —— 每格:前望5d%(勝) | 21d%(勝) | n")
        print(f"{'RSI-2':<14}{'+ breadth 闊(broad,續)':>26}{'+ breadth 窄(narrow,轉)':>26}")
        for lbl, pm in [("深超賣<10", r2 < 10), ("超賣<20", r2 < 20), ("超買>80", r2 > 80), ("深超買>90", r2 > 90)]:
            print(f"{lbl:<14}{c(pm & (bsig >= 0))}{c(pm & (bsig < 0))}")

    grid("A. 同期 2 日 breadth(matched)", b2)
    grid("B. 10 日 breadth(mismatched,我之前)", b10)

    print("\n### C. RSI-2 方向(拆你嘅『80 升 vs 80 跌』含糊)—— 前望5d%(勝)|21d%(勝)|n")
    print(f"{'狀態':<20}{'':>26}")
    for lbl, pm in [("超買>80 & RSI2 升(推緊)", (r2 > 80) & r2_rising),
                    ("超買>80 & RSI2 跌(冷卻)", (r2 > 80) & ~r2_rising),
                    ("超賣<20 & RSI2 跌(仲插)", (r2 < 20) & ~r2_rising),
                    ("超賣<20 & RSI2 升(轉頭)", (r2 < 20) & r2_rising)]:
        print(f"{lbl:<20}{c(pm)}")

    print("\n讀法:A vs B —— 若同期 2 日 breadth 嘅『闊/窄』對比 比 10 日更清（差距更大/更一致）= timeframe 要 match。"
          "\nC —— 若『超買+RSI2 跌(冷卻)』前望明顯低過『超買+升』= RSI-2 方向本身已含 revert 訊息,唔可淨睇 level。")


if __name__ == "__main__":
    run()
