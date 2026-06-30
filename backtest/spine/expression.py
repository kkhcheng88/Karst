"""Stage 3 — two-tier expression router.

  tier-1 (SPY/QQQ/SPMO) -> options toolkit, by WRAPPING the validated scorecard
                           (LEAP / SHORT_CALL / CSP / CASH). Not rewritten.
  tier-2 (everything else) -> Long Position only, STRUCTURAL eligibility.

Phase 0 honesty: tier-2 carries NO TA timing. The score is pure eligibility
(market_gate x sector_warm x thesis_unit) — 0 or 100 here, since the gates are binary
and thesis is the NEUTRAL stub. Entry timing (RSI-2 dip) is Phase 4, a separate card
field, NEVER multiplied into this score. (NB: tier-1's scorecard still bakes RSI-2 in;
Phase 4 will factor that out into the shared timing layer.)
"""
from __future__ import annotations

import scorecard
from signals import sma

from .universe import TIER1


def route(entry) -> str:
    return "options" if entry.ticker in TIER1 else "long"


def express_options(entry, df):
    """df: OHLC joined with a 'vix' column. Returns (scores_dict, expression_dict)."""
    f = scorecard.features(df, df["vix"]).dropna()
    s = scorecard.scores(f).iloc[-1]
    row = f.iloc[-1]
    scores = {k: round(float(v)) for k, v in s.items()}
    expr = {
        "type": "OPTIONS",
        "recommended": max(scores, key=scores.get),
        "csp_mode": scorecard.csp_mode(row),
        "drivers": scorecard.driver_str(row),
    }
    return scores, expr


def express_long(entry, df, mc, thesis, sector_warm: int):
    """Long-only structural eligibility. NO timing (Phase 4)."""
    close = df["close"]
    sma200 = sma(close, 200)
    above200 = bool(close.iloc[-1] > sma200.iloc[-1]) if len(close) >= 200 else False
    dist = float(close.iloc[-1] / sma200.iloc[-1] - 1) if above200 or len(close) >= 200 else float("nan")

    # eligibility = market gate (Stage 0) x name's own trend gate (INV-6 / layer2 family #1)
    #               x sector warm (STUB=1 in Phase 0) x thesis (NEUTRAL stub passes)
    eligible = bool(mc.gate and above200 and sector_warm and thesis.unit > 0)
    score = 100.0 * mc.gate * (1 if above200 else 0) * sector_warm * thesis.unit if eligible else 0.0

    reasons = []
    if not mc.gate:
        reasons.append(f"market gate closed ({mc.gate_label})")
    if not above200:
        reasons.append("below own 200SMA")
    if thesis.unit <= 0:
        reasons.append("thesis kill")

    expr = {
        "type": "LONG",
        "action": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
        "above_200sma": above200,
        "blocked_by": reasons,
        "stop": "wide / none (layer2 §6)",
        "note": "structural eligibility only — entry timing (RSI-2 dip) is Phase 4",
        "drivers": (f"{'above' if above200 else 'below'} 200SMA "
                    f"({dist * 100:+.1f}%)" if dist == dist else "insufficient history for 200SMA"),
    }
    return score, expr
