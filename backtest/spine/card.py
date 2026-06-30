"""Card builder — assembles the per-ticker output and serializes it."""
from __future__ import annotations

from .schemas import TickerCard


def _thesis_dict(thesis):
    return {"verdict": thesis.verdict, "unit": thesis.unit,
            "source": thesis.source, "kill_condition": thesis.kill_condition}


def build_card(entry, mc, score, expr, thesis, sector_temp, sector_warm) -> TickerCard:
    return TickerCard(
        ticker=entry.ticker, asof=mc.asof, tier=entry.tier, sector=entry.sector,
        market_gate=mc.gate, market_gate_label=mc.gate_label,
        sector_temp=sector_temp, sector_warm=sector_warm,
        thesis=_thesis_dict(thesis), score=score, expression=expr,
        drivers=expr.get("drivers", "") or "", caveats=list(mc.caveats),
    )


def error_card(entry, mc, exc) -> TickerCard:
    return TickerCard(
        ticker=entry.ticker, asof=mc.asof if mc else "", tier=entry.tier, sector=entry.sector,
        market_gate=mc.gate if mc else 0, market_gate_label=mc.gate_label if mc else "",
        sector_temp="N/A", sector_warm=0, thesis={}, score=None,
        expression={"type": "ERROR", "error": f"{type(exc).__name__}: {exc}"},
        drivers="", caveats=[],
    )


def to_dict(card: TickerCard) -> dict:
    return {
        "ticker": card.ticker, "asof": card.asof, "tier": card.tier, "sector": card.sector,
        "market_gate": card.market_gate, "market_gate_label": card.market_gate_label,
        "sector_temp": card.sector_temp, "sector_warm": card.sector_warm,
        "thesis": card.thesis, "score": card.score, "expression": card.expression,
        "drivers": card.drivers, "caveats": card.caveats,
    }
