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

Run everything from the Karst repo root. Data is fetched live (yfinance-first for fresh
prices, defeatbeta fallback + fundamentals; network required); the data layer self-handles
the console banner.

## The full system is two-tier (scope)
Karst scores **all** names; only **SPY/QQQ/SPMO** get the options toolkit
(LEAP / Covered Call→PMCC / CSP). **Every other name is Long-only.** The top-down scan
below is the spine that delivers this; the scorecard (further down) is the tier-1 options
quick-read it wraps.

## Daily top-down scan (the front door — MVP1 complete: Phase 0+1+4)
```
python backtest/scan.py            # human-readable
python backtest/scan.py --json     # machine-readable (parse this)
```
Runs the funnel: **market gate** (risk_on/neutral/defend from SPY 200SMA + VIX + IWM breadth +
VIX/VIX3M term + SPMO-RS) → **GICS rotation map** → **sector temp** → **two-tier router** →
**RSI-2 timing** → one Card/ticker.
- **GICS rotation (Phase 2a)** ranks the 11 SPDR sectors by RS vs SPY = the DEFENSE/regime lens:
  leadership breadth (narrow = fragile/late-cycle), cyclical-vs-defensive tilt, tech-leading flag
  (offense thesis confirmation). ETF-only. A value-chain (offense) cuts ACROSS GICS → that's Phase 3.
- **Sector temp (LIVE)** from the ETF's REAL holdings (MEMORY ← DRAM: global, SK Hynix/Samsung-led;
  cash filtered; foreign included — RS/ROC currency-cancels). Two-level RS (vs market / vs parent
  SEMI), breadth/coherence, INV-5 laggard (US-tradeable only).
- tier-1 cards = options scorecard; tier-2 cards = Long-only with `action` = **BUY_DIP / WATCH /
  AVOID** (= structural eligibility × RSI-2 timing), plus the sector ETF as a sector-level long.
- **Timing is a SEPARATE field** (`entry_timing`), never folded into the score: a Hot sector +
  eligible name with no dip = `WATCH` ("allowed, wait for a pullback"), NOT buy. Present market
  gate + caveats → sectors → two tiers. See `backtest/results/2026-07-01_spine_phase4_mvp1.md`.
- **v2 pending**: thesis seam (Phase 3) is where ALPHA enters — until then tier-2 score is 0/100
  eligibility and thesis is a NEUTRAL stub; don't read tier-2 score as conviction.

## Quick win — the tier-1 options scorecard
```
python backtest/scorecard.py            # human-readable
python backtest/scorecard.py --json     # machine-readable (parse this)
```
Output per underlying: 0-100 for LEAP / PMCC / CSP / CASH + a `drivers` line
(200SMA position, ADX, IV-rank, RSI-2, 50/200). Present it, then interpret.

## How to interpret (v3 rules — validated, see `backtest/results/2026-06-30_scorecard_validation.md`)
| Tool | High score = | Notes |
|---|---|---|
| **LEAP** | `>200SMA AND RSI-2 dip` | pure gate×dip = the validated entry edge (dip days +0.85% vs +0.16% fwd-5d). Edge is short-horizon + low-capacity |
| **SHORT_CALL** | `>200SMA AND RSI-2 overbought` | sell a call vs your held long on a PEAK (validated: SPY short-call PF 1.53→2.26 at RSI2>90). The only new leg vs LEAP (PMCC long==LEAP). ⚠️ momentum names (QQQ) keep ripping at extreme overbought — don't oversize |
| **CSP** | IV-rank **U-shape** | low-IV end = calm income (SAFE default); high-IV end = **capitulation (RISKY, same regime as CASH)** — check `csp_mode` |
| **CASH** | `<200SMA AND high IV` | defend/reduce; note downturns bounce (flags risk, not guaranteed loss) |

Scores are RAW 0-100 (no return forecast — they read REGIME/RISK suitability). **Low scores across
the board = "no strong signal, wait for a trigger" (a dip, or an IV extreme).** The entry trigger is
the RSI-2 dip itself (drivers show `RSI2 (DIP)` when <10). Always read `csp_mode` before any CSP.

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
- Re-run a study: `python backtest/experiments/exp_*.py` (rsi2_filter / rsi2_exit / rsi2_alpha /
  leap_timing / csp / csp_ivrank / pmcc). Results logged in `backtest/results/`.
- Project memory / state: `.agents/KARS_MEMORY.md`, `.agents/USER.md`.

## Tuning
Score weights are v1 (judgment grounded in backtests) in `backtest/scorecard.py:scores()`.
They are meant to be tuned; if you change them, note why in `backtest/results/`.
