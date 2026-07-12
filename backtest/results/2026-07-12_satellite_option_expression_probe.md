# Result — Satellite-theme LEAP option-expression feasibility probe

**Date:** 2026-07-12  **Script:** `backtest/experiments/exp_satellite_option_probe.py`  **Tag:** 🟡 feasibility check only, NOT a backtest

## Question
Karst's two-tier design gives the options toolkit (LEAP / Covered-Call→PMCC / CSP) only to
SPY/QQQ/SPMO; every Phase-3 satellite thesis name is Long-only stock. But core v2's own biggest
structural finding is that **leverage (a LEAP call, not the underlying) is what turns timing
skill into real outperformance** — premium=max-loss is a natural kill discipline, and convexity
payoff naturally "eats" the magnitude axis Phase-3 theses are explicitly betting on (the
`magnitude_tier` 2-3x / 5-10x-binary tags in `thesis/themes.yaml`). This probe asks, for a
sample of 12 satellite names: **is a long-dated call currently tradeable** (does a LEAP-length
expiry even exist, is spread/OI/IV sane), and **how does a stock-vs-option expression of the
same dollar target compare under a real, current quote**?

**This is a market-structure feasibility check on TODAY's live option chain, NOT a backtest.**
yfinance exposes only the current chain snapshot — there is no free historical options-chain
data source to backtest an overlay against (the same limitation `exp_chain_spotcheck.py`
already documented for SPY/QQQ, 2026-07-09).

## Method
- yfinance live `option_chain()` per name — **identical method** to
  `backtest/playbook_readout.py`'s LEAP-quote block and `backtest/experiments/exp_chain_spotcheck.py`:
  BSM delta (`backtest/bsm.py:call_delta`) computed from the **chain's own `impliedVolatility`**
  per strike (never an assumed/fabricated IV), `q` = trailing-12m dividend yield, `r` = ^IRX/100.
- Expiry pick: closest-to-365d within the 330–420d window (flagged `is_true_leap=True`);
  fallback = longest listed expiry if >250d (flagged `is_true_leap=False`, i.e. "not a true
  LEAP, longest available used"); if no expiry >250d exists at all → documented error, no chain.
- Strike pick: closest to 0.50Δ (the flagship LEAP delta used elsewhere in this repo).
- `leverage_multiple = delta * spot / mid` — delta-notional exposure bought per $1 of option
  premium, vs $1 of stock (which buys exactly 1.0x delta-notional). Budget-independent.
- Viability: **viable** = spread% < 10% AND OI ≥ 50; **marginal** = spread% < 25% AND OI ≥ 10;
  else **not viable**. Separately flagged when the expiry used isn't a true 330–420d LEAP.
- Ticker → theme mapping confirmed against `thesis/themes.yaml` (see table).
- Pulled 2026-07-12 ~09:38 UTC. Raw JSON provenance:
  `backtest/experiments/_satellite_option_probe_raw.json` (regenerate via the script for a
  fresh pull — chain quotes are a live snapshot, not committed data).

## Results — per-name LEAP chain (12 satellite names)

| ticker | theme | spot | expiry | DTE | true LEAP? | strike (0.50Δ) | delta | mid | spread% | OI | vol | IV | leverage | verdict |
|---|---|---:|---|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| MU   | memory-supercycle (late, cushioned; conf 0.38) | 979.30 | 2027-06-17 | 340 | ✅ | 1480 | 0.499 | 205.75 | 5.2% | 321 | 2 | 90.1% | 2.38x | **viable** |
| FSLR | us-solar-manufacturing (22nd pctile PE; conf 0.30) | 227.83 | 2027-06-17 | 340 | ✅ | 290 | 0.500 | 38.75 | 9.0% | 133 | 7 | 66.7% | 2.94x | **viable** |
| ASML | euv-lithography-monopoly (98th pctile PE; conf 0.22) | 1797.32 | 2027-06-17 | 340 | ✅ | 2200 | 0.504 | 298.60 | 5.6% | 14 | 2 | 62.5% | 3.03x | marginal |
| AVGO | tpu-custom-silicon (75–87th pctile; conf 0.25) | 399.97 | 2027-06-17 | 340 | ✅ | 470 | 0.507 | 62.05 | 6.1% | 675 | 4 | 56.2% | 3.27x | **viable** |
| ETN  | ai-power-grid / grid-hardware (99th pctile PE; conf 0.33) | 407.28 | 2027-06-17 | 340 | ✅ | 460 | 0.499 | 51.50 | 9.7% | 47 | 1 | 46.8% | 3.95x | marginal |
| TSM  | tpu-custom-silicon (eroded-incumbent; conf 0.25) | 434.11 | 2027-06-17 | 340 | ✅ | 520 | 0.492 | 64.83 | 4.6% | 1306 | 25 | 56.3% | 3.29x | **viable** |
| WST  | glp1-biologics-packaging (71st pctile PE; conf 0.27) | 353.71 | 2027-12-17 | 523 | ❌ | 430 | 0.492 | 46.25 | 9.7% | 1 | 2 | 43.9% | 3.76x | not viable (no true 12m+ LEAP) |
| LPX  | building-products / specialty-siding (95th pctile whole-co PE; conf 0.20) | 73.16 | — | — | — | — | — | — | — | — | — | — | — | **no market** — longest listed expiry = 222d |
| USAC | gas-compression-equipment (2nd pctile PE, most undiscovered; conf 0.33) | 26.48 | — | — | — | — | — | — | — | — | — | — | — | **no market** — longest listed expiry = 159d |
| ATI  | aerospace-specialty-alloys (98th pctile PE; conf 0.24) | 187.04 | 2028-01-21 | 558 | ❌ | 250 | 0.499 | 31.75 | 14.2% | 13 | 10 | 55.0% | 2.94x | marginal (no true 12m+ LEAP) |
| GEV  | ai-power-grid / grid-hardware (magnitude_tier 2-3x; conf 0.33) | 1091.57 | 2027-06-17 | 340 | ✅ | 1360 | 0.496 | 175.55 | 5.1% | 47 | 1 | 62.6% | 3.08x | marginal |
| COHR | photonics-optical (most crowded, 58% bull; conf 0.30) | 324.50 | 2028-01-21 | 558 | ❌ | 650 | 0.525 | 87.05 | 7.0% | 115 | 6 | **96.7%** | 1.96x | viable (no true 12m+ LEAP) |

10/12 names returned real, quoted chain data (exceeds the ≥8 acceptance bar). The 2 failures
are clean, documented, and directly confirm the task's own hypothesis: **LPX and USAC — the
smallest/most illiquid names in the sample — have no LEAP-length options market at all**
(longest listed expiry 222d and 159d respectively, both short of even the >250d fallback floor).

## Viability classification
- **Viable (spread<10%, OI≥50), true LEAP window:** MU, FSLR, AVGO, TSM — 4 names.
- **Viable but not a true 330–420d LEAP (longest available used instead):** COHR (558d out).
- **Marginal (spread<25%, OI≥10):** ASML, ETN, GEV (true-LEAP window); ATI (not a true LEAP).
- **Not viable:** WST (thin OI=1, and not a true LEAP).
- **No market at all:** LPX, USAC (no LEAP-length expiry exists, period).

So: **5 clean/viable, 4 marginal, 1 not-viable, 2 no-market** — a majority of this satellite
sample (9/12) has *some* tradeable long-dated call, but only a third (4/12) hit the clean
"true 12m+ LEAP + tight spread + real OI" bar simultaneously. Leverage-multiple across the
tradeable names ranges from **1.96x (COHR — rich IV drags leverage down)** to **3.95x (ETN)**.

## MU worked demonstration
Target: memory-supercycle satellite allocation. Plan A = all-stock. Plan B = premium into the
0.50Δ LEAP call (2027-06-17, strike 1480, mid $205.75/share = **$20,575/contract**) + cash.
Two scenarios, **at-expiry intrinsic value only** (no fabricated IV path, no theta schedule —
real current spot $979.30 and real current quote used throughout).

**Key finding before the P&L even starts: the task's literal $1,000-premium / $3,000-total
sizing is arithmetically infeasible for MU.** A full scan of MU's own 2027-06-17 call chain
(254 strikes) found the **cheapest strike available at ANY delta** is strike 2500 (deep OTM,
Δ≈0.27), mid $91.075/share = **$9,107.50/contract** — still ~9x over the $1,000 sub-budget.
**Zero strikes** on the whole chain price under $3,000/contract. MU's own re-rating (spot
~$979, consistent with the memory-supercycle thesis's "late, cushioned" cycle_stage note) has
pushed contract-level entry cost past what a $3,000 satellite slice can hold in even one
contract. This is reported as itself the headline finding of the MU demo.

### (a) As literally specified — $1,000 premium / $2,000 cash / $3,000 total
Shown as fractional contracts (0.0486 of a contract) to answer the exact question asked.
**Explicitly illustrative only — no broker sells fractional option contracts.**

| scenario | Plan A (stock) value | Plan A P&L | Plan B option intrinsic | Plan B cash | Plan B value | Plan B P&L |
|---|---:|---:|---:|---:|---:|---:|
| MU +100% ($979.30→$1,958.60) | $6,000 | **+$3,000** | $2,326.12 | $2,000 | $4,326.12 | **+$1,326.12** |
| MU −40% ($979.30→$587.58) | $1,800 | **−$1,200** | $0 | $2,000 | $2,000 | **−$1,000** |

Max loss: Plan A = **−$3,000** (stock → $0); Plan B = **−$1,000** (premium only, cash preserved).

### (b) Realistic minimum-tradeable size — 1 whole contract
1 whole contract is the smallest **real, executable** trade. Cash sized 2x premium to preserve
the requested 1:2 premium:cash ratio → total budget scales to **$61,725** (≈20.6x the task's
nominal $3,000 satellite slice). Plan A sized to the same $61,725 for a fair comparison.

| scenario | Plan A (stock) value | Plan A P&L | Plan B option intrinsic | Plan B cash | Plan B value | Plan B P&L |
|---|---:|---:|---:|---:|---:|---:|
| MU +100% | $123,450 | **+$61,725** | $47,860.00 | $41,150 | $89,010.00 | **+$27,285.00** |
| MU −40% | $37,035 | **−$24,690** | $0 | $41,150 | $41,150 | **−$20,575.00** |

Max loss: Plan A = **−$61,725** (stock → $0); Plan B = **−$20,575** (premium only, fixed
regardless of how much further MU falls).

At realistic size, Plan B captures **44.2%** of Plan A's upside P&L ($27,285 / $61,725) while
capping max-loss exposure to **33.3%** of Plan A's ($20,575 / $61,725) — the convexity/kill-
discipline mechanism the task brief hypothesized is real and visible in the numbers, but only
once the position is scaled ~20x past the nominal satellite budget.

## Conclusions
1. **10/12 sampled names have a real, quotable option chain; 2 (LPX, USAC) have no LEAP-length
   market at all** — directly confirms the brief's own hypothesis that small/illiquid satellite
   names may be un-expressible via options.
2. Of the 10 with chain data: **4 clean-viable** (MU, FSLR, AVGO, TSM — true LEAP window, tight
   spread, real OI), **4 marginal**, **1 not-viable** (WST), **1 viable-but-not-a-true-LEAP**
   (COHR). Liquidity is workable for roughly a third of this sample, not most of it.
3. Leverage-multiple (delta-notional per $1 of premium) ranges **1.96x–3.95x** across the
   tradeable names — a real, quantified convexity benefit vs 1x for straight stock, exactly the
   mechanism the brief wanted probed.
4. **MU's own affordability, not its liquidity, is the binding constraint on the demo as
   specified.** MU is liquid (viable, OI=321, spread 5.2%) but its price has re-rated so far
   that a single 0.50Δ LEAP contract costs $20,575 — and even the cheapest strike on the entire
   chain costs $9,107.50 — vs a $3,000 (or $1,000-premium) target. The literal sizing only works
   as a fractional-contract illustration; a real, executable trade requires scaling the whole
   position to ~$61.7k (≈20.6x nominal) before you can buy even 1 contract.
5. At that realistic scale, the mechanism the brief hypothesized **does hold**: Plan B captures
   ~44% of Plan A's upside while capping max-loss to ~33% of Plan A's max-loss, with a fixed
   floor on the downside regardless of how much further the stock falls (Plan A −$24,690 and
   still falling if MU drops further; Plan B fixed at −$20,575 no matter how far MU falls).
6. **IV richness**: COHR is the most expensive name in the sample (IV 96.7%, dragging its
   leverage-multiple down to the sample's lowest, 1.96x) — richer than even MU (90.1%, 2nd
   richest). Both are notably above the rest of the sample (43.9%–66.7%), consistent with COHR
   being flagged the "most crowded cluster, 58% bull" thesis and MU being the most-advanced/
   already-priced-in name of this batch.

## Caveats / open risk (explicit boundary)
- **This is a feasibility check on TODAY's live chain, not a backtest.** yfinance exposes only
  the current option-chain snapshot; there is no free historical-options-chain data source, so
  none of this can be validated against how spreads/OI/leverage would have behaved historically
  or through a drawdown — the same limitation already documented in
  `2026-07-09_options_chain_spotcheck.md` for SPY/QQQ.
- **Theta / time decay is NOT modeled.** The MU demo values the option at expiry using intrinsic
  value only (`max(S_new − K, 0) × 100`); it deliberately does not simulate any price path or
  a decay schedule, since doing so would require assuming an IV path — and the brief explicitly
  forbids fabricating IV ("唔准老作 IV"). Real P&L before expiry would differ (theta drag,
  vega moves), especially since both MU and COHR sit in rich-IV territory.
- **No IV was invented anywhere in this probe** — every delta, spread, and leverage number uses
  the option chain's own quoted `impliedVolatility`, matching repo precedent
  (`playbook_readout.py`, `exp_chain_spotcheck.py`).
- **Single snapshot, one point in time** (2026-07-12 ~09:38 UTC) — spreads/OI/IV are known to
  move intraday and are not averaged across multiple pulls; a name flagged "marginal" today
  could flip either direction on a different day.
- **Granularity / lumpiness is the real practical blocker, distinct from liquidity.** Even for
  liquid, viable names, whole-contract sizing means options can't be fractionally scaled the way
  stock can. For MU specifically the minimum tradeable option position ($20,575 premium) is
  ~7x the repo's own typical satellite-basket sizing convention noted in `themes.yaml`
  (~$10–15k), let alone the task's nominal $3,000 example — so a LEAP expression of MU today
  would need to be an outsized, concentrated single-name bet, not a small satellite slice.
  Cheaper-priced names in this sample are closer to fitting a realistic satellite budget: ATI
  ($3,175/contract) and FSLR ($3,875/contract) are the closest to affordable at typical satellite
  sizing, still above a literal $1,000 premium but far more tractable than MU/GEV/ASML
  ($17.6k–$29.9k/contract).
- **Recommended next step**: paper-trade in parallel — run a stock-book and an options-book
  bookkeeping side by side (starting from a realistically-sized, whole-contract position, not
  the fractional-contract illustration) for a subset of the viable names (MU, FSLR, AVGO, TSM)
  to observe real slippage, theta drag, and roll behavior over time, since none of that can be
  backtested with data available today.
