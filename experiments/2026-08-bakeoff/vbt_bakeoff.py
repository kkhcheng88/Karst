"""KARST-009:vectorbt 一邊的實作。

策略:每 interval 個月的第一個交易日,按平滑後的因子橫斷面排名選頭 N 隻,
平均分持有,下一個交易日以收市價成交(避免同日前視)。

vectorbt 的表達路徑:自己把「排名 -> 目標權重矩陣」算好,再交給
Portfolio.from_orders(size_type='targetpercent', cash_sharing=True, call_seq='auto')。
排名/選股不是引擎的一等公民,要自己在 numpy 層砌。
"""

from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import vectorbt as vbt

import karst_spec as spec


def load_wide() -> tuple[pd.DataFrame, pd.DataFrame]:
    """把自家長格式面板轉成 vectorbt 要的寬表。這就是「接資料層」要做的適配。"""
    # --- ADAPTER-BEGIN ---
    panel = spec.load_panel()
    close = panel.pivot(index="date", columns="symbol", values="close")
    factor = panel.pivot(index="date", columns="symbol", values="factor")
    close.columns.name = "symbol"
    factor.columns.name = "symbol"
    # --- ADAPTER-END ---
    return close.astype(np.float64), factor.astype(np.float64)


# --- STRATEGY-CORE-BEGIN ---
def target_weights(factor: pd.DataFrame, top_n: int, interval: int, smooth: int) -> np.ndarray:
    """算出目標權重矩陣:換倉日的下一個交易日放權重,其餘為 NaN(不下單)。"""
    fac = spec.smooth_factor(factor, smooth).to_numpy()
    dates = factor.index
    reb = spec.rebalance_dates(dates, interval)
    sig_pos = dates.get_indexer(reb)
    exec_pos = sig_pos + 1
    keep = exec_pos < len(dates)
    sig_pos, exec_pos = sig_pos[keep], exec_pos[keep]

    scores = fac[sig_pos]                                   # (R, K) 訊號日的因子
    rank = np.argsort(np.argsort(-scores, axis=1), axis=1)   # 橫斷面排名,0 = 最高分
    picked = (rank < top_n).astype(np.float64) / top_n       # 頭 N 名平均分

    weights = np.full(fac.shape, np.nan, dtype=np.float64)
    weights[exec_pos] = picked
    return weights


def run_backtest(close: pd.DataFrame, weights: np.ndarray) -> vbt.Portfolio:
    return vbt.Portfolio.from_orders(
        close=close,
        size=weights,
        size_type="targetpercent",
        direction="longonly",
        group_by=True,
        cash_sharing=True,
        call_seq="auto",
        init_cash=spec.INIT_CASH,
        freq="1D",
    )
# --- STRATEGY-CORE-END ---


def run_sweep_batch(close: pd.DataFrame, factor: pd.DataFrame, combos: list[dict]) -> np.ndarray:
    """一次過把 B 組參數塞進同一個 Portfolio 呼叫——vectorbt 的賣點就在這裡。"""
    # --- SWEEP-CORE-BEGIN ---
    blocks = [target_weights(factor, c["top_n"], c["interval"], c["smooth"]) for c in combos]
    big_w = np.concatenate(blocks, axis=1)
    cols = pd.MultiIndex.from_tuples(
        [(i, s) for i in range(len(combos)) for s in close.columns], names=["combo", "symbol"]
    )
    big_close = pd.DataFrame(
        np.tile(close.to_numpy(), (1, len(combos))), index=close.index, columns=cols
    )
    pf = vbt.Portfolio.from_orders(
        close=big_close,
        size=big_w,
        size_type="targetpercent",
        direction="longonly",
        group_by="combo",
        cash_sharing=True,
        call_seq="auto",
        init_cash=spec.INIT_CASH,
        freq="1D",
    )
    return np.asarray(pf.total_return())
    # --- SWEEP-CORE-END ---


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["single", "sweep"], default="single")
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0, help="只跑頭 N 組(0 = 全部 1000)")
    args = ap.parse_args()

    os.makedirs(spec.RESULT_DIR, exist_ok=True)
    t0 = time.perf_counter()
    close, factor = load_wide()
    t_load = time.perf_counter() - t0
    print(f"[vbt] 讀資料+轉寬表 {t_load:.2f}s  shape={close.shape}")

    if args.mode == "single":
        # 冷跑(含 numba JIT 編譯)
        t0 = time.perf_counter()
        w = target_weights(factor, spec.BASE_N, spec.BASE_INTERVAL, spec.BASE_SMOOTH)
        pf = run_backtest(close, w)
        tr = float(pf.total_return())
        cold = time.perf_counter() - t0

        warm = []
        for _ in range(3):
            t0 = time.perf_counter()
            w = target_weights(factor, spec.BASE_N, spec.BASE_INTERVAL, spec.BASE_SMOOTH)
            pf2 = run_backtest(close, w)
            _ = float(pf2.total_return())
            warm.append(time.perf_counter() - t0)

        n_orders = int(np.asarray(pf.orders.count()).sum())
        res = {
            "engine": "vectorbt",
            "version": vbt.__version__,
            "load_sec": t_load,
            "single_cold_sec": cold,
            "single_warm_sec_median": float(np.median(warm)),
            "single_warm_runs": warm,
            "total_return": tr,
            "final_value": float(np.asarray(pf.final_value())),
            "orders": n_orders,
            "params": {"top_n": spec.BASE_N, "interval": spec.BASE_INTERVAL, "smooth": spec.BASE_SMOOTH},
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        with open(os.path.join(spec.RESULT_DIR, "vbt_single.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    else:
        combos = spec.param_grid()
        if args.limit:
            combos = combos[: args.limit]
        # 先熱身,把 numba 編譯成本移出計時
        _ = run_sweep_batch(close, factor, combos[:1])

        t0 = time.perf_counter()
        rets = []
        for i in range(0, len(combos), args.batch):
            rets.append(run_sweep_batch(close, factor, combos[i : i + args.batch]))
            done = min(i + args.batch, len(combos))
            print(f"  [vbt] {done}/{len(combos)}  已用 {time.perf_counter() - t0:.1f}s", flush=True)
        rets = np.concatenate(rets)
        elapsed = time.perf_counter() - t0

        res = {
            "engine": "vectorbt",
            "version": vbt.__version__,
            "n_combos": len(combos),
            "batch": args.batch,
            "sweep_sec": elapsed,
            "sec_per_combo": elapsed / len(combos),
            "best_total_return": float(np.max(rets)),
            "worst_total_return": float(np.min(rets)),
            "best_combo": combos[int(np.argmax(rets))],
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        with open(os.path.join(spec.RESULT_DIR, "vbt_sweep.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        pd.DataFrame(combos).assign(total_return=rets).to_csv(
            os.path.join(spec.RESULT_DIR, "vbt_sweep_returns.csv"), index=False
        )


if __name__ == "__main__":
    main()
