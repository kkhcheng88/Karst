"""BREAKOUT momentum (SPEC D — Livermore/Darvas/Donchian new-N-day-high) as a basket TIMER — the
practitioner short-horizon momentum, distilled from the Discretionary Momentum library (O'Neil/Darvas/
Livermore common core: buy new highs, exit on trend break). Tests whether breakout-timing beats the
trailing-return TSMOM timer / plain hold, on our standard.

Donchian channel timer: enter LONG when close makes a new N-day high; exit to cash when close makes a
new M-day low. Grid entry N {20,55,126,252} × exit M {10,20,55,126}. Look-ahead-safe (prior-bar channel
+ shift). Cell = 部署CAGR%/條件Sharpe/曝險%, vs B&H. 4 ETF categories + 4 market-cap tiers. FULL + two-halves.
CAVEAT: price-only (cache has no volume) — the practitioners' VOLUME≥1.5× confirmation is NOT applied.

    python backtest/experiments/exp_breakout_timer.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as D  # noqa: E402

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
COST = 0.001
START = "2016-01-01"
SPLIT = pd.Timestamp("2021-01-01")
ENTRY_N = [20, 55, 126, 252]
EXIT_M = [10, 20, 55, 126]
CATS = [
    ("大盤指數 (SPY/QQQ/SPMO)", ["SPY", "QQQ", "SPMO"]),
    ("細價股 (IWM/IJR)", ["IWM", "IJR"]),
    ("板塊ETF (11 SPDR)", ["XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLB", "XLY", "XLC", "XLRE"]),
    ("Mag7", ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]),
]
TIERS = [("micro <$300M", 0, 3e8), ("small $300M-2B", 3e8, 2e9),
         ("mid $2B-10B", 2e9, 1e10), ("large >$10B", 1e10, 1e99)]


def basket_ret(syms):
    cols = {}
    for s in syms:
        try:
            cols[s] = D.load(s, min_rows=200)["close"].pct_change()
        except Exception:
            pass
    return pd.DataFrame(cols).mean(axis=1)[lambda r: r.index >= START].dropna()


def tier_baskets():
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    mc = pickle.load(open(os.path.join(_DATA, "mktcap_defeatbeta.pkl"), "rb"))
    stocks = [t for t in px if isinstance(px.get(t), pd.Series) and mc.get(t) is not None and len(px[t]) > 400]
    R, M = {}, {}
    for t in stocks:
        s = px[t]; s = s[~s.index.duplicated()].sort_index()
        R[t] = s.pct_change().clip(-0.5, 1.0)
        M[t] = mc[t][~mc[t].index.duplicated()].sort_index().reindex(s.index, method="ffill")
    R = pd.DataFrame(R); M = pd.DataFrame(M)
    R = R[R.index >= START]; M = M.reindex(R.index)
    return {t: R.where((M >= lo) & (M < hi)).mean(axis=1).fillna(0) for t, lo, hi in TIERS}


def donchian_pos(price, N, M):
    hh = price.rolling(N).max().shift(1).values   # prior-bar N-day high
    ll = price.rolling(M).min().shift(1).values
    c = price.values; pos = np.zeros(len(c)); inp = False
    for i in range(len(c)):
        if hh[i] == hh[i] and ll[i] == ll[i]:
            if not inp and c[i] >= hh[i]:
                inp = True
            elif inp and c[i] <= ll[i]:
                inp = False
        pos[i] = 1.0 if inp else 0.0
    return pd.Series(pos, index=price.index).shift(1).fillna(0)


def capeff(bret, pos):
    pos = pos.reindex(bret.index).fillna(0)
    strat = pos * bret - COST * pos.diff().abs().fillna(0)
    exp = pos.mean(); inm = pos.values > 0.5; n = int(inm.sum())
    if n < 15:
        return float("nan"), float("nan"), exp
    r_in = strat[inm]
    return (1 + r_in).prod() ** (252 / n) - 1, (r_in.mean() / r_in.std() * np.sqrt(252) if r_in.std() else float("nan")), exp


def bh(bret):
    if len(bret) < 60:
        return float("nan"), float("nan"), float("nan")
    n = len(bret); eq = (1 + bret).cumprod()
    return eq.iloc[-1] ** (252 / n) - 1, bret.mean() / bret.std() * np.sqrt(252), (eq / eq.cummax() - 1).min()


def grid(bret, idx):
    print(f"{'entryN\\exitM':<11}" + "".join(f"{'low'+str(m):>15}" for m in EXIT_M))
    for N in ENTRY_N:
        row = f"high{N:<7}"
        for M in EXIT_M:
            dep, csh, exp = capeff(bret, donchian_pos(idx, N, M).reindex(bret.index, method="ffill"))
            row += f"{dep*100:>+5.0f}/{csh:>4.2f}/{exp*100:>3.0f}".rjust(15)
        print(row)


def report(name, bret):
    idx = (1 + bret).cumprod()
    print(f"\n========== {name} ==========")
    for seg, sub in [("FULL", bret), ("H1 2016-2020", bret[bret.index < SPLIT]), ("H2 2021-now", bret[bret.index >= SPLIT])]:
        c, s, d = bh(sub)
        print(f"\n  --- {seg}  (B&H {c*100:+.1f}%/{s:.2f}/{d*100:.0f}%) 部署CAGR%/條件Sharpe/曝險% ---")
        grid(sub, idx)


def run():
    print("######### 4 ETF 類別 #########")
    for name, syms in CATS:
        report(name, basket_ret(syms))
    print("\n\n######### 4 市值層(個股籃) #########")
    tb = tier_baskets()
    for tier, _, _ in TIERS:
        report(tier, tb[tier])
    print("\nREAD: SPEC D 突破 timer(新 N 日高入、新 M 日低出)。同 TSMOM/SMA 比,睇突破式擇時有冇著數。"
          "\n price-only(無成交量確認)。兩半睇穩健。")


if __name__ == "__main__":
    run()
