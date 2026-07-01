"""Valuation, BROAD universe — is the PE U-shape universal or a tech-giant artifact?

The first study (exp_valuation.py) used 18 hand-picked, tech-heavy names -> the "expensive
wins" (Q4) result was likely survivorship/growth bias. Here we take a broad, NOT-hand-picked,
sector-diversified universe = the top-10 US holdings of all 11 SPDR sector ETFs (~90 names),
and break the value signal down BY SECTOR. That directly answers: does buying cheap (own-PE-
history) work everywhere, or only in some sectors (mature/cyclical) and fail in growth (tech)?

PE = defeatbeta ttm_pe (long daily history). Percentile via fast rolling rank (trailing 3y).

Run: python backtest/exp_valuation_broad.py
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
import yfinance as yf

WIN, MINP, FWD = 756, 252, 126
SECTORS = {"XLK": "Tech", "XLC": "Comm", "XLY": "Discr", "XLI": "Indus", "XLF": "Fin",
           "XLB": "Materl", "XLE": "Energy", "XLV": "Health", "XLP": "Staples",
           "XLU": "Util", "XLRE": "RealEst"}


def build_universe():
    """sym -> sector, from top-10 US holdings of each SPDR sector ETF."""
    uni = {}
    for etf, name in SECTORS.items():
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                th = yf.Ticker(etf).funds_data.top_holdings
            for sym in th.index:
                s = str(sym)
                if "." not in s and s not in uni:   # US-listed, first sector wins
                    uni[s] = name
        except Exception:
            continue
    return uni


def pe_pctile_fwd(sym):
    with contextlib.redirect_stdout(io.StringIO()):
        df = Ticker(sym).ttm_pe()
    df = df[["report_date", "close_price", "ttm_pe"]].copy()
    df["date"] = pd.to_datetime(df["report_date"])
    df = df.set_index("date").sort_index()
    pe = df["ttm_pe"].where(df["ttm_pe"] > 0)
    pct = pe.rolling(WIN, min_periods=MINP).rank(pct=True)
    fwd = df["close_price"].shift(-FWD) / df["close_price"] - 1.0
    return pct, fwd, len(df)


def run():
    uni = build_universe()
    print(f"universe = {len(uni)} US names across {len(SECTORS)} SPDR sectors\n")

    by_sec = {s: {"spreads": [], "q": {i: [] for i in range(5)}, "names": 0} for s in SECTORS.values()}
    allq = {i: [] for i in range(5)}
    n_ok = pos_all = 0

    for sym, sec in uni.items():
        try:
            pct, fwd, n = pe_pctile_fwd(sym)
        except Exception:
            continue
        if n < WIN + FWD:
            continue
        cheap = fwd[pct < 0.20].mean()
        exp = fwd[pct > 0.80].mean()
        if cheap == cheap and exp == exp:
            sp = cheap - exp
            by_sec[sec]["spreads"].append(sp)
            pos_all += sp > 0
            n_ok += 1
        by_sec[sec]["names"] += 1
        for i in range(5):
            m = (pct >= i * 0.2) & (pct < (i + 1) * 0.2)
            vals = fwd[m].dropna().tolist()
            by_sec[sec]["q"][i].extend(vals)
            allq[i].extend(vals)

    print("BY SECTOR -- mean(cheap-minus-expensive fwd-126d spread) + quintile fwd returns")
    print(f"{'sector':9}{'names':>6}{'spread':>8}{'%pos':>6} | {'Q0':>6}{'Q1':>6}{'Q2':>6}{'Q3':>6}{'Q4':>6}  shape")
    print("-" * 74)
    for sec in SECTORS.values():
        d = by_sec[sec]
        sp = d["spreads"]
        if not sp:
            continue
        avg = np.mean(sp)
        pospct = np.mean([x > 0 for x in sp]) * 100
        qm = [np.mean(d["q"][i]) * 100 if d["q"][i] else np.nan for i in range(5)]
        # shape: does cheap (Q0) beat pricey (Q4)?  and is it monotone-down (value) or U/growth?
        shape = "VALUE" if qm[0] > qm[4] + 1 else "GROWTH" if qm[4] > qm[0] + 1 else "flat"
        print(f"{sec:9}{len(sp):>6}{avg*100:>7.1f}%{pospct:>5.0f}% | "
              f"{qm[0]:>6.1f}{qm[1]:>6.1f}{qm[2]:>6.1f}{qm[3]:>6.1f}{qm[4]:>6.1f}  {shape}")

    print("-" * 74)
    qall = [np.mean(allq[i]) * 100 for i in range(5)]
    print(f"{'ALL':9}{n_ok:>6}{'':>8}{pos_all/max(n_ok,1)*100:>5.0f}% | "
          f"{qall[0]:>6.1f}{qall[1]:>6.1f}{qall[2]:>6.1f}{qall[3]:>6.1f}{qall[4]:>6.1f}")
    print(f"\n  {pos_all}/{n_ok} names overall: cheap beats expensive (fwd-{FWD}d).")
    print("  Q0=cheapest .. Q4=priciest quintile, mean fwd-126d return %.")
    print("  VALUE shape (Q0>Q4) = buying cheap works; GROWTH shape (Q4>Q0) = pricey keeps winning.")
    print("  Read per sector: is the value tilt real in mature/cyclical sectors and a trap in growth?")


if __name__ == "__main__":
    run()
