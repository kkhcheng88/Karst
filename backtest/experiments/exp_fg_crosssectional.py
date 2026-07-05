"""F&G CROSS-SECTIONAL — the dimension we missed (Baker-Wurgler 2006/2007).

We only tested F&G at market level (SPY fwd). B-W: sentiment hits HARD-TO-ARBITRAGE stocks
(small / young / high-vol / speculative) hardest — high sentiment -> those underperform;
low sentiment -> they outperform. Test with ETF proxies for the speculative-vs-safe spread:
  size:  IWM (small) - SPY (large)
  spec:  SPHB (S&P High Beta) - SPLV (S&P Low Vol)   <- cleanest "hard-to-arbitrage" proxy
Does high F&G predict the spec-minus-safe spread going NEGATIVE (spec underperforms)? If yes,
F&G is a far sharper DE-RISK signal for the speculative sleeve than the market-level read.

CNN F&G (github whit3rabbit), 2011+ overlap (SPHB/SPLV launched 2011). Forward 21/63d.

    python backtest/experiments/exp_fg_crosssectional.py
"""
import io
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as D  # noqa: E402


def load_fg():
    url = "https://raw.githubusercontent.com/whit3rabbit/fear-greed-data/main/fear-greed.csv"
    df = pd.read_csv(io.StringIO(urllib.request.urlopen(url, timeout=30).read().decode()))
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")["Fear Greed"].sort_index()


def px(sym):
    try:
        return D.load(sym, min_rows=200)["close"]
    except Exception:
        return None


def run():
    fg = load_fg()
    syms = {s: px(s) for s in ["SPY", "IWM", "SPHB", "SPLV", "QQQ"]}
    idx = syms["SPY"].index
    fg = fg.reindex(idx).ffill(limit=5)
    for s in syms:
        syms[s] = syms[s].reindex(idx)

    def fwd(sym, h):
        s = syms[sym]
        return s.shift(-h) / s - 1

    ZONES = [("恐懼<25", 0, 25), ("中25-75", 25, 75), ("貪婪>75", 75, 101), ("極端>80", 80, 101)]
    SPREADS = [("小-大 (IWM-SPY)", "IWM", "SPY"), ("高beta-低波 (SPHB-SPLV)", "SPHB", "SPLV")]

    print(f"樣本 {idx.min().date()}→{idx.max().date()} (F&G overlap)\n")
    print("=== PART 1 — F&G 區 → 未來投機價差(spec − safe)平均% / t ===")
    for name, spec, safe in SPREADS:
        print(f"\n  {name}:")
        for h in [21, 63]:
            sp = fwd(spec, h) - fwd(safe, h)
            row = f"    {h}日 "
            for zn, lo, hi in ZONES:
                m = (fg >= lo) & (fg < hi)
                x = sp[m].dropna()
                if len(x) < 20:
                    row += f"{zn}: n<20  "
                    continue
                t = x.mean() / (x.std() / np.sqrt(len(x)))
                row += f"{zn} {x.mean()*100:>+4.1f}%(t{t:>+3.1f})  "
            print(row)

    print("\n=== PART 2 — F&G>80 之後未來 63日:市場 vs 投機 vs 安全(de-risk 邊個勁)===")
    for lbl, sym in [("SPY 市場", "SPY"), ("QQQ", "QQQ"), ("SPHB 高beta(投機)", "SPHB"),
                     ("IWM 小型", "IWM"), ("SPLV 低波動(安全)", "SPLV")]:
        f80 = fwd(sym, 63)[fg > 80].dropna()
        base = fwd(sym, 63).dropna()
        print(f"  {lbl:<18} F&G>80: {f80.mean()*100:>+5.1f}% (n={len(f80)})  |  全樣本 {base.mean()*100:>+5.1f}%")

    print("\nREAD: 若『貪婪』區價差顯著負(spec 跑輸)而『恐懼』區正 -> B-W cross-sectional 成立,"
          " F&G 係投機股 de-risk 嘅利器(比大盤層強)。")


if __name__ == "__main__":
    run()
