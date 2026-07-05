# Result — Top-10-days coverage & exposure-normalized alpha, fear/greed overlay (HANDOFF #8)

**Date:** 2026-07-03  **Script:** `backtest/experiments/exp_topdays_exposure.py`  **Tag:** reconstruction
(the 2026-07-03 capstone run was inline/unsaved — see `HANDOFF.md` — this is a documented
rebuild from findings #5-#8, not a byte-exact replay)

## Question
User: (1) does the fear/greed regime-timing approach avoid the classic "miss the market's
top 10 days, miss your year" trap? (2) if alpha is expressed per unit of exposure
(relevered to the same average market exposure as buy & hold), does the ~0 alpha
conclusion (finding #8) change?

## Method
3 variants, long-only, SPY/QQQ/SPMO, adjusted (total-return) closes, VIX + RSI(2) + real
CNN Fear&Greed history (2011-2026, github.com/whit3rabbit/fear-greed-data — cached to
`reference/fear_greed/`, gitignored/regenerable). 5bps cost per unit of exposure changed.
Signals decided on bar i−1 act on bar i (look-ahead-safe).

- **lev**: baseline 1.0x; FEAR (VIX>30 or RSI2(2)<10 & VIX>25) → **1.3x**; GREED (F&G>80) → 0.5x
- **nolev**: same triggers, FEAR → **1.0x** (no leverage) instead of 1.3x
- **mr**: flat-baseline (0x by default), enters ONLY on FEAR, exits on VIX<20 or F&G>55 —
  a pure MR-timing form (closer to what "avg exposure/beta ≈ 0.7" in finding #8 implies);
  included because lev/nolev run avg exposure ≈ 0.97-1.0, too close to B&H to make
  relevering (Q2) a meaningful test.
- **Relevered** = same signal timing, position scaled by 1/avg(exposure) so average
  exposure matches B&H's (1.0). Isolates: is alpha ≈0 real "no skill", or under-exposed
  skill being diluted?

## Results — alpha vs exposure (Q2)

| Asset | Variant | AvgExp | Alpha (raw) | t | Alpha (relevered to 1.0x) | t |
|---|---|---|---|---|---|---|
| SPY  | lev   | 0.99 | −1.33% | −1.9 | −1.34% | −1.9 |
| SPY  | nolev | 0.97 | −0.61% | −2.7 | −0.63% | −2.7 |
| SPY  | mr    | 0.14 | −2.61% | −1.2 | **−19.31%** | −1.2 |
| QQQ  | lev   | 0.99 | −1.13% | −1.4 | −1.14% | −1.4 |
| QQQ  | nolev | 0.97 | −0.75% | −2.3 | −0.77% | −2.3 |
| QQQ  | mr    | 0.13 | −2.12% | −0.8 | **−16.78%** | −0.8 |
| SPMO | lev   | 1.00 | −1.95% | −1.9 | −1.95% | −1.9 |
| SPMO | nolev | 0.98 | −0.83% | −2.2 | −0.84% | −2.2 |
| SPMO | mr    | 0.15 | −0.84% | −0.3 | **−5.75%**  | −0.3 |

(B&H CAGR/Sharpe: SPY 14.2%/0.86, QQQ 19.1%/0.94, SPMO 19.7%/0.99, 2011/2015→2026.)

## Results — top-10-day coverage (Q1)

Across all 3 assets, **9 or 10 of the top-10 single-day return dates** (2011-2026) occur
during VIX-elevated fear windows: the 2020-03 COVID crash rallies (5 of the 10 on SPY/QQQ),
2018-12-26, 2011-08-09 (debt-ceiling), 2025-04-09 (tariff shock). Only exception found:
SPMO 2016-07-25 (VIX 12.9, F&G 85 — a genuine calm/greed day, not a crash rally).

| Asset | B&H sum of top-10 days | lev captured | nolev captured | mr captured |
|---|---|---|---|---|
| SPY  | 66.4% | 84.7% (**128%** of B&H) | 66.4% (100%) | 60.9% (92%) |
| QQQ  | 78.6% | 100.0% (**127%**) | 78.6% (100%) | 59.9% (76%) |
| SPMO | 72.9% | 90.9% (**125%**) | 70.5% (97%) | 62.5% (86%) |

Reference (classic folklore stat, literal 0 exposure on those 10 days only): SPY total
return 670%→306%, QQQ 1372%→592%, SPMO 574%→234% — confirms the folklore is directionally
real, but none of the fear/greed variants come close to that miss rate.

## Conclusions

1. **The overlay does not fall into the "miss the top 10 days" trap — structurally the
   opposite.** The market's best single days cluster with its worst (violent
   short-covering rallies inside crashes), which is exactly when VIX/RSI2-based fear
   triggers fire. `lev` is *overweight* (1.3x) on 9-10/10 top days → captures 125-128% of
   B&H's top-day return. `nolev` is never underweight on them → captures ~97-100%. Only
   the flat-baseline `mr` variant — which is out of the market ~85% of the time by
   construction — leaks some (76-92%), because its calm-exit (VIX<20 or F&G>55) can fire
   just before the rally.
2. **Raw alpha is mildly-to-moderately NEGATIVE, not the ≈0 of finding #8**, across all 3
   variants × 3 assets after cost — `nolev` is the most consistent (t=−2.2 to −2.7,
   borderline significant by this repo's |t|>2 convention). Likely explained by
   reconstruction differences from the untracked capstone (see Caveats), not a
   contradiction — same conclusion, slightly sharper number.
3. **Relevering to B&H's average exposure does NOT unlock hidden alpha — anywhere.** For
   `lev`/`nolev` (avg exposure already ≈0.97-1.0) it mechanically changes almost nothing.
   For `mr` (avg exposure ≈0.13-0.15) relevering means ~7x leverage during fear windows —
   alpha gets **massively worse** (−17% to −19%/yr), not better: leveraging into exactly
   the highest-vol regime amplifies compounding/vol drag faster than it amplifies any
   timing edge. SPMO's relevered `mr` equity curve goes negative (CAGR undefined) —
   evidence the naive rescale is untradeable, not a real strategy.
4. **Mechanism, general takeaway:** relevering only rescales the *same* timing decisions by
   a constant — it cannot flip a mistimed/non-predictive signal's alpha sign, only amplify
   whatever is already there (worse here, because leverage lands in the worst-vol regime).
   Answering the user's Q2 directly: **yes, dividing/relevering by exposure changes the
   number — but not the sign, and not the conclusion.**

## Caveats
- Reconstruction, not the original untracked capstone (see HANDOFF) — thresholds
  (VIX 30/25/20, F&G 80/55, RSI2<10) are a best-effort rebuild from findings #5-#8.
- `mr`'s relevered case is a naive constant-leverage rescale with no vol-targeting or
  margin constraint — included only to demonstrate the mechanism, not as a tradable
  strategy.
- 15-year sample; several top-10 days cluster in 2 events (2020 COVID, 2011 debt-ceiling)
  → not fully independent draws. DSR reported per-cut but multiple-testing universe is
  small (9 trials).
- F&G ffill limited to 5 days (holiday/gap tolerance); real CNN history, not a proxy.

## Refinement (same day) — B&H exposure=1 is trivial; ours must be CALCULATED, not assumed
User's correction: B&H's exposure is 1.0 by construction (buy Jan-1, hold to Dec-31) —
not something to test. `lev`/`nolev` above landed at avg exposure ≈0.97-1.0 (basically
B&H-plus-a-small-overlay), which makes relevering on them close to a no-op — a weak test
of Q2 (already flagged in the original Caveats). Two follow-ups, in order of rigor:

1. `backtest/experiments/exp_exposure_sweep.py` — swept a fixed hold-period knob (5/10/21/42/63d)
   post-FEAR-entry to trace exposure from ~0.12→0.48 and watch whether "relevering
   doesn't rescue alpha" holds across the range. It does, at every point tested (alpha
   stays negative pre- and post-relever, all 3 assets). **But picking hold-days to hit a
   target exposure is itself an assumption** — superseded by:
2. `backtest/experiments/exp_mr_roundtrip.py` — the canonical test: entry and exit BOTH taken
   directly from the findings, no exposure target assumed —
   **ENTRY** (finding #5): `VIX>30` or `(RSI2(2)<10 & VIX>25)`.
   **EXIT** (finding #7 "lock the bounce" + finding #6 "froth trim"): `RSI2(2)>90` or
   `F&G>80`. Average exposure is whatever this produces, not chosen.

   | Asset | Trades | Win% | **Calculated AvgExp** | Alpha (raw) | t | Alpha (relevered to 1.0x) | t |
   |---|---|---|---|---|---|---|---|
   | SPY  | 45 | 87% | **13.7%** | −1.65% | −0.8 | **−12.08%** | −0.8 |
   | QQQ  | 44 | 80% | **14.4%** | −1.74% | −0.7 | **−12.06%** | −0.7 |
   | SPMO | 34 | 79% | **14.6%** | −0.78% | −0.2 | **−5.35%**  | −0.2 |

   All 3 assets converge to a calculated avg exposure of **~14%** independent of the
   exact exit rule (matches the earlier ad hoc `mr` variant's ~0.13-0.15 almost exactly)
   — the FEAR entry condition (rare, extreme) is what dominates time-in-market, not the
   exit choice. Relevering (~7x, to match B&H's exposure=1.0) does not rescue alpha —
   it turns a small, statistically insignificant negative (t≈−0.2 to −0.8) into a large,
   still-negative one (−5% to −12%/yr) via compounding/vol drag under leverage.

**Cross-check across every exposure level actually tested today** (0.12 → 1.00, via three
independently-built variants: `mr_roundtrip` ≈0.14, `exposure_sweep` 0.12–0.48,
`lev`/`nolev` ≈0.97–1.0): **relevering never flips alpha positive, at any exposure
level.** The Q2 answer is robust to the "what should avg exposure be" methodology
question the user raised — it doesn't depend on which reconstruction you pick.

**Open gap, honestly flagged:** none of these reconstructions land near finding #8's
stated **beta≈0.7** — the findings-grounded round-trip calculates to ~0.14, and the
B&H-plus-overlay design sits at ~1.0. The original capstone (unsaved, inline) likely
blended these differently (e.g. a base allocation + smaller tactical tilt, or gentler
entry/exit thresholds than VIX>30/RSI2<10/RSI2>90) — that exact design is not recoverable
without the original session. Does not change the Q2 conclusion (negative-to-flat alpha,
relevering doesn't help across the whole 0.14–1.0 range tested), but flags that the
*specific* 0.7 figure from finding #8 remains a citation to an unreplicated run, not a
number this rebuild reproduces.

## Refinement 2 (same day) — split RSI2 and VIX+F&G into 2 INDEPENDENT rules
`exp_mr_roundtrip.py`'s entry/exit OR'd both signal families together. User asked to
isolate them: does RSI2 alone, or VIX+F&G alone, do the work — or does combining them
just dilute/cancel (per finding #3's "blending cancels" pattern)? `exp_mr_split_rules.py`:

| Asset | Rule | N trades | Win% | Calc AvgExp | Alpha (raw) | t | Alpha (relevered) | t |
|---|---|---|---|---|---|---|---|---|
| SPY  | rsi2 (entry<10, exit>90)   | 120 | 79% | 39.1% | −1.17% | −0.6 | −3.00%  | −0.6 |
| SPY  | vix_fg (entry VIX>30, exit F&G>80) | 6 | 100% | 49.0% | −2.78% | −1.5 | −5.67%  | −1.5 |
| SPY  | combo (OR'd, reference)    | 45  | 87% | 13.7% | −1.65% | −0.8 | −12.08% | −0.8 |
| QQQ  | rsi2                       | 119 | 76% | 39.4% | −2.36% | −0.9 | −5.98%  | −0.9 |
| QQQ  | vix_fg                     | 6   | 83% | 49.0% | −4.84% | **−2.1** | −9.87% | −2.1 |
| QQQ  | combo                      | 44  | 80% | 14.4% | −1.74% | −0.7 | −12.06% | −0.7 |
| SPMO | rsi2                       | 85  | 73% | 38.2% | −3.24% | −1.1 | −8.50%  | −1.1 |
| SPMO | vix_fg                     | 4   | 100%| 59.7% | −4.52% | **−2.0** | −7.57% | −2.0 |
| SPMO | combo                      | 34  | 79% | 14.6% | −0.78% | −0.2 | −5.35%  | −0.2 |

- **RSI2 alone is the workhorse**: 85–120 trades, ~39% calculated exposure (the highest
  of any variant tested today besides the ~1.0x B&H-overlay ones) — a genuinely
  moderate, non-trivial exposure level, reached without picking any threshold to hit it.
  Alpha still negative but weak/insignificant (t=−0.6 to −1.1).
- **VIX+F&G alone is rare and fragile**: only **4–6 trades in 15 years** (VIX>30 is a
  crisis-only trigger). Its alpha looks more negative and more "significant" (t up to
  −2.1) but **this significance is not trustworthy** — 4–6 discrete episodes is too few
  for the t-stat's daily-return machinery to represent independent draws; it's likely 1–2
  bad trades (2020 unwind timing, 2018 Q4) dominating. Flag, don't over-read.
- **Combining does NOT cancel/dilute vs either alone here** (unlike finding #3's VIX/F&G
  blending-cancels-signal pattern) — for QQQ/SPMO, `combo`'s alpha is actually LESS
  negative than either isolated rule (some diversification from mixing 2 different-timing
  trade populations), though never positive. For SPY it sits between the two.
- **Still no positive alpha anywhere** — RSI2 alone (the best-powered, most trades, least
  fragile cut) confirms the same conclusion with the least small-sample risk of the three.

## Refinement 3 (same day) — capital-efficiency lens: the user was right, per-exposure it IS efficient
`backtest/experiments/exp_capital_efficiency.py`. User's objection: Jensen alpha and the relevered-CAGR
figures both understate a real fact — the strategy trades SPY, so *while invested* it earns
the SPY rate; comparing its (mostly-flat) calendar CAGR against always-up B&H is the "unfair"
framing. Correct measure = return PER UNIT OF EXPOSURE (PnL% / exposure). This is a
CAPITAL-adjusted question, distinct from Jensen alpha's RISK/beta-adjusted one — and both
are true at once.

| Asset | Rule | AvgExp | calendar CAGR | **PnL/Exp (arith)** | **deployed-cap ann. (geom)** | mean-daily-invested vs B&H | **Sharpe-while-invested** vs B&H | Jensen α (t), β |
|---|---|---|---|---|---|---|---|---|
| SPY  | rsi2  | 39.1% | 7.97% | 20.4% | 24.1% | 1.64x | **1.08** vs 0.86 | −1.17% (−0.6), β0.67 |
| SPY  | combo | 13.7% | 5.25% | 38.4% | 48.5% | 3.05x | **1.37** vs 0.86 | −1.65% (−0.8), β0.51 |
| QQQ  | rsi2  | 39.4% | 8.71% | 22.1% | 26.0% | 1.35x | **1.02** vs 0.94 | −2.36% (−0.9), β0.61 |
| QQQ  | combo | 14.4% | 6.26% | 43.4% | 55.5% | 2.59x | **1.38** vs 0.94 | −1.74% (−0.7), β0.45 |
| SPMO | rsi2  | 38.2% | 8.05% | 21.1% | 25.1% | 1.28x | **1.00** vs 0.99 | −3.24% (−1.1), β0.61 |
| SPMO | combo | 14.6% | 8.11% | 55.5% | 74.2% | 3.10x | **1.70** vs 0.99 | −0.78% (−0.2), β0.48 |

Robust across BOTH rules and ALL 3 assets: the timing deploys into **above-average-return
days** (1.3–3.1x B&H's mean daily) at a **conditional Sharpe that beats B&H** (1.0–1.7 vs
0.86–0.99). So per unit of capital deployed, the MR timing is efficient — it concentrates
capital into the highest-return windows.

**Why Jensen α is still ≈0/slightly-negative despite this (not a contradiction):** β≠exposure.
combo deploys only ~14% of days but the regression β is ~0.45–0.51, because it enters
high-VOLATILITY fear days whose large |returns| dominate Cov(strat,mkt). CAPM treats that as
"~0.5 beta held full-time" and demands ~0.5×market to break even; earning it in concentrated
bursts nets a small, INSIGNIFICANT (t −0.2 to −1.1) negative α. Per-time-capital = efficient;
per-unit-systematic-risk = neutral. Different questions, both true.

**The earlier relevered-CAGR framing (Refinements 1–2) was a misleading way to express
per-exposure performance** — geometric releverage to exposure=1.0 applies ~7x leverage to
33–37%-vol fear windows, and the resulting −5% to −12% "alpha" is dominated by leverage
vol-drag, NOT timing skill. The arithmetic PnL/Exp (user's formula) and the deployed-capital
geometric annualization are the honest capital-efficiency measures, and they are strongly
POSITIVE vs B&H.

## Implication for Karst (revised)
Two lenses, both must be stated:
1. **As a SPY-replacement / total-wealth engine — still no.** Flat ~86% of the time in a
   secular uptrend → calendar CAGR (5–8%) lags B&H (14–20%). And you cannot naively lever it
   back to full exposure to capture the efficiency — leverage on the fear windows' 33–37% vol
   reintroduces the drag (that's what the relevered −12% was). Consistent with finding #8's
   do-not-deploy-as-alpha call.
2. **As a DRY-POWDER DEPLOYMENT timer — genuinely useful, and stronger than "just a risk
   knob".** For capital you'd hold as cash/liquidity anyway, deploying it via this signal
   earns a high rate ON DEPLOYED CAPITAL (24–74% annualized) at a conditional Sharpe > B&H.
   The knob doesn't just cut beta (finding #8) — the beta it keeps is concentrated into the
   market's best-paid windows.

Caveats: conditional (in-market-only) Sharpe is a sampling statistic on self-selected bounce
windows — wide error bars for combo's few episodes; RSI2-alone (1000+ invested days) is the
trustworthy version and still shows the effect (1.0–1.1 conditional Sharpe, 1.3–1.6x daily).
Costs modelled on transitions only; idle-capital opportunity cost and tax friction of
frequent in/out are NOT modelled and would eat into the deployment-timer use case.

## Refinement 4 (same day) — WHY trading SPY-vs-SPY neutralizes the timing skill
`backtest/experiments/exp_alpha_decomp.py`. User's point: "good timing → positive alpha only makes
sense for SPY if exposure is high enough, or leveraged, or the traded instrument isn't SPY
itself." Confirmed via an EXACT identity for a long/flat strat = pos·mkt regressed on the
same mkt it trades:

  alpha = Cov(pos, mkt)  +  (exposure − beta)·mean_mkt
          └─ T1 timing ─┘    └──── T2 structural drag ────┘

| Asset | Rule | Exp | β | β/Exp | **T1 timing skill** | **T2 structural drag** | gross α (=T1+T2) |
|---|---|---|---|---|---|---|---|
| SPY  | rsi2  | 39% | 0.67 | 1.71x | **+3.67%** | −4.07% | −0.39% |
| SPY  | combo | 14% | 0.51 | 3.73x | **+4.14%** | −5.50% | −1.36% |
| QQQ  | rsi2  | 39% | 0.61 | 1.55x | **+2.71%** | −4.29% | −1.58% |
| QQQ  | combo | 14% | 0.45 | 3.10x | **+4.50%** | −5.95% | −1.45% |
| SPMO | rsi2  | 38% | 0.61 | 1.60x | **+2.16%** | −4.60% | −2.44% |
| SPMO | combo | 15% | 0.48 | 3.26x | **+6.17%** | −6.63% | −0.46% |

- **T1 (timing skill) is POSITIVE in all 6 cases** (+2.2% to +6.2%/yr) — the position DOES
  anticipate above-average days. The user's "if timing works, alpha positive" logic is
  correct at the signal level; it's T2 that neutralizes it at the portfolio level.
- **T2 (structural drag) is negative because β ≫ exposure** (1.5–3.7×): buy-the-dip forces
  entry into high-VARIANCE fear days, inflating the OLS β far above the deployed fraction;
  you carry that β's risk while sitting flat through the market's up-drift the rest of the
  time. This is STRUCTURAL to timing an up-drifting index against itself, not a bad signal.
- **The user's three remedies, precisely** (verified, not asserted):
  - *Higher exposure* — does NOT create positive Jensen α by itself. Adding an always-on SPY
    baseline b moves exposure→exp+b AND β→β+b, leaving (exposure−β) and α UNCHANGED (a
    zero-α, β-1 dilution toward B&H). It fixes the total-WEALTH lag (less cash drag), not α.
  - *Leverage* — does NOT flip α. Uniform L scaling gives α→L·α (sign-preserving): −1.36%
    → −2.7% at 2×. And geometrically it reintroduces the vol-drag (Refinement 3's relevered
    −12%). Not a fix.
  - *Traded instrument ≠ SPY* — **the structural fix.** If "when invested" you earn some
    instrument X ≠ the SPY benchmark, the per-day return is no longer capped at SPY's, so
    T1 (Cov) can be large enough to clear T2. This is the ONLY one of the three that
    converts the +T1 timing skill into realized outperformance.

**This validates the existing Karst architecture, not overturns it.** Karst applies RSI-2 /
fear timing as an ENTRY-timing field on individual oversold names (tier-2 long-only) and on
option structures (LEAP/CSP entries harvesting VRP) — NOT as an SPY-in/out timer benchmarked
against SPY. `exp_family_validate.py` already showed RSI-2 long-only holding the top quintile
of the BROAD universe beats SPY B&H by +12.5% CAGR — the same +T1 skill, harvested on the
right instrument (X ≠ benchmark), where T2 doesn't apply. The user re-derived, from the alpha
algebra alone, exactly why Phase 4 keeps RSI-2 as a separate entry-timing field rather than an
index-alpha engine (ARCHITECTURE.md §3 firewall + §5 "MR = gated timing overlay, not
standalone alpha").
