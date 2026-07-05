"""F&G speculative-sleeve STRATEGY — proper capital-efficiency backtest (not an event study).

Better proxy than ETFs (SPHB/SPLV/IWM): build the speculative & safe baskets from INDIVIDUAL
stocks sorted on Baker-Wurgler characteristics (size × volatility). SPEC = small-cap (bottom
market-cap tercile) AND high-vol (top realized-vol tercile); SAFE = large-cap AND low-vol.
Equal-weight, monthly rebalance, from the cached universe (px + market cap from the insider runs).

Then a REAL strategy with entry/exit and the standard capital-efficiency measure:
  Rule: hold the SPEC basket when F&G < EXIT (not greedy); go to cash when F&G >= EXIT (greed).
  Metrics: Exposure · Deployed CAGR (months held) · Conditional Sharpe · Total CAGR · MaxDD,
  vs B&H SPEC / B&H SAFE.

Caveat: cached universe = names defeatbeta can price → SURVIVORSHIP (delisted losers drop out) →
spec returns INFLATED; monthly, ~10bps cost on F&G-timing turnover. Honest read = the RELATIVE
picture (timed vs B&H spec) + direction, not the absolute magnitude.

    python backtest/experiments/exp_fg_spec_strategy.py
"""
import io
import os
import pickle
import sys
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
COST = 0.001   # 10bps on F&G-timing turnover


def load_fg():
    url = "https://raw.githubusercontent.com/whit3rabbit/fear-greed-data/main/fear-greed.csv"
    df = pd.read_csv(io.StringIO(urllib.request.urlopen(url, timeout=30).read().decode()))
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")["Fear Greed"].sort_index()


def _series(cache, key):
    v = cache.get(key)
    if v is None:
        return None
    s = (v["close"] if hasattr(v, "columns") and "close" in getattr(v, "columns", []) else v)
    if not isinstance(s, pd.Series):
        return None
    return s[~s.index.duplicated()].sort_index()


def run():
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    mc = pickle.load(open(os.path.join(_DATA, "mktcap_defeatbeta.pkl"), "rb"))
    tickers = [t for t in px if _series(px, t) is not None and mc.get(t) is not None][:8000]
    months = pd.date_range("2011-01-31", "2026-06-30", freq="ME")
    close, vol, mcap = {}, {}, {}
    for t in tickers:
        s = _series(px, t)
        m = mc.get(t)
        if s is None or m is None or len(s) < 200:
            continue
        m = m[~m.index.duplicated()].sort_index()
        close[t] = s.reindex(months, method="ffill")
        vol[t] = (s.pct_change().rolling(63).std() * np.sqrt(252)).reindex(months, method="ffill")
        mcap[t] = m.reindex(months, method="ffill")
    close = pd.DataFrame(close); vol = pd.DataFrame(vol); mcap = pd.DataFrame(mcap)
    fwd = close.shift(-1) / close - 1
    print(f"[spec-strat] universe {close.shape[1]} tickers, {len(months)} months")

    spec_r, safe_r, dts = [], [], []
    for m in months[:-1]:
        c, v, mm, f = close.loc[m], vol.loc[m], mcap.loc[m], fwd.loc[m]
        elig = c.notna() & v.notna() & mm.notna() & f.notna() & (c > 1)
        if elig.sum() < 60:
            continue
        vv, cc, ff = v[elig], mm[elig], f[elig].clip(-0.6, 2.0)   # clip extreme (partial outlier guard)
        clo, chi = cc.quantile([1/3, 2/3]); vlo, vhi = vv.quantile([1/3, 2/3])
        spec = ff[(cc <= clo) & (vv >= vhi)]
        safe = ff[(cc >= chi) & (vv <= vlo)]
        if len(spec) < 5 or len(safe) < 5:
            continue
        spec_r.append(spec.mean()); safe_r.append(safe.mean()); dts.append(m)
    spec = pd.Series(spec_r, index=dts); safe = pd.Series(safe_r, index=dts)
    fg = load_fg().reindex(dts, method="ffill")
    print(f"[spec-strat] {len(spec)} months with baskets ({dts[0].date()}→{dts[-1].date()})\n")

    def metrics(ret):
        n = len(ret); eq = (1 + ret).cumprod()
        cagr = eq.iloc[-1] ** (12 / n) - 1
        sh = ret.mean() / ret.std() * np.sqrt(12) if ret.std() else 0
        mdd = (eq / eq.cummax() - 1).min()
        return cagr, sh, mdd

    print("=== 基準(B&H,月度)===")
    for lbl, r in [("SPEC 投機籃(小+高波)", spec), ("SAFE 安全籃(大+低波)", safe)]:
        c, s, d = metrics(r)
        print(f"  {lbl:<20} CAGR {c*100:>+6.1f}% | Sharpe {s:>4.2f} | MaxDD {d*100:>5.0f}%")
    print(f"  SPEC−SAFE 全期價差(月均) {(spec-safe).mean()*100:>+.2f}%  "
          f"| 恐懼<25月 {(spec-safe)[fg < 25].mean()*100:>+.2f}% | 貪婪>75月 {(spec-safe)[fg > 75].mean()*100:>+.2f}%")

    print("\n=== F&G-timed SPEC sleeve(持 SPEC when F&G<EXIT,否則現金)——資本效率 ===")
    print(f"{'EXIT門檻':<10}{'曝險':>6}{'部署CAGR':>10}{'條件Sharpe':>11}{'總CAGR':>9}{'MaxDD':>8}")
    for exit_ in [55, 70, 80]:
        pos = (fg < exit_).astype(float)
        pos_l = pos.shift(1).fillna(0)
        strat = pos_l * spec - COST * pos_l.diff().abs().fillna(0)
        exp = pos_l.mean()
        inm = pos_l > 0
        dep_cagr = (1 + spec[inm]).prod() ** (12 / max(inm.sum(), 1)) - 1 if inm.sum() > 6 else float("nan")
        csh = spec[inm].mean() / spec[inm].std() * np.sqrt(12) if inm.sum() > 6 and spec[inm].std() else float("nan")
        tc, _, tmdd = metrics(strat)
        print(f"F&G<{exit_:<7}{exp*100:>5.0f}%{dep_cagr*100:>9.1f}%{csh:>11.2f}{tc*100:>8.1f}%{tmdd*100:>7.0f}%")
    print("\nREAD: 若 F&G-timed 部署CAGR / 條件Sharpe 明顯 > B&H SPEC -> 用 F&G 揀時機持投機股係資本"
          "有效(擇時把資金放喺 spec 抵買嗰啲月)。SURVIVORSHIP 令絕對數偏高,睇相對(timed vs B&H spec)。")


if __name__ == "__main__":
    run()
