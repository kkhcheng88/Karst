"""KARST-009:PyBroker 一邊的實作。

同一條考題:每 interval 個月按平滑後的因子橫斷面排名選頭 N 隻,平均分,
下一個交易日以收市價成交。

PyBroker 的表達路徑:把分數寫入 ctx.long_score,排名、持倉名額、換入換出、
平均分注碼全部由引擎的 rotation 機制處理。選股排名在這裡是一等公民。
"""

from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import pybroker as pb

import karst_spec as spec

# 由 main() 填入的執行期參數(PyBroker 的 exec 函式是每股票每根 bar 呼叫一次)
SMOOTH = spec.BASE_SMOOTH
LAST_REB = np.zeros(1, dtype=np.int64)


def build_last_reb(dates: pd.DatetimeIndex, interval: int) -> np.ndarray:
    """每根 bar 對應「最近一個已發生的換倉日」的索引——分數在換倉之間保持不變,
    排名就不會在月中變動,等於每 interval 個月才換倉一次。"""
    reb = spec.rebalance_dates(dates, interval)
    pos = dates.get_indexer(reb)
    out = np.zeros(len(dates), dtype=np.int64)
    for p in pos:
        out[p:] = p
    return out


# --- STRATEGY-CORE-BEGIN ---
def exec_fn(ctx) -> None:
    j = LAST_REB[ctx.bars - 1]                      # 最近一個換倉日
    f = ctx.factor                                   # 自家因子欄,history array
    ctx.long_score = float(f[max(0, j - SMOOTH + 1) : j + 1].mean())
    ctx.buy_fill_price = pb.PriceType.CLOSE
    ctx.sell_fill_price = pb.PriceType.CLOSE


def build_strategy(panel: pd.DataFrame, top_n: int) -> pb.Strategy:
    config = pb.StrategyConfig(
        initial_cash=spec.INIT_CASH,
        enable_fractional_shares=True,
        max_long_positions=top_n,
        buy_delay=1,
        sell_delay=1,
    )
    strategy = pb.Strategy(panel, spec.START, spec.END, config)
    strategy.add_execution(exec_fn, spec.SYMBOLS)
    strategy.enable_rotation(worst_rank_held=top_n)   # 排名跌出頭 N 名就換走
    return strategy
# --- STRATEGY-CORE-END ---


def load_panel_for_pb(limit_symbols: int = 0) -> pd.DataFrame:
    """接自家資料層:PyBroker 直接吃長格式 (date, symbol, OHLCV, 自訂欄)。"""
    # --- ADAPTER-BEGIN ---
    panel = spec.load_panel()
    pb.register_columns("factor")
    # --- ADAPTER-END ---
    if limit_symbols:
        keep = set(spec.SYMBOLS[:limit_symbols])
        panel = panel[panel["symbol"].isin(keep)].reset_index(drop=True)
    return panel


def run_one(panel: pd.DataFrame, top_n: int, interval: int, smooth: int, dates) -> tuple[float, float]:
    global SMOOTH, LAST_REB
    SMOOTH = smooth
    LAST_REB = build_last_reb(dates, interval)
    t0 = time.perf_counter()
    strategy = build_strategy(panel, top_n)
    result = strategy.backtest(calc_bootstrap=False)
    elapsed = time.perf_counter() - t0
    end_value = float(result.portfolio["equity"].iloc[-1])
    return end_value / spec.INIT_CASH - 1.0, elapsed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["smoke", "single", "sweep"], default="single")
    ap.add_argument("--limit", type=int, default=0, help="sweep 只跑頭 N 組")
    args = ap.parse_args()

    os.makedirs(spec.RESULT_DIR, exist_ok=True)
    pb.disable_progress_bar()

    n_syms = 50 if args.mode == "smoke" else 0
    t0 = time.perf_counter()
    panel = load_panel_for_pb(n_syms)
    t_load = time.perf_counter() - t0
    dates = pd.DatetimeIndex(np.sort(panel["date"].unique()))
    print(f"[pb] 讀資料 {t_load:.2f}s  rows={len(panel)} syms={panel['symbol'].nunique()} days={len(dates)}")

    if args.mode == "smoke":
        global SMOOTH, LAST_REB
        SMOOTH = 1
        LAST_REB = build_last_reb(dates, 1)
        syms = spec.SYMBOLS[:n_syms]
        cfg = pb.StrategyConfig(
            initial_cash=spec.INIT_CASH, enable_fractional_shares=True,
            max_long_positions=5, buy_delay=1, sell_delay=1)
        st = pb.Strategy(panel, spec.START, spec.END, cfg)
        st.add_execution(exec_fn, syms)
        st.enable_rotation(worst_rank_held=5)
        t0 = time.perf_counter()
        r = st.backtest(calc_bootstrap=False)
        print(f"[pb] smoke 完成 {time.perf_counter() - t0:.2f}s")
        print("portfolio cols:", list(r.portfolio.columns))
        print("末值:", float(r.portfolio['market_value'].iloc[-1]))
        print("orders:", len(r.orders))
        return

    if args.mode == "single":
        tr_cold, cold = run_one(panel, spec.BASE_N, spec.BASE_INTERVAL, spec.BASE_SMOOTH, dates)
        warm = []
        for _ in range(2):
            tr, el = run_one(panel, spec.BASE_N, spec.BASE_INTERVAL, spec.BASE_SMOOTH, dates)
            warm.append(el)
        res = {
            "engine": "pybroker",
            "version": pb.__version__ if hasattr(pb, "__version__") else "2.0.0",
            "load_sec": t_load,
            "single_cold_sec": cold,
            "single_warm_sec_median": float(np.median(warm)),
            "single_warm_runs": warm,
            "total_return": tr_cold,
            "final_value": spec.INIT_CASH * (1 + tr_cold),
            "params": {"top_n": spec.BASE_N, "interval": spec.BASE_INTERVAL, "smooth": spec.BASE_SMOOTH},
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        with open(os.path.join(spec.RESULT_DIR, "pb_single.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    else:
        combos = spec.param_grid()
        if args.limit:
            step = max(1, len(combos) // args.limit)
            combos = combos[::step][: args.limit]
        rows = []
        t0 = time.perf_counter()
        for k, c in enumerate(combos, 1):
            tr, el = run_one(panel, c["top_n"], c["interval"], c["smooth"], dates)
            rows.append({**c, "total_return": tr, "sec": el})
            print(f"  [pb] {k}/{len(combos)} {c} -> {el:.2f}s", flush=True)
        elapsed = time.perf_counter() - t0
        secs = [r["sec"] for r in rows]
        res = {
            "engine": "pybroker",
            "n_combos_measured": len(combos),
            "measured_sec_total": elapsed,
            "sec_per_combo_median": float(np.median(secs)),
            "sec_per_combo_mean": float(np.mean(secs)),
            "extrapolated_1000_sec": float(np.mean(secs)) * 1000,
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        with open(os.path.join(spec.RESULT_DIR, "pb_sweep.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        pd.DataFrame(rows).to_csv(os.path.join(spec.RESULT_DIR, "pb_sweep_returns.csv"), index=False)


if __name__ == "__main__":
    main()
