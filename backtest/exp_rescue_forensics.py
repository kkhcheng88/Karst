"""Are the big sector explosions OVERSOLD-in-FEAR rescue bounces? (user's hypothesis)

Hypothesis: the biggest single-week sector gaps vs SPY are systemically-important sectors that were
BEATEN DOWN (worst), exploding during EXTREME FEAR when policy/government must step in (GFC banks
too-big-to-fail; COVID -> healthcare/reopening). So: extreme fear + worst sector -> rescue bounce.

Test (last ~10y, INCLUDING tech): for the top-20 weeks by best-sector gap vs SPY, report the
exploding sector's state GOING IN (trailing-4w return + its rank among sectors, 1=worst) and the
market fear (VIX level at t-1, SPY trailing-4w). Then see how many fit "fear + oversold rescue"
vs "momentum on an already-strong sector" (e.g. energy supply shocks).

11 SPDR sectors + SPY + VIX, weekly.
Run: python backtest/exp_rescue_forensics.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import load

SECTORS = ["XLK", "XLC", "XLY", "XLI", "XLF", "XLB", "XLE", "XLV", "XLP", "XLU", "XLRE"]
WEEKS_10Y = 520


def run():
    cols = {s: load(s, adjusted=True)["close"].resample("W-FRI").last() for s in SECTORS}
    cols["SPY"] = load("SPY", adjusted=True)["close"].resample("W-FRI").last()
    px = pd.DataFrame(cols).dropna()
    vix = load("^VIX", min_rows=50)["close"].resample("W-FRI").last().reindex(px.index)
    px = px.iloc[-WEEKS_10Y:]
    vix = vix.iloc[-WEEKS_10Y:]
    R = px.pct_change()
    sec = R[SECTORS].to_numpy()
    spy = R["SPY"].to_numpy()
    idx = px.index
    n, k = sec.shape

    win = sec.argmax(1)
    gap = sec[np.arange(n), win] - spy
    # trailing 4w return per sector, as of t-1 (uses weeks t-4..t-1)
    P = px[SECTORS].to_numpy()
    tr4 = np.full((n, k), np.nan)
    tr4[5:] = P[4:-1] / P[:-5] - 1.0                        # return over the 4 weeks ending at t-1
    spy_tr4 = np.full(n, np.nan)
    Ps = px["SPY"].to_numpy()
    spy_tr4[5:] = Ps[4:-1] / Ps[:-5] - 1.0
    vix_in = np.full(n, np.nan)
    vix_in[1:] = vix.to_numpy()[:-1]                        # VIX at t-1

    order = np.argsort(-gap)
    top = [t for t in order if not np.isnan(tr4[t, win[t]])][:20]

    print(f"\n=== top-20 sector explosions (last ~10y), oversold-in-fear? -- {idx[0].date()}->{idx[-1].date()} ===")
    print(f"{'week':12}{'sector':7}{'ret%':>6}{'gap%':>6}{'priorTR4%':>10}{'rank':>5}{'VIXin':>7}{'SPYtr4%':>8}")
    fear_oversold = 0
    for t in top:
        j = win[t]
        rank = int((tr4[t] < tr4[t, j]).sum()) + 1          # 1 = worst prior 4w among sectors
        is_fear = vix_in[t] >= 25
        is_oversold = rank <= 4
        if is_fear and is_oversold:
            fear_oversold += 1
        tag = " <FEAR+OVERSOLD" if (is_fear and is_oversold) else (" <fear" if is_fear else " <momentum" if tr4[t, j] > 0 else "")
        print(f"{str(idx[t].date()):12}{SECTORS[j]:7}{sec[t,j]*100:5.0f}{gap[t]*100:6.0f}"
              f"{tr4[t,j]*100:9.0f}{rank:5d}{vix_in[t]:7.0f}{spy_tr4[t]*100:7.0f}{tag}")

    print(f"\n  fit 'FEAR (VIX>=25 going in) + OVERSOLD (sector in bottom-4 prior-4w)': {fear_oversold}/20")
    print("  Read: if the rescue-bounce weeks (GFC/COVID) show worst-sector + high-VIX, the pattern")
    print("  is 'buy the beaten systemic sector in extreme fear -> policy rescue'. Energy supply-shock")
    print("  weeks should instead show momentum (sector already strong, low fear) -- a different type.")


if __name__ == "__main__":
    run()
