"""VERIFY the breadth-reversion claims — two challenges from the user:

(1) DATES: extract the actual episodes where "washout & VIX-high" fired vs "VIX-high & NO
    washout" fired -> eyeball whether the former = real crash bottoms (2008/2020/2022) and
    the latter = isolated scares. Print start/end + peak VIX + trough breadth per episode.

(2) ASYMMETRY is it real or a DRIFT artifact? %above50 is directionally symmetric (100-%below50),
    so if washout->bounce but overheated->no-fade, that could just be the market's long-run UP
    drift inflating every mean. So we re-read each decile with:
      - EXCESS = mean - unconditional baseline (removes drift)
      - DOWNSIDE = P(fwd < -5%) and worst-5% (5th pctile) -> does the TOP hide crash risk?
    And an explicit SHORT-SIDE test: after overheated breadth, is fwd return BELOW baseline /
    is the left tail fatter? If not, a reversed (short-the-top) setup genuinely adds no value.

    python backtest/experiments/exp_breadth_reversion_verify.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp_breadth_reversion import build_breadth, dl  # noqa: E402


def episodes(mask, gap=20):
    """Group True-days into episodes; new episode when > `gap` trading days apart."""
    m = mask.fillna(False).values
    pos = np.where(m)[0]
    if len(pos) == 0:
        return []
    idx = mask.index
    eps, s = [], 0
    for i in range(1, len(pos)):
        if pos[i] - pos[i - 1] > gap:
            eps.append((pos[s], pos[i - 1]))
            s = i
    eps.append((pos[s], pos[-1]))
    return [(idx[a], idx[b], b - a + 1) for a, b in eps]


def run():
    adv, a50, a200 = build_breadth()
    spy, vix = dl("SPY"), dl("^VIX")
    idx = a50.dropna().index
    idx = idx.intersection(spy.index)
    spy = spy.reindex(idx); a50 = a50.reindex(idx); vixa = vix.reindex(idx).ffill()
    F = {h: (spy.shift(-h) / spy - 1) for h in [21, 63]}
    base = {h: F[h].mean() for h in [21, 63]}
    print(f"BASELINE 無條件:  21d {base[21]*100:+.2f}%   63d {base[63]*100:+.2f}%")

    p20 = a50.quantile(.20); vhi = vixa.quantile(.80)
    print(f"[thresholds] 洗盤 = %above50 <= {p20:.1f}(底 20%);  VIX 高 = >= {vhi:.1f}(頂 20%)")

    # ---------- (1) EPISODE DATES ----------
    wash_vh = (a50 <= p20) & (vixa >= vhi)
    scare = (a50 > p20) & (vixa >= vhi)
    for name, mask in [("洗盤 & VIX 高(應為真.股災底)", wash_vh),
                       ("VIX 高 & 冇洗盤(應為孤立驚嚇)", scare)]:
        print("\n" + "=" * 92)
        print(f"({name})  事件(gap>20 交易日分段;只列 >=3 日)")
        for a, b, n in episodes(mask):
            if n < 3:
                continue
            seg = slice(a, b)
            pv = vixa.loc[seg].max()
            tb = a50.loc[seg].min()
            print(f"    {a.date()} → {b.date()}  ({n:>3}d)  VIX 峰值 {pv:5.1f}  breadth 谷底 {tb:4.1f}%")

    # ---------- (2) ASYMMETRY: excess + downside per decile ----------
    print("\n" + "=" * 92)
    print("(2) %above50 decile:mean / EXCESS(減 drift)/ 下行風險 —— 頂格係咪真.唔插定俾 drift 呃")
    d = pd.qcut(a50, 10, labels=False, duplicates="drop")
    print(f"    {'decile':<20}{'21d mean':>10}{'excess':>9}{'P(<-5%)':>9}{'worst5%':>9}"
          f"{'63d mean':>11}{'excess':>9}{'P(<-10%)':>9}")
    for q in sorted(pd.unique(d.dropna())):
        m = d == q
        f21 = F[21][m].dropna(); f63 = F[63][m].dropna()
        lo, hi = a50[m].min(), a50[m].max()
        print(f"    D{int(q)} [{lo:5.1f}-{hi:5.1f}]  "
              f"{f21.mean()*100:>+8.2f}%{(f21.mean()-base[21])*100:>+8.2f}"
              f"{(f21 < -.05).mean()*100:>8.0f}%{f21.quantile(.05)*100:>+8.1f}%"
              f"{f63.mean()*100:>+9.2f}%{(f63.mean()-base[63])*100:>+8.2f}"
              f"{(f63 < -.10).mean()*100:>8.0f}%")

    # ---------- (3) explicit SHORT-SIDE test ----------
    print("\n" + "=" * 92)
    print("(3) 反向(做空)測試 —— 頂格/過熱之後,fwd 有冇低過 baseline / 左尾有冇更肥?")
    p80, p90 = a50.quantile(.80), a50.quantile(.90)
    for lbl, m in [("底 10%(洗盤)", a50 <= a50.quantile(.10)),
                   ("頂 10%(過熱)", a50 >= p90),
                   ("頂 20%(過熱)", a50 >= p80)]:
        f21 = F[21][m].dropna(); f63 = F[63][m].dropna()
        print(f"    {lbl:14} 21d mean {f21.mean()*100:+5.2f}%(excess {(f21.mean()-base[21])*100:+5.2f}pp, "
              f"P(<-5%) {(f21 < -.05).mean()*100:3.0f}%, worst5% {f21.quantile(.05)*100:+6.1f}%) | "
              f"63d mean {f63.mean()*100:+5.2f}%(excess {(f63.mean()-base[63])*100:+5.2f}pp)")
    print("    → 若『做空頂格』有值:頂格 fwd 應 << baseline(負 excess)或左尾明顯更肥。否則反向無值。")


if __name__ == "__main__":
    run()
