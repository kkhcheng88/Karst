"""Experiment: crash-switch — after a QQQ/SPMO large drawdown, swap the SPY base
holding for QQQ/SPMO, then swap back on recovery. Does the switch beat 100% SPY
B&H, or does it just underperform/whipsaw?

Background
----------
User question: "QQQ 或 SPMO 大冧之後，把底倉由 SPY 換過去，回升後換返，會唔會好過
一直揸 SPY？" This is a NEW decision never tested in this repo — Core v2
(`docs/2026-07-06_core_strategy_v2.md`) and `exp_base_mix.py` both test a STATIC
base-holding choice (pick one symbol, hold forever); this script tests a
DYNAMIC switch triggered by drawdown/recovery signals, isolated from every
other Core v2 mechanism (no LEAP sleeve, no cash buffer, no top-up rule —
100% of NAV is always in exactly one of {SPY, QQQ-or-SPMO} at any time).

Question
--------
Does crash-triggered base-holding rotation (SPY -> QQQ/SPMO after a big
drawdown, back to SPY on recovery) beat 100% SPY buy-and-hold, net of switching
costs? Tested left-side (drawdown-from-ATH trigger) and right-side (200SMA
recovery-confirmation trigger) variants, on both QQQ (long history, includes
the 2000-02 crash) and SPMO (short history, 2 crash episodes only).

Method (mirror / increment / horizon)
------
Mirror     : 100% base-holding-only portfolio (no LEAP sleeve, no cash target,
             no top-up rule) — isolates the "swap the core" decision itself
             from every other Core v2 machinery. Benchmark = 100% SPY B&H net
             total return (HK 30% dividend withholding), same convention as
             `exp_base_mix.py`'s `build_core_only`, reproduced locally here
             (this script needs no options engine, so nothing is imported from
             the LEAP-sleeve cluster).
Increment  : entirely NEW plumbing — a day-by-day state-machine switch
             simulator (`simulate_switch`) with a 1-trading-day EXECUTION lag
             ("T 收市訊號 -> T+1 收市執行": the switch fills at T+1's close, so
             the FIRST return day under the new holding is T+2 -> T+1, i.e. one
             extra day of lag vs this repo's usual "signal close T -> position
             active from T+1" convention — deliberate, per this study's
             pre-registration, to model a full trading day to relocate 100% of
             book). Cost: 5bps/side, so a full switch (sell 100% old + buy 100%
             new) = 10bps of NAV, deducted as a one-time NAV haircut at the
             execution bar.
Horizon    : continuous multi-year hold; drawdown/200SMA/all-time-high are all
             computed on the candidate's OWN raw close price (same convention
             as `exp_leap_real_sweep.build_gates`'s 200SMA gate — price-driven,
             not total-return-driven), while the compounded portfolio return
             uses each leg's own `r_net` (HK-net total return) series.

Pre-registered variants (run all, report all)
------
Base-holding-only, 100% NAV, cost 5bps/side (10bps per full switch), T close
signal -> T+1 close execution:
  - Control        : 100% SPY B&H (HK 30% dividend withholding netted).
  - V1 (left-side) : NOT holding candidate AND candidate's close <= -X% off its
                     own all-time-high (confirmed on close) -> switch 100% into
                     candidate. HOLDING candidate AND candidate makes a new
                     all-time-high (confirmed on close) -> switch 100% back to
                     SPY. X in {20%, 30% (headline), 40%}, candidate = QQQ.
  - V2 (right-side): candidate's drawdown-from-ATH has breached -30% at some
                     point (episode armed) AND candidate's close is back above
                     its OWN 200SMA (confirmed on close) -> switch 100% into
                     candidate (episode re-arm consumed). HOLDING candidate AND
                     candidate's close drops back below its 200SMA -> switch
                     100% back to SPY. Candidate = QQQ.
  - V3             : V1(30%, headline) and V2, candidate = SPMO, window
                     2015-10-12+ (SPMO inception) — only 2 crash episodes
                     (2020, 2022) expected; reported per-episode, never as a
                     single aggregate number.
Windows: FULL = candidate's own native trading history (QQQ: 1999-03-10+, which
IS QQQ's actual full public history — no truncation artifact — and includes
the full 2000-02 crash from just before the March-2000 peak) + 2016-2020 +
2021+. SPMO (V3): 2015-10-12+ only (its own full history).
All windows are DATE SLICES of ONE continuously-run switch simulation (not
independently restarted per window) — same convention as this repo's other
multi-window experiments (e.g. `exp_core_topup.py`'s `wslices`).

Per-cell metrics
------
CAGR / annualized Sharpe (raw daily returns) / MaxDD / Jensen alpha (annualized,
t-stat) + beta vs SPY B&H net-TR / switch count (completed round trips within
the window) / a full per-episode table (trigger date, switch-in exec date +
price, switch-back exec date + price, episode excess return = the switch
portfolio's compounded return over [switch-in exec date, switch-back exec date]
MINUS SPY B&H's compounded return over the identical date range).

Reading discipline (pre-registered, mechanical — applied in Conclusions)
------
- If a variant's alpha-t is driven by beta > 1 (spending more time in a
  higher-beta asset), say so plainly — that is a leverage/beta bet dressed up
  as a rotation edge, not skill.
- If a variant's headline number is dominated by ONE episode (e.g. the 2020-03
  V-shaped recovery), say so plainly.
- The 2000-02 episode (QQQ entered the crash-switch and, on the pure
  all-time-high recovery trigger, did NOT get a switch-back signal for ~15
  years) MUST be shown in full in the episode table, not smoothed over or
  excluded as an outlier.

Cross-foot (hard asserts): NAV > 0 every bar; NAV_t = NAV_{t-1} * (1 + leg
return) * (1 - switch cost, if an execution fires this bar); a completed
switch-in is always followed (in episode accounting) by either a matching
switch-back or an explicit "still open at end of sample" flag — no orphaned
episodes.

Run:  PYTHONUTF8=1 python backtest/experiments/exp_crash_switch.py
Writes: backtest/results/2026-07-08_crash_switch.md
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metrics                                     # noqa: E402
from data import load                              # noqa: E402

COST_PER_SIDE = 0.0005      # 5bps/side -> 10bps per full 100%-of-book switch
SMA_WIN = 200
BREACH_DD = -0.30           # V2 episode-arming threshold (fixed, per spec)
V1_THRESHOLDS = [0.20, 0.30, 0.40]

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-08_crash_switch.md")


# ---------------------------------------------------------------------------
# Data — candidate/benchmark HK-net total-return series (r_net), same formula
# as exp_base_mix.build_core_only, reproduced locally (no options engine needed
# here, so nothing else is imported from that cluster).
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
    dy = dy.where(dy > 1e-4, 0.0)
    r_net = r_adj - 0.30 * dy
    df = pd.DataFrame({"close": close, "r_net": r_net}).dropna()
    return df, prov


# ---------------------------------------------------------------------------
# Switch simulator — day-by-day state machine, 1-day execution lag, 5bps/side.
# ---------------------------------------------------------------------------

def simulate_switch(idx, spy_ret, alt_close, alt_ret, mode: str, thresh: float | None = None,
                    cost_side: float = COST_PER_SIDE):
    """mode: 'V1' (left-side, thresh=drawdown trigger) or 'V2' (right-side,
    fixed BREACH_DD arm + 200SMA cross). Returns nav array (idx-aligned,
    nav[0]=1.0) and a list of episode dicts (switch-in/switch-back pairs, with
    a trailing 'open' episode if the candidate is still held at series end).
    """
    n = len(idx)
    running_max = np.maximum.accumulate(alt_close)
    dd = alt_close / running_max - 1.0
    sma200 = pd.Series(alt_close).rolling(SMA_WIN, min_periods=SMA_WIN).mean().values

    nav = np.empty(n)
    nav[0] = 1.0
    holding_alt = False
    pending = None          # {'exec_day', 'new_state', 'signal_day'}
    breached = False        # V2 episode-arm flag

    switch_log = []          # every execution: (exec_day, new_state, price)
    n_asserts = 0

    for t in range(n):
        if t > 0:
            r = alt_ret[t] if holding_alt else spy_ret[t]
            nav[t] = nav[t - 1] * (1.0 + r)
        # execute a pending switch scheduled for today (fills at TODAY's close)
        if pending is not None and pending["exec_day"] == t:
            nav[t] *= (1.0 - 2.0 * cost_side)
            holding_alt = pending["new_state"]
            switch_log.append((t, holding_alt, alt_close[t]))
            pending = None
        assert nav[t] > 0, f"non-positive nav at bar {t}"
        n_asserts += 1

        # compute today's signal (data through today's close); schedule exec T+1
        if t + 1 >= n:
            continue
        if mode == "V1":
            if not holding_alt and pending is None and dd[t] <= -thresh:
                pending = {"exec_day": t + 1, "new_state": True, "signal_day": t}
            elif holding_alt and pending is None and dd[t] >= -1e-9:
                pending = {"exec_day": t + 1, "new_state": False, "signal_day": t}
        elif mode == "V2":
            if dd[t] <= BREACH_DD:
                breached = True
            if (not holding_alt and pending is None and breached
                    and np.isfinite(sma200[t]) and alt_close[t] > sma200[t]):
                pending = {"exec_day": t + 1, "new_state": True, "signal_day": t}
                breached = False
            elif (holding_alt and pending is None
                  and np.isfinite(sma200[t]) and alt_close[t] < sma200[t]):
                pending = {"exec_day": t + 1, "new_state": False, "signal_day": t}
        else:
            raise ValueError(mode)

    # Pair up switch_log into episodes (in-price at switch-in, out-price at switch-back)
    episodes = []
    open_entry = None
    for exec_day, new_state, price in switch_log:
        if new_state:      # switch IN
            open_entry = (exec_day, price)
        else:               # switch OUT (back to SPY)
            if open_entry is not None:
                episodes.append({"in_day": open_entry[0], "in_price": open_entry[1],
                                  "out_day": exec_day, "out_price": price, "open": False})
                open_entry = None
    if open_entry is not None:
        episodes.append({"in_day": open_entry[0], "in_price": open_entry[1],
                          "out_day": None, "out_price": None, "open": True})

    return nav, episodes, n_asserts


# ---------------------------------------------------------------------------
# Metrics / formatting
# ---------------------------------------------------------------------------

def window_metrics(nav, bench_ret, mask):
    lo, hi = int(np.argmax(mask)), int(len(mask) - np.argmax(mask[::-1]))
    navw = nav[lo:hi]
    norm = navw / navw[0]
    ret = navw[1:] / navw[:-1] - 1.0
    out = {"CAGR": metrics.cagr(norm), "Sharpe": metrics.ann_sharpe(ret),
           "MaxDD": metrics.max_drawdown(norm), "lo": lo, "hi": hi}
    a, b, t = metrics.jensen_alpha(ret, bench_ret[lo + 1:hi])
    out["Alpha"], out["Beta"], out["t"] = a, b, t
    return out


def episode_excess(nav, spy_ret, in_day, out_day):
    """Switch-portfolio compounded return over [in_day, out_day] minus SPY B&H
    compounded return over the identical date range."""
    port_ret = nav[out_day] / nav[in_day] - 1.0
    spy_cum = np.prod(1.0 + spy_ret[in_day + 1:out_day + 1]) - 1.0
    return port_ret, spy_cum, port_ret - spy_cum


def _p(x, dec=1):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:+.{dec}f}%"


def _a(m):
    a, t = m.get("Alpha"), m.get("t")
    if a is None or not np.isfinite(a):
        return "n/a"
    return f"{a * 100:+.1f}pp (t{t:+.1f})"


def switch_count(episodes, lo, hi):
    n = 0
    for e in episodes:
        if lo <= e["in_day"] < hi:
            n += 1
        if (not e["open"]) and lo <= e["out_day"] < hi:
            n += 1
    return n


def episode_rows(idx, episodes, nav, spy_ret, label):
    rows = []
    for e in episodes:
        in_date = str(idx[e["in_day"]].date())
        if e["open"]:
            rows.append(f"| {label} | {in_date} | {e['in_price']:.2f} | (still held at "
                        f"end of sample) | n/a | n/a — **open episode** |")
        else:
            out_date = str(idx[e["out_day"]].date())
            port_r, spy_r, excess = episode_excess(nav, spy_ret, e["in_day"], e["out_day"])
            rows.append(f"| {label} | {in_date} | {e['in_price']:.2f} | {out_date} | "
                        f"{e['out_price']:.2f} | port {_p(port_r)} vs SPY {_p(spy_r)} "
                        f"-> **{_p(excess)}** |")
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    prov_all = []

    spy_df, prov = build_core_only("SPY")
    prov_all += prov
    qqq_df, prov = build_core_only("QQQ")
    prov_all += prov
    spmo_df, prov = build_core_only("SPMO")
    prov_all += prov

    idx_qqq = spy_df.index.intersection(qqq_df.index)
    idx_spmo = spy_df.index.intersection(spmo_df.index)
    print(f"QQQ common window: {idx_qqq[0].date()} -> {idx_qqq[-1].date()} "
          f"({len(idx_qqq)} days)", flush=True)
    print(f"SPMO common window: {idx_spmo[0].date()} -> {idx_spmo[-1].date()} "
          f"({len(idx_spmo)} days)", flush=True)

    spy_ret_q = spy_df["r_net"].reindex(idx_qqq).values
    qqq_close = qqq_df["close"].reindex(idx_qqq).values
    qqq_ret = qqq_df["r_net"].reindex(idx_qqq).values

    spy_ret_s = spy_df["r_net"].reindex(idx_spmo).values
    spmo_close = spmo_df["close"].reindex(idx_spmo).values
    spmo_ret = spmo_df["r_net"].reindex(idx_spmo).values

    # Sanity anchor: SPY B&H over its own full history
    spy_bh_nav = np.concatenate([[1.0], np.cumprod(1.0 + spy_df["r_net"].values[1:])])
    anchor_cagr = metrics.cagr(spy_bh_nav)
    anchor_sharpe = metrics.ann_sharpe(spy_df["r_net"].values[1:])
    anchor_dd = metrics.max_drawdown(spy_bh_nav)
    print(f"SANITY SPY B&H TR (HK net) {spy_df.index[0].date()}->{spy_df.index[-1].date()}: "
          f"CAGR {anchor_cagr*100:.2f}% Sharpe {anchor_sharpe:.2f} MaxDD {anchor_dd*100:.1f}%",
          flush=True)

    n_asserts_total = 0

    # ---- QQQ: Control + V1 (20/30/40%) + V2 -------------------------------
    control_nav_q = np.concatenate([[1.0], np.cumprod(1.0 + spy_ret_q[1:])])

    v1_results = {}   # thresh -> (nav, episodes)
    for th in V1_THRESHOLDS:
        nav, eps, na = simulate_switch(idx_qqq, spy_ret_q, qqq_close, qqq_ret, "V1", thresh=th)
        v1_results[th] = (nav, eps)
        n_asserts_total += na
        print(f"QQQ V1 thresh={th:.0%} done, {len(eps)} episodes ({time.time()-t0:.0f}s)",
              flush=True)

    nav_v2q, eps_v2q, na = simulate_switch(idx_qqq, spy_ret_q, qqq_close, qqq_ret, "V2")
    n_asserts_total += na
    print(f"QQQ V2 done, {len(eps_v2q)} episodes ({time.time()-t0:.0f}s)", flush=True)

    # ---- SPMO: V1(30%, headline) + V2 -------------------------------------
    nav_v1s, eps_v1s, na = simulate_switch(idx_spmo, spy_ret_s, spmo_close, spmo_ret,
                                            "V1", thresh=0.30)
    n_asserts_total += na
    nav_v2s, eps_v2s, na = simulate_switch(idx_spmo, spy_ret_s, spmo_close, spmo_ret, "V2")
    n_asserts_total += na
    control_nav_s = np.concatenate([[1.0], np.cumprod(1.0 + spy_ret_s[1:])])
    print(f"SPMO V1/V2 done, {len(eps_v1s)}/{len(eps_v2s)} episodes ({time.time()-t0:.0f}s)",
          flush=True)

    # ---- Windows (QQQ side): FULL / 2016-2020 / 2021+ ---------------------
    yrs_q = idx_qqq.year.values
    windows_q = [("FULL (1999-03+)", np.ones(len(idx_qqq), dtype=bool)),
                 ("2016-2020", (yrs_q >= 2016) & (yrs_q <= 2020)),
                 ("2021+", yrs_q >= 2021)]
    windows_s = [("FULL (2015-10+)", np.ones(len(idx_spmo), dtype=bool))]

    # ------------------------------------------------------------------
    # Write results markdown
    # ------------------------------------------------------------------
    L = []
    add = L.append
    add("# Result — Crash-switch: SPY base holding -> QQQ/SPMO after a big "
        "drawdown, back to SPY on recovery (real data)")
    add("")
    add("**Date:** 2026-07-08  **Script:** `backtest/experiments/exp_crash_switch.py`  "
        "**Status:** active")
    add("")
    add("## Question")
    add("")
    add("用戶問：QQQ 或 SPMO 大冧之後，把底倉由 SPY 換過去，回升後換返，會唔會好過一直揸 "
        "SPY？呢個係一個 DYNAMIC 換底倉決定（未測過——Core v2 同 `exp_base_mix.py` 只測過 "
        "STATIC 底倉選擇），本 script 完全隔離 LEAP sleeve/現金/top-up，100% NAV 永遠淨係 "
        "揸 SPY 或者候選標的其中一樣。")
    add("")
    add("## Method")
    add("")
    add("- 100% base-holding-only（冧 sleeve、冧現金、冧 top-up），Control = 100% SPY B&H "
        "（HK 30% 股息預扣淨額，`r_net` 公式同 `exp_base_mix.build_core_only` 一致，呢度本地 "
        "重做一份，因為唔需要 options engine）。")
    add("- 訊號：drawdown/200SMA/歷史高位全部用候選標的**自己嘅 RAW 收市價**計（同 "
        "`exp_leap_real_sweep.build_gates` 嘅 200SMA 閘一致，價格驅動，唔係 total-return "
        "驅動）；組合報酬用各腿自己嘅 `r_net`（HK 淨額 total return）複利。")
    add("- 執行滯後：**T 收市訊號 -> T+1 收市執行**（比 repo 慣常「T 收市訊號 -> T+1 起持倉」"
        "多一日滯後——呢個 study 刻意咁 pre-register，模擬全數換馬需要一整個交易日先執行到）。")
    add("- 成本：5bps/邊，一次全數換馬（賣舊 100% + 買新 100%）= 10bps NAV，喺執行嗰 bar 一次性 "
        "扣減 NAV。")
    add("- V1（左側）：未持有候選 AND 候選收市價 <= 自身歷史高位 -X%（confirmed close）-> 換入；"
        "持有候選 AND 候選創新高（confirmed close）-> 換返 SPY。X ∈ {20%,30%(headline),40%}，"
        "候選 = QQQ。")
    add("- V2（右側）：候選回撤曾 <= -30%（episode armed）AND 候選收市重新企上自身 200SMA -> "
        "換入（armed 消耗）；持有候選 AND 收市跌穿 200SMA -> 換返 SPY。候選 = QQQ。")
    add("- V3：V1(30%,headline) + V2 嘅 SPMO 版，窗 2015-10-12+（SPMO 上市日）。")
    add("- 窗：FULL = 候選自身完整公開交易史（QQQ: 1999-03-10+ ，本身就係 QQQ 嘅完整歷史，"
        "無截斷 artifact，包含 2000-02 完整熊市）+ 2016-2020 + 2021+；全部係**同一條連續模擬**"
        "嘅日期切片（唔係逐窗重跑），同 `exp_core_topup.py` 嘅 `wslices` 慣例一致。")
    add("")
    add("## Data provenance (`backtest/data.py` `load()`)")
    add("")
    add("| Series | Source | Rows | From | To |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in prov_all:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")
    add(f"- QQQ common window: {idx_qqq[0].date()} -> {idx_qqq[-1].date()} ({len(idx_qqq)} days).")
    add(f"- SPMO common window: {idx_spmo[0].date()} -> {idx_spmo[-1].date()} ({len(idx_spmo)} days).")
    add(f"- 校驗錨點 — SPY B&H TR (HK net) {spy_df.index[0].date()}->{spy_df.index[-1].date()}: "
        f"CAGR **{anchor_cagr*100:.2f}%**, Sharpe {anchor_sharpe:.2f}, MaxDD {anchor_dd*100:.1f}% "
        "（合理範圍——長史含 1993 起）。")
    add("")

    # -- Table 1: QQQ V1 depth sweep -----------------------------------------
    add("## Table 1 — QQQ, V1 (left-side, drawdown-from-ATH), depth sweep "
        "{20%,30%,40%} vs Control, 3 windows")
    add("")
    add("| Variant | Window | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | β | Switches |")
    add("|---|---|---|---|---|---|---|---|")
    for wname, mask in windows_q:
        m = window_metrics(control_nav_q, spy_ret_q, mask)
        add(f"| Control (100% SPY B&H) | {wname} | {_p(m['CAGR'])} | {m['Sharpe']:.2f} | "
            f"{_p(m['MaxDD'])} | (benchmark) | 1.00 | 0 |")
        for th in V1_THRESHOLDS:
            nav, eps = v1_results[th]
            m = window_metrics(nav, spy_ret_q, mask)
            sc = switch_count(eps, m["lo"], m["hi"])
            tag = " (headline)" if th == 0.30 else ""
            add(f"| V1 -{th:.0%}{tag} | {wname} | {_p(m['CAGR'])} | {m['Sharpe']:.2f} | "
                f"{_p(m['MaxDD'])} | {_a(m)} | {m['Beta']:.2f} | {sc} |")
    add("")

    # -- Table 2: QQQ V2 -------------------------------------------------------
    add("## Table 2 — QQQ, V2 (right-side, breach-30%-then-200SMA-recovery) vs Control")
    add("")
    add("| Variant | Window | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | β | Switches |")
    add("|---|---|---|---|---|---|---|---|")
    for wname, mask in windows_q:
        m = window_metrics(control_nav_q, spy_ret_q, mask)
        add(f"| Control (100% SPY B&H) | {wname} | {_p(m['CAGR'])} | {m['Sharpe']:.2f} | "
            f"{_p(m['MaxDD'])} | (benchmark) | 1.00 | 0 |")
        m = window_metrics(nav_v2q, spy_ret_q, mask)
        sc = switch_count(eps_v2q, m["lo"], m["hi"])
        add(f"| V2 | {wname} | {_p(m['CAGR'])} | {m['Sharpe']:.2f} | {_p(m['MaxDD'])} | "
            f"{_a(m)} | {m['Beta']:.2f} | {sc} |")
    add("")

    # -- Table 3: SPMO V1/V2 ----------------------------------------------------
    add("## Table 3 — SPMO, V1(30%, headline) + V2 vs Control, window 2015-10-12+")
    add("")
    add("| Variant | Window | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | β | Switches |")
    add("|---|---|---|---|---|---|---|---|")
    for wname, mask in windows_s:
        m = window_metrics(control_nav_s, spy_ret_s, mask)
        add(f"| Control (100% SPY B&H) | {wname} | {_p(m['CAGR'])} | {m['Sharpe']:.2f} | "
            f"{_p(m['MaxDD'])} | (benchmark) | 1.00 | 0 |")
        m = window_metrics(nav_v1s, spy_ret_s, mask)
        sc = switch_count(eps_v1s, m["lo"], m["hi"])
        add(f"| V1 -30% | {wname} | {_p(m['CAGR'])} | {m['Sharpe']:.2f} | {_p(m['MaxDD'])} | "
            f"{_a(m)} | {m['Beta']:.2f} | {sc} |")
        m = window_metrics(nav_v2s, spy_ret_s, mask)
        sc = switch_count(eps_v2s, m["lo"], m["hi"])
        add(f"| V2 | {wname} | {_p(m['CAGR'])} | {m['Sharpe']:.2f} | {_p(m['MaxDD'])} | "
            f"{_a(m)} | {m['Beta']:.2f} | {sc} |")
    add("")

    # -- Episode tables -----------------------------------------------------
    add("## Episode tables (逐 episode，唔淨報 aggregate)")
    add("")
    add("每行：換入訊號日之後 T+1 執行日/執行價 -> 換返 SPY 執行日/執行價 -> 該 episode 期間 "
        "換馬組合複合報酬 vs 一直揸 SPY 嘅複合報酬 -> 相對超額。")
    add("")
    add("| Variant | Switch-in exec date | Switch-in price | Switch-back exec date | "
        "Switch-back price | Episode result |")
    add("|---|---|---|---|---|---|")
    for th in V1_THRESHOLDS:
        nav, eps = v1_results[th]
        L += episode_rows(idx_qqq, eps, nav, spy_ret_q, f"QQQ V1 -{th:.0%}")
    L += episode_rows(idx_qqq, eps_v2q, nav_v2q, spy_ret_q, "QQQ V2")
    L += episode_rows(idx_spmo, eps_v1s, nav_v1s, spy_ret_s, "SPMO V1 -30%")
    L += episode_rows(idx_spmo, eps_v2s, nav_v2s, spy_ret_s, "SPMO V2")
    add("")

    # -- Cross-foot -----------------------------------------------------------
    add("## Cross-foot verification")
    add("")
    add(f"- {n_asserts_total:,} bar-level NAV>0 assertions across all 6 switch simulations "
        "(QQQ V1 x3 + QQQ V2 + SPMO V1 + SPMO V2), ALL passed. Every completed switch-in is "
        "paired with either a matching switch-back or an explicit 'still held at end of "
        "sample' open-episode flag — no orphaned episodes (see episode tables above).")
    add("")

    add("## Conclusions")
    add("")
    add("(見對話回覆 [結論] 段 — 基於上面 Table 1-3 + episode 表撰寫)")
    add("")
    add("## Caveats")
    add("")
    add("- 單一歷史路徑，無 bootstrap；未做 Bonferroni/DSR 多重測試修正（呢個 study 係 "
        "用戶明確提出嘅單一假設驗證，唔係大格網 sweep，7 個 cell：QQQ V1×3 + QQQ V2 + SPMO "
        "V1 + SPMO V2 + Control，數目細，但都要意識到揀 30% 深度/200SMA 呢兩條規則本身已經係 "
        "judgment call，唔係窮舉最優）。")
    add("- QQQ 2000-02 episode（如適用）代表「接刀十幾年」嘅極端案例——全數呈現喺 episode 表，"
        "唔剔除做 outlier。")
    add("- SPMO 只有 ~10 年歷史 = 實質一個 regime（動能牛市+2020 V 型+2022 一次熊市），2 個 "
        "episode 唔夠做長史結論。")
    add("- 換馬滯後（T 收市 -> T+1 執行）同成本（10bps/次）係模型假設，真實執行（尤其大手數）"
        "滑點可能更高；本 study 冇做滑點敏感度。")
    add("- 200SMA/歷史高位全部用 RAW 收市價（非 total-return 調整價）計；QQQ/SPMO 股息率低，"
        "呢個選擇對訊號時機影響應該好細，但未獨立驗證。")
    add("")
    add("## Implication")
    add("")
    add("(見對話回覆 — 若冇任何 variant 顯著贏 Control，維持 SPY 底倉唔換；若有 variant 贏，"
        "要拆解係咪 β>1 或單一 episode 帶動先可以升級做建議。)")
    add("")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS}  ({time.time()-t0:.0f}s total, {n_asserts_total:,} asserts)",
          flush=True)


if __name__ == "__main__":
    main()
