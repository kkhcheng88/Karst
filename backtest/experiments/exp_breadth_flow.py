"""PHASE 2 flow — market-level: (1) BREADTH (RSP/SPY equal-vs-cap weight; falling = breadth narrowing,
few mega-caps carrying) + breadth DIVERGENCE (SPY near high but breadth narrowing = classic top warning);
(2) DIX (dark-pool, SqueezeMetrics free CSV). Evidence-first: does each add INCREMENTAL to VIX (the
validated fear axis) before we wire it? (Same test as credit/GEX — many flow signals turn out redundant.)

Breadth = RSP/SPY (clean, no survivorship, unlike %-above-200SMA from the cache). RSP 2003+.
Forward SPY 21/63d return + 63d worst-drawdown. Two-halves (split 2015). partial corr | VIX.

    python backtest/experiments/exp_breadth_flow.py
"""
import io
import urllib.request

import numpy as np
import pandas as pd

SPLIT = pd.Timestamp("2015-01-01")


def dl(tk):
    import yfinance as yf
    v = yf.download(tk, start="2003-01-01", progress=False, auto_adjust=True)["Close"]
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
    spy, rsp, vix = dl("SPY"), dl("RSP"), dl("^VIX")
    idx = spy.index
    ratio = (rsp / spy).reindex(idx).ffill()
    narrow = -(ratio / ratio.rolling(126).mean() - 1)      # +ve = breadth narrowing (RSP underperforming)
    vixa = vix.reindex(idx).ffill()
    fwd21 = spy.shift(-21) / spy - 1
    fwd63 = spy.shift(-63) / spy - 1
    fwd_min = spy[::-1].rolling(63, min_periods=10).min()[::-1] / spy - 1
    print(f"[breadth] {idx[0].date()}→{idx[-1].date()}  RSP/SPY + VIX, n={len(idx)}")

    print("\n=== (1) breadth 狹窄化 → 前望(Spearman;partial 控 VIX)===")
    print(f"{'seg':<11}{'narrow→ret63':>14}{'partial|VIX':>13}{'narrow→最差dd':>15}{'partial|VIX':>13}")
    for lbl, m in [("FULL", idx >= idx[0]), ("H1<2015", idx < SPLIT), ("H2 2015+", idx >= SPLIT)]:
        print(f"{lbl:<11}{sc(narrow[m], fwd63[m]):>+14.3f}{pcorr(narrow[m], fwd63[m], vixa[m]):>+13.3f}"
              f"{sc(narrow[m], fwd_min[m]):>+15.3f}{pcorr(narrow[m], fwd_min[m], vixa[m]):>+13.3f}")
    print("  (narrow→ret 負 = 狹窄→未來股市差;narrow→dd 負 = 狹窄→未來回撤更深。partial≈0 = 對 VIX 無增量)")

    print("\n=== (2) breadth 背離:SPY 近高位(≤2% 距 252d 高)× breadth 闊/窄 → 前望63d / 最差dd ===")
    near_high = spy >= 0.98 * spy.rolling(252).max()
    narrowing = ratio < ratio.rolling(126).mean()
    quads = [("近高+breadth窄(背離/見頂?)", near_high & narrowing),
             ("近高+breadth闊(健康)", near_high & ~narrowing),
             ("非近高", ~near_high)]
    for seg, sm in [("FULL 2004+", idx >= idx[0]), ("H1<2015", idx < SPLIT), ("H2 2015+", idx >= SPLIT)]:
        print(f"\n  --- {seg} ---")
        for name, q in quads:
            mm = q & sm & fwd63.notna()
            if int(mm.sum()) < 20:
                print(f"  {name:<26} n<20"); continue
            print(f"  {name:<26}{fwd63[mm].mean()*100:>+8.2f}%{fwd_min[mm].mean()*100:>+9.2f}%{int(mm.sum()):>7}")

    # (3) DIX
    try:
        raw = urllib.request.urlopen("https://squeezemetrics.com/monitor/static/DIX.csv", timeout=30).read().decode()
        g = pd.read_csv(io.StringIO(raw)); g["date"] = pd.to_datetime(g["date"]); g = g.set_index("date").sort_index()
        dix = g["dix"]; px = g["price"]
        dr21 = px.shift(-21) / px - 1; dr63 = px.shift(-63) / px - 1
        vixd = vix.reindex(g.index).ffill()
        print("\n=== (3) DIX(暗池)→ 前望 SPX(partial 控 VIX)===")
        print(f"  corr(DIX,ret21) {sc(dix, dr21):+.3f}  partial|VIX {pcorr(dix, dr21, vixd):+.3f}  |  ret63 {sc(dix, dr63):+.3f}  partial|VIX {pcorr(dix, dr63, vixd):+.3f}")
        qd = pd.qcut(dix, 3, labels=["低", "中", "高(吸貨)"])
        for t in ["低", "中", "高(吸貨)"]:
            mm = (qd == t)
            print(f"    DIX {t:<7} 前望21d {dr21[mm].mean()*100:>+.2f}%  63d {dr63[mm].mean()*100:>+.2f}%  n={int(mm.sum())}")
    except Exception as e:
        print(f"\n[DIX] skip ({str(e)[:50]})")

    print("\nREAD: breadth——若「近高+窄」前望差過「近高+闊」(尤其 dd 更深)= 背離見頂訊號成立;若 partial|VIX"
          " 明顯 = 對 VIX 有增量值得建。DIX——partial|VIX 大 = 暗池 flow 有獨立訊號。全部 ≈0 = 冗餘(似 credit/GEX)。")


if __name__ == "__main__":
    run()
