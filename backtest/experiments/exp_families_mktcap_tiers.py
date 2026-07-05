"""Fill the gap: MOMENTUM (trend) + MEAN-REV (RSI-2) on the 4 MARKET-CAP TIERS (micro/small/mid/large
individual-stock baskets) — the ETF-category runs (exp_momentum_family / exp_rsi2_meanrev_family)
covered 大盤/細價/板塊/Mag7 but NOT the market-cap tiers. Standing rule: never drop small caps.

Per tier basket (equal-weight daily, returns clipped ±[-0.5,1.0] to kill penny blow-ups):
  MEAN-REV  RSI-2 entry<{20,15,10,5} × exit>{75,80,85,90}   (buy weakness)
  MOMENTUM  price>SMA{50,100,150,200} in × <SMA out          (trend, buy strength)
Cell = 部署CAGR%/條件Sharpe/曝險%, vs each tier's B&H. FULL + H1 2016-2020 + H2 2021-now.
2016+, 10bps/turnover, signal shifted. Survivorship: small/mid/micro inflated — relative picture.

    python backtest/experiments/exp_families_mktcap_tiers.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signals import rsi  # noqa: E402

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
COST = 0.001
START = "2016-01-01"
SPLIT = pd.Timestamp("2021-01-01")
TIERS = [("micro <$300M", 0, 3e8), ("small $300M-2B", 3e8, 2e9),
         ("mid $2B-10B", 2e9, 1e10), ("large >$10B", 1e10, 1e99)]
RSI_E = [20, 15, 10, 5]; RSI_X = [75, 80, 85, 90]
SMA_E = [50, 100, 150, 200]; SMA_X = [50, 100, 150, 200]


def tier_baskets():
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    mc = pickle.load(open(os.path.join(_DATA, "mktcap_defeatbeta.pkl"), "rb"))
    stocks = [t for t in px if isinstance(px.get(t), pd.Series) and mc.get(t) is not None and len(px[t]) > 400]
    R, M = {}, {}
    for t in stocks:
        s = px[t]; s = s[~s.index.duplicated()].sort_index()
        m = mc[t]; m = m[~m.index.duplicated()].sort_index()
        R[t] = s.pct_change().clip(-0.5, 1.0)
        M[t] = m.reindex(s.index, method="ffill")
    R = pd.DataFrame(R); M = pd.DataFrame(M.values, index=R.index, columns=R.columns) if False else pd.DataFrame(M)
    R = R[R.index >= START]; M = M.reindex(R.index)
    print(f"[tiers] {R.shape[1]} stocks")
    return {t: R.where((M >= lo) & (M < hi)).mean(axis=1).fillna(0) for t, lo, hi in TIERS}


def rsi_pos(price, E, X):
    r2 = rsi(price, 2).values; pos = np.zeros(len(r2)); inp = False
    for i in range(len(r2)):
        if r2[i] != r2[i]:
            pos[i] = 1.0 if inp else 0.0; continue
        if not inp and r2[i] < E:
            inp = True
        elif inp and r2[i] > X:
            inp = False
        pos[i] = 1.0 if inp else 0.0
    return pd.Series(pos, index=price.index).shift(1).fillna(0)


def trend_pos(price, Pe, Px):
    se = price.rolling(Pe).mean().values; sx = price.rolling(Px).mean().values; p = price.values
    pos = np.zeros(len(p)); inp = False
    for i in range(len(p)):
        if se[i] != se[i] or sx[i] != sx[i]:
            pos[i] = 1.0 if inp else 0.0; continue
        if not inp and p[i] > se[i]:
            inp = True
        elif inp and p[i] < sx[i]:
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


def grid(bret, idx, pos_fn, ES, XS, elab, xlab):
    print(f"{elab:<9}" + "".join(f"{xlab+str(x):>15}" for x in XS))
    for E in ES:
        row = f"{E:<9}"
        for X in XS:
            dep, csh, exp = capeff(bret, pos_fn(idx, E, X).reindex(bret.index, method="ffill"))
            row += f"{dep*100:>+5.0f}/{csh:>4.2f}/{exp*100:>3.0f}".rjust(15)
        print(row)


def block(bret, idx, fam):
    pos_fn, ES, XS, elab, xlab = ((rsi_pos, RSI_E, RSI_X, "ent<", ">") if fam == "MEANREV"
                                  else (trend_pos, SMA_E, SMA_X, "in>SMA", "<SMA"))
    for seg, sub in [("FULL", bret), ("H1 2016-2020", bret[bret.index < SPLIT]), ("H2 2021-now", bret[bret.index >= SPLIT])]:
        c, s, d = bh(sub)
        print(f"\n  --- {fam} · {seg}  (B&H {c*100:+.1f}%/{s:.2f}/{d*100:.0f}%) 部署CAGR%/條件Sharpe/曝險% ---")
        grid(sub, idx, pos_fn, ES, XS, elab, xlab)


def run():
    tb = tier_baskets()
    for tier, _, _ in TIERS:
        bret = tb[tier]; idx = (1 + bret).cumprod()
        print(f"\n========================= {tier} =========================")
        block(bret, idx, "MEANREV")
        block(bret, idx, "MOMENTUM")
    print("\nREAD: 補市值層(個股籃)。MEANREV=RSI-2 買弱;MOMENTUM=SMA 趨勢買強。同 ETF 類比較 small/mid 得唔得。"
          "\nsurvivorship 偏高(micro 最甚)睇相對 + 兩半。")


if __name__ == "__main__":
    run()
