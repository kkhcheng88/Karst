"""Insider 21d edge — rigor checks: is it a small-cap/illiquidity illusion, tail-driven, or
cost-fragile? Reuses exp_insider_validate's events + (already warm) price cache; no re-fetch.

The full-universe 21d edge (mean +2.01%, t 5.12) vs the large-cap subset (t 2.3) suggests the
strength may be small-cap-driven. Tests, all on the SAME events:
  1. price-level buckets (<$5 / $5-20 / >$20)  — proxy for size/liquidity (is it penny stocks?)
  2. realized-vol terciles                     — is it the wild high-vol names?
  3. trimmed mean (winsorize 5% / 10%)         — is the +2% a few huge winners? (median≈0)
  4. cost sensitivity (flat 0.3/0.6/1.0% + a price-scaled spread) — survives real costs?
  5. equal-weight vs price-weight vs vol-weight — does down-weighting small/wild names kill it?

    python backtest/experiments/exp_insider_rigor.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_insider_validate as IV  # noqa: E402


def stat(x, w=None):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 15:
        return f"{len(x):>5}  n<15"
    if w is None:
        m = x.mean()
    else:
        w = np.asarray(w, float)[:len(x)]
        m = np.average(x, weights=w)
    t = x.mean() / (x.std() / np.sqrt(len(x)))
    return f"{len(x):>5}{m*100:>+8.2f}{np.median(x)*100:>+8.2f}{(x > 0).mean()*100:>6.0f}%{t:>7.2f}"


def run():
    qtrs = IV._quarters("2022q1", "2025q2")
    ev = IV.build_events(qtrs)
    IV._batch_prices(ev["ticker"].tolist())
    spy = IV._px("SPY")
    rows = []
    for _, e in ev.iterrows():
        s = IV._px(e["ticker"])
        if s is None:
            continue
        pos = s.index.searchsorted(pd.Timestamp(e["date"]))
        if pos < 21 or pos + 21 >= len(s):
            continue
        x21, b21 = IV._fwd(s, e["date"], 21), IV._fwd(spy, e["date"], 21)
        if x21 is None or b21 is None:
            continue
        r = s.iloc[pos - 21:pos].pct_change().dropna()
        rows.append(dict(x=x21 - b21, price=float(s.iloc[pos]),
                         vol=(r.std() * np.sqrt(252)) if len(r) > 5 else np.nan))
    df = pd.DataFrame(rows).dropna(subset=["x", "price"])
    H = f"{'n':>5}{'mean%':>8}{'med%':>8}{'hit':>6}{'t':>7}"
    print(f"\n全部 21d 事件: n={len(df)}")
    print(f"{'切法':<18}{H}")
    print(f"{'全部':<18}{stat(df['x'])}")

    print("\n--- 1. 價格層(規模/流動性代理)---")
    for lbl, m in [("<$5(penny)", df.price < 5), ("$5-20", (df.price >= 5) & (df.price < 20)),
                   (">$20", df.price >= 20)]:
        print(f"{lbl:<18}{stat(df[m]['x'])}")

    print("\n--- 2. 實現波動 三分位 ---")
    q = df["vol"].quantile([1/3, 2/3]).values
    for lbl, m in [("低波動", df.vol < q[0]), ("中", (df.vol >= q[0]) & (df.vol < q[1])),
                   ("高波動", df.vol >= q[1])]:
        print(f"{lbl:<18}{stat(df[m]['x'])}")

    print("\n--- 3. 修剪均值(去極端,睇 tail-driven)---")
    x = df["x"].values
    for p, lbl in [(0, "原始"), (0.05, "去頭尾5%"), (0.10, "去頭尾10%")]:
        lo, hi = np.quantile(x, [p, 1 - p])
        xt = x[(x >= lo) & (x <= hi)]
        print(f"{lbl:<18}{'':5}{xt.mean()*100:>+8.2f} (n={len(xt)})")

    print("\n--- 4. 成本敏感度(21d 淨均值 + 仍為正嘅事件%)---")
    for c, lbl in [(0.003, "0.3%"), (0.006, "0.6%"), (0.010, "1.0%")]:
        net = df["x"] - c
        print(f"  flat {lbl:<6} 淨均值 {net.mean()*100:>+6.2f}%  正事件 {(net > 0).mean()*100:.0f}%")
    sp = np.clip(0.10 / df["price"], 0.002, 0.05)          # ~$0.10 spread / price, cap 5%
    net = df["x"] - sp
    print(f"  價格比例spread 淨均值 {net.mean()*100:>+6.2f}%  正事件 {(net > 0).mean()*100:.0f}%  "
          f"(penny 名成本大)")

    print("\n--- 5. 加權方式(down-weight 細/野 名)---")
    print(f"{'等權(原)':<18}{stat(df['x'])}")
    print(f"{'價格加權':<18}{stat(df['x'], w=df['price'])}")
    print(f"{'1/波動加權':<18}{stat(df['x'], w=1/df['vol'].clip(0.05))}")
    print("\nREAD: 若 edge 集中喺 <$5 / 高波動 / 去極端後大縮 / 價格加權後消失 -> 係細價股+tail 假象,"
          "唔可部署;若跨桶穩、修剪後仍在、價格加權仍正 -> 真、可交易。")


if __name__ == "__main__":
    run()
