"""KARST-129 加項:回望窗長度敏感度數表(純診斷,不是考試,不產生任何及格宣稱)。

只郁一個自由度——回望窗長度。規則形狀完全照 KARST-127:
  月末收市按動能排名 → 揸最強三隻等權 → 次一交易日開市成交 → 扣 10 個基點 × 單邊換手率
  → 前三名動能全為負則整注揸 SPY(D-071 地板) → 對 SPY 買入持有基線比較。

動能定義沿用 KARST-127 的命名法:(L, S) 表示「由 t-L 個月末到 t-S 個月末的累計回報」。
  (12, 1) 即 KARST-127 主組,本表用它做自我校驗——應該重現 +0.75pp 年化超額、配對 t 0.49。

評分期對全部格子固定為 2000-01 起(即 L 最大值 12 所能支撐的起點),否則長短窗的成績不可比。
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PRICES = HERE.parent / "2026-08-31-fear-greed" / "prices_daily.parquet"

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPY = "SPY"
N_HOLD = 3
COST_BP = 10.0
MAX_LOOKBACK = 12               # 固定評分期起點,令所有格子可比
LOOKBACKS = range(1, 13)
SKIPS = (0, 1)


def run_cell(lookback, skip, me_close, me_pos, open_arr, sec_idx, spy_col, m):
    """跑一格 (L, S),回傳月度淨回報、SPY 月度回報、命中率、換馬次數。"""
    strat, spy_r, hits, slots, n_switch, n_retreat = [], [], 0, 0, 0, 0
    prev_w = np.zeros(open_arr.shape[1])
    first = True
    kmax = len(me_pos) - 1
    for k in range(MAX_LOOKBACK, kmax):
        if me_pos[k] + 1 >= m or me_pos[k + 1] + 1 >= m:
            break
        mom = me_close[k - skip, sec_idx] / me_close[k - lookback, sec_idx] - 1.0
        top = np.argsort(-mom)[:N_HOLD]
        retreat = bool(np.all(mom[top] < 0))

        b, e = me_pos[k] + 1, me_pos[k + 1] + 1
        ret_all = open_arr[e] / open_arr[b] - 1.0
        sec_ret = ret_all[sec_idx]

        w = np.zeros(open_arr.shape[1])
        if retreat:
            w[spy_col] = 1.0
            gross = float(ret_all[spy_col])
            n_retreat += 1
        else:
            for i in top:
                w[sec_idx[i]] = 1.0 / N_HOLD
            gross = float(sec_ret[top].mean())
            top3_actual = set(np.argsort(-sec_ret)[:N_HOLD].tolist())
            hits += sum(1 for i in top if int(i) in top3_actual)
            slots += N_HOLD

        turnover = float(np.abs(w - prev_w).sum() / 2.0)
        if not first and turnover > 1e-9:
            n_switch += 1
        strat.append(gross - turnover * COST_BP / 10000.0)
        spy_r.append(float(ret_all[spy_col]) - (COST_BP / 10000.0 if first else 0.0))
        prev_w, first = w, False

    s, p = np.array(strat), np.array(spy_r)
    n = len(s)
    cagr = lambda r: (np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0) * 100
    diff = s - p
    t_paired = diff.mean() / (diff.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
    return {
        "lookback_months": lookback, "skip_months": skip,
        "window_label": f"{lookback}-{skip}",
        "n_months": n,
        "cagr_pct": round(cagr(s), 3),
        "spy_cagr_pct": round(cagr(p), 3),
        "excess_cagr_pp": round(cagr(s) - cagr(p), 3),
        "monthly_excess_pp": round((s.mean() - p.mean()) * 100, 4),
        "paired_t": round(t_paired, 3),
        "hit_rate_pct": round(hits / slots * 100, 2) if slots else float("nan"),
        "n_switch": n_switch,
        "n_retreat_spy": n_retreat,
    }


def main() -> int:
    if not PRICES.exists():
        raise SystemExit(f"缺檔,響亮失敗:{PRICES}")
    px = pd.read_parquet(PRICES)
    close = px.pivot(index="date", columns="ticker", values="close")
    opn = px.pivot(index="date", columns="ticker", values="open")
    cols = SECTORS + [SPY]
    close = close[cols].dropna()
    opn = opn.loc[close.index, cols]
    dates = close.index

    me_pos = (pd.Series(np.arange(len(dates)), index=dates)
              .groupby([dates.year, dates.month]).last().to_numpy())
    me_close = close.to_numpy()[me_pos]
    open_arr = opn.to_numpy()
    sec_idx = np.array([cols.index(s) for s in SECTORS])
    spy_col = cols.index(SPY)
    m = len(dates)

    rows = []
    for skip in SKIPS:
        for L in LOOKBACKS:
            if L <= skip:
                continue        # L 必須大過跳空,否則窗口是空的
            rows.append(run_cell(L, skip, me_close, me_pos, open_arr,
                                 sec_idx, spy_col, m))

    grid = pd.DataFrame(rows)
    grid.to_csv(HERE / "window_grid.csv", index=False, encoding="utf-8")

    # 熱圖式數表(行 = 回望窗長,列 = 跳空)
    for metric in ("excess_cagr_pp", "paired_t", "hit_rate_pct"):
        piv = grid.pivot(index="lookback_months", columns="skip_months", values=metric)
        piv.to_csv(HERE / f"window_grid_{metric}.csv", encoding="utf-8")

    print(f"評分期:{grid['n_months'].iloc[0]} 個月(全部格子固定同一段,2000-01 起)\n")
    print("年化超額(百分點) / 配對 t 值 / 命中率%")
    print(f"{'回望窗':>6} | {'跳空 0':>22} | {'跳空 1':>22}")
    print("-" * 56)
    for L in LOOKBACKS:
        cells = []
        for s in SKIPS:
            r = grid[(grid.lookback_months == L) & (grid.skip_months == s)]
            cells.append("—".rjust(22) if r.empty else
                         f"{r.excess_cagr_pp.iloc[0]:+7.2f} / {r.paired_t.iloc[0]:+5.2f} / {r.hit_rate_pct.iloc[0]:5.2f}")
        print(f"{L:>6} | {cells[0]} | {cells[1]}")

    chk = grid[(grid.lookback_months == 12) & (grid.skip_months == 1)].iloc[0]
    print(f"\n自我校驗 (12,1) 應重現 KARST-127 主組:年化超額 {chk.excess_cagr_pp:+.2f}pp "
          f"(127 報 +0.75)、配對 t {chk.paired_t:+.2f}(127 報 0.49)、"
          f"命中率 {chk.hit_rate_pct:.2f}%(127 報 33.66)、月數 {chk.n_months}(127 報 319)")

    best = grid.loc[grid.excess_cagr_pp.idxmax()]
    worst = grid.loc[grid.excess_cagr_pp.idxmin()]
    print(f"最高一格 {best.window_label}:{best.excess_cagr_pp:+.2f}pp(t {best.paired_t:+.2f})")
    print(f"最低一格 {worst.window_label}:{worst.excess_cagr_pp:+.2f}pp(t {worst.paired_t:+.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
