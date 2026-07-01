"""Phase-3 prelude — does VALUATION have a return edge? ("is it priced in?")

Everything in Karst so far is price/momentum/regime -- ZERO valuation. Valuation
mean-reversion (the value premium) has real academic support, unlike the short-term price
mean-reversion that kept testing out as risk-control-only. So we MEASURE it (same discipline
as 2b): does buying a stock when it's CHEAP vs its OWN PE history beat buy-and-hold?

Metric: defeatbeta ttm_pe -- the one valuation series with long DAILY history (back to the
90s). PE percentile vs trailing 3y (own history). PS/EV-EBITDA/ROIC exist but only ~2022+,
too short for a multi-regime backtest.

Universe: large caps across sectors, deliberately MIXING secular winners and laggards
(INTC/DIS/T/XOM/CSCO) to fight survivorship bias.

Tests:
  1) forward-126d return in CHEAP (pctile<20) vs EXPENSIVE (pctile>80) periods, per name +
     aggregate spread -> is there a value signal at all?
  2) tradeable CHEAP strategy (long when pctile<40, exit >60) vs B&H, + a value+trend variant,
     deflated Sharpe over all trials, IS/OOS.

Run: python backtest/exp_valuation.py
"""
from __future__ import annotations

import contextlib
import io
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

with contextlib.redirect_stdout(io.StringIO()):
    from defeatbeta_api.data.ticker import Ticker

from engine import backtest, buy_hold
from metrics import ann_sharpe, cagr, deflated_sharpe_ratio, max_drawdown
from signals import sma

UNIVERSE = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META",   # growth winners
            "INTC", "CSCO", "DIS", "T",                          # laggards (anti-survivorship)
            "JPM", "JNJ", "LLY", "XOM", "WMT", "PG", "KO", "HD"]  # sector leaders / cyclicals
WIN, MINP, FWD = 756, 252, 126
COST_BPS = 2.0


def pe_frame(sym):
    with contextlib.redirect_stdout(io.StringIO()):
        df = Ticker(sym).ttm_pe()
    df = df[["report_date", "close_price", "ttm_pe"]].copy()
    df["date"] = pd.to_datetime(df["report_date"])
    df = df.set_index("date").sort_index()
    df = df.rename(columns={"close_price": "close", "ttm_pe": "pe"})
    df.loc[df["pe"] <= 0, "pe"] = np.nan   # negative PE = no earnings, not "cheap"
    return df[["close", "pe"]]


def roll_pctile(s):
    return s.rolling(WIN, min_periods=MINP).apply(lambda x: float((x <= x[-1]).mean()), raw=True)


def run():
    rows, trials = [], []
    pooled = {q: [] for q in range(5)}   # pooled fwd-return by PE quintile

    for sym in UNIVERSE:
        try:
            d = pe_frame(sym)
        except Exception as e:
            print(f"{sym:5} SKIP {str(e)[:40]}")
            continue
        if len(d) < WIN + FWD:
            print(f"{sym:5} SKIP short ({len(d)})")
            continue
        close = d["close"]
        pct = roll_pctile(d["pe"])
        fwd = close.shift(-FWD) / close - 1.0

        # Test 1: cheap vs expensive forward return
        cheap = fwd[(pct < 0.20)].mean()
        exp = fwd[(pct > 0.80)].mean()
        spread = cheap - exp
        for q in range(5):
            m = (pct >= q * 0.2) & (pct < (q + 1) * 0.2)
            pooled[q].extend(fwd[m].dropna().tolist())

        # Test 2: tradeable CHEAP (long pctile<40, exit >60) and value+trend
        c = close.to_numpy()
        s200 = sma(close, 200).to_numpy()
        p = pct.to_numpy()
        en_val = p < 0.40
        ex_val = p > 0.60
        en_vt = (p < 0.40) & (c > s200)
        ex_vt = (p > 0.60) | (c < s200)

        bh_ret, bh_eq = buy_hold(c)
        bh = {"CAGR": cagr(bh_eq), "Sharpe": ann_sharpe(bh_ret), "MaxDD": max_drawdown(bh_eq)}
        out = {}
        for k, (en, ex) in {"VAL": (en_val, ex_val), "VAL+TREND": (en_vt, ex_vt)}.items():
            en = np.nan_to_num(en, nan=0).astype(bool)
            ex = np.nan_to_num(ex, nan=0).astype(bool)
            pos, strat, equity = backtest(c, en, ex, cost_bps=COST_BPS)
            out[k] = {"CAGR": cagr(equity), "Sharpe": ann_sharpe(strat), "MaxDD": max_drawdown(equity),
                      "Exp": float(pos.mean()), "Trades": int(np.sum(np.diff(pos) > 0)), "strat": strat}
            trials.append(out[k]["Sharpe"])

        rows.append({"sym": sym, "n": len(d), "start": str(d.index[0].date()),
                     "cheap": cheap, "exp": exp, "spread": spread, "bh": bh, "out": out})

    # ---- report ----
    print(f"\n=== VALUATION (own-history PE percentile, fwd={FWD}d, cost {COST_BPS}bp) ===\n")
    print("TEST 1 -- forward-126d return: CHEAP (PE pctile<20) vs EXPENSIVE (>80), per name")
    print(f"{'sym':6}{'cheap%':>8}{'exp%':>8}{'spread':>8}   (positive spread = value works)")
    for r in sorted(rows, key=lambda r: -r["spread"]):
        print(f"{r['sym']:6}{r['cheap']*100:7.1f}%{r['exp']*100:7.1f}%{r['spread']*100:7.1f}%")
    pos_spread = sum(1 for r in rows if r["spread"] > 0)
    print(f"\n  {pos_spread}/{len(rows)} names: cheap beats expensive on fwd-{FWD}d return")
    print("  pooled fwd-126d return by PE quintile (Q0=cheapest .. Q4=priciest):")
    for q in range(5):
        arr = np.array(pooled[q])
        print(f"    Q{q} (pctile {q*20}-{(q+1)*20}): mean {np.mean(arr)*100:5.1f}%  median {np.median(arr)*100:5.1f}%  n={len(arr)}")

    print("\nTEST 2 -- tradeable CHEAP strategy vs B&H (Sharpe / CAGR), + deflated SR")
    print(f"{'sym':6}| {'VAL_Sh':>7}{'VT_Sh':>7}{'BH_Sh':>6} | {'VAL_CAGR':>9}{'VT_CAGR':>9}{'BH_CAGR':>9} | {'>BH':>4}{'DSR':>6}")
    n_beat = 0
    for r in rows:
        o, bh = r["out"], r["bh"]
        best = max(o, key=lambda k: o[k]["Sharpe"] if o[k]["Sharpe"] == o[k]["Sharpe"] else -9)
        beat = o[best]["Sharpe"] > bh["Sharpe"]
        n_beat += beat
        dsr = deflated_sharpe_ratio(o[best]["strat"], trials)
        print(f"{r['sym']:6}| {o['VAL']['Sharpe']:7.2f}{o['VAL+TREND']['Sharpe']:7.2f}{bh['Sharpe']:6.2f} | "
              f"{o['VAL']['CAGR']*100:8.1f}%{o['VAL+TREND']['CAGR']*100:8.1f}%{bh['CAGR']*100:8.1f}% | "
              f"{'Y' if beat else 'n':>4}{dsr:6.2f}")
    print(f"\n  {n_beat}/{len(rows)} names: best value-strategy beats B&H on Sharpe")
    print("  Read: value 'works' if cheap>expensive fwd-return (Test 1, robust across names) AND "
          "a tradeable variant beats B&H net of cost surviving DSR (Test 2). Caveats: survivorship "
          "(large-cap survivors), PE distorted by cyclical/peak earnings (value trap), raw (not total-return) close.")


if __name__ == "__main__":
    run()
