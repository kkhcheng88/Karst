"""Experiment: does the fear/greed exposure overlay (HANDOFF finding #8) miss the
market's best days, and does alpha survive once you correct for average exposure?

Two questions from the user, both empirical:
  1. "Miss the top-10 days, miss the year" — does the overlay actually sit OUT on the
     market's best single days, or does it catch them (fear/crash rallies cluster with
     high-VIX days, which is exactly when this overlay is OVERWEIGHT)?
  2. The capstone found Jensen alpha ~= 0 with avg exposure (beta) ~= 0.7 (finding #8).
     Is that "no skill", or is a real per-dollar-invested edge being diluted by running
     under full exposure? Test by RELEVERING the same signal to avg exposure = 1.0 (same
     average market exposure as B&H) and re-measuring alpha, Sharpe, CAGR, MaxDD.

Strategy reconstruction (the capstone run was inline/unsaved — this is a transparent,
documented rebuild from the findings, NOT a byte-exact replay):
  baseline exposure = 1.0 (long-only, always-invested by default)
  FEAR   (finding #5): VIX>30  OR  (RSI2(2)<10 AND VIX>25)   -> overweight
  GREED  (finding #6/#7): CNN Fear&Greed > 80                -> de-risk (trim, not exit —
         F&G's own literature calls this "froth", not "get out")
  variant "lev"    : fear -> 1.3x exposure   (tests open item #1: leveraged fearful dips)
  variant "nolev"  : fear -> 1.0x exposure   (pure de-risk overlay, no leverage assumed)
  both variants    : greed -> 0.5x exposure; else -> 1.0x
A THIRD variant, "mr" (flat-baseline MR-timing), is added because "lev"/"nolev" above
are B&H-plus-overlay (baseline=1.0, so avg exposure stays ~1.0) — that makes relevering
a weak test of Q2 (dividing by ~1 barely moves anything). "mr" starts FLAT (0 exposure)
and only enters on fear, exiting when VIX<20 or F&G>55 — this is closer to what
finding #8's "avg exposure/beta ~= 0.7" implies and gives relevering something real to
correct for.
Signals decided on bar i-1 act on bar i (look-ahead-safe, matches engine.py convention).
Cost: 5bps per unit of exposure changed (round-trip ~= 2x one-way), matching the
capstone's cost assumption (HANDOFF: "5bps/side").

Data: F&G = real CNN history 2011-2026 (github whit3rabbit/fear-greed-data), downloaded
to reference/fear_greed/fear-greed.csv (gitignored, regenerable). Sample = intersection
of F&G availability x adjusted price history.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import metrics  # noqa: E402
from data import load  # noqa: E402
from signals import rsi  # noqa: E402

ASSETS = ["SPY", "QQQ", "SPMO"]
COST_BPS = 5.0
FG_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                       "reference", "fear_greed", "fear-greed.csv")
TOP_N = 10


def load_fg() -> pd.Series:
    df = pd.read_csv(FG_CSV, parse_dates=["Date"]).set_index("Date").sort_index()
    return df["Fear Greed"].rename("fg")


def build_frame(sym: str, fg: pd.Series) -> pd.DataFrame:
    close = load(sym, adjusted=True)["close"]
    vix = load("^VIX")["close"].rename("vix")
    r2 = rsi(close, 2).rename("rsi2")
    df = pd.concat([close.rename("close"), vix, r2, fg], axis=1)
    df["fg"] = df["fg"].ffill(limit=5)
    df = df.dropna()
    # clip to F&G's actual coverage window (avoid ffill bleeding before/after real data)
    df = df.loc[fg.index.min():fg.index.max()]
    return df


def exposure_series(df: pd.DataFrame, fear_mult: float) -> np.ndarray:
    """Exposure decided on bar i-1, applied on bar i (shift(1) below)."""
    fear = (df["vix"] > 30) | ((df["rsi2"] < 10) & (df["vix"] > 25))
    greed = df["fg"] > 80
    exp_signal = pd.Series(1.0, index=df.index)
    exp_signal[greed] = 0.5
    exp_signal[fear] = fear_mult          # fear overrides greed (rare overlap anyway)
    return exp_signal.shift(1).fillna(1.0).values


def mr_timing_position(df: pd.DataFrame) -> np.ndarray:
    """Flat-baseline: 0 by default, ON while fear-triggered, OFF once VIX calms or F&G
    exits fear/neutral. Matches engine.py's stateful entry/exit convention.
    """
    fear = ((df["vix"] > 30) | ((df["rsi2"] < 10) & (df["vix"] > 25))).values
    calm = ((df["vix"] < 20) | (df["fg"] > 55)).values
    n = len(df)
    pos = np.zeros(n)
    in_mkt = False
    for i in range(1, n):
        if not in_mkt and fear[i - 1]:
            in_mkt = True
        elif in_mkt and calm[i - 1]:
            in_mkt = False
        pos[i] = 1.0 if in_mkt else 0.0
    return pos


def mkt_returns(df: pd.DataFrame) -> np.ndarray:
    close = df["close"].values
    mkt_ret = np.zeros(len(close))
    mkt_ret[1:] = close[1:] / close[:-1] - 1.0
    return mkt_ret


def strat_from_pos(mkt_ret: np.ndarray, pos: np.ndarray, start: float = 1.0):
    turn = np.abs(np.diff(np.concatenate([[start], pos])))
    strat = pos * mkt_ret - turn * (COST_BPS / 1e4)
    equity = np.cumprod(1.0 + strat)
    return strat, equity


def run_variant(df: pd.DataFrame, fear_mult: float):
    mkt_ret = mkt_returns(df)
    pos = exposure_series(df, fear_mult)
    strat, equity = strat_from_pos(mkt_ret, pos, start=1.0)
    return pos, mkt_ret, strat, equity


def run_mr_variant(df: pd.DataFrame):
    mkt_ret = mkt_returns(df)
    pos = mr_timing_position(df)
    strat, equity = strat_from_pos(mkt_ret, pos, start=0.0)
    return pos, mkt_ret, strat, equity


def relever(pos: np.ndarray, mkt_ret: np.ndarray):
    """Scale the SAME signal to avg exposure == 1.0 (match B&H's average market exposure).
    Answers: is alpha ~0 because of no skill, or because running under-exposed dilutes it?
    """
    avg_exp = pos.mean()
    if avg_exp <= 0:
        return pos, np.zeros_like(mkt_ret), np.ones_like(mkt_ret)
    pos_r = pos / avg_exp
    turn = np.abs(np.diff(np.concatenate([[1.0], pos_r])))
    strat = pos_r * mkt_ret - turn * (COST_BPS / 1e4)
    equity = np.cumprod(1.0 + strat)
    return pos_r, strat, equity


def top_days_report(sym: str, df: pd.DataFrame, pos_lev: np.ndarray, pos_nolev: np.ndarray,
                    pos_mr: np.ndarray):
    close = df["close"]
    ret = close.pct_change()
    idx = df.index
    valid = np.flatnonzero(~np.isnan(ret.values))
    rank = sorted(valid, key=lambda i: -ret.values[i])[:TOP_N]
    print(f"\n  Top {TOP_N} single-day return dates ({idx.min().date()}->{idx.max().date()}):")
    print("   date        ret    VIX   RSI2   F&G  | exp(lev) exp(nolev) exp(mr)")
    cap_lev = cap_nolev = cap_mr = cap_bh = 0.0
    for i in rank:
        d = idx[i]
        r = ret.values[i]
        cap_bh += r
        cap_lev += pos_lev[i] * r
        cap_nolev += pos_nolev[i] * r
        cap_mr += pos_mr[i] * r
        print(f"   {d.date()}  {r*100:5.1f}% {df['vix'].values[i]:5.1f} "
              f"{df['rsi2'].values[i]:5.1f} {df['fg'].values[i]:5.1f} | "
              f"{pos_lev[i]:6.2f}x   {pos_nolev[i]:6.2f}x   {pos_mr[i]:4.1f}x")
    print(f"  sum of top-{TOP_N} day returns: B&H(1.0x)={cap_bh*100:5.1f}%  "
          f"lev-overlay captured={cap_lev*100:5.1f}% ({cap_lev/cap_bh*100:.0f}% of B&H)  "
          f"nolev-overlay captured={cap_nolev*100:5.1f}% ({cap_nolev/cap_bh*100:.0f}% of B&H)  "
          f"mr-timing captured={cap_mr*100:5.1f}% ({cap_mr/cap_bh*100:.0f}% of B&H)")
    # classic "miss the top N days" reference stat: zero exposure on those N days only
    ret_missed = ret.values.copy()
    ret_missed[rank] = 0.0
    eq_bh = np.cumprod(1.0 + np.nan_to_num(ret.values))
    eq_missed = np.cumprod(1.0 + np.nan_to_num(ret_missed))
    print(f"  reference: B&H total return {(eq_bh[-1]-1)*100:5.1f}%  vs  "
          f"B&H-minus-top-{TOP_N}-days {(eq_missed[-1]-1)*100:5.1f}%  "
          f"(classic 'miss the top days' cost)")


def main():
    fg = load_fg()
    print(f"F&G coverage: {fg.index.min().date()} -> {fg.index.max().date()} ({len(fg)} rows)")
    trials = []
    cache = {}
    for sym in ASSETS:
        df = build_frame(sym, fg)
        cache[sym] = df
        for mult in (1.3, 1.0):
            pos, mkt, strat, eq = run_variant(df, mult)
            trials.append(metrics.ann_sharpe(strat))
        _, _, strat_mr, _ = run_mr_variant(df)
        trials.append(metrics.ann_sharpe(strat_mr))

    for sym in ASSETS:
        df = cache[sym]
        mkt_ret = mkt_returns(df)
        bh_eq = np.cumprod(1.0 + mkt_ret)
        bh = metrics.summary(mkt_ret, bh_eq)
        print(f"\n### {sym}  ({df.index.min().date()}->{df.index.max().date()}, {len(df)} days)  "
              f"B&H CAGR {bh['CAGR']*100:.2f}%  Sharpe {bh['Sharpe']:.2f}  MaxDD {bh['MaxDD']*100:.1f}%")

        print("  --- Q2: alpha vs exposure -----------------------------------------------")
        print("  variant        AvgExp | CAGR   Alpha    aT   Sharpe | MaxDD  | (relevered to AvgExp=1.0:) "
              "CAGR   Alpha    aT   Sharpe  MaxDD")
        rows = {}
        variants = [("lev(1.3x fear)", lambda: run_variant(df, 1.3)),
                    ("nolev(1.0x fear)", lambda: run_variant(df, 1.0)),
                    ("mr(flat-baseline)", lambda: run_mr_variant(df))]
        for label, fn in variants:
            pos, mkt, strat, eq = fn()
            rows[label] = pos
            a, b, ta = metrics.jensen_alpha(strat, mkt_ret)
            sm = metrics.summary(strat, eq, pos)
            pos_r, strat_r, eq_r = relever(pos, mkt_ret)
            ar, br, tar = metrics.jensen_alpha(strat_r, mkt_ret)
            smr = metrics.summary(strat_r, eq_r, pos_r)
            dsr = metrics.deflated_sharpe_ratio(strat, trials)
            print(f"  {label:18} {sm['Exposure']:5.2f}  | {sm['CAGR']*100:5.2f}% {a*100:6.2f}% "
                  f"{ta:5.1f} {sm['Sharpe']:6.2f} | {sm['MaxDD']*100:5.1f}% | "
                  f"{smr['CAGR']*100:5.2f}% {ar*100:6.2f}% {tar:5.1f} {smr['Sharpe']:6.2f} "
                  f"{smr['MaxDD']*100:5.1f}%   DSR={dsr*100:3.0f}%")
            naive = a / sm["Exposure"] if sm["Exposure"] else float("nan")
            print(f"     naive alpha/avgExposure heuristic: {naive*100:5.2f}%  "
                  f"(vs relevered-actual alpha {ar*100:5.2f}% above)")

        print("  --- Q1: top-day coverage --------------------------------------------------")
        top_days_report(sym, df, rows["lev(1.3x fear)"], rows["nolev(1.0x fear)"],
                        rows["mr(flat-baseline)"])


if __name__ == "__main__":
    main()
