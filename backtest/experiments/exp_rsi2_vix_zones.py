"""RSI-2 dip trades split by ENTRY-VIX zone (low / mid / extreme), keeping the RSI-2 exit.

Tests the three-zone VIX thesis: VIX = one-sided downside fear, not two-sided vol. So:
  - low VIX (calm bull/sideways): a dip reliably reverts to the upside -> a LOOSE exit
    (RSI2>90/95) captures more; deployed return should RISE as exit loosens.
  - mid VIX (fear/falling): bounce is an unreliable dead-cat -> a TIGHT exit (>70) is best;
    deployed return should FALL as exit loosens.
  - extreme VIX (capitulation, >~28): fear peaked / oversold -> the low is likely in and a
    multi-week recovery follows -> holding (LOOSE exit) should pay again.

Trade-level, classified by VIX on the entry day, pooled across all names for power in the
rare extreme zone. Exit stays RSI2>{70,80,90,95} (no time-exit — RSI2 is the framework under
test). entry RSI2<{5,10}. 2016-01-01+, look-ahead-safe, 2bp round-trip cost, raw close.

    python backtest/experiments/exp_rsi2_vix_zones.py
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
RT_COST = 0.0002
START = "2016-01-01"
ZONES = [("低VIX<18", 0, 18), ("中VIX 18-28", 18, 28), ("極端VIX>28", 28, 999)]

NAMES = ["SPY", "QQQ", "SPMO", "IWM", "IJR",
         "XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLB", "XLY", "XLC", "XLRE",
         "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]


def w(px):
    return px[px.index >= START] if px is not None else None


def trades(px, entry, exit_, vix_al):
    r2 = rsi(px, 2).values
    n = len(px)
    pos = np.zeros(n)
    inp = False
    for i in range(n):
        if not inp and r2[i] < entry:
            inp = True
        elif inp and r2[i] > exit_:
            inp = False
        pos[i] = 1.0 if inp else 0.0
    pos = pd.Series(pos, index=px.index).shift(1).fillna(0).values
    p = px.values
    v = vix_al.values
    out = []
    e = None
    for i in range(1, n):
        if pos[i] > 0 and pos[i - 1] == 0:
            e = i
        elif pos[i] == 0 and pos[i - 1] > 0 and e is not None:
            out.append((p[i] / p[e] - 1 - RT_COST, i - e, v[e]))
            e = None
    return out


def run():
    vix = w(D.load("^VIX", min_rows=260)["close"])
    pool = {en: {z[0]: {x: [] for x in EXITS} for z in ZONES} for en in ENTRIES}
    for t in NAMES:
        try:
            px = w(D.load(t, min_rows=260)["close"])
        except Exception:
            continue
        if px is None or len(px) < 200:
            continue
        va = vix.reindex(px.index).ffill()
        for en in ENTRIES:
            for x in EXITS:
                for ret, hold, evix in trades(px, en, x, va):
                    if evix != evix:
                        continue
                    for zn, lo, hi in ZONES:
                        if lo <= evix < hi:
                            pool[en][zn][x].append((ret, hold))
                            break

    for en in ENTRIES:
        print(f"\n########## entry RSI2<{en} ##########")
        print(f"每格 = 平均每筆回報% / 勝率% / 平均持有日 [筆數]")
        print(f"{'入場VIX區':<14}" + "".join(f"{'>'+str(x):>22}" for x in EXITS))
        for zn, _, _ in ZONES:
            row = f"{zn:<14}"
            for x in EXITS:
                tr = pool[en][zn][x]
                if len(tr) < 10:
                    row += f"{'n<10':>22}"
                    continue
                r = np.array([a for a, _ in tr])
                h = np.array([b for _, b in tr])
                row += f"{r.mean()*100:>+5.1f}/{(r > 0).mean()*100:>3.0f}/{h.mean():>2.0f}d[{len(tr):>4}]".rjust(22)
            print(row)


if __name__ == "__main__":
    run()
