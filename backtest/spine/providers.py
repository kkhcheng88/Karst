"""Provider SEAMS — the LLM/Compass/Tree plug points.

  - thesis_quality : Phase 3 — reads thesis/themes.yaml (the confidence bridge). Falls back to a
                     NEUTRAL pass-through (unit 1.0) when a ticker has no thesis yet.
  - sector_temp    : Phase 1 (computed RS/coherence) + Phase 2 (Compass overlay).

Confidence (the ThesisVerdict.unit) is evidence-derived + calibrated (DESIGN §1), NOT human belief;
it multiplies tier-2 eligibility into sizing. Cold start: values in themes.yaml are INITIAL and
uncalibrated until track_record accumulates (DESIGN §6).
"""
from __future__ import annotations

import os

import yaml

from .schemas import ThesisVerdict

# Phase 0 sector stub: every sector is "warm" so tier-2 names flow through the router.
SECTOR_STUB_TEMP = "STUB"
SECTOR_STUB_WARM = 1

_THEMES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "thesis", "themes.yaml")
_THEMES = None


def _themes() -> dict:
    global _THEMES
    if _THEMES is None:
        try:
            with open(_THEMES_PATH, encoding="utf-8") as fh:
                _THEMES = (yaml.safe_load(fh) or {}).get("themes", {}) or {}
        except Exception:
            _THEMES = {}
    return _THEMES


def thesis_quality(ticker: str) -> ThesisVerdict:
    """Read the ticker's theme verdict from thesis/themes.yaml. No thesis -> NEUTRAL pass-through."""
    for slug, t in _themes().items():
        if ticker in (t.get("tickers") or []):
            return ThesisVerdict(
                verdict=str(t.get("verdict", "pass")),
                unit=float(t.get("confidence", 1.0)),          # confidence = the sizing multiplier
                source=f"thesis:{slug}",
                kill_condition=t.get("kill_condition"),
                cycle_stage=t.get("cycle_stage"),
            )
    return ThesisVerdict(verdict="neutral", unit=1.0, source="no-thesis")
