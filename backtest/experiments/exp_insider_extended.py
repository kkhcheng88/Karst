"""Insider — EXTENDED to 2006q1 (multi-regime) to close the 'one regime (2022-25)' gap.

SEC Form 345 bulk sets exist 2006q1+ (verified); defeatbeta prices+market_cap go to 1994.
Tests whether the deployable finding — the LARGE-cap (>$10B) SHORT-term (5-21d) insider edge —
holds across regimes (GFC 2008, 2011, 2015, 2018, 2020, 2022) or is 2022-25-specific.

Caveats: old delisted micro names may be unpriced by defeatbeta -> survivorship in the
micro/small buckets (large caps unaffected); pre-2023 quarters lack the 10b5-1 flag (minor for
open-market BUYS). Big one-time run (78 quarters, prices thousands of tickers; all cached).

    python backtest/experiments/exp_insider_extended.py            # 2006q1..2025q2
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_insider_validate as IV       # noqa: E402
import exp_insider_mktcap as MC         # noqa: E402

HORS = [5, 10, 21, 42, 63, 126, 252]


def stat(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 15:
        return f"{'n<15':>17}"
    t = x.mean() / (x.std() / np.sqrt(len(x)))
    return f"{x.mean()*100:>+6.2f}/{np.median(x)*100:>+5.1f}/{t:>4.1f}[{len(x):>4}]"


def run(start="2006q1", end="2025q2"):
    ev = IV.build_events(IV._quarters(start, end))
    print(f"[extended] {start}..{end}: {len(ev)} events / {ev['ticker'].nunique()} tickers")
    IV._batch_prices(ev["ticker"].tolist())
    MC._batch_mcap(ev["ticker"].tolist())
    spy = IV._px("SPY")
    rows = []
    for _, e in ev.iterrows():
        s = IV._px(e["ticker"])
        if s is None:
            continue
        mc = MC._MCAP.get(e["ticker"])
        rec = {"yr": e["date"].year,
               "mcap": mc.asof(pd.Timestamp(e["date"])) if mc is not None else np.nan}
        ok = False
        for h in HORS:
            r, b = IV._fwd(s, e["date"], h), IV._fwd(spy, e["date"], h)
            rec[h] = (r - b) if (r is not None and b is not None) else np.nan
            ok = ok or (r is not None)
        if ok:
            rows.append(rec)
    df = pd.DataFrame(rows)
    large = df[df.mcap >= 1e10]
    micro = df[df.mcap < 3e8]
    print(f"\n總事件 {len(df)} | large>$10B {len(large)} | micro<$300M {len(micro)}  ({start[:4]}-{end[:4]})")

    print("\n=== 全樣本 horizon profile 平均%/中位%/t[n] ===")
    print(f"{'hor':>5}{'全部':>18}{'micro':>18}{'large>$10B':>18}")
    for h in HORS:
        print(f"{str(h)+'d':>5}{stat(df[h]):>18}{stat(micro[h]):>18}{stat(large[h]):>18}")

    print("\n=== 大型股(>$10B)短線 edge 逐年(regime-robustness 決定測試)===")
    print(f"{'年':>6}{'5d 均%/t[n]':>18}{'10d':>18}{'21d':>18}")
    for y in sorted(large.yr.unique()):
        g = large[large.yr == y]
        def cell(h):
            x = g[h].dropna()
            if len(x) < 8:
                return f"{'n<8':>18}"
            t = x.mean()/(x.std()/np.sqrt(len(x))) if x.std() else 0
            return f"{x.mean()*100:>+6.2f}/{t:>4.1f}[{len(x):>3}]".rjust(18)
        print(f"{y:>6}{cell(5)}{cell(10)}{cell(21)}")
    print("\nREAD: 若大型股 5-21d 均值喺多數年份(尤其 2008/2018/2020/2022 危機)為正 -> regime-robust,"
          " 封 HIGH;若淨係 2022-25 正 -> regime-specific,標明。")


if __name__ == "__main__":
    a = sys.argv[1:]
    run(a[0] if a else "2006q1", a[1] if len(a) > 1 else "2025q2")
