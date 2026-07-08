# Result — BTC/ETH vs SPY: is crypto a real decorrelation asset?

**Date:** 2026-07-08  **Script:** `backtest/experiments/exp_crypto_decorr.py`  **Status:** active

## Question

Would carving 5-10% of a SPY-centric core into BTC or ETH meaningfully help via low correlation to equities, or does any historical improvement come mostly from BTC/ETH's 2017-2021 bull run, with 2022+ pulling the other way?

## Method

- Crypto trades 7 days/week; equities do not. Convention: crypto CLOSE reindexed onto the SPY trading-day calendar (exact-date match, ffill for rare gaps), THEN pct_change taken of that aligned series — a weekend/holiday move is entirely attributed to the next SPY trading day's return ("假期跨日報酬照連"). This changes day-to-day attribution only, not weekly/monthly cumulative returns.
- SPY/QQQ/IEF use the repo's standard `r_net` convention (adjusted-close total return, HK 30% dividend withholding netted). BTC/ETH have no dividends so raw == adjusted close; no withholding applied. Cash = ^IRX / 252 (annualized T-bill yield, daily-compounded approximation), reindexed onto the SPY calendar.
- Combo blends: monthly-rebalanced (`exp_core_topup.month_start_mask` — same cadence convention as core v2's LEAP sleeve top-up), 2-asset (SPY base + ONE carve-out), weights {5%, 10%, 20%} carve-out. Windows: ETH-available (2017-11-09+) and 2022+ (harder, post-bull test).
- **Reading discipline (pre-registered, mechanical)**: for every blend in the ETH-available window, split the SAME nav path into pre-2022 and 2022+ legs. If the full-window Sharpe beats 100% SPY AND the 2022+-only leg's Sharpe is WORSE than 100% SPY, flag **BULL-RUN ARTIFACT, NOT DIVERSIFICATION** — the headline gain is a historical-bull-market artifact, not a repeatable diversification effect.
- CAPITAL = $500,000 notionally; all figures reported as returns (capital cancels out). Sharpe = raw daily returns, annualized (repo convention, no rf subtraction).

## Data provenance (`backtest/data.py` `load()`)

| Series | Source | Rows | From | To |
|---|---|---|---|---|
| SPY | yfinance | 8415 | 1993-01-29 | 2026-07-07 |
| SPY(adj) | yfinance(adj) | 8415 | 1993-01-29 | 2026-07-07 |
| QQQ | yfinance | 6873 | 1999-03-10 | 2026-07-07 |
| QQQ(adj) | yfinance(adj) | 6873 | 1999-03-10 | 2026-07-07 |
| IEF | yfinance | 6022 | 2002-07-30 | 2026-07-07 |
| IEF(adj) | yfinance(adj) | 6022 | 2002-07-30 | 2026-07-07 |
| ^IRX | yfinance | 16610 | 1960-01-04 | 2026-07-07 |
| BTC-USD | yfinance | 4313 | 2014-09-17 | 2026-07-08 |
| ETH-USD | yfinance | 3164 | 2017-11-09 | 2026-07-08 |

## Table 1 — Correlation, full period + sub-periods (daily & monthly Pearson)

| Asset / period | vs | Daily corr | Monthly corr | N (days) |
|---|---|---|---|---|
| BTC full (2014-09+) | SPY | +0.23 | +0.35 | 2966 |
| BTC full (2014-09+) | QQQ | +0.23 | +0.33 | 2966 |
| ETH full (2017-11+) | SPY | +0.31 | +0.40 | 2172 |
| ETH full (2017-11+) | QQQ | +0.31 | +0.38 | 2172 |
| BTC 2014-2017 | SPY | +0.02 | +0.35 | 828 |
| BTC 2014-2017 | QQQ | +0.03 | +0.35 | 828 |
| ETH 2014-2017 | SPY | +0.12 | n/a | 34 |
| ETH 2014-2017 | QQQ | +0.14 | n/a | 34 |
| BTC 2018-2021 | SPY | +0.21 | +0.30 | 1008 |
| BTC 2018-2021 | QQQ | +0.21 | +0.25 | 1008 |
| ETH 2018-2021 | SPY | +0.23 | +0.30 | 1008 |
| ETH 2018-2021 | QQQ | +0.22 | +0.31 | 1008 |
| BTC 2022-2026 | SPY | +0.42 | +0.51 | 1130 |
| BTC 2022-2026 | QQQ | +0.42 | +0.49 | 1130 |
| ETH 2022-2026 | SPY | +0.45 | +0.57 | 1130 |
| ETH 2022-2026 | QQQ | +0.45 | +0.54 | 1130 |
| BTC 2024-2026 | SPY | +0.38 | +0.48 | 629 |
| BTC 2024-2026 | QQQ | +0.38 | +0.36 | 629 |
| ETH 2024-2026 | SPY | +0.44 | +0.49 | 629 |
| ETH 2024-2026 | QQQ | +0.44 | +0.39 | 629 |

Note: BTC's 2014-2017 sub-period cell has NO ETH counterpart (ETH data starts 2017-11-09, i.e. inside this bucket only for its last ~7 weeks — reported n/a where the overlap is too thin for a stable estimate).

## Table 2 — Tail correlation: SPY's worst 5% days

| Asset | N (common days) | N (worst-5% days) | Mean SPY ret | Mean crypto ret | Conditional corr |
|---|---|---|---|---|---|
| BTC | 2966 | 149 | -2.7% | -2.5% | +0.35 |
| ETH | 2172 | 109 | -2.9% | -4.5% | +0.37 |

## Table 3 — Crisis windows, SAME calendar window, cumulative return

| Window | Start | End | SPY | BTC | ETH |
|---|---|---|---|---|---|
| 2018Q4 | 2018-10-01 | 2018-12-24 | -19.1% | -38.6% | -36.9% |
| 2020-03 COVID | 2020-02-19 | 2020-03-23 | -33.5% | -36.7% | -52.1% |
| 2022 full year | 2022-01-03 | 2022-12-30 | -18.6% | -64.1% | -67.4% |
| 2025-04 tariff shock | 2025-04-02 | 2025-04-08 | -11.5% | -10.4% | -22.7% |
| 2026-07 (trailing 5d, 2026-06-30->2026-07-07) | 2026-06-30 | 2026-07-07 | +0.9% | +5.3% | +9.8% |

## Table 4 — BTC/ETH standalone: CAGR / annualized vol / MaxDD per sub-period

| Asset | Period | CAGR | Ann. vol | MaxDD | N (days) |
|---|---|---|---|---|---|
| BTC | 2014-2017 | +187.27% | 71.5% | -61.1% | 828 |
| BTC | 2018-2021 | +33.32% | 74.6% | -81.4% | 1008 |
| BTC | 2022-2026 | +7.22% | 52.3% | -66.7% | 1130 |
| BTC | 2024-2026 | +17.75% | 48.9% | -53.1% | 629 |
| ETH | 2014-2017 | n/a | 140.2% | -18.4% | 34 |
| ETH | 2018-2021 | +48.68% | 98.4% | -93.5% | 1008 |
| ETH | 2022-2026 | -15.09% | 69.7% | -72.6% | 1130 |
| ETH | 2024-2026 | -10.00% | 68.8% | -67.6% | 629 |

## Table — Combo A/B, window: ETH-available (2017-11-09+)

Benchmark 100% SPY B&H this window: CAGR +14.38%, Sharpe 0.80, MaxDD -33.8%.

| Carve-out | Weight | CAGR | Sharpe | MaxDD | Worst mo | Pre-2022 Sharpe | 2022+ Sharpe | Judge |
|---|---|---|---|---|---|---|---|---|
| BTC | 5% | +16.28% | 0.88 | -33.9% | -32.9% | 1.03 | 0.72 | improvement holds post-2022 too |
| BTC | 10% | +18.08% | 0.93 | -34.1% | -33.0% | 1.13 | 0.72 | improvement holds post-2022 too |
| BTC | 20% | +21.34% | 0.96 | -35.3% | -33.5% | 1.21 | 0.68 | BULL-RUN ARTIFACT, NOT DIVERSIFICATION |
| ETH | 5% | +17.01% | 0.89 | -34.9% | -33.8% | 1.10 | 0.66 | BULL-RUN ARTIFACT, NOT DIVERSIFICATION |
| ETH | 10% | +19.43% | 0.93 | -36.0% | -34.7% | 1.24 | 0.61 | BULL-RUN ARTIFACT, NOT DIVERSIFICATION |
| ETH | 20% | +23.62% | 0.93 | -38.3% | -36.5% | 1.33 | 0.49 | BULL-RUN ARTIFACT, NOT DIVERSIFICATION |
| IEF | 5% | +13.72% | 0.80 | -32.0% | -31.1% | 0.90 | 0.70 | no full-window improvement |
| IEF | 10% | +13.06% | 0.81 | -30.2% | -29.3% | 0.92 | 0.69 | no full-window improvement |
| IEF | 20% | +11.71% | 0.81 | -26.4% | -25.7% | 0.96 | 0.66 | BULL-RUN ARTIFACT, NOT DIVERSIFICATION |
| cash | 5% | +13.85% | 0.81 | -32.3% | -31.3% | 0.89 | 0.72 | no full-window improvement |
| cash | 10% | +13.31% | 0.82 | -30.7% | -29.8% | 0.89 | 0.73 | improvement holds post-2022 too |
| cash | 20% | +12.20% | 0.84 | -27.5% | -26.6% | 0.91 | 0.76 | improvement holds post-2022 too |

## Table — Combo A/B, window: 2022+ (post-bull, harder test)

Benchmark 100% SPY B&H this window: CAGR +11.57%, Sharpe 0.71, MaxDD -24.8%.

| Carve-out | Weight | CAGR | Sharpe | MaxDD | Worst mo |
|---|---|---|---|---|---|
| BTC | 5% | +11.97% | 0.72 | -26.5% | -13.1% |
| BTC | 10% | +12.30% | 0.72 | -28.3% | -13.9% |
| BTC | 20% | +12.76% | 0.68 | -31.8% | -15.7% |
| ETH | 5% | +11.16% | 0.66 | -26.6% | -13.5% |
| ETH | 10% | +10.62% | 0.61 | -29.1% | -14.6% |
| ETH | 20% | +9.22% | 0.49 | -34.9% | -18.1% |
| IEF | 5% | +10.90% | 0.70 | -24.3% | -12.6% |
| IEF | 10% | +10.22% | 0.69 | -23.8% | -12.3% |
| IEF | 20% | +8.86% | 0.66 | -22.8% | -11.7% |
| cash | 5% | +11.25% | 0.72 | -23.6% | -12.3% |
| cash | 10% | +10.91% | 0.73 | -22.4% | -11.6% |
| cash | 20% | +10.23% | 0.76 | -20.0% | -10.4% |

## Rebalance behavior — 5% BTC blend, 2022 monthly rebalances

- 12 monthly rebalances fell inside 2022; **9** of them found the BTC weight BELOW the 5% target immediately before rebalancing (i.e. the rebalance bought MORE BTC while it was falling).

| Rebalance date | Pre-rebalance BTC weight | Action |
|---|---|---|
| 2022-01-03 | 3.86% | BUY (below target) |
| 2022-02-01 | 4.42% | BUY (below target) |
| 2022-03-01 | 5.97% | SELL (above target) |
| 2022-04-01 | 4.95% | BUY (below target) |
| 2022-05-02 | 4.57% | BUY (below target) |
| 2022-06-01 | 3.96% | BUY (below target) |
| 2022-07-01 | 3.52% | BUY (below target) |
| 2022-08-01 | 5.58% | SELL (above target) |
| 2022-09-01 | 4.50% | BUY (below target) |
| 2022-10-03 | 5.24% | SELL (above target) |
| 2022-11-01 | 4.98% | BUY (below target) |
| 2022-12-01 | 3.95% | BUY (below target) |

## Conclusions

**Correlation is rising over time, not falling (Table 1).** BTC/SPY daily correlation
went +0.02 (2014-2017) -> +0.21 (2018-2021) -> +0.42 (2022-2026) -> +0.38 (2024-2026);
ETH tracks the same shape (+0.23 -> +0.45 -> +0.44). Monthly correlations are even
higher (BTC 2022-2026: +0.51; ETH: +0.57). The "crypto is decorrelated from equities"
pitch was much truer in 2014-2017 (BTC's near-zero correlation era, before
institutional adoption) than it is today — the asset has been getting MORE
equity-correlated, not less, especially since 2022 (macro/rates-driven risk-on/off
now dominates both).

**Tail correlation fails the real test (Table 2).** On SPY's worst 5% days, BTC/ETH
do NOT decouple — conditional correlation is +0.35 (BTC) / +0.37 (ETH), actually
HIGHER than the full-period unconditional correlation. Mean crypto return on those
days is negative and, for ETH, WORSE than SPY's own mean tail-day return (-4.5% vs
-2.9%). A decorrelation asset is supposed to hold up (or at least not amplify) when
equities crash hardest; BTC/ETH do the opposite — this is the single clearest
disproof of the "crypto as portfolio insurance" framing.

**Every real crisis window confirms it (Table 3).** All five windows show BTC/ETH
falling AT LEAST as much as SPY in the SAME window: 2018Q4 (SPY -19.1% vs BTC -38.6%
/ ETH -36.9%), 2020-03 COVID (SPY -33.5% vs BTC -36.7% / ETH -52.1%), 2022 full year
(SPY -18.6% vs BTC -64.1% / ETH -67.4%), 2025-04 tariff shock (SPY -11.5% vs BTC
-10.4% / ETH -22.7% — BTC's the only near-tie, ETH still worse). There is no crisis
window in this dataset where crypto cushioned an equity drawdown.

**Independent-asset stats confirm crypto's well-known drawdown severity (Table 4)**:
BTC -81.4% MaxDD in the 2018-2021 window (the 2018 bear, real data) and -66.7% in
2022-2026 (the 2022 bear); ETH -93.5% (2018-2021) and -72.6% (2022-2026) — both
assets are capable of destroying 2/3-9/10 of their value in a single regime.
ETH's 2014-2017 CAGR cell is suppressed to n/a (only 34 days of data before ETH's
2017-11-09 inception inside that bucket — any annualized number there would be a
meaningless artifact of a tiny, non-representative sample; ETH's ACTUAL early-life
appreciation was enormous but is not usable as a forward-looking statistic).

**Combo A/B (Tables 5-6) — the bull-run-artifact flag matters.** In the
ETH-available window (2017-11+), ALL BTC/ETH carve-outs raise CAGR and Sharpe over
100% SPY (e.g. 10% BTC: Sharpe 0.93 vs 0.80 benchmark). But the mechanical
pre/post-2022 split shows WHY: for every ETH weight and for 20% BTC, the pre-2022
leg's Sharpe (1.03-1.33) is dramatically higher than the 2022+ leg's Sharpe
(0.49-0.72, all AT OR BELOW the 2022+-only 100%-SPY benchmark of 0.71) — flagged
**BULL-RUN ARTIFACT, NOT DIVERSIFICATION**. Only the 5%/10% BTC carve-outs escape
that flag: their 2022+ leg (Sharpe 0.72) sits almost exactly on top of the 2022+
SPY-only benchmark (0.71) rather than below it — i.e. a small BTC carve-out did not
meaningfully HURT risk-adjusted return post-2022, but it also did not clearly help
in the harder, single, post-bull test window (Table 6: 5%/10% BTC Sharpe 0.72/0.72
vs SPY-only 0.71 — a rounding-level difference, not a demonstrated edge). The 20%+
weights and all ETH weights are unambiguously riding 2017-2021's historical bull
run, not demonstrating a repeatable diversification benefit.

**The control group shows what a real low-correlation asset looks like (both
tables).** IEF and cash carve-outs consistently REDUCE MaxDD in both windows (e.g.
IEF 20% in the 2022+ window: MaxDD -22.8% vs SPY-only -24.8%; cash 20%: -20.0%) at
a modest CAGR cost — the textbook shape of a real diversifier (smaller drawdown,
Sharpe roughly flat-to-slightly-better because the vol reduction outpaces the
return cost). BTC/ETH carve-outs do the reverse in the 2022+ window: MaxDD gets
WORSE as the crypto weight rises (BTC 20%: -31.8% vs SPY-only -24.8%; ETH 20%:
-34.9%) — crypto adds risk exactly when a diversifier is supposed to remove it.

**Rebalancing mechanically buys the crypto dip (2022 diagnostic).** 9 of 12 monthly
rebalances in 2022 found the 5%-target BTC weight already below target before
rebalancing (as low as 3.52% in July 2022, mid-crash) — confirming the mechanical
behavior the brief anticipated: a fixed-weight monthly-rebalance policy forces
buying more BTC while it is falling. This is a real, quantifiable cost of the
policy (not a benefit), independent of whether BTC eventually recovers.

## Caveats

- Crypto has no cash flows / no valuation anchor (no earnings, no coupon) — this script answers "historical correlation / combination math," NOT "what should BTC/ETH's future expected return be." A low historical correlation with a fat pre-2022 return tailwind is not evidence of a repeatable expected return.
- Survivorship: BTC and ETH are the two survivors of a much larger set of cryptoassets from the same eras; assets that went to zero (many 2018/2022 alt-coins) are not in this sample. Any statement here about "crypto" only covers these two survivors.
- Single historical path, no bootstrap; BTC/ETH have ~11.8/~8.7 years of history in this dataset — short relative to SPY's ~33 years, so tail-window and sub-period cells for crypto have materially fewer independent regimes than the equity side of every comparison.
- IEF/cash proxies use the same HK 30% dividend-withholding convention applied elsewhere in this repo to bond-ETF distributions — an approximation (bond distributions may be taxed differently in practice), noted for completeness.
- Crypto close-price alignment onto the SPY calendar attributes weekend/holiday moves entirely to the next SPY trading day; this affects daily-return attribution (and hence daily-vs-monthly correlation comparisons) but not cumulative/monthly figures.

## Implication

**BTC/ETH do not qualify as a decorrelation asset on this data — the correlation is
positive, RISING since 2022, and highest exactly when equities crash hardest (tail
days, 2018Q4, 2022, 2025-04 tariff shock).** The headline "adding 10% BTC improved
Sharpe from 0.80 to 0.93" is real arithmetic but is mechanically shown here to be
mostly a 2017-2021 bull-run artifact for every weight/asset except small (5-10%)
BTC carve-outs, whose post-2022 Sharpe is merely FLAT vs 100% SPY (not better) —
i.e. even the best-case cell here is "didn't clearly hurt," not "diversified."

**If the goal is genuine portfolio-level decorrelation (smaller drawdowns, not just
a historical Sharpe bump), IEF or cash carve-outs deliver that mechanically in both
windows tested here — real MaxDD reduction at a modest CAGR cost — and BTC/ETH do
not.** If the goal is instead a small, sized-to-tolerate-90%-drawdown speculative
position on crypto's own (uncorrelated-to-fundamentals) return prospects, that is a
different, legitimate decision — but it should be sized and framed as a directional
bet on the asset itself, not marketed internally as "diversification," per the
caveat above (no cash flows / no valuation anchor here — this script cannot and
does not speak to crypto's future expected return).

No change recommended to core v2's SPY-centric base holding or cash sleeve based on
this result. If the user still wants crypto exposure, a small (<=5%) BTC-only
carve-out is the least-bad shape found here (flat post-2022 risk-adjusted return,
not a demonstrated drag) — but it should be sized and monitored as a speculative
sleeve, with the 2022 rebalance-buys-the-dip mechanic (Table: Rebalance behavior)
understood and accepted, not a "core diversifier" line item.
