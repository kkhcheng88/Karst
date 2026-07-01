# Valuation (own-history PE percentile) — a context gauge, NOT a mechanical alpha

2026-07-01. `backtest/exp_valuation.py`. Karst had ZERO valuation dimension (all price/
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

## Files
New: `backtest/exp_valuation.py` (uses defeatbeta ttm_pe direct; engine/metrics reused).
