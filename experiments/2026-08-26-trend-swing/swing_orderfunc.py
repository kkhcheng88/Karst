"""KARST-013:路線 B —— 用 Portfolio.from_order_func 把五件規則全部照原意表達。

與路線 A 的分別只有兩處,但都是要害:
  - 注碼的「權益」是**當下權益**(c.value_now),不是起始本金
  - 月度熔斷在**模擬之內**判定(pre_segment_func_nb 讀得到組合現金與持倉),
    一次過跑完,不需要迭代

代價:from_order_func 沒有內建 sl_stop / tp_stop,止蝕與目標要自己逐根 bar 手寫,
連成交價的擺位(跳空穿價時以開市價成交)都要自己處理。本檔的 order_func_nb 就是那筆代價。

用法:
  python swing_orderfunc.py --mode single [--breaker on|off]
  python swing_orderfunc.py --mode sweep  [--breaker on|off]
"""

from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import vectorbt as vbt
from numba import njit
from vectorbt.portfolio.enums import Direction, NoOrder, SizeType
from vectorbt.portfolio.nb import order_nb

import swing_spec as spec

# state 陣列的欄位(每組一份):
S_MONTH_START = 0   # 本月起點權益
S_BLOCKED = 1       # 本月已熔斷?(1.0 = 停止新入場)
S_PREV_EQ = 2       # 上一根 bar 的權益
S_BLOCK_BARS = 3    # 累計被熔斷封鎖的 bar 數(統計用)


@njit(cache=True)
def pre_segment_func_nb(c, close, mid, state, breaker_dd):
    """規則 5:組合層月度虧損熔斷——只有在這一層才看得見組合權益。"""
    i = c.i
    g = c.group

    # 先把估值價更新為今日收市,令引擎之後算的 value_now 反映今日權益
    for col in range(c.from_col, c.to_col):
        c.last_val_price[col] = close[i, col]

    # last_value 要等本函式回傳之後才由引擎更新,所以自己按今日收市算一次
    eq = c.last_cash[g]
    for col in range(c.from_col, c.to_col):
        p = c.last_position[col]
        if p != 0.0:
            eq += p * close[i, col]

    if i == 0:
        state[S_MONTH_START] = eq
        state[S_BLOCKED] = 0.0
    elif mid[i] != mid[i - 1]:
        state[S_MONTH_START] = state[S_PREV_EQ]   # 本月起點 = 上月最後一根的權益
        state[S_BLOCKED] = 0.0

    if state[S_BLOCKED] == 0.0 and state[S_MONTH_START] > 0.0:
        if eq / state[S_MONTH_START] - 1.0 <= -breaker_dd:
            state[S_BLOCKED] = 1.0

    state[S_PREV_EQ] = eq
    if state[S_BLOCKED] == 1.0:
        state[S_BLOCK_BARS] += 1.0
    return ()


@njit(cache=True)
def order_func_nb(c, open_, high, low, close, entries, stop_abs, tgt_abs,
                  pos_stop, pos_tgt, state, risk_per_trade, max_pos_frac, equity_base):
    i, col = c.i, c.col
    pos = c.position_now

    if pos > 0.0:
        # --- 手寫離場:止蝕優先,再看目標。跳空穿價時以開市價成交 ---
        st = pos_stop[col]
        tg = pos_tgt[col]
        o = open_[i, col]
        if st == st and low[i, col] <= st:            # st == st 即非 NaN
            px = o if o <= st else st
            pos_stop[col] = np.nan
            pos_tgt[col] = np.nan
            return order_nb(size=-pos, price=px, size_type=SizeType.Amount,
                            direction=Direction.LongOnly)
        if tg == tg and high[i, col] >= tg:
            px = o if o >= tg else tg
            pos_stop[col] = np.nan
            pos_tgt[col] = np.nan
            return order_nb(size=-pos, price=px, size_type=SizeType.Amount,
                            direction=Direction.LongOnly)
        return NoOrder

    # --- 入場:規則 1/2/3 已在訊號層過濾好,這裡做規則 4 與規則 5 ---
    if not entries[i, col]:
        return NoOrder
    if state[S_BLOCKED] == 1.0:                        # 規則 5:本月已熔斷
        return NoOrder

    px = close[i, col]
    sd = px - stop_abs[i, col]
    if not (sd > 0.0):
        return NoOrder

    # 規則 4:預設用當下權益;equity_base > 0 時改用固定基數(對照臂,用來重現路線 A)
    v = c.value_now if equity_base <= 0.0 else equity_base
    shares = risk_per_trade * v / sd
    cap = max_pos_frac * v / px
    if shares > cap:
        shares = cap
    if not (shares > 0.0):
        return NoOrder

    pos_stop[col] = stop_abs[i, col]
    pos_tgt[col] = tgt_abs[i, col]
    return order_nb(size=shares, price=px, size_type=SizeType.Amount,
                    direction=Direction.LongOnly)


def run(close, open_, high, low, sig, mid, breaker_on: bool,
        equity_base: float = 0.0) -> tuple[vbt.Portfolio, np.ndarray]:
    T, K = close.shape
    pos_stop = np.full(K, np.nan)
    pos_tgt = np.full(K, np.nan)
    state = np.zeros(4)
    dd = spec.BREAKER_DD if breaker_on else 1e9        # 關掉熔斷 = 門檻推到無限遠

    pf = vbt.Portfolio.from_order_func(
        close,
        order_func_nb,
        open_.to_numpy(), high.to_numpy(), low.to_numpy(), close.to_numpy(),
        sig["entries"], sig["stop_abs"], sig["tgt_abs"],
        pos_stop, pos_tgt, state,
        spec.RISK_PER_TRADE, spec.MAX_POS_FRAC, equity_base,
        pre_segment_func_nb=pre_segment_func_nb,
        pre_segment_args=(close.to_numpy(), mid, state, dd),
        group_by=True,
        cash_sharing=True,
        call_seq="random",
        seed=spec.SEED,
        init_cash=spec.INIT_CASH,
        freq="1D",
    )
    return pf, state


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
    v = value.to_numpy()
    worst, start_v = 0.0, v[0]
    for t in range(len(v)):
        if t > 0 and mid[t] != mid[t - 1]:
            start_v = v[t - 1]
        worst = min(worst, v[t] / start_v - 1.0)
    return float(worst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["single", "sweep"], default="single")
    ap.add_argument("--breaker", choices=["on", "off"], default="on")
    ap.add_argument("--sizebase", choices=["equity", "init"], default="equity",
                    help="equity=當下權益(原意);init=起始本金(對照臂,重現路線 A 的扭曲)")
    args = ap.parse_args()
    breaker_on = args.breaker == "on"
    eq_base = spec.INIT_CASH if args.sizebase == "init" else 0.0
    os.makedirs(spec.RESULT_DIR, exist_ok=True)

    t0 = time.perf_counter()
    wide = spec.load_wide()
    feat = spec.build_features(wide)
    t_load = time.perf_counter() - t0
    close, high, low, open_ = wide["close"], wide["high"], wide["low"], wide["open"]
    mid = spec.month_id(close.index)
    print(f"[B/from_order_func] 讀資料+特徵 {t_load:.2f}s shape={close.shape}", flush=True)

    if args.mode == "single":
        ph, pl = spec.rolling_range(wide, spec.BASE_N)
        sig = spec.build_signals(feat, ph, pl, spec.BASE_RR)

        t0 = time.perf_counter()
        pf, st = run(close, open_, high, low, sig, mid, breaker_on, eq_base)
        _ = float(np.asarray(pf.total_return()))
        cold = time.perf_counter() - t0

        warm = []
        for _ in range(3):
            t0 = time.perf_counter()
            pf, st = run(close, open_, high, low, sig, mid, breaker_on, eq_base)
            _ = float(np.asarray(pf.total_return()))
            warm.append(time.perf_counter() - t0)

        res = metrics(pf, {
            "engine_path": "from_order_func",
            "vbt_version": vbt.__version__,
            "breaker": args.breaker,
            "size_base": args.sizebase,
            "load_sec": t_load,
            "single_cold_sec": cold,
            "single_warm_sec_median": float(np.median(warm)),
            "n_entry_signals": sig["n_signals"],
            "breaker_blocked_bars": int(st[S_BLOCK_BARS]),
            "worst_month_dd": worst_month_dd(pf.value(), mid),
            "params": {"n_break": spec.BASE_N, "rr_min": spec.BASE_RR},
        })
        print(json.dumps(res, ensure_ascii=False, indent=2))
        name = f"B_from_order_func_single_breaker-{args.breaker}_size-{args.sizebase}.json"
        with open(os.path.join(spec.RESULT_DIR, name), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    else:
        combos = spec.param_grid()
        ph, pl = spec.rolling_range(wide, spec.BASE_N)
        s0 = spec.build_signals(feat, ph, pl, spec.BASE_RR)
        _ = run(close, open_, high, low, s0, mid, breaker_on, eq_base)   # 熱身

        rows = []
        cache: dict[int, tuple] = {}
        t_all = time.perf_counter()
        for k, c in enumerate(combos):
            if c["n_break"] not in cache:
                cache[c["n_break"]] = spec.rolling_range(wide, c["n_break"])
            t0 = time.perf_counter()
            p_h, p_l = cache[c["n_break"]]
            sig = spec.build_signals(feat, p_h, p_l, c["rr_min"])
            pf, st = run(close, open_, high, low, sig, mid, breaker_on, eq_base)
            m = metrics(pf)
            m.update(c)
            m["sec"] = time.perf_counter() - t0
            m["n_entry_signals"] = sig["n_signals"]
            m["breaker_blocked_bars"] = int(st[S_BLOCK_BARS])
            m["worst_month_dd"] = worst_month_dd(pf.value(), mid)
            rows.append(m)
            if (k + 1) % 12 == 0:
                print(f"  [B] {k+1}/{len(combos)} 已用 {time.perf_counter()-t_all:.1f}s",
                      flush=True)
        elapsed = time.perf_counter() - t_all
        df = pd.DataFrame(rows)
        tag = args.breaker
        df.to_csv(os.path.join(spec.RESULT_DIR, f"B_sweep_breaker-{tag}.csv"), index=False)
        summary = {
            "engine_path": "from_order_func",
            "breaker": tag,
            "n_combos": len(combos),
            "sweep_sec": elapsed,
            "sec_per_combo": elapsed / len(combos),
            "grid_n": spec.GRID_N,
            "grid_rr": spec.GRID_RR,
            "best": df.loc[df["total_return"].idxmax()].to_dict(),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        with open(os.path.join(spec.RESULT_DIR, f"B_sweep_breaker-{tag}.json"),
                  "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)


if __name__ == "__main__":
    main()
