"""Follow-up to exp_topdays_exposure.py — exposure-level ROBUSTNESS sweep.

User's methodological correction: B&H exposure = 1.0 by construction (buy Jan-1, hold to
Dec-31, always fully invested — trivial). A genuine TACTICAL/timing strategy's annualized
average exposure should be well below 1.0, not the ~0.97-1.0 that `exp_topdays_exposure.py`'s
"lev"/"nolev" variants landed on (those are really B&H-plus-a-small-overlay, not a timing
strategy — relevering them is close to a no-op, as that script's own caveats flagged).
That script's "mr" flat-baseline variant DID sit well below 1.0 (avg exposure ~0.14) — but
that's one point, and hand-picking thresholds to hit a specific target (e.g. finding #8's
implied beta~0.7) risks curve-fitting to a number from an unreplicated run.

So: sweep a HOLD-PERIOD knob instead of guessing thresholds. Same FEAR entry signal
(VIX>30 or RSI2(2)<10 & VIX>25) as before; on trigger, hold long for exactly N trading
days (re-triggers while holding extend the hold), then exit. N sweeps average exposure
smoothly from ~0.1 (N=5) up toward ~0.6-0.7 (N=63) without touching the entry logic —
apples-to-apples across the sweep. For each N: raw Jensen alpha (actual exposure) vs
RELEVERED alpha (same signal, position scaled by 1/avg_exposure to match B&H's exposure=1).
Answers: does "relevering doesn't rescue alpha" hold at every exposure level tested in
exp_topdays_exposure.py, or was it an artifact of the one very-low-exposure (~0.14) point?
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

import metrics  # noqa: E402
from exp_topdays_exposure import ASSETS, build_frame, load_fg, mkt_returns, relever, strat_from_pos  # noqa: E402

HOLD_DAYS = [5, 10, 21, 42, 63]


def mr_fixed_hold_position(df, hold_days: int) -> np.ndarray:
    """FEAR-triggered entry, fixed N-day hold (re-triggers extend the hold). i-1 -> i."""
    fear = ((df["vix"] > 30) | ((df["rsi2"] < 10) & (df["vix"] > 25))).values
    n = len(df)
    pos = np.zeros(n)
    remaining = 0
    for i in range(1, n):
        if fear[i - 1]:
            remaining = hold_days
        pos[i] = 1.0 if remaining > 0 else 0.0
        if remaining > 0:
            remaining -= 1
    return pos


def main():
    fg = load_fg()
    cache = {sym: build_frame(sym, fg) for sym in ASSETS}

    trials = []
    for sym in ASSETS:
        df = cache[sym]
        mkt_ret = mkt_returns(df)
        for hold in HOLD_DAYS:
            pos = mr_fixed_hold_position(df, hold)
            strat, _ = strat_from_pos(mkt_ret, pos, start=0.0)
            trials.append(metrics.ann_sharpe(strat))

    for sym in ASSETS:
        df = cache[sym]
        mkt_ret = mkt_returns(df)
        bh_eq = np.cumprod(1.0 + mkt_ret)
        bh = metrics.summary(mkt_ret, bh_eq)
        print(f"\n### {sym}  ({df.index.min().date()}->{df.index.max().date()})  "
              f"B&H(exposure=1.0 by construction) CAGR {bh['CAGR']*100:.2f}%  "
              f"Sharpe {bh['Sharpe']:.2f}  MaxDD {bh['MaxDD']*100:.1f}%")
        print("  hold  AvgExp | raw: CAGR   Alpha    aT  Sharpe  MaxDD | "
              "relevered-to-1.0x: CAGR    Alpha    aT  Sharpe   MaxDD")
        for hold in HOLD_DAYS:
            pos = mr_fixed_hold_position(df, hold)
            strat, eq = strat_from_pos(mkt_ret, pos, start=0.0)
            a, b, ta = metrics.jensen_alpha(strat, mkt_ret)
            sm = metrics.summary(strat, eq, pos)
            pos_r, strat_r, eq_r = relever(pos, mkt_ret)
            ar, br, tar = metrics.jensen_alpha(strat_r, mkt_ret)
            smr = metrics.summary(strat_r, eq_r, pos_r)
            dsr = metrics.deflated_sharpe_ratio(strat, trials)
            print(f"  {hold:3d}d {sm['Exposure']:5.2f}  | {sm['CAGR']*100:6.2f}% {a*100:6.2f}% "
                  f"{ta:5.1f} {sm['Sharpe']:6.2f} {sm['MaxDD']*100:6.1f}% | "
                  f"{smr['CAGR']*100:7.2f}% {ar*100:7.2f}% {tar:5.1f} {smr['Sharpe']:6.2f} "
                  f"{smr['MaxDD']*100:7.1f}%   DSR={dsr*100:3.0f}%")


if __name__ == "__main__":
    main()
