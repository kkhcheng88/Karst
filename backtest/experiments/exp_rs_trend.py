"""RS refined — LEVEL × TREND 2x2 (user: quintiles conflate >0/<0 and ignore RS trend; test whether
RISING vs rolling-over RS matters). Two absolute, point-in-time dimensions (no pooled-quantile threshold
-> also fixes the prior look-ahead-on-boundary caveat):

  LEVEL  = sign of 126d relative return vs SPY:  RS>0 (beating SPY / leader) vs RS<0 (laggard).
  TREND  = RS LINE (stock/SPY ratio) vs its own 50d SMA:  RISING (above) vs FALLING (below, rolling over).

Four quadrants:
  L+/T↑ 加速 leader | L+/T↓ 褪色 leader(陷阱?) | L-/T↑ 翻身 laggard | L-/T↓ 惡化 laggard
Hypothesis: L+/T↑ best; L+/T↓ (fading leader) the momentum-crash trap despite high level.

  (1) SELECTION — forward ANNUALISED return per quadrant at 21/63/126/252d, FULL + two-halves.
  (2) FILTER on RSI-2 — RSI-2 dip trades (entry<{10,5}/exit>75) bucketed by the quadrant AT ENTRY;
      does 'buy the dip in a RISING-RS leader' beat 'fading-RS leader'? per-trade%/win%/eff, two-halves.

Individual-stock universe (cache; survivorship — relative). fwd/trade clipped [-0.9,3.0]. 2016+, 2bp/trade.

    python backtest/experiments/exp_rs_trend.py
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
H = [21, 63, 126, 252]
START = pd.Timestamp("2016-01-01")
SPLIT = pd.Timestamp("2021-01-01")
END = pd.Timestamp("2100-01-01")
RT = 0.0002
LB = 126
SMA = 50
QUAD = [("L+/T↑ 加速leader", 1, 1), ("L+/T↓ 褪色leader", 1, 0),
        ("L-/T↑ 翻身laggard", 0, 1), ("L-/T↓ 惡化laggard", 0, 0)]


def _ann(r, h):
    return (1 + r) ** (252 / h) - 1 if r == r and r > -1 else float("nan")


def _prep(s, spy):
    s = s[~s.index.duplicated()].sort_index()
    spa = spy.reindex(s.index, method="ffill")
    rel126 = (s / s.shift(LB)) / (spa / spa.shift(LB)) - 1     # LEVEL
    rsline = s / spa
    trend_up = (rsline > rsline.rolling(SMA).mean()).astype(float)  # TREND (RS line vs own SMA)
    return s, rel126, trend_up


def build_panel(px, spy):
    stocks = [t for t in px if isinstance(px.get(t), pd.Series) and len(px[t]) > 400]
    rows = []
    for tk in stocks:
        s0 = px[tk]
        if len(s0) < 300:
            continue
        s, rel126, tup = _prep(s0, spy)
        me = s.resample("ME").last().index
        for t in me:
            if t < START:
                continue
            pos = s.index.searchsorted(t)
            if pos < LB or pos >= len(s):
                continue
            lv = rel126.iloc[pos]; tr = tup.iloc[pos]
            if lv != lv or tr != tr:
                continue
            rec = {"date": t, "L": 1 if lv > 0 else 0, "T": int(tr)}
            for h in H:
                rec[f"f{h}"] = float(np.clip(s.iloc[pos + h] / s.iloc[pos] - 1, -0.9, 3.0)) if pos + h < len(s) and s.iloc[pos] > 0 else np.nan
            rows.append(rec)
    return pd.DataFrame(rows)


def selection(df):
    print("\n########## (1) RS LEVEL×TREND SELECTION — 前望年化%(vs 宇宙均值)##########")
    for seg, mask in [("FULL 2016+", df["date"] >= START),
                      ("H1 2016-2020", (df["date"] >= START) & (df["date"] < SPLIT)),
                      ("H2 2021-now", df["date"] >= SPLIT)]:
        sub = df[mask]
        print(f"\n  === {seg} ===   (n=name-months)")
        print(f"{'象限':<20}" + "".join(f"{str(h)+'d':>9}" for h in H) + f"{'n':>9}")
        for lbl, L, T in QUAD:
            g = sub[(sub["L"] == L) & (sub["T"] == T)]
            row = f"{lbl:<20}"
            for h in H:
                row += f"{_ann(g[f'f{h}'].mean(), h) * 100:>+8.1f}%"
            print(row + f"{len(g):>9}")
        row = f"{'宇宙均值':<20}"
        for h in H:
            row += f"{_ann(sub[f'f{h}'].mean(), h) * 100:>+8.1f}%"
        print(row + f"{len(sub):>9}")


def rs_filter(px, spy):
    print("\n########## (2) RS LEVEL×TREND FILTER on RSI-2 — 每筆%/勝%/持有d[n]/效率%/yr ##########")
    trades = []
    stocks = [t for t in px if isinstance(px.get(t), pd.Series) and len(px[t]) > 400]
    for tk in stocks:
        s0 = px[tk]
        if len(s0) < 300:
            continue
        s, rel126, tup = _prep(s0, spy)
        s = s[s.index >= (START - pd.Timedelta(days=400))]
        rel126 = rel126.reindex(s.index); tup = tup.reindex(s.index)
        r2 = rsi(s, 2).values
        for E in [10, 5]:
            n = len(s); pos = np.zeros(n); inp = False
            for i in range(n):
                if not inp and r2[i] < E:
                    inp = True
                elif inp and r2[i] > 75:
                    inp = False
                pos[i] = 1.0 if inp else 0.0
            posx = pd.Series(pos, index=s.index).shift(1).fillna(0).values
            p = s.values; e = None
            for i in range(1, n):
                if posx[i] > 0 and posx[i - 1] == 0:
                    e = i
                elif posx[i] == 0 and posx[i - 1] > 0 and e is not None:
                    lv = rel126.iloc[e]; tr = tup.iloc[e]
                    if s.index[e] >= START and p[e] > 0 and lv == lv and tr == tr:
                        ret = float(np.clip(p[i] / p[e] - 1, -0.9, 3.0)) - RT
                        trades.append((E, 1 if lv > 0 else 0, int(tr), ret, i - e, s.index[e]))
                    e = None
    for seg, lo_d, hi_d in [("FULL 2016+", START, END), ("H1 2016-2020", START, SPLIT), ("H2 2021-now", SPLIT, END)]:
        for E in [10, 5]:
            print(f"\n  === {seg} · entry RSI2<{E} / exit>75 ===")
            print(f"{'象限':<20}{'每筆%':>8}{'勝%':>6}{'持有d':>7}{'n':>8}{'效率%/yr':>9}")
            for lbl, L, T in QUAD:
                sel = [(r, h) for (e, l, t, r, h, d) in trades if e == E and l == L and t == T and lo_d <= d < hi_d]
                if len(sel) < 20:
                    print(f"  {lbl:<18} n<20"); continue
                r = np.array([a for a, _ in sel]); hh = np.array([b for _, b in sel])
                eff = (r.mean() / max(hh.mean(), 1)) * 252 * 100
                print(f"  {lbl:<18}{r.mean()*100:>+7.1f}{(r>0).mean()*100:>6.0f}{hh.mean():>7.0f}{len(sel):>8}{eff:>+8.0f}%")


def run():
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    spy = D.load("SPY")["close"]; spy = spy[~spy.index.duplicated()].sort_index()
    print(f"[rs-trend] universe {sum(1 for t in px if isinstance(px.get(t), pd.Series))} priced; LEVEL=126d rel, TREND=RSline vs SMA{SMA}")
    df = build_panel(px, spy)
    print(f"[rs-trend] panel {len(df)} name-months")
    selection(df)
    rs_filter(px, spy)
    print("\nREAD: 假設 L+/T↑(加速leader)最強、L+/T↓(褪色leader)係陷阱。FILTER 睇『買升緊-RS leader 嘅 dip』"
          "係咪贏『褪色-RS leader 嘅 dip』。兩半睇穩健。")


if __name__ == "__main__":
    run()
