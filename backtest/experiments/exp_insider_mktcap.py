"""Insider 21d edge by MARKET CAP (price is misleading — a $3 stock can be large, a $500 stock
small). Uses defeatbeta market_capitalization() (daily close × latest quarterly shares) for a
point-in-time market cap at each event date. Reuses exp_insider_validate events + price cache;
market-cap series cached to mktcap_defeatbeta.pkl.

Question: the price test said the edge lives in <$5 penny names. Does a PROPER size measure
(market cap) confirm the edge is a micro/small-cap illusion, and is there ANY edge in tradeable
mid/large caps?

    python backtest/experiments/exp_insider_mktcap.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_insider_validate as IV  # noqa: E402

_MCAP = {}
_CACHE = os.path.join(IV._DATA, "mktcap_defeatbeta.pkl")


def _mcap_series(tk):
    try:
        from defeatbeta_api.data.ticker import Ticker
        d = Ticker(tk).market_capitalization()
        d = d.data if hasattr(d, "data") else d
        s = pd.Series(pd.to_numeric(d["market_capitalization"], errors="coerce").values,
                      index=pd.to_datetime(d["report_date"], errors="coerce")).dropna().sort_index()
        return s[~s.index.duplicated()] if len(s) > 10 else None
    except Exception:
        return None


def _batch_mcap(tickers):
    cache = {}
    if os.path.exists(_CACHE):
        try:
            cache = pickle.load(open(_CACHE, "rb"))
        except Exception:
            cache = {}
    need = [t for t in sorted(set(tickers)) if cache.get(t) is None]
    for i, t in enumerate(need):
        cache[t] = _mcap_series(t)
        if i % 200 == 199:
            pickle.dump(cache, open(_CACHE, "wb"))
    pickle.dump(cache, open(_CACHE, "wb"))
    for t in set(tickers):
        _MCAP[t] = cache.get(t)
    print(f"[mktcap] got market cap for {sum(_MCAP.get(t) is not None for t in set(tickers))}/"
          f"{len(set(tickers))} tickers")


def stat(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 15:
        return f"{len(x):>5}   n<15"
    t = x.mean() / (x.std() / np.sqrt(len(x)))
    return f"{len(x):>5}{x.mean()*100:>+8.2f}{np.median(x)*100:>+8.2f}{(x > 0).mean()*100:>6.0f}%{t:>7.2f}"


def run():
    ev = IV.build_events(IV._quarters("2022q1", "2025q2"))
    IV._batch_prices(ev["ticker"].tolist())
    _batch_mcap(ev["ticker"].tolist())
    spy = IV._px("SPY")
    rows = []
    for _, e in ev.iterrows():
        s = IV._px(e["ticker"])
        mc = _MCAP.get(e["ticker"])
        if s is None:
            continue
        x21, b21 = IV._fwd(s, e["date"], 21), IV._fwd(spy, e["date"], 21)
        if x21 is None or b21 is None:
            continue
        m = mc.asof(pd.Timestamp(e["date"])) if mc is not None else np.nan
        pos = s.index.searchsorted(pd.Timestamp(e["date"]))
        price = float(s.iloc[pos]) if pos < len(s) else np.nan
        rows.append(dict(x=x21 - b21, mcap=m, price=price))
    df = pd.DataFrame(rows).dropna(subset=["x"])
    have = df.dropna(subset=["mcap"])
    print(f"\n21d 事件 n={len(df)},有市值 {len(have)}")
    H = f"{'n':>5}{'mean%':>8}{'med%':>8}{'hit':>6}{'t':>7}"
    print(f"{'切法':<20}{H}")
    print(f"{'全部(有市值)':<20}{stat(have['x'])}")

    print("\n--- 市值分桶(正確 size)---")
    B = [("micro <$300M", 0, 3e8), ("small $300M-2B", 3e8, 2e9),
         ("mid $2B-10B", 2e9, 1e10), ("large >$10B", 1e10, 1e99)]
    for lbl, lo, hi in B:
        m = (have.mcap >= lo) & (have.mcap < hi)
        print(f"{lbl:<20}{stat(have[m]['x'])}")

    print("\n--- 可交易 cut:市值 >$1B(除去 micro/small)---")
    print(f"{'>$1B':<20}{stat(have[have.mcap >= 1e9]['x'])}")
    print(f"{'>$2B':<20}{stat(have[have.mcap >= 2e9]['x'])}")

    print("\n--- 對照:price 分桶(睇 price vs mcap 講唔講同一件事)---")
    for lbl, m in [("price<$5", have.price < 5), ("price$5-20", (have.price >= 5) & (have.price < 20)),
                   ("price>$20", have.price >= 20)]:
        print(f"{lbl:<20}{stat(have[m]['x'])}")
    # cross: are <$5 names all micro-cap?
    p5 = have[have.price < 5]
    print(f"\n  <$5 名嘅市值中位: ${p5['mcap'].median()/1e6:.0f}M  (若係 micro -> price 同 mcap 講同一件事)")


if __name__ == "__main__":
    run()
