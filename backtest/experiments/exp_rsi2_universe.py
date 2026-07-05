"""RSI-2 buy-the-dip capital efficiency across the FULL entry x exit grid, SINCE 2016,
with a first-half / second-half out-of-sample confirmation.

Grid: entry RSI2 < {5, 10}  x  exit RSI2 > {70, 80, 90, 95}  (8 combos). Both entry and
exit are exposure/quality dials (tighter entry <5 = deeper, fewer, higher-conviction dips;
looser exit >95 = more exposure). No cherry-picking of cells.

Window: 2016-01-01 -> present (standard going forward). Two-halves split 2021-01-01
(H1 2016-2020: 2018 selloff + COVID; H2 2021-2026: 2022 bear + 2025 tariff). Same fixed
rule in both halves — holds in both => out-of-sample robust.

Capital-efficiency framing: Deployed CAGR (in-market days only) & Cond. Sharpe vs B&H.
Long/flat, look-ahead-safe, 1bp/side (fine for limit-order swing on liquid names), raw close.

    python backtest/experiments/exp_rsi2_universe.py
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
SPLIT = "2021-01-01"

UNIVERSES = {
    "大盤指數": ["SPY", "QQQ", "SPMO"],
    "細價股指數": ["IWM", "IJR"],
    "板塊ETF": ["XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLB", "XLY", "XLC", "XLRE"],
    "Mag7單股": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"],
}


def window(px, lo=None, hi=None):
    s = px
    if lo is not None:
        s = s[s.index >= lo]
    if hi is not None:
        s = s[s.index < hi]
    return s


def backtest(px, entry, exit_):
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
    n_in = int(inmkt.sum())
    dep_cagr, cond_sh = float("nan"), float("nan")
    if n_in > 20:
        r_in = strat[inmkt]
        dep_cagr = (1 + r_in).prod() ** (252 / n_in) - 1
        cond_sh = r_in.mean() / r_in.std() * np.sqrt(252) if r_in.std() else float("nan")
    bh_cagr = (1 + ret).prod() ** (252 / len(ret)) - 1
    bh_sh = ret.mean() / ret.std() * np.sqrt(252) if ret.std() else float("nan")
    return dict(dep_cagr=dep_cagr, exp=pos.mean(), cond_sh=cond_sh, bh_cagr=bh_cagr, bh_sh=bh_sh)


def avg(rows, k):
    v = [r[k] for r in rows if r is not None]
    return np.nanmean(v) if v else float("nan")


def run():
    cache = {}
    for tks in UNIVERSES.values():
        for t in tks:
            if t not in cache:
                try:
                    cache[t] = D.load(t, min_rows=260)["close"]
                except Exception:
                    cache[t] = None

    hdr = "".join(f"{'>'+str(x):>13}" for x in EXITS)

    print(f"########## PART 1 — {START} 全窗:部署回報% / 曝險%  (entry × exit 全格) ##########")
    for name, tks in UNIVERSES.items():
        valid = [t for t in tks if cache.get(t) is not None]
        print(f"\n===== {name} ({len(valid)} 隻) =====\n{'entry':<7}{hdr}")
        for e in ENTRIES:
            row = f"<{e:<6}"
            for x in EXITS:
                a = [backtest(window(cache[t], START), e, x) for t in valid]
                row += f"{avg(a,'dep_cagr')*100:>5.0f}/{avg(a,'exp')*100:>3.0f}%".rjust(13)
            print(row)
        b = [backtest(window(cache[t], START), 10, 70) for t in valid]
        print(f"  B&H: CAGR {avg(b,'bh_cagr')*100:.1f}% / Sharpe {avg(b,'bh_sh'):.2f}")

    print(f"\n\n########## PART 2 — 前半(2016-20)/後半(2021-26) 條件Sharpe (前 / 後) 全格 ##########")
    for name, tks in UNIVERSES.items():
        valid = [t for t in tks if cache.get(t) is not None]
        print(f"\n===== {name} =====\n{'entry':<7}{hdr}")
        for e in ENTRIES:
            row = f"<{e:<6}"
            for x in EXITS:
                h1 = [backtest(window(cache[t], START, SPLIT), e, x) for t in valid]
                h2 = [backtest(window(cache[t], SPLIT), e, x) for t in valid]
                row += f"{avg(h1,'cond_sh'):>5.2f}/{avg(h2,'cond_sh'):>5.2f}".rjust(13)
            print(row)


if __name__ == "__main__":
    run()
