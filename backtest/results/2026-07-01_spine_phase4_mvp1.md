# Spine Phase 4 — RSI-2 timing → MVP1 complete

2026-07-01. Adds the TA entry-timing layer. **MVP1 = Phase 0 (market gate) + Phase 1
(sector temp) + Phase 4 (timing) is now complete and runnable end-to-end.**

## Phase 4 — timing as a SEPARATE field, never a score multiplier

The validated lesson (and the user's design rule): the structural score reads regime/
eligibility; timing says *when*. So `spine/timing.py` `entry_timing(close)` returns an
`EntryTiming{rsi2, label, note}` carried on every card as its own field — it is NOT
multiplied into the 0/100 structural score. Labels (reuse the scorecard's Wilder RSI-2):
- `DIP` (RSI-2 < 10)  — the validated long-entry trigger
- `overbought` (> 90) — short-call peak, not a long entry
- `elevated` (70-90)  — extended, wait for a pullback
- `neutral`           — no trigger

## The actionable combination (tier-2 long)

`action` = structural eligibility × timing (kept separate, combined only for the human call):
- eligible + DIP        → **BUY_DIP**
- eligible + not DIP     → **WATCH** (allowed but extended/neutral — wait for a dip)
- not eligible           → **AVOID**

tier-1 (SPY/QQQ/SPMO) keeps the validated scorecard (which already encodes timing in
LEAP=dip / SHORT_CALL=overbought); RSI-2 is surfaced as the `entry_timing` field for
consistency, NOT decomposed out of scorecard (deliberate — don't disturb validated output;
a future cleanup can factor it out).

## Verified read (2026-06-30) — the whole funnel now speaks

- MARKET risk_on; MEMORY Hot but semis-led (vs SEMI 0.99).
- Every memory name `WATCH` — structurally eligible (gate × Hot sector × uptrend) but **none at
  a dip** (RSI-2 50-75), and hugely extended (+114%..+232% vs 200SMA). So the scan says
  "allowed, but wait for a pullback" — NOT buy. STX also flagged INV-5 laggard.
- This is the honest two-layer output the design aimed for: structure says *who's allowed*,
  timing says *not now*.

## MVP1 status
Phase 0 ✓ + Phase 1 ✓ + Phase 4 ✓. A usable daily top-down scan: market gate → sector
temperature (from real ETF holdings) → two-tier expression → RSI-2 action. tier-1 = options
toolkit; tier-2 = Long-only BUY_DIP/WATCH/AVOID + the sector ETF as a sector-level long.

## Deferred to v2
- **Phase 2** — Compass overlays (capital-flow / narrative / macro regime_matrix) via snapshots.
- **Phase 3** — thesis seam (Tree/LLM verdict + defeatbeta fundamentals/news) = where ALPHA
  enters; until then tier-2 score is eligibility (0/100), thesis NEUTRAL stub.
- Flow/positioning (gamma walls, CTA, Fear&Greed) — tagged-unvalidated overlays, later.
- Optional: factor RSI-2 out of tier-1 scorecard; issuer-CSV full holdings; cap-weight fallback.

## Files
New: `spine/timing.py`; `EntryTiming` in `schemas.py` (+ `entry_timing` on TickerCard).
Changed: `expression.py` (express_long action from eligibility×timing), `card.py`
(entry_timing on every card), `orchestrator.py` (compute timing per ticker, display).

## Run
`python backtest/scan.py` (human) / `--json`. The `/karst` skill's Daily Scan is the front door.
