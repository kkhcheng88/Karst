"""Experiment: BTC/ETH vs SPY — is crypto a real decorrelation asset, or a
historical bull-run dressed up as one? User question, answered with real data.

Question
--------
The user holds SPY-centric core (v2). Would adding a small BTC/ETH sleeve
(5-10% of NAV) meaningfully help via LOW correlation to equities — the classic
"decorrelation asset" pitch — or does any historical Sharpe/MaxDD improvement
come mostly from BTC/ETH's 2017-2021 bull run, with 2022+ pulling the other way
(a return-chasing bet on a young, historically volatile asset, not a
diversification finding)?

Method (mirror / increment / horizon)
--------
Mirror     : the actual decision the user faces — "carve X% of the SPY-centric
             core into BTC or ETH, monthly-rebalanced" — vs the SAME decision
             carved into IEF (bonds) or cash (^IRX), a genuinely low-beta
             control group, so the user can see what a REAL low-correlation
             asset's contribution looks like next to crypto's.
Increment  : crypto's OWN return series (`data.load` yfinance BTC-USD/ETH-USD,
             no dividends -> raw close == adjusted close) is the only new input;
             SPY/QQQ r_net (HK 30% dividend withholding netted) and the
             month-start-rebalance mechanics are reused from repo convention
             (`exp_core_topup.month_start_mask`).
Horizon    : BTC since 2014-09-17 inception in this data source; ETH since
             2017-11-09; combo A/B tested over the ETH-available window
             (2017-11+) and a 2022+ sub-window (post-2021-bull, the harder
             test), monthly rebalance cadence (matches the repo's core-v2
             top-up cadence, not a high-frequency crypto-specific policy).

Calendar alignment (pre-registered)
--------
Crypto trades 7 days/week; equities do not. Convention: reindex each crypto
close series onto the SPY trading-day calendar (exact-date match; ffill only
for the rare missing print) and take pct_change of THAT aligned series. This
means a Friday-close -> Monday-close (or holiday-spanning) return is entirely
attributed to the next SPY trading day — "假期跨日報酬照連" per the brief. This
slightly smooths day-to-day crypto vol (weekend moves land in Monday) but does
NOT change weekly/monthly cumulative returns, which is what the correlation
and combo tests below actually depend on.

Pre-registered analyses (all reported, negative or positive)
--------
1. Full-period + sub-period Pearson correlation (daily AND monthly returns),
   BTC/ETH vs SPY/QQQ. Sub-periods: {2014-2017, 2018-2021, 2022-2026, 2024-2026}
   (ETH only has data from 2017-11, so its 2014-2017 cell is n/a).
2. Tail correlation: SPY's worst 5% days (within each pair's OWN common
   window) -> mean BTC/ETH return + conditional correlation on that subset.
   Crisis-window table (SAME calendar window for all three assets, cumulative
   return, not each asset's own peak/trough): 2018Q4, 2020-03 COVID,
   2022 full year, 2025-04 tariff shock, 2026-07 (trailing week of data).
3. Independent-asset stats: BTC/ETH CAGR / annualized vol / MaxDD per
   sub-period (BTC's well-known -83% 2018 and -77% 2022 drawdowns should
   reproduce here from real data).
4. Combo A/B: benchmark = 100% SPY B&H (monthly-rebalance no-op); variants =
   {95/5, 90/10, 80/20} SPY/BTC and SPY/ETH, monthly-rebalanced. Windows =
   ETH-available (2017-11+) and 2022+ (harder, post-bull test). Reading
   discipline (pre-registered, mechanical): for every blend, ALSO report the
   blend's own CAGR split pre-2022 vs 2022+ — if the full-window Sharpe gain is
   driven almost entirely by the pre-2022 leg while the 2022+ leg alone shows
   a Sharpe/MaxDD WORSE than 100% SPY, the headline is flagged "BULL-RUN
   ARTIFACT, NOT DIVERSIFICATION" rather than reported as a clean alpha/
   diversification finding.
5. Rebalance-buys-the-dip behavior (5% BTC blend only): report the BTC weight
   immediately BEFORE each 2022 monthly rebalance (should dip well under the 5%
   target during BTC's crash, i.e. rebalancing forces buying more BTC while it
   is falling) and count how many of the 12 monthly rebalances in 2022 bought
   (pre-rebalance weight < target) vs sold.
6. Control group: same 5%/10% carve-outs into IEF (bonds) and cash (^IRX),
   same windows, so the user can see what a genuine low-correlation asset's
   combo contribution looks like next to crypto's.

Caveats (pre-registered, must be stated regardless of result)
--------
- Crypto has no cash flows / no valuation anchor (no earnings, no coupon) —
  this script answers "historical correlation / combination math," NOT "what
  should BTC/ETH's future expected return be." A low historical correlation
  with a fat pre-2022 return tailwind is not evidence of a repeatable expected
  return.
- Survivorship: BTC and ETH are the two survivors of a much larger set of
  cryptoassets from the same eras; assets that went to zero (many 2018/2022
  alt-coins) are not in this sample. Any statement here about "crypto" only
  covers these two survivors, not the asset class's full historical
  distribution.
- Single historical path, no bootstrap; BTC/ETH have ~11/~9 years of history —
  short relative to SPY's ~33 years in this dataset, so tail-window and
  sub-period cells for crypto have materially fewer independent regimes than
  the equity side of every comparison.
- IEF/cash proxies use the same HK 30% dividend-withholding convention applied
  elsewhere in this repo to bond-ETF distributions; this is an approximation
  (bond distributions may be taxed differently in practice) noted for
  completeness, not re-derived here.

Run:  PYTHONUTF8=1 python backtest/experiments/exp_crypto_decorr.py
Writes: backtest/results/2026-07-08_crypto_decorr.md
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metrics                                      # noqa: E402
from data import load                               # noqa: E402
from exp_core_topup import month_start_mask         # noqa: E402

CAPITAL = 500_000.0
TD = 252

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-08_crypto_decorr.md")

SUBPERIODS = [
    ("2014-2017", "2014-01-01", "2017-12-31"),
    ("2018-2021", "2018-01-01", "2021-12-31"),
    ("2022-2026", "2022-01-01", "2026-12-31"),
    ("2024-2026", "2024-01-01", "2026-12-31"),
]

CRISIS_WINDOWS = [
    ("2018Q4", "2018-10-01", "2018-12-24"),
    ("2020-03 COVID", "2020-02-19", "2020-03-23"),
    ("2022 full year", "2022-01-03", "2022-12-30"),
    ("2025-04 tariff shock", "2025-04-02", "2025-04-08"),
]


# ---------------------------------------------------------------------------
# Data plumbing
# ---------------------------------------------------------------------------

def r_net_series(symbol: str, prov: list, apply_withholding: bool = True):
    """HK-net total-return daily series (adjusted close, 30% dividend
    withholding netted — repo convention). For crypto (no dividends) raw ==
    adjusted, so this collapses to a plain pct_change of close."""
    raw = load(symbol)
    adj = load(symbol, adjusted=True)
    prov.append((symbol, raw.attrs.get("source", "?"), len(raw),
                 str(raw.index.min().date()), str(raw.index.max().date())))
    prov.append((f"{symbol}(adj)", adj.attrs.get("source", "?"), len(adj),
                 str(adj.index.min().date()), str(adj.index.max().date())))
    r_adj = adj["close"].pct_change()
    if not apply_withholding:
        return r_adj.dropna()
    r_raw = raw["close"].pct_change()
    dy = (r_adj - r_raw).clip(lower=0.0)
    dy = dy.where(dy > 1e-4, 0.0)
    r_net = r_adj - 0.30 * dy
    return r_net.dropna()


def close_aligned(symbol: str, cal: pd.DatetimeIndex, prov: list):
    raw = load(symbol)
    prov.append((symbol, raw.attrs.get("source", "?"), len(raw),
                 str(raw.index.min().date()), str(raw.index.max().date())))
    close = raw["close"].reindex(cal, method="ffill")
    return close


# ---------------------------------------------------------------------------
# Analysis 1 — correlation (full + sub-period, daily + monthly)
# ---------------------------------------------------------------------------

def corr_table(r_crypto: pd.Series, r_bench: pd.Series, start: str, end: str):
    a = r_crypto.loc[start:end].dropna()
    b = r_bench.reindex(a.index).dropna()
    common = a.index.intersection(b.index)
    if len(common) < 20:
        return np.nan, np.nan, 0
    a, b = a.loc[common], b.loc[common]
    daily_corr = float(np.corrcoef(a.values, b.values)[0, 1])
    ma = (1 + a).resample("ME").prod() - 1
    mb = (1 + b).resample("ME").prod() - 1
    common_m = ma.index.intersection(mb.index)
    monthly_corr = (float(np.corrcoef(ma.loc[common_m].values, mb.loc[common_m].values)[0, 1])
                    if len(common_m) >= 6 else np.nan)
    return daily_corr, monthly_corr, len(common)


# ---------------------------------------------------------------------------
# Analysis 3 — independent asset stats per sub-period
# ---------------------------------------------------------------------------

def asset_stats(r: pd.Series, start: str, end: str):
    seg = r.loc[start:end].dropna()
    if len(seg) < 20:
        return {"CAGR": np.nan, "Vol": np.nan, "MaxDD": np.nan, "N": len(seg)}
    nav = np.concatenate([[1.0], np.cumprod(1.0 + seg.values)])
    cagr_v = metrics.cagr(nav) if len(seg) >= 90 else np.nan  # <90d: annualization noise
    return {
        "CAGR": cagr_v,
        "Vol": float(seg.std(ddof=1) * np.sqrt(TD)),
        "MaxDD": metrics.max_drawdown(nav),
        "N": len(seg),
    }


# ---------------------------------------------------------------------------
# Analysis 4/5 — monthly-rebalanced two-asset blend
# ---------------------------------------------------------------------------

def simulate_blend(r_a: np.ndarray, r_b: np.ndarray, w_b_target: float,
                    rebal_mask: np.ndarray):
    """Monthly-rebalanced blend of asset A (base) + asset B (carve-out).
    Returns (nav array, list of (t, pre-rebalance weight_b) at each rebalance).
    """
    n = len(r_a)
    val_a = 1.0 - w_b_target
    val_b = w_b_target
    nav = np.empty(n)
    nav[0] = 1.0
    pre_rebal_w = []
    for t in range(1, n):
        val_a *= (1.0 + r_a[t])
        val_b *= (1.0 + (r_b[t] if np.isfinite(r_b[t]) else 0.0))
        tot = val_a + val_b
        nav[t] = tot
        if rebal_mask[t]:
            pre_rebal_w.append((t, val_b / tot if tot > 0 else np.nan))
            val_a = tot * (1.0 - w_b_target)
            val_b = tot * w_b_target
    return nav, pre_rebal_w


def blend_metrics(nav: np.ndarray, r_bench: np.ndarray, lo: int, hi: int):
    navw = nav[lo:hi]
    ret = navw[1:] / navw[:-1] - 1.0
    out = {"CAGR": metrics.cagr(navw), "Sharpe": metrics.ann_sharpe(ret),
           "MaxDD": metrics.max_drawdown(navw)}
    worst = 1e9
    for i in range(len(navw) - 21):
        w = navw[i + 21] / navw[i] - 1.0
        worst = min(worst, w)
    out["WorstMonth"] = worst if worst < 1e9 else np.nan
    return out


def _p(x, dec=1):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:+.{dec}f}%"


def _pv(x, dec=1):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:.{dec}f}%"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    prov = []

    r_spy = r_net_series("SPY", prov)
    r_qqq = r_net_series("QQQ", prov)
    r_ief = r_net_series("IEF", prov)
    irx_df = load("^IRX")
    prov.append(("^IRX", irx_df.attrs.get("source", "?"), len(irx_df),
                 str(irx_df.index.min().date()), str(irx_df.index.max().date())))
    r_cash_annual = irx_df["close"] / 100.0
    r_cash = (r_cash_annual / TD).reindex(r_spy.index, method="ffill")

    cal = r_spy.index  # SPY trading-day calendar is the master alignment

    btc_close = close_aligned("BTC-USD", cal, prov)
    eth_close = close_aligned("ETH-USD", cal, prov)
    r_btc_cal = btc_close.pct_change()
    r_eth_cal = eth_close.pct_change()
    r_ief_cal = r_ief.reindex(cal)
    r_cash_cal = r_cash.reindex(cal)
    r_spy_cal = r_spy.reindex(cal)
    r_qqq_cal = r_qqq.reindex(cal)

    print(f"BTC aligned: {r_btc_cal.dropna().index[0].date()} -> "
          f"{r_btc_cal.dropna().index[-1].date()}, {r_btc_cal.dropna().shape[0]} days",
          flush=True)
    print(f"ETH aligned: {r_eth_cal.dropna().index[0].date()} -> "
          f"{r_eth_cal.dropna().index[-1].date()}, {r_eth_cal.dropna().shape[0]} days",
          flush=True)

    # ------------------------------------------------------------------
    # 1. Correlation table (full + sub-periods, daily + monthly)
    # ------------------------------------------------------------------
    corr_rows = []
    full_ranges = [
        ("BTC full (2014-09+)", r_btc_cal, "2014-09-17", "2026-12-31"),
        ("ETH full (2017-11+)", r_eth_cal, "2017-11-09", "2026-12-31"),
    ]
    for label, series, s0, e0 in full_ranges:
        for bench_label, bench in [("SPY", r_spy_cal), ("QQQ", r_qqq_cal)]:
            dc, mc, n = corr_table(series, bench, s0, e0)
            corr_rows.append((label, bench_label, dc, mc, n))
    for pname, s0, e0 in SUBPERIODS:
        for clabel, series in [("BTC", r_btc_cal), ("ETH", r_eth_cal)]:
            for bench_label, bench in [("SPY", r_spy_cal), ("QQQ", r_qqq_cal)]:
                dc, mc, n = corr_table(series, bench, s0, e0)
                corr_rows.append((f"{clabel} {pname}", bench_label, dc, mc, n))

    # ------------------------------------------------------------------
    # 2. Tail correlation + crisis windows
    # ------------------------------------------------------------------
    tail_rows = []
    for clabel, series, cstart in [("BTC", r_btc_cal, "2014-09-17"),
                                    ("ETH", r_eth_cal, "2017-11-09")]:
        seg_spy = r_spy_cal.loc[cstart:].dropna()
        seg_c = series.reindex(seg_spy.index).dropna()
        common = seg_spy.index.intersection(seg_c.index)
        seg_spy2, seg_c2 = seg_spy.loc[common], seg_c.loc[common]
        thresh = seg_spy2.quantile(0.05)
        worst_mask = seg_spy2 <= thresh
        mean_c_on_worst = float(seg_c2[worst_mask].mean())
        mean_spy_on_worst = float(seg_spy2[worst_mask].mean())
        cond_corr = float(np.corrcoef(seg_spy2[worst_mask].values,
                                       seg_c2[worst_mask].values)[0, 1])
        tail_rows.append((clabel, len(common), int(worst_mask.sum()),
                          mean_spy_on_worst, mean_c_on_worst, cond_corr))

    crisis_rows = []
    for label, s0, e0 in CRISIS_WINDOWS:
        row = [label, s0, e0]
        for series in [r_spy_cal, r_btc_cal, r_eth_cal]:
            seg = series.loc[s0:e0].dropna()
            if len(seg) < 2:
                row.append(np.nan)
            else:
                cum = float(np.prod(1.0 + seg.values) - 1.0)
                row.append(cum)
        crisis_rows.append(row)
    # trailing-week window (2026-07, "this week")
    last_n = 5
    tail_idx = cal[-last_n:]
    row = [f"2026-07 (trailing {last_n}d, {tail_idx[0].date()}->{tail_idx[-1].date()})",
           str(tail_idx[0].date()), str(tail_idx[-1].date())]
    for series in [r_spy_cal, r_btc_cal, r_eth_cal]:
        seg = series.loc[tail_idx[0]:tail_idx[-1]].dropna()
        cum = float(np.prod(1.0 + seg.values) - 1.0) if len(seg) >= 1 else np.nan
        row.append(cum)
    crisis_rows.append(row)

    # ------------------------------------------------------------------
    # 3. Independent asset stats
    # ------------------------------------------------------------------
    stat_rows = []
    for clabel, series in [("BTC", r_btc_cal), ("ETH", r_eth_cal)]:
        for pname, s0, e0 in SUBPERIODS:
            st = asset_stats(series, s0, e0)
            stat_rows.append((clabel, pname, st))

    # ------------------------------------------------------------------
    # 4/5/6. Combo A/B blends: SPY base + {BTC, ETH, IEF, cash} carve-outs
    # ------------------------------------------------------------------
    WEIGHTS = [0.05, 0.10, 0.20]
    CARVES = [("BTC", r_btc_cal), ("ETH", r_eth_cal), ("IEF", r_ief_cal), ("cash", r_cash_cal)]

    combo_windows = [
        ("ETH-available (2017-11-09+)", "2017-11-09"),
        ("2022+ (post-bull, harder test)", "2022-01-01"),
    ]

    combo_results = {}   # (wname, carve, w) -> {'full':m, 'pre2022':m or None, 'post2022':m or None, 'rebal': ...}
    for wname, wstart in combo_windows:
        widx = cal[cal >= wstart]
        r_spy_w = r_spy_cal.reindex(widx).fillna(0.0).values
        rmask = month_start_mask(widx)
        bench_nav = np.concatenate([[1.0], np.cumprod(1.0 + r_spy_w[1:])])
        bench_m = {"CAGR": metrics.cagr(bench_nav), "Sharpe": metrics.ann_sharpe(r_spy_w[1:]),
                   "MaxDD": metrics.max_drawdown(bench_nav)}
        combo_results[(wname, "SPY 100% (base)", 0.0)] = {"full": bench_m}

        for cname, cseries in CARVES:
            r_c_w = cseries.reindex(widx).fillna(0.0).values
            for w in WEIGHTS:
                nav, pre_rebal = simulate_blend(r_spy_w, r_c_w, w, rmask)
                m_full = blend_metrics(nav, r_spy_w, 0, len(nav))
                entry = {"full": m_full}
                # pre/post-2022 split (only meaningful for the ETH-available window)
                if wname.startswith("ETH-available"):
                    split_date = pd.Timestamp("2022-01-01")
                    if widx[0] < split_date and widx[-1] >= split_date:
                        cut = int(np.searchsorted(widx.values, split_date.to_datetime64()))
                        m_pre = blend_metrics(nav, r_spy_w, 0, cut)
                        m_post = blend_metrics(nav, r_spy_w, cut, len(nav))
                        entry["pre2022"] = m_pre
                        entry["post2022"] = m_post
                if cname == "BTC" and w == 0.05 and wname.startswith("ETH-available"):
                    # rebalance-buys-the-dip diagnostic for 2022
                    n2022 = [(t, wt) for t, wt in pre_rebal
                             if pd.Timestamp("2022-01-01") <= widx[t] < pd.Timestamp("2023-01-01")]
                    bought = sum(1 for _, wt in n2022 if wt < w)
                    entry["rebal_2022"] = (n2022, bought)
                combo_results[(wname, cname, w)] = entry
        print(f"{wname} combos done ({time.time()-t0:.0f}s)", flush=True)

    # ------------------------------------------------------------------
    # Judge: bull-run-artifact flag for ETH-available window
    # ------------------------------------------------------------------
    bench_post2022 = combo_results[("2022+ (post-bull, harder test)",
                                     "SPY 100% (base)", 0.0)]["full"]

    def judge_bullrun(entry, bench_m):
        """bench_m = the ETH-available window's 100% SPY Sharpe (for the FULL-window
        comparison); bench_post2022 = the 2022+-only window's OWN 100% SPY Sharpe (for
        the post-2022-leg comparison) — comparing a partial-period leg against a
        FULL-period benchmark would be an apples/oranges mismatch."""
        if "pre2022" not in entry or "post2022" not in entry:
            return "n/a"
        post = entry["post2022"]
        full = entry["full"]
        if not (np.isfinite(post.get("Sharpe", np.nan)) and np.isfinite(full.get("Sharpe", np.nan))):
            return "n/a"
        full_better = full["Sharpe"] > bench_m["Sharpe"] + 0.01
        post_worse = post["Sharpe"] < bench_post2022.get("Sharpe", np.nan) - 0.01
        if full_better and post_worse:
            return "BULL-RUN ARTIFACT, NOT DIVERSIFICATION"
        if full_better:
            return "improvement holds post-2022 too"
        return "no full-window improvement"

    # ------------------------------------------------------------------
    # Write results markdown
    # ------------------------------------------------------------------
    L = []
    add = L.append
    add("# Result — BTC/ETH vs SPY: is crypto a real decorrelation asset?")
    add("")
    add("**Date:** 2026-07-08  **Script:** `backtest/experiments/exp_crypto_decorr.py`  "
        "**Status:** active")
    add("")
    add("## Question")
    add("")
    add("Would carving 5-10% of a SPY-centric core into BTC or ETH meaningfully help via "
        "low correlation to equities, or does any historical improvement come mostly from "
        "BTC/ETH's 2017-2021 bull run, with 2022+ pulling the other way?")
    add("")
    add("## Method")
    add("")
    add("- Crypto trades 7 days/week; equities do not. Convention: crypto CLOSE reindexed "
        "onto the SPY trading-day calendar (exact-date match, ffill for rare gaps), THEN "
        "pct_change taken of that aligned series — a weekend/holiday move is entirely "
        "attributed to the next SPY trading day's return (\"假期跨日報酬照連\"). This "
        "changes day-to-day attribution only, not weekly/monthly cumulative returns.")
    add("- SPY/QQQ/IEF use the repo's standard `r_net` convention (adjusted-close total "
        "return, HK 30% dividend withholding netted). BTC/ETH have no dividends so raw == "
        "adjusted close; no withholding applied. Cash = ^IRX / 252 (annualized T-bill "
        "yield, daily-compounded approximation), reindexed onto the SPY calendar.")
    add("- Combo blends: monthly-rebalanced (`exp_core_topup.month_start_mask` — same "
        "cadence convention as core v2's LEAP sleeve top-up), 2-asset (SPY base + ONE "
        "carve-out), weights {5%, 10%, 20%} carve-out. Windows: ETH-available "
        "(2017-11-09+) and 2022+ (harder, post-bull test).")
    add("- **Reading discipline (pre-registered, mechanical)**: for every blend in the "
        "ETH-available window, split the SAME nav path into pre-2022 and 2022+ legs. If "
        "the full-window Sharpe beats 100% SPY AND the 2022+-only leg's Sharpe is WORSE "
        "than 100% SPY, flag **BULL-RUN ARTIFACT, NOT DIVERSIFICATION** — the headline "
        "gain is a historical-bull-market artifact, not a repeatable diversification "
        "effect.")
    add("- CAPITAL = $500,000 notionally; all figures reported as returns (capital cancels "
        "out). Sharpe = raw daily returns, annualized (repo convention, no rf subtraction).")
    add("")
    add("## Data provenance (`backtest/data.py` `load()`)")
    add("")
    add("| Series | Source | Rows | From | To |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in prov:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")

    # -- Table 1: correlation --------------------------------------------
    add("## Table 1 — Correlation, full period + sub-periods (daily & monthly Pearson)")
    add("")
    add("| Asset / period | vs | Daily corr | Monthly corr | N (days) |")
    add("|---|---|---|---|---|")
    for label, bench_label, dc, mc, n in corr_rows:
        dcs = f"{dc:+.2f}" if np.isfinite(dc) else "n/a"
        mcs = f"{mc:+.2f}" if np.isfinite(mc) else "n/a"
        add(f"| {label} | {bench_label} | {dcs} | {mcs} | {n} |")
    add("")
    add("Note: BTC's 2014-2017 sub-period cell has NO ETH counterpart (ETH data starts "
        "2017-11-09, i.e. inside this bucket only for its last ~7 weeks — reported n/a "
        "where the overlap is too thin for a stable estimate).")
    add("")

    # -- Table 2: tail correlation ----------------------------------------
    add("## Table 2 — Tail correlation: SPY's worst 5% days")
    add("")
    add("| Asset | N (common days) | N (worst-5% days) | Mean SPY ret | Mean crypto ret | "
        "Conditional corr |")
    add("|---|---|---|---|---|---|")
    for clabel, n, nw, mspy, mc, cc in tail_rows:
        add(f"| {clabel} | {n} | {nw} | {_p(mspy)} | {_p(mc)} | {cc:+.2f} |")
    add("")

    # -- Table 3: crisis windows --------------------------------------------
    add("## Table 3 — Crisis windows, SAME calendar window, cumulative return")
    add("")
    add("| Window | Start | End | SPY | BTC | ETH |")
    add("|---|---|---|---|---|---|")
    for label, s0, e0, cspy, cbtc, ceth in crisis_rows:
        add(f"| {label} | {s0} | {e0} | {_p(cspy)} | {_p(cbtc)} | {_p(ceth)} |")
    add("")

    # -- Table 4: independent asset stats -----------------------------------
    add("## Table 4 — BTC/ETH standalone: CAGR / annualized vol / MaxDD per sub-period")
    add("")
    add("| Asset | Period | CAGR | Ann. vol | MaxDD | N (days) |")
    add("|---|---|---|---|---|---|")
    for clabel, pname, st in stat_rows:
        add(f"| {clabel} | {pname} | {_p(st['CAGR'], 2)} | {_pv(st['Vol'])} | "
            f"{_p(st['MaxDD'])} | {st['N']} |")
    add("")

    # -- Table 5/6: combo A/B ------------------------------------------------
    for wname, wstart in combo_windows:
        add(f"## Table — Combo A/B, window: {wname}")
        add("")
        bench_m = combo_results[(wname, "SPY 100% (base)", 0.0)]["full"]
        add(f"Benchmark 100% SPY B&H this window: CAGR {_p(bench_m['CAGR'], 2)}, "
            f"Sharpe {bench_m['Sharpe']:.2f}, MaxDD {_p(bench_m['MaxDD'])}.")
        add("")
        cols = ["Carve-out", "Weight", "CAGR", "Sharpe", "MaxDD", "Worst mo"]
        if wname.startswith("ETH-available"):
            cols += ["Pre-2022 Sharpe", "2022+ Sharpe", "Judge"]
        add("| " + " | ".join(cols) + " |")
        add("|" + "---|" * len(cols))
        for cname, _ in CARVES:
            for w in WEIGHTS:
                entry = combo_results[(wname, cname, w)]
                m = entry["full"]
                row = [cname, f"{int(w*100)}%", _p(m['CAGR'], 2), f"{m['Sharpe']:.2f}",
                       _p(m['MaxDD']), _p(m['WorstMonth'])]
                if wname.startswith("ETH-available"):
                    if "pre2022" in entry:
                        row.append(f"{entry['pre2022']['Sharpe']:.2f}")
                        row.append(f"{entry['post2022']['Sharpe']:.2f}")
                        row.append(judge_bullrun(entry, bench_m))
                    else:
                        row += ["n/a", "n/a", "n/a"]
                add("| " + " | ".join(row) + " |")
        add("")

    # -- Rebalance-buys-the-dip diagnostic ------------------------------------
    add("## Rebalance behavior — 5% BTC blend, 2022 monthly rebalances")
    add("")
    entry_5btc = combo_results[("ETH-available (2017-11-09+)", "BTC", 0.05)]
    if "rebal_2022" in entry_5btc:
        n2022, bought = entry_5btc["rebal_2022"]
        add(f"- {len(n2022)} monthly rebalances fell inside 2022; **{bought}** of them "
            "found the BTC weight BELOW the 5% target immediately before rebalancing "
            "(i.e. the rebalance bought MORE BTC while it was falling).")
        add("")
        add("| Rebalance date | Pre-rebalance BTC weight | Action |")
        add("|---|---|---|")
        widx_eth = cal[cal >= "2017-11-09"]
        for t, wt in n2022:
            action = "BUY (below target)" if wt < 0.05 else "SELL (above target)"
            add(f"| {widx_eth[t].date()} | {wt*100:.2f}% | {action} |")
        add("")

    add("## Conclusions")
    add("")
    add("(placeholder — filled by hand after reviewing Tables 1-6)")
    add("")
    add("## Caveats")
    add("")
    add("- Crypto has no cash flows / no valuation anchor (no earnings, no coupon) — this "
        "script answers \"historical correlation / combination math,\" NOT \"what should "
        "BTC/ETH's future expected return be.\" A low historical correlation with a fat "
        "pre-2022 return tailwind is not evidence of a repeatable expected return.")
    add("- Survivorship: BTC and ETH are the two survivors of a much larger set of "
        "cryptoassets from the same eras; assets that went to zero (many 2018/2022 "
        "alt-coins) are not in this sample. Any statement here about \"crypto\" only "
        "covers these two survivors.")
    add("- Single historical path, no bootstrap; BTC/ETH have ~11.8/~8.7 years of history "
        "in this dataset — short relative to SPY's ~33 years, so tail-window and "
        "sub-period cells for crypto have materially fewer independent regimes than the "
        "equity side of every comparison.")
    add("- IEF/cash proxies use the same HK 30% dividend-withholding convention applied "
        "elsewhere in this repo to bond-ETF distributions — an approximation (bond "
        "distributions may be taxed differently in practice), noted for completeness.")
    add("- Crypto close-price alignment onto the SPY calendar attributes weekend/holiday "
        "moves entirely to the next SPY trading day; this affects daily-return attribution "
        "(and hence daily-vs-monthly correlation comparisons) but not cumulative/monthly "
        "figures.")
    add("")
    add("## Implication")
    add("")
    add("(placeholder — filled by hand after reviewing Tables 1-6)")
    add("")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS} ({time.time()-t0:.0f}s total)", flush=True)


if __name__ == "__main__":
    main()
