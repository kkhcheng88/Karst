"""Karst spine — the top-down scanning pipeline.

The 6-stage funnel: Market gate (0) -> Sector temp (1) -> Stock score (2) ->
two-tier Expression (3) -> Risk (4) -> [later] self-heal. Output = one Card per
ticker. Status (updated 2026-07-03; see STATUS.md at repo root):

  Phase 0  BUILT    : Market gate (trend/VIX/term/breadth/SPMO-RS) + two-tier router.
                      Known gap: credit axis + trend-vs-risk divergence NOT wired
                      (docs/2026-07-03_strategy_methodology_review.md P0-2).
  Phase 1  BUILT    : Sector layer (ETF-holdings temp, two-level RS, coherence/breadth).
  Phase 2  DEFERRED : Compass overlays (capital flow / narrative / macro).
  Phase 3  LIVE     : Thesis seam (thesis/themes.yaml confidence -> tier-2 score).
                      Known gap: insider conf_eff computed but NOT fed to score (P0-1).
  Phase 4  BUILT    : RSI-2 timing as a SEPARATE card field, never a score multiplier.
                      (tier-1 scorecard still bakes RSI-2 in — dedup pending, P1-9.)

Honest core: the structural score = market_gate x sector_warm x thesis. It reads
REGIME/eligibility, NOT a TA alpha rank (Karst backtests: TA on liquid names = risk
control, not alpha). Timing is layered on top, separately, in Phase 4.

This __init__ puts backtest/ on sys.path so spine modules can import the validated
flat modules (scorecard / regime / signals / data) by their BARE names, exactly as
those modules import each other. Do not packagify those — their standalone __main__
runs back the /karst skill.
"""
from __future__ import annotations

import os
import sys

_BACKTEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKTEST_DIR not in sys.path:
    sys.path.insert(0, _BACKTEST_DIR)
