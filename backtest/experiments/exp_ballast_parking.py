"""Experiment: ballast parking — when the 200SMA trend gate says "exit SPY", is a
DEFENSIVE-SECTOR basket (XLP/XLU/XLV equal-weight) a viable "pseudo-cash" parking
spot for a full-risk-portfolio design (no cash/T-bills/SPY-spot allowed to sit
idle), or does it just add drag/whipsaw exposure vs plain cash?

Background
----------
Main-agent design constraint: the eventual portfolio must stay 100% deployed in
non-zero-beta assets at all times (no cash/T-bills/SPY-spot parking sleeve). The
open question is what happens on the days the 200SMA trend gate says "get out of
SPY" — there is nowhere to go but into SOME other asset. This script tests
whether XLP/XLU/XLV (classic low-beta defensive sectors) is a survivable
substitute for cash during those gated-out windows, and quantifies the price of
holding that same defensive basket permanently (the "ballast rent" a LEAP delta
sleeve would need to offset in bull regimes).

Question
--------
(1) Does parking in XLP/XLU/XLV equal-weight during 200SMA-gated-out episodes
    beat parking in cash (^IRX), specifically in bear/stress windows (2008,
    2020, 2022) — the increment W3-W2? (2) What is the annualized drag of
    holding 100% XLP/XLU/XLV instead of SPY during the periods SPY is ABOVE its
    own 200SMA (the "bull-market rent" a compensating sleeve would need to make
    up) — W4 vs W1 restricted to SPY-bull days?

Method (mirror / increment / horizon)
------
Mirror     : single ONE-asset-at-a-time warehouse (100% of NAV always in exactly
             one holding) — no LEAP sleeve, no options, no fractional cash
             buffer. Same style of isolation as `exp_crash_switch.py`'s
             base-holding-only mirror, but here the SWITCH direction is
             SPY <-> {cash, defensive basket} gated by SPY's own 200SMA trend
             signal (not a drawdown/recovery trigger on the alternate asset).
Increment  : the alternate "parking" leg is the ONLY thing that varies across
             W2 (cash) vs W3 (defensive basket) — identical gate, identical
             cost model, identical SPY leg — so W3-W2 isolates "what you park
             in", nothing else. W1/W4 are the two STATIC long-only anchors
             (100% SPY, 100% defensive basket) that bound the comparison.
Horizon    : continuous multi-year program, daily-observed gate.

Warehouses (pre-registered, no parameter search — the defensive basket weights
are FIXED equal-weight, not optimized; the gate is the repo's standard 200SMA
close-vs-SMA rule, not tuned here)
------
  W1  100% SPY buy-and-hold (base case / benchmark for Jensen alpha).
  W2  SPY when gate=ON, else 100% cash (^IRX daily accrual) — classic gated
      exit-to-cash.
  W3  SPY when gate=ON, else 100% XLP/XLU/XLV equal-weight (daily-rebalanced
      composite return) — the "pseudo-cash" design under test.
  W4  100% XLP/XLU/XLV equal-weight buy-and-hold (long-only comparator: what
      the defensive basket does on its own, unconditionally).
Gate: SPY close > SPY's own 200-day SMA, computed on RAW (non-total-return)
close, signal at close T -> position active from T+1 (repo's usual convention,
`gate = above.shift(1)`, NOT `exp_crash_switch.py`'s extra-lag "T+1 signal ->
T+2 execution" variant — this study uses the standard 1-day shift).
Cost: 10bps/side (per this study's spec), so a full switch (sell old leg + buy
new leg) = 20bps of NAV, charged as a one-time NAV haircut on the bar the gate
flips. W2 and W3 share the identical gate, so they incur IDENTICAL switch
timing/count — the cost cancels out of the W3-W2 episode-level comparison
(both pay the same 20bps in/out), isolating the "what asset earns the return
while parked" question cleanly.
HK tax: all four legs' returns are HK-net total return, `r_net = r_adj -
0.30*dy` (dy = dividend-yield-per-day reconstructed from adjusted-vs-raw close
divergence, 1bp/day threshold to kill adjustment rounding noise) — the SAME
formula used throughout this repo (`exp_leap_real_sweep.build_underlying`,
`exp_crash_switch.build_core_only`), NOT re-derived here. This matters most for
XLP/XLU/XLV (defensive sectors carry materially higher dividend yields than
SPY) — un-netted dividends would overstate exactly the "pseudo-cash" case this
study is testing.
Basket construction: XLP/XLU/XLV equal-weight, DAILY-rebalanced composite
return (basket_r_net[t] = mean of the three legs' own r_net[t]) — a modeling
simplification (real execution would not literally rebalance daily); no
internal rebalancing cost is charged inside the basket itself (only the
switch cost of entering/exiting the basket AS A WHOLE is charged, at the gate
transition). Equal-weight is FIXED per this study's spec, not optimized.

Windows: FULL (native start of the 3-way XLP/XLU/XLV/SPY/^IRX common window,
~1999+) + two halves split at 2012-01-01 (H1 / H2) + three stress windows
(calendar years 2008 / 2020 / 2022).

Special readouts (pre-registered, the actual point of this study)
------
(a) W3-W2 increment in bear windows: for every 200SMA gated-out EPISODE
    (contiguous run of gate=OFF) that overlaps a stress window, compute the
    basket's compounded return over the episode MINUS cash's compounded
    return over the identical date range (raw returns, cost-neutral per the
    Method note above) — then average this excess across all qualifying
    episodes. This is the core "is defensive parking worth it during a
    downturn" number.
(b) W4 bull-market rent: restrict to days SPY's OWN gate says ON (SPY>200SMA),
    compute the annualized (geometric, compounded-then-annualized-by-day-count)
    return of the defensive basket vs SPY over exactly those days — the gap is
    the annual "rent" a compensating LEAP-delta sleeve would need to earn back.

Cross-foot (hard asserts): NAV > 0 every bar of every simulation; every
gated-out episode is either closed (paired in/out) or explicitly flagged
"open at end of sample" — no orphaned episodes.

Run:  PYTHONUTF8=1 python backtest/experiments/exp_ballast_parking.py
Writes: backtest/results/2026-07-12_ballast_parking_ab.md
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import metrics                                     # noqa: E402
from data import load                              # noqa: E402

TD = 252
SMA_WIN = 200
COST_SIDE = 0.0010          # 10bps/side -> 20bps per full switch (this study's spec)
DEFENSIVE = ["XLP", "XLU", "XLV"]
WINDOW_START = pd.Timestamp("1999-01-01")

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-12_ballast_parking_ab.md")

ASSERT_N = {"n": 0}


# ---------------------------------------------------------------------------
# Data — HK-net total-return series (r_net), repo-standard formula, reproduced
# locally (this study needs no options engine, no import from that cluster).
# ---------------------------------------------------------------------------

def build_core_only(symbol: str):
    raw = load(symbol)
    adj = load(symbol, adjusted=True)
    prov = [(symbol, raw.attrs.get("source", "?"), len(raw),
             str(raw.index.min().date()), str(raw.index.max().date())),
            (f"{symbol}(adj)", adj.attrs.get("source", "?"), len(adj),
             str(adj.index.min().date()), str(adj.index.max().date()))]
    close = raw["close"]
    r_adj = adj["close"].pct_change()
    r_raw = close.pct_change()
    dy = (r_adj - r_raw).clip(lower=0.0)
    dy = dy.where(dy > 1e-4, 0.0)          # 1bp threshold: kill adjustment rounding noise
    r_net = r_adj - 0.30 * dy              # HK 30% withholding on dividends
    df = pd.DataFrame({"close": close, "r_net": r_net}).dropna()
    return df, prov


# ---------------------------------------------------------------------------
# Gate — SPY close vs its OWN 200SMA (raw price), T+1-execution shift(1),
# repo's usual convention (NOT exp_crash_switch's extra-lag variant).
# ---------------------------------------------------------------------------

def build_gate(spy_raw_close: pd.Series) -> pd.Series:
    sma = spy_raw_close.rolling(SMA_WIN, min_periods=SMA_WIN).mean()
    above = (spy_raw_close > sma)
    return above.shift(1).fillna(False).astype(bool)


# ---------------------------------------------------------------------------
# Switch simulator — 100% NAV always in leg A (gate=True) or leg B (gate=False),
# 20bps NAV haircut on the bar the gate flips.
# ---------------------------------------------------------------------------

def simulate_gated(gate: np.ndarray, ret_a: np.ndarray, ret_b: np.ndarray,
                   cost_side: float) -> tuple[np.ndarray, int]:
    n = len(gate)
    nav = np.empty(n)
    nav[0] = 1.0
    switches = 0
    for i in range(1, n):
        r = ret_a[i] if gate[i] else ret_b[i]
        nav[i] = nav[i - 1] * (1.0 + r)
        if gate[i] != gate[i - 1]:
            nav[i] *= (1.0 - 2.0 * cost_side)
            switches += 1
        assert nav[i] > 0, f"non-positive NAV at bar {i}"
        ASSERT_N["n"] += 1
    return nav, switches


def buyhold_nav(ret: np.ndarray) -> np.ndarray:
    n = len(ret)
    nav = np.empty(n)
    nav[0] = 1.0
    for i in range(1, n):
        nav[i] = nav[i - 1] * (1.0 + ret[i])
        assert nav[i] > 0, f"non-positive NAV at bar {i}"
        ASSERT_N["n"] += 1
    return nav


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def worst_roll_return(nav: np.ndarray, lo: int, hi: int, span: int) -> float:
    navw = nav[lo:hi]
    if len(navw) <= span:
        return np.nan
    logr = np.diff(np.log(navw))
    roll = pd.Series(logr).rolling(span).sum()
    w = roll.min()
    return np.nan if pd.isna(w) else float(np.exp(w) - 1.0)


def window_metrics(nav: np.ndarray, bench_ret: np.ndarray, mask: np.ndarray) -> dict:
    if not mask.any():
        return {"lo": 0, "hi": 0, "Days": 0}
    lo, hi = int(np.argmax(mask)), int(len(mask) - np.argmax(mask[::-1]))
    navw = nav[lo:hi]
    norm = navw / navw[0]
    ret = navw[1:] / navw[:-1] - 1.0
    out = {"CAGR": metrics.cagr(norm), "Sharpe": metrics.ann_sharpe(ret),
           "MaxDD": metrics.max_drawdown(norm),
           "Worst12m": worst_roll_return(nav, lo, hi, TD),
           "lo": lo, "hi": hi, "Days": hi - lo}
    a, b, t = metrics.jensen_alpha(ret, bench_ret[lo + 1:hi])
    out["Alpha"], out["Beta"], out["t"] = a, b, t
    return out


def cost_drag(nav_cost: np.ndarray, nav_zero: np.ndarray, mask: np.ndarray) -> float:
    if not mask.any():
        return np.nan
    lo, hi = int(np.argmax(mask)), int(len(mask) - np.argmax(mask[::-1]))
    nc = nav_cost[lo:hi]; nz = nav_zero[lo:hi]
    return (metrics.cagr(nz / nz[0]) - metrics.cagr(nc / nc[0])) * 100.0


def count_switches(gate: np.ndarray, mask: np.ndarray) -> int:
    if not mask.any():
        return 0
    lo, hi = int(np.argmax(mask)), int(len(mask) - np.argmax(mask[::-1]))
    seg = gate[max(lo, 0):hi]
    if len(seg) < 2:
        return 0
    return int(np.sum(seg[1:] != seg[:-1]))


def ann_ret_masked(ret: np.ndarray, mask: np.ndarray) -> tuple[float, int]:
    r = ret[mask]
    n_days = int(mask.sum())
    if n_days < 2:
        return np.nan, n_days
    compounded = float(np.prod(1.0 + r)) - 1.0
    years = n_days / TD
    return (1.0 + compounded) ** (1.0 / years) - 1.0, n_days


def find_episodes(gate: np.ndarray) -> list[dict]:
    """Contiguous runs of gate==False (gated OUT of SPY, parked)."""
    n = len(gate)
    episodes = []
    i = 0
    while i < n:
        if not gate[i]:
            j = i
            while j < n and not gate[j]:
                j += 1
            episodes.append({"start": i, "end": j, "open": j == n})
            i = j
        else:
            i += 1
    return episodes


def episode_excess(r_basket: np.ndarray, r_cash: np.ndarray, ep: dict) -> tuple[float, float, float]:
    lo, hi = ep["start"], ep["end"]
    basket_c = float(np.prod(1.0 + r_basket[lo:hi])) - 1.0
    cash_c = float(np.prod(1.0 + r_cash[lo:hi])) - 1.0
    return basket_c, cash_c, basket_c - cash_c


def overlaps(idx: pd.DatetimeIndex, ep: dict, w_start: pd.Timestamp, w_end: pd.Timestamp) -> bool:
    ep_start = idx[ep["start"]]
    ep_end = idx[ep["end"] - 1]
    return not (ep_end < w_start or ep_start > w_end)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _p(x, dec=1):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:+.{dec}f}%"


def _a(m):
    a, t = m.get("Alpha"), m.get("t")
    if a is None or not np.isfinite(a):
        return "n/a"
    return f"{a * 100:+.1f}pp (t{t:+.1f})"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    prov_all = []

    spy_df, prov = build_core_only("SPY")
    prov_all += prov
    def_dfs = {}
    for sym in DEFENSIVE:
        df, prov = build_core_only(sym)
        def_dfs[sym] = df
        prov_all += prov

    irx_raw = load("^IRX")
    prov_all.append(("^IRX", irx_raw.attrs.get("source", "?"), len(irx_raw),
                     str(irx_raw.index.min().date()), str(irx_raw.index.max().date())))
    r_cash_full = (irx_raw["close"] / 100.0 / TD).reindex(spy_df.index).ffill()

    # Gate computed on SPY's OWN full raw-close history (warm-up well before 1999).
    spy_raw = load("SPY")
    gate_full = build_gate(spy_raw["close"])

    # Basket: equal-weight, daily-rebalanced composite of the 3 defensive legs'
    # own r_net, on their common trading-day intersection.
    def_idx = def_dfs["XLP"].index
    for sym in DEFENSIVE[1:]:
        def_idx = def_idx.intersection(def_dfs[sym].index)
    basket_r = pd.concat([def_dfs[sym]["r_net"].reindex(def_idx) for sym in DEFENSIVE],
                         axis=1).mean(axis=1)
    basket_r.name = "basket_r_net"

    # Common index: SPY r_net ∩ basket ∩ gate ∩ cash, floored at WINDOW_START.
    common_idx = spy_df.index.intersection(basket_r.index).intersection(gate_full.index)
    common_idx = common_idx.intersection(r_cash_full.index)
    common_idx = common_idx[common_idx >= WINDOW_START]
    print(f"common window: {common_idx[0].date()} -> {common_idx[-1].date()} "
          f"({len(common_idx)} days)", flush=True)

    r_spy = spy_df["r_net"].reindex(common_idx).values
    r_basket = basket_r.reindex(common_idx).values
    r_cash = r_cash_full.reindex(common_idx).values
    gate = gate_full.reindex(common_idx).fillna(False).values.astype(bool)

    assert not np.isnan(r_spy[1:]).any(), "NaN in SPY r_net on common window"
    assert not np.isnan(r_basket[1:]).any(), "NaN in basket r_net on common window"
    assert not np.isnan(r_cash[1:]).any(), "NaN in cash return on common window"

    # Sanity anchor
    anchor_nav = buyhold_nav(r_spy)
    print(f"SANITY SPY B&H TR (HK net) {common_idx[0].date()}->{common_idx[-1].date()}: "
          f"CAGR {metrics.cagr(anchor_nav)*100:.2f}% Sharpe {metrics.ann_sharpe(r_spy[1:]):.2f} "
          f"MaxDD {metrics.max_drawdown(anchor_nav)*100:.1f}%", flush=True)

    # ------------------------------------------------------------------
    # 4 warehouses
    # ------------------------------------------------------------------
    nav_w1 = buyhold_nav(r_spy)
    nav_w2, sw2 = simulate_gated(gate, r_spy, r_cash, COST_SIDE)
    nav_w3, sw3 = simulate_gated(gate, r_spy, r_basket, COST_SIDE)
    nav_w4 = buyhold_nav(r_basket)
    nav_w2_0, _ = simulate_gated(gate, r_spy, r_cash, 0.0)
    nav_w3_0, _ = simulate_gated(gate, r_spy, r_basket, 0.0)
    print(f"4 warehouses simulated ({time.time()-t0:.0f}s); "
          f"W2 switches={sw2} W3 switches={sw3} (should be identical: same gate)",
          flush=True)
    assert sw2 == sw3, "W2/W3 switch counts diverged despite sharing the same gate"

    WAREHOUSES = [
        ("W1  100% SPY B&H", nav_w1, None, None),
        ("W2  SPY / cash(^IRX) gated", nav_w2, nav_w2_0, gate),
        ("W3  SPY / XLP+XLU+XLV gated", nav_w3, nav_w3_0, gate),
        ("W4  100% XLP+XLU+XLV B&H", nav_w4, None, None),
    ]

    # ------------------------------------------------------------------
    # Windows
    # ------------------------------------------------------------------
    yrs = common_idx.year.values
    windows = [
        ("FULL", np.ones(len(common_idx), dtype=bool)),
        ("H1 (start-2011)", yrs <= 2011),
        ("H2 (2012+)", yrs >= 2012),
        ("Stress 2008", yrs == 2008),
        ("Stress 2020", yrs == 2020),
        ("Stress 2022", yrs == 2022),
    ]
    STRESS_WINDOWS = [
        ("2008", pd.Timestamp("2008-01-01"), pd.Timestamp("2008-12-31")),
        ("2020", pd.Timestamp("2020-01-01"), pd.Timestamp("2020-12-31")),
        ("2022", pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31")),
    ]

    # ------------------------------------------------------------------
    # Special readout (a): W3-W2 per-episode excess, bear windows only
    # ------------------------------------------------------------------
    episodes = find_episodes(gate)
    ep_rows = []
    bear_excess = []
    for ep in episodes:
        basket_c, cash_c, excess = episode_excess(r_basket, r_cash, ep)
        in_bear = any(overlaps(common_idx, ep, ws, we) for _, ws, we in STRESS_WINDOWS)
        which = [name for name, ws, we in STRESS_WINDOWS if overlaps(common_idx, ep, ws, we)]
        ep_rows.append({
            "start": common_idx[ep["start"]], "end": common_idx[ep["end"] - 1] if not ep["open"] else None,
            "open": ep["open"], "days": ep["end"] - ep["start"],
            "basket_c": basket_c, "cash_c": cash_c, "excess": excess,
            "in_bear": in_bear, "which": which,
        })
        if in_bear:
            bear_excess.append(excess)
    avg_bear_excess = float(np.mean(bear_excess)) if bear_excess else np.nan
    n_bear_episodes = len(bear_excess)
    print(f"{len(episodes)} gated-out episodes total, {n_bear_episodes} overlap a stress "
          f"window; avg W3-W2 excess in those episodes = {avg_bear_excess*100:+.2f}%",
          flush=True)

    # ------------------------------------------------------------------
    # Special readout (b): W4 bull-market rent vs SPY, SPY-bull days only
    # ------------------------------------------------------------------
    ann_spy_bull, n_bull_days = ann_ret_masked(r_spy, gate)
    ann_basket_bull, _ = ann_ret_masked(r_basket, gate)
    rent_pp = (ann_basket_bull - ann_spy_bull) * 100.0
    print(f"SPY-bull days: {n_bull_days} ({n_bull_days/len(common_idx)*100:.0f}% of sample). "
          f"SPY ann {ann_spy_bull*100:.2f}% vs basket ann {ann_basket_bull*100:.2f}% "
          f"-> rent {rent_pp:+.2f}pp/yr", flush=True)

    # per-half breakdown of the same rent calc, for robustness (not the headline)
    rent_halves = {}
    for wname, mask in [("H1 (start-2011)", yrs <= 2011), ("H2 (2012+)", yrs >= 2012)]:
        bull_h = gate & mask
        a_spy, nb = ann_ret_masked(r_spy, bull_h)
        a_bas, _ = ann_ret_masked(r_basket, bull_h)
        rent_halves[wname] = (a_spy, a_bas, (a_bas - a_spy) * 100.0, nb)

    # ------------------------------------------------------------------
    # Write results markdown
    # ------------------------------------------------------------------
    L = []
    add = L.append
    add("# Result — Ballast parking: is XLP/XLU/XLV \"pseudo-cash\" a viable "
        "substitute for cash when the 200SMA trend gate exits SPY?")
    add("")
    add("**Date:** 2026-07-12  **Script:** `backtest/experiments/exp_ballast_parking.py`  "
        "**Status:** active")
    add("")
    add("## Question")
    add("")
    add("主 agent 設計「全風險組合」(唔准持有現金/T-bills/SPY 現貨)。核心未知數：當 200SMA "
        "趨勢閘叫你離開 SPY 曝險時，錢冇得去現金——去防守板塊 XLP/XLU/XLV 做「偽現金」係咪可行 "
        "代替品？代價幾大？兩個專項讀數：(a) W3(防守停泊) vs W2(現金停泊) 喺 bear 窗口嘅每次 "
        "切換平均差；(b) W4(100%防守長持) 喺 SPY>200SMA 期間相對 SPY 嘅年化落後（「牛市租金」，"
        "要用 LEAP delta 補返）。")
    add("")
    add("## Method")
    add("")
    add("- 四個 warehouse，同一條 SPY 200SMA 訊號（RAW 收市價 vs 200SMA，signal close T -> "
        "position active T+1，repo 標準 `shift(1)` 慣例）：W1 100% SPY B&H；W2 gate=ON 揸 SPY / "
        "OFF 揸 100% cash(^IRX 逐日計息)；W3 gate=ON 揸 SPY / OFF 揸 XLP+XLU+XLV 等權；W4 100% "
        "XLP+XLU+XLV B&H。")
    add("- 成本：10bps/邊 -> 一次全數切換 = 20bps NAV，喺 gate 反轉嗰 bar 一次性扣減。W2/W3 共用 "
        "同一條 gate，切換時機/次數必然相同——成本喺 W3-W2 嘅逐 episode 比較入面互相抵銷（兩者入/"
        "出都畀同一 20bps），淨係睇「揸乜嘢資產渡過呢段時間」嘅差異。")
    add("- HK 稅：全部四條腿用 repo 標準 `r_net = r_adj - 0.30*dy`（dy = adjusted vs raw 收市價 "
        "差分重建嘅每日息率，1bp 門檻殺 adjustment 捨入雜訊）——同 `exp_leap_real_sweep.py` / "
        "`exp_crash_switch.py` 完全一致嘅公式，冇重新發明。防守板塊息率比 SPY 高好多，呢個唔可以 "
        "慳，否則會高估「偽現金」嘅吸引力。")
    add("- 防守籃子：XLP/XLU/XLV **等權**，逐日重新平衡嘅複合 r_net（**指定，唔係擇優**——冇對 "
        "權重做任何搜尋）。籃子內部逐日重平衡假設無額外成本（只有進/出籃子整體嗰刻收 20bps 切換 "
        "成本）——呢個係建模簡化，見 Caveats。")
    add("- 窗：FULL（XLP/XLU/XLV/SPY/^IRX 三方共同視窗，floor 1999-01-01，XL 系 1998-12-16 "
        "上市）+ 兩半（split 2012-01-01）+ 三個壓力窗（календар年 2008/2020/2022）。")
    add("")
    add("## Data provenance (`backtest/data.py` `load()`)")
    add("")
    add("| Series | Source | Rows | From | To |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in prov_all:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")
    add(f"- 共同模擬視窗：{common_idx[0].date()} -> {common_idx[-1].date()} "
        f"（{len(common_idx)} 個交易日）。")
    add(f"- 校驗錨點 — SPY B&H TR (HK net)：CAGR **{metrics.cagr(anchor_nav)*100:.2f}%**, "
        f"Sharpe {metrics.ann_sharpe(r_spy[1:]):.2f}, MaxDD {metrics.max_drawdown(anchor_nav)*100:.1f}%.")
    add("")

    # -- Table 1: main grid -----------------------------------------------------
    add("## Table 1 — 四方案 x 六窗（全期 / 兩半 / 三壓力窗）")
    add("")
    add("| Warehouse | Window | CAGR | Sharpe | MaxDD | Worst 12m roll | "
        "α vs SPY B&H (t) | β | Switches | CostDrag pp/yr |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for label, nav, nav0, gate_arr in WAREHOUSES:
        for wname, mask in windows:
            m = window_metrics(nav, r_spy, mask)
            sw = count_switches(gate_arr, mask) if gate_arr is not None else 0
            cd = cost_drag(nav, nav0, mask) if nav0 is not None else np.nan
            cd_s = f"{cd:+.2f}" if np.isfinite(cd) else "n/a"
            add(f"| {label} | {wname} | {_p(m.get('CAGR'))} | "
                f"{m.get('Sharpe', np.nan):.2f} | {_p(m.get('MaxDD'))} | "
                f"{_p(m.get('Worst12m'))} | {_a(m)} | "
                f"{m.get('Beta', np.nan):.2f} | {sw} | {cd_s} |")
    add("")

    # -- Special readout (a) ------------------------------------------------
    add("## 專項讀數 (a) — W3-W2 增量：防守停泊 vs 現金停泊，bear 窗口嘅每次切換")
    add("")
    add(f"共 {len(episodes)} 個 gated-out episode（SPY 曝險關閉期）；當中 **{n_bear_episodes} 個** "
        f"同 2008/2020/2022 壓力窗有重疊。呢批 episode 入面，防守籃子相對現金嘅平均超額（每 "
        f"episode 複合報酬差，cost-neutral，見 Method）：")
    add("")
    add(f"### **W3-W2 平均增量（bear 窗口 episode）= {avg_bear_excess*100:+.2f}%**")
    add("")
    add("逐 episode 明細（全部列出，唔淨係 bear 窗口）：")
    add("")
    add("| 換出日 | 換返日 | 天數 | 籃子複合報酬 | 現金複合報酬 | W3-W2 超額 | 屬壓力窗？ |")
    add("|---|---|---|---|---|---|---|")
    for r in ep_rows:
        end_s = "（樣本結尾仍持有）" if r["open"] else str(r["end"].date())
        bear_s = ", ".join(r["which"]) if r["in_bear"] else "—"
        add(f"| {r['start'].date()} | {end_s} | {r['days']} | {_p(r['basket_c'])} | "
            f"{_p(r['cash_c'])} | {_p(r['excess'])} | {bear_s} |")
    add("")

    # -- Special readout (b) ------------------------------------------------
    add("## 專項讀數 (b) — W4 牛市租金：防守籃子喺 SPY>200SMA 期間相對 SPY 嘅年化落後")
    add("")
    add(f"SPY-bull 日數：{n_bull_days}（{n_bull_days/len(common_idx)*100:.0f}% of FULL 樣本）。"
        f"呢啲日子入面（年化，複合後按日數還原年率）：SPY {ann_spy_bull*100:.2f}%/yr vs "
        f"防守籃子 {ann_basket_bull*100:.2f}%/yr。")
    add("")
    add(f"### **W4 牛市租金 = {rent_pp:+.2f}pp/yr**（LEAP delta sleeve 要補返呢個數）")
    add("")
    add("兩半分拆（穩健性檢查，非headline）：")
    add("")
    add("| 窗 | SPY-bull 日數 | SPY 年化 | 籃子年化 | 租金 pp/yr |")
    add("|---|---|---|---|---|")
    for wname, (a_spy, a_bas, rent, nb) in rent_halves.items():
        add(f"| {wname} | {nb} | {a_spy*100:.2f}% | {a_bas*100:.2f}% | {rent:+.2f} |")
    add("")

    # -- Cross-foot -------------------------------------------------------------
    add("## Cross-foot verification")
    add("")
    open_eps = sum(1 for r in ep_rows if r["open"])
    add(f"- {ASSERT_N['n']:,} bar-level NAV>0 assertions across all 4 warehouse simulations, "
        f"ALL passed. {len(episodes)} gated-out episodes detected, {open_eps} still open at "
        "end of sample (flagged, not orphaned) — see episode table above.")
    add(f"- W2/W3 switch counts verified IDENTICAL on every window (shared gate; see Table 1).")
    add("")

    add("## Conclusions")
    add("")
    add(f"- **(a) W3-W2 (防守 vs 現金停泊, bear 窗口, {n_bear_episodes} episodes): "
        f"{avg_bear_excess*100:+.2f}% 平均每 episode 超額.**")
    add(f"- **(b) W4 牛市租金 (防守籃子 vs SPY, SPY-bull 期間): {rent_pp:+.2f}pp/yr.**")
    add("- （其餘判斷、W2/W3 全期 Sharpe/MaxDD/whipsaw 頻率對比，見對話回覆 [結論] 段，基於 "
        "Table 1 全表撰寫。）")
    add("")
    add("## Caveats")
    add("")
    add("- 單一歷史路徑，冇 bootstrap／冇 Bonferroni／DSR 多重測試修正——呢個係用戶指定嘅單一 "
        "假設驗證（4 個 warehouse，冚唪唥 pre-registered），唔係大格網 sweep，但都要意識到「等權"
        "」呢個籃子構成本身係 judgment call，唔係窮舉最優。")
    add("- XLP/XLU/XLV 1998-12-16 先上市，FULL 窗只有 ~1999-01 至今（~27 年），只含 2 次完整 "
        "熊市週期（2008 GFC + 2020 COVID + 2022 rate-hike，2000-02 dot-com 熊市唔喺呢個窗入面， "
        "因為防守板塊 ETF 自己都未上市）——樣本比 SPY/QQQ 自己嘅歷史短，結論嘅時間跨度有限。")
    add("- 200SMA 閘本身對 whipsaw（假訊號來回切換）敏感——本 study 冇獨立量化「省返嘅回撤」相對"
        "「多付嘅切換成本+踏空」呢條數，Table 1 嘅 Switches 欄係逐窗切換次數，讀者要自行對比其"
        "他 200SMA 研究（`2026-06-30_rsi2_200sma.md` 等）先可以判斷閘本身是否值得用，本 study 只"
        "問「閘開咗之後泊喺邊」。")
    add("- 籃子逐日等權重平嘅假設係簡化——真實執行唔會逐日重平三隻 ETF，但 XLP/XLU/XLV 高度相關"
        "、漂移緩慢，呢個簡化嘅誤差預期細（未獨立驗證）。")
    add("- 切換成本（10bps/邊，20bps/次全換）係模型假設；真實執行（尤其大手數）滑點可能更高，本 "
        "study 冇做滑點敏感度掃描。")
    add("- W3-W2 嘅 episode-level 比較係 cost-neutral（見 Method），但 Table 1 嘅 CostDrag 欄"
        "（zero-cost shadow 對比）已經獨立呈現整體成本拖累，唔靠 episode 比較嚟隱藏成本。")
    add("")
    add("## Implication")
    add("")
    add("（見對話回覆——若 (a) 顯著正值，防守停泊喺 bear 窗口優於現金停泊，支持設計採用「偽現金」"
        "方案；若 (a) 接近零或負值，防守停泊冇明顯優勢，需要重新諗全風險組合喺閘關閉時嘅去向。"
        "(b) 嘅牛市租金數字直接餵返 LEAP delta sizing 嘅補償要求。）")
    add("")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS}  ({time.time()-t0:.0f}s total, {ASSERT_N['n']:,} asserts)",
          flush=True)


if __name__ == "__main__":
    main()
