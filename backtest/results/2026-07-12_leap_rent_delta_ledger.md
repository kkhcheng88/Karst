# Result — LEAP "beta warehouse rent" + delta-notional ledger (real chain, 2026-07-12)

**Date:** 2026-07-12  **Script:** `backtest/experiments/exp_leap_rent.py`  **Tag:** 🟢 answers both
asked questions with real numbers; capital-efficiency finding materially favors the 0.50Δ flagship

## Question
Core v2's design replaces SPY/QQQ spot beta with LEAP calls (no spot holding) to free capital for
thesis/defensive sleeves. Two numbers were needed from TODAY's real chain: (1) the annualized
**"rent"** (time-value drag) of carrying beta via LEAP instead of spot, at Δ≈0.80 (stock
replacement) and Δ≈0.50 (flagship convexity, core v2's actual pick); (2) whether the resulting
**delta-notional ledger** is even feasible — how much premium (% NAV) is needed to hit a target
overall portfolio delta of 100/115/130%, given a ballast+thesis sleeve base.

## Method
- yfinance live `option_chain()` snapshot, SPY (vs ^VIX) and QQQ (vs ^VXN), pulled **2026-07-12
  ~11:42 UTC**.
- Provenance: SPY spot **$754.95**, QQQ spot **$725.51**, VIX **15.03**, VXN **24.89**, r (^IRX)
  **3.695%**, q (trailing-12m dividend yield): SPY 1.00%, QQQ 0.42%.
- Expiry: nearest standard monthly in the **365–456 day window (12–15mo)**, closest to a 410d
  midpoint target → both legs landed on **2027-09-17 (T=432 calendar days, ≈14.2 months)**. (The
  2027-06-30 expiry used by the 2026-07-09 spotcheck is now only 353 days out — outside this
  window's 365d floor — so this pull necessarily uses a different, slightly longer-dated expiry.)
- Delta computed per-strike from the chain's own `impliedVolatility` via BSM
  (`backtest/bsm.py:call_delta`), identical methodology to
  `backtest/experiments/exp_chain_spotcheck.py` (the script behind
  `2026-07-09_options_chain_spotcheck.md`), so IV/skew results are directly comparable.
- **Rent, primary definition (as specified):** `time_value / spot`, annualized by linear pro-rata
  scaling `× (365.25 / T_days)` — i.e., a straight-line average rate, NOT a theta-decay curve
  (time value does not decay linearly; front-loaded vs back-loaded decay is a caveat below).
- **Rent, delta-adjusted definition (added):** `time_value / (delta × spot)` — cost per unit of
  delta-notional actually carried, same annualization. Added because the primary definition
  divides by full spot notional even at 0.50Δ, where only half a "share" of delta backs the
  premium — this second lens answers "what does it cost to carry $1 of delta exposure," which
  matters more for the AA arithmetic below.
- **Leverage:** `delta × spot / premium_mid` (delta-notional obtained per $1 of premium paid).
- Raw JSON dump: `backtest/experiments/_leap_rent_raw.json` (not committed data — provenance only,
  regenerate via the script for a fresh pull).

## Results — 1 | Chain legs

### SPY (spot $754.95, VIX=15.03, q=1.00%, expiry 2027-09-17, T=432d)
| target Δ | strike | actual Δ | bid | ask | mid | intrinsic | time value | IV | OI | spread % of mid |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.80 | 600 | 0.800 | 193.31 | 198.00 | **195.655** | 154.950 | 40.705 | 35.14% | 207 | 2.40% |
| 0.50 | 800 | 0.496 | 51.44 | 51.53 | **51.485** | 0.000 | 51.485 | 21.30% | 201 | 0.17% |

### QQQ (spot $725.51, VXN=24.89, q=0.42%, expiry 2027-09-17, T=432d)
| target Δ | strike | actual Δ | bid | ask | mid | intrinsic | time value | IV | OI | spread % of mid |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.80 | 570 | 0.798 | 204.63 | 208.50 | **206.565** | 155.510 | 51.055 | 41.13% | 1,535 | 1.87% |
| 0.50 | 795 | 0.497 | 62.71 | 66.59 | **64.650** | 0.000 | 64.650 | 29.63% | 1,088 | 6.00% |

Note: at 0.50Δ both legs are struck OTM (strike > spot), so 100% of premium is time value; at
0.80Δ both legs are deep ITM, so most premium is intrinsic (money already "spent" on the
in-the-moneyness, not on time). QQQ's 0.50Δ spread (6.0% of mid) is materially wider than SPY's
(0.17%) — SPY LEAP liquidity at this tenor/strike is far better; QQQ 0.50Δ execution risk is real.

## Results — 2 | Rent (annualized, both definitions)

| leg | Δ | rent = TV/spot (raw) | **rent annualized** | rent = TV/(Δ×spot) (raw) | **rent/Δ-notional annualized** |
|---|---|---|---|---|---|
| SPY | 0.80 | 5.39% | **4.56%** | 6.74% | **5.70%** |
| SPY | 0.50 | 6.82% | **5.77%** | 13.76% | **11.64%** |
| QQQ | 0.80 | 7.04% | **5.95%** | 8.82% | **7.45%** |
| QQQ | 0.50 | 8.91% | **7.53%** | 17.94% | **15.17%** |

**Headline rent (primary definition, time value ÷ spot notional, annualized):**
- SPY: 4.56% (0.80Δ) / 5.77% (0.50Δ)
- QQQ: 5.95% (0.80Δ) / 7.53% (0.50Δ)

**Delta-adjusted rent (cost per $1 of delta-notional actually carried) is roughly 2× higher at
0.50Δ than at 0.80Δ for both underlyings** (SPY 11.64% vs 5.70%; QQQ 15.17% vs 7.45%). This
looks like it contradicts the headline number, but it doesn't — it's a different question. The
primary metric answers "what % of $1 of *underlying* does the LEAP cost extra, per year" (fair
for the stock-replacement 0.80Δ framing, where you really are approximating 1 share). The
delta-adjusted metric answers "what % of $1 of *delta exposure actually held* does the LEAP cost,
per year" (the right lens for the 0.50Δ flagship, since at 0.50Δ you only hold half a share's
worth of delta per option). Both are reported so neither reading is hidden.

## Results — 3 | Leverage (delta-notional per $1 of premium)

| leg | Δ | leverage |
|---|---|---|
| SPY | 0.80 | **3.09×** |
| SPY | 0.50 | **7.27×** |
| QQQ | 0.80 | **2.80×** |
| QQQ | 0.50 | **5.57×** |

0.50Δ delivers ~2.3–2.4× more delta-notional per premium dollar than 0.80Δ, on both underlyings —
this is the capital-efficiency case for the flagship strike, and it's a *separate, additive*
reason to prefer 0.50Δ beyond the skew argument below (it directly drives the AA premium-budget
result in section 5).

## Results — 4 | Skew cross-check vs `2026-07-09_options_chain_spotcheck.md`

| leg | date | expiry (T) | 0.50Δ IV | 0.70Δ IV | 0.80Δ IV | Δ(0.80−0.50) |
|---|---|---|---|---|---|---|
| SPY | 2026-07-09 | 2027-06-30 (356d) | 20.6% | 27.5% | 33.5% | **+12.9pp** |
| SPY | 2026-07-12 (this run) | 2027-09-17 (432d) | 21.3% | — | 35.1% | **+13.8pp** |
| QQQ | 2026-07-09 | 2027-06-30 (356d) | 29.5% | 35.1% | 39.9% | **+10.4pp** |
| QQQ | 2026-07-12 (this run) | 2027-09-17 (432d) | 29.6% | — | 41.1% | **+11.5pp** |

**The put-skew-premium finding at 0.70–0.80Δ is still confirmed**, 3 days later and on a
different (longer-dated, +76d) expiry: 0.80Δ IV sits 13.8pp (SPY) / 11.5pp (QQQ) above 0.50Δ IV,
essentially unchanged in magnitude from the 2026-07-09 read (+12.9pp / +10.4pp) despite VIX
falling from 16.9→15.0 and VXN from 27.9→24.9 in between. Skew is a stable structural feature of
the chain, not a transient artifact of that one snapshot.

**Reconciling skew with the rent finding above:** 0.80Δ carries *higher* IV (skew-loaded) yet
*lower* rent-per-delta-notional than 0.50Δ. Both are true because they're driven by different
mechanics — skew is a vol-surface fact (deep ITM calls inherit the low-strike put bid via
put-call parity), while rent-per-delta is a moneyness/leverage fact (a 0.50Δ option is ~100% time
value against only half a share of delta, so its time-value cost is spread over a smaller delta
base than the intrinsic-heavy 0.80Δ option's). The skew argument and the capital-efficiency
argument both point the same direction on 0.80Δ's downside (expensive vol) but pull in *opposite*
directions on rent-per-delta (0.80Δ is cheaper per unit of delta carried) — the AA arithmetic
below resolves this by using leverage (delta-notional/$premium), which is the metric that
actually determines the premium budget.

## Results — 5 | AA arithmetic table

**Base sleeve delta** (ballast 45% × β0.55 + thesis 25% × β1.20):
`0.45 × 0.55 + 0.25 × 1.20 = 0.2475 + 0.30 = 0.5475 → 54.75%`

(Note: the brief's illustrative figure was "55.75%" — verified arithmetic on the stated weights/
betas gives **54.75%**; using the correct figure below. If the intended ballast/thesis
weights or betas differ from 45%/0.55 and 25%/1.20, the needed-from-LEAP figures shift 1:1 with
any change to this base number.)

LEAP delta needed = target − 54.75%, split 50/50 SPY/QQQ. Premium % NAV = (per-leg delta needed) ÷
leverage.

| target delta | needed from LEAP | per leg (SPY=QQQ) | **premium at 0.80Δ (SPY+QQQ)** | **premium at 0.50Δ (SPY+QQQ)** |
|---|---|---|---|---|
| **100%** | 45.25% | 22.625% each | 7.33% + 8.07% = **15.40% NAV** | 3.11% + 4.06% = **7.17% NAV** |
| **115%** | 60.25% | 30.125% each | 9.76% + 10.75% = **20.51% NAV** | 4.15% + 5.41% = **9.55% NAV** |
| **130%** | 75.25% | 37.625% each | 12.19% + 13.42% = **25.61% NAV** | 5.18% + 6.75% = **11.93% NAV** |

**115% target (core v2's actual number) needs ~9.55% of NAV in premium at 0.50Δ vs ~20.51% at
0.80Δ — 0.50Δ is not just the skew-cleaner choice, it is ~2.1× more capital-efficient**, leaving
~90% of NAV free for ballast collateral / thesis sleeve / cash, vs ~80% at 0.80Δ. This is the
strongest single number in this ledger for why core v2 picked the 0.50Δ flagship over the
0.80Δ stock-replacement variant.

**Bear case — LEAP delta → 0** (deep OTM after a crash-through-strike, or LEAP rolled off/
liquidated before renewal, or written to zero): portfolio delta floor = ballast + thesis only =
**54.75%**, regardless of which delta-choice or target was used to size the LEAP legs. At a 115%
target this is a **−60.25pp** collapse entirely on the LEAP legs (by design — that's exactly the
delta the LEAP legs were sized to contribute). This is the raw arithmetic floor, not a
probability-weighted or path-dependent estimate — it does not model how fast/likely a LEAP goes
to zero delta, gap risk, or partial (not full) delta erosion in an actual drawdown.

## Conclusions
1. **Rent (primary definition, time value ÷ spot, annualized):** SPY 4.56% (0.80Δ) / 5.77%
   (0.50Δ); QQQ 5.95% (0.80Δ) / 7.53% (0.50Δ). On a delta-adjusted basis (cost per $1 of delta
   actually carried) the 0.50Δ leg costs roughly 2× more than 0.80Δ (SPY 11.64% vs 5.70%; QQQ
   15.17% vs 7.45%) — a real, honest tradeoff, not free convexity.
2. **But the 0.50Δ flagship wins decisively on capital efficiency**: 7.27× (SPY) / 5.57× (QQQ)
   delta-notional per $ premium vs 3.09× / 2.80× at 0.80Δ. Hitting the 115% target delta needs
   ~9.55% of NAV in premium at 0.50Δ vs ~20.51% at 0.80Δ.
3. **Skew still confirms the 2026-07-09 spotcheck finding**, on a fresh pull 3 days later and a
   different (further-out) expiry: 0.80Δ IV sits ~12–14pp above 0.50Δ IV on both underlyings,
   essentially unchanged in magnitude even though VIX/VXN both fell meaningfully in between.
4. **Net read**: three independent lenses (skew cost, rent-per-delta, capital efficiency) do NOT
   all point the same way — skew and rent-per-delta both make 0.80Δ look *cheaper* per unit of
   delta than 0.50Δ, while leverage/capital-efficiency (the metric that actually gates the AA
   premium budget) makes 0.50Δ dramatically more affordable in absolute NAV terms. Core v2's
   0.50Δ choice is defensible on the budget-feasibility axis specifically, not on a "cheaper
   vol" axis — that distinction should stay explicit in any writeup that cites this ledger.
5. **Bear-case floor**: if LEAP delta fully collapses, portfolio delta reverts to the 54.75%
   ballast+thesis floor (recomputed; brief's "55.75%" appears to be an arithmetic slip) — a raw
   arithmetic floor, not a stress-scenario probability estimate.

## Caveats / open risk (explicit boundary)
- **Single snapshot, single day (2026-07-12 ~11:42 UTC)** — no averaging across days, no
  historical IV-surface path. Same limitation as the 2026-07-09 spotcheck: this can confirm
  today's chain shape but cannot see crash-time term structure or how rent/leverage move when
  VIX/VXN spike.
- **Mid price is not a fill price.** QQQ's 0.50Δ leg has a 6.0% bid/ask spread as % of mid — real
  execution will be worse than the mid-based premium % NAV figures above, especially at size.
  SPY's spreads are tight (≤2.4%) and much closer to a realistic fill.
- **Rent annualization is linear pro-rata**, not a theta-decay curve — real time-value decay
  accelerates as expiry approaches (especially in the final ~60-90 days), so the 432-day-average
  annualized rate understates near-term carry cost early in the LEAP's life and overstates it late
  in the life. This ledger reports an average, not a decay schedule.
- **Expiry differs from the 2026-07-09 spotcheck** (2027-09-17 / 432d here vs 2027-06-30 / 356d
  there) because the 12-15mo window's 365d floor excludes the older expiry as of today. The skew
  cross-check in section 4 is therefore a same-direction confirmation on a different date/tenor,
  not an apples-to-apples same-expiry comparison.
- **AA base-sleeve inputs (45%/0.55, 25%/1.20) are the brief's illustrative assumptions**, not
  fitted/validated betas — if core v2's actual ballast/thesis composition differs, rerun
  `aa_table()` in the script with the correct weights/betas; the needed-from-LEAP and premium
  figures scale directly off `base_delta`.
- Does not address the already-flagged, still-open crash-vega/term-structure underestimate from
  the adversarial addendum (constant-m maps 30d vol spikes 1:1 into 1y, which is wrong in a
  crash) — this ledger is a capital/rent accounting exercise on TODAY's calm-market chain, not a
  crash-scenario repricing.
