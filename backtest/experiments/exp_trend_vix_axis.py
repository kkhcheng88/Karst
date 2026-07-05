"""The 2D done RIGHT — TREND (bull/bear, SPY vs 200SMA) × FEAR (VIX). Replaces the failed credit axis
(exp_credit_axis.py: credit regime-unstable, no increment to VIX). Both these axes ARE separately
validated by us (trend/momentum = robust engine; VIX = stable contrarian fear). Question: does the
4-QUADRANT interaction hold? (Test before asserting — we got burned asserting the credit quadrants.)

Axes:  TREND = SPY > 200SMA (bull) / < (bear)   ·   FEAR = VIX >20 elevated (also >28 extreme)
Quadrants + hypothesis (the user's original "2D / potential revision" idea):
  ① bull+calm   正常上升        -> 穩定正
  ② bull+fear   上升中恐懼(買dip)-> 我估最好(buy fear in an uptrend)
  ③ bear+fear   下跌中恐慌       -> 暴烈(深回撤,可能急彈)
  ④ bear+calm   自滿熊/派發       -> 我估最差(complacent bear)
Forward SPY 21/63d return + forward 63d worst-drawdown, per quadrant. FULL + two-halves (split 2010,
pre/post-QE). + continuous partial corr both ways (trend|VIX, VIX|trend). SPY 1993+, VIX 1990+. yfinance.

    python backtest/experiments/exp_trend_vix_axis.py
"""
import numpy as np
import pandas as pd

SPLIT = pd.Timestamp("2010-01-01")


def dl(tk):
    import yfinance as yf
    v = yf.download(tk, start="1993-01-01", progress=False, auto_adjust=True)["Close"]
    if isinstance(v, pd.DataFrame):
        v = v.iloc[:, 0]
    return v[~v.index.duplicated()].sort_index()


def sc(x, y):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    return d["x"].corr(d["y"], method="spearman") if len(d) > 50 else float("nan")


def pcorr(x, y, z):
    d = pd.DataFrame({"x": x, "y": y, "z": z}).dropna()
    if len(d) < 50:
        return float("nan")
    r = d.rank()
    rx = r["x"] - np.polyval(np.polyfit(r["z"], r["x"], 1), r["z"])
    ry = r["y"] - np.polyval(np.polyfit(r["z"], r["y"], 1), r["z"])
    return np.corrcoef(rx, ry)[0, 1]


def run():
    spy, vix = dl("SPY"), dl("^VIX")
    idx = spy.index
    sma200 = spy.rolling(200).mean()
    trend_dist = spy / sma200 - 1            # +ve = above 200SMA (bull), continuous
    bull = spy > sma200
    vixa = vix.reindex(idx).ffill()
    print(f"[trend×vix] {idx[0].date()}→{idx[-1].date()}  SPY vs 200SMA × VIX, n={len(idx)}")

    fwd21 = spy.shift(-21) / spy - 1
    fwd63 = spy.shift(-63) / spy - 1
    fwd_min = spy[::-1].rolling(63, min_periods=10).min()[::-1] / spy - 1

    print("\n=== (1) 連續:各軸對前望 63d 報酬(Spearman;partial 控另一軸)===")
    print(f"{'seg':<11}{'trend→ret':>11}{'trend|VIX':>11}{'VIX→ret':>10}{'VIX|trend':>11}")
    for lbl, m in [("FULL", idx >= idx[0]), ("H1<2010", idx < SPLIT), ("H2 2010+", idx >= SPLIT)]:
        print(f"{lbl:<11}{sc(trend_dist[m], fwd63[m]):>+11.3f}{pcorr(trend_dist[m], fwd63[m], vixa[m]):>+11.3f}"
              f"{sc(vixa[m], fwd63[m]):>+10.3f}{pcorr(vixa[m], fwd63[m], trend_dist[m]):>+11.3f}")
    print("  (trend→ret >0 = 順勢;VIX→ret >0 = 逆向買恐懼。partial 睇邊軸有獨立增量。)")

    hv = vixa > 20
    quads = [("② 牛市+恐懼(升中買dip)", bull & hv), ("① 牛市+平靜(正常)", bull & ~hv),
             ("④ 熊市+平靜(自滿/派發)", ~bull & ~hv), ("③ 熊市+恐慌(下跌中)", ~bull & hv)]
    print("\n=== (2) 四象限:牛熊(200SMA)× VIX(>20)→ 前望21d / 63d / 63d最差 / n ===")
    for seg, sm in [("FULL 1993+", idx >= idx[0]), ("H1 1993-09", idx < SPLIT), ("H2 2010+", idx >= SPLIT)]:
        print(f"\n  --- {seg} ---")
        for name, q in quads:
            mm = q & sm & fwd63.notna()
            n = int(mm.sum())
            if n < 20:
                print(f"  {name:<24} n<20"); continue
            print(f"  {name:<24}{fwd21[mm].mean()*100:>+7.2f}%{fwd63[mm].mean()*100:>+8.2f}%{fwd_min[mm].mean()*100:>+9.2f}%{n:>7}")

    print("\n=== 對照:極端恐懼 VIX>28 分牛熊 ===")
    for name, q in [("VIX>28 + 牛市", (vixa > 28) & bull), ("VIX>28 + 熊市", (vixa > 28) & ~bull)]:
        mm = q & fwd63.notna()
        if int(mm.sum()) >= 20:
            print(f"  {name:<16} 前望63d {fwd63[mm].mean()*100:>+.2f}%  最差 {fwd_min[mm].mean()*100:>+.2f}%  n={int(mm.sum())}")
        else:
            print(f"  {name:<16} n<20")

    print("\nREAD: 若 ② 牛市+恐懼 前望最好、④ 熊市+平靜 最差 = 你原本個 2D idea 成立(順勢中買恐懼)。"
          "\n若兩軸 partial 都顯著 = 兩軸都有獨立增量(值得建 2D);若得一軸 = 淨用嗰軸。")


if __name__ == "__main__":
    run()
