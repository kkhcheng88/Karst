# Result — Scorecard validation (does the score reach both ends + predict?)

**Date:** 2026-06-30  **Script:** `backtest/experiments/exp_scorecard_validation.py`  **Tag:** ✅ verified
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

## v2 (percentile scale + dip/gate-weighted LEAP/PMCC) — re-validated
- ✅ **Percentile scaling fixed the range** — scores now span 0-100 (p99=100). "Reaches both ends" yes.
- ✅ **CSP still validated** (high score -> lower fwd drawdown); **CASH improved** (high score ->
  worse fwd return AND bigger drawdown = clean danger flag).
- 🔴 **LEAP still doesn't predict return (5d or 21d).** Reason: BLENDING the RSI-2 dip edge into the
  score (with IV/trend) + percentile-ranking DILUTES it. The dip alpha only shows ISOLATED
  (exp_rsi2_alpha: RSI2<5/<10 entry, t~2-3).
- 🔴 **PMCC degenerate** — raw clusters -> percentile inflates -> PMCC falsely dominates the live
  board (89-97). Needs rework or drop.

## Architectural conclusion (the real lesson)
**Do NOT blend the entry edge into the suitability score — blending destroys the one real edge.**
Two layers instead:
- **Scorecard = regime/RISK suitability** (which tool's risk profile fits now). Validated: CSP=calm,
  CASH=danger, LEAP=right-side gate/risk-reducer. NOT a return predictor.
- **Entry trigger = RSI-2 dip**, kept PURE and separate (the validated short-horizon entry alpha),
  applied as the trigger within the chosen tool. (Already visible as RSI2 in the scorecard drivers.)

**v3:** separate the dip trigger out of the score; rework or drop PMCC; keep percentile + CSP/CASH.
