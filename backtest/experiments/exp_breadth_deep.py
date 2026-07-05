"""BREADTH divergence done DEEP — answer the rigor questions:
  (A) MULTI-TIMEFRAME + forward IC: does breadth reflect in 1w or really 3m? (weekly IC, 1w/1m/3m/6m)
  (B) BOTH SIDES: top (near-high + narrow = distribution) AND bottom (near-low + broad = breadth thrust)?
  (C) measure = RSP/SPY (equal-vs-cap weight) — the standard clean breadth proxy (≈ %-above-200SMA / A-D,
      no survivorship). Cross-check vs %-above-200SMA (cache, survivorship-flagged) at market level.
Forward SPY return + 63d worst-drawdown. Two-halves (split 2015). RSP 2003+. yfinance + cache.

    python backtest/experiments/exp_breadth_deep.py
"""
import os
import pickle

import numpy as np
import pandas as pd

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
SPLIT = pd.Timestamp("2015-01-01")


def dl(tk):
    import yfinance as yf
    v = yf.download(tk, start="2003-01-01", progress=False, auto_adjust=True)["Close"]
    if isinstance(v, pd.DataFrame):
        v = v.iloc[:, 0]
    return v[~v.index.duplicated()].sort_index()


def ic_t(x, y):
    d = pd.DataFrame({"x": x, "y": y}).dropna(); n = len(d)
    if n < 30:
        return float("nan"), float("nan")
    ic = d["x"].corr(d["y"], method="spearman")
    return ic, (ic * np.sqrt(n - 2) / np.sqrt(1 - ic * ic) if abs(ic) < 1 else float("nan"))


def pic(x, y, z):
    d = pd.DataFrame({"x": x, "y": y, "z": z}).dropna()
    if len(d) < 30:
        return float("nan")
    r = d.rank()
    rx = r["x"] - np.polyval(np.polyfit(r["z"], r["x"], 1), r["z"])
    ry = r["y"] - np.polyval(np.polyfit(r["z"], r["y"], 1), r["z"])
    return np.corrcoef(rx, ry)[0, 1]


def pct_above_200(idx):
    """% of cache stocks above own 200SMA (survivorship-biased — cross-check only)."""
    try:
        px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    except Exception:
        return None
    cnt = pd.DataFrame(index=idx); above = pd.Series(0, index=idx); tot = pd.Series(0, index=idx)
    for t, s in px.items():
        if not isinstance(s, pd.Series) or len(s) < 260:
            continue
        s = s[~s.index.duplicated()].sort_index()
        a = (s > s.rolling(200).mean()).reindex(idx)
        above = above.add(a.fillna(False).astype(int), fill_value=0)
        tot = tot.add(a.notna().astype(int), fill_value=0)
    return (above / tot.replace(0, np.nan)) * 100


def run():
    spy, rsp, vix = dl("SPY"), dl("RSP"), dl("^VIX")
    idx = spy.index
    ratio = (rsp / spy).reindex(idx).ffill()
    narrow = -(ratio / ratio.rolling(126).mean() - 1)     # +ve = narrowing
    vixa = vix.reindex(idx).ffill()
    print(f"[breadth-deep] {idx[0].date()}→{idx[-1].date()}  RSP/SPY, n={len(idx)}")

    # (A) multi-timeframe forward IC (weekly)
    nw = narrow.resample("W-FRI").last(); pw = spy.resample("W-FRI").last(); vw = vixa.resample("W-FRI").last()
    print("\n=== (A) breadth 狹窄化 forward IC(週度,IC(t)｜partial|VIX)——睇邊個 timeframe 反映 ===")
    print(f"{'seg':<10}" + "".join(f"{h:>18}" for h in ["+1w", "+1m", "+3m", "+6m"]))
    for lbl, m in [("FULL", nw.index >= nw.index[0]), ("H1<2015", nw.index < SPLIT), ("H2 2015+", nw.index >= SPLIT)]:
        row = f"{lbl:<10}"
        for wk in [1, 4, 13, 26]:
            fr = pw.shift(-wk) / pw - 1
            ic, t = ic_t(nw[m], fr[m]); pi = pic(nw[m], fr[m], vw[m])
            row += f"{ic:>+6.3f}({t:>+3.1f})|{pi:>+4.2f}".rjust(18)
        print(row)
    print("  (narrow→ret 負 = 狹窄→未來差。睇 IC 喺邊個 horizon 最強 = 幾時反映)")

    # (B) both sides, multi-horizon
    near_high = spy >= 0.98 * spy.rolling(252).max()
    near_low = spy <= 1.06 * spy.rolling(252).min()
    narrowing = ratio < ratio.rolling(126).mean()
    fwd_min = spy[::-1].rolling(63, min_periods=10).min()[::-1] / spy - 1
    print("\n=== (B) 頂側 + 底側 × breadth,多 horizon(前望報酬%;n)===")
    print(f"{'情境':<28}{'+21d':>9}{'+63d':>9}{'63d最差':>10}{'n':>7}")
    scen = [("頂:近高+breadth窄(派發)", near_high & narrowing),
            ("頂:近高+breadth闊(健康)", near_high & ~narrowing),
            ("底:近低+breadth闊(thrust?)", near_low & ~narrowing),
            ("底:近低+breadth窄(仲弱)", near_low & narrowing)]
    f21 = spy.shift(-21) / spy - 1; f63 = spy.shift(-63) / spy - 1
    for name, q in scen:
        mm = q & f63.notna()
        if int(mm.sum()) < 20:
            print(f"  {name:<26} n<20"); continue
        print(f"  {name:<28}{f21[mm].mean()*100:>+8.2f}%{f63[mm].mean()*100:>+8.2f}%{fwd_min[mm].mean()*100:>+9.2f}%{int(mm.sum()):>7}")

    # (C) cross-check vs %-above-200SMA
    pa = pct_above_200(idx)
    if pa is not None:
        pa_narrow = -(pa / pa.rolling(126).mean() - 1)
        ic1, _ = ic_t(pa_narrow, f63); ic2, _ = ic_t(narrow, f63)
        print(f"\n=== (C) 現成指標 cross-check(%above200SMA,survivorship 偏)===")
        print(f"  corr(RSP/SPY-narrow, %above200-narrow) = {narrow.corr(pa_narrow):+.2f}(兩指標一唔一致)")
        print(f"  兩者對前望63d IC:RSP/SPY {ic2:+.3f} · %above200 {ic1:+.3f}")

    print("\nREAD: (A) IC 喺邊 horizon 最強 = 反映速度;兩半同號 = 穩。(B) 頂側「窄<闊」+ 底側「thrust 闊>窄」"
          "都成立 = breadth 兩側都有用。(C) 兩個 breadth 指標一致 = 唔係單一 proxy 假象。")


if __name__ == "__main__":
    run()
