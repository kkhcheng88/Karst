"""BREADTH with REAL advance line + timeframe-match theory test (user's ask).
Build breadth from the individual-stock cache (NOT the RSP/SPY proxy):
   ADV  = % of stocks UP today (same-day advance line / 漲跌線)
   A50  = % of stocks above own 50-day MA (medium-term breadth)
   A200 = % above 200-day MA (long-term breadth)
Test the timeframe-match theory:
  (A) FORWARD IC of breadth at 1w/2w/4w/8w, weekly-sampled + partial|VIX + two-halves.
      -> if the theory is solid, WEEKLY breadth should predict WEEKLY-forward (remain effective).
  (B) DIRECTIONAL-FORCE confirmation (weekly): this-week SPY up/down × weekly breadth broad/narrow
      -> does breadth confirm the weekly move (broad=continue, narrow=revert)?
  (C) same, DAILY (same-day advance line × today's move) for the timeframe comparison.
⚠ Cache = survivors -> breadth LEVEL biased high; the RELATIVE/divergence signal is what we read.

    python backtest/experiments/exp_breadth_real.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
SPLIT = pd.Timestamp("2016-01-01")


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
    adv = (R > 0).sum(axis=1) / R.notna().sum(axis=1) * 100
    a50 = A50.sum(axis=1) / A50.notna().sum(axis=1) * 100
    a200 = A200.sum(axis=1) / A200.notna().sum(axis=1) * 100
    print(f"[breadth-real] {R.shape[1]} stocks (survivorship-biased)")
    return adv, a50, a200


def run():
    adv, a50, a200 = build_breadth()
    spy, vix = dl("SPY"), dl("^VIX")
    idx = spy.index
    adv = adv.reindex(idx).ffill(); a50 = a50.reindex(idx).ffill(); a200 = a200.reindex(idx).ffill()
    vixa = vix.reindex(idx).ffill()

    # (A) forward IC weekly
    pw = spy.resample("W-FRI").last(); vw = vixa.resample("W-FRI").last()
    print("\n=== (A) breadth LEVEL forward IC(週度,IC(t)｜partial|VIX)——你嘅 timeframe 理論 ===")
    for name, ser in [("同日漲跌線 %up", adv), ("%above50SMA", a50), ("%above200SMA", a200)]:
        bw = ser.resample("W-FRI").last()
        print(f"\n  {name}")
        for lbl, m in [("FULL", bw.index >= bw.index[0]), ("H1<2016", bw.index < SPLIT), ("H2 2016+", bw.index >= SPLIT)]:
            row = f"    {lbl:<9}"
            for wk in [1, 2, 4, 8]:
                fr = pw.shift(-wk) / pw - 1
                ic, t = ic_t(bw[m], fr[m]); p = pic(bw[m], fr[m], vw[m])
                row += f"+{wk}w {ic:>+5.2f}({t:>+3.1f})|{p:>+4.2f}".rjust(20)
            print(row)
    print("  (breadth 高→未來高 = 正 IC。睇邊個 horizon 最強 + 兩半同號)")

    # (B) directional-force confirmation
    def force(bday, prefix, up, dn, fwds, note):
        print(f"\n=== ({prefix}) 方向力確認:{note} —— 前望%(勝%)/n ===")
        broad = bday > bday.rolling(252).median()   # breadth 相對自己中位:闊/窄
        for mv_lbl, mv in [("升", up), ("跌", dn)]:
            for br_lbl, br in [("闊", broad), ("窄", ~broad)]:
                m = mv & br
                for fl, fr in fwds.items():
                    mm = m & fr.notna(); n = int(mm.sum())
                    s = f"{fr[mm].mean()*100:>+5.2f}%({(fr[mm]>0).mean()*100:>3.0f})n{n}" if n >= 20 else "n<20"
                    print(f"  {mv_lbl}+breadth{br_lbl:<2} {fl}: {s}")

    # weekly
    wr = pw.pct_change()
    aw = a50.resample("W-FRI").last()
    f1 = pw.shift(-1) / pw - 1; f2 = pw.shift(-2) / pw - 1
    force(aw, "B 週度", wr > 0, wr < 0, {"+1w": f1, "+2w": f2}, "本週SPY升/跌 × 週breadth(%above50)闊/窄")
    # daily
    dr = spy.pct_change()
    fd5 = spy.shift(-5) / spy - 1
    force(adv, "C 日度", dr > 0, dr < 0, {"+5d": fd5}, "今日SPY升/跌 × 同日漲跌線(%up)闊/窄")

    print("\nREAD: (A) 若週度 breadth 對 +1~4w 有正 IC 且過 0.05、兩半同號 = timeframe 理論成立(週配週有效)。"
          "\n(B/C) 若『升+闊 續升 / 升+窄 轉弱』且『跌+闊 續跌 / 跌+窄 轉升』= breadth 確認方向力,兩 timeframe 都應成立。")


if __name__ == "__main__":
    run()
