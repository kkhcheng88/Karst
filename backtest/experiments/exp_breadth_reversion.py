"""BREADTH REVERSION — does market breadth predict MEAN-REVERSION at the TAILS?

We already killed breadth LEVEL as a *linear* forward-return predictor (weak, VIX-redundant).
But reversion signals classically live in the NON-LINEAR tails / thrust / divergence, which a
linear Spearman IC is blind to. This tests those constructs directly, with CONDITIONAL returns:

  (1) DECILE conditional forward return — is there a U-shape / tail asymmetry (washout->bounce,
      overheated->fade) that the linear IC averages away?
  (2) WASHOUT x VIX double-sort — does deep-washout breadth add ANY increment OVER VIX
      (which spikes at washouts anyway)? This is the real bar.
  (3) breadth THRUST (recover from washout) — rare Zweig-style major-bottom signal.
  (4) price/breadth DIVERGENCE — SPY near a high but participation narrowing -> pullback?
  (5) BONUS: sector-participation breadth (% of 11 SPDR above own 50SMA) — clean, long history.

Method: CONDITIONAL mean/median/win%/n per bucket (NOT linear IC); two-halves (dynamic median
split for balance); forward 5/21/63d. Breadth from px_defeatbeta cache = SURVIVORSHIP-biased ->
we use RELATIVE deciles/percentiles of its own history (not absolute %), which the bias survives.
SPY/VIX/SPDR via yfinance. Baseline printed so every conditional is read as an EDGE vs baseline.

    python backtest/experiments/exp_breadth_reversion.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")


def dl(tk):
    import yfinance as yf
    v = yf.download(tk, start="1999-01-01", progress=False, auto_adjust=True)["Close"]
    if isinstance(v, pd.DataFrame):
        v = v.iloc[:, 0]
    return v[~v.index.duplicated()].sort_index()


def build_breadth():
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    R, A50, A200 = {}, {}, {}
    for t, s in px.items():
        if not isinstance(s, pd.Series) or len(s) < 260:
            continue
        s = s[~s.index.duplicated()].sort_index()
        R[t] = s.pct_change()
        A50[t] = s > s.rolling(50).mean()
        A200[t] = s > s.rolling(200).mean()
    R = pd.DataFrame(R); A50 = pd.DataFrame(A50); A200 = pd.DataFrame(A200)
    a50 = A50.sum(1) / A50.notna().sum(1) * 100
    a200 = A200.sum(1) / A200.notna().sum(1) * 100
    adv = (R > 0).sum(1) / R.notna().sum(1) * 100
    n = R.notna().sum(1)
    d = a50.dropna()
    print(f"[breadth] {R.shape[1]} stocks (survivorship-biased); dates {d.index[0].date()}..{d.index[-1].date()}; "
          f"median names/day {int(n.median())}")
    return adv, a50, a200


def st(fr):
    fr = fr.dropna()
    n = len(fr)
    if n < 15:
        return f"n={n:<5}(太少)"
    return f"n={n:<5} mean={fr.mean()*100:+5.2f}% med={fr.median()*100:+5.2f}% win={(fr > 0).mean()*100:3.0f}%"


def run():
    adv, a50, a200 = build_breadth()
    spy, vix = dl("SPY"), dl("^VIX")
    idx = spy.index
    a50 = a50.reindex(idx).ffill(); a200 = a200.reindex(idx).ffill(); adv = adv.reindex(idx).ffill()
    vixa = vix.reindex(idx).ffill()
    # keep only where breadth exists
    valid = a50.notna()
    idx = a50[valid].index
    spy = spy.reindex(idx); vixa = vixa.reindex(idx)
    a50 = a50.reindex(idx); a200 = a200.reindex(idx); adv = adv.reindex(idx)

    F = {h: (spy.shift(-h) / spy - 1) for h in [5, 21, 63]}
    SPLIT = a50.index[len(a50) // 2]
    halves = [("FULL", pd.Series(True, index=idx)),
              (f"H1<{SPLIT.year}", pd.Series(idx < SPLIT, index=idx)),
              (f"H2 {SPLIT.year}+", pd.Series(idx >= SPLIT, index=idx))]
    print(f"[split] two-halves at median date {SPLIT.date()}")
    print("\nBASELINE(無條件):  " + "  ".join(f"{h}d {st(F[h])}" for h in [5, 21, 63]))

    # (1) DECILE conditional
    print("\n" + "=" * 96)
    print("(1) DECILE 條件報酬 —— breadth 分 10 格睇尾巴(底格洗盤→彈? 頂格過熱→回?)線性 IC 睇唔到嘅非線性")
    for bname, b in [("%above50", a50), ("%above200", a200)]:
        print(f"\n  ── {bname}:decile × forward 21d / 63d(FULL)──")
        d = pd.qcut(b, 10, labels=False, duplicates="drop")
        for q in sorted(pd.unique(d.dropna())):
            m = (d == q)
            print(f"    D{int(q)} [{b[m].min():5.1f}-{b[m].max():5.1f}]   21d {st(F[21][m])}   63d {st(F[63][m])}")

    # (1b) extreme tails two-halves
    print("\n  ── 極端尾巴 two-halves(%above50 底/頂 10%)——")
    p10, p90 = a50.quantile(.10), a50.quantile(.90)
    for lbl, m in halves:
        print(f"    {lbl:9} 洗盤(≤{p10:.0f}%): 21d {st(F[21][m & (a50 <= p10)])} | 63d {st(F[63][m & (a50 <= p10)])}")
        print(f"    {lbl:9} 過熱(≥{p90:.0f}%): 21d {st(F[21][m & (a50 >= p90)])} | 63d {st(F[63][m & (a50 >= p90)])}")

    # (2) WASHOUT x VIX double-sort — the increment-over-VIX bar
    print("\n" + "=" * 96)
    print("(2) 洗盤 × VIX 雙排序 —— breadth 有冇喺 VIX 之上加值?(比『洗盤&VIX高』vs『非洗盤&VIX高』)")
    p20 = a50.quantile(.20); vhi = vixa.quantile(.80)
    conds = [("洗盤&VIX高", (a50 <= p20) & (vixa >= vhi)),
             ("洗盤&VIX低", (a50 <= p20) & (vixa < vhi)),
             ("非洗盤&VIX高", (a50 > p20) & (vixa >= vhi)),
             ("非洗盤&VIX低", (a50 > p20) & (vixa < vhi))]
    for cn, c in conds:
        print(f"    {cn:14} 21d {st(F[21][c])} | 63d {st(F[63][c])}")
    print("    → 讀:若『洗盤&VIX高』明顯贏『非洗盤&VIX高』= breadth 喺 VIX 之上有增量;否則 VIX 已捉走。")

    # (3) THRUST
    print("\n" + "=" * 96)
    print("(3) Breadth THRUST(10 日前處洗盤、家陣急彈 >10pp)—— 罕見大底信號(事件自相關,n 偏高)")
    thrust = (a50.shift(10) <= p20) & (a50 > a50.shift(10) + 10) & (a50 > a50.shift(5))
    for lbl, m in halves:
        mm = m & thrust
        print(f"    {lbl:9} thrust: 21d {st(F[21][mm])} | 63d {st(F[63][mm])}")

    # (4) DIVERGENCE
    print("\n" + "=" * 96)
    print("(4) 價/breadth 背離 —— SPY 貼近 63d 高 但參與度較 20d 前低 → 回檔?(vs 確認)")
    near_high = spy >= spy.rolling(63).max() * 0.98
    diverge = near_high & (a50 < a50.shift(20))
    confirm = near_high & (a50 >= a50.shift(20))
    for lbl, m in halves:
        print(f"    {lbl:9} 背離(高位+參與↓): 21d {st(F[21][m & diverge])} | 63d {st(F[63][m & diverge])}")
        print(f"    {lbl:9} 確認(高位+參與↑): 21d {st(F[21][m & confirm])} | 63d {st(F[63][m & confirm])}")

    # (5) SECTOR-PARTICIPATION breadth (clean, long)
    print("\n" + "=" * 96)
    print("(5) 板塊參與度 breadth(11 SPDR 幾多喺自己 50SMA 上)—— 乾淨、無 survivorship、長史")
    spdr = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]
    closes = {}
    for t in spdr:
        try:
            closes[t] = dl(t)
        except Exception as e:
            print(f"    (skip {t}: {e})")
    C = pd.DataFrame(closes)
    above = C > C.rolling(50).mean()
    spct = (above.sum(1) / above.notna().sum(1) * 100)
    d2 = spct.dropna()
    print(f"    [sector-breadth] {C.shape[1]} SPDR; dates {d2.index[0].date()}..{d2.index[-1].date()}")
    spct = spct.reindex(idx).ffill()
    Fs = {h: (spy.shift(-h) / spy - 1) for h in [5, 21, 63]}
    vhi2 = vixa.quantile(.80)
    for lbl, m in halves:
        wash = m & (spct <= 20)
        washv = m & (spct <= 20) & (vixa >= vhi2)
        hot = m & (spct >= 90)
        print(f"    {lbl:9} 板塊洗盤(≤20%上50): 21d {st(Fs[21][wash])} | 63d {st(Fs[63][wash])}")
        print(f"    {lbl:9}   └ &VIX高:        21d {st(Fs[21][washv])} | 63d {st(Fs[63][washv])}")
        print(f"    {lbl:9} 板塊過熱(≥90%):    21d {st(Fs[21][hot])} | 63d {st(Fs[63][hot])}")

    print("\nREAD: 對比每格 mean vs BASELINE。reversion 若真 → 洗盤/thrust 底格 21-63d mean 明顯 > baseline、")
    print("      過熱/背離 < baseline;而且『洗盤&VIX高』要贏『非洗盤&VIX高』先算喺 VIX 之上有增量。")


if __name__ == "__main__":
    run()
