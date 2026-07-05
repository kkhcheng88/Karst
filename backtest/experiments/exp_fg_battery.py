"""Complete Fear&Greed battery — full grids, entry {5,10}. Holds CNN F&G to the RSI-2
standard and asks: does F&G add anything over VIX? Every combination shown (no summary).

  PART 1  F&G-zone x category decision matrix, entry {5,10} x exit {70,80,90,95}
  PART 2  head-to-head: F&G-fear vs VIX-fear predicting the bounce (pooled), entry {5,10}
  PART 3  two-halves (2016-20 vs 2021-26), F&G fear zone, entry {5,10}
  PART 4  greed de-risk: SPY fwd-63d after F&G>80 vs VIX<13 vs baseline (market-level)

RSI-2 dip entries per instrument, classified by F&G at entry, 4 categories, 2016+,
look-ahead-safe, 2bp/trade, raw close. F&G low=fear (inverse of VIX).

    python backtest/experiments/exp_fg_battery.py
"""
import io
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as D  # noqa: E402
from signals import rsi  # noqa: E402

ENTRIES = [5, 10]
EXITS = [70, 80, 90, 95]
RT_COST = 0.0002
START = "2016-01-01"
SPLIT = "2021-01-01"
FG_ZONES = [("貪婪>50", 50, 101), ("中性25-50", 25, 50), ("恐懼<25", 0, 25)]

CATS = {
    "大盤指數": ["SPY", "QQQ", "SPMO"],
    "細價股": ["IWM", "IJR"],
    "板塊ETF": ["XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLB", "XLY", "XLC", "XLRE"],
    "Mag7": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"],
}


def w(px):
    return px[px.index >= START] if px is not None else None


def load_fg():
    url = "https://raw.githubusercontent.com/whit3rabbit/fear-greed-data/main/fear-greed.csv"
    df = pd.read_csv(io.StringIO(urllib.request.urlopen(url, timeout=30).read().decode()))
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")["Fear Greed"].sort_index()


def trades(px, entry, exit_, fg, vix):
    r2 = rsi(px, 2).values
    n = len(px)
    pos = np.zeros(n)
    inp = False
    for i in range(n):
        if not inp and r2[i] < entry:
            inp = True
        elif inp and r2[i] > exit_:
            inp = False
        pos[i] = 1.0 if inp else 0.0
    pos = pd.Series(pos, index=px.index).shift(1).fillna(0).values
    p, f, v, idx = px.values, fg.values, vix.values, px.index
    out, e = [], None
    for i in range(1, n):
        if pos[i] > 0 and pos[i - 1] == 0:
            e = i
        elif pos[i] == 0 and pos[i - 1] > 0 and e is not None:
            out.append((p[i] / p[e] - 1 - RT_COST, i - e, f[e], v[e], idx[e]))
            e = None
    return out


def st(tr):
    if len(tr) < 10:
        return None
    r = np.array([a[0] for a in tr])
    h = np.array([a[1] for a in tr])
    return f"{r.mean()*100:>+4.1f}/{(r > 0).mean()*100:>3.0f}/{h.mean():>2.0f}[{len(tr):>3}]"


def run():
    fg_all = load_fg()
    vix_all = w(D.load("^VIX", min_rows=260)["close"])
    per = {}         # (entry, cat, zone, exit) -> trades
    allt = {}        # (entry, exit) -> trades (pooled, with fg/vix/date)
    for cat, tks in CATS.items():
        for t in tks:
            try:
                px = w(D.load(t, min_rows=260)["close"])
            except Exception:
                px = None
            if px is None or len(px) < 200:
                continue
            fg = fg_all.reindex(px.index).ffill(limit=5)
            vx = vix_all.reindex(px.index).ffill()
            for en in ENTRIES:
                for x in EXITS:
                    for tr in trades(px, en, x, fg, vx):
                        if tr[2] != tr[2] or tr[3] != tr[3]:
                            continue
                        allt.setdefault((en, x), []).append(tr)
                        for zn, lo, hi in FG_ZONES:
                            if lo <= tr[2] < hi:
                                per.setdefault((en, cat, zn, x), []).append(tr)
                                break

    hdr = "".join(f"{'>'+str(x):>16}" for x in EXITS)
    for en in ENTRIES:
        print(f"\n############## PART 1 — F&G-zone × 股種 (entry RSI2<{en}; per-trade%/勝%/持d[n]) ##############")
        for cat in CATS:
            print(f"\n=== {cat} ===\n{'F&G區':<12}{hdr}")
            for zn, _, _ in FG_ZONES:
                row = f"{zn:<12}"
                for x in EXITS:
                    s = st(per.get((en, cat, zn, x), []))
                    row += (s.rjust(16) if s else f"{'n<10':>16}")
                print(row)

    for en in ENTRIES:
        print(f"\n############## PART 2 — Head-to-head F&G vs VIX (entry<{en}, pooled) ##############")
        print(f"{'恐懼定義':<16}{hdr}")
        defs = [("F&G<25", lambda tr: tr[2] < 25), ("F&G<15", lambda tr: tr[2] < 15),
                ("VIX>28", lambda tr: tr[3] > 28), ("VIX>40", lambda tr: tr[3] > 40)]
        for nm, fn in defs:
            row = f"{nm:<16}"
            for x in EXITS:
                sub = [tr for tr in allt.get((en, x), []) if fn(tr)]
                row += (st(sub).rjust(16) if st(sub) else f"{'n<10':>16}")
            print(row)

    for en in ENTRIES:
        print(f"\n############## PART 3 — 前半/後半 (entry<{en}, F&G恐懼<25 zone, pooled) ##############")
        print(f"{'期間':<12}{hdr}")
        for lbl, cut in [("前2016-20", True), ("後2021-26", False)]:
            row = f"{lbl:<12}"
            for x in EXITS:
                sub = [tr for tr in allt.get((en, x), []) if tr[2] < 25
                       and ((tr[4] < pd.Timestamp(SPLIT)) == cut)]
                row += (st(sub).rjust(16) if st(sub) else f"{'n<10':>16}")
            print(row)

    print(f"\n############## PART 4 — 貪婪 de-risk:SPY 未來63日 (2016+, market-level) ##############")
    spy = w(D.load("SPY")["close"])
    fg = fg_all.reindex(spy.index).ffill(limit=5)
    vx = vix_all.reindex(spy.index).ffill()
    fwd = spy.shift(-63) / spy - 1
    for nm, m in [("全樣本", pd.Series(True, index=spy.index)), ("F&G>80", fg > 80),
                  ("F&G>75", fg > 75), ("F&G>70", fg > 70), ("VIX<13", vx < 13), ("VIX<15", vx < 15)]:
        r = fwd[m].dropna()
        print(f"  {nm:<12} 均 {r.mean()*100:>+5.1f}% 勝 {(r > 0).mean()*100:>3.0f}% n={len(r)}")


if __name__ == "__main__":
    run()
