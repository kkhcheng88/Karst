"""backtest/experiments/exp_trim_rule_backtest.py -- 「獲利回收 trim 規則」歷史回溯初驗
(Fable 交接書 P2-15;前瞻追蹤機制係 thesis/trim_rule_tracker.py,呢個係佢嘅歷史初驗)。

Question: 「擁擠複合 top decile + 倉位 >= 2x 成本 -> trim 1/3」呢條規則,套落歷史,有冇增量?

Method (mirror / increment / horizon -- memory validation-mirror-and-increment):
  mirror     : 呢個唔係選股訊號,係「持倉管理/減磅時機」規則,mirror 係喺同一個「已經升咗
               2x」嘅事件上,比較兩條前瞻路徑 -- TRIM 1/3(部分減磅)vs HOLD(揸到尾,對照組)。
  increment  : 擁擠代理(見下面 Data honesty)喺 2x-成本事件當下嘅讀數,對「事件之後嘅表現」
               係咪有增量預測力 -- 用 TRIGGER 組(擁擠 >=90 百分位)vs NOTRIGGER 組(<90)嘅
               forward return / drawdown 分佈對比嚟判斷:TRIGGER 組如果系統性跑輸/跌得深,
               trim 喺嗰一刻做就有正期望值(保住本金);冇分別就冇增量。
  horizon    : 事件後 63/126/252 個交易日(~3/6/12 個月),同 house 慣例一致(exp_capital_
               efficiency 等)。

Data honesty (載入 thesis/crowding_composite.py 已經披露嘅限制,呢度再收緊一層):
  - 今日 dashboard 用嘅 composite_pctile 係 attendance + bull_ratio 兩個輸入嘅平均,但
    bull_ratio 冇歷史時序(gooptions research-manifest 淨係一個「而家」嘅快照,冇逐季歷史),
    gs_flow 完全冇數據源。所以呢個回溯**淨係用 attendance percentile 單輸入**做擁擠代理 --
    誠實地話低咗今日 composite 嘅完整度,唔係同一個訊號嘅完整重現。
  - attendance percentile 呢度用 POINT-IN-TIME 計法:第 i 季嘅 percentile = 呢一季嘅
    analyst 人數,響「第 1..i 季已知歷史」入面嘅排名(唔包含未來季度)。呢個同
    thesis/crowding_composite.py production 版本(用全歷史,包括未來季度)唔一樣 -- production
    版本嗰種做法喺呢度用會構成 look-ahead bias,回測必須逐季重新計。extract_analysts() /
    get_transcripts() 呢兩個底層 parser 函數直接由 thesis/crowding_composite.py IMPORT 重用
    (唔重寫、唔修改嗰個檔),只係呢度自己逐季重新跑一次百分位計算。
  - basket = themes.yaml 現存(2026-07 定案)嘅 tickers 名單,套落歷史 = 適用性偏差(呢個
    theme 分類 2016 年根本未存在)+ 生存者偏差(2026 年仲喺名單入面嘅先會入呢個回測)。
  - entry 唔係真實歷史交易 -- 台帳啱啱先開倉,冇歷史成本可用。用 ROLLING ENTRY(每 126 個
    交易日一個模擬進場點,covers 整個 basket 已載入歷史)模擬「隨便邊個時間點買入,依家啱好
    升咗 2x」呢個情境,唔係話呢啲時間點真係策略歷史上買入過。Overlapping windows -> 自相關,
    已用 decluster(同一 theme 內,cross_date 63 交易日內只保留最早一個)做輕度處理,pooled
    (raw,未 decluster)版本並列作 robustness 對照。
  - 冇交易成本(呢個係 event-return 對比,唔係可執行 PnL)。freed cash(trim 出嚟嗰 1/3)
    假設閒置 0% 回報(保守;若果攞去做別的用途回報會更高,trim 嘅相對優勢只會更強唔會更弱)。

Run: python backtest/experiments/exp_trim_rule_backtest.py
"""
from __future__ import annotations

import os
import pickle
import sqlite3
import sys

import numpy as np
import pandas as pd
import yaml

_THIS = os.path.abspath(__file__)
_BACKTEST_DIR = os.path.dirname(os.path.dirname(_THIS))     # backtest/
_REPO_ROOT = os.path.dirname(_BACKTEST_DIR)                  # Karst/
_THESIS_DIR = os.path.join(_REPO_ROOT, "thesis")
sys.path.insert(0, _BACKTEST_DIR)
sys.path.insert(0, _THESIS_DIR)

from data import load as data_load          # noqa: E402 -- backtest/data.py, NOT modified
import crowding_composite as crowding_mod   # noqa: E402 -- thesis/crowding_composite.py, NOT modified
                                             # (reuses extract_analysts/get_transcripts/MIN_QUARTERS)

THEMES_PATH = os.path.join(_THESIS_DIR, "themes.yaml")
CORPUS_DB = os.path.join(_THESIS_DIR, "corpus.db")
CACHE_DIR = os.path.join(_BACKTEST_DIR, ".insider_data")     # existing gitignored disk-cache dir
                                                               # (exp_buyback_capital_allocation.py
                                                               # already reuses this dir for an
                                                               # unrelated .pkl cache -- same convention)
CACHE_PATH = os.path.join(CACHE_DIR, "trim_rule_backtest_cache.pkl")

TRIGGER_COMPOSITE_PCTILE = 90.0
TRIGGER_MULTIPLE = 2.0
TRIM_FRACTION = 1.0 / 3.0
ENTRY_STEP_DAYS = 126           # ~semi-annual rolling entries
HORIZONS = [63, 126, 252]
DECLUSTER_GAP_DAYS = 63         # same-theme events with cross_date within this many trading days
                                 # of an already-kept event are dropped from the DECLUSTERED table
TWO_HALVES_SPLIT = pd.Timestamp("2021-01-01")
HEADLINE_START = pd.Timestamp("2016-01-01")


# ============================================================================
# point-in-time attendance percentile (own reuse of crowding_mod's parser, own re-derivation
# of the percentile so it's point-in-time, not crowding_mod's full-history version)
# ============================================================================

def ticker_attendance_pit_series(con: sqlite3.Connection, ticker: str) -> pd.Series:
    df = crowding_mod.attendance_series(con, ticker)         # slug, published, n_analysts, method
    if df.empty:
        return pd.Series(dtype=float)
    ok = df[df["method"] != "failed"].reset_index(drop=True)
    if len(ok) < crowding_mod.MIN_QUARTERS:
        return pd.Series(dtype=float)
    vals = ok["n_analysts"].to_numpy()
    dates = ok["published"].to_numpy()
    out = {}
    for i in range(crowding_mod.MIN_QUARTERS - 1, len(ok)):
        hist = vals[: i + 1]                                  # up to and including quarter i -- no look-ahead
        pct = float((hist <= vals[i]).mean() * 100.0)
        out[pd.Timestamp(dates[i])] = pct
    return pd.Series(out).sort_index()


def build_pit_cache(tickers: list[str]) -> dict[str, pd.Series]:
    cache = {}
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "rb") as fh:
                cache = pickle.load(fh)
        except Exception:
            cache = {}
    pit = cache.get("pit_attendance", {})
    need = [t for t in tickers if t not in pit]
    if need:
        con = sqlite3.connect(f"file:{CORPUS_DB}?mode=ro", uri=True)
        for i, tk in enumerate(need):
            pit[tk] = ticker_attendance_pit_series(con, tk)
            if i % 15 == 14:
                print(f"  ... point-in-time attendance parsed {i+1}/{len(need)}")
        con.close()
        cache["pit_attendance"] = pit
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_PATH, "wb") as fh:
            pickle.dump(cache, fh)
    return {t: pit[t] for t in tickers}


def build_close_cache(tickers: list[str]) -> dict[str, pd.Series | None]:
    cache = {}
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "rb") as fh:
                cache = pickle.load(fh)
        except Exception:
            cache = {}
    closes = cache.get("closes", {})
    need = [t for t in tickers if t not in closes]
    if need:
        for i, tk in enumerate(need):
            try:
                closes[tk] = data_load(tk, adjusted=True, min_rows=60)["close"]
            except Exception:
                closes[tk] = None
            if i % 15 == 14:
                print(f"  ... prices loaded {i+1}/{len(need)}")
        cache["closes"] = closes
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_PATH, "wb") as fh:
            pickle.dump(cache, fh)
    return {t: closes[t] for t in tickers}


def build_basket(tickers: list[str], close_cache: dict) -> tuple[pd.Series | None, list[str], list[str]]:
    """Equal-weight, daily-rebalanced basket return series -- re-implementation of thesis/
    beta_check.py's build_basket() (NOT modified there; re-derived here self-contained so a
    single shared close_cache can serve all 15 themes without re-downloading overlapping
    tickers -- same "re-implement rather than couple" precedent as crowding_composite.py's
    own docstring re: exp_analyst_attendance.py)."""
    closes, failed = {}, []
    for tk in tickers:
        s = close_cache.get(tk)
        if s is None or len(s) < 60:
            failed.append(tk)
        else:
            closes[tk] = s
    if not closes:
        return None, [], failed
    prices = pd.concat(closes, axis=1, sort=True).sort_index().ffill().dropna(how="all")
    returns = prices.pct_change()
    basket_ret = returns.mean(axis=1, skipna=True).dropna()
    return basket_ret, list(closes.keys()), failed


# ============================================================================
# event generation: rolling entries -> first 2x-cost crossing -> crowding read at crossing
# ============================================================================

def find_events(theme_slug: str, cum: pd.Series, pit_by_ticker: dict[str, pd.Series]) -> list[dict]:
    idx = cum.index
    events = []
    if len(idx) < ENTRY_STEP_DAYS * 2:
        return events
    for pos in range(0, len(idx) - 1, ENTRY_STEP_DAYS):
        entry_date = idx[pos]
        entry_val = cum.iloc[pos]
        fwd = cum.iloc[pos + 1:]
        hit = fwd[fwd >= entry_val * 2.0]
        if hit.empty:
            continue
        cross_date = hit.index[0]
        cross_pos = idx.get_loc(cross_date)
        vals = []
        for s in pit_by_ticker.values():
            if s.empty:
                continue
            v = s.asof(cross_date)
            if pd.notna(v):
                vals.append(float(v))
        crowd = float(np.median(vals)) if vals else None
        events.append({
            "theme": theme_slug, "entry_date": entry_date, "cross_date": cross_date,
            "cross_pos": cross_pos, "days_to_2x": cross_pos - pos,
            "crowd_pctile": crowd, "n_tickers_cov": len(vals),
        })
    return events


def add_forward_outcomes(events: list[dict], cum: pd.Series) -> None:
    idx = cum.index
    for e in events:
        cp = e["cross_pos"]
        base = cum.iloc[cp]
        for h in HORIZONS:
            if cp + h < len(idx):
                fwd_ret = float(cum.iloc[cp + h] / base - 1.0)
                window = cum.iloc[cp:cp + h + 1]
                mdd = float((window / window.cummax() - 1.0).min())
            else:
                fwd_ret, mdd = float("nan"), float("nan")
            e[f"fwd_ret_{h}"] = fwd_ret
            e[f"mdd_{h}"] = mdd


def decluster(events: list[dict]) -> list[dict]:
    """Per theme, keep only the first event when cross_dates cluster within DECLUSTER_GAP_DAYS
    of an already-kept event -- crude but honest reduction of the mechanical overlap from
    ENTRY_STEP_DAYS rolling entries during fast-moving bull runs."""
    out = []
    by_theme: dict[str, list[dict]] = {}
    for e in events:
        by_theme.setdefault(e["theme"], []).append(e)
    for theme, evs in by_theme.items():
        evs = sorted(evs, key=lambda x: x["cross_pos"])
        kept_pos = []
        for e in evs:
            if all(abs(e["cross_pos"] - p) > DECLUSTER_GAP_DAYS for p in kept_pos):
                kept_pos.append(e["cross_pos"])
                out.append(e)
    return out


# ============================================================================
# stats helpers
# ============================================================================

def _welch_t(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = np.sqrt(va / len(a) + vb / len(b))
    return float((a.mean() - b.mean()) / se) if se else float("nan")


def group_stats(events: list[dict], h: int) -> dict:
    a = np.array([e[f"fwd_ret_{h}"] for e in events if e[f"fwd_ret_{h}"] == e[f"fwd_ret_{h}"]])
    m = np.array([e[f"mdd_{h}"] for e in events if e[f"mdd_{h}"] == e[f"mdd_{h}"]])
    if len(a) == 0:
        return {"n": 0}
    return {"n": len(a), "mean": float(a.mean()), "median": float(np.median(a)),
            "mdd_mean": float(m.mean()) if len(m) else float("nan"), "raw": a}


# ============================================================================
# main
# ============================================================================

def run():
    with open(THEMES_PATH, encoding="utf-8") as fh:
        themes_yaml = (yaml.safe_load(fh) or {}).get("themes", {}) or {}
    active = {slug: t for slug, t in themes_yaml.items() if t.get("status", "active") == "active"}
    all_tickers = sorted({tk for t in active.values() for tk in (t.get("tickers") or [])})
    print(f"=== exp_trim_rule_backtest: {len(active)} active themes, {len(all_tickers)} unique tickers ===")

    print("\nbuilding point-in-time attendance percentiles (thesis/corpus.db, cached) ...")
    pit_cache = build_pit_cache(all_tickers)
    print("loading total-return close prices (cached) ...")
    close_cache = build_close_cache(all_tickers)

    all_events = []
    coverage_rows = []
    for slug, t in sorted(active.items()):
        tickers = t.get("tickers") or []
        basket_ret, loaded, failed = build_basket(tickers, close_cache)
        if basket_ret is None or len(basket_ret) < ENTRY_STEP_DAYS * 2:
            coverage_rows.append({"theme": slug, "n_tickers": len(tickers), "n_loaded": len(loaded),
                                   "hist_start": None, "hist_end": None, "n_entries": 0, "n_events": 0})
            continue
        cum = (1.0 + basket_ret).cumprod()
        pit_by_ticker = {tk: pit_cache.get(tk, pd.Series(dtype=float)) for tk in loaded}
        n_pit_covered = sum(1 for s in pit_by_ticker.values() if not s.empty)
        events = find_events(slug, cum, pit_by_ticker)
        add_forward_outcomes(events, cum)
        all_events.extend(events)
        n_entries = len(range(0, len(cum.index) - 1, ENTRY_STEP_DAYS))
        coverage_rows.append({
            "theme": slug, "n_tickers": len(tickers), "n_loaded": len(loaded),
            "n_pit_covered": n_pit_covered, "hist_start": str(cum.index[0].date()),
            "hist_end": str(cum.index[-1].date()), "n_entries": n_entries, "n_events": len(events),
        })

    # ---- coverage table ----
    print(f"\n{'theme':<32}{'tick':>5}{'loaded':>7}{'pit_cov':>8}{'hist_start':>12}{'hist_end':>12}"
          f"{'entries':>9}{'2x_events':>11}")
    for r in coverage_rows:
        print(f"{r['theme']:<32}{r['n_tickers']:>5}{r.get('n_loaded',0):>7}{r.get('n_pit_covered','-'):>8}"
              f"{str(r.get('hist_start')):>12}{str(r.get('hist_end')):>12}{r.get('n_entries',0):>9}"
              f"{r.get('n_events',0):>11}")

    n_total = len(all_events)
    n_crowd_ok = sum(1 for e in all_events if e["crowd_pctile"] is not None)
    n_trigger = sum(1 for e in all_events if e["crowd_pctile"] is not None
                     and e["crowd_pctile"] >= TRIGGER_COMPOSITE_PCTILE)
    n_notrigger = n_crowd_ok - n_trigger
    print(f"\nTOTAL 2x-cost events (raw, overlapping, all history): {n_total}")
    print(f"  crowding computable: {n_crowd_ok}  (TRIGGER >=90pctile: {n_trigger}  NOTRIGGER <90: {n_notrigger}  "
          f"insufficient_data: {n_total - n_crowd_ok})")

    decl_events = decluster(all_events)
    print(f"DECLUSTERED events (same theme, cross_dates >={DECLUSTER_GAP_DAYS}d apart): {len(decl_events)}")

    def _report_block(events: list[dict], label: str, start: pd.Timestamp | None, end: pd.Timestamp | None):
        sub = events
        if start is not None:
            sub = [e for e in sub if e["cross_date"] >= start]
        if end is not None:
            sub = [e for e in sub if e["cross_date"] < end]
        trig = [e for e in sub if e["crowd_pctile"] is not None and e["crowd_pctile"] >= TRIGGER_COMPOSITE_PCTILE]
        notrig = [e for e in sub if e["crowd_pctile"] is not None and e["crowd_pctile"] < TRIGGER_COMPOSITE_PCTILE]
        print(f"\n--- {label}  (n_events={len(sub)}  TRIGGER={len(trig)}  NOTRIGGER={len(notrig)}) ---")
        print(f"  {'h':>4} | {'TRIG n':>7} {'mean%':>7} {'med%':>7} {'mdd%':>7} | "
              f"{'NOTRIG n':>8} {'mean%':>7} {'med%':>7} {'mdd%':>7} | {'Welch-t':>8}")
        rows = []
        for h in HORIZONS:
            gt = group_stats(trig, h)
            gn = group_stats(notrig, h)
            t_stat = float("nan")
            if gt.get("n", 0) >= 2 and gn.get("n", 0) >= 2:
                t_stat = _welch_t(gt["raw"], gn["raw"])
            gt_s = (f"{gt['n']:>7} {gt['mean']*100:>+6.1f}% {gt['median']*100:>+6.1f}% {gt['mdd_mean']*100:>+6.1f}%"
                    if gt.get("n", 0) else f"{0:>7} {'--':>7} {'--':>7} {'--':>7}")
            gn_s = (f"{gn['n']:>8} {gn['mean']*100:>+6.1f}% {gn['median']*100:>+6.1f}% {gn['mdd_mean']*100:>+6.1f}%"
                    if gn.get("n", 0) else f"{0:>8} {'--':>7} {'--':>7} {'--':>7}")
            print(f"  {h:>4} | {gt_s} | {gn_s} | {t_stat:>8.2f}")
            rows.append({"h": h, "trig": gt, "notrig": gn, "t": t_stat})
        return rows

    print("\n" + "=" * 100)
    print("POOLED (raw, overlapping) -- full history")
    print("=" * 100)
    pooled_full = _report_block(all_events, "POOLED full-history", None, None)

    print("\n" + "=" * 100)
    print("POOLED -- headline window 2016+")
    print("=" * 100)
    pooled_2016 = _report_block(all_events, "POOLED 2016+", HEADLINE_START, None)
    pre_half = _report_block(all_events, "2016-01-01..2020-12-31 (pre)", HEADLINE_START, TWO_HALVES_SPLIT)
    post_half = _report_block(all_events, "2021-01-01+ (post)", TWO_HALVES_SPLIT, None)

    print("\n" + "=" * 100)
    print("DECLUSTERED (robustness -- reduced overlap) -- 2016+")
    print("=" * 100)
    decl_2016 = _report_block(decl_events, "DECLUSTERED 2016+", HEADLINE_START, None)

    # ---- $ / capital-efficiency lens on TRIGGER events (2016+, pooled) ----
    print("\n" + "=" * 100)
    print(f"CAPITAL EFFICIENCY -- TRIM({TRIM_FRACTION:.2f} realized, 0% idle cash) vs HOLD, TRIGGER events, 2016+")
    print("=" * 100)
    trig_2016 = [e for e in all_events if e["cross_date"] >= HEADLINE_START and e["crowd_pctile"] is not None
                 and e["crowd_pctile"] >= TRIGGER_COMPOSITE_PCTILE]
    print(f"  {'h':>4} | {'n':>4} {'HOLD mean%':>11} {'TRIM mean%':>11} {'diff(TRIM-HOLD)':>16} {'win-rate TRIM':>14}")
    capeff_rows = []
    for h in HORIZONS:
        rets = np.array([e[f"fwd_ret_{h}"] for e in trig_2016 if e[f"fwd_ret_{h}"] == e[f"fwd_ret_{h}"]])
        if len(rets) == 0:
            print(f"  {h:>4} | {0:>4}   (no events with a full {h}d forward window)")
            capeff_rows.append({"h": h, "n": 0})
            continue
        hold_val = 1.0 + rets
        trim_val = (1 - TRIM_FRACTION) * (1.0 + rets) + TRIM_FRACTION * 1.0
        diff = trim_val - hold_val
        win = float((trim_val > hold_val).mean())
        print(f"  {h:>4} | {len(rets):>4} {hold_val.mean()*100-100:>+10.1f}% {trim_val.mean()*100-100:>+10.1f}% "
              f"{diff.mean()*100:>+15.1f}pp {win*100:>13.0f}%")
        capeff_rows.append({"h": h, "n": len(rets), "hold_mean": float(hold_val.mean() - 1),
                             "trim_mean": float(trim_val.mean() - 1), "diff_mean": float(diff.mean()),
                             "win_rate": win})

    print("\nNOTE: diff = -TRIM_FRACTION * fwd_ret ALGEBRAICALLY (freed cash at 0% is a pure descale) -- "
          "the only real empirical question is whether TRIGGER's fwd_ret distribution differs from "
          "NOTRIGGER's (the group_stats/Welch-t tables above), not this $-translation by itself.")

    return {
        "coverage": coverage_rows, "n_total_events": n_total, "n_crowd_ok": n_crowd_ok,
        "n_trigger": n_trigger, "n_notrigger": n_notrigger,
        "pooled_full": pooled_full, "pooled_2016": pooled_2016, "pre_half": pre_half,
        "post_half": post_half, "decl_2016": decl_2016, "capeff": capeff_rows,
    }


if __name__ == "__main__":
    run()
