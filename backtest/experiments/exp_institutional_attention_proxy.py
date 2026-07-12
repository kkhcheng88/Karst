"""Institutional-ownership / "neglected firm" crowding axis -- LOW END, broad-universe backtest.

Context: Phase-3's priced-in gate currently only uses analyst coverage / OW-rating narrative as the
LATE/crowded end of a "market attention" axis. Peter Lynch (One Up on Wall Street Sec.8.1.5) argues
the SAME axis has an early-side signal: low institutional ownership / low analyst coverage = "not yet
discovered" = often a positive. This is also a real, named academic anomaly: Arbel & Strebel (1982,
1983) "neglected firm effect" -- firms followed by fewer analysts earn higher average returns, and the
effect is NOT just a small-firm-effect proxy (persists after controlling for size).

FEASIBILITY (see backtest/results/2026-07-11_institutional_ownership_crowding_axis.md Sec.1 for detail):
  - yfinance `heldPercentInstitutions` / `numberOfAnalystOpinions`: confirmed via yfinance source
    (scrapers/holders.py, scrapers/analysis.py) to be single quoteSummary snapshot calls with NO date
    param -- there is no free historical time series for either institutional ownership OR analyst
    coverage count via yfinance. defeatbeta_api has neither field at all.
  - SEC EDGAR Form 13F bulk data sets (sec.gov/data-research/.../form-13f-data-sets) DO contain the raw
    holdings needed to reconstruct historical institutional-ownership%, confirmed by downloading one
    quarter (01sep2025-30nov2025_form13f.zip = 85.6MB zipped / 338MB INFOTABLE.tsv, 3.27M rows). But
    the INFOTABLE has CUSIP, not ticker, and there is no free authoritative CUSIP<->ticker crosswalk
    (CUSIP itself is licensed/proprietary data; OpenFIGI explicitly does not carry it). Reconstructing
    even a ~200-name universe's historical ownership% needs per-name CUSIP resolution (fuzzy match
    NAMEOFISSUER across ~52 quarterly files back to 2013q2) + a historical shares-outstanding series to
    normalize -- a multi-day engineering project, out of scope here. VERDICT: not attempted.
  - PROXY CHOSEN: dollar-volume turnover (trailing 63d avg $ volume / market cap) as a market-attention
    proxy. Conceptually: low turnover = few active participants = plausibly under-covered/under-owned
    (same underlying construct Lynch/Arbel-Strebel describe, "how much does the Street care about this
    name"), and unlike institutional-ownership% or analyst-count, this has a clean, deep, free daily
    history via defeatbeta (price+volume back to listing) x cached market cap
    (backtest/.insider_data/mktcap_defeatbeta.pkl). This is a PROXY, not the same construct -- flagged
    throughout.

METHOD:
  - Universe: backtest/.insider_data/px_defeatbeta.pkl / mktcap_defeatbeta.pkl (built for the insider
    project; 2627 tickers w/ >=500 daily rows). NOT hand-picked: systematic alphabetical sample, ~75
    tickers per market-cap tier (micro/small/mid/large, same thresholds as exp_families_mktcap_tiers.py)
    = ~300 names total, so small/micro caps are NOT dropped (per backtest-testing-standard memory).
  - Per name: fetch full price+volume history fresh via defeatbeta_api (cached px pkl has no volume).
  - turnover_t = (63d avg $ volume) / (market cap, ffilled from quarterly-ish mc series)
  - attention state = OWN-HISTORY rolling percentile of turnover (756d window, min 252d) -- same
    convention as exp_valuation_broad.py's PE-percentile method. Q0 = bottom quintile (LOW turnover =
    Lynch's "low attention" bucket), Q4 = top quintile (crowded).
  - dynamic tier per ticker-date (from ffilled mkt cap, same bins as exp_families_mktcap_tiers.py)
  - forward excess return @ 63/126/252 trading days = name's fwd return MINUS the equal-weighted
    average fwd return of ALL sampled names in the SAME TIER on the SAME DATE. This is the
    size-matched-benchmark control the backtest-testing-standard memory requires, and it's exactly the
    control Arbel-Strebel say the neglected-firm effect must survive.
  - Stat test: primary = per-ticker mean(Q0 excess) - mean(Q4 excess), then one-sample t-test of that
    spread ACROSS TICKERS (N = names with usable obs in both quintiles) -- avoids treating overlapping
    daily windows as independent observations. Secondary: pooled quintile means (flagged as
    autocorrelated/overlapping, descriptive only).

Run: python backtest/experiments/exp_institutional_attention_proxy.py
"""
from __future__ import annotations

import contextlib
import io
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
TIERS_BINS = [0, 3e8, 2e9, 1e10, np.inf]
TIERS_LABELS = ["micro <$300M", "small $300M-2B", "mid $2B-10B", "large >$10B"]
WIN, MINP = 756, 252
HORIZONS = {"fwd63": 63, "fwd126": 126, "fwd252": 252}
N_PER_TIER = 75
START = "2016-01-01"
SPLIT = pd.Timestamp("2021-01-01")


def build_sample_universe():
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    mc = pickle.load(open(os.path.join(_DATA, "mktcap_defeatbeta.pkl"), "rb"))
    rows = []
    for t, s in mc.items():
        if not isinstance(s, pd.Series) or s.dropna().empty:
            continue
        p = px.get(t)
        if not isinstance(p, pd.Series) or len(p) < 500:
            continue
        med = s.dropna().median()
        rows.append((t, med))
    df = pd.DataFrame(rows, columns=["t", "medmc"]).sort_values("t")
    df["tier"] = pd.cut(df["medmc"], bins=TIERS_BINS, labels=TIERS_LABELS)
    chosen = []
    for lab in TIERS_LABELS:
        sub = df[df["tier"] == lab]["t"].tolist()
        if len(sub) <= N_PER_TIER:
            pick = sub
        else:
            step = len(sub) / N_PER_TIER
            idx = [int(i * step) for i in range(N_PER_TIER)]
            pick = [sub[i] for i in idx]
        chosen.extend(pick)
    print(f"[universe] candidates(>=500 rows)={len(df)} -> sampled={len(chosen)} "
          f"({N_PER_TIER}/tier target x{len(TIERS_LABELS)} tiers)")
    return chosen, mc


def fetch_one(sym, mc_series):
    with contextlib.redirect_stdout(io.StringIO()):
        from defeatbeta_api.data.ticker import Ticker
    p = Ticker(sym).price()
    p = p[["report_date", "close", "volume"]].copy()
    p["date"] = pd.to_datetime(p["report_date"])
    p = p.set_index("date").sort_index()
    p = p[~p.index.duplicated()]
    close, vol = p["close"], p["volume"]
    if len(close) < 500:
        return None
    mc_ff = mc_series.reindex(close.index.union(mc_series.index)).sort_index().ffill().reindex(close.index)
    dollar_vol = close * vol
    avg_dv = dollar_vol.rolling(63, min_periods=42).mean()
    turnover = (avg_dv / mc_ff).replace([np.inf, -np.inf], np.nan)
    pctile = turnover.rolling(WIN, min_periods=MINP).rank(pct=True)
    tier = pd.cut(mc_ff, bins=TIERS_BINS, labels=TIERS_LABELS)
    out = pd.DataFrame({"close": close, "pctile": pctile, "tier": tier})
    for name, h in HORIZONS.items():
        out[name] = close.shift(-h) / close - 1.0
    out = out[out.index >= START]
    out["sym"] = sym
    return out


def run():
    chosen, mc = build_sample_universe()
    panels = []
    t0 = time.time()
    ok = fail = 0
    for i, sym in enumerate(chosen):
        try:
            d = fetch_one(sym, mc[sym])
            if d is not None and not d.empty:
                panels.append(d)
                ok += 1
            else:
                fail += 1
        except Exception:
            fail += 1
        if (i + 1) % 25 == 0:
            print(f"  ...{i+1}/{len(chosen)} fetched (ok={ok} fail={fail}) elapsed={time.time()-t0:.0f}s")
    print(f"[fetch] done: ok={ok} fail={fail} elapsed={time.time()-t0:.0f}s")

    panel = pd.concat(panels)
    panel.index.name = "date"
    panel = panel.reset_index()
    panel = panel.dropna(subset=["tier"])
    print(f"[panel] rows={len(panel)} names={panel['sym'].nunique()} "
          f"date_range={panel['date'].min().date()}..{panel['date'].max().date()}")

    with open(os.path.join(_DATA, "attention_panel.pkl"), "wb") as f:
        pickle.dump(panel, f)

    # tier-matched benchmark: equal-weighted avg fwd return by (date,tier), each horizon
    for name in HORIZONS:
        bench = panel.groupby(["date", "tier"], observed=True)[name].transform("mean")
        panel[name + "_xs"] = panel[name] - bench

    print("\n" + "=" * 100)
    print("PART A -- pooled quintile means (descriptive; overlapping windows, NOT the primary stat test)")
    print("=" * 100)
    panel["q"] = panel.groupby(["date", "tier"], observed=True)["pctile"].transform(
        lambda s: s)  # noop placeholder; quintile from own pctile directly below
    panel["quintile"] = pd.cut(panel["pctile"], bins=[0, .2, .4, .6, .8, 1.0], labels=[0, 1, 2, 3, 4],
                                include_lowest=True)

    for name, h in HORIZONS.items():
        print(f"\n-- horizon {h}d ({name}) --  excess return vs same-tier same-date average, by quintile"
              f" (Q0=lowest turnover/attention .. Q4=highest)")
        g = panel.dropna(subset=[name + "_xs", "quintile"]).groupby("quintile", observed=True)[name + "_xs"]
        for q in [0, 1, 2, 3, 4]:
            if q in g.groups:
                vals = g.get_group(q)
                print(f"   Q{q}: n={len(vals):>7}  mean_xs={vals.mean()*100:>6.2f}%  "
                      f"median_xs={vals.median()*100:>6.2f}%")
        if 0 in g.groups and 4 in g.groups:
            spread = g.get_group(0).mean() - g.get_group(4).mean()
            print(f"   pooled spread Q0-Q4 = {spread*100:+.2f}pp  (descriptive only, see Part B for real test)")

    print("\n" + "=" * 100)
    print("PART B -- PRIMARY TEST: per-ticker mean(Q0 excess) - mean(Q4 excess), t-test ACROSS TICKERS")
    print("=" * 100)
    for name, h in HORIZONS.items():
        rows = []
        for sym, d in panel.groupby("sym"):
            d0 = d[(d["quintile"] == 0)][name + "_xs"].dropna()
            d4 = d[(d["quintile"] == 4)][name + "_xs"].dropna()
            if len(d0) >= 20 and len(d4) >= 20:
                rows.append((sym, d0.mean(), d4.mean(), d0.mean() - d4.mean(), d["tier"].iloc[0]))
        r = pd.DataFrame(rows, columns=["sym", "q0_mean", "q4_mean", "spread", "tier"])
        if len(r) < 5:
            print(f"\n-- {h}d: too few names with usable Q0+Q4 history (n={len(r)}) -- skip")
            continue
        t, p = stats.ttest_1samp(r["spread"], 0.0)
        pos_pct = (r["spread"] > 0).mean() * 100
        print(f"\n-- horizon {h}d ({name}) -- N_names={len(r)}  "
              f"mean(Q0-Q4 excess)={r['spread'].mean()*100:+.2f}pp  "
              f"t={t:+.2f}  p={p:.3f}  %names_positive={pos_pct:.0f}%")
        print("   by tier:")
        for lab in TIERS_LABELS:
            sub = r[r["tier"] == lab]
            if len(sub) >= 5:
                tt, pp = stats.ttest_1samp(sub["spread"], 0.0)
                print(f"     {lab:16}: n={len(sub):>3}  mean_spread={sub['spread'].mean()*100:>+6.2f}pp  "
                      f"t={tt:+.2f}  p={pp:.3f}  %pos={((sub['spread']>0).mean()*100):.0f}%")

    print("\n" + "=" * 100)
    print("PART C -- period stability: pre-2021 vs 2021+ (pooled quintile spread, descriptive)")
    print("=" * 100)
    for half_name, mask in [("pre-2021", panel["date"] < SPLIT), ("2021+", panel["date"] >= SPLIT)]:
        sub = panel[mask]
        for name, h in [("fwd126", 126)]:
            g = sub.dropna(subset=[name + "_xs", "quintile"]).groupby("quintile", observed=True)[name + "_xs"]
            if 0 in g.groups and 4 in g.groups:
                spread = g.get_group(0).mean() - g.get_group(4).mean()
                print(f"   {half_name:10} fwd126d pooled spread Q0-Q4 = {spread*100:+.2f}pp "
                      f"(n_Q0={len(g.get_group(0))}, n_Q4={len(g.get_group(4))})")


if __name__ == "__main__":
    run()
