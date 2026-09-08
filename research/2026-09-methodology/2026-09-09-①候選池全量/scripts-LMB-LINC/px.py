import warnings, json
warnings.filterwarnings("ignore")
import yfinance as yf
import pandas as pd, numpy as np

TK = ["LMB","LINC","FIX","EME","IESC","APG","MTZ","UTI","APEI","PRDO","LOPE","ATGE","STRA","SPY"]
d = yf.download(TK, start="2024-09-01", end="2026-09-09", auto_adjust=True, progress=False, threads=True)
close = d["Close"]
vol = d["Volume"]

W0 = "2026-06-01"; W1 = "2026-09-08"
w = close.loc[W0:W1]
print("== window rows:", w.index[0].date(), "->", w.index[-1].date(), "n=", len(w))
spy = (w["SPY"].iloc[-1]/w["SPY"].iloc[0]-1)
print("== SPY window ret: %.4f" % spy)
print("\n== window returns (abs / rel SPY)")
for t in TK:
    s = w[t].dropna()
    if len(s) < 2: print(t, "no data"); continue
    r = s.iloc[-1]/s.iloc[0]-1
    print("%-6s abs=%+.4f rel=%+.4f last=%.2f first=%.2f" % (t, r, r-spy, s.iloc[-1], s.iloc[0]))

for t in ["LMB","LINC"]:
    print("\n===== %s daily moves in window (|move| >= 4%%) =====" % t)
    s = close[t].loc["2026-05-20":W1].dropna()
    ret = s.pct_change()
    for dt, v in ret.items():
        if abs(v) >= 0.04 and dt >= pd.Timestamp(W0):
            print("  %s  %+.2f%%  close=%.2f" % (dt.date(), v*100, s.loc[dt]))
    full = close[t].dropna()
    ma200 = full.rolling(200).mean()
    px = full.loc[:W1].iloc[-1]; m = ma200.loc[:W1].iloc[-1]
    slope40 = (ma200.loc[:W1].iloc[-1]/ma200.loc[:W1].iloc[-41]-1)
    print("  price=%.2f ma200=%.2f  px/ma200-1=%+.2f%%  ma200 40d slope=%+.2f%%" % (px, m, (px/m-1)*100, slope40*100))
    y1 = full.loc["2025-09-08":W1]
    print("  52wk high=%.2f (%s)  low=%.2f (%s)  maxDD from running peak=%.2f%%" % (
        y1.max(), y1.idxmax().date(), y1.min(), y1.idxmin().date(),
        (y1/y1.cummax()-1).min()*100))
    print("  52wk trough-to-date from high: %.2f%%" % ((y1.iloc[-1]/y1.max()-1)*100))
    dv = (close[t]*vol[t]).loc[:W1].dropna().iloc[-60:]
    print("  60d median dollar volume = $%.0f  mean=$%.0f" % (dv.median(), dv.mean()))
    # 2y max drawdown
    f2 = full.loc[:W1]
    print("  2y maxDD=%.2f%%" % ((f2/f2.cummax()-1).min()*100))
