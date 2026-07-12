# Result — BT-2: Karst-AA all-active STRUCTURE vs core-v2 vs SPY B&H (2-variant, base+damp)

**Date:** 2026-07-12  **Script:** `backtest/experiments/exp_bt2_aa_structure.py`  **Status:** active

## Scope limit (read this first)

**The Karst-AA "T" (thesis) sleeve has NO valid historical proxy in this repo, so it is proxied here as pure QQQ beta exposure with a ZERO thesis-alpha assumption.** This backtest ONLY tests whether the AA *structure* (defensive ballast + delta-ledger LEAP overlay + a beta-only stand-in for the thesis sleeve) matches or beats core-v2's structure and SPY B&H. It is NOT a test of AA's real edge, because the whole point of the T sleeve in the live design is stock-picking alpha that cannot be backtested here (its true judge is forward IC/Brier, not a historical sim). Every AA number below is a STRUCTURE result. Do not read any AA out/under-performance here as evidence about thesis-alpha — the sim has none by construction.

## Method (mechanical rules, point by point)

**Sleeves / NAV buckets** (tracked every bar; NAV=100% start, capital=$500,000): `T_val` = QQQ spot (thesis stand-in, target 25% NAV); `B_val` = XLP/XLU/XLV equal-weight trio spot (ballast, residual plug); `L_val` = SPY-leg + QQQ-leg 0.50Δ LEAP market value (capped 15% NAV premium); `Parked_val` = strict-only trio bought with cash-that-would-be-LEAP-premium on a gate close (0 for pragmatic); `Cash_val` = residual cash @ ^IRX.
- **Data**: SPY/QQQ/^VIX/^VXN/^IRX via `build_underlying` (exp_core_topup import); XLP/XLU/XLV via `build_core_only` (exp_ballast_parking import). Trio composite = equal-weight daily mean of the three `r_net`. FULL window = intersection of ALL of {SPY,QQQ,XLP,XLU,XLV,^IRX,^VIX,^VXN}.
- **Gates**: `build_gates(df)["GATED"]` for SPY and QQQ — the existing T+1-shifted 200SMA convention (this is the entire "R1/R2" execution rule; nothing new added).
- **Rolling 252-td beta** (min 60), causal/trailing, computed on each series' full native history: `beta_B` = trio vs SPY, `beta_T` = QQQ vs SPY (computed, not hardcoded).
- **Monthly delta ledger** (first trading day of each month; also forced on day 1 to deploy): (1) snapshot NAV_now BEFORE trades; (2) `B_actual_w`=B_val/NAV, `T_actual_w`=T_val/NAV (trailing actuals, excludes Parked); (3) band from gate state (0 off→1.15, 1 off→0.925, 2 off→0.0); (4) `leap_target_dn = max(0, band - B_actual_w*beta_B - T_actual_w*beta_T)`; (5) split 50/50, or 100% to the open leg if one is gated off; (6) per open+held leg `lev=(delta*close)/mark`, `leg_premium_frac = share/lev`; (7) cap total premium at 15%, scale both legs proportionally if over; (8) `B_target = 1 - 0.25 - total_premium_capped` (nominal); (9) execute at bar close: (a) T→0.25*NAV (10bps), (b) resize each LEAP leg to its premium target (0.5%/side), (c) B absorbs the residual so Cash→0 (10bps).
- **Variant difference (only this differs)**: on a gate-close LEAP sell — pragmatic routes proceeds to Cash_val; strict routes them to Parked_val (buys trio, 10bps). On a gate-reopen buy — pragmatic funds from Cash first; strict funds from Parked first, then Cash, then B. Everything else byte-identical.
- **Intramonth**: no resize; the gate's own T+1 sells/buys/rolls fire per `simulate_unit_path`, sizing any fresh buy from the most-recent month-start `leg_premium_frac` (carried forward).
- **Costs/tax**: options 0.5%/side (COST_BASE); ETF 10bps/side (COST_SIDE); HK 30% dividend withholding baked into `r_net` by the loaders; LEAP legs pay no dividend.
- **IV models**: base m=0.85 AND damped 0.4 (`damp_iv`), reported side by side for every strategy — no cherry-picking.

## Data provenance (`backtest/data.py` `load()`)

| Series | Source | Rows | From | To |
|---|---|---|---|---|
| ^IRX | yfinance | 16614 | 1960-01-04 | 2026-07-10 |
| SPY | yfinance | 8418 | 1993-01-29 | 2026-07-10 |
| SPY(adj) | yfinance(adj) | 8418 | 1993-01-29 | 2026-07-10 |
| ^VIX | yfinance | 9198 | 1990-01-02 | 2026-07-10 |
| QQQ | yfinance | 6876 | 1999-03-10 | 2026-07-10 |
| QQQ(adj) | yfinance(adj) | 6876 | 1999-03-10 | 2026-07-10 |
| ^VXN | yfinance | 6403 | 2001-01-23 | 2026-07-10 |
| XLP | yfinance | 6928 | 1998-12-22 | 2026-07-10 |
| XLP(adj) | yfinance(adj) | 6928 | 1998-12-22 | 2026-07-10 |
| XLU | yfinance | 6928 | 1998-12-22 | 2026-07-10 |
| XLU(adj) | yfinance(adj) | 6928 | 1998-12-22 | 2026-07-10 |
| XLV | yfinance | 6928 | 1998-12-22 | 2026-07-10 |
| XLV(adj) | yfinance(adj) | 6928 | 1998-12-22 | 2026-07-10 |

- AA FULL common (8-way) window: **2001-01-23 -> 2026-07-10 (6397 days)**; gated by ^VXN availability (2001-01-23).
- core-v2 native (SPY∩QQQ) window: 2001-01-23 -> 2026-07-10 (6403 days). **Windows DIFFER** — the AA main table recomputes core-v2 AND SPY B&H on the AA common window for apples-to-apples; the native-window core-v2 row is kept separately labeled.)
- Rolling 252-td betas computed on each underlying's FULL native return history (QQQ from 1999-03 for warm-up, independent of the ^VXN option-IV join): warm by the window start (beta_B[0]=0.37, beta_T[0]=2.08); forced-zero (NaN-beta) bars inside window: **0**.

## Step-0 reproduction cross-check

Step-0 (safety-net reproduction of core-v2's flagship cell) already PASSED on the 2026-07-06 data pull: base α **+12.37pp (t+5.41)**, damp α **+6.45pp (t+3.05)**, SPY B&H sanity CAGR **9.86%** — all within the pre-registered acceptance bands (base [+11,+14]pp, damp [+5.5,+7.5]pp, anchor [9,11]%). Below, core-v2 is recomputed on today's data on BOTH windows; the AA-window row is the apples-to-apples head-to-head input and is asserted to stay inside the Step-0 bands (the script hard-stops otherwise).

| core-v2 reproduction | base α (t) | in [+11,+14]? | damp α (t) | in [+5.5,+7.5]? |
|---|---|---|---|---|
| Step-0 published (2026-07-06 data, native) | +12.37pp (t+5.41) | PASS | +6.45pp (t+3.05) | PASS |
| core-v2 @ AA common window (today's data) | +12.38pp | PASS | +6.44pp | PASS |
| core-v2 @ native window (today's data) | +12.37pp | PASS | +6.45pp | PASS |

- SPY B&H sanity anchor (1996-01→2026-07-10, HK net-TR): CAGR **9.86%**, Sharpe 0.59, MaxDD -55.6% — in [9,11]% → PASS.

## Four-strategy main comparison (AA common window 2001-01-23→2026-07-10; base m0.85 AND damp 0.4 side by side)

| Strategy | IV | CAGR | Sharpe | MaxDD | β | Worst 12m | α vs SPY net-TR (t) |
|---|---|---|---|---|---|---|---|
| SPY B&H (TR, HK net) | base/damp n/a | +8.4% | 0.52 | -55.6% | 1.00 | -47.7% | +0.0pp (ref) |
| core-v2 (C-monthly/b15/Δ0.50/mix) | base m0.85 | +22.3% | 0.98 | -54.5% | 1.07 | -45.8% | +12.4pp (t+5.4) |
| core-v2 (C-monthly/b15/Δ0.50/mix) | damp 0.4 | +16.1% | 0.73 | -55.6% | 1.18 | -46.9% | +6.4pp (t+3.0) |
| AA-pragmatic @115 | base m0.85 | +12.8% | 0.79 | -43.7% | 0.82 | -35.6% | +5.4pp (t+4.1) |
| AA-pragmatic @115 | damp 0.4 | +11.3% | 0.69 | -44.6% | 0.86 | -36.5% | +3.8pp (t+2.9) |
| AA-strict @115 | base m0.85 | +15.4% | 0.89 | -44.2% | 0.85 | -36.1% | +7.5pp (t+5.0) |
| AA-strict @115 | damp 0.4 | +13.0% | 0.74 | -45.2% | 0.91 | -37.2% | +5.0pp (t+3.4) |

| core-v2 native-window reference | base m0.85 | +22.3% | 0.98 | -54.5% | 1.07 | -45.8% | +12.4pp (t+5.4) |
| core-v2 native-window reference | damp 0.4 | +16.1% | 0.72 | -55.6% | 1.18 | -46.9% | +6.4pp (t+3.0) |

**AA-only readouts (base IV, FULL window)** — delta-notional target time series (`leap_target_delta_notional_frac`) and average alpha-capital share (= 0.25 + mean `total_premium_frac_capped`):

| Variant | Dn median | Dn p90 | avg alpha-capital share | bailout events | underfund events | park events (strict) | warm-up-zero bars |
|---|---|---|---|---|---|---|---|
| AA-pragmatic @115 | 35% | 53% | 29.1% | 48 | 0 | 0 | 0 |
| AA-strict @115 | 61% | 77% | 31.2% | 15 | 1 | 103 | 0 |

## Sub-window / stress-year breakdown (CAGR / α base / α damp)

| Strategy | FULL CAGR | α base | α damp | H1 (start-2011) CAGR | α base | α damp | H2 (2012+) CAGR | α base | α damp | Stress 2008 CAGR | α base | α damp | Stress 2020 CAGR | α base | α damp | Stress 2022 CAGR | α base | α damp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY B&H | +8.4% | ref | ref | +0.6% | ref | ref | +14.5% | ref | ref | -36.7% | ref | ref | +16.6% | ref | ref | -19.2% | ref | ref |
| AA-pragmatic @115 | +12.8% | +5.4pp (t+4.1) | +3.8pp (t+2.9) | +5.3% | +4.5pp (t+2.1) | +3.7pp (t+1.7) | +18.7% | +5.6pp (t+3.4) | +3.1pp (t+1.9) | -27.6% | -2.5pp (t-0.3) | -3.0pp (t-0.3) | +25.0% | +8.3pp (t+0.9) | +5.8pp (t+0.6) | -10.4% | +4.6pp (t+0.7) | +1.3pp (t+0.2) |
| AA-strict @115 | +15.4% | +7.5pp (t+5.0) | +5.0pp (t+3.4) | +5.7% | +4.9pp (t+2.2) | +3.8pp (t+1.7) | +23.4% | +8.6pp (t+4.4) | +4.4pp (t+2.4) | -27.9% | -3.0pp (t-0.3) | -3.5pp (t-0.4) | +39.7% | +19.0pp (t+1.7) | +15.6pp (t+1.4) | -11.3% | +3.7pp (t+0.6) | -1.5pp (t-0.2) |

(core-v2 sub-window α is in `2026-07-06_core_topup.md` Table 2; not re-tabulated here — this study's increment is the AA structure, benchmarked against core-v2's FULL-window numbers in the main table above.)

- Stress-year coverage on the AA window (2001-01-23→2026-07-10): 2008 ✓, 2020 ✓, 2022 ✓ — all three fully covered (window starts 2001).

## Sensitivity — both-open band 1.00 / 1.30 (0.925 & 0.0 states unchanged)

Separate from the headline (@1.15). Re-runs AA-pragmatic and AA-strict with the both-legs-open band set to 1.00 and 1.30. CAGR / α(base) / α(damp) / MaxDD(base).

| Variant | Band | CAGR (base) | α base (t) | α damp (t) | MaxDD (base) |
|---|---|---|---|---|---|
| AA-pragmatic | 1.00 | +11.1% | +4.1pp (t+3.3) | +3.1pp (t+2.5) | -43.4% |
| AA-pragmatic | 1.15 (headline) | +12.8% | +5.4pp (t+4.1) | +3.8pp (t+2.9) | -43.7% |
| AA-pragmatic | 1.30 | +14.4% | +6.7pp (t+4.6) | +4.6pp (t+3.1) | -44.4% |
| AA-strict | 1.00 | +13.4% | +5.9pp (t+4.4) | +4.0pp (t+3.0) | -43.6% |
| AA-strict | 1.15 (headline) | +15.4% | +7.5pp (t+5.0) | +5.0pp (t+3.4) | -44.2% |
| AA-strict | 1.30 | +17.1% | +8.9pp (t+5.4) | +5.8pp (t+3.5) | -45.0% |

## Trial registry, Bonferroni x48, DSR

6 new trials added to the existing 42-trial registry (18 Loop-3 + 24 Loop-4 cells from `2026-07-06_core_topup.md`) = **48 total**. Bonferroni α = 0.05/48 ≈ **0.00104**. DSR via `backtest.metrics.deflated_sharpe_ratio` (the repo's reusable helper — located, not reinvented), fed each headline AA variant's real base-IV daily return series + the 48-cell annualized-Sharpe universe.

| New trial | base α-t | base p (2-sided) | Bonf×48? | damp α-t | damp p | Bonf×48? |
|---|---|---|---|---|---|---|
| AA-pragmatic @115 | +4.09 | 4.38e-05 | PASS | +2.87 | 0.00411 | FAIL |
| AA-strict @115 | +5.03 | 4.83e-07 | PASS | +3.35 | 0.000794 | PASS |
| AA-pragmatic @100 | +3.33 | 0.000875 | PASS | +2.48 | 0.0131 | FAIL |
| AA-pragmatic @130 | +4.63 | 3.72e-06 | PASS | +3.12 | 0.0018 | FAIL |
| AA-strict @100 | +4.42 | 9.9e-06 | PASS | +3.02 | 0.00257 | FAIL |
| AA-strict @130 | +5.36 | 8.52e-08 | PASS | +3.47 | 0.000514 | PASS |

DSR (base IV, vs 48-cell Sharpe universe): AA-pragmatic @115 = 0.999, AA-strict @115 = 1.000.
- 48-cell trial-universe annualized Sharpes: min 0.60, median 0.73, max 0.98.

## Caveats

- **(scope) The T sleeve is a ZERO-alpha QQQ-beta stand-in** — see the scope-limit section. This is a structure test only; the live T sleeve's real edge is a forward problem, unmeasurable here.
- **(a) Monthly delta-ledger vs daily live-trading reconciliation gap**: positions resize only once a month. Intramonth drift (weights, delta) is real and unmodeled beyond the gate's own T+1 exits/entries/rolls. A live daily-rebalanced book would differ; the monthly cadence mirrors core-v2's own monthly top-up ritual.
- **(b) Trio ETF data only starts 1998-12** (XLP/XLU/XLV listed 1998-12-16, per `2026-07-12_ballast_parking_ab.md`); the AA window is further floored to 2001-01-23 by ^VXN, so the trio's pre-2001 history is used only to warm the rolling beta, not scored.
- **(c) LEAP/BSM model risk is inherited AS-IS from core v2**, unchanged: still ^VIX/^VXN 30d→1y IV-proxy based, with the same base (m0.85) / damped (0.4) IV caveats already on record (`2026-07-06_leap_real_sweep.md`, `2026-07-09_options_chain_spotcheck.md` — deep-ITM/skew underpricing risk unresolved). Both IV models are shown for every strategy; neither is cherry-picked.
- **(d) Beta warm-up**: rolling 252-td betas use each underlying's FULL native return history (QQQ from 1999-03, independent of the ^VXN option-IV join), so they are warm by the 2001-01-23 window start (beta_B[0]=0.37, beta_T[0]=2.08). Forced-zero (NaN-beta) bars INSIDE the reported window: **0** — the warm-up caveat did NOT bind.
- **(e) Cash-shortfall / B-bailout**: LEAP grows and reopens draw Cash first then (bailout) sell ballast; the monthly B-plug can also draw ballast to zero Cash. Bailout/underfund counts are in the AA-readouts table above. **At least one underfunding event triggered — see the counts; results past that point rely on the ballast-drain fallback.**
- **(f) 9c residual-plug interpretation**: step 9c ("rebalance B using whatever residual is left") is implemented as B being the true plug that drives Cash_val to 0 each month-start (Parked_val untouched). This is the only way the byte-identical B_target formula (1 − 0.25 − total_premium) conserves NAV given no explicit cash reserve; documented so it can be checked against the spec.
- **(g) Strict leftover-parked**: un-parking releases exactly the reopening leg's funding need; if a leg reopens needing less than was parked, the remainder stays in Parked (trio) — still fully deployed and NAV-conserving, but not swept back into B until a later reopen. A faithful reading of the spec (which only un-parks on buy).
- **(h) Single historical path**, one data vendor (yfinance-first); no bootstrap. Bonferroni×48 + DSR are the multiple-testing checks; both reported honestly per trial.

## Cross-foot verification

- 12 AA accounting runs, 307,056 bar-level assertions, ALL passed: NAV = T + B + L + Parked + Cash; NAV > 0; Cash >= 0; Parked >= 0; NAV_t = NAV_(t-1) + interest + B/T/Parked P&L + LEAP P&L - costs (all sleeve trades are internal transfers + costs; rel tol 1e-6). Any violation raises and aborts. core-v2 reproduction runs carry their own imported cross-foot asserts (exp_core_topup `simulate_portfolio_topup`).

## Conclusions

1. **AA's structure BUYS drawdown protection, at the cost of raw return — exactly what a beta-diversified, regime-scaled book should do.** On the AA common window (2001-01-23→2026-07-10), AA-strict base MaxDD -44.2% and AA-pragmatic -43.7% are ~11pp SHALLOWER than core-v2's -54.5% and SPY B&H's -55.6%. AA's worst 12m (-36.1% strict / -35.6% prag) also beats core-v2 (-45.8%). The price is raw return: AA-strict base CAGR +15.4% / α +7.5pp (t+5.0) vs core-v2's +22.3% / +12.4pp (t+5.4). **This is a STRUCTURE trade-off, not a verdict on AA's real edge** — the T sleeve carries ZERO thesis-alpha here by construction (scope limit), so ~5pp of the gap to core-v2 is precisely the alpha the live design expects the (unbacktestable) stock-picking T sleeve to supply.
2. **AA-strict beats AA-pragmatic on BOTH return and risk-adjusted alpha — the opposite of what the standalone ballast study's 14pp "strict MaxDD tax" implied.** Strict base +15.4% / +7.5pp (t+5.0) vs pragmatic +12.8% / +5.4pp (t+4.1), with essentially the SAME MaxDD (-44.2% vs -43.7%). Mechanism: strict parks gate-out premium in the trio and EXCLUDES it from the delta-ledger beta-netting, so the open leg re-levers more (and parked trio out-earns idle cash in recoveries). The ballast study's 14pp tax was measured on 100%-switched warehouses; in the full AA book the trio is the dominant sleeve in BOTH variants regardless, so the transient gate-out routing barely moves MaxDD. **The constraint's real cost is far smaller inside the full structure than the isolated pseudo-cash test suggested.**
3. **Base-IV alpha is decisive for every AA variant; damp-IV alpha survives only for strict — reported honestly, not hidden.** Bonferroni×48 (α≤0.00104): all 6 new trials PASS on base IV. On damp IV, only **AA-strict @115 (t+3.35, p=0.000794)** and AA-strict @130 clear the bar; AA-pragmatic @115 damp (t+2.87, p=0.00411) FAILS — the same pattern core-v2's own winner shows (its damp Bonferroni p=0.095 also missed its bar in `2026-07-06_core_topup.md`). DSR (vs the 48-cell universe) is ≥0.996 for all six, ≥0.999 for both @115 headliners.
4. **The delta ledger behaves as designed: monthly, bounded, and gate-responsive.** AA-strict avg alpha-capital share (0.25 + mean capped LEAP premium) and the delta-notional target series (median/p90 in the AA-readouts table) confirm the LEAP overlay fills the gap between the regime band and the (B+T) beta contribution, never exceeding the 15% premium cap. Routine ballast-funds-LEAP transfers ('bailout') are normal operation; the rarer parked last-resort tap ('underfund') fired 1 time(s) for strict, 0 for pragmatic — disclosed, NAV-conserving, all cross-foot asserts held.

## Implication

- **Structurally, Karst-AA is a viable alternative to core-v2: it gives up raw beta return for a materially shallower drawdown, WITHOUT needing any thesis-alpha to be competitive on risk-adjusted terms.** Since the live design intends the T sleeve to add idiosyncratic alpha on TOP of this structure (a forward-IC question this sim cannot answer), the honest read is: AA's structure does not lose to core-v2 on a risk-adjusted basis, and it has ~11pp more drawdown headroom into which real thesis alpha could be deployed. This matches the design doc's own pre-registered claim ('BT-2 能證明嘅係結構層面唔輸 core v2；T sleeve 嘅增量係 forward 問題').
- **Prefer AA-strict over AA-pragmatic on this evidence** — it dominates on return and alpha at equal drawdown, and its damp-IV alpha is the only one that survives Bonferroni×48. The design doc's recommendation was pragmatic (to avoid a feared 14pp MaxDD tax); that tax does not materialize inside the full structure, so the evidence flips the call. (Both remain on the table; this is a structure result, and the strict/pragmatic choice interacts with the live T sleeve's own cash needs, untested here.)
- **Model risk is the binding caveat, inherited wholesale from core-v2**: the entire LEAP overlay still prices on the ^VIX/^VXN 30d→1y IV proxy, with the deep-ITM/skew underpricing risk still unresolved (`2026-07-09_options_chain_spotcheck.md`). Both IV models are shown; the damp-IV column is the operative conservative read.
- **Next (not this study's job)**: BT-3 (regime band increment vs fixed 115%), BT-4 (washout boost), and — the real test of AA — forward IC/Brier on the live T sleeve, which no historical sim can stand in for.
