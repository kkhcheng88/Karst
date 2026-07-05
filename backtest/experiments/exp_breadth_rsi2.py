"""BREADTH done RIGHT — as a CONFIRMATION on a top/bottom (RSI-2), NOT standalone.
(User: breadth alone has no direction; it tells you if the current move is BROAD=trending=continues
or NARROWING=exhausting=reverts. So pair it with an overbought/oversold, and read continue-vs-revert.)

Primary top/bottom = SPY RSI-2 (2-day): 深超賣<10 · 超賣<20 · 超買>80 · 深超買>90.
Breadth direction = RSP/SPY (equal÷cap) 10-day change:
   broadening (RSP/SPY 升 = 細價股追返 = 參與變闊)  vs  narrowing (跌 = 得大股撐 = 收窄).
The user's hypothesis (test it, don't assert):
   超買 + narrowing = 升勢收窄 → 轉跌 (前望負/低)      超買 + broadening = 升勢broad → 續升
   超賣 + narrowing = 跌勢收窄 → 轉升 (前望高)         超賣 + broadening = 跌勢broad → 續跌
Forward SPY 5d/21d mean return + WIN% + n, per cell + baseline. FULL numbers shown. RSP 2003+. yfinance.

    python backtest/experiments/exp_breadth_rsi2.py
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
    breadth = (rsp / spy).reindex(idx).ffill()
    b10 = breadth / breadth.shift(10) - 1            # +ve = broadening (RSP/SPY 升); -ve = narrowing
    fwd5 = spy.shift(-5) / spy - 1
    fwd21 = spy.shift(-21) / spy - 1
    print(f"[breadth×rsi2] {idx[0].date()}→{idx[-1].date()}  n={len(idx)}")

    def cell(mask):
        m = mask & fwd21.notna()
        n = int(m.sum())
        if n < 20:
            return None
        f5 = fwd5[m]; f21 = fwd21[m]
        return (f5.mean() * 100, (f5 > 0).mean() * 100, f21.mean() * 100, (f21 > 0).mean() * 100, n)

    base = cell(pd.Series(True, index=idx))
    print(f"\n基準(所有日):前望5d {base[0]:+.2f}% (勝{base[1]:.0f}%) · 21d {base[2]:+.2f}% (勝{base[3]:.0f}%) · n={base[4]}")
    print("\n每格:前望5d均值%(勝%) | 前望21d均值%(勝%) | n")
    print(f"{'頂/底(RSI-2)':<16}{'+ breadth broadening(闊,續)':>30}{'+ breadth narrowing(窄,轉)':>30}")
    prims = [("深超賣 RSI2<10", r2 < 10), ("超賣 RSI2<20", r2 < 20),
             ("超買 RSI2>80", r2 > 80), ("深超買 RSI2>90", r2 > 90)]
    for lbl, pm in prims:
        row = f"{lbl:<16}"
        for bm in [b10 >= 0, b10 < 0]:
            c = cell(pm & bm)
            row += (f"{c[0]:>+6.2f}%({c[1]:>3.0f}) {c[2]:>+6.2f}%({c[3]:>3.0f}) n{c[4]:>4}".rjust(30)
                    if c else f"{'n<20':>30}")
        print(row)

    print("\n讀法(逐格對比基準):")
    print("  • 超買+窄(收窄)若前望 < 超買+闊 = 升勢收窄→轉跌(頂背離)成立。")
    print("  • 超賣+窄(收窄)若前望 > 超賣+闊 = 跌勢收窄→轉升成立(你嘅 model)。")
    print("  • 同向(超買+闊續升 / 超賣+闊續跌)= 趨勢延續。breadth = 續 vs 轉 嘅確認,唔係方向本身。")


if __name__ == "__main__":
    run()
