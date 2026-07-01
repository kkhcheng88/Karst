"""Provider SEAMS — the LLM/Compass/Tree plug points.

  - thesis_quality : Phase 3 — reads thesis/themes.yaml (the confidence bridge). Falls back to a
                     NEUTRAL pass-through (unit 1.0) when a ticker has no thesis yet.
  - sector_temp    : Phase 1 (computed RS/coherence) + Phase 2 (Compass overlay).

Confidence (the ThesisVerdict.unit) is evidence-derived + calibrated (DESIGN §1), NOT human belief;
it multiplies tier-2 eligibility into sizing. Cold start: values in themes.yaml are INITIAL and
uncalibrated until track_record accumulates (DESIGN §6).
"""
from __future__ import annotations

import importlib.util
import os
import sys

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


# --- Phase 3 corroboration: insider buying (the one durable Flow family; NOT in the price chart) ---
_INSIDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "thesis", "insider.py")
_INSIDER_MOD = None


def _insider_mod():
    global _INSIDER_MOD
    if _INSIDER_MOD is None:
        try:
            spec = importlib.util.spec_from_file_location("karst_insider", _INSIDER_PATH)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["karst_insider"] = mod          # register so @dataclass finds its module
            spec.loader.exec_module(mod)
            _INSIDER_MOD = mod
        except Exception:
            _INSIDER_MOD = False
    return _INSIDER_MOD


def insider(ticker: str):
    """Insider-buying corroboration (thesis/insider.py). Returns an InsiderSignal or None on failure.
    A BOUNDED Phase-3 nudge: buying (esp. cluster/C-suite) corroborates; net selling gently tempers."""
    mod = _insider_mod()
    if not mod:
        return None
    try:
        return mod.insider_signal(ticker)
    except Exception:
        return None


def corroborated_confidence(base_conf: float, ins) -> float:
    """Nudge a thesis confidence by the insider score, bounded to +/-30%. Corroboration, not driver."""
    if ins is None or base_conf is None:
        return base_conf
    return round(max(0.0, min(1.0, base_conf * (1.0 + 0.30 * ins.score))), 3)
