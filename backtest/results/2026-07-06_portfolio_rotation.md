# Result — CAUSAL weekly/monthly sector rotation vs SPY/EW (closing 孤兒/存疑: exp_portfolio_rotation.py)

**Date:** 2026-07-06 (rerun; script written 2026-07-01, flagged in `backtest/experiments/README.md` as
"孤兒/存疑 — 疑被 rotation_challenge 吸收". This file resolves that: **not** a duplicate, see verdict below.)
**Script:** `exp_portfolio_rotation.py`  **Tag:** active (confirms + adds a distinct data point to
Cluster B, alongside `2026-07-01_rotation_challenge.md`)

## Question
Given the oracle ceiling (`2026-07-01_portfolio_oracle.md`: perfect-foresight weekly sector rotation
≈155% net CAGR), how much of that does a REAL, look-ahead-safe, causal weekly/monthly
cross-sectional-momentum signal capture? Mirror: causal capture of the oracle ceiling (increment on
top of the oracle/rotation_challenge/oracle_forensics/gap_forensics chain — Cluster B in the
experiments README).

## Method
9 core SPDR sectors (XLC/XLRE excluded as too young), total-return weekly bars, cost 5bp/unit
turnover. Signals use data through week *t-1* only, applied to week *t*'s return (look-ahead-safe).
Strategies: cross-sectional momentum top-3 by trailing 13-week or 26-week return, rebalanced weekly
or monthly; a MOM+TREND monthly variant additionally requires price > 40-week SMA, else the pick is
dropped to **CASH** (not bonds — contrast with rotation_challenge below). Reported: CAGR/Sharpe/MaxDD/
turnover, full-period + last-10y, and DSR against the 4 momentum-variant trial set.

## Results (real run, 2026-07-06)
**Data provenance:** yfinance via `backtest/data.py` (`load(..., adjusted=True)`), 9 SPDR sectors +
SPY, **1998-12-25 → 2026-07-10, 1437 weekly bars** (no cache/pickle involved — live pull, network
confirmed working).

| strategy | CAGR | Sharpe | MaxDD | turn/yr | CAGR_10y | Sharpe_10y | DSR |
|---|---|---|---|---|---|---|---|
| SPY | 8.6% | 0.56 | −54.6% | 0.0 | 15.0% | 0.91 | — |
| EW 9 sectors | 9.2% | 0.60 | −52.5% | 0.0 | 13.0% | 0.82 | — |
| MOM-13 top3 wk | 4.5% | 0.34 | −57.0% | 20.9/yr | 10.4% | 0.66 | 0.92 |
| MOM-26 top3 wk | 6.7% | 0.47 | −49.0% | 15.3/yr | 12.4% | 0.77 | 0.98 |
| MOM-26 top3 monthly | 7.0% | 0.48 | −49.0% | 6.9/yr | 10.6% | 0.68 | 0.98 |
| MOM-26+TREND monthly | 5.1% | 0.41 | **−43.3%** | 6.8/yr | 7.0% | 0.52 | 0.96 |

(turn/yr already annualized weight-change sum; e.g. 20.9 ≈ 2090%/yr gross turnover for weekly top-3
full rebalancing among 9 sectors.)

## Judgment vs `2026-07-01_rotation_challenge.md` — NOT fully absorbed; confirms + extends
`rotation_challenge` tested a **different specific variant**: DualMom-26 + **IEF Treasury fallback**,
monthly only, 2002-2026 window (IEF-constrained) → CAGR 7.4% / Sharpe 0.57 / MaxDD **−34.2%** vs SPY
11.2%/0.71/−54.6% in that window. This script tests the **weekly-native family** (13w/26w, weekly AND
monthly rebalance) with a **CASH fallback** instead of bonds, over the full 1998-2026 window — a
different signal family, different fallback asset, different window. The specific numbers are **not**
redundant with rotation_challenge's table. However:

- **The verdict is identical**: every causal momentum variant underperforms SPY/EW on CAGR (best here:
  MOM-26 monthly 7.0% vs SPY 8.6%, EW 9.2%) and on Sharpe (best 0.48 vs SPY 0.56), even at weekly
  granularity and even though 3 of 4 variants pass DSR ≥0.95 (not attributable to variant-selection
  luck within this small trial set — but "not luck" ≠ "beats the benchmark").
- **New finding this run adds to Cluster B**: the TREND+cash gate here cuts MaxDD to −43.3% (vs SPY
  −54.6%) — real, but a **materially weaker defensive effect** than rotation_challenge's bond
  fallback (−34.2%). **Bonds > cash as the rotation strategy's defensive leg** — this is a genuinely
  new, previously-unfiled data point (rotation_challenge only tested the bond-fallback variant; this
  script only tested the cash-fallback variant — neither README entry had both side-by-side before).

**Net call: confirms rotation_challenge's core verdict (no causal quant rotation edge on return)
using an independent variant family, and additionally shows WHERE fallback-asset choice matters
(bonds beat cash for drawdown control). Filed as its own result, not marked pure-superseded.**

## Caveats
- Simple flat 5bp/unit-turnover cost model; MOM-13/26 weekly variants have very high annualized
  turnover (15-21×/yr equivalent in weight-churn) — real slippage/market-impact at that turnover in
  less-liquid sector ETFs could be worse than modeled.
- DSR here is computed only against this script's own 4-variant trial set (a locally-scoped
  multiple-testing correction), not the full universe of Cluster B experiments already run on this
  same sector data (oracle, oracle_forensics, gap_forensics, rotation_challenge) — a stricter,
  repo-wide DSR would likely be lower.
- Sector ETFs are liquid, actively-listed instruments — no survivorship concern (unlike the
  individual-stock experiments elsewhere in the family).
- No script code changes were needed — ran as-is against live yfinance data.

## Implication
No new causal sector-rotation quant edge (consistent with the whole Cluster B chain: oracle →
oracle_forensics → gap_forensics → rotation_challenge → this). For the composition engine: **if a
defensive/de-risking leg is added to a rotation sleeve, prefer a Treasury/bond fallback over cash** —
this run's cash-fallback variant achieves a materially smaller drawdown cut for a similar-or-worse
CAGR/Sharpe drag versus rotation_challenge's bond-fallback variant. Composition line stays closed;
the actionable residual (quant = risk/defense, thesis = return) is unchanged from rotation_challenge's
original conclusion.
