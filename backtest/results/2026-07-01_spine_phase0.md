# Spine Phase 0 — top-down scan skeleton (market gate + two-tier router)

2026-07-01. Built the first vertebra of the daily top-down scanning system
(KARS_MEMORY §2 终极目标). Until now Karst was a 3-ETF options widget; the spine
turns it into a universe-driven scanner. `backtest/spine/`, runs end-to-end today.

## The end-state (locked) — a 6-stage funnel, output = one Card per ticker

| Stage | Question | Phase |
|---|---|---|
| 0 Market gate | risk-on / neutral / defend? | **0 (this)** |
| 1 Sector temp (hierarchical) | which sectors/subsectors Warm? | 1 |
| 2 Stock score | structural eligibility per name | 0 (stub) → deepened by 1/3 |
| 3 Expression (two-tier) | SPY/QQQ/SPMO → options; others → Long only | **0** |
| 4 Risk / sizing | invariants, sizing caps | later |
| (timing) **TA 擇时** | RSI-2 dip entry / overbought short-call | **4 (separate)** |

Two-tier output (recorded): the system scores ALL names; only SPY/QQQ/SPMO get
the options toolkit (LEAP / Covered Call / CSP → PMCC), every other name is Long-only.

## Locked design decisions (this session)

1. **Timing is its own Phase 4, and a SEPARATE card field — NEVER a score multiplier.**
   Re-affirms the validated lesson: structural score (regime/eligibility) ≠ entry trigger
   (RSI-2). The structural score reads suitability; timing says *when*. Phase 0 carries
   NO timing — so a hugely-extended name (MU +165% vs 200SMA) is ELIGIBLE but gets no
   buy call. Phase 4 will also factor the RSI-2 baked into tier-1 `scorecard` out into the
   shared timing layer.
2. **SPMO = momentum FACTOR, not market and not a sector.** Stays a tier-1 options ticker;
   its `RS(SPMO/SPY)` feeds the market gate as a momentum-regime confirmation.
3. **Market gate inputs (Stage 0):** SPY>200SMA (trend) + ^VIX bands/iv_rank (vol, A/B/C/D)
   + IWM>200SMA (small-cap breadth divergence) + ^VIX/^VIX3M (term backwardation = stress)
   + RS(SPMO/SPY) (momentum). **Rejected QQQ/DIA in the gate** — too correlated with SPY to
   add info (simple>complex). **ETF for price/RS; index only for vol** (indices have no usable
   volume; tracking error negligible for 200SMA/RS).
4. **Memory chosen as the Phase-1 sector** (small, cyclical → real Warm/Cold swings, news-rich).
   `DRAM` (Roundhill Memory ETF) EXISTS but is too young (listed 2026-04, 61d, no 200SMA) →
   Stage-1 temperature must use a **cap-weighted basket {MU,WDC,STX}** (SNDK seasons in; DRAM
   swaps in ~2027). Forces the right abstraction: SectorContext source = `etf:` OR `basket:`.
5. **Subsector hierarchy** (schema now, populate Memory→SEMI in Phase 1): two-level RS —
   subsector-vs-parent (Memory vs SOXX = intra-semi leader/laggard, feeds INV-5) and
   parent-vs-market (SOXX vs SPY). Plus a **coherence/breadth** metric (% above 50DMA,
   ROC dispersion, leader-contribution) to catch "MU is carrying the whole sector."
6. **Flow/positioning signals quarantined.** Gamma walls/GEX, CTA scores, Fear&Greed are
   paid / not-free-backtestable → overlay phase only, tagged unvalidated, never core rules.
   The free+backtestable orthogonal dims the project endorses are **breadth** and **VIX term
   structure** (the latter now in the gate).
7. **Data freshness fix:** defeatbeta's price pipeline **lags ~1 trading day** (06-29 vs
   yfinance 06-30; SNDK gap +11% in this regime). Flipped `data.py` `load()` to **yfinance-first,
   defeatbeta-fallback** for prices; defeatbeta stays the source for fundamentals/transcripts/news
   (Phase 3, separate paths). `source=` still pins a vendor for backtest reproducibility.

## What Phase 0 produces (verified, as of 2026-06-30)

- Market: RISK_ON (SPY +8.0%>200SMA, VIX 16.5 rank 17% C, term 0.87, IWM+, SPMO-RS 1.27 on).
- tier-1: reproduces scorecard exactly (SPY rec SHORT_CALL @RSI2 87; QQQ SHORT_CALL mid-IV avoid; SPMO CSP).
- tier-2: MU/SNDK/WDC/STX all `score 100 ELIGIBLE` (gate×above-200×warm-stub×thesis-stub), no timing.
- `--json` validated; per-ticker failures isolated (error card, never crashes the run).

## Honest caveats
- tier-2 score is **0/100 eligibility only** — no gradation until thesis (Phase 3) and no
  trigger until timing (Phase 4). This is by design, not a bug.
- Sector is STUB (warm=1) in Phase 0; memory names look eligible regardless of sector heat.
- Supercycle prices (MU ~$1150, SNDK ~$2270) — both vendors agree; spine signals are
  scale-invariant, but verify against a broker before acting.

## Files
`backtest/spine/` — `__init__.py` (path shim), `dataio.py` (cached load), `schemas.py`,
`universe.yaml` + `universe.py`, `context.py` (Stage 0), `providers.py` (stubs),
`expression.py` (router + tiers), `card.py`, `orchestrator.py`. Entry: `backtest/scan.py`.
Also `backtest/__init__.py` (package marker), `data.py` (source flip).

## Run
```
python backtest/scan.py            # human
python backtest/scan.py --json     # machine-readable
```

## Next (Phase 1)
Sector layer: Memory cap-weight basket; two-level RS (vs SEMI / vs market); breadth/coherence;
INV-5 RS-top-2; replace the STUB. Then Phase 2 (Compass overlays) → 3 (thesis seam) → 4 (timing).
