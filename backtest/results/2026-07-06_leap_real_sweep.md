# Result — LEAP real-data sweep: delta x gate x frame on real ^VIX/^VXN + real total returns

**Date:** 2026-07-06  **Script:** `backtest/experiments/exp_leap_real_sweep.py`  **Status:** active (supersedes the RV-proxy sandbox draft `exp_leap_delta_sweep.py` / `2026-07-06_leap_delta_sweep.md`)

## Question

Which LEAP delta {0.30/0.50/0.70/0.80}, which gate {ALWAYS/GATED/GATED+DIP/
GATED+DIP+HYST}, which sizing frame {SLEEVE/PORTFOLIO 10%} — decided on REAL
vol-index IV (^VIX/^VXN), real dividends, real cash rates and an HK-net
total-return benchmark. Pre-registered grid; every cell reported.

## Method

- 1y LEAP call (252 td), roll @ 63 td remaining; fractional contracts; BSM via
  repo `backtest/bsm.py` (new simulator in the experiment file because
  `options_engine.simulate_leap` lacks time-varying r/q, telemetry, the
  PORTFOLIO frame and cross-foot asserts — math is repo `bsm.py` verbatim).
- IV_1y = volindex/100 x m, m in {0.85 base, 1.00, 1.15}. Repo convention not
  pinned (options_engine uses m=1.00 but flags it as vega-overstating; the
  2026-06-30 leap-timing results file recommends ~0.8x for a 1y tenor), so
  0.85 is the base with 1.00/1.15 bounding it.
- Pricing r and PORTFOLIO/SLEEVE idle-cash rate = ^IRX (13-wk T-bill)/252,
  forward-filled; `cash0` sensitivity zeroes only the cash accrual.
- BSM q = trailing-12m gross dividend yield reconstructed from adjusted-vs-raw
  close return gaps (1bp/day threshold vs rounding noise). Options priced gross.
- Benchmark = B&H total return net of HK 30% dividend withholding:
  r_net = r_adj - 0.30 x dividend component, deducted on actual ex-div days
  (exact form of the daily-drip spec). QQQ cells: main tables vs SPY net-TR
  (core benchmark), appendix vs QQQ net-TR (tool mirror).
- Execution: signal at close T -> trade at close T+1 (all gate series shifted
  1 day; rolls are calendar-mechanical at dte=63).
- Costs: % of option premium per side; charged on entry, exit and both legs of
  a roll. Sharpe = raw daily returns (repo convention, no rf subtraction).
- EffLev = median over in-position days of contracts x delta x S x 100 / NAV
  (frame-level). Theta bleed = median annualized 1-day value decay / premium
  (per-unit, same both frames). Cost drag = zero-cost-shadow CAGR - actual CAGR.
- Medians (not means) for EffLev/Theta: OTM-crash cells otherwise blow up the
  mean via near-worthless marks.

## Data provenance (backtest/data.py `load()`)

| Series | Source | Rows | From | To |
|---|---|---|---|---|
| ^IRX | yfinance | 16610 | 1960-01-04 | 2026-07-06 |
| SPY | yfinance | 8414 | 1993-01-29 | 2026-07-06 |
| SPY(adj) | yfinance(adj) | 8414 | 1993-01-29 | 2026-07-06 |
| ^VIX | yfinance | 9194 | 1990-01-02 | 2026-07-06 |
| QQQ | yfinance | 6872 | 1999-03-10 | 2026-07-06 |
| QQQ(adj) | yfinance(adj) | 6872 | 1999-03-10 | 2026-07-06 |
| ^VXN | yfinance | 6399 | 2001-01-23 | 2026-07-06 |

- SPY x ^VIX joined sim window: 1994-01-27 -> 2026-07-06 (8162 days; start = 200SMA + 252d-yield warm-up and vol-index availability).
- QQQ x ^VXN joined sim window: 2001-01-23 -> 2026-07-06 (6399 days; start = 200SMA + 252d-yield warm-up and vol-index availability).
- SPMO excluded (pre-registered): no vol index, options history too short.

## Benchmarks (B&H total return, HK 30% dividend withholding netted)

**Sanity anchor** — SPY B&H TR (HK net) 1996-01→2026-07-06: CAGR **9.84%**, Sharpe 0.58, MaxDD -55.6%  (pre-registered acceptance band 9–11%).

### SPY calendar

| Window | SPY net-TR CAGR | Sharpe | MaxDD | SPY net-TR CAGR | Sharpe | MaxDD |
|---|---|---|---|---|---|---|
| FULL 1994-01-27~2026-07-06 | +10.23% | 0.61 | -55.6% | +10.23% | 0.61 | -55.6% |
| H1 1996-2010 | +6.06% | 0.38 | -55.6% | +6.06% | 0.38 | -55.6% |
| H2 2011-2026 | +13.55% | 0.83 | -33.8% | +13.55% | 0.83 | -33.8% |
| 2016-2020 | +14.78% | 0.83 | -33.8% | +14.78% | 0.83 | -33.8% |
| 2021+ | +14.89% | 0.91 | -24.8% | +14.89% | 0.91 | -24.8% |

### QQQ calendar

| Window | SPY net-TR CAGR | Sharpe | MaxDD | QQQ net-TR CAGR | Sharpe | MaxDD |
|---|---|---|---|---|---|---|
| FULL 2001-01-23~2026-07-06 | +8.31% | 0.51 | -55.6% | +10.29% | 0.52 | -70.4% |
| H1 2001-2010 | +0.51% | 0.13 | -55.6% | -1.92% | 0.08 | -70.4% |
| H2 2011-2026 | +13.55% | 0.83 | -33.8% | +18.80% | 0.93 | -35.2% |
| 2016-2020 | +14.78% | 0.83 | -33.8% | +24.21% | 1.10 | -28.6% |
| 2021+ | +14.89% | 0.91 | -24.8% | +17.26% | 0.82 | -35.2% |

## Results — PORTFOLIO frame (main; premium budget 10% NAV, rest cash @ ^IRX)

### SPY x ^VIX — PORTFOLIO frame, FULL window (1994-01-27~2026-07-06), base setting (IV m=0.85, cost 0.5%/side, cash=^IRX)

| Δ | Gate | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | EffLev | Theta %/yr | Rolls | Expo | CostDrag pp/yr |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.30 | ALWAYS | +10.3% | 0.68 | -37.8% | +9.1pp (t+3.2) | 1.22x | +132.9% | 43 | 100% | +0.2 |
| 0.30 | GATED | +18.5% | 1.11 | -26.9% | +15.7pp (t+5.6) | 1.70x | +85.8% | 17 | 75% | +0.6 |
| 0.30 | GATED+DIP | +16.9% | 1.07 | -26.2% | +14.7pp (t+5.4) | 1.72x | +87.5% | 15 | 66% | +0.4 |
| 0.30 | GATED+DIP+HYST | +13.7% | 0.90 | -28.8% | +12.1pp (t+4.5) | 1.56x | +105.6% | 25 | 75% | +0.2 |
| 0.50 | ALWAYS | +10.9% | 0.92 | -31.7% | +7.4pp (t+4.1) | 1.03x | +64.3% | 43 | 100% | +0.2 |
| 0.50 | GATED | +14.0% | 1.20 | -15.8% | +10.6pp (t+5.9) | 1.27x | +36.1% | 17 | 75% | +0.6 |
| 0.50 | GATED+DIP | +12.9% | 1.17 | -18.3% | +10.0pp (t+5.7) | 1.29x | +36.7% | 15 | 66% | +0.4 |
| 0.50 | GATED+DIP+HYST | +12.5% | 1.11 | -16.0% | +9.4pp (t+5.3) | 1.23x | +43.8% | 25 | 75% | +0.2 |
| 0.70 | ALWAYS | +9.6% | 1.03 | -27.1% | +5.7pp (t+4.8) | 0.79x | +26.0% | 43 | 100% | +0.2 |
| 0.70 | GATED | +10.1% | 1.17 | -11.2% | +7.2pp (t+5.7) | 0.88x | +13.9% | 17 | 75% | +0.5 |
| 0.70 | GATED+DIP | +9.5% | 1.17 | -13.8% | +6.9pp (t+5.7) | 0.91x | +14.3% | 15 | 66% | +0.3 |
| 0.70 | GATED+DIP+HYST | +10.0% | 1.17 | -10.8% | +7.0pp (t+5.7) | 0.89x | +16.4% | 25 | 75% | +0.2 |
| 0.80 | ALWAYS | +8.6% | 1.06 | -23.8% | +4.8pp (t+5.2) | 0.66x | +14.7% | 43 | 100% | +0.2 |
| 0.80 | GATED | +8.3% | 1.15 | -9.5% | +5.7pp (t+5.5) | 0.71x | +8.1% | 17 | 75% | +0.5 |
| 0.80 | GATED+DIP | +7.9% | 1.16 | -11.5% | +5.6pp (t+5.6) | 0.73x | +8.7% | 15 | 66% | +0.3 |
| 0.80 | GATED+DIP+HYST | +8.6% | 1.17 | -9.5% | +5.8pp (t+5.7) | 0.71x | +9.8% | 25 | 75% | +0.2 |

### QQQ x ^VXN — PORTFOLIO frame, FULL window (2001-01-23~2026-07-06), base setting (IV m=0.85, cost 0.5%/side, cash=^IRX)

| Δ | Gate | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | EffLev | Theta %/yr | Rolls | Expo | CostDrag pp/yr |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.30 | ALWAYS | +12.9% | 0.76 | -28.1% | +11.1pp (t+3.2) | 1.16x | +125.9% | 33 | 100% | +0.2 |
| 0.30 | GATED | +18.9% | 1.06 | -27.5% | +16.6pp (t+4.8) | 1.61x | +91.1% | 17 | 74% | +0.6 |
| 0.30 | GATED+DIP | +13.5% | 0.88 | -27.5% | +11.9pp (t+3.9) | 1.48x | +99.3% | 13 | 65% | +0.4 |
| 0.30 | GATED+DIP+HYST | +15.3% | 0.92 | -27.7% | +13.5pp (t+4.1) | 1.50x | +99.2% | 17 | 73% | +0.3 |
| 0.50 | ALWAYS | +12.5% | 0.92 | -22.9% | +9.3pp (t+3.8) | 0.96x | +61.2% | 33 | 100% | +0.2 |
| 0.50 | GATED | +14.8% | 1.12 | -19.8% | +12.0pp (t+5.0) | 1.17x | +40.4% | 17 | 74% | +0.6 |
| 0.50 | GATED+DIP | +11.4% | 0.96 | -19.8% | +9.2pp (t+4.2) | 1.13x | +43.4% | 13 | 65% | +0.3 |
| 0.50 | GATED+DIP+HYST | +13.3% | 1.03 | -21.1% | +10.7pp (t+4.5) | 1.13x | +42.4% | 17 | 73% | +0.3 |
| 0.70 | ALWAYS | +10.5% | 0.97 | -18.6% | +7.1pp (t+4.2) | 0.71x | +26.5% | 33 | 100% | +0.2 |
| 0.70 | GATED | +10.7% | 1.09 | -14.1% | +8.3pp (t+4.8) | 0.81x | +15.7% | 17 | 74% | +0.5 |
| 0.70 | GATED+DIP | +8.8% | 0.98 | -16.0% | +6.8pp (t+4.2) | 0.79x | +16.7% | 13 | 65% | +0.3 |
| 0.70 | GATED+DIP+HYST | +10.2% | 1.04 | -17.8% | +7.8pp (t+4.6) | 0.79x | +16.1% | 17 | 73% | +0.2 |
| 0.80 | ALWAYS | +9.1% | 0.96 | -17.6% | +5.9pp (t+4.2) | 0.59x | +14.8% | 33 | 100% | +0.2 |
| 0.80 | GATED | +8.8% | 1.06 | -11.7% | +6.6pp (t+4.6) | 0.66x | +8.9% | 17 | 74% | +0.5 |
| 0.80 | GATED+DIP | +7.5% | 0.98 | -14.1% | +5.6pp (t+4.2) | 0.65x | +9.3% | 13 | 65% | +0.3 |
| 0.80 | GATED+DIP+HYST | +8.6% | 1.03 | -16.2% | +6.4pp (t+4.5) | 0.65x | +9.3% | 17 | 73% | +0.2 |

## Results — SLEEVE frame (100% compounding; leverage mirror, NOT the sizing recommendation)

### SPY x ^VIX — SLEEVE frame, FULL window (1994-01-27~2026-07-06), base setting (IV m=0.85, cost 0.5%/side, cash=^IRX)

| Δ | Gate | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | EffLev | Theta %/yr | Rolls | Expo | CostDrag pp/yr |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.30 | ALWAYS | -62.1% **RUIN** | 0.30 | -100.0% | +44.2pp (t+1.4) | 13.10x | +132.9% | 43 | 100% | +0.5 |
| 0.30 | GATED | +101.1% | 1.19 | -96.6% | +104.0pp (t+6.2) | 11.44x | +85.8% | 17 | 75% | +8.1 |
| 0.30 | GATED+DIP | +79.5% | 1.08 | -97.9% | +90.4pp (t+5.6) | 11.72x | +87.5% | 15 | 66% | +4.3 |
| 0.30 | GATED+DIP+HYST | +56.2% **RUIN** | 0.94 | -99.7% | +89.8pp (t+4.8) | 12.50x | +105.6% | 25 | 75% | +2.0 |
| 0.50 | ALWAYS | -20.6% **RUIN** | 0.40 | -100.0% | +15.9pp (t+0.8) | 9.84x | +64.3% | 43 | 100% | +1.1 |
| 0.50 | GATED | +77.5% | 1.17 | -88.9% | +62.6pp (t+5.7) | 8.25x | +36.1% | 17 | 75% | +7.2 |
| 0.50 | GATED+DIP | +65.7% | 1.09 | -91.0% | +56.1pp (t+5.2) | 8.42x | +36.7% | 15 | 66% | +4.0 |
| 0.50 | GATED+DIP+HYST | +66.5% | 1.04 | -88.0% | +60.2pp (t+4.9) | 9.07x | +43.8% | 25 | 75% | +2.1 |
| 0.70 | ALWAYS | +7.5% **RUIN** | 0.55 | -100.0% | +13.6pp (t+1.1) | 7.21x | +26.0% | 43 | 100% | +1.5 |
| 0.70 | GATED | +52.5% | 1.03 | -81.4% | +39.2pp (t+4.7) | 6.01x | +13.9% | 17 | 75% | +6.2 |
| 0.70 | GATED+DIP | +47.5% | 0.99 | -80.7% | +36.8pp (t+4.5) | 6.16x | +14.3% | 15 | 66% | +3.6 |
| 0.70 | GATED+DIP+HYST | +55.2% | 1.01 | -71.6% | +42.0pp (t+4.6) | 6.60x | +16.4% | 25 | 75% | +2.0 |
| 0.80 | ALWAYS | +15.3% **RUIN** | 0.59 | -100.0% | +11.2pp (t+1.1) | 6.02x | +14.7% | 43 | 100% | +1.6 |
| 0.80 | GATED | +40.5% | 0.92 | -76.7% | +29.0pp (t+3.9) | 5.04x | +8.1% | 17 | 75% | +5.7 |
| 0.80 | GATED+DIP | +38.1% | 0.90 | -75.8% | +28.3pp (t+3.9) | 5.15x | +8.7% | 15 | 66% | +3.3 |
| 0.80 | GATED+DIP+HYST | +46.4% | 0.95 | -64.1% | +33.2pp (t+4.1) | 5.51x | +9.8% | 25 | 75% | +1.9 |

### QQQ x ^VXN — SLEEVE frame, FULL window (2001-01-23~2026-07-06), base setting (IV m=0.85, cost 0.5%/side, cash=^IRX)

| Δ | Gate | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | EffLev | Theta %/yr | Rolls | Expo | CostDrag pp/yr |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.30 | ALWAYS | -74.4% **RUIN** | 0.27 | -100.0% | +34.8pp (t+0.9) | 10.92x | +125.9% | 33 | 100% | +0.3 |
| 0.30 | GATED | +109.9% | 1.23 | -95.4% | +113.1pp (t+5.7) | 10.01x | +91.1% | 17 | 74% | +8.2 |
| 0.30 | GATED+DIP | +63.5% | 0.98 | -97.3% | +84.5pp (t+4.5) | 10.31x | +99.3% | 13 | 65% | +3.7 |
| 0.30 | GATED+DIP+HYST | +59.8% **RUIN** | 0.97 | -99.1% | +89.6pp (t+4.4) | 10.22x | +99.2% | 17 | 73% | +2.2 |
| 0.50 | ALWAYS | -40.1% **RUIN** | 0.37 | -100.0% | +22.9pp (t+0.9) | 8.02x | +61.2% | 33 | 100% | +0.8 |
| 0.50 | GATED | +89.7% | 1.21 | -88.1% | +78.6pp (t+5.5) | 7.38x | +40.4% | 17 | 74% | +7.4 |
| 0.50 | GATED+DIP | +63.2% | 1.03 | -94.5% | +62.3pp (t+4.5) | 7.51x | +43.4% | 13 | 65% | +3.7 |
| 0.50 | GATED+DIP+HYST | +67.2% | 1.04 | -94.3% | +68.0pp (t+4.6) | 7.62x | +42.4% | 17 | 73% | +2.4 |
| 0.70 | ALWAYS | -8.0% **RUIN** | 0.49 | -100.0% | +21.5pp (t+1.2) | 5.92x | +26.5% | 33 | 100% | +1.2 |
| 0.70 | GATED | +62.5% | 1.08 | -79.7% | +53.5pp (t+4.8) | 5.52x | +15.7% | 17 | 74% | +6.4 |
| 0.70 | GATED+DIP | +50.2% | 0.97 | -90.2% | +45.4pp (t+4.2) | 5.60x | +16.7% | 13 | 65% | +3.4 |
| 0.70 | GATED+DIP+HYST | +55.8% | 0.99 | -88.8% | +50.4pp (t+4.3) | 5.70x | +16.1% | 17 | 73% | +2.2 |
| 0.80 | ALWAYS | +5.2% **RUIN** | 0.55 | -100.0% | +20.7pp (t+1.4) | 5.00x | +14.8% | 33 | 100% | +1.4 |
| 0.80 | GATED | +49.3% | 0.98 | -74.1% | +42.0pp (t+4.2) | 4.67x | +8.9% | 17 | 74% | +5.8 |
| 0.80 | GATED+DIP | +42.0% | 0.91 | -86.8% | +37.1pp (t+3.8) | 4.73x | +9.3% | 13 | 65% | +3.3 |
| 0.80 | GATED+DIP+HYST | +47.5% | 0.94 | -86.9% | +41.5pp (t+4.0) | 4.86x | +9.3% | 17 | 73% | +2.1 |

## Two-halves + sub-windows (PORTFOLIO frame, base setting)

### SPY — α vs SPY net-TR (t) per window

| Δ | Gate | H1 1996-2010 CAGR | α(t) | H2 2011-2026 CAGR | α(t) | 2016-2020 CAGR | α(t) | 2021+ CAGR | α(t) |
|---|---|---|---|---|---|---|---|---|---|
| 0.30 | ALWAYS | +3.5% | +2.8pp (t+0.8) | +15.7% | +14.5pp (t+3.3) | +15.5% | +13.5pp (t+1.8) | +18.5% | +18.3pp (t+2.4) |
| 0.30 | GATED | +15.2% | +13.3pp (t+3.5) | +19.0% | +16.5pp (t+3.9) | +20.2% | +20.4pp (t+2.4) | +18.4% | +14.4pp (t+2.2) |
| 0.30 | GATED+DIP | +15.2% | +13.6pp (t+3.8) | +16.1% | +14.5pp (t+3.4) | +17.9% | +18.5pp (t+2.2) | +13.6% | +11.3pp (t+1.7) |
| 0.30 | GATED+DIP+HYST | +8.1% | +7.3pp (t+2.1) | +16.7% | +15.4pp (t+3.7) | +22.6% | +22.3pp (t+2.8) | +16.0% | +14.3pp (t+2.0) |
| 0.50 | ALWAYS | +6.2% | +4.3pp (t+1.6) | +14.2% | +9.6pp (t+3.5) | +14.0% | +9.0pp (t+2.0) | +16.5% | +12.0pp (t+2.6) |
| 0.50 | GATED | +11.7% | +9.7pp (t+3.6) | +14.7% | +10.3pp (t+3.9) | +15.7% | +13.0pp (t+2.7) | +15.1% | +9.5pp (t+2.3) |
| 0.50 | GATED+DIP | +11.5% | +9.7pp (t+3.9) | +12.7% | +9.0pp (t+3.5) | +13.7% | +11.7pp (t+2.5) | +12.4% | +7.8pp (t+1.9) |
| 0.50 | GATED+DIP+HYST | +8.5% | +6.9pp (t+2.8) | +14.7% | +10.4pp (t+4.0) | +18.6% | +15.1pp (t+3.1) | +15.1% | +10.1pp (t+2.3) |
| 0.70 | ALWAYS | +6.4% | +4.2pp (t+2.4) | +11.8% | +6.3pp (t+3.7) | +12.1% | +6.3pp (t+2.2) | +13.5% | +7.8pp (t+2.7) |
| 0.70 | GATED | +8.6% | +6.9pp (t+3.6) | +10.6% | +6.5pp (t+3.7) | +11.4% | +8.2pp (t+2.6) | +11.6% | +6.6pp (t+2.3) |
| 0.70 | GATED+DIP | +8.4% | +7.0pp (t+3.9) | +9.4% | +5.8pp (t+3.3) | +9.9% | +7.4pp (t+2.4) | +10.1% | +5.8pp (t+2.1) |
| 0.70 | GATED+DIP+HYST | +7.6% | +6.0pp (t+3.3) | +11.2% | +6.8pp (t+3.8) | +13.4% | +9.7pp (t+2.9) | +12.3% | +7.2pp (t+2.5) |
| 0.80 | ALWAYS | +6.1% | +3.8pp (t+2.7) | +10.3% | +4.9pp (t+3.8) | +10.7% | +5.0pp (t+2.3) | +11.9% | +6.2pp (t+2.9) |
| 0.80 | GATED | +7.2% | +5.7pp (t+3.6) | +8.7% | +5.0pp (t+3.4) | +9.3% | +6.3pp (t+2.4) | +9.8% | +5.5pp (t+2.3) |
| 0.80 | GATED+DIP | +7.1% | +5.8pp (t+3.8) | +7.8% | +4.6pp (t+3.1) | +8.2% | +5.7pp (t+2.2) | +8.9% | +5.1pp (t+2.2) |
| 0.80 | GATED+DIP+HYST | +6.9% | +5.4pp (t+3.5) | +9.4% | +5.2pp (t+3.6) | +10.8% | +7.3pp (t+2.6) | +10.7% | +6.0pp (t+2.7) |

### QQQ — α vs SPY net-TR (t) per window

| Δ | Gate | H1 2001-2010 CAGR | α(t) | H2 2011-2026 CAGR | α(t) | 2016-2020 CAGR | α(t) | 2021+ CAGR | α(t) |
|---|---|---|---|---|---|---|---|---|---|
| 0.30 | ALWAYS | +0.7% | +1.3pp (t+0.3) | +21.4% | +15.3pp (t+3.1) | +31.0% | +21.7pp (t+2.4) | +16.6% | +10.3pp (t+1.3) |
| 0.30 | GATED | +5.4% | +5.7pp (t+1.4) | +28.3% | +22.1pp (t+4.5) | +41.7% | +32.9pp (t+3.5) | +19.0% | +13.4pp (t+1.7) |
| 0.30 | GATED+DIP | +5.3% | +5.5pp (t+1.4) | +19.0% | +14.8pp (t+3.4) | +26.4% | +21.3pp (t+2.7) | +12.6% | +7.5pp (t+1.0) |
| 0.30 | GATED+DIP+HYST | +3.2% | +3.6pp (t+0.9) | +23.8% | +18.7pp (t+4.0) | +35.6% | +29.6pp (t+3.5) | +14.9% | +9.3pp (t+1.2) |
| 0.50 | ALWAYS | +3.0% | +3.0pp (t+0.9) | +19.0% | +11.2pp (t+3.5) | +24.7% | +15.0pp (t+2.5) | +17.3% | +9.1pp (t+1.7) |
| 0.50 | GATED | +6.1% | +6.0pp (t+1.9) | +20.7% | +14.4pp (t+4.4) | +27.7% | +20.5pp (t+3.3) | +16.6% | +10.3pp (t+1.9) |
| 0.50 | GATED+DIP | +6.1% | +6.0pp (t+2.0) | +14.9% | +9.9pp (t+3.2) | +18.0% | +13.2pp (t+2.5) | +13.1% | +7.0pp (t+1.3) |
| 0.50 | GATED+DIP+HYST | +4.9% | +4.8pp (t+1.5) | +19.0% | +13.0pp (t+4.0) | +24.7% | +18.8pp (t+3.3) | +15.3% | +8.5pp (t+1.6) |
| 0.70 | ALWAYS | +3.7% | +3.4pp (t+1.4) | +15.0% | +7.7pp (t+3.6) | +18.6% | +10.2pp (t+2.6) | +14.3% | +6.6pp (t+1.8) |
| 0.70 | GATED | +5.2% | +5.0pp (t+2.1) | +14.2% | +9.0pp (t+4.0) | +18.1% | +12.6pp (t+3.0) | +13.4% | +7.8pp (t+2.0) |
| 0.70 | GATED+DIP | +5.3% | +5.1pp (t+2.3) | +11.0% | +6.6pp (t+3.1) | +12.4% | +8.2pp (t+2.2) | +11.5% | +6.2pp (t+1.6) |
| 0.70 | GATED+DIP+HYST | +4.6% | +4.4pp (t+1.8) | +13.9% | +8.6pp (t+3.8) | +16.6% | +11.6pp (t+2.9) | +13.2% | +7.3pp (t+1.9) |
| 0.80 | ALWAYS | +3.5% | +3.2pp (t+1.5) | +12.7% | +6.1pp (t+3.6) | +15.7% | +8.1pp (t+2.5) | +12.4% | +5.3pp (t+1.9) |
| 0.80 | GATED | +4.6% | +4.4pp (t+2.2) | +11.4% | +6.8pp (t+3.7) | +14.3% | +9.5pp (t+2.7) | +11.6% | +6.8pp (t+2.1) |
| 0.80 | GATED+DIP | +4.8% | +4.6pp (t+2.4) | +9.2% | +5.3pp (t+3.0) | +10.0% | +6.3pp (t+2.0) | +10.3% | +5.7pp (t+1.8) |
| 0.80 | GATED+DIP+HYST | +4.3% | +4.1pp (t+2.0) | +11.5% | +6.8pp (t+3.7) | +13.2% | +8.7pp (t+2.6) | +11.8% | +6.7pp (t+2.1) |

### SLEEVE two-halves (CAGR per window; ruin cells flagged)

**SPY**

| Δ | Gate | H1 1996-2010 | H2 2011-2026 | 2016-2020 | 2021+ | FULL MaxDD |
|---|---|---|---|---|---|---|
| 0.30 | ALWAYS | -88.0% **RUIN** | -7.2% **RUIN** | -12.8% **RUIN** | -28.1% **RUIN** | -100.0% |
| 0.30 | GATED | +56.0% | +135.6% | +176.5% | +97.2% | -96.6% |
| 0.30 | GATED+DIP | +48.3% | +103.9% | +141.0% | +64.9% | -97.9% |
| 0.30 | GATED+DIP+HYST | +2.3% **RUIN** | +111.7% | +218.8% | +72.4% | -99.7% |
| 0.50 | ALWAYS | -64.9% **RUIN** | +53.0% | +70.5% | +22.8% | -100.0% |
| 0.50 | GATED | +43.5% | +108.2% | +138.0% | +84.3% | -88.9% |
| 0.50 | GATED+DIP | +39.4% | +88.8% | +112.0% | +68.0% | -91.0% |
| 0.50 | GATED+DIP+HYST | +24.6% | +107.4% | +179.2% | +84.5% | -88.0% |
| 0.70 | ALWAYS | -39.7% **RUIN** | +72.4% | +96.7% | +48.0% | -100.0% |
| 0.70 | GATED | +29.2% | +74.8% | +96.4% | +60.4% | -81.4% |
| 0.70 | GATED+DIP | +27.6% | +65.4% | +80.5% | +55.4% | -80.7% |
| 0.70 | GATED+DIP+HYST | +27.4% | +81.3% | +120.4% | +70.4% | -71.6% |
| 0.80 | ALWAYS | -28.1% **RUIN** | +69.8% | +91.0% | +51.6% | -100.0% |
| 0.80 | GATED | +22.2% | +58.4% | +76.5% | +47.7% | -76.7% |
| 0.80 | GATED+DIP | +21.6% | +52.9% | +64.9% | +47.0% | -75.8% |
| 0.80 | GATED+DIP+HYST | +24.7% | +66.2% | +92.0% | +59.8% | -64.1% |

**QQQ**

| Δ | Gate | H1 2001-2010 | H2 2011-2026 | 2016-2020 | 2021+ | FULL MaxDD |
|---|---|---|---|---|---|---|
| 0.30 | ALWAYS | -97.6% **RUIN** | +16.0% **RUIN** | +132.3% | -50.0% **RUIN** | -100.0% |
| 0.30 | GATED | +1.9% | +231.2% | +386.6% | +115.2% | -95.4% |
| 0.30 | GATED+DIP | +2.5% | +118.9% | +179.7% | +64.4% | -97.3% |
| 0.30 | GATED+DIP+HYST | -23.8% **RUIN** | +154.9% | +295.6% | +75.4% | -99.1% |
| 0.50 | ALWAYS | -87.8% **RUIN** | +65.2% **RUIN** | +169.2% | -9.9% **RUIN** | -100.0% |
| 0.50 | GATED | +15.3% | +159.7% | +225.4% | +111.6% | -88.1% |
| 0.50 | GATED+DIP | +15.8% | +102.1% | +123.6% | +79.6% | -94.5% |
| 0.50 | GATED+DIP+HYST | -3.0% | +135.7% | +202.1% | +97.6% | -94.3% |
| 0.70 | ALWAYS | -67.8% **RUIN** | +79.4% | +152.0% | +18.6% | -100.0% |
| 0.70 | GATED | +15.6% | +101.4% | +134.0% | +88.2% | -79.7% |
| 0.70 | GATED+DIP | +16.5% | +75.9% | +83.5% | +71.6% | -90.2% |
| 0.70 | GATED+DIP+HYST | +5.1% | +99.6% | +129.4% | +89.1% | -88.8% |
| 0.80 | ALWAYS | -53.7% **RUIN** | +77.5% | +133.2% | +29.1% | -100.0% |
| 0.80 | GATED | +13.7% | +77.2% | +100.8% | +74.1% | -74.1% |
| 0.80 | GATED+DIP | +15.1% | +61.8% | +66.2% | +63.4% | -86.8% |
| 0.80 | GATED+DIP+HYST | +6.6% | +80.9% | +98.9% | +79.2% | -86.9% |

## Sensitivity (PORTFOLIO frame, FULL window) — α vs SPY net-TR (t)

### SPY

| Δ | Gate | base (m0.85, 0.5%, IRX) | IV m=1.00 | IV m=1.15 | cost 1.0%/side | cash 0% |
|---|---|---|---|---|---|---|
| 0.30 | ALWAYS | +9.1pp (t+3.2) | +6.4pp (t+2.5) | +4.7pp (t+1.9) | +8.9pp (t+3.2) | +7.0pp (t+2.5) |
| 0.30 | GATED | +15.7pp (t+5.6) | +13.4pp (t+5.3) | +11.8pp (t+4.9) | +15.2pp (t+5.4) | +13.7pp (t+4.8) |
| 0.30 | GATED+DIP | +14.7pp (t+5.4) | +12.5pp (t+5.1) | +11.0pp (t+4.7) | +14.4pp (t+5.3) | +12.6pp (t+4.6) |
| 0.30 | GATED+DIP+HYST | +12.1pp (t+4.5) | +9.7pp (t+3.9) | +8.1pp (t+3.4) | +11.9pp (t+4.5) | +10.0pp (t+3.7) |
| 0.50 | ALWAYS | +7.4pp (t+4.1) | +5.8pp (t+3.5) | +4.6pp (t+3.0) | +7.2pp (t+4.0) | +5.3pp (t+2.9) |
| 0.50 | GATED | +10.6pp (t+5.9) | +9.5pp (t+6.0) | +8.7pp (t+6.1) | +10.2pp (t+5.6) | +8.5pp (t+4.7) |
| 0.50 | GATED+DIP | +10.0pp (t+5.7) | +9.0pp (t+5.9) | +8.2pp (t+5.9) | +9.7pp (t+5.6) | +7.9pp (t+4.5) |
| 0.50 | GATED+DIP+HYST | +9.4pp (t+5.3) | +8.1pp (t+5.2) | +7.2pp (t+5.1) | +9.3pp (t+5.2) | +7.3pp (t+4.1) |
| 0.70 | ALWAYS | +5.7pp (t+4.8) | +4.9pp (t+4.6) | +4.3pp (t+4.5) | +5.5pp (t+4.7) | +3.6pp (t+3.0) |
| 0.70 | GATED | +7.2pp (t+5.7) | +6.6pp (t+6.1) | +6.2pp (t+6.5) | +6.7pp (t+5.4) | +5.0pp (t+3.9) |
| 0.70 | GATED+DIP | +6.9pp (t+5.7) | +6.4pp (t+6.1) | +6.0pp (t+6.5) | +6.6pp (t+5.5) | +4.7pp (t+3.8) |
| 0.70 | GATED+DIP+HYST | +7.0pp (t+5.7) | +6.4pp (t+5.9) | +5.9pp (t+6.2) | +6.8pp (t+5.5) | +4.8pp (t+3.9) |
| 0.80 | ALWAYS | +4.8pp (t+5.2) | +4.3pp (t+5.2) | +3.9pp (t+5.3) | +4.6pp (t+5.0) | +2.7pp (t+2.8) |
| 0.80 | GATED | +5.7pp (t+5.5) | +5.4pp (t+6.0) | +5.1pp (t+6.4) | +5.3pp (t+5.1) | +3.6pp (t+3.4) |
| 0.80 | GATED+DIP | +5.6pp (t+5.6) | +5.3pp (t+6.1) | +5.0pp (t+6.5) | +5.4pp (t+5.3) | +3.5pp (t+3.4) |
| 0.80 | GATED+DIP+HYST | +5.8pp (t+5.7) | +5.4pp (t+6.1) | +5.1pp (t+6.5) | +5.7pp (t+5.6) | +3.7pp (t+3.6) |

### QQQ

| Δ | Gate | base (m0.85, 0.5%, IRX) | IV m=1.00 | IV m=1.15 | cost 1.0%/side | cash 0% |
|---|---|---|---|---|---|---|
| 0.30 | ALWAYS | +11.1pp (t+3.2) | +7.1pp (t+2.4) | +4.5pp (t+1.7) | +10.9pp (t+3.2) | +9.6pp (t+2.8) |
| 0.30 | GATED | +16.6pp (t+4.8) | +13.1pp (t+4.6) | +10.7pp (t+4.2) | +16.1pp (t+4.7) | +15.1pp (t+4.4) |
| 0.30 | GATED+DIP | +11.9pp (t+3.9) | +9.2pp (t+3.6) | +7.4pp (t+3.3) | +11.6pp (t+3.8) | +10.4pp (t+3.4) |
| 0.30 | GATED+DIP+HYST | +13.5pp (t+4.1) | +10.1pp (t+3.7) | +7.9pp (t+3.2) | +13.3pp (t+4.1) | +12.0pp (t+3.6) |
| 0.50 | ALWAYS | +9.3pp (t+3.8) | +6.9pp (t+3.3) | +5.2pp (t+2.8) | +9.1pp (t+3.8) | +7.8pp (t+3.2) |
| 0.50 | GATED | +12.0pp (t+5.0) | +10.3pp (t+5.1) | +9.0pp (t+5.1) | +11.6pp (t+4.9) | +10.5pp (t+4.4) |
| 0.50 | GATED+DIP | +9.2pp (t+4.2) | +7.8pp (t+4.2) | +6.7pp (t+4.2) | +8.9pp (t+4.0) | +7.7pp (t+3.4) |
| 0.50 | GATED+DIP+HYST | +10.7pp (t+4.5) | +8.8pp (t+4.5) | +7.5pp (t+4.4) | +10.5pp (t+4.5) | +9.2pp (t+3.9) |
| 0.70 | ALWAYS | +7.1pp (t+4.2) | +5.8pp (t+4.0) | +4.9pp (t+3.7) | +6.9pp (t+4.1) | +5.6pp (t+3.3) |
| 0.70 | GATED | +8.3pp (t+4.8) | +7.4pp (t+5.1) | +6.7pp (t+5.3) | +7.8pp (t+4.6) | +6.7pp (t+3.9) |
| 0.70 | GATED+DIP | +6.8pp (t+4.2) | +6.0pp (t+4.4) | +5.5pp (t+4.6) | +6.5pp (t+4.1) | +5.2pp (t+3.2) |
| 0.70 | GATED+DIP+HYST | +7.8pp (t+4.6) | +6.9pp (t+4.7) | +6.2pp (t+4.9) | +7.6pp (t+4.5) | +6.3pp (t+3.6) |
| 0.80 | ALWAYS | +5.9pp (t+4.2) | +5.0pp (t+4.1) | +4.4pp (t+4.1) | +5.7pp (t+4.1) | +4.4pp (t+3.1) |
| 0.80 | GATED | +6.6pp (t+4.6) | +6.0pp (t+4.9) | +5.6pp (t+5.2) | +6.2pp (t+4.4) | +5.1pp (t+3.5) |
| 0.80 | GATED+DIP | +5.6pp (t+4.2) | +5.1pp (t+4.4) | +4.7pp (t+4.7) | +5.4pp (t+4.0) | +4.1pp (t+3.0) |
| 0.80 | GATED+DIP+HYST | +6.4pp (t+4.5) | +5.8pp (t+4.7) | +5.3pp (t+5.0) | +6.3pp (t+4.4) | +4.9pp (t+3.4) |

SLEEVE-frame sensitivity is not tabulated (SLEEVE is the leverage mirror, not the
sizing recommendation; the decision frame is PORTFOLIO). Reproducible by re-running
the script.

## QQQ appendix — vs QQQ B&H net-TR (tool mirror), PORTFOLIO frame, base

| Δ | Gate | FULL CAGR | FULL α_QQQ(t) | H1 2001-2010 α_QQQ(t) | H2 2011-2026 α_QQQ(t) | 2016-2020 α_QQQ(t) | 2021+ α_QQQ(t) |
|---|---|---|---|---|---|---|---|
| 0.30 | ALWAYS | +12.9% | +10.0pp (t+3.0) | +1.3pp (t+0.3) | +12.1pp (t+2.6) | +16.4pp (t+1.9) | +8.6pp (t+1.2) |
| 0.30 | GATED | +18.9% | +15.6pp (t+4.7) | +5.8pp (t+1.4) | +18.9pp (t+4.1) | +27.9pp (t+3.1) | +12.1pp (t+1.6) |
| 0.30 | GATED+DIP | +13.5% | +11.2pp (t+3.7) | +5.6pp (t+1.5) | +12.4pp (t+3.0) | +18.3pp (t+2.4) | +6.3pp (t+0.9) |
| 0.30 | GATED+DIP+HYST | +15.3% | +12.6pp (t+4.0) | +3.7pp (t+0.9) | +15.9pp (t+3.6) | +26.0pp (t+3.2) | +7.9pp (t+1.1) |
| 0.50 | ALWAYS | +12.5% | +8.4pp (t+3.8) | +3.1pp (t+1.0) | +8.5pp (t+3.0) | +10.1pp (t+2.0) | +8.3pp (t+1.7) |
| 0.50 | GATED | +14.8% | +11.4pp (t+5.0) | +6.1pp (t+2.0) | +11.9pp (t+4.0) | +16.3pp (t+2.9) | +9.5pp (t+1.9) |
| 0.50 | GATED+DIP | +11.4% | +8.7pp (t+4.1) | +6.1pp (t+2.1) | +7.9pp (t+2.8) | +10.4pp (t+2.1) | +6.4pp (t+1.3) |
| 0.50 | GATED+DIP+HYST | +13.3% | +10.1pp (t+4.5) | +5.0pp (t+1.6) | +10.6pp (t+3.6) | +15.4pp (t+2.9) | +7.7pp (t+1.6) |
| 0.70 | ALWAYS | +10.5% | +6.4pp (t+4.3) | +3.6pp (t+1.6) | +5.5pp (t+3.2) | +6.0pp (t+1.9) | +6.3pp (t+2.1) |
| 0.70 | GATED | +10.7% | +7.8pp (t+4.8) | +5.2pp (t+2.2) | +7.2pp (t+3.6) | +9.3pp (t+2.5) | +7.4pp (t+2.1) |
| 0.70 | GATED+DIP | +8.8% | +6.4pp (t+4.2) | +5.2pp (t+2.4) | +5.1pp (t+2.6) | +5.8pp (t+1.7) | +5.8pp (t+1.6) |
| 0.70 | GATED+DIP+HYST | +10.2% | +7.4pp (t+4.6) | +4.6pp (t+2.0) | +6.8pp (t+3.4) | +8.7pp (t+2.4) | +6.9pp (t+2.0) |
| 0.80 | ALWAYS | +9.1% | +5.3pp (t+4.5) | +3.3pp (t+1.8) | +4.2pp (t+3.3) | +4.4pp (t+1.8) | +5.1pp (t+2.4) |
| 0.80 | GATED | +8.8% | +6.3pp (t+4.6) | +4.5pp (t+2.3) | +5.3pp (t+3.2) | +6.6pp (t+2.2) | +6.4pp (t+2.2) |
| 0.80 | GATED+DIP | +7.5% | +5.4pp (t+4.2) | +4.7pp (t+2.5) | +4.0pp (t+2.5) | +4.1pp (t+1.4) | +5.5pp (t+1.9) |
| 0.80 | GATED+DIP+HYST | +8.6% | +6.1pp (t+4.5) | +4.2pp (t+2.1) | +5.3pp (t+3.2) | +6.1pp (t+2.0) | +6.4pp (t+2.3) |

## Ranking stability (PORTFOLIO, top-3 cells by α vs SPY net-TR)

**SPY**

- [base][FULL 1994-01-27~2026-07-06]: 0.30Δ GATED (+15.7pp (t+5.6)), 0.30Δ GATED+DIP (+14.7pp (t+5.4)), 0.30Δ GATED+DIP+HYST (+12.1pp (t+4.5))
- [base][H1 1996-2010]: 0.30Δ GATED+DIP (+13.6pp (t+3.8)), 0.30Δ GATED (+13.3pp (t+3.5)), 0.50Δ GATED+DIP (+9.7pp (t+3.9))
- [base][H2 2011-2026]: 0.30Δ GATED (+16.5pp (t+3.9)), 0.30Δ GATED+DIP+HYST (+15.4pp (t+3.7)), 0.30Δ ALWAYS (+14.5pp (t+3.3))
- [base][2016-2020]: 0.30Δ GATED+DIP+HYST (+22.3pp (t+2.8)), 0.30Δ GATED (+20.4pp (t+2.4)), 0.30Δ GATED+DIP (+18.5pp (t+2.2))
- [base][2021+]: 0.30Δ ALWAYS (+18.3pp (t+2.4)), 0.30Δ GATED (+14.4pp (t+2.2)), 0.30Δ GATED+DIP+HYST (+14.3pp (t+2.0))
- [iv100][FULL 1994-01-27~2026-07-06]: 0.30Δ GATED (+13.4pp (t+5.3)), 0.30Δ GATED+DIP (+12.5pp (t+5.1)), 0.30Δ GATED+DIP+HYST (+9.7pp (t+3.9))
- [iv115][FULL 1994-01-27~2026-07-06]: 0.30Δ GATED (+11.8pp (t+4.9)), 0.30Δ GATED+DIP (+11.0pp (t+4.7)), 0.50Δ GATED (+8.7pp (t+6.1))
- [cost10][FULL 1994-01-27~2026-07-06]: 0.30Δ GATED (+15.2pp (t+5.4)), 0.30Δ GATED+DIP (+14.4pp (t+5.3)), 0.30Δ GATED+DIP+HYST (+11.9pp (t+4.5))
- [cash0][FULL 1994-01-27~2026-07-06]: 0.30Δ GATED (+13.7pp (t+4.8)), 0.30Δ GATED+DIP (+12.6pp (t+4.6)), 0.30Δ GATED+DIP+HYST (+10.0pp (t+3.7))

**QQQ**

- [base][FULL 2001-01-23~2026-07-06]: 0.30Δ GATED (+16.6pp (t+4.8)), 0.30Δ GATED+DIP+HYST (+13.5pp (t+4.1)), 0.50Δ GATED (+12.0pp (t+5.0))
- [base][H1 2001-2010]: 0.50Δ GATED+DIP (+6.0pp (t+2.0)), 0.50Δ GATED (+6.0pp (t+1.9)), 0.30Δ GATED (+5.7pp (t+1.4))
- [base][H2 2011-2026]: 0.30Δ GATED (+22.1pp (t+4.5)), 0.30Δ GATED+DIP+HYST (+18.7pp (t+4.0)), 0.30Δ ALWAYS (+15.3pp (t+3.1))
- [base][2016-2020]: 0.30Δ GATED (+32.9pp (t+3.5)), 0.30Δ GATED+DIP+HYST (+29.6pp (t+3.5)), 0.30Δ ALWAYS (+21.7pp (t+2.4))
- [base][2021+]: 0.30Δ GATED (+13.4pp (t+1.7)), 0.50Δ GATED (+10.3pp (t+1.9)), 0.30Δ ALWAYS (+10.3pp (t+1.3))
- [iv100][FULL 2001-01-23~2026-07-06]: 0.30Δ GATED (+13.1pp (t+4.6)), 0.50Δ GATED (+10.3pp (t+5.1)), 0.30Δ GATED+DIP+HYST (+10.1pp (t+3.7))
- [iv115][FULL 2001-01-23~2026-07-06]: 0.30Δ GATED (+10.7pp (t+4.2)), 0.50Δ GATED (+9.0pp (t+5.1)), 0.30Δ GATED+DIP+HYST (+7.9pp (t+3.2))
- [cost10][FULL 2001-01-23~2026-07-06]: 0.30Δ GATED (+16.1pp (t+4.7)), 0.30Δ GATED+DIP+HYST (+13.3pp (t+4.1)), 0.30Δ GATED+DIP (+11.6pp (t+3.8))
- [cash0][FULL 2001-01-23~2026-07-06]: 0.30Δ GATED (+15.1pp (t+4.4)), 0.30Δ GATED+DIP+HYST (+12.0pp (t+3.6)), 0.50Δ GATED (+10.5pp (t+4.4))

## Cross-foot verification

- 384 accounting runs, 8,387,136 bar-level assertions, ALL passed:
  NAV = cash + option market value (identity); cash >= 0; NAV > 0;
  NAV_t = NAV_(t-1) + cash interest + option P&L - costs (roll-day value
  conservation, rel. tol 1e-7). Any violation raises and aborts the run.

## Conclusions

1. **Sanity anchor 命中**:SPY B&H TR(HK net)1996→2026 CAGR **9.84%**,落 pre-registered
   9–11% 收貨帶。所有結論建基於此校準嘅 benchmark。
2. **Frame:PORTFOLIO 10% 係唯一 hostable frame。** SLEEVE(100% 複利)全格 MaxDD −64%~−100%:
   ALWAYS 四個 delta 全部 ruin(MaxDD −100%,pre-registered artifact,照報);0.30Δ
   GATED+DIP+HYST 近 ruin(SPY FULL MaxDD −99.7%、QQQ −99.1%)——高槓桿 + 慢出場(HYST)
   喺 2000/2008 級數跌浪係致命組合。SLEEVE 表只當槓桿鏡讀。
3. **Gate:純 GATED(200SMA 右側閘)最穩,DIP/HYST 唔加值。** PORTFOLIO frame 下 GATED 喺
   兩個 underlying、幾乎所有窗口/敏感度都排最前(SPY FULL α +5.7pp~+15.7pp 隨 delta,
   t 全 >4.5)。GATED+DIP 一致地略輸(expo 66% vs 75%,錯過 V 型反彈再入場,QQQ 尤明顯);
   GATED+DIP+HYST ≈ GATED(2016-20 最好)但無淨增值,且喺 SLEEVE 低 delta 下係 ruin 源。
   ALWAYS 喺 PORTFOLIO 唔 ruin 但 α 最低、H1 唔顯著(t 0.3~0.8)→ **alpha 來源係個閘
   (T1 趨勢技巧),LEAP 只係兌現槓桿嘅工具**;荷包(frame)唔可以冇閘。
4. **Delta:0.30Δ 贏 pre-registered α 排名——同 sandbox draft「0.80Δ 全格贏」相反,
   呢個係同 draft 嘅最大分歧。** 0.30Δ GATED 喺 SPY 9 個 setting×window 組合中 8 個第一
   (H1 屈居 0.30Δ GATED+DIP 之後)、QQQ FULL 全部 sensitivity 第一。分歧來源判斷:
   **真 ^VIX 危機 spike**——OTM call 喺暴跌中有 vega mark 收益(crash convexity),
   RV-proxy(滯後嘅實現波動)結構性產生唔到呢塊;唔係 tax 或 data 問題。
5. **但 0.30Δ 嘅 α 水平要當上限睇,三個誠實 flag:**
   (a) **IV 映射敏感度最大**:m 0.85→1.15,SPY α +15.7→+11.8pp、QQQ +16.6→+10.7pp
       (0.80Δ 幾乎唔郁:+5.7→+5.1pp)。排名不變,但水平依賴 30d→1y 映射假設。
   (b) **日頻 β 被機械性壓低**(實測 OLS β≈0.18-0.23,delta-implied ~1.2-1.7):用
       0.85×VIX 逐日 mark 1 年期權,誇大咗 vega 對沖(VIX 日度 vol-of-vol 遠大於真 1y IV),
       daily-β 偏低 → Jensen α 偏高,低 delta(vega/premium 最大)最受惠。CAGR/MaxDD
       只依賴 roll 日 mark,受影響細得多。
   (c) **MaxDD 差 2-3 倍**:0.30Δ GATED −26.9%(SPY)/−27.5%(QQQ) vs 0.80Δ gated 格
       −9.5%~−14.1%。
6. **CAGR cross-check(唔依賴 β 分解)**:0.30Δ GATED PORTFOLIO FULL CAGR 18.5%(SPY)/
   18.9%(QQQ) vs SPY benchmark 10.2%/8.3% —— 每年 +8~+11pp 總回報差,expo 只 74-75%。
   0.70-0.80Δ gated 格 CAGR 7.5%~10.7%(貼近或略輸 B&H),但 Sharpe 1.03-1.20、
   MaxDD −9.5%~−17.8%,而且 90% NAV 坐喺現金收 ^IRX。
7. **Anchor cell vs draft**:SPY PORTFOLIO 0.80Δ GATED+DIP FULL α **+5.6pp(t+5.6)** vs
   draft +4.3pp(t3.8)→ 差 +1.3pp,**喺 ±3pp 收貨帶內**。分歧在跨-delta 排名(見 #4),
   唔在錨格水平。
8. **成本唔係決定因素(PORTFOLIO)**:drag 0.2-0.6pp/yr;0.5%→1.0%/side α 只跌 0.2-0.5pp。
   SLEEVE GATED drag 5.7-8.2pp/yr(全倉 whipsaw churn)——再一個唔用 SLEEVE 嘅理由。
   cash=0% 敏感度:α 跌 1.5-2pp、排名不變(90% 現金收息係回報結構嘅一部分)。
9. **排名穩定性(落結論紀律)**:delta 維度——0.30Δ 喺 SPY 5 個窗口 × 5 個 sensitivity
   全部佔 top-3 主導;QQQ 除 H1(0.50Δ GATED+DIP 第一,0.30Δ GATED 第三)外同樣。
   gate 維度——GATED 喺 FULL 全部第一;sub-window 有兩次俾 GATED+DIP(SPY H1)/
   GATED+DIP+HYST(SPY 2016-20)超前,幅度細。2021+ 窗口 t 值普遍弱(1.0-2.9),
   短窗照報唔落重注。

## Caveats

1. **單一歷史路徑**,美股長牛偏樣本;無 capacity/流動性/融資/assignment model。
2. **30d→1y IV 映射係假設**:^VIX/^VXN 係 30 日 ATM IV,乘常數 m 映射去 1 年 tenor;
   m∈{0.85,1.00,1.15} 敏感度包住咗「水平」不確定性,但**日度 vol-of-vol 冇得包**——
   真 1y IV 日度波動遠低於 VIX,逐日 mark 誇大 vega 效應 → daily β 偏低、Jensen α
   偏高(尤其低 delta,見 Conclusions #5b)。α 水平當上限;CAGR/MaxDD 較可靠。
3. **無真期權鏈**:無 bid-ask(成本用 premium % 近似,OTM 低 delta 實際 spread 比例
   更闊,0.30Δ 成本或被低估)、無 volatility smile/skew(deep-ITM call 行使價低,
   受 index put-skew 影響實際 IV 較高 → 0.80Δ 入場 premium 或被略低估;OTM call IV
   通常低過 ATM → 0.30Δ premium 或被略高估,方向上對 0.30Δ 有利)。
4. **European BSM,無 American early-exercise**:SPY/QQQ LEAP call 喺除息前嘅提早行使
   價值細,影響有限,但未 model。
5. **股息稅假設**:benchmark 扣 HK 30% 股息預扣;LEAP 本身唔收息(q 用 gross 定價),
   呢個「期權避稅」edge 係真實而且係設計一部分,但幅度依賴 30% 假設。
6. QQQ×^VXN 由 2001-01 起——**miss 咗 2000 年 dot-com 頂部**,H1 QQQ 只包括跌浪後半。
7. SPMO 冇入 grid(pre-registered 排除):無對應 vol index、期權史太短。
8. 閘只用日收市價,無 intraday;T+1 收市成交假設無滑價(成本項已含 0.5-1.0%/side)。

## Implication

- **Core 策略 LEAP 引擎落地規格**:PORTFOLIO frame(premium 預算 10% NAV,roll/入場時
  rebalance)+ **純 200SMA GATED**(唔使 DIP、唔使 HYST)。
- **Delta 係風險預算選擇,唔係單一答案**:0.30Δ = α/CAGR 最大化(SPY FULL α +15.7pp
  t5.6;CAGR 18.5%)但 IV-假設敏感 + MaxDD ~−27% + theta bleed ~86%/yr of premium;
  0.70-0.80Δ = hostable 檔(α +5.6~+7.2pp t>5.5,MaxDD −9.5%~−13.8%,theta 8-16%/yr)。
  中間 0.50Δ 兩邊唔輸蝕(Sharpe 最高 1.20)。
- **喺 spine 接線前要做**:用真期權鏈 spot-check 幾個 roll 日(validate 30d→1y 映射
  同 skew 影響,特別係 0.30Δ 格);同埋喺 portfolio 層面決定 delta 風險預算檔位。
- Draft(exp_leap_delta_sweep)嘅「0.80Δ 全格贏」結論**唔成立**——RV-proxy IV 冇
  crash-vega,系統性低估低 delta 嘅 convexity 價值。Draft 標記 superseded。

---

## 終審 Addendum(2026-07-06,主腦合議 + 獨立 adversarial 覆核後)

> 覆核方法:獨立 opus 覆核員,三條 refutation(月頻 β 重計 / episode 拆帳 / term-structure
> 現實檢查),自建 harness import 原函數 verbatim(原 script 未動)。詳:session scratchpad
> `loop1_adversarial_review.md` + `adv_harness.py`。

**逐條 verdict:**

| 結論 | Verdict | 關鍵數 |
|---|---|---|
| R1:0.30Δ 贏 α 排名 | **SURVIVES(排名)/ α 幅度打折 ~25%** | β-suppression 係真(daily β 0.23 → 21td 0.43 → 63td 0.70);月/季頻 α +15.8→+14.0(t4.7)→+11.9(t3.3),排名唔反轉 |
| R2:GATED 贏 GATED+DIP | **SURVIVES** | 分歧攤喺 71 個 episode,最大單一佔 23%;剔 top-3 後 wealth ratio 仍 1.23×;DIP⊆GATED(純曝險削減)|
| R3:0.30Δ headline 幅度 | **WEAKENED(命門 = term structure)** | constant-m 把 VIX crash spike 1:1 塞落 1y IV;damped-IV(damp 0.4)下 0.30Δ α +15.8→**+6.4**,對 0.80Δ 嘅 gap +10.0pp→**+2.3pp**;cost 非 swing 變量 |

**終審定案(寫入 core 策略嘅版本):**

1. **鎖定(HIGH,對 model 誤差免疫)**:LEAP + 純 200SMA GATED + PORTFOLIO 10% premium 預算
   = 真 Jensen α。最 model-免疫格(0.80Δ,vega 極細):**α +5.7pp t5.5 / MaxDD −9.5%**。
2. **鎖定**:純 GATED > GATED+DIP(dip 過濾 = 純曝險削減,miss V 型再入場)——**修訂
   scorecard v3.1 嘅「LEAP = >200SMA × RSI-2 dip」**:RSI-2 dip 唔再係 LEAP sleeve 嘅
   持有條件;初次建倉時機可仍參考,但唔好為等 dip 而空倉。
3. **0.30Δ「+15.7pp」唔准做賣點**:一半以上係 30d-VIX crash-spike 誤映射落 1y 期權嘅
   artifact;model-honest 讀法 = 0.30Δ 對 0.80Δ 淨 gap +2~4pp,買嚟嘅代價係 MaxDD 3×
  (−27% vs −10%)+ 更闊 spread + 更大 model 風險。
4. **Delta 檔位建議**:base = **0.70-0.80Δ**(hostable、羅賓斯特);進取檔 = 0.50Δ
  (Sharpe 1.20 最高,vega 中等 → α 有部分同樣要打折)。0.30Δ 檔要等真期權鏈驗證先可上桌。
5. Spine 接線前 to-do 不變:真期權鏈 spot-check roll 日(重點 0.50Δ 以下格)。
