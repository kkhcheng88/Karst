# Valuation (own-history PE percentile) — a context gauge, NOT a mechanical alpha

2026-07-01. `backtest/experiments/exp_valuation.py`. Karst had ZERO valuation dimension (all price/
momentum/regime). Tested whether buying a name CHEAP vs its OWN PE history has a return edge
(the value premium) — using defeatbeta `ttm_pe` (the one valuation series with long daily
history, back to the 90s; PS/EV-EBITDA/ROIC are only ~2022+). Universe = 18 large caps across
sectors, deliberately mixing secular winners and laggards (INTC/DIS/T/XOM/CSCO) vs survivorship.

## Test 1 — forward-126d return by PE percentile (own trailing 3y): U-SHAPED
```
Q0 cheapest 8.4% | Q1 8.3% | Q2 5.7% | Q3 4.9% | Q4 priciest 9.1%  (highest!)
```
- Cheap (Q0/Q1) beats FAIRLY-valued (Q2/Q3) → value has SOME signal.
- BUT the PRICIEST quintile (Q4) has the HIGHEST forward return → high-PE secular growers kept
  compounding. Only 10/18 names have positive cheap-minus-expensive spread. The names that
  KILL "value works": NVDA (spread -21%), META (-15%), CSCO, MSFT — buying them "cheap" meant
  avoiding the biggest runs. Value WORKED on mature/steady names: AAPL (+15%), KO, PG, JNJ, DIS, HD.

## Test 2 — tradeable CHEAP strategy (long pctile<40, exit >60) vs B&H: does NOT survive
- 7/18 beat B&H on Sharpe; only **AAPL clears DSR (0.97)** — and AAPL is the survivorship poster
  child, so it's ~1 fluke. Everything else DSR < 0.8.
- Value strategy generally LOSES to B&H on CAGR (MSFT 4.4 vs 15.5, NVDA 10.6 vs 37) by sitting
  out the biggest runs. Adding a trend gate (VAL+TREND) mostly makes it worse.

## Conclusion (5th consistent lesson, with a useful twist)
Valuation is NOT a harvestable mechanical alpha (fails DSR, loses to B&H) — same fate as price-TA.
But it has two real uses:
1. **Context gauge (modestly useful):** extreme own-history cheapness does associate with higher
   forward return than fair value → a legitimate THESIS TILT input, not a standalone strategy.
2. **It validates the offense/defense split from the valuation angle:**
   - **Growth / offense names (NVDA/META, high PE): value is a TRAP** — "expensive" is not a sell
     (Q4 wins); momentum/growth dominates. Do NOT time them on cheapness.
   - **Mature / defense names (AAPL/KO/PG/JNJ): cheapness is a valid tilt** — valuation mean-reversion
     applies here.

Answers "is it priced in?": the percentile shows WHERE EXPECTATIONS SIT, but "expensive" ≠ sell for
a real grower. Valuation is a gauge, not a decision — it must be paired with moat / ROIC / growth-
durability judgment (Expectations Investing). Directly relevant to the Mag7-CAPEX-fear case: the
dip is an opportunity for a DURABLE grower, a trap for a false one — valuation alone can't tell them apart.

## Caveats
- Survivorship: universe includes today's mega-winners → inflates BOTH "expensive wins" (Q4) and
  "value hurts on winners". The robust parts are "cheap > middle" and "value doesn't beat B&H".
- PE distorted by cyclical/peak earnings (low PE at peak EPS = value trap); raw (not total-return)
  close; single metric (PE) — PS/EV-EBITDA history too short to cross-check over the long run.

## Decision
Do NOT build a mechanical valuation strategy. ADD valuation percentile (own-history + industry-
relative via `industry_ttm_pe`) as a CONTEXT dimension in the Phase-3 thesis layer — the
"valuation/expectations" KPI — used STYLE-DEPENDENTLY (offense: watch growth-durability not
cheapness; defense: cheapness is a tilt). Not a standalone signal.

## Broad-universe update — the U-shape was a TECH artifact (`exp_valuation_broad.py`)
The 18-name study was ~half tech giants, which over-stated "expensive wins". Re-ran on a broad,
non-hand-picked universe = top-10 US holdings of ALL 11 SPDR sectors (110 names), broken down
BY SECTOR:

```
sector    spread %pos   Q0   Q1   Q2   Q3   Q4   shape
Tech       -7.9%  20%  10.5 11.8 13.0 11.3 15.7  GROWTH (value trap)
Materials +11.3%  90%  12.2  6.7  7.2  5.7  4.4  VALUE (strongest)
Utilities  +6.6%  60%   4.7  4.9  4.5  4.2  3.8  VALUE
Comm       +5.8%  89%  11.0  8.6  8.0  4.4  3.5  VALUE
Discr      +2.5%  50%  10.8 11.3  7.8  6.1  8.3  VALUE
Fin/Energy/Health/Staples/Indus/RealEst ~+1%  ~flat
ALL (107)          58%   7.9  7.4  6.7  5.8  6.9   mostly monotone-declining (value-ish)
```
- **The U-shape (Q4 highest) is essentially TECH-ONLY.** In the broad pool, Q4 is NOT the peak;
  the pattern is roughly monotone-declining Q0>Q1>Q2>Q3 (cheap beats fair), with only a small
  Q4 uptick that Tech alone produces.
- **Value is sector-dependent:** a TRAP in Tech (the lone GROWTH sector), a real positive tilt in
  Materials/Comm/Discr/Utilities (cyclical/mature), ~flat elsewhere. 58% of names cheap>expensive.
- **This confirms the offense/defense-by-valuation split on a broad universe:** don't apply
  valuation cheapness to growth/offense (Tech); it's a legit tilt for mature/cyclical/defense.
- Discipline unchanged: even where the tilt exists, mechanical harvesting still loses to B&H
  (Test 2) -> valuation is a style-dependent CONTEXT tilt, not a mechanical strategy.

## Files
New: `backtest/experiments/exp_valuation.py` (18 hand-picked, ttm_pe), `backtest/experiments/exp_valuation_broad.py`
(110 SPDR-top-10 names, by-sector, fast rolling-rank percentile).
