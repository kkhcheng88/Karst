"""RSI2 leader dip-reversion: does it still exist (2010+ literature says RSI2/Connors
decayed hard), and if it does, how much of it survives ETF-level diversification?

User's hypothesis: mature quality leaders that "won't die" should show strong short-term
mean reversion (buy the dip, sell the bounce) -- and this should still be visible at the
concentrated-ETF level (MAGS/QQQ/SOXX/XLK), just diluted by basket averaging. This script
does NOT assume the hypothesis is true -- literature (Connors RSI2) says the classic edge
decayed sharply post-2010, and this repo's own fear/greed mean-reversion probe found
alpha ~ 0 at the index level. Test honestly; report decay if decay is what's there.

Universe (3 layers):
  (a) individual leaders: 8 mega-cap tech (AAPL MSFT NVDA GOOGL AMZN META AVGO TSLA)
      + 6 mature non-tech leaders (JPM JNJ PG XOM UNH HD)
  (b) concentrated ETFs: MAGS QQQ SOXX XLK
  (c) broad ETF: SPY

Signal variants (entry, all gated by close > 200SMA -- only buy dips in an uptrend):
  RSI2_LT10 : RSI(2) < 10
  RSI2_LT5  : RSI(2) < 5   (stricter)
  DROP3_3PCT: 3-day cumulative return <= -3%

Exit (same for all variants): RSI(2) > 70, or 10 trading days max, whichever first.
Entry executes at the NEXT close after the signal fires (no same-bar lookahead).
No overlapping positions per symbol/variant (skip ahead past the exit).

Metrics per (symbol, variant, era): hit rate, avg event return, avg holding days,
signal frequency/year, annualized contribution (event returns compounded, cash
otherwise, annualized over the era's calendar span) vs era buy&hold CAGR (excess),
plus worst single event return (individual-stock tail risk).

Eras: 2016-2020 vs 2021+ (decay check). Data: adjusted (total-return) closes via
backtest/data.py load(..., adjusted=True).

Run: PYTHONUTF8=1 python backtest/experiments/exp_leader_dip_reversion.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load  # noqa: E402

LEADERS_TECH = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "TSLA"]
LEADERS_NONTECH = ["JPM", "JNJ", "PG", "XOM", "UNH", "HD"]
LEADERS = LEADERS_TECH + LEADERS_NONTECH
CONCENTRATED_ETF = ["MAGS", "QQQ", "SOXX", "XLK"]
BROAD_ETF = ["SPY"]
ALL_SYMBOLS = LEADERS + CONCENTRATED_ETF + BROAD_ETF

SMA_TREND = 200
EXIT_RSI = 70.0
MAX_HOLD = 10

ERAS = {
    "2016-2020": (pd.Timestamp("2016-01-01"), pd.Timestamp("2020-12-31")),
    "2021+": (pd.Timestamp("2021-01-01"), pd.Timestamp("2099-01-01")),
}


def compute_rsi(close: pd.Series, period: int = 2) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    return rsi.fillna(100.0)


def build_frame(symbol: str) -> pd.DataFrame | None:
    try:
        df = load(symbol, adjusted=True)
    except Exception as e:
        print(f"  [skip] {symbol}: {type(e).__name__}: {str(e)[:100]}")
        return None
    df = df.copy()
    df["sma200"] = df["close"].rolling(SMA_TREND, min_periods=SMA_TREND).mean()
    df["rsi2"] = compute_rsi(df["close"], 2)
    df["trend_ok"] = df["close"] > df["sma200"]
    df["ret3"] = df["close"].pct_change(3)
    return df


def signal_mask(df: pd.DataFrame, variant: str) -> pd.Series:
    if variant == "RSI2_LT10":
        base = df["rsi2"] < 10.0
    elif variant == "RSI2_LT5":
        base = df["rsi2"] < 5.0
    elif variant == "DROP3_3PCT":
        base = df["ret3"] <= -0.03
    else:
        raise ValueError(variant)
    return (base & df["trend_ok"]).fillna(False)


def run_events(df: pd.DataFrame, sig: pd.Series) -> list[dict]:
    """Non-overlapping event study. Entry = next close after signal day.
    Exit = first day with RSI2 > EXIT_RSI (checked from day 2 of the hold onward),
    or MAX_HOLD trading days, whichever first."""
    close = df["close"].to_numpy()
    rsi2 = df["rsi2"].to_numpy()
    dates = df.index
    n = len(df)
    sig_arr = sig.to_numpy()
    events = []
    i = 0
    while i < n - 1:
        if not sig_arr[i]:
            i += 1
            continue
        entry_idx = i + 1
        exit_idx = None
        for d in range(1, MAX_HOLD + 1):
            j = entry_idx + d - 1
            if j >= n:
                exit_idx = n - 1
                break
            if d > 1 and rsi2[j] > EXIT_RSI:
                exit_idx = j
                break
            if d == MAX_HOLD:
                exit_idx = j
                break
        if exit_idx is None:
            exit_idx = min(entry_idx + MAX_HOLD - 1, n - 1)
        ret = float(close[exit_idx] / close[entry_idx] - 1.0)
        hold_days = int(exit_idx - entry_idx + 1)
        events.append({
            "entry_date": dates[entry_idx], "exit_date": dates[exit_idx],
            "ret": ret, "hold_days": hold_days,
        })
        i = exit_idx + 1
    return events


def era_bh_cagr(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple[float, float]:
    """Buy&hold CAGR of the symbol within [start, end]. Returns (cagr, years).
    Context only (shows the era's overall drift) -- NOT the excess benchmark
    (that would conflate 'always invested' vs 'invested ~5 days/event' exposure)."""
    sub = df.loc[(df.index >= start) & (df.index <= end)]
    if len(sub) < 30:
        return (np.nan, np.nan)
    years = (sub.index[-1] - sub.index[0]).days / 365.25
    if years <= 0:
        return (np.nan, np.nan)
    total = sub["close"].iloc[-1] / sub["close"].iloc[0]
    return (float(total ** (1.0 / years) - 1.0), years)


def _matched_bench_factory(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    """Unconditional expected return for a RANDOM entry held k trading days, matched
    to each event's actual holding length, over the same era -- controls for
    'always invested vs invested ~5 days/event' exposure so the excess is apples
    to apples (not just re-discovering the era's drift)."""
    close = df["close"]
    cache: dict[int, float] = {}

    def bench(k: int) -> float:
        if k not in cache:
            r = close.pct_change(k)
            sub = r.loc[(r.index >= start) & (r.index <= end)].dropna()
            cache[k] = float(sub.mean()) if len(sub) > 10 else np.nan
        return cache[k]
    return bench


def summarize(events: list[dict], df: pd.DataFrame, start: pd.Timestamp,
              end: pd.Timestamp) -> dict:
    ev = [e for e in events if start <= e["entry_date"] <= end]
    bh_cagr, years = era_bh_cagr(df, start, end)
    if len(ev) == 0 or np.isnan(years) or years <= 0:
        return {"n": len(ev), "hit_rate": np.nan, "avg_ret": np.nan,
                "avg_hold": np.nan, "freq_yr": np.nan, "ann_contrib": np.nan,
                "bh_cagr": bh_cagr, "excess": np.nan, "worst": np.nan}
    rets = np.array([e["ret"] for e in ev])
    hit_rate = float((rets > 0).mean())
    avg_ret = float(rets.mean())
    avg_hold = float(np.mean([e["hold_days"] for e in ev]))
    freq_yr = len(ev) / years
    equity_final = float(np.prod(1.0 + rets))
    ann_contrib = equity_final ** (1.0 / years) - 1.0
    bench = _matched_bench_factory(df, start, end)
    matched = np.array([bench(e["hold_days"]) for e in ev])
    valid = ~np.isnan(matched)
    excess = float((rets[valid] - matched[valid]).mean()) if valid.any() else np.nan
    worst = float(rets.min())
    return {"n": len(ev), "hit_rate": hit_rate, "avg_ret": avg_ret,
            "avg_hold": avg_hold, "freq_yr": freq_yr, "ann_contrib": ann_contrib,
            "bh_cagr": bh_cagr, "excess": excess, "worst": worst}


def fmt_pct(x, dp=1):
    return "n/a" if (x is None or (isinstance(x, float) and np.isnan(x))) else f"{x*100:.{dp}f}%"


def main():
    variants = ["RSI2_LT10", "RSI2_LT5", "DROP3_3PCT"]
    frames = {}
    print("=== loading data (adjusted, total-return) ===")
    for sym in ALL_SYMBOLS:
        df = build_frame(sym)
        if df is not None:
            frames[sym] = df
            print(f"  {sym:6} rows={len(df):5} {df.index.min().date()} -> {df.index.max().date()}")

    full_start = pd.Timestamp("2010-01-01")
    full_end = pd.Timestamp("2099-01-01")

    results = []  # rows: symbol, variant, era, metrics
    for sym, df in frames.items():
        for variant in variants:
            sig = signal_mask(df, variant)
            events = run_events(df, sig)
            for era_name, (s, e) in {**ERAS, "FULL": (full_start, full_end)}.items():
                m = summarize(events, df, s, e)
                results.append({"symbol": sym, "variant": variant, "era": era_name, **m})

    res = pd.DataFrame(results)

    def layer_of(sym):
        if sym in LEADERS:
            return "LEADER"
        if sym in CONCENTRATED_ETF:
            return "CONC_ETF"
        return "BROAD_ETF"
    res["layer"] = res["symbol"].map(layer_of)

    print("\n=== per-symbol event study (FULL sample) ===")
    for variant in variants:
        print(f"\n-- variant: {variant} --")
        sub = res[(res["variant"] == variant) & (res["era"] == "FULL")]
        print(f"{'symbol':7}{'layer':10}{'n':>5}{'hit%':>7}{'avg_ret':>9}{'avg_hold':>9}"
              f"{'freq/yr':>9}{'ann_contrib':>13}{'bh_cagr':>10}{'excess':>9}{'worst':>9}")
        for _, r in sub.sort_values("layer").iterrows():
            print(f"{r['symbol']:7}{r['layer']:10}{r['n']:>5.0f}"
                  f"{fmt_pct(r['hit_rate']):>7}{fmt_pct(r['avg_ret']):>9}"
                  f"{r['avg_hold']:>9.1f}{r['freq_yr']:>9.1f}"
                  f"{fmt_pct(r['ann_contrib']):>13}{fmt_pct(r['bh_cagr']):>10}"
                  f"{fmt_pct(r['excess']):>9}{fmt_pct(r['worst']):>9}")

    print("\n=== era split (decay check): 2016-2020 vs 2021+ ===")
    for variant in variants:
        print(f"\n-- variant: {variant} --")
        for era_name in ["2016-2020", "2021+"]:
            sub = res[(res["variant"] == variant) & (res["era"] == era_name)]
            layer_avg = sub.groupby("layer")["excess"].mean()
            layer_hit = sub.groupby("layer")["hit_rate"].mean()
            layer_n = sub.groupby("layer")["n"].sum()
            print(f"  {era_name}:")
            for layer in ["LEADER", "CONC_ETF", "BROAD_ETF"]:
                if layer in layer_avg.index:
                    print(f"    {layer:10} avg_excess={fmt_pct(layer_avg[layer]):>8}  "
                          f"avg_hit={fmt_pct(layer_hit[layer]):>7}  n_events={int(layer_n[layer])}")

    print("\n=== dispersion-premium table (FULL sample, avg across symbols in layer) ===")
    for variant in variants:
        sub = res[(res["variant"] == variant) & (res["era"] == "FULL")]
        layer_avg = sub.groupby("layer")["excess"].mean()
        layer_ann = sub.groupby("layer")["ann_contrib"].mean()
        layer_hit = sub.groupby("layer")["hit_rate"].mean()
        print(f"\n-- variant: {variant} --")
        for layer in ["LEADER", "CONC_ETF", "BROAD_ETF"]:
            if layer in layer_avg.index:
                print(f"  {layer:10} avg_ann_contrib={fmt_pct(layer_ann[layer]):>8}  "
                      f"avg_excess_vs_bh={fmt_pct(layer_avg[layer]):>8}  avg_hit={fmt_pct(layer_hit[layer]):>7}")
        if "LEADER" in layer_avg.index and "CONC_ETF" in layer_avg.index:
            premium = layer_avg["LEADER"] - layer_avg["CONC_ETF"]
            print(f"  >> dispersion premium (LEADER excess - CONC_ETF excess) = {fmt_pct(premium)}")

    print("\n=== worst single event per leader (tail risk, FULL sample, RSI2_LT10) ===")
    sub = res[(res["variant"] == "RSI2_LT10") & (res["era"] == "FULL") & (res["layer"] == "LEADER")]
    for _, r in sub.sort_values("worst").iterrows():
        print(f"  {r['symbol']:7} worst_event_ret={fmt_pct(r['worst']):>8}  n_events={r['n']:.0f}")

    scratch_csv = os.environ.get("KARST_SCRATCH_CSV", "")
    if scratch_csv:
        res.to_csv(scratch_csv, index=False)
        print(f"\n[saved] {scratch_csv}")


if __name__ == "__main__":
    main()
