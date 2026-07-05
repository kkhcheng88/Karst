r"""Decompose Jensen alpha into (timing skill) + (structural drag), to answer the user's
point: "good timing -> positive alpha only makes sense for SPY if exposure is high enough,
or leveraged, or the traded instrument is not SPY itself."

EXACT identity for a long/flat strategy strat = pos * mkt (pos in [0,1], gross, no cost),
regressed on mkt (the SAME instrument it trades):

  alpha = mean(pos*mkt) - beta*mean(mkt)
        = [exposure*mean_mkt + Cov(pos,mkt)] - beta*mean_mkt
        = Cov(pos, mkt)                +  (exposure - beta) * mean_mkt
          \_______________/               \_______________________/
           T1 = TIMING SKILL               T2 = STRUCTURAL DRAG
           (does position anticipate        (you hold LESS than your beta implies, and
            the day's return? +ve = yes)      the market drifts UP while you sit flat)

  exposure = mean(pos);  beta = OLS slope;  mean_mkt = mean daily market return;
  Cov = population covariance. Identity is exact (verified numerically below).

Key: T2 < 0 whenever exposure < beta AND mean_mkt > 0 — i.e. a low-exposure buy-the-dip
timer on an up-drifting index. beta > exposure because the strategy concentrates into
high-VARIANCE fear days (their big |returns| dominate the OLS slope). So the drag is
STRUCTURAL to timing SPY-vs-SPY, not a property of the signal being bad.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

import metrics  # noqa: E402
from exp_topdays_exposure import ASSETS, build_frame, load_fg, mkt_returns  # noqa: E402
from exp_mr_split_rules import combo_position, rsi2_position  # noqa: E402

TD = 252
RULES = [("rsi2 (in RSI2<10, out RSI2>90)", rsi2_position),
         ("combo (VIX/RSI2 in, RSI2/F&G out)", combo_position)]


def main():
    fg = load_fg()
    cache = {sym: build_frame(sym, fg) for sym in ASSETS}
    print("Alpha (gross, no cost) = T1 timing-skill  +  T2 structural-drag   [annualized %]")
    for sym in ASSETS:
        df = cache[sym]
        mkt = mkt_returns(df)
        mean_mkt = float(np.mean(mkt))
        print(f"\n### {sym}   mean-daily-mkt {mean_mkt*100:.4f}%  (annual drift {mean_mkt*TD*100:.1f}%)")
        for label, fn in RULES:
            pos = fn(df)
            gross = pos * mkt                                    # no cost, pure timing
            a, beta, ta = metrics.jensen_alpha(gross, mkt)      # gross alpha & beta
            exposure = float(np.mean(pos))
            cov = float(np.mean(pos * mkt) - np.mean(pos) * mean_mkt)   # population Cov(pos,mkt)
            t1 = cov * TD                                        # timing skill, annualized
            t2 = (exposure - beta) * mean_mkt * TD               # structural drag, annualized
            # exposure that would zero the drag (T2=0): exposure == beta
            need_lev = beta / exposure if exposure else float("nan")
            print(f"  -- {label}")
            print(f"     exposure {exposure*100:4.1f}%   beta {beta:4.2f}   "
                  f"(beta/exposure = {need_lev:4.2f}x  <- variance-concentration into fear days)")
            print(f"     T1 timing-skill  = {t1*100:+6.2f}%/yr   <- position DOES anticipate good days"
                  if t1 > 0 else
                  f"     T1 timing-skill  = {t1*100:+6.2f}%/yr   <- position does NOT anticipate good days")
            print(f"     T2 structural-drag = {t2*100:+6.2f}%/yr   <- hold {exposure*100:.0f}% but carry "
                  f"beta {beta:.2f}, market drifts up while flat")
            print(f"     -> gross alpha = {a*100:+6.2f}%/yr   (T1+T2 check = {(t1+t2)*100:+6.2f}%)")


if __name__ == "__main__":
    main()
