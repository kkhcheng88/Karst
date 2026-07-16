"""KOL sector-flow claim check (tier-2, ETF-only) -- 2026-07-16.

The user follows a KOL who made three sector-level claims. This script tests each
one on real total-return price data (backtest/data.py load(), yfinance) so we can
tell the user which claims hold up and which don't, in plain language.

Universe: SOXX/SMH (semis), IGV (software), MAGS (Mag7, since 2023-04), CIBR
(cybersecurity), QQQ, SPY, XLF (financials).

Claim 1 -- "hardware (semis) vs software/Mag7/cyber are negatively correlated" is a
myth?  We separate two DIFFERENT meanings of "correlation" that get conflated:
  (a) ABSOLUTE daily-return correlation (rolling 63d) -- do they rise/fall TOGETHER?
      Expect strongly POSITIVE (both are "tech beta").
  (b) RELATIVE-STRENGTH correlation (rolling 63d, on ratio-to-QQQ CHANGES) -- does
      money rotate BETWEEN them when one leads/lags QQQ? This is where a genuine
      negative reading (rotation) could show up.
  Plus a "right now" readout: is semis-vs-QQQ strength diverging from Mag7-vs-QQQ
  strength over the last 21/63 trading days (i.e. is a semis->megacap rotation
  actually happening at the moment)?

Claim 2 -- does XLF show a repair/reaction pattern around bank earnings season
(JPM/GS report first, ~mid Jan/Apr/Jul/Oct)? We approximate JPM's release date each
quarter as the nearest trading day to the 14th of the reporting month (documented
approximation -- see report), then measure XLF's excess return vs SPY over
[release_day - 2 trading days, release_day + 5 trading days] vs all other days.
Small sample (~60 quarters) -- reported honestly (hit-rate + mean, not dressed up),
split into two halves of the sample for stability.

Claim 3 -- "semis correction is mostly done" after a >=15% pullback from a rolling
high. We find every SOXX drawdown episode since 2016 that first crosses -15% from
its most recent peak (episodes separated by a full recovery to a new high), and
look at what actually happened next (21/63/126 trading days forward), case by case,
against the unconditional (any random day) baseline.

Run: PYTHONUTF8=1 python backtest/experiments/exp_sector_flow_claims.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load

TICKERS = ["SOXX", "SMH", "IGV", "MAGS", "CIBR", "QQQ", "SPY", "XLF"]
WIN = 63          # rolling window for correlations (~1 quarter of trading days)
SHORT, LONG = 21, 63   # "right now" lookback windows


def load_all():
    out = {}
    for t in TICKERS:
        try:
            df = load(t, adjusted=True, min_rows=50)
            out[t] = df["close"]
            print(f"{t:5} loaded: {df.index[0].date()} -> {df.index[-1].date()}  n={len(df)}")
        except Exception as e:
            print(f"{t:5} SKIP: {str(e)[:60]}")
    return out


def rolling_corr(a: pd.Series, b: pd.Series, window=WIN) -> pd.Series:
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    return d["a"].rolling(window).corr(d["b"]).dropna()


def summarize_rc(rc: pd.Series) -> dict:
    if len(rc) == 0:
        return {"mean": np.nan, "pct_pos": np.nan, "current": np.nan, "n": 0}
    return {"mean": float(rc.mean()), "pct_pos": float((rc > 0).mean()),
            "current": float(rc.iloc[-1]), "n": len(rc)}


# ---------------------------------------------------------------------------
# Claim 1
# ---------------------------------------------------------------------------
def claim1(px: dict):
    print("\n" + "=" * 78)
    print("CLAIM 1 -- semis vs software/Mag7/cyber: negatively correlated (myth)?")
    print("=" * 78)

    qqq = px["QQQ"]
    ret = {t: np.log(px[t]).diff() for t in px if t != "QQQ"}
    ret["QQQ"] = np.log(qqq).diff()

    print("\n(a) ABSOLUTE daily-return correlation, rolling 63d (2016+ where available):")
    print(f"{'pair':16}{'mean corr':>10}{'%time>0':>9}{'current':>9}{'n obs':>7}")
    abs_rows = {}
    for semis in ["SOXX", "SMH"]:
        for other in ["IGV", "MAGS", "CIBR"]:
            if semis not in px or other not in px:
                continue
            rc = rolling_corr(ret[semis], ret[other])
            s = summarize_rc(rc)
            abs_rows[(semis, other)] = s
            print(f"{semis}-{other:12}{s['mean']:10.2f}{s['pct_pos']*100:8.0f}%{s['current']:9.2f}{s['n']:7d}")

    print("\n(b) RELATIVE-STRENGTH correlation, rolling 63d, on log-changes of the")
    print("    ETF/QQQ ratio (this is the ROTATION axis, not the absolute-return axis):")
    ratio_chg = {}
    for t in ["SOXX", "SMH", "IGV", "MAGS", "CIBR"]:
        if t not in px:
            continue
        r = (px[t] / qqq)
        ratio_chg[t] = np.log(r).diff()

    print(f"{'pair (ratio-chg)':20}{'mean corr':>10}{'%time>0':>9}{'current':>9}{'n obs':>7}")
    rel_rows = {}
    for semis in ["SOXX", "SMH"]:
        for other in ["IGV", "MAGS", "CIBR"]:
            if semis not in ratio_chg or other not in ratio_chg:
                continue
            rc = rolling_corr(ratio_chg[semis], ratio_chg[other])
            s = summarize_rc(rc)
            rel_rows[(semis, other)] = s
            print(f"{semis}/QQQ vs {other}/QQQ  {s['mean']:6.2f}{s['pct_pos']*100:8.0f}%{s['current']:9.2f}{s['n']:7d}")

    print("\n(c) RIGHT NOW -- relative-strength direction, last 21d / 63d")
    print("    (ratio = ETF/QQQ; positive = ETF outperforming QQQ over that window):")
    print(f"{'ratio':12}{'21d chg':>10}{'63d chg':>10}")
    now_rows = {}
    for t in ["SOXX", "SMH", "IGV", "MAGS", "CIBR"]:
        if t not in px:
            continue
        r = (px[t] / qqq).dropna()
        c21 = float(r.iloc[-1] / r.iloc[-1 - SHORT] - 1) if len(r) > SHORT else np.nan
        c63 = float(r.iloc[-1] / r.iloc[-1 - LONG] - 1) if len(r) > LONG else np.nan
        now_rows[t] = (c21, c63)
        print(f"{t}/QQQ     {c21*100:9.1f}%{c63*100:9.1f}%")

    return {"abs": abs_rows, "rel": rel_rows, "now": now_rows}


# ---------------------------------------------------------------------------
# Claim 2
# ---------------------------------------------------------------------------
def nearest_trading_day(index: pd.DatetimeIndex, target: pd.Timestamp):
    pos = index.searchsorted(target)
    cands = []
    if pos < len(index):
        cands.append((index[pos], pos))
    if pos > 0:
        cands.append((index[pos - 1], pos - 1))
    if not cands:
        return None, None
    day, loc = min(cands, key=lambda x: abs((x[0] - target).days))
    return day, loc


def claim2(px: dict):
    print("\n" + "=" * 78)
    print("CLAIM 2 -- does XLF show a bank-earnings-week repair pattern?")
    print("=" * 78)
    print("APPROXIMATION (documented): JPM/GS report first each quarter, historically")
    print("mid Jan / Apr / Jul / Oct. We proxy the release day as the nearest actual")
    print("trading day to the 14th of that month -- this is a calendar approximation,")
    print("NOT the confirmed JPM press-release date, and can be off by a few days.")

    xlf, spy = px["XLF"], px["SPY"]
    df = pd.DataFrame({"xlf": xlf, "spy": spy}).dropna()
    idx = df.index
    daily_excess = (df["xlf"].pct_change() - df["spy"].pct_change()).dropna()

    start_year = idx[0].year
    end_year = idx[-1].year
    events = []
    for y in range(start_year, end_year + 1):
        for m in (1, 4, 7, 10):
            target = pd.Timestamp(year=y, month=m, day=14)
            if target < idx[0] or target > idx[-1]:
                continue
            day, loc = nearest_trading_day(idx, target)
            if day is None:
                continue
            lo, hi = loc - 2, loc + 5
            if lo < 0 or hi >= len(idx):
                continue  # not enough data for the full window yet
            window_ret = float(daily_excess.iloc[lo:hi + 1].sum())
            events.append({"year": y, "month": m, "approx_date": str(day.date()),
                            "window_excess": window_ret})

    ev = pd.DataFrame(events)
    win_days_per_event = 8  # -2 .. +5 inclusive
    baseline_mean = float(daily_excess.mean()) * win_days_per_event

    print(f"\nn quarters with full window data: {len(ev)}  "
          f"(baseline = mean daily XLF-SPY excess x {win_days_per_event}d)")
    print(f"baseline (any random {win_days_per_event}-day span): {baseline_mean*100:.2f}%")
    print(f"earnings-week window: mean excess {ev['window_excess'].mean()*100:.2f}%  "
          f"median {ev['window_excess'].median()*100:.2f}%  "
          f"hit-rate(>0) {(ev['window_excess'] > 0).mean()*100:.0f}%")

    mid = len(ev) // 2
    first_half, second_half = ev.iloc[:mid], ev.iloc[mid:]
    print(f"\nfirst half of sample  ({first_half['year'].min()}-{first_half['year'].max()}, n={len(first_half)}): "
          f"mean {first_half['window_excess'].mean()*100:.2f}%  hit-rate {(first_half['window_excess']>0).mean()*100:.0f}%")
    print(f"second half of sample ({second_half['year'].min()}-{second_half['year'].max()}, n={len(second_half)}): "
          f"mean {second_half['window_excess'].mean()*100:.2f}%  hit-rate {(second_half['window_excess']>0).mean()*100:.0f}%")

    since2016 = ev[ev["year"] >= 2016]
    print(f"\n2016+ subset (n={len(since2016)}): mean {since2016['window_excess'].mean()*100:.2f}%  "
          f"hit-rate {(since2016['window_excess']>0).mean()*100:.0f}%")

    print("\nall quarters:")
    print(f"{'year':6}{'mon':5}{'approx date':>13}{'window excess':>15}")
    for r in events:
        print(f"{r['year']:<6}{r['month']:<5}{r['approx_date']:>13}{r['window_excess']*100:14.2f}%")

    # current readout
    s200 = xlf.rolling(200).mean()
    xlf_vs_sma = float(xlf.iloc[-1] / s200.iloc[-1] - 1)
    r_xlf_spy = (xlf / spy).dropna()
    rs21 = float(r_xlf_spy.iloc[-1] / r_xlf_spy.iloc[-1 - SHORT] - 1)
    rs63 = float(r_xlf_spy.iloc[-1] / r_xlf_spy.iloc[-1 - LONG] - 1)
    print(f"\nRIGHT NOW: XLF vs 200d avg = {xlf_vs_sma*100:+.1f}%   "
          f"XLF/SPY relative strength 21d = {rs21*100:+.1f}%  63d = {rs63*100:+.1f}%")

    return {"events": ev, "baseline": baseline_mean, "xlf_vs_sma": xlf_vs_sma,
            "rs21": rs21, "rs63": rs63}


# ---------------------------------------------------------------------------
# Claim 3
# ---------------------------------------------------------------------------
def drawdown_episodes(close: pd.Series, threshold=0.15, since="2016-01-01"):
    c = close[close.index >= since]
    c = c.dropna()
    peak = c.iloc[0]
    peak_date = c.index[0]
    in_dd = False
    episodes = []
    for i in range(1, len(c)):
        v = c.iloc[i]
        if v > peak:
            peak = v
            peak_date = c.index[i]
            in_dd = False  # new high -> fully recovered, ready to arm the next episode
            continue
        dd = v / peak - 1
        if not in_dd and dd <= -threshold:
            in_dd = True
            episodes.append({"entry_date": c.index[i], "entry_idx": i,
                              "peak_price": peak, "peak_date": peak_date,
                              "entry_price": v,
                              "trough_dd": dd, "trough_date": c.index[i]})
        elif in_dd and dd < episodes[-1]["trough_dd"]:
            episodes[-1]["trough_dd"] = dd
            episodes[-1]["trough_date"] = c.index[i]
    return c, episodes


def claim3(px: dict):
    print("\n" + "=" * 78)
    print("CLAIM 3 -- 'semis correction is mostly done' after a >=15% pullback")
    print("=" * 78)

    soxx = px["SOXX"]
    c, episodes = drawdown_episodes(soxx, threshold=0.15, since="2016-01-01")
    print(f"SOXX since 2016: n={len(c)} days, {len(episodes)} distinct >=15%-drawdown episodes "
          "(a new episode only starts after the prior one fully recovers to a new high)")

    horizons = [21, 63, 126]
    rows = []
    for ep in episodes:
        i = ep["entry_idx"]
        row = {"entry_date": str(ep["entry_date"].date()), "entry_dd_at_trigger": np.nan,
               "eventual_trough_dd": ep["trough_dd"]}
        p0 = c.iloc[i]
        row["entry_dd_at_trigger"] = float(p0 / ep["peak_price"] - 1)
        for h in horizons:
            if i + h < len(c):
                row[f"fwd_{h}d"] = float(c.iloc[i + h] / p0 - 1)
            else:
                row[f"fwd_{h}d"] = np.nan
        rows.append(row)

    print(f"\n{'entry date':12}{'trigger dd':>11}{'eventual low':>13}" +
          "".join(f"{'fwd '+str(h)+'d':>10}" for h in horizons))
    for r in rows:
        line = f"{r['entry_date']:12}{r['entry_dd_at_trigger']*100:10.1f}%{r['eventual_trough_dd']*100:12.1f}%"
        for h in horizons:
            v = r[f"fwd_{h}d"]
            line += f"{'n/a':>10}" if np.isnan(v) else f"{v*100:9.1f}%"
        print(line)

    # unconditional baseline over the same period
    print("\nunconditional baseline (forward return from ANY random day in the same period):")
    close_arr = c.to_numpy()
    for h in horizons:
        vals = close_arr[h:] / close_arr[:-h] - 1
        good = [r[f"fwd_{h}d"] for r in rows if not np.isnan(r[f"fwd_{h}d"])]
        n_pos = sum(1 for v in good if v > 0)
        print(f"  {h:>3}d: baseline mean {np.mean(vals)*100:6.1f}%  |  "
              f"after-15%-drawdown mean {np.mean(good)*100 if good else float('nan'):6.1f}%  "
              f"({n_pos}/{len(good)} episodes positive)")

    return rows


def run():
    px = load_all()
    if "QQQ" not in px:
        print("QQQ missing -- cannot compute relative-strength claims. Abort.")
        return
    c1 = claim1(px)
    c2 = claim2(px) if "XLF" in px and "SPY" in px else None
    c3 = claim3(px) if "SOXX" in px else None
    print("\n" + "=" * 78)
    print("DONE")
    print("=" * 78)
    return c1, c2, c3


if __name__ == "__main__":
    run()
