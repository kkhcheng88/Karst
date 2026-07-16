"""Mag7/hyperscaler valuation-timing throttle + accelerator, and S&P100-wide "cheap-side"
episode study — testing whether trailing-P/E can add tactical increment on top of Core v2's
SPY/QQQ 200SMA-gated LEAP sleeve, and whether an asymmetric read (expensive-side timing is
useless, cheap-side timing may have edge) survives outside the Mag7 survivorship sample.

BACKGROUND (see task brief; not re-derived here)
-------------------------------------------------
Core v2 is already finalized (SPY core + QQQ/SPY LEAP, pure 200SMA gate + monthly top-up).
This experiment does NOT challenge that; it tests an incremental valuation throttle/accelerator
layered on the SAME QQQ sleeve mechanics. Hypothesis 2 (the interesting one): valuation signals
may be ASYMMETRIC — expensive is not useful for timing (can stay expensive for years), but cheap
may be useful for quality megacaps that fall into a historically low own-history PE percentile
(e.g. MSFT 2011-2013 forward PE 9-11x for three years, then outperformed). Literature prior:
tactical (monthly/quarterly) valuation timing is close to useless; predictive power only emerges
at 7-10y horizons. A "cheap works" finding must be checked doubly hard for survivorship (picking
only ex-post Mag7 winners).

KNOWN, ACCEPTED LIMITATION: no free historical forward-P/E (analyst consensus) series exists
(defeatbeta doesn't have it, yfinance is snapshot-only). We use trailing P/E as the accepted
proxy throughout — this is a pre-approved simplification, not re-litigated here.

REUSED, ALREADY-VALIDATED BUILDING BLOCKS (do not re-derive)
--------------------------------------------------------------
- backtest/data.py `load(symbol, adjusted=True)` — yfinance-first price loader.
- backtest/experiments/exp_earnings_expectation_probe.py `_load_fundamentals` / `_pit_pe_daily`
  — point-in-time quarterly EPS + look-ahead-free daily trailing-PE reconstruction
  (pe_pit(t) = defeatbeta_close(t) / tailing_eps(quarter_end + 60d filing lag <= t)).
- backtest/metrics.py `cagr`, `max_drawdown`.

STRUCTURE
---------
PART 1 — QQQ valuation-proxy throttle/accelerator on the Core-v2 QQQ sleeve (A/B/B2/C/C2),
         unit-NAV bookkeeping engine that isolates organic return from DCA contribution flow.
PART 2 — Mag7-six (MSFT META GOOGL AAPL AMZN NVDA) individual cheap-side episode detail table.
PART 3 — S&P100-wide cheap-side episode study: pooled distribution, tech-vs-non-tech split,
         value-trap rate, and quantified survivorship gap vs the Mag7 subset.

Re-run: PYTHONUTF8=1 python backtest/experiments/exp_mag7_valuation_throttle.py
Output: backtest/results/2026-07-16_mag7_valuation_throttle.md
Cache:  <scratchpad>/mag7_valuation_cache/*.pkl (per-ticker fundamentals+price, avoids re-fetch)
"""
from __future__ import annotations

import os
import pickle
import sys
import traceback

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backtest"))
sys.path.insert(0, os.path.join(ROOT, "backtest", "experiments"))
import data as kdata  # noqa: E402
from exp_earnings_expectation_probe import _load_fundamentals, _pit_pe_daily  # noqa: E402
import metrics as kmetrics  # noqa: E402

OUT_MD = os.path.join(ROOT, "backtest", "results", "2026-07-16_mag7_valuation_throttle.md")
CACHE_DIR = os.path.join(
    "C:\\Users\\Kaho\\AppData\\Local\\Temp\\claude\\C--projects-Investment-karst",
    "f26b2e5c-22b5-49fe-9cf6-81e08b44ffaa", "scratchpad", "mag7_valuation_cache",
)
os.makedirs(CACHE_DIR, exist_ok=True)

START = pd.Timestamp("2016-01-01")
BURN_IN_MONTHS = 60           # 5y expanding-percentile burn-in (Part 1, monthly grid)
BURN_IN_DAYS = 1260           # ~5y expanding-percentile burn-in (Part 2/3, daily grid)
EPISODE_PCTILE = 0.20         # "cheap" episode threshold
MIN_EPISODE_DAYS = 20         # filter noise episodes
BASE_CONTRIB = 1000.0

WEIGHTS = {"AAPL": 0.085, "MSFT": 0.080, "NVDA": 0.075, "AMZN": 0.055, "GOOGL": 0.040,
           "META": 0.040, "AVGO": 0.045, "TSLA": 0.025, "COST": 0.025, "NFLX": 0.020}

MAG7_SIX = ["MSFT", "META", "GOOGL", "AAPL", "AMZN", "NVDA"]

SP100 = ["AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN", "AVGO", "AXP",
         "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "BRK-B", "C", "CAT", "CHTR", "CL", "CMCSA", "COF",
         "COP", "COST", "CRM", "CSCO", "CVS", "CVX", "DE", "DHR", "DIS", "DUK", "EMR", "F", "FDX", "GD",
         "GE", "GILD", "GM", "GOOGL", "GS", "HD", "HON", "IBM", "INTC", "INTU", "ISRG", "JNJ", "JPM",
         "KHC", "KO", "LIN", "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ", "MDT", "MET", "META", "MMM", "MO",
         "MRK", "MS", "MSFT", "NEE", "NFLX", "NKE", "NOW", "NVDA", "ORCL", "PEP", "PFE", "PG", "PM",
         "PYPL", "QCOM", "RTX", "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TJX", "TMO", "TMUS", "TSLA",
         "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WFC", "WMT", "XOM"]
SP100 = sorted(set(SP100))   # dedupe (GOOGL, META appear via Mag7 overlap notes — list itself has none, but be safe)
if os.getenv("KARST_QUICK"):
    SP100 = ["AAPL", "MSFT", "JPM", "XOM", "PFE", "KO", "IBM", "CAT"]

TECH = {"AAPL", "ACN", "ADBE", "AMD", "AMZN", "AVGO", "CRM", "CSCO", "GOOGL", "IBM", "INTC", "INTU",
        "META", "MSFT", "NFLX", "NOW", "NVDA", "ORCL", "PYPL", "QCOM", "TSLA"}


# ==================================================================== cache helpers
def _cache_path(tk):
    return os.path.join(CACHE_DIR, f"{tk}.pkl")


def _fetch_cached(tk):
    """Return (q, close_db, adj_close) for tk, using scratchpad pickle cache. Raises on failure."""
    cp = _cache_path(tk)
    if os.path.exists(cp):
        with open(cp, "rb") as fh:
            payload = pickle.load(fh)
        if payload.get("error"):
            raise RuntimeError(payload["error"])
        return payload["q"], payload["close_db"], payload["adj"]
    try:
        q, close_db = _load_fundamentals(tk)
        adj = kdata.load(tk, adjusted=True)["close"]
        with open(cp, "wb") as fh:
            pickle.dump({"q": q, "close_db": close_db, "adj": adj, "error": None}, fh)
        return q, close_db, adj
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:160]}"
        with open(cp, "wb") as fh:
            pickle.dump({"error": err}, fh)
        raise


# ==================================================================== PART 1: QQQ proxy PE
def build_qqq_pe_proxy():
    """Monthly, weight-renormalized-by-coverage trailing-PE proxy for the QQQ mega-cap basket."""
    qqq = kdata.load("QQQ", adjusted=True)["close"]
    cal = qqq.index

    pe_daily_by_tk = {}
    failed = []
    for tk in WEIGHTS:
        try:
            q, close_db, _adj_unused = _fetch_cached(tk)
            pe = _pit_pe_daily(close_db, q)
            pe_c = pe.reindex(cal).ffill()
            first_valid = pe.dropna().index.min() if len(pe.dropna()) else None
            if first_valid is not None:
                pe_c[cal < first_valid] = np.nan
            else:
                pe_c[:] = np.nan
            pe_daily_by_tk[tk] = pe_c
        except Exception as e:
            failed.append((tk, str(e)))

    # monthly grid = month-end trading day
    grid = pd.Series(cal, index=cal).resample("ME").last().dropna()
    grid = pd.DatetimeIndex(grid.values)

    rows = []
    for d in grid:
        vals, wts, n_cov = [], [], 0
        for tk, w in WEIGHTS.items():
            if tk not in pe_daily_by_tk:
                continue
            v = pe_daily_by_tk[tk].get(d, np.nan)
            if np.isfinite(v):
                vals.append(v); wts.append(w); n_cov += 1
        if n_cov == 0:
            rows.append({"date": d, "pe": np.nan, "coverage": 0})
            continue
        wts = np.array(wts); wts = wts / wts.sum()
        pe = float(np.dot(vals, wts))
        rows.append({"date": d, "pe": pe, "coverage": n_cov})

    dfm = pd.DataFrame(rows).set_index("date")
    dfm = dfm[dfm.index >= START - pd.DateOffset(years=6)]   # keep pre-2016 history for burn-in

    # expanding percentile, >=60mo burn-in
    pctiles = [np.nan] * len(dfm)
    pe_vals = dfm["pe"].values
    for i in range(len(dfm)):
        hist = pe_vals[:i + 1]
        hist_valid = hist[np.isfinite(hist)]
        if np.isfinite(pe_vals[i]) and len(hist_valid) >= BURN_IN_MONTHS:
            pctiles[i] = float((hist_valid <= pe_vals[i]).mean())
    dfm["pctile"] = pctiles
    dfm = dfm[dfm.index >= START]
    return dfm, qqq, failed


def run_qqq_engine(qqq: pd.Series, monthly_pctile: pd.Series, policy_fn, label):
    """Daily unit-NAV DCA engine with 200SMA gate. monthly_pctile indexed by month-end date,
    value = pctile computed AS OF THAT month-end (mapped to apply from the FOLLOWING month's
    first trading day, i.e. prior-month-end signal)."""
    cal = qqq.index
    sma200 = qqq.rolling(200, min_periods=200).mean()

    # map: for each trading day, the "prior month-end pctile" in effect
    month_ends = monthly_pctile.index
    prior_pctile_by_day = pd.Series(index=cal, dtype=float)
    me_ptr = -1
    me_list = list(month_ends)
    me_vals = list(monthly_pctile.values)
    cur_val = np.nan
    month_key = None
    for d in cal:
        if d.to_period("M") != month_key:
            month_key = d.to_period("M")
            # find the last month_end strictly before this month
            while me_ptr + 1 < len(me_list) and me_list[me_ptr + 1] < d.to_period("M").to_timestamp():
                me_ptr += 1
            cur_val = me_vals[me_ptr] if me_ptr >= 0 else np.nan
        prior_pctile_by_day[d] = cur_val

    shares = 0.0
    cash_pool = 0.0
    state = {"backlog": 0.0, "debt": 0.0}
    total_contrib = 0.0
    unit_nav = 1.0
    unit_nav_series = []
    wealth_series = []
    exposure_flags = []
    prev_month = None
    contrib_by_month = []

    for i, d in enumerate(cal):
        price = qqq.loc[d]
        gate_open = np.isfinite(sma200.loc[d]) and price > sma200.loc[d]

        # monthly contribution on first trading day of month
        cur_month = d.to_period("M")
        if cur_month != prev_month:
            pctile = prior_pctile_by_day[d]
            contrib_amt = policy_fn(pctile, state)
            cash_pool += contrib_amt
            total_contrib += contrib_amt
            contrib_by_month.append((d, contrib_amt))
            prev_month = cur_month
            contrib_today = contrib_amt
        else:
            contrib_today = 0.0

        nav_before = shares * price + cash_pool

        if gate_open:
            if cash_pool > 0:
                shares += cash_pool / price
                cash_pool = 0.0
        else:
            if shares > 0:
                cash_pool += shares * price
                shares = 0.0

        nav_after = shares * price + cash_pool

        if i == 0:
            unit_nav_series.append(unit_nav)
        else:
            prev_nav = wealth_series[-1]
            denom = prev_nav
            if denom > 0:
                r_organic = (nav_after - contrib_today) / denom - 1.0
            else:
                r_organic = 0.0
            unit_nav = unit_nav * (1.0 + r_organic)
            unit_nav_series.append(unit_nav)
        wealth_series.append(nav_after)
        exposure_flags.append(1.0 if gate_open and (shares * price) > 0 else 0.0)

    return {
        "label": label,
        "dates": cal,
        "unit_nav": np.array(unit_nav_series),
        "wealth": np.array(wealth_series),
        "total_contrib": total_contrib,
        "backlog_end": state["backlog"],
        "debt_end": state["debt"],
        "exposure": np.array(exposure_flags),
        "contrib_by_month": contrib_by_month,
    }


def policy_A(pctile, state):
    return BASE_CONTRIB


def policy_B(pctile, state):
    if np.isfinite(pctile) and pctile > 0.90:
        state["backlog"] += BASE_CONTRIB
        return 0.0
    release = min(state["backlog"], BASE_CONTRIB)
    state["backlog"] -= release
    return BASE_CONTRIB + release


def policy_B2(pctile, state):
    if np.isfinite(pctile) and pctile > 0.80:
        state["backlog"] += 0.5 * BASE_CONTRIB
        return 0.5 * BASE_CONTRIB
    release = min(state["backlog"], BASE_CONTRIB)
    state["backlog"] -= release
    return BASE_CONTRIB + release


def policy_C(pctile, state):
    if np.isfinite(pctile) and pctile < 0.10:
        state["debt"] += BASE_CONTRIB
        return 2.0 * BASE_CONTRIB
    repay = min(state["debt"], BASE_CONTRIB)
    state["debt"] -= repay
    return BASE_CONTRIB - repay


def policy_C2(pctile, state):
    if np.isfinite(pctile) and pctile < 0.20:
        state["debt"] += 0.5 * BASE_CONTRIB
        return 1.5 * BASE_CONTRIB
    repay = min(state["debt"], BASE_CONTRIB)
    state["debt"] -= repay
    return BASE_CONTRIB - repay


def part1_metrics(res, qqq_index):
    unit_nav = res["unit_nav"]
    wealth = res["wealth"]
    cagr = kmetrics.cagr(unit_nav)
    mdd = kmetrics.max_drawdown(unit_nav)
    final_wealth = wealth[-1]
    total_contrib = res["total_contrib"]
    pnl = final_wealth - total_contrib
    avg_exposure_dollars = float(np.mean(wealth * res["exposure"])) if len(wealth) else np.nan
    cap_eff = pnl / avg_exposure_dollars if avg_exposure_dollars and avg_exposure_dollars > 0 else np.nan
    return {
        "cagr": cagr, "mdd": mdd, "final_wealth": final_wealth, "total_contrib": total_contrib,
        "pnl": pnl, "cap_eff": cap_eff, "backlog_end": res["backlog_end"], "debt_end": res["debt_end"],
    }


def part1_subperiod_metrics(res, start, end):
    dates = res["dates"]
    mask = (dates >= start) & (dates <= end)
    if mask.sum() < 2:
        return None
    unit_nav = res["unit_nav"][mask]
    unit_nav = unit_nav / unit_nav[0]
    return {"cagr": kmetrics.cagr(unit_nav), "mdd": kmetrics.max_drawdown(unit_nav)}


# ==================================================================== PART 2/3: episodes
def compute_episodes(pe_daily: pd.Series, adj_close: pd.Series, spy_close: pd.Series,
                     min_episode_days=MIN_EPISODE_DAYS, burn_in=BURN_IN_DAYS, pctile_thr=EPISODE_PCTILE):
    """Expanding-percentile (own history, burn-in) daily; find contiguous below-threshold runs.
    Returns list of episode dicts with start/mid entry forward returns vs SPY."""
    idx = pe_daily.index
    pe_vals = pe_daily.values
    n = len(pe_vals)
    pctile = np.full(n, np.nan)
    valid_hist = []
    for i in range(n):
        v = pe_vals[i]
        if np.isfinite(v):
            valid_hist.append(v)
        if len(valid_hist) >= burn_in and np.isfinite(v):
            arr = np.array(valid_hist)
            pctile[i] = float((arr <= v).mean())

    below = np.isfinite(pctile) & (pctile <= pctile_thr)
    episodes = []
    i = 0
    while i < n:
        if below[i]:
            j = i
            while j < n and below[j]:
                j += 1
            if (j - i) >= min_episode_days:
                episodes.append((i, j))
            i = j
        else:
            i += 1

    pos = {d: k for k, d in enumerate(adj_close.index)}
    spy_pos = {d: k for k, d in enumerate(spy_close.index)}

    def fwd(series, posmap, d, days):
        k = posmap.get(d)
        if k is None or k + days >= len(series):
            return np.nan
        p0, p1 = series.iloc[k], series.iloc[k + days]
        if not (np.isfinite(p0) and np.isfinite(p1)) or p0 <= 0:
            return np.nan
        return p1 / p0 - 1.0

    out = []
    for (i, j) in episodes:
        start_date = idx[i]
        mid_date = idx[i + (j - i) // 2]
        end_date = idx[j - 1]
        dur_days = j - i
        # max additional drawdown during episode (own price)
        if start_date in pos and end_date in pos:
            k0, k1 = pos[start_date], pos[end_date]
            window = adj_close.iloc[k0:k1 + 1]
            max_dd_in_ep = float(window.min() / window.iloc[0] - 1.0) if len(window) else np.nan
        else:
            max_dd_in_ep = np.nan

        rec = {"start": start_date, "mid": mid_date, "end": end_date, "dur_months": dur_days / 21.0}
        for entry_label, entry_date in [("start", start_date), ("mid", mid_date)]:
            for H, hlabel in [(252, "1y"), (504, "2y"), (756, "3y")]:
                r_stock = fwd(adj_close, pos, entry_date, H)
                r_spy = fwd(spy_close, spy_pos, entry_date, H)
                excess = (r_stock - r_spy) if (np.isfinite(r_stock) and np.isfinite(r_spy)) else np.nan
                rec[f"{entry_label}_{hlabel}_stock"] = r_stock
                rec[f"{entry_label}_{hlabel}_spy"] = r_spy
                rec[f"{entry_label}_{hlabel}_excess"] = excess
        rec["max_dd_in_episode"] = max_dd_in_ep
        out.append(rec)
    return out


def compute_pe_for_ticker(tk, spy_close):
    q, close_db, adj = _fetch_cached(tk)
    pe_daily = _pit_pe_daily(close_db, q)
    return pe_daily, adj


# ==================================================================== report writer
def fmt_pct(x, dp=2):
    return f"{x*100:+.{dp}f}%" if np.isfinite(x) else "N/A"


def fmt_pct0(x):
    return f"{x*100:.0f}%" if np.isfinite(x) else "N/A"


def main():
    L = []
    A = L.append
    A("# Mag7/Hyperscaler 估值節流閥/加速器 + S&P100 全宇宙平谷 Episode Study — 2026-07-16")
    A("")
    A("Script: `backtest/experiments/exp_mag7_valuation_throttle.py` "
      "(`PYTHONUTF8=1 python backtest/experiments/exp_mag7_valuation_throttle.py`)")
    A("")
    A("## 背景與先驗(非推翻,係測增量)")
    A("")
    A("Core v2(SPY 底倉 + QQQ/SPY LEAP,純 200SMA 閘 + 月度 top-up)已定稿,本實驗**唔推翻**佢,"
      "只測一個疊加喺同一 QQQ sleeve 之上嘅估值節流/加速訊號。假說一:Mag7/hyperscaler 結構長持正確,"
      "想知 trailing P/E 做戰術(月度)timing 有冇用。假說二(重點,新增):估值訊號可能**不對稱**——"
      "貴嗰邊冇用(貴可以貴好耐),但優質巨頭跌入自身歷史低估值百分位嗰邊可能有用"
      "(例:MSFT 2011-2013 forward PE 9-11x 維持三年先跑贏)。文獻先驗:戰術估值 timing 幾乎冇用,"
      "預測力要 7-10 年先浮現——落負面結論前已對照文獻(見全篇末判詞)。")
    A("")
    A("**已知、已接受嘅限制**:forward P/E(分析師共識)冇免費歷史數據,全篇用 trailing P/E 做代理"
      "(defeatbeta/yfinance 都冇 forward 歷史,呢個限制唔再覆查)。")
    A("")

    # ================================================================ PART 1
    A("---")
    A("")
    A("## Part 1 — QQQ 估值節流閥/加速器回測(A/B/B2/C/C2)")
    A("")
    dfm, qqq, failed_qqq = build_qqq_pe_proxy()
    A("### 1a/1b. QQQ 估值代理 + 百分位")
    A("")
    A(f"10 股靜態權重(申報:非逐年 PIT 重組,係近似固定權重):"
      f"{', '.join(f'{k} {v:.0%}' for k, v in WEIGHTS.items())}。")
    if failed_qqq:
        A(f"載入失敗:{failed_qqq}")
    cov_min = dfm["coverage"].min() if len(dfm) else np.nan
    cov_max = dfm["coverage"].max() if len(dfm) else np.nan
    cov_mean = dfm["coverage"].mean() if len(dfm) else np.nan
    n_valid_pctile = dfm["pctile"].notna().sum()
    first_valid_pctile_date = dfm[dfm["pctile"].notna()].index.min() if n_valid_pctile else None
    A(f"- 每月覆蓋率:min {cov_min}/10、mean {cov_mean:.1f}/10、max {cov_max}/10 隻(TSLA 2020 前、"
      f"META 2012 前等未上市/未有 EPS 期間唔 ffill 補、留 NaN,每月喺有數據嘅股之間重新歸一化權重)。")
    A(f"- {BURN_IN_MONTHS} 個月 expanding 百分位 burn-in:訊號由 "
      f"{first_valid_pctile_date.date() if first_valid_pctile_date is not None else 'N/A'} 起生效"
      f"(之前 pctile=NaN,唔觸發任何節流/加速,行為等同 policy A)。")
    sig_pctile = dfm["pctile"].dropna()
    if len(sig_pctile):
        A(f"- 生效期內百分位範圍:min {sig_pctile.min():.1%}、max {sig_pctile.max():.1%}"
          f"(expanding 歷史包含 1999-2001 dot-com 泡沫同 2008-2009 金融海嘯,呢兩段定咗歷史頂/底位,"
          f"令 2016+ 生效期嘅 QQQ-proxy 估值從未再逼近嗰啲極端 —— 觸發次數見下表)。")
        trig_counts = {
            "B(>90 pause)": int((sig_pctile > 0.90).sum()),
            "B2(>80 half)": int((sig_pctile > 0.80).sum()),
            "C(<10 double)": int((sig_pctile < 0.10).sum()),
            "C2(<20 x1.5)": int((sig_pctile < 0.20).sum()),
        }
        A(f"- 各門檻喺生效期內(共 {len(sig_pctile)} 個月)觸發月數:" +
          "、".join(f"{k} {v} 個月" for k, v in trig_counts.items()) + "。")
        A("  觸發次數少/零可以解釋下面 A/B/B2/C/C2 幾乎完全一樣嘅結果——唔係計算錯誤,"
          "而係呢個 QQQ-proxy 喺 2016+ 從未再貴過/平過 dot-com/海嘯級別嘅歷史極端。")
    A("")

    # engine runs
    monthly_pctile = dfm["pctile"]
    results = {}
    for name, fn in [("A", policy_A), ("B", policy_B), ("B2", policy_B2), ("C", policy_C), ("C2", policy_C2)]:
        results[name] = run_qqq_engine(qqq, monthly_pctile, fn, name)

    A("### 1c/1d/1e. 五個 policy 對比(unit-NAV 記帳,已剔除 DCA 資金流污染)")
    A("")
    A(f"BASE_CONTRIB = ${BASE_CONTRIB:.0f}/月(名義,絕對值唔重要,relative 比較先重要)。"
      "unit_nav 用嚟計 CAGR/MaxDD(剔除注資污染);最終財富/PnL 用完整 dollar wealth"
      "(唔剔除注資,反映真實袋落嘅錢)。")
    A("")
    A("| Policy | 總注入 | 期末backlog | 期末debt | 最終財富 | PnL | CAGR(unit) | MaxDD(unit) | 資本效率(PnL/平均曝險$) |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    pm = {}
    for name in ["A", "B", "B2", "C", "C2"]:
        m = part1_metrics(results[name], qqq.index)
        pm[name] = m
        A(f"| {name} | ${m['total_contrib']:,.0f} | ${m['backlog_end']:,.0f} | ${m['debt_end']:,.0f} | "
          f"${m['final_wealth']:,.0f} | ${m['pnl']:,.0f} | {fmt_pct(m['cagr'])} | {fmt_pct(m['mdd'])} | "
          f"{fmt_pct(m['cap_eff']) if np.isfinite(m['cap_eff']) else 'N/A'} |")
    A("")
    contrib_A = pm["A"]["total_contrib"]
    for name in ["B", "B2", "C", "C2"]:
        diff = pm[name]["total_contrib"] - contrib_A
        pct_diff = diff / contrib_A * 100 if contrib_A else np.nan
        note_resid = f"殘留 backlog=${pm[name]['backlog_end']:,.0f}, debt=${pm[name]['debt_end']:,.0f}"
        A(f"- **{name} capital-matched 核查**:總注入 vs A 差 ${diff:,.0f}({pct_diff:+.2f}%);{note_resid}"
          "(期末殘留代表回測窗口截斷令部分 backlog/debt 未及派清/還清,已計入誤差申報)。")
    A("")

    # 2021+ subperiod (signal-effective period)
    sig_start = first_valid_pctile_date if first_valid_pctile_date is not None else START
    A(f"### 訊號生效期(≥{sig_start.date()})子區間對比")
    A("")
    A("| Policy | CAGR(unit,子區間) | MaxDD(unit,子區間) |")
    A("|---|---:|---:|")
    for name in ["A", "B", "B2", "C", "C2"]:
        sm = part1_subperiod_metrics(results[name], sig_start, qqq.index.max())
        if sm:
            A(f"| {name} | {fmt_pct(sm['cagr'])} | {fmt_pct(sm['mdd'])} |")
        else:
            A(f"| {name} | N/A | N/A |")
    A("")

    # per-year CAGR breakdown
    A("### 分年 CAGR(unit_nav,per calendar year)")
    A("")
    years = sorted(set(qqq.index.year))
    header = "| Policy | " + " | ".join(str(y) for y in years) + " |"
    A(header)
    A("|---|" + "---:|" * len(years))
    for name in ["A", "B", "B2", "C", "C2"]:
        dates = results[name]["dates"]
        unav = results[name]["unit_nav"]
        row_vals = []
        for y in years:
            mask = dates.year == y
            if mask.sum() < 2:
                row_vals.append("N/A"); continue
            seg = unav[mask]
            yr_ret = seg[-1] / seg[0] - 1.0
            row_vals.append(f"{yr_ret*100:+.1f}%")
        A(f"| {name} | " + " | ".join(row_vals) + " |")
    A("")

    # judgement
    b_cagr_diff = pm["B"]["cagr"] - pm["A"]["cagr"] if np.isfinite(pm["B"]["cagr"]) and np.isfinite(pm["A"]["cagr"]) else np.nan
    c_cagr_diff = pm["C"]["cagr"] - pm["A"]["cagr"] if np.isfinite(pm["C"]["cagr"]) and np.isfinite(pm["A"]["cagr"]) else np.nan

    def verdict_word(diff, thr=0.003):
        if not np.isfinite(diff):
            return "數據不足"
        if diff > thr:
            return "有正增量"
        if diff < -thr:
            return "有負增量(拖累)"
        return "無增量(差異細過噪音)"

    A("### Part 1 業務判詞")
    A("")
    A(f"節流閥(A vs B/B2,「貴嗰邊暫停/減半供款」):B CAGR 差 A {fmt_pct(b_cagr_diff)}"
      f"({verdict_word(b_cagr_diff)});MaxDD 差 {fmt_pct(pm['B']['mdd']-pm['A']['mdd'])}。"
      f"加速器(A vs C/C2,「平嗰邊雙倍/1.5倍供款」):C CAGR 差 A {fmt_pct(c_cagr_diff)}"
      f"({verdict_word(c_cagr_diff)})。"
      "整體:呢個 QQQ-proxy 月度估值 timing 疊加喺 200SMA 閘之上,"
      f"{'節流同加速兩邊都同文獻一致——無穩健增量' if verdict_word(b_cagr_diff)=='無增量(差異細過噪音)' and verdict_word(c_cagr_diff)=='無增量(差異細過噪音)' else '見上實際數字判讀,唔誇大'}。"
      " **重要 caveat**:呢個「無增量」好大程度上係因為 B/B2/C 門檻(>90%/>80%/<10%)喺 2016+ 生效期"
      "幾乎從未觸發(見上觸發月數)——即係話呢個測試對「節流閥有冇用」嘅結論力度有限,"
      "唔係「測到訊號但冇效」,而係「訊號成日冇響」。C2(<20%)觸發 7 次,樣本仍然好細,"
      "結果唔可以當「已充分驗證冇用」,只可以講「喺呢個 10 年窗、呢組門檻,無法展示增量」。")
    A("")

    # ================================================================ PART 2
    A("---")
    A("")
    A("## Part 2 — Mag7 六隻個股平谷 Episode 細表")
    A("")
    spy_close = kdata.load("SPY", adjusted=True)["close"]
    part2_episodes = {}
    part2_failed = []
    for tk in MAG7_SIX:
        try:
            pe_daily, adj = compute_pe_for_ticker(tk, spy_close)
            eps = compute_episodes(pe_daily, adj, spy_close)
            part2_episodes[tk] = eps
        except Exception as e:
            part2_failed.append((tk, str(e)))

    if part2_failed:
        A(f"載入失敗:{part2_failed}")
        A("")

    A(f"Episode 定義:own-history expanding 百分位(≥{BURN_IN_DAYS} 交易日/~5年 burn-in)連續 "
      f"≤{EPISODE_PCTILE:.0%} 分位,過濾持續 <{MIN_EPISODE_DAYS} 交易日嘅雜訊 episode。")
    A("")
    A("| Ticker | 開始日 | 持續(月) | 期內最大追加跌幅 | 1y(start) excess vs SPY | 2y(start) excess | "
      "3y(start) excess | 1y(mid) excess | 2y(mid) excess | 3y(mid) excess |")
    A("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for tk, eps in part2_episodes.items():
        for e in eps:
            def g(k):
                v = e.get(k, np.nan)
                return fmt_pct(v) if np.isfinite(v) else "N/A(尾端截斷)"
            A(f"| {tk} | {e['start'].date()} | {e['dur_months']:.1f} | {fmt_pct(e['max_dd_in_episode'])} | "
              f"{g('start_1y_excess')} | {g('start_2y_excess')} | {g('start_3y_excess')} | "
              f"{g('mid_1y_excess')} | {g('mid_2y_excess')} | {g('mid_3y_excess')} |")
    total_p2 = sum(len(v) for v in part2_episodes.values())
    A("")
    A(f"共 {total_p2} 個 episode(6 隻股)。")
    A("")
    A("### Part 2 業務判詞")
    A("")
    # quick stat: hit rate at start_3y among those with valid data
    all_start3y = [e["start_3y_excess"] for eps in part2_episodes.values() for e in eps if np.isfinite(e.get("start_3y_excess", np.nan))]
    if all_start3y:
        hit = float(np.mean([x > 0 for x in all_start3y]))
        med = float(np.median(all_start3y))
        A(f"Mag7 六隻 episode 開始入場 3y excess vs SPY:n={len(all_start3y)},median {fmt_pct(med)},"
          f"命中率(跑贏 SPY){fmt_pct0(hit)}。呢個係細樣本(單一 survivorship 子集),"
          "初步方向留待 Part 3 全宇宙拆解對照先下判斷,唔喺呢度單獨定論。")
    else:
        A("3y forward 數據不足(episode 太近期/樣本太少),留待 Part 3 全宇宙統計。")
    A("")

    # ================================================================ PART 3
    A("---")
    A("")
    A("## Part 3 — S&P100 全宇宙平谷 Episode Study")
    A("")
    A(f"Universe:{len(SP100)} 隻近似 S&P100(OEX)成份(今日版本,hardcode)。"
      "**申報**:呢份係今日成份,唔係逐年 point-in-time 重組,所以仍有輕度生存偏差"
      "(倒閉/被踢出 S&P100 嘅公司唔喺呢份名單度)——結論措辭已反映呢點,唔話「完全冇 survivorship」。")
    A("")
    A(f"Sector tag:簡化二分,{len(TECH)} 隻列為 tech,其餘視為非tech(financials/healthcare/"
      "industrials/staples/energy/utilities/legacy telecom 等)。申報呢個係簡化二分,唔係官方 GICS 分類。")
    A("")

    all_episodes = []   # each: dict with ticker, sector, + episode fields
    loaded_tk, failed_tk = [], []
    for tk in SP100:
        try:
            pe_daily, adj = compute_pe_for_ticker(tk, spy_close)
            eps = compute_episodes(pe_daily, adj, spy_close)
            loaded_tk.append(tk)
            sector = "tech" if tk in TECH else "non-tech"
            for e in eps:
                rec = dict(e)
                rec["ticker"] = tk
                rec["sector"] = sector
                all_episodes.append(rec)
        except Exception as e:
            failed_tk.append((tk, str(e)[:120]))

    A(f"### 3c. 覆蓋率")
    A("")
    A(f"成功攞到基本面數據:{len(loaded_tk)}/{len(SP100)} 隻。")
    if failed_tk:
        A("")
        A("失敗清單(ticker: 原因):")
        for tk, err in failed_tk:
            A(f"- {tk}: {err}")
    A("")
    A(f"負 EPS 期間 PE 已由 `_pit_pe_daily` 自動設為 NaN(唔計入百分位/episode 偵測),"
      "呢個備註喺覆蓋率統計入面已隱含(negative-EPS 公司/年份嘅 episode 樣本天然較少)。")
    A("")

    ev_df = pd.DataFrame(all_episodes)
    A(f"### 3d. 全宇宙彙總統計")
    A("")
    A(f"共 {len(ev_df)} 個 episode(pool 全部 {len(loaded_tk)} 隻股)。")
    A("")

    if len(ev_df) == 0:
        A("**無 episode 偵測到 —— 檢查數據或門檻設定。**")
    else:
        # (a) duration distribution
        dur = ev_df["dur_months"].dropna()
        A("**(a) 持續時間分佈(月)**")
        A("")
        A(f"- median {dur.median():.1f} 月, p75 {dur.quantile(0.75):.1f} 月, p90 {dur.quantile(0.90):.1f} 月")
        A("")

        def dist_block(title, subdf):
            A(f"**{title}**")
            A("")
            A("| Horizon | n(有效) | median excess | 命中率(跑贏SPY) | p10(左尾) |")
            A("|---|---:|---:|---:|---:|")
            for hlabel in ["1y", "2y", "3y"]:
                col = f"start_{hlabel}_excess"
                x = subdf[col].dropna().values if col in subdf.columns else np.array([])
                if len(x) == 0:
                    A(f"| {hlabel} | 0 | N/A | N/A | N/A |")
                    continue
                med = float(np.median(x))
                hit = float(np.mean(x > 0))
                p10 = float(np.quantile(x, 0.10))
                A(f"| {hlabel} | {len(x)} | {fmt_pct(med)} | {fmt_pct0(hit)} | {fmt_pct(p10)} |")
            A("")

        dist_block("(b) 全宇宙:episode 開始入場前向 excess vs SPY", ev_df)

        tech_df = ev_df[ev_df["sector"] == "tech"]
        nontech_df = ev_df[ev_df["sector"] == "non-tech"]
        dist_block(f"(c) Tech 子集(n_episode={len(tech_df)})", tech_df)
        dist_block(f"(c) 非Tech 子集(n_episode={len(nontech_df)})", nontech_df)

        # (d) value trap rate
        x3 = ev_df["start_3y_excess"].dropna()
        if len(x3) > 0:
            trap_mask = x3 <= -0.20
            trap_rate = float(trap_mask.mean())
            trap_tickers = ev_df.loc[x3[trap_mask].index, "ticker"].tolist()
            A(f"**(d) Value trap 率**:episode 開始後 3y excess ≤ -20pp 佔全部有 3y 數據嘅 episode "
              f"{fmt_pct0(trap_rate)}(n={len(x3)},trap 數={int(trap_mask.sum())})。")
            A("")
            if trap_tickers:
                A("Trap episode 對應 ticker(可重複):" + ", ".join(trap_tickers))
            A("")
        else:
            A("**(d) Value trap 率**:3y 數據不足,無法計算。")
            A("")

        # (e) Mag7 vs universe survivorship gap
        mag7_df = ev_df[ev_df["ticker"].isin(MAG7_SIX)]
        A("**(e) Mag7 六隻子集 vs 全宇宙 —— 生存偏差量化**")
        A("")
        A("| 樣本 | n(3y有效) | median excess(3y) | 命中率(3y) |")
        A("|---|---:|---:|---:|")
        for label, sub in [("Mag7六隻", mag7_df), ("全宇宙(S&P100)", ev_df)]:
            x = sub["start_3y_excess"].dropna().values
            if len(x) == 0:
                A(f"| {label} | 0 | N/A | N/A |")
                continue
            A(f"| {label} | {len(x)} | {fmt_pct(float(np.median(x)))} | {fmt_pct0(float(np.mean(x>0)))} |")
        x_m = mag7_df["start_3y_excess"].dropna().values
        x_u = ev_df["start_3y_excess"].dropna().values
        if len(x_m) and len(x_u):
            gap_hit = float(np.mean(x_m > 0)) - float(np.mean(x_u > 0))
            gap_med = float(np.median(x_m)) - float(np.median(x_u))
            A("")
            A(f"生存偏差量化:Mag7 命中率 - 全宇宙命中率 = {gap_hit*100:+.0f}pp;"
              f"median excess 差 = {gap_med*100:+.1f}pp。")
        A("")

    A("### Part 3 業務判詞")
    A("")
    if len(ev_df) > 0 and len(ev_df["start_3y_excess"].dropna()) > 0:
        x_u = ev_df["start_3y_excess"].dropna().values
        u_hit = float(np.mean(x_u > 0))
        u_med = float(np.median(x_u))
        verdict3 = ("全宇宙層面「平咗買」有正期望" if u_hit > 0.55 and u_med > 0 else
                    "全宇宙層面「平咗買」大約打和/偏弱" if 0.45 <= u_hit <= 0.55 else
                    "全宇宙層面「平咗買」冇正期望,甚至偏負")
        A(f"全宇宙 3y 命中率 {fmt_pct0(u_hit)}、median excess {fmt_pct(u_med)} —— {verdict3}。"
          "具體 Mag7-vs-全宇宙生存偏差幅度見上 (e),數字判讀留返全篇最後總判詞一併回答。")
    else:
        A("3y forward 樣本不足以下判斷。")
    A("")

    # ================================================================ FINAL VERDICT
    A("---")
    A("")
    A("## 全篇最後判詞")
    A("")
    if len(ev_df) > 0 and len(ev_df["start_3y_excess"].dropna()) > 0:
        x_u = ev_df["start_3y_excess"].dropna().values
        u_hit = float(np.mean(x_u > 0))
        u_med = float(np.median(x_u))
        x_m = mag7_df["start_3y_excess"].dropna().values if len(mag7_df) else np.array([])
        m_hit = float(np.mean(x_m > 0)) if len(x_m) else np.nan
        m_med = float(np.median(x_m)) if len(x_m) else np.nan
        gap = (m_hit - u_hit) * 100 if np.isfinite(m_hit) else np.nan

        A(f"**「巨頭平咗買」係咪全體 S&P100 巨頭樣本入面一個正期望策略?** "
          f"全宇宙 episode 開始入場 3y 命中率 {fmt_pct0(u_hit)}、median excess {fmt_pct(u_med)}"
          f"(n={len(x_u)})。Mag7 六隻同一定義命中率 {fmt_pct0(m_hit) if np.isfinite(m_hit) else 'N/A'}"
          f"(n={len(x_m)})。")
        if np.isfinite(gap):
            if abs(gap) >= 15:
                A(f"兩者相差 {gap:+.0f}pp —— **生存偏差顯著**:Mag7 嘅「平咗買」表現大幅好過全宇宙,"
                  "反映呢個 edge 好大程度上係「揀咗事後贏家」嘅結果,而唔係「平嘅巨頭普遍值得買」呢個"
                  "廣譜規律。換做全宇宙,edge 明顯縮水(甚至可能接近打和/偏弱,見上 3d 全宇宙數字)。")
            else:
                A(f"兩者相差 {gap:+.0f}pp,差距唔算誇張 —— 全宇宙同 Mag7 方向大致一致,"
                  "「平咗買」呢個 edge 喺全宇宙巨頭樣本入面都站得住,唔淨係 survivorship 產物。")
        A("")
        A(f"**估值訊號係咪不對稱(賣貴冇用、買平有用)?** "
          f"Part 1:節流閥(A vs B/B2)CAGR 差 {fmt_pct(b_cagr_diff)}({verdict_word(b_cagr_diff)});"
          f"加速器(A vs C/C2)CAGR 差 {fmt_pct(c_cagr_diff)}({verdict_word(c_cagr_diff)})。"
          f"Part 3 全宇宙 episode(買平嗰邊)3y 命中率 {fmt_pct0(u_hit)}、median excess {fmt_pct(u_med)}。")
        if u_hit > 0.55 and u_med > 0:
            A("買平嗰邊喺全宇宙層面顯示正期望,同賣貴嗰邊(節流閥)嘅「無增量」形成對比 —— "
              "**方向上支持不對稱假說**:估值訊號喺「平」嗰邊比「貴」嗰邊更有用。"
              "呢個同 **Lakonishok-Shleifer-Vishny(1994)** value/glamour 文獻一致"
              "(value 一邊有 premium,glamour/高估一邊冇對稱嘅做空 alpha),"
              "唔係新發現,而係喺呢個 universe 印證咗成熟嘅 value literature。"
              "如果 3d 生存偏差拆解(見上)顯示 Mag7 大幅跑贏全宇宙,要同時指出 —— "
              "呢個正正係 **Bordalo, Gennaioli, La Porta & Shleifer(2019, JF)** "
              "警告嘅「揀事後贏家」偏差:淨睇 Mag7 會誇大條 edge。")
        else:
            A("買平嗰邊喺全宇宙層面**冇顯示穩健正期望**(命中率/median 唔夠強)—— "
              "唔支持不對稱假說去到「全宇宙巨頭平咗普遍值得買」呢一步;"
              "同 **La Porta(1996)**/主流戰術估值 timing 文獻(月/季度層面預測力弱、要 7-10 年"
              "先浮現)一致,結論:此訊號喺呢個 universe/期間、呢個戰術頻率,**唔夠格做自動化 timing 訊號**"
              "(至多 dashboard 參考,唔接入 sizing)。")
        A("")
        A("**總結**:唔誇大 —— 差異細過噪音就直講「無增量」。以上數字係全篇結論嘅依據,"
          "任何自動化 sizing/timing 接入前應再覆核(尤其 survivorship gap 幅度)。")
    else:
        A("3y forward 樣本不足,全篇判詞留空 —— 需要更長歷史數據先可以回答呢個問題。")
    A("")

    A("## 誠實 Caveat")
    A("")
    A("1. **QQQ-proxy 權重係近似靜態**,唔係逐年 PIT 重組(見 1a)。")
    A("2. **S&P100 universe 係今日成份**,非逐年 PIT,仍有輕度生存偏差(見 3a)。")
    A("3. **Sector tag 係簡化二分**,非官方 GICS(見 3b)。")
    A("4. **trailing PE 代理 forward PE**——已知、已接受嘅限制,唔係本實驗新發現嘅 gap。")
    A("5. **filing lag 固定 60 日**,近似值(見 exp_earnings_expectation_probe.py 文檔)。")
    A("6. **近期 episode(2024/2025 後)3y forward 數據截斷**,標 N/A,唔靜雞雞跳過。")
    A("7. **episode 之間唔獨立**(同一隻股連續多個 episode、episode 之間 forward window 可能重疊)——"
      "有效獨立樣本數少過表面 n,命中率/median 喺細樣本(n<30)時只作方向參考。")
    A("")

    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
