"""Karst spine — the top-down scanning pipeline.

The 6-stage funnel: Market gate (0) -> Sector temp (1) -> Stock score (2) ->
two-tier Expression (3) -> Risk (4) -> [later] self-heal. Output = one Card per
ticker. Built incrementally:

  Phase 0 (this) : Market gate + plumbing + two-tier router. Sector STUBBED.
                   NO TA timing (RSI-2 is Phase 4, a SEPARATE field, never a score multiplier).
  Phase 1        : Sector layer (hierarchical: subsector vs parent vs market) + coherence/breadth.
  Phase 2        : Compass overlays (capital flow / narrative / macro) via snapshots.
  Phase 3        : Thesis seam (Tree/LLM + news) — where alpha actually enters.
  Phase 4        : TA timing overlay (RSI-2 dip entry / overbought short-call), both tiers.

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
