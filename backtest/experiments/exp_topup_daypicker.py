"""按 ASSUMPTIONS.md(2026-07-17 版),遵守 A1-A7 —— 核心 v2 月度 top-up「揀日器」A/B/C
(現行月初 vs RSI2 揀日 vs 隨機對照)

背景(未跑過嘅增量 —— 呢個先係本檔存在嘅原因)
------
`2026-07-17_rsi2_connors_settle.md` §7d/7e 判「RSI2 撈底做獨立 sleeve 錢細撐唔起注碼,但有
一個位用得著:core v2 月度 top-up 嘅入場擇日器」,並且明文話「呢個係一條可以直接 A/B 嘅增量
……本報告唔宣稱佢有效 —— 只宣稱佢係唯一一個值得跑嘅 RSI2 用法」。`SETTLED.md` #13d 將呢句
收咗做 settled,但 §7e 自己都寫明「OPEN —— 呢條未跑,唔可以收檔」。本檔就係跑呢條增量。

⚠️ 唔好同 `2026-07-07_topup_timing_ab.md` 嘅 Rule E 混淆:
  - Rule E 嘅設計 = 「RSI2 訊號完全取代月曆」——冇訊號嗰個月 = 零 top-up。結果:同月曆
    alpha 打和,但流動性明顯差咗(cash-starved% 15%/14% vs C-monthly 嘅 10%/7%)。
  - 本檔嘅設計 = 「月曆保底,揀日淨係決定嗰個月入面邊一日」——每個月保證都有一次
    top-up,冇 Rule E 嗰種 starvation 風險。呢個係完全唔同嘅假設,唔係 Rule E 嘅重跑。

問題
------
core v2 已定案嘅勝出格(C-monthly / b=15% NAV / Δ=0.50 / SPY+QQQ 50/50)而家嘅月度
top-up 揀「每月第一個交易日」。用 SPY RSI2(Wilder)嚟揀「嗰個月入面邊一日」top-up,
會唔會攞到更平嘅入市價 / 更好嘅資本效率?三臂,**唯一變數 = 揀邊一日**:

  A(現行)   ── 每月首個交易日 top-up(`month_start_mask`,IMPORTED verbatim,原封不動)。
  B(揀日器) ── 當月首個「SPY RSI2(Wilder) < 10」exec 日 top-up(signal close T -> exec
              T+1,同 `2026-07-07_topup_timing_ab.md` Rule E 一致嘅 convention);
              成個月都冇訊號 -> 月尾最後交易日照入(保底,唔會 starve,同 Rule E 嘅
              「零 top-up」設計不同)。
  C(對照)   ── 當月隨機一個交易日 top-up,1000 次 Monte Carlo 攞分佈(seed 20260718)。
              **B 要贏 C 先算訊號 —— 淨係贏 A 唔算數**,因為 A 只係「現行慣例」,
              唔係一把中性嘅隨機尺(呼應 `2026-07-17_rsi2_connors_settle.md` 用隨機
              同曝險對照嚟判 RSI2 訊號嗰個紀律)。

方法(mirror / increment / horizon)
------
Mirror    : 同 `exp_core_topup.py` 個勝出格一模一樣嘅三桶程式(SPY 底倉 + SPY/QQQ 50/50
            LEAP sleeve、純 200SMA GATED entry、cash buffer),同一組真實
            ^VIX/^VXN/^IRX 數據,同一個 benchmark(SPY B&H total return,HK 30% 股息
            預扣淨額)。
Increment : 淨係 top-up 嘅「揀邊一日」trigger mask 係新嘅。引擎全部 verbatim import,
            一行都冇重寫:
              - `simulate_unit_path` / `build_underlying` / `build_gates` / `TD`
                                                          <- exp_leap_real_sweep.py
              - `damp_iv` / `to_wslices` / `window_metrics` / `bench_metrics` / `CAPITAL`
                                                          <- exp_core_assembly_real.py
              - `simulate_portfolio_topup` / `cell_label` / `month_start_mask` /
                `CASH_W` / `COST_BASE` / `DAMP`           <- exp_core_topup.py(Arm A
                                                             原封不動用返呢個 mask)
              - `cap_eff` / `alpha_ci`                    <- exp_core_topup_realcost.py
            (同 `exp_core_topup_realcost.py` 07-17 示範嘅「唯一變數」手法一樣:凍結
            成個引擎,淨係換一個 trigger mask 函數。)
Horizon   : 連續多年程式;LEAP 63td roll(引擎預設,不變);b=15% NAV、Δ=0.50、
            SPY+QQQ 50/50、cash=15%,全部凍結喺勝出格本身嘅設定,唔重新搜格。

凍結(唔重新搜格 —— 呢個唔係新 grid search)
------
  cadence = 月度(三臂都保證每月一次,只係揀邊一日) | b = 15% NAV | Delta = 0.50 |
  mix = SPY+QQQ 50/50 | gate(LEAP entry) = 純 200SMA GATED | roll @ 63td |
  cost = 0.5%/side | CAPITAL = $500,000 | cash weight = 15% |
  RSI2 門檻 = <10(同 `2026-07-07_topup_timing_ab.md` Rule E 一致,唔係 Connors 原著
  嘅 <5 —— 本檔唔重新試門檻,跟返用戶指定嘅 <10)。
  **m = 1.15**(A5:`2026-07-09_options_chain_spotcheck.md` 證咗 m=0.85 偏低;
  `2026-07-17_core_topup_realcost.md` 定咗 m=1.15 做「唔准做判詞」以外嘅誠實假設 ——
  本檔跟返呢個,唔再用 m=0.85)。base 同 damp=0.4 兩個 IV 處理都跑(`damp_iv()` 同一個
  方法,verbatim import)。
  **200SMA 唔係揀日器本身嘅入場濾網**(A2:用戶裁決 200SMA 唔再做「入場濾網」通用角色,
  趨勢閘淨係保留喺「LEAP 呢類槓桿工具嘅防爆倉」——LEAP 自己嘅 GATED entry 已經做緊
  呢個角色;RSI2 揀日訊號本身唔疊多一層 200SMA 條件)。

窗口(A4)
------
FULL(common window 原生起點,2001+)PRIMARY + 2016+ 前後半:**2016-2020**(前半)/
**2021+**(後半)—— 沿用 `exp_core_topup.py` / `exp_core_topup_realcost.py` 嗰組
`to_wslices()` 命名窗口,唔新開視窗邏輯。

量度(A3)
------
每一格(A、B,以及 C 嘅 1000 次分佈)喺以上 3 個窗口都報:**資本效率**(`cap_eff()`,
alpha(pp) / DnMed 中位 delta-notional 曝險,verbatim import,alpha<=0 標 n/a-neg)
+ **絕對 PnL**($,窗口自身以 CAPITAL 重新 rebase,同 `window_metrics()` 計 CAGR 用嗰個
rebase 一致)並列;**alpha 喺呢層用係啱尺**(全組合層:core v2 vs SPY net-TR,唔係
sleeve/訊號層,ASSUMPTIONS A3);MaxDD;cash-starved%(SPY 腿/QQQ 腿,沿用
`exp_core_topup.py` 嘅定義 —— base IV only,同 repo 既有慣例一致)。

直觀數(唯一嘅「單一數字」輸出)
------
「B 平均每年執平幾多入市價 bp」:逐月攞 A 揀嗰日同 B 揀嗰日嘅 SPY 收巿價,
(price_A - price_B) / price_A * 10000 = 嗰個月嘅 bp 優勢(正 = B 果日買平咗),
全期平均後 x 12 = 每年平均 bp。C 嘅 1000 次分佈做返同一個計算(A vs 每次隨機抽樣),
俾一個「隨機揀日期望上應該貼近 0」嘅對照,同 B 自己嗰個數擺埋一齊比較(百分位)。

判詞紀律
------
**本檔只報數,唔落判詞**(用戶明令)。全文唔用「有料」/「冇料」/「SETTLED」/「建議」
呢類判詞字眼;數表 + 中性描述,覆核留返俾人手。本次結果亦**唔寫入** `SETTLED.md`
(任務範圍只准新增呢兩個檔 —— .py 同 .md;要覆核 #13d 留返俾後續任務/人手決定)。

Run:  PYTHONUTF8=1 python backtest/experiments/exp_topup_daypicker.py
Writes: backtest/results/2026-07-18_topup_daypicker.md
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import load                              # noqa: E402
from exp_leap_real_sweep import (                  # noqa: E402
    build_underlying, build_gates, simulate_unit_path, TD,
)
from exp_core_assembly_real import (               # noqa: E402
    damp_iv, to_wslices, window_metrics, bench_metrics, _p, _a, _ruin, CAPITAL,
)
import exp_core_topup as TOPUP                      # noqa: E402
from exp_core_topup import (                       # noqa: E402
    simulate_portfolio_topup, cell_label, month_start_mask, CASH_W, COST_BASE, DAMP,
)
from exp_core_topup_realcost import cap_eff, alpha_ci   # noqa: E402

# ---- 凍結嘅勝出格設定(唔重新搜格,見 docstring) ---------------------------
B_BUDGET = 0.15
DELTA = 0.50
IV_M = 1.15                 # A5: m=0.85 已知偏低;m=1.15 = 誠實假設(realcost 檔已證)
RSI_THRESH = 10.0           # 同 `2026-07-07_topup_timing_ab.md` Rule E 一致
N_SIMS = 1000
SEED = 20260718

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-18_topup_daypicker.md")

# CITED 對照:`2026-07-17_core_topup_realcost.md` 表1 嘅 m=1.15 格(Arm A 呢度嘅設定
# 同嗰格機制上完全一樣,只係資料尾巴唔同凍結日 —— 用嚟做回歸檢查,唔係重新引用判詞)。
CITED_A = {
    "base": {"CAGR": 17.4, "Alpha": 9.0, "t": 4.9, "MaxDD": -52.2},
    "damp": {"CAGR": 11.7, "Alpha": 3.0, "t": 2.0, "MaxDD": -53.6},
    "starved": [0.10, 0.08],   # SPY-leg / QQQ-leg, base IV, FULL window
}
REG_TOL = {"CAGR": 0.5, "Alpha": 0.5, "t": 0.4}   # pp / t-units；容許少少 live-data 尾巴漂移


# ---------------------------------------------------------------------------
# Trigger masks(唯一變數)—— A 用返 exp_core_topup.month_start_mask,原封不動
# ---------------------------------------------------------------------------

def build_month_groups(index: pd.DatetimeIndex) -> list[np.ndarray]:
    """逐月嘅 bar-position 陣列。月轉字判斷同 `month_start_mask` 完全一致(淨比較
    `.month`,唔比較 `.year` —— 連續交易日曆下呢個判斷本身已經冇歧義)。第一格 = 第一個
    (局部)月,同 `month_start_mask` 一樣唔會喺呢格觸發 top-up。
    """
    n = len(index)
    mo = index.month.values
    start_mask = np.zeros(n, dtype=bool)
    if n > 1:
        start_mask[1:] = mo[1:] != mo[:-1]
    starts = np.where(start_mask)[0].tolist()
    bounds = [0] + starts + [n]
    return [np.arange(bounds[j], bounds[j + 1]) for j in range(len(bounds) - 1)]


def build_daypicker_mask(groups: list[np.ndarray], exec_signal: np.ndarray,
                         n: int) -> tuple[np.ndarray, np.ndarray]:
    """Arm B:逐月首個 exec_signal=True 嘅日;成個月冇 -> 月尾最後交易日(保底)。"""
    out = np.zeros(n, dtype=bool)
    was_hit = np.zeros(len(groups), dtype=bool)
    for gi, g in enumerate(groups):
        hits = np.where(exec_signal[g])[0]
        if len(hits):
            out[g[hits[0]]] = True
            was_hit[gi] = True
        else:
            out[g[-1]] = True
    return out, was_hit


def sample_random_mask(groups: list[np.ndarray], rng: np.random.Generator, n: int) -> np.ndarray:
    """Arm C(單次抽樣):逐月隨機一個交易日。"""
    out = np.zeros(n, dtype=bool)
    for g in groups:
        out[g[rng.integers(0, len(g))]] = True
    return out


# ---------------------------------------------------------------------------
# 報表用嘅細量度(全部由已驗證嘅引擎輸出/`metrics.py` 原生函數推導,唔重寫引擎本身)
# ---------------------------------------------------------------------------

def dollar_pnl(res: dict, lo: int, hi: int, capital: float = CAPITAL) -> float:
    """窗口自身 rebase 到 CAPITAL 之後嘅絕對 $ PnL(同 `window_metrics()` 計 CAGR
    用嗰個 `navw/navw[0]*CAPITAL` rebase 一致,純粹加一步減返 CAPITAL)。
    """
    navw = res["nav"][lo:hi]
    return float(navw[-1] / navw[0] * capital - capital)


def starved_pct(res: dict, gates: list[np.ndarray], lo: int, hi: int) -> list[float]:
    """cash-starved% = 該腿自己 200SMA 閘話可以持倉嘅日子入面,實際揸 0 張嘅比例
    (定義同 `exp_core_topup.py` Table 3 一致)。"""
    out = []
    for L, g in enumerate(gates):
        conts = res["conts"][L]
        elig = g[lo:hi]
        unfunded = elig & (conts[lo:hi] <= 0)
        out.append(float(unfunded.sum()) / float(elig.sum()) if elig.sum() > 0 else float("nan"))
    return out


def bp_advantage_series(spy_close: np.ndarray, mask_ref: np.ndarray, mask_cmp: np.ndarray,
                        index: pd.DatetimeIndex) -> pd.Series:
    """逐月 (price_ref - price_cmp)/price_ref * 10000,以 mask_ref 揀嗰日嘅日期做索引。
    正數 = mask_cmp 揀嗰日嘅 SPY 收巿價平過 mask_ref。兩個 mask 必須逐月各揀剛好一日
    (build_month_groups + build_daypicker_mask/sample_random_mask/month_start_mask
    三個都符合呢個不變量),否則屬於上游 bug,直接 raise。
    """
    pos_ref = np.where(mask_ref)[0]
    pos_cmp = np.where(mask_cmp)[0]
    if len(pos_ref) != len(pos_cmp):
        raise AssertionError(
            f"mask 揀選日數目對唔上: ref={len(pos_ref)} cmp={len(pos_cmp)} —— "
            "逐月剛好一日嘅不變量被打破,停低查。")
    p_ref = spy_close[pos_ref]
    p_cmp = spy_close[pos_cmp]
    bp = (p_ref - p_cmp) / p_ref * 10000.0
    return pd.Series(bp, index=index[pos_ref])


def bp_year(bp_series: pd.Series, lo_date, hi_date) -> float:
    s = bp_series[(bp_series.index >= lo_date) & (bp_series.index <= hi_date)]
    if len(s) == 0:
        return float("nan")
    return float(s.mean()) * 12.0


def pct_rank(value: float, dist) -> float:
    """value 喺 dist(通常係 1000 次 MC 分佈)入面嘅百分位:dist 入面有幾多%
    <= value。"""
    d = np.asarray(dist, dtype="float64")
    d = d[np.isfinite(d)]
    if len(d) == 0 or value is None or not np.isfinite(value):
        return float("nan")
    return float((d <= value).mean() * 100.0)


def pctiles(dist) -> dict:
    d = np.asarray(dist, dtype="float64")
    d = d[np.isfinite(d)]
    if len(d) == 0:
        return {k: float("nan") for k in ("p5", "p25", "p50", "p75", "p95")}
    return {"p5": float(np.percentile(d, 5)), "p25": float(np.percentile(d, 25)),
            "p50": float(np.percentile(d, 50)), "p75": float(np.percentile(d, 75)),
            "p95": float(np.percentile(d, 95))}


def _ce(m: dict) -> str:
    ce = cap_eff(m)
    if np.isfinite(ce):
        return f"{ce:+.1f}"
    a = m.get("Alpha")
    return "n/a-neg" if (a is not None and np.isfinite(a) and a <= 0) else "n/a"


def _ci(m: dict) -> str:
    lo, hi = alpha_ci(m)
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return "n/a"
    return f"[{lo*100:+.1f}, {hi*100:+.1f}]pp"


def _usd(x: float) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"${x:,.0f}"


def _pctfmt(x: float, dec: int = 1) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.{dec}f}%"


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
        df, prov, _r_net_full = build_underlying(under, volsym, irx)
        data[under] = {"df": df}
        prov_all += prov
        print(f"{under} joined: {df.index[0].date()} -> {df.index[-1].date()}, "
              f"{len(df)} days", flush=True)

    spy_df, qqq_df = data["SPY"]["df"], data["QQQ"]["df"]
    common_idx = spy_df.index.intersection(qqq_df.index)
    n_common = len(common_idx)
    print(f"common (mix) window: {common_idx[0].date()} -> {common_idx[-1].date()}, "
          f"{n_common} days", flush=True)

    for under, df in [("SPY", spy_df), ("QQQ", qqq_df)]:
        d = data[under]
        d["close"] = df["close"].values
        d["vol"] = df["vol"].values
        d["r_arr"] = df["irx"].values / 100.0
        d["q_arr"] = df["q"].values
        d["r_cash"] = d["r_arr"] / TD
        d["gate"] = build_gates(df)["GATED"]
        d["r_net"] = df["r_net"].values
        d["rsi2"] = df["rsi2"]     # pd.Series, native index, Wilder RSI-2 (verbatim)

    a_mask = spy_df.index >= "1996-01-01"
    a_lo = int(np.where(a_mask)[0][0])
    anchor = bench_metrics(spy_df["r_net"].values, a_lo, len(spy_df))
    print(f"SANITY SPY B&H TR (HK net) 1996->end: CAGR {anchor['CAGR']*100:.2f}% "
          f"Sharpe {anchor['Sharpe']:.2f} MaxDD {anchor['MaxDD']*100:.1f}%", flush=True)

    # ------------------------------------------------------------------
    # Unit paths:m=1.15 凍結,base + damp=0.4,2 個標的 = 4 次 simulate_unit_path
    # (呢個同 top-up 揀邊一日完全無關 —— gate/option path 淨係食價同 IV,喺三臂
    # 之間 100% 共用,只計一次)
    # ------------------------------------------------------------------
    base_paths, damped_paths = {}, {}
    for under in ("SPY", "QQQ"):
        d = data[under]
        iv_raw = d["vol"] / 100.0 * IV_M
        iv_damped = damp_iv(iv_raw, DAMP)
        base_paths[under] = simulate_unit_path(
            d["close"], iv_raw, d["r_arr"], d["q_arr"], d["gate"], DELTA)
        damped_paths[under] = simulate_unit_path(
            d["close"], iv_damped, d["r_arr"], d["q_arr"], d["gate"], DELTA)
    print(f"unit paths (base+damp x SPY/QQQ, m={IV_M}) done ({time.time()-t0:.0f}s)", flush=True)

    native_index = {"SPY": spy_df.index, "QQQ": qqq_df.index}

    def unit_slice(under, paths_dict, index_target):
        udf = pd.DataFrame(paths_dict[under], index=native_index[under])
        sl = udf.reindex(index_target)
        return {k: sl[k].values for k in udf.columns}

    spy_close_c = pd.Series(data["SPY"]["close"], index=spy_df.index).reindex(common_idx).values
    qqq_close_c = pd.Series(data["QQQ"]["close"], index=qqq_df.index).reindex(common_idx).values
    core_ret_c = pd.Series(data["SPY"]["r_net"], index=spy_df.index).reindex(common_idx).values
    r_cash_c = pd.Series(data["SPY"]["r_cash"], index=spy_df.index).reindex(common_idx).values
    bench_c = core_ret_c    # Jensen-alpha benchmark = SPY net-TR(同核心 sleeve 自己嘅回報)
    gate_spy_c = pd.Series(data["SPY"]["gate"], index=spy_df.index).reindex(common_idx).values.astype(bool)
    gate_qqq_c = pd.Series(data["QQQ"]["gate"], index=qqq_df.index).reindex(common_idx).values.astype(bool)
    gates_c = [gate_spy_c, gate_qqq_c]

    def legs_for(paths_dict):
        u_spy = unit_slice("SPY", paths_dict, common_idx)
        u_qqq = unit_slice("QQQ", paths_dict, common_idx)
        return [{"b": B_BUDGET / 2.0, "unit": u_spy, "close": spy_close_c},
                {"b": B_BUDGET / 2.0, "unit": u_qqq, "close": qqq_close_c}]

    legs_base = legs_for(base_paths)
    legs_damp = legs_for(damped_paths)

    # ------------------------------------------------------------------
    # 窗口(A4):FULL + 2016-2020(前半)+ 2021+(後半)
    # ------------------------------------------------------------------
    wslices_all = to_wslices("QQQ", common_idx)
    wslices = {name: (lo, hi) for name, lo, hi in wslices_all
              if name.startswith("FULL") or name.startswith("2016") or name.startswith("2021")}
    full_name = [n for n in wslices if n.startswith("FULL")][0]
    window_order = [full_name, "2016-2020", "2021+"]
    window_bounds = {wname: (common_idx[lo], common_idx[hi - 1]) for wname, (lo, hi) in wslices.items()}
    print(f"windows: {window_order}", flush=True)

    # ------------------------------------------------------------------
    # RSI2 day-picker 訊號(Arm B):signal close T -> exec T+1,同 Rule E 一致
    # ------------------------------------------------------------------
    spy_rsi2_native = data["SPY"]["rsi2"]
    raw_sig_native = (spy_rsi2_native < RSI_THRESH)
    exec_sig_native = raw_sig_native.shift(1).fillna(False).astype(bool)
    exec_sig_c = exec_sig_native.reindex(common_idx).fillna(False).values.astype(bool)

    groups = build_month_groups(common_idx)
    groups_topup = groups[1:]     # 第一個(局部)月冇 top-up,同 month_start_mask 一致
    n_months = len(groups_topup)

    mask_A = month_start_mask(common_idx)
    mask_B, was_hit_B = build_daypicker_mask(groups_topup, exec_sig_c, n_common)

    n_A, n_B = int(mask_A.sum()), int(mask_B.sum())
    if not (n_A == n_B == n_months):
        raise AssertionError(f"逐月剛好一次 top-up 嘅不變量被打破: n_A={n_A} n_B={n_B} "
                             f"n_months={n_months}")
    print(f"月份總數(去頭嗰個局部月)={n_months}, A/B 各觸發 {n_A}/{n_B} 次(一致)", flush=True)

    # ------------------------------------------------------------------
    # Arm A / Arm B:確定性單次跑(base + damp)
    # ------------------------------------------------------------------
    def run_topup(trigger_mask, rule_id):
        res_base = simulate_portfolio_topup(legs_base, core_ret_c, r_cash_c, COST_BASE,
                                            CASH_W, rule_id, B_BUDGET, trigger_mask)
        res_damp = simulate_portfolio_topup(legs_damp, core_ret_c, r_cash_c, COST_BASE,
                                            CASH_W, rule_id, B_BUDGET, trigger_mask)
        return res_base, res_damp

    resA_base, resA_damp = run_topup(mask_A, "A-monthcal")
    resB_base, resB_damp = run_topup(mask_B, "B-daypicker")
    print(f"Arm A/B 跑完 ({time.time()-t0:.0f}s)", flush=True)

    def arm_metrics(res_base, res_damp):
        out = {}
        for wname in window_order:
            lo, hi = wslices[wname]
            mb = window_metrics(res_base, bench_c, common_idx, lo, hi)
            md = window_metrics(res_damp, bench_c, common_idx, lo, hi)
            s = starved_pct(res_base, gates_c, lo, hi)
            out[wname] = {
                "base": mb, "damp": md,
                "pnl_base": dollar_pnl(res_base, lo, hi),
                "pnl_damp": dollar_pnl(res_damp, lo, hi),
                "starved": s,
            }
        return out

    metricsA = arm_metrics(resA_base, resA_damp)
    metricsB = arm_metrics(resB_base, resB_damp)

    # ------------------------------------------------------------------
    # 回歸檢查:Arm A(m=1.15)理應接近重現 `2026-07-17_core_topup_realcost.md`
    # 表1 嘅 m=1.15 格(機制完全一樣,淨係 live 資料尾巴日期唔同)
    # ------------------------------------------------------------------
    reg_rows = []
    for ivkey in ("base", "damp"):
        mm = metricsA[full_name][ivkey]
        for field, got in (("CAGR", mm["CAGR"] * 100.0), ("Alpha", mm["Alpha"] * 100.0),
                          ("t", mm["t"])):
            want = CITED_A[ivkey][field]
            diff = got - want
            ok = abs(diff) <= REG_TOL[field]
            reg_rows.append((ivkey, field, want, got, diff, ok))
    reg_fail = [r for r in reg_rows if not r[5]]
    print("回歸檢查 vs 2026-07-17_core_topup_realcost.md(m=1.15):", flush=True)
    for ivkey, field, want, got, diff, ok in reg_rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {ivkey:5} {field:5} 已刊 {want:+.2f} "
              f"本次 {got:+.3f} 差 {diff:+.3f}", flush=True)
    if reg_fail:
        raise AssertionError(
            "回歸檢查失敗 —— Arm A(m=1.15)未能重現 2026-07-17_core_topup_realcost.md "
            "嘅 m=1.15 格,引擎 import 可能有問題,停低查:\n  "
            + "\n  ".join(f"{i}/{f}: 已刊{w:+.2f} 本次{g:+.3f} 差{d:+.3f}"
                         for i, f, w, g, d, _ in reg_fail))
    print("  -> 全部 PASS(容差內)—— 引擎接線正確,下面 A/B/C 對照企得住。", flush=True)

    # ------------------------------------------------------------------
    # 直觀數:B 相對 A 嘅入市價優勢(bp/年)—— 逐窗口
    # ------------------------------------------------------------------
    bp_series_AB = bp_advantage_series(spy_close_c, mask_A, mask_B, common_idx)
    bp_year_AB = {wname: bp_year(bp_series_AB, *window_bounds[wname]) for wname in window_order}

    # ------------------------------------------------------------------
    # Arm B 揀日診斷:逐月係咪撈中 RSI2<10,定係跌落月尾保底
    # ------------------------------------------------------------------
    chosen_pos_B = np.where(mask_B)[0]
    chosen_dates_B = common_idx[chosen_pos_B]
    offsets_B = np.array([pos - g[0] for pos, g in zip(chosen_pos_B, groups_topup)])
    diag_B = pd.DataFrame({"hit": was_hit_B, "offset": offsets_B}, index=chosen_dates_B)

    def diag_window(wname):
        lo_d, hi_d = window_bounds[wname]
        sub = diag_B[(diag_B.index >= lo_d) & (diag_B.index <= hi_d)]
        total = len(sub)
        hits = int(sub["hit"].sum())
        mean_off = float(sub["offset"].mean()) if total else float("nan")
        return total, hits, total - hits, mean_off

    diag_rows = {wname: diag_window(wname) for wname in window_order}

    # ------------------------------------------------------------------
    # Arm C:1000 次 Monte Carlo(逐月隨機一個交易日),base+damp 都跑
    # ------------------------------------------------------------------
    rng = np.random.default_rng(SEED)
    mc = {wname: {"capeff_base": [], "capeff_damp": [], "pnl_base": [], "pnl_damp": [],
                 "alpha_base": [], "alpha_damp": [], "maxdd_base": [], "maxdd_damp": [],
                 "starved_spy": [], "starved_qqq": [], "bp_year": []}
         for wname in window_order}

    for k in range(N_SIMS):
        mask_C = sample_random_mask(groups_topup, rng, n_common)
        resC_base, resC_damp = run_topup(mask_C, "C-random")
        bp_series_AC = bp_advantage_series(spy_close_c, mask_A, mask_C, common_idx)
        for wname in window_order:
            lo, hi = wslices[wname]
            mb = window_metrics(resC_base, bench_c, common_idx, lo, hi)
            md = window_metrics(resC_damp, bench_c, common_idx, lo, hi)
            s = starved_pct(resC_base, gates_c, lo, hi)
            bucket = mc[wname]
            bucket["capeff_base"].append(cap_eff(mb))
            bucket["capeff_damp"].append(cap_eff(md))
            bucket["pnl_base"].append(dollar_pnl(resC_base, lo, hi))
            bucket["pnl_damp"].append(dollar_pnl(resC_damp, lo, hi))
            bucket["alpha_base"].append(mb["Alpha"] * 100.0)
            bucket["alpha_damp"].append(md["Alpha"] * 100.0)
            bucket["maxdd_base"].append(mb["MaxDD"] * 100.0)
            bucket["maxdd_damp"].append(md["MaxDD"] * 100.0)
            bucket["starved_spy"].append(s[0] * 100.0)
            bucket["starved_qqq"].append(s[1] * 100.0)
            bucket["bp_year"].append(bp_year(bp_series_AC, *window_bounds[wname]))
        if (k + 1) % 100 == 0:
            print(f"MC {k+1}/{N_SIMS} 完成 ({time.time()-t0:.0f}s)", flush=True)

    print(f"MC 1000 次跑晒 ({time.time()-t0:.0f}s), "
          f"{TOPUP.ASSERT_COUNT['runs']} 個會計 run, "
          f"{TOPUP.ASSERT_COUNT['n']:,} 個 bar 層 assertion 全通過", flush=True)

    # ------------------------------------------------------------------
    # 寫報告
    # ------------------------------------------------------------------
    L = []
    add = L.append
    add("# 結果 — 核心 v2 月度 top-up「揀日器」A/B/C:現行月初 vs RSI2 揀日 vs 隨機對照")
    add("")
    add("**日期:** 2026-07-18  **腳本:** `backtest/experiments/exp_topup_daypicker.py`  "
        "**狀態:** active")
    add("")
    add("**本檔只報數,唔落判詞**(用戶明令)。三臂,唯一變數 = 月度 top-up 揀邊一日:"
        "**A** 現行(每月首個交易日)、**B** RSI2(SPY)<10 揀日(冇訊號月尾保底)、"
        "**C** 隨機一日(1000 次 MC)。**B 要贏 C 先算訊號,淨係贏 A 唔算。**")
    add("")
    add("⚠️ 唔好同 `2026-07-07_topup_timing_ab.md` 嘅 Rule E 混淆:嗰個係「RSI2 訊號完全"
        "取代月曆」(冇訊號嗰個月 = 零 top-up,結果流動性變差);本檔係「月曆保底,揀日淨係"
        "決定邊一日」,每個月保證有一次 top-up。")
    add("")
    add("## 問題")
    add("")
    add("`2026-07-17_rsi2_connors_settle.md` §7d/7e 判 RSI2 撈底做獨立 sleeve 錢細撐唔起"
        "注碼,但話「core v2 月度 top-up 嘅入場擇日器」係「唯一值得跑嘅 RSI2 用法」且"
        "「呢條未跑」。本檔就係跑呢條增量。")
    add("")
    add("## 方法(凍結咗乜、變咗乜)")
    add("")
    add("- **唯一變數 = top-up 揀邊一日嘅 trigger mask。** 引擎全部 verbatim import:"
        "`simulate_unit_path`/`build_underlying`/`build_gates`/`TD` ← "
        "`exp_leap_real_sweep.py`;`damp_iv`/`to_wslices`/`window_metrics`/"
        "`bench_metrics`/`CAPITAL` ← `exp_core_assembly_real.py`;"
        "`simulate_portfolio_topup`/`cell_label`/`month_start_mask`/`CASH_W`/"
        "`COST_BASE`/`DAMP` ← `exp_core_topup.py`;`cap_eff`/`alpha_ci` ← "
        "`exp_core_topup_realcost.py`。")
    add(f"- **凍結:** 月度 cadence(三臂逐月各一次)/ b={int(B_BUDGET*100)}% NAV / "
        f"Δ{DELTA:.2f} / SPY+QQQ 50/50 / 純 200SMA GATED entry / roll@63td / "
        f"成本 {COST_BASE*100:.1f}%/side / CAPITAL=${CAPITAL:,.0f} / "
        f"cash={int(CASH_W*100)}% / RSI2 門檻 <{RSI_THRESH:.0f}(同 Rule E 一致)。")
    add(f"- **m = {IV_M}**(A5:m=0.85 已知偏低;base 同 damp={DAMP} 兩個 IV 處理都跑,"
        "`damp_iv()` 同一個方法,verbatim import)。**200SMA 唔係揀日訊號嘅入場濾網**"
        "(A2:趨勢閘淨係用喺 LEAP 呢類槓桿工具嘅防爆倉,LEAP 自己 GATED entry 已經做"
        "緊呢個角色)。")
    add(f"- **窗口(A4):** FULL(common window 原生起點)PRIMARY + 2016+ 前後半"
        "(**2016-2020** 前半 / **2021+** 後半),沿用 `to_wslices()` 命名窗口。")
    add("- **量度(A3):** 資本效率(`cap_eff()`,alpha(pp)/DnMed)+ 絕對 PnL($,窗口自身"
        "rebase 到 CAPITAL)並列;alpha(全組合層:core v2 vs SPY net-TR)、MaxDD、"
        "cash-starved%(base IV,SPY 腿/QQQ 腿,定義同 `exp_core_topup.py` 一致)。")
    add(f"- **直觀數:** 逐月 (SPY收巿價_A - SPY收巿價_B)/SPY收巿價_A * 10000 bp,"
        "全期平均 x12 = 每年 bp;Arm C 嘅 1000 次分佈做同一個計算做對照。")
    add(f"- **Arm C:** N_SIMS={N_SIMS},seed={SEED},逐月隨機一個交易日(同 A/B 一樣"
        "逐月剛好一次,唔會逐月多過一次或零次)。")
    add("")
    add("## 資料來源(`backtest/data.py` `load()`)")
    add("")
    add("| Series | Source | Rows | From | To |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in prov_all:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")
    add(f"- 共同(mix)模擬窗口: {common_idx[0].date()} -> {common_idx[-1].date()} "
        f"({n_common} 日,{n_months} 個計 top-up 嘅月份)。")
    add(f"- 健全性錨 — SPY B&H TR(HK net)1996-01->{spy_df.index[-1].date()}: CAGR "
        f"**{anchor['CAGR']*100:.2f}%**, Sharpe {anchor['Sharpe']:.2f}, MaxDD "
        f"{anchor['MaxDD']*100:.1f}%(預登記接受區間 9–11%)。")
    add("")

    # -- 回歸檢查 -----------------------------------------------------------
    add(f"## 回歸檢查 — Arm A(m={IV_M})應接近重現 `2026-07-17_core_topup_realcost.md` "
        "表1 嘅 m=1.15 格")
    add("")
    add("機制完全一樣(C-monthly cadence / b15 / Δ0.50 / SPY+QQQ / m=1.15),差異只可能"
        "來自 live 資料尾巴日期唔同(`data.py load()` 冇快取)。")
    add("")
    add("| IV | 指標 | 已刊(realcost m=1.15) | 本次(Arm A) | 差 | 判 |")
    add("|---|---|---|---|---|---|")
    for ivkey, field, want, got, diff, ok in reg_rows:
        add(f"| {ivkey} | {field} | {want:+.2f} | {got:+.3f} | {diff:+.3f} | "
            f"{'PASS' if ok else 'FAIL'} |")
    add("")
    add(f"全部喺容差內(CAGR/Alpha ±{REG_TOL['CAGR']}pp,t ±{REG_TOL['t']})—— "
        "引擎接線正確,下面 A/B/C 對照可信。")
    add("")

    # -- 表 1:A vs B 頭對頭 --------------------------------------------------
    add("## 表 1 — Arm A vs Arm B 頭對頭(資本效率 + 絕對PnL + alpha + MaxDD + "
        "cash-starved%,base 同 damp 並列)")
    add("")
    add("| 窗口 | 臂 | IV | 資本效率 | 絕對PnL | alpha(t) | alpha 95%CI | MaxDD | "
        "SPY starved% | QQQ starved% |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for wname in window_order:
        for arm_label, mset in [("A(現行月初)", metricsA), ("B(RSI2揀日)", metricsB)]:
            for ivlabel, ivkey in [(f"base m{IV_M}", "base"), (f"damp {DAMP}", "damp")]:
                mm = mset[wname][ivkey]
                pnl = mset[wname][f"pnl_{ivkey}"]
                s = mset[wname]["starved"]
                add(f"| {wname} | {arm_label} | {ivlabel} | {_ce(mm)} | {_usd(pnl)} | "
                    f"{_a(mm)} | {_ci(mm)} | {_p(mm['MaxDD'])}{_ruin(mm)} | "
                    f"{_pctfmt(s[0]*100)} | {_pctfmt(s[1]*100)} |")
    add("")

    # -- 直觀數表 -------------------------------------------------------------
    add("## 直觀數 — B 相對 A 嘅入市價優勢(bp/年),同 C 嘅 1000 次分佈對照")
    add("")
    add("正數 = B 揀嗰日嘅 SPY 收巿價平過 A;每月一對一比較,全期平均後 x12 表示做"
        "「每年」。")
    add("")
    add("| 窗口 | B vs A(bp/年) | C 分佈 p5 | p25 | p50(中位) | p75 | p95 | "
        "B 喺 C 分佈嘅百分位 |")
    add("|---|---|---|---|---|---|---|---|")
    for wname in window_order:
        pc = pctiles(mc[wname]["bp_year"])
        rank = pct_rank(bp_year_AB[wname], mc[wname]["bp_year"])
        add(f"| {wname} | **{bp_year_AB[wname]:+.1f}** | {pc['p5']:+.1f} | {pc['p25']:+.1f} | "
            f"{pc['p50']:+.1f} | {pc['p75']:+.1f} | {pc['p95']:+.1f} | {rank:.1f} |")
    add("")

    # -- 表 2:揀日診斷 ---------------------------------------------------------
    add("## 表 2 — Arm B 揀日診斷(逐月係咪撈中 RSI2<10,定係跌落月尾保底)")
    add("")
    add("A 定義上恆企喺 offset=0(月首個交易日);下表淨列 B。offset = 揀中嗰日距離"
        "當月第一個交易日嘅交易日數(0 = 就係月首日)。")
    add("")
    add("| 窗口 | 總月數 | 撈中 RSI2<10(hit) | 跌落月尾保底(fallback) | "
        "B 平均 offset(交易日) |")
    add("|---|---|---|---|---|")
    for wname in window_order:
        total, hits, fb, mean_off = diag_rows[wname]
        add(f"| {wname} | {total} | {hits}({hits/total*100:.0f}%) | "
            f"{fb}({fb/total*100:.0f}%) | {mean_off:+.1f} |")
    add("")

    # -- 表 3:Arm C 完整分佈 ---------------------------------------------------
    add("## 表 3 — Arm C(隨機揀日,1000 次 MC)完整分佈")
    add("")
    add(f"### 3a. 資本效率(base m{IV_M:.2f} / damp {DAMP:.1f})")
    add("")
    add("| 窗口 | IV | p5 | p25 | p50 | p75 | p95 | B 實際值 | B 百分位 |")
    add("|---|---|---|---|---|---|---|---|---|")
    for wname in window_order:
        for ivlabel, key in [("base", "capeff_base"), ("damp", "capeff_damp")]:
            pc = pctiles(mc[wname][key])
            b_val = cap_eff(metricsB[wname][ivlabel])
            rank = pct_rank(b_val, mc[wname][key])
            b_str = f"{b_val:+.1f}" if np.isfinite(b_val) else "n/a"
            add(f"| {wname} | {ivlabel} | {pc['p5']:+.1f} | {pc['p25']:+.1f} | "
                f"{pc['p50']:+.1f} | {pc['p75']:+.1f} | {pc['p95']:+.1f} | {b_str} | "
                f"{rank:.1f} |")
    add("")
    add("### 3b. 絕對 PnL($)")
    add("")
    add("| 窗口 | IV | p5 | p25 | p50 | p75 | p95 | B 實際值 | B 百分位 |")
    add("|---|---|---|---|---|---|---|---|---|")
    for wname in window_order:
        for ivlabel, key in [("base", "pnl_base"), ("damp", "pnl_damp")]:
            pc = pctiles(mc[wname][key])
            b_val = metricsB[wname][f"pnl_{ivlabel}"]
            rank = pct_rank(b_val, mc[wname][key])
            add(f"| {wname} | {ivlabel} | {_usd(pc['p5'])} | {_usd(pc['p25'])} | "
                f"{_usd(pc['p50'])} | {_usd(pc['p75'])} | {_usd(pc['p95'])} | "
                f"{_usd(b_val)} | {rank:.1f} |")
    add("")
    add("### 3c. alpha(pp,全組合層 vs SPY net-TR)")
    add("")
    add("| 窗口 | IV | p5 | p25 | p50 | p75 | p95 | B 實際值 | B 百分位 |")
    add("|---|---|---|---|---|---|---|---|---|")
    for wname in window_order:
        for ivlabel, key in [("base", "alpha_base"), ("damp", "alpha_damp")]:
            pc = pctiles(mc[wname][key])
            b_val = metricsB[wname][ivlabel]["Alpha"] * 100.0
            rank = pct_rank(b_val, mc[wname][key])
            add(f"| {wname} | {ivlabel} | {pc['p5']:+.1f} | {pc['p25']:+.1f} | "
                f"{pc['p50']:+.1f} | {pc['p75']:+.1f} | {pc['p95']:+.1f} | "
                f"{b_val:+.1f} | {rank:.1f} |")
    add("")
    add("### 3d. MaxDD(%,描述性 —— 冇 B 百分位,方向解讀留返人手)")
    add("")
    add("| 窗口 | IV | p5 | p25 | p50 | p75 | p95 | B 實際值 |")
    add("|---|---|---|---|---|---|---|---|")
    for wname in window_order:
        for ivlabel, key in [("base", "maxdd_base"), ("damp", "maxdd_damp")]:
            pc = pctiles(mc[wname][key])
            b_val = metricsB[wname][ivlabel]["MaxDD"] * 100.0
            add(f"| {wname} | {ivlabel} | {pc['p5']:.1f} | {pc['p25']:.1f} | "
                f"{pc['p50']:.1f} | {pc['p75']:.1f} | {pc['p95']:.1f} | {b_val:.1f} |")
    add("")
    add("### 3e. cash-starved%(base IV,描述性)")
    add("")
    add("| 窗口 | 腿 | p5 | p25 | p50 | p75 | p95 | B 實際值 |")
    add("|---|---|---|---|---|---|---|---|")
    for wname in window_order:
        for leg_label, key, b_idx in [("SPY", "starved_spy", 0), ("QQQ", "starved_qqq", 1)]:
            pc = pctiles(mc[wname][key])
            b_val = metricsB[wname]["starved"][b_idx] * 100.0
            add(f"| {wname} | {leg_label} | {pc['p5']:.0f} | {pc['p25']:.0f} | "
                f"{pc['p50']:.0f} | {pc['p75']:.0f} | {pc['p95']:.0f} | {b_val:.0f} |")
    add("")

    # -- Cross-foot -----------------------------------------------------------
    add("## Cross-foot 驗證")
    add("")
    add(f"- {TOPUP.ASSERT_COUNT['runs']:,} 個會計 run("
        f"Arm A + Arm B + {N_SIMS} 次 Arm C,base+damp 各一),"
        f"{TOPUP.ASSERT_COUNT['n']:,} 個 bar 層 assertion 全部通過:"
        "NAV = core + cash + Σ(期權市值);cash >= 0;NAV > 0;"
        "NAV_t = NAV_(t-1) + 利息 + core P&L + 期權 P&L − 成本(月度 floor top-up 係"
        "零和內部轉帳,唔入呢條恆等式;相對容差 1e-6)。任何違反即 raise 並中止 —— 冇。")
    add(f"- 逐月剛好一次 top-up 嘅不變量喺三臂(A/B/{N_SIMS}次C)全部驗證通過"
        f"(n_months={n_months})。")
    add("")

    add("## 方法備註(唔係判詞 —— 只講方法本身嘅已知局限)")
    add("")
    add("- 本檔冇做 Bonferroni/DSR 多重檢定校正:呢個係一個針對已定案勝出格嘅 3 臂"
        "對照測試(A 現行 / B 揀日 / C 隨機),唔係新開嘅多格 grid search —— 同"
        "`2026-07-07_topup_timing_ab.md` 嘅統計脈絡一致。")
    add("- Arm C 嘅隨機 null 冇特別保留「dip 之後波動較高」嘅條件結構(逐月純均勻隨機"
        "揀一個交易日),對照本身冇針對呢點做額外調整。")
    add("- cash-starved% 只用 base IV 計(同 `exp_core_topup.py`/`exp_core_topup_"
        "realcost.py` 既有慣例一致,damp IV 冇另計)。")
    add("- alpha 嘅信賴區間 = 普通 OLS 標準誤(冇 Newey-West 自相關修正)—— repo 一貫"
        "做法,照實講明。")
    add("- RSI2 門檻用 <10(跟 Rule E),唔係 Connors 原著嘅 <5 —— 本檔冇重新掃門檻。")
    add("- **bp/年呢個直觀數混埋咗『月入面邊日買』同『大市長期向上飄移』兩件事**:"
        "喺一個持續向上嘅市場,月入面買得越遲,原始收巿價傾向越貴(純粹因為飄移,同"
        "RSI2 訊號本身有冇擇時能力無關)。B 平均 offset(表2)明顯大過 0,即係 B 通常"
        "買得比 A 遲 —— 本測試冇將「遲買嘅飄移代價」同「RSI2 揀嘅係咪一個相對抵嘅日子」"
        "呢兩件事拆開嚟講,讀 bp/年嗰欄時要意識到呢個混雜。")
    add("- 本次結果**未寫入** `backtest/SETTLED.md`(任務範圍只准新增 exp_topup_"
        "daypicker.py 同本檔;#13d 要唔要覆核留返後續)。")
    add("")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS}  ({time.time()-t0:.0f}s total, "
          f"{TOPUP.ASSERT_COUNT['n']:,} asserts / {TOPUP.ASSERT_COUNT['runs']} runs)",
          flush=True)


if __name__ == "__main__":
    main()
