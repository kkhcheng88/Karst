"""RSI-2 buy-the-dip conditioned on the VIX REGIME (not calendar), full entry x exit grid.

Nails the mechanism from exp_rsi2_universe's two-halves result: is the edge driven by
VOLATILITY (choppy regime) rather than which years happened to be good? Split every day by
whether the market is in a high-vol regime (VIX 20-day average > its 2016+ median) vs a
low-vol regime, then measure the strategy's in-market performance in EACH regime, across the
FULL grid: entry RSI2 < {5,10} x exit RSI2 > {70,80,90,95} = 8 combos.

If high-VIX-regime deployed performance >> low-VIX across the grid -> confirmed: it is a
volatility-harvesting edge, not a lucky window.

Window 2016-01-01+. Long/flat, look-ahead-safe, 1bp/side, raw close. Metric: Cond. Sharpe
(in-market days only) and Deployed CAGR, each split low-VIX / high-VIX regime. Baskets =
per-name average.

    python backtest/experiments/exp_rsi2_vix_regime.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as D  # noqa: E402
from signals import rsi  # noqa: E402

ENTRIES = [5, 10]
EXITS = [70, 80, 90, 95]
COST = 0.0001
START = "2016-01-01"

UNIVERSES = {
    "大盤指數": ["SPY", "QQQ", "SPMO"],
    "細價股指數": ["IWM", "IJR"],
    "板塊ETF": ["XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLB", "XLY", "XLC", "XLRE"],
    "Mag7單股": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"],
}


def w(px):
    return px[px.index >= START] if px is not None else None


def backtest(px, entry, exit_, reg):
    if px is None or len(px) < 120:
        return None
    r2 = rsi(px, 2).values
    ret = px.pct_change().fillna(0)
    pos = np.zeros(len(px))
    inp = False
    for i in range(len(px)):
        if not inp and r2[i] < entry:
            inp = True
        elif inp and r2[i] > exit_:
            inp = False
        pos[i] = 1.0 if inp else 0.0
    pos = pd.Series(pos, index=px.index).shift(1).fillna(0)
    strat = pos * ret - COST * pos.diff().abs().fillna(0)
    inmkt = pos.values > 0
    r_in = strat[inmkt]
    reg_in = reg.reindex(px.index).ffill().fillna(False).values[inmkt].astype(bool)

    def sh(m):
        r = r_in[m]
        return r.mean() / r.std() * np.sqrt(252) if len(r) > 20 and r.std() else np.nan

    def dep(m):
        r = r_in[m]
        return (1 + r).prod() ** (252 / len(r)) - 1 if len(r) > 20 else np.nan
    return dict(sh_lo=sh(~reg_in), sh_hi=sh(reg_in), dep_lo=dep(~reg_in), dep_hi=dep(reg_in),
                n_lo=int((~reg_in).sum()), n_hi=int(reg_in.sum()))


def avg(rows, k):
    v = [r[k] for r in rows if r is not None]
    return np.nanmean(v) if v else float("nan")


def run():
    vix = w(D.load("^VIX", min_rows=260)["close"])
    v20 = vix.rolling(20).mean()
    reg = v20 > v20.median()          # True = high-vol regime
    print(f"VIX 20日均線中位 = {v20.median():.1f}  (>此 = 高波動 regime)")

    cache = {}
    for tks in UNIVERSES.values():
        for t in tks:
            if t not in cache:
                try:
                    cache[t] = w(D.load(t, min_rows=260)["close"])
                except Exception:
                    cache[t] = None

    hdr = "".join(f"{'>'+str(x):>15}" for x in EXITS)
    for name, tks in UNIVERSES.items():
        valid = [t for t in tks if cache.get(t) is not None]
        grid = {(e, x): [backtest(cache[t], e, x, reg) for t in valid] for e in ENTRIES for x in EXITS}
        print(f"\n===== {name} ({len(valid)} 隻) =====")
        print(f"條件Sharpe  低VIX / 高VIX  (全 8 格)\n{'entry':<7}{hdr}")
        for e in ENTRIES:
            row = f"<{e:<6}"
            for x in EXITS:
                a = grid[(e, x)]
                row += f"{avg(a,'sh_lo'):>6.2f} /{avg(a,'sh_hi'):>6.2f}".rjust(15)
            print(row)
        print(f"部署回報%  低VIX / 高VIX  (全 8 格)\n{'entry':<7}{hdr}")
        for e in ENTRIES:
            row = f"<{e:<6}"
            for x in EXITS:
                a = grid[(e, x)]
                row += f"{avg(a,'dep_lo')*100:>5.0f} /{avg(a,'dep_hi')*100:>5.0f}".rjust(15)
            print(row)
        a = grid[(10, 80)]
        print(f"  (在場日:低VIX {avg(a,'n_lo'):.0f} / 高VIX {avg(a,'n_hi'):.0f},以 <10/>80 計)")


if __name__ == "__main__":
    run()
