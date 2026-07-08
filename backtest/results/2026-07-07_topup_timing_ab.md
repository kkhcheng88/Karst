# Result — Top-up TIMING A/B: RSI-2-funded top-up (E) and monthly top-up + dip-gated entry (F) vs the locked Loop-4 winner (C-monthly/b15/Delta0.50/SPY+QQQ)

**Date:** 2026-07-07  **Script:** `backtest/experiments/exp_topup_timing_ab.py`  **Status:** active

## Question

User challenge to the Loop-4 winner: "why not RSI-time the top-up?" Two pre-registered new cells, everything else pinned to the winning cell's own settings (b=15% NAV, Delta=0.50, mix=SPY+QQQ 50/50, roll@63td): **Rule E** replaces the calendar top-up trigger with SPY RSI-2(Wilder)<10 (signal T -> exec T+1), same pure-200SMA GATED entry gate as the winner. **Rule F** keeps the winner's monthly calendar top-up but requires each leg's OWN entry to ALSO clear a dip condition (GATED+DIP: close>200SMA AND RSI-2<10 within the last 5 trading days; trend-exit unchanged). Rule C's own numbers are CITED from `2026-07-06_core_topup.md` (not re-derived as the reported figures); a regression-check re-run of the identical Rule-C cell is included separately to confirm the imported engine still reproduces those numbers.

## Method

- LEAP unit engine (`simulate_unit_path`), the GATED+DIP state machine, and the floor-top-up mechanic (`simulate_portfolio_topup`) are IMPORTED verbatim from `exp_leap_real_sweep.py` / `exp_core_topup.py` — only the TRIGGER mask (and, for Rule F, which pre-built gate array feeds the unit path) is new.
- IV_1y = vol-index/100 x 0.85 (base), real ^VIX (SPY leg) / ^VXN (QQQ leg); damp=0.4 IV via `damp_iv()` (verbatim). Costs: 0.5%/side of option premium, core-equity transfers zero-cost. Sharpe = raw daily returns. CAPITAL = $500,000.
- Core sleeve compounds at the SAME SPY net-TR series used as the Jensen-alpha benchmark, so alpha isolates the LEAP-sleeve + cash-buffer + top-up-TIMING machinery, not stock selection.
- Windows: FULL (native start of the SPY+QQQ common window, 2001+) PRIMARY, + H2 2011-2026 / 2016-2020 / 2021+ (identical set to `exp_core_topup.py`).
- Statistical context: this is a targeted 2-cell challenge test against the ALREADY-SELECTED winner (same b/delta/mix), not a fresh multi-cell search — a new Bonferroni/DSR table is not the governing lens here (see docstring).

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

## Table 1 — FULL (2001+) window, base (m0.85) AND damp=0.4, b15/Delta0.50/SPY+QQQ (E and F computed here; C-monthly is CITED from `2026-07-06_core_topup.md`, not rerun)

| Rule | Gate | IV | CAGR | Sharpe | MaxDD | alpha vs SPY net-TR (t) | Worst mo | TE | Dn% med/p90/max | CostDrag pp/yr |
|---|---|---|---|---|---|---|---|---|---|---|
| C-monthly (CITED, winner) | GATED | base m0.85 | +22.3% | 0.98 | -54.5% | +12.4pp (t+5.4) | -39.8% | +11.6% | 120%/216%/301% | +0.7 |
| C-monthly (CITED, winner) | GATED | damp 0.4 | +16.1% | 0.72 | -55.6% | +6.5pp (t+3.1) | -41.6% | +11.2% | 118%/172%/217% | +0.6 |
| E-rsi2topup | GATED | base m0.85 | +22.0% | 0.97 | -54.6% | +12.2pp (t+5.3) | -37.0% | +11.5% | 109%/215%/301% | +0.7 |
| E-rsi2topup | GATED | damp 0.4 | +16.0% | 0.73 | -55.2% | +6.5pp (t+3.0) | -40.0% | +11.1% | 104%/171%/217% | +0.6 |
| F-monthlydip | GATED+DIP | base m0.85 | +19.9% | 0.91 | -52.8% | +10.5pp (t+4.7) | -39.8% | +11.3% | 122%/217%/280% | +0.5 |
| F-monthlydip | GATED+DIP | damp 0.4 | +14.9% | 0.69 | -53.5% | +5.6pp (t+2.6) | -41.6% | +11.2% | 119%/173%/203% | +0.4 |

MaxDD tolerance ceiling (Loop-4 convention): >= -56%.

## Table 2 — sub-windows (H2 2011-2026 / 2016-2020 / 2021+), base IV only (CAGR / alpha(t))

| Rule | H2 2011-2026 CAGR | alpha(t) | 2016-2020 CAGR | alpha(t) | 2021+ CAGR | alpha(t) |
|---|---|---|---|---|---|---|
| C-monthly (CITED, winner) | +32.8% | +14.3pp (t+4.6) | +41.6% | +20.4pp (t+3.3) | +29.9% | +10.1pp (t+2.0) |
| E-rsi2topup | +32.2% | +14.2pp (t+4.5) | +38.2% | +18.6pp (t+3.1) | +30.0% | +10.3pp (t+2.0) |
| F-monthlydip | +28.1% | +10.7pp (t+3.6) | +30.9% | +12.8pp (t+2.6) | +25.5% | +6.8pp (t+1.3) |

## Table 3 — cash-starved% (base IV, FULL window; SPY-leg/QQQ-leg): "of days the leg's OWN entry gate says eligible, fraction the sim carried 0 contracts because cash could not fund the fresh premium"

| Rule | Gate | SPY-leg starved% | QQQ-leg starved% |
|---|---|---|---|
| C-monthly (CITED, winner) | GATED | 10% | 7% |
| E-rsi2topup | GATED | 15% | 14% |
| F-monthlydip | GATED+DIP | 5% | 0% |

## Table 4 — Rule E "no RSI<10 day all year" diagnostic (FULL window, raw SPY RSI-2(Wilder)<10 signal days per calendar year, BEFORE the T+1 execution shift)

Total calendar years in FULL window: 26. Years with ZERO raw RSI-2<10 day (sleeve gets NO top-up all year under Rule E): **0** -> (none).

| Year | Trading days | Raw RSI<10 days | Executed top-up days |
|---|---|---|---|
| 2001 | 234 | 31 | 31 |
| 2002 | 252 | 38 | 38 |
| 2003 | 252 | 19 | 19 |
| 2004 | 252 | 21 | 21 |
| 2005 | 252 | 22 | 21 |
| 2006 | 251 | 22 | 23 |
| 2007 | 251 | 20 | 19 |
| 2008 | 253 | 39 | 40 |
| 2009 | 252 | 25 | 24 |
| 2010 | 252 | 26 | 27 |
| 2011 | 252 | 35 | 35 |
| 2012 | 250 | 35 | 35 |
| 2013 | 252 | 13 | 13 |
| 2014 | 252 | 21 | 20 |
| 2015 | 252 | 29 | 30 |
| 2016 | 252 | 24 | 23 |
| 2017 | 251 | 9 | 10 |
| 2018 | 251 | 32 | 32 |
| 2019 | 252 | 17 | 17 |
| 2020 | 253 | 17 | 17 |
| 2021 | 252 | 14 | 14 |
| 2022 | 251 | 45 | 45 |
| 2023 | 250 | 24 | 24 |
| 2024 | 252 | 21 | 20 |
| 2025 | 250 | 26 | 26 |
| 2026 | 126 | 13 | 14 |

## Rule F vs the engine-level GATED+DIP finding (consistency check)

Already-settled engine-level (single-unit, PORTFOLIO frame, Delta=0.50) finding from `exp_leap_real_sweep.py` / `2026-07-06_leap_real_sweep.md` ("pure GATED > DIP/HYST", CITED):

| Underlying | Gate | alpha vs SPY net-TR (t) |
|---|---|---|
| SPY | GATED | +10.6pp (t+5.9) |
| SPY | GATED+DIP | +10.0pp (t+5.7) |
| QQQ | GATED | +12.0pp (t+5.0) |
| QQQ | GATED+DIP | +9.2pp (t+4.2) |

Portfolio-level, this script (FULL window, b15/Delta0.50/SPY+QQQ, monthly top-up both sides): **F (GATED+DIP entry) base alpha +10.5pp (t+4.7) vs C (pure GATED, CITED) base alpha +12.4pp (t+5.4)**; damp=0.4: F +5.6pp (t+2.6) vs C +6.5pp (t+3.1). CONSISTENT with the engine-level finding that dip-gating entries does not help (F underperforms C at both IV settings).

## Regression check — Rule C recomputed here vs CITED (`2026-07-06_core_topup.md`)

Recomputed with the IDENTICAL imported engine (GATED gate, monthly trigger, b15/Delta0.50/SPY+QQQ) purely to confirm the import chain still reproduces the cited winner numbers before trusting E/F's comparisons against it. Small residual diffs are expected: this run's `load()` call pulls data through 2026-07-07 (one extra trading day vs the cited file's 2026-07-06 snapshot).

| Metric | Recomputed here | Cited (2026-07-06) | Diff |
|---|---|---|---|
| base CAGR | 0.2229 | 0.2230 | -0.0001 |
| base Sharpe | 0.9779 | 0.9800 | -0.0021 |
| base MaxDD | -0.5452 | -0.5450 | -0.0002 |
| base alpha | 0.1240 | 0.1240 | +0.0000 |
| base t | 5.4217 | 5.4000 | +0.0217 |
| damp CAGR | 0.1609 | 0.1610 | -0.0001 |
| damp alpha | 0.0646 | 0.0650 | -0.0004 |
| damp t | 3.0500 | 3.1000 | -0.0500 |

## Cross-foot verification

- All 3 rules' accounting runs (base+base0+damp+damp0 x {E, F, C-regen} = 12 runs) passed every bar-level assert IMPORTED from `exp_core_topup.simulate_portfolio_topup`: NAV = core + cash + sum(option market value); cash >= 0; NAV > 0; NAV_t = NAV_(t-1) + cash interest + core P&L + option P&L - costs (the floor top-up is a zero-sum internal transfer and does not appear in this identity; rel. tol 1e-6). Any violation raises and aborts the run — none did.

## Conclusions

1. **Rule E (RSI-2-funded top-up) does not beat Rule C (calendar monthly) — it is a statistical tie on alpha but WORSE on the very liquidity metric it was meant to fix.** FULL(2001+): E base alpha +12.2pp(t+5.3) vs C's +12.4pp(t+5.4); damp=0.4: +6.5pp(t+3.0) vs C's +6.5pp(t+3.1) — indistinguishable from noise either way. But cash-starved% (SPY-leg/QQQ-leg) is WORSE under E: **15%/14% vs C's 10%/7%**. Mechanism: SPY RSI-2<10 events cluster in bursts (median ~24 signal-days/year, min 9 in 2017, max 45 in 2022, per Table 4) rather than spreading evenly, so the gap between clusters can exceed a month during quiet/trending stretches — exactly when a leg might need fresh funding after a gate re-entry. A guaranteed monthly tick funds the sleeve more reliably than an event that is frequent on average but unevenly spaced.
2. **The user's specific "2017-type starved year" hypothesis is DISCONFIRMED in this window.** Every one of the 26 calendar years 2001-2026 had at least one raw SPY RSI-2<10 day (2017's low was 9 days — the sparsest year in the sample, still nonzero — see Table 4). Rule E never goes a full calendar year without at least one top-up opportunity here; the cash-starved% degradation in Conclusion 1 comes from within-year gaps, not full-year droughts.
3. **Rule F (monthly top-up + GATED+DIP entry) is CLEARLY worse than Rule C at every window and both IV settings, CONSISTENT with the already-settled engine-level finding** (`2026-07-06_leap_real_sweep.md`, "pure GATED > DIP/HYST"): FULL base alpha +10.5pp(t+4.7) vs C's +12.4pp(t+5.4); damp=0.4 +5.6pp(t+2.6) vs C's +6.5pp(t+3.1); the gap widens in 2016-2020 (alpha +12.8pp(t+2.6) vs C's +20.4pp(t+3.3), the largest divergence of any window). Gating entries on a recent dip on top of the trend gate throws away eligible up-trend days waiting for a dip that may not come soon — the same effect already documented at the single-unit engine level, now reproduced at the full-portfolio level.
4. **Rule F's cash-starved% DOES improve (5%/0% vs C's 10%/7%), but this is a side-effect of a stricter entry test, not a liquidity win** — GATED+DIP is eligible fewer days overall, so there are fewer days to fund, not smarter deployment of capital. Read together with Conclusion 3, F trades real alpha for a better-looking (but not like-for-like, see Caveats) starved% number.
5. **Regression check confirms the import chain is faithful.** Recomputing the identical Rule-C cell here reproduces the cited numbers to within citation-rounding noise (base alpha 0.1240 vs cited 0.1240 exact; Sharpe/t differ by <=0.03/0.05, fully explained by the cited file only publishing 2-3 significant figures) — E and F's comparisons against C rest on a verified-identical engine, not on reimplementation drift.
6. **Verdict: neither pre-registered timing variant displaces Rule C-monthly/b15/Delta0.50/SPY+QQQ.** E is a wash on alpha but worse on the liquidity metric it targeted; F is a clear alpha loser, consistent with prior evidence against dip-gating. No change to the Loop-4 recommendation.

## Caveats

- Rule E's trigger is SPY-only (per the pre-registration) even though the QQQ leg has its own eligibility/starvation profile — a QQQ-RSI-2-timed (or dual-trigger) variant was not tested and might behave differently; out of scope here.
- The starved-year diagnostic (Table 4) uses the RAW (pre-T+1-shift) signal count as the right lens for "did RSI-2 ever dip under 10 that calendar year"; the actual funding events are the shifted/executed column, which differs by at most a day or two per year from calendar-boundary shifts — never materially.
- Cash-starved% denominators differ between Rule E/C (GATED gate) and Rule F (GATED+DIP gate) because "eligible" is defined relative to each rule's OWN entry gate — F's improved-looking starved% is measured against a smaller eligible-day base (Conclusion 4), so the E/C comparison is like-for-like (both plain GATED) but the F comparison is not.
- Cited Rule-C figures carry only the precision printed in `2026-07-06_core_topup.md` (1-2 decimal places); the regression-check table shows the full-precision recomputation for anyone who wants tighter figures.
- This is a 2-cell targeted challenge test against an already-selected winner, not a new grid search — no fresh Bonferroni/DSR correction was computed (see Method); the existing 42-cell Loop-4 registry context still stands for anything drawing on the C-monthly winner itself.

## Implication

- **No change to the recommended program**: keep Rule C-monthly (calendar top-up, first trading day of each month) + pure 200SMA GATED entries, b=15% NAV, Delta=0.50, 50/50 SPY+QQQ mix — the Loop-4 winner stands unchallenged by either pre-registered alternative tested here.
- **Answering the user's question directly**: RSI-timing the top-up is not a free improvement — it trades a small, statistically insignificant alpha difference for a WORSE cash-starvation profile, because RSI-2<10 events cluster rather than spread evenly across the year. A calendar tick remains the more reliable liquidity-funding cadence.
- **Dip-gating LEAP entries (Rule F) is now confirmed to hurt at BOTH the single-unit engine level and the full portfolio-assembly level** — two independent tests now agree; this closes the "maybe dip-gating helps once cash-flow is fixed" possibility the user's question implicitly raised.
- **Next-loop candidate (not this loop's job)**: if the goal is genuinely to push cash-starved% further below Rule C's already-good 10%/7%, a higher-frequency CALENDAR cadence (e.g., weekly) is the more promising direction, not an event-based trigger — consistent with Loop-4's own finding that C (monthly) already beat B (quarterly) monotonically.
