"""DIX done PROPERLY — forward IC, weekly (non-overlapping), smoothed, as a TREND indicator.
(User: don't collapse on the 1-day-63d critique — DIX is a slow flow gauge; smooth it, sample weekly,
measure FORWARD IC, the same falsifiable metric as the whole system.)

Signals (daily then sampled at week-end, W-FRI):
  DIX level · DIX 5d-avg (smoothed) · DIX 10d-avg · DIX 5d-change (trend/momentum of accumulation)
Forward SPX returns from each week: +1w (5d, NON-OVERLAPPING) · +2w · +4w (~1m).
Forward IC = time-series Spearman(signal_week, forward_return) + t-stat (n = independent weeks).
+ partial vs VIX (does DIX add over the fear axis). Two-halves (split 2018). SqueezeMetrics free CSV.

    python backtest/experiments/exp_dix_ic.py
"""
import io
import urllib.request

import numpy as np
import pandas as pd

SPLIT = pd.Timestamp("2018-06-01")


def ic_t(x, y):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(d)
    if n < 30:
        return float("nan"), float("nan"), n
    ic = d["x"].corr(d["y"], method="spearman")
    t = ic * np.sqrt(n - 2) / np.sqrt(1 - ic * ic) if abs(ic) < 1 else float("nan")
    return ic, t, n


def pic(x, y, z):
    d = pd.DataFrame({"x": x, "y": y, "z": z}).dropna()
    if len(d) < 30:
        return float("nan")
    r = d.rank()
    rx = r["x"] - np.polyval(np.polyfit(r["z"], r["x"], 1), r["z"])
    ry = r["y"] - np.polyval(np.polyfit(r["z"], r["y"], 1), r["z"])
    return np.corrcoef(rx, ry)[0, 1]


def run():
    raw = urllib.request.urlopen("https://squeezemetrics.com/monitor/static/DIX.csv", timeout=30).read().decode()
    g = pd.read_csv(io.StringIO(raw)); g["date"] = pd.to_datetime(g["date"]); g = g.set_index("date").sort_index()
    dix, px = g["dix"], g["price"]
    import yfinance as yf
    vix = yf.download("^VIX", start="2011-01-01", progress=False, auto_adjust=True)["Close"]
    if isinstance(vix, pd.DataFrame):
        vix = vix.iloc[:, 0]

    sigs = pd.DataFrame({
        "DIX level": dix,
        "DIX 5d-avg": dix.rolling(5).mean(),
        "DIX 10d-avg": dix.rolling(10).mean(),
        "DIX 5d-chg": dix - dix.shift(5),
    })
    W = "W-FRI"
    sw = sigs.resample(W).last()
    pw = px.resample(W).last()
    vw = vix.reindex(px.index).ffill().resample(W).last()
    fwd = {"+1w": pw.shift(-1) / pw - 1, "+2w": pw.shift(-2) / pw - 1, "+4w": pw.shift(-4) / pw - 1}
    print(f"[dix-ic] 週度 {sw.index[0].date()}→{sw.index[-1].date()}, {len(sw)} 週")

    for seg, m in [("FULL", sw.index >= sw.index[0]), ("H1<2018", sw.index < SPLIT), ("H2 2018+", sw.index >= SPLIT)]:
        print(f"\n=== {seg} —— forward IC(t)｜partial|VIX ===")
        print(f"{'signal':<12}" + "".join(f"{h:>20}" for h in fwd))
        for s in sigs.columns:
            row = f"{s:<12}"
            for h, fr in fwd.items():
                ic, t, n = ic_t(sw[s][m], fr[m])
                pi = pic(sw[s][m], fr[m], vw[m])
                row += f"{ic:>+6.3f}({t:>+4.1f})|{pi:>+5.2f}".rjust(20)
            print(row)
    print("\n(對照)VIX 自己 forward IC:")
    for h, fr in fwd.items():
        ic, t, n = ic_t(vw, fr)
        print(f"  VIX {h}: IC {ic:+.3f} (t {t:+.1f})")

    print("\nREAD: forward IC ≥ 0.05 + t 顯著 + 兩半同號 = DIX 真有預測力(值得建 Phase 2 flow);"
          "\npartial|VIX 仍 >0 = 對恐懼軸有增量。smoothed/趨勢(5d-avg/chg)應該勝過 raw level。週度=非重疊(+1w)。")


if __name__ == "__main__":
    run()
