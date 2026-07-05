"""GEX — does it add anything over VIX for a Phase-0 fragility gate? FREE test on the SqueezeMetrics
public CSV (SPX GEX + DIX daily 2011+, verified live). Research (FlashAlpha 8yr; Baltussen et al. 2021
JFE) says: GEX predicts VOLATILITY strongly RAW but ~0 INCREMENTAL once VIX/ATM-IV controlled, and
Karst already carries VIX/credit/RV. This confirms on our own data before deciding build/skip.

Tests (full + two halves):
  - corr(GEX, forward 21d realized vol)  RAW  vs  PARTIAL (control VIX)  vs  corr(VIX, fwdRV) benchmark
  - corr(GEX, forward return 5/21d)  (does GEX time DIRECTION, not just vol?)
  - GEX tercile -> forward RV / return   (regime read)
  - DIX (dark-pool, same CSV) as bonus
Mirror = Phase-0 gate: does low/negative GEX flag higher forward vol / worse returns, INCREMENTAL to VIX?

    python backtest/experiments/exp_gex_test.py
"""
import io
import urllib.request

import numpy as np
import pandas as pd

GEX_URL = "https://squeezemetrics.com/monitor/static/DIX.csv"
SPLIT = pd.Timestamp("2019-01-01")


def load_gex():
    raw = urllib.request.urlopen(GEX_URL, timeout=30).read().decode()
    df = pd.read_csv(io.StringIO(raw))
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


def load_vix():
    try:
        import yfinance as yf
        v = yf.download("^VIX", start="2010-06-01", progress=False, auto_adjust=False)["Close"]
        if isinstance(v, pd.DataFrame):
            v = v.iloc[:, 0]
        return v[~v.index.duplicated()].sort_index()
    except Exception as e:
        print(f"[gex] VIX fetch failed ({str(e)[:60]}) -> partial-corr skipped")
        return None


def pcorr(x, y, z):
    """partial spearman corr(x,y | z) via rank-residuals."""
    d = pd.DataFrame({"x": x, "y": y, "z": z}).dropna()
    if len(d) < 50:
        return float("nan")
    r = d.rank()
    rx = r["x"] - np.polyval(np.polyfit(r["z"], r["x"], 1), r["z"])
    ry = r["y"] - np.polyval(np.polyfit(r["z"], r["y"], 1), r["z"])
    return np.corrcoef(rx, ry)[0, 1]


def sc(x, y):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    return d["x"].corr(d["y"], method="spearman") if len(d) > 50 else float("nan")


def run():
    g = load_gex()
    print(f"[gex] SqueezeMetrics CSV: {len(g)} rows {g.index[0].date()}→{g.index[-1].date()} cols={list(g.columns)}")
    px = g["price"]; ret = px.pct_change()
    gex = g["gex"]; dix = g["dix"] if "dix" in g.columns else None
    fwd_rv = (ret.rolling(21).std() * np.sqrt(252)).shift(-21)       # forward 21d realized vol
    fwd_r5 = px.shift(-5) / px - 1
    fwd_r21 = px.shift(-21) / px - 1
    vix = load_vix()
    vixa = vix.reindex(g.index, method="ffill") if vix is not None else None

    segs = [("FULL", g.index >= g.index[0]),
            (f"H1 <{SPLIT.year}", g.index < SPLIT),
            (f"H2 {SPLIT.year}+", g.index >= SPLIT)]

    print("\n=== GEX vs forward 21d realized-vol(Spearman;partial 控 VIX)===")
    print(f"{'seg':<10}{'corr(GEX,RV)':>14}{'partial|VIX':>14}{'corr(VIX,RV)':>14}{'corr(GEX,ret21)':>16}")
    for lbl, m in segs:
        cg = sc(gex[m], fwd_rv[m])
        pg = pcorr(gex[m], fwd_rv[m], vixa[m]) if vixa is not None else float("nan")
        cv = sc(vixa[m], fwd_rv[m]) if vixa is not None else float("nan")
        cr = sc(gex[m], fwd_r21[m])
        print(f"{lbl:<10}{cg:>+14.3f}{pg:>+14.3f}{cv:>+14.3f}{cr:>+16.3f}")

    print("\n=== GEX 三分位 → 前望 21d RV% / 前望報酬%(FULL）===")
    q = pd.qcut(gex, 3, labels=["低GEX(脆弱)", "中", "高GEX(釘價)"])
    print(f"{'GEX tercile':<14}{'fwdRV%':>9}{'fwdRet5%':>10}{'fwdRet21%':>11}{'n':>7}")
    for t in ["低GEX(脆弱)", "中", "高GEX(釘價)"]:
        mm = (q == t)
        print(f"{t:<14}{fwd_rv[mm].mean()*100:>8.1f}%{fwd_r5[mm].mean()*100:>+9.2f}%{fwd_r21[mm].mean()*100:>+10.2f}%{int(mm.sum()):>7}")

    if dix is not None:
        print("\n=== DIX(暗池,同 CSV)三分位 → 前望報酬%（bonus）===")
        qd = pd.qcut(dix, 3, labels=["低DIX", "中", "高DIX(吸貨)"])
        for t in ["低DIX", "中", "高DIX(吸貨)"]:
            mm = (qd == t)
            print(f"{t:<12}{'fwdRet5':>8} {fwd_r5[mm].mean()*100:>+.2f}%  fwdRet21 {fwd_r21[mm].mean()*100:>+.2f}%  n={int(mm.sum())}")

    print("\nREAD: 若 corr(GEX,RV) 大但 partial|VIX ≈ 0 → GEX 對 VIX 冇增量(同研究一致,Karst 已有 VIX 就夠)。"
          "\n若 corr(GEX,ret) ≈ 0 → GEX 唔擇方向。低GEX tercile RV 明顯高 = 脆弱 regime 讀數(context 用)。")


if __name__ == "__main__":
    run()
