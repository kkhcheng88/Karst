"""RELATIVE STRENGTH — reframed as SELECTION + FILTER (user: RS is a filter/selection, NOT a timer).
Corrects `exp_momentum_family.py`'s RS-as-timer (which answered the wrong question for RS).

  (1) SELECTION — 5 RS tiers × multiple horizons. Each month rank the individual-stock universe into
      quintiles by 126d relative strength (stock 126d return / SPY 126d return). Forward ANNUALISED
      return per tier at horizons {21,63,126,252}d, vs the universe mean (B&H proxy). Monotonic &
      which horizon? FULL + H1 2016-2020 + H2 2021-now.

  (2) FILTER on RSI-2 — does buying the DIP only in RS LEADERS work better? RSI-2 dip trades
      (entry<{10,5} × exit>75) on each stock; bucket each trade by the stock's RS quintile AT ENTRY
      (pooled-distribution quintile — approximate, flag). Per bucket: per-trade% / win% / 部署效率%/yr.
      If top-RS-tier dips bounce more -> "buy the pullback in leaders" (RS filter improves RSI-2).

Individual-stock universe (cache; survivorship — flag, relative picture). 2bp/trade, 2016+, point-in-time.

    python backtest/experiments/exp_rs_selection_filter.py
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
RT = 0.0002
LB = 126


def _ann(r, h):
    return (1 + r) ** (252 / h) - 1 if r == r and r > -1 else float("nan")


def build_panel(px, spy):
    stocks = [t for t in px if isinstance(px.get(t), pd.Series) and len(px[t]) > 400]
    rows = []
    for tk in stocks:
        s = px[tk]; s = s[~s.index.duplicated()].sort_index()
        if len(s) < 300:
            continue
        me = s.resample("ME").last().index
        for t in me:
            if t < START:
                continue
            pos = s.index.searchsorted(t)
            sp = spy.index.searchsorted(t)
            if pos < LB or pos >= len(s) or sp < LB or sp >= len(spy):
                continue
            rs = (s.iloc[pos] / s.iloc[pos - LB]) / (spy.iloc[sp] / spy.iloc[sp - LB]) - 1
            rec = {"date": t, "rs": rs}
            for h in H:
                if pos + h < len(s) and s.iloc[pos] > 0:
                    rec[f"f{h}"] = float(np.clip(s.iloc[pos + h] / s.iloc[pos] - 1, -0.9, 3.0))
                else:
                    rec[f"f{h}"] = np.nan
            rows.append(rec)
    return pd.DataFrame(rows)


def selection(df):
    df = df.dropna(subset=["rs"]).copy()
    df["q"] = df.groupby("date")["rs"].transform(
        lambda x: pd.qcut(x, 5, labels=False, duplicates="drop") if x.nunique() > 5 else np.nan)
    print("\n########## (1) RS SELECTION — 5 tier 前望年化報酬(vs 宇宙均值=B&H)##########")
    for seg, mask in [("FULL 2016+", df["date"] >= START),
                      ("H1 2016-2020", (df["date"] >= START) & (df["date"] < SPLIT)),
                      ("H2 2021-now", df["date"] >= SPLIT)]:
        sub = df[mask]
        print(f"\n  === {seg} ===   前望年化%(每格)")
        print(f"{'RS tier':<12}" + "".join(f"{str(h)+'d':>10}" for h in H))
        for q in [4, 3, 2, 1, 0]:
            lbl = {4: "Q5 最強", 3: "Q4", 2: "Q3", 1: "Q2", 0: "Q1 最弱"}[q]
            g = sub[sub["q"] == q]
            row = f"{lbl:<12}"
            for h in H:
                row += f"{_ann(g[f'f{h}'].mean(), h) * 100:>+9.1f}%"
            print(row)
        row = f"{'宇宙均值':<12}"
        for h in H:
            row += f"{_ann(sub[f'f{h}'].mean(), h) * 100:>+9.1f}%"
        print(row)


def rs_filter(px, spy):
    print("\n########## (2) RS FILTER on RSI-2 — 買跌只揀 RS 高 tier?(每筆%/勝%/部署效率%/yr)##########")
    spyr = spy / spy.shift(LB)
    pooled = {}  # (entryE, tier) -> [(ret,hold)]
    rs_all = []
    trades = []
    for tk in [t for t in px if isinstance(px.get(t), pd.Series) and len(px[t]) > 400]:
        s = px[tk]; s = s[~s.index.duplicated()].sort_index()
        if len(s) < 300:
            continue
        s = s[s.index >= (START - pd.Timedelta(days=400))]
        rs = (s / s.shift(LB)) / spyr.reindex(s.index, method="ffill") - 1
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
                    if s.index[e] >= START and p[e] > 0:
                        rv = rs.iloc[e]
                        if rv == rv:
                            ret = float(np.clip(p[i] / p[e] - 1, -0.9, 3.0)) - RT
                            trades.append((E, rv, ret, i - e, s.index[e]))
                    e = None
    if not trades:
        print("  no trades"); return
    rsv = np.array([t[1] for t in trades])
    qs = np.quantile(rsv, [0.2, 0.4, 0.6, 0.8])
    END = pd.Timestamp("2100-01-01")
    for seg, lo_d, hi_d in [("FULL 2016+", START, END), ("H1 2016-2020", START, SPLIT), ("H2 2021-now", SPLIT, END)]:
        for E in [10, 5]:
            print(f"\n  === {seg} · entry RSI2<{E} / exit>75 ===")
            print(f"{'RS tier(entry)':<16}{'每筆%':>8}{'勝%':>6}{'持有d':>7}{'n':>7}{'效率%/yr':>9}")
            for ti, lbl in [(4, "Q5 最強"), (3, "Q4"), (2, "Q3"), (1, "Q2"), (0, "Q1 最弱")]:
                lo = qs[ti - 1] if ti > 0 else -np.inf
                hi = qs[ti] if ti < 4 else np.inf
                sel = [(r, h) for (e, rv, r, h, d) in trades if e == E and lo <= rv < hi and lo_d <= d < hi_d]
                if len(sel) < 20:
                    print(f"  {lbl:<14} n<20"); continue
                r = np.array([a for a, _ in sel]); hh = np.array([b for _, b in sel])
                eff = (r.mean() / max(hh.mean(), 1)) * 252 * 100
                print(f"  {lbl:<14}{r.mean()*100:>+7.1f}{(r>0).mean()*100:>6.0f}{hh.mean():>7.0f}{len(sel):>7}{eff:>+8.0f}%")


def run():
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    spy = D.load("SPY")["close"]; spy = spy[~spy.index.duplicated()].sort_index()
    print(f"[rs] universe {sum(1 for t in px if isinstance(px.get(t), pd.Series))} priced")
    df = build_panel(px, spy)
    print(f"[rs] panel {len(df)} name-months")
    selection(df)
    rs_filter(px, spy)
    print("\nREAD: (1) Q5>Q4>...>Q1 單調 + 高過宇宙均值 = RS 選股有效;睇邊個 horizon 最勁。"
          "\n(2) 若 Q5(強勢)嘅買跌 每筆/效率 高過 Q1 = 『買 leader 回調』成立,RS filter 改善 RSI-2。")


if __name__ == "__main__":
    run()
