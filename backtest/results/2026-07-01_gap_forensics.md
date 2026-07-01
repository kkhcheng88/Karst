# Top-20 non-tech gap weeks — the high-frequency tail is EVENT-driven, not noise

2026-07-01. `exp_gap_forensics.py`. The user's point: if the oracle alpha were pure slow-regime,
the monthly oracle would keep most of the weekly (regimes persist over months) — but it halves
(151%->66%). So a lot of the edge is high-frequency and NOT regime-persistence. Test the tail: the
20 weeks where the best NON-tech sector most out-gapped SPY (exclude tech — its dominance is the
obvious story). Are they recognizable events or noise?

## Result — every one maps to a named macro event
| week | sector | gap | event |
|---|---|---|---|
| 2009-03-13 | XLF +32% | 22% | GFC market bottom (3/9; Pandit memo -> banks explode) |
| 2008-11-28 | XLF +31% | 18% | Citigroup bailout (11/23) first bank-rescue rally |
| 2009-05-08 | XLF +22% | 16% | bank stress-test results (5/7) "less bad than feared" |
| 2020-11-13 | XLE +17% | 15% | Pfizer vaccine (11/9) -> reopening/value/energy rotation |
| 2022-10-07 | XLE +14% | 12% | OPEC+ 2M bpd production cut (10/5) |
| 2022-03-04 | XLE +9% | 11% | Russia invades Ukraine (2/24) -> oil ~$130 |
| 2022-01/05, 2021-03 | XLE | ~10% | inflation/reflation trade, oil rising |
| 2000-03-17 | XLF +16% | 11% | dotcom peak -> rotation to financials/value |
| 2000-04-14 | XLP (SPY -10%) | 10% | dotcom crash week, staples defensive |
| 2001-09-21 | XLU (SPY -11%) | 9% | 9/11 reopening week, utilities defensive |
| 2020-04-10 | XLB +21% | 9% | COVID recovery start (Fed unlimited QE) |
| 2002-07-26 | XLV +10% | 9% | 2002 bear-market bottom, healthcare defensive |

By year: 2000x3, 2008x2, 2009x2, 2020x3, 2022x4 — all crisis/shock years. By sector: XLE x7
(oil/geopolitical shocks), XLF x5 (financial crisis), XLB x3 (cyclical reflation), XLV/XLU/XLP
(crash defensives). NOT scattered noise — recognizable named catalysts.

## Three layers of oracle alpha (stop over-narrating a single story)
1. Pure high-frequency noise — uncapturable (the bulk of the inflated weekly number).
2. Slow regime tilts — annual sector leadership (energy supercycles, tech/AI booms); ~2x SPY
   ceiling; recognizable macro narrative.
3. Event catalysts — the top-20 gaps: GFC rescues, Ukraine/OPEC oil shocks, vaccine reopening,
   crash defensives, 9/11 — ALL recognizable named events, actionable with a short news lag.

## The empirical conclusion of the whole arc
The capturable alpha is a READ-MACRO-REGIME + READ-EVENT-CATALYST problem, NOT a price-pattern
problem. This is WHY every price/volume test gave IC ~0: a price chart does NOT contain "Russia
invaded Ukraine", "OPEC cut", "the vaccine works", "banks were bailed out" — that information is
in NEWS/EVENTS. So offense MUST be qualitative (regime + catalyst -> sector/theme tilt) = Phase 3
(news/catalysts/fundamentals/bottleneck), now with an empirical shape (these event weeks) and a
measured ceiling (annual regime ~2x SPY). The arc's value isn't "quant is useless" — it empirically
LOCATED the edge: not in prices, in the ability to read events and regimes.

## Files
New: `backtest/exp_gap_forensics.py`.
