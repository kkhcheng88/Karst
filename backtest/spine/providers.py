"""Provider SEAMS — the LLM/Compass/Tree plug points. Phase 0 stubs return NEUTRAL.

These are the only places where non-backtested, qualitative signal enters the spine.
Each returns a NEUTRAL default ("no information," never a penalty) so the structural
score collapses to honest eligibility until the real provider is wired:
  - thesis_quality : Phase 3 (Tree/LLM verdict + news)
  - sector_temp    : Phase 1 (computed RS/coherence) + Phase 2 (Compass overlay)
"""
from __future__ import annotations

from .schemas import ThesisVerdict

# Phase 0 sector stub: every sector is "warm" so tier-2 names flow through the router.
SECTOR_STUB_TEMP = "STUB"
SECTOR_STUB_WARM = 1


def thesis_quality(ticker: str) -> ThesisVerdict:
    """Stub: NEUTRAL pass-through (unit 1.0). Alpha enters here in Phase 3."""
    return ThesisVerdict(verdict="neutral", unit=1.0, source="stub")
