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


def express_long(entry, df, mc, thesis, sector_ctx, timing):
    """Long-only. Structural eligibility (gate x trend x sector x thesis) and the entry
    TIMING (RSI-2, Phase 4) are kept SEPARATE: the 0/100 `score` stays structural; `timing`
    is its own field. The human-facing `action` is the COMBINATION of the two:
        eligible + DIP        -> BUY_DIP   (structurally allowed AND at the validated trigger)
        eligible + not DIP    -> WATCH     (allowed but extended/neutral -- wait for a dip)
        not eligible          -> AVOID
    Young names (e.g. the sector ETF, <200d) fall back to a 50SMA trend gate with a caveat.
    """
    close = df["close"]
    n = len(close)
    if n >= 200:
        ma, gate_name = sma(close, 200), "200SMA"
    elif n >= 50:
        ma, gate_name = sma(close, 50), "50SMA(<200d hist)"
    else:
        ma, gate_name = None, "n/a"
    above = bool(close.iloc[-1] > ma.iloc[-1]) if ma is not None else False
    dist = float(close.iloc[-1] / ma.iloc[-1] - 1) if ma is not None else float("nan")

    warm = sector_ctx.warm if sector_ctx else 1
    temp = sector_ctx.temperature if sector_ctx else "STUB"
    rankinfo = (sector_ctx.member_rank.get(entry.ticker) if sector_ctx else None) or {}
    is_laggard = bool(rankinfo.get("is_laggard"))

    eligible = bool(mc.gate and above and warm and thesis.unit > 0)
    score = 100.0 * mc.gate * (1 if above else 0) * warm * thesis.unit if eligible else 0.0

    reasons = []
    if not mc.gate:
        reasons.append(f"market gate ({mc.gate_label})")
    if not above:
        reasons.append(f"below {gate_name}")
    if not warm:
        reasons.append(f"sector {temp}")
    if thesis.unit <= 0:
        reasons.append("thesis kill")

    if not eligible:
        action = "AVOID"
    elif timing.label == "DIP":
        action = "BUY_DIP"
    else:
        action = "WATCH"  # eligible but no dip trigger (extended / neutral)

    notes = []
    if is_laggard and warm:
        notes.append(f"INV-5 laggard (US RS rank {rankinfo.get('us_rank')}/{rankinfo.get('n_us')}) -- prefer the RS top-2")
    if action == "WATCH":
        notes.append(f"wait for a dip (RSI2 {timing.rsi2}, {timing.label})")

    base = (f"{'above' if above else 'below'} {gate_name} ({dist * 100:+.1f}%)"
            if dist == dist else "insufficient history")
    expr = {
        "type": "LONG",
        "action": action,
        "above_trend": above,
        "trend_gate": gate_name,
        "sector_temp": temp,
        "is_laggard": is_laggard,
        "blocked_by": reasons,
        "stop": "wide / none (layer2 §6)",
        "drivers": base + ("; " + "; ".join(notes) if notes else ""),
    }
    return score, expr
