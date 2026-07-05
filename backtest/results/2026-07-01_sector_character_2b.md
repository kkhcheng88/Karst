# 2b — sector character: hypothesis largely NOT validated (a disciplined negative result)

2026-07-01. `backtest/experiments/exp_sector_character.py`. Tested the user's hypothesis — "some sectors
(tech-linked) are persistent uptrends → ride the dip; others (consumer/health/...) are
range-bound → mean-revert" — by MEASURING it (not hardcoding), on total-return prices, full
multi-regime history, with an IS/OOS split and deflated Sharpe over all 33 variants.

## Method
Per SPDR sector, total-return (adjusted) closes, cost 2bp, look-ahead-safe (`engine.backtest`):
- character: %>200SMA, Kaufman trend-efficiency (TE), B&H MaxDD.
- 3 variants: HOLD (enter RSI2<10 & >200SMA; exit <200SMA = trend-follow), BOUNCE (same entry;
  exit RSI2>70 = gated mean-revert), MR (enter RSI2<10 no gate; exit RSI2>70 = pure mean-revert).
- vs B&H. Tag = TREND if HOLD wins (Sharpe), CHOP otherwise. Gates: beats B&H, IS/OOS stable, DSR.

## Result — the hypothesis mostly fails the gates
- **TE is ~identical across sectors (0.21–0.24)** → sectors are NOT distinguishable by trendiness
  at this scale (confirms the daily-Hurst finding). %>200SMA varies (66–79%) but doesn't predict
  the winning variant.
- **Only 3/11 tags are IS/OOS-stable; 6/11 beat B&H on Sharpe; most DSR < 0.8** (33-variant trial
  universe). The "trend vs chop" winner flips out-of-sample for 8/11 → mostly noise.
- **In CAGR, nearly every active variant LOSES to B&H** (Tech HOLD 8.0% vs 10.6%; Indus 5.9 vs 9.7;
  Materl 2.2 vs 8.3) **but cuts MaxDD ~half-to-third** (Tech -27% vs -82%; Util -33 vs -52). →
  the dip-timing is **RISK CONTROL, not return** — exactly the project's iron prior (TA on liquid
  names = risk control, not alpha).

## The one credible differentiation
- **Financials (XLF): MR beats B&H on BOTH Sharpe and CAGR (9.0% vs 5.9%), IS/OOS-STABLE**, at only
  24% exposure (sidesteps the GFC -82%). Economically sensible (cyclical, rate-sensitive, range-y).
- **Health (XLV): MR, stable, beats B&H Sharpe.**
- BUT both DSR ≈ 0.71–0.74 < 0.95 → **suggestive, NOT confirmed** under multiple testing.

## Decision (discipline over a pretty feature)
- **Do NOT build the 11-sector trend/chop EXIT map** — it's mostly overfitting (the exact
  multiple-testing false-discovery risk we flagged). The validation gate did its job.
- **Reusable, robust finding → feed Phase 4:** one UNIVERSAL exit, `dip-entry + exit on <200SMA`
  (HOLD), as a risk-control overlay (halves drawdowns across all sectors at modest return cost).
- **Fin / Health = low-confidence "watch for mean-reversion" hints only** (don't pin as rules; DSR
  not cleared).
- Net: the system stays SIMPLER and more honest because we measured instead of assuming.

## Caveats / scope
- TE/Hurst here are SHORT-horizon (20d) → this tests dip-timing character, NOT the multi-YEAR
  secular-uptrend claim (Tech's secular trend is a different, longer timescale; %>200 hints at it
  but it didn't predict the dip-timing winner).
- OOS = last 756d (a strong bull) → biases OOS toward trend variants; part of the instability.
- Older sectors (XLK/XLF/XLE… from 1998) span dotcom+GFC+2022 (multi-regime ✓); XLC (2018),
  XLRE (2015) are bull-only — less regime coverage.
- Data: total-return (yfinance `adjusted=True`, added to `data.py load()` for backtests only;
  the live spine stays raw).

## Files
New: `backtest/experiments/exp_sector_character.py`. Changed: `data.py` (`adjusted=` total-return load).
