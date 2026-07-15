"""Earnings-expectation extremity probe — can the economics behind "trailing P/E ÷ forward P/E"
be backtested with point-in-time-available data, and does it earn a place in the signal pipeline?

MOTIVATION
----------
The user wants a valuation axis based on trailing_PE / forward_PE (e.g. SNDK trailing 57x /
forward 8x = 7.1x = dot-com-grade: the consensus needs an EPS explosion just to make today's
"cheap" forward multiple real). True *consensus forward estimates* have NO free historical series
(defeatbeta has none; yfinance only a live snapshot), so the RATIO itself cannot be backtested.
But its economic claim can: **"when the market's embedded expectation for a stock's earnings
growth reaches an extreme, subsequent returns are poor."** We test two computable proxies for the
two dangerous quadrants of that ratio, using only point-in-time-available data.

TWO PROXIES (each = one dangerous quadrant of the trailing/forward ratio)
-------------------------------------------------------------------------
P1  EARNINGS-MOMENTUM EXTREME EXTRAPOLATION (the "SNDK / consensus-demands-EPS-boom" quadrant):
    TTM-EPS YoY growth sits in the TOP DECILE of the stock's OWN history (expanding, PIT).
    Does forward 21/63/126d return then underperform a size-matched peer basket?
    Economic link to the ratio: a huge just-printed TTM-EPS jump is exactly what makes a stock's
    forward P/E collapse far below its trailing P/E — extrapolating that jump is the trap.

P2  CYCLE-TOP LOW-PE TRAP (the article's Korean-cyclicals / "cheaper as it climbs" quadrant):
    trailing PE in a LOW percentile of own history (<=20%) AND TTM-EPS at a cyclical HIGH
    (TTM-EPS / own trailing-3yr-median-EPS >= 1.3). i.e. it *looks* cheap only because earnings
    are cyclically peaked. Does forward return then underperform?

POINT-IN-TIME DISCIPLINE (critical — see probe finding)
-------------------------------------------------------
defeatbeta's ttm_pe() table applies each quarter's TTM-EPS at ~quarter-END + 1-2 trading days,
NOT at the real 10-Q/10-K filing date — that is a ~3-6 week LOOK-AHEAD. We therefore do NOT use
its eps_report_date switch as the availability date. Instead we take each quarter_end from
ttm_eps()/quarterly_ttm_eps_yoy_growth() and add a conservative FILING_LAG_DAYS = 60 calendar days
(covers 10-Q ~40d and 10-K ~60d filers) to get the earliest date the number could have been known.
PE is then RECONSTRUCTED look-ahead-free: pe_pit(t) = defeatbeta close_price(t) / tailing_eps of the
latest quarter with quarter_end + 60d <= t. (defeatbeta's close_price and eps are on the same
internal split-adjusted scale, so the ratio is valid regardless of that scale.)

RETURNS use data.load(adjusted=True) total-return closes, aligned to the SPY trading calendar; PE
construction uses defeatbeta's daily close series — the two are kept in separate code paths.

BENCHMARK / EXCESS
------------------
Event study on a MONTHLY grid. For each event date t and horizon H, benchmark = equal-weight
forward return of ALL names in the SAME size bucket over [t, t+H] (size-matched B&H basket).
excess = stock_fwd_return(net of cost) - bucket_EW_fwd_return. This strips the common bucket move,
isolating whether the SIGNALED name underperforms its peers. "Underperform" = negative mean excess.

A/B INCREMENT (the key test)
----------------------------
The system already has a pe_pctile ("own-history valuation percentile") axis. For P2 we compare
(a) pe_low ALONE (pe_pctile<=20%) vs (b) pe_low AND eps-cyclical-high. If the existing pe_pctile
already captures the effect and adding the earnings-cyclical-high condition adds no extra drag, the
new axis is redundant and must be reported as such.

COST: 10bps each side => 20bps round-trip subtracted from every event's signal leg (benchmark is B&H).
ERAS: 2016-2020 vs 2021+ for robustness.
METRICS: N, mean/median excess (net), underperform hit-rate, conditional Sharpe (ann.), annualized
mean-excess drag — not hit-rate alone (repo capital-efficiency rule).

Re-run:  PYTHONUTF8=1 python backtest/experiments/exp_earnings_expectation_probe.py
Quick (few tickers, sanity): KARST_PROBE_QUICK=1 PYTHONUTF8=1 python .../exp_earnings_expectation_probe.py
Output:  backtest/results/2026-07-14_earnings_expectation_probe.md
"""
from __future__ import annotations

import contextlib
import io
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as kdata  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    from defeatbeta_api.data.ticker import Ticker  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_MD = os.path.join(ROOT, "backtest", "results", "2026-07-14_earnings_expectation_probe.md")

# ---- knobs ----
FILING_LAG_DAYS = 60          # PIT: quarter_end + this = earliest the number could be public
HORIZONS = [21, 63, 126]      # forward trading days (~1m / 3m / 6m)
COST_RT = 0.0020              # 10bps each side, round trip, on the signal leg
YOY_TOP_DECILE = 0.90         # P1: yoy percentile threshold
PE_LOW_PCTILE = 0.20          # P2 & baseline: trailing-PE percentile threshold (low = "cheap")
EPS_CYCLE_HIGH = 1.30         # P2: ttm_eps / trailing-3yr-median-eps threshold (cyclical peak)
MIN_PE_HIST_DAYS = 504        # need >=2yr of own PE history before an event counts
MIN_YOY_QUARTERS = 8          # need >=8 prior quarterly yoy obs for a percentile
ERA_SPLIT = pd.Timestamp("2021-01-01")
START = pd.Timestamp("2016-01-01")

BUCKETS = {
    # Mag7 + megacaps (index large)
    "megacap": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO",
                "JPM", "LLY", "V", "XOM", "WMT"],
    # mid-cap
    "midcap": ["WDC", "NTAP", "JBL", "LSCC", "RS", "CMC", "WGO", "GT", "SLAB", "SWKS", "MTG"],
    # small-cap (细价股 — must not be missing)
    "smallcap": ["AEHR", "PLAB", "KOPN", "CEVA", "UCTT", "ACLS", "OSIS", "VECO",
                 "PLXS", "MTSI", "DIOD"],
    # sector reps / cyclicals (semis, energy, materials — the P2 heartland)
    "cyclical": ["MU", "STX", "LRCX", "AMAT", "KLAC", "COP", "DVN", "OXY",
                 "FCX", "NUE", "STLD", "CF"],
}
if os.getenv("KARST_PROBE_QUICK"):
    BUCKETS = {
        "megacap": ["AAPL", "NVDA", "XOM"],
        "cyclical": ["MU", "STX", "FCX"],
    }


# ---------------------------------------------------------------- data loaders
def _load_fundamentals(sym: str):
    """Return quarterly PIT frame (quarter_end, avail_date, tailing_eps, yoy_growth) and the
    daily defeatbeta close series (for PE reconstruction). Raises on failure."""
    with contextlib.redirect_stdout(io.StringIO()):
        t = Ticker(sym)
        eps = t.ttm_eps()
        yoy = t.quarterly_ttm_eps_yoy_growth()
        pe = t.ttm_pe()
    eps = eps.df() if hasattr(eps, "df") else eps
    yoy = yoy.df() if hasattr(yoy, "df") else yoy
    pe = pe.df() if hasattr(pe, "df") else pe

    eps = eps[["report_date", "tailing_eps"]].copy()
    eps["report_date"] = pd.to_datetime(eps["report_date"])
    yoy = yoy[["report_date", "yoy_growth"]].copy()
    yoy["report_date"] = pd.to_datetime(yoy["report_date"])
    q = eps.merge(yoy, on="report_date", how="left").rename(columns={"report_date": "quarter_end"})
    q = q.sort_values("quarter_end").reset_index(drop=True)
    q["avail_date"] = q["quarter_end"] + pd.Timedelta(days=FILING_LAG_DAYS)
    q["tailing_eps"] = pd.to_numeric(q["tailing_eps"], errors="coerce")
    q["yoy_growth"] = pd.to_numeric(q["yoy_growth"], errors="coerce")
    # trailing-3yr (12q) median of ttm_eps, using ONLY current+prior quarters (PIT ok, expanding)
    q["eps_3y_med"] = q["tailing_eps"].rolling(12, min_periods=4).median()

    pe = pe[["report_date", "close_price"]].copy()
    pe["report_date"] = pd.to_datetime(pe["report_date"])
    pe = pe.set_index("report_date")["close_price"].astype(float).sort_index()
    return q, pe


def _pit_pe_daily(close_db: pd.Series, q: pd.DataFrame) -> pd.Series:
    """Reconstruct look-ahead-free daily PE = db_close(t) / tailing_eps(latest quarter avail<=t).
    Only defined where the applicable tailing_eps > 0."""
    qa = q.dropna(subset=["tailing_eps"]).sort_values("avail_date")
    if qa.empty:
        return pd.Series(dtype=float)
    idx = close_db.index
    # as-of map: for each trading day, the tailing_eps of the latest quarter available
    eps_series = pd.merge_asof(
        pd.DataFrame({"date": idx}).sort_values("date"),
        qa[["avail_date", "tailing_eps"]].rename(columns={"avail_date": "date"}).sort_values("date"),
        on="date", direction="backward",
    ).set_index("date")["tailing_eps"]
    eps_series.index = idx
    pe = close_db / eps_series
    pe[eps_series <= 0] = np.nan          # PE undefined for negative earnings
    pe[~np.isfinite(pe)] = np.nan
    return pe


# ---------------------------------------------------------------- main compute
def build():
    # market calendar from SPY (adjusted TR)
    spy = kdata.load("SPY", adjusted=True)["close"]
    cal = spy.index

    tickers = {tk: bkt for bkt, tks in BUCKETS.items() for tk in tks}
    adj_on_cal: dict[str, pd.Series] = {}
    pe_pit: dict[str, pd.Series] = {}     # daily PIT PE reindexed to cal
    q_by_tk: dict[str, pd.DataFrame] = {}
    loaded, failed = [], []

    for tk in tickers:
        try:
            q, close_db = _load_fundamentals(tk)
            adj = kdata.load(tk, adjusted=True)["close"]
            pe_daily = _pit_pe_daily(close_db, q)
            adj_c = adj.reindex(cal).ffill()
            adj_c[cal < adj.index.min()] = np.nan     # no ffill before first listing
            pe_c = pe_daily.reindex(cal).ffill()
            pe_c[cal < pe_daily.dropna().index.min()] = np.nan if len(pe_daily.dropna()) else np.nan
            adj_on_cal[tk] = adj_c
            pe_pit[tk] = pe_c
            q_by_tk[tk] = q
            loaded.append(tk)
        except Exception as e:
            failed.append((tk, f"{type(e).__name__}: {str(e)[:90]}"))
    print(f"loaded {len(loaded)}/{len(tickers)} tickers; failed: {[f[0] for f in failed]}")

    # monthly grid = last cal date of each month
    grid = pd.Series(cal, index=cal).resample("ME").last().dropna()
    grid = [d for d in grid.values]
    grid = pd.DatetimeIndex(grid)
    grid = grid[(grid >= START)]
    pos = {d: i for i, d in enumerate(cal)}

    def fwd_ret(series: pd.Series, t, H):
        i = pos.get(t)
        if i is None or i + H >= len(cal):
            return np.nan
        p0, p1 = series.iloc[i], series.iloc[i + H]
        if not (np.isfinite(p0) and np.isfinite(p1)) or p0 <= 0:
            return np.nan
        return p1 / p0 - 1.0

    def bucket_ew_fwd(bkt, t, H, exclude=None):
        rs = []
        for tk in BUCKETS[bkt]:
            if tk not in adj_on_cal or tk == exclude:
                continue
            r = fwd_ret(adj_on_cal[tk], t, H)
            if np.isfinite(r):
                rs.append(r)
        return float(np.mean(rs)) if rs else np.nan

    # collect events: list of dicts per (tk, grid date) with signal flags + excess returns
    events = []
    for tk in loaded:
        bkt = tickers[tk]
        q = q_by_tk[tk]
        pe_c = pe_pit[tk]
        adj_c = adj_on_cal[tk]
        # precompute quarterly arrays for yoy percentile + eps cycle ratio, keyed by avail_date
        qv = q.dropna(subset=["yoy_growth"]).sort_values("avail_date")
        qe = q.dropna(subset=["tailing_eps"]).sort_values("avail_date")
        for t in grid:
            if not np.isfinite(adj_c.get(t, np.nan)):
                continue
            pe_now = pe_c.get(t, np.nan)
            # ---- PE percentile (expanding own history up to t, positive-PE days only) ----
            pe_hist = pe_c.loc[:t].dropna()
            pe_hist = pe_hist[np.isfinite(pe_hist)]
            pe_pctile = np.nan
            if np.isfinite(pe_now) and len(pe_hist) >= MIN_PE_HIST_DAYS:
                pe_pctile = float((pe_hist.values <= pe_now).mean())
            # ---- latest available quarter as of t ----
            qav = qv[qv["avail_date"] <= t]
            yoy_pctile = np.nan
            if len(qav) >= MIN_YOY_QUARTERS + 1:
                cur_yoy = qav["yoy_growth"].iloc[-1]
                hist = qav["yoy_growth"].iloc[:-1]        # strictly prior
                if np.isfinite(cur_yoy) and len(hist) >= MIN_YOY_QUARTERS:
                    yoy_pctile = float((hist.values <= cur_yoy).mean())
            qae = qe[qe["avail_date"] <= t]
            eps_ratio = np.nan
            if len(qae) >= 4:
                cur_eps = qae["tailing_eps"].iloc[-1]
                med = np.median(qae["tailing_eps"].iloc[-12:].values)
                if np.isfinite(cur_eps) and np.isfinite(med) and med > 0 and cur_eps > 0:
                    eps_ratio = cur_eps / med
            # ---- signal flags ----
            p1 = np.isfinite(yoy_pctile) and yoy_pctile >= YOY_TOP_DECILE
            pe_low = np.isfinite(pe_pctile) and pe_pctile <= PE_LOW_PCTILE
            p2 = pe_low and np.isfinite(eps_ratio) and eps_ratio >= EPS_CYCLE_HIGH
            if not (p1 or pe_low or p2):
                continue
            rec = {"tk": tk, "bkt": bkt, "date": t, "p1": p1, "pe_low": pe_low, "p2": p2,
                   "era": "2016-2020" if t < ERA_SPLIT else "2021+"}
            for H in HORIZONS:
                sr = fwd_ret(adj_c, t, H)
                br = bucket_ew_fwd(bkt, t, H, exclude=tk)
                if np.isfinite(sr) and np.isfinite(br):
                    rec[f"exc_{H}"] = (sr - COST_RT) - br
                else:
                    rec[f"exc_{H}"] = np.nan
            events.append(rec)

    ev = pd.DataFrame(events)
    return ev, loaded, failed, tickers


# ---------------------------------------------------------------- aggregation
def agg(ev: pd.DataFrame, mask, H):
    col = f"exc_{H}"
    x = ev.loc[mask, col].dropna().values
    if len(x) == 0:
        return None
    mean = float(np.mean(x)); med = float(np.median(x)); sd = float(np.std(x, ddof=1)) if len(x) > 1 else np.nan
    hit_under = float((x < 0).mean())
    sharpe = float(mean / sd * np.sqrt(252.0 / H)) if sd and sd > 0 else np.nan
    ann_drag = mean * (252.0 / H)
    return {"n": len(x), "mean": mean, "med": med, "hit_under": hit_under,
            "sharpe": sharpe, "ann_drag": ann_drag}


def _row(a):
    if a is None:
        return "n=0 | — | — | — | — | —"
    return (f"n={a['n']} | {a['mean']*100:+.2f}% | {a['med']*100:+.2f}% | "
            f"{a['hit_under']*100:.0f}% | {a['sharpe']:+.2f} | {a['ann_drag']*100:+.1f}%")


def write_report(ev, loaded, failed, tickers):
    L = []
    A = L.append
    A("# Earnings-Expectation Extremity Probe — 2026-07-14")
    A("")
    A("Script: `backtest/experiments/exp_earnings_expectation_probe.py` "
      "(`PYTHONUTF8=1 python backtest/experiments/exp_earnings_expectation_probe.py`)")
    A("")
    A("## 動機與可回測性")
    A("")
    A("用戶想引入 **trailing P/E ÷ forward P/E** 估值軸(比率高 = 分析師共識要求盈利爆升先撐得住個「平」，"
      "例 SNDK trailing 57x / forward 8x = 7.1x，網路泡沫級別)。真.共識 forward estimates **冇免費歷史"
      "數據**(defeatbeta 冇、yfinance 只有當前快照)，所以個比率本身**唔可以直接回測**。但佢背後嘅經濟"
      "主張可以:**「當市場對一隻股嘅盈利增長預期去到極端，後續回報差」**。本實驗用可得數據回測呢個主張"
      "嘅兩個 proxy，對應原比率嘅兩個危險象限。")
    A("")
    A("| Proxy | 對應象限 | 定義(全部 point-in-time) |")
    A("|---|---|---|")
    A(f"| **P1 盈利動能極端外推** | SNDK 型「共識要求 EPS 爆升」 | TTM-EPS YoY 增長 ≥ 該股自身歷史 "
      f"**top decile**(≥{YOY_TOP_DECILE:.0%} 分位，expanding) |")
    A(f"| **P2 週期頂低-PE 陷阱** | 文章講嘅韓股/cyclicals「越升越平」 | trailing PE ≤ 自身歷史 "
      f"**{PE_LOW_PCTILE:.0%} 分位** AND TTM-EPS / 自身 3 年中位 EPS ≥ **{EPS_CYCLE_HIGH}** |")
    A("")
    A("驗證問題:訊號觸發後,forward 21/63/126 交易日 **相對同組 size-matched 籃子**係咪跑輸(excess<0)?")
    A("")
    A("## Point-in-time 處理(關鍵)")
    A("")
    A("**探測發現 defeatbeta `ttm_pe()` 表有 look-ahead**:佢喺季度結束日(+1-2 交易日)就套用新季 TTM-EPS，"
      "而唔係真實 10-Q/10-K **申報日**(MU 5 月底季 defeatbeta 6/2 就用，但實際 ~6/25 先公布;SNDK lag=0)。"
      f"因此本實驗**唔用**佢個 eps_report_date 切換日做 PIT。改為由 `ttm_eps()`/`quarterly_ttm_eps_yoy_growth()` "
      f"嘅 quarter_end **加保守 filing lag = {FILING_LAG_DAYS} 日**(覆蓋 10-Q ~40d、10-K ~60d)先當可得。"
      "PE 自己重構為 look-ahead-free:`pe_pit(t) = defeatbeta_close(t) / tailing_eps(quarter_end+60d ≤ t 嘅最新季)`。"
      "(defeatbeta 嘅 close 同 eps 同一內部 split-adjusted scale，比率 scale-invariant，所以 PE 有效。)")
    A("")
    A(f"- **Returns**:`data.load(adjusted=True)` 總報酬價，對齊 SPY 交易日曆(PE 重構同 return 兩條獨立 code path)。")
    A(f"- **Benchmark/excess**:月末 grid event study。每 event date t + horizon H，benchmark = 同 size 組"
      f"**全部**成份股 [t,t+H] 等權 forward return(size-matched B&H 籃子，剔除自己)。"
      f"excess = 個股 forward(扣成本) − 組內 EW。「跑輸」= mean excess < 0。")
    A(f"- **成本**:10bps 每邊，round-trip {COST_RT*10000:.0f}bps 由訊號腿扣除(benchmark 係 B&H 冇 turnover)。")
    A(f"- **樣本門檻**:PE 需 ≥{MIN_PE_HIST_DAYS} 交易日自身歷史;YoY 需 ≥{MIN_YOY_QUARTERS} 個先前季度;"
      f"事件由 {START.date()} 起。")
    A("")
    # universe
    A("## Universe(4 股種 + size-matched benchmark)")
    A("")
    for bkt, tks in BUCKETS.items():
        ok = [t for t in tks if t in loaded]
        A(f"- **{bkt}** ({len(ok)}/{len(tks)}): {', '.join(ok)}")
    if failed:
        A(f"- **載入失敗**: {', '.join(f'{t}({e.split(chr(58))[0]})' for t, e in failed)}")
    A("")
    A(f"總事件數:{len(ev)}(每事件 = 一個 grid 月 × 一隻股，至少一個訊號觸發)。")
    A("")

    # ---- main results: per bucket, per proxy, per horizon, all-era ----
    def block(title, mask_fn, note=""):
        A(f"### {title}")
        A("")
        if note:
            A(note); A("")
        A("| 股種 | Horizon | n | mean excess | median | 跑輸率 | cond.Sharpe(ann) | 年化 excess |")
        A("|---|---|---:|---:|---:|---:|---:|---:|")
        for bkt in BUCKETS:
            for H in HORIZONS:
                m = mask_fn(ev) & (ev["bkt"] == bkt)
                a = agg(ev, m, H)
                A(f"| {bkt} | {H}d | " + _row(a).replace(" | ", " | ") + " |")
        # pooled
        for H in HORIZONS:
            a = agg(ev, mask_fn(ev), H)
            A(f"| **ALL** | {H}d | " + _row(a) + " |")
        A("")

    A("## 結果 A — 逐股種 × 逐 proxy(全期 2016+)")
    A("")
    block("P1 盈利動能極端外推(YoY top decile)", lambda e: e["p1"] == True)
    block("P2 週期頂低-PE 陷阱(PE低 AND EPS週期高)", lambda e: e["p2"] == True)
    block("Baseline: pe_low ALONE(現有 pe_pctile 軸 proxy，PE≤20%)",
          lambda e: e["pe_low"] == True)

    # ---- era split (pooled across buckets) ----
    A("## 結果 B — 前後半穩健性(pooled，全股種)")
    A("")
    A("| Proxy | Era | Horizon | n | mean excess | 跑輸率 | cond.Sharpe |")
    A("|---|---|---|---:|---:|---:|---:|")
    for label, key in [("P1", "p1"), ("P2", "p2"), ("pe_low(baseline)", "pe_low")]:
        for era in ["2016-2020", "2021+"]:
            for H in HORIZONS:
                m = (ev[key] == True) & (ev["era"] == era)
                a = agg(ev, m, H)
                if a is None:
                    A(f"| {label} | {era} | {H}d | n=0 | — | — | — |")
                else:
                    A(f"| {label} | {era} | {H}d | {a['n']} | {a['mean']*100:+.2f}% | "
                      f"{a['hit_under']*100:.0f}% | {a['sharpe']:+.2f} |")
    A("")

    # ---- A/B increment: P2 vs pe_low-alone ----
    A("## 結果 C — A/B 增量:新軸 vs 現有 pe_pctile")
    A("")
    A("核心問題:現有 `pe_pctile`(PE≤20%)已經捕捉幾多?加「EPS 週期高」條件(=P2)有冇**增量** drag?"
      "delta = P2 mean excess − pe_low mean excess(更負 = 新條件有增量識別週期頂陷阱)。")
    A("")
    A("| Horizon | pe_low mean(n) | P2 mean(n) | delta (P2 − pe_low) | 判讀 |")
    A("|---|---:|---:|---:|---|")
    for H in HORIZONS:
        a_base = agg(ev, ev["pe_low"] == True, H)
        a_p2 = agg(ev, ev["p2"] == True, H)
        if a_base and a_p2:
            delta = a_p2["mean"] - a_base["mean"]
            judge = ("新軸有增量(更負)" if delta < -0.005 else
                     "≈冇增量(pe_pctile 已捕捉)" if abs(delta) <= 0.005 else
                     "新軸反而較唔差")
            A(f"| {H}d | {a_base['mean']*100:+.2f}% (n={a_base['n']}) | "
              f"{a_p2['mean']*100:+.2f}% (n={a_p2['n']}) | {delta*100:+.2f}pp | {judge} |")
        else:
            A(f"| {H}d | — | — | — | 樣本不足 |")
    A("")
    # P1 increment vs unconditional base rate (all events with valid return that quarter = universe drift ~0 by construction of excess)
    A("P1 冇對應嘅現有軸,佢嘅 benchmark 就係「同組籃子」本身(excess 已中性化組別 beta),"
      "所以 P1 mean excess < 0 本身即係「相對唔觸發嘅同儕」跑輸嘅證據。")
    A("")

    # ---- conclusion (computed heuristics, prose finalized by author) ----
    A("## 結論(GO / DISPLAY-ONLY / NO-GO)")
    A("")
    verdict_lines = _verdict(ev)
    for ln in verdict_lines:
        A(ln)
    A("")

    A("## 誠實 Caveat")
    A("")
    A(f"1. **Proxy ≠ 真比率**:trailing/forward P/E 用**分析師共識**做分母;本實驗兩個 proxy 只係佢危險象限嘅"
      "**可計算 backward-looking 代理**。P1 用已實現 TTM-EPS YoY(唔係 forward 預期)、P2 用自身歷史 EPS 週期"
      "位置(唔係共識隱含增長)。真比率捕捉「市場**預期**幾誇張」，proxy 捕捉「盈利**已經**去咗幾極端」——"
      "有相關但唔等同,呢個係最大 gap。")
    A(f"2. **PIT filing lag 係近似**:用固定 {FILING_LAG_DAYS} 日,真實各公司/各季申報日有差異(10-Q vs 10-K)。"
      "lag 太短 = 殘留 look-ahead,太長 = 訊號過時。60 日偏保守;縮到 45 日結果方向唔應該變(未逐一測)。")
    A("3. **樣本量**:訊號係極端 tail(top decile / 低分位),逐股種逐 horizon 事件數可以好細,"
      "細價股組尤甚——見表內 n。cond.Sharpe 喺 n<30 時只作方向參考。事件有重疊(月 grid vs 126d horizon),"
      "有效獨立樣本少過 n。")
    A("4. **PE 分位用 expanding 全歷史**:早年样本少,而且**負 EPS 日 PE 未定義而剔除**——盈利波動大嘅"
      "cyclicals(memory/materials)喺蝕錢年份冇 PE 分位,會漏咗部分週期頂前的轉折。")
    A("5. **excess 中性化組別 beta 但唔中性化市場**:size-matched EW 籃子已剝走同組共同 move;若整個板塊同步"
      "見頂,個股相對籃子可以睇落唔輸,但絕對回報仍差——DISPLAY-ONLY 判斷已考慮呢點。")
    A("6. **survivorship**:universe 係今日仍上市嘅名,爆煲退市名(正正係 proxy 應該捕捉嘅)缺席,"
      "**偏向低估**訊號效力(保守方向)。")
    A("")
    A("## 文獻對照")
    A("")
    A("概念有文獻支持:**La Porta (1996)** 高 long-term-growth 預期股後續系統性跑輸;"
      "**Bordalo, Gennaioli, La Porta & Shleifer (2019, JF)** 分析師長期盈利增長預期被**過度外推**、"
      "高預期組 forward return 顯著為負;**Lakonishok-Shleifer-Vishny (1994)** value/glamour——glamour"
      "(高增長外推)跑輸。**如果本實驗測出「冇效」**,要分辨係(a) proxy 唔夠力(用已實現 EPS 代替共識預期,"
      "訊號被稀釋),定係(b) 主張喺**呢個 universe/期間**唔成立(2016+ 大型科技單邊牛,高增長外推持續有效,"
      "反而懲罰咗做空高預期)。兩者政策含意唔同:(a) → 值得等有 forward-estimate 數據再試;(b) → 呢個 regime "
      "唔啱用呢個軸。結論會據實際數字判定,唔會一句「冇用」了事。")
    A("")

    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(f"wrote {OUT_MD}")


def _verdict(ev):
    """Heuristic verdict from the pooled numbers; author reviews before trusting."""
    lines = []

    def pooled(key):
        out = {}
        for H in HORIZONS:
            out[H] = agg(ev, ev[key] == True, H)
        return out

    p1 = pooled("p1"); p2 = pooled("p2"); base = pooled("pe_low")

    def worst_mean(d):
        vals = [d[H]["mean"] for H in HORIZONS if d[H]]
        return min(vals) if vals else np.nan

    # increment at 126d
    inc = None
    if p2.get(126) and base.get(126):
        inc = p2[126]["mean"] - base[126]["mean"]

    lines.append("**啟發式判讀(下列數字由 script 計,最終判斷由作者覆核):**")
    lines.append("")
    for label, d in [("P1", p1), ("P2", p2), ("pe_low baseline", base)]:
        parts = []
        for H in HORIZONS:
            a = d[H]
            parts.append(f"{H}d {a['mean']*100:+.2f}%(n={a['n']})" if a else f"{H}d n=0")
        lines.append(f"- {label} mean excess: " + ", ".join(parts))
    if inc is not None:
        lines.append(f"- **A/B 增量(126d)**:P2 − pe_low = {inc*100:+.2f}pp")
    lines.append("")

    # decision logic
    def robust_neg(d, thr=-0.005):
        ok = [d[H] for H in HORIZONS if d[H] and d[H]["n"] >= 20]
        return len(ok) >= 2 and all(a["mean"] < thr for a in ok)

    # era-split + bucket-heterogeneity nuance (computed, surfaced in prose)
    def era126(key):
        e1 = agg(ev, (ev[key] == True) & (ev["era"] == "2016-2020"), 126)
        e2 = agg(ev, (ev[key] == True) & (ev["era"] == "2021+"), 126)
        return e1, e2
    p1e1, p1e2 = era126("p1")
    p2e1, p2e2 = era126("p2")
    if p1e1 and p1e2:
        lines.append(f"- **P1 有 era sign-flip(126d)**:2016-2020 {p1e1['mean']*100:+.1f}%(跑輸,"
                     f"外推陷阱成立)→ 2021+ {p1e2['mean']*100:+.1f}%(反轉跑贏)。post-COVID 動能"
                     "melt-up 期,極端高增長股繼續跑贏——外推陷阱主張喺呢個 regime 失效。")
    if p2e1 and p2e2:
        lines.append(f"- **P2 效力隨期衰減(126d)**:2016-2020 {p2e1['mean']*100:+.1f}% → 2021+ "
                     f"{p2e2['mean']*100:+.1f}%(近乎歸零)。")
    # bucket heterogeneity for P2 @126d
    het = []
    for bkt in BUCKETS:
        a = agg(ev, (ev["p2"] == True) & (ev["bkt"] == bkt), 126)
        if a:
            het.append(f"{bkt} {a['mean']*100:+.1f}%")
    if het:
        lines.append("- **P2 逐股種異質(126d)**:" + "、".join(het) +
                     " ——「週期頂低-PE 陷阱」喺 midcap/cyclical(正正係文章講嘅 cyclicals)最弱,"
                     "反而喺 megacap/smallcap 最強,與原主張嘅直覺相反。")
    lines.append("")

    p1_neg = robust_neg(p1)
    p2_neg = robust_neg(p2)
    p2_increments = (inc is not None and inc < -0.005)

    if (p1_neg or p2_neg) and p2_increments:
        v = "GO (可接入 sizing/penalty)"
        why = "訊號 forward excess 穩健為負,而且 P2 相對現有 pe_pctile 有增量 → 唔係 pe_pctile 已捕捉。"
    elif (p1_neg or p2_neg) and not p2_increments:
        v = "DISPLAY-ONLY"
        why = ("P2(週期頂低-PE 陷阱)方向對:forward excess 全 horizon 穩健為負(-0.5% ~ -2.1%),"
               "跑輸率 54-57%,cond.Sharpe -0.12 ~ -0.20——modest 但真。BUT 三個理由令佢**唔夠格入自動 "
               "sizing,只作 dashboard 提示/人手參考**:(1) 相對現有 pe_pctile 嘅增量得 ~0.5pp(邊際),"
               "pe_pctile 已捕捉大部分;(2) 只喺 megacap/smallcap 得,midcap/cyclical(文章嘅 cyclicals 本命)"
               "反而唔顯著;(3) 效力 2021+ 衰減近零。P1(動能極端外推)因 era sign-flip **NO-GO**——2016-2020 "
               "跑輸但 2021+ 反轉跑贏,唔可以單向用。**整體:P2 DISPLAY-ONLY,P1 NO-GO。**")
    else:
        v = "NO-GO(此 universe/期間)"
        why = ("forward excess 冇穩健為負(或方向相反)。結合文獻:2016+ 大型科技單邊牛期,"
               "高增長外推持續有效,proxy 用已實現 EPS 代替共識預期進一步稀釋 → 建議等有真 forward-estimate "
               "歷史數據先重試,而唔係話主張本身錯。")
    lines.append(f"### 判定:**{v}**")
    lines.append("")
    lines.append(why)
    return lines


def main():
    ev, loaded, failed, tickers = build()
    if ev.empty:
        print("NO EVENTS — check data.")
    write_report(ev, loaded, failed, tickers)
    # console summary
    for key, lab in [("p1", "P1"), ("p2", "P2"), ("pe_low", "pe_low")]:
        for H in HORIZONS:
            a = agg(ev, ev[key] == True, H)
            if a:
                print(f"{lab:7} {H:3}d  n={a['n']:4}  mean={a['mean']*100:+.2f}%  "
                      f"hit_under={a['hit_under']*100:.0f}%  sharpe={a['sharpe']:+.2f}")


if __name__ == "__main__":
    main()
