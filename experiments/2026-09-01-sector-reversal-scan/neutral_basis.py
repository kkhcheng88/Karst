"""KARST-131 對照:等權板塊籃子 對 SPY 嘅基差(basket basis)。

兩臂都係揸九隻之中三隻、等權,而基線係市值加權嘅 SPY。
所以「超額」入面有一部分唔係訊號,係「等權板塊籃子 對 市值加權大市」嘅基差。
唔量呢一格,就分唔清反轉臂嗰片正區係真訊號定係籃子基差。

三條中性線,同一套會計(次一交易日開市成交、10 個基點單邊換手成本):
  EW9  — 九隻板塊全部等權,每月底再平衡
  RND3 — 每月底隨機揀三隻等權(1000 次抽樣嘅分佈),即「盲揀三隻」嘅對照臂
  SPY  — 基線本身
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sw", HERE / "sweep_reversal_vbt.py")
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)


def main() -> int:
    close, opn, cols = sw.load_panel()
    dates = close.index
    close_a, opn_a = close.to_numpy(), opn.to_numpy()
    sec_idx = np.array([cols.index(s) for s in sw.SECTORS])
    spy_col = cols.index(sw.SPY)
    m = len(dates)
    pos = pd.Series(np.arange(m), index=dates)
    anchors = np.sort(pos.groupby([dates.year, dates.month]).last().to_numpy())

    max_days = max(max(sw.WEEK_LOOKBACKS) * sw.DPW, max(sw.MONTH_LOOKBACKS) * sw.DPM)
    ks = [k for k in range(len(anchors))
          if dates[anchors[k]] >= sw.SCORE_START and anchors[k] - max_days >= 0
          and k - max(sw.MONTH_LOOKBACKS) >= 0 and anchors[k] + 1 < m]
    kmax, ks = ks[-1], np.array(ks[:-1])
    n = len(ks)
    exec_rows = np.array([anchors[k] + 1 for k in ks] + [anchors[kmax] + 1])
    px = opn_a[exec_rows]
    rets = px[1:] / px[:-1] - 1.0
    spy_ret = rets[:, spy_col].copy()
    spy_ret[0] -= sw.COST_BP / 10000.0

    def cagr(r):
        return (np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0) * 100

    def run(weights):
        gross = (weights * rets).sum(axis=1)
        turn = np.abs(np.diff(np.vstack([np.zeros((1, len(cols))), weights]), axis=0)).sum(axis=1) / 2
        turn[0] = 1.0
        return gross - turn * sw.COST_BP / 10000.0

    spy_cagr = cagr(spy_ret)

    # EW9:九隻等權,月底再平衡
    w = np.zeros((n, len(cols)))
    w[:, sec_idx] = 1.0 / len(sw.SECTORS)
    ew9 = run(w)
    d = ew9 - spy_ret
    t_ew9 = d.mean() / (d.std(ddof=1) / math.sqrt(len(d)))

    print(f"評分期 {n} 期({dates[exec_rows[0]].date()}..{dates[exec_rows[-1]].date()})")
    print(f"SPY 基線年化 {spy_cagr:.2f}%\n")
    print(f"EW9(九隻等權,月底再平衡):年化 {cagr(ew9):.2f}% | "
          f"對 SPY 超額 {cagr(ew9)-spy_cagr:+.2f}pp | 配對 t {t_ew9:+.2f}")

    # RND3:盲揀三隻
    rng = np.random.default_rng(20260901)
    outs = []
    for _ in range(1000):
        w = np.zeros((n, len(cols)))
        for r_ in range(n):
            w[r_, sec_idx[rng.choice(len(sw.SECTORS), sw.N_HOLD, replace=False)]] = 1.0 / sw.N_HOLD
        outs.append(cagr(run(w)) - spy_cagr)
    outs = np.array(outs)
    print(f"RND3(每月盲揀三隻,1000 次):對 SPY 超額 平均 {outs.mean():+.2f}pp | "
          f"中位 {np.median(outs):+.2f}pp | 5~95 百分位 {np.percentile(outs,5):+.2f} ~ "
          f"{np.percentile(outs,95):+.2f}pp | 標準差 {outs.std(ddof=1):.2f}pp")

    grid = pd.read_csv(HERE / "reversal_sweep.csv")
    pan = grid[grid.side != "calib"]
    for side in ("reversal", "momentum"):
        s = pan[(pan.side == side) & (pan.cadence == "month")]
        nm = "反轉臂" if side == "reversal" else "順勢臂"
        print(f"\n  {nm}(月調倉 43 格):平均超額 {s.excess_cagr_pp.mean():+.2f}pp"
              f" → 減走盲揀三隻嘅基差後 {s.excess_cagr_pp.mean()-outs.mean():+.2f}pp")
        print(f"    其中落喺盲揀分佈 5~95 百分位之內嘅格數:"
              f"{((s.excess_cagr_pp>=np.percentile(outs,5))&(s.excess_cagr_pp<=np.percentile(outs,95))).sum()}"
              f"/{len(s)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
