"""F&G-timed strategy — capital efficiency AND total wealth, full grid.
Buy when F&G<ENTRY (fear), sell to cash when F&G>EXIT (greed). 4 categories + 4 market-cap tiers
× entry F&G<{20,15,10,5} × exit F&G>{75,80,85,90}.

Two views per basket (so "beats B&H?" is answerable):
  資本效率  部署CAGR% (in-market days) / 條件Sharpe (in-market)
  財富      總CAGR% (idle cash 0) / 全期Sharpe (incl cash days) / MaxDD%
Exposure is IDENTICAL across baskets (F&G is market-level) -> shown once.
Tier stock returns CLIPPED to [-0.5,1.0]/day to kill penny pct_change blow-ups.
10bps/turnover, F&G 2011+, look-ahead-safe.

    python backtest/experiments/exp_fg_timed_capeff.py
"""
import io
import os
import pickle
import sys
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as D  # noqa: E402
_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
ENTRIES = [20, 15, 10, 5]
EXITS = [75, 80, 85, 90]
COST = 0.001
TIERS = [("micro <$300M", 0, 3e8), ("small $300M-2B", 3e8, 2e9),
         ("mid $2B-10B", 2e9, 1e10), ("large >$10B", 1e10, 1e99)]


def load_fg():
    url = "https://raw.githubusercontent.com/whit3rabbit/fear-greed-data/main/fear-greed.csv"
    df = pd.read_csv(io.StringIO(urllib.request.urlopen(url, timeout=30).read().decode()))
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")["Fear Greed"].sort_index()


def _pos(fg, E, X):
    f = fg.values
    pos = np.zeros(len(f))
    inp = False
    for i in range(len(f)):
        if not inp and f[i] < E:
            inp = True
        elif inp and f[i] > X:
            inp = False
        pos[i] = 1.0 if inp else 0.0
    return pd.Series(pos, index=fg.index).shift(1).fillna(0)


def capeff(bret, fg, E, X):
    pos = _pos(fg, E, X)
    strat = pos * bret - COST * pos.diff().abs().fillna(0)
    exp = pos.mean()
    inm = pos.values > 0
    r_in = strat[inm]
    dep = (1 + r_in).prod() ** (252 / max(inm.sum(), 1)) - 1 if inm.sum() > 40 else float("nan")
    csh = r_in.mean() / r_in.std() * np.sqrt(252) if inm.sum() > 40 and r_in.std() else float("nan")
    n = len(strat); eq = (1 + strat).cumprod()
    tot = eq.iloc[-1] ** (252 / n) - 1
    fsh = strat.mean() / strat.std() * np.sqrt(252) if strat.std() else float("nan")
    mdd = (eq / eq.cummax() - 1).min()
    return dep, csh, exp, tot, fsh, mdd


def bh(bret):
    n = len(bret); eq = (1 + bret).cumprod()
    return eq.iloc[-1] ** (252 / n) - 1, bret.mean() / bret.std() * np.sqrt(252), (eq / eq.cummax() - 1).min()


def grid(name, bret, fg):
    bret = bret.reindex(fg.index).fillna(0)
    c, s, d = bh(bret)
    vals = {(E, X): capeff(bret, fg, E, X) for E in ENTRIES for X in EXITS}
    print(f"\n===== {name} =====   B&H: CAGR {c*100:+.1f}% / Sharpe {s:.2f} / MaxDD {d*100:.0f}%")
    print(f"  【資本效率 部署CAGR%/條件Sharpe】{'':6}【財富 總CAGR%/全期Sharpe/MaxDD%】")
    print(f"{'ent\\exit':<8}" + "".join(f"{'>'+str(x):>13}" for x in EXITS)
          + "  |" + "".join(f"{'>'+str(x):>15}" for x in EXITS))
    for E in ENTRIES:
        eff = "".join(f"{vals[(E,X)][0]*100:>+5.0f}/{vals[(E,X)][1]:>4.2f}".rjust(13) for X in EXITS)
        wl = "".join(f"{vals[(E,X)][3]*100:>+4.0f}/{vals[(E,X)][4]:>4.2f}/{vals[(E,X)][5]*100:>3.0f}".rjust(15) for X in EXITS)
        print(f"<{E:<7}{eff}  |{wl}")


def tier_baskets(fg):
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    mc = pickle.load(open(os.path.join(_DATA, "mktcap_defeatbeta.pkl"), "rb"))
    stocks = [t for t in px if isinstance(px.get(t), pd.Series) and mc.get(t) is not None and len(px[t]) > 260]
    idx = fg.index
    R, M = {}, {}
    for t in stocks:
        s = px[t]; s = s[~s.index.duplicated()].sort_index()
        m = mc[t]; m = m[~m.index.duplicated()].sort_index()
        R[t] = s.pct_change().clip(-0.5, 1.0).reindex(idx)      # clip penny blow-ups
        M[t] = m.reindex(idx, method="ffill")
    R = pd.DataFrame(R); M = pd.DataFrame(M)
    print(f"[tiers] {R.shape[1]} stocks (daily returns clipped ±)")
    return {tier: R.where((M >= lo) & (M < hi)).mean(axis=1).fillna(0) for tier, lo, hi in TIERS}


def run():
    fg = load_fg()
    idx = D.load("SPY")["close"].index
    fg = fg.reindex(idx[idx >= fg.index.min()]).ffill(limit=5).dropna()

    print("=== 曝險參考(所有籃相同,因 F&G 係市場層)entry×exit → 曝險% ===")
    print(f"{'ent\\exit':<8}" + "".join(f"{'>'+str(x):>8}" for x in EXITS))
    for E in ENTRIES:
        print(f"<{E:<7}" + "".join(f"{_pos(fg, E, X).mean()*100:>7.0f}%" for X in EXITS))

    def avg(syms):
        cols = {}
        for s in syms:
            try:
                cols[s] = D.load(s, min_rows=200)["close"].pct_change().reindex(fg.index)
            except Exception:
                pass
        return pd.DataFrame(cols).mean(axis=1)

    print("\n######### 4 類別(乾淨 ETF)#########")
    grid("大盤指數 (SPY/QQQ/SPMO)", avg(["SPY", "QQQ", "SPMO"]), fg)
    grid("細價股 (IWM/IJR)", avg(["IWM", "IJR"]), fg)
    grid("板塊ETF (11 SPDR)", avg(["XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLB", "XLY", "XLC", "XLRE"]), fg)
    grid("Mag7", avg(["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]), fg)

    print("\n\n######### 4 市值層(個股籃,clip 後;small/mid 仍有 survivorship,睇相對)#########")
    tb = tier_baskets(fg)
    for tier, _, _ in TIERS:
        grid(tier, tb[tier], fg)


if __name__ == "__main__":
    run()
