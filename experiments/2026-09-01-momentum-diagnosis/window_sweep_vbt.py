"""KARST-129 加項(依 D-095):回望窗長度全掃,用 vectorBT 向量化。

純診斷,不是考試,不產生任何及格宣稱。

只郁一個自由度——形成窗長度。規則形狀完全照 KARST-127 不變:
  月底收市排名 → 揸最強三隻等權 → 次一交易日開市成交 → 10 個基點成本
  → 前三名動能全為負則整注揸 SPY(D-071 地板) → 對 SPY 買入持有基線。
**調倉頻率一律月底,不變**(週調倉是另一種規則形狀,不在本票)。

掃描範圍(D-095 加闊):
  月粒度:形成窗 L = 1~12 個月,跳空 S = 0 或 1 個月
  週粒度:形成窗 L = 2~52 週,  跳空 S = 0 或 4 週(1 週 = 5 個交易日)
  一律要求 L > S。

兩套實作一齊跑,互相對數:
  (甲) vectorBT Portfolio.from_orders(TargetPercent, cash_sharing) —— D-095 指定
  (乙) 手寫向量化 —— 與 KARST-127 同一套會計,用來錨定 (12,1) 那一格
差異原因記入報告。
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt

HERE = Path(__file__).resolve().parent
PRICES = HERE.parent / "2026-08-31-fear-greed" / "prices_daily.parquet"

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPY = "SPY"
N_HOLD = 3
COST_BP = 10.0                 # 單邊換手率 × 10 個基點
DAYS_PER_WEEK = 5

MONTH_LOOKBACKS = range(1, 13)
MONTH_SKIPS = (0, 1)
WEEK_LOOKBACKS = range(2, 53)
WEEK_SKIPS = (0, 4)


def build_combos():
    out = []
    for s in MONTH_SKIPS:
        for L in MONTH_LOOKBACKS:
            if L > s:
                out.append(("month", L, s))
    for s in WEEK_SKIPS:
        for L in WEEK_LOOKBACKS:
            if L > s:
                out.append(("week", L, s))
    return out


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
    close_a, open_a = close.to_numpy(), opn.to_numpy()

    me_pos = (pd.Series(np.arange(len(dates)), index=dates)
              .groupby([dates.year, dates.month]).last().to_numpy())
    me_labels = [dates[p].strftime("%Y-%m") for p in me_pos]
    sec_idx = np.array([cols.index(s) for s in SECTORS])
    spy_col = cols.index(SPY)
    m = len(dates)

    combos = build_combos()
    # 共同起點:所有格子(最長月窗 12 個月、最長週窗 52 週)都有足夠歷史
    max_week_days = max(WEEK_LOOKBACKS) * DAYS_PER_WEEK
    k0 = next(k for k in range(len(me_pos))
              if k >= max(MONTH_LOOKBACKS) and me_pos[k] - max_week_days >= 0)
    kmax = len(me_pos) - 2
    while me_pos[kmax + 1] + 1 >= m:
        kmax -= 1
    ks = np.arange(k0, kmax + 1)
    n_per = len(ks)

    # 成交價序列:每個決策月末的「次一交易日開市價」;持有到下一個同樣的點
    exec_rows = np.array([me_pos[k] + 1 for k in ks] + [me_pos[kmax + 1] + 1])
    exec_px = pd.DataFrame(open_a[exec_rows], columns=cols,
                           index=pd.DatetimeIndex(dates[exec_rows]))

    # ── 逐格砌目標權重 ────────────────────────────────────────────────
    weight_blocks, labels = [], []
    for gran, L, S in combos:
        w = np.zeros((n_per + 1, len(cols)))
        for row, k in enumerate(ks):
            if gran == "month":
                a, b = close_a[me_pos[k - S]], close_a[me_pos[k - L]]
            else:
                a = close_a[me_pos[k] - S * DAYS_PER_WEEK]
                b = close_a[me_pos[k] - L * DAYS_PER_WEEK]
            mom = a[sec_idx] / b[sec_idx] - 1.0
            top = np.argsort(-mom)[:N_HOLD]
            if bool(np.all(mom[top] < 0)):
                w[row, spy_col] = 1.0                 # 退 SPY 地板
            else:
                w[row, sec_idx[top]] = 1.0 / N_HOLD
        w[-1] = w[-2]                                  # 最後一列不再調倉
        weight_blocks.append(w)
        labels.append(f"{gran[0]}{L}-{S}")

    # ── (乙) 手寫向量化:與 KARST-127 同一套會計(目標對目標換手)──────
    rets = exec_px.to_numpy()[1:] / exec_px.to_numpy()[:-1] - 1.0   # (n_per, 10)
    spy_ret = rets[:, spy_col].copy()
    spy_ret[0] -= COST_BP / 10000.0                    # 基線期初收一次
    hand = {}
    for lab, w in zip(labels, weight_blocks):
        wt = w[:n_per]
        gross = (wt * rets).sum(axis=1)
        turn = np.abs(np.diff(np.vstack([np.zeros((1, len(cols))), wt]), axis=0)).sum(axis=1) / 2
        turn[0] = 1.0                                  # 期初建倉
        hand[lab] = gross - turn * COST_BP / 10000.0

    # ── (甲) vectorBT ─────────────────────────────────────────────────
    big_w = np.concatenate(weight_blocks, axis=1)
    mi = pd.MultiIndex.from_tuples(
        [(lab, t) for lab in labels for t in cols], names=["combo", "ticker"])
    size = pd.DataFrame(big_w, index=exec_px.index, columns=mi)
    price = pd.concat({lab: exec_px for lab in labels}, axis=1)
    price.columns.names = ["combo", "ticker"]
    price = price[mi]

    pf = vbt.Portfolio.from_orders(
        close=price, size=size, size_type="targetpercent",
        group_by="combo", cash_sharing=True, call_seq="auto",
        fees=COST_BP / 2 / 10000.0,      # 每邊收費;來回 = 2 × 單邊換手率 × 此值
        init_cash=100.0, freq="30D",
    )
    vbt_rets = pf.returns()                            # 每格的月度回報

    # ── 匯總 ─────────────────────────────────────────────────────────
    def cagr(r):
        return (np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0) * 100

    spy_cagr = cagr(spy_ret)
    rows = []
    for (gran, L, S), lab in zip(combos, labels):
        h = hand[lab]
        v = vbt_rets[lab].to_numpy()
        v = v[-len(h):] if len(v) > len(h) else v
        d = h - spy_ret
        t = d.mean() / (d.std(ddof=1) / math.sqrt(len(d)))
        rows.append({
            "granularity": gran, "lookback": L, "skip": S, "window_label": lab,
            "lookback_months_equiv": round(L if gran == "month" else L * DAYS_PER_WEEK / 21.0, 2),
            "n_periods": len(h),
            "cagr_pct": round(cagr(h), 3),
            "excess_cagr_pp": round(cagr(h) - spy_cagr, 3),
            "paired_t": round(t, 3),
            "vbt_cagr_pct": round(cagr(v), 3),
            "vbt_excess_cagr_pp": round(cagr(v) - spy_cagr, 3),
            "vbt_minus_hand_pp": round(cagr(v) - cagr(h), 3),
        })

    grid = pd.DataFrame(rows).sort_values(["granularity", "skip", "lookback"])
    grid.to_csv(HERE / "window_sweep.csv", index=False, encoding="utf-8")
    for metric in ("excess_cagr_pp", "paired_t", "vbt_excess_cagr_pp"):
        for gran in ("month", "week"):
            (grid[grid.granularity == gran]
             .pivot(index="lookback", columns="skip", values=metric)
             .to_csv(HERE / f"sweep_{gran}_{metric}.csv", encoding="utf-8"))

    print(f"評分期:{n_per} 期({me_labels[k0+1]}..{me_labels[kmax+1]}),"
          f"全部 {len(combos)} 格固定同一段 | SPY 基線年化 {spy_cagr:.2f}%")
    dv = grid["vbt_minus_hand_pp"].abs()
    print(f"vectorBT 對手寫:年化差 中位 {dv.median():.3f}pp 最大 {dv.max():.3f}pp "
          f"(相關 {np.corrcoef(grid.excess_cagr_pp, grid.vbt_excess_cagr_pp)[0,1]:.4f})")

    print("\n— 月粒度(年化超額 pp / 配對 t)—")
    for L in MONTH_LOOKBACKS:
        cells = []
        for S in MONTH_SKIPS:
            r = grid[(grid.granularity == "month") & (grid.lookback == L) & (grid.skip == S)]
            cells.append("      —      " if r.empty else
                         f"{r.excess_cagr_pp.iloc[0]:+6.2f}/{r.paired_t.iloc[0]:+5.2f}")
        print(f"  {L:>2} 個月 | 跳0 {cells[0]} | 跳1 {cells[1]}")

    print("\n— 週粒度(年化超額 pp / 配對 t),每 4 週抽一行 —")
    for L in WEEK_LOOKBACKS:
        if L % 4 and L != 2:
            continue
        cells = []
        for S in WEEK_SKIPS:
            r = grid[(grid.granularity == "week") & (grid.lookback == L) & (grid.skip == S)]
            cells.append("      —      " if r.empty else
                         f"{r.excess_cagr_pp.iloc[0]:+6.2f}/{r.paired_t.iloc[0]:+5.2f}")
        print(f"  {L:>2} 週({L*5/21.0:4.1f}月) | 跳0 {cells[0]} | 跳4週 {cells[1]}")

    b = grid.loc[grid.excess_cagr_pp.idxmax()]
    w = grid.loc[grid.excess_cagr_pp.idxmin()]
    print(f"\n最高 {b.window_label}:{b.excess_cagr_pp:+.2f}pp(t {b.paired_t:+.2f})")
    print(f"最低 {w.window_label}:{w.excess_cagr_pp:+.2f}pp(t {w.paired_t:+.2f})")
    print(f"配對 t 全域範圍:{grid.paired_t.min():+.2f} ~ {grid.paired_t.max():+.2f} | "
          f"|t|>=2 的格數:{(grid.paired_t.abs() >= 2).sum()} / {len(grid)}")
    print(f"超額為正的格數:{(grid.excess_cagr_pp > 0).sum()} / {len(grid)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
