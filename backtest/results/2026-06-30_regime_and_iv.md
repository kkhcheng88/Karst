# Result — Regime quantification + IV/CSP reconciliation

**Date:** 2026-06-30  **Scripts:** `backtest/regime.py`, transcripts 56/57  **Tag:** ✅ (regime) / 🔧 design

## Regime distribution (last 10y, ADX + 200SMA)

| Regime | SPY | QQQ | avg ADX | high-IV share |
|---|---|---|---|---|
| strong_up | 29% | 28% | ~32 | 1–5% |
| moderate_up | 19% | 19% | ~22 | ~2% |
| sideways | 35% | 37% | ~15 | ~0% |
| down | 17% | 17% | ~26 | **14–22%** |

**Key:** high IV lives almost ONLY in downtrends. In safe (up/sideways) regimes IV is low.
→ premium-selling's "sell when IV high" is self-defeating: high IV = downtrend = assignment risk.
ADX cleanly separates trend (strong_up ~32) from range (sideways 15.4); thresholds >25/<20 work.

## Quantified scorecard inputs (the answer to "how to quantify 溫和/橫盤/risk-on")
- trend vs range → **ADX(14)** (>25 trend, <20 range)
- direction/strength → price vs SMA200, SMA200 slope(20d), distance, SMA50/200
- IV cheap vs rich → **IV rank** (VIX/VXN 252d percentile)
- risk-on/off (macro, later) → VIX level + 10Y-2Y curve + HYG/LQD credit spread

## IV / CSP reconciliation (transcripts 56/57 — bull put spreads, 2,865 trades)
| IV rank | result |
|---|---|
| **low 0–25%** | **91.2% WR, +$24,556, PF 1.58 (best)** |
| mid 25–50 | −$8,885 |
| high 50–75 | −$7,986 |
| very-high 75–100 | 90.7% WR, +$4,720, PF 1.69 (only 193 trades) |

Video quote: *"Low IV usually means the market is calm and trending. Credit spreads thrive
in calm trending markets."* → **U-shaped: low IV is BEST**, middle worst, very-high a small bonus.

**Correction to an earlier overstatement:** low IV is NOT a "thin/weak" compromise — it is the
BEST environment for credit put spreads (edge = reliability in calm markets, not premium size).
This AGREES with the regime finding (safe = low IV = calm). "Sell high IV" is the actual myth.

**Critical gap:** 56/57 tested bull put SPREADS (defined risk); our `exp_csp` tested NAKED CSP,
which did NOT reproduce the edge (alpha insignificant). The spread caps the assignment-in-crash
tail that hurts naked CSP. → **the validated premium-selling tool is a low-IV bull put SPREAD,
not naked CSP.** Very-high-IV bucket = downtrend/capitulation (advanced contrarian, small sample).

## Design implications
1. Scorecard primary lever = TREND regime (ADX/200SMA) + RSI-2 entry; IV is secondary and
   mostly co-moves with trend (high IV = caution flag, not opportunity for naked selling).
2. Premium-selling leg = **bull put SPREAD in low IV**, not naked CSP.
3. PMCC sim numbers (this session) are garbage-magnitude (VIX-as-1yr-IV, low cost, single path);
   only qualitative read: the short call cushioned MaxDD vs naked LEAP (−36/−42% vs −51/−52%).

## Addendum — naked CSP by IV rank (hold-to-expiry, full history) — `exp_csp_ivrank.py`
Does naked CSP show the 56/57 spread pattern? **No — it's more forgiving.**

| IV rank | QQQ P&L / PF / avg | SPY P&L / PF / avg |
|---|---|---|
| low 0–25 | $26,395 / 2.24 / $175 | $25,935 / 2.13 / $134 |
| mid 25–50 | $12,734 / 1.53 / $131 | $8,212 / 1.40 / $91 |
| high 50–75 | $10,481 / 4.38 / $361 | $18,158 / 5.14 / $363 |
| vhigh 75–100 | $4,094 / 1.92 / $273 | $970 / 1.14 / $54 |

- **All buckets POSITIVE** (vs 56/57 spread's negative mid/high). Naked index CSP held-to-expiry
  benefits from index recovery + no long-put cost drag → **supports CSP-over-spread for indices**.
- "Middle weakest" direction survives (mid 25–50 lowest PF/avg) but not negative.
- high 50–75 surprisingly best per-trade (sell fat premium into a recovering dip) — but SMALL
  sample (29–50 trades) and depends on recovery.
- 🔴 **Caveat:** this is realized expiry P&L; it HIDES mid-trade drawdown. "All positive" assumes
  you can hold through (2008/2020 puts were deeply underwater before recovering) and that the
  index recovers (not Japan-style). The "recoverable" property converts realized loss into
  hold-through risk — governed by sizing (INV-1/2). high/vhigh PFs are sample-thin; don't over-trust.

## Next
- Standalone LEAP delta (0.3 vs 0.5 vs 0.8) via BSM (separate from PMCC long leg 0.8).
- (optional) wheel overlay to model CSP recovery path explicitly.
