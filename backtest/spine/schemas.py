"""Frozen data shapes for the spine. Plain dataclasses — no behavior, just contracts."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MarketContext:
    """Stage 0 output — the market gate. Computed from price/vol ETFs (+ index VIX)."""
    asof: str
    risk_appetite: str          # A/B/C/D from VIX level (Compass regime_matrix outer layer)
    vix: float
    vix_iv_rank: float          # 252d percentile
    vix_term: float             # VIX / VIX3M  (>1 backwardation = near-term stress)
    spy_above_200sma: bool
    spy_dist: float             # close/200sma - 1
    spy_adx: float
    spy_regime: str             # down/sideways/moderate_up/strong_up (regime.classify)
    iwm_above_200sma: bool
    breadth_divergence: bool    # SPY up but IWM (small-cap) not — narrow/late-cycle warning
    momentum_on: bool           # RS(SPMO/SPY) over 63d > 1 (momentum factor in favor)
    gate: int                   # 0/1 — is the market eligible for NEW long/risk (SPY>200SMA)
    gate_label: str             # risk_on / risk_on_fragile / wait / defend
    drivers: str
    caveats: list


@dataclass(frozen=True)
class ThesisVerdict:
    """Stage 2 alpha SEAM. Phase 0 stub = NEUTRAL (unit 1.0, multiplicative identity).
    Real verdicts arrive in Phase 3 from Tree/LLM. FAIL (unit 0) = a kill condition fired."""
    verdict: str                # fail/weak/neutral/pass/strong
    unit: float                 # 0..1 multiplier; NEUTRAL=1.0 -> score collapses to eligibility
    source: str                 # "stub" until Phase 3
    kill_condition: str | None = None


@dataclass(frozen=True)
class UniverseEntry:
    ticker: str
    tier: str                   # "options" (SPY/QQQ/SPMO) | "long" (everything else)
    sector: str                 # "MARKET" for the index ETFs; a sector key otherwise
    iv_proxy: str | None = None  # ^VIX / ^VXN for options tickers


@dataclass(frozen=True)
class TickerCard:
    """The output unit — one per ticker per daily run."""
    ticker: str
    asof: str
    tier: str
    sector: str
    market_gate: int
    market_gate_label: str
    sector_temp: str            # "N/A" (MARKET) | "STUB" (Phase 0 sector) | a temp later
    sector_warm: int
    thesis: dict                # {verdict, unit, source, kill_condition}
    score: object               # dict (options: per-tool) | float (long: 0/100 eligibility)
    expression: dict            # tier-aware payload
    drivers: str
    caveats: list
