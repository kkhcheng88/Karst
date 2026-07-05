"""CREDIT as the RISK axis — does it actually work, incremental to VIX? (User: "risk=credit, did we
backtest?" Answer was NO — this fills the gap.) Credit proxy = HYG/LQD ratio (junk vs investment-grade;
ratio FALLING = credit spreads widening = structural risk-off). VIX = the fear/emotion axis.

Two tests (mirror the GEX test's discipline):
  (1) Does credit-stress predict forward SPY return / drawdown, INCREMENTAL to VIX? (partial corr | VIX)
  (2) The 2-axis 4-QUADRANT framework (the XY plot): VIX high/low × credit stress/healthy ->
      forward SPY 21/63d return + forward 63d worst-drawdown. Hypothesis:
        ② VIX高 + credit穩 (純恐慌)      -> 高前望報酬 (買點/反彈)
        ③ VIX高 + credit擴 (真危機)      -> 低/負 (減曝險)
        ④ VIX低 + credit擴 (自滿+轉差)    -> 差 (頂部警號)
        ① VIX低 + credit穩 (正常)        -> 正常
FULL + two-halves (split 2016). HYG inception 2007. Data: yfinance (free).

    python backtest/experiments/exp_credit_axis.py
"""
import numpy as np
import pandas as pd

SPLIT = pd.Timestamp("2016-01-01")


def dl(tk):
    import yfinance as yf
    v = yf.download(tk, start="2007-01-01", progress=False, auto_adjust=True)["Close"]
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
    hyg, lqd, vix, spy = dl("HYG"), dl("LQD"), dl("^VIX"), dl("SPY")
    idx = spy.index
    ratio = (hyg / lqd.reindex(hyg.index)).reindex(idx).ffill()
    ma = ratio.rolling(126).mean()
    stress_c = -(ratio / ma - 1)                     # +ve = credit stress (ratio below MA)
    stress_b = (ratio < ma)                           # True = stress
    vixa = vix.reindex(idx).ffill()
    print(f"[credit] {idx[0].date()}→{idx[-1].date()}  HYG/LQD + VIX + SPY, n={len(idx)}")

    fwd21 = spy.shift(-21) / spy - 1
    fwd63 = spy.shift(-63) / spy - 1
    fwd_min = spy[::-1].rolling(63, min_periods=10).min()[::-1] / spy - 1   # forward 63d worst level

    print("\n=== (1) credit-stress → 前望 SPY 報酬(Spearman;partial 控 VIX)===")
    print(f"{'seg':<9}{'':2}{'credit→ret63':>14}{'partial|VIX':>13}{'VIX→ret63':>12}{'credit→ret21':>14}")
    for lbl, m in [("FULL", idx >= idx[0]), ("H1<2016", idx < SPLIT), ("H2 2016+", idx >= SPLIT)]:
        cc = sc(stress_c[m], fwd63[m]); pc = pcorr(stress_c[m], fwd63[m], vixa[m])
        cv = sc(vixa[m], fwd63[m]); c21 = sc(stress_c[m], fwd21[m])
        print(f"{lbl:<11}{cc:>+14.3f}{pc:>+13.3f}{cv:>+12.3f}{c21:>+14.3f}")
    print("  (credit→ret 負 = credit 擴→未來股市差;partial|VIX ≈0 = 對 VIX 無增量;大 = 有獨立訊號)")

    print("\n=== (2) 四象限:VIX(>20 elevated)× credit(ratio<126MA=擴)→ 前望% ===")
    hv = vixa > 20
    quads = [("② VIX高+credit穩(純恐慌/買)", hv & ~stress_b),
             ("③ VIX高+credit擴(真危機/走)", hv & stress_b),
             ("④ VIX低+credit擴(頂部警號)", ~hv & stress_b),
             ("① VIX低+credit穩(正常)", ~hv & ~stress_b)]
    for seg, sm in [("FULL 2007+", idx >= idx[0]), ("H1 2007-15", idx < SPLIT), ("H2 2016+", idx >= SPLIT)]:
        print(f"\n  --- {seg} ---   前望21d / 前望63d / 前望63d最差 / n")
        for name, q in quads:
            mm = q & sm
            n = int((mm & fwd63.notna()).sum())
            if n < 20:
                print(f"  {name:<26} n<20"); continue
            print(f"  {name:<26}{fwd21[mm].mean()*100:>+7.2f}%{fwd63[mm].mean()*100:>+8.2f}%{fwd_min[mm].mean()*100:>+9.2f}%{n:>7}")

    print("\n=== 對照:極端恐懼 VIX>28 分 credit ===")
    for name, q in [("VIX>28 + credit穩", (vixa > 28) & ~stress_b), ("VIX>28 + credit擴", (vixa > 28) & stress_b)]:
        mm = q & fwd63.notna()
        if int(mm.sum()) >= 20:
            print(f"  {name:<20} 前望63d {fwd63[mm].mean()*100:>+.2f}%  最差 {fwd_min[mm].mean()*100:>+.2f}%  n={int(mm.sum())}")
        else:
            print(f"  {name:<20} n<20")

    print("\nREAD: 若四象限次序 ②>①>④>③(尤其 ③ 差過 ②、④ 差過 ①)= 兩軸框架成立、credit 有結構訊號。"
          "\n若 partial|VIX 明顯負 = credit 對 VIX 有增量(值得建 Y 軸);若 ≈0 = VIX 已夠(同 GEX 一樣)。")


if __name__ == "__main__":
    run()
