# Oracle forensics — the capturable layer is ANNUAL regime, not weekly ranking

2026-07-01. `exp_oracle_forensics.py`. Reverse-engineered the weekly oracle (user's idea): which
sectors it picks, their alpha contribution, and the by-year pattern -> then read what regime drove
the big years. 9 core SPDR, 1999-2026.

## Pick distribution + alpha attribution
Energy (XLE) dominates: top-1 winner 22.6% of weeks (2x the 1/9 baseline), 19.6%/yr contribution.
Then XLF 14.6%, XLK 14.2%, XLB 13.1%, XLY 12.3%. Tech and Utilities also frequent single-week
winners (14.6% / 14.7% top-1). Contribution is spread, Energy-led.

## By-year dominant sector = a recognizable macro narrative
1999 XLK; 2000-03 XLK (dotcom bust/recovery); 2004-07 XLE (oil supercycle to $147);
2008-10 XLF (GFC, financials the epicentre); 2020-23 XLE (COVID + 2021-22 energy/inflation
supercycle); 2024 XLK (AI); 2025-26 XLE. Each year's dominant sector was a recognizable regime
in real time (everyone knew energy was ripping in 2022, financials imploding in 2008).

## Two layers of oracle alpha (the key finding)
- **Weekly switching**: the excess is spread across ALL years (top-5 years = only 33% of it) ->
  this is the unpredictable high-frequency NOISE, uncapturable (weekly IC ~0, established).
- **Annual sector regime**: the dominant-sector-per-year traces a recognizable macro narrative ->
  potentially capturable by MACRO / QUALITATIVE judgment, not weekly quant.

Cross-reference the frequency-collapse (rotation_challenge): the YEARLY-hold oracle = 23.5%/yr
(~2x SPY 11.2%) = the annual-regime ceiling; the jump to 151% weekly is the noise layer. So the
capturable target is a fraction of ~12pp/yr from getting the multi-month regime/sector right.

## Reframe (what this changes)
Stop chasing weekly ranking (noise, IC~0). The capturable structure is ANNUAL/multi-month regime
positioning -- overweight the sector whose macro regime is recognizable (energy = inflation/supply,
tech = innovation cycle, financials = credit cycle, utilities = risk-off/rates). Ceiling ~2x SPY.
This is a LOW-FREQUENCY macro/qualitative job = Compass `regime_matrix` + Phase 3, NOT weekly quant.
It explains why every weekly quant test failed AND gives the qualitative offense a concrete shape
with a measured ceiling.

## Next
Test an ANNUAL/quarterly REGIME TILT: with IMPERFECT (not hindsight) regime calls, how much of the
~12pp/yr annual-regime ceiling is captured? First empirical hook for Compass regime_matrix -> sectors.

## Files
New: `backtest/exp_oracle_forensics.py`.
