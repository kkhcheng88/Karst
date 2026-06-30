# Result — Scorecard validation (does the score reach both ends + predict?)

**Date:** 2026-06-30  **Script:** `backtest/exp_scorecard_validation.py`  **Tag:** ✅ verified
Method: bucket each day by a tool's score, measure realized forward 21d underlying
return + drawdown (OHLCV only — no provisional option magnitudes). Full history.

## 1. Range / calibration — scores DON'T cleanly reach both ends
- LEAP max ~88–91, p99 78–79, top bin sparse (198–245 days).
- PMCC barely reaches high (p99 64; 75-100 bin = 18–23 days = noise).
- Only CSP / CASH reach high scores. → 0–100 scale poorly calibrated; per-tool ranges differ.

## 2. Predictive power (SPY / QQQ, fwd 21d)
| Tool | high score → fwd RETURN | high score → fwd DRAWDOWN |
|---|---|---|
| LEAP | ❌ non-monotonic / worse at top (QQQ 75-100 +0.37%) | ✅ smaller (4.2%→1.7%) |
| PMCC | ❌ high bins negative (−1.1/−0.7%), small sample | ❌ larger |
| CSP | ~flat | ✅✅ monotonic smaller (SPY 4.6→2.2%, QQQ 5.7→2.1%) |
| CASH | + (post-drop bounce) | ✅ larger (flags fragility) |

## 3. Conclusions
1. **Scores DO NOT predict return.** LEAP/PMCC high scores mean-revert (extended uptrend →
   pullback). Weighting ADX/extension as a *return* signal is backwards — those factors
   predict *low drawdown*, not *higher return*.
2. **Scores DO predict risk/regime.** Higher LEAP/CSP → calmer forward; higher CASH → more
   fragile. The scorecard is a RISK/REGIME classifier, not an alpha timer (consistent with all
   session findings: index timing controls drawdown, not return).
3. **CSP is the one tool that works as designed**: higher score → smaller forward drawdown
   (it only needs "calm enough to not get assigned"). **Entry boundary ≈ score 25** (fwd-dd
   jumps from −4.6% to −2.6% crossing 25); ≥40–50 = comfortably calm.

## Tuning guidance (v2 scorecard)
- LEAP/PMCC: stop using strength/extension as a return signal (it's contrarian). Make the score
  = regime GATE (price>200SMA allowed) + **RSI-2 dip** (the validated entry edge); strength only
  as a low-risk flag.
- CSP: keep (validated).
- Rescale to per-tool PERCENTILE so scores reach both ends and boundaries are meaningful.
- Re-run this validation on v2 to confirm monotonicity.

**Takeaway:** the scorecard is a risk/regime dashboard, not an alpha oracle. Backtesting it before
trusting it caught that LEAP/PMCC's return-weighting was backwards.
