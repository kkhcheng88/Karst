"""Insider cluster-buy — full horizon profile (short → long) x market cap.

Prior runs used 21/63/126d (21d +2%, 63d ~0, 126d negative). Expand SHORTER (5,10d) and
LONGER (189,252d) to see the whole shape, split by market cap (micro vs large — large was the
clean tradeable edge). Answers: does the edge start earlier? does the 126d-negative recover by
252d (long-term fundamental value) or stay a short-term pop-and-fade?

Reuses cached events + prices + market cap (no re-fetch). Forward EXCESS vs SPY.

    python backtest/experiments/exp_insider_horizons.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_insider_validate as IV       # noqa: E402
import exp_insider_mktcap as MC         # noqa: E402

HORS = [5, 10, 21, 42, 63, 126, 189, 252]


def stat(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 15:
        return f"{'n<15':>18}"
    t = x.mean() / (x.std() / np.sqrt(len(x)))
    return f"{x.mean()*100:>+6.2f}/{np.median(x)*100:>+5.1f}/{t:>4.1f}[{len(x):>4}]"


def run():
    ev = IV.build_events(IV._quarters("2022q1", "2025q2"))
    IV._batch_prices(ev["ticker"].tolist())
    MC._batch_mcap(ev["ticker"].tolist())
    spy = IV._px("SPY")
    rows = []
    for _, e in ev.iterrows():
        s = IV._px(e["ticker"])
        if s is None:
            continue
        mc = MC._MCAP.get(e["ticker"])
        rec = {"mcap": mc.asof(pd.Timestamp(e["date"])) if mc is not None else np.nan}
        any_ok = False
        for h in HORS:
            r, b = IV._fwd(s, e["date"], h), IV._fwd(spy, e["date"], h)
            rec[h] = (r - b) if (r is not None and b is not None) else np.nan
            any_ok = any_ok or (r is not None)
        if any_ok:
            rows.append(rec)
    df = pd.DataFrame(rows)
    micro = df[df.mcap < 3e8]
    large = df[df.mcap >= 1e10]
    print(f"\n事件 n={len(df)} | micro<$300M {len(micro)} | large>$10B {len(large)}")
    print("每格 = 平均%/中位%/t[n]   (excess vs SPY)")
    print(f"{'horizon':>8}{'全部':>19}{'micro<$300M':>19}{'large>$10B':>19}")
    for h in HORS:
        print(f"{str(h)+'d':>8}{stat(df[h]):>19}{stat(micro[h]):>19}{stat(large[h]):>19}")
    print("\nREAD: 短 TF 睇 edge 幾時開始/最強;長 TF 睇 126d 負係咪回復(基本面價值)定持續(短彈後褪)。"
          " large 若長 TF 仍正 = 真基本面;若同 micro 一齊轉負 = 只係短彈。")


if __name__ == "__main__":
    run()
