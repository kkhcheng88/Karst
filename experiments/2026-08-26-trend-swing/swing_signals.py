"""KARST-013:路線 A —— 用 vectorbt 現成的 Portfolio.from_signals 表達趨勢波段。

五件規則在這條路線的落點:
  1) 入場      -> from_signals(entries=...)              引擎原生
  2) 止蝕      -> from_signals(sl_stop=...) 逐格百分比陣列  引擎原生
  3) 賠率門檻  -> 入場前先在 numpy 過濾 entries            引擎沒參與(訊號層算完)
  4) 風險定額注碼 -> size=股數陣列, size_type='amount'      引擎原生,但「權益」只能用起始本金
                     (SignalContext 看不到現金/權益,見報告)
  5) 月度熔斷  -> 引擎表達不到;這裡試「引擎外後處理」迭代法,量度代價

用法:
  python swing_signals.py --mode single            # 單次回測(不含熔斷)
  python swing_signals.py --mode breaker           # 單次回測 + 引擎外後處理熔斷
  python swing_signals.py --mode sweep             # N x 賠率門檻 掃描
"""

from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import vectorbt as vbt

import swing_spec as spec


def size_shares(sig: dict, feat: dict, equity_base: float) -> np.ndarray:
    """規則 4:按止蝕距離反推注碼。

    股數 = (權益 x 單筆風險) / (成交價 - 止蝕價),再受單一持倉上限封頂。
    這條路線的「權益」是常數(起始本金)——這正是扭曲點。
    """
    px = spec.exec_price_aligned(feat)
    stop_dist = px - sig["stop_abs"]
    with np.errstate(invalid="ignore", divide="ignore"):
        shares = (equity_base * spec.RISK_PER_TRADE) / stop_dist
        cap = (equity_base * spec.MAX_POS_FRAC) / px
        shares = np.minimum(shares, cap)
    return np.where(sig["entries"] & np.isfinite(shares), shares, np.nan)


def run(close: pd.DataFrame, sig: dict, size: np.ndarray,
        high: pd.DataFrame, low: pd.DataFrame, open_: pd.DataFrame) -> vbt.Portfolio:
    return vbt.Portfolio.from_signals(
        close=close,
        open=open_,
        high=high,
        low=low,
        entries=sig["entries"],
        exits=np.zeros_like(sig["entries"]),   # 只靠止蝕/目標離場
        size=size,
        size_type="amount",
        sl_stop=sig["sl_stop"],                # 規則 2
        tp_stop=sig["tp_stop"],                # 目標
        direction="longonly",
        group_by=True,
        cash_sharing=True,
        call_seq="random",                     # 同日多個突破時公平抽籤(定種子可重跑)
        seed=spec.SEED,
        init_cash=spec.INIT_CASH,
        freq="1D",
    )


def metrics(pf: vbt.Portfolio, extra: dict | None = None) -> dict:
    out = {
        "total_return": float(np.asarray(pf.total_return())),
        "max_drawdown": float(np.asarray(pf.max_drawdown())),
        "sharpe_ratio": float(np.asarray(pf.sharpe_ratio())),
        "n_orders": int(np.asarray(pf.orders.count()).sum()),
        "n_trades": int(np.asarray(pf.trades.count()).sum()),
        "final_value": float(np.asarray(pf.final_value())),
    }
    try:
        out["win_rate"] = float(np.asarray(pf.trades.win_rate()))
    except Exception:
        out["win_rate"] = float("nan")
    if extra:
        out.update(extra)
    return out


def worst_month_dd(value: pd.Series, mid: np.ndarray) -> float:
    """實際出現過的最深月內回撤(用來核實熔斷有沒有咬到東西)。"""
    v = value.to_numpy()
    worst = 0.0
    start_v = v[0]
    for t in range(len(v)):
        if t > 0 and mid[t] != mid[t - 1]:
            start_v = v[t - 1]
        worst = min(worst, v[t] / start_v - 1.0)
    return float(worst)


def apply_breaker_post(close, sig, size, high, low, open_, mid, max_iter=10):
    """規則 5 的替代寫法:引擎外後處理。

    做法:先跑一次 -> 讀組合權益曲線 -> 找出每個月首次觸及 -6% 的那一根 ->
    把該根之後、同月之內的入場訊號抹掉 -> 再跑。抹掉入場會改變權益曲線本身,
    所以要迭代到遮罩不再變。這裡量度的正是「引擎外做熔斷」的真實代價。
    """
    entries0 = sig["entries"]
    mask = np.ones_like(entries0, dtype=np.bool_)
    hist = []
    for it in range(max_iter):
        s = dict(sig)
        s["entries"] = entries0 & mask
        s["sl_stop"] = np.where(s["entries"], sig["sl_stop"], np.nan)
        s["tp_stop"] = np.where(s["entries"], sig["tp_stop"], np.nan)
        sz = np.where(s["entries"], size, np.nan)
        t0 = time.perf_counter()
        pf = run(close, s, sz, high, low, open_)
        value = pf.value()
        el = time.perf_counter() - t0

        v = np.asarray(value)
        blocked = np.zeros(len(v), dtype=np.bool_)
        start_v = v[0]
        halted = False
        for t in range(len(v)):
            if t > 0 and mid[t] != mid[t - 1]:
                start_v = v[t - 1]
                halted = False
            if halted:
                blocked[t] = True
            elif v[t] / start_v - 1.0 <= -spec.BREAKER_DD:
                halted = True          # 觸發當日之後(含次根)停止新入場
        new_mask = ~np.broadcast_to(blocked[:, None], entries0.shape)
        changed = int((new_mask != mask).sum())
        hist.append({
            "iter": it, "sec": el, "blocked_bars": int(blocked.sum()),
            "mask_cells_changed": changed,
            "total_return": float(np.asarray(pf.total_return())),
        })
        mask = new_mask
        if changed == 0:
            break
    return pf, mask, hist


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["single", "breaker", "sweep"], default="single")
    args = ap.parse_args()
    os.makedirs(spec.RESULT_DIR, exist_ok=True)

    t0 = time.perf_counter()
    wide = spec.load_wide()
    feat = spec.build_features(wide)
    t_load = time.perf_counter() - t0
    close, high, low, open_ = wide["close"], wide["high"], wide["low"], wide["open"]
    mid = spec.month_id(close.index)
    print(f"[A/from_signals] 讀資料+特徵 {t_load:.2f}s shape={close.shape}", flush=True)

    if args.mode in ("single", "breaker"):
        ph, pl = spec.rolling_range(wide, spec.BASE_N)
        sig = spec.build_signals(feat, ph, pl, spec.BASE_RR)
        size = size_shares(sig, feat, spec.INIT_CASH)

        t0 = time.perf_counter()
        pf = run(close, sig, size, high, low, open_)
        _ = float(np.asarray(pf.total_return()))
        cold = time.perf_counter() - t0

        warm = []
        for _ in range(3):
            t0 = time.perf_counter()
            pf = run(close, sig, size, high, low, open_)
            _ = float(np.asarray(pf.total_return()))
            warm.append(time.perf_counter() - t0)

        res = metrics(pf, {
            "engine_path": "from_signals",
            "vbt_version": vbt.__version__,
            "load_sec": t_load,
            "single_cold_sec": cold,
            "single_warm_sec_median": float(np.median(warm)),
            "n_entry_signals": sig["n_signals"],
            "worst_month_dd": worst_month_dd(pf.value(), mid),
            "params": {"n_break": spec.BASE_N, "rr_min": spec.BASE_RR},
            "breaker": "off",
        })
        name = "A_from_signals_single.json"

        if args.mode == "breaker":
            t0 = time.perf_counter()
            pf_b, mask, hist = apply_breaker_post(
                close, sig, size, high, low, open_, mid)
            total = time.perf_counter() - t0
            res = metrics(pf_b, {
                "engine_path": "from_signals + 引擎外後處理熔斷",
                "vbt_version": vbt.__version__,
                "breaker": "post-processing",
                "breaker_total_sec": total,
                "breaker_iters": len(hist),
                "breaker_history": hist,
                "converged": hist[-1]["mask_cells_changed"] == 0,
                "worst_month_dd": worst_month_dd(pf_b.value(), mid),
                "params": {"n_break": spec.BASE_N, "rr_min": spec.BASE_RR},
            })
            name = "A_from_signals_breaker.json"

        print(json.dumps(res, ensure_ascii=False, indent=2))
        with open(os.path.join(spec.RESULT_DIR, name), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    else:
        combos = spec.param_grid()
        # 熱身,把 numba 編譯移出計時
        ph, pl = spec.rolling_range(wide, spec.BASE_N)
        s0 = spec.build_signals(feat, ph, pl, spec.BASE_RR)
        _ = run(close, s0, size_shares(s0, feat, spec.INIT_CASH), high, low, open_)

        rows = []
        t_all = time.perf_counter()
        ph_cache: dict[int, tuple] = {}
        for k, c in enumerate(combos):
            if c["n_break"] not in ph_cache:
                ph_cache[c["n_break"]] = spec.rolling_range(wide, c["n_break"])
            t0 = time.perf_counter()
            ph, pl = ph_cache[c["n_break"]]
            sig = spec.build_signals(feat, ph, pl, c["rr_min"])
            size = size_shares(sig, feat, spec.INIT_CASH)
            pf = run(close, sig, size, high, low, open_)
            m = metrics(pf)
            m.update(c)
            m["sec"] = time.perf_counter() - t0
            m["n_entry_signals"] = sig["n_signals"]
            rows.append(m)
            if (k + 1) % 12 == 0:
                print(f"  [A] {k+1}/{len(combos)} 已用 {time.perf_counter()-t_all:.1f}s",
                      flush=True)
        elapsed = time.perf_counter() - t_all
        df = pd.DataFrame(rows)
        df.to_csv(os.path.join(spec.RESULT_DIR, "A_sweep.csv"), index=False)
        summary = {
            "engine_path": "from_signals",
            "n_combos": len(combos),
            "sweep_sec": elapsed,
            "sec_per_combo": elapsed / len(combos),
            "grid_n": spec.GRID_N,
            "grid_rr": spec.GRID_RR,
            "best": df.loc[df["total_return"].idxmax()].to_dict(),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        with open(os.path.join(spec.RESULT_DIR, "A_sweep.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)


if __name__ == "__main__":
    main()
