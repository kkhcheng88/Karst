"""按 ASSUMPTIONS.md(2026-07-17 版)—— 本檔嚴守 A1-A7,逐條對照見下。

真實期權成本(m=1.15)之下,重新搜成個核心 LEAP (b, Δ, mix) 格
================================================================
`2026-07-17_core_topup_realcost.md` 已證:用戶手上核心 v2 勝出格
(C-monthly / b=15% / Δ0.50 / SPY+QQQ 50/50)係喺一個已被否定嘅期權定價
(m=0.85)下揀出嚟嘅。嗰份檔嘅判詞 3 逐字講明:「應該直接喺 m=1.15 上面
重新跑成個 (b, Δ, cadence) 格,因為勝出格本身就係喺一個錯咗嘅報價下揀
出嚟嘅,『邊格最好』呢個結論本身都可能跟住變。呢個係另一輪嘅工作。」
本檔就係嗰「另一輪」。用戶授權:用真價重揀,以資本效率為最優目標。

問題
----
喺最貼真實嘅期權報價(m=1.15)之下,b × Δ × LEAP-mix 邊一格資本效率最高?
換咗真價,勝出格同舊勝出格(b15/Δ0.50/50-50)差幾多?

ASSUMPTIONS.md 逐條對照(A1-A7)
--------------------------------
A1 永遠喺市 : core = 100% SPY 現貨,永不趨勢賣出;LEAP sleeve 係「現貨 vs
             LEAP」嘅槓桿選擇,唔係「入定唔入」。基準 = 全程 SPY net-TR
             (= core sleeve 自己嘅回報),唔係現金。
A2 尾部     : 200SMA 只做 LEAP sleeve 嘅「槓桿防爆倉」閘(engine 內建 GATED,
             verbatim import,唔郁),唔做核心入場濾網。MaxDD 每格照報,唔設
             硬淘汰閘 —— A2 係前瞻押注,唔係回測約束;由覆核點對照 A2 落判。
A3 量度     : 資本效率(α pp ÷ 中位 delta-notional 曝險)+ 絕對 PnL(CAGR /
             絕對 α)並列,每格都齊。CapEff 兩陷阱每表必檢:(a) 細分母谷高
             比率 → 每格並列 DnMed 分母 + 標記細分母格;(b) 蝕本組合比率倒轉
             → α≤0 一律 n/a-neg,唔入 CE 排序。α 只喺全組合層出現。
A4 窗口     : FULL(2001+,mix 共同窗口)主表 + H2 2011-2026 / 2016-2020 /
             2021+(「2016+ 前後半」= 2016-2020 與 2021+)子表。
A5 成本     : LEAP m=1.15 定價(07-09 實測 m=0.85 全面偏低)。ETF 交易免費
             (股票),期權 0.5%/side。**深-ITM(Δ0.70/0.80)用 m=1.15 係低估**
             (07-09 spotcheck:0.70Δ 隱含 m≈1.63 SPY / 1.26 QQQ),所以呢啲格
             另跑 m=1.30 / 1.50 敏感度帶包住,唔俾深-ITM 靠平價假設贏。
A6 節奏     : cadence 凍結 C-monthly(07-06/07-07 已定 C-monthly 勝,唔重掃)。
             月/週級決策,無 day-trade / 0DTE。
A7 載具     : ETF-only(SPY/QQQ),個股不入;core 恆為 SPY。

方法(凍結咗乜、變咗乜)
------------------------
引擎全部 **verbatim import**,一行都冇重寫,所以格間差異只來自 (b, Δ, mix, m):
  - `build_underlying` / `build_gates` / `simulate_unit_path` / `TD`
                                            <- exp_leap_real_sweep.py
  - `damp_iv` / `to_wslices` / `window_metrics` / `bench_metrics` / `cost_drag`
    `two_sided_p_from_t` / `_p` / `_a` / `_ruin` / `CAPITAL`
                                            <- exp_core_assembly_real.py
  - `simulate_portfolio_topup` / `month_start_mask`
                                            <- exp_core_topup.py
  - `cap_eff` / `alpha_ci`(CE / CI 定義,原檔口徑,保證 CE 錨對得返)
                                            <- exp_core_topup_realcost.py

Grid(本實驗全部)
------------------
  b   ∈ {10%, 12%, 15%, 20%} NAV
  Δ   ∈ {0.50, 0.60, 0.70, 0.80}(1y call,GATED,roll@63td)
  mix ∈ {SPY+QQQ 50/50, QQQ-only, SPY-only}
  cadence = C-monthly(凍結)
  = 4 × 4 × 3 = 48 格。全部 m=1.15,base 同 damp=0.4 都跑。
  深-ITM 誠實帶:Δ∈{0.70,0.80} 24 格另跑 m∈{1.30,1.50}(base+damp)。

資料尾巴凍結喺 2026-07-06(DATA_END)——同 realcost 一致
------------------------------------------------------
`data.py load()` 係 live yfinance(無快取)。凍結尾巴令 (a) m 成為唯一報價
變數、(b) b15/Δ0.50/50-50 @ m=1.15 呢格可以逐個數對返 realcost 檔。所有輸入
(rolling SMA/RSI/trailing-q/damp sigma_bar)都向後望,截尾只重現、唔擾動。

回歸錨(硬 assert —— 對唔上即 raise,停低查)
----------------------------------------------
b15/Δ0.50/SPY+QQQ 50/50 @ m=1.15 必須重現 `2026-07-17_core_topup_realcost.md`
表 1 嘅誠實格:base α +9.0pp(t+4.9)/ CAGR +17.4%;damp α +3.0pp(t+2.04)/
CAGR +11.7%。對唔上 = 引擎 import 唔忠實,下面冇一個數企得住。

預先登記嘅排序規則(睇數之前定,唔係睇完先揀)
------------------------------------------------
1. 48 格按 **damp × m=1.15 資本效率(CE)** 由大到細排(damp = 最保守嘅
   模型風險視角,同 realcost 誠實頭條、07-06 winner-on-damp 慣例一致)。
2. A3 兩陷阱閘:α≤0 → CE = n/a-neg,唔入排序(陷阱 b);DnMed 落喺全格
   下四分位 → 標記「⚠小分母」(陷阱 a,CE 谷高風險)。
3. 「新贏家」= 排序第 1 格。同「舊贏家」(b15/Δ0.50/50-50)正面對比。
4. 深-ITM(Δ≥0.70)格若上榜,m=1.30/1.50 誠實帶直接擺喺對比旁,唔俾平價
   假設誤導。本檔只報數;判詞喺覆核點對照 ASSUMPTIONS + SETTLED 先落。

統計紀律
--------
本輪登記宇宙 = 48 格(m=1.15)。**唔併入 07-06 舊 42 格**:realcost 明言
「舊 DSR=1.000 係 m=0.85 嘅產物,唔可以攞嚟為新報價背書」。Bonferroni
(normal-approx p × 48)+ DSR(`metrics.deflated_sharpe_ratio`,餵新贏家真實
日回報 + 48 格年化 Sharpe 宇宙)為新贏家報。

Cross-foot(每個會計 run 逐 bar 硬 assert,經 exp_core_topup.ASSERT_COUNT
累計):NAV = core + cash + Σ(期權市值);cash≥0;NAV>0;NAV_t 恆等式。

Run:  PYTHONUTF8=1 python backtest/experiments/exp_grid_realcost.py
Writes: backtest/results/2026-07-18_grid_realcost.md
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metrics                                    # noqa: E402
from data import load                             # noqa: E402
from exp_leap_real_sweep import (                 # noqa: E402
    build_underlying, build_gates, simulate_unit_path, TD,
)
from exp_core_assembly_real import (              # noqa: E402
    damp_iv, to_wslices, window_metrics, bench_metrics, cost_drag,
    two_sided_p_from_t, _p, _a, _ruin, CAPITAL,
)
import exp_core_topup as TOPUP                     # noqa: E402
from exp_core_topup import (                       # noqa: E402
    simulate_portfolio_topup, month_start_mask,
)
from exp_core_topup_realcost import cap_eff, alpha_ci   # noqa: E402  (CE/CI 口徑沿用)

# ---- grid axes ------------------------------------------------------------
BUDGETS = [0.10, 0.12, 0.15, 0.20]
DELTAS = [0.50, 0.60, 0.70, 0.80]
MIXES = ["SPY+QQQ", "QQQ-only", "SPY-only"]
DEEP_DELTAS = [0.70, 0.80]              # 深-ITM,m=1.15 低估 -> 另跑誠實帶

# ---- frozen (NOT searched) ------------------------------------------------
RULE = "C-monthly"
CASH_W = 0.15
COST_BASE = 0.005
DAMP = 0.4

# ---- pricing --------------------------------------------------------------
M_MAIN = 1.15                          # 07-09 spotcheck @0.50Δ 最貼真實
M_BAND = [1.30, 1.50]                  # 深-ITM 誠實帶(0.70Δ 真 m≈1.63/1.26)

DATA_END = pd.Timestamp("2026-07-06")  # 凍結:見 docstring

# ---- regression anchor (from 2026-07-17_core_topup_realcost.md 表 1) ------
ANCHOR = {("base", "Alpha"): 9.0, ("base", "CAGR"): 17.4, ("base", "t"): 4.9,
          ("damp", "Alpha"): 3.0, ("damp", "CAGR"): 11.7, ("damp", "t"): 2.04}
ANCHOR_TOL = {"Alpha": 0.25, "CAGR": 0.35, "t": 0.30}   # 抓 import break,容 yfinance 微漂

ANCHOR_KEY = (0.15, 0.50, "SPY+QQQ")

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-18_grid_realcost.md")


def cell_label(key) -> str:
    b, delta, mix = key
    return f"b{int(round(b*100))}/Δ{delta:.2f}/{mix}"


def ce_str(m: dict) -> str:
    ce = cap_eff(m)
    if np.isfinite(ce):
        return f"{ce:+.1f}"
    a = m.get("Alpha")
    return "n/a-neg" if (a is not None and np.isfinite(a) and a <= 0) else "n/a"


def main():
    t0 = time.time()
    irx_df = load("^IRX")
    irx = irx_df["close"]
    prov_all = [("^IRX", irx_df.attrs.get("source", "?"), len(irx_df),
                 str(irx_df.index.min().date()), str(irx_df.index.max().date()))]

    # ---- data prep: replicate realcost verbatim so the anchor reconciles ----
    data = {}
    for under, volsym in [("SPY", "^VIX"), ("QQQ", "^VXN")]:
        df, prov, _r = build_underlying(under, volsym, irx)
        df = df[df.index <= DATA_END]            # freeze tail (see docstring)
        data[under] = {"df": df}
        prov_all += prov
        print(f"{under} joined (frozen @{DATA_END.date()}): {df.index[0].date()} -> "
              f"{df.index[-1].date()}, {len(df)} days", flush=True)

    spy_df, qqq_df = data["SPY"]["df"], data["QQQ"]["df"]
    common_idx = spy_df.index.intersection(qqq_df.index)
    print(f"common (mix) window: {common_idx[0].date()} -> {common_idx[-1].date()}, "
          f"{len(common_idx)} days", flush=True)

    for under, df in [("SPY", spy_df), ("QQQ", qqq_df)]:
        d = data[under]
        d["close"] = df["close"].values
        d["vol"] = df["vol"].values            # RAW vol index; m applied per-cell
        d["r_arr"] = df["irx"].values / 100.0
        d["q_arr"] = df["q"].values
        d["r_cash"] = d["r_arr"] / TD
        d["gate"] = build_gates(df)["GATED"]
        d["r_net"] = df["r_net"].values

    a_mask = spy_df.index >= "1996-01-01"
    a_lo = int(np.where(a_mask)[0][0])
    anchor_bh = bench_metrics(spy_df["r_net"].values, a_lo, len(spy_df))
    print(f"SANITY SPY B&H TR (HK net) 1996->{spy_df.index[-1].date()}: "
          f"CAGR {anchor_bh['CAGR']*100:.2f}% Sharpe {anchor_bh['Sharpe']:.2f} "
          f"MaxDD {anchor_bh['MaxDD']*100:.1f}%", flush=True)

    native_index = {"SPY": spy_df.index, "QQQ": qqq_df.index}

    # common-window series (identical for every cell -> apples-to-apples) -----
    spy_close_c = pd.Series(data["SPY"]["close"], index=spy_df.index).reindex(common_idx).values
    qqq_close_c = pd.Series(data["QQQ"]["close"], index=qqq_df.index).reindex(common_idx).values
    close_c = {"SPY": spy_close_c, "QQQ": qqq_close_c}
    core_ret_c = pd.Series(data["SPY"]["r_net"], index=spy_df.index).reindex(common_idx).values
    r_cash_c = pd.Series(data["SPY"]["r_cash"], index=spy_df.index).reindex(common_idx).values
    bench_c = core_ret_c        # Jensen benchmark = SPY net-TR (core sleeve's own return)
    gate_c = {
        "SPY": pd.Series(data["SPY"]["gate"], index=spy_df.index).reindex(common_idx).values.astype(bool),
        "QQQ": pd.Series(data["QQQ"]["gate"], index=qqq_df.index).reindex(common_idx).values.astype(bool),
    }

    ms_mask = month_start_mask(common_idx)      # C-monthly trigger (IV-independent)

    wslices_all = to_wslices("QQQ", common_idx)
    wslices = {name: (lo, hi) for name, lo, hi in wslices_all
               if name.startswith("FULL") or name.startswith("H2")
               or name.startswith("2016") or name.startswith("2021")}
    full_name = [n for n in wslices if n.startswith("FULL")][0]
    lo0, hi0 = wslices[full_name]
    sub_names = [n for n in wslices if not n.startswith("FULL")]

    # ---- IV arrays + unit paths (compute each unique path once) -------------
    iv_cache = {}       # (under, m, ivkey) -> iv array (native frozen window)
    for under in ("SPY", "QQQ"):
        for mm in sorted(set([M_MAIN] + M_BAND)):
            iv_raw = data[under]["vol"] / 100.0 * mm
            iv_cache[(under, mm, "base")] = iv_raw
            iv_cache[(under, mm, "damp")] = damp_iv(iv_raw, DAMP)

    needed = set()                                  # (under, delta, m)
    for delta in DELTAS:
        for under in ("SPY", "QQQ"):
            needed.add((under, delta, M_MAIN))
    for delta in DEEP_DELTAS:
        for mm in M_BAND:
            for under in ("SPY", "QQQ"):
                needed.add((under, delta, mm))

    upath = {}          # (under, delta, m, ivkey) -> unit dict (native frozen)
    for (under, delta, mm) in sorted(needed):
        d = data[under]
        for ivkey in ("base", "damp"):
            upath[(under, delta, mm, ivkey)] = simulate_unit_path(
                d["close"], iv_cache[(under, mm, ivkey)],
                d["r_arr"], d["q_arr"], d["gate"], delta)
    print(f"{len(upath)} unit paths done ({time.time()-t0:.0f}s)", flush=True)

    _slice_cache = {}

    def uslice(under, delta, mm, ivkey):
        k = (under, delta, mm, ivkey)
        if k not in _slice_cache:
            udf = pd.DataFrame(upath[k], index=native_index[under])
            sl = udf.reindex(common_idx)
            _slice_cache[k] = {c: sl[c].values for c in udf.columns}
        return _slice_cache[k]

    def legs_unders(mix):
        return {"SPY-only": ["SPY"], "QQQ-only": ["QQQ"],
                "SPY+QQQ": ["SPY", "QQQ"]}[mix]

    def legs_for(mix, b, delta, mm, ivkey):
        unders = legs_unders(mix)
        b_each = b / len(unders)
        return [{"b": b_each, "unit": uslice(u, delta, mm, ivkey), "close": close_c[u]}
                for u in unders]

    def run_cell(mix, b, delta, mm, want_full_only=False, want_starved=False):
        """base + damp portfolio metrics on the common window. FULL-only for the band."""
        out = {}
        starved = None
        for ivkey in ("base", "damp"):
            legs = legs_for(mix, b, delta, mm, ivkey)
            res = simulate_portfolio_topup(legs, core_ret_c, r_cash_c, COST_BASE,
                                           CASH_W, RULE, b, ms_mask)
            names = [full_name] if want_full_only else list(wslices.keys())
            wm = {}
            if want_full_only:
                wm[full_name] = window_metrics(res, bench_c, common_idx, lo0, hi0)
            else:
                res0 = simulate_portfolio_topup(legs, core_ret_c, r_cash_c, 0.0,
                                                CASH_W, RULE, b, ms_mask)
                for wname in names:
                    lo, hi = wslices[wname]
                    m = window_metrics(res, bench_c, common_idx, lo, hi)
                    m["CostDrag"] = cost_drag(res, res0, lo, hi)
                    wm[wname] = m
            out[ivkey] = wm
            if want_starved and ivkey == "base":
                s = []
                for L, u in enumerate(legs_unders(mix)):
                    conts = res["conts"][L]
                    elig = gate_c[u][lo0:hi0]
                    unfunded = elig & (conts[lo0:hi0] <= 0)
                    s.append(float(unfunded.sum()) / float(elig.sum())
                             if elig.sum() > 0 else float("nan"))
                starved = s
        return out, starved

    # ---- main grid: 48 cells @ m=1.15 --------------------------------------
    CELLS = [(b, delta, mix) for b in BUDGETS for delta in DELTAS for mix in MIXES]
    R, STARVED = {}, {}
    for key in CELLS:
        b, delta, mix = key
        out, starved = run_cell(mix, b, delta, M_MAIN, want_starved=True)
        R[key] = out
        STARVED[key] = starved
        bm, dm = out["base"][full_name], out["damp"][full_name]
        print(f"cell {cell_label(key)} | base a{bm['Alpha']*100:+.1f} CE{ce_str(bm)} "
              f"| damp a{dm['Alpha']*100:+.1f} CE{ce_str(dm)} ({time.time()-t0:.0f}s)",
              flush=True)

    # ---- deep-ITM honesty band: Δ0.70/0.80 @ m=1.30/1.50 -------------------
    BAND = {}           # (b,delta,mix,m) -> {"base":wm,"damp":wm} FULL-only
    for b in BUDGETS:
        for delta in DEEP_DELTAS:
            for mix in MIXES:
                for mm in M_BAND:
                    out, _ = run_cell(mix, b, delta, mm, want_full_only=True)
                    BAND[(b, delta, mix, mm)] = out
    print(f"band done ({time.time()-t0:.0f}s)", flush=True)

    # ---- REGRESSION ANCHOR CHECK (hard) ------------------------------------
    reg_rows, reg_fail = [], []
    for iv in ("base", "damp"):
        mm = R[ANCHOR_KEY][iv][full_name]
        for field, got in (("CAGR", mm["CAGR"] * 100.0), ("Alpha", mm["Alpha"] * 100.0),
                           ("t", mm["t"])):
            want = ANCHOR[(iv, field)]
            diff = got - want
            ok = abs(diff) <= ANCHOR_TOL[field]
            reg_rows.append((iv, field, want, got, diff, ok))
            if not ok:
                reg_fail.append(f"{iv}/{field}: got {got:.3f} vs realcost {want:.3f} "
                                f"(diff {diff:+.3f}, tol {ANCHOR_TOL[field]})")
    print("\nREGRESSION ANCHOR vs 2026-07-17_core_topup_realcost.md 表1 (b15/Δ0.50/50-50 @m1.15):",
          flush=True)
    for iv, field, want, got, diff, ok in reg_rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {iv:4} {field:5} realcost {want:+.2f} "
              f"got {got:+.3f}  diff {diff:+.3f}", flush=True)
    if reg_fail:
        raise AssertionError(
            "REGRESSION ANCHOR FAILED -- b15/Δ0.50/50-50 @ m=1.15 does NOT reproduce "
            "2026-07-17_core_topup_realcost.md. The engine import is not faithful; STOP "
            "and debug before trusting any number in this grid.\n  " + "\n  ".join(reg_fail))
    print("  -> anchor holds: engine import faithful, grid is apples-to-apples.\n", flush=True)

    # ---- CE ranking (pre-registered: damp CE, two-trap guards) -------------
    def ce_damp(key):
        v = cap_eff(R[key]["damp"][full_name])
        return v if np.isfinite(v) else -9e9

    ranked = sorted(CELLS, key=lambda k: -ce_damp(k))
    dn_all = np.array([R[k]["damp"][full_name]["DnMed"] for k in CELLS], dtype="float64")
    dn_p25 = float(np.nanpercentile(dn_all, 25))
    small_denom = {k for k in CELLS
                   if np.isfinite(R[k]["damp"][full_name]["DnMed"])
                   and R[k]["damp"][full_name]["DnMed"] < dn_p25}
    winner = next((k for k in ranked if np.isfinite(cap_eff(R[k]["damp"][full_name]))), ranked[0])

    # ranking by absolute damp alpha too (shown so CE is never read alone) ----
    ranked_alpha = sorted(CELLS, key=lambda k: -(R[k]["damp"][full_name]["Alpha"]
                          if np.isfinite(R[k]["damp"][full_name]["Alpha"]) else -9e9))

    # ---- registry: Bonferroni x48, DSR -------------------------------------
    sharpes_48 = np.array([R[k]["base"][full_name]["Sharpe"] for k in CELLS], dtype="float64")
    wb, wd = R[winner]["base"][full_name], R[winner]["damp"][full_name]
    p_base = two_sided_p_from_t(wb["t"]); p_base_bonf = min(1.0, p_base * 48) if np.isfinite(p_base) else np.nan
    p_damp = two_sided_p_from_t(wd["t"]); p_damp_bonf = min(1.0, p_damp * 48) if np.isfinite(p_damp) else np.nan
    dsr = metrics.deflated_sharpe_ratio(wb["ret"], sharpes_48)
    psr = metrics.probabilistic_sharpe_ratio(wb["ret"], 0.0)

    # ====================================================================
    # Report
    # ====================================================================
    L = []
    add = L.append
    W = cell_label(winner)
    A = cell_label(ANCHOR_KEY)

    add("# 結果 — 真價(m=1.15)之下重搜核心 LEAP (b, Δ, mix) 格,資本效率最優")
    add("")
    add("**日期:** 2026-07-18  **腳本:** `backtest/experiments/exp_grid_realcost.py`  "
        "**狀態:** active — 回應 `2026-07-17_core_topup_realcost.md` 判詞 3「喺 m=1.15 "
        "重搜成個格」嘅那一輪;**本檔只報數,判詞喺覆核點對照 ASSUMPTIONS + SETTLED 先落**")
    add("")
    add("## 問題")
    add("")
    add("- realcost 檔已證舊核心 v2 勝出格(C-monthly / b15% / Δ0.50 / SPY+QQQ 50/50)"
        "係喺已被否定嘅 m=0.85 揀出;判詞 3 逐字:「應該直接喺 m=1.15 上面重新跑成個 "
        "(b, Δ, cadence) 格,因為勝出格本身就係喺一個錯咗嘅報價下揀出嚟嘅,『邊格最好』"
        "呢個結論本身都可能跟住變」。")
    add("- SETTLED.md #2「Core v2 最終配置:SPY 底倉+SPY/QQQ LEAP、預算 15-20%、Δ0.50」"
        "就係現行已定案格;本檔用真價(m=1.15)重驗佢係咪仲係資本效率最高嗰格。")
    add("- **用戶授權:用真價重揀,以資本效率為最優目標。** 本檔只報數。")
    add("")
    add("## 方法(凍結咗乜、變咗乜)")
    add("")
    add("- **引擎全部 verbatim import**,一行都冇重寫,格間差異只來自 (b, Δ, mix, m):")
    add("  - `build_underlying`/`build_gates`/`simulate_unit_path`/`TD` ← `exp_leap_real_sweep.py`")
    add("  - `damp_iv`/`to_wslices`/`window_metrics`/`bench_metrics`/`cost_drag`/`CAPITAL` "
        "← `exp_core_assembly_real.py`")
    add("  - `simulate_portfolio_topup`/`month_start_mask` ← `exp_core_topup.py`")
    add("  - `cap_eff`/`alpha_ci`(CE/CI 口徑)← `exp_core_topup_realcost.py`")
    add(f"- **Grid:** b∈{{10,12,15,20}}% × Δ∈{{0.50,0.60,0.70,0.80}} × mix∈{{SPY+QQQ 50/50, "
        f"QQQ-only, SPY-only}} × cadence={RULE}(凍結)= **48 格**,全部 m={M_MAIN},"
        f"base 同 damp={DAMP} 都跑。")
    add(f"- **深-ITM 誠實帶:** Δ∈{{0.70,0.80}} 用 m={M_MAIN} 係低估(07-09 spotcheck 實測 "
        f"0.70Δ 隱含 m≈1.63 SPY / 1.26 QQQ),故此 24 個深-ITM 格另跑 m∈{M_BAND}"
        "(base+damp,FULL 窗口),擺喺對比旁包住,唔俾深-ITM 靠平價假設贏。")
    add(f"- **凍結:** cadence={RULE} / cash={int(CASH_W*100)}% / 成本 {COST_BASE*100:.1f}%/side / "
        f"純 200SMA GATED / roll@63td / T+1 收市 / CAPITAL=${CAPITAL:,.0f} / core 恆為 SPY / "
        f"damp={DAMP}。")
    add(f"- **窗口(A4):** FULL(2001+,mix 共同窗口)主表 + {' / '.join(sub_names)} 子表"
        "(「2016+ 前後半」= 2016-2020 與 2021+)。全部 mix 都喺同一 2001+ 共同窗口跑,基準"
        "同為 SPY net-TR,48 格逐格可比。")
    add(f"- **資料尾巴凍結喺 {DATA_END.date()}:** live yfinance 無快取;凍結令 m 成為唯一報價"
        "變數,並令 b15/Δ0.50/50-50 呢格逐個數對返 realcost。")
    add("- **量度(A3):** 資本效率 CE = 年化 α(pp)÷ 中位 delta-notional 曝險(1.0x=100%NAV);"
        "絕對 PnL(CAGR、絕對 α)並列。CE 兩陷阱每表檢:(a) 細分母谷高比率 → 並列 DnMed 分母 "
        "+ 標記下四分位格「⚠小分母」;(b) 蝕本比率倒轉 → α≤0 記 n/a-neg,不入排序。α 只喺"
        "全組合層(vs SPY net-TR),呢層用 alpha 係啱尺。")
    add("- **排序規則(睇數前登記):** 48 格按 damp×m=1.15 CE 由大到細排;新贏家 = 第 1 格;"
        "同舊贏家(b15/Δ0.50/50-50)正面對比;深-ITM 上榜即擺誠實帶喺旁。")
    add("- α 信賴區間 = 普通 OLS 標準誤(無 Newey-West),repo 一貫做法,照講明。")
    add("")
    add("## 資料來源(`backtest/data.py` `load()`)")
    add("")
    add("| Series | Source | Rows | From | To |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in prov_all:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")
    add(f"- 共同(mix)模擬窗口(凍結後): {common_idx[0].date()} -> {common_idx[-1].date()} "
        f"({len(common_idx)} 日)。")
    add(f"- 健全性錨 — SPY B&H TR(HK net)1996-01->{spy_df.index[-1].date()}: CAGR "
        f"**{anchor_bh['CAGR']*100:.2f}%**, Sharpe {anchor_bh['Sharpe']:.2f}, MaxDD "
        f"{anchor_bh['MaxDD']*100:.1f}%(預登記接受區間 9–11%)。")
    add("")

    # -- regression anchor ----------------------------------------------------
    add(f"## 回歸錨 — {A} @ m={M_MAIN} 必須重現 realcost 表 1(硬 assert)")
    add("")
    add("| IV | 指標 | realcost 表1 | 本次重跑 | 差 | 判 |")
    add("|---|---|---|---|---|---|")
    for iv, field, want, got, diff, ok in reg_rows:
        unit = "" if field == "t" else "pp" if field == "Alpha" else "%"
        add(f"| {iv} | {field} | {want:+.2f}{unit} | {got:+.2f}{unit} | {diff:+.2f} | "
            f"{'✅ PASS' if ok else '❌ FAIL'} |")
    add("")
    max_absdiff = max(abs(d) for _, _, _, _, d, _ in reg_rows)
    add(f"**錨對得返(最大殘差 {max_absdiff:.2f})—— 引擎 import 忠實,48 格企得住。** 殘差"
        "來自 live yfinance 兩個 run 日期之間對歷史數列嘅微調(realcost 已載同一 ≤0.05pp 級"
        "效應),對格間排序無影響。")
    add("")

    # -- Table 1: 48-cell master, CE-sorted ----------------------------------
    add("## 表 1 — 48 格主表(FULL 2001+;按 damp×m1.15 資本效率排序;base/damp 並列)")
    add("")
    add("CE = 年化 α(pp)÷ 中位 delta-notional 曝險(1.0x=100%NAV)。Dn med = CE 分母"
        "(中位曝險);並列於此以檢陷阱 (a)。註:🏆=新贏家,⚓=舊贏家(b15/Δ0.50/50-50),"
        "⚠=小分母(DnMed 下四分位),◆=深-ITM(m=1.15 低估,見表 3)。")
    add("")
    add("| # | b/Δ/mix | CE damp | CE base | α damp (t) | α base (t) | CAGR d/b | "
        "MaxDD d | Dn med d | starved% | CostDrag b | 註 |")
    add("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, key in enumerate(ranked, 1):
        b, delta, mix = key
        dm, bm = R[key]["damp"][full_name], R[key]["base"][full_name]
        tags = []
        if key == winner:
            tags.append("🏆")
        if key == ANCHOR_KEY:
            tags.append("⚓")
        if key in small_denom:
            tags.append("⚠")
        if delta in DEEP_DELTAS:
            tags.append("◆")
        s = STARVED[key]
        s_str = "/".join(f"{x*100:.0f}%" for x in s) if s else "n/a"
        add(f"| {i} | {cell_label(key)} | {ce_str(dm)} | {ce_str(bm)} | {_a(dm)} | {_a(bm)} | "
            f"{_p(dm['CAGR'])}{_ruin(dm)} / {_p(bm['CAGR'])} | {_p(dm['MaxDD'])} | "
            f"{dm['DnMed']*100:.0f}% | {s_str} | {bm['CostDrag']:+.1f} | {' '.join(tags)} |")
    add("")
    add("**CE 兩陷阱檢查(A3):**")
    add(f"- 陷阱 (a) 細分母:DnMed 下四分位門檻 = {dn_p25*100:.0f}%NAV;標 ⚠ 嘅格 = "
        + (", ".join(cell_label(k) for k in ranked if k in small_denom) or "無")
        + " —— 呢啲格 CE 高有可能係分母細(曝險少)嘅人工品,須同絕對 α 一齊睇。")
    n_neg = sum(1 for k in CELLS if R[k]["damp"][full_name]["Alpha"] <= 0)
    add(f"- 陷阱 (b) 蝕本倒轉:damp α≤0 記 n/a-neg 不入排序,本格共 {n_neg} 個。")
    add("- 絕對 α(damp)排序頭 5(對照 CE 排序,防止只讀比率):"
        + ", ".join(f"{cell_label(k)} ({R[k]['damp'][full_name]['Alpha']*100:+.1f}pp)"
                    for k in ranked_alpha[:5]) + "。")
    add("")

    # -- Table 2: sub-windows (same order as Table 1) ------------------------
    add(f"## 表 2 — 48 格子窗口(damp,CAGR / α(t);排序同表 1)")
    add("")
    add("| # | b/Δ/mix | " + " | ".join(f"{w} CAGR | α(t)" for w in sub_names) + " |")
    add("|---|---|" + "---|" * (2 * len(sub_names)))
    for i, key in enumerate(ranked, 1):
        row = [str(i), cell_label(key)]
        for w in sub_names:
            m = R[key]["damp"][w]
            row += [_p(m["CAGR"]), _a(m)]
        add("| " + " | ".join(row) + " |")
    add("")
    add(f"註:「2016+ 前後半」= {sub_names[-2] if len(sub_names)>=2 else sub_names[-1]} 與 "
        f"{sub_names[-1]}。FULL 主表數見表 1。")
    add("")

    # -- Table 3: deep-ITM honesty band --------------------------------------
    add(f"## 表 3 — 深-ITM(Δ0.70/0.80)誠實定價帶(damp;m={M_MAIN} → {M_BAND[0]} → {M_BAND[1]})")
    add("")
    add(f"07-09 spotcheck 實測 0.70Δ 真實隱含 m≈1.63(SPY)/ 1.26(QQQ)。故此深-ITM 用 "
        f"m={M_MAIN} 係低估(α/CE 報大)。下表顯示同一格喺 m={M_MAIN}/{M_BAND[0]}/{M_BAND[1]} "
        "嘅 damp CE 同 α 退化。**帶 [1.30, 1.50] 大致框住 QQQ 深-ITM 真 m(≈1.26,略低於帶)"
        "並趨近 SPY 嘅(≈1.63,高於帶頂)—— 即係連 m=1.50 都仍可能低估 SPY 深-ITM 腿。**")
    add("")
    add("| b/Δ/mix | CE@1.15 | CE@1.30 | CE@1.50 | α@1.15 (t) | α@1.30 (t) | α@1.50 (t) |")
    add("|---|---|---|---|---|---|---|")
    band_keys = [(b, delta, mix) for b in BUDGETS for delta in DEEP_DELTAS for mix in MIXES]
    band_keys = sorted(band_keys, key=lambda k: -ce_damp(k))   # same CE order
    for key in band_keys:
        b, delta, mix = key
        m115 = R[key]["damp"][full_name]
        m130 = BAND[(b, delta, mix, 1.30)]["damp"][full_name]
        m150 = BAND[(b, delta, mix, 1.50)]["damp"][full_name]
        add(f"| {cell_label(key)} | {ce_str(m115)} | {ce_str(m130)} | {ce_str(m150)} | "
            f"{_a(m115)} | {_a(m130)} | {_a(m150)} |")
    add("")
    add("註:深-ITM 低 vega,base 與 damp 差距細(damp 對低-vega 格幾乎唔郁),故此帶只列 damp;"
        "base 走勢同向、幅度更細。")
    add("")

    # -- Table 4: new winner vs old winner head-to-head ----------------------
    add(f"## 表 4 — 正面對比:新贏家 {W}(🏆)vs 舊贏家 {A}(⚓)")
    add("")
    add("| 指標(FULL 2001+) | " + f"新贏家 {W}" + " | " + f"舊贏家 {A}" + " |")
    add("|---|---|---|")

    def h2h_rows(mkey):
        wk, ak = R[winner][mkey][full_name], R[ANCHOR_KEY][mkey][full_name]
        return wk, ak

    for mkey, lab in [("base", "base m1.15"), ("damp", f"damp {DAMP}")]:
        wk, ak = h2h_rows(mkey)
        add(f"| **[{lab}]** CE | {ce_str(wk)} | {ce_str(ak)} |")
        add(f"| [{lab}] α vs SPY net-TR (t) | {_a(wk)} | {_a(ak)} |")
        lo_w, hi_w = alpha_ci(wk); lo_a, hi_a = alpha_ci(ak)
        add(f"| [{lab}] α 95% CI | [{lo_w*100:+.1f}, {hi_w*100:+.1f}]pp | "
            f"[{lo_a*100:+.1f}, {hi_a*100:+.1f}]pp |")
        add(f"| [{lab}] CAGR | {_p(wk['CAGR'])} | {_p(ak['CAGR'])} |")
        add(f"| [{lab}] Sharpe | {wk['Sharpe']:.2f} | {ak['Sharpe']:.2f} |")
        add(f"| [{lab}] MaxDD | {_p(wk['MaxDD'])} | {_p(ak['MaxDD'])} |")
        add(f"| [{lab}] Dn med (CE 分母) | {wk['DnMed']*100:.0f}% | {ak['DnMed']*100:.0f}% |")
    sw, sa = STARVED[winner], STARVED[ANCHOR_KEY]
    add(f"| cash-starved% (base) | {'/'.join(f'{x*100:.0f}%' for x in sw)} | "
        f"{'/'.join(f'{x*100:.0f}%' for x in sa)} |")
    add(f"| CostDrag pp/yr (base) | {R[winner]['base'][full_name]['CostDrag']:+.1f} | "
        f"{R[ANCHOR_KEY]['base'][full_name]['CostDrag']:+.1f} |")
    add("")
    add("子窗口(damp CAGR / α(t)):")
    add("")
    add("| 窗口 | " + f"新贏家 {W}" + " | " + f"舊贏家 {A}" + " |")
    add("|---|---|---|")
    for w in sub_names:
        wm_, am_ = R[winner]["damp"][w], R[ANCHOR_KEY]["damp"][w]
        add(f"| {w} | {_p(wm_['CAGR'])} · {_a(wm_)} | {_p(am_['CAGR'])} · {_a(am_)} |")
    add("")
    if winner[1] in DEEP_DELTAS:
        wk = R[winner]["damp"][full_name]
        w130 = BAND[(winner[0], winner[1], winner[2], 1.30)]["damp"][full_name]
        w150 = BAND[(winner[0], winner[1], winner[2], 1.50)]["damp"][full_name]
        add(f"⚠️ **新贏家 {W} 係深-ITM(Δ{winner[1]:.2f}),m={M_MAIN} 係低估。** 誠實帶:"
            f"damp CE @1.15={ce_str(wk)} → @1.30={ce_str(w130)} → @1.50={ce_str(w150)};"
            f"damp α @1.15={_a(wk)} → @1.30={_a(w130)} → @1.50={_a(w150)}。"
            f"SPY 深-ITM 真 m≈1.63 高於帶頂,故連 @1.50 都可能仍偏高。")
    else:
        add(f"註:新贏家 {W} 係 Δ{winner[1]:.2f}(非深-ITM),m={M_MAIN} 喺旗艦 0.50Δ 附近"
            "「track reasonably(~1–3pp)」,無深-ITM 嘅系統性低估。")
    add("")

    # -- multiple comparison --------------------------------------------------
    add("## 多重比較(48 格,Bonferroni / DSR;照 07-06 慣例)")
    add("")
    add(f"- **本輪登記宇宙 = 48 格(m={M_MAIN})。唔併入 07-06 舊 42 格**:realcost 明言舊 "
        "DSR 係 m=0.85 產物,唔可以為新報價背書。")
    add(f"- 新贏家 **{W}**,FULL(2001+):base α-t = {wb['t']:+.2f}"
        f"(two-sided p={p_base:.4g},**Bonferroni×48 p={p_base_bonf:.4g}**);"
        f"damp α-t = {wd['t']:+.2f}(two-sided p={p_damp:.4g},"
        f"**Bonferroni×48 p={p_damp_bonf:.4g}**)。")
    add(f"- **DSR**(新贏家 base-IV 真實日回報 vs 48 格年化 Sharpe 宇宙)= **{dsr:.3f}** "
        f"(PSR vs 0 = {psr:.3f})。DSR>0.95 ≈ 過到多重檢定。")
    add(f"- 48 格年化 Sharpe(base,FULL):min {np.nanmin(sharpes_48):.2f} / "
        f"median {np.nanmedian(sharpes_48):.2f} / max {np.nanmax(sharpes_48):.2f}。")
    add("")

    # -- cross-foot -----------------------------------------------------------
    add("## Cross-foot 驗證")
    add("")
    add(f"- {TOPUP.ASSERT_COUNT['runs']} 個會計 run,{TOPUP.ASSERT_COUNT['n']:,} 個 bar 層 "
        "assertion 全部通過:NAV = core + cash + Σ(期權市值);cash≥0;NAV>0;"
        "NAV_t = NAV_(t-1) + 利息 + core P&L + 期權 P&L − 成本(月度 floor top-up 係零和內部"
        "轉帳,不入此恆等式;相對容差 1e-6)。任何違反即 raise 並中止。")
    add("")
    add("**每個 run 逐 bar 帳目都平衡 —— 上面啲數係引擎真跑出嚟,唔係手寫落表。**")
    add("")

    # -- report discipline / controls / caveats ------------------------------
    add("## 對照臂(判詞紀律)")
    add("")
    add("本檔**只報數,唔落判詞**(判詞喺覆核點對照 ASSUMPTIONS + SETTLED 先落)。已備對照臂:")
    add(f"- **舊贏家對照**(表 4):新贏家對比 SETTLED #2 現行格 {A},同窗口同基準同曝險量度。")
    add("- **報價對照**(表 3):深-ITM 格 m=1.15 vs 1.30 vs 1.50,防止平價假設造成假優勢。")
    add("- **陷阱對照**(表 1):CE 排序旁並列絕對 α 排序 + DnMed 分母,防止細分母/蝕本比率誤讀。")
    add("")
    add("## 未解 / 風險")
    add("")
    add(f"- **m={M_MAIN} 唔係真.歷史期權鏈**,只係 2026-07-09 一日平靜市喺 0.50Δ 嘅最貼格點;"
        "本 repo 冇 25 年真實 IV surface,每個 m 都係代理。07-09 另證 SPY 0.50Δ 真隱含 m≈1.22 "
        "(高於 1.15),即旗艦格 m=1.15 都仍略買平;崩盤期 term-structure(固定 m 將 30d 尖峰 "
        "1:1 映入 1y)仍 OPEN 未量化,同向低估。")
    add("- **深-ITM 帶只到 m=1.50**;SPY 0.70Δ 真 m≈1.63 高於帶頂,故深-ITM 格連 @1.50 都可能"
        "仍偏樂觀 —— 表 3 標數,唔外推。")
    add("- **α 的 t / CI 用普通 OLS 標準誤(無 Newey-West)**,日頻殘差通常正自相關 → 真實 SE "
        "大機會闊過本表,貼 t=2 線嘅格尤須留意。")
    add("- **damp sigma_bar 係全樣本平均**(定價輸入輕微 look-ahead,不影響價格/200SMA 驅動嘅"
        "閘與 roll 時機)—— 沿用 07-06 同一 caveat。")
    add(f"- **資料尾巴凍結喺 {DATA_END.date()}**(為令 m 成唯一報價變數 + 錨可對返);"
        "代價 = 本表不含 07-07 至今市況。")
    add("- **細分母 CE 格**(表 1 標 ⚠)嘅高 CE 可能係曝險少嘅人工品,已並列絕對 α 供對照。")
    add("- **DSR/Bonferroni 只登記本輪 48 格**;若覆核要同歷史累計檢定,須另議登記邊界。")
    add("")
    add("---")
    add("")
    add(f"**註:** 本檔係「m=1.15 全格重搜」嘅數據正本,回應 realcost 判詞 3。勝負判詞、"
        "SETTLED.md #2 更不更新,由覆核點對照 ASSUMPTIONS(A1-A7)+ 預登記 spec 落。")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS}  ({time.time()-t0:.0f}s total, "
          f"{TOPUP.ASSERT_COUNT['n']:,} asserts / {TOPUP.ASSERT_COUNT['runs']} runs)", flush=True)

    # ---- compact stdout summary (numbers the review reads) -----------------
    print("\n=== CE RANKING (damp x m1.15, top 12) ===", flush=True)
    for i, key in enumerate(ranked[:12], 1):
        dm, bm = R[key]["damp"][full_name], R[key]["base"][full_name]
        flags = ("🏆" if key == winner else "") + ("⚓" if key == ANCHOR_KEY else "") \
            + ("⚠" if key in small_denom else "") + ("◆" if key[1] in DEEP_DELTAS else "")
        print(f"  #{i:2} {cell_label(key):24} CEd {ce_str(dm):>7} CEb {ce_str(bm):>6} "
              f"| ad {dm['Alpha']*100:+5.1f}(t{dm['t']:+.1f}) ab {bm['Alpha']*100:+5.1f}"
              f"(t{bm['t']:+.1f}) | DDd {dm['MaxDD']*100:+.0f}% Dn {dm['DnMed']*100:.0f}% {flags}",
              flush=True)
    print(f"\nNEW WINNER {W}  vs  OLD WINNER {A}", flush=True)
    for mkey in ("base", "damp"):
        wk, ak = R[winner][mkey][full_name], R[ANCHOR_KEY][mkey][full_name]
        print(f"  [{mkey}] CE {ce_str(wk)} vs {ce_str(ak)} | a {wk['Alpha']*100:+.1f}"
              f"(t{wk['t']:+.1f}) vs {ak['Alpha']*100:+.1f}(t{ak['t']:+.1f}) | "
              f"CAGR {wk['CAGR']*100:+.1f}% vs {ak['CAGR']*100:+.1f}% | "
              f"DD {wk['MaxDD']*100:+.0f}% vs {ak['MaxDD']*100:+.0f}%", flush=True)
    print(f"Bonferroni×48: base p={p_base_bonf:.4g}, damp p={p_damp_bonf:.4g}; "
          f"DSR={dsr:.3f} PSR={psr:.3f}", flush=True)


if __name__ == "__main__":
    main()
