"""Test the sharpely.in rule-based VCP screener -- does its 'tightness' add value over a momentum leader?

sharpely VCP rules (as given):
  liquidity : avg daily volume > 200,000            [market-cap filter skipped -- no PIT mcap]
  trend     : close > EMA50/100/200 AND EMA50>EMA100>EMA200
  momentum  : 1-year return > 20%  AND  within 15% of the 52-week high
  TIGHTNESS : ATR14/close < 0.05  AND  ATR14 < ATR50  AND  1-month range < 10%  AND  vol20 < vol50
(the screener defines the tight SETUP; the breakout/pivot entry was cut off with 'AND X'.)

Question tested: within the SAME momentum leaders, does adding the 4 TIGHTNESS conditions (the VCP part)
improve forward returns? A = leader; B = leader + VCP-tight. If B ~ A -> tightness adds nothing.

Data limit: the price cache stores CLOSE only, so ATR uses a close-to-close proxy (|Δclose|); range,
volume, EMAs, 1y-return, 52w-high are exact. Look-ahead-safe (month-end signal, 63d forward). Prices:
defeatbeta cache. CAVEATS: ATR = close proxy; costless; survivorship; market-cap filter skipped.

    python backtest/experiments/exp_vcp_sharpely.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".insider_data")
_FWD = 63


def _universe():
    px = {}
    for f in ["px_defeatbeta.pkl", "sp500_px.pkl"]:
        p = os.path.join(_DATA, f)
        if os.path.exists(p):
            for k, v in pickle.load(open(p, "rb")).items():
                if v is not None and k not in px:
                    s = (v["close"] if isinstance(v, pd.DataFrame) else v)
                    vol = v["volume"] if isinstance(v, pd.DataFrame) and "volume" in v else None
                    px[k] = (s[~s.index.duplicated()].sort_index(),
                             vol[~vol.index.duplicated()].sort_index() if vol is not None else None)
    return px


def run():
    px = _universe()
    spy = px["SPY"][0]
    recs = []
    for tk, (s, vol) in px.items():
        if tk == "SPY" or s is None or len(s) < 320:
            continue
        e50, e100, e200 = s.ewm(span=50).mean(), s.ewm(span=100).mean(), s.ewm(span=200).mean()
        hi52 = s.rolling(252).max()
        ret1y = s / s.shift(252) - 1
        atr = s.diff().abs()                                   # close-to-close ATR proxy
        atr14, atr50 = atr.rolling(14).mean(), atr.rolling(50).mean()
        atr_pct = atr14 / s
        rng1m = (s.rolling(20).max() - s.rolling(20).min()) / s.rolling(20).min()
        v20 = vol.rolling(20).mean() if vol is not None else None
        v50 = vol.rolling(50).mean() if vol is not None else None

        leader = ((s > e50) & (s > e100) & (s > e200) & (e50 > e100) & (e100 > e200)
                  & (ret1y > 0.20) & (s >= hi52 * 0.85))
        if v50 is not None:
            leader = leader & (v50 > 200000)
        tight = (atr_pct < 0.05) & (atr14 < atr50) & (rng1m < 0.10)
        if v20 is not None and v50 is not None:
            tight = tight & (v20 < v50)
        vcp = leader & tight

        idx = s.index
        for t in s.resample("ME").last().index:               # month-end sampling
            i = idx.searchsorted(t)
            if i < 260 or i + _FWD >= len(s):
                continue
            if not leader.iloc[i]:
                continue
            fwd = s.iloc[i + _FWD] / s.iloc[i] - 1
            b0, b1 = spy.asof(t), spy.asof(idx[i + _FWD])
            exc = fwd - (b1 / b0 - 1) if (b0 == b0 and b1 == b1 and b0 > 0) else np.nan
            recs.append({"date": t, "fwd": fwd, "excess": exc,
                         "leader": True, "vcp": bool(vcp.iloc[i])})
    df = pd.DataFrame(recs).dropna(subset=["excess"])
    print(f"[sharpely-vcp] leader name-months: {len(df)} | of which VCP-tight: {int(df['vcp'].sum())} "
          f"({df['vcp'].mean()*100:.0f}%)\n")

    print("=== does VCP-TIGHTNESS add value over a plain momentum leader? (63d fwd, month-end) ===")
    print(f"{'set':>26} {'n':>6} {'mean fwd%':>9} {'excess%':>8} {'win%':>5} {'exc t':>6}")
    for name, sub in [("A: momentum leader (all)", df),
                      ("B: leader + VCP-tight", df[df.vcp]),
                      ("leader NOT tight", df[~df.vcp])]:
        if len(sub) < 20:
            print(f"{name:>26} {len(sub):>6}  (insufficient)"); continue
        e = sub["excess"]
        t = e.mean() / (e.std() / np.sqrt(len(e))) if e.std() else np.nan
        print(f"{name:>26} {len(sub):>6} {sub['fwd'].mean()*100:>8.2f} {e.mean()*100:>7.2f} "
              f"{(sub['fwd']>0).mean()*100:>4.0f} {t:>6.2f}")
    b, a = df[df.vcp]["excess"], df[~df.vcp]["excess"]
    if len(b) > 20 and len(a) > 20:
        from math import sqrt
        diff = b.mean() - a.mean()
        se = sqrt(b.var()/len(b) + a.var()/len(a))
        print(f"\n  VCP-tight minus not-tight: {diff*100:+.2f}% excess  (t {diff/se:.2f})")
    print("\nREAD: B > (leader NOT tight) with a significant gap -> the VCP tightness ADDS value. "
          "B ~ leader-not-tight -> tightness is dressing on momentum. CAVEATS: ATR=close proxy; "
          "costless; survivorship; market-cap filter skipped; no breakout-entry (setup-state test).")


if __name__ == "__main__":
    run()
