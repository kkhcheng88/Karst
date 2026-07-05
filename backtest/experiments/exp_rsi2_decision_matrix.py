"""RSI-2 decision matrix: best entry/exit per (instrument category x VIX zone).

Fills the practical gap: capitulation (extreme VIX) is rare, so we need the best setup for
low & mid VIX too, and it differs by instrument type. Trade-level, classified by entry-day
VIX, split BY CATEGORY (not pooled). Two decision lenses, because they disagree:
  - per-trade return + win%  -> matters if dips are intermittent (can't redeploy) -> favours LOOSE exit
  - efficiency = per-trade return / avg-hold x 252 -> matters if you can redeploy into the next
    dip (diversified book) -> favours TIGHT exit
Report both so the exit choice is a conscious call.

entry RSI2<{5,10}, exit RSI2>{70,80,90,95} (RSI2 exit kept — no time-exit). 2016+, 2bp/trade,
look-ahead-safe, raw close.

    python backtest/experiments/exp_rsi2_decision_matrix.py
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
ZONES = [("低VIX<18", 0, 18), ("中VIX18-28", 18, 28), ("極端>28", 28, 999)]

CATS = {
    "大盤指數": ["SPY", "QQQ", "SPMO"],
    "細價股": ["IWM", "IJR"],
    "板塊ETF": ["XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLB", "XLY", "XLC", "XLRE"],
    "Mag7": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"],
}


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
    p, v = px.values, vix_al.values
    out, e = [], None
    for i in range(1, n):
        if pos[i] > 0 and pos[i - 1] == 0:
            e = i
        elif pos[i] == 0 and pos[i - 1] > 0 and e is not None:
            out.append((p[i] / p[e] - 1 - RT_COST, i - e, v[e]))
            e = None
    return out


def agg(tr):
    if len(tr) < 12:
        return None
    r = np.array([a for a, _ in tr])
    h = np.array([b for _, b in tr])
    return dict(ret=r.mean() * 100, win=(r > 0).mean() * 100, hold=h.mean(),
                eff=(r.mean() / max(h.mean(), 1)) * 252 * 100, n=len(tr))


def run():
    vix = w(D.load("^VIX", min_rows=260)["close"])
    cache = {}
    for tks in CATS.values():
        for t in tks:
            if t not in cache:
                try:
                    cache[t] = w(D.load(t, min_rows=260)["close"])
                except Exception:
                    cache[t] = None

    store = {}  # (cat, zone, entry, exit) -> list of trades
    for cat, tks in CATS.items():
        for t in tks:
            px = cache.get(t)
            if px is None or len(px) < 200:
                continue
            va = vix.reindex(px.index).ffill()
            for en in ENTRIES:
                for x in EXITS:
                    for ret, hold, ev in trades(px, en, x, va):
                        if ev != ev:
                            continue
                        for zn, lo, hi in ZONES:
                            if lo <= ev < hi:
                                store.setdefault((cat, zn, en, x), []).append((ret, hold))
                                break

    for cat in CATS:
        print(f"\n========== {cat} ==========  每格 = per-trade%/勝%/持有d  (entry<10)")
        print(f"{'VIX區':<12}" + "".join(f"{'>'+str(x):>16}" for x in EXITS))
        for zn, _, _ in ZONES:
            row = f"{zn:<12}"
            for x in EXITS:
                a = agg(store.get((cat, zn, 10, x), []))
                row += (f"{a['ret']:>+4.1f}/{a['win']:>3.0f}/{a['hold']:>2.0f}[{a['n']:>3}]".rjust(16)
                        if a else f"{'n<12':>16}")
            print(row)
        # recommendation per zone: best exit by two lenses (entry<10, else <5 if too few)
        for zn, _, _ in ZONES:
            best_ret = best_eff = None
            for en in (10, 5):
                cells = {x: agg(store.get((cat, zn, en, x), [])) for x in EXITS}
                cells = {x: a for x, a in cells.items() if a and a['n'] >= 15}
                if cells:
                    best_ret = (en, max(cells, key=lambda x: cells[x]['ret']), cells)
                    best_eff = (en, max(cells, key=lambda x: cells[x]['eff']), cells)
                    break
            if best_ret:
                en, xr, c = best_ret
                _, xe, _ = best_eff
                print(f"   建議 {zn}: 追效率→ entry<{en}/exit>{xe} (eff {c[xe]['eff']:.0f}%/yr, {c[xe]['ret']:+.1f}%/筆) "
                      f"| 追每筆→ exit>{xr} ({c[xr]['ret']:+.1f}%/筆, 勝{c[xr]['win']:.0f}%)")
            else:
                print(f"   建議 {zn}: 樣本不足")


if __name__ == "__main__":
    run()
