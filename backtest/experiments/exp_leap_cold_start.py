"""COLD START — how should a Core-v2 operator who holds ZERO LEAPs, on a day the
200SMA gate is ALREADY open and mid-month, get to the b=15% NAV target?

The manual vacuum this closes
-----------------------------
`docs/2026-07-07_core_playbook.md` (§0 param card, §1 daily test, §2 entry SOP,
§3 monthly top-up) is written for a program ALREADY RUNNING. It has no cold-start
chapter. Its §2 SOP reads "buy to the 7.5%/leg target" with no guidance on whether
a from-zero operator should put the whole 15% NAV on in one T+1 close, or ladder
in. The headline +6.5pp damp alpha (`2026-07-06_core_topup.md`, winner cell
C-monthly/b15/Delta0.50/SPY+QQQ) is the average of ONE continuous 300-month path
whose entries are naturally spread across 25 years of gate re-entries and rolls —
it is NOT a statement about the risk of any single first deployment. Those are
different objects and the manual never says so.

Question (pre-registered)
-------------------------
(1) From a cold start on a gate-open mid-month day, does laddering the first
    deployment beat deploying it all at once? By how much?
(2) In the subsample where the start happens to sit just before a major top, how
    much does laddering actually rescue?
(3) Should the playbook carry a cold-start rule?

Method (mirror / increment / horizon)
-------------------------------------
Mirror     : the same 3-bucket program the user runs (SPY core + 50/50 SPY+QQQ
             LEAP sleeve + cash), same real ^VIX/^VXN/^IRX data, same benchmark
             (SPY B&H total return, HK 30% dividend withholding netted), same
             locked winner settings (b=15% NAV, Delta=0.50, roll@63td, pure
             200SMA GATED, C-monthly floor top-up).
Increment  : ONLY the FIRST deployment schedule differs across the 4 arms. Every
             arm reverts to the identical C-monthly regime thereafter, and every
             arm is CAPITAL-MATCHED (total premium budget b=15% NAV, cash floor
             15%*NAV, core weight 70% at t0 — identical for all 4).
Horizon    : 3 years (756 trading days) from the cold start. ROLLING START: every
             eligible start day gets its own 3-year path, so the answer is a
             DISTRIBUTION over entry luck, not one path.

Engines — IMPORTED VERBATIM, nothing reimplemented
--------------------------------------------------
  `simulate_unit_path`, `build_underlying`, `build_gates`  <- exp_leap_real_sweep
  `simulate_portfolio_topup`, `month_start_mask`           <- exp_core_topup
  `damp_iv`, `window_metrics`, `CAPITAL`, `_p`             <- exp_core_assembly_real
The staged arms are expressed WITHOUT touching the engine: a k-tranche ladder is
k separate legs per underlying, each with premium budget b_leg = 0.075/k and each
with its own unit path started at its own deployment bar. `simulate_portfolio_topup`
already accepts an arbitrary leg list and sums option value across legs, so the
ladder is pure composition of the existing engine, not a new accounting path.

The 4 pre-registered cold-start arms (capital-matched; all revert to C-monthly)
-------------------------------------------------------------------------------
  1. IMMEDIATE : deploy the full 15% NAV at the T+1 close of the start day.
  2. NEXT-MONTH: deploy the full 15% at the next month's first trading day
                 (the closest literal reading of the manual's §3 cadence).
  3. LADDER-3  : 1/3 of the 15% at each of the NEXT 3 month-starts.
  4. LADDER-6  : 1/6 of the 15% at each of the NEXT 6 month-starts.
Un-deployed premium cash sits in the cash pool earning ^IRX (this is what the
C-monthly floor already does) — the ladder is a deployment schedule, not a
different asset allocation.

Start universe (pre-registered)
-------------------------------
Every trading day s of the SPY+QQQ common window (2001+) such that:
  - BOTH legs' gates are open at s (mirrors the user's actual state today: QQQ
    and SPY both above their 200SMA; also the only state where "deploy the whole
    sleeve now" is even a live option for both legs), AND
  - s is NOT a month-start bar (a cold start ON a month-start would collapse
    arms 1 and 2 into the same thing — the user is explicitly mid-month), AND
  - a full 756-bar horizon fits before the end of data.
No subsampling. Paths OVERLAP heavily by construction — see the statistics note.

Metrics (capital efficiency first, per repo convention)
-------------------------------------------------------
  CapEff  : EXCESS dollars earned over the 3 years (NAV_end minus what the same
            starting NAV would be if it had just compounded at SPY net-TR)
            DIVIDED BY the mean sleeve delta-notional dollars carried over the
            path (zero-exposure days included in the mean — waiting for a tranche
            genuinely lowers average exposure, and this metric is what prices
            that trade-off). "Excess dollars per dollar of LEAP exposure carried."
  CAGR    : 3-year NAV CAGR.
  MaxDD   : over the full 3 years.
  DD12    : WORST drawdown inside the FIRST 12 months (252 bars) measured from
            the path's own running peak. THIS is the metric the user's question
            is actually about ("what if today is the top?").
  Alpha   : Jensen alpha (annualized) vs SPY net-TR over the 3-year path.
Reported as DISTRIBUTIONS across all starts (median / p10 / p90), never as a
single mean. Base IV (m=0.85) AND damp=0.4 both reported for every arm.

"Bought right before the top" subsample (pre-registered label)
--------------------------------------------------------------
A start s is in the TOP-TRAP subsample iff there exists a bar h in [s, s+60]
such that QQQ's close at h is a 60-day running high AND QQQ subsequently falls
more than 20% below that high within the following 252 bars. This label uses
future information BY DESIGN — it is a way to slice history to answer "what
happened to people who started just before a top", not a tradable signal.

Statistics note (honest, not decorative)
----------------------------------------
Rolling 3-year paths from adjacent start days share ~99.9% of their bars. Naive
cross-start t-stats would be nonsense. So: (a) the primary read is the PAIRED
per-start difference (arm minus IMMEDIATE) on the SAME start, which removes the
common market path; (b) the only significance statement made is a block bootstrap
that resamples whole CALENDAR YEARS of start dates with replacement (B=2000),
which respects the dominant dependence; (c) multiple comparisons: 3 arms x 2 IV
settings x 5 metrics x 2 subsamples are computed, and ALL are printed — no cell
is selected after the fact. There is no winner-selection algorithm here because
this loop is not a search; it is a description of one distribution.

Run:  PYTHONUTF8=1 python backtest/experiments/exp_leap_cold_start.py
Writes: backtest/results/2026-07-17_leap_cold_start.md (tables + provenance;
narrative conclusions finalized by hand afterwards).
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import load                                  # noqa: E402
from exp_leap_real_sweep import (                       # noqa: E402
    build_underlying, build_gates, simulate_unit_path,
)
from exp_core_topup import (                            # noqa: E402
    simulate_portfolio_topup, month_start_mask,
)
from exp_core_assembly_real import (                    # noqa: E402
    damp_iv, window_metrics, CAPITAL,
)

# ---- locked winner settings (NOT re-searched here) -------------------------
DELTA = 0.50
B_TOTAL = 0.15
CASH_W = 0.15
IV_MULT = 0.85
COST_BASE = 0.005
DAMP = 0.4
RULE = "C-monthly"          # post-cold-start regime for every arm

HOR = 756                   # 3 years
DD12_BARS = 252
TOP_LOOKAHEAD = 60          # bars after start in which a top may form
TOP_DROP = -0.20            # subsequent fall that defines "a top"
TOP_HIGH_WIN = 60           # bars: running-high window defining a "high"
TOP_FWD = 252               # bars after the high in which the fall must happen

ARMS = ["1-immediate", "2-next-month", "3-ladder-3", "4-ladder-6"]
ARM_TRANCHES = {"1-immediate": 1, "2-next-month": 1, "3-ladder-3": 3, "4-ladder-6": 6}

BOOT_B = 2000
BOOT_SEED = 20260717

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-17_leap_cold_start.md")

UNIT_KEYS = ("mark", "mark_pre", "sell", "sell_mark", "buy", "buy_mark", "delta")


# ---------------------------------------------------------------------------
# Unit-path cache: a fresh path started at bar d, length min(HOR, N-d).
# simulate_unit_path is IMPORTED VERBATIM; slicing the input arrays at d is what
# makes the path "cold" at d (not holding, buys at the first gate-open bar >= d).
# ---------------------------------------------------------------------------

def make_unit_from(arrs, d, n_bars):
    u = simulate_unit_path(arrs["close"][d:d + n_bars], arrs["iv"][d:d + n_bars],
                           arrs["r"][d:d + n_bars], arrs["q"][d:d + n_bars],
                           arrs["gate"][d:d + n_bars], DELTA)
    return {k: u[k] for k in UNIT_KEYS}


def pad_unit(u, offset, length):
    """Place a unit path that starts at bar (start+offset) into a `length`-bar
    window that starts at `start`. Bars before the deployment are a no-op:
    NaN marks, no buy/sell events -> the engine carries 0 contracts there."""
    out = {}
    take = min(length - offset, len(u["mark"]))
    for k in UNIT_KEYS:
        src = u[k]
        if src.dtype == bool:
            a = np.zeros(length, dtype=bool)
        else:
            a = np.full(length, np.nan)
        a[offset:offset + take] = src[:take]
        out[k] = a
    return out


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def dd_first_12m(nav):
    w = nav[:DD12_BARS]
    peak = np.maximum.accumulate(w)
    return float(np.min(w / peak - 1.0))


def cap_eff(res, bench):
    nav = res["nav"]
    growth = float(np.prod(1.0 + bench[1:len(nav)]))
    excess_dollars = nav[-1] - nav[0] * growth
    expo = res["dnotional"] * nav
    expo = expo[np.isfinite(expo)]
    mean_expo = float(np.mean(expo)) if len(expo) else np.nan
    if not np.isfinite(mean_expo) or mean_expo <= 0:
        return np.nan
    return float(excess_dollars / mean_expo)


def q3(x):
    x = np.asarray(x, dtype="float64")
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return (np.nan, np.nan, np.nan)
    return (float(np.percentile(x, 10)), float(np.median(x)),
            float(np.percentile(x, 90)))


def block_boot_median_diff(diff, years, rng, B=BOOT_B):
    """95% CI for the median paired difference, resampling whole calendar YEARS
    of start dates with replacement (the dominant dependence in overlapping
    rolling paths)."""
    diff = np.asarray(diff, dtype="float64")
    years = np.asarray(years)
    uy = np.unique(years)
    buckets = [np.where(years == y)[0] for y in uy]
    out = np.empty(B)
    for b in range(B):
        pick = rng.integers(0, len(buckets), len(buckets))
        idx = np.concatenate([buckets[p] for p in pick])
        d = diff[idx]
        d = d[np.isfinite(d)]
        out[b] = np.median(d) if len(d) else np.nan
    out = out[np.isfinite(out)]
    if len(out) == 0:
        return (np.nan, np.nan)
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def _pp(x, dec=2):
    return "n/a" if not np.isfinite(x) else f"{x * 100:+.{dec}f}%"


def _f(x, dec=3):
    return "n/a" if not np.isfinite(x) else f"{x:+.{dec}f}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    irx_df = load("^IRX")
    irx = irx_df["close"]
    prov_all = [("^IRX", irx_df.attrs.get("source", "?"), len(irx_df),
                 str(irx_df.index.min().date()), str(irx_df.index.max().date()))]

    data = {}
    for under, volsym in [("SPY", "^VIX"), ("QQQ", "^VXN")]:
        df, prov, _ = build_underlying(under, volsym, irx)
        data[under] = {"df": df}
        prov_all += prov

    spy_df, qqq_df = data["SPY"]["df"], data["QQQ"]["df"]
    common_idx = spy_df.index.intersection(qqq_df.index)
    N = len(common_idx)
    print(f"common window {common_idx[0].date()} -> {common_idx[-1].date()} "
          f"({N} days)", flush=True)

    # Per-underlying arrays on the common index. IV damping uses the NATIVE full
    # window mean (damp_iv verbatim) BEFORE reindexing -- same convention as
    # exp_core_topup.py, not recomputed per sub-window.
    A = {}
    for under, df in [("SPY", spy_df), ("QQQ", qqq_df)]:
        iv_raw = df["vol"].values / 100.0 * IV_MULT
        iv_damp = damp_iv(iv_raw, DAMP)
        gate = build_gates(df)["GATED"]
        s = lambda v: pd.Series(v, index=df.index).reindex(common_idx).values
        A[(under, "base")] = {"close": s(df["close"].values), "iv": s(iv_raw),
                              "r": s(df["irx"].values / 100.0), "q": s(df["q"].values),
                              "gate": s(gate).astype(bool)}
        A[(under, "damp")] = dict(A[(under, "base")], iv=s(iv_damp))

    core_ret = pd.Series(spy_df["r_net"].values, index=spy_df.index).reindex(common_idx).values
    r_cash = pd.Series(spy_df["irx"].values / 100.0 / 252.0, index=spy_df.index).reindex(common_idx).values
    bench = core_ret
    gate_spy = A[("SPY", "base")]["gate"]
    gate_qqq = A[("QQQ", "base")]["gate"]
    ms_mask = month_start_mask(common_idx)
    ms_bars = np.where(ms_mask)[0]

    # ---- start universe --------------------------------------------------
    starts = [s for s in range(N - HOR)
              if gate_spy[s] and gate_qqq[s] and not ms_mask[s]]
    starts = np.array(starts)
    # Smoke-test knob ONLY (COLD_START_STRIDE>1 thins the universe so the script
    # can be exercised end-to-end in seconds). The reported run uses stride=1 =
    # the full pre-registered universe; the results file records the stride used.
    stride = int(os.environ.get("COLD_START_STRIDE", "1"))
    if stride > 1:
        starts = starts[::stride]
    print(f"start universe: {len(starts)} gate-open non-month-start days "
          f"with a full {HOR}-bar horizon (stride={stride})", flush=True)

    # ---- TOP-TRAP label ---------------------------------------------------
    qc = A[("QQQ", "base")]["close"]
    is_top = np.zeros(N, dtype=bool)
    for h in range(N):
        lo = max(0, h - TOP_HIGH_WIN)
        if qc[h] < np.max(qc[lo:h + 1]):
            continue
        fwd = qc[h + 1:h + 1 + TOP_FWD]
        if len(fwd) and float(np.min(fwd)) / qc[h] - 1.0 <= TOP_DROP:
            is_top[h] = True
    top_cum = np.concatenate([[0], np.cumsum(is_top)])
    trap = np.array([top_cum[min(N, s + TOP_LOOKAHEAD + 1)] - top_cum[s] > 0
                     for s in starts])
    print(f"TOP-TRAP subsample: {int(trap.sum())} / {len(starts)} starts "
          f"({trap.mean()*100:.1f}%)", flush=True)

    # ---- month-start unit-path cache (shared across many starts) ----------
    cache = {}

    def unit_at(under, iv, d):
        key = (under, iv, d)
        if key not in cache:
            cache[key] = make_unit_from(A[(under, iv)], d, min(HOR, N - d))
        return cache[key]

    for iv in ("base", "damp"):
        for under in ("SPY", "QQQ"):
            for d in ms_bars:
                if d >= N - 1:
                    continue
                unit_at(under, iv, int(d))
    print(f"month-start unit cache built: {len(cache)} paths ({time.time()-t0:.0f}s)",
          flush=True)

    # ---- run the grid -----------------------------------------------------
    M = {}   # (arm, iv) -> dict of metric -> list over starts
    for arm in ARMS:
        for iv in ("base", "damp"):
            M[(arm, iv)] = {k: [] for k in
                            ("CapEff", "CAGR", "MaxDD", "DD12", "Alpha", "ExpoMed",
                             "R12", "Expo12")}
    start_years = np.array([common_idx[s].year for s in starts])

    for si, s in enumerate(starts):
        s = int(s)
        idx_w = common_idx[s:s + HOR]
        bench_w = bench[s:s + HOR]
        core_w = core_ret[s:s + HOR]
        rc_w = r_cash[s:s + HOR]
        trig_w = ms_mask[s:s + HOR]
        nxt = ms_bars[ms_bars > s][:6]
        if len(nxt) < 6:
            continue
        close_w = {u: A[(u, "base")]["close"][s:s + HOR] for u in ("SPY", "QQQ")}

        for iv in ("base", "damp"):
            fresh = {u: make_unit_from(A[(u, iv)], s, HOR) for u in ("SPY", "QQQ")}
            for arm in ARMS:
                k = ARM_TRANCHES[arm]
                b_leg = (B_TOTAL / 2.0) / k
                legs = []
                for u in ("SPY", "QQQ"):
                    if arm == "1-immediate":
                        ds = [s]
                    else:
                        ds = [int(x) for x in nxt[:k]]
                    for d in ds:
                        u_path = fresh[u] if d == s else unit_at(u, iv, d)
                        legs.append({"b": b_leg,
                                     "unit": pad_unit(u_path, d - s, HOR),
                                     "close": close_w[u]})
                res = simulate_portfolio_topup(legs, core_w, rc_w, COST_BASE,
                                               CASH_W, RULE, B_TOTAL, trig_w)
                m = window_metrics(res, bench_w, idx_w, 0, HOR)
                d = M[(arm, iv)]
                d["CapEff"].append(cap_eff(res, bench_w))
                d["CAGR"].append(m["CAGR"])
                d["MaxDD"].append(m["MaxDD"])
                d["DD12"].append(dd_first_12m(res["nav"]))
                d["Alpha"].append(m["Alpha"])
                d["ExpoMed"].append(m["DnMed"])
                nav = res["nav"]
                d["R12"].append(float(nav[DD12_BARS - 1] / nav[0] - 1.0))
                e12 = (res["dnotional"] * nav)[:DD12_BARS]
                e12 = e12[np.isfinite(e12)]
                d["Expo12"].append(float(np.mean(e12)) if len(e12) else np.nan)
        if si % 200 == 0:
            print(f"  start {si}/{len(starts)} {common_idx[s].date()} "
                  f"({time.time()-t0:.0f}s)", flush=True)

    n_paths = len(M[("1-immediate", "base")]["CAGR"])
    keep = np.array([True] * len(starts))
    if n_paths != len(starts):     # starts dropped for <6 forward month-starts
        keep = np.zeros(len(starts), dtype=bool)
        keep[:n_paths] = True
    trap_k = trap[keep][:n_paths]
    years_k = start_years[keep][:n_paths]
    print(f"paths simulated: {n_paths} x 4 arms x 2 IV ({time.time()-t0:.0f}s)",
          flush=True)

    # ---- report ------------------------------------------------------------
    rng = np.random.default_rng(BOOT_SEED)
    L = []
    add = L.append
    add("# Result — LEAP 冷啟動:由零開始應該一次過入,定係分期入?"
        "(rolling-start,4 條路徑規則,真數據)")
    add("")
    add(f"**Date:** 2026-07-17  **Script:** `backtest/experiments/exp_leap_cold_start.py`  "
        f"**Status:** active")
    add("")
    add("## 問題")
    add("")
    add("Core v2 手冊(`docs/2026-07-07_core_playbook.md`)§0-§9 **冇冷啟動章節**——"
        "佢由頭到尾假設個程式已經跑緊。用戶今日嘅真實處境:手上零 QQQ LEAP、"
        "閘已經開咗一段時間、而家係月中。手冊答唔到「由零開始應該點入場」。"
        "而 `2026-07-06_core_topup.md` 嗰個 +6.5pp(damp)alpha 係**一條連續跑 25 年、"
        "入場天然攤薄晒**嘅路徑嘅平均值——佢**唔係**任何單一次首次部署嘅風險陳述。"
        "呢兩樣嘢唔係同一回事,手冊從來冇講明。本 loop 就係補呢個真空。")
    add("")
    add("## 方法")
    add("")
    add("- **引擎全部 verbatim import,冇重寫**:`simulate_unit_path`/`build_underlying`/"
        "`build_gates`(← `exp_leap_real_sweep.py`)、`simulate_portfolio_topup`/"
        "`month_start_mask`(← `exp_core_topup.py`)、`damp_iv`/`window_metrics`/`CAPITAL`"
        "(← `exp_core_assembly_real.py`)。分期入場**唔使改引擎**:k 期階梯 = 每個標的 k 條"
        "獨立 leg,每條 b_leg = 0.075/k、各自由自己嘅部署日開一條全新 unit path;"
        "`simulate_portfolio_topup` 本身已經收任意 leg list 並加總期權市值。")
    add(f"- **鎖死參數**(唔喺度重新搜):b={int(B_TOTAL*100)}% NAV、Δ={DELTA:.2f}、"
        f"SPY+QQQ 50/50、純 200SMA GATED、roll@63td、C-monthly floor top-up、"
        f"成本 0.5%/side、T+1 收市執行、CAPITAL=${CAPITAL:,.0f}。")
    add("- **4 條冷啟動規則(capital-matched,全部之後轉入正常 C-monthly régime)**:"
        "1-immediate=起點 T+1 收市一次過 deploy 到 15% NAV;2-next-month=等下一個月首個"
        "交易日先一次過 deploy;3-ladder-3=未來 3 個月頭各 1/3;4-ladder-6=未來 6 個月頭各 1/6。"
        "未部署嘅 premium 現金留喺池收 ^IRX(C-monthly floor 本身就係咁),"
        "所以 4 條規則嘅總投入、現金 floor(15%×NAV)同 t0 底倉(70%)完全一樣。")
    add(f"- **Rolling start(呢個先係核心方法)**:2001+ 共同窗每一個「兩條腿嘅閘都開住、"
        f"而且唔係月頭」嘅交易日各做一次「由零開始跑 3 年({HOR} 個交易日)」嘅路徑。"
        f"冇 subsample。起點宇宙 = **{len(starts)} 條路徑**,每條 ×4 規則 ×2 IV。")
    add("- **base(m=0.85)同 damp=0.4 兩個 IV 都全報**,每格都有。")
    add("")
    add("### 量度(資本效率行先,Karst 原則)")
    add("")
    add("| 名 | 定義 |")
    add("|---|---|")
    add("| **CapEff** | 3 年**超額美金**(NAV_end 減「同一筆起始 NAV 淨係跟 SPY net-TR 複利」嘅終值)"
        "÷ 路徑上**平均 sleeve delta-notional 美金**(零曝險日**計入**分母平均——等錢入場真係會拉低平均曝險,"
        "而呢個比率就係為咗替呢個 trade-off 定價)。即「每承受一蚊 LEAP 曝險,賺到幾多超額」 |")
    add("| CAGR | 3 年 NAV CAGR |")
    add("| MaxDD | 3 年全程最大回撤 |")
    add("| **DD12** | **首 12 個月(252 bars)內、由路徑自己嘅高位起計嘅最差回撤** —— "
        "呢個先係用戶問嘅嘢(「萬一今日就係頂」) |")
    add("| Alpha | 3 年路徑對 SPY net-TR 嘅 Jensen alpha(年化) |")
    add("")
    add("### 「啱啱買喺頂前」子樣本(預先登記嘅標籤)")
    add("")
    add(f"起點 s 入 TOP-TRAP 子樣本,當且僅當 [s, s+{TOP_LOOKAHEAD}] 之間存在一個 bar h,"
        f"h 係 QQQ 嘅 {TOP_HIGH_WIN} 日新高,**而且** QQQ 喺之後 {TOP_FWD} 個 bar 內"
        f"由該高位跌超過 {abs(TOP_DROP)*100:.0f}%。呢個標籤**故意用未來資訊**——"
        f"佢係一把切歷史嘅刀(「當年啱啱買喺頂前嗰批人點收科」),**唔係**一個可交易訊號。")
    add("")
    add("### 統計誠實聲明")
    add("")
    add("- 相鄰起點嘅 3 年路徑共用 ~99.9% 嘅 bar。**跨起點嘅 naive t-stat 係垃圾**,本檔一個都唔報。")
    add("- 主視角 = **同一起點上嘅配對差**(規則 X 減 1-immediate),自動消掉共同市場路徑。")
    add(f"- 唯一嘅顯著性陳述 = **block bootstrap**(B={BOOT_B},以**整個曆年**嘅起點為 block "
        f"resample,尊重最主要嗰層相依),報配對差中位數嘅 95% CI。")
    add("- **多重比較申報**:3 條規則 × 2 IV × 5 個量度 × 2 個子樣本全部計晒、"
        "**全部印晒**,冇任何一格係事後揀出嚟。本 loop **冇 winner-selection 演算法**,"
        "因為佢唔係一個 search,佢係一個分佈嘅描述。")
    add("")
    add("## Data provenance (`backtest/data.py` `load()`)")
    add("")
    add("| Series | Source | Rows | From | To |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in prov_all:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")
    add(f"- 共同(mix)模擬窗:{common_idx[0].date()} -> {common_idx[-1].date()} "
        f"({N} days)。")
    add(f"- 起點宇宙:**{n_paths}** 條 rolling 冷啟動路徑;其中 TOP-TRAP 子樣本 "
        f"**{int(trap_k.sum())}** 條({trap_k.mean()*100:.1f}%)。")
    add("")

    def dist_table(mask, title, note):
        add(f"## {title}")
        add("")
        add(note)
        add("")
        add("| 規則 | IV | CapEff p10/med/p90 | CAGR p10/med/p90 | MaxDD p10/med/p90 | "
            "**DD12 p10/med/p90** | Alpha p10/med/p90 | 平均曝險(med Dn%) |")
        add("|---|---|---|---|---|---|---|---|")
        for arm in ARMS:
            for iv in ("base", "damp"):
                d = M[(arm, iv)]
                sel = lambda k: np.asarray(d[k], dtype="float64")[mask]
                ce = q3(sel("CapEff")); cg = q3(sel("CAGR"))
                md = q3(sel("MaxDD")); dd = q3(sel("DD12"))
                al = q3(sel("Alpha")); ex = q3(sel("ExpoMed"))
                add(f"| {arm} | {iv} | {_f(ce[0])}/{_f(ce[1])}/{_f(ce[2])} "
                    f"| {_pp(cg[0],1)}/{_pp(cg[1],1)}/{_pp(cg[2],1)} "
                    f"| {_pp(md[0],1)}/{_pp(md[1],1)}/{_pp(md[2],1)} "
                    f"| **{_pp(dd[0],1)}/{_pp(dd[1],1)}/{_pp(dd[2],1)}** "
                    f"| {_pp(al[0],1)}/{_pp(al[1],1)}/{_pp(al[2],1)} "
                    f"| {ex[1]*100:.0f}% |")
        add("")

    all_mask = np.ones(n_paths, dtype=bool)
    dist_table(all_mask, "Table 1 — 4 條冷啟動規則,全起點分佈(p10 = 壞運,med = 中位,p90 = 好運)",
               f"全部 {n_paths} 條 rolling 冷啟動路徑。每行 = 一條規則 × 一個 IV 設定。")
    dist_table(trap_k, "Table 2 — **TOP-TRAP 子樣本**:起點之後 60 日內見一個之後跌 >20% 嘅頂",
               f"{int(trap_k.sum())} 條路徑。呢張表直接答「萬一而家就係頂」。")

    # ---- paired differences ------------------------------------------------
    def paired_table(mask, title, note):
        add(f"## {title}")
        add("")
        add(note)
        add("")
        add("| 規則(對比 1-immediate)| IV | 量度 | 配對差中位數 | 95% CI(年-block bootstrap)| "
            "配對差 >0 嘅比例 |")
        add("|---|---|---|---|---|---|")
        for arm in ARMS[1:]:
            for iv in ("base", "damp"):
                for met in ("CapEff", "CAGR", "MaxDD", "DD12", "Alpha", "R12"):
                    a = np.asarray(M[(arm, iv)][met], dtype="float64")[mask]
                    b = np.asarray(M[("1-immediate", iv)][met], dtype="float64")[mask]
                    diff = a - b
                    ok = np.isfinite(diff)
                    med = float(np.median(diff[ok])) if ok.any() else np.nan
                    lo_, hi_ = block_boot_median_diff(diff[ok], years_k[mask][ok], rng)
                    frac = float(np.mean(diff[ok] > 0)) if ok.any() else np.nan
                    fmt = _f if met == "CapEff" else (lambda x: _pp(x, 2))
                    add(f"| {arm} | {iv} | {met} | {fmt(med)} | {fmt(lo_)} .. {fmt(hi_)} "
                        f"| {frac*100:.0f}% |")
        add("")

    paired_table(all_mask, "Table 3 — 配對差(同一起點),全起點",
                 "正數 = 該規則好過「即刻全入」。CapEff 係比率;其餘係百分點。"
                 "MaxDD/DD12 嘅正數 = 回撤**冇咁深**(即分期救到)。")
    paired_table(trap_k, "Table 4 — 配對差(同一起點),**TOP-TRAP 子樣本**",
                 "同上,但只計「啱啱買喺頂前」嗰批起點。呢張表量化「分期救到幾多」。")

    # ---- cost of waiting ---------------------------------------------------
    add("## Table 5 — 等錢入場嘅代價(首 12 個月,全起點)")
    add("")
    add("分期入場嘅代價 = 等緊嗰段時間放棄咗嘅曝險同升幅。呢張表用首 12 個月嘅"
        "數字直接量化:回報少咗幾多、曝險少咗幾多。")
    add("")
    add("| 規則 | IV | 首12m 回報 p10/med/p90 | 對 immediate 嘅配對差(med) | "
        "首12m 平均曝險 $(med) | 曝險 vs immediate |")
    add("|---|---|---|---|---|---|")
    for arm in ARMS:
        for iv in ("base", "damp"):
            r = np.asarray(M[(arm, iv)]["R12"], dtype="float64")
            r0 = np.asarray(M[("1-immediate", iv)]["R12"], dtype="float64")
            e = np.asarray(M[(arm, iv)]["Expo12"], dtype="float64")
            e0 = np.asarray(M[("1-immediate", iv)]["Expo12"], dtype="float64")
            rq = q3(r)
            dmed = float(np.median((r - r0)[np.isfinite(r - r0)]))
            emed = float(np.median(e[np.isfinite(e)]))
            eratio = float(np.median((e / e0)[np.isfinite(e / e0)]))
            add(f"| {arm} | {iv} | {_pp(rq[0],1)}/{_pp(rq[1],1)}/{_pp(rq[2],1)} "
                f"| {_pp(dmed,2) if arm != '1-immediate' else '—'} "
                f"| ${emed:,.0f} | {eratio*100:.0f}% |")
    add("")

    add("## 判詞")
    add("")
    add("(placeholder — 睇完 Table 1-5 之後人手填)")
    add("")
    add("## Caveats")
    add("")
    add("(placeholder — 人手填)")
    add("")
    add("## 建議條文(草稿,等用戶拍板;本 loop 唔改 playbook)")
    add("")
    add("(placeholder — 人手填)")
    add("")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS}  ({time.time()-t0:.0f}s total)", flush=True)


if __name__ == "__main__":
    main()
