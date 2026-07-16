"""RSI2 dip-buying judged on CAPITAL EFFICIENCY (PnL / avg exposure) -- 2026-07-17.

USER'S CHALLENGE (and it is a fair one): 2026-07-16_leader_dip_reversion.md judged dip-buying
against B&H and same-length random entry, and reported ~zero excess. But B&H is a 100%-exposure
benchmark. If capital is LIMITED, the hours you are NOT in QQQ/SMH are hours that capital can
earn elsewhere -- so the right yardstick is PnL divided by average exposure, not total return.
That is Karst's stated primary metric (memory: tier1-metrics-decision) and the spirit of
AA-strict (gate-out premium parks in the ballast trio; capital is never dead).

WHAT THIS ADDS: the capital-efficiency lens, plus the control that lens still needs. A high
PnL/exposure ratio proves nothing on its own -- a SMALL denominator inflates it (documented trap:
2026-07-17_xle_xlk_rotation.md conclusion 3). So the control here is random entry with the
IDENTICAL exposure AND trade count: if RSI2 carries information, it must beat that, not B&H.

Run: PYTHONUTF8=1 python backtest/experiments/exp_dip_capital_efficiency.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load

SINCE = "2016-01-01"
N_SIMS = 2000
SEED = 42
TICKERS = ["SMH", "QQQ", "SOXX"]


def rsi(s: pd.Series, n: int = 2) -> pd.Series:
    d = s.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    ru = up.ewm(alpha=1 / n, adjust=False).mean()
    rd = dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + ru / rd)


def run_one(ticker: str, rng: np.random.Generator) -> dict:
    px = load(ticker, adjusted=True, min_rows=50)["close"]
    df = pd.DataFrame({"px": px, "r2": rsi(px, 2), "sma": px.rolling(200).mean()}).dropna()
    df = df[df.index >= SINCE]
    ret = np.log(df["px"]).diff().fillna(0).values
    n = len(df)

    # Signal T (RSI2<10 AND close>200SMA) -> enter T+1 close -> exit on RSI2>70 or 10 td.
    inpos, trades, i = np.zeros(n), [], 0
    while i < n - 1:
        if df["r2"].iloc[i] < 10 and df["px"].iloc[i] > df["sma"].iloc[i]:
            e = i + 1
            j = e
            while j < min(e + 10, n - 1) and df["r2"].iloc[j] <= 70:
                j += 1
            inpos[e + 1:j + 1] = 1
            trades.append((e, j))
            i = j + 1
        else:
            i += 1

    expo = inpos.mean()
    pnl_dip, pnl_bh = float((ret * inpos).sum()), float(ret.sum())
    ce_dip = pnl_dip / expo if expo > 0 else np.nan

    # Control: same trade count, same durations, random placement -> isolates the SIGNAL from
    # the structural fact that short bursts in a rising asset are capital-efficient by nature.
    durs = [j - e for e, j in trades]
    sims = np.empty(N_SIMS)
    for k in range(N_SIMS):
        m = np.zeros(n)
        for d in durs:
            s0 = rng.integers(0, max(1, n - d - 1))
            m[s0:s0 + d] = 1
        sims[k] = float((ret * m).sum()) / max(m.mean(), 1e-9)

    return {
        "ticker": ticker, "n_trades": len(trades), "expo": expo, "n_days": n,
        "pnl_dip": pnl_dip, "pnl_bh": pnl_bh, "ce_dip": ce_dip, "ce_bh": pnl_bh,
        "sim_med": float(np.median(sims)), "sim_p10": float(np.percentile(sims, 10)),
        "sim_p90": float(np.percentile(sims, 90)),
        "pctile": float((sims < ce_dip).mean() * 100),
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = [run_one(t, rng) for t in TICKERS]
    print(f"\n{'ticker':7} {'trades':>6} {'expo':>7} {'CE dip':>9} {'CE B&H':>9} "
          f"{'CE rand med':>12} {'pctile':>7}")
    for r in rows:
        print(f"{r['ticker']:7} {r['n_trades']:6d} {r['expo']*100:6.1f}% {r['ce_dip']*100:8.1f}% "
              f"{r['ce_bh']*100:8.1f}% {r['sim_med']*100:11.1f}% {r['pctile']:6.0f}")

    print("\nBreak-even on the freed capital (what the other ~89% of TIME must earn for the dip")
    print("strategy to match B&H total return):")
    yrs = 10.5
    for r in rows:
        gap = r["pnl_bh"] - r["pnl_dip"]          # log return given up
        idle_yrs = yrs * (1 - r["expo"])
        need_log = gap / idle_yrs                  # per-year log return required while parked
        bh_log_yr = r["pnl_bh"] / yrs
        print(f"  {r['ticker']}: gave up {gap*100:.0f}% log; parked {idle_yrs:.1f}y -> "
              f"needs {np.expm1(need_log)*100:.0f}%/yr elsewhere "
              f"(vs the asset's own {np.expm1(bh_log_yr)*100:.0f}%/yr)")


if __name__ == "__main__":
    main()
