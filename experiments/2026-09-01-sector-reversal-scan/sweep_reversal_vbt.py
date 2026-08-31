"""KARST-131 板塊短窗反轉全景圖(考試協議第七節探索閘)。

**純探索,不是考試,不產生任何及格宣稱。** 任何一格幾靚都只可以入候選庫。

問題:板塊層「短窗買弱者」(反轉)呢條線,參數面上有冇一片講得通嘅平原?

規則形狀(反向臂,主體):
  排名日收市計形成窗回報 → 揸**最弱三隻**等權 → 次一交易日開市成交
  → 單邊換手率 × 10 個基點 → 對 SPY 含息買入持有基線
  **冇 D-071 退 SPY 地板**——嗰條地板係為順勢臂設計(前三名動能全負就退場),
  照搬落反轉臂會變成「最弱三隻回報全負就唔買最弱三隻」,同規則本意打架。
  順勢對照臂同樣唔開地板,兩臂口徑一致先可以逐格對照。

參數面(一次過掃齊,第七節第 6 條:唔准擠牙膏式逐次加格重跑):
  形成窗 週粒度 L = 1~13 週、月粒度 L = 1~3 個月
  跳空   S = 0、1 或 4 週(1 週 = 5 個交易日)
  一律要求形成窗長過跳空
  → 每網 43 格 × 2 個方向(反轉主體 + 順勢對照)
  主網:月底調倉  ‖  副網:週五(該週最後一個交易日)調倉
  → 全景圖合共 172 格

**跳空 4 週係票面之外嘅擴充,喺見到任何結果之前決定,理由寫低**:
票面寫死跳空 0/1 週,但本票嘅線索本身就係 KARST-129 全表唯一 |t|≥2 嘅 `w8-4`
——8 週形成、**跳 4 週**、追強者 t=−2.41。冇跳 4 週嗰一行,本票報唔到嗰格嘅
鏡像,即係答唔到自己開票嘅理由。依第七節第 6 條「一次過掃齊」,補喺同一次掃描
入面,唔係事後加格重跑。

另加 2 格**機械校驗**(唔屬全景圖,唔入候選):順勢臂 + D-071 地板 + 月底調倉,
重跑 KARST-129 嘅 m12-1 同 w8-4,對得返 +0.75pp/+0.48 同 −3.77pp/−2.41 先算部機器啱。

實作:vectorBT 1.1.0 `Portfolio.from_orders`(D-095 指定)為主,
另跑一套手寫向量化對數(與 KARST-127/129 同一套會計)。
"""

from __future__ import annotations

import json
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
COST_BP = 10.0          # 單邊換手率 × 10 個基點(與 KARST-127/129 同一把尺)
DPW = 5                 # 一週 = 5 個交易日
DPM = 21                # 一個月 = 21 個交易日(只用於週調倉副網的月粒度形成窗)

WEEK_LOOKBACKS = range(1, 14)     # 1~13 週
MONTH_LOOKBACKS = range(1, 4)     # 1~3 個月
SKIPS_WEEKS = (0, 1, 4)           # 跳空 0、1 或 4 週(4 週為票面外擴充,理由見檔頭)

# 評分期起點對齊 KARST-129(2000-02 持有月起),令兩票逐格可比
SCORE_START = pd.Timestamp("2000-01-31")


# ── 面板 ────────────────────────────────────────────────────────────────
def load_panel():
    if not PRICES.exists():
        raise SystemExit(f"缺檔,響亮失敗:{PRICES}")
    px = pd.read_parquet(PRICES)
    close = px.pivot(index="date", columns="ticker", values="close")
    opn = px.pivot(index="date", columns="ticker", values="open")
    cols = SECTORS + [SPY]
    close = close[cols].dropna()
    opn = opn.loc[close.index, cols]
    return close, opn, cols


def build_combos():
    """(粒度, 形成窗, 跳空週) 清單,一律要求 L > S。"""
    out = []
    for s in SKIPS_WEEKS:
        for L in WEEK_LOOKBACKS:
            if L > s:
                out.append(("week", L, s))
    for s in SKIPS_WEEKS:
        for L in MONTH_LOOKBACKS:
            if L * DPM > s * DPW:           # 以交易日計,形成窗要長過跳空
                out.append(("month", L, s))
    return out


def label_of(gran, L, S, side):
    return f"{'R' if side == 'reversal' else 'M'}:{gran[0]}{L}-{S}"


# ── 逐網掃描 ────────────────────────────────────────────────────────────
def run_grid(close, opn, cols, cadence):
    """cadence = 'month' 月底調倉主網 / 'week' 週五調倉副網。"""
    dates = close.index
    close_a, opn_a = close.to_numpy(), opn.to_numpy()
    sec_idx = np.array([cols.index(s) for s in SECTORS])
    spy_col = cols.index(SPY)
    m = len(dates)
    pos_ser = pd.Series(np.arange(m), index=dates)

    if cadence == "month":
        anchors = pos_ser.groupby([dates.year, dates.month]).last().to_numpy()
        ppy = 12.0
    else:
        iso = dates.isocalendar()
        anchors = pos_ser.groupby([iso.year.to_numpy(), iso.week.to_numpy()]).last().to_numpy()
        ppy = 52.0
    anchors = np.sort(anchors)

    # 形成窗最遠要回望幾多個交易日 / 幾多個錨點
    max_days = max(max(WEEK_LOOKBACKS) * DPW, max(MONTH_LOOKBACKS) * DPM)
    max_months = max(MONTH_LOOKBACKS)

    # 決策錨點:要有足夠歷史,而且執行日(次一交易日)存在;起點對齊 SCORE_START
    ks = []
    for k in range(len(anchors)):
        p = anchors[k]
        if dates[p] < SCORE_START:
            continue
        if p - max_days < 0:
            continue
        if cadence == "month" and k - max_months < 0:
            continue
        if p + 1 >= m:
            continue
        ks.append(k)
    ks = np.array(ks)
    # 最後一個錨點只用來平倉,不再開新倉
    kmax = ks[-1]
    ks = ks[:-1]
    n_per = len(ks)

    exec_rows = np.array([anchors[k] + 1 for k in ks] + [anchors[kmax] + 1])
    exec_px = pd.DataFrame(opn_a[exec_rows], columns=cols,
                           index=pd.DatetimeIndex(dates[exec_rows]))

    combos = build_combos()
    weight_blocks, labels, meta = [], [], []
    for gran, L, S in combos:
        # 形成窗回報:由 t−L 到 t−S
        moms = np.empty((n_per, len(SECTORS)))
        for row, k in enumerate(ks):
            p = anchors[k]
            a = close_a[p - S * DPW]
            if gran == "week":
                b = close_a[p - L * DPW]
            elif cadence == "month":
                b = close_a[anchors[k - L]]      # 月底對月底(同 KARST-129)
            else:
                b = close_a[p - L * DPM]         # 週調倉副網:用交易日近似
            moms[row] = a[sec_idx] / b[sec_idx] - 1.0

        for side in ("reversal", "momentum"):
            w = np.zeros((n_per + 1, len(cols)))
            for row in range(n_per):
                mom = moms[row]
                pick = np.argsort(mom)[:N_HOLD] if side == "reversal" else np.argsort(-mom)[:N_HOLD]
                w[row, sec_idx[pick]] = 1.0 / N_HOLD
            w[-1] = w[-2]
            weight_blocks.append(w)
            labels.append(label_of(gran, L, S, side))
            meta.append((gran, L, S, side))

    # ── 校驗格:順勢 + D-071 地板,重跑 KARST-129 兩格(只在月底主網)──
    calib = []
    if cadence == "month":
        for cg, cL, cS in (("month", 12, 1), ("week", 8, 4)):
            w = np.zeros((n_per + 1, len(cols)))
            for row, k in enumerate(ks):
                p = anchors[k]
                if cg == "month":
                    a, b = close_a[anchors[k - cS]], close_a[anchors[k - cL]]
                else:
                    a, b = close_a[p - cS * DPW], close_a[p - cL * DPW]
                mom = a[sec_idx] / b[sec_idx] - 1.0
                top = np.argsort(-mom)[:N_HOLD]
                if bool(np.all(mom[top] < 0)):
                    w[row, spy_col] = 1.0          # D-071 地板
                else:
                    w[row, sec_idx[top]] = 1.0 / N_HOLD
            w[-1] = w[-2]
            weight_blocks.append(w)
            lab = f"CAL:{cg[0]}{cL}-{cS}"
            labels.append(lab)
            meta.append((cg, cL, cS, "calib"))
            calib.append(lab)

    # ── (乙) 手寫向量化:目標對目標換手,與 KARST-127/129 同一套會計 ──
    px_a = exec_px.to_numpy()
    rets = px_a[1:] / px_a[:-1] - 1.0
    spy_ret = rets[:, spy_col].copy()
    spy_ret[0] -= COST_BP / 10000.0                # 基線期初收一次
    hand = {}
    for lab, w in zip(labels, weight_blocks):
        wt = w[:n_per]
        gross = (wt * rets).sum(axis=1)
        turn = np.abs(np.diff(np.vstack([np.zeros((1, len(cols))), wt]), axis=0)).sum(axis=1) / 2
        turn[0] = 1.0
        hand[lab] = gross - turn * COST_BP / 10000.0

    # ── (甲) vectorBT ────────────────────────────────────────────────
    big_w = np.concatenate(weight_blocks, axis=1)
    mi = pd.MultiIndex.from_tuples([(l, t) for l in labels for t in cols],
                                   names=["combo", "ticker"])
    size = pd.DataFrame(big_w, index=exec_px.index, columns=mi)
    price = pd.concat({l: exec_px for l in labels}, axis=1)
    price.columns.names = ["combo", "ticker"]
    price = price[mi]
    pf = vbt.Portfolio.from_orders(
        close=price, size=size, size_type="targetpercent",
        group_by="combo", cash_sharing=True, call_seq="auto",
        fees=COST_BP / 2 / 10000.0,      # 每邊收費;來回 = 2 × 單邊換手率 × 此值
        init_cash=100.0, freq="30D" if cadence == "month" else "7D",
    )
    vbt_rets = pf.returns()

    def cagr(r):
        return (np.prod(1.0 + r) ** (ppy / len(r)) - 1.0) * 100

    spy_cagr = cagr(spy_ret)
    rows = []
    for lab, (gran, L, S, side) in zip(labels, meta):
        h = hand[lab]
        v = vbt_rets[lab].to_numpy()
        v = v[-len(h):] if len(v) > len(h) else v
        d = h - spy_ret
        t = d.mean() / (d.std(ddof=1) / math.sqrt(len(d)))
        turn = np.abs(np.diff(np.vstack([np.zeros((1, len(cols))),
                                         weight_blocks[labels.index(lab)][:n_per]]),
                              axis=0)).sum(axis=1) / 2
        turn[0] = 1.0
        rows.append({
            "cadence": cadence, "side": side, "granularity": gran,
            "lookback": L, "skip_weeks": S, "label": lab,
            "lookback_months_equiv": round(L * DPW / 21.0 if gran == "week" else float(L), 2),
            "n_periods": len(h),
            "cagr_pct": round(cagr(h), 3),
            "excess_cagr_pp": round(cagr(h) - spy_cagr, 3),
            "paired_t": round(t, 3),
            "hit_rate_pct": round(float((d > 0).mean() * 100), 2),
            "ann_turnover_x": round(float(turn[1:].mean() * ppy), 2),
            "ann_cost_drag_pp": round(float(turn[1:].mean() * ppy * COST_BP / 100.0), 3),
            "vbt_cagr_pct": round(cagr(v), 3),
            "vbt_excess_cagr_pp": round(cagr(v) - spy_cagr, 3),
            "vbt_minus_hand_pp": round(cagr(v) - cagr(h), 3),
        })

    info = {
        "cadence": cadence, "n_periods": int(n_per),
        "first_exec": str(exec_px.index[0].date()),
        "last_exec": str(exec_px.index[-1].date()),
        "spy_cagr_pct": round(spy_cagr, 3),
        "n_cells": int(len(labels)), "calib_cells": calib,
    }
    return pd.DataFrame(rows), info


def main() -> int:
    close, opn, cols = load_panel()
    out_rows, infos = [], {}
    for cadence in ("month", "week"):
        g, info = run_grid(close, opn, cols, cadence)
        out_rows.append(g)
        infos[cadence] = info
        print(f"[{cadence}] {info['n_periods']} 期 "
              f"({info['first_exec']}..{info['last_exec']}), "
              f"{info['n_cells']} 格, SPY 基線年化 {info['spy_cagr_pct']:.2f}%")

    grid = pd.concat(out_rows, ignore_index=True)
    grid.to_csv(HERE / "reversal_sweep.csv", index=False, encoding="utf-8")

    dv = grid["vbt_minus_hand_pp"].abs()
    print(f"\nvectorBT 對手寫:年化差 中位 {dv.median():.4f}pp 最大 {dv.max():.4f}pp "
          f"(相關 {np.corrcoef(grid.excess_cagr_pp, grid.vbt_excess_cagr_pp)[0,1]:.4f})")

    # 機械校驗
    print("\n— 機械校驗(順勢 + D-071 地板,對 KARST-129)—")
    for lab, ref in (("CAL:m12-1", "+0.75pp / t +0.48"), ("CAL:w8-4", "−3.77pp / t −2.41")):
        r = grid[grid.label == lab]
        if not r.empty:
            print(f"  {lab}: 本票 {r.excess_cagr_pp.iloc[0]:+.2f}pp / t "
                  f"{r.paired_t.iloc[0]:+.2f}   ‖ KARST-129 {ref}")

    # 逐網數表
    pan = grid[grid.side != "calib"]
    for cadence in ("month", "week"):
        for side in ("reversal", "momentum"):
            sub = pan[(pan.cadence == cadence) & (pan.side == side)]
            for metric in ("excess_cagr_pp", "paired_t"):
                (sub.assign(win=sub.granularity.str[0] + sub.lookback.astype(str))
                    .pivot(index="win", columns="skip_weeks", values=metric)
                    .to_csv(HERE / f"grid_{cadence}_{side}_{metric}.csv", encoding="utf-8"))

    def table(cadence, side):
        sub = pan[(pan.cadence == cadence) & (pan.side == side)]
        print(f"\n— {cadence} 調倉 / {'反轉(買最弱三隻)' if side=='reversal' else '順勢(買最強三隻)'} "
              f"(年化超額 pp / 配對 t)—")
        for gran, rng in (("week", WEEK_LOOKBACKS), ("month", MONTH_LOOKBACKS)):
            for L in rng:
                cells = []
                for S in SKIPS_WEEKS:
                    r = sub[(sub.granularity == gran) & (sub.lookback == L) & (sub.skip_weeks == S)]
                    cells.append("      —      " if r.empty else
                                 f"{r.excess_cagr_pp.iloc[0]:+6.2f}/{r.paired_t.iloc[0]:+5.2f}")
                unit = "週" if gran == "week" else "個月"
                print(f"  {L:>2} {unit} | 跳0 {cells[0]} | 跳1週 {cells[1]}")

    for cadence in ("month", "week"):
        for side in ("reversal", "momentum"):
            table(cadence, side)

    rev = pan[pan.side == "reversal"]
    print(f"\n=== 反轉臂全景({len(rev)} 格)===")
    for cadence in ("month", "week"):
        s = rev[rev.cadence == cadence]
        b, w = s.loc[s.excess_cagr_pp.idxmax()], s.loc[s.excess_cagr_pp.idxmin()]
        print(f"  [{cadence}] 最高 {b.label} {b.excess_cagr_pp:+.2f}pp(t {b.paired_t:+.2f}) | "
              f"最低 {w.label} {w.excess_cagr_pp:+.2f}pp(t {w.paired_t:+.2f}) | "
              f"為正 {(s.excess_cagr_pp>0).sum()}/{len(s)} | "
              f"|t|>=2 {(s.paired_t.abs()>=2).sum()} | t 範圍 "
              f"{s.paired_t.min():+.2f}~{s.paired_t.max():+.2f}")
    print(f"  全反轉臂 |t|>=2 格數:{(rev.paired_t.abs()>=2).sum()} / {len(rev)};"
          f"  最高 t = {rev.paired_t.max():+.2f}({rev.loc[rev.paired_t.idxmax()].label})")

    with open(HERE / "results.json", "w", encoding="utf-8") as f:
        json.dump({
            "ticket": "KARST-131",
            "nature": "探索票(考試協議第七節);不產生任何及格宣稱,一切入候選庫",
            "engine": f"vectorBT {vbt.__version__} + 手寫向量化對數",
            "panel": str(PRICES),
            "cost_bp_per_side_turnover": COST_BP,
            "grids": infos,
            "vbt_vs_hand_max_pp": float(dv.max()),
            "cells": grid.to_dict(orient="records"),
        }, f, ensure_ascii=False, indent=1)
    print(f"\n落檔:{HERE / 'reversal_sweep.csv'} / results.json / grid_*.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
