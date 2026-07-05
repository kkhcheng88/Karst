"""RSI-2 capital-efficiency — FULL detailed grid: 4 market-cap tiers × entry × exit.

Detailed table the user can actually read/discuss (not a rushed summary). Individual stocks
(not ETF proxies), classified by market cap AT ENTRY into 4 tiers; plus 大盤指數 / 板塊ETF
index references. Entry RSI2<{20,15,10,5} × exit RSI2>{75,80,85,90} = 16 combos.

Per cell (capital-efficiency lens): per-trade return% · win% · avg hold-days · [n trades] ·
DEPLOYED EFFICIENCY (= per-trade% / avg-hold × 252 = annualised return on deployed capital).

Trade-level, look-ahead-safe, 2bp/trade round-trip, raw close. Universe = cached stocks with
price+market-cap (survivorship-biased — flag; relative picture across tiers/thresholds robust).

    python backtest/experiments/exp_rsi2_capeff_detailed.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as D  # noqa: E402
from signals import rsi  # noqa: E402

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
ENTRIES = [20, 15, 10, 5]
EXITS = [75, 80, 85, 90]
RT = 0.0002
TIERS = [("micro <$300M", 0, 3e8), ("small $300M-2B", 3e8, 2e9),
         ("mid $2B-10B", 2e9, 1e10), ("large >$10B", 1e10, 1e99)]


def _trades(s, r2, entry, exit_):
    n = len(s)
    pos = np.zeros(n)
    inp = False
    for i in range(n):
        if not inp and r2[i] < entry:
            inp = True
        elif inp and r2[i] > exit_:
            inp = False
        pos[i] = 1.0 if inp else 0.0
    pos = pd.Series(pos, index=s.index).shift(1).fillna(0).values
    p = s.values
    out, e = [], None
    for i in range(1, n):
        if pos[i] > 0 and pos[i - 1] == 0:
            e = i
        elif pos[i] == 0 and pos[i - 1] > 0 and e is not None:
            out.append((p[i] / p[e] - 1 - RT, i - e, e))
            e = None
    return out


def _grids(pool, tiers):
    """print per-tier: (ret%/win%/hold[n]) grid + deployed-efficiency grid."""
    for tier in tiers:
        print(f"\n===== {tier} =====")
        print(f"{'entry\\exit':<10}" + "".join(f"{'>'+str(x):>18}" for x in EXITS))
        for E in ENTRIES:
            row = f"<{E:<8}"
            for X in EXITS:
                tr = pool.get((tier, E, X), [])
                if len(tr) < 15:
                    row += f"{'n<15':>18}"
                    continue
                r = np.array([a for a, _ in tr]); h = np.array([b for _, b in tr])
                row += f"{r.mean()*100:>+5.1f}/{(r > 0).mean()*100:>3.0f}/{h.mean():>2.0f}[{len(tr):>4}]".rjust(18)
            print(row)
        print(f"{'部署效率%/yr':<10}" + "".join(f"{'>'+str(x):>18}" for x in EXITS))
        for E in ENTRIES:
            row = f"<{E:<8}"
            for X in EXITS:
                tr = pool.get((tier, E, X), [])
                if len(tr) < 15:
                    row += f"{'—':>18}"
                    continue
                r = np.array([a for a, _ in tr]); h = np.array([b for _, b in tr])
                eff = (r.mean() / max(h.mean(), 1)) * 252 * 100
                row += f"{eff:>+8.0f}%".rjust(18)
            print(row)


def run():
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    mc = pickle.load(open(os.path.join(_DATA, "mktcap_defeatbeta.pkl"), "rb"))
    stocks = [t for t in px if isinstance(px.get(t), pd.Series) and mc.get(t) is not None]
    print(f"[capeff] individual-stock universe: {len(stocks)}")
    pool = {}
    for t in stocks:
        s = px[t]
        s = s[~s.index.duplicated()].sort_index()
        if len(s) < 260:
            continue
        m = mc[t]; m = m[~m.index.duplicated()].sort_index()
        r2 = rsi(s, 2).values
        for E in ENTRIES:
            for X in EXITS:
                for ret, hold, ei in _trades(s, r2, E, X):
                    cap = m.asof(s.index[ei])
                    if cap != cap:
                        continue
                    for tier, lo, hi in TIERS:
                        if lo <= cap < hi:
                            pool.setdefault((tier, E, X), []).append((ret, hold))
                            break

    print("\n######### 個股 · 4 市值層 (per-trade%/勝%/持有d[n] + 部署效率%/yr) #########")
    _grids(pool, [t[0] for t in TIERS])

    # index references: 大盤指數 + 板塊ETF
    ipool = {}
    for grp, syms in [("大盤指數(SPY/QQQ/SPMO)", ["SPY", "QQQ", "SPMO"]),
                      ("板塊ETF(11 SPDR)", ["XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLB", "XLY", "XLC", "XLRE"])]:
        for sym in syms:
            try:
                s = D.load(sym, min_rows=260)["close"]
            except Exception:
                continue
            r2 = rsi(s, 2).values
            for E in ENTRIES:
                for X in EXITS:
                    for ret, hold, ei in _trades(s, r2, E, X):
                        ipool.setdefault((grp, E, X), []).append((ret, hold))
    print("\n######### Index 對照 #########")
    _grids(ipool, ["大盤指數(SPY/QQQ/SPMO)", "板塊ETF(11 SPDR)"])
    print("\nREAD: per-trade% = 每筆賺幾多(鬆離場愈高);部署效率%/yr = 錢落場嘅年化速率(緊離場愈高,"
          "因持有短)。跨層睇邊個市值最食 RSI-2。SURVIVORSHIP:micro 偏高,睇相對。")


if __name__ == "__main__":
    run()
