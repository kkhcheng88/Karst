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
class SectorContext:
    """Stage 1 output — sector/subsector temperature (computed Layer-1 price metrics).

    Hierarchy: the basket (e.g. Memory) is measured BOTH vs its parent (SEMI) — intra-sector
    leader/laggard, feeds INV-5 — AND vs the market (SPY). Coherence/breadth catches a Warm
    reading that is really one name carrying the basket.
    """
    sector: str
    parent: str | None
    members: list               # tickers actually used in the basket
    weight_mode: str            # "market_cap" | "equal"
    rs_vs_market: float         # basket vs SPY over 20d (>1 = outperforming)
    rs_vs_parent: float         # basket vs parent (SEMI) — intra-sector rotation
    parent_rs_vs_market: float  # parent vs SPY (sector rotation)
    roc20: float                # cap-weighted basket 20d return
    layer1_score: int           # 0-3 (RS / breadth / ROC points)
    temperature: str            # Cold / Warm / Hot
    warm: int                   # 0/1 — eligible (Warm or Hot)
    breadth_above50: float      # fraction of members above own 50DMA
    roc_dispersion: float       # stdev of member 20d returns
    leader: str                 # member contributing most to basket momentum
    leader_share: float         # leader's share of cap-weighted positive momentum (NaN if basket down)
    coherence: str              # broad / mixed / leader-carried
    member_rank: dict           # ticker -> {rank, rs_vs_parent, is_laggard}  (INV-5)
    drivers: str
    caveats: list
    equal_roc20: float = float("nan")           # EQUAL-weighted basket 20d return (breadth view)
    cap_equal_divergence: float = float("nan")  # cap_roc - equal_roc: >0 megacap-led (narrow) /
    #                                             <0 small-cap-led (froth); |large| = late/fragile


@dataclass(frozen=True)
class SectorRotation:
    """Stage-1 TOP level — the GICS sector-rotation map (the DEFENSE / regime lens).

    11 SPDR sectors ranked by RS vs SPY. Distinct from a value-chain (which cuts ACROSS
    GICS): this is the broad rotation/regime read, ETF-only. Surfaces leadership breadth
    (narrow = fragile/late-cycle), the cyclical-vs-defensive tilt (risk-on/off), and
    whether tech is confirming leadership.
    """
    asof: str
    rows: list                  # ranked: [{etf, name, rs63, rs21, above200, temp, group}]
    n_beating: int              # how many of 11 beat SPY (RS63 > 1)
    breadth: str                # narrow / mixed / broad
    tilt: str                   # "risk-on (cyclicals lead)" / "risk-off (defensives lead)"
    cyc_rs: float               # mean RS63 of cyclicals
    def_rs: float               # mean RS63 of defensives
    tech_leading: bool          # XLK beating SPY
    drivers: str
    caveats: list


@dataclass(frozen=True)
class ThesisVerdict:
    """Stage 2 alpha SEAM. NEUTRAL stub = unit 1.0 (pass-through) until a thesis exists.
    Phase 3 fills it from thesis/themes.yaml. `unit` IS the CONFIDENCE (0..1, evidence-derived +
    calibrated; NOT human 'belief') -> it multiplies the tier-2 eligibility into sizing. FAIL/kill
    -> unit 0. cycle_stage (early/mid/late) tempers confidence (late = don't chase)."""
    verdict: str                # real-but-late / pass / weak / fail / neutral ...
    unit: float                 # = confidence 0..1 (the sizing multiplier); NEUTRAL=1.0
    source: str                 # "thesis:<slug>" | "no-thesis"
    kill_condition: str | None = None
    cycle_stage: str | None = None   # early / mid / late / None


@dataclass(frozen=True)
class EntryTiming:
    """Phase 4 — the TA timing layer. A SEPARATE field, NEVER multiplied into the structural
    score (validated lesson: regime/eligibility != entry trigger). RSI-2 dip = the validated
    long entry; overbought = the short-call peak."""
    rsi2: float
    label: str                  # DIP / neutral / elevated / overbought / n/a
    note: str


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
    entry_timing: dict          # {rsi2, label, note} — Phase 4, separate from score
    score: object               # dict (options: per-tool) | float (long: 0/100 eligibility)
    expression: dict            # tier-aware payload
    drivers: str
    caveats: list
