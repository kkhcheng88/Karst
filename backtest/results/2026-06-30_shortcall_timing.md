# Result — short-call overlay timing (PMCC's only new leg vs LEAP)

**Date:** 2026-06-30  **Script:** `backtest/exp_shortcall.py`  **Tag:** ✅ verified
Insight (user): PMCC long leg == LEAP, so "PMCC" is not a separate tool. The only new thing is
the SHORT CALL leg, and the question is WHEN to sell it. Hypothesis: sell when underlying is high
(overbought). Short call 0.30D, 30 DTE (~21td), 50% PT, cost 1.5%/side.

## Results (per-trade quality is the differentiator; win% ~80-86% everywhere)
| gate | SPY Trades/PF/Avg | QQQ Trades/PF/Avg |
|---|---|---|
| unconditional | 652 / 1.53 / $99 | 563 / 1.30 / $84 |
| overbought RSI2>70 | 489 / 1.70 / $107 | 420 / 1.37 / $88 |
| overbought RSI2>90 | 317 / **2.26** / **$141** | 258 / 1.22 / $54 |
| high IV rank>50% | 217 / 1.26 / $71 | 190 / 1.30 / $91 |

## Conclusions
1. **Overbought timing works (user's hypothesis validated), esp. on SPY**: PF 1.53 → 1.70 → 2.26
   as overbought gets stricter. Sell the short call on a PEAK.
2. **Asset-dependent**: QQQ (momentum) — mild overbought (>70) helps slightly, but EXTREME (>90)
   BACKFIRES (PF 1.22) because momentum keeps ripping and the call gets run over. SPY (mean-reverts)
   → overbought reverts → call safe.
3. **High-IV timing does NOT help** (PF ≤ unconditional). The short call's edge is OVERBOUGHT
   (price/RSI-2), not IV.

## Symmetry (clean model)
- LEAP entry = RSI-2 **DIP** (buy the oversold trough).
- SHORT_CALL = RSI-2 **OVERBOUGHT** (sell the call on the peak), against a held long.
Both are RSI-2 mean-reversion, opposite ends. Encoded in scorecard v3.1 (PMCC dropped).
Caveat: momentum names — don't size the short call up at extreme overbought.
