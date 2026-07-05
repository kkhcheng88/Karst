"""Capital-efficiency lens (user's question): the negative Jensen alpha and the
relevered-CAGR figures both understate a real fact — measured PER UNIT OF EXPOSURE
(return on deployed capital), the fear/greed MR timing is EFFICIENT. Jensen alpha is a
RISK/beta-adjusted statement; the user asked for the CAPITAL-adjusted one (PnL% / exposure).
They answer different questions and can BOTH be true. This script shows all of them side by
side so the reconciliation is explicit, not hand-waved.

Metrics per rule (RSI2-alone and the combined round-trip), all 3 assets:
  - AvgExp                : fraction of days deployed (calculated, not assumed)
  - B&H CAGR / Sharpe     : the always-invested benchmark (exposure = 1.0 by construction)
  - strat calendar CAGR   : annualized over ALL days (the "unfair" number — penalizes being flat)
  - PnL/Exp  (arithmetic) : calendar CAGR / AvgExp  == the user's literal "10%/0.17" formula
  - deployed-cap annualized (geometric): (1+totalPnL)^(252/investedDays)-1 — the honest
                            "annualized rate WHILE your capital is actually working"
  - mean daily WHEN INVESTED vs B&H mean daily : does the timing deploy into ABOVE-average days?
  - Sharpe WHILE INVESTED vs B&H Sharpe : is the deployed capital also RISK-efficient, or is
                            the high per-time return just compensation for concentrated vol?
  - Jensen alpha / beta   : the risk-adjusted verdict (for cross-reference)

Gross while-invested returns (market return on deployed days, pre-cost) are used for the
capital-efficiency block — costs are 5bps x ~40-120 transitions over 15y, negligible to the
rate-while-deployed question; the net Jensen alpha column still carries full costs.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

import metrics  # noqa: E402
from exp_topdays_exposure import ASSETS, build_frame, load_fg, mkt_returns, strat_from_pos  # noqa: E402
from exp_mr_split_rules import combo_position, rsi2_position  # noqa: E402

TD = 252
RULES = [("rsi2 (in RSI2<10, out RSI2>90)", rsi2_position),
         ("combo (VIX/RSI2 in, RSI2/F&G out)", combo_position)]


def ann(compound_growth: float, n_days: int) -> float:
    if n_days <= 0 or compound_growth <= 0:
        return float("nan")
    return compound_growth ** (TD / n_days) - 1.0


def main():
    fg = load_fg()
    cache = {sym: build_frame(sym, fg) for sym in ASSETS}

    for sym in ASSETS:
        df = cache[sym]
        mkt = mkt_returns(df)
        n_all = len(mkt)
        bh_mean_d = float(np.mean(mkt))
        bh_sharpe = metrics.ann_sharpe(mkt)
        bh_cagr = metrics.cagr(np.cumprod(1.0 + mkt))
        print(f"\n### {sym}  ({df.index.min().date()}->{df.index.max().date()})")
        print(f"  B&H (exposure=1.0):  CAGR {bh_cagr*100:6.2f}%   Sharpe {bh_sharpe:.2f}   "
              f"mean-daily {bh_mean_d*100:.4f}%   ann-vol {np.std(mkt,ddof=1)*np.sqrt(TD)*100:.1f}%")

        for label, fn in RULES:
            pos = fn(df)
            strat, eq = strat_from_pos(mkt, pos, start=0.0)          # net of cost
            exp = float(np.mean(pos))
            inv = pos > 0
            n_inv = int(inv.sum())
            inv_d = mkt[inv]                                          # gross market ret on deployed days
            cal_cagr = metrics.cagr(eq)                              # calendar-annualized (net)
            total_pnl = float(eq[-1] - 1.0)                          # net total return
            # user's two ways to express "return per unit exposure":
            pnl_over_exp = cal_cagr / exp if exp else float("nan")   # arithmetic (the "10%/0.17")
            deployed_ann = ann(float(np.prod(1.0 + inv_d)), n_inv)   # geometric on deployed days (gross)
            # is the deployed capital picking above-average days, and is it risk-efficient?
            inv_mean_d = float(np.mean(inv_d))
            inv_sharpe = float(np.mean(inv_d) / np.std(inv_d, ddof=1) * np.sqrt(TD)) if n_inv > 2 else float("nan")
            inv_vol = float(np.std(inv_d, ddof=1) * np.sqrt(TD)) if n_inv > 2 else float("nan")
            a, b, ta = metrics.jensen_alpha(strat, mkt)

            print(f"  -- {label}")
            print(f"     AvgExp {exp*100:4.1f}%  ({n_inv}/{n_all} days) | "
                  f"calendar-CAGR {cal_cagr*100:6.2f}%  (looks weak: flat {(1-exp)*100:.0f}% of the time)")
            print(f"     RETURN PER UNIT EXPOSURE:  PnL/Exp(arith) {pnl_over_exp*100:6.2f}%   "
                  f"deployed-capital-annualized(geom) {deployed_ann*100:6.2f}%   vs  B&H {bh_cagr*100:.2f}%")
            print(f"     mean-daily WHEN INVESTED {inv_mean_d*100:.4f}%  vs  B&H {bh_mean_d*100:.4f}%   "
                  f"(ratio {inv_mean_d/bh_mean_d:4.2f}x  -> {'ABOVE' if inv_mean_d>bh_mean_d else 'below'}-average days)")
            print(f"     but RISK while invested:   ann-vol {inv_vol*100:4.1f}%  "
                  f"Sharpe-while-invested {inv_sharpe:4.2f}  vs  B&H Sharpe {bh_sharpe:.2f}   "
                  f"| Jensen alpha {a*100:5.2f}% (t {ta:.1f}), beta {b:.2f}")


if __name__ == "__main__":
    main()
