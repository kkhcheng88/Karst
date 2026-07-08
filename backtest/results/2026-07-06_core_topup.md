# Result — Core portfolio, Loop 4 (final): cash top-up rules to fix Loop-3's cash-starvation + full base/damp disclosure, 24-cell grid (real data)

**Date:** 2026-07-06  **Script:** `backtest/experiments/exp_core_topup.py`  **Status:** active

## Question

Loop-3 (`exp_core_assembly_real.py`) found the annual-only cash rebalance leaves the LEAP sleeve cash-starved 40-60% of trend-eligible days, and only stress-tested IV-damping on its Delta=0.50 top-3 (not Delta=0.70/0.80). This loop fixes both: (1) tests 3 higher-frequency/event-tied cash top-up rules against the annual-rebalance control, (2) runs base-IV AND damp=0.4 IV on EVERY cell. Grid: 4 top-up rules x {10%,15%} premium budget x {0.50,0.70,0.80} delta, LEAP mix FIXED to 50/50 SPY+QQQ (Loop-3's settled winner). Benchmark = SPY B&H total return, HK 30% dividend withholding netted.

## Method

- LEAP unit engine (`simulate_unit_path`) IMPORTED verbatim from `exp_leap_real_sweep.py`. Gate = pure 200SMA GATED. 1y call (252td), roll @ 63td remaining. IV_1y = vol-index/100 x 0.85 (base), real ^VIX (SPY leg) / ^VXN (QQQ leg); damp=0.4 IV via `damp_iv()` IMPORTED verbatim from `exp_core_assembly_real.py` (same adversarially-reviewed method, not redone).
- NEW in this script: the fund-replenishment RULE axis. Rule A (annual, SYMMETRIC core:cash rebalance) reproduces `exp_core_assembly_real.py`'s mechanics byte-for-byte as the control. Rules B/C/D are an ASYMMETRIC FLOOR top-up (pull cash up to b%NAV from core ONLY when short; never sell cash back down when already sufficient) fired quarterly / monthly / on-roll respectively — a liquidity-mechanics fix, not a market-timing signal.
- Core sleeve compounds at the SAME SPY net-TR series used as the Jensen-alpha benchmark, so alpha isolates the LEAP-sleeve + cash-buffer + replenishment-rule MACHINERY, not stock selection.
- Costs: 0.5%/side of option premium (base), charged on entry/exit/both legs of a roll; core-equity trades (rebalance/top-up/sweep) zero-cost (ETF shares). Sharpe = raw daily returns. CAPITAL = $500,000.
- Windows: FULL (native start of the SPY+QQQ common window, 2001+) as PRIMARY, + H2 2011-2026 / 2016-2020 / 2021+. H1 2001-2010 is dropped from the printed tables (pre-registered; see script docstring).

## Data provenance (`backtest/data.py` `load()`)

| Series | Source | Rows | From | To |
|---|---|---|---|---|
| ^IRX | yfinance | 16610 | 1960-01-04 | 2026-07-06 |
| SPY | yfinance | 8414 | 1993-01-29 | 2026-07-06 |
| SPY(adj) | yfinance(adj) | 8414 | 1993-01-29 | 2026-07-06 |
| ^VIX | yfinance | 9194 | 1990-01-02 | 2026-07-06 |
| QQQ | yfinance | 6872 | 1999-03-10 | 2026-07-06 |
| QQQ(adj) | yfinance(adj) | 6872 | 1999-03-10 | 2026-07-06 |
| ^VXN | yfinance | 6399 | 2001-01-23 | 2026-07-06 |

- Common (mix) simulation window: 2001-01-23 -> 2026-07-06 (6399 days).
- Sanity anchor — SPY B&H TR (HK net) 1996-01->2026-07-06: CAGR **9.85%**, Sharpe 0.58, MaxDD -55.6% (pre-registered acceptance band 9-11%).

## Table 1 — 24-cell grid, FULL (2001+) window, base (m0.85) AND damp=0.4 (every cell reports both — no base-only rows)

| Rule | b | Δ | IV | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) | Worst mo | TE | Dn% med/p90/max | CostDrag pp/yr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A-annual | 10% | 0.50 | base m0.85 | +13.6% | 0.73 | -55.6% | +4.8pp (t+4.0) | -31.1% | +6.2% | 0%/136%/213% | +0.2 |
| A-annual | 10% | 0.50 | damp 0.4 | +10.5% | 0.58 | -55.6% | +1.8pp (t+1.6) | -31.8% | +5.6% | 0%/112%/152% | +0.2 |
| A-annual | 10% | 0.70 | base m0.85 | +11.6% | 0.65 | -54.8% | +3.0pp (t+3.4) | -31.4% | +4.4% | 0%/89%/130% | +0.2 |
| A-annual | 10% | 0.70 | damp 0.4 | +9.9% | 0.57 | -54.7% | +1.3pp (t+1.6) | -31.9% | +4.2% | 0%/77%/93% | +0.2 |
| A-annual | 10% | 0.80 | base m0.85 | +10.7% | 0.62 | -54.4% | +2.2pp (t+3.0) | -31.6% | +3.7% | 0%/73%/101% | +0.2 |
| A-annual | 10% | 0.80 | damp 0.4 | +9.6% | 0.56 | -54.3% | +1.1pp (t+1.5) | -31.9% | +3.6% | 0%/62%/72% | +0.2 |
| A-annual | 15% | 0.50 | base m0.85 | +15.5% | 0.79 | -56.7% | +6.6pp (t+4.1) | -31.6% | +8.1% | 0%/169%/298% | +0.3 |
| A-annual | 15% | 0.50 | damp 0.4 | +11.4% | 0.60 | -56.9% | +2.5pp (t+1.8) | -31.5% | +7.4% | 0%/152%/214% | +0.2 |
| A-annual | 15% | 0.70 | base m0.85 | +12.9% | 0.69 | -55.6% | +4.1pp (t+3.5) | -31.6% | +5.9% | 0%/123%/188% | +0.3 |
| A-annual | 15% | 0.70 | damp 0.4 | +10.6% | 0.59 | -55.6% | +1.9pp (t+1.7) | -31.6% | +5.6% | 0%/108%/133% | +0.2 |
| A-annual | 15% | 0.80 | base m0.85 | +11.7% | 0.65 | -55.1% | +3.0pp (t+3.1) | -31.6% | +5.0% | 0%/105%/147% | +0.3 |
| A-annual | 15% | 0.80 | damp 0.4 | +10.2% | 0.57 | -54.9% | +1.5pp (t+1.6) | -31.6% | +4.8% | 0%/87%/104% | +0.2 |
| B-quarterly | 10% | 0.50 | base m0.85 | +16.1% | 0.82 | -55.2% | +7.0pp (t+5.0) | -37.7% | +7.1% | 55%/144%/214% | +0.3 |
| B-quarterly | 10% | 0.50 | damp 0.4 | +12.4% | 0.65 | -55.4% | +3.4pp (t+2.6) | -38.9% | +6.7% | 50%/115%/153% | +0.3 |
| B-quarterly | 10% | 0.70 | base m0.85 | +13.1% | 0.71 | -54.4% | +4.3pp (t+4.3) | -36.2% | +5.0% | 42%/95%/131% | +0.3 |
| B-quarterly | 10% | 0.70 | damp 0.4 | +11.2% | 0.62 | -54.4% | +2.4pp (t+2.6) | -36.6% | +4.8% | 36%/78%/93% | +0.3 |
| B-quarterly | 10% | 0.80 | base m0.85 | +11.8% | 0.66 | -54.0% | +3.2pp (t+3.8) | -35.4% | +4.2% | 35%/76%/102% | +0.3 |
| B-quarterly | 10% | 0.80 | damp 0.4 | +10.5% | 0.60 | -53.9% | +1.9pp (t+2.4) | -35.6% | +4.0% | 30%/63%/72% | +0.3 |
| B-quarterly | 15% | 0.50 | base m0.85 | +19.7% | 0.92 | -55.2% | +10.3pp (t+5.1) | -39.9% | +10.2% | 83%/208%/301% | +0.5 |
| B-quarterly | 15% | 0.50 | damp 0.4 | +14.2% | 0.68 | -55.7% | +4.9pp (t+2.6) | -41.6% | +9.7% | 74%/167%/217% | +0.4 |
| B-quarterly | 15% | 0.70 | base m0.85 | +15.3% | 0.78 | -54.1% | +6.3pp (t+4.4) | -37.5% | +7.3% | 63%/140%/190% | +0.5 |
| B-quarterly | 15% | 0.70 | damp 0.4 | +12.4% | 0.65 | -54.2% | +3.5pp (t+2.5) | -38.1% | +7.0% | 54%/115%/135% | +0.4 |
| B-quarterly | 15% | 0.80 | base m0.85 | +13.4% | 0.72 | -53.5% | +4.6pp (t+3.9) | -36.5% | +6.1% | 53%/111%/148% | +0.4 |
| B-quarterly | 15% | 0.80 | damp 0.4 | +11.4% | 0.63 | -53.4% | +2.7pp (t+2.4) | -36.8% | +5.8% | 44%/93%/105% | +0.4 |
| C-monthly | 10% | 0.50 | base m0.85 | +17.8% | 0.87 | -54.7% | +8.5pp (t+5.3) | -37.7% | +8.0% | 81%/150%/214% | +0.5 |
| C-monthly | 10% | 0.50 | damp 0.4 | +13.7% | 0.68 | -55.3% | +4.4pp (t+3.0) | -38.9% | +7.7% | 79%/118%/153% | +0.4 |
| C-monthly | 10% | 0.70 | base m0.85 | +14.3% | 0.75 | -54.0% | +5.3pp (t+4.8) | -36.1% | +5.6% | 58%/99%/131% | +0.4 |
| C-monthly | 10% | 0.70 | damp 0.4 | +12.1% | 0.65 | -54.4% | +3.2pp (t+3.0) | -36.6% | +5.5% | 60%/80%/93% | +0.4 |
| C-monthly | 10% | 0.80 | base m0.85 | +12.7% | 0.70 | -53.7% | +3.9pp (t+4.3) | -35.4% | +4.6% | 46%/80%/102% | +0.4 |
| C-monthly | 10% | 0.80 | damp 0.4 | +11.2% | 0.63 | -53.8% | +2.5pp (t+2.9) | -35.6% | +4.5% | 50%/64%/72% | +0.4 |
| C-monthly | 15% | 0.50 | base m0.85 | +22.3% | 0.98 | -54.5% | +12.4pp (t+5.4) | -39.8% | +11.6% | 120%/216%/301% | +0.7 |
| C-monthly | 15% | 0.50 | damp 0.4 | +16.1% | 0.72 | -55.6% | +6.5pp (t+3.1) | -41.6% | +11.2% | 118%/172%/217% | +0.6 |
| C-monthly | 15% | 0.70 | base m0.85 | +17.1% | 0.84 | -53.5% | +7.8pp (t+4.8) | -37.5% | +8.1% | 86%/144%/190% | +0.6 |
| C-monthly | 15% | 0.70 | damp 0.4 | +13.8% | 0.69 | -53.9% | +4.6pp (t+3.0) | -38.1% | +7.9% | 90%/118%/135% | +0.6 |
| C-monthly | 15% | 0.80 | base m0.85 | +14.7% | 0.76 | -52.9% | +5.7pp (t+4.3) | -36.5% | +6.7% | 68%/116%/148% | +0.6 |
| C-monthly | 15% | 0.80 | damp 0.4 | +12.5% | 0.66 | -53.1% | +3.6pp (t+2.8) | -36.8% | +6.5% | 74%/95%/105% | +0.6 |
| D-onroll | 10% | 0.50 | base m0.85 | +12.8% | 0.69 | -58.3% | +4.0pp (t+3.6) | -32.7% | +5.6% | 0%/128%/213% | +0.2 |
| D-onroll | 10% | 0.50 | damp 0.4 | +10.1% | 0.56 | -58.0% | +1.3pp (t+1.4) | -33.4% | +4.9% | 0%/107%/152% | +0.1 |
| D-onroll | 10% | 0.70 | base m0.85 | +11.2% | 0.63 | -57.4% | +2.5pp (t+3.2) | -33.0% | +4.0% | 0%/89%/130% | +0.1 |
| D-onroll | 10% | 0.70 | damp 0.4 | +9.7% | 0.56 | -57.2% | +1.0pp (t+1.4) | -33.4% | +3.7% | 0%/75%/93% | +0.1 |
| D-onroll | 10% | 0.80 | base m0.85 | +10.5% | 0.60 | -57.0% | +1.8pp (t+2.8) | -33.0% | +3.3% | 0%/68%/101% | +0.1 |
| D-onroll | 10% | 0.80 | damp 0.4 | +9.4% | 0.55 | -56.9% | +0.8pp (t+1.4) | -33.3% | +3.1% | 0%/62%/72% | +0.1 |
| D-onroll | 15% | 0.50 | base m0.85 | +14.8% | 0.75 | -59.8% | +5.9pp (t+3.7) | -32.7% | +8.1% | 0%/187%/299% | +0.2 |
| D-onroll | 15% | 0.50 | damp 0.4 | +10.8% | 0.57 | -59.4% | +1.9pp (t+1.4) | -33.6% | +7.1% | 0%/156%/215% | +0.2 |
| D-onroll | 15% | 0.70 | base m0.85 | +12.4% | 0.67 | -58.5% | +3.6pp (t+3.2) | -33.0% | +5.8% | 0%/129%/189% | +0.2 |
| D-onroll | 15% | 0.70 | damp 0.4 | +10.2% | 0.57 | -58.2% | +1.4pp (t+1.4) | -33.6% | +5.4% | 0%/110%/134% | +0.2 |
| D-onroll | 15% | 0.80 | base m0.85 | +11.4% | 0.63 | -58.0% | +2.6pp (t+2.8) | -33.1% | +4.8% | 0%/100%/148% | +0.2 |
| D-onroll | 15% | 0.80 | damp 0.4 | +9.8% | 0.56 | -57.6% | +1.1pp (t+1.3) | -33.6% | +4.5% | 0%/91%/104% | +0.2 |

## Table 2 — sub-windows (H2 2011-2026 / 2016-2020 / 2021+), base IV only (CAGR / a(t))

| Rule | b | Δ | H2 2011-2026 CAGR | α(t) | 2016-2020 CAGR | α(t) | 2021+ CAGR | α(t) |
|---|---|---|---|---|---|---|---|---|
| A-annual | 10% | 0.50 | +21.6% | +6.4pp (t+3.6) | +22.6% | +7.0pp (t+2.1) | +19.4% | +3.2pp (t+1.2) |
| A-annual | 10% | 0.70 | +18.7% | +3.7pp (t+3.0) | +19.7% | +4.1pp (t+1.9) | +18.0% | +1.8pp (t+1.0) |
| A-annual | 10% | 0.80 | +17.3% | +2.6pp (t+2.6) | +18.5% | +3.0pp (t+1.7) | +17.1% | +1.2pp (t+0.8) |
| A-annual | 15% | 0.50 | +24.6% | +8.7pp (t+3.7) | +26.5% | +10.2pp (t+2.2) | +19.5% | +3.2pp (t+1.1) |
| A-annual | 15% | 0.70 | +20.7% | +5.2pp (t+3.2) | +22.6% | +6.5pp (t+2.0) | +18.1% | +1.6pp (t+0.7) |
| A-annual | 15% | 0.80 | +19.0% | +3.7pp (t+2.8) | +20.9% | +4.9pp (t+1.9) | +17.2% | +1.0pp (t+0.5) |
| B-quarterly | 10% | 0.50 | +24.7% | +8.5pp (t+4.4) | +30.4% | +12.1pp (t+3.0) | +21.3% | +4.4pp (t+1.6) |
| B-quarterly | 10% | 0.70 | +20.5% | +4.9pp (t+3.8) | +24.4% | +7.1pp (t+2.8) | +19.0% | +2.5pp (t+1.3) |
| B-quarterly | 10% | 0.80 | +18.6% | +3.4pp (t+3.3) | +21.9% | +5.1pp (t+2.5) | +17.9% | +1.8pp (t+1.1) |
| B-quarterly | 15% | 0.50 | +30.1% | +12.5pp (t+4.5) | +37.9% | +17.8pp (t+3.1) | +24.3% | +6.6pp (t+1.7) |
| B-quarterly | 15% | 0.70 | +23.8% | +7.3pp (t+3.8) | +29.0% | +10.5pp (t+2.8) | +20.9% | +3.8pp (t+1.4) |
| B-quarterly | 15% | 0.80 | +21.0% | +5.1pp (t+3.3) | +25.3% | +7.6pp (t+2.6) | +19.2% | +2.6pp (t+1.2) |
| C-monthly | 10% | 0.50 | +26.6% | +9.7pp (t+4.5) | +32.8% | +13.9pp (t+3.3) | +25.0% | +6.7pp (t+1.9) |
| C-monthly | 10% | 0.70 | +21.7% | +5.6pp (t+4.0) | +25.9% | +8.2pp (t+3.0) | +21.6% | +4.2pp (t+1.8) |
| C-monthly | 10% | 0.80 | +19.4% | +4.0pp (t+3.5) | +23.0% | +5.9pp (t+2.7) | +19.9% | +3.1pp (t+1.6) |
| C-monthly | 15% | 0.50 | +32.8% | +14.3pp (t+4.6) | +41.6% | +20.4pp (t+3.3) | +29.9% | +10.1pp (t+2.0) |
| C-monthly | 15% | 0.70 | +25.6% | +8.4pp (t+4.0) | +31.3% | +12.1pp (t+3.0) | +24.8% | +6.3pp (t+1.8) |
| C-monthly | 15% | 0.80 | +22.3% | +5.9pp (t+3.5) | +26.9% | +8.7pp (t+2.7) | +22.3% | +4.6pp (t+1.6) |
| D-onroll | 10% | 0.50 | +20.8% | +5.5pp (t+3.3) | +23.3% | +7.3pp (t+2.2) | +19.6% | +2.8pp (t+1.2) |
| D-onroll | 10% | 0.70 | +18.2% | +3.2pp (t+2.9) | +20.3% | +4.4pp (t+2.0) | +18.3% | +1.7pp (t+1.0) |
| D-onroll | 10% | 0.80 | +17.1% | +2.3pp (t+2.5) | +19.0% | +3.2pp (t+1.9) | +17.5% | +1.2pp (t+0.9) |
| D-onroll | 15% | 0.50 | +24.2% | +8.2pp (t+3.4) | +27.2% | +10.6pp (t+2.3) | +21.9% | +4.4pp (t+1.2) |
| D-onroll | 15% | 0.70 | +20.5% | +4.8pp (t+2.9) | +22.8% | +6.4pp (t+2.1) | +19.9% | +2.6pp (t+1.0) |
| D-onroll | 15% | 0.80 | +18.8% | +3.4pp (t+2.6) | +21.0% | +4.7pp (t+1.9) | +18.8% | +1.8pp (t+0.9) |

## Table 3 — cash-starved% (base IV, FULL window; SPY-leg/QQQ-leg): "of days the leg's own 200SMA gate says eligible, fraction the sim carried 0 contracts because cash could not fund the fresh premium"

| Rule | b | Δ | SPY-leg starved% | QQQ-leg starved% | (rule-A same b/Δ, for comparison) |
|---|---|---|---|---|---|
| A-annual | 10% | 0.50 | 52% | 40% | 52%/40% |
| A-annual | 10% | 0.70 | 52% | 40% | 52%/40% |
| A-annual | 10% | 0.80 | 52% | 40% | 52%/40% |
| A-annual | 15% | 0.50 | 53% | 48% | 53%/48% |
| A-annual | 15% | 0.70 | 53% | 48% | 53%/48% |
| A-annual | 15% | 0.80 | 53% | 48% | 53%/48% |
| B-quarterly | 10% | 0.50 | 24% | 22% | 52%/40% |
| B-quarterly | 10% | 0.70 | 24% | 22% | 52%/40% |
| B-quarterly | 10% | 0.80 | 24% | 22% | 52%/40% |
| B-quarterly | 15% | 0.50 | 24% | 22% | 53%/48% |
| B-quarterly | 15% | 0.70 | 24% | 22% | 53%/48% |
| B-quarterly | 15% | 0.80 | 24% | 22% | 53%/48% |
| C-monthly | 10% | 0.50 | 10% | 7% | 52%/40% |
| C-monthly | 10% | 0.70 | 10% | 7% | 52%/40% |
| C-monthly | 10% | 0.80 | 10% | 7% | 52%/40% |
| C-monthly | 15% | 0.50 | 10% | 7% | 53%/48% |
| C-monthly | 15% | 0.70 | 10% | 7% | 53%/48% |
| C-monthly | 15% | 0.80 | 10% | 7% | 53%/48% |
| D-onroll | 10% | 0.50 | 61% | 59% | 52%/40% |
| D-onroll | 10% | 0.70 | 61% | 58% | 52%/40% |
| D-onroll | 10% | 0.80 | 61% | 58% | 52%/40% |
| D-onroll | 15% | 0.50 | 62% | 59% | 53%/48% |
| D-onroll | 15% | 0.70 | 61% | 59% | 53%/48% |
| D-onroll | 15% | 0.80 | 61% | 58% | 53%/48% |

## Winner selection (pre-registered algorithm — see script docstring)

Ranking by DAMP=0.4 α-t-stat (FULL window), top 8: C-monthly/b15/Δ0.50 (t=+3.05), C-monthly/b10/Δ0.50 (t=+3.04), C-monthly/b10/Δ0.70 (t=+3.03), C-monthly/b15/Δ0.70 (t=+3.02), C-monthly/b10/Δ0.80 (t=+2.87), C-monthly/b15/Δ0.80 (t=+2.85), B-quarterly/b15/Δ0.50 (t=+2.63), B-quarterly/b10/Δ0.50 (t=+2.62)

Ranking by BASE α-t-stat (FULL window), top 8: C-monthly/b15/Δ0.50 (t=+5.42), C-monthly/b10/Δ0.50 (t=+5.33), B-quarterly/b15/Δ0.50 (t=+5.05), B-quarterly/b10/Δ0.50 (t=+4.98), C-monthly/b15/Δ0.70 (t=+4.85), C-monthly/b10/Δ0.70 (t=+4.80), B-quarterly/b15/Δ0.70 (t=+4.39), B-quarterly/b10/Δ0.70 (t=+4.35)

MaxDD cap filter: damp MaxDD >= -56%. Rank-consistency filter: must place in the top 6 (of 24) by BASE α-t as well.

**WINNER: C-monthly/b15/Δ0.50**

| | CAGR | Sharpe | MaxDD | α vs SPY net-TR (t) |
|---|---|---|---|---|
| base m0.85 | +22.3% | 0.98 | -54.5% | +12.4pp (t+5.4) |
| damp 0.4 | +16.1% | 0.72 | -55.6% | +6.5pp (t+3.1) |

Δ=0.50 still wins under damp=0.4 (consistent with Loop-3's un-stressed ranking) — the pre-registered aggressive-delta contingency does not apply.

## Granularity check ($500k program, winner cell C-monthly/b15/Δ0.50)

Per-contract premium uses the LAST 252 trading days only (recent price/IV level, not a full-history median dominated by cheaper legacy prices).

- SPY leg: premium budget ~$37,500; median per-contract premium (last 252td) ~$6,926 -> ~5.4 contracts (continuous).
- QQQ leg: premium budget ~$37,500; median per-contract premium (last 252td) ~$7,742 -> ~4.8 contracts (continuous).

| | CAGR | α vs SPY net-TR (t) |
|---|---|---|
| continuous/fractional contracts | +22.3% | +12.4pp (t+5.4) |
| whole-contract rounding | +22.3% | +12.4pp (t+5.4) |
| **rounding drag** | **+0.01pp CAGR** | **+0.01pp alpha** |

## Cross-foot verification

- 97 accounting runs, 1,862,109 bar-level assertions, ALL passed: NAV = core + cash + sum(option market value); cash >= 0; NAV > 0; NAV_t = NAV_(t-1) + cash interest + core P&L + option P&L - costs (both the annual rebalance and the new floor top-up are zero-sum internal transfers and do not appear in this identity; rel. tol 1e-6). Any violation raises and aborts the run.

## Trial registry, Bonferroni x42, DSR

- **This loop's registered trial universe: 24 grid cells** (4 top-up rules x 2 premium budgets x 3 deltas, mix fixed), all reported (Table 1). Cumulative with Loop-3's 18 pre-registered cells (`2026-07-06_core_assembly_real.md`, hardcoded not re-run) = **42 trials** for this correction.
- Winner **C-monthly/b15/Δ0.50**, FULL(2001+) window: base α-t = +5.42 (two-sided p=5.815e-08, **Bonferroni x42 p=2.442e-06**); damp=0.4 α-t = +3.05 (two-sided p=0.002269, **Bonferroni x42 p=0.09528**).
- **Deflated Sharpe Ratio (DSR)** of the winner (real daily-return series at base IV/cost, vs the 42-cell annualized-Sharpe trial universe): **1.000** (PSR against 0 = 1.000). DSR > 0.95 ~ survives multiple testing.
- Trial-universe annualized Sharpes (42 cells): min 0.60, median 0.72, max 0.98.

## Conclusions

1. **The cash-starvation mechanism is real and mechanically fixable — higher-frequency top-up dominates monotonically (C-monthly > B-quarterly > A-annual) at every (b,delta) cell.** Cash-starved% (b=15%, SPY-leg/QQQ-leg, of the leg's own trend-eligible days): A-annual 53%/48% -> B-quarterly 24%/22% -> **C-monthly 10%/7%**. This is the direct "rescue" the pre-registration asked for, and it is not a free lunch dressed up — the fix is a pure liquidity-mechanics change (top up the shared premium-cash pool from core when short of b%NAV; never sell cash back down when already sufficient), not a new market-timing signal.
2. **Winner (pre-registered algorithm, no cherry-picking): C-monthly / b15 / Δ0.50** — ranks #1 on BOTH the base-IV and damp=0.4 α-t-stat orderings (no fallback needed), and its damp MaxDD (-55.6%) clears the -56% user-tolerance cap by a hair. FULL(2001+) window: **base CAGR +22.3%, Sharpe 0.98, MaxDD -54.5%, α +12.4pp (t+5.4)**; **damp=0.4: CAGR +16.1%, Sharpe 0.72, MaxDD -55.6%, α +6.5pp (t+3.1)**.
3. **The fix's real value is not the extra CAGR — it's that the edge now SURVIVES the model-risk stress test Loop-3's control barely passed.** At the identical b15/Δ0.50 cell, Rule A (Loop-3's status quo) damp-alpha is +2.5pp (t+1.8) — not significant at the conventional t>=2 bar. The SAME cell under Rule C (monthly top-up) damp-alpha is +6.5pp (t+3.1) — clearly significant. Fixing cash-starvation roughly doubles both the base alpha (6.6pp->12.4pp) and, more importantly, pulls the damp-stressed alpha from "marginal" to "solid."
4. **Δ=0.50 still dominates Δ=0.70/0.80 under damp=0.4 across the whole grid — the pre-registered "aggressive-delta needs real chain validation" contingency does NOT trigger.** Every rule's ranking (base and damp alike) puts Δ0.50 cells at the top; Δ0.70/0.80 are directionally similar but consistently weaker (e.g. C-monthly/b15/Δ0.70 damp α+4.6pp t+3.0, Δ0.80 damp α+3.6pp t+2.8, both still significant but below Δ0.50's t+3.1 — lower vega did NOT make them win the damp race, contrary to the a-priori "vega=exposure to model risk" intuition; Δ0.50's larger BASE edge more than compensates for its larger damp haircut).
5. **Rule D (on-roll) is a clean NEGATIVE finding, disclosed as pre-registered.** Tying the top-up to the 63td roll retry point (rather than a calendar cadence) does NOT fix cash-starvation — b15 starved% is 62%/59%, actually WORSE than the do-nothing control (53%/48%) — and it costs both alpha (b15/Δ0.50 base α+5.9pp vs A's +6.6pp) and MaxDD (-59.8% vs A's -56.7%, breaching the -56% cap outright). The mechanism is exactly the disclosed limitation: D only re-funds at a leg's own periodic roll (~every 189 trading days while continuously held), never at a fresh gate re-entry after a trend-down exit — the single largest source of unfunded eligible-days is untouched by this rule.
6. **Bonferroni x42 and DSR tell different stories under damp=0.4 — both reported, neither hidden.** Base IV: α-t=+5.42, Bonferroni-x42 p=2.44e-6 (decisive). Damp IV: α-t=+3.05, Bonferroni-x42 p=**0.095** — this does NOT clear the conventional 0.05 bar (it clears 0.10, and the raw/uncorrected p=0.0023 is small, but the blunt x42 normal-approximation correction on the damped t-stat leaves it borderline). DSR against the 42-cell Sharpe universe = **1.000** (uses the actual return distribution's skew/kurtosis rather than a normal approximation on a single t-stat, and is the repo's usual primary bar) — decisively passes. The honest read: DSR says the winner is robust to multiple testing; the cruder Bonferroni-on-damped-t check says "not quite at the strictest threshold." Report both; do not average them into a false consensus.
7. **Rounding to whole option contracts is immaterial at $500k.** Winner cell: ~5.4 SPY contracts + ~4.8 QQQ contracts (continuous) at ~$37,500 premium/leg; whole-contract rounding drag = **+0.01pp CAGR / +0.01pp alpha** — a non-issue for the granularity check.
8. **b=15% vs b=10% is close to a statistical tie within Rule C** (damp t+3.05 vs t+3.04 — noise-level difference), but b15 delivers meaningfully more CAGR/alpha (base +12.4pp vs +8.5pp) for essentially the same damp MaxDD (-55.6% vs -55.3%, both under the cap) — the pre-registered algorithm picks b15 by the smallest of margins; a risk-averse reader could reasonably prefer b10 as the "practically identical, slightly safer" choice.

## Caveats

- **MaxDD improved (got LESS negative) under B/C relative to A at most cells despite MUCH higher median notional exposure** (e.g. winner cell Dn% med/p90/max = 120%/216%/301% vs Rule A's 0%/169%/298% at the same b/delta) — a genuinely counter-intuitive result. The mechanism is plausible (A's cash-starved days meant the sleeve sat OUT of the market for long stretches, including stretches that happened to precede the worst drawdown episode in-sample; B/C keep it funded/participating far more consistently, which shifts WHEN drawdowns bite) but this loop did not do the path-level forensics to prove causality — reported as observed, not over-explained.
- **The -56% MaxDD cap is a judgment call on ambiguous natural-language input** ("MaxDD ≤ -56%"): interpreted as a CEILING on drawdown magnitude (MaxDD must not be WORSE than -56%, i.e. MaxDD >= -56%), consistent with Loop-3's own use of ~SPY's -55.6% historical MaxDD as the practical tolerance edge and with why b=20% was excluded from this grid. The alternative (literal) reading would select worse-not-better drawdowns and was rejected as economically nonsensical.
- **The "rank-consistency" filter (top-6-of-24 by BASE alpha-t) never had to bind** — the winner is literally rank #1 on both orderings, so this pre-registered guard-rail was not tested against a genuine conflict in this run. It remains in the algorithm for future loops where base/damp rankings might actually diverge.
- **6 of this loop's 24 registered trials (the "A-annual" rows) are near-identical re-runs of 6 of Loop-3's already-registered 18 cells** (same b/delta/mix, same annual-rebalance mechanics, reproduced here as the control arm — see regression check below). Per the pre-registration, all 24 are still counted in the x42 registry (as literally specified: "24 格 + Loop-3 嘅 18 格 = 42 累計"); this makes the Bonferroni correction slightly conservative (double-counts near-duplicate trials) rather than anti-conservative, which is the safe direction to err.
- **Regression check (not printed as a formal assert, verified by inspection):** Rule-A cells reproduce Loop-3's `2026-07-06_core_assembly_real.md` main-table numbers for the identical b/delta/mix cells almost exactly — e.g. b15/Δ0.50/SPY+QQQ: this loop's Rule-A base CAGR +15.5%/Sharpe 0.79/MaxDD -56.7%/α+6.6pp(t+4.1) vs Loop-3's reported +15.5%/0.79/-56.7%/+6.6pp(t+4.1) (identical); damp=0.4 α+2.5pp(t+1.8) vs Loop-3's +2.5pp(t+1.7) (t-stat differs by 0.1, rounding-level). This confirms the new engine's core mechanics (leg processing, sweep, cross-foot identity) are a faithful port before the new top-up axis is layered on.
- **D-onroll's higher cash-starved% than the do-nothing control is a genuine emergent effect of the shared-cash-pool dynamics** (both legs draw from one pool; a roll-triggered top-up for one leg can leave less room for the other leg's own fresh entry attempt shortly after), not a bug — all 1.86M cross-foot bar-level assertions passed across all 97 accounting runs.
- **Higher-than-monthly cadence (e.g. weekly) was NOT tested** — out of the pre-registered A/B/C/D scope. Given C (monthly) beats B (quarterly) monotonically at every cell, an even shorter cadence is a plausible next-loop candidate, not a reason to distrust this loop's result.
- Core-equity trades (top-up transfers, rebalance, roll-sweep) are treated as zero-cost (ETF shares) in all rules — only option legs carry the 0.5%/side cost assumption, same convention as Loop-3.
- IV-damping's sigma_bar is a full-sample mean (mild look-ahead in the pricing input only, not the price/200SMA-driven gate/roll timing) — acceptable for a robustness sensitivity, not presented as a tradable rule (same caveat Loop-3 already carried, reused unchanged).

## Implication

- **Recommended operational change: replace Loop-3's annual-only core:cash rebalance with a MONTHLY floor top-up of the LEAP premium cash pool (Rule C), at b=15% premium budget, Δ=0.50, SPY+QQQ 50/50 mix.** This is a pure liquidity-mechanics change (one extra check on the first trading day of each month: if cash < 15%*NAV, pull the shortfall from the core equity sleeve into cash; never sell cash back down) — no new market-timing signal, no change to the 200SMA gate, no change to which options get bought.
- **This is the single most load-bearing operational fix identified across the whole core-portfolio search (Loops 1-4): it is what turns "the edge survives model-risk stress-testing" from a marginal call (t+1.8, Loop-3's Rule A) into a solid one (t+3.1)** — a bigger swing in statistical robustness than any of the delta/mix/gate choices settled in earlier loops.
- **Granularity is a non-issue at $500k**: ~5 SPY + ~5 QQQ LEAP contracts, whole-contract rounding costs ~0.01pp — round normally, no special sizing logic needed.
- **Statistical honesty on the finish line**: report DSR=1.000 as the primary "survives multiple testing" bar (consistent with how every other loop in this search has been judged), but do NOT suppress that the cruder Bonferroni-on-damped-alpha check (p=0.095) sits just above the conventional 0.05 line — a reader who weights that check more heavily should treat the damp-IV alpha as "probably real, not airtight" rather than "proven."
- **Next-loop candidates (not this loop's job)**: (a) test cadences shorter than monthly (weekly?) since C already beats B monotonically; (b) do the path-level forensics on WHY B/C's MaxDD improved despite far higher exposure, instead of leaving it as an observed-but-unexplained pattern; (c) validate Δ0.50 pricing against a real SPY/QQQ LEAP options chain before sizing real capital (the whole grid, including this fix, still runs on the ^VIX/^VXN-anchored IV proxy, not quoted option markets).
