"""LOW-VOLATILITY family — two mirrors (entry/exit grid applies only to the timer):

  (1) SELECTION (the anomaly itself, Baker-Bradley-Wurgler / Frazzini-Pedersen BAB): cross-sectional.
      Each month rank the individual-stock universe by trailing 63d realized vol; LOW-vol basket
      (bottom tercile) vs HIGH-vol basket (top tercile), equal-weight, hold 1 month. Compare
      CAGR/Sharpe/MaxDD. FULL + H1 2016-2020 + H2 2021-now. (No entry/exit — it's a holding tilt.)

  (2) TIMER (vol-targeting / risk-off): per basket, hold when its 63d-vol PERCENTILE (vs own 2yr) is
      LOW (calm), de-risk to cash when HIGH (turbulent). Grid entry vol-pct<{40,30,20,10} (stay in
      when calm) × exit vol-pct>{60,70,80,90} (out when turbulent). Capital efficiency, 4 categories,
      FULL + two-halves. NOTE: prior work found VIX is CONTRARIAN (high vol -> bounce) — so this timer
      may UNDERPERFORM (sells capitulation); testing it honestly.

10bps/turnover, signal shifted (next bar), 2016+. Survivorship: cache = priceable names (flag; relative).

    python backtest/experiments/exp_lowvol_family.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as D  # noqa: E402

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
ENTRIES = [40, 30, 20, 10]     # stay IN when vol-percentile < entry (calm)
EXITS = [60, 70, 80, 90]       # de-risk when vol-percentile > exit (turbulent)
COST = 0.001
START = "2016-01-01"
SPLIT = pd.Timestamp("2021-01-01")
CATS = [
    ("大盤指數 (SPY/QQQ/SPMO)", ["SPY", "QQQ", "SPMO"]),
    ("細價股 (IWM/IJR)", ["IWM", "IJR"]),
    ("板塊ETF (11 SPDR)", ["XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLB", "XLY", "XLC", "XLRE"]),
    ("Mag7", ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]),
]


def basket_ret(syms):
    cols = {}
    for s in syms:
        try:
            cols[s] = D.load(s, min_rows=200)["close"].pct_change()
        except Exception:
            pass
    return pd.DataFrame(cols).mean(axis=1)[lambda r: r.index >= START].dropna()


def metrics(ret, per=252):
    if len(ret) < 30:
        return float("nan"), float("nan"), float("nan")
    n = len(ret); eq = (1 + ret).cumprod()
    return eq.iloc[-1] ** (per / n) - 1, ret.mean() / ret.std() * np.sqrt(per) if ret.std() else float("nan"), (eq / eq.cummax() - 1).min()


# ---------- (1) SELECTION: low-vol vs high-vol basket ----------
def selection():
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    stocks = [t for t in px if isinstance(px.get(t), pd.Series) and len(px[t]) > 400]
    months = pd.date_range("2015-06-30", "2026-06-30", freq="ME")
    vol, fwd = {}, {}
    for t in stocks:
        s = px[t]; s = s[~s.index.duplicated()].sort_index()
        r = s.pct_change()
        v = (r.rolling(63).std() * np.sqrt(252)).reindex(months, method="ffill")
        pm = s.reindex(months, method="ffill")
        vol[t] = v; fwd[t] = pm.shift(-1) / pm - 1
    V = pd.DataFrame(vol); F = pd.DataFrame(fwd)
    lo_r, hi_r, dts = [], [], []
    for m in months[:-1]:
        v = V.loc[m].dropna(); f = F.loc[m]
        elig = v.index[v.index.isin(f.dropna().index)]
        v = v[elig]; f = f[elig]
        if len(v) < 60:
            continue
        qlo, qhi = v.quantile([1/3, 2/3])
        lo = f[v <= qlo].clip(-0.6, 2.0); hi = f[v >= qhi].clip(-0.6, 2.0)
        if len(lo) < 10 or len(hi) < 10:
            continue
        lo_r.append(lo.mean()); hi_r.append(hi.mean()); dts.append(m)
    lo = pd.Series(lo_r, index=dts); hi = pd.Series(hi_r, index=dts)
    print(f"\n########## (1) SELECTION 低波籃 vs 高波籃(個股月度,{len(lo)} 月,survivorship 偏高睇相對)##########")
    print(f"{'':16}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}")
    for seg, mask in [("FULL 2016+", lo.index >= START), ("H1 2016-2020", (lo.index >= START) & (lo.index < SPLIT)), ("H2 2021-now", lo.index >= SPLIT)]:
        for lbl, r in [("低波籃 LOW-VOL", lo[mask]), ("高波籃 HIGH-VOL", hi[mask]), ("LOW−HIGN 價差", (lo - hi)[mask])]:
            c, s, d = metrics(r, per=12)
            print(f"  {seg:<13} {lbl:<16} {c*100:>+6.1f}%{s:>7.2f}{d*100:>7.0f}%")
        print()


# ---------- (2) TIMER: vol-percentile risk-off ----------
def vol_pct(price):
    r = price.pct_change()
    v = r.rolling(63).std() * np.sqrt(252)
    return v.rolling(504, min_periods=126).apply(lambda w: (w[-1] > w).mean() * 100, raw=True)


def timer_pos(vp, E, X):
    v = vp.values; pos = np.zeros(len(v)); inp = False
    for i in range(len(v)):
        if v[i] != v[i]:
            pos[i] = 1.0 if inp else 0.0; continue
        if not inp and v[i] < E:
            inp = True
        elif inp and v[i] > X:
            inp = False
        pos[i] = 1.0 if inp else 0.0
    return pd.Series(pos, index=vp.index).shift(1).fillna(0)


def capeff(bret, pos):
    pos = pos.reindex(bret.index).fillna(0)
    strat = pos * bret - COST * pos.diff().abs().fillna(0)
    exp = pos.mean(); inm = pos.values > 0.5; n = int(inm.sum())
    if n < 15:
        return float("nan"), float("nan"), exp
    r_in = strat[inm]
    dep = (1 + r_in).prod() ** (252 / n) - 1
    csh = r_in.mean() / r_in.std() * np.sqrt(252) if r_in.std() else float("nan")
    return dep, csh, exp


def timer():
    print("\n########## (2) TIMER 波動 risk-off(vol-pct 低=揸,高=走現金)部署CAGR%/條件Sharpe/曝險% ##########")
    for name, syms in CATS:
        bret = basket_ret(syms)
        idx = (1 + bret).cumprod(); vp = vol_pct(idx)
        print(f"\n========== {name} ==========")
        for seg, sub in [("FULL 2016+", bret), ("H1 2016-2020", bret[bret.index < SPLIT]), ("H2 2021-now", bret[bret.index >= SPLIT])]:
            c, s, d = metrics(sub)
            print(f"  --- {seg}  (B&H {c*100:+.1f}%/{s:.2f}/{d*100:.0f}%) ---")
            print(f"{'in<pct\\out>pct':<14}" + "".join(f"{'>'+str(x):>14}" for x in EXITS))
            for E in ENTRIES:
                row = f"<{E:<13}"
                for X in EXITS:
                    dep, csh, exp = capeff(sub, timer_pos(vp, E, X).reindex(sub.index, method="ffill"))
                    row += f"{dep*100:>+4.0f}/{csh:>4.2f}/{exp*100:>3.0f}".rjust(14)
                print(row)


def run():
    selection()
    timer()
    print("\nREAD: (1) 低波籃 Sharpe > 高波籃 = 低波異常成立(BAB)。(2) 若 timer 部署CAGR/Sharpe 唔高過 B&H "
          "= 波動 risk-off 冇用(甚至賣咗 capitulation)——對返 VIX 逆向發現。兩半都睇。")


if __name__ == "__main__":
    run()
