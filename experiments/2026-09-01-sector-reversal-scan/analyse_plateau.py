"""KARST-131 判讀:補齊跳空 4 週欄、平原/孤峰鄰域檢定、危機期主導檢查。

危機期檢查係文獻關 §1.3 事前寫死嘅義務,唔係事後諗出嚟嘅切法:
Nagel (2012) 明證行業層反轉喺高 VIX 期間先有錢,無條件冇。所以全樣本見到
任何似樣嘅反轉,首要檢查係咪由 2000-02、2008-09、2020、2022 呢幾段主導。

五熊窗照考試協議第六節第 1 條(三票同一批,新票沿用)。
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

BEARS = [
    ("2000-04", "2002-10"), ("2007-11", "2009-03"), ("2018-10", "2018-12"),
    ("2020-03", "2020-03"), ("2022-02", "2022-10"),
]


def series_for(close, opn, cols, cadence, gran, L, S, side):
    """重造單一格嘅逐期超額序列(與主掃描同一套手寫會計)。"""
    dates = close.index
    close_a, opn_a = close.to_numpy(), opn.to_numpy()
    sec_idx = np.array([cols.index(s) for s in sw.SECTORS])
    spy_col = cols.index(sw.SPY)
    m = len(dates)
    pos_ser = pd.Series(np.arange(m), index=dates)
    if cadence == "month":
        anchors = pos_ser.groupby([dates.year, dates.month]).last().to_numpy()
    else:
        iso = dates.isocalendar()
        anchors = pos_ser.groupby([iso.year.to_numpy(), iso.week.to_numpy()]).last().to_numpy()
    anchors = np.sort(anchors)
    max_days = max(max(sw.WEEK_LOOKBACKS) * sw.DPW, max(sw.MONTH_LOOKBACKS) * sw.DPM)
    max_months = max(sw.MONTH_LOOKBACKS)
    ks = []
    for k in range(len(anchors)):
        p = anchors[k]
        if dates[p] < sw.SCORE_START or p - max_days < 0 or p + 1 >= m:
            continue
        if cadence == "month" and k - max_months < 0:
            continue
        ks.append(k)
    ks = np.array(ks)
    kmax, ks = ks[-1], ks[:-1]
    n_per = len(ks)
    exec_rows = np.array([anchors[k] + 1 for k in ks] + [anchors[kmax] + 1])
    exec_px = opn_a[exec_rows]
    exec_dates = pd.DatetimeIndex(dates[exec_rows])

    w = np.zeros((n_per + 1, len(cols)))
    for row, k in enumerate(ks):
        p = anchors[k]
        a = close_a[p - S * sw.DPW]
        if gran == "week":
            b = close_a[p - L * sw.DPW]
        elif cadence == "month":
            b = close_a[anchors[k - L]]
        else:
            b = close_a[p - L * sw.DPM]
        mom = a[sec_idx] / b[sec_idx] - 1.0
        pick = np.argsort(mom)[:sw.N_HOLD] if side == "reversal" else np.argsort(-mom)[:sw.N_HOLD]
        w[row, sec_idx[pick]] = 1.0 / sw.N_HOLD
    w[-1] = w[-2]

    rets = exec_px[1:] / exec_px[:-1] - 1.0
    spy_ret = rets[:, spy_col].copy()
    spy_ret[0] -= sw.COST_BP / 10000.0
    wt = w[:n_per]
    gross = (wt * rets).sum(axis=1)
    turn = np.abs(np.diff(np.vstack([np.zeros((1, len(cols))), wt]), axis=0)).sum(axis=1) / 2
    turn[0] = 1.0
    strat = gross - turn * sw.COST_BP / 10000.0
    # 持有期以「開倉日」標記,即 exec_dates[i] 到 exec_dates[i+1]
    return pd.Series(strat - spy_ret, index=exec_dates[:n_per])


def tstat(x):
    x = np.asarray(x)
    return x.mean() / (x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else float("nan")


def main() -> int:
    close, opn, cols = sw.load_panel()
    grid = pd.read_csv(HERE / "reversal_sweep.csv")
    pan = grid[grid.side != "calib"]

    # ── 一、補齊三欄數表(含跳空 4 週)────────────────────────────────
    for cadence in ("month", "week"):
        for side in ("reversal", "momentum"):
            sub = pan[(pan.cadence == cadence) & (pan.side == side)]
            name = "反轉(買最弱三隻)" if side == "reversal" else "順勢(買最強三隻)"
            print(f"\n— {cadence} 調倉 / {name}(年化超額 pp / 配對 t)—")
            print("  形成窗  |   跳0        |   跳1週      |   跳4週")
            for gran, rng in (("week", sw.WEEK_LOOKBACKS), ("month", sw.MONTH_LOOKBACKS)):
                for L in rng:
                    cells = []
                    for S in sw.SKIPS_WEEKS:
                        r = sub[(sub.granularity == gran) & (sub.lookback == L) & (sub.skip_weeks == S)]
                        cells.append("     —      " if r.empty else
                                     f"{r.excess_cagr_pp.iloc[0]:+6.2f}/{r.paired_t.iloc[0]:+5.2f}")
                    unit = "週" if gran == "week" else "個月"
                    print(f"  {L:>2}{unit}   | {cells[0]} | {cells[1]} | {cells[2]}")

    # ── 二、反轉臂鄰域檢定(沿形成窗軸)──────────────────────────────
    print("\n\n=== 反轉臂:沿形成窗軸嘅連續正區(平原定孤峰)===")
    for cadence in ("month", "week"):
        for S in sw.SKIPS_WEEKS:
            sub = pan[(pan.cadence == cadence) & (pan.side == "reversal")
                      & (pan.granularity == "week") & (pan.skip_weeks == S)].sort_values("lookback")
            if sub.empty:
                continue
            seq = "".join("+" if v > 0 else "-" for v in sub.excess_cagr_pp)
            runs, cur = [], 1
            for i in range(1, len(seq)):
                if seq[i] == seq[i - 1]:
                    cur += 1
                else:
                    runs.append((seq[i - 1], cur)); cur = 1
            runs.append((seq[-1], cur))
            best = max((c for s, c in runs if s == "+"), default=0)
            print(f"  [{cadence} 週粒度 跳{S}] 符號序列(1→13 週) {seq}  最長連續正區 {best} 格")

    # ── 三、危機期主導檢查(文獻關 §1.3 事前寫死)──────────────────
    print("\n\n=== 危機期主導檢查(反轉臂,五熊窗 vs 其餘)===")
    print("文獻預期:行業層反轉無條件冇錢,只喺高 VIX 期間有(Nagel 2012)。")
    targets = [
        ("month", "week", 8, 1), ("month", "week", 12, 0), ("month", "month", 2, 1),
        ("week", "week", 12, 0), ("week", "week", 10, 0), ("week", "week", 13, 0),
    ]
    print(f"\n  {'格':<18} {'全期':>16} {'熊窗內':>18} {'熊窗外':>18}")
    for cadence, gran, L, S in targets:
        d = series_for(close, opn, cols, cadence, gran, L, S, "reversal")
        mask = np.zeros(len(d), dtype=bool)
        for a, b in BEARS:
            mask |= ((d.index >= pd.Timestamp(a)) & (d.index <= pd.Timestamp(b) + pd.offsets.MonthEnd(0)))
        ppy = 12.0 if cadence == "month" else 52.0
        lab = f"{cadence[0]}/{'w' if gran=='week' else 'm'}{L}-{S}"
        tot = d.mean() * ppy * 100
        inb = d[mask].mean() * ppy * 100
        outb = d[~mask].mean() * ppy * 100
        print(f"  {lab:<18} {tot:+7.2f}pp/t{tstat(d):+5.2f} "
              f"{inb:+8.2f}pp/t{tstat(d[mask]):+5.2f}(n={mask.sum():>4}) "
              f"{outb:+8.2f}pp/t{tstat(d[~mask]):+5.2f}(n={(~mask).sum():>4})")

    # ── 四、反轉臂 對 順勢臂:係咪同一件事講兩次 ────────────────────
    print("\n\n=== 反轉臂 對 順勢臂:相關性(係咪同一個事實嘅鏡像)===")
    for cadence in ("month", "week"):
        r = pan[(pan.cadence == cadence) & (pan.side == "reversal")].set_index("label")
        mm = pan[(pan.cadence == cadence) & (pan.side == "momentum")].set_index("label")
        key = lambda s: s.str.replace(r"^[RM]:", "", regex=True)
        r2 = r.reset_index(); r2["k"] = key(r2.label)
        m2 = mm.reset_index(); m2["k"] = key(m2.label)
        j = r2.merge(m2, on="k", suffixes=("_r", "_m"))
        c = np.corrcoef(j.excess_cagr_pp_r, j.excess_cagr_pp_m)[0, 1]
        print(f"  [{cadence}] 逐格超額相關 {c:+.3f}  "
              f"(兩臂同時為正嘅格數 {(((j.excess_cagr_pp_r>0)&(j.excess_cagr_pp_m>0)).sum())}/{len(j)})")

    # ── 五、全景圖總帳 ──────────────────────────────────────────────
    rev = pan[pan.side == "reversal"]
    mom = pan[pan.side == "momentum"]
    print("\n\n=== 全景圖總帳 ===")
    for nm, s in (("反轉臂", rev), ("順勢臂", mom)):
        print(f"  {nm}:{len(s)} 格 | 平均 {s.excess_cagr_pp.mean():+.2f}pp | "
              f"中位 {s.excess_cagr_pp.median():+.2f}pp | 為正 {(s.excess_cagr_pp>0).sum()}/{len(s)} | "
              f"t 範圍 {s.paired_t.min():+.2f}~{s.paired_t.max():+.2f} | "
              f"|t|>=2 {(s.paired_t.abs()>=2).sum()} 格")
    print(f"\n  換手率對照(年化調倉次數 × 單邊換手):")
    for cadence in ("month", "week"):
        s = rev[rev.cadence == cadence]
        print(f"    [{cadence}] 中位年化換手 {s.ann_turnover_x.median():.2f} 次 → "
              f"成本拖累中位 {s.ann_cost_drag_pp.median():.2f}pp/年")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
