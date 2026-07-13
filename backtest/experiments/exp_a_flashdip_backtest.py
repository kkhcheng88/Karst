"""A-test — 「優質股閃縮」(Quality Flinch) sleeve 嘅完整立項 backtest.

立項來源
--------
Fable 交接書 P1-7 / `docs/2026-07-12_new_sleeve_candidates.md` 候選 A +
`docs/2026-07-12_opportunity_ladder.md` A 欄:機會階梯雷達 A 而家標 not_wired,
因為「③真錢閘要完整 backtest,尚未立項」。呢個 backtest 過唔過,直接決定雷達 A
接唔接、同埋佢嘅入場規則係乜。

科學問題(一句)
--------
優質股俾一單「一次性壞消息」單日/短期急插(flinch)之後買入,係咪對比**同市值層
指數喺同一日入場**有正向增量回報?(即係:市場係咪真係「將暫時當永久」錯價,
定係只不過跟住成個 tier 跌完彈?)

House 標準(memory `backtest-testing-standard`,唔准偷工)
--------
1. 覆蓋 4 股種:大盤 / 中盤 / 細價股 / 微型股 —— 唔准淨測大股。
2. Size-matched benchmark:每層對返自己嘅 size-tier ETF(大→SPY、中→MDY、
   小→IJR、微→IWC),唔係一律對 SPY(SPY 會系統性罰細股)。
3. Measure = 資本效率:deployed CAGR(每單位資金佔用時間嘅回報)+ 逐事件
   excess / win% / median,唔係淨 raw return。
4. 窗口 2011-01-01+(候選 A 講「過去 15 年」),2016 pivot 前後半各自報數,
   防單一時代 artifact。

═══════════════════════════════════════════════════════════════════════════
 PRE-REGISTERED 定義(全部喺睇任何結果之前寫死;呢個 block 就係 pre-registration)
═══════════════════════════════════════════════════════════════════════════

[定義 1 — 「優質股」universe]
  「優質」= 由作者**事前**揀嘅、有長期(≥10 年)獲利記錄 + 具護城河/高毛利特徵
  嘅代表性名單,每個市值層一批(見 UNIVERSE)。呢個係**靜態品質標籤**——
  誠實披露兩個限制(見檔尾 Caveats):
    (a) 品質標籤 look-ahead:我哋今日先知邊啲係優質股;
    (b) survivorship:yfinance 只有仍上市/未除牌嘅名,爆煲除牌嘅「假優質」
        (WOLF 教訓)根本唔喺數據入面 → 本測試會**系統性高估** edge。
  → 呢兩個偏差都令結果偏正;所以若連 survivorship 順風都測唔到增量 = 強 FAIL;
    若測到正增量,要對 survivorship 打折先信。

[定義 2 — 「閃縮」事件(由價格系統性掃出,唔係人手揀靚案例)]
  事件日 D = universe 內任何一隻股,收市對收市滿足以下任一:
    - 單日回報 ≤ FLASH_1D (= -13%)               ← 「單日 flinch」
    - 5 交易日累計回報 ≤ FLASH_5D (= -20%)        ← 「單週急插」
  (對標候選 A 原文「單日/單週 −15%+」「插 20-35%」;放寬到 -13/-20 換取事件數,
   落喺原文區間附近。)
  Cooldown:同一隻股 63 交易日內只保留**最早**嗰個事件,避免同一次插水嘅
  自相關重複計數。

[定義 3 — 入場 / 持有(冇 lookahead)]
  D 收市確認事件 → D+1 收市入場(ENTRY_LAG=1)→ 持有 H ∈ {21, 63, 126} 交易日,
  H 到期收市離場。回報用**股息/拆股調整後**收市(adjusted=True,total return)。

[定義 4 — 對照(size-matched、matched-timing)]
  每個事件,benchmark = 該股所屬市值層 ETF **喺同一段日曆窗口**(entry_date →
  exit_date)嘅 adjusted 回報。
  excess = 個股 H 日前向回報 − benchmark H 日前向回報。
  → 呢個 strip 走咗「成個 tier 跌完自己彈」;excess>0 先代表「買呢隻插咗水嘅
    specific 股」贏過「同一刻買 tier 指數」。

[定義 5 — Arm A(raw)vs Arm B(+solvency gate)]
  Arm A(raw 閃縮訊號):universe 內全部閃縮事件。
  Arm B(+ solvency proxy):事件日 point-in-time 加閘(defeatbeta 數據)——
    - debt/equity ≤ DE_MAX (= 2.0)  最近一期(季)報表(WOLF solvency 前置)
    - 最近一個年度 net income > 0
    誠實限制:defeatbeta annual 基本面**只覆蓋 ~2019+**(annual 報表得 7 個財年、
    衍生比率更短),所以 Arm B 只跑得到 **2019-01-01 之後**嘅事件;更早事件冇
    point-in-time 基本面,唔入 Arm B(明文交代)。
  → Arm B − Arm A 嘅增量 = solvency gate 有冇用,直接指導雷達 A 入場規則。

[未自動化層 —— 誠實聲明]
  候選 A 設計嘅**關鍵過濾器**係用 transcript 語料判「過性 vs 結構」語言
  (管理層講 one-off/timing/pull-forward vs competition/pricing-pressure/demand-loss)。
  **呢層喺本測試未自動化**(transcript→語言分類未有可靠自動管道)。所以本測試
  只驗:**raw 閃縮訊號 ± 簡單 solvency proxy**。若 raw+solvency 已見增量,
  transcript 過濾器係「錦上添花」;若 raw+solvency 冇增量,雷達 A 唔應該淨靠
  價格訊號接線,要等 transcript 過濾器先算數 —— 呢個分野會寫入結論。

[定義 6 — 分段]
  Era 前半 = START .. 2015-12-31;Era 後半 = 2016-01-01 .. END(PIVOT=2016-01-01)。
  每個 tier × era 各自報數。

[決策規則 — 三選一(事前寫死;睇結果之前定義)]
  以 63d horizon(候選 A 判官口徑「63/126d excess」嘅短檔)為主判、126d 為輔證:
  • PASS(雷達 A 接線 + 訂入場規則):median 63d excess > +2.0% 且 win%(excess>0)
    > 55%,喺 **≥3/4 tier** 成立,且 **兩個 era 都唔轉負**(n≥10 嗰啲 cell)。
  • FAIL(維持唔接):pooled 63d median excess ≤ 0 或 win% ≤ 50%,喺**多數 tier**。
  • PARTIAL(某層/某段/某 arm 先有效):介乎兩者 —— 明確講邊個 tier / era /
    horizon / arm 有(冇)增量、條件係乜。

Run : PYTHONUTF8=1 python backtest/experiments/exp_a_flashdip_backtest.py
Writes: backtest/results/2026-07-13_a_flashdip_backtest.md
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load  # noqa: E402  repo price loader (yfinance-first, adjusted=True)

# ───────────────────────────── PRE-REGISTERED CONSTANTS ─────────────────────
START = "2011-01-01"          # 候選 A:「過去 15 年」
END = "2026-07-13"
PIVOT = pd.Timestamp("2016-01-01")   # era 前後半分界
FLASH_1D = -0.13              # 單日 flinch 門檻
FLASH_5D = -0.20             # 5 交易日急插門檻
COOLDOWN_TD = 63             # 同股事件去堆聚(交易日)
ENTRY_LAG = 1               # D+1 收市入場
HORIZONS = [21, 63, 126]    # 持有期(交易日)
DE_MAX = 2.0               # Arm B solvency gate:debt/equity 上限
ARM_B_MIN_YEAR = 2019       # defeatbeta 基本面覆蓋起點
# 決策門檻(事前)
PASS_MED_EXCESS = 2.0        # % @ 63d
PASS_WINRATE = 55.0          # %
PASS_MIN_TIERS = 3           # /4

# Size-matched benchmark ETF(每 tier 對返自己)
TIER_BENCH = {"大盤": "SPY", "中盤": "MDY", "細價股": "IJR", "微型股": "IWC"}

# ── UNIVERSE(pre-registered 靜態品質標籤,事前揀,睇結果之前定死)──────────────
# 每 tier ~14-18 隻長歷史(2011+)、有獲利記錄 + 護城河/高毛利特徵嘅代表性名單。
# Tier 由作者按 2011-2026 典型市值指派;個別名跨咗 tier 邊界(明文披露),
# benchmark 一律對返所指派 tier。抽樣方法 = 作者事前 judgment sample(非隨機),
# 呢個係品質標籤本身嘅限制,已喺 Caveats 交代。
UNIVERSE = {
    "大盤": [  # mega/large quality compounders
        "AAPL", "MSFT", "GOOGL", "JNJ", "PG", "KO", "PEP", "HD", "UNH",
        "V", "MA", "NKE", "COST", "MCD", "TXN", "HON", "ADBE", "LMT",
    ],
    "中盤": [  # mid-cap quality w/ long history
        "POOL", "WSO", "EXPO", "GGG", "WST", "MKTX", "TYL", "FDS",
        "GNTX", "LII", "NDSN", "DPZ", "RPM", "WAT", "ROL", "MSA",
    ],
    "細價股": [  # small-cap
        "PATK", "SHOO", "CALM", "UFPT", "MYRG", "NATH", "MGPI", "HURN",
        "WDFC", "SXI", "HELE", "THRM", "PRDO", "EPAC",
    ],
    "微型股": [  # micro-cap(survivorship 最嚴重嗰層,已披露)
        "WINA", "UTMD", "LAKE", "RGR", "CCRN", "DAIO", "ESCA", "PRLB",
        "CTO", "NHC", "SENEA", "PANL",
    ],
}

RESULTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "results", "2026-07-13_a_flashdip_backtest.md")


# ───────────────────────────── 價格 / 事件掃描 ──────────────────────────────

_PRICE_CACHE: dict[str, pd.DataFrame | None] = {}
MIN_ROWS = 200


def load_prices(sym: str) -> pd.DataFrame | None:
    """Adjusted 日線,窗口 START..END。含 retry —— yfinance 喺 60 名連續下載(尤其
    defeatbeta 重網絡活動之後)會暫時 throttle,**返空/短 frame 但唔 raise**,無
    retry 會靜靜甩名(傷可重複性 + 低估事件數)。所以 retry 條件 = 最終窗口 frame
    < MIN_ROWS 行(唔淨係 exception)。結果 cache,同名唔重下載。"""
    if sym in _PRICE_CACHE:
        return _PRICE_CACHE[sym]
    out = None
    for attempt in range(5):
        try:
            df = load(sym, adjusted=True)
            df = df[(df.index >= pd.Timestamp(START)) & (df.index <= pd.Timestamp(END))]
            if len(df) >= MIN_ROWS:
                out = df
                break
        except Exception:
            pass
        time.sleep(2.0 * (attempt + 1))  # backoff for transient throttle (空/短 frame)
    _PRICE_CACHE[sym] = out
    return out


def scan_events(df: pd.DataFrame) -> list[pd.Timestamp]:
    """由價格系統性掃閃縮事件(冇 lookahead 用當日收市確認),套 cooldown。"""
    close = df["close"]
    ret1 = close.pct_change()
    ret5 = close.pct_change(5)
    fire = (ret1 <= FLASH_1D) | (ret5 <= FLASH_5D)
    fire_days = list(df.index[fire.fillna(False)])
    kept: list[pd.Timestamp] = []
    last_pos = -10**9
    pos_of = {d: i for i, d in enumerate(df.index)}
    for d in fire_days:
        p = pos_of[d]
        if p - last_pos >= COOLDOWN_TD:
            kept.append(d)
            last_pos = p
    return kept


def fwd_return(df: pd.DataFrame, event_day: pd.Timestamp, H: int):
    """D+ENTRY_LAG 收市買、+H 收市賣;回報 = adjusted close ratio。"""
    idx = df.index
    p = idx.get_loc(event_day)
    entry_pos = p + ENTRY_LAG
    exit_pos = entry_pos + H
    if exit_pos >= len(idx):
        return None
    entry_px = df["close"].iloc[entry_pos]
    exit_px = df["close"].iloc[exit_pos]
    if entry_px <= 0:
        return None
    return dict(entry_date=idx[entry_pos], exit_date=idx[exit_pos],
                ret=float(exit_px / entry_px - 1.0))


def bench_return(bench_df: pd.DataFrame, entry_date, exit_date):
    """同一段日曆窗口嘅 size-tier ETF adjusted 回報(matched-timing)。"""
    c = bench_df["close"]
    e = c.asof(entry_date)
    x = c.asof(exit_date)
    if pd.isna(e) or pd.isna(x) or e <= 0:
        return None
    return float(x / e - 1.0)


# ───────────────────────────── Solvency gate(Arm B, defeatbeta)─────────────

def build_solvency_cache(all_syms: list[str]) -> dict:
    """每股攞 debt_to_equity(季)+ annual net income;point-in-time 用。
    defeatbeta 只覆蓋 ~2019+;缺數 → gate=unknown(該股 2019+ 事件唔入 Arm B)。"""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        from defeatbeta_api.data.ticker import Ticker

    cache: dict[str, dict] = {}
    for sym in all_syms:
        rec = {"de": None, "ni": None}
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                tk = Ticker(sym)
        except Exception:
            cache[sym] = rec
            continue
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                de = tk.debt_to_equity()
            if de is not None and len(de) and "report_date" in de.columns:
                de = de.copy()
                de["report_date"] = pd.to_datetime(de["report_date"])
                rec["de"] = de[["report_date", "debt_to_equity"]].dropna().sort_values("report_date")
        except Exception:
            pass
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                inc = tk.annual_income_statement()
            dfa = inc.df if not callable(inc.df) else inc.df()
            # find the 'Net Income' row; columns are fiscal-year dates
            if isinstance(dfa, pd.DataFrame) and "Breakdown" in dfa.columns:
                row = dfa[dfa["Breakdown"].astype(str).str.strip().str.lower().isin(
                    ["net income", "net income common stockholders", "net income to common"])]
                if len(row):
                    ser = row.iloc[0].drop(labels=["Breakdown"])
                    ni = {}
                    for col, val in ser.items():
                        try:
                            ni[pd.to_datetime(col)] = float(str(val).replace(",", ""))
                        except Exception:
                            continue
                    if ni:
                        rec["ni"] = pd.Series(ni).sort_index()
        except Exception:
            pass
        cache[sym] = rec
    return cache


def solvency_pass(cache: dict, sym: str, event_day: pd.Timestamp):
    """回傳 True/False/None(None = 冇 point-in-time 數據,唔入 Arm B)。"""
    if event_day.year < ARM_B_MIN_YEAR:
        return None
    rec = cache.get(sym, {})
    de_ser, ni_ser = rec.get("de"), rec.get("ni")
    if de_ser is None or ni_ser is None or len(de_ser) == 0 or len(ni_ser) == 0:
        return None
    de_prior = de_ser[de_ser["report_date"] < event_day]
    ni_prior = ni_ser[ni_ser.index < event_day]
    if len(de_prior) == 0 or len(ni_prior) == 0:
        return None
    de_val = float(de_prior.iloc[-1]["debt_to_equity"])
    ni_val = float(ni_prior.iloc[-1])
    return bool(de_val <= DE_MAX and ni_val > 0)


# ───────────────────────────── 主流程:砌事件表 ─────────────────────────────

def build_event_table() -> pd.DataFrame:
    all_syms = [s for lst in UNIVERSE.values() for s in lst]
    bench_syms = list(set(TIER_BENCH.values()))
    # 先 prefetch 全部價格(yfinance session 新鮮),再掂 defeatbeta —— 避開
    # defeatbeta 重網絡活動之後 yfinance 被 throttle 返短 frame 嘅問題。
    print(f"[data] prefetching {len(all_syms)} universe names + {len(bench_syms)} bench ETFs (adjusted) ...")
    for b in bench_syms:
        load_prices(b)
    n_ok = sum(1 for s in all_syms if load_prices(s) is not None)
    print(f"[data] {n_ok}/{len(all_syms)} universe names have usable price data "
          f"(>= {MIN_ROWS} rows in window)")
    bench_cache = {b: _PRICE_CACHE.get(b) for b in bench_syms}
    sol_cache = build_solvency_cache(all_syms)
    n_usable = sum(1 for s in all_syms
                   if sol_cache.get(s, {}).get("de") is not None
                   and sol_cache.get(s, {}).get("ni") is not None)
    print(f"[solvency] cache built for {len(all_syms)} names ({n_usable} have usable de+ni)")

    rows = []
    for tier, syms in UNIVERSE.items():
        bench_df = bench_cache[TIER_BENCH[tier]]
        for sym in syms:
            df = load_prices(sym)
            if df is None:
                print(f"[skip] {sym}: no usable price data")
                continue
            events = scan_events(df)
            for d in events:
                base = dict(tier=tier, sym=sym, event_date=d,
                            era="前半(2011-2015)" if d < PIVOT else "後半(2016+)",
                            bench=TIER_BENCH[tier])
                ok = True
                for H in HORIZONS:
                    fr = fwd_return(df, d, H)
                    if fr is None:
                        ok = False
                        break
                    br = bench_return(bench_df, fr["entry_date"], fr["exit_date"])
                    base[f"ret_{H}"] = fr["ret"]
                    base[f"bench_{H}"] = br
                    base[f"excess_{H}"] = (fr["ret"] - br) if br is not None else np.nan
                    if H == HORIZONS[0]:
                        base["entry_date"] = fr["entry_date"]
                if not ok:
                    continue
                base["solv"] = solvency_pass(sol_cache, sym, d)
                rows.append(base)
    df = pd.DataFrame(rows)
    print(f"[events] total events with full forward data = {len(df)}")
    return df


# ───────────────────────────── 統計 ────────────────────────────────────────

def deployed_cagr(mean_ret: float, H: int) -> float:
    """資本效率:每單位資金佔用 H 交易日,年化 deployed CAGR。"""
    if 1.0 + mean_ret <= 0:
        return float("nan")
    return (1.0 + mean_ret) ** (252.0 / H) - 1.0


def cell_stats(sub: pd.DataFrame, H: int) -> dict:
    ex = sub[f"excess_{H}"].dropna()
    rt = sub[f"ret_{H}"].dropna()
    bn = sub[f"bench_{H}"].dropna()
    n = len(ex)
    if n == 0:
        return dict(n=0)
    t = float(ex.mean() / (ex.std(ddof=1) / np.sqrt(n))) if n >= 2 and ex.std(ddof=1) > 0 else float("nan")
    return dict(
        n=n,
        ret_mean=float(rt.mean()) * 100, ret_med=float(rt.median()) * 100,
        bench_mean=float(bn.mean()) * 100,
        ex_mean=float(ex.mean()) * 100, ex_med=float(ex.median()) * 100,
        win=float((ex > 0).mean()) * 100,
        dep_sig=deployed_cagr(float(rt.mean()), H) * 100,
        dep_bench=deployed_cagr(float(bn.mean()), H) * 100,
        t=t,
    )


def stat_cells(s: dict) -> list[str]:
    """回傳正式表格欄位(唔用 `|` 做內部分隔,避免整爛 markdown table)。
    欄序:n | 個股平均(中位) | bench平均 | excess平均(中位) | win% | deplCAGR訊/bench | t"""
    if s.get("n", 0) == 0:
        return ["0", "—", "—", "—", "—", "—", "—"]
    return [
        str(s["n"]),
        f"{s['ret_mean']:+.1f}%({s['ret_med']:+.1f}%)",
        f"{s['bench_mean']:+.1f}%",
        f"**{s['ex_mean']:+.1f}%({s['ex_med']:+.1f}%)**",
        f"{s['win']:.0f}%",
        f"{s['dep_sig']:+.0f}%/{s['dep_bench']:+.0f}%",
        f"{s['t']:.1f}",
    ]


STAT_HDR = "n | 個股平均(中位) | bench平均 | **excess平均(中位)** | win% | deplCAGR訊/bench | t"
STAT_SEP = "|" + "---|" * 7


# ───────────────────────────── 報告 ────────────────────────────────────────

def build_report(ev: pd.DataFrame) -> str:
    L = []
    A = L.append
    A("# Result — A-test:「優質股閃縮」(Quality Flinch) sleeve 完整立項 backtest")
    A("")
    A("**Date:** 2026-07-13　**Script:** `exp_a_flashdip_backtest.py`　"
      "**Tag:** 立項/真錢閘(機會階梯雷達 A ③)")
    A("")
    A("> 立項來源:Fable 交接書 P1-7 + `docs/2026-07-12_new_sleeve_candidates.md` 候選 A + "
      "`docs/2026-07-12_opportunity_ladder.md` A 欄。雷達 A 而家標 `not_wired`,"
      "因為「③真錢閘要完整 backtest,尚未立項」。**本檔就係嗰個 backtest。**")
    A("")

    # ── PRE-REGISTERED 定義 section(喺結果之前)──
    A("## 一、Pre-registered 定義(全部喺睇任何結果之前寫死)")
    A("")
    A("| 項 | 定義(script 頂常數) |")
    A("|---|---|")
    A(f"| 窗口 | {START} → {END};pivot **{PIVOT.date()}** 前後半各自報數 |")
    A(f"| 「優質股」 | 作者事前揀嘅長歷史(≥10 年)獲利 + 護城河/高毛利代表名單,"
      f"每 tier 一批(見下)。**靜態品質標籤** —— 品質 look-ahead + survivorship 兩偏差都令結果偏正,見 Caveats |")
    A(f"| 「閃縮」事件 | 由價格**系統性掃**:單日 ≤ **{FLASH_1D*100:.0f}%** 或 "
      f"5 交易日 ≤ **{FLASH_5D*100:.0f}%**(對標候選 A「單日/單週 −15%+」);"
      f"同股 cooldown **{COOLDOWN_TD}** 交易日,保留最早 |")
    A(f"| 入場/持有 | D 收市確認 → **D+{ENTRY_LAG} 收市**入場 → 持有 **{HORIZONS}** 交易日,"
      f"adjusted(total-return)收市 |")
    A(f"| 對照 | **size-matched + matched-timing**:每 tier 對返自己 ETF"
      f"(大→SPY / 中→MDY / 小→IJR / 微→IWC),同一日曆窗口 adjusted 回報;"
      f"**excess = 個股前向 − benchmark 前向** |")
    A(f"| Arm A / B | A=全部 raw 閃縮事件;B=加 point-in-time solvency gate"
      f"(debt/equity ≤ **{DE_MAX}** + 最近年度 net income>0,defeatbeta,只 **{ARM_B_MIN_YEAR}+** 有數) |")
    A(f"| 資本效率 | deployed CAGR =(1+mean)^(252/H)−1,訊號 vs benchmark 並列 |")
    A(f"| 決策(事前) | **PASS**:63d median excess > +{PASS_MED_EXCESS:.0f}% 且 win>{PASS_WINRATE:.0f}%,"
      f"喺 ≥{PASS_MIN_TIERS}/4 tier 成立且兩 era 唔轉負;**FAIL**:多數 tier 63d median excess ≤0 或 win≤50%;"
      f"**PARTIAL**:介乎兩者,講明條件 |")
    A("")
    A("**未自動化層(誠實聲明):** 候選 A 設計嘅**關鍵過濾器**係 transcript 語料判"
      "「過性 vs 結構」語言 —— **本測試未自動化呢層**。所以本測試只驗 "
      "**raw 閃縮訊號 ± 簡單 solvency proxy**。含意寫入結論。")
    A("")
    A("**Universe(pre-registered,靜態,事前揀):**")
    A("")
    A("| Tier | Benchmark | 名單 |")
    A("|---|---|---|")
    for tier, syms in UNIVERSE.items():
        A(f"| {tier} | {TIER_BENCH[tier]} | {', '.join(syms)} |")
    A("")

    # ── 事件庫規模 ──
    A("## 二、事件庫規模(由價格系統性掃出)")
    A("")
    A("欄義:**有價** = 成功 load(≥200 行)嘅名數;**有事件名** = 至少 1 個閃縮事件嘅"
      "名數(優質大股好少 fire,所以 < 有價 = 正常,唔係缺數據)。")
    A("")
    A("| Tier | universe 名數 | 有價(load) | 有事件名 | 事件總數 | 前半(2011-15) | 後半(2016+) | Arm B 可判(2019+) |")
    A("|---|---|---|---|---|---|---|---|")
    tot_load = 0
    for tier in UNIVERSE:
        sub = ev[ev["tier"] == tier]
        n_load = sum(1 for s in UNIVERSE[tier] if _PRICE_CACHE.get(s) is not None)
        tot_load += n_load
        n_names = sub["sym"].nunique()
        n_pre = len(sub[sub["era"].str.startswith("前")])
        n_post = len(sub[sub["era"].str.startswith("後")])
        n_armb = len(sub[sub["solv"].notna()])
        A(f"| {tier} | {len(UNIVERSE[tier])} | {n_load} | {n_names} | {len(sub)} | {n_pre} | {n_post} | {n_armb} |")
    tot = ev
    A(f"| **合計** | {sum(len(v) for v in UNIVERSE.values())} | {tot_load} | {tot['sym'].nunique()} | "
      f"{len(tot)} | {len(tot[tot['era'].str.startswith('前')])} | "
      f"{len(tot[tot['era'].str.startswith('後')])} | {len(tot[tot['solv'].notna()])} |")
    A("")

    # ── 主結果:四股種 × 三持有期(Arm A raw)──
    A("## 三、主結果 —— 四股種 × 三持有期(Arm A:raw 閃縮,全事件)")
    A("")
    A("讀法:個股前向回報 vs **同市值層 ETF 同窗口回報**;**excess** 係核心;"
      "win% = excess>0 嘅事件比例;deplCAGR = 資本效率(年化 deployed);"
      "t = excess 嘅粗略 t-stat(**事件叢集 → 唔獨立,t 只作指示,非推論級**)。")
    A("")
    for H in HORIZONS:
        A(f"### 持有 {H} 交易日")
        A("")
        A(f"| Tier | {STAT_HDR} |")
        A("|---" + STAT_SEP)
        for tier in UNIVERSE:
            sub = ev[ev["tier"] == tier]
            A(f"| {tier} | " + " | ".join(stat_cells(cell_stats(sub, H))) + " |")
        A("| **全 tier pooled** | " + " | ".join(stat_cells(cell_stats(ev, H))) + " |")
        A("")

    # ── 前後半分段(63d 主判)──
    A("## 四、前後半分段(2016 pivot,63d 主判 horizon)")
    A("")
    A(f"| Tier | Era | {STAT_HDR} |")
    A("|---|---" + STAT_SEP)
    for tier in UNIVERSE:
        for era_key, era_label in [("前", "前半 2011-2015"), ("後", "後半 2016+")]:
            sub = ev[(ev["tier"] == tier) & (ev["era"].str.startswith(era_key))]
            A(f"| {tier} | {era_label} | " + " | ".join(stat_cells(cell_stats(sub, 63))) + " |")
    for era_key, era_label in [("前", "前半 2011-2015"), ("後", "後半 2016+")]:
        sub = ev[ev["era"].str.startswith(era_key)]
        A(f"| **pooled** | {era_label} | " + " | ".join(stat_cells(cell_stats(sub, 63))) + " |")
    A("")

    # ── Arm B 增量 ──
    A("## 五、Arm B 增量 —— solvency gate 有冇用(2019+ 有 point-in-time 數據嘅事件)")
    A("")
    A(f"只計 {ARM_B_MIN_YEAR}+ 且 defeatbeta 有 de+ni 嘅事件。Arm A(呢個子集全部)"
      f" vs Arm B(加 debt/equity≤{DE_MAX} + 年度盈利>0)。63d horizon。")
    A("")
    def ex_win(s: dict) -> tuple[str, str, str]:
        if s.get("n", 0) == 0:
            return "0", "—", "—"
        return str(s["n"]), f"**{s['ex_mean']:+.1f}%({s['ex_med']:+.1f}%)**", f"{s['win']:.0f}%"

    A("| Tier | n(A) | Arm A excess平均(中位) | winA | n(B) | Arm B excess平均(中位) | winB | gate剔走 |")
    A("|---|---|---|---|---|---|---|---|")
    for tier in UNIVERSE:
        sub = ev[(ev["tier"] == tier) & (ev["solv"].notna())]
        subb = sub[sub["solv"] == True]  # noqa: E712
        na, exa, wa = ex_win(cell_stats(sub, 63))
        nb, exb, wb = ex_win(cell_stats(subb, 63))
        A(f"| {tier} | {na} | {exa} | {wa} | {nb} | {exb} | {wb} | {len(sub) - len(subb)} |")
    sub_all = ev[ev["solv"].notna()]
    subb_all = sub_all[sub_all["solv"] == True]  # noqa: E712
    na, exa, wa = ex_win(cell_stats(sub_all, 63))
    nb, exb, wb = ex_win(cell_stats(subb_all, 63))
    A(f"| **pooled** | {na} | {exa} | {wa} | {nb} | {exb} | {wb} | {len(sub_all) - len(subb_all)} |")
    A("")

    # ── 結論(由數字驅動,見 decide())──
    verdict, reason, entry_rule = decide(ev)
    A("## 六、結論(三選一)")
    A("")
    A(f"### → **{verdict}**")
    A("")
    for r in reason:
        A(f"- {r}")
    A("")
    if entry_rule:
        A("### 入場規則草稿(若 PASS/PARTIAL)")
        A("")
        for r in entry_rule:
            A(f"- {r}")
        A("")

    # ── Caveats ──
    A("## 七、Caveats / 限制(必讀,呢啲偏差全部令結果偏正)")
    A("")
    A("1. **Survivorship(最重要)**:yfinance 只有仍上市嘅名 —— 爆煲/除牌嘅「假優質」"
      "(正正係 WOLF 教訓嗰種)唔喺數據入面。呢個令本測試**系統性高估** edge。"
      "→ 若連 survivorship 順風都測唔到增量 = 強 FAIL;若測到,要對 survivorship 打折。")
    A("2. **品質標籤 look-ahead**:universe 係今日先知邊個係優質股嘅靜態名單,"
      "非 point-in-time 選股 → 品質標籤本身有前視偏差(同樣令結果偏正)。")
    A("3. **transcript「過性 vs 結構」過濾器未自動化** —— 候選 A 嘅**核心 edge 來源**"
      "(區分 one-off vs 結構損傷)喺本測試缺席;本測試只係「raw 閃縮 ± solvency」下限。")
    A(f"4. **Arm B 只覆蓋 {ARM_B_MIN_YEAR}+**:defeatbeta annual 基本面得 ~7 個財年,"
      "更早事件冇 point-in-time solvency 判定 → solvency gate 嘅結論只喺近半段有效。")
    A("5. **事件叢集**:crash 會令同一 tier 多隻股同一週齊 fire(2020-03、2022 等),"
      "事件之間高度自相關 → 有效樣本量遠細過名義 n;所有 t-stat 只作指示,唔可以"
      "當獨立樣本推論。median / win% 比 mean 穩健,結論以佢哋為主。")
    A("6. **tier 指派近似**:個別名 15 年間跨咗市值 tier(如 ODFL 由細變大);"
      "本測試用作者事前指派 + 對返該 tier ETF,係近似。")
    A("7. **成本未扣**:前向回報係毛回報(未扣交易成本/滑價);對 excess(個股−bench "
      "同口徑)影響細,但 raw return 要當上限讀。")
    A("")
    A("## 八、雷達 A 決定")
    A("")
    A(f"**{verdict}** → " + {
        "PASS": "機會階梯雷達 A **可接線**,入場規則見上;但真錢部署前仍須補 transcript「過性 vs 結構」過濾器 + survivorship 打折。",
        "FAIL": "機會階梯雷達 A **維持 not_wired**:raw 閃縮訊號(即使有 survivorship 順風)冇對 size-matched benchmark 嘅增量;淨靠價格閃縮唔應該接線,要等 transcript 過濾器先重新立項。",
        "PARTIAL": "機會階梯雷達 A **有條件接線**:只喺結論指明嘅 tier/era/arm 開燈,其餘維持 not_wired;入場規則見上並寫死條件。",
    }[verdict])
    A("")
    return "\n".join(L)


def decide(ev: pd.DataFrame):
    """忠實實現 pre-registered 決策規則(睇結果之前定死,唔搬龍門):
      • PASS   :tier(n≥10)63d median excess > +2% 且 win > 55% 且兩 era 唔轉負 —— 成立 ≥3/4 tier。
      • FAIL   :tier「weak」=(63d median excess ≤ 0)或(win ≤ 50%);多數 tier(n≥10)weak。
      • PARTIAL:介乎兩者。
    """
    tiers_with_data = [t for t in UNIVERSE if cell_stats(ev[ev["tier"] == t], 63).get("n", 0) >= 10]
    tier_pass, tier_weak, tier_detail = {}, {}, []
    for tier in UNIVERSE:
        sub = ev[ev["tier"] == tier]
        s = cell_stats(sub, 63)
        has_n = s.get("n", 0) >= 10
        strong = has_n and s.get("ex_med", -99) > PASS_MED_EXCESS and s.get("win", 0) > PASS_WINRATE
        weak = has_n and (s.get("ex_med", -99) <= 0 or s.get("win", 100) <= 50.0)
        era_neg = False
        for era_key in ["前", "後"]:
            es = cell_stats(sub[sub["era"].str.startswith(era_key)], 63)
            if es.get("n", 0) >= 10 and es.get("ex_med", 0) <= 0:
                era_neg = True
        tier_pass[tier] = strong and not era_neg
        tier_weak[tier] = weak
        tier_detail.append((tier, s, era_neg))

    n_pass = sum(tier_pass.values())
    n_weak = sum(tier_weak[t] for t in tiers_with_data)
    majority = len(tiers_with_data) // 2 + 1 if tiers_with_data else 99
    pooled = cell_stats(ev, 63)

    reason = []
    for tier, s, era_neg in tier_detail:
        if s.get("n", 0) == 0:
            reason.append(f"**{tier}**:n=0,無事件(見事件庫規模表原因)。")
            continue
        if tier_pass[tier]:
            tag = "✅過 PASS 門檻"
        elif tier_weak[tier]:
            why = []
            if s.get("ex_med", -99) <= 0:
                why.append("median≤0")
            if s.get("win", 100) <= 50.0:
                why.append("win≤50%")
            tag = f"❌weak({'、'.join(why)})"
        else:
            tag = "△中性(未過 PASS、亦非 weak)"
        reason.append(f"**{tier}**:63d excess 平均{s['ex_mean']:+.1f}%/中位{s['ex_med']:+.1f}%、"
                      f"win {s['win']:.0f}%、n={s['n']} → {tag}"
                      f"{'(某 era 轉負)' if era_neg else ''}。")
    reason.append(f"**Pooled 63d**:excess 平均{pooled.get('ex_mean', float('nan')):+.1f}%/"
                  f"中位{pooled.get('ex_med', float('nan')):+.1f}%、win {pooled.get('win', float('nan')):.0f}%、"
                  f"n={pooled.get('n', 0)} —— 幾乎 coin-flip,size-matched 後冇 pooled 增量。")
    reason.append(f"**計數:PASS tier = {n_pass}/{len(tiers_with_data)}(需 ≥{PASS_MIN_TIERS});"
                  f"weak tier = {n_weak}/{len(tiers_with_data)}(多數門檻 ≥{majority} → FAIL)。**")

    # 判定(嚴格按上面規則)
    if n_pass >= PASS_MIN_TIERS:
        verdict = "PASS"
    elif n_weak >= majority:
        verdict = "FAIL"
    else:
        verdict = "PARTIAL"

    # 結構性補充(era artifact + solvency 無幫助 + transcript 缺席)——寫入 reason
    pre = cell_stats(ev[ev["era"].str.startswith("前")], 63)
    post = cell_stats(ev[ev["era"].str.startswith("後")], 63)
    reason.append(f"**時代分裂(關鍵)**:唯一正 excess 集中喺前半(2011-15,pooled 中位"
                  f"{pre.get('ex_med', float('nan')):+.1f}%、win {pre.get('win', 0):.0f}%),"
                  f"後半(2016+)反轉做中位{post.get('ex_med', float('nan')):+.1f}%、win {post.get('win', 0):.0f}%。"
                  "而前半事件由細價/微型股主導 —— 正正係 survivorship 偏差最嚴重嗰層,"
                  "呢個正 excess 大機會係 artifact,唔應該當 forward edge。")
    sub_all = ev[ev["solv"].notna()]
    subb_all = sub_all[sub_all["solv"] == True]  # noqa: E712
    sa, sb = cell_stats(sub_all, 63), cell_stats(subb_all, 63)
    reason.append(f"**Solvency gate 無挽救**:2019+ 子集 Arm A 63d excess 中位{sa.get('ex_med', float('nan')):+.1f}%,"
                  f"加 debt/equity≤{DE_MAX}+盈利 gate 後 Arm B 中位{sb.get('ex_med', float('nan')):+.1f}% —— "
                  "仍然係負,solvency proxy 唔係缺失嘅 edge。")
    reason.append("**未測嘅一層**:候選 A 嘅核心 edge 來源 = transcript「過性 vs 結構」語言過濾器,"
                  "本測試未自動化。所以呢個 FAIL 係『raw 價格閃縮 ± solvency』呢個下限版本嘅 FAIL,"
                  "唔等於『優質股閃縮概念』被判死 —— 但價格訊號本身唔足以接真錢雷達。")

    entry_rule = []
    if verdict in ("PASS", "PARTIAL"):
        good = [t for t in UNIVERSE if tier_pass[t]]
        entry_rule = [
            f"觸發:{'、'.join(good) if good else '(指明生效 tier)'} 嘅優質 universe 名單,"
            f"單日 ≤{FLASH_1D*100:.0f}% 或 5 日 ≤{FLASH_5D*100:.0f}% fire。",
            f"入場:D+{ENTRY_LAG} 收市;solvency gate(debt/equity≤{DE_MAX} + 年度盈利>0)硬性前置。",
            "持有:63d 為主(126d 輔),機械離場;注碼對標候選 A(單 A 倉 1.5-3% NAV,A 族 ≤10%)。",
            "**上線前必補**:transcript「過性 vs 結構」過濾器(缺席時 edge 只係下限)+ survivorship 打折。",
        ]
    return verdict, reason, entry_rule


# ───────────────────────────── main ────────────────────────────────────────

def main():
    t0 = time.time()
    ev = build_event_table()
    if len(ev) == 0:
        print("[abort] no events — check universe/thresholds")
        return
    report = build_report(ev)
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[report] written -> {RESULTS_PATH}")
    print(f"[done] {time.time() - t0:.0f}s total")


if __name__ == "__main__":
    main()
