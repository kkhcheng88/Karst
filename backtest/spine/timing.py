"""Phase 4 — TA entry timing (RSI-2), the validated low-capacity edge.

A SEPARATE card field, NEVER folded into the structural score (Karst's validated lesson:
the structural score reads regime/eligibility; timing says *when*). The actionable trigger
is the RSI-2 dip in an uptrend (LEAP/long entry); the mirror is overbought (short-call peak).
Reuses the same Wilder RSI-2 as the validated scorecard (signals.rsi).
"""
from __future__ import annotations

from signals import rsi

from .schemas import EntryTiming


def entry_timing(close, *, dip: float = 10.0, overbought: float = 90.0, elevated: float = 70.0) -> EntryTiming:
    r = rsi(close, 2)
    v = float(r.iloc[-1]) if len(r) else float("nan")
    if v != v:
        return EntryTiming(rsi2=float("nan"), label="n/a", note="insufficient history")
    if v < dip:
        label, note = "DIP", "oversold dip -- the validated long-entry trigger"
    elif v > overbought:
        label, note = "overbought", "extreme overbought -- short-call peak, not a long entry"
    elif v >= elevated:
        label, note = "elevated", "extended -- wait for a pullback"
    else:
        label, note = "neutral", "no timing trigger -- wait for a dip"
    return EntryTiming(rsi2=round(v, 1), label=label, note=note)
