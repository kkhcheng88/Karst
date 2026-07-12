# Sector Constraint-Language Density -- Exploratory Pass (2026-07-10)

> EXPLORATORY, not a formal IC backtest (user-directed: look for patterns before committing to a supervised pass/fail test). No placebo/LM control run yet -- that is the next step ONLY if something here looks worth formalizing.

## Coverage
- Sector-quarters: 908 rows, 84 distinct quarters, 11 sector ETFs
- Quarter range: 2005Q4 .. 2026Q3
- Median tickers covered per sector-quarter: 158

## Descriptive correlations (pooled across all sector-quarters, Spearman)

| signal | fwd_3m_rel | fwd_6m_rel | fwd_12m_rel |
|---|---|---|---|
| density | -0.009 (n=820) | -0.010 (n=820) | -0.008 (n=820) |
| density_yoy_delta | -0.012 (n=784) | -0.002 (n=784) | +0.025 (n=784) |

## Per-sector correlation (density vs fwd_12m_rel, Spearman, n>=8 only)

| sector ETF | rho | n |
|---|---|---|
| XLB | -0.262 | 82 |
| XLC | +0.147 | 33 |
| XLE | -0.005 | 83 |
| XLF | -0.103 | 83 |
| XLI | -0.058 | 82 |
| XLK | -0.187 | 83 |
| XLP | +0.252 | 83 |
| XLRE | -0.252 | 43 |
| XLU | +0.097 | 82 |
| XLV | -0.068 | 83 |
| XLY | -0.184 | 83 |

## Return front-loading check (top-tercile density readings)
> Directly answers: is the forward-12m relative return already fully realised in month 1 (= priced before you could react), or does it persist/build?

- Top-tercile density threshold: 0.269 (n=303 sector-quarters)
- Mean fwd_1m_rel (n=284): -0.0003
- Mean fwd_12m_rel (n=284): -0.0221
- Month-1 share of the 12m move: 1% (spread across the year -- consistent with a slow-diffusion, tradeable signal)

## Honest caveats
- Transcript-only signal: structurally blind to market/industry-wide exogenous shocks that precede any single company's own earnings commentary (export bans, disasters) -- that is the IMA/analyst-report layer's job, not tested here.
- 11-sector cross-section is thin (same caveat as thesis/forward_ic.py's own 9-theme panel) -- correlations here are DESCRIPTIVE, not a significance-tested verdict.
- No placebo (random-phrase) or LM-tone control run in this pass -- add before trusting any positive-looking correlation above.
