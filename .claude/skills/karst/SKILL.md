---
name: karst
description: >-
  Run the Karst options decision-support engine for SPY / QQQ / SPMO. Produces a
  daily 0-100 suitability scorecard per tool (LEAP / PMCC / CSP / CASH) with drivers,
  grounded in this repo's backtested params, and can run any Karst backtest on demand.
  Use when asked for "today's scorecard / read", which option tool fits now, or to
  re-run / extend a backtest. Decision support — the human decides; never auto-trade.
---

# Karst — options regime decision support

Karst scores how favorable each tool is **right now** for the 3 core ETFs, from
quantified regime features. Tools are NOT mutually exclusive; scores can co-exist.
**This is decision support, not autopilot — present scores + drivers, the human allocates
within the invariants. Always surface the honest caveats.**

Run everything from the Karst repo root. Data is fetched live (defeatbeta + yfinance,
network required); the data layer self-handles the console banner.

## Quick win — the daily scorecard
```
python backtest/scorecard.py            # human-readable
python backtest/scorecard.py --json     # machine-readable (parse this)
```
Output per underlying: 0-100 for LEAP / PMCC / CSP / CASH + a `drivers` line
(200SMA position, ADX, IV-rank, RSI-2, 50/200). Present it, then interpret.

## How to interpret (validated logic — see `params/`, `backtest/results/`)
| Tool | High score means | Why (backtested) |
|---|---|---|
| **LEAP** | uptrend (>200SMA) + LOW IV + RSI-2 dip | uncapped leverage; edge = timing; **needs right-side (ruin avoidance)** |
| **PMCC** | uptrend + ELEVATED IV | leveraged long + sell rich calls; rare (uptrend+high-IV uncommon) |
| **CSP** | calm/sideways + LOW IV + dip | short-vol income; thin edge; on indices assignment is recoverable |
| **CASH** | below 200SMA + falling + high IV | all long-delta tools lose in downtrends |

## Guardrails (apply every time)
- **Invariants** (`invariants/systematic_rules.md`): single CSP ≤20% / total ≤50% capital;
  ETF-only for PMCC/CSP; covered-only (no naked); LEAP only price>200SMA; no stop-loss on
  premium sellers (50% PT); pause premium selling around FOMC.
- **Honest caveats**: LEAP/PMCC backtest magnitudes are PROVISIONAL (VIX-as-1yr-IV, low cost,
  single path). CSP's VRP alpha is thin (mostly beta); it loses to pure holding in a bull.
  "High IV" ≈ downtrend = caution, not a free premium harvest.
- **Read the score as REGIME/RISK suitability, NOT a return forecast** (validated: CSP=calm detector,
  CASH=danger flag, LEAP=right-side gate). The ENTRY trigger is separate: RSI-2 dip (drivers show
  RSI2; dip = <10). **PMCC scores are currently degenerate/inflated — treat PMCC manually, don't
  rank by its score.**
- **Judgment not outsourced**: recommend, show drivers + caveats; the user makes the call.

## Other actions
- Regime snapshot: `python backtest/regime.py`
- Re-run a study: `python backtest/exp_*.py` (rsi2_filter / rsi2_exit / rsi2_alpha /
  leap_timing / csp / csp_ivrank / pmcc). Results logged in `backtest/results/`.
- Project memory / state: `.agents/KARS_MEMORY.md`, `.agents/USER.md`.

## Tuning
Score weights are v1 (judgment grounded in backtests) in `backtest/scorecard.py:scores()`.
They are meant to be tuned; if you change them, note why in `backtest/results/`.
