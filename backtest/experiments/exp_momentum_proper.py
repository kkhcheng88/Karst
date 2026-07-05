"""MOMENTUM done PROPERLY — replace the crude 'price vs single SMA' timer with the well-supported
TIME-SERIES MOMENTUM (Moskowitz-Ooi-Pedersen 2012): hold when the asset's OWN trailing L-month return
is positive; to cash when negative. Re-validates the earlier 'momentum robust both halves' conclusion
with a canonical spec (my SMA test was a weak proxy — user's critique).

Signal (binary in/out, for capital-efficiency comparability to the SMA grid):
  pos = 1 if trailing-L-month return > 0 else 0   (L = 3/6/9/12 months) + COMPOSITE = majority of 6/9/12.
(Note: the FULL MOP spec also VOL-SCALES position size ∝ 1/vol + dynamic vol-targeting for crash control
— that's a position-sizing / portfolio-stage overlay, not tested here; here we isolate the timing signal.)

Per basket per lookback: 部署CAGR%/條件Sharpe/曝險%, vs B&H. FULL + H1 2016-2020 + H2 2021-now.
4 ETF categories + 4 market-cap tiers (individual-stock baskets, clipped). 2016+, 10bps/turnover, shifted.

    python backtest/experiments/exp_momentum_proper.py
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
LOOKBACKS = [("3m", 63), ("6m", 126), ("9m", 189), ("12m", 252)]
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


def tsmom_pos(idx, L):
    return (idx / idx.shift(L) - 1 > 0).astype(float).shift(1).fillna(0)


def composite_pos(idx):
    votes = sum((idx / idx.shift(L) - 1 > 0).astype(float) for _, L in LOOKBACKS[1:])  # 6/9/12
    return (votes >= 2).astype(float).shift(1).fillna(0)


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


def report(name, bret):
    idx = (1 + bret).cumprod()
    segs = [("FULL", bret), ("H1 2016-2020", bret[bret.index < SPLIT]), ("H2 2021-now", bret[bret.index >= SPLIT])]
    print(f"\n========== {name} ==========")
    for seg, sub in segs:
        c, s, d = bh(sub)
        print(f"  {seg:<13} B&H: CAGR {c*100:+.1f}% / Sharpe {s:.2f} / MaxDD {d*100:.0f}%")
    print(f"  {'TSMOM lookback':<14}" + "".join(f"{seg:>22}" for seg, _ in segs))
    print(f"  {'(部署/條件Sh/曝險)':<14}" + "".join(f"{'CAGR/Sharpe/exp':>22}" for _ in segs))
    rows = [(lbl, lambda i, L=L: tsmom_pos(i, L)) for lbl, L in LOOKBACKS] + [("COMPOSITE 6/9/12", lambda i: composite_pos(i))]
    for lbl, fn in rows:
        line = f"  {lbl:<14}"
        for seg, sub in segs:
            dep, csh, exp = capeff(sub, fn(idx).reindex(sub.index, method="ffill"))
            line += f"{dep*100:>+5.0f}/{csh:>4.2f}/{exp*100:>3.0f}".rjust(22)
        print(line)


def run():
    print("######### 4 ETF 類別 #########")
    for name, syms in CATS:
        report(name, basket_ret(syms))
    print("\n\n######### 4 市值層(個股籃) #########")
    tb = tier_baskets()
    for tier, _, _ in TIERS:
        report(tier, tb[tier])
    print("\nREAD: 正版 TSMOM(trailing L-月報酬>0 就揸)。同 SMA timer 比,睇『momentum 兩半穩健』結論企唔企得住。"
          "\nCOMPOSITE(6/9/12 多數決)= 防單一 lookback 脆弱。vol-scaling 未加(portfolio 階段)。")


if __name__ == "__main__":
    run()
