# Spine Phase 1 — sector temperature from ETF holdings (option B)

2026-07-01. Replaces the Phase-0 sector STUB with a real Stage-1 layer. MVP1 = Phase 0
+ 1 + 4; this is the middle vertebra (the key one — memory is a strongly cyclical sector).

## Decision: define the sector from the ETF's REAL holdings (option B)

The hand-picked US trio {MU,WDC,STX} was wrong. Pulling DRAM (Roundhill Memory ETF) holdings
via yfinance `funds_data.top_holdings` revealed the real composition:

| holding | weight | |
|---|---|---|
| SK Hynix (000660.KS) | 24.7% | KR |
| Samsung (005930.KS) | 16.3% | KR |
| FGXXX (money-market) | 14.9% | **cash — filtered out** |
| Kioxia (285A.T) | 6.6% | JP |
| SNDK / MU / STX | ~5% each | US |

So memory is a **global** sector led by SK Hynix/Samsung; the US names are ~14% and WDC isn't
even in it. Chosen approach (user: "DRAM is tradable even if SK Hynix isn't"):
- **Temperature from full holdings** (foreign included). Currency cancels — RS/ROC are unitless
  ratios; only the trading-session offset remains (minor over 20d). Data confirmed: all of
  000660.KS / 005930.KS / 285A.T load with full history.
- **Weights = the ETF's own holding %** (renormalized after dropping the cash sleeve).
- **tier-2 actionable longs = US holdings auto-derived** (SNDK/MU/STX) + **DRAM itself** as a
  sector-level long (expresses the whole sector incl. the foreign leaders you can't buy directly).
- Foreign names are context only (not scanned as rows).

## What Stage 1 computes (`sector.py`)

Hierarchical, per the subsector model (Memory ⊂ SEMI ⊂ market):
- **Two-level RS:** basket vs SPY (sector-vs-market) AND basket vs SEMI=SOXX/SMH (intra-sector).
  Parent-relative normalizes broad-semi beta, so the single-name weighting matters less.
- **Temperature** (Layer-1, price only): RS / breadth / ROC points → 0-3 → Cold/Warm/Hot.
- **Coherence/breadth:** % members > own 50DMA; ROC dispersion; momentum-contribution leader +
  leader_share → broad / mixed / leader-carried (catches "one name carrying the sector").
- **INV-5:** members ranked by RS-vs-parent. The actionable `is_laggard` flag is judged among
  **US-tradeable members only** (a non-tradeable foreign leader is context, never an "actionable
  laggard"); `rank` is the full-basket RS rank for context.

## Verified read (2026-06-30) — the layer earns its keep

MEMORY = **Hot (L1 3/3)**, BUT `RS vs mkt 1.11` while `vs SEMI 0.99` → "semis are hot (1.12 vs
mkt) and memory is just keeping pace, NOT leading within semis." Coherence broad (breadth 100%).
Actionable US RS leader = **SNDK** (RS-vs-SEMI 1.17, +29% ROC20); **STX is the US laggard** (rank
3/3, INV-5 says prefer top-2 SNDK/MU). Sector leader by weight×momentum = SK Hynix (foreign) →
caveat: express via DRAM or the strongest US name. This nuance is exactly what a flat US basket
would have hidden.

## Honest caveats
- yfinance gives only **top-10** holdings (DRAM small, so ~complete); full list needs issuer CSV /
  SEC N-PORT. Holdings are a periodic snapshot. Fallback list hardcoded if funds_data fails.
- Samsung is a conglomerate (impure memory exposure) — inherited from the ETF's definition.
- Still NO entry timing (Phase 4) and thesis is the NEUTRAL stub (Phase 3) — so a Hot sector +
  ELIGIBLE name is "structurally allowed," NOT "buy now." Memory names are +114%..+232% over their
  200SMA — structurally eligible but extended; Phase 4 RSI-2 is what will say "wait for a dip."

## Files
New: `spine/holdings.py` (ETF holdings, cash filter, US/foreign tag), `spine/sector.py` (Stage 1).
Changed: `spine/schemas.py` (SectorContext), `universe.yaml` (holdings_etf), `universe.py`
(expand_with_sectors), `expression.py` (sector-aware express_long + <200d 50SMA gate),
`orchestrator.py` (sector block + JSON), `providers.py` (stub → fallback only).

## Next: Phase 4 (TA timing) — the last MVP1 vertebra
RSI-2 dip (entry) / overbought (short-call) as a SEPARATE card field, both tiers; factor the RSI-2
baked into tier-1 scorecard out into the shared timing layer. Then MVP1 is complete.
