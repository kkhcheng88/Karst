"""KARST-013:把 N x 賠率門檻 掃描結果畫成穩健平原視圖(D-016 第 3 條)。

判準不是單點最優,而是「最優參數的鄰域表現皆佳」。所以除了原始格,
另畫一張 3x3 鄰域平均圖:平原會保持亮,孤峰會在鄰域圖裡塌下去。

輸出:results/sweep-2026-08-26-trend-swing.png 與 results/robustness.json
用法:python sweep_view.py [--src B_sweep_breaker-on.csv]
"""

from __future__ import annotations

import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import swing_spec as spec

# Windows 上的繁中字型;找不到就退回英文標籤也不會爆
for cand in ("Microsoft JhengHei", "Microsoft YaHei", "SimHei"):
    if any(cand.lower() in f.name.lower()
           for f in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False


MIN_TRADES = 30   # 成交太少的格不算數:報酬率沒有統計意義,夏普會變成無限大


def grid_of(df: pd.DataFrame, col: str, mask_thin: bool = True) -> np.ndarray:
    """(賠率門檻 x N) 的矩陣,行 = RR,列 = N。成交太少的格一律當 NaN。"""
    d = df.copy()
    if mask_thin:
        d.loc[d["n_trades"] < MIN_TRADES, col] = np.nan
    p = d.pivot(index="rr_min", columns="n_break", values=col)
    g = p.reindex(index=spec.GRID_RR, columns=spec.GRID_N).to_numpy().astype(float)
    return np.where(np.isfinite(g), g, np.nan)


def neighbourhood_mean(g: np.ndarray) -> np.ndarray:
    """3x3 鄰域平均(邊緣用可得的鄰居),即「平原度」。"""
    out = np.full_like(g, np.nan)
    R, C = g.shape
    for r in range(R):
        for c in range(C):
            blk = g[max(0, r - 1):r + 2, max(0, c - 1):c + 2]
            out[r, c] = np.nanmean(blk)
    return out


def draw(ax, g, title, cbar_label, fmt="{:.2f}"):
    im = ax.imshow(g, origin="lower", aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(spec.GRID_N)), [str(n) for n in spec.GRID_N], fontsize=8)
    ax.set_yticks(range(len(spec.GRID_RR)), [str(r) for r in spec.GRID_RR], fontsize=8)
    ax.set_xlabel("N(突破日數)")
    ax.set_ylabel("賠率門檻")
    ax.set_title(title, fontsize=11)
    for r in range(g.shape[0]):
        for c in range(g.shape[1]):
            v = g[r, c]
            if np.isfinite(v):
                ax.text(c, r, fmt.format(v), ha="center", va="center", fontsize=5.5,
                        color="white" if v < np.nanpercentile(g, 60) else "black")
    plt.colorbar(im, ax=ax, label=cbar_label)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="B_sweep_breaker-on.csv")
    args = ap.parse_args()

    path = os.path.join(spec.RESULT_DIR, args.src)
    df = pd.read_csv(path)

    sharpe = grid_of(df, "sharpe_ratio")
    ret = grid_of(df, "total_return")
    trades = grid_of(df, "n_trades", mask_thin=False)
    nbr = neighbourhood_mean(sharpe)

    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    draw(axes[0, 0], sharpe, "夏普比率(原始格)", "Sharpe")
    draw(axes[0, 1], nbr, "夏普比率(3x3 鄰域平均)= 穩健平原視圖", "Sharpe(鄰域)")
    draw(axes[1, 0], ret, "十年總報酬(倍)", "total return", fmt="{:.1f}")
    draw(axes[1, 1], trades, "成交筆數", "trades", fmt="{:.0f}")

    # 標出單點最優 vs 鄰域最優
    ri, ci = np.unravel_index(np.nanargmax(sharpe), sharpe.shape)
    rn, cn = np.unravel_index(np.nanargmax(nbr), nbr.shape)
    axes[0, 0].plot(ci, ri, "r*", ms=16, mec="k")
    axes[0, 1].plot(cn, rn, "r*", ms=16, mec="k")

    fig.suptitle(
        "KARST-013 趨勢波段玩具版:N x 賠率門檻 參數掃描"
        f"(500 股 x 2608 個交易日,{len(df)} 組,vectorbt from_order_func,五件規則全開)",
        fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    png = os.path.join(spec.RESULT_DIR, "sweep-2026-08-26-trend-swing.png")
    fig.savefig(png, dpi=130)
    print("寫出", png)

    peak_sharpe = float(sharpe[ri, ci])
    peak_nbr = float(nbr[ri, ci])
    info = {
        "source_csv": args.src,
        "n_combos": int(len(df)),
        "min_trades_filter": MIN_TRADES,
        "cells_dropped_thin": int((df["n_trades"] < MIN_TRADES).sum()),
        "best_single": {
            "n_break": spec.GRID_N[ci], "rr_min": spec.GRID_RR[ri],
            "sharpe": peak_sharpe, "neighbourhood_sharpe": peak_nbr,
            "peak_over_neighbourhood": peak_sharpe / peak_nbr if peak_nbr else None,
        },
        "best_plateau": {
            "n_break": spec.GRID_N[cn], "rr_min": spec.GRID_RR[rn],
            "neighbourhood_sharpe": float(nbr[rn, cn]),
            "sharpe": float(sharpe[rn, cn]),
        },
        "sharpe_range": [float(np.nanmin(sharpe)), float(np.nanmax(sharpe))],
        "png": os.path.basename(png),
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))
    with open(os.path.join(spec.RESULT_DIR, "robustness.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
