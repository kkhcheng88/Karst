# Result — Sector-ETF capital-efficiency loop (Core Loop-2): 4 pre-registered deployment hypotheses

**Date:** 2026-07-06
**Script:** `backtest/experiments/exp_sector_capeff.py`
**Tag:** active — negative/mixed (no hypothesis clears significance at the increment level; H4 finds a
real, regime-dependent but not-significant-on-its-own buffer effect, consistent with the prior in
`2026-07-06_portfolio_rotation.md`)

## Question

Quant cross-sectional sector **rotation** (predicting which sector wins) is already a closed, negative
line (0/28 factors past Bonferroni — `exp_rotation_challenge.py`, `exp_skill_curve.py`,
`docs/2026-07-06_core_strategy.md` §5). This loop does **not** revisit that. It asks a narrower,
user-requested question instead: **given money is already being deployed at some moment for a
non-sector reason (a dip-buy, a panic hedge, a defensive tilt, a buffer asset), is expressing that
deployment through sectors better than expressing it through SPY at the same moment?** Every
hypothesis therefore carries an explicit **control leg** on the identical entry/exit dates buying SPY
instead (mirror/increment discipline — memory `validation-mirror-and-increment`); the number that
matters is the increment (strategy − control), not the absolute return.

- **H1** Cross-sectional dip rotation inside a bull regime (RSI-2<10 dip-buys, cap 3 sectors, 2x2
  exit grid).
- **H2** Panic-window sector deployment (buy the 2 worst-63d-return sectors when SPY>200SMA &
  VIX>28; bear+panic variant reported separately).
- **H3** Portfolio-level defensive sector tilt (XLP/XLV/XLU) on bear-hysteresis, vs doing nothing and
  vs just buying more SPY with the same capital.
- **H4** Defensive-leg asset choice in a core shell: cash vs IEF (bonds) vs 50/50, following up on
  `2026-07-06_portfolio_rotation.md`'s finding that bonds beat cash as a rotation sleeve's defensive
  leg — does that hold at the core-shell buffer level too?

## Method

**Universe (point-in-time):** 11 SPDR sectors — XLK/XLF/XLE/XLV/XLI/XLP/XLU/XLY/XLB (long history,
1998-12-22+) and XLRE (2015-10-08+) / XLC (2018-06-19+, short history). No ffill-before-inception:
a sector simply has no price series (and is excluded from cross-sectional selection) before its own
inception — this mechanically implements "XLRE/XLC only from their real start", no separate window
hack needed. SPY, IEF (7-10y Treasury), ^VIX, ^IRX (13-week T-bill, cash-rate proxy) load alongside.

**Data:** `backtest/data.py` `load(sym, adjusted=True)` (yfinance total-return; dividends matter a lot
for high-yield sectors) for sectors/SPY/IEF; `^VIX`/`^IRX` loaded raw (no dividends, adjusted has no
effect on an index). Master calendar = SPY's own trading-day index (1993-01-29 → 2026-07-06, 8,414
rows; live pull, network confirmed working, same-day as this report).

**Cost:** 5bps/side on every ETF trade (entry, exit, and monthly rebalance in H4), repo standard.
**Execution:** signal computed from data through close T; trade executes at close T+1 (the
conservative literal reading — applied uniformly to *entries and exits alike*, so a "5-day timeout"
in H1 can realize as a 6-trading-day hold once the one-day execution lag on the exit itself is
counted; documented, not a bug).
**Windows:** FULL 2000-2026 / 2016-2020 / 2021+ for H1-H3 (sector-200SMA warmup-safe); H4 is
IEF-inception-constrained (FULL 2002-08-01+ / 2016-2020 / 2021+), plus 2008/2020/2022 stress-year
detail.
**Stats:** increment = paired t-test (scipy `ttest_1samp` on the excess/diff series, which *is* the
paired same-day/-episode diff) — no Bonferroni applied here (left to the orchestrator across the
whole research program); each section reports its own trial count for that purpose.
**Cross-foot asserts:** H1 caps concurrent positions at 3 (never >100% notional); H3 asserts
cash/base legs never go negative; H4 asserts NAV stays positive — all passed on every run.

## Results

### H1 — cross-sectional dip rotation (bull-gated, cap 3 sectors, 1/3 notional each)

2x2 grid = exit on RSI-2>{70,80} OR {5,10}-trading-day timeout, whichever first. "Deployed CAGR" /
"cond. Sharpe" = capital-efficiency lens (return/Sharpe computed only over days capital is actually
deployed, `exp_capital_efficiency.py` convention), reported for both the sector strategy and its
same-footprint SPY control.

| exit rule | window | n | mean excess/trade | t (p) | win% | avg days held | deployed CAGR strat | deployed CAGR ctrl | cond.Sharpe strat | cond.Sharpe ctrl |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| RSI>70 / 5td | FULL 2000-2026 | 1409 | +0.060% | t+1.44 (p=.149) | 53.7% | 4.2 | +13.83% | +10.02% | 0.85 | 0.73 |
| RSI>70 / 5td | 2016-2020 | 327 | −0.085% | t−1.09 (p=.275) | 51.4% | 4.3 | +7.01% | +13.85% | 0.50 | 1.03 |
| RSI>70 / 5td | 2021+ | 365 | +0.096% | t+1.00 (p=.320) | 55.6% | 4.1 | +18.88% | +11.76% | 1.11 | 0.88 |
| RSI>70 / 10td | FULL | 1251 | +0.043% | t+0.93 (p=.354) | 54.8% | 5.0 | +13.35% | +11.68% | 0.80 | 0.80 |
| RSI>70 / 10td | 2016-2020 | 288 | −0.124% | t−1.33 (p=.185) | 51.7% | 5.1 | +1.53% | +8.78% | 0.18 | 0.64 |
| RSI>70 / 10td | 2021+ | 326 | +0.063% | t+0.61 (p=.542) | 55.5% | 4.9 | +27.73% | +19.98% | 1.55 | 1.38 |
| RSI>80 / 5td | FULL | 1363 | +0.057% | t+1.21 (p=.225) | 52.2% | 4.9 | +14.11% | +10.55% | 0.87 | 0.77 |
| RSI>80 / 5td | 2016-2020 | 319 | −0.147% | t−1.68 (p=.093) | 51.1% | 5.0 | +4.72% | +14.26% | 0.37 | 1.07 |
| RSI>80 / 5td | 2021+ | 351 | +0.130% | t+1.24 (p=.215) | 53.8% | 4.9 | +18.32% | +11.48% | 1.12 | 0.87 |
| RSI>80 / 10td | FULL | 1136 | +0.042% | t+0.74 (p=.458) | 54.1% | 6.6 | +11.15% | +9.65% | 0.69 | 0.69 |
| RSI>80 / 10td | 2016-2020 | 264 | −0.133% | t−1.17 (p=.242) | 53.0% | 6.6 | −0.60% | +7.34% | 0.05 | 0.55 |
| RSI>80 / 10td | 2021+ | 292 | +0.032% | t+0.25 (p=.799) | 54.5% | 6.4 | +20.05% | +17.38% | 1.19 | 1.24 |

**No cell clears |t|≥2.** Trial count: 4 grid cells × 3 windows = 12 tests, all 12 had n≥3.

### H2 — panic-window sector deployment (worst-63d-return pair, exit VIX<18)

Rare by construction; reported per-episode (not just aggregated), per spec.

**Quadrant ② bull+panic (SPY>200SMA & VIX>28) — the brief's primary case, n=14 episodes:**

| entry | exit | sectors | entry VIX | exit VIX | days | strat% | ctrl% | excess% |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 1999-05-26 | 1999-07-12 | XLP+XLY | 28.9 | 18.0 | 31 | 3.97 | 7.45 | −3.48 |
| 1999-08-11 | 2000-08-15 | XLY+XLF | 28.5 | 17.9 | 256 | 10.60 | 15.60 | −5.00 |
| 2003-03-24 | 2003-07-28 | XLP+XLE | 28.7 | 17.8 | 87 | 6.30 | 15.49 | −9.20 |
| 2007-08-13 | 2007-09-27 | XLF+XLY | 28.3 | 17.6 | 32 | 2.64 | 5.81 | −3.17 |
| 2009-06-01 | 2010-01-12 | XLU+XLV | 28.9 | 17.5 | 156 | 19.65 | 21.72 | −2.06 |
| 2010-05-07 | 2010-12-08 | XLV+XLU | 32.8 | 18.0 | 149 | 6.63 | 11.81 | −5.18 |
| 2011-03-17 | 2011-03-28 | XLK+XLP | 29.4 | 17.9 | 7 | 3.33 | 2.79 | +0.54 |
| 2011-11-14 | 2012-02-03 | XLF+XLB | 30.0 | 18.0 | 55 | 11.88 | 7.81 | +4.07 |
| 2018-02-06 | 2018-02-26 | XLU+XLRE | 37.3 | 16.5 | 13 | 2.36 | 3.16 | −0.80 |
| 2020-03-03 | 2021-04-05 | XLE+XLB | 33.4 | 17.3 | 274 | 33.61 | 38.19 | −4.58 |
| 2021-11-29 | 2021-12-27 | XLC+XLU | 28.6 | 18.0 | 19 | 2.77 | 2.98 | −0.21 |
| 2022-01-25 | 2023-02-02 | XLC+XLF | 29.9 | 17.9 | 257 | −9.38 | −2.61 | −6.76 |
| 2024-08-06 | 2024-08-15 | XLE+XLY | 38.6 | 16.2 | 7 | 4.74 | 5.82 | −1.07 |
| 2026-03-09 | 2026-04-17 | XLF+XLK | 29.5 | 17.9 | 28 | 7.53 | 4.88 | +2.65 |

**AGGREGATE:** mean excess = **−2.45%**, t=−2.52 (p=0.026, n=14 — small-n, indicative), win% = 21.4%
(only 3 of 14 episodes beat SPY).

**Quadrant ③ bear+panic variant (SPY≤200SMA & VIX>28, expected negative), n=15 episodes:** mean
excess = **+0.70%**, t=+0.52 (p=0.611, n=15), win% = 60.0% (full episode table in script stdout log;
range −11.94% to +7.26% excess, dominated by two large-magnitude 2022 and dot-com-bust episodes).

Trial count: 2 quadrant variants tested (14 + 15 episodes).

### H3 — portfolio-level defensive tilt (75/25 SPY/cash shell)

Bear-hysteresis = close < 0.98×200SMA for 5 consecutive days (re-entry to bull is immediate, no
hysteresis, per the T2 rule already used in `docs/2026-07-06_core_strategy.md`).

| config | window | CAGR | Sharpe | MaxDD | Alpha vs DoNothing (t) | Beta |
|---|---|---:|---:|---:|---|---:|
| Control-DoNothing (75/25, never touched) | FULL 2000-2026 | +7.93% | 0.53 | −48.7% | — | — |
| Control-DoNothing | 2016-2020 | +14.55% | 0.84 | −32.1% | — | — |
| Control-DoNothing | 2021+ | +14.97% | 0.92 | −23.7% | — | — |
| Variant A (25pp cash→defensive XLP/XLV/XLU) | FULL | +7.93% | 0.51 | −53.6% | −0.37% (t−1.5) | 1.06 |
| Variant A | 2016-2020 | +14.92% | 0.84 | −32.7% | +0.03% (t+0.1) | 1.02 |
| Variant A | 2021+ | +15.04% | 0.92 | −23.8% | −0.01% (t−0.1) | 1.01 |
| Control A-SPY (25pp cash→more SPY) | FULL | +7.96% | 0.50 | **−54.6%** | −0.48% (t−1.6) | 1.09 |
| Control A-SPY | 2016-2020 | +15.09% | 0.85 | −32.7% | +0.14% (t+0.6) | 1.03 |
| Control A-SPY | 2021+ | +15.11% | 0.93 | −23.6% | +0.04% (t+0.3) | 1.01 |
| Variant B (25pp cash + 25pp pulled from base → defensive, 50pp total) | FULL | +6.69% | 0.49 | −49.2% | −0.54% (t−1.0) | 0.91 |
| Variant B | 2016-2020 | +12.45% | 0.80 | −29.4% | −0.39% (t−0.3) | 0.88 |
| Variant B | 2021+ | +12.53% | 0.93 | −20.5% | +0.15% (t+0.2) | 0.82 |
| Control B-SPY (50pp → more SPY) | FULL | +7.14% | 0.48 | **−54.0%** | −0.72% (t−1.3) | 1.01 |
| Control B-SPY | 2016-2020 | +13.96% | 0.88 | −28.3% | +0.76% (t+0.8) | 0.90 |
| Control B-SPY | 2021+ | +13.90% | 0.97 | −19.8% | +0.70% (t+1.0) | 0.87 |

**Increment (Variant − SPY-control, paired daily t-test):**

| variant | window | ann. diff | t (p) | n |
|---|---|---:|---|---:|
| A − A-SPY | FULL | −0.10pp/yr | t−0.64 (p=.520) | 6665 |
| A − A-SPY | 2016-2020 | −0.15pp/yr | t−1.26 (p=.207) | 1259 |
| A − A-SPY | 2021+ | −0.07pp/yr | t−0.72 (p=.472) | 1381 |
| B − B-SPY | FULL | −0.69pp/yr | t−1.02 (p=.308) | 6665 |
| B − B-SPY | 2016-2020 | −1.36pp/yr | t−1.29 (p=.196) | 1259 |
| B − B-SPY | 2021+ | −1.33pp/yr | t−1.23 (p=.218) | 1381 |

No cell clears |t|≥2 either against DoNothing or against the SPY-control. The one directionally
consistent (not significant) signal: MaxDD is slightly *better* under the sector-basket variants than
their SPY-control twins (A: −53.6% vs −54.6%; B: −49.2% vs −54.0%) — i.e. if anything, the defensive
basket shaves drawdown a little vs. just buying more SPY at the same moments, at essentially zero
CAGR cost. Trial count: 2 variants × 2 comparisons (vs DoNothing, vs SPY-control) × 3 windows = 12
tests.

### H4 — defensive leg: cash vs IEF (bonds) vs 50/50

Core shell 75% SPY / 10% LEAP-premium PROXY (simplified per spec to a 1.7×-daily-reset SPY exposure
sleeve — **not** a real option; no theta/skew/crash-vega modeled) / 15% buffer, monthly rebalance to
target weights.

**Full period + sub-windows:**

| window | series | CAGR | Sharpe | MaxDD |
|---|---|---:|---:|---:|
| FULL 2002-2026 (IEF-constrained) | SPY 100% B&H (ref) | +11.37% | 0.66 | −55.2% |
| FULL | shell 75/10/buffer=cash | +10.75% | 0.68 | −52.0% |
| FULL | shell 75/10/buffer=IEF | +11.11% | 0.70 | −50.7% |
| FULL | shell 75/10/buffer=50/50 | +10.93% | 0.69 | −51.3% |
| 2016-2020 | SPY (ref) | +15.45% | 0.84 | −33.7% |
| 2016-2020 | buffer=cash | +14.44% | 0.86 | −31.0% |
| 2016-2020 | buffer=IEF | +15.07% | 0.91 | −30.2% |
| 2016-2020 | buffer=50/50 | +14.75% | 0.88 | −30.6% |
| 2021+ | SPY (ref) | +15.38% | 0.92 | −24.5% |
| 2021+ | buffer=cash | +14.67% | 0.95 | −22.6% |
| 2021+ | buffer=IEF | +13.80% | 0.89 | −24.7% |
| 2021+ | buffer=50/50 | +14.24% | 0.92 | −23.6% |

**Stress windows (within-window rebased MaxDD):**

| window | series | CAGR | MaxDD |
|---|---|---:|---:|
| 2008 GFC | SPY (ref) | −36.24% | −47.1% |
| 2008 GFC | buffer=cash | −33.79% | −44.0% |
| 2008 GFC | buffer=IEF | **−32.19%** | **−43.1%** |
| 2008 GFC | buffer=50/50 | −32.99% | −43.6% |
| 2020 COVID | SPY (ref) | +17.24% | −33.7% |
| 2020 COVID | buffer=cash | +16.19% | −31.0% |
| 2020 COVID | buffer=IEF | **+17.94%** | **−30.2%** |
| 2020 COVID | buffer=50/50 | +17.07% | −30.6% |
| 2022 selloff | SPY (ref) | −18.78% | −24.5% |
| 2022 selloff | buffer=cash | **−17.12%** | **−22.6%** |
| 2022 selloff | buffer=IEF | −19.32% | −24.7% |
| 2022 selloff | buffer=50/50 | −18.22% | −23.6% |

**Increment (buffer variant − cash-buffer, paired daily t-test):**

| window | comparison | ann. diff | t (p) | n |
|---|---|---:|---|---:|
| FULL 2002-2026 | IEF − cash | +0.27pp/yr | t+1.28 (p=.201) | 6019 |
| FULL 2002-2026 | 50/50 − cash | +0.14pp/yr | t+1.28 (p=.201) | 6019 |
| 2016-2020 | IEF − cash | +0.50pp/yr | t+1.30 (p=.192) | 1259 |
| 2016-2020 | 50/50 − cash | +0.25pp/yr | t+1.30 (p=.193) | 1259 |
| 2021+ | IEF − cash | −0.74pp/yr | t−1.53 (p=.126) | 1381 |
| 2021+ | 50/50 − cash | −0.37pp/yr | t−1.53 (p=.126) | 1381 |

No window clears significance either direction, but the **sign flips exactly where expected**: bonds
help in the classic equity-crash episodes (2008: better CAGR *and* MaxDD; 2020: better CAGR *and*
MaxDD) and hurt in 2022's stocks-and-bonds-fall-together regime (worse CAGR *and* MaxDD than cash).
Trial count: 3 buffer variants, 2 increments × 3 windows = 6 increment tests + 9 stress-window cells.

## Conclusions

**H1 (cross-sectional dip rotation):** No significant increment in any of the 4 grid cells × 3
windows (max |t|=1.68). Directionally mixed: positive-but-small in FULL/2021+, consistently negative
in 2016-2020 (worst cell: RSI>80/10td deployed-CAGR 11.15%→−0.60% swing vs SPY's 9.65%→7.34%, i.e.
sector dip-picks actively **lagged** SPY that specific half). **Verdict: no edge.**

**H2 (panic-window deployment):** Quadrant ② (the brief's primary hypothesis) is the one place this
loop found a *significant* result — and it is **significantly negative**: buying the worst-63d-return
sector pair during a bull-market VIX>28 spike underperformed just buying SPY by −2.45%/episode
(t=−2.52, p=0.026, n=14, only 3/14 wins). Contrarian sector-picking into a fear spike, inside an
uptrend, looks like catching falling laggards rather than buying a recoverable dip. Quadrant ③
(bear+panic) variant is directionally positive but not significant (n=15, wide dispersion driven by
2 large episodes) — reported per spec, not elevated to a claim. **Verdict: H2's primary case is
negative (significant); the bear-variant is noise, not a finding.**

**H3 (portfolio-level defensive tilt):** No alpha vs either control in any window/variant (max
|t|=1.6, all vs-DoNothing; max |t|=1.29 vs SPY-control). Confirms the prior flagged as "未驗證" in
`docs/2026-07-06_core_strategy.md` §4 ("低波/防守板塊 = 防守非 alpha") **now at the portfolio level**:
the defensive-sector basket does not add return over doing nothing, and does not add return over
simply de-risking into more SPY at the same trigger dates — its only (non-significant) edge is a
slightly shallower MaxDD than the SPY-control twin. Variant B (pulling 25pp from the equity base) is,
as flagged in the brief, a structural index-timing bet and shows the expected mild negative alpha vs
DoNothing (−0.54pp FULL, not significant) — reported negative, not massaged. **Verdict: no alpha;
keep defensive-sector tilt OUT of the core's mechanical rule set, consistent with the existing core
decision not to add sector branches (`2026-07-06_core_strategy.md` §5).**

**H4 (defensive leg — cash vs bonds):** No increment clears significance at any window (max
|t|=1.53), but the **sign pattern is exactly the regime story the brief anticipated**: IEF beats cash
as the buffer asset in FULL and 2016-2020 (+0.27 to +0.50pp/yr) and in the classic crash windows
(2008: CAGR −32.2% vs −33.8%, MaxDD −43.1% vs −44.0%; 2020: CAGR +17.9% vs +16.2%, MaxDD −30.2% vs
−31.0%), then **reverses** in 2021+ (−0.74pp/yr) driven entirely by 2022 (CAGR −19.3% vs −17.1%,
MaxDD −24.7% vs −22.6% — bonds were *worse* ballast the one year stocks and bonds fell together).
This extends (not just repeats) the `2026-07-06_portfolio_rotation.md` finding that bonds beat cash
as a defensive leg: true here too at the core-shell buffer level, in the regimes where duration
actually decorrelates from equities — but not a free lunch, and not statistically significant on its
own in any single window given the sample size.

## Caveats

- **LEAP sleeve is a simplification, not a real option** (H4): 1.7×-daily-reset SPY exposure, no
  theta/skew/crash-vega. This is identical across all 3 buffer variants, so it nets out of the
  cash-vs-bonds *comparison* — but the shell's absolute CAGR/Sharpe/MaxDD numbers should not be read
  as a forecast of the real LEAP-based core (see `exp_leap_real_sweep.py` / `2026-07-06_core_strategy.md`
  for the real-option version).
- **Next-bar lag applied uniformly to entries AND exits** (all 4 H's): a "5-day timeout" in H1 can
  realize as a 6-trading-day hold once the exit's own 1-day execution lag is counted. Documented
  design choice (literal "T signal → T+1 trade"), not a bug — but means "timeout" labels are a
  ceiling, not exact.
- **H1 tie-break rule**: when more sectors trigger RSI-2<10 than free slots, the MOST oversold
  (lowest RSI-2) fill first. An unregistered but necessary modeling choice — not swept.
- **H2 small-n**: 14 (Q②) and 15 (Q③) episodes over 27 years. The Q② result clears p<0.05 but is
  still a small sample dominated by a few long-holding-period episodes (e.g. 2020-03 COVID, 256-377
  trading days) — a handful of episode-level outliers materially move the mean.
- **H2 open-position-at-end handling**: any panic episode still open at the end of the data window is
  dropped from the episode table (not force-closed), consistent across quadrant variants.
- **H3 defensive-basket weighting**: equal-thirds XLP/XLV/XLU, rebalanced only at entry (not
  continuously re-equal-weighted while held) — a discrete simplification, not a continuously
  rebalanced basket.
- **H4 monthly rebalance** (not continuous/daily) — a realistic institutional cadence, but a design
  choice; daily constant-mix rebalancing of very different-vol sleeves is a known separate drag
  mechanism (see `exp_core_portfolio_lab.py`'s combiner note) that this experiment does not need to
  re-litigate since all 3 buffer variants share the same monthly cadence.
- **^IRX as cash-rate proxy**: daily-accrual approximation (irx%/100/252) of a secondary-market
  T-bill discount yield, not a true daily-compounding money-market rate — standard simplification,
  small effect size.
- **Point-in-time universe** means FULL-window statistics for XLRE/XLC-eligible episodes are
  necessarily thin pre-2015/2018 (structural, not a bug — see H2's 2018-02 episode, the first one
  where XLRE was even eligible to be picked).
- **No survivorship concern**: all 11 SPDR sectors are large, liquid, currently-listed ETFs.

## Implication

Sector ETFs remain **out of the core's mechanical rule set** — this loop is a second, independent
confirmation (after the rotation-ranking line closed at 0/28) that even *capital-efficiency*/
*deployment-expression* uses of sectors (dip-buying, panic-hedging, defensive-tilting) don't clear
the SPY-control bar. The one place this loop adds new, actionable signal is **H4: the core shell's
buffer asset**. It extends `2026-07-06_portfolio_rotation.md`'s bonds>cash finding down to the
shell-buffer level with the important caveat the rotation study didn't have room to show: bonds help
in classic equity-crash regimes (2008, 2020) and hurt in a 2022-style stocks-and-bonds-fall-together
regime — a **regime-conditional** ballast choice, not a strict dominance. Given no window reaches
significance on its own, this is a "worth a look at implementation time, not a rule to hard-code"
finding, not a new core mechanic to add today.
